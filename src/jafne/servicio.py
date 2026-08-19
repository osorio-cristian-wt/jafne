"""Lo común de correr un servicio HTTP de larga vida: el panel y el nodo de voz.

Hoy tiene una sola responsabilidad, y es de higiene operativa. Desde que los servicios
corren como tareas programadas (README, sección Operación) su salida va a un archivo que
nadie mira hasta que algo falla — y ahí lo único que importa es que lo que esté escrito
**signifique algo**. Un log lleno de tracebacks inofensivos es peor que uno vacío: entrena
a ignorarlo, y el día que aparezca un error de verdad va a estar sepultado entre ruido.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

#: El callback de asyncio que revienta cuando el cliente corta de golpe.
_CALLBACK_RUIDOSO = "_call_connection_lost"


def _es_corte_cosmetico(contexto: dict[str, Any]) -> bool:
    """Si esto es el `ConnectionResetError` inofensivo de asyncio en Windows.

    Pasa con el Proactor —el bucle por defecto en Windows— cuando el cliente corta la
    conexión de golpe: al cerrar el transporte, asyncio llama `shutdown()` sobre un socket
    que el otro lado ya reseteó, y el error sube al manejador del bucle. La respuesta ya
    se envió y la petición se atendió entera; es un `WinError 10054` en la limpieza.

    Un navegador que cambia de página o un teléfono que bloquea la pantalla lo producen
    varias veces por minuto, así que en un servicio de larga vida es la mayor fuente de
    ruido del log — y no reporta nada que se pueda arreglar.
    """
    if not isinstance(contexto.get("exception"), ConnectionResetError):
        return False
    rastro = f"{contexto.get('message', '')} {contexto.get('handle', '')!r}"
    return _CALLBACK_RUIDOSO in rastro


def _manejador(bucle: asyncio.AbstractEventLoop, contexto: dict[str, Any]) -> None:
    """Descarta **solo** ese corte; todo lo demás sigue al manejador de siempre.

    Acotado a propósito: silenciar `ConnectionResetError` en general taparía cortes que sí
    importan —por ejemplo contra el nodo de voz (ADR-0037), donde perder la conexión a
    mitad de una transcripción es un hecho que hay que ver—.
    """
    if _es_corte_cosmetico(contexto):
        return
    bucle.default_exception_handler(contexto)


@asynccontextmanager
async def ciclo(app: FastAPI) -> AsyncIterator[None]:
    """Ciclo de vida del servicio: instala el manejador en el bucle que va a correr.

    Se hace acá y no al arrancar el proceso porque el bucle lo crea uvicorn: recién existe
    cuando la aplicación ya está levantando.
    """
    asyncio.get_running_loop().set_exception_handler(_manejador)
    yield
