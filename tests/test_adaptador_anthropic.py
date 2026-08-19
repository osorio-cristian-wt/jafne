"""El adaptador de Anthropic sobre la CLI de Claude Code (ADR-0028, ADR-0031, ADR-0034).

Ningún test invoca la CLI de verdad: se sustituye `subprocess.run` y se verifica **qué
comando se arma** y **cómo se interpreta la respuesta**. No es solo por velocidad — correr
la CLI de verdad gastaría el saldo de la suscripción del Usuario cada vez que alguien
ejecuta la suite, que es justo lo que ADR-0025 mira con lupa.

La forma del JSON que se simula acá es la real, capturada de una corrida contra la CLI el
2026-08-19.
"""

import json
import subprocess
from pathlib import Path

import pytest

from jafne.nucleo import adaptadores, prompts
from jafne.nucleo.adaptador_anthropic import AdaptadorAnthropic, ErrorDelProveedor
from jafne.nucleo.roles import Rol
from jafne.nucleo.sesion import TipoEvento, cumple_contrato
from jafne.nucleo.tamanos import Tamano

#: Un resultado real de `claude -p … --output-format json`, recortado a lo que se usa.
RESPUESTA = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "result": "LISTO",
    "session_id": "e413df97-731d-4ae3-ae0d-4676dc746252",
    "total_cost_usd": 0.0182,
    "num_turns": 1,
    "duration_ms": 3780,
}


