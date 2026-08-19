"""Dictado por voz: audio del Usuario a texto, sin salir de sus máquinas (ADR-0036/0037).

El panel deja dictar el mensaje del chat en vez de tipearlo. La transcripción corre con
Whisper **en una máquina del Usuario**, por dos decisiones que ya estaban tomadas: ADR-0025
fijó suscripciones personales y ADR-0034 que JAFNE no maneja credenciales — una API de
transcripción en la nube pide justo la clave propia que no existe, y manda afuera audio
del Usuario hablando de sus proyectos.

*Cuál* máquina se declara (ADR-0037): sin `$JAFNE_VOZ_NODO` se transcribe en el mismo
proceso, y con él se delega en un nodo de la malla ZeroTier —típicamente el que tiene GPU—.
Las dos ramas devuelven lo mismo y fallan igual; la de red agrega `NodoInalcanzable`, que
**no** cae de vuelta a la CPU local en silencio: la diferencia entre un segundo y catorce
tiene que verse.

Esto **no escribe estado**. Entra audio por la request, sale texto, y no se toca
`~/.jafne/` ni el disco. La propiedad que ADR-0035 le devolvió al panel —que el observador
no escribe— se mantiene, y este módulo es el lugar donde eso se puede verificar de un
vistazo: no importa `Almacen`.

El motor es una dependencia **opcional** (`pip install -e ".[voz]"`). Sin él, JAFNE corre
entero menos este botón: se falla con `TranscripcionNoDisponible`, que es un error propio
—como `AdaptadorNoImplementado` de ADR-0028— y **no** una `DecisionPendiente`. La decisión
está tomada; lo que puede faltar es el paquete.
"""

from __future__ import annotations

import io
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

#: Tamaño del modelo por defecto: el grande, que es lo que pidió el Usuario (ADR-0036).
#: Se puede declarar otro, pero no se degrada solo — ver `TranscripcionNoDisponible`.
MODELO_POR_DEFECTO = "large-v3"

#: Cuantización. `int8` es lo que hace que el modelo grande sea usable en CPU sin GPU
#: NVIDIA; con CUDA presente, `float16` sería la elección.
COMPUTO_POR_DEFECTO = "int8"

#: Cuánto audio se acepta de una vez. Un endpoint sin límite es una forma barata de tumbar
#: el proceso del panel, incluso sin querer: alcanza con dejar el micrófono abierto.
LIMITE_AUDIO = 25 * 1024 * 1024

#: Dónde transcribir: `auto` usa la GPU si hay una servible, si no la CPU. Declarar
#: `cuda` a mano y que no haya se **rechaza**, en vez de caer a CPU en silencio (ADR-0037).
DISPOSITIVO_POR_DEFECTO = "auto"

#: Cuánto esperar a un nodo remoto. Generoso: cruza la malla y transcribe del otro lado.
ESPERA_NODO = 300

VARIABLE_MODELO = "JAFNE_VOZ_MODELO"
VARIABLE_COMPUTO = "JAFNE_VOZ_COMPUTO"
VARIABLE_HILOS = "JAFNE_VOZ_HILOS"
VARIABLE_DISPOSITIVO = "JAFNE_VOZ_DISPOSITIVO"

#: A qué nodo de la malla delegar el dictado (ADR-0037). Sin declarar, se transcribe acá.
VARIABLE_NODO = "JAFNE_VOZ_NODO"

#: Token del nodo de voz, que es el de ADR-0020 aplicado a este segundo servicio.
VARIABLE_TOKEN_NODO = "JAFNE_VOZ_TOKEN"


class TranscripcionNoDisponible(RuntimeError):
    """Falta el motor de voz, o el modelo declarado no se pudo cargar.

    Es un error de instalación, no una decisión abierta: por eso no vive en
    `pendientes.py`. ADR-0036 pidió que se rechace en vez de degradar a un modelo más
    chico — servir una transcripción peor que la declarada, sin decirlo, es la clase de
    silencio que ADR-0032 ya había descartado para el aislamiento.
    """


class NodoInalcanzable(TranscripcionNoDisponible):
    """Se declaró un nodo de voz y no contestó.

    Es su propia excepción y **no** se resuelve transcribiendo local: sería servir un
    resultado diez veces más lento sin decirlo, que es exactamente lo que ADR-0036 y
    ADR-0032 descartaron para el modelo y para el aislamiento.
    """


