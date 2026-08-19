# ADR-0014 — La gestión de sprints es parte del trabajo regular, y se accede vía MCP

- **Estado**: Aceptada
- **Fecha**: 2026-08-11

## Contexto

JAFNE ya sabe organizar el trabajo en **Asuntos**
([ADR-0006](./0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md)), que son la unidad
persistente de una conversación de trabajo con un Encargado. Falta la capa de
**planificación**: un Asunto no es un sprint, y hoy no hay forma de que, en medio de una
tarea normal, se cree o actualice un sprint.

Requisito directo del Usuario (2026-08-11), documentado directo como ADR según
[ADR-0005](./0005-cuando-investigar-vs-adr-directo.md).

## Decisión

- **Planificar es trabajo regular.** Durante una tarea normal, el Encargado tiene que
  poder **crear sprints** — no es una actividad aparte que ocurra fuera de JAFNE.
- **El acceso a la gestión de sprints se hace vía MCP**, coherente con
  [ADR-0004](./0004-capacidades-por-repositorio.md), donde las capacidades de un rol ya
  son skills + MCP. El Encargado no habla con la herramienta de sprints por su cuenta:
  la consume como una capacidad más.
- **Se consigue o se crea.** Se prefiere **adoptar un servidor MCP existente** de gestión
  de sprints antes que construir uno; si ninguno sirve, JAFNE construye el suyo. Cuál de
  las dos ramas se toma es una pregunta de investigación, no una decisión ya tomada.
- **Sigue la cadena de aprobación.** Sumar este MCP es agregar una capacidad, así que
  requiere aprobación del Usuario por la cadena de escalación completa
  ([ADR-0002](./0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md),
  [ADR-0004](./0004-capacidades-por-repositorio.md)).

## Alternativas descartadas

- **Gestionar sprints a mano, fuera de JAFNE:** descartado por el requisito — si planificar
  queda afuera, el Encargado nunca puede abrir un sprint en el momento en que detecta el
  trabajo, que es justo cuando tiene el contexto.
- **Que cada Agente hable directo con la herramienta de sprints:** descartado — planificar
  es una actividad de **nivel proyecto** (cruza repos), o sea del Encargado, igual que la
  documentación Casa Justina
  ([ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md)).
- **Inventar un formato propio de sprints sin mirar qué existe:** descartado — contradice
  el litmus test de [ADR-0005](./0005-cuando-investigar-vs-adr-directo.md); acá sí hay
  alternativas reales que buscar y comparar.

## Consecuencias

- Se abre la investigación
  [`investigacion/gestion-de-sprints/`](../../investigacion/gestion-de-sprints/research.md)
  para responder: qué servidores MCP de gestión de sprints existen y cuáles sirven, si hay
  que construir uno, dónde vive el estado de un sprint (`~/.jafne/`, el repo `encargado/`,
  o una herramienta externa) y **qué relación tiene un Sprint con un Asunto** (¿un sprint
  agrupa Asuntos? ¿un Asunto pertenece a un sprint? ¿son ejes independientes, como el
  estado de Asunto y el de contenedor en ADR-0008?).
- El panel web ([ADR-0013](./0013-panel-web-como-dashboard-visual.md)) probablemente
  quiera mostrar sprints junto a los Asuntos, pero **no se diseña esa vista** hasta que la
  investigación cierre.
- Hasta que esa investigación gradúe, **no se implementa nada de sprints**: no hay
  contrato que programar.
