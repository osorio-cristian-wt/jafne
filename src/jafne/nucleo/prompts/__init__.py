"""Los system prompts por rol, versionados en el repo (ADR-0040).

El Usuario decidió, para el chat del panel: el texto se **agrega** al system prompt de
Claude Code (`--append-system-prompt-file`) en vez de reemplazarlo, vive versionado acá
—no en `~/.jafne/`— y hay un archivo por rol en vez de una plantilla parametrizada.

Solo existe el del Asistente: es el único rol al que el encargo de identidad le tocó
(2026-08-19). Encargado y Agente se agregan cuando les toque el suyo, con el mismo patrón.
"""

from __future__ import annotations

from pathlib import Path

from ..roles import Rol

_DIR = Path(__file__).parent

_ARCHIVOS: dict[Rol, str] = {
    Rol.ASISTENTE: "asistente.md",
}


def ruta_prompt(rol: Rol) -> Path | None:
    """El archivo con el system prompt de ese rol, o `None` si todavía no tiene uno."""
    archivo = _ARCHIVOS.get(rol)
    return (_DIR / archivo) if archivo else None