class AudioInvalido(ValueError):
    """El audio que llegó está vacío, es enorme, o no se puede decodificar."""


@dataclass(frozen=True)
class Transcripcion:
    """Lo que se entendió, con qué y dónde."""

    texto: str
    idioma: str | None
    duracion: float
    modelo: str
    #: `local`, o la URL del nodo que la produjo. Va al panel para que el Usuario vea en
    #: qué máquina se transcribió su audio, que después de ADR-0037 dejó de ser obvio.
    donde: str = "local"

    def a_dict(self) -> dict[str, Any]:
        return {
            "texto": self.texto,
            "idioma": self.idioma,
            "duracion": round(self.duracion, 2),
            "modelo": self.modelo,
            "donde": self.donde,
        }


@dataclass(frozen=True)
class EstadoVoz:
    """Si se puede dictar, con qué, y —si no— qué falta.

    Lo consulta el panel al pintar la vista: un botón deshabilitado con el motivo al lado
    informa; uno que aparece y falla al apretarlo, no.
    """

    disponible: bool
    modelo: str
    computo: str
    detalle: str
    cargado: bool = False
    dispositivo: str = "cpu"
    #: La URL del nodo al que se delega, o `None` si se transcribe acá (ADR-0037).
    nodo: str | None = None

    def a_dict(self) -> dict[str, Any]:
        return {
            "disponible": self.disponible,
            "modelo": self.modelo,
            "computo": self.computo,
            "detalle": self.detalle,
            "cargado": self.cargado,
            "dispositivo": self.dispositivo,
            "nodo": self.nodo,
            "limite_audio": LIMITE_AUDIO,
        }


def modelo_declarado() -> str:
    return os.environ.get(VARIABLE_MODELO) or MODELO_POR_DEFECTO


def nodo_declarado() -> str | None:
    """A qué nodo delegar, si se declaró uno (ADR-0037)."""
    return (os.environ.get(VARIABLE_NODO) or "").strip() or None


def dispositivo_declarado() -> str:
    return (os.environ.get(VARIABLE_DISPOSITIVO) or DISPOSITIVO_POR_DEFECTO).lower()


def _hay_cuda() -> bool:
    """Si hay una GPU NVIDIA que CTranslate2 pueda usar de verdad.

    Se pregunta al motor y no a `nvidia-smi`: lo que importa no es que exista la placa,
    sino que estén las librerías con las que este proceso puede cargar el modelo.
    """
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def dispositivo_efectivo() -> str:
    """`cuda` o `cpu`, resolviendo `auto` y rechazando un `cuda` que no existe.

    `auto` eligiendo CPU no es degradar: es lo que el Usuario pidió al no elegir. Declarar
    `cuda` y no tenerla **sí** lo sería, y por eso levanta en vez de seguir (ADR-0037) —
    si no, un nodo con la GPU mal instalada haría el trabajo a 3x tiempo real y nadie se
    enteraría hasta cronometrarlo.
    """
    declarado = dispositivo_declarado()
    if declarado == "cuda":
        if not _hay_cuda():
            raise TranscripcionNoDisponible(
                f"Se declaró ${VARIABLE_DISPOSITIVO}=cuda y CTranslate2 no ve ninguna GPU "
                f"usable. Faltan los binarios de CUDA/cuDNN, o la placa no es NVIDIA. "
                f"ADR-0037 pide rechazar antes que transcribir en CPU sin avisar."
            )
        return "cuda"
    if declarado == "cpu":
        return "cpu"
    return "cuda" if _hay_cuda() else "cpu"


def computo_declarado(dispositivo: str | None = None) -> str:
    """La cuantización: `float16` en GPU, `int8` en CPU, salvo que se declare otra.

    No es un detalle de rendimiento nada más: `int8` es lo que vuelve usable al modelo
    grande sin GPU, y `float16` lo que aprovecha una que sí está.
    """
    declarado = os.environ.get(VARIABLE_COMPUTO)
    if declarado:
        return declarado
    return "float16" if (dispositivo or "cpu") == "cuda" else COMPUTO_POR_DEFECTO


def _hilos() -> int:
    """Cuántos hilos de CPU usar.

    Se dejan dos libres: el panel tiene que seguir respondiendo mientras transcribe, y una
    máquina de trabajo tiene al Usuario haciendo otras cosas encima.
    """
    declarado = os.environ.get(VARIABLE_HILOS)
    if declarado and declarado.isdigit() and int(declarado) > 0:
        return int(declarado)
    return max(1, (os.cpu_count() or 4) - 2)


