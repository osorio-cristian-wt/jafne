"""Las capacidades de un repositorio: sus skills y sus servidores MCP (ADR-0004).

ADR-0004 decidió que las capacidades de un Agente viven **versionadas dentro del repo al
que pertenecen**, y que el repo mismo es la unidad de almacenamiento y el canal de
descubrimiento. ADR-0003 le puso nombre a la carpeta: `.agents/`, neutral de proveedor,
para que un adaptador la traduzca a lo que cada cerebro concreto espera (`.claude/skills/`
si el cerebro es Claude Code).

Este módulo es solo el **lector**. No inventa la convención: la lee de los repos que ya la
usan. Verificado el 2026-08-19 contra `BoRR` y `gustagua`, que la tienen igual:

```
<repo>/
  .agents/
    skills/
      <nombre>/
        SKILL.md      ← front-matter con `name` y `description`
        references/
        assets/
  .mcp.json           ← servidores MCP del repo, en la raíz
```

Lo que este módulo **no** hace, y no es un olvido:

- **No inyecta nada en un Workspace.** Cómo llegan las skills adentro —montadas por el
  Broker, declaradas en `engineering.yaml`, o resueltas por nombre en la red del
  proyecto— es la pregunta abierta `workspace-broker`, y elegir una acá sería decidirla
  de prepo.
- **No crea capacidades.** ADR-0004 fue explícito: una capacidad nueva pasa por la cadena
  de escalación completa hasta el Usuario, que aprueba o rechaza. Un lector que además
  escribiera saltearía ese control.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

#: Dónde vive la declaración neutral de proveedor (ADR-0003).
CARPETA = ".agents"

#: Dónde viven las skills adentro de esa carpeta.
SUBCARPETA_SKILLS = "skills"

#: El archivo que describe una skill. En mayúsculas, como lo escriben los repos que ya la
#: usan; en Windows da igual, pero en el Workspace (Linux) no.
ARCHIVO_SKILL = "SKILL.md"

#: Los servidores MCP del repo. Va en la raíz y no en `.agents/` porque así lo tienen los
#: repos existentes, y porque es donde los proveedores ya lo buscan.
ARCHIVO_MCP = ".mcp.json"


@dataclass(frozen=True)
class Skill:
    """Una skill del repo: qué sabe hacer un Agente ahí adentro."""

    nombre: str
    descripcion: str | None = None
    version: str | None = None
    autor: str | None = None
    #: Relativa al repo, para que se pueda mostrar sin filtrar rutas de la máquina.
    ruta: str = ""

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Capacidades:
    """Lo que un repositorio le ofrece a su Agente (ADR-0004)."""

    repo: str
    existe: bool
    skills: tuple[Skill, ...] = ()
    servidores_mcp: tuple[str, ...] = ()
    #: Por qué no hay nada, cuando no hay nada. Un repo sin `.agents/` no es un error.
    detalle: str | None = None
    avisos: tuple[str, ...] = field(default_factory=tuple)

    def a_dict(self) -> dict:
        return {
            "repo": self.repo,
            "existe": self.existe,
            "skills": [s.a_dict() for s in self.skills],
            "servidores_mcp": list(self.servidores_mcp),
            "detalle": self.detalle,
            "avisos": list(self.avisos),
        }


def _frontmatter(texto: str) -> dict:
    """El bloque YAML de arriba de un `SKILL.md`, o vacío si no tiene.

    Se parsea a mano y no con una librería de front-matter para no sumar dependencia por
    algo que son tres líneas, igual criterio que ADR-0015 con el panel sin build.
    """
    if not texto.startswith("---"):
        return {}
    cierre = texto.find("\n---", 3)
    if cierre == -1:
        return {}
    try:
        datos = yaml.safe_load(texto[3:cierre])
    except yaml.YAMLError:
        return {}
    return datos if isinstance(datos, dict) else {}


def _leer_skill(carpeta: Path) -> Skill | None:
    archivo = carpeta / ARCHIVO_SKILL
    if not archivo.is_file():
        return None
    try:
        datos = _frontmatter(archivo.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    meta = datos.get("metadata") if isinstance(datos.get("metadata"), dict) else {}
    return Skill(
        # El nombre del front-matter manda, pero si falta el de la carpeta sirve: una
        # skill sin nombre declarado sigue siendo una skill que el Agente puede usar.
        nombre=str(datos.get("name") or carpeta.name),
        descripcion=(str(datos["description"]) if datos.get("description") else None),
        version=(str(meta.get("version")) if meta.get("version") else None),
        autor=(str(meta.get("author")) if meta.get("author") else None),
        ruta=f"{CARPETA}/{SUBCARPETA_SKILLS}/{carpeta.name}",
    )


def _servidores_mcp(raiz: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Los nombres de los servidores MCP declarados, y los avisos que surjan.

    Se devuelven **solo los nombres**: un `.mcp.json` puede tener tokens o URLs con
    credenciales adentro, y esto se sirve por el panel.
    """
    archivo = raiz / ARCHIVO_MCP
    if not archivo.is_file():
        return (), ()
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return (), (f"`{ARCHIVO_MCP}` existe pero no se pudo leer: {error}",)
    servidores = datos.get("mcpServers")
    if not isinstance(servidores, dict):
        return (), (f"`{ARCHIVO_MCP}` no tiene un objeto `mcpServers`.",)
    return tuple(sorted(str(n) for n in servidores)), ()


def leer(ruta_repo: str | Path) -> Capacidades:
    """Las capacidades declaradas en ese repo (ADR-0004).

    Un repo sin `.agents/` devuelve `existe=False` con el motivo, y no una excepción: la
    mayoría de los repos todavía no la tiene, y eso es el estado normal, no una falla.
    """
    raiz = Path(ruta_repo)
    nombre = raiz.name
    if not raiz.is_dir():
        return Capacidades(
            repo=nombre,
            existe=False,
            detalle=f"No existe el repositorio '{raiz}'.",
        )

    servidores, avisos = _servidores_mcp(raiz)
    carpeta_skills = raiz / CARPETA / SUBCARPETA_SKILLS
    if not carpeta_skills.is_dir():
        return Capacidades(
            repo=nombre,
            existe=bool(servidores),
            servidores_mcp=servidores,
            detalle=(
                f"El repo no declara skills: no tiene `{CARPETA}/{SUBCARPETA_SKILLS}/`. "
                f"Agregar una capacidad pasa por la cadena de escalación hasta el "
                f"Usuario, que aprueba o rechaza (ADR-0004)."
            ),
            avisos=avisos,
        )

    skills = tuple(
        sorted(
            (s for s in (_leer_skill(c) for c in carpeta_skills.iterdir() if c.is_dir()) if s),
            key=lambda s: s.nombre,
        )
    )
    return Capacidades(
        repo=nombre,
        existe=True,
        skills=skills,
        servidores_mcp=servidores,
        detalle=None,
        avisos=avisos,
    )
