"""Panel web de JAFNE: dashboard visual y punto de entrada gráfico (ADR-0013)."""

from .api import (
    PUERTO_POR_DEFECTO,
    VARIABLE_TOKEN,
    ConfiguracionInsegura,
    crear_app,
    servir,
    validar_bind,
)

__all__ = [
    "PUERTO_POR_DEFECTO",
    "VARIABLE_TOKEN",
    "ConfiguracionInsegura",
    "crear_app",
    "servir",
    "validar_bind",
]
