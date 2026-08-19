"""Roles y su cerebro (ADR-0033), y el contrato de sesión (ADR-0031)."""

from collections.abc import Iterator

import pytest

from jafne.nucleo import Almacen
from jafne.nucleo.almacen import SinCerebroParaElRol
from jafne.nucleo.modelos import Suscripcion
from jafne.nucleo.roles import Rol, RolInvalido, parsear, tamano_por_defecto
from jafne.nucleo.sesion import AdaptadorSesion, Evento, TipoEvento, cumple_contrato
from jafne.nucleo.tamanos import Tamano


@pytest.fixture
def alm(tmp_path):
    almacen = Almacen(tmp_path / "jafne")
    almacen.inicializar()
    return almacen


# ── roles (ADR-0033) ─────────────────────────────────────────────────────────


def test_el_usuario_no_es_un_rol():
    # Es humano y no ejecuta un cerebro.
    assert {r.value for r in Rol} == {"asistente", "encargado", "agente"}
    with pytest.raises(RolInvalido):
        parsear("usuario")


def test_el_asistente_corre_en_medio():
    assert tamano_por_defecto(Rol.ASISTENTE) is Tamano.MEDIO


def test_el_encargado_conversa_en_grande():
    """Lo fijó el Usuario (ADR-0044), y no contradice a ADR-0003.

    Lo que ADR-0003 dejó al Encargado es el cerebro de una **tarea**. Esto es el tamaño con
    el que *conversa*, que es cuando todavía no hay tarea de donde derivarlo — y su trabajo
    al conversar es arquitectura y organización, donde la capacidad del modelo es lo que
    más pesa.
    """
    assert tamano_por_defecto(Rol.ENCARGADO) is Tamano.GRANDE


def test_solo_el_agente_se_elige_por_tarea():
    # `None` no es "falta decidirlo": es la decisión de ADR-0003. Un Agente siempre nace de
    # una tarea concreta, así que ahí sí hay de dónde derivarlo.
    assert tamano_por_defecto(Rol.AGENTE) is None


def test_el_cerebro_del_asistente_se_deriva_de_cerebros_yaml(alm):
    cerebro = alm.cerebro_de(Rol.ASISTENTE)
    assert cerebro.tamano is Tamano.MEDIO
    assert cerebro.modelo == "claude-sonnet-5"


def test_no_se_le_da_al_asistente_un_cerebro_sin_adaptador(alm):
    # Hay dos cerebros `medio` de fábrica; el de OpenAI no tiene adaptador (ADR-0028).
    assert alm.cerebro_de(Rol.ASISTENTE).proveedor == "anthropic"


def test_cambiar_cerebros_yaml_cambia_el_cerebro_del_asistente(alm):
    # Se deriva al leer, así que no hay copia que se desincronice.
    alm.ruta_cerebros.write_text(
        "cerebros:\n"
        "  otro-medio:\n"
        "    proveedor: anthropic\n"
        "    modelo: modelo-nuevo\n"
        "    tamano: medio\n",
        encoding="utf-8",
    )
    assert alm.cerebro_de(Rol.ASISTENTE).modelo == "modelo-nuevo"


def test_sin_cerebro_usable_falla_diciendo_que_falta(alm):
    # Solo cerebros de OpenAI: son `medio` pero no tienen adaptador.
    alm.ruta_cerebros.write_text(
        "cerebros:\n  solo-openai:\n    proveedor: openai\n    tamano: medio\n",
        encoding="utf-8",
    )
    with pytest.raises(SinCerebroParaElRol) as excepcion:
        alm.cerebro_de(Rol.ASISTENTE)
    assert "adaptador" in str(excepcion.value)


def test_el_encargado_resuelve_un_cerebro_grande(alm):
    # ADR-0044 le dio tamaño, así que su chat dejó de responder 501.
    assert alm.cerebro_de(Rol.ENCARGADO).tamano is Tamano.GRANDE


def test_un_rol_sin_tamano_no_resuelve_cerebro(alm):
    # El Agente sigue sin default: lo elige el Encargado por tarea (ADR-0003).
    assert alm.cerebro_de(Rol.AGENTE) is None


# ── contrato de sesión (ADR-0031) ────────────────────────────────────────────


