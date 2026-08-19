"""Control de acceso compartido: bind, token y TLS (ADR-0020, ADR-0038).

Vive aparte de `test_api.py` porque `jafne/acceso.py` dejó de ser del panel: lo usan el
panel y el nodo de voz, y lo que se fija acá es que la regla sea **una sola**. Dos
servicios con comprobaciones copiadas terminan, tarde o temprano, con reglas distintas.
"""

import pytest

from jafne.acceso import (
    ConfiguracionInsegura,
    aviso_sin_tls,
    es_loopback,
    es_todas_las_interfaces,
    resolver_tls,
    resolver_token,
    validar_bind,
)

CERT = "JAFNE_PRUEBA_CERT"
CLAVE = "JAFNE_PRUEBA_CLAVE"


@pytest.fixture
def par(tmp_path):
    """Un certificado y su clave de mentira: acá solo importa que los archivos existan."""
    cert = tmp_path / "panel.crt"
    clave = tmp_path / "panel.key"
    cert.write_text("-----BEGIN CERTIFICATE-----", encoding="utf-8")
    clave.write_text("-----BEGIN PRIVATE KEY-----", encoding="utf-8")
    return cert, clave


# ── bind y token (ADR-0020) ──────────────────────────────────────────────────


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_se_reconoce(host):
    assert es_loopback(host)


@pytest.mark.parametrize("host", ["", "0.0.0.0", "::", "*"])
def test_todas_las_interfaces_se_reconocen(host):
    assert es_todas_las_interfaces(host)


def test_el_mensaje_nombra_al_servicio_que_falla():
    # El panel y el nodo comparten la comprobación, así que el error tiene que decir cuál
    # de los dos se negó a arrancar.
    with pytest.raises(ConfiguracionInsegura) as error:
        validar_bind("0.0.0.0", "t", servicio="El nodo de voz", variable="X")
    assert "El nodo de voz" in str(error.value)


def test_el_token_sale_del_entorno_si_no_se_pasa(monkeypatch):
    monkeypatch.setenv("JAFNE_PRUEBA_TOKEN", "del-entorno")
    assert resolver_token(None, "JAFNE_PRUEBA_TOKEN") == "del-entorno"
    assert resolver_token("explicito", "JAFNE_PRUEBA_TOKEN") == "explicito"


# ── TLS (ADR-0038) ───────────────────────────────────────────────────────────


def test_sin_declarar_nada_no_hay_tls(monkeypatch):
    # ADR-0038: TLS es opcional. Sin certificado se sirve HTTP, porque por la malla el
    # tráfico ya va cifrado (ADR-0011) y mirar el dashboard así es legítimo.
    monkeypatch.delenv(CERT, raising=False)
    monkeypatch.delenv(CLAVE, raising=False)
    assert resolver_tls(None, None, CERT, CLAVE) is None


def test_declarar_el_certificado_sin_la_clave_se_rechaza(par, monkeypatch):
    monkeypatch.delenv(CLAVE, raising=False)
    with pytest.raises(ConfiguracionInsegura) as error:
        resolver_tls(str(par[0]), None, CERT, CLAVE)
    assert CLAVE in str(error.value)


def test_declarar_la_clave_sin_el_certificado_se_rechaza(par, monkeypatch):
    monkeypatch.delenv(CERT, raising=False)
    with pytest.raises(ConfiguracionInsegura):
        resolver_tls(None, str(par[1]), CERT, CLAVE)


def test_un_certificado_inexistente_se_rechaza_antes_de_escuchar(tmp_path, monkeypatch):
    # Se comprueba al arrancar y no al primer navegador: un servicio que dijo estar listo
    # y no lo estaba es peor que uno que no arrancó.
    monkeypatch.delenv(CERT, raising=False)
    monkeypatch.delenv(CLAVE, raising=False)
    with pytest.raises(ConfiguracionInsegura) as error:
        resolver_tls(str(tmp_path / "no-existe.crt"), str(tmp_path / "no-existe.key"), CERT, CLAVE)
    assert "mkcert" in str(error.value)  # dice cómo generarlo


def test_con_los_dos_archivos_se_devuelven_sus_rutas(par):
    rutas = resolver_tls(str(par[0]), str(par[1]), CERT, CLAVE)
    assert rutas == (par[0], par[1])


def test_el_tls_tambien_se_declara_por_entorno(par, monkeypatch):
    monkeypatch.setenv(CERT, str(par[0]))
    monkeypatch.setenv(CLAVE, str(par[1]))
    assert resolver_tls(None, None, CERT, CLAVE) == (par[0], par[1])


# ── el aviso: por qué importa el TLS acá (ADR-0038) ──────────────────────────


def test_en_loopback_no_se_avisa_nada():
    # Loopback ya es contexto seguro para el navegador: el micrófono anda sin TLS.
    assert aviso_sin_tls("127.0.0.1") is None


def test_fuera_de_loopback_se_avisa_que_el_microfono_no_va_a_andar():
    # El motivo del TLS en ADR-0038 no es la confidencialidad —la malla ya cifra— sino que
    # el navegador no entrega el micrófono a un origen inseguro. El aviso dice eso, para
    # que no se descubra con un botón gris.
    aviso = aviso_sin_tls("10.144.0.1")
    assert aviso is not None
    assert "micrófono" in aviso
    assert "ADR-0011" in aviso  # y aclara que el tráfico igual va cifrado


# ── ruido del log en Windows (asyncio Proactor) ──────────────────────────────


def _contexto_de_corte(mensaje="Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)"):
    return {"message": mensaje, "exception": ConnectionResetError(10054, "forzada")}


def test_el_corte_cosmetico_de_windows_se_reconoce():
    # asyncio llama shutdown() sobre un socket que el otro lado ya reseteó. La respuesta
    # ya salió: no hay nada que arreglar, y en un servicio de larga vida es la mayor
    # fuente de ruido del log.
    from jafne.servicio import _es_corte_cosmetico

    assert _es_corte_cosmetico(_contexto_de_corte())


def test_un_corte_de_conexion_en_otro_lado_no_se_silencia():
    # Acotado a propósito: perder la conexión contra el nodo de voz a mitad de una
    # transcripción (ADR-0037) es un hecho que hay que ver.
    from jafne.servicio import _es_corte_cosmetico

    assert not _es_corte_cosmetico(_contexto_de_corte("Task exception was never retrieved"))


def test_cualquier_otro_error_no_se_silencia():
    from jafne.servicio import _es_corte_cosmetico

    assert not _es_corte_cosmetico(
        {"message": "algo con _call_connection_lost", "exception": ValueError("otra cosa")}
    )


def test_lo_que_no_es_cosmetico_va_al_manejador_de_siempre():
    from jafne.servicio import _manejador

    vistos = []

    class BucleFalso:
        def default_exception_handler(self, contexto):
            vistos.append(contexto)

    bucle = BucleFalso()
    _manejador(bucle, _contexto_de_corte())  # cosmético: se descarta
    assert vistos == []

    grave = {"message": "boom", "exception": RuntimeError("de verdad")}
    _manejador(bucle, grave)
    assert vistos == [grave]
