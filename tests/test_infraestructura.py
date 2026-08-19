"""Infraestructura y su servidor MCP (ADR-0042).

Lo que se verifica acá es el **alcance por rol** y el protocolo. El alcance es lo más
delicado del módulo: si un Encargado pudiera ver o tocar proyectos ajenos, la jerarquía de
ADR-0002 dejaría de existir aunque el diagrama siga dibujado.
"""

import pytest
from fastapi.testclient import TestClient

from jafne.infraestructura import crear_app
from jafne.nucleo.workspaces import Broker
from test_workspaces import MotorFalso


@pytest.fixture
def infra(almacen) -> TestClient:
    from jafne.nucleo import Almacen

    return TestClient(
        crear_app(almacen=Almacen(almacen.ruta), broker=Broker(MotorFalso()))
    )


def _llamar(cliente: TestClient, url: str, metodo: str, parametros=None, ident=1):
    cuerpo = {"jsonrpc": "2.0", "id": ident, "method": metodo}
    if parametros is not None:
        cuerpo["params"] = parametros
    return cliente.post(url, json=cuerpo).json()


def _herramienta(cliente: TestClient, url: str, nombre: str, argumentos=None):
    import json

    respuesta = _llamar(
        cliente, url, "tools/call", {"name": nombre, "arguments": argumentos or {}}
    )
    contenido = respuesta["result"]["content"][0]["text"]
    try:
        return json.loads(contenido), respuesta["result"].get("isError", False)
    except json.JSONDecodeError:
        return contenido, respuesta["result"].get("isError", False)


ASISTENTE = "/mcp/asistente"
ENCARGADO = "/mcp/proyecto/borr"


# ── el protocolo ─────────────────────────────────────────────────────────────


def test_el_handshake_devuelve_la_version_que_el_cliente_pidio(infra):
    resultado = _llamar(infra, ASISTENTE, "initialize", {"protocolVersion": "2025-06-18"})
    assert resultado["result"]["protocolVersion"] == "2025-06-18"
    assert "tools" in resultado["result"]["capabilities"]


