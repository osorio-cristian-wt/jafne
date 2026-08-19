"""Registro de las decisiones que todavía no se tomaron.

Regla de ADR-0015: *lo que no está decidido no se programa*. Cada punto del sistema
que depende de una pregunta abierta se declara acá en vez de resolverse con un default
improvisado. El registro es consultable (`GET /api/pendientes`, `jafne pendientes`), así
que el estado de diseño de JAFNE se ve desde el propio JAFNE.

Sacar algo de este registro es el paso final de graduar una investigación a ADR, o de
responder una pregunta abierta que un ADR dejó anotada. El 2026-08-11 salieron siete
entradas de una vez (ADR-0016 a ADR-0022) y entraron tres nuevas que esos mismos ADRs
dejaron abiertas.

Graduar rara vez vacía una entrada: la mueve. ADR-0023 a ADR-0025 contestaron el *qué* de
los sprints y del consumo, y lo que quedó bloqueado pasó a ser el *cómo* — por eso
`uso-suscripciones` se volvió `medicion-de-consumo` en vez de desaparecer. El 2026-08-18
pasó de las dos maneras, y a lo grande: salieron enteras `conmutacion-por-saldo` y
`trabajo-programado` (ADR-0026, ADR-0029), y después `chat-asistente`, `chat-encargado` y
`adaptador-agents`, las tres de un saque, cuando ADR-0031 contestó quién es dueño del
proceso del agente. `workspace-broker` se afinó dos veces en el mismo día —ADR-0027 fijó
quién declara el aislamiento, ADR-0032 a qué runtime mapea— hasta quedarse solo con el
descubrimiento de servicios.

El 2026-08-19 volvió a pasar, y es el ejemplo más limpio: `tls-y-rotacion-de-token`
llevaba dos preguntas pegadas y ADR-0038 contestó una sola —el TLS—, así que la entrada se
renombró a `rotacion-de-token` en vez de borrarse. Contestar la mitad y tachar el todo es
la forma más rápida de que este registro deje de servir.

**Esto no registra trabajo pendiente, sino decisiones pendientes.** Un adaptador decidido
y todavía no escrito no va acá: va con su propia señal (`nucleo/adaptadores.py`, ADR-0028),
porque si las dos cosas se mezclan la pregunta *"¿qué falta decidir?"* deja de tener una
respuesta confiable, que es justo lo que hace útil a este registro.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Pendiente:
    """Una decisión abierta que bloquea una funcionalidad concreta."""

    clave: str
    titulo: str
    bloqueado_por: str
    pregunta: str

    def a_dict(self) -> dict[str, str]:
        return asdict(self)


class DecisionPendiente(RuntimeError):
    """Se invocó algo que depende de una decisión todavía no tomada."""

    def __init__(self, clave: str) -> None:
        self.pendiente = obtener(clave)
        super().__init__(
            f"{self.pendiente.titulo} — bloqueado por {self.pendiente.bloqueado_por}. "
            f"{self.pendiente.pregunta}"
        )


_REGISTRO: tuple[Pendiente, ...] = (
    Pendiente(
        clave="medicion-de-consumo",
        titulo="Cómo observa Infraestructura el consumo de los agentes",
        bloqueado_por="ADR-0025 + investigacion/medicion-de-consumo",
        pregunta=(
            "ADR-0025 fijó qué se mide (saldo, no gasto) y quién lleva la cuenta "
            "(Infraestructura, la única con vista de todos los agentes). Falta el cómo: "
            "el Broker crea los Workspaces, pero las llamadas al modelo las hacen los "
            "agentes adentro. O pasan por un punto que mide, o cada agente reporta lo "
            "suyo — son dos arquitecturas distintas. Cruza con que `/usage` de Claude "
            "Code muestra el saldo pero no está verificado que tenga salida consumible "
            "por un proceso. Mientras tanto el saldo se carga a mano (`jafne saldo`)."
        ),
    ),
    Pendiente(
        clave="historial-desbordado",
        titulo="Historial más largo que la ventana de contexto",
        bloqueado_por="ADR-0018",
        pregunta=(
            "Al reabrir un Asunto largo, el historial puede no entrar en el contexto del "
            "cerebro que retoma. ¿Resumen, ventana móvil, o el cierre.md como sustituto? "
            "ADR-0031 achicó el problema: si el proveedor sabe reanudar su propia sesión, "
            "la ventana la administra él con su compactación. La pregunta queda solo para "
            "el piso genérico, el que reinyecta el historial a mano."
        ),
    ),
    Pendiente(
        clave="workspace-broker",
        titulo="Descubrimiento de los servicios de un proyecto",
        bloqueado_por="ADR-0011 + investigacion/orquestacion-entornos",
        pregunta=(
            "Lo que quedaba del Broker se fue cerrando: ADR-0027 fijó quién declara el "
            "aislamiento y ADR-0032 a qué runtime mapea cada clase. Queda cómo un "
            "Workspace descubre los servicios del proyecto —base de datos, colas, otros "
            "repos— con la red restringida por proyecto de ADR-0011: si se declaran en "
            "`engineering.yaml`, si los inyecta el Broker, o si se resuelven por nombre "
            "dentro de la red del proyecto. Crear Workspaces de verdad ya no está "
            "bloqueado por una decisión: es trabajo."
        ),
    ),
    Pendiente(
        clave="sprints",
        titulo="Herramienta de sprints y vocabulario mínimo para hablarle",
        bloqueado_por="ADR-0023 + ADR-0014 + investigacion/gestion-de-sprints",
        pregunta=(
            "El modelo ya está decidido: Sprint y Asunto son ejes independientes y el "
            "estado vive en la herramienta externa que el equipo ya mira (ADR-0023). "
            "Falta cuál —criterio práctico, la que el equipo use— y qué vocabulario "
            "mínimo necesita JAFNE para hablarle a cualquiera: Jira tiene *sprints* y "
            "Linear tiene *cycles*, y el desajuste es conceptual, no de nombre. También "
            "falta si habla el Encargado desde su Workspace, con la red restringida por "
            "ADR-0011, o el Asistente desde afuera."
        ),
    ),
    Pendiente(
        clave="protocolo-asignacion-tareas",
        titulo="Protocolo de asignación de tareas Encargado → Agente",
        bloqueado_por="investigacion/protocolo-de-asignacion-de-tareas",
        pregunta=(
            "¿Task de A2A, patrón tipo CrewAI, o MCP-handoff? Es el hop 4 y se puede "
            "decidir aparte de los hops conversacionales: no bloquea al panel."
        ),
    ),
    Pendiente(
        clave="cerebro-del-encargado-conversando",
        titulo="Con qué cerebro conversa un Encargado que todavía no tiene tarea",
        bloqueado_por="ADR-0033 + ADR-0003",
        pregunta=(
            "ADR-0033 fijó que el Asistente corre en `medio` y que Encargado y Agente no "
            "tienen tamaño por defecto: los elige el Encargado **por tarea**. El chat del "
            "panel con un Encargado (ADR-0013) rompe ese supuesto — es una conversación "
            "sin tarea todavía, así que no hay nada de donde derivar el tamaño. ¿Conversa "
            "en `medio` como el Asistente hasta que haya trabajo, se declara un default "
            "aparte en `cerebros.yaml`, o el chat obliga a abrir un Asunto primero? Se "
            "encontró al escribir el adaptador, no antes: el contrato no lo pedía."
        ),
    ),
    Pendiente(
        clave="rotacion-de-token",
        titulo="Rotación del token del panel y del nodo de voz",
        bloqueado_por="ADR-0020 + ADR-0038",
        pregunta=(
            "ADR-0038 contestó la mitad de lo que esta entrada tenía: el panel puede "
            "servir TLS con una CA propia, y se decidió por qué —desbloquear el micrófono "
            "del navegador, no agregar confidencialidad, que la malla ya da—. Lo que sigue "
            "abierto es el token: cada cuánto rota, quién lo rota y qué se hace si se "
            "filtra. Ahora son dos tokens, uno por servicio, así que la respuesta tiene "
            "que valer para los dos."
        ),
    ),
    Pendiente(
        clave="sincronia-entre-maquinas",
        titulo="Sincronía de `~/.jafne/` entre máquinas",
        bloqueado_por="ADR-0021",
        pregunta=(
            "ADR-0021 resolvió la pérdida de la memoria durable (va a la bitácora del repo "
            "`encargado/`), pero no qué pasa si el Usuario opera JAFNE desde dos máquinas "
            "y cada una tiene su propio estado operativo."
        ),
    ),
)

_POR_CLAVE: dict[str, Pendiente] = {p.clave: p for p in _REGISTRO}


def todos() -> list[Pendiente]:
    """Todas las decisiones pendientes, en orden de declaración."""
    return list(_REGISTRO)


def obtener(clave: str) -> Pendiente:
    try:
        return _POR_CLAVE[clave]
    except KeyError:
        raise KeyError(
            f"'{clave}' no está en el registro de pendientes. Si es una decisión abierta "
            f"nueva, declarala en src/jafne/pendientes.py antes de referenciarla."
        ) from None
