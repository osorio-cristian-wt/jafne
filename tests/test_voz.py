"""Dictado por voz del panel: Whisper local (ADR-0036).

Estos tests no cargan el modelo: pesa varios GB y tardaría más que toda la suite. Lo que
fijan es el contrato alrededor —qué se declara, qué se rechaza y cómo se informa lo que
falta—, que es donde están las decisiones. Que el motor transcriba bien es problema de
Whisper, no de JAFNE.

El paquete se enmascara en `sys.modules` en vez de mirar si está instalado: así los dos
caminos —con motor y sin motor— se verifican igual en cualquier máquina.
"""

import io
import sys
import types

import pytest

from jafne.nucleo import transcripcion
from jafne.nucleo.transcripcion import (
    LIMITE_AUDIO,
    MODELO_POR_DEFECTO,
    VARIABLE_MODELO,
    AudioInvalido,
    TranscripcionNoDisponible,
)


@pytest.fixture(autouse=True)
def sin_modelo_cargado():
    """El modelo vive en un `lru_cache`: se limpia para que un test no arrastre al otro."""
    transcripcion._motor.cache_clear()
    yield
    transcripcion._motor.cache_clear()


@pytest.fixture
def con_motor(monkeypatch):
    """Simula el extra `voz` instalado, sin depender de que lo esté."""
    monkeypatch.setitem(sys.modules, "faster_whisper", types.ModuleType("faster_whisper"))


@pytest.fixture
def sin_motor(monkeypatch):
    """Simula el extra `voz` ausente: `import faster_whisper` levanta ImportError."""
    monkeypatch.setitem(sys.modules, "faster_whisper", None)


# ── qué se declara (ADR-0036) ────────────────────────────────────────────────


def test_el_modelo_por_defecto_es_el_grande(con_motor):
    # Es lo que pidió el Usuario y lo que la máquina sostiene.
    assert transcripcion.estado().modelo == MODELO_POR_DEFECTO == "large-v3"


def test_el_modelo_se_puede_declarar_por_configuracion(monkeypatch, con_motor):
    monkeypatch.setenv(VARIABLE_MODELO, "medium")
    assert transcripcion.estado().modelo == "medium"


def test_el_estado_no_carga_el_modelo_para_contestar(con_motor):
    # Si contestar "¿se puede dictar?" cargara el modelo, abrir el panel pagaría varios GB
    # de RAM sin que nadie haya dictado nada.
    estado = transcripcion.estado()
    assert estado.disponible
    assert not estado.cargado


def test_el_estado_dice_que_el_audio_no_sale_de_la_maquina(con_motor):
    # Es la propiedad que justifica el costo en CPU, así que se muestra, no se supone.
    assert "no sale de esta máquina" in transcripcion.estado().detalle


# ── sin el motor instalado: se informa, no se rompe ──────────────────────────


def test_sin_el_motor_el_dictado_se_reporta_no_disponible(sin_motor):
    estado = transcripcion.estado()
    assert not estado.disponible
    assert "voz" in estado.detalle  # dice con qué extra se instala


def test_sin_el_motor_transcribir_falla_con_su_propio_error(sin_motor):
    # ADR-0036: es un error de instalación, no una decisión abierta. Si levantara
    # `DecisionPendiente`, la pregunta "¿qué falta decidir?" dejaría de tener respuesta
    # confiable — la misma separación que ADR-0028 hizo con los adaptadores.
    with pytest.raises(TranscripcionNoDisponible):
        transcripcion.transcribir(b"audio de mentira")


def test_el_error_de_falta_de_motor_no_es_una_decision_pendiente(sin_motor):
    from jafne.pendientes import DecisionPendiente

    assert not issubclass(TranscripcionNoDisponible, DecisionPendiente)


# ── qué audio se acepta ──────────────────────────────────────────────────────


def test_un_audio_vacio_se_rechaza_antes_de_tocar_el_modelo(sin_motor):
    # Se valida antes de cargar nada: por eso falla con AudioInvalido y no por falta de
    # motor, aun con el motor enmascarado.
    with pytest.raises(AudioInvalido):
        transcripcion.transcribir(b"")


