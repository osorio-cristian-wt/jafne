# Comparación: A2A vs. frameworks de orquestación vs. MCP-handoff

- **Estado:** explorando
- **Sub-problema de:** [protocolo de asignación de tareas](../research.md)

## Las tres opciones, en limpio

| Opción | Qué es | A favor | En contra |
|---|---|---|---|
| **Adoptar A2A** (o un subconjunto) | Protocolo abierto con Agent Cards + Tasks + transporte HTTP/SSE/JSON-RPC | Estándar real, interoperable, 150+ orgs adoptantes; su ciclo de vida de Task calza con `estado_asunto` (ADR-0009) | Pensado para interoperar entre agentes de vendors *distintos y desconocidos* — JAFNE controla ambos lados (Encargado y Agente), puede ser más peso del que hace falta |
| **Patrón de framework** (CrewAI/LangGraph/AutoGen) | Adoptar el patrón conceptual (no el framework entero) de coordinador→descompone→despacha→sintetiza | CrewAI en particular calza casi 1:1 con Encargado→Agente (roles + delegación jerárquica) | Ninguno de los tres es un protocolo interoperable — es un patrón de diseño interno de un framework, no una especificación de mensajes |
| **MCP como canal de handoff** | Reusar MCP (ya presente para capacidades, ADR-0004) también para delegar tareas | Una sola tecnología de transporte para capacidades y delegación; JAFNE ya asume MCP en su diseño | Los patrones de handoff sobre MCP son más informales/emergentes que A2A específicamente para ciclo de vida de tareas; probablemente necesite convenciones propias encima |

## Lean actual (no decidido — solo una lectura, a confirmar con el usuario)

Las tres piezas no son excluyentes: **A2A** podría dar el *vocabulario* (Task, estados,
Agent Card) sin necesariamente adoptar todo su transporte pesado (JSON-RPC/HTTP/SSE) si
Encargado y Agente siempre corren dentro del mismo JAFNE — y ese vocabulario podría
viajar sobre **MCP**, que JAFNE ya usa para capacidades. El patrón de **CrewAI** (roles +
delegación jerárquica) es el que más se parece, conceptualmente, a lo que el Encargado ya
hace.

## Abierto

- ¿JAFNE necesita interoperar con agentes verdaderamente externos/de terceros (el caso
  para el que A2A fue diseñado), o Encargado/Agente siempre corren dentro del mismo
  sistema controlado por JAFNE?
- ¿Un "Agent Card" por repo es lo mismo que la declaración de capacidades de `.agents/`
  (ADR-0003/0004), o son dos cosas distintas?
- Formato concreto del mensaje de asignación (qué campos lleva una "tarea" del Encargado
  a un Agente) — todavía no definido.
