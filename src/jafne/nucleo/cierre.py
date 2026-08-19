"""Skill de cierre de un Asunto: las cinco validaciones de ADR-0019.

El cierre es **todo o nada**. Si alguna validación falla, el Asunto vuelve a
`interactuando_con_el_usuario` llevando cuál falló y por qué (ADR-0009). No hay cierre
parcial ni forzado — el `--force` está descartado en ADR-0019, no ausente por olvido.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from .estados import EstadoContenedor
from .modelos import Asunto

#: Candidatas a rama principal. ADR-0006 dice "develop o staging, según el repo", así que
#: se busca la primera que exista y contenga la rama del Asunto en vez de asumir una.
RAMAS_PRINCIPALES = ("develop", "staging", "main", "master")


class Veredicto(StrEnum):
    OK = "ok"
    FALLA = "falla"
    #: La validación no tiene nada que verificar (ej. un Asunto que nunca tuvo Workspace
    #: no puede tener Agentes en vuelo). Cuenta como aprobada.
    NO_APLICA = "no_aplica"


@dataclass(frozen=True)
class Validacion:
    numero: int
    nombre: str
    veredicto: Veredicto
    detalle: str

    def a_dict(self) -> dict[str, object]:
        return {
            "numero": self.numero,
            "nombre": self.nombre,
            "veredicto": self.veredicto.value,
            "detalle": self.detalle,
        }


@dataclass(frozen=True)
class Cierre:
    """El resultado de correr las cinco validaciones, en orden."""

    validaciones: tuple[Validacion, ...]

    @property
    def paso(self) -> bool:
        return all(v.veredicto is not Veredicto.FALLA for v in self.validaciones)

    @property
    def falla(self) -> Validacion | None:
        """La primera validación que falló, que es la causa a reportar (ADR-0019)."""
        return next(
            (v for v in self.validaciones if v.veredicto is Veredicto.FALLA), None
        )

    @property
    def motivo(self) -> str | None:
        fallo = self.falla
        return f"cierre bloqueado en «{fallo.nombre}»: {fallo.detalle}" if fallo else None

    def a_dict(self) -> dict[str, object]:
        return {
            "paso": self.paso,
            "motivo": self.motivo,
            "validaciones": [v.a_dict() for v in self.validaciones],
        }


def _git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        proceso = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError) as error:
        return 1, str(error)
    return proceso.returncode, (proceso.stdout + proceso.stderr).strip()


def _repos_validos(asunto: Asunto) -> list[Path]:
    return [Path(r).expanduser() for r in asunto.repos if Path(r).expanduser().is_dir()]


def _v1_trabajo_guardado(asunto: Asunto) -> Validacion:
    repos = _repos_validos(asunto)
    if not repos:
        return Validacion(
            1,
            "trabajo guardado",
            Veredicto.NO_APLICA,
            "El Asunto no registró repos; no hay cambios que puedan quedar sin guardar.",
        )
    sucios = []
    for repo in repos:
        codigo, salida = _git(repo, "status", "--porcelain")
        if codigo != 0:
            return Validacion(
                1, "trabajo guardado", Veredicto.FALLA, f"No se pudo leer {repo}: {salida}"
            )
        if salida:
            sucios.append(repo.name)
    if sucios:
        return Validacion(
            1,
            "trabajo guardado",
            Veredicto.FALLA,
            f"Quedan cambios sin commitear en: {', '.join(sucios)}.",
        )
    return Validacion(
        1,
        "trabajo guardado",
        Veredicto.OK,
        f"Sin cambios pendientes en {len(repos)} repo(s).",
    )


def _v2_merge_cerrado(asunto: Asunto) -> Validacion:
    if not asunto.rama:
        return Validacion(
            2,
            "merge cerrado",
            Veredicto.NO_APLICA,
            "El Asunto no registró rama de trabajo.",
        )
    repos = _repos_validos(asunto)
    if not repos:
        return Validacion(
            2, "merge cerrado", Veredicto.NO_APLICA, "El Asunto no registró repos."
        )

    sin_mergear, mergeados = [], []
    for repo in repos:
        if _git(repo, "rev-parse", "--verify", asunto.rama)[0] != 0:
            continue  # la rama del Asunto no existe en este repo
        destino = next(
            (
                candidata
                for candidata in RAMAS_PRINCIPALES
                if _git(repo, "rev-parse", "--verify", candidata)[0] == 0
                and _git(repo, "merge-base", "--is-ancestor", asunto.rama, candidata)[0] == 0
            ),
            None,
        )
        (mergeados if destino else sin_mergear).append(
            f"{repo.name}→{destino}" if destino else repo.name
        )

    if sin_mergear:
        return Validacion(
            2,
            "merge cerrado",
            Veredicto.FALLA,
            f"'{asunto.rama}' no está mergeada a ninguna rama principal en: "
            f"{', '.join(sin_mergear)}.",
        )
    if not mergeados:
        return Validacion(
            2,
            "merge cerrado",
            Veredicto.NO_APLICA,
            f"'{asunto.rama}' no existe en ninguno de los repos registrados.",
        )
    return Validacion(
        2, "merge cerrado", Veredicto.OK, f"Mergeada en: {', '.join(mergeados)}."
    )


def _v3_documentado(ruta_cierre: Path, ruta_bitacora: Path | None) -> Validacion:
    if not ruta_cierre.is_file():
        return Validacion(
            3,
            "lo hablado documentado",
            Veredicto.FALLA,
            f"Falta el cierre.md del Asunto en {ruta_cierre}.",
        )
    if ruta_bitacora is None:
        return Validacion(
            3,
            "lo hablado documentado",
            Veredicto.FALLA,
            "El proyecto no tiene repo `encargado/` registrado en proyectos.yaml, así "
            "que la bitácora de ADR-0021 no tiene dónde escribirse.",
        )
    if not ruta_bitacora.is_file():
        return Validacion(
            3,
            "lo hablado documentado",
            Veredicto.FALLA,
            f"Falta la entrada de bitácora en {ruta_bitacora} (ADR-0021).",
        )
    return Validacion(
        3,
        "lo hablado documentado",
        Veredicto.OK,
        f"cierre.md y bitácora escritos ({ruta_bitacora.name}).",
    )


def _v4_sin_agentes_en_vuelo(asunto: Asunto) -> Validacion:
    if asunto.estado_contenedor is None:
        return Validacion(
            4,
            "sin Agentes en vuelo",
            Veredicto.NO_APLICA,
            "El Asunto nunca tuvo Workspace; no hay Agentes que puedan seguir corriendo.",
        )
    return Validacion(
        4,
        "sin Agentes en vuelo",
        Veredicto.FALLA,
        "Verificar si quedan Agentes trabajando requiere el Workspace Broker, que no "
        "está implementado (pendiente `workspace-broker`).",
    )


def _v5_workspace_liberado(asunto: Asunto) -> Validacion:
    if asunto.estado_contenedor is None:
        return Validacion(
            5, "workspace liberado", Veredicto.NO_APLICA, "El Asunto nunca tuvo Workspace."
        )
    if asunto.estado_contenedor is EstadoContenedor.DESTRUIDO:
        return Validacion(
            5, "workspace liberado", Veredicto.OK, "El Workspace quedó en 'destruido'."
        )
    return Validacion(
        5,
        "workspace liberado",
        Veredicto.FALLA,
        f"El Workspace está en '{asunto.estado_contenedor.value}'; hay que liberarlo "
        f"antes de cerrar.",
    )


def evaluar(asunto: Asunto, ruta_cierre: Path, ruta_bitacora: Path | None) -> Cierre:
    """Corre las cinco validaciones de ADR-0019, en orden."""
    return Cierre(
        (
            _v1_trabajo_guardado(asunto),
            _v2_merge_cerrado(asunto),
            _v3_documentado(ruta_cierre, ruta_bitacora),
            _v4_sin_agentes_en_vuelo(asunto),
            _v5_workspace_liberado(asunto),
        )
    )


def ruta_de_bitacora(repo_encargado: str | None, asunto: Asunto) -> Path | None:
    """Dónde va la entrada de bitácora de este Asunto (ADR-0021)."""
    if not repo_encargado:
        return None
    fecha = (asunto.creado or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    return Path(repo_encargado).expanduser() / "bitacora" / f"{fecha}-{asunto.id}.md"


def escribir_bitacora(ruta: Path, asunto: Asunto, resumen: str) -> Path:
    """Escribe el resumen durable del Asunto en el repo `encargado/` (ADR-0021).

    Es el resumen, no el transcript: el historial crudo se queda en `~/.jafne/`
    (ADR-0018) porque es estado operativo, no documentación del proyecto.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    cerrado = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ruta.write_text(
        f"# {asunto.titulo or asunto.id}\n\n"
        f"- **Asunto**: `{asunto.id}`\n"
        f"- **Proyecto**: {asunto.proyecto}\n"
        f"- **Rama**: {asunto.rama or '(sin rama)'}\n"
        f"- **Cerrado**: {cerrado}\n\n"
        f"{resumen.strip()}\n",
        encoding="utf-8",
    )
    return ruta
