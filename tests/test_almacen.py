"""El almacén `~/.jafne/` (ADR-0007), su historial (ADR-0018) y sus dos ejes de estado."""

from datetime import datetime, timedelta, timezone

import pytest
import yaml

from jafne.nucleo import Almacen, EstadoAsunto, EstadoContenedor
from jafne.nucleo.almacen import (
    AlmacenNoInicializado,
    AsuntoDesconocido,
    IdInvalido,
    ProyectoDesconocido,
    SaldoInvalido,
)
from jafne.nucleo.estados import TIMEOUT_SIN_RESPUESTA, TransicionInvalida
from jafne.nucleo.tamanos import ORDEN, Tamano, TamanoInvalido


def test_init_crea_la_estructura_del_adr_0007(tmp_path):
    alm = Almacen(tmp_path / "jafne")
    assert not alm.existe
    alm.inicializar()
    assert alm.ruta_proyectos.is_file()
    assert alm.ruta_cerebros.is_file()
    assert alm.ruta_saldo.is_file()
    assert alm.ruta_programado.is_file()
    assert alm.ruta_asuntos.is_dir()


def test_init_no_pisa_lo_que_ya_existe(tmp_path):
    alm = Almacen(tmp_path / "jafne")
    alm.inicializar()
    alm.ruta_proyectos.write_text("proyectos: {mio: {nombre: Mío}}", encoding="utf-8")
    alm.inicializar()
    assert [p.id for p in alm.proyectos()] == ["mio"]


def test_los_cerebros_de_fabrica_usan_el_catalogo_comun_de_tamanos(tmp_path):
    alm = Almacen(tmp_path / "jafne")
    alm.inicializar()
    por_id = {c.id: c for c in alm.cerebros()}
    # El mismo tamaño cruza proveedores, que es la razón de ser de ADR-0030.
    assert por_id["openai-sol"].tamano is Tamano.GRANDE
    assert por_id["claude-opus"].tamano is Tamano.GRANDE
    assert por_id["openai-tierra"].tamano is por_id["claude-sonnet"].tamano is Tamano.MEDIO
    assert por_id["openai-luna"].tamano is Tamano.CHICO
    # El orden interno de ADR-0022 sobrevive traducido: Sol > Tierra > Luna.
    assert [ORDEN.index(por_id[f"openai-{n}"].tamano) for n in ("sol", "tierra", "luna")] == [2, 1, 0]
    assert {c.proveedor for c in alm.cerebros()} == {"anthropic", "openai"}


def test_gigante_existe_de_un_solo_lado_y_eso_es_un_dato(tmp_path):
    alm = Almacen(tmp_path / "jafne")
    alm.inicializar()
    por_tamano = {}
    for cerebro in alm.cerebros():
        por_tamano.setdefault(cerebro.tamano, set()).add(cerebro.proveedor)
    # ADR-0030: un proveedor no cubre necesariamente todos los tamaños.
    assert por_tamano[Tamano.GIGANTE] == {"anthropic"}
    assert por_tamano[Tamano.GRANDE] == {"anthropic", "openai"}


def test_el_vocabulario_viejo_de_tier_se_traduce_al_leer(tmp_path):
    alm = Almacen(tmp_path / "jafne")
    alm.inicializar()
    # Un ~/.jafne/ escrito antes de ADR-0030 no se rompe: se traduce.
    alm.ruta_cerebros.write_text(
        "cerebros:\n  viejo:\n    proveedor: openai\n    tier: pesado\n", encoding="utf-8"
    )
    assert alm.cerebros()[0].tamano is Tamano.GRANDE


def test_un_tamano_fuera_del_catalogo_se_rechaza_al_leer(tmp_path):
    alm = Almacen(tmp_path / "jafne")
    alm.inicializar()
    alm.ruta_cerebros.write_text(
        "cerebros:\n  raro:\n    proveedor: openai\n    tamano: enorme\n", encoding="utf-8"
    )
    with pytest.raises(TamanoInvalido):
        alm.cerebros()


def test_los_cerebros_sin_adaptador_se_listan_igual(tmp_path):
    alm = Almacen(tmp_path / "jafne")
    alm.inicializar()
    por_id = {c.id: c for c in alm.cerebros()}
    # ADR-0028: uno visible que falla al usarse informa; uno ausente miente por omisión.
    assert por_id["claude-opus"].adaptador is True
    assert por_id["openai-sol"].adaptador is False


def test_lee_proyectos_y_asuntos(almacen):
    assert [p.id for p in almacen.proyectos()] == ["borr", "casa-justina"]
    assert [a.id for a in almacen.asuntos("borr")] == ["migrar-bff", "rediseno-panel"]
    assert almacen.asuntos("casa-justina") == []


def test_el_asistente_ve_los_asuntos_de_todos_los_proyectos(almacen):
    almacen.abrir_asunto("casa-justina", "revisar-docs")
    assert {(a.proyecto, a.id) for a in almacen.asuntos()} == {
        ("borr", "migrar-bff"),
        ("borr", "rediseno-panel"),
        ("casa-justina", "revisar-docs"),
    }


