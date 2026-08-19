import subprocess

import pytest
import yaml
from fastapi.testclient import TestClient

from jafne.nucleo import Almacen
from jafne.panel import crear_app


@pytest.fixture
def repo_encargado(tmp_path):
    """Un repo `encargado/` de mentira, para que el cierre tenga dónde escribir."""
    ruta = tmp_path / "borr" / "encargado"
    ruta.mkdir(parents=True)
    return ruta


@pytest.fixture
def almacen(tmp_path, repo_encargado) -> Almacen:
    """Un `~/.jafne/` de mentira, con dos proyectos y dos Asuntos."""
    alm = Almacen(tmp_path / "jafne")
    alm.inicializar()

    alm.ruta_proyectos.write_text(
        yaml.safe_dump(
            {
                "proyectos": {
                    "borr": {
                        "nombre": "BoRR Pizzería",
                        "encargado": str(repo_encargado),
                    },
                    "casa-justina": {"nombre": "Casa Justina"},
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    alm.abrir_asunto(
        "borr", "rediseno-panel", titulo="Rediseño del panel", rama="feature/panel"
    )
    alm.actualizar_estado("borr", "rediseno-panel", "interactuando_con_el_usuario")
    alm.abrir_asunto("borr", "migrar-bff", titulo="Migrar el BFF")
    return alm


@pytest.fixture
def git_disponible() -> bool:
    try:
        return subprocess.run(["git", "--version"], capture_output=True).returncode == 0
    except OSError:
        return False


@pytest.fixture
def cliente(almacen) -> TestClient:
    """El panel sobre el almacén de mentira, sin token (ADR-0020: loopback no lo exige)."""
    return TestClient(crear_app(almacen.ruta))