class _AdaptadorDePrueba:
    """Un adaptador mínimo, para probar que el contrato se puede cumplir."""

    proveedor = "de-prueba"

    def abrir(self, directorio: str, tamano: Tamano) -> str:
        return "ses-1"

    def reanudar(self, id_sesion: str) -> None:
        return None

    def emitir(self, mensaje: str) -> Iterator[Evento]:
        yield Evento(tipo=TipoEvento.TEXTO, texto="hola")
        yield Evento(tipo=TipoEvento.RESULTADO, datos={"costo_usd": 0.01})

    def saldo(self) -> Suscripcion | None:
        return None


def test_el_contrato_se_puede_cumplir_sin_heredar_de_nada():
    # Es un Protocol: un adaptador no depende del núcleo para cumplirlo.
    assert cumple_contrato(_AdaptadorDePrueba())
    assert isinstance(_AdaptadorDePrueba(), AdaptadorSesion)


def test_algo_que_no_tiene_las_cuatro_operaciones_no_cumple():
    class Incompleto:
        proveedor = "roto"

        def abrir(self, directorio, tamano):
            return "x"

    assert not cumple_contrato(Incompleto())


def test_el_contrato_congelado_tiene_exactamente_cuatro_operaciones():
    # ADR-0031: cuatro, ni una más. Todo lo que no esté acá es específico de un proveedor
    # y no puede subir al contrato sin romper ADR-0003.
    operaciones = {n for n in dir(AdaptadorSesion) if not n.startswith("_")}
    assert operaciones == {"abrir", "reanudar", "emitir", "saldo"}
    # `proveedor` es un atributo del adaptador, no una operación del contrato.
    assert "proveedor" in AdaptadorSesion.__annotations__


def test_los_eventos_se_serializan_para_el_panel():
    evento = Evento(tipo=TipoEvento.HERRAMIENTA, texto="Read", datos={"ruta": "a.py"})
    assert evento.a_dict() == {
        "tipo": "herramienta",
        "texto": "Read",
        "datos": {"ruta": "a.py"},
    }


# ── credencial (ADR-0034) ────────────────────────────────────────────────────


def test_una_api_key_en_el_entorno_se_avisa_porque_pisa_la_suscripcion(monkeypatch):
    """El aviso que justifica todo el módulo.

    ADR-0034 eligió la suscripción justamente para no gastar por token. Una
    `ANTHROPIC_API_KEY` olvidada de otro proyecto la pisa en silencio y llega en la
    factura, no en un error.
    """
    from jafne.nucleo import credenciales

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-lo-que-sea")
    estado = credenciales.estado()
    assert estado.api_key_definida is True
    assert any("pisa" in aviso for aviso in estado.avisos)


def test_sin_api_key_no_hay_aviso(monkeypatch):
    from jafne.nucleo import credenciales

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert credenciales.estado().avisos == ()


def test_el_cli_se_puede_apuntar_a_mano_porque_no_siempre_esta_en_el_path(monkeypatch, tmp_path):
    # Quien usa Claude Code desde la extensión no tiene `claude` en el PATH.
    from jafne.nucleo import credenciales

    binario = tmp_path / "claude.exe"
    binario.write_text("", encoding="utf-8")
    monkeypatch.setenv(credenciales.VARIABLE_CLI, str(binario))
    assert credenciales.ruta_cli() == str(binario)

    monkeypatch.setenv(credenciales.VARIABLE_CLI, str(tmp_path / "no-existe"))
    assert credenciales.ruta_cli() is None


def test_no_se_declara_listo_sin_cli_ni_sesion(monkeypatch, tmp_path):
    from jafne.nucleo import credenciales

    monkeypatch.setenv(credenciales.VARIABLE_CLI, str(tmp_path / "no-existe"))
    monkeypatch.setenv(credenciales.VARIABLE_CONFIG, str(tmp_path / "sin-config"))
    estado = credenciales.estado()
    assert estado.listo is False
    assert "JAFNE_CLAUDE_CLI" in estado.sugerencia


def test_estar_listo_no_significa_sesion_verificada(monkeypatch, tmp_path):
    # Confirmarlo exige una llamada real, y cobrarle tokens al Usuario por mirar el
    # panel sería peor que no confirmarlo.
    from jafne.nucleo import credenciales

    binario = tmp_path / "claude.exe"
    binario.write_text("", encoding="utf-8")
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setenv(credenciales.VARIABLE_CLI, str(binario))
    monkeypatch.setenv(credenciales.VARIABLE_CONFIG, str(config))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    estado = credenciales.estado()
    assert estado.listo is True
    assert estado.sugerencia is None
    assert estado.a_dict()["verificado"] is False
