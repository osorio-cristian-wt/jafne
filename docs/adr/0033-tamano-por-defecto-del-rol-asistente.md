# ADR-0033 — El Asistente corre en `medio` por defecto; los demás roles se eligen por tarea

- **Estado**: Aceptada, matizada por [ADR-0044](./0044-la-cadena-de-delegacion.md)
- **Fecha**: 2026-08-18

## Contexto

[ADR-0030](./0030-tamanos-de-cerebro-catalogo-comun-entre-proveedores.md) creó el catálogo
común de tamaños y dejó anotado, en sus consecuencias, exactamente esta pregunta:

> *Queda abierto qué tamaño corresponde a cada rol por defecto. Que el Asistente corra hoy
> en `grande` es una elección de configuración, no una regla: si conviene un default por
> rol, es otro ADR.*

Era una elección heredada, no decidida: el `cerebros.yaml` de fábrica declaraba un cerebro
Anthropic con `tier: pesado` y nada decía que ese fuera el del Asistente. De hecho, hasta
acá **el rol no existía en el código** — `rol` era un texto libre en los mensajes del
historial, y ningún componente sabía qué cerebro le tocaba a quién.

El Usuario resolvió el default (2026-08-18): el Asistente va en **mediano**.

## Decisión

- **El catálogo de roles es cerrado y sale de
  [ADR-0002](./0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md):**
  `asistente`, `encargado`, `agente`. El Usuario no está en el catálogo: es humano y no
  tiene cerebro asignado.

- **El Asistente corre en `medio`.** Su trabajo es conversar con el Usuario, enrutar y
  delegar; el trabajo difícil lo hace el nivel de abajo, en el Workspace. Un rol que
  delega no necesita el cerebro más caro para decidir a quién delegarle.

- **El Encargado y el Agente no tienen default, y eso no es un hueco.**
  [ADR-0003](./0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md) ya decidió que el
  Encargado elige cerebro y esfuerzo **tarea por tarea**; ponerle un default por rol
  contradiría esa decisión, no la completaría. La dificultad la fija la tarea, no el
  escalafón.

- **El default se resuelve al leer, no se persiste.** JAFNE parte del tamaño del rol y
  busca entre los cerebros declarados uno de ese tamaño **que tenga adaptador**
  ([ADR-0028](./0028-anthropic-primero-alcance-de-adaptadores.md)). Es la misma forma que
  [ADR-0017](./0017-timeout-derivado-y-pregunta-pendiente.md) usa para el timeout: derivar
  en vez de guardar una copia que se desincroniza.

- **Qué cerebro le tocó a cada rol es consultable**, por el Usuario desde el panel o la
  CLI y **por el propio agente**: un agente que puede preguntar sobre qué modelo está
  corriendo puede calibrar cuánto abarcar y cuándo escalar, en vez de suponerlo.

## Alternativas descartadas

- **Dejar al Asistente en `grande`:** descartada por el Usuario. Además era un default
  heredado de la config de fábrica, no una decisión: nadie lo había elegido.
- **Un default para los tres roles:** descartada — para Encargado y Agente contradice
  ADR-0003. La elección por tarea es una decisión tomada, no una pendiente.
- **Fijar el cerebro concreto del Asistente en vez del tamaño:** descartada — ataría el rol
  a un modelo y a un proveedor, que es exactamente lo que ADR-0030 vino a desatar. El rol
  pide capacidad; qué modelo la provee hoy es de la tabla, no del rol.
- **Guardar el cerebro resuelto en `~/.jafne/`:** descartada — se desincroniza en cuanto
  cambia `cerebros.yaml` o aparece un adaptador nuevo, y el dato ya se puede derivar.

## Consecuencias

- **El rol entra al núcleo como catálogo cerrado.** Es el cuarto, junto a `estado_asunto`,
  `estado_contenedor`, la clase de riesgo y el tamaño. Agregar un rol requiere un ADR que
  reemplace a este.

- **Resolver el cerebro del Asistente puede fallar, y tiene que fallar claro.** Si no hay
  ningún cerebro `medio` con adaptador, no hay Asistente. Con la config de fábrica sí lo
  hay —Sonnet, del lado Anthropic—, pero un `cerebros.yaml` editado a mano puede quedarse
  sin candidatos, y ahí conviene un error que diga qué falta y no un `None` que reviente
  más lejos.

- **Cambiar el default es cambiar una constante**, no migrar datos: como no se persiste,
  el cambio se ve en la próxima lectura.

- **Baja el costo del rol más conversacional.** El Asistente es el que más turnos tiene
  con el Usuario; moverlo de `grande` a `medio` es la palanca de gasto más grande que hay
  sin tocar la política de ADR-0003, que sigue prefiriendo gastar antes que rehacer donde
  el trabajo es difícil.