@lru_cache(maxsize=1)
def _motor():
    """El modelo, cargado una sola vez y perezosamente.

    Perezoso a propósito (ADR-0036): un panel que nadie usó para dictar no paga ni la
    memoria ni el arranque. Después queda caliente, así que la primera transcripción es la
    cara y las siguientes no.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise TranscripcionNoDisponible(
            "El motor de voz no está instalado. Se instala con "
            '`pip install -e ".[voz]"` (ADR-0036). JAFNE corre entero sin él: lo único '
            "que falta es el dictado del panel."
        ) from error

    nombre = modelo_declarado()
    dispositivo = dispositivo_efectivo()
    try:
        return WhisperModel(
            nombre,
            device=dispositivo,
            compute_type=computo_declarado(dispositivo),
            cpu_threads=_hilos(),
        )
    except Exception as error:  # el motor levanta errores propios y de red
        raise TranscripcionNoDisponible(
            f"No se pudo cargar el modelo '{nombre}' en '{dispositivo}': {error}. "
            f"ADR-0036 pide rechazar en vez de degradar a uno más chico — declaralo con "
            f"${VARIABLE_MODELO} o descargalo antes de dictar."
        ) from error


def estado() -> EstadoVoz:
    """Si el dictado está disponible, sin cargar el modelo para averiguarlo."""
    nombre = modelo_declarado()
    nodo = nodo_declarado()

    # Con nodo declarado, el motor que importa es el **del otro lado**: acá puede no haber
    # ni faster-whisper instalado. Se pregunta al nodo, que contesta su propio estado.
    if nodo:
        return _estado_del_nodo(nodo)

    return estado_local()


def estado_local() -> EstadoVoz:
    """Qué puede hacer **este** proceso, sin mirar si hay un nodo declarado.

    Es lo que contesta el nodo cuando le preguntan, por el mismo motivo que
    `transcribir_local`: si consultara el estado delegado, un nodo mal configurado se
    preguntaría a sí mismo para siempre.
    """
    nombre = modelo_declarado()

    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return EstadoVoz(
            disponible=False,
            modelo=nombre,
            computo=computo_declarado(),
            detalle=(
                'El motor de voz no está instalado (`pip install -e ".[voz]"`). El resto '
                "del panel funciona igual."
            ),
        )

    try:
        dispositivo = dispositivo_efectivo()
    except TranscripcionNoDisponible as error:
        return EstadoVoz(
            disponible=False,
            modelo=nombre,
            computo=computo_declarado(),
            detalle=str(error),
        )

    computo = computo_declarado(dispositivo)
    cargado = _motor.cache_info().currsize > 0
    return EstadoVoz(
        disponible=True,
        modelo=nombre,
        computo=computo,
        cargado=cargado,
        dispositivo=dispositivo,
        detalle=(
            f"Dictado local con Whisper '{nombre}' ({computo}, {dispositivo.upper()}). "
            f"El audio no sale de esta máquina ni se guarda (ADR-0036)."
            + ("" if cargado else " El modelo se carga en el primer dictado.")
        ),
    )


def _pedir_al_nodo(nodo: str, ruta: str, datos: bytes | None, espera: float) -> Any:
    """Una llamada al nodo de voz, traduciendo sus errores a los de acá.

    El nodo corre el mismo JAFNE, así que sus errores ya vienen con la forma de este
    módulo: lo único que hay que hacer es no perderlos por el camino.
    """
    url = nodo.rstrip("/") + ruta
    cabeceras = {"Content-Type": "application/octet-stream"}
    token = os.environ.get(VARIABLE_TOKEN_NODO)
    if token:
        cabeceras["X-Jafne-Token"] = token

    pedido = urllib.request.Request(
        url, data=datos, method="POST" if datos is not None else "GET", headers=cabeceras
    )
    try:
        with urllib.request.urlopen(pedido, timeout=espera) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        cuerpo = {}
        try:
            cuerpo = json.loads(error.read().decode("utf-8"))
        except Exception:
            pass
        detalle = cuerpo.get("detalle") or error.reason
        if error.code == 400:
            raise AudioInvalido(f"El nodo {nodo} rechazó el audio: {detalle}") from error
        if error.code == 401:
            raise NodoInalcanzable(
                f"El nodo {nodo} pidió el token de ADR-0020 y no lo aceptó. Definí "
                f"${VARIABLE_TOKEN_NODO} con el mismo que arrancó `jafne voz`."
            ) from error
        raise TranscripcionNoDisponible(f"El nodo {nodo} falló: {detalle}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise NodoInalcanzable(
            f"No se pudo hablar con el nodo de voz {nodo}: {error}. Si la máquina está "
            f"apagada o fuera de la malla, el dictado no corre — ADR-0037 pide decirlo en "
            f"vez de transcribir en la CPU de acá, que tarda diez veces más."
        ) from error


def _estado_del_nodo(nodo: str) -> EstadoVoz:
    """Qué dice de sí mismo el nodo declarado, sin cargar nada de este lado."""
    try:
        # Corto a propósito: esto se consulta al pintar el panel, y un nodo apagado no
        # puede dejar la vista colgada.
        datos = _pedir_al_nodo(nodo, "/api/voz", None, espera=5)
    except TranscripcionNoDisponible as error:
        return EstadoVoz(
            disponible=False,
            modelo=modelo_declarado(),
            computo=computo_declarado(),
            nodo=nodo,
            detalle=str(error),
        )
    return EstadoVoz(
        disponible=bool(datos.get("disponible")),
        modelo=datos.get("modelo") or modelo_declarado(),
        computo=datos.get("computo") or "?",
        cargado=bool(datos.get("cargado")),
        dispositivo=datos.get("dispositivo") or "?",
        nodo=nodo,
        detalle=(
            f"Dictado delegado en el nodo {nodo} (ADR-0037): {datos.get('detalle', '')} "
            f"El audio cruza la malla ZeroTier cifrada y no se guarda de ningún lado."
        ),
    )


def transcribir(audio: bytes, idioma: str | None = None) -> Transcripcion:
    """Convierte audio en texto. No persiste nada: ni el audio ni el resultado.

    `idioma` en `None` deja que Whisper lo detecte, que es lo correcto para un Usuario que
    mezcla español con términos técnicos en inglés.

    Si hay un nodo declarado (ADR-0037), el audio se manda ahí y este proceso no carga
    ningún modelo. El límite de tamaño se aplica **antes** de salir a la red: no tiene
    sentido empujar 30 MB por la malla para que los rechacen del otro lado.
    """
    if not audio:
        raise AudioInvalido("No llegó audio para transcribir.")
    if len(audio) > LIMITE_AUDIO:
        raise AudioInvalido(
            f"El audio pesa {len(audio) // 1024} KB y el límite es "
            f"{LIMITE_AUDIO // 1024} KB (ADR-0036). Dictá en tramos más cortos."
        )

    nodo = nodo_declarado()
    if nodo:
        ruta = f"/api/transcribir?idioma={idioma}" if idioma else "/api/transcribir"
        datos = _pedir_al_nodo(nodo, ruta, audio, espera=ESPERA_NODO)
        return Transcripcion(
            texto=datos.get("texto", ""),
            idioma=datos.get("idioma"),
            duracion=float(datos.get("duracion") or 0.0),
            modelo=datos.get("modelo") or modelo_declarado(),
            donde=nodo,
        )

    return transcribir_local(audio, idioma)


def transcribir_local(audio: bytes, idioma: str | None = None) -> Transcripcion:
    """Transcribe **en este proceso**, ignorando cualquier nodo declarado.

    Es lo que corre el nodo de voz (`jafne voz`), y por eso existe aparte: si el nodo
    llamara a `transcribir()` y alguien dejara `$JAFNE_VOZ_NODO` puesto en esa máquina, se
    reenviaría el pedido a sí mismo en un lazo. Un servicio que presta cómputo no delega:
    esa es su única razón de ser.
    """
    motor = _motor()
    try:
        segmentos, info = motor.transcribe(
            io.BytesIO(audio),
            language=idioma,
            # Recorta los silencios antes de transcribir: dictando se arranca y se corta
            # tarde, y sin esto el modelo alucina texto sobre el silencio del final.
            vad_filter=True,
        )
        texto = "".join(segmento.text for segmento in segmentos).strip()
    except TranscripcionNoDisponible:
        raise
    except Exception as error:
        raise AudioInvalido(
            f"No se pudo decodificar el audio que mandó el navegador: {error}"
        ) from error

    return Transcripcion(
        texto=texto,
        idioma=getattr(info, "language", None),
        duracion=float(getattr(info, "duration", 0.0)),
        modelo=modelo_declarado(),
    )
