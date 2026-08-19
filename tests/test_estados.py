"""Los dos catálogos cerrados y sus máquinas de estados (ADR-0009, ADR-0016, ADR-0017)."""

from datetime import datetime, timedelta, timezone

import pytest

from jafne.nucleo.estados import (
    TIMEOUT_SIN_RESPUESTA,
    EstadoAsunto,
    EstadoContenedor,
    EstadoDesconocido,
    TransicionInvalida,
    estado_efectivo,
    parsear,
    parsear_contenedor,
    transicion_valida,
    validar_transicion,
    validar_transicion_contenedor,
)

AHORA = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


# ── estado_asunto (ADR-0009) ─────────────────────────────────────────────────


def test_el_catalogo_de_asunto_tiene_exactamente_los_cinco_valores_del_adr():
    assert [e.value for e in EstadoAsunto] == [
        "iniciando",
        "interactuando_con_el_usuario",
        "esperando_respuesta",
        "cerrando",
        "cerrado",
    ]


def test_un_estado_de_asunto_fuera_del_catalogo_no_se_acepta():
    with pytest.raises(EstadoDesconocido):
        parsear("trabajando")  # del catálogo original, descartado en ADR-0009


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoAsunto.INICIANDO, EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO),
        (EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO, EstadoAsunto.ESPERANDO_RESPUESTA),
        (EstadoAsunto.ESPERANDO_RESPUESTA, EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO),
        (EstadoAsunto.ESPERANDO_RESPUESTA, EstadoAsunto.CERRANDO),
        (EstadoAsunto.CERRANDO, EstadoAsunto.CERRADO),
        (EstadoAsunto.CERRANDO, EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO),
        (EstadoAsunto.CERRADO, EstadoAsunto.INICIANDO),
    ],
)
def test_transiciones_del_diagrama_de_asunto(desde, hacia):
    assert transicion_valida(desde, hacia)


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoAsunto.INICIANDO, EstadoAsunto.CERRADO),
        (EstadoAsunto.INICIANDO, EstadoAsunto.ESPERANDO_RESPUESTA),
        (EstadoAsunto.CERRADO, EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO),
        (EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO, EstadoAsunto.CERRADO),
    ],
)
def test_los_saltos_de_asunto_que_el_diagrama_no_tiene_se_rechazan(desde, hacia):
    with pytest.raises(TransicionInvalida):
        validar_transicion(desde, hacia)


# ── estado_contenedor (ADR-0016) ─────────────────────────────────────────────


def test_el_catalogo_de_contenedor_tiene_exactamente_los_cuatro_valores_del_adr():
    assert [e.value for e in EstadoContenedor] == [
        "creando",
        "activo",
        "suspendido",
        "destruido",
    ]


def test_un_estado_de_contenedor_fuera_del_catalogo_no_se_acepta():
    with pytest.raises(EstadoDesconocido):
        parsear_contenedor("pausado")


def test_sin_estado_de_contenedor_significa_que_nunca_tuvo_workspace():
    assert parsear_contenedor(None) is None


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (None, EstadoContenedor.CREANDO),
        (EstadoContenedor.CREANDO, EstadoContenedor.ACTIVO),
        (EstadoContenedor.ACTIVO, EstadoContenedor.SUSPENDIDO),
        (EstadoContenedor.SUSPENDIDO, EstadoContenedor.ACTIVO),
        (EstadoContenedor.ACTIVO, EstadoContenedor.DESTRUIDO),
        (EstadoContenedor.SUSPENDIDO, EstadoContenedor.DESTRUIDO),
        (EstadoContenedor.DESTRUIDO, EstadoContenedor.CREANDO),
    ],
)
def test_transiciones_del_diagrama_de_contenedor(desde, hacia):
    validar_transicion_contenedor(desde, hacia)


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (None, EstadoContenedor.ACTIVO),
        (EstadoContenedor.CREANDO, EstadoContenedor.DESTRUIDO),
        (EstadoContenedor.DESTRUIDO, EstadoContenedor.ACTIVO),
    ],
)
def test_los_saltos_de_contenedor_que_el_diagrama_no_tiene_se_rechazan(desde, hacia):
    with pytest.raises(TransicionInvalida):
        validar_transicion_contenedor(desde, hacia)


# ── timeout derivado (ADR-0017) ──────────────────────────────────────────────


def test_el_timeout_mueve_a_esperando_respuesta_si_hay_pregunta_pendiente():
    hace_rato = AHORA - TIMEOUT_SIN_RESPUESTA - timedelta(seconds=1)
    assert (
        estado_efectivo(
            EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO,
            hace_rato,
            pregunta_pendiente=True,
            ahora=AHORA,
        )
        is EstadoAsunto.ESPERANDO_RESPUESTA
    )


def test_sin_pregunta_pendiente_el_silencio_no_dispara_el_timeout():
    # Un Asunto trabajando en background (modo delegado, ADR-0002) puede pasar horas
    # sin actividad visible sin estar esperando al Usuario.
    hace_mucho = AHORA - timedelta(hours=6)
    assert (
        estado_efectivo(
            EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO,
            hace_mucho,
            pregunta_pendiente=False,
            ahora=AHORA,
        )
        is EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO
    )


def test_dentro_de_los_tres_minutos_sigue_interactuando():
    recien = AHORA - timedelta(seconds=30)
    assert (
        estado_efectivo(
            EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO,
            recien,
            pregunta_pendiente=True,
            ahora=AHORA,
        )
        is EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO
    )


@pytest.mark.parametrize(
    "estado",
    [EstadoAsunto.INICIANDO, EstadoAsunto.CERRANDO, EstadoAsunto.CERRADO],
)
def test_el_timeout_solo_aplica_desde_interactuando(estado):
    viejo = AHORA - timedelta(days=3)
    assert (
        estado_efectivo(estado, viejo, pregunta_pendiente=True, ahora=AHORA) is estado
    )