def test_un_audio_demasiado_grande_se_rechaza(sin_motor):
    # Un endpoint sin límite es una forma barata de tumbar el proceso del panel: alcanza
    # con dejar el micrófono abierto y olvidado.
    with pytest.raises(AudioInvalido) as error:
        transcripcion.transcribir(b"x" * (LIMITE_AUDIO + 1))
    assert "límite" in str(error.value)


def test_el_limite_de_audio_se_publica_para_el_navegador(con_motor):
    assert transcripcion.estado().a_dict()["limite_audio"] == LIMITE_AUDIO


# ── el panel (ADR-0036 sobre ADR-0013) ───────────────────────────────────────


def test_el_panel_publica_el_estado_del_dictado(cliente, con_motor):
    datos = cliente.get("/api/voz").json()
    assert datos["disponible"] is True
    assert datos["modelo"] == MODELO_POR_DEFECTO


def test_el_panel_avisa_cuando_falta_el_motor(cliente, sin_motor):
    datos = cliente.get("/api/voz").json()
    assert datos["disponible"] is False


def test_transcribir_sin_motor_responde_501_pero_decidido(cliente, sin_motor):
    respuesta = cliente.post("/api/transcribir", content=b"audio de mentira")
    assert respuesta.status_code == 501
    # Mismo 501 que el chat, distinta causa: acá la decisión está tomada y falta el
    # paquete, así que la respuesta lo dice y el panel puede sugerir cómo instalarlo.
    assert respuesta.json()["decidido"] is True
    assert respuesta.json()["error"] == "voz_no_disponible"


def test_transcribir_sin_audio_responde_400(cliente):
    respuesta = cliente.post("/api/transcribir", content=b"")
    assert respuesta.status_code == 400
    assert respuesta.json()["error"] == "audio_invalido"


def test_el_dictado_no_escribe_estado(cliente, almacen, sin_motor):
    # ADR-0035 le devolvió al panel la propiedad de no escribir estado, y ADR-0036 la
    # mantiene: transcribir es cómputo, no una escritura. Si esto se cayera, el panel
    # habría vuelto a ser escritor por la puerta de atrás.
    antes = {a.id: a.estado_asunto for a in almacen.asuntos()}
    cliente.post("/api/transcribir", content=b"audio de mentira")
    assert {a.id: a.estado_asunto for a in almacen.asuntos()} == antes
    assert not (almacen.ruta / "audio").exists()


# ── delegar en un nodo de la malla (ADR-0037) ────────────────────────────────


def _redirigir_al_nodo(monkeypatch, servidor):
    """Hace que el cliente HTTP del módulo caiga en el nodo de mentira, sin abrir sockets.

    Se intercepta `urlopen` y no el módulo entero a propósito: así lo que se verifica es el
    viaje completo —cabeceras, cuerpo, códigos de error— y no una función mockeada que
    devuelve lo que el test quiere oír.
    """
    import urllib.request

    class Respuesta:
        def __init__(self, cuerpo):
            self._cuerpo = cuerpo

        def read(self):
            return self._cuerpo

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def urlopen(pedido, timeout=None):
        ruta = pedido.full_url.split("8731", 1)[1]
        cabeceras = dict(pedido.header_items())
        if pedido.get_method() == "GET":
            r = servidor.get(ruta, headers=cabeceras)
        else:
            r = servidor.post(ruta, content=pedido.data, headers=cabeceras)
        if r.status_code >= 400:
            raise urllib.error.HTTPError(
                pedido.full_url, r.status_code, "", r.headers, io.BytesIO(r.content)
            )
        return Respuesta(r.content)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)


@pytest.fixture
def nodo(monkeypatch):
    """El nodo de voz real, servido en memoria y declarado como destino del dictado."""
    from fastapi.testclient import TestClient

    from jafne import voz as nodo_voz

    servidor = TestClient(nodo_voz.crear_app())
    monkeypatch.setenv(transcripcion.VARIABLE_NODO, "http://nodo-de-prueba:8731")
    _redirigir_al_nodo(monkeypatch, servidor)
    return servidor


