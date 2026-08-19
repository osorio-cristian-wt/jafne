"""Modelos de lo que vive en `~/.jafne/` (ADR-0007, ADR-0018).

Cuatro cosas: proyectos conocidos (`proyectos.yaml`), cerebros disponibles
(`cerebros.yaml`), el saldo observado de cada suscripción (`saldo.yaml`, ADR-0025) y los
Asuntos (`asuntos/<proyecto>/<asunto-id>/`), donde cada Asunto tiene `meta.yaml`,
`cierre.md` y su `historial.jsonl`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .estados import (
    DESCRIPCIONES,
    DESCRIPCIONES_CONTENEDOR,
    EstadoAsunto,
    EstadoContenedor,
    estado_efectivo,
    parsear,
    parsear_contenedor,
)
from .tamanos import Tamano


def a_utc(valor: Any) -> datetime | None:
    """Normaliza a `datetime` con zona UTC.

    PyYAML devuelve `datetime` nativo para timestamps ISO, pero puede venir naive (sin
    zona) o como texto si el archivo lo escribió otra herramienta. Un naive se interpreta
    como UTC en vez de asumir la zona de la máquina, que cambiaría el resultado del
    timeout de 3 minutos según dónde corra el panel.
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        momento = valor
    else:
        try:
            momento = datetime.fromisoformat(str(valor).strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def _iso(momento: datetime | None) -> str | None:
    return momento.isoformat() if momento else None


@dataclass(frozen=True)
class Proyecto:
    """Un proyecto conocido: su repo `encargado/` y poco más (ADR-0007)."""

    id: str
    nombre: str
    encargado: str | None = None
    descripcion: str | None = None

    def a_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "encargado": self.encargado,
            "descripcion": self.descripcion,
        }


@dataclass(frozen=True)
class Ventana:
    """Una ventana de límite de una suscripción, con lo que queda y cuándo resetea.

    Las ventanas son de **tiempo, no de dinero**: Claude Code expone una de 5 horas y una
    semanal, cada una con su reset (`investigacion/medicion-de-consumo/fuentes/03`). Por
    eso el saldo sin su horizonte de reset no alcanza para decidir: "queda poco y resetea
    en 40 minutos" y "queda poco y resetea el lunes" llevan a decisiones opuestas.

    `restante` es la fracción del límite que queda, de 0 a 1.
    """

    nombre: str
    restante: float | None = None
    resetea: datetime | None = None

    @property
    def agotada(self) -> bool:
        """Sin saldo: cero es cero.

        Es un hecho, no una política: *cuán cerca del límite* amerita actuar lo fija
        ADR-0026 y se calcula en `nucleo/senal_saldo.py`, que además decide si eso
        significa conmutar de proveedor o esperar el reset.
        """
        return self.restante is not None and self.restante <= 0

    def a_dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "restante": self.restante,
            "resetea": _iso(self.resetea),
            "agotada": self.agotada,
        }


@dataclass(frozen=True)
class Suscripcion:
    """El saldo observado de la suscripción de un proveedor (ADR-0025).

    Es del **proveedor**, no del cerebro: el límite pertenece a la suscripción y se
    comparte entre todos los proyectos y todos los modelos de esa familia, así que tres
    cerebros de OpenAI miran el mismo saldo.

    Las ventanas se exponen todas, sin colapsarlas en un único "hay saldo", y ADR-0026
    explicó por qué eso estaba bien: no se combinan en una señal porque **producen
    acciones distintas**. Una ventana escasa que resetea pronto se espera; una que resetea
    lejos obliga a conmutar de proveedor. Colapsarlas perdería justo esa diferencia.
    """

    proveedor: str
    ventanas: tuple[Ventana, ...] = ()
    plan: str | None = None
    observado: datetime | None = None
    fuente: str | None = None

    @property
    def agotado(self) -> bool:
        """Alguna ventana en cero. Si una lo está, la llamada no entra por ninguna."""
        return any(v.agotada for v in self.ventanas)

    def a_dict(self) -> dict[str, Any]:
        return {
            "proveedor": self.proveedor,
            "plan": self.plan,
            "observado": _iso(self.observado),
            "fuente": self.fuente,
            "agotado": self.agotado,
            "ventanas": [v.a_dict() for v in self.ventanas],
        }


