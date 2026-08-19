"""Clase de riesgo de una tarea, y su mapeo a driver de aislamiento (ADR-0027).

El Encargado declara algo que entiende —¿este código lo revisó un humano, o lo acaba de
escribir un modelo?— y nunca nombra tecnología de virtualización. Traducir riesgo a driver
es trabajo de Infraestructura, que es donde ya vive la elección de motor (ADR-0012).

El catálogo es **cerrado** y tiene dos valores a propósito: uno que no se puede recitar se
completa a ojo, y una clase elegida a ojo no es una garantía.

La clase viaja en el **pedido de Workspace**, no en `engineering.yaml`: el riesgo es una
propiedad de *la tarea*, no del repositorio.
"""

from __future__ import annotations

from enum import StrEnum


class ClaseRiesgo(StrEnum):
    """Las dos clases de riesgo posibles (ADR-0027)."""

    REVISADO = "revisado"
    GENERADO = "generado"


#: Ante la duda, la clase más estricta. Es el análogo exacto de la política de ADR-0003:
#: ahí se gasta de más antes que arriesgar re-trabajo; acá se **aísla de más antes que
#: arriesgar un escape**.
POR_DEFECTO = ClaseRiesgo.GENERADO

DESCRIPCIONES: dict[ClaseRiesgo, str] = {
    ClaseRiesgo.REVISADO: (
        "El código pasó por revisión humana o ya está commiteado: correr tests conocidos, "
        "buildear, levantar los servicios del proyecto."
    ),
    ClaseRiesgo.GENERADO: (
        "El Agente va a ejecutar código que un modelo acaba de escribir, sin revisar."
    ),
}

#: Runtime OCI que sirve a cada clase (ADR-0032).
#:
#: **No son dos motores: son dos runtimes del mismo Podman**, que elige runtime por
#: contenedor. Esa fue la respuesta a la pregunta de costo que la investigación había
#: dejado abierta — no hace falta operar dos stacks, hace falta un flag por Workspace.
#:
#: `generado` va a microVM porque ese límite lo impone el hardware, por debajo de la capa
#: donde el agente puede razonar. El incidente de 2026 —Claude Code desactivando su propio
#: sandbox para terminar la tarea— es el caso exacto que esto cubre.
DRIVERS: dict[ClaseRiesgo, str] = {
    ClaseRiesgo.REVISADO: "crun",
    ClaseRiesgo.GENERADO: "kata",
}


class RuntimeNoDisponible(RuntimeError):
    """La clase pide un runtime que esta máquina no tiene.

    Se levanta en vez de degradar. Servir `generado` sobre `crun` porque `kata` no está
    instalado le daría al Encargado una garantía que no tiene, y fallar ruidoso es el
    comportamiento correcto acá (ADR-0027, ADR-0032).
    """

    def __init__(self, clase: ClaseRiesgo, driver: str, disponibles: frozenset[str]) -> None:
        self.clase = clase
        self.driver = driver
        tiene = ", ".join(sorted(disponibles)) or "ninguno"
        super().__init__(
            f"La clase '{clase.value}' pide el runtime '{driver}' y esta máquina tiene: "
            f"{tiene}. El Workspace se rechaza en vez de servirse con menos aislamiento "
            f"del declarado (ADR-0032)."
        )


class ClaseRiesgoInvalida(ValueError):
    """Una clase de riesgo fuera del catálogo cerrado de ADR-0027."""


def parsear(valor: object) -> ClaseRiesgo:
    """Convierte un valor recibido en una `ClaseRiesgo`, o falla.

    Un pedido **sin** clase declarada no es un error: es `generado`, la más estricta. Un
    pedido con una clase que no existe sí lo es — ahí alguien quiso decir algo y se
    equivocó, y adivinarle sería elegir el aislamiento por él.
    """
    if valor is None or str(valor).strip() == "":
        return POR_DEFECTO
    try:
        return ClaseRiesgo(str(valor).strip().lower())
    except ValueError:
        validos = ", ".join(c.value for c in ClaseRiesgo)
        raise ClaseRiesgoInvalida(
            f"'{valor}' no es una clase de riesgo. El catálogo de ADR-0027 es cerrado: "
            f"{validos}. Agregar una requiere un ADR que reemplace a ADR-0027."
        ) from None


def driver_para(clase: ClaseRiesgo) -> str:
    """Qué runtime OCI sirve a esa clase de riesgo (ADR-0032)."""
    return DRIVERS[clase]


def exigir_runtime(clase: ClaseRiesgo, disponibles: frozenset[str] | set[str]) -> str:
    """El runtime de esa clase, si esta máquina lo tiene. Si no, falla.

    Los runtimes disponibles los reporta el Broker: el núcleo no consulta la máquina,
    porque entonces no se podría testear ni razonar sobre él. Acá vive la regla, no el
    descubrimiento.
    """
    driver = driver_para(clase)
    if driver not in disponibles:
        raise RuntimeNoDisponible(clase, driver, frozenset(disponibles))
    return driver
