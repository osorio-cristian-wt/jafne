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
    por_que_no_avanza,
    resumir_contenedores,
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


# ── por qué un Asunto está parado (derivado, no persistido) ──────────────────


def test_un_asunto_sin_agentes_delegados_dice_que_eso_es_normal():
    # Desde ADR-0047 los contenedores nacen al delegar, no al abrir. Un Asunto recién
    # abierto sin contenedores no es un síntoma, y el panel tiene que decirlo así.
    motivo = por_que_no_avanza(EstadoAsunto.INICIANDO, None)
    assert "todavía no delegó" in motivo
    assert "ADR-0047" in motivo


def test_un_asunto_que_no_esta_en_iniciando_no_tiene_nada_que_explicar():
    # Solo `iniciando` es un estado donde quedarse parado es ambiguo. En los demás el
    # estado ya se explica solo, y agregar texto sería ruido.
    assert por_que_no_avanza(EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO, None) is None


def test_un_asunto_con_los_contenedores_destruidos_pide_volver_a_delegar():
    # ADR-0018: reabrir conserva el historial pero deja los contenedores destruidos. Sin
    # el aviso, parece el mismo cuelgue que el caso anterior.
    motivo = por_que_no_avanza(EstadoAsunto.INICIANDO, EstadoContenedor.DESTRUIDO)
    assert "volver a delegar" in motivo


def test_un_asunto_con_el_workspace_activo_señala_al_encargado():
    # Acá la infraestructura hizo su parte: lo que falta es el primer turno.
    motivo = por_que_no_avanza(EstadoAsunto.INICIANDO, EstadoContenedor.ACTIVO)
    assert "Encargado" in motivo


# ── el resumen de los contenedores de un Asunto (ADR-0047) ───────────────────


def test_un_asunto_sin_agentes_no_tiene_estado_de_contenedor():
    # Sigue significando "nunca tuvo" y no `destruido`, como fijó ADR-0016.
    assert resumir_contenedores([]) is None
    assert resumir_contenedores([None, None]) is None


def test_basta_un_contenedor_en_pie_para_que_el_asunto_este_activo():
    # Con uno activo el Asunto tiene dónde trabajar, así que `activo` gana sobre los demás.
    assert (
        resumir_contenedores([EstadoContenedor.SUSPENDIDO, EstadoContenedor.ACTIVO])
        is EstadoContenedor.ACTIVO
    )


def test_con_todos_dormidos_el_asunto_figura_suspendido():
    assert (
        resumir_contenedores([EstadoContenedor.SUSPENDIDO, EstadoContenedor.SUSPENDIDO])
        is EstadoContenedor.SUSPENDIDO
    )


def test_con_todos_destruidos_el_asunto_figura_destruido():
    # Distinto de `None`: acá hubo contenedores y se liberaron.
    assert (
        resumir_contenedores([EstadoContenedor.DESTRUIDO, EstadoContenedor.DESTRUIDO])
        is EstadoContenedor.DESTRUIDO
    )
