"""El nodo de voz: presta una GPU de la malla para transcribir (ADR-0037).

Un servicio mínimo —dos endpoints— que se levanta en la máquina que tiene la placa, y al
que el panel le delega el dictado declarando `$JAFNE_VOZ_NODO`. Corre **el mismo JAFNE**
que el panel, con el mismo `nucleo/transcripcion.py`: no hay un segundo contrato de
transcripción que mantener sincronizado, ni un servidor de terceros del que dependa el
formato de la respuesta.

Deliberadamente **no** sabe nada de Asuntos. No lee `~/.jafne/`, no tiene almacén y no
puede escribir estado ni por error: es una máquina que presta cómputo, no un segundo JAFNE.
Por eso es un proceso propio y no `jafne panel` levantado del otro lado, que arrastraría un
dashboard entero para exponer una placa de video.

Le aplica ADR-0020 completo, por el módulo compartido `jafne/acceso.py`: nunca todas las
interfaces, y fuera de loopback exige token. Acá importa más que en el panel — lo que
cruza es audio del Usuario hablando de sus proyectos.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from . import __version__
from .acceso import ConfiguracionInsegura  # noqa: F401  (se re-exporta para la CLI)
from .acceso import montar_token
from .acceso import resolver_token as _resolver_token
from .acceso import validar_bind as _validar_bind
from .nucleo.transcripcion import (
    VARIABLE_TOKEN_NODO,
    AudioInvalido,
    TranscripcionNoDisponible,
)
from .nucleo.transcripcion import estado_local as voz_estado
from .nucleo.transcripcion import transcribir_local as voz_transcribir

#: Puerto por defecto del nodo. Uno más que el panel, para poder correr los dos en la
#: misma máquina mientras se prueba. No es una decisión de diseño.
PUERTO_POR_DEFECTO = 8731


def crear_app(token: str | None = None) -> FastAPI:
    """Arma el servicio del nodo: `GET /api/voz` y `POST /api/transcribir`."""
    app = FastAPI(
        title="JAFNE — nodo de voz",
        version=__version__,
        description="Transcripción prestada a la malla (ADR-0037).",
    )
    app.state.token = token

    montar_token(
        app,
        detalle=(
            "El nodo de voz escucha fuera de loopback y exige el token compartido de "
            f"ADR-0020. Definí ${VARIABLE_TOKEN_NODO} del lado del panel con el mismo "
            "valor con el que arrancó este nodo."
        ),
    )

    @app.exception_handler(TranscripcionNoDisponible)
    async def _sin_voz(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=501,
            content={
                "error": "voz_no_disponible",
                "detalle": str(exc),
                "decidido": True,
            },
        )

    @app.exception_handler(AudioInvalido)
    async def _audio_invalido(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=400, content={"error": "audio_invalido", "detalle": str(exc)}
        )

    @app.get("/api/voz")
    def voz() -> dict[str, Any]:
        """Qué puede hacer este nodo. Lo consulta el panel antes de pintar el botón.

        Contesta por **este** proceso: usa las variantes locales de `transcripcion`, no las
        que delegan. Un nodo que delegara se reenviaría a sí mismo si alguien dejó
        `$JAFNE_VOZ_NODO` puesto en esta máquina, y el lazo no tendría fondo.
        """
        return voz_estado().a_dict()

    @app.post("/api/transcribir")
    async def transcribir(request: Request) -> dict[str, Any]:
        """Audio a texto. Nada se guarda: ni el audio, ni el texto, ni quién lo pidió."""
        audio = await request.body()
        idioma = request.query_params.get("idioma") or None
        # Transcribir bloquea varios segundos: en el hilo del bucle de eventos dejaría al
        # nodo sordo mientras trabaja, incluso para contestar `/api/voz`.
        return (await run_in_threadpool(voz_transcribir, audio, idioma)).a_dict()

    return app


def resolver_token(token: str | None = None) -> str | None:
    return _resolver_token(token, VARIABLE_TOKEN_NODO)


def validar_bind(host: str, token: str | None) -> None:
    """ADR-0020 para el nodo: sin token no se expone fuera de loopback."""
    _validar_bind(host, token, servicio="El nodo de voz", variable=VARIABLE_TOKEN_NODO)


def servir(
    host: str = "127.0.0.1",
    puerto: int = PUERTO_POR_DEFECTO,
    token: str | None = None,
) -> None:
    """Levanta el nodo, validando el bind contra ADR-0020 antes de abrir el socket."""
    token = resolver_token(token)
    validar_bind(host, token)

    import uvicorn

    uvicorn.run(crear_app(token=token), host=host, port=puerto)
