"""Los roles que ejecutan un cerebro, y qué tamaño les toca (ADR-0002, ADR-0033, ADR-0044).

El catálogo sale de la jerarquía de ADR-0002. El Usuario no está: es humano y no tiene
cerebro asignado.

**Asistente** y **Encargado** tienen tamaño por defecto para *conversar*; el **Agente** no,
y eso no es un hueco. ADR-0003 decidió que el cerebro de una tarea lo elige el Encargado, y
un Agente siempre nace de una tarea concreta: hay de dónde derivarlo. Conversar es el caso
raro —todavía no hay tarea—, y por eso los dos roles que conversan necesitaron que alguien
les fijara uno.

Que el Encargado vaya en `grande` y el Asistente en `medio` no es escalafón: es qué hace
cada uno. El Asistente enruta y delega; el Encargado piensa la arquitectura y la
organización de su proyecto, y ahí la capacidad del modelo es lo que más pesa.
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

#: Tamaño por defecto de cada rol (ADR-0033, ADR-0044).
#:
#: El Asistente va en `medio`: conversa, enruta y delega, y el trabajo difícil lo hace el
#: nivel de abajo. Un rol que delega no necesita el cerebro más caro para decidir a quién
#: delegarle.
#:
#: El Encargado va en `grande`, y es el Usuario quien lo fijó (ADR-0044). No contradice a
#: ADR-0003 —el cerebro de una **tarea** lo sigue eligiendo él— porque esto es el tamaño con
#: el que *conversa*, que es otra cosa: cuando conversa todavía no hay tarea de donde
#: derivarlo. Su trabajo al conversar es de arquitectura y de organización, y ahí la
#: capacidad del modelo es la variable que más pesa.
#:
#: El Agente **no figura a propósito**: su cerebro lo elige el Encargado tarea por tarea
#: (ADR-0003), y ahí sí hay tarea de donde derivarlo.
TAMANO_POR_DEFECTO: dict[Rol, Tamano] = {
    Rol.ASISTENTE: Tamano.MEDIO,
    Rol.ENCARGADO: Tamano.GRANDE,
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
    """El tamaño con el que ese rol **conversa**, o `None` si se elige por tarea.

    `None` no es "falta decidirlo": es la decisión de ADR-0003 de que lo elija el
    Encargado según la tarea. Hoy solo el Agente cae en ese caso.
    """
    return TAMANO_POR_DEFECTO.get(rol)
