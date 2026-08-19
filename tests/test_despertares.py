"""La cola de despertares: cadencias y diferimientos en una sola cola (ADR-0035).

Lo que fijan estos tests no es el calendario sino la **forma**: que la cola sea función
del tiempo y no del reloj del sistema, que los dos productores entren en la misma cola
ordenada, y que una cadencia que JAFNE no entiende se rechace en vez de quedar muda.
"""

from datetime import datetime, time, timedelta, timezone

import pytest

from jafne.nucleo.despertares import (
    Cadencia,
    CadenciaInvalida,
    Origen,
    Periodo,
    TrabajoProgramado,
    cola,
    id_de_asunto,
    parsear_cadencia,
    proximo,
)
from jafne.nucleo.modelos import Suscripcion, Ventana

#: Un martes a las 12:00, para que ningún test dependa de "hoy".
MARTES = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)


def _trabajo(cadencia: str, **kwargs) -> TrabajoProgramado:
    datos = {
        "id": "sprint-semanal",
        "skill": "armar-sprint",
        "proyecto": "borr",
        **kwargs,
    }
    return TrabajoProgramado(cadencia=parsear_cadencia(cadencia), **datos)


# ── el vocabulario cerrado de cadencias (ADR-0035) ───────────────────────────


def test_una_cadencia_diaria_se_parsea_con_su_hora():
    cadencia = parsear_cadencia("diaria 08:00")
    assert cadencia.periodo is Periodo.DIARIA
    assert cadencia.hora == time(8, 0)
    assert cadencia.dia is None


def test_una_cadencia_semanal_se_parsea_con_su_dia():
    cadencia = parsear_cadencia("semanal lunes 08:00")
    assert cadencia.periodo is Periodo.SEMANAL
    assert cadencia.dia == 0  # lunes, igual que datetime.weekday()


def test_el_dia_se_acepta_con_tilde_o_sin_ella():
    # Quien escribe el YAML no tiene por qué acordarse de cómo lo normaliza JAFNE.
    assert parsear_cadencia("semanal miércoles 09:30") == parsear_cadencia(
        "semanal miercoles 09:30"
    )


def test_una_cadencia_fuera_del_catalogo_se_rechaza():
    # ADR-0035: una entrada que se ignora en silencio no falla, simplemente nunca
    # dispara — y nadie se entera hasta que pregunta por qué no se armó el sprint.
    with pytest.raises(CadenciaInvalida):
        parsear_cadencia("cada dos jueves")


def test_una_cadencia_mensual_todavia_no_esta_en_el_catalogo():
    # El catálogo es cerrado a propósito: se amplía decidiendo, no adivinando.
    with pytest.raises(CadenciaInvalida):
        parsear_cadencia("mensual 1 08:00")


def test_un_dia_que_no_existe_se_rechaza_nombrando_el_catalogo():
    with pytest.raises(CadenciaInvalida) as error:
        parsear_cadencia("semanal lunez 08:00")
    assert "domingo" in str(error.value)


def test_una_hora_imposible_se_rechaza():
    with pytest.raises(CadenciaInvalida):
        parsear_cadencia("diaria 25:00")


def test_una_cadencia_vacia_recuerda_las_tres_cosas_de_adr_0024():
    with pytest.raises(CadenciaInvalida) as error:
        parsear_cadencia("")
    assert "skill" in str(error.value)


# ── el próximo disparo, como función del tiempo ──────────────────────────────


def test_la_diaria_de_mas_tarde_dispara_hoy():
    cadencia = parsear_cadencia("diaria 18:00")
    assert cadencia.proximo(MARTES) == MARTES.replace(hour=18, minute=0)


def test_la_diaria_ya_pasada_dispara_manana():
    cadencia = parsear_cadencia("diaria 08:00")
    assert cadencia.proximo(MARTES) == MARTES.replace(hour=8) + timedelta(days=1)


def test_la_hora_exacta_no_se_vuelve_a_elegir():
    # Estrictamente posterior: si no, el reloj que acaba de disparar a las 12:00 elegiría
    # las 12:00 de hoy otra vez y giraría en falso.
    cadencia = parsear_cadencia("diaria 12:00")
    assert cadencia.proximo(MARTES) == MARTES + timedelta(days=1)


def test_la_semanal_espera_al_dia_declarado():
    # Del martes al lunes que viene hay seis días.
    cadencia = parsear_cadencia("semanal lunes 08:00")
    esperado = (MARTES + timedelta(days=6)).replace(hour=8, minute=0)
    assert cadencia.proximo(MARTES) == esperado


def test_la_semanal_del_mismo_dia_mas_tarde_dispara_hoy():
    cadencia = parsear_cadencia("semanal martes 18:00")
    assert cadencia.proximo(MARTES) == MARTES.replace(hour=18)


def test_la_semanal_del_mismo_dia_ya_pasada_salta_una_semana_entera():
    cadencia = parsear_cadencia("semanal martes 08:00")
    esperado = (MARTES + timedelta(days=7)).replace(hour=8)
    assert cadencia.proximo(MARTES) == esperado


def test_la_cadencia_se_interpreta_en_la_zona_de_quien_pregunta():
    # ADR-0035: "lunes 08:00" es el lunes del Usuario, no UTC. La zona la trae `desde`,
    # que es lo que mantiene a la función determinista.
    montevideo = timezone(timedelta(hours=-3))
    desde = MARTES.astimezone(montevideo)
    siguiente = parsear_cadencia("diaria 08:00").proximo(desde)
    assert siguiente.utcoffset() == timedelta(hours=-3)
    assert siguiente.hour == 8


