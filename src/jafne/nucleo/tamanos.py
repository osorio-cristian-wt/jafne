"""Tamaño de cerebro: el catálogo común que cruza proveedores (ADR-0030).

Antes de esta decisión convivían tres vocabularios que no se hablaban —los nombres de
modelo de cada proveedor, los nombres propios de la familia OpenAI, y un
`liviano`/`intermedio`/`pesado` que nunca tuvo ADR—, así que un Encargado no podía pedir
"un cerebro grande" sin nombrar un modelo, que es justo el acople que ADR-0003 evita.

El catálogo es **cerrado**, como los de ADR-0009, ADR-0016 y ADR-0027: agregar un valor
requiere un ADR que reemplace a ADR-0030.

El tamaño **ordena**; no promete equivalencia exacta. `medio` de un proveedor y `medio` del
otro son comparables para decidir, no idénticos en capacidad.
"""

from __future__ import annotations

from enum import StrEnum


class Tamano(StrEnum):
    """Los cuatro tamaños posibles de un cerebro (ADR-0030)."""

    CHICO = "chico"
    MEDIO = "medio"
    GRANDE = "grande"
    GIGANTE = "gigante"


#: De menor a mayor capacidad. El orden es la razón de ser del catálogo.
ORDEN: tuple[Tamano, ...] = (
    Tamano.CHICO,
    Tamano.MEDIO,
    Tamano.GRANDE,
    Tamano.GIGANTE,
)

DESCRIPCIONES: dict[Tamano, str] = {
    Tamano.CHICO: "Tareas acotadas y sensibles a latencia.",
    Tamano.MEDIO: "El caballo de batalla: la mayoría del trabajo regular.",
    Tamano.GRANDE: "Trabajo difícil, de varios pasos o de horizonte largo.",
    Tamano.GIGANTE: "Lo más capaz disponible, cuando la dificultad lo justifica.",
}

#: Correspondencia tamaño → familia de modelos, por proveedor (ADR-0030).
#:
#: **Un proveedor no cubre necesariamente todos los tamaños**, y eso es un dato, no un
#: hueco a rellenar: hoy `gigante` existe solo del lado Anthropic. Cuando salga el próximo
#: modelo de cualquiera de los dos, cambia una fila de esta tabla y nada más.
CORRESPONDENCIA: dict[str, dict[Tamano, str]] = {
    "anthropic": {
        Tamano.CHICO: "haiku",
        Tamano.MEDIO: "sonnet",
        Tamano.GRANDE: "opus",
        Tamano.GIGANTE: "fable",
    },
    "openai": {
        Tamano.CHICO: "luna",
        Tamano.MEDIO: "tierra",
        Tamano.GRANDE: "sol",
    },
}

#: Vocabulario heredado que ADR-0030 reemplaza. Se traduce al leer para no romper un
#: `~/.jafne/` escrito antes de la decisión; no se escribe nunca.
EQUIVALENCIAS_HEREDADAS: dict[str, Tamano] = {
    "liviano": Tamano.CHICO,
    "intermedio": Tamano.MEDIO,
    "pesado": Tamano.GRANDE,
}


class TamanoInvalido(ValueError):
    """Un tamaño fuera del catálogo cerrado de ADR-0030."""


def parsear(valor: object) -> Tamano:
    """Convierte un valor leído de disco en un `Tamano`, o falla.

    Acepta el vocabulario heredado (`liviano`/`intermedio`/`pesado`) traduciéndolo, que es
    honrar el reemplazo de ADR-0030 y no debilitar el catálogo.
    """
    texto = str(valor or "").strip().lower()
    if texto in EQUIVALENCIAS_HEREDADAS:
        return EQUIVALENCIAS_HEREDADAS[texto]
    try:
        return Tamano(texto)
    except ValueError:
        validos = ", ".join(t.value for t in ORDEN)
        raise TamanoInvalido(
            f"'{valor}' no es un tamaño de cerebro. El catálogo de ADR-0030 es cerrado: "
            f"{validos}. Agregar uno requiere un ADR que reemplace a ADR-0030."
        ) from None


def familia(proveedor: str, tamano: Tamano) -> str | None:
    """Qué familia de modelos de ese proveedor corresponde al tamaño, si la hay."""
    return CORRESPONDENCIA.get(proveedor, {}).get(tamano)


def cubiertos(proveedor: str) -> tuple[Tamano, ...]:
    """Los tamaños que ese proveedor cubre, de menor a mayor."""
    disponibles = CORRESPONDENCIA.get(proveedor, {})
    return tuple(t for t in ORDEN if t in disponibles)


def degradar(proveedor: str, tamano: Tamano) -> Tamano | None:
    """El mayor tamaño que ese proveedor cubre sin pasarse del pedido.

    Es la consecuencia ejecutable de ADR-0026: conmutar de proveedor puede **degradar** el
    tamaño, porque el destino no siempre tiene equivalente. Un Asunto en `gigante` que
    conmuta a un proveedor sin `gigante` baja a `grande`, y eso tiene que verse.

    Devuelve `None` si el proveedor no cubre ningún tamaño igual o menor — es decir, si no
    hay a dónde degradar.
    """
    disponibles = cubiertos(proveedor)
    if not disponibles:
        return None
    tope = ORDEN.index(tamano)
    candidatos = [t for t in disponibles if ORDEN.index(t) <= tope]
    return candidatos[-1] if candidatos else None