@dataclass(frozen=True)
class Cerebro:
    """Un proveedor + modelo disponible para ejecutar un rol (ADR-0003, ADR-0010).

    `tamano` ordena por capacidad con un catálogo **común a todos los proveedores**
    (ADR-0030): `chico` / `medio` / `grande` / `gigante`. Reemplaza al par de vocabularios
    que convivían antes —el interno de la familia OpenAI (ADR-0022) y un
    `liviano`/`intermedio`/`pesado` que nunca tuvo ADR—, y es lo que permite al Encargado
    pedir "un cerebro grande" sin nombrar un modelo.

    `saldo` es el de su proveedor (ADR-0025), y es la otra entrada de la decisión de qué
    cerebro usar: se elige **tamaño** por dificultad de la tarea y **proveedor** por saldo
    disponible. Dos ejes independientes.

    `adaptador` dice si ese proveedor se puede usar hoy (ADR-0028). Un cerebro sin
    adaptador sigue siendo soportado por diseño: se lista, y falla al usarse.
    """

    id: str
    proveedor: str
    modelo: str | None = None
    tamano: Tamano | None = None
    saldo: Suscripcion | None = None
    adaptador: bool = True

    def a_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "proveedor": self.proveedor,
            "modelo": self.modelo,
            "tamano": self.tamano.value if self.tamano else None,
            "adaptador": self.adaptador,
            "saldo": self.saldo.a_dict() if self.saldo else None,
        }


@dataclass(frozen=True)
class Mensaje:
    """Una línea del historial de conversación de un Asunto (ADR-0018).

    El historial es un artefacto persistente del **Asunto**, no del contenedor: por eso
    sobrevive a que el Workspace se destruya y está disponible al reabrir.
    """

    momento: datetime
    rol: str
    texto: str

    def a_dict(self) -> dict[str, Any]:
        return {"momento": _iso(self.momento), "rol": self.rol, "texto": self.texto}

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> Mensaje:
        return cls(
            momento=a_utc(datos.get("momento")) or datetime.now(timezone.utc),
            rol=str(datos.get("rol") or "desconocido"),
            texto=str(datos.get("texto") or ""),
        )


