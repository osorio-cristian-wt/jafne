"""Estado de la credencial con la que JAFNE va a hablar con el proveedor (ADR-0034).

**JAFNE no maneja credenciales.** No las pide, no las guarda, no las muestra y no tiene
login propio: la sesión es de Claude Code y JAFNE la hereda por ser el proceso que lo
invoca. Este módulo solo *mira* y reporta — nunca lee un secreto ni escribe nada.

El aviso más importante que da es el de `ANTHROPIC_API_KEY`: esa variable **pisa** la
sesión de la suscripción y hace que las llamadas se facturen por token. Alguien que la
tenga puesta de otro proyecto pagaría aparte sin enterarse, que es exactamente lo que
ADR-0034 vino a evitar.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Sobrescribe dónde está el ejecutable de Claude Code.
#:
#: Hace falta porque `claude` **no siempre está en el PATH**: quien usa Claude Code desde
#: la extensión del editor tiene el binario que trae la extensión, no uno instalado a mano.
VARIABLE_CLI = "JAFNE_CLAUDE_CLI"

#: Dónde guarda Claude Code su configuración y sus sesiones.
VARIABLE_CONFIG = "CLAUDE_CONFIG_DIR"

#: La que pisa la suscripción si está definida.
VARIABLE_API_KEY = "ANTHROPIC_API_KEY"


@dataclass(frozen=True)
class EstadoCredencial:
    """Qué se sabe de la credencial, sin haber leído ninguna."""

    cli_encontrado: bool
    ruta_cli: str | None
    config_presente: bool
    ruta_config: str
    api_key_definida: bool
    avisos: tuple[str, ...]
    sugerencia: str | None

    @property
    def listo(self) -> bool:
        """Si están las condiciones para que el adaptador pueda correr.

        **No confirma que la sesión esté viva.** Eso solo se sabe haciendo una llamada
        real, y gastar tokens en un chequeo de estado sería cobrarle al Usuario por mirar
        el panel.
        """
        return self.cli_encontrado and self.config_presente

    def a_dict(self) -> dict[str, Any]:
        return {
            "cli_encontrado": self.cli_encontrado,
            "ruta_cli": self.ruta_cli,
            "config_presente": self.config_presente,
            "ruta_config": self.ruta_config,
            "api_key_definida": self.api_key_definida,
            "listo": self.listo,
            "avisos": list(self.avisos),
            "sugerencia": self.sugerencia,
            "verificado": False,
        }


def ruta_config() -> Path:
    definida = os.environ.get(VARIABLE_CONFIG)
    return Path(definida).expanduser() if definida else Path.home() / ".claude"


def ruta_cli() -> str | None:
    """Dónde está el ejecutable de Claude Code, si se puede encontrar."""
    definida = os.environ.get(VARIABLE_CLI)
    if definida:
        candidato = Path(definida).expanduser()
        return str(candidato) if candidato.is_file() else None
    return shutil.which("claude")


def estado() -> EstadoCredencial:
    """Qué se sabe hoy de la credencial (ADR-0034)."""
    cli = ruta_cli()
    config = ruta_config()
    api_key = bool(os.environ.get(VARIABLE_API_KEY))

    avisos: list[str] = []
    sugerencia: str | None = None

    if api_key:
        avisos.append(
            f"${VARIABLE_API_KEY} está definida y **pisa** la sesión de la suscripción: "
            f"las llamadas se van a facturar por token. Si querés usar tu suscripción "
            f"(ADR-0034), sacala del entorno del proceso de JAFNE."
        )

    if not cli:
        sugerencia = (
            "No encuentro el ejecutable de Claude Code. Instalá la CLI en el PATH, o "
            f"apuntá ${VARIABLE_CLI} al binario que ya tenés."
        )
    elif not config.is_dir():
        sugerencia = (
            f"Está la CLI pero no {config}: parece que nunca se inició sesión. Corré "
            f"`claude` una vez y hacé `/login`."
        )

    return EstadoCredencial(
        cli_encontrado=cli is not None,
        ruta_cli=cli,
        config_presente=config.is_dir(),
        ruta_config=str(config),
        api_key_definida=api_key,
        avisos=tuple(avisos),
        sugerencia=sugerencia,
    )
