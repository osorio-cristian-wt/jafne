"""Los catálogos que no son ejes de estado de un Asunto.

- `riesgo` — clase de riesgo declarada por el Encargado (ADR-0027).
- `tamanos` — tamaño de cerebro común entre proveedores (ADR-0030).
- `adaptadores` — qué proveedores se pueden usar hoy (ADR-0028).
"""

import pytest

from jafne.nucleo import riesgo, tamanos
from jafne.nucleo.adaptadores import AdaptadorNoImplementado, exigir, hay_adaptador
from jafne.nucleo.riesgo import ClaseRiesgo, ClaseRiesgoInvalida
from jafne.nucleo.tamanos import ORDEN, Tamano, TamanoInvalido
from jafne.pendientes import DecisionPendiente

# ── clase de riesgo (ADR-0027) ───────────────────────────────────────────────


def test_sin_clase_declarada_se_asume_la_mas_estricta():
    # "Aislar de más antes que arriesgar un escape": el análogo de la política de
    # ADR-0003 aplicado a infraestructura.
    assert riesgo.parsear(None) is ClaseRiesgo.GENERADO
    assert riesgo.parsear("") is ClaseRiesgo.GENERADO
    assert riesgo.POR_DEFECTO is ClaseRiesgo.GENERADO


def test_una_clase_declarada_se_respeta():
    assert riesgo.parsear("revisado") is ClaseRiesgo.REVISADO
    assert riesgo.parsear("  GENERADO  ") is ClaseRiesgo.GENERADO


def test_una_clase_que_no_existe_no_se_adivina():
    # Omitirla es aceptar el default; escribirla mal es querer decir algo y errarle.
    # Adivinar ahí sería elegir el aislamiento por el Encargado.
    with pytest.raises(ClaseRiesgoInvalida):
        riesgo.parsear("microvm")


def test_el_catalogo_de_riesgo_tiene_dos_valores():
    assert {c.value for c in ClaseRiesgo} == {"revisado", "generado"}


def test_cada_clase_tiene_su_runtime():
    # No son dos motores: son dos runtimes del mismo Podman (ADR-0032).
    assert riesgo.driver_para(ClaseRiesgo.REVISADO) == "crun"
    assert riesgo.driver_para(ClaseRiesgo.GENERADO) == "kata"


def test_el_default_pide_el_aislamiento_fuerte():
    # `generado` es el default, así que el camino normal es el de microVM.
    assert riesgo.driver_para(riesgo.POR_DEFECTO) == "kata"


def test_con_el_runtime_disponible_se_sirve():
    assert riesgo.exigir_runtime(ClaseRiesgo.GENERADO, {"crun", "kata"}) == "kata"


def test_sin_el_runtime_se_rechaza_en_vez_de_degradar():
    # ADR-0032: servir `generado` sobre `crun` le daría al Encargado una garantía que no
    # tiene. Fallar ruidoso es el comportamiento correcto acá.
    with pytest.raises(riesgo.RuntimeNoDisponible) as excepcion:
        riesgo.exigir_runtime(ClaseRiesgo.GENERADO, {"crun"})
    assert excepcion.value.driver == "kata"
    assert "menos aislamiento" in str(excepcion.value)


def test_la_clase_revisada_no_necesita_microvm():
    assert riesgo.exigir_runtime(ClaseRiesgo.REVISADO, {"crun"}) == "crun"


# ── tamaño de cerebro (ADR-0030) ─────────────────────────────────────────────


def test_los_tamanos_van_de_menor_a_mayor():
    assert [t.value for t in ORDEN] == ["chico", "medio", "grande", "gigante"]


def test_la_correspondencia_cruza_proveedores():
    assert tamanos.familia("anthropic", Tamano.MEDIO) == "sonnet"
    assert tamanos.familia("openai", Tamano.MEDIO) == "tierra"
    assert tamanos.familia("anthropic", Tamano.GIGANTE) == "fable"


def test_un_proveedor_no_cubre_necesariamente_todos_los_tamanos():
    assert tamanos.familia("openai", Tamano.GIGANTE) is None
    assert tamanos.cubiertos("openai") == (Tamano.CHICO, Tamano.MEDIO, Tamano.GRANDE)
    assert len(tamanos.cubiertos("anthropic")) == 4


def test_conmutar_puede_degradar_el_tamano():
    # La consecuencia de ADR-0026 hecha código: un Asunto en `gigante` que conmuta a un
    # proveedor sin `gigante` baja a `grande`, y eso tiene que verse.
    assert tamanos.degradar("openai", Tamano.GIGANTE) is Tamano.GRANDE
    assert tamanos.degradar("anthropic", Tamano.GIGANTE) is Tamano.GIGANTE
    assert tamanos.degradar("openai", Tamano.CHICO) is Tamano.CHICO


def test_degradar_a_un_proveedor_desconocido_no_inventa_nada():
    assert tamanos.degradar("proveedor-nuevo", Tamano.GRANDE) is None


def test_el_vocabulario_que_adr_0030_reemplaza_se_traduce():
    assert tamanos.parsear("liviano") is Tamano.CHICO
    assert tamanos.parsear("intermedio") is Tamano.MEDIO
    assert tamanos.parsear("pesado") is Tamano.GRANDE


def test_un_tamano_fuera_del_catalogo_se_rechaza():
    with pytest.raises(TamanoInvalido) as excepcion:
        tamanos.parsear("enorme")
    # El error enseña el catálogo en vez de solo negarse.
    assert "chico, medio, grande, gigante" in str(excepcion.value)


# ── adaptadores (ADR-0028) ───────────────────────────────────────────────────


def test_solo_anthropic_tiene_adaptador_hoy():
    assert hay_adaptador("anthropic") is True
    assert hay_adaptador("openai") is False


def test_usar_un_proveedor_sin_adaptador_falla_con_su_propio_error():
    with pytest.raises(AdaptadorNoImplementado) as excepcion:
        exigir("openai")
    assert excepcion.value.proveedor == "openai"


def test_falta_de_adaptador_no_es_una_decision_pendiente():
    # La distinción que ADR-0028 pide sostener: "nadie decidió esto" y "está decidido,
    # falta escribirlo" son dos respuestas distintas, y llevan a acciones distintas.
    assert not issubclass(AdaptadorNoImplementado, DecisionPendiente)
    with pytest.raises(AdaptadorNoImplementado):
        exigir("openai")


def test_un_proveedor_con_adaptador_no_molesta():
    assert exigir("anthropic") is None


# ── salida de la CLI ─────────────────────────────────────────────────────────


def test_los_pendientes_se_imprimen_sin_romper_en_consolas_no_utf8(capsys, monkeypatch):
    """La consola de Windows es cp1252 y el hop 4 tiene un `→` en el título.

    Sin forzar UTF-8, `jafne pendientes` moría con UnicodeEncodeError — un comando caído
    por un carácter es peor que un carácter feo.
    """
    import io
    import sys

    from jafne.cli import main

    crudo = io.BytesIO()
    monkeypatch.setattr(
        sys, "stdout", io.TextIOWrapper(crudo, encoding="cp1252", errors="strict")
    )
    assert main(["pendientes"]) == 0
    sys.stdout.flush()
    assert "protocolo-asignacion-tareas" in crudo.getvalue().decode("utf-8")