@pytest.fixture
def cli_falsa(monkeypatch):
    """Sustituye la CLI y deja ver con qué comando se la invocó."""
    llamadas = []

    def falso_run(comando, **kwargs):
        llamadas.append({"comando": comando, **kwargs})
        return subprocess.CompletedProcess(
            comando, 0, stdout=json.dumps(RESPUESTA), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", falso_run)
    return llamadas


def _adaptador(**kwargs) -> AdaptadorAnthropic:
    return AdaptadorAnthropic(cli="claude-de-mentira", **kwargs)


# ── el contrato congelado (ADR-0031) ─────────────────────────────────────────


def test_el_adaptador_cumple_el_contrato():
    # Es la prueba de que ADR-0028 acertó al congelar el contrato **antes**: el primer
    # adaptador real entra sin que el contrato tenga que ceder.
    assert cumple_contrato(_adaptador())


def test_esta_registrado_como_construido():
    # `PROVEEDORES_CON_ADAPTADOR` dice *en alcance*; el registro dice *escrito*.
    assert adaptadores.hay_adaptador("anthropic")
    assert "anthropic" in adaptadores.REGISTRO


def test_el_registro_guarda_fabricas_no_instancias():
    # Cada conversación necesita su propio adaptador: el adaptador lleva la sesión adentro.
    uno = adaptadores.construir("anthropic")
    otro = adaptadores.construir("anthropic")
    assert uno is not otro


def test_openai_sigue_sin_adaptador():
    with pytest.raises(adaptadores.AdaptadorNoImplementado):
        adaptadores.construir("openai")


# ── abrir y reanudar no gastan nada ──────────────────────────────────────────


def test_abrir_no_invoca_la_cli(cli_falsa):
    # El id se inventa de este lado y se le impone con `--session-id`. La alternativa era
    # mandar un turno de mentira para que el proveedor devolviera un id: cobrarle al
    # Usuario por abrir una conversación vacía.
    id_sesion = _adaptador().abrir("C:/proyecto", Tamano.MEDIO)
    assert id_sesion
    assert cli_falsa == []


def test_dos_sesiones_nuevas_no_comparten_id(cli_falsa):
    assert _adaptador().abrir("/x", Tamano.MEDIO) != _adaptador().abrir("/x", Tamano.MEDIO)


def test_reanudar_tampoco_invoca_la_cli(cli_falsa):
    # Rehidratar es reanudar, no reinyectar: el historial lo tiene el proveedor y vuelve
    # recién en el próximo turno (ADR-0018, ADR-0031).
    _adaptador().reanudar("una-sesion-vieja")
    assert cli_falsa == []


def test_emitir_sin_sesion_es_un_error_de_uso(cli_falsa):
    with pytest.raises(ErrorDelProveedor):
        list(_adaptador().emitir("hola"))


# ── qué comando se arma ──────────────────────────────────────────────────────


def test_el_primer_turno_impone_el_id_de_sesion(cli_falsa):
    adaptador = _adaptador()
    id_sesion = adaptador.abrir("C:/proyecto", Tamano.MEDIO)
    list(adaptador.emitir("hola"))

    comando = cli_falsa[0]["comando"]
    assert "--session-id" in comando
    assert comando[comando.index("--session-id") + 1] == id_sesion
    assert "--resume" not in comando
    assert cli_falsa[0]["cwd"] == "C:/proyecto"


def test_el_segundo_turno_reanuda_en_vez_de_abrir(cli_falsa):
    adaptador = _adaptador()
    adaptador.abrir("C:/proyecto", Tamano.MEDIO)
    list(adaptador.emitir("uno"))
    list(adaptador.emitir("dos"))

    segundo = cli_falsa[1]["comando"]
    assert "--resume" in segundo
    assert segundo[segundo.index("--resume") + 1] == RESPUESTA["session_id"]
    assert "--session-id" not in segundo


def test_reanudar_una_sesion_vieja_usa_resume_desde_el_primer_turno(cli_falsa):
    adaptador = _adaptador()
    adaptador.reanudar("sesion-de-ayer")
    list(adaptador.emitir("seguimos"))
    assert "--resume" in cli_falsa[0]["comando"]


def test_el_modelo_del_cerebro_viaja_a_la_cli(cli_falsa):
    adaptador = _adaptador(modelo="claude-sonnet-5")
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    comando = cli_falsa[0]["comando"]
    assert comando[comando.index("--model") + 1] == "claude-sonnet-5"


def test_el_agente_trabaja_pero_acotado_a_la_raiz(cli_falsa):
    """El Usuario decidió que el chat use herramientas, con borde (ADR-0039).

    Verificado contra la CLI real el 2026-08-19: adentro de la raíz escribe y lee; un
    `Read` a un archivo de afuera cae en `permission_denials`, el contenido no se filtra,
    y el turno **termina** pidiendo permiso en vez de colgarse.
    """
    adaptador = _adaptador(raiz_trabajo="C:/Repos")
    adaptador.abrir("C:/Repos", Tamano.MEDIO)
    list(adaptador.emitir("hola"))

    comando = cli_falsa[0]["comando"]
    assert comando[comando.index("--add-dir") + 1] == "C:/Repos"
    assert comando[comando.index("--permission-mode") + 1] == "acceptEdits"


def test_nunca_se_saltean_los_permisos(cli_falsa):
    # `bypassPermissions` borraría el borde: el agente podría tocar cualquier cosa del
    # disco y el límite que el Usuario pidió dejaría de existir.
    adaptador = _adaptador()
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    comando = cli_falsa[0]["comando"]
    assert "--dangerously-skip-permissions" not in comando
    assert "bypassPermissions" not in comando


def test_la_raiz_se_puede_declarar_por_entorno(monkeypatch, cli_falsa):
    from jafne.nucleo import adaptador_anthropic

    monkeypatch.setenv(adaptador_anthropic.VARIABLE_RAIZ_TRABAJO, "D:/otro-lado")
    adaptador = AdaptadorAnthropic(cli="claude-de-mentira")
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    comando = cli_falsa[0]["comando"]
    assert comando[comando.index("--add-dir") + 1] == "D:/otro-lado"


def test_el_asistente_se_presenta_con_su_identidad_de_rol(cli_falsa):
    """El agente sabe que es el Asistente de JAFNE sin que el mensaje se lo diga (ADR-0040).

    Antes de esto el mensaje del Usuario viajaba crudo y el agente del otro lado no conocía
    ni su rol, ni la jerarquía, ni su borde: se presentaba como "tu ayudante para tareas de
    desarrollo" solo porque el mensaje se lo había dicho.
    """
    adaptador = _adaptador(rol=Rol.ASISTENTE)
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))

    comando = cli_falsa[0]["comando"]
    ruta = Path(comando[comando.index("--append-system-prompt-file") + 1])
    assert ruta.is_file()


