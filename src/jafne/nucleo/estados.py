"""Los dos ejes de estado de un Asunto, ambos con catálogo cerrado.

- `estado_asunto` — lo escribe el Encargado ([ADR-0009]). Cinco valores.
- `estado_contenedor` — lo escribe el Workspace Broker ([ADR-0016]). Cuatro valores.

Son **independientes** (ADR-0008): cualquier combinación es representable, y varias son
normales (`esperando_respuesta` + `suspendido`, `cerrado` + `destruido`). Agregar un valor
a cualquiera de los dos requiere un ADR que reemplace al suyo, no una edición acá.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum

#: Sin respuesta a una pregunta pendiente durante más de este lapso, un Asunto
#: `interactuando_con_el_usuario` se lee como `esperando_respuesta` (ADR-0009).
TIMEOUT_SIN_RESPUESTA = timedelta(minutes=3)


class EstadoAsunto(StrEnum):
    """Los cinco valores posibles de `estado_asunto` (ADR-0009)."""

    INICIANDO = "iniciando"
    INTERACTUANDO_CON_EL_USUARIO = "interactuando_con_el_usuario"
    ESPERANDO_RESPUESTA = "esperando_respuesta"
    CERRANDO = "cerrando"
    CERRADO = "cerrado"


class EstadoContenedor(StrEnum):
    """Los cuatro valores posibles de `estado_contenedor` (ADR-0016).

    Un Asunto **sin** este campo nunca tuvo Workspace, que no es lo mismo que
    `destruido` (tuvo uno y se liberó).
    """

    CREANDO = "creando"
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    DESTRUIDO = "destruido"


DESCRIPCIONES: dict[EstadoAsunto, str] = {
    EstadoAsunto.INICIANDO: "Se crea o retoma el contenedor; el trabajo todavía no arrancó.",
    EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO: "Actividad en curso, sin nada pendiente de respuesta.",
    EstadoAsunto.ESPERANDO_RESPUESTA: "Se preguntó algo y pasaron más de 3 minutos sin respuesta.",
    EstadoAsunto.CERRANDO: "Corriendo la skill de cierre: guardado, merge, documentación, agentes, workspace.",
    EstadoAsunto.CERRADO: "La skill de cierre terminó OK; el Asunto queda guardado y reabrible.",
}

DESCRIPCIONES_CONTENEDOR: dict[EstadoContenedor, str] = {
    EstadoContenedor.CREANDO: "Aprovisionando el Workspace: imagen, red del proyecto, montajes.",
    EstadoContenedor.ACTIVO: "El Workspace está en pie y acepta trabajo.",
    EstadoContenedor.SUSPENDIDO: "El Workspace existe pero no consume cómputo.",
    EstadoContenedor.DESTRUIDO: "El Workspace se liberó; el Asunto puede seguir sin él.",
}

#: Transiciones de `estado_asunto`, tal cual el diagrama de ADR-0009.
TRANSICIONES: dict[EstadoAsunto, frozenset[EstadoAsunto]] = {
    EstadoAsunto.INICIANDO: frozenset({EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO}),
    EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO: frozenset(
        {EstadoAsunto.ESPERANDO_RESPUESTA, EstadoAsunto.CERRANDO}
    ),
    EstadoAsunto.ESPERANDO_RESPUESTA: frozenset(
        {EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO, EstadoAsunto.CERRANDO}
    ),
    EstadoAsunto.CERRANDO: frozenset(
        {EstadoAsunto.CERRADO, EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO}
    ),
    EstadoAsunto.CERRADO: frozenset({EstadoAsunto.INICIANDO}),
}

#: Transiciones de `estado_contenedor`, tal cual el diagrama de ADR-0016.
TRANSICIONES_CONTENEDOR: dict[EstadoContenedor, frozenset[EstadoContenedor]] = {
    EstadoContenedor.CREANDO: frozenset({EstadoContenedor.ACTIVO}),
    EstadoContenedor.ACTIVO: frozenset(
        {EstadoContenedor.SUSPENDIDO, EstadoContenedor.DESTRUIDO}
    ),
    EstadoContenedor.SUSPENDIDO: frozenset(
        {EstadoContenedor.ACTIVO, EstadoContenedor.DESTRUIDO}
    ),
    EstadoContenedor.DESTRUIDO: frozenset({EstadoContenedor.CREANDO}),
}


class EstadoDesconocido(ValueError):
    """Un valor que no está en el catálogo cerrado de su eje."""


class TransicionInvalida(ValueError):
    """Un salto de estado que el diagrama de su ADR no permite."""


def _parsear(valor, enum, adr: str):
    if isinstance(valor, enum):
        return valor
    try:
        return enum(str(valor).strip())
    except ValueError:
        validos = ", ".join(e.value for e in enum)
        raise EstadoDesconocido(
            f"'{valor}' no es un {enum.__name__} válido. El catálogo es cerrado "
            f"({adr}): {validos}."
        ) from None


def parsear(valor: str | EstadoAsunto) -> EstadoAsunto:
    """Convierte texto de `meta.yaml` a `EstadoAsunto`, o falla explícito."""
    return _parsear(valor, EstadoAsunto, "ADR-0009")


def parsear_contenedor(valor: str | EstadoContenedor | None) -> EstadoContenedor | None:
    """Ídem para `estado_contenedor`. `None` = el Asunto nunca tuvo Workspace."""
    if valor is None:
        return None
    return _parsear(valor, EstadoContenedor, "ADR-0016")


def transicion_valida(desde: EstadoAsunto, hacia: EstadoAsunto) -> bool:
    return hacia in TRANSICIONES[desde]


def validar_transicion(desde: EstadoAsunto, hacia: EstadoAsunto) -> None:
    """Levanta `TransicionInvalida` si el salto no está en el diagrama de ADR-0009."""
    if not transicion_valida(desde, hacia):
        permitidos = ", ".join(sorted(e.value for e in TRANSICIONES[desde]))
        raise TransicionInvalida(
            f"'{desde.value}' → '{hacia.value}' no es una transición válida (ADR-0009). "
            f"Desde '{desde.value}' solo se puede ir a: {permitidos}."
        )


def validar_transicion_contenedor(
    desde: EstadoContenedor | None, hacia: EstadoContenedor
) -> None:
    """Ídem para `estado_contenedor` (ADR-0016).

    Desde `None` (nunca tuvo Workspace) solo se puede empezar por `creando`.
    """
    if desde is None:
        if hacia is not EstadoContenedor.CREANDO:
            raise TransicionInvalida(
                f"Un Asunto sin Workspace solo puede pasar a 'creando', no a "
                f"'{hacia.value}' (ADR-0016)."
            )
        return
    if hacia not in TRANSICIONES_CONTENEDOR[desde]:
        permitidos = ", ".join(sorted(e.value for e in TRANSICIONES_CONTENEDOR[desde]))
        raise TransicionInvalida(
            f"'{desde.value}' → '{hacia.value}' no es una transición válida (ADR-0016). "
            f"Desde '{desde.value}' solo se puede ir a: {permitidos}."
        )


def estado_efectivo(
    estado: EstadoAsunto,
    ultima_actividad: datetime | None,
    pregunta_pendiente: bool = False,
    ahora: datetime | None = None,
) -> EstadoAsunto:
    """El estado que corresponde *ahora*, aplicando el timeout de ADR-0009.

    El timeout es **derivado, nunca persistido** ([ADR-0017]): se calcula al leer, así
    que no puede desincronizarse. Y solo aplica si hay una pregunta efectivamente
    pendiente — un Asunto trabajando en background sin nada que preguntar no está
    "esperando respuesta", está en modo delegado (ADR-0002).
    """
    if not pregunta_pendiente or ultima_actividad is None:
        return estado
    if estado is not EstadoAsunto.INTERACTUANDO_CON_EL_USUARIO:
        return estado
    ahora = ahora or datetime.now(timezone.utc)
    if ahora - ultima_actividad > TIMEOUT_SIN_RESPUESTA:
        return EstadoAsunto.ESPERANDO_RESPUESTA
    return estado
