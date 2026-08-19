"""Los system prompts por rol, versionados en el repo (ADR-0040).

El Usuario decidió, para el chat del panel: el texto se **agrega** al system prompt de
Claude Code (`--append-system-prompt-file`) en vez de reemplazarlo, vive versionado acá
—no en `~/.jafne/`— y hay un archivo por rol en vez de una plantilla parametrizada.

Hay uno por rol. El del **Encargado** llegó con
[ADR-0044](../../../../docs/adr/0044-la-cadena-de-delegacion.md), que es cuando pasó a tener
algo propio que decir: alcance de organización —no de repositorio— y que delega un Agente
por repo.

El del **Agente** faltaba porque su identidad dependía de *qué es un repo concreto para
JAFNE*, y eso no estaba contestado. Ahora sí lo está, y por eso se pudo escribir: un repo es
un contenedor propio ([ADR-0047](../../../../docs/adr/0047-los-contenedores-son-por-repositorio.md)),
un entorno que él mismo declara en su `Dockerfile.dev`
([ADR-0048](../../../../docs/adr/0048-el-repo-declara-su-entorno-de-desarrollo.md)) y unas
capacidades versionadas en `.agents/` (ADR-0004).

Que el Agente tenga prompt **no** significa que tenga servidor MCP: su alcance es un
repositorio y el servidor no expone ese recorte (ADR-0044). Son dos cosas separadas, y
`mcp.url_para()` le sigue devolviendo `None`.
"""

from __future__ import annotations

from pathlib import Path

from ..roles import Rol

_DIR = Path(__file__).parent

_ARCHIVOS: dict[Rol, str] = {
    Rol.ASISTENTE: "asistente.md",
    Rol.ENCARGADO: "encargado.md",
    Rol.AGENTE: "agente.md",
}


def ruta_prompt(rol: Rol) -> Path | None:
    """El archivo con el system prompt de ese rol, o `None` si todavía no tiene uno."""
    archivo = _ARCHIVOS.get(rol)
    return (_DIR / archivo) if archivo else None