def test_una_notificacion_no_se_contesta(infra):
    # Sin `id` es una notificación: contestarla es un error de protocolo, no cortesía.
    respuesta = infra.post(ASISTENTE, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert respuesta.status_code == 202


def test_un_metodo_que_no_existe_se_dice_con_codigo_de_json_rpc(infra):
    resultado = _llamar(infra, ASISTENTE, "metodo/inventado")
    assert resultado["error"]["code"] == -32601


def test_un_cuerpo_que_no_es_json_no_tumba_el_servicio(infra):
    respuesta = infra.post(ASISTENTE, content=b"no soy json")
    assert respuesta.json()["error"]["code"] == -32700


def test_un_fallo_de_herramienta_vuelve_como_resultado_y_no_como_error_rpc(infra):
    """El agente tiene que poder **leer** qué salió mal y decidir.

    Un error de JSON-RPC lo dejaría sin texto que interpretar, y la CLI lo trataría como
    protocolo roto en vez de como una respuesta.
    """
    _, hubo_error = _herramienta(infra, ASISTENTE, "asunto_ver", {"proyecto": "borr", "asunto": "no-existe"})
    assert hubo_error is True


# ── el alcance por rol, que es lo que sostiene la jerarquía ──────────────────


def test_el_asistente_ve_todos_los_proyectos(infra):
    proyectos, _ = _herramienta(infra, ASISTENTE, "proyectos_listar")
    assert {p["id"] for p in proyectos} == {"borr", "casa-justina"}


def test_el_encargado_ve_solo_el_suyo(infra):
    proyectos, _ = _herramienta(infra, ENCARGADO, "proyectos_listar")
    assert [p["id"] for p in proyectos] == ["borr"]


def test_el_encargado_no_ve_asuntos_de_otro_proyecto(infra):
    asuntos, _ = _herramienta(infra, ENCARGADO, "asuntos_listar")
    assert {a["proyecto"] for a in asuntos} == {"borr"}


def test_el_encargado_no_puede_pedir_otro_proyecto_por_argumento(infra):
    """El alcance lo fija la URL con la que JAFNE lo lanzó, no lo que el agente mande.

    Si el argumento ganara, acotar al Encargado sería una sugerencia y no un límite: le
    alcanzaría con nombrar otro proyecto para salirse del suyo.
    """
    asuntos, _ = _herramienta(infra, ENCARGADO, "asuntos_listar", {"proyecto": "casa-justina"})
    assert {a["proyecto"] for a in asuntos} == {"borr"}


def test_el_encargado_no_puede_abrir_un_asunto_en_otro_proyecto(infra, almacen):
    _herramienta(
        infra, ENCARGADO, "asunto_abrir",
        {"proyecto": "casa-justina", "asunto": "colado", "titulo": "no debería"},
    )
    assert [a.proyecto for a in almacen.asuntos()].count("casa-justina") == 0


def test_al_encargado_ni_se_le_listan_las_herramientas_con_proyecto(infra):
    # Una herramienta listada es una promesa: no alcanza con que falle si la llama.
    herramientas = _llamar(infra, ENCARGADO, "tools/list")["result"]["tools"]
    abrir = next(h for h in herramientas if h["name"] == "asunto_abrir")
    assert "proyecto" not in abrir["inputSchema"]["properties"]


def test_al_asistente_si_se_le_pide_el_proyecto(infra):
    herramientas = _llamar(infra, ASISTENTE, "tools/list")["result"]["tools"]
    abrir = next(h for h in herramientas if h["name"] == "asunto_abrir")
    assert "proyecto" in abrir["inputSchema"]["properties"]


def test_un_encargado_de_un_proyecto_inexistente_es_404(infra):
    assert infra.post("/mcp/proyecto/fantasma", json={"jsonrpc": "2.0", "id": 1, "method": "ping"}).status_code == 404


# ── delegar es abrir un Asunto (ADR-0006, ADR-0044) ─────────────────────────


def test_el_asistente_puede_abrir_un_asunto(infra, almacen):
    resultado, hubo_error = _herramienta(
        infra, ASISTENTE, "asunto_abrir",
        {"proyecto": "borr", "asunto": "nueva-func", "titulo": "Una funcionalidad"},
    )
    assert hubo_error is False
    assert resultado["abierto"]["id"] == "nueva-func"
    assert almacen.asunto("borr", "nueva-func").titulo == "Una funcionalidad"


# ── el saldo, con su pendiente pegado (ADR-0025) ─────────────────────────────


def test_el_saldo_viene_con_el_aviso_de_que_se_carga_a_mano(infra):
    # Servir el número solo haría creer que hay una medición automática que no existe.
    saldo, _ = _herramienta(infra, ASISTENTE, "saldo_ver")
    assert "aviso" in saldo
    assert "mano" in saldo["aviso"] or "medir" in saldo["aviso"]


# ── el motor, visto desde afuera ─────────────────────────────────────────────


def test_el_estado_del_motor_se_sirve_por_http(infra):
    datos = infra.get("/api/infraestructura").json()
    assert "runtimes" in datos


def test_el_estado_del_motor_tambien_esta_en_el_mcp(infra):
    estado, _ = _herramienta(infra, ASISTENTE, "infraestructura_estado")
    assert "runtimes" in estado


# ── mirar adentro de un Workspace (ADR-0041, ADR-0042) ───────────────────────


def test_el_registro_de_un_workspace_se_sirve_por_http(almacen):
    # Con `krun` no hay `exec`: leer el registro es el único camino para saber qué pasó
    # adentro, así que tiene que estar expuesto o el Workspace es una caja negra.
    from jafne.nucleo import Almacen

    infra = TestClient(
        crear_app(
            almacen=Almacen(almacen.ruta),
            broker=Broker(MotorFalso(vivos=("jafne-borr-uno",))),
        )
    )
    cuerpo = infra.get("/api/workspaces/jafne-borr-uno/registro").json()
    assert cuerpo["existe"] is True
    assert "lo que escribió la tarea" in cuerpo["registro"]


def test_pedir_el_registro_de_un_workspace_que_no_existe_lo_dice(infra):
    # Un 200 con `registro` vacío se leería como "corrió y no escribió nada", que es
    # justamente el diagnóstico equivocado. Se distingue con `existe`.
    cuerpo = infra.get("/api/workspaces/jafne-no-existe/registro").json()
    assert cuerpo["existe"] is False
    assert "No hay ningún Workspace" in cuerpo["detalle"]


# ── el disparador de la delegación (ADR-0047) ────────────────────────────────


def test_delegar_un_agente_fuera_de_la_raiz_de_trabajo_se_rechaza(infra):
    # El borde de ADR-0039 vale también para lo que se monta adentro de un contenedor: sin
    # esto, un `repo` con `..` montaría cualquier carpeta del disco.
    respuesta = infra.post(
        "/api/workspaces",
        json={"proyecto": "borr", "asunto": "rediseno-panel", "repo": "../../fuera"},
    )
    assert respuesta.status_code == 400
    assert "ADR-0039" in respuesta.json()["detalle"]


def test_el_encargado_ve_la_herramienta_para_delegar(infra):
    # Es el disparador de ADR-0047, y le toca al Encargado: es quien delega (ADR-0044).
    nombres = [h["name"] for h in _llamar(infra, ENCARGADO, "tools/list")["result"]["tools"]]
    assert "agente_delegar" in nombres


def test_al_encargado_no_se_le_pide_el_proyecto_para_delegar(infra):
    # Su alcance lo fija la URL con la que JAFNE lo lanzó, no lo que él mande (ADR-0042).
    (delegar,) = [
        h
        for h in _llamar(infra, ENCARGADO, "tools/list")["result"]["tools"]
        if h["name"] == "agente_delegar"
    ]
    assert "proyecto" not in delegar["inputSchema"]["properties"]
