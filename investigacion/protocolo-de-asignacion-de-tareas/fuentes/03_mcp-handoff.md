# MCP como canal de handoff multi-agente

- **Consultado:** 2026-07-23

## Qué es

El Model Context Protocol (MCP) — que JAFNE ya usa como canal de capacidades por repo
([ADR-0004](../../../docs/adr/0004-capacidades-por-repositorio.md)) — también tiene
patrones establecidos de *handoff* entre agentes: un agente orquestador delega una
subtarea a un sub-agente especializado, espera su salida, y continúa o escala según el
resultado.

## Cómo funciona el handoff

- El contexto se empaqueta y transfiere usando el formato estandarizado de recursos de
  MCP.
- Los handoffs se trackean con IDs de workflow y contexto específico de la tarea.
- Un agente puede invocar a otro "como si fuera una herramienta más".

## Relevancia para JAFNE

Si el protocolo de asignación de tareas también usa MCP como transporte, JAFNE tendría
**una sola tecnología** (MCP) para dos planos que hoy están separados en el diseño:
capacidades ([ADR-0004](../../../docs/adr/0004-capacidades-por-repositorio.md)) y
delegación de tareas — en vez de mantener dos protocolos distintos.

## Fuentes originales

- [MCP Agent Orchestration: Chaining, Handoffs, and Multi-Agent Patterns — getknit.dev](https://www.getknit.dev/blog/advanced-mcp-agent-orchestration-chaining-and-handoffs)
- [Advancing Multi-Agent Systems Through MCP — arXiv](https://arxiv.org/html/2504.21030v1)
- [Model Context Protocol architecture patterns — IBM Developer](https://developer.ibm.com/articles/mcp-architecture-patterns-ai-systems/)
- [mcp-handoff-server — GitHub](https://github.com/dazeb/mcp-handoff-server)
