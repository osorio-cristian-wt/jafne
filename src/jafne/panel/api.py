"""API del panel web (ADR-0013, ADR-0020).

El panel es el punto de entrada gráfico a JAFNE. Lo que ya está decidido —listar
proyectos, ver Asuntos, su estado y su historial, y el saldo de cada suscripción— se sirve
de verdad, leyendo `~/.jafne/` (ADR-0007/ADR-0008/ADR-0025). Lo que depende de una decisión
abierta —el chat con el Asistente o el Encargado— existe como endpoint pero responde **501**
citando qué lo bloquea, en vez de devolver datos inventados.

El saldo es el caso intermedio: el dato se sirve, pero **cómo** se observa sigue abierto,
así que la respuesta lleva ese pendiente adjunto en vez de aparentar una medición
automática que no existe.

El estado es de **solo lectura** desde acá: lo escriben el Encargado y el Workspace
Broker (ADR-0008), no la UI.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .. import __version__
from ..acceso import COOKIE_TOKEN, ConfiguracionInsegura, aviso_sin_tls, es_loopback, montar_token
from ..acceso import es_todas_las_interfaces as _es_todas_las_interfaces
from ..acceso import resolver_tls as _resolver_tls
from ..acceso import resolver_token as _resolver_token
from ..acceso import validar_bind as _validar_bind
from ..nucleo.adaptadores import AdaptadorNoConstruido, AdaptadorNoImplementado
from ..nucleo.adaptadores import obtener as obtener_adaptador
from ..nucleo.almacen import SinCerebroParaElRol
from ..nucleo.credenciales import estado as credencial_estado
from ..nucleo.roles import DESCRIPCIONES as DESCRIPCIONES_ROL
from ..nucleo.transcripcion import AudioInvalido, TranscripcionNoDisponible
from ..nucleo.transcripcion import estado as voz_estado
from ..nucleo.transcripcion import transcribir as voz_transcribir
from ..nucleo.roles import Rol, tamano_por_defecto
from ..nucleo import (
    DESCRIPCIONES,
    DESCRIPCIONES_CONTENEDOR,
    TIMEOUT_SIN_RESPUESTA,
    TRANSICIONES,
    TRANSICIONES_CONTENEDOR,
    Almacen,
    AsuntoDesconocido,
    EstadoAsunto,
    EstadoContenedor,
    IdInvalido,
    ProyectoDesconocido,
    Suscripcion,
)
from ..pendientes import DecisionPendiente
from ..pendientes import obtener as obtener_pendiente
from ..pendientes import todos as pendientes_todos

#: Puerto por defecto del panel. Elegido libre, no es una decisión de diseño.
PUERTO_POR_DEFECTO = 8730

#: Variable de entorno con el token compartido del panel (ADR-0020).
VARIABLE_TOKEN = "JAFNE_PANEL_TOKEN"

#: Certificado y clave para servir HTTPS (ADR-0038). Sin ellos se sirve HTTP.
VARIABLE_CERT = "JAFNE_PANEL_CERT"
VARIABLE_CLAVE = "JAFNE_PANEL_CLAVE"

WEB = Path(__file__).parent / "web"


class MensajeEntrada(BaseModel):
    """Un mensaje del Usuario hacia el Asistente o un Encargado (ADR-0002)."""

    mensaje: str = Field(min_length=1)


def crear_app(ruta_almacen: Path | None = None, token: str | None = None) -> FastAPI:
    """Arma la app.

    `token` habilita la autenticación de ADR-0020. En `None` el panel no pide nada, que
    es lo correcto solo en loopback — `servir()` es quien hace cumplir esa regla.
    """
    app = FastAPI(
        title="JAFNE — panel",
        version=__version__,
        description="Dashboard visual de JAFNE (ADR-0013).",
    )
    app.state.almacen = Almacen(ruta_almacen)
    app.state.token = token

    def almacen(request: Request) -> Almacen:
        return request.app.state.almacen

    # ── autenticación (ADR-0020) ─────────────────────────────────────────────
    #
    # La comprobación es la compartida de `jafne/acceso.py`: el panel y el nodo de voz
    # (ADR-0037) exponen cosas distintas por la misma malla, y con la misma regla.

    montar_token(
        app,
        detalle=(
            "El panel escucha fuera de loopback y exige el token compartido de "
            "ADR-0020. Pasalo como ?token=…, cabecera Authorization: Bearer … o "
            "X-Jafne-Token."
        ),
    )

    # ── errores ───────────────────────────────────────────────────────────────

    @app.exception_handler(DecisionPendiente)
    async def _pendiente(request: Request, exc: DecisionPendiente) -> JSONResponse:
        return JSONResponse(
            status_code=501,
            content={
                "error": "decision_pendiente",
                "detalle": str(exc),
                "pendiente": exc.pendiente.a_dict(),
            },
        )

    @app.exception_handler(ProyectoDesconocido)
    @app.exception_handler(AsuntoDesconocido)
    async def _no_encontrado(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=404, content={"error": "no_encontrado", "detalle": str(exc)}
        )

    @app.exception_handler(AdaptadorNoConstruido)
    @app.exception_handler(AdaptadorNoImplementado)
    async def _sin_adaptador(request: Request, exc: Exception) -> JSONResponse:
        """501, pero por trabajo pendiente y no por decisión pendiente (ADR-0028)."""
        return JSONResponse(
            status_code=501,
            content={
                "error": "adaptador_no_disponible",
                "detalle": str(exc),
                "decidido": True,
            },
        )

    @app.exception_handler(IdInvalido)
    async def _id_invalido(request: Request, exc: IdInvalido) -> JSONResponse:
        return JSONResponse(
            status_code=400, content={"error": "id_invalido", "detalle": str(exc)}
        )

    @app.exception_handler(TranscripcionNoDisponible)
    async def _sin_voz(request: Request, exc: Exception) -> JSONResponse:
        """501 por instalación, no por decisión: ADR-0036 ya decidió el dictado."""
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

    # ── lo decidido: se sirve de verdad ──────────────────────────────────────

    @app.get("/api/salud")
    def salud(request: Request) -> dict[str, Any]:
        alm = almacen(request)
        return {
            "version": __version__,
            "almacen": str(alm.ruta),
            "inicializado": alm.existe,
            "protegido": bool(request.app.state.token),
            "sugerencia": None if alm.existe else "Creá el almacén con `jafne init`.",
        }

    @app.get("/api/estados")
    def estados() -> dict[str, Any]:
        """Los dos catálogos cerrados y sus transiciones (ADR-0009, ADR-0016)."""
        return {
            "asunto": {
                "catalogo": [
                    {"valor": e.value, "descripcion": DESCRIPCIONES[e]}
                    for e in EstadoAsunto
                ],
                "transiciones": {
                    e.value: sorted(d.value for d in destinos)
                    for e, destinos in TRANSICIONES.items()
                },
            },
            "contenedor": {
                "catalogo": [
                    {"valor": e.value, "descripcion": DESCRIPCIONES_CONTENEDOR[e]}
                    for e in EstadoContenedor
                ],
                "transiciones": {
                    e.value: sorted(d.value for d in destinos)
                    for e, destinos in TRANSICIONES_CONTENEDOR.items()
                },
            },
            "timeout_sin_respuesta_segundos": int(TIMEOUT_SIN_RESPUESTA.total_seconds()),
        }

    @app.get("/api/proyectos")
    def proyectos(request: Request) -> list[dict[str, Any]]:
        alm = almacen(request)
        por_proyecto: dict[str, list] = {}
        for asunto in alm.asuntos():
            por_proyecto.setdefault(asunto.proyecto, []).append(asunto)

        salida = []
        for proyecto in alm.proyectos():
            salida.append({**proyecto.a_dict(), **_resumen(por_proyecto.pop(proyecto.id, []))})
        # Un proyecto con Asuntos pero sin entrada en proyectos.yaml no se oculta:
        # el desfasaje es información, no un error a tapar.
        for proyecto_id, suyos in sorted(por_proyecto.items()):
            salida.append(
                {
                    "id": proyecto_id,
                    "nombre": proyecto_id,
                    "encargado": None,
                    "descripcion": None,
                    "sin_registrar": True,
                    **_resumen(suyos),
                }
            )
        return salida

    @app.get("/api/proyectos/{proyecto_id}")
    def proyecto(request: Request, proyecto_id: str) -> dict[str, Any]:
        alm = almacen(request)
        datos = alm.proyecto(proyecto_id)
        asuntos = alm.asuntos(proyecto_id)
        return {
            **datos.a_dict(),
            **_resumen(asuntos),
            "asuntos": [a.a_dict() for a in asuntos],
        }

    @app.get("/api/asuntos")
    def asuntos(request: Request, proyecto: str | None = None) -> list[dict[str, Any]]:
        return [a.a_dict() for a in almacen(request).asuntos(proyecto)]

    @app.get("/api/asuntos/{proyecto_id}/{asunto_id}")
    def asunto(request: Request, proyecto_id: str, asunto_id: str) -> dict[str, Any]:
        alm = almacen(request)
        datos = alm.asunto(proyecto_id, asunto_id)
        return {**datos.a_dict(), "cierre": alm.cierre(proyecto_id, asunto_id)}

    @app.get("/api/asuntos/{proyecto_id}/{asunto_id}/historial")
    def historial(
        request: Request, proyecto_id: str, asunto_id: str
    ) -> list[dict[str, Any]]:
        """La conversación del Asunto (ADR-0018), que sobrevive al contenedor."""
        alm = almacen(request)
        alm.asunto(proyecto_id, asunto_id)  # 404 si no existe
        return [m.a_dict() for m in alm.historial(proyecto_id, asunto_id)]

    @app.get("/api/cerebros")
    def cerebros(request: Request) -> list[dict[str, Any]]:
        """Los cerebros disponibles, cada uno con el saldo de su proveedor (ADR-0025)."""
        return [c.a_dict() for c in almacen(request).cerebros()]

    @app.get("/api/roles")
    def roles(request: Request) -> list[dict[str, Any]]:
        """Qué cerebro le toca a cada rol hoy (ADR-0033).

        Lo consulta el panel para mostrarlo, y **el propio agente** para saber sobre qué
        modelo está corriendo: uno que lo sabe puede calibrar cuánto abarcar y cuándo
        escalar, en vez de suponerlo.

        Se deriva al leer (ADR-0033), así que refleja `cerebros.yaml` sin copia intermedia.
        Un rol sin tamaño por defecto no es un error: su cerebro lo elige el Encargado
        tarea por tarea (ADR-0003), y eso viaja en `por_tarea`.
        """
        alm = almacen(request)
        salida: list[dict[str, Any]] = []
        for rol in Rol:
            tamano = tamano_por_defecto(rol)
            cerebro = None
            problema = None
            try:
                cerebro = alm.cerebro_de(rol)
            except SinCerebroParaElRol as error:
                problema = str(error)
            salida.append(
                {
                    "rol": rol.value,
                    "descripcion": DESCRIPCIONES_ROL[rol],
                    "tamano": tamano.value if tamano else None,
                    "por_tarea": tamano is None,
                    "cerebro": cerebro.a_dict() if cerebro else None,
                    "problema": problema,
                }
            )
        return salida

    @app.get("/api/credencial")
    def credencial() -> dict[str, Any]:
        """Con qué credencial va a hablar JAFNE con el proveedor (ADR-0034).

        JAFNE **no maneja credenciales**: la sesión es de Claude Code y JAFNE la hereda.
        Acá se mira y se reporta, nunca se lee un secreto ni se pide uno — por eso no hay
        formulario de login, y esa ausencia es del diseño.

        `verificado` viene siempre en `false` a propósito: confirmar que la sesión está
        viva exige una llamada real, y cobrarle tokens al Usuario por mirar el panel sería
        peor que no confirmarlo.
        """
        return credencial_estado().a_dict()

    @app.get("/api/uso-suscripciones")
    def uso_suscripciones(request: Request) -> dict[str, Any]:
        """Saldo de las suscripciones (ADR-0013, ADR-0025).

        Sirve lo que Infraestructura registró, y nada más: un proveedor sin saldo
        observado aparece con la lista de ventanas vacía en vez de con un número
        inventado. La medición automática sigue abierta, así que la respuesta lleva el
        pendiente adjunto — el panel lo muestra al lado del dato.
        """
        alm = almacen(request)
        observadas = alm.suscripciones()
        proveedores = sorted({c.proveedor for c in alm.cerebros()} | set(observadas))
        return {
            "metrica": "saldo",
            "suscripciones": [
                (observadas.get(p) or Suscripcion(proveedor=p)).a_dict()
                for p in proveedores
            ],
            "medicion_automatica": obtener_pendiente("medicion-de-consumo").a_dict(),
        }

    @app.get("/api/pendientes")
    def pendientes() -> list[dict[str, str]]:
        """Las decisiones abiertas que bloquean funcionalidad (ADR-0015)."""
        return [p.a_dict() for p in pendientes_todos()]

    @app.get("/api/voz")
    def voz() -> dict[str, Any]:
        """Si se puede dictar, con qué modelo y —si no— qué falta (ADR-0036).

        El panel lo consulta antes de pintar el botón: uno deshabilitado con el motivo al
        lado informa, uno que aparece y falla al apretarlo no. No carga el modelo para
        contestar.
        """
        return voz_estado().a_dict()

    @app.post("/api/transcribir")
    async def transcribir(request: Request) -> dict[str, Any]:
        """Audio a texto, local y sin persistir nada (ADR-0036).

        Recibe el audio crudo del `MediaRecorder` del navegador y devuelve el texto. **No
        escribe estado**: no toca `~/.jafne/`, no guarda el audio y no abre nada. El panel
        sigue siendo el observador de ADR-0008/ADR-0013, que es la propiedad que ADR-0035
        acaba de devolverle — esto es cómputo sobre lo que el Usuario dijo recién, y el
        resultado va al campo de texto para que lo edite o lo descarte.
        """
        audio = await request.body()
        idioma = request.query_params.get("idioma") or None
        # Fuera del bucle de eventos: transcribir bloquea segundos —o el viaje a un nodo
        # remoto (ADR-0037)—, y en el hilo del bucle dejaría al panel entero congelado
        # mientras tanto, sin poder ni servir la grilla de proyectos.
        return (await run_in_threadpool(voz_transcribir, audio, idioma)).a_dict()

    # ── decidido, todavía sin construir ──────────────────────────────────────
    #
    # Hasta ADR-0031 el chat estaba bloqueado por una **decisión**: no se sabía quién era
    # dueño del proceso del agente. Ahora se sabe —lo es JAFNE, y el panel se adjunta a
    # JAFNE, no al proveedor—, así que lo que falta es el adaptador. Sigue siendo un 501,
    # pero por otra razón, y la respuesta lo dice: no falta decidir, falta código.

    def _chat(request: Request) -> dict[str, Any]:
        cerebro = almacen(request).cerebro_de(Rol.ASISTENTE)
        obtener_adaptador(cerebro.proveedor)  # levanta: todavía no hay adaptador
        raise AssertionError("inalcanzable mientras el registro esté vacío")

    @app.post("/api/chat/asistente")
    def chat_asistente(request: Request, entrada: MensajeEntrada) -> dict[str, Any]:
        """Chat con el Asistente desde la raíz del panel (ADR-0013, ADR-0031)."""
        return _chat(request)

    @app.post("/api/proyectos/{proyecto_id}/chat")
    def chat_encargado(
        request: Request, proyecto_id: str, entrada: MensajeEntrada
    ) -> dict[str, Any]:
        """Chat con el Encargado del proyecto — el modo directo de ADR-0002."""
        almacen(request).proyecto(proyecto_id)  # 404 antes que 501 si no existe
        return _chat(request)

    if WEB.is_dir():
        app.mount("/", StaticFiles(directory=WEB, html=True), name="web")

    return app


def _resumen(asuntos: list) -> dict[str, Any]:
    """Cuántos Asuntos hay por estado efectivo, para la tarjeta del proyecto."""
    conteo = Counter(a.estado_efectivo.value for a in asuntos)
    return {
        "total_asuntos": len(asuntos),
        "asuntos_abiertos": sum(1 for a in asuntos if a.abierto),
        "por_estado": {e.value: conteo.get(e.value, 0) for e in EstadoAsunto},
    }


def resolver_token(token: str | None = None) -> str | None:
    return _resolver_token(token, VARIABLE_TOKEN)


def validar_bind(host: str, token: str | None) -> None:
    """ADR-0020 para el panel: nunca todas las interfaces, nunca expuesto sin token.

    El panel **opera** JAFNE (ADR-0013), así que publicarlo sin control de acceso es
    publicar una consola de control.
    """
    _validar_bind(host, token, servicio="El panel", variable=VARIABLE_TOKEN)


def resolver_tls(cert: str | None = None, clave: str | None = None):
    return _resolver_tls(cert, clave, VARIABLE_CERT, VARIABLE_CLAVE)


def servir(
    host: str = "127.0.0.1",
    puerto: int = PUERTO_POR_DEFECTO,
    ruta_almacen: Path | None = None,
    token: str | None = None,
    cert: str | None = None,
    clave: str | None = None,
) -> None:
    """Levanta el panel, validando el bind contra ADR-0020 y el TLS de ADR-0038."""
    token = resolver_token(token)
    validar_bind(host, token)
    tls = resolver_tls(cert, clave)

    import uvicorn

    uvicorn.run(
        crear_app(ruta_almacen, token=token),
        host=host,
        port=puerto,
        ssl_certfile=str(tls[0]) if tls else None,
        ssl_keyfile=str(tls[1]) if tls else None,
    )
