"""El registro de puertos publicados hacia la malla (ADR-0011).

Lo que se verifica acá es la cuenta, no el motor: asignar el primer libre de un rango es
determinista y se prueba sin Podman. Que dos proyectos con el mismo nombre de servicio no
se choquen **adentro** no se prueba acá porque no pasa por este módulo — lo resuelve la red
por proyecto, verificado el 2026-08-19 contra el motor real.
"""

import pytest

from jafne.nucleo.puertos import RANGO, Registro, SinPuertosLibres


@pytest.fixture
def registro(tmp_path) -> Registro:
    return Registro(tmp_path)


def test_el_primer_puerto_sale_del_rango_de_jafne(registro):
    assert registro.reservar("jafne-borr-x-front", 3000).puerto == RANGO.start


def test_dos_servicios_distintos_no_reciben_el_mismo_puerto(registro):
    uno = registro.reservar("jafne-borr-x-front", 3000)
    otro = registro.reservar("jafne-otro-y-front", 3000)
    assert uno.puerto != otro.puerto


def test_pedir_dos_veces_lo_mismo_devuelve_el_mismo_puerto(registro):
    # Si el puerto cambiara en cada rearmado, el link que el Usuario ya tenía dejaría de
    # servir. La idempotencia es lo que hace que un contenedor se pueda recrear.
    primero = registro.reservar("jafne-borr-x-front", 3000)
    assert registro.reservar("jafne-borr-x-front", 3000).puerto == primero.puerto


def test_un_mismo_contenedor_puede_publicar_dos_servicios(registro):
    web = registro.reservar("jafne-borr-x-bff", 3000)
    metricas = registro.reservar("jafne-borr-x-bff", 9090)
    assert web.puerto != metricas.puerto
    assert len(registro.de("jafne-borr-x-bff")) == 2


def test_liberar_devuelve_los_puertos_al_rango(registro):
    # Un puerto reservado para un contenedor que ya no existe agota el rango de a poco, y
    # el síntoma aparece mucho después de la causa.
    reservado = registro.reservar("jafne-borr-x-front", 3000)
    assert registro.liberar("jafne-borr-x-front") == [reservado.puerto]
    assert registro.publicaciones() == []
    assert registro.reservar("jafne-otro-y-front", 3000).puerto == reservado.puerto


def test_liberar_no_toca_los_puertos_de_otros_contenedores(registro):
    mio = registro.reservar("jafne-borr-x-front", 3000)
    ajeno = registro.reservar("jafne-otro-y-front", 3000)
    registro.liberar("jafne-borr-x-front")
    assert [p.puerto for p in registro.publicaciones()] == [ajeno.puerto]
    assert mio.puerto not in [p.puerto for p in registro.publicaciones()]


def test_el_registro_sobrevive_a_un_reinicio(tmp_path):
    # Infraestructura es un proceso largo y se reinicia; los contenedores no se enteran.
    Registro(tmp_path).reservar("jafne-borr-x-front", 3000)
    assert len(Registro(tmp_path).publicaciones()) == 1


def test_un_archivo_corrupto_no_deja_a_infraestructura_sin_publicar(tmp_path):
    (tmp_path / "puertos.json").write_text("{ esto no es json", encoding="utf-8")
    assert Registro(tmp_path).reservar("jafne-borr-x-front", 3000).puerto == RANGO.start


def test_cuando_el_rango_se_agota_se_dice_con_el_rango(registro, monkeypatch):
    import jafne.nucleo.puertos as mod

    monkeypatch.setattr(mod, "RANGO", range(9000, 9002))
    registro.reservar("uno", 1)
    registro.reservar("dos", 2)
    with pytest.raises(SinPuertosLibres) as error:
        registro.reservar("tres", 3)
    assert "9000" in str(error.value) and "9001" in str(error.value)
