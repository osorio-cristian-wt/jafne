"""Cómo se le declara el MCP de JAFNE a un agente (ADR-0042, ADR-0044).

Este módulo es el lado **cliente**: arma la configuración que se le pasa a la CLI para que
vea el servidor MCP que Infraestructura sirve. El servidor vive en `jafne/infraestructura.py`.

Lo que hace que el acotamiento por rol funcione está acá: **la URL la arma JAFNE**, no el
agente. El Asistente recibe `/mcp/asistente` y ve todos los proyectos; un Encargado recibe
`/mcp/proyecto/<id>` y ve el suyo. Si el rol fuera un campo del mensaje, un Encargado podría
declararse Asistente y la jerarquía de ADR-0002 se caería con una línea de texto.

Dos cosas que se verificaron contra la CLI real el 2026-08-19, porque ninguna es obvia:

- **`--mcp-config` acepta el JSON como string**, no solo como archivo. Se pasa inline: un
  archivo temporal por conversación habría que limpiarlo, y nadie limpia bien.
- **`acceptEdits` no alcanza para que el agente *use* las herramientas MCP.** Ve el servidor
  y las lista, pero la llamada queda esperando una aprobación que desde el panel no hay
  quién dé — el mismo problema que ADR-0039 ya había encontrado. Hay que permitirlas
  explícitamente con `--allowed-tools`.
"""

from __future__ import annotations

import json
import os

from .roles import Rol

#: Nombre del servidor dentro de la configuración. Es lo que la CLI usa para prefijar las
#: herramientas: `proyectos_listar` se vuelve `mcp__jafne__proyectos_listar`.
NOMBRE = "jafne"

#: Con esto se permiten **todas** las herramientas del servidor, y solo las de él.
#:
#: Se permite el servidor entero y no herramienta por herramienta a propósito: el catálogo
#: ya viene acotado por rol del lado del servidor (ADR-0042), así que una lista acá sería
#: una segunda copia del acotamiento, capaz de desincronizarse con la primera.
HERRAMIENTAS_PERMITIDAS = f"mcp__{NOMBRE}"

#: Dónde corre Infraestructura, y con qué token se le habla.
VARIABLE_NODO = "JAFNE_INFRA"
VARIABLE_TOKEN = "JAFNE_INFRA_TOKEN"

#: Puerto por defecto. Uno más que el nodo de voz. No es una decisión de diseño.
PUERTO_POR_DEFECTO = 8732


def nodo(url: str | None = None) -> str:
    """Dónde está Infraestructura. Por defecto, en esta máquina."""
    crudo = url or os.environ.get(VARIABLE_NODO) or f"http://127.0.0.1:{PUERTO_POR_DEFECTO}"
    return crudo.rstrip("/")


def url_para(rol: Rol, proyecto: str | None = None, url: str | None = None) -> str | None:
    """El punto de entrada MCP que le toca a ese rol, o `None` si no le toca ninguno.

    El **Agente** todavía no tiene: su alcance es un repositorio (ADR-0044) y el servidor no
    expone ese recorte. Devolver `None` es lo correcto — darle el del Encargado le daría la
    vista del proyecto entero, que es justamente lo que la jerarquía separa.
    """
    base = nodo(url)
    if rol is Rol.ASISTENTE:
        return f"{base}/mcp/asistente"
    if rol is Rol.ENCARGADO and proyecto:
        return f"{base}/mcp/proyecto/{proyecto}"
    return None


def configuracion(
    rol: Rol,
    proyecto: str | None = None,
    url: str | None = None,
    token: str | None = None,
) -> str | None:
    """El JSON que se le pasa a `--mcp-config`, o `None` si a ese rol no le toca MCP.

    Se devuelve serializado porque así es como viaja: la CLI acepta el JSON inline.
    """
    destino = url_para(rol, proyecto, url)
    if not destino:
        return None

    servidor: dict = {"type": "http", "url": destino}
    secreto = token or os.environ.get(VARIABLE_TOKEN)
    if secreto:
        # Fuera de loopback Infraestructura exige el token (ADR-0020). Va en la cabecera y
        # no en la URL: la URL aparece en la línea de comandos, que cualquiera puede ver
        # con un listado de procesos.
        servidor["headers"] = {"Authorization": f"Bearer {secreto}"}

    return json.dumps({"mcpServers": {NOMBRE: servidor}})
