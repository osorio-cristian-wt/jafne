"""El reloj de JAFNE: el proceso que consume la cola de despertares (ADR-0035).

Es un proceso **propio**, no una hebra del panel. ADR-0029 lo había metido adentro del
dashboard por economía y ADR-0035 lo revirtió por dos costos operativos: acoplaba el
trabajo programado a que hubiera una pestaña abierta, y convertía al observador en
escritor de estado. Con esta separación el panel vuelve a ser de solo lectura **sin
excepciones** (ADR-0008, ADR-0013).

El reparto de responsabilidades es el mismo que en el resto del núcleo: `nucleo/
despertares.py` calcula *qué sigue y cuándo* como función pura del tiempo, y acá vive lo
único que no se puede hacer sin efectos — esperar, tomar el candado y abrir el Asunto.
Por eso el reloj se puede verificar sin dormir: se le inyectan `ahora` y `dormir`.

Lo que el reloj hace al disparar una cadencia es **abrir el Asunto** (ADR-0024: es un
Asunto normal, con el mismo ciclo de vida) y dejar anotado qué skill hay que correr.
Correrla necesita el adaptador del proveedor (ADR-0028/ADR-0034), que todavía no existe:
el Asunto queda en `iniciando` con el pedido visible, en vez de simular trabajo hecho.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

from .nucleo import Almacen
from .nucleo.almacen import ProyectoDesconocido
from .nucleo.despertares import Despertar, Origen, cola, id_de_asunto

#: Cuánto espera el reloj cuando no hay nada agendado, antes de volver a mirar. No es una
#: cadencia: es cada cuánto se entera de que el Usuario editó `programado.yaml`.
INTERVALO_OCIOSO = timedelta(minutes=15)

#: El candado que hace cumplir "un solo reloj por almacén" (ADR-0035).
NOMBRE_CANDADO = "reloj.lock"


class RelojYaCorriendo(RuntimeError):
    """Ya hay un reloj sobre este `~/.jafne/`.

    Dos relojes disparan el mismo trabajo dos veces (ADR-0035). El candado corta el caso
    fácil —arrancarlo dos veces en la misma máquina—; el id derivado del Asunto corta el
    resto.
    """


@dataclass(frozen=True)
class Disparo:
    """Qué pasó con un despertar que llegó a su hora.

    `hecho` dice si el despertar produjo su efecto, no si el reloj funcionó. Un
    diferimiento por cupo llega a horario y aun así sale en `False`: reanudar el trabajo
    diferido necesita el adaptador. Es la misma honestidad que el 501 del panel — se
    informa qué falta, no se aparenta que corrió.
    """

    despertar: Despertar
    hecho: bool
    detalle: str
    asunto: str | None = None

    def a_dict(self) -> dict[str, object]:
        return {
            "despertar": self.despertar.a_dict(),
            "hecho": self.hecho,
            "detalle": self.detalle,
            "asunto": self.asunto,
        }


@contextmanager
def candado(almacen: Almacen) -> Iterator[Path]:
    """Toma el candado del almacén mientras corre el reloj (ADR-0035)."""
    ruta = almacen.ruta / NOMBRE_CANDADO
    try:
        descriptor = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        detalle = ruta.read_text(encoding="utf-8").strip() if ruta.is_file() else ""
        raise RelojYaCorriendo(
            f"Ya hay un reloj sobre {almacen.ruta} ({detalle or 'sin detalle'}). Dos "
            f"relojes disparan el mismo trabajo dos veces (ADR-0035). Si estás seguro de "
            f"que no quedó ninguno corriendo, borrá {ruta}."
        ) from None
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        archivo.write(f"pid {os.getpid()} desde {datetime.now().astimezone().isoformat()}")
    try:
        yield ruta
    finally:
        # El candado es del proceso vivo, no del almacén: si no se suelta, el próximo
        # arranque queda bloqueado por un reloj que ya no existe.
        ruta.unlink(missing_ok=True)


def _ahora_local() -> datetime:
    """El instante actual **con** zona horaria local.

    Con zona porque la cadencia se interpreta en la hora del Usuario (ADR-0035) y porque
    la cola compara contra el `resetea` de `saldo.yaml`, que viene en UTC.
    """
    return datetime.now().astimezone()


class Reloj:
    """El bucle: pide la cola, espera al primero y lo dispara.

    `ahora` y `dormir` se inyectan para poder verificar el calendario de un año sin que
    pase un segundo — el mismo criterio con el que `senal_saldo.evaluar` recibe el
    instante en vez de leer el reloj del sistema.
    """

    def __init__(
        self,
        almacen: Almacen,
        ahora: Callable[[], datetime] = _ahora_local,
        dormir: Callable[[float], None] = sleep,
    ) -> None:
        self.almacen = almacen
        self._ahora = ahora
        self._dormir = dormir

    def cola(self, desde: datetime | None = None) -> list[Despertar]:
        """Qué viene, del más cercano al más lejano.

        Se relee entera en cada vuelta: una cadencia agregada mientras el reloj corría
        entra sin reiniciar nada, y una borrada deja de dispararse.
        """
        return cola(
            self.almacen.programados(),
            self.almacen.suscripciones(),
            desde or self._ahora(),
        )

    def disparar(self, despertar: Despertar) -> Disparo:
        """Ejecuta el efecto de un despertar que ya llegó a su hora."""
        if despertar.origen is Origen.DIFERIMIENTO:
            return Disparo(
                despertar=despertar,
                hecho=False,
                detalle=(
                    f"El cupo de '{despertar.proveedor}' ya reseteó, pero retomar el "
                    f"trabajo diferido necesita el adaptador del proveedor "
                    f"(ADR-0028/ADR-0031/ADR-0034), que todavía no está escrito."
                ),
            )

        trabajo = despertar.trabajo
        if trabajo is None:
            raise ValueError(
                "Un despertar de cadencia sin trabajo asociado: la cola siempre los "
                "encola juntos (nucleo/despertares.py)."
            )
        asunto_id = id_de_asunto(trabajo, despertar.momento)

        try:
            # Se verifica el proyecto antes de abrir: `abrir_asunto` crea la carpeta sin
            # preguntar, y una cadencia que apunta a un proyecto inexistente dejaría
            # Asuntos huérfanos cada semana sin que nadie mire.
            self.almacen.proyecto(trabajo.proyecto)
            self.almacen.abrir_asunto(
                trabajo.proyecto,
                asunto_id,
                titulo=f"{trabajo.skill} — {despertar.momento:%Y-%m-%d}",
            )
        except FileExistsError:
            # El id derivado hizo su trabajo: otro reloj (u otra vuelta) ya lo abrió.
            return Disparo(
                despertar=despertar,
                hecho=False,
                asunto=asunto_id,
                detalle=(
                    f"El Asunto '{trabajo.proyecto}/{asunto_id}' ya existía: este "
                    f"despertar ya se había disparado y no se duplica (ADR-0035)."
                ),
            )
        except ProyectoDesconocido:
            return Disparo(
                despertar=despertar,
                hecho=False,
                detalle=(
                    f"El trabajo '{trabajo.id}' apunta al proyecto '{trabajo.proyecto}', "
                    f"que no está en proyectos.yaml. No se abre nada."
                ),
            )

        self.almacen.anotar(
            trabajo.proyecto,
            asunto_id,
            "sistema",
            (
                f"Asunto abierto por el reloj (ADR-0024/ADR-0035) al cumplirse la "
                f"cadencia '{trabajo.cadencia.texto}' del trabajo programado "
                f"'{trabajo.id}'. Queda por correr la skill '{trabajo.skill}': "
                f"ejecutarla necesita el adaptador del proveedor (ADR-0028/ADR-0034). "
                f"Este Asunto no puede consultar al Usuario (ADR-0024)."
            ),
        )
        return Disparo(
            despertar=despertar,
            hecho=True,
            asunto=asunto_id,
            detalle=(
                f"Abierto {trabajo.proyecto}/{asunto_id} para la skill "
                f"'{trabajo.skill}'."
            ),
        )

    def correr(
        self,
        vueltas: int | None = None,
        informar: Callable[[Disparo], None] | None = None,
    ) -> list[Disparo]:
        """El bucle del reloj. Sin `vueltas` no termina: es un proceso de fondo.

        Los despertares vencidos **no se reponen** (ADR-0035): la cola se calcula desde
        *ahora*, así que lo que tocaba mientras el reloj estaba caído no se dispara al
        levantar. Reponer una cadencia semanal caída tres semanas abriría tres Asuntos
        iguales que no pueden preguntarle nada a nadie.
        """
        disparos: list[Disparo] = []
        vuelta = 0
        while vueltas is None or vuelta < vueltas:
            vuelta += 1
            ahora = self._ahora()
            pendientes = self.cola(ahora)
            if not pendientes:
                self._dormir(INTERVALO_OCIOSO.total_seconds())
                continue

            proximo = pendientes[0]
            espera = (proximo.momento - ahora).total_seconds()
            if espera > 0:
                self._dormir(espera)
                if self._ahora() < proximo.momento:
                    # El sueño se cortó antes de tiempo: se vuelve a mirar la cola en vez
                    # de disparar algo que todavía no llegó a su hora.
                    continue

            disparo = self.disparar(proximo)
            disparos.append(disparo)
            if informar is not None:
                informar(disparo)
        return disparos