def test_el_audio_va_al_nodo_y_el_texto_vuelve(monkeypatch, nodo):
    """El viaje completo: panel → nodo → panel, sin cargar ningún modelo de este lado."""
    from jafne import voz as nodo_voz

    recibido = {}

    def transcribir_en_el_nodo(audio, idioma=None):
        recibido["audio"] = audio
        recibido["idioma"] = idioma
        return transcripcion.Transcripcion(
            texto="probando el dictado", idioma="es", duracion=2.0, modelo="large-v3"
        )

    monkeypatch.setattr(nodo_voz, "voz_transcribir", transcribir_en_el_nodo)

    resultado = transcripcion.transcribir(b"audio-de-mentira", idioma="es")

    assert recibido["audio"] == b"audio-de-mentira"
    assert recibido["idioma"] == "es"
    assert resultado.texto == "probando el dictado"
    # `donde` es lo que después muestra el panel: tras ADR-0037, en qué máquina se
    # transcribió el audio dejó de ser obvio.
    assert resultado.donde == "http://nodo-de-prueba:8731"


def test_el_nodo_reporta_su_propio_estado_no_el_de_aca(monkeypatch, nodo, sin_motor):
    # Con un nodo declarado, este proceso puede no tener ni faster-whisper: el modelo y el
    # dispositivo que importan son los del otro lado.
    estado = transcripcion.estado()
    assert estado.nodo == "http://nodo-de-prueba:8731"
    assert "delegado en el nodo" in estado.detalle


def test_un_rechazo_del_nodo_vuelve_como_audio_invalido(nodo):
    # El nodo corre el mismo JAFNE, así que sus errores ya vienen con la forma de acá: lo
    # único que hay que hacer es no perderlos por el camino.
    with pytest.raises(AudioInvalido):
        transcripcion.transcribir(b"")


def test_con_nodo_declarado_el_audio_se_manda_alla(monkeypatch, nodo, con_motor):
    # No es una preferencia: es lo que evita que el panel cargue un modelo de 3 GB en una
    # máquina que decidió no transcribir.
    assert transcripcion.nodo_declarado() == "http://nodo-de-prueba:8731"
    assert transcripcion.estado().nodo == "http://nodo-de-prueba:8731"


def test_sin_nodo_declarado_se_transcribe_aca(con_motor):
    # ADR-0037 no cambia el default: sin declarar nada, sigue valiendo ADR-0036.
    assert transcripcion.nodo_declarado() is None
    assert transcripcion.estado().nodo is None


def test_el_nodo_apagado_se_rechaza_y_no_cae_a_la_cpu_local(monkeypatch, con_motor):
    # La diferencia entre un segundo y catorce tiene que verse: un dictado que de golpe
    # tarda diez veces más parece un panel roto, no un nodo apagado (ADR-0037).
    monkeypatch.setenv(transcripcion.VARIABLE_NODO, "http://127.0.0.1:1")
    with pytest.raises(transcripcion.NodoInalcanzable):
        transcripcion.transcribir(b"audio de mentira")


def test_un_nodo_inalcanzable_deja_el_estado_no_disponible_con_el_motivo(monkeypatch):
    monkeypatch.setenv(transcripcion.VARIABLE_NODO, "http://127.0.0.1:1")
    estado = transcripcion.estado()
    assert not estado.disponible
    assert estado.nodo == "http://127.0.0.1:1"
    assert "nodo de voz" in estado.detalle


def test_nodo_inalcanzable_es_un_caso_de_voz_no_disponible():
    # Hereda a propósito: para el panel es el mismo 501 "decidido", con otro motivo.
    assert issubclass(transcripcion.NodoInalcanzable, TranscripcionNoDisponible)


def test_el_audio_grande_se_corta_antes_de_salir_a_la_red(monkeypatch):
    # No tiene sentido empujar 30 MB por la malla para que los rechacen del otro lado.
    monkeypatch.setenv(transcripcion.VARIABLE_NODO, "http://127.0.0.1:1")
    with pytest.raises(AudioInvalido):
        transcripcion.transcribir(b"x" * (LIMITE_AUDIO + 1))


# ── dónde corre: cuda, cpu, y qué se rechaza (ADR-0037) ──────────────────────


def test_auto_elige_cpu_si_no_hay_gpu(monkeypatch):
    # `auto` cayendo en CPU no es degradar: es lo que el Usuario pidió al no elegir.
    monkeypatch.setattr(transcripcion, "_hay_cuda", lambda: False)
    assert transcripcion.dispositivo_efectivo() == "cpu"