def test_el_prompt_se_agrega_y_no_reemplaza(cli_falsa):
    # El Usuario eligió `--append-...` el 2026-08-19: reemplazarlo perdería todo lo que la
    # CLI ya sabe de sí misma —sus herramientas, sus convenciones— y habría que reescribirlo.
    adaptador = _adaptador(rol=Rol.ASISTENTE)
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    assert "--system-prompt" not in cli_falsa[0]["comando"]


def test_sin_rol_no_se_inyecta_ningun_prompt(cli_falsa):
    # El adaptador se usa fuera del chat del panel —el Encargado trabajando un Asunto, por
    # ejemplo—, y ahí la identidad la pone quien lo invoca, no este objeto por su cuenta.
    adaptador = _adaptador()
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    assert "--append-system-prompt-file" not in cli_falsa[0]["comando"]


def test_el_agente_tiene_identidad_pero_no_servidor_mcp(cli_falsa):
    """Prompt e identidad de rol son cosas separadas (ADR-0040 vs ADR-0044).

    El Agente ya tiene prompt —se pudo escribir cuando ADR-0047 y ADR-0048 contestaron qué
    es un repo para JAFNE—, pero **no** tiene MCP: su alcance es un repositorio y el
    servidor no expone ese recorte. Que tenga uno no implica lo otro.
    """
    adaptador = _adaptador(rol=Rol.AGENTE)
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    comando = cli_falsa[0]["comando"]
    assert "--append-system-prompt-file" in comando
    assert "agente.md" in comando[comando.index("--append-system-prompt-file") + 1]
    assert "--mcp-config" not in comando


def test_el_encargado_tiene_identidad_de_organizacion(cli_falsa):
    """Su alcance es la organización, no un repositorio (ADR-0044).

    Es la distinción que sostiene la delegación: si el Encargado se cree dueño de la
    implementación de un repo, hace el trabajo del Agente y no delega nada.
    """
    texto = " ".join(prompts.ruta_prompt(Rol.ENCARGADO).read_text(encoding="utf-8").split())
    assert "una organización" in texto
    assert "varios Agentes, uno por repo" in texto
    assert "escalá al Asistente" in texto


def test_el_prompt_del_asistente_dice_las_tres_cosas_que_tiene_que_decir():
    """Rol, borde y que las decisiones son del Usuario (ADR-0040, ADR-0002, ADR-0039).

    No se verifica la redacción sino que las tres piezas estén: son las que el agente no
    podía saber de ninguna otra forma, y borrar cualquiera lo devuelve a no saber quién es.
    """
    # Sin los saltos de línea: el texto se corta a 90 columnas y una pieza puede quedar
    # partida al medio sin que eso cambie lo que el agente lee.
    texto = " ".join(prompts.ruta_prompt(Rol.ASISTENTE).read_text(encoding="utf-8").split())
    assert "Asistente de JAFNE" in texto
    assert "Usuario → Asistente (vos) → Encargado → Agentes" in texto
    assert "raíz de repos" in texto
    assert "No tomás decisiones de diseño" in texto


# ── el MCP, acotado por rol (ADR-0042, ADR-0044) ─────────────────────────────


def _config_mcp(comando: list[str]) -> dict:
    return json.loads(comando[comando.index("--mcp-config") + 1])


