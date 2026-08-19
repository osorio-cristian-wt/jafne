# MCP oficiales de primera parte: Atlassian y Linear

- **Relevado:** 2026-08-11
- **Para:** [gestión de sprints](../research.md)

## Atlassian — servidor MCP remoto oficial

- **GA desde febrero de 2026**, con Claude como primer socio de integración.
- Endpoint hospedado por Atlassian: `https://mcp.atlassian.com/v1/mcp/authv2`.
- Autenticación **OAuth 2.1** o API tokens.
- Cubre **Jira, Confluence, Jira Service Management, Bitbucket y Compass** en un solo
  servidor.
- Repo oficial: [`atlassian/atlassian-mcp-server`](https://github.com/atlassian/atlassian-mcp-server).
- Clientes soportados explícitamente: Claude, ChatGPT, Cursor, VS Code.

## Linear — servidor MCP remoto oficial

- Hospedado y mantenido por Linear en `https://mcp.linear.app/mcp`. Lanzado en mayo de
  2025 y **ampliado en febrero de 2026**.
- Es **conector de primera parte en Claude**.
- Primitivas expuestas: *issues, projects, comments, teams, users, labels, issue statuses*
  y **cycles**.
- La ampliación de 2026 sumó cobertura de product management: *initiatives, initiative
  updates, project milestones, project updates, project labels*.

## Lo que importa para JAFNE

1. **Las dos opciones serias son remotas y hospedadas por el vendor**, no procesos
   locales. Eso cruza directo con [ADR-0011](../../../docs/adr/0011-redes-y-puertos-de-workspace.md):
   un Workspace con red restringida por proyecto tiene que poder alcanzar un endpoint
   externo, y hoy la única salida remota prevista es la malla ZeroTier.
2. **Autenticación OAuth**, no una API key en un archivo. Se cruza con el manejo de
   secretos, que sigue abierto en [`arquitectura.md`](../../../docs/arquitectura.md).
3. **Linear no tiene "sprints", tiene *cycles*.** Jira sí tiene sprints. No es un detalle
   de nombre: un *cycle* de Linear es una ventana de tiempo fija del equipo, mientras que
   un sprint de Jira es un contenedor de trabajo que se abre y se cierra. Si JAFNE modela
   sprints sobre una abstracción propia, tiene que decidir a cuál de las dos se parece.
4. Ninguno de los dos es un MCP "de sprints": son MCP **del producto entero**. Adoptar uno
   trae mucha más superficie que la que ADR-0014 pide.

## Fuentes

- [Atlassian — Introducing the Remote MCP Server](https://www.atlassian.com/blog/announcements/remote-mcp-server)
- [`atlassian/atlassian-mcp-server` (GitHub)](https://github.com/atlassian/atlassian-mcp-server)
- [Atlassian Official Remote MCP Server — setup](https://mcpservers.org/remote-mcp-servers/atlassian)
- [Linear MCP Server: Tools, Setup, and the SSE Retirement](https://www.usecarly.com/blog/linear-mcp/)
- [Linear MCP Server — setup y casos de uso](https://growthengineer.ai/mcp-servers/linear)
