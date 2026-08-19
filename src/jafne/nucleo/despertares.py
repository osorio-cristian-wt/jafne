"""La cola de despertares: qué hay que despertar y cuándo (ADR-0035).

[ADR-0024](../../../docs/adr/0024-trabajo-programado-asuntos-disparados-por-tiempo.md)
decidió que hay Asuntos que se abren solos por cadencia, y ADR-0035 fijó que eso lo maneja
un proceso propio —el reloj— con **una sola cola y dos productores**:

| Productor | Qué encola | Origen |
|---|---|---|
| Cadencias declaradas en `programado.yaml` | Repetitivo (diario, semanal) | ADR-0024 |
| El diferimiento por cupo | One-shot, con hora exacta | ADR-0026 |

Este módulo es **la cola, no el reloj**: acá no se duerme, no se abre nada y no se toca el
disco. Entra un instante y sale qué despertares vienen y en qué orden, igual que
`senal_saldo.evaluar` entra una `Suscripcion` y sale una decisión. El bucle que
efectivamente espera y dispara vive en `jafne/reloj.py`, y así se puede verificar el
calendario de un año sin que pase un segundo.

Las cadencias se interpretan en la zona horaria de `desde` (ADR-0035: "lunes 08:00" es el
lunes del Usuario, no UTC). Quien llama elige esa zona, que es lo que mantiene a estas
funciones deterministas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import StrEnum

from . import senal_saldo
from .modelos import Suscripcion

#: Los días de la semana, en el orden de `datetime.weekday()`: lunes = 0.
DIAS: tuple[str, ...] = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)

_HORA = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


class CadenciaInvalida(ValueError):
    """Una cadencia fuera del vocabulario cerrado de ADR-0035.

    Se rechaza al leer en vez de ignorarse: una entrada programada que se ignora en
    silencio no falla, simplemente **nunca dispara**, y nadie se entera hasta que alguien
    pregunta por qué no se armó el sprint.
    """


class TrabajoInvalido(ValueError):
    """Una entrada de `programado.yaml` a la que le falta algo que ADR-0024 pide."""


class Periodo(StrEnum):
    """Catálogo cerrado de períodos de cadencia (ADR-0035)."""

    DIARIA = "diaria"
    SEMANAL = "semanal"


class Origen(StrEnum):
    """Cuál de los dos productores encoló un despertar (ADR-0035)."""

    CADENCIA = "cadencia"
    DIFERIMIENTO = "diferimiento"


def _sin_tildes(texto: str) -> str:
    """`miércoles` y `miercoles` son la misma palabra para quien declara un YAML."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _parsear_hora(texto: str) -> time:
    coincidencia = _HORA.match(texto)
    if not coincidencia:
        raise CadenciaInvalida(
            f"'{texto}' no es una hora del día. Se espera HH:MM en 24 horas, ej. '08:00'."
        )
    return time(int(coincidencia.group(1)), int(coincidencia.group(2)))


@dataclass(frozen=True)
class Cadencia:
    """Cada cuánto se repite un trabajo programado.

    El vocabulario es **cerrado** (ADR-0035), igual que los catálogos de estado: `diaria
    HH:MM` y `semanal <día> HH:MM`. Lo que no entra se rechaza con el catálogo en el
    mensaje, en vez de quedar como una entrada muda.
    """

    periodo: Periodo
    hora: time
    dia: int | None = None  #: Día de la semana (lunes = 0); solo en `semanal`.

    @property
    def texto(self) -> str:
        """Cómo se escribe esta cadencia en `programado.yaml`."""
        reloj = f"{self.hora.hour:02d}:{self.hora.minute:02d}"
        if self.periodo is Periodo.DIARIA:
            return f"diaria {reloj}"
        return f"semanal {DIAS[self.dia or 0]} {reloj}"

    def proximo(self, desde: datetime) -> datetime:
        """El próximo disparo **estrictamente posterior** a `desde`.

        Estrictamente: si fuera "posterior o igual", el reloj que acaba de disparar a las
        08:00 volvería a elegir las 08:00 de hoy y giraría en falso.
        """
        base = datetime.combine(desde.date(), self.hora, tzinfo=desde.tzinfo)
        if self.periodo is Periodo.DIARIA:
            return base if base > desde else base + timedelta(days=1)
        avance = ((self.dia or 0) - base.weekday()) % 7
        candidato = base + timedelta(days=avance)
        return candidato if candidato > desde else candidato + timedelta(days=7)


