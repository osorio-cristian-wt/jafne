"""Control de acceso de los servicios HTTP de JAFNE (ADR-0020).

Dos reglas, y son las mismas para todo lo que JAFNE expone por red: **nunca todas las
interfaces**, y **nunca fuera de loopback sin token**. ADR-0020 las escribió para el panel,
que opera JAFNE y por eso no puede publicarse sin control de acceso; ADR-0037 sumó un
segundo servicio —el nodo de voz— que cruza la malla ZeroTier con audio del Usuario, y le
aplican igual.

Vive acá y no en `panel/` porque duplicar código de autenticación es la forma más común de
que dos servicios terminen con reglas distintas: uno se arregla, el otro no. Cada servicio
pone su mensaje y su variable de entorno; la comprobación es una sola.
"""

from __future__ import annotations

import ipaddress
import os
import secrets
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

#: Dónde queda el token cuando llegó por query, para que el navegador no lo arrastre en
#: cada URL —ni lo deje en el historial más de una vez—.
COOKIE_TOKEN = "jafne_token"


class ConfiguracionInsegura(ValueError):
    """Se pidió levantar un servicio de una forma que ADR-0020 prohíbe."""


def es_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def es_todas_las_interfaces(host: str) -> bool:
    return host.strip() in {"", "0.0.0.0", "::", "*"}


def resolver_token(token: str | None, variable: str) -> str | None:
    """El token explícito, o el del entorno, o nada."""
    return token or os.environ.get(variable) or None


def validar_bind(host: str, token: str | None, *, servicio: str, variable: str) -> None:
    """Hace cumplir ADR-0020 **antes** de abrir el socket.

    Falla ruidosamente a propósito: la alternativa es arrancar inseguro sin que nadie se
    entere, que es peor que no arrancar.
    """
    if es_todas_las_interfaces(host):
        raise ConfiguracionInsegura(
            f"{servicio} no escucha en '{host}': ADR-0020 prohíbe bindear todas las "
            f"interfaces. Usá loopback (127.0.0.1) o la IP de la interfaz ZeroTier."
        )
    if not es_loopback(host) and not token:
        raise ConfiguracionInsegura(
            f"Escuchar en '{host}' exige el token compartido de ADR-0020. Definí "
            f"${variable} o pasá --token."
        )


def montar_token(app: FastAPI, *, detalle: str) -> None:
    """Registra el middleware que exige el token guardado en `app.state.token`.

    Con `app.state.token` en `None` no se pide nada, que es lo correcto **solo** en
    loopback: quien hace cumplir esa condición es `validar_bind`, antes de escuchar.
    """

    @app.middleware("http")
    async def _token(request: Request, siguiente: Any):
        esperado = request.app.state.token
        if not esperado:
            return await siguiente(request)

        cabecera = request.headers.get("authorization", "")
        recibido = (
            cabecera[7:]
            if cabecera.lower().startswith("bearer ")
            else request.headers.get("x-jafne-token")
            or request.query_params.get("token")
            or request.cookies.get(COOKIE_TOKEN)
            or ""
        )
        if not secrets.compare_digest(recibido, esperado):
            return JSONResponse(
                status_code=401,
                content={"error": "token_invalido", "detalle": detalle},
            )

        respuesta = await siguiente(request)
        if request.query_params.get("token"):
            respuesta.set_cookie(
                COOKIE_TOKEN, esperado, httponly=True, samesite="strict"
            )
        return respuesta
