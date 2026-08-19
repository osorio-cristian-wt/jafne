"""El panel (ADR-0013): sirve lo decidido, responde 501 en lo que falta, y no se expone
sin control de acceso (ADR-0020)."""

import pytest
from fastapi.testclient import TestClient

from jafne.panel import ConfiguracionInsegura, crear_app, servir, validar_bind

TOKEN = "un-token-de-prueba"


@pytest.fixture
def cliente_protegido(almacen) -> TestClient:
    return TestClient(crear_app(almacen.ruta, token=TOKEN))


# ── lo decidido ──────────────────────────────────────────────────────────────


def test_salud_reporta_el_almacen(cliente, almacen):
    datos = cliente.get("/api/salud").json()
    assert datos["inicializado"] is True
    assert datos["almacen"] == str(almacen.ruta)
    assert datos["protegido"] is False


def test_proyectos_trae_el_resumen_por_estado(cliente):
    proyectos = cliente.get("/api/proyectos").json()
    borr = next(p for p in proyectos if p["id"] == "borr")
    assert borr["nombre"] == "BoRR Pizzería"
    assert borr["total_asuntos"] == 2
    assert borr["asuntos_abiertos"] == 2
    assert borr["por_estado"]["iniciando"] == 1


def test_un_proyecto_con_asuntos_pero_sin_registrar_no_se_oculta(cliente, almacen):
    almacen.abrir_asunto("fantasma", "algo")
    proyectos = cliente.get("/api/proyectos").json()
    assert next(p for p in proyectos if p["id"] == "fantasma")["sin_registrar"] is True


def test_detalle_de_proyecto_lista_sus_asuntos(cliente):
    datos = cliente.get("/api/proyectos/borr").json()
    assert [a["id"] for a in datos["asuntos"]] == ["migrar-bff", "rediseno-panel"]


def test_detalle_de_asunto(cliente):
    datos = cliente.get("/api/asuntos/borr/rediseno-panel").json()
    assert datos["titulo"] == "Rediseño del panel"
    assert datos["rama"] == "feature/panel"
    assert datos["estado_efectivo"] == "interactuando_con_el_usuario"
    assert datos["estado_contenedor"] is None
    assert datos["pregunta_pendiente"] is False
    assert datos["cierre"] is None


def test_el_historial_se_sirve_en_orden(cliente, almacen):
    almacen.anotar("borr", "rediseno-panel", "usuario", "hola")
    almacen.anotar("borr", "rediseno-panel", "encargado", "voy")
    historial = cliente.get("/api/asuntos/borr/rediseno-panel/historial").json()
    assert [m["rol"] for m in historial] == ["usuario", "encargado"]
    assert cliente.get("/api/asuntos/borr/inexistente/historial").status_code == 404


def test_los_dos_catalogos_se_exponen_para_la_ui(cliente):
    datos = cliente.get("/api/estados").json()
    assert len(datos["asunto"]["catalogo"]) == 5
    assert len(datos["contenedor"]["catalogo"]) == 4
    assert datos["asunto"]["transiciones"]["cerrado"] == ["iniciando"]
    assert datos["contenedor"]["transiciones"]["destruido"] == ["creando"]
    assert datos["timeout_sin_respuesta_segundos"] == 180


def test_los_cerebros_traen_el_tamano_del_catalogo_comun(cliente):
    por_id = {c["id"]: c for c in cliente.get("/api/cerebros").json()}
    assert por_id["openai-sol"]["tamano"] == "grande"
    assert por_id["claude-opus"]["tamano"] == "grande"
    assert por_id["openai-luna"]["tamano"] == "chico"


def test_la_ui_ve_que_un_cerebro_no_tiene_adaptador(cliente):
    por_id = {c["id"]: c for c in cliente.get("/api/cerebros").json()}
    # ADR-0028: se sirve igual, con el hecho a la vista.
    assert por_id["claude-opus"]["adaptador"] is True
    assert por_id["openai-sol"]["adaptador"] is False


def test_el_saldo_se_sirve_por_proveedor_con_su_medicion_pendiente(cliente, almacen):
    almacen.registrar_saldo("anthropic", "5h", 0.25, plan="max")
    datos = cliente.get("/api/uso-suscripciones").json()

    assert datos["metrica"] == "saldo"
    por_proveedor = {s["proveedor"]: s for s in datos["suscripciones"]}
    assert por_proveedor["anthropic"]["ventanas"][0]["restante"] == 0.25
    # Un proveedor declarado pero sin saldo observado aparece vacío, no inventado.
    assert por_proveedor["openai"]["ventanas"] == []
    assert por_proveedor["openai"]["observado"] is None
    # Servir el dato no tapa que medirlo solo sigue abierto.
    assert datos["medicion_automatica"]["clave"] == "medicion-de-consumo"


def test_el_saldo_llega_pegado_a_cada_cerebro_de_ese_proveedor(cliente, almacen):
    almacen.registrar_saldo("openai", "semanal", 0.6)
    por_id = {c["id"]: c for c in cliente.get("/api/cerebros").json()}
    assert por_id["openai-sol"]["saldo"]["ventanas"][0]["restante"] == 0.6
    assert por_id["openai-luna"]["saldo"]["proveedor"] == "openai"
    assert por_id["claude-opus"]["saldo"] is None


# ── errores ──────────────────────────────────────────────────────────────────


def test_lo_que_no_existe_da_404(cliente):
    assert cliente.get("/api/proyectos/inexistente").status_code == 404
    assert cliente.get("/api/asuntos/borr/inexistente").status_code == 404


