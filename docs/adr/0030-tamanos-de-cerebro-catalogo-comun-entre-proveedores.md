# ADR-0030 — Tamaños de cerebro: un catálogo común que cruza proveedores

- **Estado**: Aceptada
- **Fecha**: 2026-08-18
- **Matiza a**: [ADR-0022](./0022-orden-de-la-familia-openai.md)

## Contexto

[ADR-0003](./0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md) hizo a JAFNE agnóstico
de proveedor y puso al Encargado a elegir, tarea por tarea, qué cerebro asignar.
[ADR-0022](./0022-orden-de-la-familia-openai.md) ordenó la familia OpenAI —Sol > Tierra >
Luna—, pero **solo puertas adentro de ese proveedor**. El código lo dice sin vueltas:
*"Comparar tiers entre proveedores sigue sin definirse"*.

El resultado es que hoy conviven **tres vocabularios** que no se hablan: los nombres de
modelo de cada proveedor, los nombres propios de la familia OpenAI, y un tercero
—`liviano` / `intermedio` / `pesado`— que apareció en el `cerebros.yaml` de fábrica sin
que ningún ADR lo fijara.

Eso rompe tres cosas a la vez:

1. Un Encargado no puede pedir *"un cerebro grande"* de forma neutral: tiene que nombrar
   un modelo, que es justo el acople que ADR-0003 evita.
2. La conmutación de
   [ADR-0026](./0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md) no sabe
   qué cerebro del otro proveedor es *equivalente* al que estaba usando.
3. Cada release de cualquier proveedor obliga a revisar comparaciones escritas a mano.

El Usuario propuso el catálogo (2026-08-18): *"abstraer los nombres como chico, medio,
grande, gigante — así al hablar de sonnet sabés que es medio, y opus grande, así como
tierra medio, sol grande, y fable gigante"*.

## Decisión

- **Un catálogo cerrado de cuatro tamaños, común a todos los proveedores:** `chico`,
  `medio`, `grande`, `gigante`. Agregar un valor requiere un ADR que reemplace a este,
  igual que los catálogos de [ADR-0009](./0009-catalogo-cerrado-estado-asunto.md),
  [ADR-0016](./0016-catalogo-cerrado-estado-contenedor.md) y
  [ADR-0027](./0027-clase-de-riesgo-declarada-por-el-encargado.md).

- **La correspondencia por proveedor:**

  | Tamaño | Anthropic | OpenAI |
  |---|---|---|
  | `chico` | Haiku | Luna |
  | `medio` | Sonnet | Tierra |
  | `grande` | Opus | Sol |
  | `gigante` | Fable | — |

- **El Encargado pide un tamaño; el modelo concreto lo resuelve el adaptador.** Es la
  misma forma que [ADR-0027](./0027-clase-de-riesgo-declarada-por-el-encargado.md) usa para
  el aislamiento: quien decide habla en términos que entiende —capacidad—, y la traducción
  a la tecnología del momento queda de un solo lado. Cuando salga el próximo modelo de
  cualquiera de los dos, cambia una fila de la tabla y nada más.

- **El tamaño ordena; no promete equivalencia exacta.** `medio` de un proveedor y `medio`
  del otro son comparables para decidir, no idénticos en capacidad. Sirve para elegir y
  para conmutar, no para prometer que el resultado será el mismo.

- **Reemplaza a `liviano` / `intermedio` / `pesado`** en `cerebros.yaml`. Ese vocabulario
  nunca tuvo ADR, describía costo más que capacidad, y con tres niveles no tenía dónde
  poner a Fable.

- **No todo proveedor cubre todos los tamaños**, y eso es un dato, no un hueco a rellenar.
  Hoy `gigante` existe solo del lado Anthropic.

## Alternativas descartadas

- **Comparar por nombre de modelo:** descartada — se rompe en cada release y obliga a que
  el Encargado conozca el catálogo de todos los proveedores.
- **Números (1 a 4) en vez de nombres:** descartada — un `3` no dice nada sin la tabla al
  lado, y el objetivo es que el Encargado pueda razonar sin consultarla.
- **Mantener `liviano`/`intermedio`/`pesado`:** descartada — tres niveles no alcanzan, y
  "pesado" nombra el costo y no la capacidad, que es lo que hay que comparar.
- **Extender los nombres de la familia OpenAI (Sol/Tierra/Luna) a todos los proveedores:**
  descartada — son nombres propios de una familia; usarlos como vocabulario común haría que
  el resto de los proveedores hablen en términos de uno.
- **Una escala continua o un puntaje de capacidad:** descartada — invita a comparaciones
  falsamente precisas entre proveedores y hay que recalibrarla en cada release.

## Consecuencias

- **ADR-0022 queda matizada, no reemplazada.** Su orden interno —Sol > Tierra > Luna—
  sigue siendo cierto y es exactamente lo que la columna OpenAI de la tabla expresa. Lo que
  cambia es que ahora ese orden se dice en un vocabulario que también entiende Anthropic.

- **La conmutación de ADR-0026 puede degradar de tamaño.** Un Asunto en `gigante` que
  conmuta a un proveedor sin `gigante` baja a `grande`. Eso es una degradación real, tiene
  que ser visible, y es un argumento más para no conmutar a mitad de un Asunto.

- **`cerebros.yaml` de fábrica cambia de vocabulario**, y con él el panel y la CLI, que
  muestran el tier.

- **El tamaño es una segunda variable de la elección de cerebro**, junto al saldo que sumó
  ADR-0025. El Encargado elige *tamaño* por dificultad de la tarea y *proveedor* por saldo
  disponible — dos ejes independientes, como los dos ejes de estado de
  [ADR-0008](./0008-estado-de-asuntos-y-panel-web.md).

- **Queda abierto qué tamaño corresponde a cada rol por defecto.** Que el Asistente corra
  hoy en `grande` es una elección de configuración, no una regla: si conviene un default
  por rol, es otro ADR.
