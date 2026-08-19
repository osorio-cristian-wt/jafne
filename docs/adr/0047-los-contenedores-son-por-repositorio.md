# ADR-0047 — Los contenedores son por repositorio, y el Asunto no tiene uno

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0006](./0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md),
  [ADR-0016](./0016-catalogo-cerrado-estado-contenedor.md),
  [ADR-0042](./0042-infraestructura-es-un-proceso-con-el-mcp-adentro.md),
  [ADR-0044](./0044-la-cadena-de-delegacion.md)

## Contexto

Desde ADR-0006 se venía asumiendo que **un Asunto tiene un contenedor**: ese ADR lo
describe existiendo *"con su contenedor, su rama, su estado"*, y ADR-0016 le puso a
`meta.yaml` un eje `estado_contenedor` con cuatro valores. Nunca se cableó, así que la
suposición nunca se puso a prueba.

Al bajar el aislamiento de motivo a consecuencia
([ADR-0045](./0045-para-que-existen-los-contenedores.md)) y sacar el cerebro afuera
([ADR-0046](./0046-el-cerebro-corre-afuera-el-contenedor-ejecuta.md)), el Usuario preguntó
lo que faltaba preguntar: si la imagen la declara el repo, y el Encargado no trabaja en un
repo, **¿qué es el contenedor del Asunto?**

No es nada. Un Encargado hace arquitectura, requisitos, decisiones que cruzan repos,
documentación y orquestación — su propio prompt le prohíbe bajar a la implementación de un
repositorio. Con el cerebro afuera, lee el estado por MCP y los archivos por el host, que
[ADR-0039](./0039-el-chat-del-panel-usa-herramientas-acotadas-a-la-raiz-de-repos.md) ya le
acota. Un contenedor para eso no ejecuta nada.

Contra los tres motivos de ADR-0045, el resultado es el mismo por triplicado: dormir y
despertar no aplica porque no hay proceso que dormir, y la portabilidad que se busca es la
del entorno de un repo, no la de una conversación.

## Decisión

**Hay un contenedor por repositorio, y ninguno por Asunto.**

- Los contenedores se crean **al delegar** un Agente de código a un repo, no al abrir el
  Asunto. Un Asunto que todavía no delegó a nadie **no tiene contenedores, y eso es
  normal**, no un síntoma.
- Un trabajo que cruza tres repos son tres Agentes y tres contenedores, uno por repo, tal
  como ADR-0044 ya había fijado el reparto.
- El **Encargado corre en el host**, acotado por ADR-0039, igual que hoy.
- El nombre de un contenedor lleva los tres niveles: `jafne-<proyecto>-<asunto>-<repo>`.
  Derivado y no aleatorio, por la misma razón de siempre: quien mire `podman ps` tiene que
  poder decir de qué trabajo es sin consultarle a JAFNE.
- La red sigue siendo **por proyecto** (ADR-0011): los Agentes de un mismo Asunto se ven
  entre sí, que es lo que necesitan cuando el trabajo cruza repos.

**`estado_contenedor` del Asunto pasa a ser derivado**: un resumen de los contenedores de
sus Agentes, calculado al leer y nunca guardado.

| Situación de los Agentes | `estado_contenedor` del Asunto |
|---|---|
| Todavía no delegó a nadie | sin definir |
| Alguno en pie | `activo` |
| Todos dormidos | `suspendido` |
| Hubo y ya no queda ninguno | `destruido` |

El catálogo cerrado de ADR-0016 **no cambia** —siguen siendo los mismos cuatro valores— y
sigue valiendo que su ausencia significa *"nunca tuvo"*. Lo que cambia es quién es el
sujeto: antes el Asunto, ahora sus Agentes.

## Alternativas descartadas

- **Que el Asunto tenga contenedor con una imagen genérica:** descartada — es un contenedor
  que no ejecuta nada, y obliga a que JAFNE invente una imagen por defecto para el
  Encargado, que es justo el default improvisado que ADR-0048 evita.
- **Que el Workspace del Asunto sea el del repo principal cuando hay uno solo:** descartada
  — deja dos comportamientos distintos según cuántos repos tenga el proyecto, y el caso de
  un repo es el que menos ayuda a descubrir los errores del caso de varios.
- **Guardar `estado_contenedor` del Asunto en `meta.yaml` como campo propio:** descartada —
  serían dos verdades sobre lo mismo, y la copia se desincroniza. Es el mismo criterio con
  el que ADR-0017 dejó el timeout como derivado.

## Consecuencias

- **`nombre_de()` gana un nivel.** Hoy toma proyecto y asunto; le falta el repo.
- **Hay que reescribir el diagnóstico de por qué un Asunto no avanza.** El que se escribió
  el 2026-08-19 dice *"nunca se le pidió un Workspace"* para un Asunto en `iniciando` sin
  contenedor, y bajo este ADR eso es falso: es el estado normal de un Asunto que todavía no
  delegó. Tiene que hablar de Agentes, no de un Workspace del Asunto.
- **`agente.md` deja de estar bloqueado.** `prompts/__init__.py` decía que no se podía
  escribir porque dependía de *"qué es un repo concreto para JAFNE — sus skills, su MCP"*.
  Ahora está contestado: un repo es un contenedor, una imagen que él mismo declara
  (ADR-0048), y sus capacidades en `.agents/` (ADR-0004).
- **Un Asunto puede tener varios contenedores a la vez, o ninguno.** El panel tiene que
  mostrarlos en plural; hasta hoy mostraba un campo suelto.
