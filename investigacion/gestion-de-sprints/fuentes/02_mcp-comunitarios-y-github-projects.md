# MCP comunitarios de Jira y GitHub Projects

- **Relevado:** 2026-08-11
- **Para:** [gestión de sprints](../research.md)

## Jira — implementaciones comunitarias

Hay **al menos seis** servidores MCP de Jira mantenidos por la comunidad, con alcances muy
distintos:

| Repo | Notas |
|---|---|
| [`vish288/mcp-atlassian-extended`](https://github.com/vish288/mcp-atlassian-extended) | El más completo para lo que pide ADR-0014: 23 tools, 15 resources, 5 prompts, con **sprints, agile boards, backlog y capacidad de sprint** explícitos |
| [`guhcostan/jira-mcp`](https://github.com/guhcostan/jira-mcp) | "manage issues and sprints directly from your AI agent" |
| [`nguyenvanduocit/jira-mcp`](https://github.com/nguyenvanduocit/jira-mcp) | En Go; issue management, sprint planning y transiciones de workflow |
| [`cfdude/mcp-jira`](https://github.com/cfdude/mcp-jira) | |
| [`aashari/mcp-server-atlassian-jira`](https://github.com/aashari/mcp-server-atlassian-jira) | Node/TS; búsqueda JQL y dev info (commits, PRs) |
| [`phuc-nt/mcp-atlassian-server`](https://github.com/phuc-nt/mcp-atlassian-server) | Jira + Confluence |
| [`Warzuponus/mcp-jira`](https://github.com/Warzuponus/mcp-jira) | |

## GitHub Projects

- [`mcp-github-projects`](https://github.com/TensorBlock/awesome-mcp-servers/blob/main/docs/project--task-management.md)
  — gestión de proyectos **Agile basados en sprints** sobre GitHub Projects vía MCP.
- `TerraCo89/mcp-server-github-projects` — vistas, prioridades, dependencias y métricas de
  GitHub Projects.

## Lo que importa para JAFNE

1. **La densidad de implementaciones comunitarias de Jira es una señal ambigua.** Que haya
   seis significa que el problema es común, pero también que ninguna se impuso — y adoptar
   una capacidad comunitaria implica aprobación del Usuario por la cadena completa
   ([ADR-0004](../../../docs/adr/0004-capacidades-por-repositorio.md)) sobre un repo que
   no controla nadie del proyecto.
2. **GitHub Projects es el candidato de menor fricción para JAFNE.** Los repos de Agente
   ya viven en GitHub ([ADR-0004](../../../docs/adr/0004-capacidades-por-repositorio.md):
   las capacidades se publican vía GitHub), así que no suma una cuenta, un vendor ni un
   flujo de auth nuevos.
3. **Ninguno resuelve la pregunta de modelo.** Todos asumen que el sprint vive en la
   herramienta externa. La pregunta de dónde vive el estado de un sprint para JAFNE
   —`~/.jafne/`, el repo `encargado/`, o afuera— no la contesta ninguna de estas
   opciones: la esquiva.

## Fuentes

- [awesome-mcp-servers — Project & Task Management](https://github.com/TensorBlock/awesome-mcp-servers/blob/main/docs/project--task-management.md)
- [Jira MCP Server Guide (2026): Official vs Community Setup](https://mcp.directory/blog/jira-mcp-complete-guide-2026)
- [AI Sprint Planning Tools: Jira, Linear, GitHub & Beyond](https://www.augmentcode.com/tools/ai-sprint-planning-tools-jira-linear-github)
