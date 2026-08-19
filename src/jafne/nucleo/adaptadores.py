"""Qué proveedores tienen adaptador escrito, y qué pasa si se elige uno que no (ADR-0028).

Esta es una categoría que JAFNE no sabía expresar: **decidido pero no implementado**.

No va a `pendientes.py`, que es explícitamente el registro de *decisiones que todavía no se
tomaron*. Acá la decisión está tomada —ADR-0010 declaró soportados a Claude Code y a la
familia OpenAI— y lo que falta es el trabajo. Confundirlas vaciaría de significado al
registro que hace legible el estado de diseño, que es justo lo que lo hace útil.

Por eso el error es propio y distinto de `DecisionPendiente`: uno dice *"nadie decidió
esto todavía"* y el otro *"está decidido, falta escribirlo"*. Son dos respuestas distintas
para quien las lea, y la acción que sigue a cada una también.
"""

from __future__ import annotations

#: Proveedores cuyo adaptador de sesión existe hoy (ADR-0028).
#:
#: El resto sigue **soportado por diseño** (ADR-0010) y declarado en `cerebros.yaml`: se
#: dejan a la vista fallando explícito en vez de sacarlos, porque un cerebro visible que
#: falla informa y uno ausente miente por omisión.
PROVEEDORES_CON_ADAPTADOR: frozenset[str] = frozenset({"anthropic"})


class AdaptadorNoImplementado(RuntimeError):
    """Se eligió un cerebro de un proveedor soportado que todavía no tiene adaptador."""

    def __init__(self, proveedor: str) -> None:
        self.proveedor = proveedor
        implementados = ", ".join(sorted(PROVEEDORES_CON_ADAPTADOR)) or "ninguno"
        super().__init__(
            f"El proveedor '{proveedor}' está soportado por diseño (ADR-0010) pero su "
            f"adaptador todavía no se implementó (ADR-0028). Con adaptador: "
            f"{implementados}. No es una decisión pendiente: es trabajo pendiente."
        )


#: Adaptadores realmente construidos, por proveedor.
#:
#: Está vacío a propósito, y la distinción con `PROVEEDORES_CON_ADAPTADOR` importa:
#: ese conjunto dice **en alcance** (ADR-0028 decidió que se implementa Anthropic), este
#: dice **construido**. Confundirlos haría que el panel prometa un chat que no existe.
REGISTRO: dict[str, object] = {}


class AdaptadorNoConstruido(RuntimeError):
    """El adaptador está decidido y en alcance, pero todavía no se escribió."""

    def __init__(self, proveedor: str) -> None:
        self.proveedor = proveedor
        super().__init__(
            f"El adaptador de '{proveedor}' está decidido y su contrato congelado "
            f"(ADR-0031), pero todavía no se escribió. No falta decidir nada: falta "
            f"código."
        )


def hay_adaptador(proveedor: str) -> bool:
    """Si ese proveedor está **en alcance** para tener adaptador (ADR-0028).

    No dice que el adaptador exista — para eso está `obtener()`. Es lo que se muestra al
    listar cerebros: un proveedor fuera de alcance no se va a poder usar ni cuando haya
    código, y eso es lo que el Usuario necesita ver al elegir.
    """
    return proveedor in PROVEEDORES_CON_ADAPTADOR


def exigir(proveedor: str) -> None:
    """Falla si el proveedor está fuera de alcance. Se llama al *usar* un cerebro."""
    if not hay_adaptador(proveedor):
        raise AdaptadorNoImplementado(proveedor)


def obtener(proveedor: str) -> object:
    """El adaptador de ese proveedor, si existe.

    Dos fallos distintos a propósito: fuera de alcance es `AdaptadorNoImplementado` (hay
    una decisión detrás), y en alcance pero sin escribir es `AdaptadorNoConstruido` (hay
    trabajo detrás). Ninguno de los dos es `DecisionPendiente`: eso sería decir que falta
    decidir algo, y no falta.
    """
    exigir(proveedor)
    adaptador = REGISTRO.get(proveedor)
    if adaptador is None:
        raise AdaptadorNoConstruido(proveedor)
    return adaptador
