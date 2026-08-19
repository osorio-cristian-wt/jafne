"""Acceso a `~/.jafne/`, la fuente de verdad operativa de los Asuntos (ADR-0007).

    ~/.jafne/
      proyectos.yaml                                   proyectos → repo encargado/
      cerebros.yaml                                    proveedores de IA disponibles
      saldo.yaml                                       saldo observado por proveedor
      asuntos/<proyecto>/<asunto-id>/meta.yaml         estado del Asunto y del contenedor
      asuntos/<proyecto>/<asunto-id>/cierre.md         documentación de cierre
      asuntos/<proyecto>/<asunto-id>/historial.jsonl   conversación del Asunto (ADR-0018)

La memoria durable de lo decidido **no** vive solo acá: el cierre deja una entrada de
bitácora versionada en el repo `encargado/` del proyecto ([ADR-0021]), así que perder
`~/.jafne/` cuesta el estado operativo y los historiales, no el registro de qué se hizo.

El panel lee de acá y **no** escribe (ADR-0008/ADR-0013): el `estado_asunto` lo escribe el
Encargado y el `estado_contenedor` el Workspace Broker.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from . import cierre as skill_cierre
from .despertares import TrabajoInvalido, TrabajoProgramado, parsear_cadencia
from .estados import (
    EstadoAsunto,
    EstadoContenedor,
    parsear,
    parsear_contenedor,
    validar_transicion,
    validar_transicion_contenedor,
)
from .adaptadores import hay_adaptador
from .modelos import Asunto, Cerebro, Mensaje, Proyecto, Suscripcion, Ventana, a_utc
from .roles import Rol, tamano_por_defecto
from .tamanos import parsear as parsear_tamano

#: Variable de entorno para apuntar el almacén a otro lado (tests, varias instancias).
VARIABLE_RAIZ = "JAFNE_HOME"

_ID_VALIDO = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

#: Un id de trabajo programado entra en el id del Asunto que abre, junto con la fecha del
#: despertar (ADR-0035). Se acota acá para que el choque se vea al declararlo y no medio
#: año después, cuando el reloj intente abrir un id de 70 caracteres a las 3 AM.
LARGO_MAXIMO_ID_TRABAJO = 48

PLANTILLA_PROYECTOS = """\
# Proyectos conocidos por el Asistente (ADR-0007).
# La clave es el id del proyecto; `encargado` apunta a su repo encargado/, donde el
# cierre escribe la bitácora durable (ADR-0021).
proyectos: {}
"""

PLANTILLA_CEREBROS = """\
# Cerebros disponibles: proveedor + modelo que puede ejecutar un rol (ADR-0003).
#
# `tamano` usa el catálogo común de ADR-0030, que cruza proveedores:
#
#   tamaño  | Anthropic | OpenAI
#   --------|-----------|-------
#   chico   | Haiku     | Luna
#   medio   | Sonnet    | Tierra
#   grande  | Opus      | Sol
#   gigante | Fable     | (no cubre)
#
# Así el Encargado pide "un cerebro grande" sin nombrar un modelo, y la conmutación de
# ADR-0026 sabe qué es equivalente del otro lado. Un proveedor no cubre necesariamente
# todos los tamaños, y eso es un dato: hoy `gigante` existe solo del lado Anthropic.
#
# Proveedores soportados (ADR-0010): Claude Code y la familia OpenAI Luna/Tierra/Sol.
# Adaptador implementado (ADR-0028): solo Anthropic. Los demás se declaran igual y fallan
# explícito al usarse — un cerebro visible que falla informa, uno ausente miente.
cerebros:
  claude-opus:
    proveedor: anthropic
    modelo: claude-opus-5
    tamano: grande
  claude-sonnet:
    proveedor: anthropic
    modelo: claude-sonnet-5
    tamano: medio
  claude-haiku:
    proveedor: anthropic
    modelo: claude-haiku-4-5
    tamano: chico
  claude-fable:
    proveedor: anthropic
    modelo: claude-fable-5
    tamano: gigante
  openai-sol:
    proveedor: openai
    modelo: sol
    tamano: grande
  openai-tierra:
    proveedor: openai
    modelo: tierra
    tamano: medio
  openai-luna:
    proveedor: openai
    modelo: luna
    tamano: chico