@dataclass(frozen=True)
class Asunto:
    """Un Asunto: la unidad persistente de trabajo del Encargado (ADR-0006).

    Los dos ejes de estado son independientes (ADR-0008) y ambos tienen catálogo cerrado:
    `estado_asunto` lo escribe el Encargado (ADR-0009) y `estado_contenedor` el Workspace
    Broker (ADR-0016).
    """

    proyecto: str
    id: str
    estado_asunto: EstadoAsunto
    ultima_actividad: datetime | None = None
    estado_contenedor: EstadoContenedor | None = None
    pregunta_pendiente: bool = False
    motivo: str | None = None
    titulo: str | None = None
    rama: str | None = None
    preview_url: str | None = None
    creado: datetime | None = None
    tiene_cierre: bool = False
    mensajes: int = 0
    #: Repos que tocó el Asunto, para poder verificar el cierre (ADR-0019). Los escribe
    #: el Encargado a medida que trabaja; sin esto no hay dónde mirar el estado de git.
    repos: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def estado_efectivo(self) -> EstadoAsunto:
        """`estado_asunto` con el timeout de 3 minutos ya aplicado (ADR-0009/ADR-0017)."""
        return estado_efectivo(
            self.estado_asunto, self.ultima_actividad, self.pregunta_pendiente
        )

    @property
    def abierto(self) -> bool:
        return self.estado_asunto is not EstadoAsunto.CERRADO

    @property
    def reabrible(self) -> bool:
        """Un Asunto cerrado se puede reabrir con su contexto (ADR-0018)."""
        return self.estado_asunto is EstadoAsunto.CERRADO

    def a_dict(self) -> dict[str, Any]:
        efectivo = self.estado_efectivo
        contenedor = self.estado_contenedor
        return {
            "proyecto": self.proyecto,
            "id": self.id,
            "titulo": self.titulo,
            "estado_asunto": self.estado_asunto.value,
            "estado_efectivo": efectivo.value,
            "estado_por_timeout": efectivo is not self.estado_asunto,
            "descripcion_estado": DESCRIPCIONES[efectivo],
            "pregunta_pendiente": self.pregunta_pendiente,
            "estado_contenedor": contenedor.value if contenedor else None,
            "descripcion_contenedor": (
                DESCRIPCIONES_CONTENEDOR[contenedor] if contenedor else None
            ),
            "motivo": self.motivo,
            "rama": self.rama,
            "preview_url": self.preview_url,
            "ultima_actividad": _iso(self.ultima_actividad),
            "creado": _iso(self.creado),
            "abierto": self.abierto,
            "reabrible": self.reabrible,
            "tiene_cierre": self.tiene_cierre,
            "mensajes": self.mensajes,
            "repos": list(self.repos),
        }

    @classmethod
    def desde_meta(
        cls,
        proyecto: str,
        asunto_id: str,
        meta: dict[str, Any],
        tiene_cierre: bool = False,
        mensajes: int = 0,
    ) -> Asunto:
        """Construye un Asunto desde el contenido de su `meta.yaml`."""
        conocidas = {
            "proyecto",
            "id",
            "asunto_id",
            "estado_asunto",
            "estado_contenedor",
            "pregunta_pendiente",
            "motivo",
            "titulo",
            "rama",
            "preview_url",
            "ultima_actividad",
            "creado",
            "repos",
        }
        return cls(
            proyecto=proyecto,
            id=asunto_id,
            estado_asunto=parsear(meta.get("estado_asunto", EstadoAsunto.INICIANDO)),
            ultima_actividad=a_utc(meta.get("ultima_actividad")),
            estado_contenedor=parsear_contenedor(meta.get("estado_contenedor")),
            pregunta_pendiente=bool(meta.get("pregunta_pendiente", False)),
            motivo=meta.get("motivo"),
            titulo=meta.get("titulo"),
            rama=meta.get("rama"),
            preview_url=meta.get("preview_url"),
            creado=a_utc(meta.get("creado")),
            tiene_cierre=tiene_cierre,
            mensajes=mensajes,
            repos=tuple(meta.get("repos") or ()),
            extra={k: v for k, v in meta.items() if k not in conocidas},
        )

    def a_meta(self) -> dict[str, Any]:
        """El `meta.yaml` que corresponde a este Asunto.

        Se escribe `estado_asunto`, nunca el efectivo: el timeout es una lectura, no un
        hecho persistido (ADR-0017).
        """
        meta: dict[str, Any] = {
            "proyecto": self.proyecto,
            "asunto_id": self.id,
            "titulo": self.titulo,
            "estado_asunto": self.estado_asunto.value,
            "pregunta_pendiente": self.pregunta_pendiente,
            "estado_contenedor": (
                self.estado_contenedor.value if self.estado_contenedor else None
            ),
            "motivo": self.motivo,
            "rama": self.rama,
            "preview_url": self.preview_url,
            "ultima_actividad": _iso(self.ultima_actividad),
            "creado": _iso(self.creado),
            "repos": list(self.repos) or None,
        }
        meta.update(self.extra)
        # `pregunta_pendiente` se escribe siempre, incluso en False: su ausencia y su
        # valor negativo significan lo mismo, pero explícito se lee mejor en el archivo.
        return {
            k: v for k, v in meta.items() if v is not None or k == "pregunta_pendiente"
        }