def test_el_texto_de_la_cadencia_vuelve_a_como_se_declara():
    # Es lo que el reloj anota en el historial del Asunto y lo que el panel muestra.
    assert parsear_cadencia("semanal lunes 8:00").texto == "semanal lunes 08:00"
    assert parsear_cadencia("diaria 18:05").texto == "diaria 18:05"


# ── una sola cola, dos productores (ADR-0035) ────────────────────────────────


def test_la_cola_sale_ordenada_por_momento():
    trabajos = [
        _trabajo("diaria 18:00", id="repaso-diario"),
        _trabajo("diaria 13:00", id="repaso-temprano"),
    ]
    momentos = [d.momento for d in cola(trabajos, desde=MARTES)]
    assert momentos == sorted(momentos)
    assert momentos[0].hour == 13


def test_un_diferimiento_por_cupo_entra_en_la_misma_cola():
    # ADR-0035 re-declara lo que ADR-0029 acertó: son el mismo mecanismo —despertar en el
    # instante T y hacer X—, así que es una cola, no dos.
    reset = MARTES + timedelta(hours=2)
    suscripciones = {
        "anthropic": Suscripcion(
            proveedor="anthropic",
            ventanas=(Ventana(nombre="5h", restante=0.05, resetea=reset),),
        )
    }
    pendientes = cola([_trabajo("diaria 18:00")], suscripciones, desde=MARTES)
    origenes = [d.origen for d in pendientes]
    assert origenes == [Origen.DIFERIMIENTO, Origen.CADENCIA]
    assert pendientes[0].momento == reset
    assert pendientes[0].proveedor == "anthropic"


def test_el_diferimiento_no_se_declara_sale_del_saldo_que_ya_existe():
    # ADR-0035: un diferimiento no agrega estado, agrega una razón para volver a mirar.
    reset = MARTES + timedelta(hours=1)
    suscripciones = {
        "anthropic": Suscripcion(
            proveedor="anthropic",
            ventanas=(Ventana(nombre="5h", restante=0.01, resetea=reset),),
        )
    }
    assert [d.momento for d in cola([], suscripciones, desde=MARTES)] == [reset]


def test_conmutar_no_encola_nada():
    # Conmutar de proveedor se resuelve al elegir cerebro, no esperando: una ventana que
    # resetea lejos no produce un despertar (ADR-0026).
    suscripciones = {
        "anthropic": Suscripcion(
            proveedor="anthropic",
            ventanas=(
                Ventana(nombre="semanal", restante=0.05, resetea=MARTES + timedelta(days=3)),
            ),
        )
    }
    assert cola([], suscripciones, desde=MARTES) == []


def test_un_proveedor_con_saldo_de_sobra_no_encola_nada():
    suscripciones = {
        "anthropic": Suscripcion(
            proveedor="anthropic",
            ventanas=(Ventana(nombre="5h", restante=0.9, resetea=MARTES + timedelta(hours=1)),),
        )
    }
    assert cola([], suscripciones, desde=MARTES) == []


def test_sin_nada_declarado_la_cola_esta_vacia():
    assert cola([], {}, desde=MARTES) == []
    assert proximo([], {}, desde=MARTES) is None


def test_la_cola_exige_un_instante_con_zona_horaria():
    # Sin zona no se puede ni interpretar la cadencia ni comparar contra el `resetea` de
    # saldo.yaml, que viene en UTC.
    with pytest.raises(ValueError):
        cola([_trabajo("diaria 08:00")], {}, desde=datetime(2026, 8, 18, 12, 0))


def test_el_motivo_dice_que_trabajo_y_que_proyecto():
    # El reloj corre de noche: el motivo es lo que después explica por qué hay un Asunto.
    despertar = proximo([_trabajo("diaria 18:00")], {}, desde=MARTES)
    assert "sprint-semanal" in despertar.motivo
    assert "borr" in despertar.motivo
    assert despertar.trabajo.skill == "armar-sprint"


# ── el id derivado del Asunto (ADR-0035) ─────────────────────────────────────


def test_el_id_del_asunto_sale_de_la_entrada_y_la_fecha():
    trabajo = _trabajo("semanal lunes 08:00")
    assert id_de_asunto(trabajo, MARTES) == "sprint-semanal-2026-08-18"


def test_dos_disparos_de_la_misma_fecha_dan_el_mismo_id():
    # Es la mitad de cómo ADR-0035 evita duplicados: dos relojes intentan abrir el mismo
    # Asunto y el segundo choca con el que ya existe, en vez de abrir uno gemelo.
    trabajo = _trabajo("diaria 08:00")
    temprano = MARTES.replace(hour=8)
    tarde = MARTES.replace(hour=8, minute=30)
    assert id_de_asunto(trabajo, temprano) == id_de_asunto(trabajo, tarde)


def test_dos_dias_distintos_dan_ids_distintos():
    trabajo = _trabajo("diaria 08:00")
    assert id_de_asunto(trabajo, MARTES) != id_de_asunto(trabajo, MARTES + timedelta(days=1))


def test_una_cadencia_construida_a_mano_tambien_sirve():
    # La cola no depende del parser: se puede armar el trabajo desde código.
    cadencia = Cadencia(periodo=Periodo.DIARIA, hora=time(7, 15))
    trabajo = TrabajoProgramado(
        id="tarea", skill="revisar", cadencia=cadencia, proyecto="borr"
    )
    assert proximo([trabajo], {}, desde=MARTES).momento.hour == 7