def parsear_cadencia(texto: str) -> Cadencia:
    """Lee una cadencia declarada, o falla diciendo cuál es el catálogo."""
    partes = _sin_tildes((texto or "").strip().lower()).split()
    if not partes:
        raise CadenciaInvalida(
            "Falta la cadencia. ADR-0024 pide tres cosas por trabajo programado: la "
            "skill, la cadencia y a qué proyecto aplica."
        )

    if partes[0] == Periodo.DIARIA.value and len(partes) == 2:
        return Cadencia(periodo=Periodo.DIARIA, hora=_parsear_hora(partes[1]))

    if partes[0] == Periodo.SEMANAL.value and len(partes) == 3:
        if partes[1] not in DIAS:
            raise CadenciaInvalida(
                f"'{partes[1]}' no es un día de la semana. Se esperaba uno de: "
                f"{', '.join(DIAS)}."
            )
        return Cadencia(
            periodo=Periodo.SEMANAL,
            hora=_parsear_hora(partes[2]),
            dia=DIAS.index(partes[1]),
        )

    raise CadenciaInvalida(
        f"'{texto}' no es una cadencia que JAFNE entienda. El vocabulario es cerrado "
        f"(ADR-0035): 'diaria HH:MM' o 'semanal <día> HH:MM'."
    )


@dataclass(frozen=True)
class TrabajoProgramado:
    """Una entrada de `~/.jafne/programado.yaml` (ADR-0024, ADR-0035).

    Las tres cosas que ADR-0024 pidió, y nada más: la **skill** del Encargado, la
    **cadencia** y a qué **proyecto** aplica. El `id` es la clave de la entrada, y no es
    decorativo: de él sale el id del Asunto que abre cada disparo.
    """

    id: str
    skill: str
    cadencia: Cadencia
    proyecto: str

    def a_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "skill": self.skill,
            "cadencia": self.cadencia.texto,
            "proyecto": self.proyecto,
        }


@dataclass(frozen=True)
class Despertar:
    """Un instante en el que hay que hacer algo, y qué.

    Los dos productores producen esto mismo —*despertar en el instante T y hacer X*—, que
    es la razón por la que ADR-0029 y ADR-0035 fijaron una sola cola y no dos.
    """

    momento: datetime
    origen: Origen
    motivo: str
    trabajo: TrabajoProgramado | None = None
    proveedor: str | None = None

    def a_dict(self) -> dict[str, object]:
        return {
            "momento": self.momento.isoformat(),
            "origen": self.origen.value,
            "motivo": self.motivo,
            "trabajo": self.trabajo.a_dict() if self.trabajo else None,
            "proveedor": self.proveedor,
        }


def id_de_asunto(trabajo: TrabajoProgramado, momento: datetime) -> str:
    """El id del Asunto que abre un disparo: la entrada más la fecha del despertar.

    Derivarlo en vez de sortearlo es la mitad de cómo ADR-0035 evita disparos duplicados:
    dos relojes sobre el mismo `~/.jafne/` intentan abrir **el mismo** Asunto, y el
    segundo choca con el que ya existe (ADR-0006) en vez de abrir uno gemelo.
    """
    return f"{trabajo.id}-{momento:%Y-%m-%d}"


def cola(
    trabajos: list[TrabajoProgramado],
    suscripciones: dict[str, Suscripcion] | None = None,
    desde: datetime | None = None,
) -> list[Despertar]:
    """Los próximos despertares de los dos productores, del más cercano al más lejano.

    Un despertar por cadencia y por proveedor diferido: la cola dice *qué sigue*, no todo
    el calendario futuro. El reloj vuelve a pedirla después de cada disparo, así que una
    cadencia declarada mientras corría entra sin reiniciar nada.
    """
    if desde is None or desde.tzinfo is None:
        raise ValueError(
            "La cola se calcula sobre un instante con zona horaria: la cadencia se "
            "interpreta en la hora local de quien corre el reloj (ADR-0035)."
        )

    despertares = [
        Despertar(
            momento=trabajo.cadencia.proximo(desde),
            origen=Origen.CADENCIA,
            motivo=(
                f"Cadencia '{trabajo.cadencia.texto}' del trabajo '{trabajo.id}': abre un "
                f"Asunto en '{trabajo.proyecto}' para la skill '{trabajo.skill}'."
            ),
            trabajo=trabajo,
        )
        for trabajo in trabajos
    ]

    # Segundo productor: un diferimiento por cupo (ADR-0026). No se declara ni se
    # persiste — sale de `resetea` en saldo.yaml, que ya existe. Un diferimiento no agrega
    # estado, agrega una razón para volver a mirar.
    for proveedor, suscripcion in sorted((suscripciones or {}).items()):
        decision = senal_saldo.evaluar(suscripcion, desde)
        if decision.senal is not senal_saldo.Senal.DIFERIR or decision.reanudar is None:
            continue
        despertares.append(
            Despertar(
                momento=decision.reanudar,
                origen=Origen.DIFERIMIENTO,
                motivo=(
                    f"La ventana '{decision.ventana}' de {proveedor} resetea entonces: "
                    f"el trabajo diferido por cupo puede retomarse."
                ),
                proveedor=proveedor,
            )
        )

    return sorted(despertares, key=lambda d: d.momento)


def proximo(
    trabajos: list[TrabajoProgramado],
    suscripciones: dict[str, Suscripcion] | None = None,
    desde: datetime | None = None,
) -> Despertar | None:
    """El primer despertar de la cola, o `None` si no hay nada agendado."""
    pendientes = cola(trabajos, suscripciones, desde)
    return pendientes[0] if pendientes else None
