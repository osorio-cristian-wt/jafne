# Protocolo de asignación de tareas Encargado → Agente

- **Estado:** explorando (2026-07-23)
- **Origen:** pregunta abierta desde [jerarquía de roles](../jerarquia-de-roles/research.md)
  — el usuario no tiene una dirección previa acá, por eso pasa por investigación real en
  vez de ir directo a ADR ([ADR-0005](../../docs/adr/0005-cuando-investigar-vs-adr-directo.md)).

## El tema

JAFNE ya decidió la jerarquía y la escalación
([ADR-0002](../../docs/adr/0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md)),
pero no cómo, en concreto, el Encargado le asigna una tarea a un Agente: qué
mensaje/estructura usa, cómo el Agente reporta avance/resultado, y cómo eso se engancha
con el ciclo de vida de un Asunto
([ADR-0006](../../docs/adr/0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md)) y su
estado ([ADR-0009](../../docs/adr/0009-catalogo-cerrado-estado-asunto.md)).

## Qué hay en el mundo real

Tres corrientes distintas, según las fuentes:

1. **A2A (Agent2Agent)** — ver [`fuentes/01_a2a-protocol.md`](./fuentes/01_a2a-protocol.md).
   Protocolo abierto de Google, gobernado por Linux Foundation desde 2025, v1.0 en 2026,
   con más de 150 organizaciones adoptantes (Google, Microsoft, AWS, Salesforce, SAP,
   ServiceNow, Workday, IBM). Define **Agent Cards** (qué puede hacer un agente),
   **Tasks** (la estructura del trabajo) y transporte (HTTP/SSE/JSON-RPC 2.0). Ciclo de
   vida de una Task: `submitted → working → completed / failed / canceled`, con soporte
   multi-turno.

2. **Frameworks de orquestación (AutoGen, CrewAI, LangGraph)** — ver
   [`fuentes/02_frameworks-orquestacion.md`](./fuentes/02_frameworks-orquestacion.md).
   Tres filosofías distintas de asignación: **CrewAI** (roles + Tasks, delegación
   jerárquica explícita — la más parecida conceptualmente a Encargado→Agente),
   **LangGraph** (grafo/máquina de estados, agentes pasándose estado por nodos), y
   **AutoGen** (todo como conversación tipo GroupChat, con un selector que decide quién
   habla). Patrón común: un coordinador recibe una tarea de alto nivel, la descompone,
   despacha a workers especializados, y sintetiza resultados — coincide con el rol ya
   definido del Encargado.

3. **MCP como canal de handoff** — ver
   [`fuentes/03_mcp-handoff.md`](./fuentes/03_mcp-handoff.md). El propio Model Context
   Protocol (que JAFNE ya usa para capacidades,
   [ADR-0004](../../docs/adr/0004-capacidades-por-repositorio.md)) tiene patrones de
   *handoff*: un orquestador delega una subtarea a un sub-agente vía MCP, espera su
   resultado, y continúa o escala. El handoff se trackea con IDs de workflow y contexto
   empaquetado como recursos MCP.

## Por qué importa para JAFNE

JAFNE ya tomó decisiones que restringen las opciones:

- **ADR-0003** (agnosticismo de proveedor) — A2A nació justo para resolver
  interoperabilidad entre agentes de distintos vendors, un objetivo hermano.
- **ADR-0004** (capacidades vía MCP por repo) — si la asignación de tareas también usa
  MCP como canal, es una sola tecnología de transporte para dos planos en vez de dos.
- **ADR-0009** (`estado_asunto` cerrado) — ya tiene forma de máquina de estados, muy
  parecida en espíritu al ciclo de vida de una Task en A2A.

## Líneas para seguir explorando (sin decidir todavía)

- ¿JAFNE adopta el **Task** de A2A (o un subconjunto) para el mensaje Encargado→Agente,
  en vez de inventar un formato propio?
- ¿El transporte real es MCP (ya presente para capacidades) o hace falta HTTP/JSON-RPC
  completo como en A2A?
- ¿Cuánto del patrón CrewAI (roles + delegación jerárquica explícita) se puede tomar
  prestado sin adoptar el framework entero?
- ¿Hace falta un "Agent Card" por Agente (ligado a `.agents/`, ADR-0003) para que el
  Encargado sepa a quién asignarle qué?

## Análisis

- [`analisis/comparacion-de-protocolos.md`](./analisis/comparacion-de-protocolos.md) — las
  tres corrientes, comparadas.
- [`analisis/hops-de-comunicacion.md`](./analisis/hops-de-comunicacion.md) — **el tema no
  es un protocolo, son cuatro hops** con requisitos distintos. El hop Panel ↔ Asistente/
  Encargado (chat del panel, [ADR-0013](../../docs/adr/0013-panel-web-como-dashboard-visual.md))
  no lo resuelve ninguna de las tres corrientes de arriba, y es el que hoy bloquea la
  implementación.

## Fuentes

Ver el índice en [`fuentes/README.md`](./fuentes/README.md).

## Graduación

**Graduó [ADR-0031](../../docs/adr/0031-contrato-de-sesion-reanudable.md)** (2026-08-18):
el hop 2, que era el que bloqueaba al panel. El relevamiento del Agent SDK dio vuelta el
lean: las sesiones de los proveedores son **reanudables, no adjuntables**, y la API
experimental que sí permitía engancharse a un turno vivo fue removida. Así que la opción
B del análisis no existe, y el proceso del agente termina siendo de JAFNE — la opción A,
pero sin su desventaja, porque el SDK entrega mensajes estructurados y no texto de
terminal.

**Lo que queda de esta investigación es el hop 4** —el protocolo de asignación Encargado →
Agente—, que el propio análisis de hops ya había separado como decidible aparte.
