"""La señal de saldo: proceder, conmutar o diferir (ADR-0026).

ADR-0025 dejó tres preguntas abiertas —cuán cerca del límite justifica conmutar, cómo se
combinan las ventanas, y si aplica a mitad de un Asunto— y ADR-0026 las contestó. Este
módulo es esa decisión hecha código.

Lo importante es que las dos ventanas **no se colapsan en un booleano**: producen acciones
distintas. Lo que decide cuál se aplica no es el nombre de la ventana sino su **horizonte
de reset**, para no clavar en el núcleo el vocabulario de un proveedor.

Es una función pura: entra una `Suscripcion` y un instante, sale una de tres constantes.
Ni red, ni disco, ni reloj implícito.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from .modelos import Suscripcion, Ventana

#: Por debajo de esta fracción restante, una ventana está cerca del límite (ADR-0026).
#: Es un número fijo, como los 3 minutos de ADR-0017: un valor por configurar es un valor
#: que nadie configura y que hace que dos JAFNE se comporten distinto.
UMBRAL = 0.20

#: Frontera entre "el reset está cerca" y "está lejos". Elegida para cubrir el peor caso
#: de una ventana de 5 h sin nombrarla.
HORIZONTE_DE_ESPERA = timedelta(hours=6)


class Senal(StrEnum):
    """Las tres acciones posibles frente al saldo de un proveedor (ADR-0026)."""

    PROCEDER = "proceder"
    CONMUTAR = "conmutar"
    DIFERIR = "diferir"


@dataclass(frozen=True)
class Decision:
    """Qué hacer, por qué, y —si hay que esperar— hasta cuándo.

    `reanudar` solo viene con `DIFERIR`: un diferimiento sin hora de reanudación sería
    frenar, que es justamente lo que ADR-0025 descartó.
    """

    senal: Senal
    motivo: str
    ventana: str | None = None
    reanudar: datetime | None = None

    def a_dict(self) -> dict[str, object]:
        return {
            "senal": self.senal.value,
            "motivo": self.motivo,
            "ventana": self.ventana,
            "reanudar": self.reanudar.isoformat() if self.reanudar else None,
        }


def _escasa(ventana: Ventana) -> bool:
    """Una ventana sin dato no es una ventana en cero: desconocido no es escasez."""
    return ventana.restante is not None and ventana.restante < UMBRAL


def evaluar(
    suscripcion: Suscripcion | None, ahora: datetime | None = None
) -> Decision:
    """Qué hacer con el saldo de un proveedor, según ADR-0026.

    - Ninguna ventana bajo el umbral → `PROCEDER`.
    - Alguna bajo el umbral con reset **lejos** → `CONMUTAR`: esperar no lo resuelve.
    - Alguna bajo el umbral con reset **cerca** → `DIFERIR` hasta ese reset.

    `CONMUTAR` gana sobre `DIFERIR` si se dan las dos: la ventana larga no se arregla
    esperando.

    Una ventana escasa **sin** `resetea` cuenta como lejos. No es un detalle: sin hora de
    reset no se puede prometer reanudación, y un diferimiento sin promesa es frenar.
    """
    momento = ahora or datetime.now(timezone.utc)

    if suscripcion is None or not suscripcion.ventanas:
        return Decision(
            senal=Senal.PROCEDER,
            motivo="Sin saldo observado para este proveedor.",
        )

    escasas = [v for v in suscripcion.ventanas if _escasa(v)]
    if not escasas:
        return Decision(
            senal=Senal.PROCEDER,
            motivo=f"Ninguna ventana por debajo del {UMBRAL:.0%}.",
        )

    diferibles: list[tuple[Ventana, datetime]] = []
    for ventana in escasas:
        reset = ventana.resetea
        if reset is not None and momento < reset <= momento + HORIZONTE_DE_ESPERA:
            diferibles.append((ventana, reset))

    # Las escasas que no se pueden esperar obligan a conmutar.
    if len(diferibles) < len(escasas):
        lejanas = [v for v in escasas if all(v is not d for d, _ in diferibles)]
        peor = lejanas[0]
        return Decision(
            senal=Senal.CONMUTAR,
            motivo=(
                f"La ventana '{peor.nombre}' está por debajo del {UMBRAL:.0%} y su reset "
                f"no entra en las próximas {int(HORIZONTE_DE_ESPERA.total_seconds() // 3600)} h."
            ),
            ventana=peor.nombre,
        )

    # Todas las escasas se recuperan pronto: se espera a la última.
    ventana, reset = max(diferibles, key=lambda par: par[1])
    return Decision(
        senal=Senal.DIFERIR,
        motivo=(
            f"La ventana '{ventana.nombre}' está por debajo del {UMBRAL:.0%}, pero resetea "
            f"pronto: conviene esperar antes que invalidar el contexto cacheado."
        ),
        ventana=ventana.nombre,
        reanudar=reset,
    )
