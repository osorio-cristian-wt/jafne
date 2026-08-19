# ADR-0018 — Reapertura de un Asunto: el contexto vuelve, el contenedor no

- **Estado**: Aceptada
- **Fecha**: 2026-08-11

## Contexto

[ADR-0006](./0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md) estableció que los Asuntos
cerrados "quedan guardados y se pueden reabrir", y dejó el mecanismo sin definir.
[ADR-0009](./0009-catalogo-cerrado-estado-asunto.md) puso la transición `cerrado →
iniciando` en el diagrama, pero no dijo qué se restaura al hacerla.

Requisito directo del Usuario (2026-08-11): al reabrir un Asunto, **el Encargado retoma el
contexto y el historial de la conversación anterior** — no arranca de cero sabiendo solo
que hubo un Asunto con ese nombre.

## Decisión

Reabrir un Asunto restaura **el estado conversacional**, no el estado de máquina:

| Qué | Al reabrir |
|---|---|
| Historial de la conversación | **Se restaura.** Es la razón de ser de la reapertura |
| `cierre.md` del cierre anterior | **Se restaura** como contexto: qué se hizo y cómo terminó |
| Rama de trabajo | **Se retoma** la que ya está registrada en `meta.yaml` |
| Contenedor / Workspace | **No se resucita.** Se pide uno nuevo |

- **El historial de la conversación es un artefacto persistente del Asunto**, no del
  contenedor. Vive junto a `meta.yaml` y `cierre.md` en
  `~/.jafne/asuntos/<proyecto>/<asunto-id>/`
  ([ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md)), y se escribe
  mientras el Asunto avanza — no recién al cerrar, porque un cierre que falla no puede
  llevarse el historial con él.
- **La transición es `cerrado → iniciando`** (ADR-0009). `iniciando` es exactamente lo que
  pasa: se aprovisiona un contenedor nuevo (`creando`,
  [ADR-0016](./0016-catalogo-cerrado-estado-contenedor.md)) y se rehidrata el contexto
  antes de volver a `interactuando_con_el_usuario`.

> **El contexto es del Asunto; el contenedor es del Workspace.** Un Asunto puede pasar por
> varios contenedores a lo largo de su vida sin perder de qué se venía hablando.

## Alternativas descartadas

- **Resucitar el contenedor original (snapshot/restore):** descartado — contradice
  "efímero por defecto" ([`arquitectura.md`](../arquitectura.md), principio 2), y ata la
  reapertura a que el snapshot siga existiendo y siga siendo válido. Un Workspace se
  reconstruye desde `engineering.yaml` y la rama; eso es reproducible, un snapshot viejo
  no.
- **Reabrir arrancando de cero, con solo `cierre.md` como contexto:** descartado por el
  requisito del Usuario — el resumen de cierre no reemplaza al historial. Se pierde el
  detalle de por qué se descartaron cosas, que es justo lo que hace falta al retomar.
- **Guardar el historial solo al cerrar:** descartado — si la skill de cierre falla
  ([ADR-0019](./0019-validaciones-del-cierre-de-asunto.md)) o el proceso se cae, se pierde
  todo lo hablado. Se escribe incrementalmente.
- **Guardar el historial en el repo del proyecto:** descartado por la misma razón que
  ADR-0007 sacó los Asuntos del repo — es estado operativo de sesión, no documentación de
  diseño. El rastro durable en el proyecto es la bitácora de
  [ADR-0021](./0021-bitacora-de-cierre-en-el-repo-encargado.md), no el transcript crudo.

## Consecuencias

- El directorio de un Asunto (ADR-0007) suma un tercer artefacto, junto a `meta.yaml` y
  `cierre.md`: el **historial de la conversación**. Esto extiende ADR-0007, no lo
  reemplaza.
- Reabrir sigue siendo una operación local del Asistente, como preveía ADR-0007 — salvo
  por pedirle un Workspace nuevo a Infraestructura.
- **Rehidratar el contexto depende del hop Panel ↔ sesión viva**, que sigue abierto (ver
  [`hops-de-comunicacion.md`](../../investigacion/protocolo-de-asignacion-de-tareas/analisis/hops-de-comunicacion.md)):
  cómo se le inyecta un historial a una sesión nueva es específico de cada proveedor y lo
  resuelve el adaptador de [ADR-0003](./0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md).
  Hasta entonces, JAFNE **persiste** el historial pero no lo reinyecta.
- Un historial largo puede no entrar en la ventana de contexto del cerebro que retoma.
  Queda abierto qué se hace ahí (¿resumen, ventana móvil, el `cierre.md` como sustituto?).