"""

CABECERA_SALDO = """\
# Saldo observado de cada suscripción (ADR-0025).
#
# Lo escribe Infraestructura (`jafne saldo`), no el Usuario: es estado **observado**, no
# configuración. Por eso vive acá y no en cerebros.yaml, que es lo que se declara a mano.
#
# El saldo es del **proveedor**, no del cerebro: el límite pertenece a la suscripción y se
# comparte entre todos los proyectos y modelos de esa familia.
#
# `restante` va de 0 a 1 y `resetea` dice cuándo vuelve a llenarse esa ventana. Las
# ventanas son de tiempo, no de dinero: Claude Code expone una de 5 h y una semanal.
"""

PLANTILLA_SALDO = CABECERA_SALDO + "suscripciones: {}\n"

PLANTILLA_PROGRAMADO = """\
# Trabajo programado: Asuntos que se abren solos, por cadencia (ADR-0024, ADR-0035).
#
# Lo consume el reloj (`jafne reloj`), que corre en su **propio proceso**: no depende de
# que el panel esté abierto, y el panel no dispara nada. Si el reloj no corre, no hay
# trabajo programado — es la contrapartida explícita de ADR-0035.
#
# Cada entrada necesita las tres cosas que ADR-0024 pidió, y nada más:
#
#   <id-del-trabajo>:
#     skill:    qué skill del Encargado corre
#     cadencia: cada cuánto
#     proyecto: sobre qué proyecto de proyectos.yaml
#
# La cadencia usa un vocabulario **cerrado**: `diaria HH:MM` o `semanal <día> HH:MM`.
# Una que JAFNE no entienda se rechaza al leer, no se ignora: una entrada muda no falla,
# simplemente nunca dispara, y nadie se entera hasta que pregunta por qué no corrió.
#
# La hora es la **local de la máquina que corre el reloj**: "lunes 08:00" es el lunes del
# Usuario, no UTC.
#
# Ejemplo — el caso que motivó ADR-0024, armar el sprint semanal:
#
#   sprint-semanal:
#     skill: armar-sprint
#     cadencia: semanal lunes 08:00
#     proyecto: borr
trabajos: {}
"""


class AlmacenNoInicializado(FileNotFoundError):
    """No existe `~/.jafne/`. Se crea con `jafne init`."""


class ProyectoDesconocido(KeyError):
    """El proyecto no está en `proyectos.yaml`."""


class AsuntoDesconocido(KeyError):
    """No hay un Asunto con ese id en ese proyecto."""


class IdInvalido(ValueError):
    """Un id de proyecto o de Asunto que no se puede usar como nombre de carpeta."""


class SaldoInvalido(ValueError):
    """Un saldo fuera del rango que ADR-0025 le da sentido: una fracción de 0 a 1."""


class SinCerebroParaElRol(RuntimeError):
    """El rol tiene un tamaño por defecto, pero no hay cerebro usable de ese tamaño."""


def raiz() -> Path:
    """Dónde vive el almacén: `$JAFNE_HOME` si está definida, si no `~/.jafne`."""
    definida = os.environ.get(VARIABLE_RAIZ)
    return Path(definida).expanduser() if definida else Path.home() / ".jafne"


def _validar_id(valor: str, que: str) -> str:
    """Los ids se usan como nombre de carpeta y llegan por URL: se validan siempre."""
    if not _ID_VALIDO.match(valor or ""):
        raise IdInvalido(
            f"'{valor}' no es un id de {que} válido: se esperan minúsculas, dígitos, "
            f"'.', '-' o '_', empezando por letra o dígito."
        )
    return valor


def _leer_yaml(ruta: Path) -> dict[str, Any]:
    if not ruta.is_file():
        return {}
    contenido = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    return contenido if isinstance(contenido, dict) else {}


def _fraccion(valor: Any) -> float | None:
    """Un `restante` de 0 a 1, o nada.

    Al leer se es tolerante —un saldo ilegible es un saldo que no se observó, no un
    almacén roto—; la validación estricta va en `registrar_saldo`, que es la escritura.
    """
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if 0 <= numero <= 1 else None


class Almacen:
    """Lectura y escritura de `~/.jafne/`."""

    def __init__(self, ruta: Path | None = None) -> None:
        self.ruta = Path(ruta).expanduser() if ruta else raiz()

    # ── estructura ────────────────────────────────────────────────────────────

    @property
    def existe(self) -> bool:
        return self.ruta.is_dir()

    @property
    def ruta_proyectos(self) -> Path:
        return self.ruta / "proyectos.yaml"

    @property
    def ruta_cerebros(self) -> Path:
        return self.ruta / "cerebros.yaml"

    @property
    def ruta_saldo(self) -> Path:
        return self.ruta / "saldo.yaml"

    @property
    def ruta_programado(self) -> Path:
        return self.ruta / "programado.yaml"

    @property
    def ruta_asuntos(self) -> Path:
        return self.ruta / "asuntos"

    def ruta_asunto(self, proyecto: str, asunto_id: str) -> Path:
        _validar_id(proyecto, "proyecto")
        _validar_id(asunto_id, "asunto")
        return self.ruta_asuntos / proyecto / asunto_id

    def ruta_cierre(self, proyecto: str, asunto_id: str) -> Path:
        return self.ruta_asunto(proyecto, asunto_id) / "cierre.md"

    def ruta_historial(self, proyecto: str, asunto_id: str) -> Path:
        return self.ruta_asunto(proyecto, asunto_id) / "historial.jsonl"

    def inicializar(self) -> Path:
        """Crea el esqueleto de `~/.jafne/` sin pisar lo que ya exista."""
        self.ruta.mkdir(parents=True, exist_ok=True)
        self.ruta_asuntos.mkdir(exist_ok=True)
        if not self.ruta_proyectos.exists():
            self.ruta_proyectos.write_text(PLANTILLA_PROYECTOS, encoding="utf-8")
        if not self.ruta_cerebros.exists():
            self.ruta_cerebros.write_text(PLANTILLA_CEREBROS, encoding="utf-8")
        if not self.ruta_saldo.exists():
            self.ruta_saldo.write_text(PLANTILLA_SALDO, encoding="utf-8")
        if not self.ruta_programado.exists():
            self.ruta_programado.write_text(PLANTILLA_PROGRAMADO, encoding="utf-8")
        return self.ruta

    def _exigir_inicializado(self) -> None:
        if not self.existe:
            raise AlmacenNoInicializado(
                f"No existe {self.ruta}. Creá el almacén con `jafne init`."
            )

    # ── proyectos y cerebros ──────────────────────────────────────────────────

    def proyectos(self) -> list[Proyecto]:
        crudos = _leer_yaml(self.ruta_proyectos).get("proyectos") or {}
        return [
            Proyecto(
                id=pid,
                nombre=(datos or {}).get("nombre") or pid,
                encargado=(datos or {}).get("encargado"),
                descripcion=(datos or {}).get("descripcion"),
            )
            for pid, datos in sorted(crudos.items())
        ]

    def proyecto(self, proyecto_id: str) -> Proyecto:
        _validar_id(proyecto_id, "proyecto")
        for proyecto in self.proyectos():
            if proyecto.id == proyecto_id:
                return proyecto
        raise ProyectoDesconocido(
            f"'{proyecto_id}' no está registrado en {self.ruta_proyectos}."
        )

    def cerebros(self) -> list[Cerebro]:
        """Los cerebros declarados, con el saldo de su proveedor y su tamaño.

        Tres fuentes se leen como una: `cerebros.yaml` es lo que el Usuario declara,
        `saldo.yaml` lo que Infraestructura observa (ADR-0025), y el catálogo de ADR-0028
        dice cuáles se pueden usar hoy. Para quien elige cerebro, la lista dejó de ser
        estática.

        Se listan **todos**, incluidos los que no tienen adaptador: uno visible que falla
        al usarse informa, y uno ausente miente por omisión (ADR-0028).
        """
        crudos = _leer_yaml(self.ruta_cerebros).get("cerebros") or {}
        saldos = self.suscripciones()
        cerebros = []
        for cid, datos in sorted(crudos.items()):
            datos = datos or {}
            proveedor = datos.get("proveedor") or "desconocido"
            # `tier` es como se llamaba el campo antes de que ADR-0030 lo renombrara.
            declarado = datos.get("tamano", datos.get("tier"))
            cerebros.append(
                Cerebro(
                    id=cid,
                    proveedor=proveedor,
                    modelo=datos.get("modelo"),
                    tamano=parsear_tamano(declarado) if declarado else None,
                    saldo=saldos.get(proveedor),
                    adaptador=hay_adaptador(proveedor),
                )
            )
        return cerebros

    def cerebro_de(self, rol: Rol) -> Cerebro | None:
        """Qué cerebro le toca a ese rol hoy (ADR-0033).

        Se **deriva** al leer en vez de guardarse: una copia persistida se desincroniza en
        cuanto cambia `cerebros.yaml` o aparece un adaptador nuevo. Misma forma que el
        timeout de ADR-0017.

        Devuelve `None` para los roles sin tamaño por defecto —Encargado y Agente—, que no
        es un hueco: su cerebro lo elige el Encargado tarea por tarea (ADR-0003).

        Levanta `SinCerebroParaElRol` si el rol tiene tamaño pero no hay ningún cerebro de
        ese tamaño **con adaptador**. Es preferible a devolver `None` y que reviente más
        lejos, sin decir qué falta.
        """
        tamano = tamano_por_defecto(rol)
        if tamano is None:
            return None

        candidatos = [c for c in self.cerebros() if c.tamano is tamano]
        usables = [c for c in candidatos if c.adaptador]
        if usables:
            return usables[0]

        if candidatos:
            proveedores = ", ".join(sorted({c.proveedor for c in candidatos}))
            detalle = (
                f"hay cerebros '{tamano.value}' pero ninguno con adaptador "
                f"implementado (declarados: {proveedores})"
            )
        else:
            detalle = f"no hay ningún cerebro de tamaño '{tamano.value}' declarado"
        raise SinCerebroParaElRol(
            f"El rol '{rol.value}' corre en '{tamano.value}' (ADR-0033) y {detalle}. "
            f"Revisá cerebros.yaml."
        )

    # ── trabajo programado (ADR-0024, ADR-0035) ───────────────────────────────

    def programados(self) -> list[TrabajoProgramado]:
        """Las cadencias declaradas en `programado.yaml`, validadas al leer.

        Estricto a propósito, al revés que `suscripciones()`: un saldo ilegible es un
        saldo que no se observó y se degrada a `None`, pero una cadencia ilegible que se
        degradara a nada **nunca dispararía**, en silencio. ADR-0035 pidió lo contrario:
        se rechaza y se dice cuál es el catálogo.
        """
        crudos = _leer_yaml(self.ruta_programado).get("trabajos") or {}
        trabajos: list[TrabajoProgramado] = []
        for tid, datos in sorted(crudos.items()):
            datos = datos or {}
            _validar_id(tid, "trabajo programado")
            if len(tid) > LARGO_MAXIMO_ID_TRABAJO:
                raise TrabajoInvalido(
                    f"El id de trabajo '{tid}' es demasiado largo: el Asunto que abre "
                    f"cada disparo lo lleva con la fecha pegada (ADR-0035), así que no "
                    f"puede pasar de {LARGO_MAXIMO_ID_TRABAJO} caracteres."
                )
            faltan = [c for c in ("skill", "cadencia", "proyecto") if not datos.get(c)]
            if faltan:
                raise TrabajoInvalido(
                    f"Al trabajo programado '{tid}' le falta {', '.join(faltan)}. "
                    f"ADR-0024 pide las tres cosas: la skill, la cadencia y a qué "
                    f"proyecto aplica."
                )
            trabajos.append(
                TrabajoProgramado(
                    id=tid,
                    skill=str(datos["skill"]),
                    cadencia=parsear_cadencia(str(datos["cadencia"])),
                    proyecto=_validar_id(str(datos["proyecto"]), "proyecto"),
                )
            )
        return trabajos

    # ── saldo de las suscripciones (ADR-0025) ─────────────────────────────────

    def suscripciones(self) -> dict[str, Suscripcion]:
        """El saldo observado por proveedor, tal como lo dejó Infraestructura."""
        crudas = _leer_yaml(self.ruta_saldo).get("suscripciones") or {}
        salida: dict[str, Suscripcion] = {}
        for proveedor, datos in sorted(crudas.items()):
            datos = datos or {}
            ventanas = tuple(
                Ventana(
                    nombre=nombre,
                    restante=_fraccion((v or {}).get("restante")),
                    resetea=a_utc((v or {}).get("resetea")),
                )
                for nombre, v in sorted((datos.get("ventanas") or {}).items())
            )
            salida[proveedor] = Suscripcion(
                proveedor=proveedor,
                ventanas=ventanas,
                plan=datos.get("plan"),
                observado=a_utc(datos.get("observado")),
                fuente=datos.get("fuente"),
            )
        return salida

    def registrar_saldo(
        self,
        proveedor: str,
        ventana: str,
        restante: float,
        resetea: datetime | None = None,
        plan: str | None = None,
        fuente: str | None = None,
    ) -> Suscripcion:
        """Anota cuánto queda de una ventana de un proveedor.

        Es la escritura de Infraestructura, el análogo de `actualizar_contenedor` para el
        otro eje que gestiona (ADR-0025). Existe antes que la medición automática por la
        misma razón que `jafne contenedor` existe antes que el Broker: el contrato se
        puede fijar aunque la fuente del dato siga en discusión — **cómo** Infraestructura
        observa el consumo es el pendiente `medicion-de-consumo`.

        Cada llamada actualiza **una** ventana y conserva las demás: las de 5 h y semanal
        se observan juntas pero se vencen por separado.
        """
        self._exigir_inicializado()
        _validar_id(proveedor, "proveedor")
        _validar_id(ventana, "ventana")
        if not isinstance(restante, (int, float)) or not 0 <= float(restante) <= 1:
            raise SaldoInvalido(
                f"'{restante}' no es un saldo válido: se espera la fracción que queda de "
                f"la ventana, de 0 (agotada) a 1 (intacta)."
            )

        crudas = _leer_yaml(self.ruta_saldo).get("suscripciones") or {}
        actual = dict(crudas.get(proveedor) or {})
        ventanas = dict(actual.get("ventanas") or {})
        ventanas[ventana] = {
            "restante": round(float(restante), 4),
            "resetea": resetea.isoformat() if resetea else None,
        }
        ventanas[ventana] = {k: v for k, v in ventanas[ventana].items() if v is not None}
        actual.update(
            {
                "plan": plan if plan is not None else actual.get("plan"),
                "fuente": fuente if fuente is not None else actual.get("fuente"),
                "observado": datetime.now(timezone.utc).isoformat(),
                "ventanas": ventanas,
            }
        )
        crudas[proveedor] = {k: v for k, v in actual.items() if v is not None}

        self.ruta_saldo.write_text(
            CABECERA_SALDO
            + yaml.safe_dump(
                {"suscripciones": dict(sorted(crudas.items()))},
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        return self.suscripciones()[proveedor]

    # ── asuntos ───────────────────────────────────────────────────────────────

    def asuntos(self, proyecto: str | None = None) -> list[Asunto]:
        """Todos los Asuntos, o los de un proyecto.

        El Asistente ve los de todos los proyectos a la vez (ADR-0008), así que sin
        filtro devuelve la vista completa.
        """
        if not self.ruta_asuntos.is_dir():
            return []
        if proyecto is not None:
            _validar_id(proyecto, "proyecto")
            carpetas = [self.ruta_asuntos / proyecto]
        else:
            carpetas = sorted(p for p in self.ruta_asuntos.iterdir() if p.is_dir())

        encontrados: list[Asunto] = []
        for carpeta in carpetas:
            if not carpeta.is_dir():
                continue
            for carpeta_asunto in sorted(p for p in carpeta.iterdir() if p.is_dir()):
                asunto = self._leer_asunto(carpeta.name, carpeta_asunto)
                if asunto is not None:
                    encontrados.append(asunto)
        return encontrados

    def asunto(self, proyecto: str, asunto_id: str) -> Asunto:
        carpeta = self.ruta_asunto(proyecto, asunto_id)
        asunto = self._leer_asunto(proyecto, carpeta)
        if asunto is None:
            raise AsuntoDesconocido(f"No hay un Asunto '{asunto_id}' en '{proyecto}'.")
        return asunto

    def _leer_asunto(self, proyecto: str, carpeta: Path) -> Asunto | None:
        meta = carpeta / "meta.yaml"
        if not meta.is_file():
            return None
        historial = carpeta / "historial.jsonl"
        mensajes = (
            sum(1 for linea in historial.read_text("utf-8").splitlines() if linea.strip())
            if historial.is_file()
            else 0
        )
        return Asunto.desde_meta(
            proyecto=proyecto,
            asunto_id=carpeta.name,
            meta=_leer_yaml(meta),
            tiene_cierre=(carpeta / "cierre.md").is_file(),
            mensajes=mensajes,
        )

    def cierre(self, proyecto: str, asunto_id: str) -> str | None:
        """El `cierre.md` del Asunto, si la skill de cierre ya lo escribió."""
        archivo = self.ruta_cierre(proyecto, asunto_id)
        return archivo.read_text(encoding="utf-8") if archivo.is_file() else None

    # ── historial de la conversación (ADR-0018) ──────────────────────────────

    def historial(self, proyecto: str, asunto_id: str) -> list[Mensaje]:
        """La conversación del Asunto, en orden.

        Sobrevive al contenedor: el contexto es del Asunto, el contenedor es del
        Workspace (ADR-0018).
        """
        archivo = self.ruta_historial(proyecto, asunto_id)
        if not archivo.is_file():
            return []
        mensajes = []
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            try:
                mensajes.append(Mensaje.desde_dict(json.loads(linea)))
            except json.JSONDecodeError:
                continue  # una línea corrupta no invalida el resto del historial
        return mensajes

    def anotar(self, proyecto: str, asunto_id: str, rol: str, texto: str) -> Mensaje:
        """Agrega un mensaje al historial.

        Se escribe **incrementalmente**, no al cerrar: un cierre que falla no puede
        llevarse la conversación con él (ADR-0018).
        """
        mensaje = Mensaje(momento=datetime.now(timezone.utc), rol=rol, texto=texto)
        archivo = self.ruta_historial(proyecto, asunto_id)
        archivo.parent.mkdir(parents=True, exist_ok=True)
        with archivo.open("a", encoding="utf-8") as salida:
            salida.write(json.dumps(mensaje.a_dict(), ensure_ascii=False) + "\n")
        return mensaje

    # ── escrituras (Encargado y Workspace Broker, no el panel) ───────────────

    def abrir_asunto(
        self,
        proyecto: str,
        asunto_id: str,
        titulo: str | None = None,
        rama: str | None = None,
        repos: tuple[str, ...] = (),
    ) -> Asunto:
        """Registra un Asunto nuevo en `iniciando` (ADR-0006, ADR-0009).

        Registra **solo el Asunto**. Crear el contenedor/workspace que ADR-0006 pide en la
        apertura no está implementado — ver el pendiente `workspace-broker` —, por eso
        `estado_contenedor` queda sin definir y el Asunto no avanza solo a
        `interactuando_con_el_usuario`.
        """
        self._exigir_inicializado()
        carpeta = self.ruta_asunto(proyecto, asunto_id)
        if (carpeta / "meta.yaml").exists():
            raise FileExistsError(
                f"Ya existe el Asunto '{asunto_id}' en '{proyecto}'. Se retoma o se "
                f"reabre, no se vuelve a abrir (ADR-0006/ADR-0018)."
            )
        ahora = datetime.now(timezone.utc)
        asunto = Asunto(
            proyecto=proyecto,
            id=asunto_id,
            estado_asunto=EstadoAsunto.INICIANDO,
            titulo=titulo,
            rama=rama,
            repos=repos,
            creado=ahora,
            ultima_actividad=ahora,
        )
        self._escribir(asunto)
        return asunto

    def actualizar_estado(
        self,
        proyecto: str,
        asunto_id: str,
        nuevo: str | EstadoAsunto,
        motivo: str | None = None,
    ) -> Asunto:
        """Mueve el `estado_asunto`, validando contra el diagrama de ADR-0009."""
        actual = self.asunto(proyecto, asunto_id)
        destino = parsear(nuevo)
        validar_transicion(actual.estado_asunto, destino)
        actualizado = replace(
            actual,
            estado_asunto=destino,
            motivo=motivo if motivo is not None else actual.motivo,
            ultima_actividad=datetime.now(timezone.utc),
        )
        self._escribir(actualizado)
        return actualizado

    def actualizar_contenedor(
        self, proyecto: str, asunto_id: str, estado: str | EstadoContenedor
    ) -> Asunto:
        """Mueve el `estado_contenedor`, el eje que gestiona Infraestructura (ADR-0008).

        Valida contra el catálogo y el diagrama cerrados en ADR-0016.
        """
        actual = self.asunto(proyecto, asunto_id)
        destino = parsear_contenedor(estado)
        assert destino is not None
        validar_transicion_contenedor(actual.estado_contenedor, destino)
        actualizado = replace(actual, estado_contenedor=destino)
        self._escribir(actualizado)
        return actualizado

    def marcar_pregunta(
        self, proyecto: str, asunto_id: str, pendiente: bool
    ) -> Asunto:
        """Sube o baja `pregunta_pendiente` (ADR-0017).

        Es lo que habilita el timeout de 3 minutos: sin pregunta pendiente, un Asunto
        callado está trabajando en modo delegado, no esperando al Usuario.
        """
        actual = self.asunto(proyecto, asunto_id)
        actualizado = replace(
            actual,
            pregunta_pendiente=pendiente,
            ultima_actividad=datetime.now(timezone.utc),
        )
        self._escribir(actualizado)
        return actualizado

    def reabrir_asunto(self, proyecto: str, asunto_id: str) -> Asunto:
        """Reabre un Asunto cerrado conservando su contexto (ADR-0018).

        El historial y el `cierre.md` quedan donde estaban — son artefactos del Asunto.
        El contenedor **no** se resucita: queda en `destruido` y hace falta pedir un
        Workspace nuevo, que es lo que significa volver a `iniciando`.
        """
        actual = self.asunto(proyecto, asunto_id)
        validar_transicion(actual.estado_asunto, EstadoAsunto.INICIANDO)
        actualizado = replace(
            actual,
            estado_asunto=EstadoAsunto.INICIANDO,
            pregunta_pendiente=False,
            motivo="reapertura",
            ultima_actividad=datetime.now(timezone.utc),
        )
        self._escribir(actualizado)
        self.anotar(
            proyecto,
            asunto_id,
            "sistema",
            f"Asunto reabierto con {actualizado.mensajes} mensajes de contexto previo.",
        )
        return actualizado

    def cerrar_asunto(
        self, proyecto: str, asunto_id: str, resumen: str
    ) -> tuple[Asunto, skill_cierre.Cierre]:
        """Corre la skill de cierre: documenta y valida (ADR-0019, ADR-0021).

        Escribe primero (`cierre.md` + bitácora en el repo `encargado/`) y valida
        después, porque la validación 3 verifica justamente que eso quedó escrito. Si
        alguna validación falla, el Asunto vuelve a `interactuando_con_el_usuario` con el
        motivo — no hay cierre parcial.
        """
        asunto = self.asunto(proyecto, asunto_id)
        if asunto.estado_asunto is not EstadoAsunto.CERRANDO:
            asunto = self.actualizar_estado(
                proyecto, asunto_id, EstadoAsunto.CERRANDO, motivo="cerramos asunto"
            )

        ruta_cierre = self.ruta_cierre(proyecto, asunto_id)
        ruta_cierre.parent.mkdir(parents=True, exist_ok=True)
        ruta_cierre.write_text(resumen.strip() + "\n", encoding="utf-8")

        try:
            registro = self.proyecto(proyecto)
        except ProyectoDesconocido:
            registro = None
        ruta_bitacora = skill_cierre.ruta_de_bitacora(
            registro.encargado if registro else None, asunto
        )
        if ruta_bitacora is not None:
            skill_cierre.escribir_bitacora(ruta_bitacora, asunto, resumen)

        resultado = skill_cierre.evaluar(asunto, ruta_cierre, ruta_bitacora)
        destino = (
            EstadoAsunto.CERRADO
            if resultado.paso
            else EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO
        )
        asunto = self.actualizar_estado(
            proyecto, asunto_id, destino, motivo=resultado.motivo
        )
        return asunto, resultado

    def _escribir(self, asunto: Asunto) -> None:
        carpeta = self.ruta_asunto(asunto.proyecto, asunto.id)
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "meta.yaml").write_text(
            yaml.safe_dump(asunto.a_meta(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