def test_un_id_invalido_da_400_y_no_escapa_de_la_carpeta(cliente):
    assert cliente.get("/api/proyectos/MAYUS").status_code == 400


# ── lo no decidido ───────────────────────────────────────────────────────────


def test_el_chat_sigue_en_501_pero_ya_no_por_falta_de_decision(cliente):
    # Hasta ADR-0031 faltaba decidir quién era dueño del proceso. Ahora falta el
    # adaptador, y la respuesta distingue las dos cosas.
    respuesta = cliente.post("/api/chat/asistente", json={"mensaje": "hola"})
    assert respuesta.status_code == 501
    cuerpo = respuesta.json()
    assert cuerpo["error"] == "adaptador_no_disponible"
    assert cuerpo["decidido"] is True
    assert "pendiente" not in cuerpo


def test_el_chat_con_el_encargado_valida_el_proyecto_antes_del_501(cliente):
    assert cliente.post("/api/proyectos/inexistente/chat", json={"mensaje": "x"}).status_code == 404
    respuesta = cliente.post("/api/proyectos/borr/chat", json={"mensaje": "hola"})
    assert respuesta.status_code == 501
    assert respuesta.json()["error"] == "adaptador_no_disponible"


def test_las_decisiones_pendientes_son_consultables(cliente):
    claves = {p["clave"] for p in cliente.get("/api/pendientes").json()}
    assert {
        "medicion-de-consumo",
        "sprints",
        "workspace-broker",
    } <= claves
    # Lo que se congeló el 2026-08-11 salió del registro. `uso-suscripciones` no se
    # respondió del todo: graduó a ADR-0025 y lo que quedó abierto es el cómo, así que
    # se rebautizó `medicion-de-consumo`.
    #
    # El 2026-08-18 salieron dos más, esta vez enteras: ADR-0026 fijó el umbral de
    # conmutación y ADR-0029 decidió quién corre el reloj. Que ADR-0035 lo haya movido a
    # su propio proceso no las devuelve al registro: la pregunta seguía contestada, lo que
    # cambió fue la respuesta.
    assert claves.isdisjoint(
        {
            "auth-panel",
            "skill-de-cierre",
            "reapertura-asunto",
            "tier-openai",
            "uso-suscripciones",
            "conmutacion-por-saldo",
            "trabajo-programado",
            "chat-asistente",
            "chat-encargado",
            "adaptador-agents",
            # ADR-0038 contestó el TLS y la entrada se renombró a `rotacion-de-token`:
            # contestar la mitad y tachar el todo es como este registro deja de servir.
            "tls-y-rotacion-de-token",
        }
    )
    assert "rotacion-de-token" in claves


# ── autenticación y bind (ADR-0020) ──────────────────────────────────────────


def test_sin_token_no_se_pasa_de_la_puerta(cliente_protegido):
    assert cliente_protegido.get("/api/salud").status_code == 401
    assert cliente_protegido.get("/api/salud", params={"token": "otro"}).status_code == 401


@pytest.mark.parametrize(
    "peticion",
    [
        {"params": {"token": TOKEN}},
        {"headers": {"Authorization": f"Bearer {TOKEN}"}},
        {"headers": {"X-Jafne-Token": TOKEN}},
    ],
)
def test_el_token_se_acepta_por_query_o_cabecera(cliente_protegido, peticion):
    respuesta = cliente_protegido.get("/api/salud", **peticion)
    assert respuesta.status_code == 200
    assert respuesta.json()["protegido"] is True


def test_un_token_por_query_deja_cookie_para_las_siguientes(cliente_protegido):
    cliente_protegido.get("/api/salud", params={"token": TOKEN})
    assert cliente_protegido.get("/api/salud").status_code == 200


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "", "*"])
def test_el_panel_nunca_bindea_todas_las_interfaces(host):
    with pytest.raises(ConfiguracionInsegura):
        validar_bind(host, TOKEN)


def test_fuera_de_loopback_el_token_es_obligatorio(almacen):
    with pytest.raises(ConfiguracionInsegura):
        servir(host="10.147.20.5", ruta_almacen=almacen.ruta, token=None)
    validar_bind("10.147.20.5", TOKEN)  # con token, permitido


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_en_loopback_el_token_es_opcional(host):
    validar_bind(host, None)


def test_la_web_estatica_se_sirve_en_la_raiz(cliente):
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "JAFNE" in respuesta.text


def test_el_agente_puede_consultar_sobre_que_modelo_corre(cliente):
    """ADR-0033: lo consulta el panel para mostrarlo y el agente para saberlo."""
    por_rol = {r["rol"]: r for r in cliente.get("/api/roles").json()}

    asistente = por_rol["asistente"]
    assert asistente["tamano"] == "medio"
    assert asistente["por_tarea"] is False
    assert asistente["cerebro"]["modelo"] == "claude-sonnet-5"
    assert asistente["problema"] is None

    # Encargado y Agente no tienen default, y eso no es un error: ADR-0003 ya decidió
    # que su cerebro se elige tarea por tarea.
    assert por_rol["encargado"]["por_tarea"] is True
    assert por_rol["encargado"]["cerebro"] is None
    assert por_rol["agente"]["tamano"] is None


def test_el_panel_reporta_la_credencial_sin_pedir_ninguna(cliente):
    """ADR-0034: no hay login en el panel, y esa ausencia es del diseño."""
    datos = cliente.get("/api/credencial").json()
    assert set(datos) >= {"cli_encontrado", "listo", "avisos", "verificado"}
    # Nada que se parezca a un secreto sale por acá.
    assert "token" not in datos and "api_key" not in datos
    assert datos["verificado"] is False
