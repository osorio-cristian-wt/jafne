"""El reloj: el proceso que consume la cola de despertares (ADR-0035).

`test_despertares.py` verifica *qué* hay que despertar y cuándo; acá se verifica lo que
pasa cuando ese instante llega — que abra un Asunto normal (ADR-0024), que no lo duplique,
que no reponga lo vencido y que no deje correr dos relojes sobre el mismo almacén.

El reloj se prueba sin dormir ni un segundo: `ahora` y `dormir` se inyectan, igual que
`senal_saldo.evaluar` recibe el instante en vez de leer el reloj del sistema.
"""

from datetime import datetime, timedelta, timezone

import pytest
import yaml

from jafne.nucleo import EstadoAsunto
from jafne.nucleo.despertares import (
    CadenciaInvalida,
    Despertar,
    Origen,
    TrabajoInvalido,
)
from jafne.reloj import Reloj, RelojYaCorriendo, candado

#: Un martes a las 12:00 en hora local: la cadencia se interpreta en la zona del Usuario.
LOCAL = timezone(timedelta(hours=-3))
MARTES = datetime(2026, 8, 18, 12, 0, tzinfo=LOCAL)


class RelojFalso:
    """Un reloj de mentira: dormir no espera, adelanta la hora."""

    def __init__(self, inicio: datetime) -> None:
        self.momento = inicio
        self.dormidas: list[float] = []

    def ahora(self) -> datetime:
        return self.momento

    def dormir(self, segundos: float) -> None:
        self.dormidas.append(segundos)
        self.momento += timedelta(seconds=segundos)


def _declarar(almacen, **trabajos) -> None:
    """Escribe `programado.yaml` con las entradas que pida el test."""
    almacen.ruta_programado.write_text(
        yaml.safe_dump({"trabajos": trabajos}, allow_unicode=True), encoding="utf-8"
    )


def _sprint_semanal(cadencia: str = "diaria 18:00") -> dict:
    return {"skill": "armar-sprint", "cadencia": cadencia, "proyecto": "borr"}


def _reloj(almacen, inicio: datetime = MARTES) -> tuple[Reloj, RelojFalso]:
    falso = RelojFalso(inicio)
    return Reloj(almacen, ahora=falso.ahora, dormir=falso.dormir), falso


# ── programado.yaml: las tres cosas de ADR-0024 ──────────────────────────────


def test_init_crea_programado_yaml(tmp_path):
    from jafne.nucleo import Almacen

    alm = Almacen(tmp_path / "jafne")
    alm.inicializar()
    assert alm.ruta_programado.is_file()
    assert alm.programados() == []  # existe y está vacío, que no es lo mismo que faltar


def test_un_trabajo_declarado_trae_skill_cadencia_y_proyecto(almacen):
    _declarar(almacen, **{"sprint-semanal": _sprint_semanal("semanal lunes 08:00")})
    (trabajo,) = almacen.programados()
    assert trabajo.id == "sprint-semanal"
    assert trabajo.skill == "armar-sprint"
    assert trabajo.proyecto == "borr"
    assert trabajo.cadencia.texto == "semanal lunes 08:00"


def test_un_trabajo_sin_skill_se_rechaza_al_leer(almacen):
    # ADR-0024 pide las tres cosas. Con dos, la entrada no es programable.
    _declarar(almacen, incompleto={"cadencia": "diaria 08:00", "proyecto": "borr"})
    with pytest.raises(TrabajoInvalido) as error:
        almacen.programados()
    assert "skill" in str(error.value)


def test_un_trabajo_sin_proyecto_se_rechaza_al_leer(almacen):
    _declarar(almacen, incompleto={"skill": "armar-sprint", "cadencia": "diaria 08:00"})
    with pytest.raises(TrabajoInvalido):
        almacen.programados()


def test_una_cadencia_ilegible_se_rechaza_en_vez_de_ignorarse(almacen):
    # Al revés que el saldo, que se degrada a "no observado": una cadencia degradada a
    # nada nunca dispararía, en silencio (ADR-0035).
    _declarar(almacen, raro={**_sprint_semanal(), "cadencia": "cuando pinte"})
    with pytest.raises(CadenciaInvalida):
        almacen.programados()


def test_un_id_de_trabajo_demasiado_largo_se_rechaza_al_declararlo(almacen):
    # Se choca al declarar y no medio año después, cuando el reloj intente abrir un
    # Asunto de 70 caracteres a las 3 AM.
    _declarar(almacen, **{"x" * 60: _sprint_semanal()})
    with pytest.raises(TrabajoInvalido) as error:
        almacen.programados()
    assert "largo" in str(error.value)


# ── disparar una cadencia: abre un Asunto normal (ADR-0024) ──────────────────


def test_al_dispararse_una_cadencia_abre_un_asunto_normal(almacen):
    _declarar(almacen, **{"sprint-semanal": _sprint_semanal()})
    reloj, falso = _reloj(almacen)

    (disparo,) = reloj.correr(vueltas=1)

    assert disparo.hecho
    asunto = almacen.asunto("borr", "sprint-semanal-2026-08-18")
    # ADR-0024: no hay una segunda clase de Asunto. Arranca en `iniciando` como cualquiera.
    assert asunto.estado_asunto is EstadoAsunto.INICIANDO


def test_el_reloj_espera_hasta_la_hora_declarada(almacen):
    _declarar(almacen, **{"sprint-semanal": _sprint_semanal("diaria 18:00")})
    reloj, falso = _reloj(almacen)

    reloj.correr(vueltas=1)

    # De las 12:00 a las 18:00 hay seis horas, y las durmió de una sola vez.
    assert falso.dormidas == [6 * 3600]