def test_auto_elige_cuda_si_la_hay(monkeypatch):
    monkeypatch.setattr(transcripcion, "_hay_cuda", lambda: True)
    assert transcripcion.dispositivo_efectivo() == "cuda"


def test_cuda_declarada_y_ausente_se_rechaza(monkeypatch):
    # Si no, un nodo con CUDA mal instalada transcribiría a 3x tiempo real y nadie se
    # enteraría hasta cronometrarlo (ADR-0037).
    monkeypatch.setenv(transcripcion.VARIABLE_DISPOSITIVO, "cuda")
    monkeypatch.setattr(transcripcion, "_hay_cuda", lambda: False)
    with pytest.raises(TranscripcionNoDisponible) as error:
        transcripcion.dispositivo_efectivo()
    assert "cuda" in str(error.value).lower()


def test_la_cuantizacion_acompana_al_dispositivo(monkeypatch):
    # int8 es lo que vuelve usable al modelo grande sin GPU; float16 aprovecha la que hay.
    monkeypatch.delenv(transcripcion.VARIABLE_COMPUTO, raising=False)
    assert transcripcion.computo_declarado("cpu") == "int8"
    assert transcripcion.computo_declarado("cuda") == "float16"


def test_la_cuantizacion_declarada_gana(monkeypatch):
    monkeypatch.setenv(transcripcion.VARIABLE_COMPUTO, "int8_float16")
    assert transcripcion.computo_declarado("cuda") == "int8_float16"


# ── el nodo presta cómputo, no es un segundo JAFNE (ADR-0037) ────────────────


def test_el_nodo_no_expone_nada_del_almacen():
    from fastapi.testclient import TestClient

    from jafne import voz as nodo_voz

    servidor = TestClient(nodo_voz.crear_app())
    # Solo dos endpoints: si algún día aparece /api/asuntos acá, el nodo dejó de prestar
    # cómputo y pasó a ser un segundo JAFNE con estado propio.
    assert servidor.get("/api/proyectos").status_code == 404
    assert servidor.get("/api/asuntos").status_code == 404
    assert servidor.get("/api/voz").status_code == 200


def test_el_nodo_fuera_de_loopback_exige_token():
    from jafne.acceso import ConfiguracionInsegura
    from jafne import voz as nodo_voz

    with pytest.raises(ConfiguracionInsegura):
        nodo_voz.validar_bind("10.144.0.2", None)
    nodo_voz.validar_bind("10.144.0.2", "un-token")  # con token, permitido


def test_el_nodo_nunca_escucha_en_todas_las_interfaces():
    from jafne.acceso import ConfiguracionInsegura
    from jafne import voz as nodo_voz

    with pytest.raises(ConfiguracionInsegura):
        nodo_voz.validar_bind("0.0.0.0", "un-token")


def test_el_nodo_sin_token_valido_responde_401():
    from fastapi.testclient import TestClient

    from jafne import voz as nodo_voz

    servidor = TestClient(nodo_voz.crear_app(token="el-token"))
    assert servidor.get("/api/voz").status_code == 401
    assert servidor.get("/api/voz", headers={"X-Jafne-Token": "el-token"}).status_code == 200


def test_el_nodo_no_se_reenvia_el_pedido_a_si_mismo(monkeypatch, nodo, con_motor):
    """Con `$JAFNE_VOZ_NODO` puesto en la máquina del nodo, el nodo transcribe igual.

    El lazo es fácil de reintroducir: alcanza con que el servicio llame a `transcribir()`
    en vez de a `transcribir_local()`. Como el nodo hereda el entorno de quien lo arranca,
    la variable puede estar puesta ahí por copiar y pegar, y el pedido daría vueltas sin
    fondo en vez de fallar.
    """
    from jafne import voz as nodo_voz

    assert nodo_voz.voz_transcribir is transcripcion.transcribir_local
    assert nodo_voz.voz_estado is transcripcion.estado_local

    # El nodo tiene la variable puesta (la declara el fixture) y aun así contesta por sí
    # mismo, en vez de salir a buscarse.
    assert transcripcion.nodo_declarado() is not None
    assert nodo.get("/api/voz").json()["nodo"] is None
