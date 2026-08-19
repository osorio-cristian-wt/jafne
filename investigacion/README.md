# Investigación — diseño exploratorio de JAFNE

Acá vive el **brainstorming**: cada tema de diseño con sus opciones, trade-offs y
descartes. Estándar Casa Justina (ver [`WORKFLOW.md`](../WORKFLOW.md)). Cuando un tema se
congela, gradúa a un [ADR](../docs/adr/README.md).

## Temas

| Tema | Estado | Qué explora |
|---|---|---|
| [`jerarquia-de-roles/`](./jerarquia-de-roles/research.md) | explorando | La jerarquía Asistente → Encargado → Agentes y quién documenta con qué estándar. |
| [`orquestacion-entornos/`](./orquestacion-entornos/research.md) | explorando | Cómo los agentes obtienen entornos de ejecución efímeros (workspaces). Heredado de Engineering OS v0.2. |
| [`protocolo-de-asignacion-de-tareas/`](./protocolo-de-asignacion-de-tareas/research.md) | explorando | Cómo el Encargado le asigna tareas a un Agente: A2A, patrones de framework (CrewAI/LangGraph/AutoGen), o MCP-handoff. |
| [`gestion-de-sprints/`](./gestion-de-sprints/research.md) | modelo graduado a [ADR-0023](../docs/adr/0023-sprints-ejes-independientes-y-estado-externo.md) | Queda la elección de herramienta concreta y el vocabulario mínimo para hablar con cualquiera (Jira tiene *sprints*, Linear tiene *cycles*). |
| [`medicion-de-consumo/`](./medicion-de-consumo/research.md) | graduado a [ADR-0025](../docs/adr/0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md) | Queda el **cómo**: por qué vía ve Infraestructura el consumo de los agentes, y si el saldo se puede leer programáticamente. |
