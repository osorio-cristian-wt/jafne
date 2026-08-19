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


def test_el_chat_con_el_asistente_habla_de_verdad(cliente, monkeypatch):
    """El chat dejó de ser un 501: hay adaptador (ADR-0028/0031/0034).

    El proveedor se sustituye por uno de mentira — no se gastan tokens del Usuario en la
    suite, y lo que se verifica es el cableado del panel, no que Claude sepa contestar.
    """
    from jafne.nucleo import adaptadores
    from jafne.nucleo.sesion import Evento, TipoEvento

    class AdaptadorFalso:
        proveedor = "anthropic"
        id_sesion = "sesion-de-prueba"

        def __init__(self, **_):
            self.dichos = []

        def abrir(self, directorio, tamano):
            return self.id_sesion

        def reanudar(self, id_sesion):
            pass

        def emitir(self, mensaje):
            self.dichos.append(mensaje)
            yield Evento(tipo=TipoEvento.TEXTO, texto=f"escuché: {mensaje}")
            yield Evento(tipo=TipoEvento.RESULTADO, datos={"id_sesion": self.id_sesion})

        def saldo(self):
            return None

    monkeypatch.setitem(adaptadores.REGISTRO, "anthropic", AdaptadorFalso)

    respuesta = cliente.post("/api/chat/asistente", json={"mensaje": "hola"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["texto"] == "escuché: hola"
    assert cuerpo["id_sesion"] == "sesion-de-prueba"
    assert [e["tipo"] for e in cuerpo["eventos"]] == ["texto", "resultado"]


def test_la_conversacion_del_asistente_se_reusa_entre_turnos(cliente, monkeypatch):
    # Un adaptador por conversación, no uno por turno: el adaptador lleva adentro la
    # sesión (ADR-0031), y rehacerlo empezaría de cero cada mensaje.
    from jafne.nucleo import adaptadores
    from jafne.nucleo.sesion import Evento, TipoEvento

    construidos = []

    class AdaptadorFalso:
        proveedor = "anthropic"
        id_sesion = "s1"

        def __init__(self, **_):
            construidos.append(self)

        def abrir(self, directorio, tamano):
            return self.id_sesion

        def emitir(self, mensaje):
            yield Evento(tipo=TipoEvento.TEXTO, texto="ok")

        def reanudar(self, id_sesion):
            pass

        def saldo(self):
            return None

    monkeypatch.setitem(adaptadores.REGISTRO, "anthropic", AdaptadorFalso)
    # Con el id del chat, que es lo que manda el panel en cada turno (ADR-0043). Sin él,
    # cada turno abriría un chat nuevo — que es el default que el Usuario pidió.
    chat_id = cliente.post("/api/chat/asistente", json={"mensaje": "uno"}).json()["chat"]
    cliente.post("/api/chat/asistente", json={"mensaje": "dos", "chat": chat_id})
    assert len(construidos) == 1


def test_el_chat_le_dice_al_adaptador_con_que_rol_habla(cliente, monkeypatch):
    """Sin el rol el agente no sabe quién es (ADR-0040).

    El adaptador resuelve el system prompt a partir del rol, así que si el panel no se lo
    pasa el turno vuelve a viajar sin identidad — que es el estado que ADR-0040 corrigió.
    """
    from jafne.nucleo import adaptadores
    from jafne.nucleo.roles import Rol
    from jafne.nucleo.sesion import Evento, TipoEvento

    recibidos = []

    class AdaptadorFalso:
        proveedor = "anthropic"
        id_sesion = "s1"

        def __init__(self, **kwargs):
            recibidos.append(kwargs)

        def abrir(self, directorio, tamano):
            return self.id_sesion

        def emitir(self, mensaje):
            yield Evento(tipo=TipoEvento.TEXTO, texto="ok")

        def reanudar(self, id_sesion):
            pass

        def saldo(self):
            return None

    monkeypatch.setitem(adaptadores.REGISTRO, "anthropic", AdaptadorFalso)
    cliente.post("/api/chat/asistente", json={"mensaje": "hola"})
    assert recibidos[0]["rol"] is Rol.ASISTENTE


def test_el_chat_escribe_su_chat_pero_no_toca_los_asuntos(cliente, almacen, monkeypatch):
    """La regla que ADR-0035 devolvió entera queda acotada, no rota (ADR-0043).

    El panel **sí** escribe ahora, y solo en `chats/`. El eje que ADR-0008 y ADR-0013
    protegen es el estado de los **Asuntos**, y eso sigue intacto: un chat no tiene estado,
    ni contenedor, ni cierre.
    """
    from jafne.nucleo import adaptadores
    from jafne.nucleo.sesion import Evento, TipoEvento

    class AdaptadorFalso:
        proveedor = "anthropic"
        id_sesion = "s1"

        def __init__(self, **_):
            pass

        def abrir(self, directorio, tamano):
            return self.id_sesion

        def emitir(self, mensaje):
            yield Evento(tipo=TipoEvento.TEXTO, texto="ok")

        def reanudar(self, id_sesion):
            pass

        def saldo(self):
            return None

    monkeypatch.setitem(adaptadores.REGISTRO, "anthropic", AdaptadorFalso)
    asuntos_antes = {(a.proyecto, a.id, a.estado_asunto) for a in almacen.asuntos()}
    cliente.post("/api/chat/asistente", json={"mensaje": "hola"})

    assert {(a.proyecto, a.id, a.estado_asunto) for a in almacen.asuntos()} == asuntos_antes
    assert almacen.chats(), "el chat tiene que haber quedado guardado"


def _adaptador_falso(monkeypatch, texto="ok"):
    """Un proveedor de mentira, para los tests de chats guardados."""
    from jafne.nucleo import adaptadores
    from jafne.nucleo.sesion import Evento, TipoEvento

    reanudados = []

    class AdaptadorFalso:
        proveedor = "anthropic"
        id_sesion = "sesion-del-proveedor"

        def __init__(self, **_):
            pass

        def abrir(self, directorio, tamano):
            return self.id_sesion

        def reanudar(self, id_sesion):
            reanudados.append(id_sesion)

        def emitir(self, mensaje):
            yield Evento(tipo=TipoEvento.TEXTO, texto=texto)

        def saldo(self):
            return None

    monkeypatch.setitem(adaptadores.REGISTRO, "anthropic", AdaptadorFalso)
    return reanudados


# ── chats guardados (ADR-0043) ───────────────────────────────────────────────


def test_un_turno_sin_chat_abre_uno_nuevo(cliente, monkeypatch):
    # "Nuevo por defecto, pero con histórico" — lo que el Usuario pidió.
    _adaptador_falso(monkeypatch)
    cuerpo = cliente.post("/api/chat/asistente", json={"mensaje": "hola"}).json()
    assert cuerpo["chat"]
    assert [c["id"] for c in cliente.get("/api/chats").json()] == [cuerpo["chat"]]


def test_se_guardan_las_dos_puntas_de_la_conversacion(cliente, monkeypatch):
    _adaptador_falso(monkeypatch, texto="te escuché")
    chat_id = cliente.post("/api/chat/asistente", json={"mensaje": "hola"}).json()["chat"]
    mensajes = cliente.get(f"/api/chats/{chat_id}").json()["mensajes"]
    assert [(m["rol"], m["texto"]) for m in mensajes] == [
        ("usuario", "hola"),
        ("asistente", "te escuché"),
    ]


def test_se_guarda_el_id_de_sesion_del_proveedor(cliente, monkeypatch):
    # Es lo que permite reanudar sin reinyectar el historial (ADR-0031).
    _adaptador_falso(monkeypatch)
    chat_id = cliente.post("/api/chat/asistente", json={"mensaje": "hola"}).json()["chat"]
    assert cliente.get(f"/api/chats/{chat_id}").json()["id_sesion"] == "sesion-del-proveedor"


def test_el_titulo_sale_del_primer_mensaje(cliente, monkeypatch):
    # Recién ahí se sabe de qué es la conversación; pedirlo antes es fricción por nada.
    _adaptador_falso(monkeypatch)
    chat_id = cliente.post(
        "/api/chat/asistente", json={"mensaje": "arreglar el panel"}
    ).json()["chat"]
    assert cliente.get(f"/api/chats/{chat_id}").json()["titulo"] == "arreglar el panel"


def test_el_titulo_no_se_pisa_en_el_segundo_turno(cliente, monkeypatch):
    _adaptador_falso(monkeypatch)
    chat_id = cliente.post("/api/chat/asistente", json={"mensaje": "el primero"}).json()["chat"]
    cliente.post("/api/chat/asistente", json={"mensaje": "el segundo", "chat": chat_id})
    assert cliente.get(f"/api/chats/{chat_id}").json()["titulo"] == "el primero"


def test_retomar_un_chat_reanuda_la_sesion_del_proveedor(cliente, monkeypatch):
    """Reanudar, no reinyectar: el historial lo tiene el proveedor (ADR-0031).

    Es lo que hace que retomar un chat viejo sea barato — no se le vuelve a mandar toda la
    conversación, se le pasa el id y él la rehidrata.
    """
    reanudados = _adaptador_falso(monkeypatch)
    chat_id = cliente.post("/api/chat/asistente", json={"mensaje": "uno"}).json()["chat"]

    # Un panel reiniciado: el adaptador en memoria ya no está, pero el chat sí.
    cliente.app.state.sesiones.clear()
    cliente.post("/api/chat/asistente", json={"mensaje": "dos", "chat": chat_id})
    assert reanudados == ["sesion-del-proveedor"]


def test_dos_chats_del_mismo_segundo_no_se_pisan(cliente, monkeypatch, almacen):
    # El panel abre uno al cargar, y un doble clic alcanza para que caigan en el mismo
    # segundo. Sin id único el segundo se metía adentro del primero.
    _adaptador_falso(monkeypatch)
    uno = cliente.post("/api/chats").json()["id"]
    otro = cliente.post("/api/chats").json()["id"]
    assert uno != otro
    assert len(almacen.chats()) == 2


def test_los_chats_se_listan_del_mas_nuevo_al_mas_viejo(cliente, almacen):
    almacen.abrir_chat(chat_id="20260101-000000")
    almacen.abrir_chat(chat_id="20260819-000000")
    assert [c["id"] for c in cliente.get("/api/chats").json()][0] == "20260819-000000"


def test_un_chat_se_borra_a_mano_y_no_caduca(cliente, monkeypatch, almacen):
    # No caducan y no se borran solos: los saca el Usuario cuando quiere (ADR-0043).
    _adaptador_falso(monkeypatch)
    chat_id = cliente.post("/api/chat/asistente", json={"mensaje": "hola"}).json()["chat"]
    assert cliente.delete(f"/api/chats/{chat_id}").json()["borrado"] is True
    assert almacen.chats() == []


def test_un_chat_que_no_existe_da_404(cliente):
    assert cliente.get("/api/chats/20200101-000000").status_code == 404


def test_el_chat_del_encargado_no_se_guarda(cliente, monkeypatch, almacen):
    """El trabajo con un Encargado es un Asunto (ADR-0006, ADR-0043).

    Duplicarlo como chat dejaría dos lugares donde vive lo mismo, y ninguno sería
    claramente el bueno.
    """
    _adaptador_falso(monkeypatch)
    cliente.post("/api/proyectos/borr/chat", json={"mensaje": "hola"})
    assert almacen.chats() == []


def test_el_chat_del_encargado_valida_el_proyecto_primero(cliente):
    assert cliente.post("/api/proyectos/inexistente/chat", json={"mensaje": "x"}).status_code == 404


def test_el_chat_del_encargado_ya_no_es_un_501(cliente, monkeypatch):
    """El Usuario le dio tamaño al Encargado: `grande` (ADR-0044).

    Ese endpoint respondía 501 citando `cerebro-del-encargado-conversando`, que era una
    decisión abierta de verdad: conversando no hay tarea de donde derivar el tamaño. Con la
    decisión tomada, el pendiente salió del registro y el chat contesta.
    """
    from jafne.nucleo import adaptadores
    from jafne.nucleo.sesion import Evento, TipoEvento

    class AdaptadorFalso:
        proveedor = "anthropic"
        id_sesion = "s1"

        def __init__(self, **_):
            pass

        def abrir(self, directorio, tamano):
            return self.id_sesion

        def reanudar(self, id_sesion):
            pass

        def emitir(self, mensaje):
            yield Evento(tipo=TipoEvento.TEXTO, texto="soy el Encargado")

        def saldo(self):
            return None

    monkeypatch.setitem(adaptadores.REGISTRO, "anthropic", AdaptadorFalso)
    respuesta = cliente.post("/api/proyectos/borr/chat", json={"mensaje": "hola"})
    assert respuesta.status_code == 200
    assert respuesta.json()["texto"] == "soy el Encargado"


def test_el_encargado_conversa_con_el_cerebro_grande(cliente, monkeypatch):
    from jafne.nucleo import adaptadores
    from jafne.nucleo.sesion import Evento, TipoEvento

    recibidos = []

    class AdaptadorFalso:
        proveedor = "anthropic"
        id_sesion = "s1"

        def __init__(self, **kwargs):
            recibidos.append(kwargs)

        def abrir(self, directorio, tamano):
            return self.id_sesion

        def reanudar(self, id_sesion):
            pass

        def emitir(self, mensaje):
            yield Evento(tipo=TipoEvento.TEXTO, texto="ok")

        def saldo(self):
            return None

    monkeypatch.setitem(adaptadores.REGISTRO, "anthropic", AdaptadorFalso)
    cliente.post("/api/proyectos/borr/chat", json={"mensaje": "hola"})
    assert recibidos[0]["modelo"] == "claude-opus-5"


def test_el_panel_le_dice_al_encargado_de_que_proyecto_es(cliente, monkeypatch):
    """El proyecto acota su MCP (ADR-0042), y lo pone el panel — no el agente.

    El panel sabe de qué proyecto es la conversación porque está en la URL que el Usuario
    abrió. Si lo eligiera el agente, acotarlo sería una sugerencia.
    """
    from jafne.nucleo import adaptadores
    from jafne.nucleo.sesion import Evento, TipoEvento

    recibidos = []

    class AdaptadorFalso:
        proveedor = "anthropic"
        id_sesion = "s1"

        def __init__(self, **kwargs):
            recibidos.append(kwargs)

        def abrir(self, directorio, tamano):
            return self.id_sesion

        def reanudar(self, id_sesion):
            pass

        def emitir(self, mensaje):
            yield Evento(tipo=TipoEvento.TEXTO, texto="ok")

        def saldo(self):
            return None

    monkeypatch.setitem(adaptadores.REGISTRO, "anthropic", AdaptadorFalso)
    cliente.post("/api/proyectos/borr/chat", json={"mensaje": "hola"})
    assert recibidos[0]["proyecto"] == "borr"


def test_el_asistente_no_se_ata_a_ningun_proyecto(cliente, monkeypatch):
    # Ve todos: es quien enruta (ADR-0002).
    from jafne.nucleo import adaptadores
    from jafne.nucleo.sesion import Evento, TipoEvento

    recibidos = []

    class AdaptadorFalso:
        proveedor = "anthropic"
        id_sesion = "s1"

        def __init__(self, **kwargs):
            recibidos.append(kwargs)

        def abrir(self, directorio, tamano):
            return self.id_sesion

        def reanudar(self, id_sesion):
            pass

        def emitir(self, mensaje):
            yield Evento(tipo=TipoEvento.TEXTO, texto="ok")

        def saldo(self):
            return None

    monkeypatch.setitem(adaptadores.REGISTRO, "anthropic", AdaptadorFalso)
    cliente.post("/api/chat/asistente", json={"mensaje": "hola"})
    assert recibidos[0]["proyecto"] is None


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

    # El Encargado conversa en `grande` desde ADR-0044: los dos roles que conversan
    # necesitaron que alguien les fijara un tamaño, porque conversando no hay tarea.
    assert por_rol["encargado"]["tamano"] == "grande"
    assert por_rol["encargado"]["por_tarea"] is False

    # El Agente sigue sin default, y eso no es un error: ADR-0003 ya decidió que su
    # cerebro se elige tarea por tarea, y un Agente siempre nace de una.
    assert por_rol["agente"]["por_tarea"] is True
    assert por_rol["agente"]["tamano"] is None


def test_el_panel_reporta_la_credencial_sin_pedir_ninguna(cliente):
    """ADR-0034: no hay login en el panel, y esa ausencia es del diseño."""
    datos = cliente.get("/api/credencial").json()
    assert set(datos) >= {"cli_encontrado", "listo", "avisos", "verificado"}
    # Nada que se parezca a un secreto sale por acá.
    assert "token" not in datos and "api_key" not in datos
    assert datos["verificado"] is False


# ── mirar adentro de un Asunto (ADR-0012, ADR-0042) ──────────────────────────


def test_el_registro_del_asunto_se_le_pide_a_infraestructura(cliente, monkeypatch):
    # El panel no corre `podman logs`: ADR-0012 dice que solo Infraestructura habla con el
    # motor. Se verifica que pregunta por el nombre de los tres niveles (ADR-0047).
    import jafne.infraestructura as infra

    pedidos = []

    def falso(nombre, url=None, token=None):
        pedidos.append(nombre)
        return {"nombre": nombre, "existe": True, "registro": "hola", "detalle": None}

    monkeypatch.setattr(infra, "registro_remoto", falso)
    cuerpo = cliente.get("/api/asuntos/borr/migrar-bff/registro?repo=bff").json()
    assert cuerpo["registro"] == "hola"
    assert pedidos == ["jafne-borr-migrar-bff-bff"]


def test_si_infraestructura_esta_apagada_el_registro_lo_dice(cliente, monkeypatch):
    # Un registro vacío se leería como "el Workspace no escribió nada", que es el
    # diagnóstico equivocado. Con Infraestructura caída hay que decir eso.
    import jafne.infraestructura as infra

    def falso(nombre, url=None, token=None):
        raise infra.InfraestructuraInalcanzable("no se pudo hablar con Infraestructura")

    monkeypatch.setattr(infra, "registro_remoto", falso)
    cuerpo = cliente.get("/api/asuntos/borr/migrar-bff/registro?repo=bff").json()
    assert cuerpo["existe"] is False
    assert "Infraestructura" in cuerpo["detalle"]


# ── la identidad de cada rol (ADR-0040, ADR-0042, ADR-0044) ──────────────────


def test_la_identidad_del_asistente_trae_su_prompt_y_su_punto_de_entrada(
    cliente, monkeypatch
):
    # Lo que antes había que deducir leyendo el código: con qué texto arranca el rol y a
    # qué MCP lo apunta JAFNE.
    import jafne.infraestructura as infra

    monkeypatch.setattr(
        infra, "herramientas_remotas", lambda *a, **k: [{"name": "proyectos_listar"}]
    )
    datos = cliente.get("/api/roles/asistente/identidad").json()
    assert datos["prompt_archivo"] == "asistente.md"
    assert "Asistente" in datos["prompt"]
    assert datos["mcp_url"].endswith("/mcp/asistente")
    assert datos["herramientas"][0]["name"] == "proyectos_listar"


def test_la_identidad_del_encargado_apunta_al_mcp_de_su_proyecto(cliente, monkeypatch):
    # El acotamiento de ADR-0042 viaja en la URL, así que tiene que verse en la URL.
    import jafne.infraestructura as infra

    monkeypatch.setattr(infra, "herramientas_remotas", lambda *a, **k: [])
    datos = cliente.get("/api/roles/encargado/identidad?proyecto=borr").json()
    assert datos["mcp_url"].endswith("/mcp/proyecto/borr")


def test_el_agente_muestra_su_prompt_y_dice_por_que_no_tiene_mcp(cliente):
    # Ya tiene prompt (ADR-0047/0048 contestaron qué es un repo), pero sigue sin MCP: su
    # alcance es un repositorio y el servidor no expone ese recorte (ADR-0044). El panel
    # tiene que mostrar las dos cosas sin tratar la segunda como un error.
    datos = cliente.get("/api/roles/agente/identidad").json()
    assert datos["prompt_archivo"] == "agente.md"
    assert "repositorio" in datos["prompt"]
    assert datos["mcp_url"] is None
    assert "repositorio" in datos["detalle"]


def test_si_infraestructura_esta_apagada_la_identidad_lo_dice(cliente, monkeypatch):
    import jafne.infraestructura as infra

    def falso(*a, **k):
        raise infra.InfraestructuraInalcanzable("Infraestructura no contesta")

    monkeypatch.setattr(infra, "herramientas_remotas", falso)
    datos = cliente.get("/api/roles/asistente/identidad").json()
    assert datos["herramientas"] == []
    assert "Infraestructura" in datos["detalle"]


# ── capacidades de un repo (ADR-0004) ────────────────────────────────────────


def test_las_capacidades_de_un_repo_se_sirven_por_el_panel(cliente, tmp_path, monkeypatch):
    import jafne.panel.api as panel_api

    (tmp_path / "mi-repo" / ".agents" / "skills" / "una").mkdir(parents=True)
    (tmp_path / "mi-repo" / ".agents" / "skills" / "una" / "SKILL.md").write_text(
        "---\nname: una\ndescription: Hace algo.\n---\n", encoding="utf-8"
    )
    monkeypatch.setattr(panel_api, "raiz_de_trabajo", lambda: str(tmp_path))
    datos = cliente.get("/api/repos/mi-repo/capacidades").json()
    assert datos["existe"] is True
    assert datos["skills"][0]["nombre"] == "una"


def test_no_se_pueden_leer_capacidades_fuera_de_la_raiz_de_trabajo(
    cliente, tmp_path, monkeypatch
):
    # El borde de ADR-0039 vale también para leer: sin esto, un `..` en el nombre dejaría
    # listar cualquier carpeta del disco a través del panel.
    import jafne.panel.api as panel_api

    monkeypatch.setattr(panel_api, "raiz_de_trabajo", lambda: str(tmp_path))
    respuesta = cliente.get("/api/repos/..%2F..%2Fetc/capacidades")
    assert respuesta.status_code == 404