def test_al_asistente_se_le_declara_el_mcp_de_todos_los_proyectos(cli_falsa):
    adaptador = _adaptador(rol=Rol.ASISTENTE)
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))

    servidor = _config_mcp(cli_falsa[0]["comando"])["mcpServers"]["jafne"]
    assert servidor["type"] == "http"
    assert servidor["url"].endswith("/mcp/asistente")


def test_al_encargado_se_le_declara_el_mcp_de_su_proyecto(cli_falsa):
    """La URL la arma JAFNE, no el agente (ADR-0042).

    Es lo que sostiene el acotamiento: si el rol viajara en el mensaje, un Encargado podría
    declararse Asistente y ver todos los proyectos.
    """
    adaptador = _adaptador(rol=Rol.ENCARGADO, proyecto="borr")
    adaptador.abrir("/x", Tamano.GRANDE)
    list(adaptador.emitir("hola"))

    servidor = _config_mcp(cli_falsa[0]["comando"])["mcpServers"]["jafne"]
    assert servidor["url"].endswith("/mcp/proyecto/borr")


def test_un_encargado_sin_proyecto_no_recibe_mcp(cli_falsa):
    # Sin proyecto no hay alcance que declarar, y darle el del Asistente le abriría todos
    # los proyectos — exactamente lo que la jerarquía separa.
    adaptador = _adaptador(rol=Rol.ENCARGADO)
    adaptador.abrir("/x", Tamano.GRANDE)
    list(adaptador.emitir("hola"))
    assert "--mcp-config" not in cli_falsa[0]["comando"]


def test_el_agente_todavia_no_tiene_mcp(cli_falsa):
    # Su alcance es un repositorio (ADR-0044) y el servidor no expone ese recorte. Darle el
    # del Encargado le daría la vista del proyecto entero.
    adaptador = _adaptador(rol=Rol.AGENTE, proyecto="borr")
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    assert "--mcp-config" not in cli_falsa[0]["comando"]


def test_las_herramientas_del_mcp_se_permiten_explicitamente(cli_falsa):
    """Sin esto el agente las **ve** y no las puede usar.

    Verificado contra la CLI real el 2026-08-19: con `acceptEdits` solo, la llamada queda
    esperando una aprobación que desde el panel no hay quién dar — el mismo problema que
    ADR-0039 encontró para las herramientas de archivos.
    """
    adaptador = _adaptador(rol=Rol.ASISTENTE)
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))

    comando = cli_falsa[0]["comando"]
    assert comando[comando.index("--allowed-tools") + 1] == "mcp__jafne"


def test_el_token_de_infraestructura_va_en_la_cabecera_y_no_en_la_url(monkeypatch, cli_falsa):
    # La línea de comandos la ve cualquiera con un listado de procesos.
    from jafne.nucleo import mcp

    monkeypatch.setenv(mcp.VARIABLE_TOKEN, "un-secreto")
    adaptador = _adaptador(rol=Rol.ASISTENTE)
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))

    servidor = _config_mcp(cli_falsa[0]["comando"])["mcpServers"]["jafne"]
    assert servidor["headers"]["Authorization"] == "Bearer un-secreto"
    assert "un-secreto" not in servidor["url"]


def test_sin_rol_no_se_declara_ningun_mcp(cli_falsa):
    adaptador = _adaptador()
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    assert "--mcp-config" not in cli_falsa[0]["comando"]


def test_nunca_se_pasa_una_credencial(cli_falsa):
    # ADR-0034: JAFNE no las pide, no las guarda y no las ve. La sesión es de Claude Code.
    adaptador = _adaptador()
    adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    assert "env" not in cli_falsa[0] or cli_falsa[0].get("env") is None
    assert not any("api" in str(a).lower() and "key" in str(a).lower() for a in cli_falsa[0]["comando"])


# ── cómo se interpreta la respuesta ──────────────────────────────────────────


