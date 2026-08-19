"""Infraestructura: el proceso que sostiene lo que sobrevive a un turno (ADR-0042).

Es el cuarto servicio de JAFNE, después del panel, el reloj y el nodo de voz, y el primero
que existe porque el diseño lo pedía desde el principio: `arquitectura.md` tiene un **plano
de infraestructura** con un Infrastructure Manager y un Workspace Broker adentro desde el
día uno, y ADR-0025 le encargó el saldo llamándola *"la única con vista de todos los
agentes"*. Hasta hoy no tenía proceso, así que nada de eso podía pasar.

Tiene tres responsabilidades, y las tres son cosas que **ningún proceso efímero puede
tener**:

1. **Los Workspaces** (ADR-0012, ADR-0045, ADR-0047). Un contenedor por repositorio, que
   vive más que el turno que lo pidió, así que alguien tiene que ser su dueño.
2. **El saldo** (ADR-0025). Es una vista global de todos los agentes; se lleva en un solo
   lugar o no se lleva.
3. **El servidor MCP** (ADR-0004, ADR-0014, ADR-0042), que es cómo el Asistente y los
   Encargados ven todo lo anterior sin que JAFNE se lo tenga que inyectar en cada turno.

**El alcance viaja en la URL, no en lo que el agente dice de sí mismo.** El Asistente habla
por `/mcp/asistente` y ve todos los proyectos; un Encargado habla por
`/mcp/proyecto/<id>` y ve el suyo. Es a propósito: si el rol fuera un campo que el agente
manda, un Encargado podría declararse Asistente y la jerarquía de ADR-0002 se caería con
una línea de texto. Quien arma esa URL es JAFNE, al lanzar al agente.

Le aplica ADR-0020 completo por `jafne/acceso.py`: nunca todas las interfaces, y fuera de
loopback exige token. Acá pesa más que en el panel — este servicio **crea máquinas** y
escribe estado.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__
from .acceso import ConfiguracionInsegura  # noqa: F401  (se re-exporta para la CLI)
from .acceso import montar_token
from .acceso import resolver_tls as _resolver_tls
from .acceso import resolver_token as _resolver_token
from .acceso import validar_bind as _validar_bind
from .nucleo import Almacen, AsuntoDesconocido, ProyectoDesconocido
from .nucleo import mcp
from .nucleo.motor import Motor, MotorNoDisponible
from .nucleo.workspaces import (
    DOCKERFILE_DEV,
    IMAGEN_POR_DEFECTO,
    Broker,
    Pedido,
    PedidoInvalido,
    Workspace,
    WorkspaceRechazado,
)
from .pendientes import obtener as obtener_pendiente
from .servicio import ciclo

#: El puerto, el token y dónde encontrarla salen de `nucleo/mcp.py`, que es el lado cliente
#: de lo mismo. Una segunda copia acá se desincronizaría el día que alguna cambie.
PUERTO_POR_DEFECTO = mcp.PUERTO_POR_DEFECTO

#: Token compartido de Infraestructura (ADR-0020). Propio y no el del panel: son dos
#: servicios con poderes distintos, y un solo token los haría equivalentes.
VARIABLE_TOKEN = mcp.VARIABLE_TOKEN

#: Dónde encontrar a Infraestructura desde otro proceso (el panel, la CLI).
VARIABLE_NODO = mcp.VARIABLE_NODO

VARIABLE_CERT = "JAFNE_INFRA_CERT"
VARIABLE_CLAVE = "JAFNE_INFRA_CLAVE"

#: La versión del protocolo MCP que se habla. Se responde la que el cliente pide si la
#: conocemos, y esta si no.
VERSION_MCP = "2025-06-18"


def crear_app(
    token: str | None = None,
    almacen: Almacen | None = None,
    broker: Broker | None = None,
) -> FastAPI:
    """Arma el servicio: estado, saldo, Workspaces y el MCP por rol."""
    app = FastAPI(
        title="JAFNE — Infraestructura",
        version=__version__,
        description="Workspaces, saldo y servidor MCP (ADR-0042).",
        lifespan=ciclo,
    )
    app.state.token = token
    app.state.almacen = almacen or Almacen()
    app.state.broker = broker or Broker(Motor())

    montar_token(
        app,
        detalle=(
            "Infraestructura crea Workspaces y escribe el saldo, así que fuera de loopback "
            f"exige el token de ADR-0020. Definí ${VARIABLE_TOKEN} con el mismo valor con "
            "el que arrancó el servicio."
        ),
    )

    @app.exception_handler(MotorNoDisponible)
    async def _sin_motor(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": "motor_no_disponible", "detalle": str(exc)},
        )

    @app.exception_handler(PedidoInvalido)
    async def _pedido_invalido(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "pedido_invalido", "detalle": str(exc)},
        )

    @app.exception_handler(WorkspaceRechazado)
    async def _rechazado(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"error": "workspace_rechazado", "detalle": str(exc)},
        )

    @app.exception_handler(ProyectoDesconocido)
    async def _sin_proyecto(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": "proyecto_desconocido", "detalle": str(exc)})

    @app.exception_handler(AsuntoDesconocido)
    async def _sin_asunto(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": "asunto_desconocido", "detalle": str(exc)})

    # ── HTTP: lo que un humano o el panel quieren mirar ───────────────────────

    @app.get("/api/infraestructura")
    def estado(request: Request) -> dict[str, Any]:
        """Qué motor hay, si está encendido y qué runtimes tiene (informativo, ADR-0045)."""
        return request.app.state.broker.estado()

    @app.get("/api/workspaces")
    def workspaces(request: Request) -> dict[str, Any]:
        return {"vivos": request.app.state.broker.vivos()}

    @app.get("/api/workspaces/{nombre}/registro")
    def registro(request: Request, nombre: str) -> dict[str, Any]:
        """Lo que el Workspace escribió.

        Es la salida del proceso principal del contenedor. Vive acá y no en el panel
        porque la dueña de los Workspaces es Infraestructura (ADR-0042), y porque nadie
        más habla con el motor (ADR-0012).
        """
        broker = request.app.state.broker
        if nombre not in broker.vivos():
            return {"nombre": nombre, "existe": False, "registro": "", "detalle": (
                f"No hay ningún Workspace llamado '{nombre}'. Los que hay: "
                f"{', '.join(broker.vivos()) or 'ninguno'}."
            )}
        return {
            "nombre": nombre,
            "existe": True,
            "registro": broker.registro(nombre),
            "detalle": None,
        }

    @app.post("/api/workspaces")
    async def delegar_agente(request: Request) -> dict[str, Any]:
        """Le da a un Agente su contenedor (ADR-0047). El mismo disparador que el MCP."""
        cuerpo = await request.json()
        workspace = _delegar(
            request.app.state.broker,
            str(cuerpo.get("proyecto") or ""),
            str(cuerpo.get("asunto") or ""),
            str(cuerpo.get("repo") or ""),
        )
        return workspace.a_dict()

    @app.get("/api/saldo")
    def saldo(request: Request) -> dict[str, Any]:
        """El saldo observado. Leer es inofensivo y no necesita pasar por acá; se sirve
        igual para que quien ya habla con Infraestructura no tenga que abrir el archivo."""
        return {
            proveedor: suscripcion.a_dict()
            for proveedor, suscripcion in request.app.state.almacen.suscripciones().items()
        }

    @app.post("/api/saldo")
    async def registrar(request: Request) -> dict[str, Any]:
        """**El** escritor del saldo (ADR-0025, ADR-0042).

        ADR-0025 dijo que la cuenta la lleva Infraestructura por ser "la única con vista de
        todos los agentes". Mientras no tuvo proceso, `jafne saldo` escribía el archivo
        directo y esa frase no se cumplía. Ahora la CLI es cliente de esto.
        """
        cuerpo = await request.json()
        from .nucleo.modelos import a_utc

        suscripcion = request.app.state.almacen.registrar_saldo(
            str(cuerpo.get("proveedor") or ""),
            str(cuerpo.get("ventana") or ""),
            cuerpo.get("restante"),
            resetea=a_utc(cuerpo.get("resetea")) if cuerpo.get("resetea") else None,
            plan=cuerpo.get("plan"),
            fuente=cuerpo.get("fuente"),
        )
        return suscripcion.a_dict()

    # ── MCP (ADR-0042) ────────────────────────────────────────────────────────

    @app.post("/mcp/asistente")
    async def mcp_asistente(request: Request) -> JSONResponse:
        """El Asistente ve todos los proyectos: es quien enruta (ADR-0002)."""
        return await _responder_mcp(request, proyecto=None)

    @app.post("/mcp/proyecto/{proyecto_id}")
    async def mcp_encargado(request: Request, proyecto_id: str) -> JSONResponse:
        """Un Encargado ve **solo su proyecto**.

        El 404 se comprueba acá y no adentro de cada herramienta: un Encargado apuntado a
        un proyecto que no existe es un error de quien armó la URL, no del turno.
        """
        request.app.state.almacen.proyecto(proyecto_id)
        return await _responder_mcp(request, proyecto=proyecto_id)

    return app


# ── el protocolo ─────────────────────────────────────────────────────────────
#
# MCP es JSON-RPC 2.0 sobre un solo endpoint. Se implementa a mano, sin SDK, por la misma
# razón que el panel no tiene build (ADR-0015): son cuatro métodos y un puñado de formas de
# mensaje, y una dependencia más es una dependencia más que mantener. Si el protocolo
# crece, esta decisión merece revisarse.


async def _responder_mcp(request: Request, proyecto: str | None) -> JSONResponse:
    try:
        cuerpo = await request.json()
    except (ValueError, TypeError):
        return _error_rpc(None, -32700, "El cuerpo no es JSON.")

    # Un lote (lista) o un mensaje suelto. Las notificaciones no llevan `id` y no se
    # contestan: contestar una notificación es un error de protocolo, no una cortesía.
    mensajes = cuerpo if isinstance(cuerpo, list) else [cuerpo]
    respuestas = []
    for mensaje in mensajes:
        if not isinstance(mensaje, dict):
            respuestas.append(_cuerpo_error(None, -32600, "Mensaje inválido."))
            continue
        respuesta = _despachar(request, mensaje, proyecto)
        if respuesta is not None:
            respuestas.append(respuesta)

    if not respuestas:
        # Solo había notificaciones: 202 sin cuerpo es lo que pide el transporte.
        return JSONResponse(status_code=202, content=None)
    return JSONResponse(content=respuestas if isinstance(cuerpo, list) else respuestas[0])


def _despachar(request: Request, mensaje: dict, proyecto: str | None) -> dict | None:
    metodo = mensaje.get("method")
    identificador = mensaje.get("id")
    parametros = mensaje.get("params") or {}

    if identificador is None:
        return None  # notificación: se acepta y no se contesta

    if metodo == "initialize":
        pedida = str(parametros.get("protocolVersion") or "")
        return _cuerpo_ok(
            identificador,
            {
                "protocolVersion": pedida or VERSION_MCP,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "jafne-infraestructura", "version": __version__},
                "instructions": _instrucciones(proyecto),
            },
        )

    if metodo == "ping":
        return _cuerpo_ok(identificador, {})

    if metodo == "tools/list":
        return _cuerpo_ok(identificador, {"tools": _herramientas(proyecto)})

    if metodo == "tools/call":
        nombre = parametros.get("name")
        argumentos = parametros.get("arguments") or {}
        try:
            texto = _invocar(request, nombre, argumentos, proyecto)
        except _HerramientaDesconocida as error:
            return _cuerpo_error(identificador, -32601, str(error))
        except Exception as error:  # noqa: BLE001
            # Un fallo de herramienta se devuelve **como resultado con isError**, no como
            # error de JSON-RPC: el agente tiene que poder leerlo y decidir qué hacer, y un
            # error de protocolo lo dejaría sin texto que interpretar.
            return _cuerpo_ok(
                identificador,
                {"content": [{"type": "text", "text": str(error)}], "isError": True},
            )
        return _cuerpo_ok(
            identificador, {"content": [{"type": "text", "text": texto}], "isError": False}
        )

    return _cuerpo_error(identificador, -32601, f"Método desconocido: {metodo}")


def _instrucciones(proyecto: str | None) -> str:
    if proyecto:
        return (
            f"Sos el Encargado del proyecto '{proyecto}'. Estas herramientas te muestran "
            f"**solo** ese proyecto: es el alcance de tu rol (ADR-0002), no una falla."
        )
    return (
        "Sos el Asistente de JAFNE. Estas herramientas te dan el estado de todos los "
        "proyectos, sus Asuntos y el saldo, y te dejan abrir un Asunto para delegar."
    )


class _HerramientaDesconocida(LookupError):
    pass


def _herramientas(proyecto: str | None) -> list[dict]:
    """El catálogo, ya acotado por rol.

    Un Encargado no *ve* las herramientas de todos los proyectos: no alcanza con que fallen
    si las llama. Una herramienta listada es una promesa.
    """
    de_proyecto = {"type": "string", "description": "Id del proyecto."}
    proyectos_listar = {
        "name": "proyectos_listar",
        "description": (
            "Los proyectos que JAFNE conoce, con su resumen de Asuntos."
            if not proyecto
            else f"El proyecto '{proyecto}', con su resumen de Asuntos."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    }
    asuntos_listar = {
        "name": "asuntos_listar",
        "description": "Los Asuntos y su estado. La unidad de trabajo de JAFNE (ADR-0006).",
        "inputSchema": {
            "type": "object",
            "properties": {} if proyecto else {"proyecto": de_proyecto},
        },
    }
    asunto_ver = {
        "name": "asunto_ver",
        "description": "El detalle de un Asunto: estado, contenedor e historial.",
        "inputSchema": {
            "type": "object",
            "properties": (
                {"asunto": {"type": "string", "description": "Id del Asunto."}}
                if proyecto
                else {
                    "proyecto": de_proyecto,
                    "asunto": {"type": "string", "description": "Id del Asunto."},
                }
            ),
            "required": ["asunto"],
        },
    }
    asunto_abrir = {
        "name": "asunto_abrir",
        "description": (
            "Abre un Asunto nuevo. Es cómo se delega trabajo (ADR-0006): crea la unidad "
            "con su estado, su historial y su cierre."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                **({} if proyecto else {"proyecto": de_proyecto}),
                "asunto": {"type": "string", "description": "Id corto y estable."},
                "titulo": {"type": "string", "description": "Qué hay que hacer."},
                "rama": {"type": "string", "description": "Rama de trabajo, si ya se sabe."},
            },
            "required": ["asunto", "titulo"],
        },
    }
    saldo_ver = {
        "name": "saldo_ver",
        "description": (
            "El saldo observado por proveedor (ADR-0025). Viene con la aclaración de que "
            "hoy se carga a mano: medirlo solo sigue sin decidirse."
        ),
        "inputSchema": {"type": "object", "properties": {}},
    }
    infraestructura_estado = {
        "name": "infraestructura_estado",
        "description": "Qué motor de contenedores hay y qué runtimes tiene la máquina.",
        "inputSchema": {"type": "object", "properties": {}},
    }
    agente_delegar = {
        "name": "agente_delegar",
        "description": (
            "Delega un Agente de código a un repo: le construye su contenedor desde el "
            "`Dockerfile.dev` del repo y lo deja en pie (ADR-0047, ADR-0048). Es el "
            "disparador — un Agente sin contenedor no tiene dónde trabajar."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                **({} if proyecto else {"proyecto": de_proyecto}),
                "asunto": {"type": "string", "description": "Id del Asunto que delega."},
                "repo": {
                    "type": "string",
                    "description": "Nombre del repo, tal como se llama su carpeta.",
                },
            },
            "required": ["asunto", "repo"],
        },
    }
    return [
        proyectos_listar,
        asuntos_listar,
        asunto_ver,
        asunto_abrir,
        agente_delegar,
        saldo_ver,
        infraestructura_estado,
    ]


def _invocar(request: Request, nombre: str, argumentos: dict, proyecto: str | None) -> str:
    almacen: Almacen = request.app.state.almacen
    broker: Broker = request.app.state.broker

    def el_proyecto(clave: str = "proyecto") -> str:
        """El proyecto sobre el que se opera, respetando el alcance del rol.

        Con un Encargado el argumento se **ignora**: su alcance lo fija la URL con la que
        JAFNE lo lanzó, no lo que él mande. Si pudiera elegirlo, el acotamiento sería una
        sugerencia.
        """
        if proyecto:
            return proyecto
        pedido = argumentos.get(clave)
        if not pedido:
            raise ValueError(f"Falta '{clave}': el Asistente ve todos, así que hay que decir cuál.")
        return str(pedido)

    if nombre == "proyectos_listar":
        todos = almacen.proyectos()
        if proyecto:
            todos = [p for p in todos if p.id == proyecto]
        return _texto(
            [
                {"id": p.id, "encargado": p.encargado, "asuntos": len(almacen.asuntos(p.id))}
                for p in todos
            ]
        )

    if nombre == "asuntos_listar":
        cual = proyecto or argumentos.get("proyecto") or None
        return _texto(
            [
                {
                    "proyecto": a.proyecto,
                    "id": a.id,
                    "titulo": a.titulo,
                    "estado": a.estado_efectivo.value,
                    "abierto": a.abierto,
                }
                for a in almacen.asuntos(cual)
            ]
        )

    if nombre == "asunto_ver":
        cual = el_proyecto()
        asunto = almacen.asunto(cual, str(argumentos.get("asunto") or ""))
        historial = almacen.historial(cual, asunto.id)
        return _texto(
            {
                "proyecto": asunto.proyecto,
                "id": asunto.id,
                "titulo": asunto.titulo,
                "estado": asunto.estado_efectivo.value,
                "contenedor": asunto.estado_contenedor.value if asunto.estado_contenedor else None,
                "historial": [{"rol": m.rol, "texto": m.texto} for m in historial],
            }
        )

    if nombre == "asunto_abrir":
        cual = el_proyecto()
        asunto = almacen.abrir_asunto(
            proyecto=cual,
            asunto_id=str(argumentos.get("asunto") or ""),
            titulo=str(argumentos.get("titulo") or ""),
            rama=argumentos.get("rama") or None,
        )
        return _texto({"abierto": {"proyecto": asunto.proyecto, "id": asunto.id, "titulo": asunto.titulo}})

    if nombre == "agente_delegar":
        cual = el_proyecto()
        asunto_id = str(argumentos.get("asunto") or "")
        repo = str(argumentos.get("repo") or "")
        almacen.asunto(cual, asunto_id)  # 404 si el Asunto no existe
        workspace = _delegar(broker, cual, asunto_id, repo)
        return _texto(
            {
                "delegado": workspace.a_dict(),
                "aviso": (
                    None
                    if workspace.imagen != IMAGEN_POR_DEFECTO
                    else (
                        f"El repo '{repo}' no declara `{DOCKERFILE_DEV}`, así que su Agente "
                        f"corre en la imagen por defecto, que no trae ni git ni runtime. "
                        f"Te toca sembrarle el entorno y sus skills (ADR-0049)."
                    )
                ),
            }
        )

    if nombre == "saldo_ver":
        pendiente = obtener_pendiente("medicion-de-consumo")
        return _texto(
            {
                "suscripciones": {
                    proveedor: {
                        v.nombre: v.restante for v in suscripcion.ventanas
                    }
                    for proveedor, suscripcion in almacen.suscripciones().items()
                },
                "aviso": pendiente.pregunta,
            }
        )

    if nombre == "infraestructura_estado":
        return _texto(broker.estado())

    raise _HerramientaDesconocida(f"No existe la herramienta '{nombre}'.")


def _delegar(broker: Broker, proyecto: str, asunto: str, repo: str) -> Workspace:
    """Le da a un Agente su contenedor, resolviendo antes dónde está el repo.

    El repo se busca **dentro de la raíz de trabajo** y nunca fuera: es el borde de
    ADR-0039, y sin comprobarlo un `repo` con `..` haría montar cualquier carpeta del disco
    adentro de un contenedor.
    """
    from pathlib import Path

    from .nucleo.adaptador_anthropic import raiz_de_trabajo

    raiz = Path(raiz_de_trabajo()).resolve()
    destino = (raiz / repo).resolve()
    if raiz not in destino.parents:
        raise PedidoInvalido(
            f"El repo '{repo}' no está dentro de la raíz de trabajo ({raiz}). El borde de "
            f"ADR-0039 vale también para lo que se monta en un contenedor."
        )
    if not destino.is_dir():
        raise PedidoInvalido(
            f"No existe el repo '{repo}' en {raiz}. Un Agente necesita un repo de verdad "
            f"sobre el que trabajar (ADR-0044)."
        )
    pedido = Pedido(proyecto=proyecto, asunto=asunto, repo=repo)
    return broker.delegar(pedido, str(destino))


def _texto(valor: Any) -> str:
    import json

    return json.dumps(valor, ensure_ascii=False, indent=2, default=str)


def _cuerpo_ok(identificador: Any, resultado: dict) -> dict:
    return {"jsonrpc": "2.0", "id": identificador, "result": resultado}


def _cuerpo_error(identificador: Any, codigo: int, mensaje: str) -> dict:
    return {"jsonrpc": "2.0", "id": identificador, "error": {"code": codigo, "message": mensaje}}


def _error_rpc(identificador: Any, codigo: int, mensaje: str) -> JSONResponse:
    return JSONResponse(content=_cuerpo_error(identificador, codigo, mensaje))


# ── el cliente: cómo le habla la CLI ─────────────────────────────────────────


class InfraestructuraInalcanzable(RuntimeError):
    """No se pudo hablar con Infraestructura.

    Se levanta en vez de escribir el archivo por atrás. Que ADR-0025 le haya dado el saldo
    a Infraestructura *"por ser la única con vista de todos los agentes"* solo significa
    algo si nadie más lo escribe — un camino alternativo silencioso devuelve el problema de
    los dos escritores que esto vino a sacar.
    """


def nodo(url: str | None = None) -> str:
    """Dónde está Infraestructura. Por defecto, en esta máquina."""
    return mcp.nodo(url)


def herramientas_remotas(
    rol: Any,
    proyecto: str | None = None,
    url: str | None = None,
    token: str | None = None,
) -> list[dict]:
    """Las herramientas que **ese rol** ve por MCP, preguntadas de verdad.

    Se hace un `tools/list` real contra el punto de entrada que le tocaría al rol, en vez
    de importar el catálogo de este módulo. La diferencia importa: lo que se muestra es lo
    que el agente vería, con el acotamiento por URL ya aplicado. Un catálogo importado
    mostraría lo que *debería* ver, que es justo lo que no sirve para diagnosticar.
    """
    import json
    import os
    import urllib.error
    import urllib.request

    destino = mcp.url_para(rol, proyecto, url)
    if not destino:
        return []

    cabeceras = {"Content-Type": "application/json"}
    secreto = token or os.environ.get(VARIABLE_TOKEN)
    if secreto:
        cabeceras["Authorization"] = f"Bearer {secreto}"

    cuerpo = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode("utf-8")
    pedido = urllib.request.Request(destino, data=cuerpo, method="POST", headers=cabeceras)
    try:
        with urllib.request.urlopen(pedido, timeout=15) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", "replace")
        raise InfraestructuraInalcanzable(
            f"Infraestructura rechazó el pedido ({error.code}): {detalle}"
        ) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise InfraestructuraInalcanzable(
            f"No se pudo hablar con Infraestructura en {nodo(url)}: {error}. "
            f"Levantala con `jafne infra`, o apuntá ${VARIABLE_NODO} a donde corre."
        ) from error
    return datos.get("result", {}).get("tools", [])


def registro_remoto(
    nombre: str,
    url: str | None = None,
    token: str | None = None,
) -> dict:
    """Le pide a Infraestructura el registro de un Workspace. Es el camino del panel.

    El panel no habla con el motor —ADR-0012 dice que nadie lo hace salvo Infraestructura—
    así que pregunta por HTTP en vez de correr `podman logs` por su cuenta.
    """
    import json
    import os
    import urllib.error
    import urllib.parse
    import urllib.request

    destino = nodo(url)
    cabeceras = {}
    secreto = token or os.environ.get(VARIABLE_TOKEN)
    if secreto:
        cabeceras["Authorization"] = f"Bearer {secreto}"

    pedido = urllib.request.Request(
        f"{destino}/api/workspaces/{urllib.parse.quote(nombre)}/registro",
        method="GET",
        headers=cabeceras,
    )
    try:
        with urllib.request.urlopen(pedido, timeout=15) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", "replace")
        raise InfraestructuraInalcanzable(
            f"Infraestructura rechazó el pedido ({error.code}): {detalle}"
        ) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise InfraestructuraInalcanzable(
            f"No se pudo hablar con Infraestructura en {destino}: {error}. "
            f"Levantala con `jafne infra`, o apuntá ${VARIABLE_NODO} a donde corre. "
            f"Con `krun` no hay `exec`, así que sin ella no hay forma de ver el registro."
        ) from error


def registrar_saldo_remoto(
    proveedor: str,
    ventana: str,
    restante: float,
    resetea: Any = None,
    plan: str | None = None,
    fuente: str | None = None,
    url: str | None = None,
    token: str | None = None,
) -> dict:
    """Le pide a Infraestructura que anote el saldo. Es el camino de `jafne saldo`."""
    import json
    import os
    import urllib.error
    import urllib.request

    destino = nodo(url)
    cuerpo = json.dumps(
        {
            "proveedor": proveedor,
            "ventana": ventana,
            "restante": restante,
            "resetea": resetea.isoformat() if hasattr(resetea, "isoformat") else resetea,
            "plan": plan,
            "fuente": fuente,
        }
    ).encode("utf-8")
    cabeceras = {"Content-Type": "application/json"}
    secreto = token or os.environ.get(VARIABLE_TOKEN)
    if secreto:
        cabeceras["Authorization"] = f"Bearer {secreto}"

    pedido = urllib.request.Request(
        f"{destino}/api/saldo", data=cuerpo, method="POST", headers=cabeceras
    )
    try:
        with urllib.request.urlopen(pedido, timeout=15) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", "replace")
        raise InfraestructuraInalcanzable(
            f"Infraestructura rechazó el saldo ({error.code}): {detalle}"
        ) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise InfraestructuraInalcanzable(
            f"No se pudo hablar con Infraestructura en {destino}: {error}. "
            f"Levantala con `jafne infra`, o apuntá ${VARIABLE_NODO} a donde corre. "
            f"El saldo lo escribe ella y nadie más (ADR-0025, ADR-0042)."
        ) from error


# ── puesta en marcha ─────────────────────────────────────────────────────────


def resolver_token(token: str | None = None) -> str | None:
    return _resolver_token(token, VARIABLE_TOKEN)


def validar_bind(host: str, token: str | None) -> None:
    """ADR-0020 para Infraestructura: crea máquinas, así que nunca se expone sin token."""
    _validar_bind(host, token, servicio="Infraestructura", variable=VARIABLE_TOKEN)


def resolver_tls(cert: str | None = None, clave: str | None = None):
    return _resolver_tls(cert, clave, VARIABLE_CERT, VARIABLE_CLAVE)


def servir(
    host: str = "127.0.0.1",
    puerto: int = PUERTO_POR_DEFECTO,
    token: str | None = None,
    cert: str | None = None,
    clave: str | None = None,
) -> None:
    """Levanta Infraestructura, validando el bind contra ADR-0020 antes de abrir el socket."""
    token = resolver_token(token)
    validar_bind(host, token)
    tls = resolver_tls(cert, clave)

    import uvicorn

    uvicorn.run(
        crear_app(token=token),
        host=host,
        port=puerto,
        ssl_certfile=str(tls[0]) if tls else None,
        ssl_keyfile=str(tls[1]) if tls else None,
    )
