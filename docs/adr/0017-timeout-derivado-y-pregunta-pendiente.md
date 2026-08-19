# ADR-0017 — El timeout de 3 minutos es derivado, no persistido

- **Estado**: Aceptada
- **Fecha**: 2026-08-11

## Contexto

[ADR-0009](./0009-catalogo-cerrado-estado-asunto.md) fijó la regla —más de 3 minutos sin
respuesta a algo pendiente mueve el Asunto de `interactuando_con_el_usuario` a
`esperando_respuesta`— y dejó anotado que "hace falta un mecanismo de reloj/scheduler que
lo dispare". También quedó ambiguo si el timeout necesita saber que **efectivamente se
preguntó algo**, o si basta con el silencio.

## Decisión

- **No hay scheduler.** El estado efectivo se **calcula al leer**, a partir de
  `ultima_actividad` y `pregunta_pendiente`. Nadie escribe `esperando_respuesta` en
  `meta.yaml` por el paso del tiempo.
- **`meta.yaml` gana un campo `pregunta_pendiente` (booleano).** Lo pone el Encargado
  cuando le pregunta algo al Usuario y lo baja cuando recibe respuesta. El timeout solo
  aplica si está en `true`: un Asunto trabajando en background sin nada que preguntar
  puede pasar horas sin actividad visible y **no** es `esperando_respuesta` — es
  exactamente el modo delegado de
  [ADR-0002](./0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md).
- El valor guardado en `estado_asunto` sigue siendo el que declaró el Encargado. El
  derivado es una **lectura**, y el panel muestra cuándo difieren.

## Alternativas descartadas

- **Un demonio/reloj que recorra los Asuntos y escriba el estado:** descartado — es una
  pieza móvil nueva cuyo único trabajo es replicar un cálculo determinista. Si se cae, se
  atrasa o corre en una máquina con otro reloj, `meta.yaml` queda mintiendo; el derivado
  no puede desincronizarse porque no tiene estado propio.
- **Aplicar el timeout solo por silencio, sin `pregunta_pendiente`:** descartado — marcaría
  como "esperando respuesta" a todo Asunto trabajando en background, que es el caso normal
  del modo delegado. El estado perdería su significado justo en el panel, que es donde se
  mira.
- **Que `esperando_respuesta` lo declare el Encargado directamente:** descartado — ADR-0009
  ya lo definió como transición automática por tiempo; que el Encargado lo declare sería
  reemplazar esa decisión, no implementarla.

## Consecuencias

- `meta.yaml` lleva `estado_asunto`, `ultima_actividad`, `motivo` (ADR-0009) y ahora
  `pregunta_pendiente`.
- El Asistente y el panel calculan lo mismo desde la misma fuente, así que no pueden
  discrepar — no hace falta un canal de sincronización entre ellos.
- Si el Encargado se olvida de bajar `pregunta_pendiente` al recibir respuesta, el Asunto
  se muestra como `esperando_respuesta` de más. Es un error visible y barato de corregir,
  a diferencia de un scheduler desincronizado, que falla en silencio.
- Cualquier notificación al Usuario por timeout (ADR-0006) se dispara al observar el
  estado derivado, no desde un temporizador propio.
