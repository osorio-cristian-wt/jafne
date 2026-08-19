# A2A (Agent2Agent) — especificación del protocolo

- **Consultado:** 2026-07-23

## Qué es

Protocolo abierto para que agentes de IA de distintos proveedores se descubran, deleguen
tareas y coordinen trabajo. Originado por Google (anunciado abril 2025); gobernado por la
Linux Foundation desde junio 2025. Alcanzó v1.0 en 2026, con más de 150 organizaciones
adoptantes (Google, Microsoft, AWS, Salesforce, SAP, ServiceNow, Workday, IBM).

## Piezas centrales

- **Agent Cards** — cómo un agente advierte qué sabe hacer.
- **Tasks** — la estructura del trabajo que se intercambia.
- **Transporte** — HTTP, SSE, JSON-RPC 2.0.

## Ciclo de vida de una Task

`submitted → working → completed / failed / canceled`, con soporte para conversaciones
multi-turno.

## Relevancia para JAFNE

El ciclo de vida de una Task es muy similar en espíritu al `estado_asunto` cerrado de
[ADR-0009](../../../docs/adr/0009-catalogo-cerrado-estado-asunto.md). El concepto de
Agent Card podría mapear a la declaración de capacidades por repo (`.agents/`,
ADR-0003/0004).

## Fuentes originales

- [A2A protocol: Architecture and technical specification](https://tyk.io/learning-center/a2a-protocol-architecture-and-technical-specification/)
- [Google A2A Protocol: How Agent-to-Agent Coordination Works](https://atlan.com/know/google-a2a-protocol/)
- [Agent2Agent (A2A) Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [Agent2Agent — Wikipedia](https://en.wikipedia.org/wiki/Agent2Agent)
