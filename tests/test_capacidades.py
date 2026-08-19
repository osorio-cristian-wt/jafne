"""Las capacidades de un repositorio: skills y servidores MCP (ADR-0004, ADR-0003).

El layout no se inventó acá: se leyó de los repos que ya lo usan (`BoRR`, `gustagua`),
verificado el 2026-08-19. Estos tests lo fijan contra un repo de mentira, para no depender
de que esas carpetas sigan existiendo en la máquina que corre la suite.
"""

import json

import pytest

from jafne.nucleo import capacidades


@pytest.fixture
def repo(tmp_path):
    """Un repo con la convención completa: dos skills y un `.mcp.json`."""
    skills = tmp_path / ".agents" / "skills"
    (skills / "supabase").mkdir(parents=True)
    (skills / "supabase" / "SKILL.md").write_text(
        '---\nname: supabase\ndescription: "Para tareas de Supabase."\n'
        'metadata:\n  author: supabase\n  version: "0.1.2"\n---\n\ncuerpo\n',
        encoding="utf-8",
    )
    (skills / "postgres").mkdir()
    (skills / "postgres" / "SKILL.md").write_text(
        "---\nname: postgres\ndescription: Consultas.\n---\n", encoding="utf-8"
    )
    (tmp_path / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"supabase": {"type": "http", "url": "https://x/mcp"}}}),
        encoding="utf-8",
    )
    return tmp_path


def test_se_leen_las_skills_declaradas_por_el_repo(repo):
    leidas = capacidades.leer(repo)
    assert leidas.existe is True
    assert [s.nombre for s in leidas.skills] == ["postgres", "supabase"]


def test_una_skill_trae_su_descripcion_y_su_version(repo):
    supabase = next(s for s in capacidades.leer(repo).skills if s.nombre == "supabase")
    assert supabase.descripcion == "Para tareas de Supabase."
    assert supabase.version == "0.1.2"
    assert supabase.ruta == ".agents/skills/supabase"


def test_del_mcp_solo_salen_los_nombres_y_nunca_las_urls(repo):
    # Un `.mcp.json` puede llevar tokens o URLs con credenciales, y esto se sirve por el
    # panel. Se exponen los nombres y nada más.
    leidas = capacidades.leer(repo)
    assert leidas.servidores_mcp == ("supabase",)
    assert "https://x/mcp" not in json.dumps(leidas.a_dict())


def test_un_repo_sin_agents_no_es_un_error_y_dice_por_que(tmp_path):
    # Es el estado normal de casi todos los repos hoy. Una excepción lo trataría como
    # falla y taparía el caso real, que es "todavía no se le declararon capacidades".
    leidas = capacidades.leer(tmp_path)
    assert leidas.existe is False
    assert leidas.skills == ()
    assert "escalación" in leidas.detalle


def test_un_mcp_json_roto_avisa_en_vez_de_romper_la_lectura(repo):
    # Si un JSON mal escrito volteara la lectura entera, las skills —que están bien—
    # dejarían de verse por culpa de un archivo aparte.
    (repo / ".mcp.json").write_text("{ esto no es json", encoding="utf-8")
    leidas = capacidades.leer(repo)
    assert len(leidas.skills) == 2
    assert leidas.avisos and ".mcp.json" in leidas.avisos[0]


def test_una_skill_sin_frontmatter_igual_se_lista_con_el_nombre_de_su_carpeta(repo):
    # Una skill sin declarar su nombre sigue siendo una skill que el Agente puede usar.
    suelta = repo / ".agents" / "skills" / "suelta"
    suelta.mkdir()
    (suelta / "SKILL.md").write_text("sin front-matter\n", encoding="utf-8")
    assert "suelta" in [s.nombre for s in capacidades.leer(repo).skills]