def test_un_asunto_nuevo_arranca_en_iniciando_sin_contenedor(almacen):
    asunto = almacen.abrir_asunto("borr", "nuevo-tema")
    assert asunto.estado_asunto is EstadoAsunto.INICIANDO
    # Nunca tuvo Workspace, que no es lo mismo que tenerlo destruido (ADR-0016).
    assert asunto.estado_contenedor is None
    assert asunto.pregunta_pendiente is False


def test_no_se_reabre_un_asunto_existente_como_si_fuera_nuevo(almacen):
    with pytest.raises(FileExistsError):
        almacen.abrir_asunto("borr", "migrar-bff")


def test_actualizar_estado_persiste_en_meta_yaml(almacen):
    almacen.actualizar_estado("borr", "rediseno-panel", "cerrando", motivo="cerramos")
    meta = yaml.safe_load(
        (almacen.ruta_asunto("borr", "rediseno-panel") / "meta.yaml").read_text("utf-8")
    )
    assert meta["estado_asunto"] == "cerrando"
    assert meta["motivo"] == "cerramos"


def test_actualizar_estado_valida_contra_el_diagrama(almacen):
    with pytest.raises(TransicionInvalida):
        almacen.actualizar_estado("borr", "migrar-bff", "cerrado")


# ── estado_contenedor (ADR-0016) ─────────────────────────────────────────────


def test_el_estado_de_contenedor_valida_su_catalogo_y_su_diagrama(almacen):
    almacen.actualizar_contenedor("borr", "migrar-bff", "creando")
    asunto = almacen.actualizar_contenedor("borr", "migrar-bff", "activo")
    assert asunto.estado_contenedor is EstadoContenedor.ACTIVO
    # Los dos ejes son independientes: mover el contenedor no toca el Asunto (ADR-0008).
    assert asunto.estado_asunto is EstadoAsunto.INICIANDO

    with pytest.raises(TransicionInvalida):
        almacen.actualizar_contenedor("borr", "migrar-bff", "creando")


def test_un_asunto_sin_workspace_solo_puede_empezar_por_creando(almacen):
    with pytest.raises(TransicionInvalida):
        almacen.actualizar_contenedor("borr", "migrar-bff", "activo")


# ── timeout derivado (ADR-0017) ──────────────────────────────────────────────


def test_el_timeout_no_se_persiste_solo_se_calcula_al_leer(almacen):
    almacen.marcar_pregunta("borr", "rediseno-panel", True)
    ruta = almacen.ruta_asunto("borr", "rediseno-panel") / "meta.yaml"
    meta = yaml.safe_load(ruta.read_text("utf-8"))
    viejo = almacen.asunto("borr", "rediseno-panel").ultima_actividad
    meta["ultima_actividad"] = (
        viejo - TIMEOUT_SIN_RESPUESTA - timedelta(minutes=1)
    ).isoformat()
    ruta.write_text(yaml.safe_dump(meta, allow_unicode=True), encoding="utf-8")

    asunto = almacen.asunto("borr", "rediseno-panel")
    assert asunto.estado_asunto is EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO
    assert asunto.estado_efectivo is EstadoAsunto.ESPERANDO_RESPUESTA
    guardado = yaml.safe_load(ruta.read_text("utf-8"))
    assert guardado["estado_asunto"] == "interactuando_con_el_usuario"


def test_bajar_la_pregunta_pendiente_apaga_el_timeout(almacen):
    almacen.marcar_pregunta("borr", "rediseno-panel", True)
    almacen.marcar_pregunta("borr", "rediseno-panel", False)
    assert almacen.asunto("borr", "rediseno-panel").pregunta_pendiente is False


# ── historial (ADR-0018) ─────────────────────────────────────────────────────


def test_el_historial_se_escribe_incrementalmente_y_se_lee_en_orden(almacen):
    almacen.anotar("borr", "rediseno-panel", "usuario", "arranquemos por el header")
    almacen.anotar("borr", "rediseno-panel", "encargado", "voy con eso")
    mensajes = almacen.historial("borr", "rediseno-panel")
    assert [(m.rol, m.texto) for m in mensajes] == [
        ("usuario", "arranquemos por el header"),
        ("encargado", "voy con eso"),
    ]
    assert almacen.asunto("borr", "rediseno-panel").mensajes == 2


def test_una_linea_corrupta_no_invalida_el_resto_del_historial(almacen):
    almacen.anotar("borr", "rediseno-panel", "usuario", "uno")
    ruta = almacen.ruta_historial("borr", "rediseno-panel")
    with ruta.open("a", encoding="utf-8") as salida:
        salida.write("{esto no es json}\n")
    almacen.anotar("borr", "rediseno-panel", "usuario", "dos")
    assert [m.texto for m in almacen.historial("borr", "rediseno-panel")] == ["uno", "dos"]


# ── reapertura (ADR-0018) ────────────────────────────────────────────────────


