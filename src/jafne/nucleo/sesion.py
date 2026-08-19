"""El contrato neutral de sesión que implementa cada adaptador (ADR-0031).

El lean original era *adjuntarse* a una sesión viva del proveedor. El relevamiento del
2026-08-18 mostró que eso no existe: las sesiones del Agent SDK son **reanudables**, no
adjuntables — un transcript en disco al que se vuelve por id—, y la API experimental que sí
ofrecía `send`/`stream` fue removida.

De ahí sale la forma de este contrato y quién es dueño de qué: **el proceso del agente es
de JAFNE**, y el panel se adjunta a JAFNE, no al proveedor. Multiplexar observadores no es
algo que el proveedor vaya a resolver, así que lo resuelve el nivel de arriba.

El contrato se congela **antes y aparte** del primer adaptador (ADR-0028): si se escribiera
después, el adaptador *sería* el contrato y el agnosticismo de ADR-0003 quedaría sin
respaldo. Por eso cada operación de acá tiene que poder contestar *"¿cómo la implementaría
el piso genérico sobre una CLI?"* — y las cuatro pueden, porque la CLI expone `-p`,
`--resume` y `--output-format json`.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from .modelos import Suscripcion
from .tamanos import Tamano


class TipoEvento(StrEnum):
    """Lo que un turno puede emitir, en vocabulario neutral.

    Es un catálogo chico a propósito: traducir los eventos ricos de cada proveedor a estos
    pocos es trabajo del adaptador. Un contrato que creciera hasta cubrir todo lo que un
    proveedor sabe emitir dejaría de ser neutral.
    """

    TEXTO = "texto"
    """Texto del agente, para mostrarle al Usuario."""

    HERRAMIENTA = "herramienta"
    """El agente usó una herramienta. El detalle va en `datos`."""

    RESULTADO = "resultado"
    """El turno terminó. Trae el costo y el id de sesión."""

    ERROR = "error"
    """El turno falló. `texto` explica por qué."""


@dataclass(frozen=True)
class Evento:
    """Una unidad de lo que pasa en un turno."""

    tipo: TipoEvento
    texto: str = ""
    datos: dict[str, Any] = field(default_factory=dict)

    def a_dict(self) -> dict[str, Any]:
        return {"tipo": self.tipo.value, "texto": self.texto, "datos": self.datos}


@runtime_checkable
class AdaptadorSesion(Protocol):
    """Lo que JAFNE necesita de un proveedor para poder usarlo (ADR-0031).

    Cuatro operaciones, que son los cuatro trabajos que ADR-0025 ya le había adjudicado al
    adaptador. Nada más: todo lo que no esté acá es específico de un proveedor y no puede
    subir al contrato sin romper ADR-0003.
    """

    proveedor: str

    def abrir(self, directorio: str, tamano: Tamano) -> str:
        """Arranca una sesión nueva y devuelve su id."""
        ...

    def reanudar(self, id_sesion: str) -> None:
        """Vuelve a una sesión existente con su contexto entero.

        Rehidratar es **reanudar**, no reinyectar: si el proveedor sabe volver a su propia
        sesión, no hay que volver a contarle la conversación (ADR-0018, ADR-0031).
        """
        ...

    def emitir(self, mensaje: str) -> Iterator[Evento]:
        """Manda un turno y devuelve el flujo de eventos que produce."""
        ...

    def saldo(self) -> Suscripcion | None:
        """Lo que el cliente del proveedor sepa decir sobre consumo (ADR-0025).

        `None` cuando no sabe decir nada, que no es lo mismo que decir cero.
        """
        ...


def cumple_contrato(candidato: object) -> bool:
    """Si un objeto sirve como adaptador.

    Existe para que el contrato sea verificable sin que haya todavía una implementación
    real: es la prueba de que se puede congelar antes que el adaptador, como pide
    ADR-0028.
    """
    return isinstance(candidato, AdaptadorSesion)
