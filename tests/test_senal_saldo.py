"""La señal de saldo: proceder, conmutar o diferir (ADR-0026).

Lo que estos tests fijan no es el número sino la **forma** de la decisión: que las dos
ventanas no se colapsen en un booleano, y que lo que distingue conmutar de diferir sea el
horizonte de reset y no el nombre de la ventana.
"""

from datetime import datetime, timedelta, timezone

from jafne.nucleo.modelos import Suscripcion, Ventana
from jafne.nucleo.senal_saldo import (
    HORIZONTE_DE_ESPERA,
    UMBRAL,
    Senal,
    evaluar,
)

AHORA = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


def _suscripcion(*ventanas: Ventana) -> Suscripcion:
    return Suscripcion(proveedor="anthropic", ventanas=ventanas)


# ── proceder ─────────────────────────────────────────────────────────────────


def test_sin_saldo_observado_se_procede():
    # Desconocido no es escasez: frenar por falta de observación sería peor que el
    # problema que resuelve.
    assert evaluar(None, AHORA).senal is Senal.PROCEDER
    assert evaluar(_suscripcion(), AHORA).senal is Senal.PROCEDER


def test_una_ventana_sin_dato_no_cuenta_como_escasa():
    suscripcion = _suscripcion(Ventana(nombre="5h", restante=None))
    assert evaluar(suscripcion, AHORA).senal is Senal.PROCEDER


def test_con_saldo_de_sobra_se_procede():
    suscripcion = _suscripcion(
        Ventana(nombre="5h", restante=0.8, resetea=AHORA + timedelta(hours=2)),
        Ventana(nombre="semanal", restante=0.6, resetea=AHORA + timedelta(days=3)),
    )
    assert evaluar(suscripcion, AHORA).senal is Senal.PROCEDER


def test_justo_en_el_umbral_todavia_se_procede():
    # El umbral es estricto: se actúa por *debajo*, no al tocarlo.
    suscripcion = _suscripcion(
        Ventana(nombre="5h", restante=UMBRAL, resetea=AHORA + timedelta(hours=1))
    )
    assert evaluar(suscripcion, AHORA).senal is Senal.PROCEDER


# ── conmutar: el reset está lejos ────────────────────────────────────────────


def test_la_ventana_larga_hace_conmutar():
    suscripcion = _suscripcion(
        Ventana(nombre="semanal", restante=0.05, resetea=AHORA + timedelta(days=3))
    )
    decision = evaluar(suscripcion, AHORA)
    assert decision.senal is Senal.CONMUTAR
    assert decision.ventana == "semanal"
    # Conmutar no promete reanudación: cambia de proveedor, no espera.
    assert decision.reanudar is None


def test_una_ventana_escasa_sin_hora_de_reset_no_se_puede_esperar():
    # Sin `resetea` no hay reanudación que prometer, y diferir sin promesa es frenar.
    suscripcion = _suscripcion(Ventana(nombre="5h", restante=0.01, resetea=None))
    assert evaluar(suscripcion, AHORA).senal is Senal.CONMUTAR


def test_un_reset_ya_vencido_tampoco_sirve_para_esperar():
    # Dato viejo: la hora pasó y el saldo sigue bajo. Esperarla no destraba nada.
    suscripcion = _suscripcion(
        Ventana(nombre="5h", restante=0.02, resetea=AHORA - timedelta(minutes=5))
    )
    assert evaluar(suscripcion, AHORA).senal is Senal.CONMUTAR


def test_el_borde_del_horizonte_todavia_es_esperable():
    suscripcion = _suscripcion(
        Ventana(nombre="5h", restante=0.01, resetea=AHORA + HORIZONTE_DE_ESPERA)
    )
    assert evaluar(suscripcion, AHORA).senal is Senal.DIFERIR

    apenas_despues = _suscripcion(
        Ventana(
            nombre="5h",
            restante=0.01,
            resetea=AHORA + HORIZONTE_DE_ESPERA + timedelta(minutes=1),
        )
    )
    assert evaluar(apenas_despues, AHORA).senal is Senal.CONMUTAR


# ── diferir: el reset está cerca ─────────────────────────────────────────────


def test_la_ventana_corta_difiere_en_vez_de_conmutar():
    # El corazón de ADR-0026: esperar 40 minutos es más barato que invalidar el
    # contexto cacheado y partir un Asunto entre dos proveedores.
    reset = AHORA + timedelta(minutes=40)
    suscripcion = _suscripcion(Ventana(nombre="5h", restante=0.03, resetea=reset))
    decision = evaluar(suscripcion, AHORA)
    assert decision.senal is Senal.DIFERIR
    assert decision.reanudar == reset


def test_con_dos_ventanas_cortas_escasas_se_espera_a_la_ultima():
    # Recuperar una sola no alcanza: hay que esperar a que las dos estén por encima.
    pronto = AHORA + timedelta(minutes=20)
    despues = AHORA + timedelta(hours=2)
    suscripcion = _suscripcion(
        Ventana(nombre="rafaga", restante=0.05, resetea=pronto),
        Ventana(nombre="5h", restante=0.05, resetea=despues),
    )
    assert evaluar(suscripcion, AHORA).reanudar == despues


# ── precedencia ──────────────────────────────────────────────────────────────


def test_conmutar_gana_sobre_diferir():
    # Si las dos condiciones se dan, esperar no arregla la ventana larga.
    suscripcion = _suscripcion(
        Ventana(nombre="5h", restante=0.05, resetea=AHORA + timedelta(minutes=30)),
        Ventana(nombre="semanal", restante=0.05, resetea=AHORA + timedelta(days=4)),
    )
    decision = evaluar(suscripcion, AHORA)
    assert decision.senal is Senal.CONMUTAR
    assert decision.ventana == "semanal"


def test_el_nombre_de_la_ventana_no_decide_nada():
    # Lo que clasifica es el horizonte, no el vocabulario del proveedor: una ventana
    # llamada 'semanal' que resetea en una hora se espera igual.
    suscripcion = _suscripcion(
        Ventana(nombre="semanal", restante=0.05, resetea=AHORA + timedelta(hours=1))
    )
    assert evaluar(suscripcion, AHORA).senal is Senal.DIFERIR


def test_la_decision_se_serializa_para_el_panel():
    reset = AHORA + timedelta(minutes=30)
    suscripcion = _suscripcion(Ventana(nombre="5h", restante=0.05, resetea=reset))
    datos = evaluar(suscripcion, AHORA).a_dict()
    assert datos["senal"] == "diferir"
    assert datos["reanudar"] == reset.isoformat()
    assert datos["ventana"] == "5h"
