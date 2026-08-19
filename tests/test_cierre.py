"""La skill de cierre y sus cinco validaciones (ADR-0019, ADR-0021)."""

import subprocess

import pytest

from jafne.nucleo import EstadoAsunto, Veredicto


def _veredictos(resultado):
    return {v.numero: v.veredicto for v in resultado.validaciones}


def _preparar_para_cerrar(almacen, asunto_id="rediseno-panel"):
    """Deja el Asunto en el estado desde el que se puede cerrar."""
    return almacen.asunto("borr", asunto_id)


def test_un_asunto_sin_repos_ni_workspace_cierra_limpio(almacen, repo_encargado):
    _preparar_para_cerrar(almacen)
    asunto, resultado = almacen.cerrar_asunto(
        "borr", "rediseno-panel", "Se rediseñó el header y se acordó la paleta."
    )
    assert resultado.paso, resultado.motivo
    assert asunto.estado_asunto is EstadoAsunto.CERRADO
    # Sin repos ni Workspace, cuatro validaciones no tienen nada que verificar.
    assert _veredictos(resultado)[3] is Veredicto.OK
    assert _veredictos(resultado)[4] is Veredicto.NO_APLICA
    assert _veredictos(resultado)[5] is Veredicto.NO_APLICA


def test_el_cierre_escribe_cierre_md_y_la_bitacora_del_repo_encargado(
    almacen, repo_encargado
):
    almacen.cerrar_asunto("borr", "rediseno-panel", "Resumen de lo hablado.")
    assert "Resumen de lo hablado." in almacen.cierre("borr", "rediseno-panel")
    entradas = list((repo_encargado / "bitacora").glob("*-rediseno-panel.md"))
    assert len(entradas) == 1
    texto = entradas[0].read_text(encoding="utf-8")
    assert "Rediseño del panel" in texto
    assert "feature/panel" in texto
    assert "Resumen de lo hablado." in texto


def test_sin_repo_encargado_registrado_el_cierre_se_bloquea(almacen):
    # casa-justina no declara `encargado`, así que la bitácora de ADR-0021 no tiene
    # dónde escribirse y la validación 3 falla.
    almacen.abrir_asunto("casa-justina", "revisar-docs")
    almacen.actualizar_estado("casa-justina", "revisar-docs", "interactuando_con_el_usuario")
    asunto, resultado = almacen.cerrar_asunto("casa-justina", "revisar-docs", "Algo.")
    assert not resultado.paso
    assert resultado.falla.numero == 3
    assert asunto.estado_asunto is EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO
    assert "bitácora" in (asunto.motivo or "")


def test_un_workspace_sin_liberar_bloquea_el_cierre(almacen, repo_encargado):
    almacen.actualizar_contenedor("borr", "rediseno-panel", "creando")
    almacen.actualizar_contenedor("borr", "rediseno-panel", "activo")
    asunto, resultado = almacen.cerrar_asunto("borr", "rediseno-panel", "Resumen.")
    assert not resultado.paso
    # La 4 falla primero: verificar Agentes en vuelo necesita el Workspace Broker.
    assert resultado.falla.numero == 4
    assert _veredictos(resultado)[5] is Veredicto.FALLA
    assert asunto.estado_asunto is EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO


def test_un_workspace_destruido_deja_pasar_la_validacion_5(almacen, repo_encargado):
    almacen.actualizar_contenedor("borr", "rediseno-panel", "creando")
    almacen.actualizar_contenedor("borr", "rediseno-panel", "activo")
    almacen.actualizar_contenedor("borr", "rediseno-panel", "destruido")
    _, resultado = almacen.cerrar_asunto("borr", "rediseno-panel", "Resumen.")
    assert _veredictos(resultado)[5] is Veredicto.OK
    # Pero la 4 sigue sin poder verificarse sin Broker: el cierre no pasa.
    assert not resultado.paso
    assert resultado.falla.numero == 4


def test_cambios_sin_commitear_bloquean_el_cierre(almacen, repo_encargado, tmp_path, git_disponible):
    if not git_disponible:
        pytest.skip("git no está disponible en este entorno")
    repo = tmp_path / "repo-agente"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    (repo / "codigo.py").write_text("print('sin commitear')\n", encoding="utf-8")

    almacen.abrir_asunto("borr", "con-repo", rama="feature/x", repos=(str(repo),))
    almacen.actualizar_estado("borr", "con-repo", "interactuando_con_el_usuario")
    asunto, resultado = almacen.cerrar_asunto("borr", "con-repo", "Resumen.")

    assert not resultado.paso
    assert resultado.falla.numero == 1
    assert "sin commitear" in resultado.falla.detalle
    assert asunto.estado_asunto is EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO


def test_no_se_puede_cerrar_un_asunto_que_nunca_arranco(almacen, repo_encargado):
    # migrar-bff sigue en `iniciando`; ADR-0009 no permite iniciando → cerrando.
    from jafne.nucleo.estados import TransicionInvalida

    with pytest.raises(TransicionInvalida):
        almacen.cerrar_asunto("borr", "migrar-bff", "Resumen.")