def test_un_turno_bueno_da_texto_y_resultado(cli_falsa):
    adaptador = _adaptador(modelo="claude-sonnet-5")
    adaptador.abrir("/x", Tamano.MEDIO)
    eventos = list(adaptador.emitir("hola"))

    assert [e.tipo for e in eventos] == [TipoEvento.TEXTO, TipoEvento.RESULTADO]
    assert eventos[0].texto == "LISTO"
    assert eventos[1].datos["id_sesion"] == RESPUESTA["session_id"]
    assert eventos[1].datos["costo_usd"] == RESPUESTA["total_cost_usd"]


def test_el_id_que_manda_el_proveedor_gana(cli_falsa):
    # Con `--resume` el proveedor puede devolver otro id (`--fork-session` es un caso), y
    # quedarse con el viejo dejaría la conversación colgada del turno siguiente.
    adaptador = _adaptador()
    puesto = adaptador.abrir("/x", Tamano.MEDIO)
    list(adaptador.emitir("hola"))
    assert adaptador.id_sesion == RESPUESTA["session_id"] != puesto


def test_un_error_del_proveedor_sale_como_evento_de_error(monkeypatch):
    respuesta = {**RESPUESTA, "is_error": True, "result": "se acabó el cupo"}
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda c, **k: subprocess.CompletedProcess(c, 0, json.dumps(respuesta), ""),
    )
    adaptador = _adaptador()
    adaptador.abrir("/x", Tamano.MEDIO)
    (evento,) = list(adaptador.emitir("hola"))
    assert evento.tipo is TipoEvento.ERROR
    assert "cupo" in evento.texto


def test_un_exit_distinto_de_cero_sale_como_error(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda c, **k: subprocess.CompletedProcess(c, 1, "", "no estás logueado"),
    )
    adaptador = _adaptador()
    adaptador.abrir("/x", Tamano.MEDIO)
    (evento,) = list(adaptador.emitir("hola"))
    assert evento.tipo is TipoEvento.ERROR
    assert "logueado" in evento.texto


def test_una_salida_que_no_es_json_no_revienta(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda c, **k: subprocess.CompletedProcess(c, 0, "no soy json", ""),
    )
    adaptador = _adaptador()
    adaptador.abrir("/x", Tamano.MEDIO)
    (evento,) = list(adaptador.emitir("hola"))
    assert evento.tipo is TipoEvento.ERROR


def test_un_turno_que_no_contesta_se_corta(monkeypatch):
    def se_cuelga(comando, **kwargs):
        raise subprocess.TimeoutExpired(comando, 1)

    monkeypatch.setattr(subprocess, "run", se_cuelga)
    adaptador = _adaptador(espera=1)
    adaptador.abrir("/x", Tamano.MEDIO)
    with pytest.raises(ErrorDelProveedor):
        list(adaptador.emitir("hola"))


def test_sin_la_cli_el_error_dice_como_arreglarlo(monkeypatch):
    monkeypatch.setattr("jafne.nucleo.credenciales.ruta_cli", lambda: None)
    adaptador = AdaptadorAnthropic()
    adaptador.abrir("/x", Tamano.MEDIO)
    with pytest.raises(ErrorDelProveedor) as error:
        list(adaptador.emitir("hola"))
    assert "jafne credencial" in str(error.value)


# ── saldo: lo que la CLI NO sabe decir (ADR-0025) ────────────────────────────


def test_el_saldo_es_none_porque_la_cli_informa_gasto_no_saldo():
    """`None` no es un hueco: es la respuesta correcta.

    La CLI informa `total_cost_usd` del turno —**gasto**—, y ADR-0025 fijó que la métrica
    es el **saldo**, cuánto queda. Derivar uno del otro exigiría conocer el límite, que es
    justamente lo que `medicion-de-consumo` tiene abierto. El contrato ya dice que `None`
    no significa cero.
    """
    assert _adaptador().saldo() is None