def test_reabrir_conserva_el_contexto_y_no_resucita_el_contenedor(almacen):
    almacen.anotar("borr", "rediseno-panel", "usuario", "algo que dijimos antes")
    almacen.actualizar_contenedor("borr", "rediseno-panel", "creando")
    almacen.actualizar_contenedor("borr", "rediseno-panel", "activo")
    almacen.actualizar_contenedor("borr", "rediseno-panel", "destruido")
    almacen.actualizar_estado("borr", "rediseno-panel", "cerrando")
    almacen.actualizar_estado("borr", "rediseno-panel", "cerrado")

    reabierto = almacen.reabrir_asunto("borr", "rediseno-panel")
    assert reabierto.estado_asunto is EstadoAsunto.INICIANDO
    # El contenedor queda destruido: hay que pedir uno nuevo, no revivir el viejo.
    assert reabierto.estado_contenedor is EstadoContenedor.DESTRUIDO
    textos = [m.texto for m in almacen.historial("borr", "rediseno-panel")]
    assert "algo que dijimos antes" in textos
    assert any("reabierto" in t for t in textos)


def test_solo_se_reabre_lo_que_esta_cerrado(almacen):
    with pytest.raises(TransicionInvalida):
        almacen.reabrir_asunto("borr", "rediseno-panel")


# ── saldo de las suscripciones (ADR-0025) ────────────────────────────────────


def test_el_saldo_es_del_proveedor_y_lo_ven_todos_sus_cerebros(almacen):
    almacen.registrar_saldo("openai", "semanal", 0.4, plan="plus")
    por_id = {c.id: c for c in almacen.cerebros()}
    # Un solo límite compartido: los tres cerebros de OpenAI miran el mismo saldo.
    assert por_id["openai-sol"].saldo is por_id["openai-luna"].saldo
    assert por_id["openai-sol"].saldo.plan == "plus"
    assert por_id["claude-opus"].saldo is None


def test_registrar_una_ventana_no_pisa_las_otras(almacen):
    almacen.registrar_saldo("anthropic", "5h", 0.1, fuente="claude-code /usage")
    suscripcion = almacen.registrar_saldo("anthropic", "semanal", 0.8)
    assert {v.nombre: v.restante for v in suscripcion.ventanas} == {
        "5h": 0.1,
        "semanal": 0.8,
    }
    # Los metadatos de la suscripción sobreviven a una observación que no los repite.
    assert suscripcion.fuente == "claude-code /usage"
    assert suscripcion.observado is not None


def test_una_ventana_en_cero_agota_la_suscripcion_entera(almacen):
    almacen.registrar_saldo("anthropic", "semanal", 0.9)
    suscripcion = almacen.registrar_saldo("anthropic", "5h", 0)
    # Si una ventana está en cero, la llamada no entra por ninguna.
    assert suscripcion.agotado is True
    assert [v.nombre for v in suscripcion.ventanas if v.agotada] == ["5h"]


def test_el_saldo_conserva_su_reset_porque_sin_el_no_se_decide(almacen):
    cuando = datetime.now(timezone.utc) + timedelta(hours=2)
    suscripcion = almacen.registrar_saldo("anthropic", "5h", 0.3, resetea=cuando)
    assert suscripcion.ventanas[0].resetea == cuando


@pytest.mark.parametrize("invalido", [-0.1, 1.5, "mucho", None])
def test_un_saldo_fuera_de_rango_se_rechaza_al_escribir(almacen, invalido):
    with pytest.raises(SaldoInvalido):
        almacen.registrar_saldo("anthropic", "5h", invalido)


def test_un_saldo_ilegible_en_el_archivo_es_un_saldo_no_observado(almacen):
    almacen.ruta_saldo.write_text(
        "suscripciones:\n  anthropic:\n    ventanas:\n      5h:\n        restante: qué\n",
        encoding="utf-8",
    )
    ventana = almacen.suscripciones()["anthropic"].ventanas[0]
    # Tolerante al leer: no se observó, no está roto el almacén.
    assert ventana.restante is None
    assert ventana.agotada is False


def test_el_archivo_de_saldo_conserva_su_cabecera_al_reescribirse(almacen):
    almacen.registrar_saldo("anthropic", "5h", 0.5)
    assert "ADR-0025" in almacen.ruta_saldo.read_text(encoding="utf-8")


# ── errores ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("malicioso", ["../otro", "..", "con espacio", "MAYUS", ""])
def test_los_ids_no_pueden_escapar_de_la_carpeta(almacen, malicioso):
    with pytest.raises(IdInvalido):
        almacen.ruta_asunto("borr", malicioso)
    with pytest.raises(IdInvalido):
        almacen.ruta_asunto(malicioso, "algo")


def test_errores_de_lo_que_no_existe(almacen, tmp_path):
    with pytest.raises(ProyectoDesconocido):
        almacen.proyecto("inexistente")
    with pytest.raises(AsuntoDesconocido):
        almacen.asunto("borr", "inexistente")
    with pytest.raises(AlmacenNoInicializado):
        Almacen(tmp_path / "no-existe").abrir_asunto("borr", "x")