def test_el_asunto_queda_anotado_con_que_skill_falta_correr(almacen):
    # ADR-0035: correr la skill necesita el adaptador, así que el Asunto queda abierto con
    # el pedido visible en vez de simular que el trabajo se hizo.
    _declarar(almacen, **{"sprint-semanal": _sprint_semanal()})
    reloj, _ = _reloj(almacen)
    reloj.correr(vueltas=1)

    (mensaje,) = almacen.historial("borr", "sprint-semanal-2026-08-18")
    assert mensaje.rol == "sistema"
    assert "armar-sprint" in mensaje.texto
    assert "ADR-0028" in mensaje.texto


def test_el_mismo_despertar_no_abre_dos_asuntos(almacen):
    # El id derivado de la entrada y la fecha (ADR-0035): el segundo intento choca con el
    # Asunto que ya existe en vez de abrir uno gemelo.
    _declarar(almacen, **{"sprint-semanal": _sprint_semanal()})
    reloj, _ = _reloj(almacen)
    despertar = reloj.cola(MARTES)[0]

    primero = reloj.disparar(despertar)
    segundo = reloj.disparar(despertar)

    assert primero.hecho and not segundo.hecho
    assert "ya existía" in segundo.detalle
    assert len(almacen.asuntos("borr")) == 3  # los dos del fixture + el del reloj


def test_dos_dias_seguidos_abren_dos_asuntos_distintos(almacen):
    _declarar(almacen, **{"repaso": {**_sprint_semanal(), "cadencia": "diaria 18:00"}})
    reloj, _ = _reloj(almacen)

    reloj.correr(vueltas=2)

    assert almacen.asunto("borr", "repaso-2026-08-18")
    assert almacen.asunto("borr", "repaso-2026-08-19")


def test_una_cadencia_a_un_proyecto_inexistente_no_abre_nada(almacen):
    _declarar(almacen, **{"huerfano": {**_sprint_semanal(), "proyecto": "inexistente"}})
    reloj, _ = _reloj(almacen)

    (disparo,) = reloj.correr(vueltas=1)

    assert not disparo.hecho
    assert "proyectos.yaml" in disparo.detalle
    assert almacen.asuntos("inexistente") == []


# ── un despertar vencido no se repone (ADR-0035) ─────────────────────────────


def test_lo_que_toco_mientras_el_reloj_estaba_caido_no_se_dispara(almacen):
    # Reponer una cadencia diaria caída dos días abriría dos Asuntos iguales de golpe, y
    # un Asunto programado no puede consultar al Usuario (ADR-0024).
    _declarar(almacen, **{"repaso": {**_sprint_semanal(), "cadencia": "diaria 08:00"}})
    jueves = MARTES + timedelta(days=2)  # las 08:00 del martes, miércoles y jueves ya pasaron
    reloj, _ = _reloj(almacen, inicio=jueves)

    (disparo,) = reloj.correr(vueltas=1)

    assert disparo.asunto == "repaso-2026-08-21"  # el viernes, el próximo de verdad
    assert [a.id for a in almacen.asuntos("borr") if a.id.startswith("repaso")] == [
        "repaso-2026-08-21"
    ]


# ── el segundo productor: diferimiento por cupo (ADR-0026) ───────────────────


def test_un_diferimiento_despierta_pero_todavia_no_puede_retomar(almacen):
    # El reloj ya es "quien despierta", que era lo que faltaba. Retomar el trabajo
    # necesita el adaptador, y eso se informa en vez de aparentarse.
    almacen.registrar_saldo(
        "anthropic", "5h", 0.02, resetea=(MARTES + timedelta(hours=2)).astimezone(timezone.utc)
    )
    reloj, _ = _reloj(almacen)

    (disparo,) = reloj.correr(vueltas=1)

    assert disparo.despertar.origen is Origen.DIFERIMIENTO
    assert not disparo.hecho
    assert "adaptador" in disparo.detalle


def test_sin_nada_agendado_el_reloj_espera_y_no_dispara(almacen):
    reloj, falso = _reloj(almacen)
    assert reloj.correr(vueltas=2) == []
    assert falso.dormidas == [15 * 60, 15 * 60]  # el intervalo ocioso, dos veces


def test_un_despertar_de_cadencia_sin_trabajo_es_un_error_de_programacion(almacen):
    reloj, _ = _reloj(almacen)
    suelto = Despertar(momento=MARTES, origen=Origen.CADENCIA, motivo="a mano")
    with pytest.raises(ValueError):
        reloj.disparar(suelto)


# ── un solo reloj por almacén (ADR-0035) ─────────────────────────────────────


def test_dos_relojes_sobre_el_mismo_almacen_no_conviven(almacen):
    with candado(almacen):
        with pytest.raises(RelojYaCorriendo) as error:
            with candado(almacen):
                pass
    assert "dos veces" in str(error.value)


def test_el_candado_se_suelta_al_terminar(almacen):
    with candado(almacen) as ruta:
        assert ruta.is_file()
    assert not ruta.exists()


def test_el_candado_se_suelta_aunque_el_reloj_reviente(almacen):
    # Si no, el próximo arranque queda bloqueado por un reloj que ya no existe.
    with pytest.raises(ZeroDivisionError):
        with candado(almacen) as ruta:
            1 / 0
    assert not ruta.exists()
