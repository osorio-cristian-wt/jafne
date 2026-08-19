"""Los roles que ejecutan un cerebro, y qué tamaño les toca (ADR-0002, ADR-0033).

El catálogo sale de la jerarquía de ADR-0002. El Usuario no está: es humano y no tiene
cerebro asignado.

Solo el **Asistente** tiene tamaño por defecto. Que el Encargado y el Agente no lo tengan
no es un hueco: ADR-0003 ya decidió que el cerebro se elige tarea por tarea, y ponerles un
default contradiría esa decisión en vez de completarla. La dificultad la fija la tarea, no
el escalafón.
"""

from __future__ import annotations

from enum import StrEnum

from .tamanos import Tamano


class Rol(StrEnum):
    """Los tres roles que pueden ejecutar un cerebro (ADR-0002)."""

    ASISTENTE = "asistente"
    ENCARGADO = "encargado"
    AGENTE = "agente"


DESCRIPCIONES: dict[Rol, str] = {
    Rol.ASISTENTE: "Habla con el Usuario, enruta y delega. Uno por instalación de JAFNE.",
    Rol.ENCARGADO: "Dueño de un proyecto y de sus Asuntos. Elige cerebro por tarea.",
    Rol.AGENTE: "Ejecuta una tarea concreta dentro de un Workspace.",
}

#: Tamaño por defecto de cada rol (ADR-0033).
#:
#: El Asistente va en `medio`: conversa, enruta y delega, y el trabajo difícil lo hace el
#: nivel de abajo. Un rol que delega no necesita el cerebro más caro para decidir a quién
#: delegarle.
#:
#: Los otros dos **no figuran a propósito**: su cerebro lo elige el Encargado tarea por
#: tarea (ADR-0003).
TAMANO_POR_DEFECTO: dict[Rol, Tamano] = {
    Rol.ASISTENTE: Tamano.MEDIO,
}


class RolInvalido(ValueError):
    """Un rol fuera del catálogo cerrado de ADR-0033."""


def parsear(valor: object) -> Rol:
    """Convierte un valor en un `Rol`, o falla."""
    try:
        return Rol(str(valor or "").strip().lower())
    except ValueError:
        validos = ", ".join(r.value for r in Rol)
        raise RolInvalido(
            f"'{valor}' no es un rol. El catálogo de ADR-0033 es cerrado: {validos}. "
            f"El Usuario no está en el catálogo: es humano y no ejecuta un cerebro."
        ) from None


def tamano_por_defecto(rol: Rol) -> Tamano | None:
    """El tamaño que le toca a ese rol, o `None` si se elige por tarea.

    `None` no es "falta decidirlo": es la decisión de ADR-0003 de que lo elija el
    Encargado según la tarea.
    """
    return TAMANO_POR_DEFECTO.get(rol)
