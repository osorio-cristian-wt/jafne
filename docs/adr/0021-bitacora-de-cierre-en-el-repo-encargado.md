# ADR-0021 — El cierre deja un rastro durable en el repo `encargado/`

- **Estado**: Aceptada
- **Fecha**: 2026-08-11

## Contexto

[ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md) puso la fuente de
verdad de los Asuntos en `~/.jafne/` y dejó abierto qué pasa si ese directorio se pierde:
"¿los Asuntos cerrados son recuperables solo desde ahí, o el cierre también deja algún
rastro mínimo en el proyecto?".

Hoy la respuesta implícita es la peor de las dos: si se pierde `~/.jafne/`, se pierde todo
el registro de qué se decidió y por qué en cada Asunto cerrado de todos los proyectos. Y
eso vive en una sola máquina, sin sincronización.

## Decisión

- **La skill de cierre ([ADR-0019](./0019-validaciones-del-cierre-de-asunto.md)) escribe
  una entrada de bitácora en el repo `encargado/` del proyecto**, versionada en git:
  `encargado/bitacora/AAAA-MM-DD-<asunto-id>.md`.
- **La entrada es el resumen, no el transcript.** Qué se pidió, qué se hizo, qué se decidió
  y qué quedó abierto — en la misma línea que el `cierre.md` de ADR-0007. El historial
  crudo de la conversación ([ADR-0018](./0018-reapertura-de-asuntos.md)) se queda en
  `~/.jafne/`: es estado operativo, no documentación del proyecto.
- **Cambia el rol de `~/.jafne/`.** Sigue siendo la fuente de verdad *operativa* —estado,
  contenedor, rama, historial— pero deja de ser el único lugar donde existe la memoria de
  lo decidido. Lo que importa a largo plazo queda en git, replicado en cada clon del repo.
- Si una decisión del Asunto restringe el diseño hacia adelante, la bitácora no la
  reemplaza: gradúa a un ADR del proyecto
  ([ADR-0005](./0005-cuando-investigar-vs-adr-directo.md)). La bitácora es el registro de
  *qué pasó*; el ADR es el registro de *qué queda decidido*.

## Alternativas descartadas

- **Dejar todo solo en `~/.jafne/`:** descartado — un único punto de pérdida, en una sola
  máquina, para la memoria de todos los proyectos.
- **Sincronizar `~/.jafne/` entre máquinas (git, rsync, nube):** descartado como respuesta
  a *esta* pregunta — versiona estado efímero (contenedores, ramas activas) para salvar la
  parte durable, y trae conflictos de merge sobre archivos que dos máquinas escriben a la
  vez. La sincronía entre máquinas sigue siendo una pregunta abierta aparte; lo que se
  resuelve acá es la pérdida de la memoria.
- **Un mensaje de merge descriptivo como único rastro** (la idea que ADR-0007 dejó
  anotada): descartado — depende de que haya merge (un Asunto puede cerrarse sin
  mergear nada), y un mensaje de commit no es un lugar donde nadie va a buscar.
- **Volcar el transcript completo al repo:** descartado — inunda el historial del proyecto
  con conversación cruda y arrastra al repo cualquier cosa que se haya dicho al pasar.

## Consecuencias

- El repo `encargado/` de un proyecto suma `bitacora/` a lo que ADR-0007 le definió
  (`investigacion/` + `docs/adr/` + `arquitectura.md` + `GLOSARIO.md` + `WORKFLOW.md`).
- La validación 3 del cierre (ADR-0019) verifica las dos cosas: el `cierre.md` en
  `~/.jafne/` **y** la entrada de bitácora en el repo.
- Perder `~/.jafne/` pasa a costar el estado operativo y los historiales, no la memoria de
  las decisiones. Un Asunto cerrado deja de ser reabrible con contexto completo, pero se
  sabe qué se hizo.
- El cierre ahora escribe en el repo del proyecto, así que **necesita permiso de escritura
  y commit** ahí — deja de ser una operación puramente local del Asistente.
