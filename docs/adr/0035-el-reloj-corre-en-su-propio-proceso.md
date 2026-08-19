# ADR-0035 — El reloj corre en su propio proceso, separado del panel

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Reemplaza a**: [ADR-0029](./0029-el-reloj-corre-en-el-proceso-del-panel.md)

## Contexto

[ADR-0029](./0029-el-reloj-corre-en-el-proceso-del-panel.md) metió el reloj adentro del
proceso del panel, con un argumento de economía: era el único proceso de larga vida que
JAFNE ya tenía, y agregar un segundo era agregar una segunda cosa que arrancar, supervisar
y explicar.

El Usuario revisó esa decisión el 2026-08-19 y la revirtió, por dos costos operativos que
ese argumento no compensa:

1. **Acopla el trabajo programado a que el dashboard esté abierto.** El panel es una
   herramienta de observación: se abre para mirar y se cierra cuando no se mira. Colgar de
   él una cadencia semanal significa que cerrar una pestaña apaga trabajo — y que para que
   corra un job del domingo a las 3 AM hay que dejar un servidor web escuchando toda la
   noche por una razón que no tiene nada que ver con servir HTTP.
2. **Convierte al panel en escritor de estado.** ADR-0029 lo dijo de frente y tuvo que
   declarar una excepción contra [ADR-0008](./0008-estado-de-asuntos-y-panel-web.md) y
   [ADR-0013](./0013-panel-web-como-dashboard-visual.md): correr el reloj lo vuelve un
   componente que **abre Asuntos**. Que la excepción estuviera declarada la hacía honesta,
   no barata: la propiedad "el panel no escribe estado" es lo que permite razonar sobre
   quién movió un Asunto sin auditar la UI.

Lo que motivó a ADR-0029 no cambió y sigue en pie: una cadencia semanal no se puede
derivar al leer como el timeout de [ADR-0017](./0017-timeout-derivado-y-pregunta-pendiente.md)
—si nadie está despierto el lunes, no pasa nada—, y el reloj no puede vivir dentro de un
Workspace, que es efímero por [ADR-0006](./0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md).
Hace falta un proceso de larga vida. La pregunta es cuál — y ADR-0029 ya había dejado la
puerta abierta al descartar el demonio propio: *"se puede separar más adelante sin cambiar
el contrato"*. Esto es ese más adelante, y el contrato efectivamente no cambia.

## Decisión

- **El reloj corre en su propio proceso**, invocable como `jafne reloj`. No depende del
  panel, no sirve HTTP y no comparte ciclo de vida con nada: se arranca y se para solo.

- **El panel vuelve a ser de solo lectura sobre el estado.** La excepción que ADR-0029 le
  abrió contra ADR-0008 y ADR-0013 **queda sin efecto**. El panel puede mostrar qué hay
  programado y cuándo despierta —leer `programado.yaml` y calcular la próxima cola es
  lectura pura, la misma clase de derivación que el timeout de ADR-0017—, pero no dispara
  nada y no abre Asuntos.

- **Una sola cola de despertares, con dos productores** (se re-declara de ADR-0029, que en
  esto acertó):

  | Productor | Qué encola | Origen |
  |---|---|---|
  | Cadencias declaradas por el Usuario | Repetitivo (semanal, diario) | [ADR-0024](./0024-trabajo-programado-asuntos-disparados-por-tiempo.md) |
  | El propio sistema, al diferir por cupo | One-shot, con hora exacta | [ADR-0026](./0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md) |

  Son el mismo mecanismo —*despertar en el instante T y hacer X*—, así que es una cola, no
  dos. Que el reloj se mude de proceso no cambia eso.

- **Las cadencias se declaran en `~/.jafne/programado.yaml`** (también re-declarado de
  ADR-0029), junto al resto del estado operativo del Asistente
  ([ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md)). Cada entrada
  necesita las tres cosas que ADR-0024 pidió: **la skill, la cadencia y a qué proyecto
  aplica**.

- **Los despertares one-shot no se declaran ni se persisten aparte.** Salen de un dato que
  ya existe: `resetea` en `saldo.yaml`. Un diferimiento no agrega estado, agrega una razón
  para volver a mirar.

- **La cadencia se declara con un vocabulario cerrado, y una que JAFNE no entiende se
  rechaza al leer.** Misma forma que los catálogos de
  [ADR-0009](./0009-catalogo-cerrado-estado-asunto.md) y
  [ADR-0027](./0027-clase-de-riesgo-declarada-por-el-encargado.md), y por la misma razón
  agravada: una entrada programada que se ignora en silencio **no falla, simplemente nunca
  dispara**, y nadie se entera hasta que alguien pregunta por qué no se armó el sprint.

- **Un despertar vencido no se repone.** Si el reloj estuvo caído cuando tocaba, al
  levantar agenda el próximo y no dispara los atrasados. Reponer una cadencia semanal
  caída tres semanas abriría tres Asuntos iguales de golpe, y ADR-0024 fijó que un Asunto
  programado **no puede consultar al Usuario**: no hay quien frene la avalancha. Lo que
  ADR-0029 pidió sigue valiendo — que un trabajo no haya corrido tiene que ser **visible**,
  no silencioso.

- **Un solo reloj por almacén.** Dos relojes sobre el mismo `~/.jafne/` disparan el mismo
  trabajo dos veces. Se cubre por dos lados: el proceso toma un candado en el almacén al
  arrancar, y el Asunto que abre una cadencia lleva un id **derivado de la entrada y de la
  fecha del despertar**, así que un segundo intento de abrir el mismo choca con el Asunto
  que ya existe (ADR-0006) en vez de duplicarlo.

## Alternativas descartadas

- **Dejar el reloj adentro del panel (ADR-0029):** descartada — es lo que este ADR
  revierte. El ahorro de un proceso se paga con trabajo programado que depende de una
  ventana de navegador abierta y con un observador que escribe estado.
- **El scheduler del sistema operativo (Task Scheduler / cron) invocando `jafne`:**
  se mantiene el descarte de ADR-0029, y por su motivo original: parte la declaración en
  dos lugares y deja fuera del repo la mitad de la configuración. Conviene registrar que
  este ADR le saca su principal ventaja comparativa —ADR-0029 la descartaba en parte por
  "un proceso más de operación", y ahora ese proceso existe igual—, pero la declaración
  unificada en `programado.yaml` sigue siendo la razón que decide.
- **Reponer todos los despertares vencidos al levantar:** descartada — abre en ráfaga
  Asuntos idénticos que nadie pidió y que no pueden preguntar nada (ADR-0024).
- **Dos colas, una por productor:** descartada por lo mismo que en ADR-0029 — es un solo
  mecanismo, y separarlo duplica el bucle, el orden y el candado.
- **Un scheduler en la nube del proveedor:** descartada por el mismo muro que la medición
  de consumo: requiere organización y clave de API, y
  [ADR-0025](./0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md) fijó
  suscripciones personales.

## Consecuencias

- **El panel recupera una propiedad, no solo pierde código.** Esto es lo que separa a este
  ADR de una mudanza de archivos: *"el panel no escribe estado"* vuelve a ser cierto **sin
  excepciones**, y ADR-0008 y ADR-0013 vuelven a leerse enteros sin una nota al pie. Quien
  se pregunte quién movió un Asunto tiene otra vez una lista corta —el Encargado, el
  Workspace Broker, y ahora el reloj— en la que la UI no está.
- **Hay dos procesos que arrancar y supervisar**, que es exactamente el costo que ADR-0029
  quiso evitar. Se paga a cambio de lo de arriba, y de poder correr el reloj en una máquina
  sin dashboard, o el dashboard sin reloj.
- **Si el reloj no corre, no hay trabajo programado.** La condición no desaparece, pero
  ahora es propia y explícita —*"¿está corriendo el reloj?"*— en vez de estar escondida
  detrás de *"¿está abierto el panel?"*.
- **La cadencia se interpreta en la hora local de la máquina que corre el reloj.** "Lunes
  08:00" es el lunes del Usuario, no UTC: es la hora que el Usuario declaró mirando su
  propio calendario. El estado persistido sigue en UTC como en todo el almacén.
- **Dos máquinas siguen sin estar cubiertas.** El candado y el id derivado resuelven dos
  relojes sobre el mismo almacén; dos máquinas con su propio `~/.jafne/` y la misma
  cadencia disparan dos veces. `sincronia-entre-maquinas` sigue abierto y esta decisión no
  lo mueve — solo deja de ser el panel quien lo agrava.
- **El reloj abre el Asunto; ejecutar la skill depende del adaptador.** La apertura por
  cadencia es real y funciona hoy. Correr la skill del Encargado adentro de ese Asunto
  necesita el adaptador de [ADR-0028](./0028-anthropic-primero-alcance-de-adaptadores.md) /
  [ADR-0034](./0034-el-adaptador-usa-la-sesion-de-claude-code.md), que todavía no existe:
  el Asunto queda abierto en `iniciando` con el pedido anotado en su historial —visible y
  honesto— en vez de simular que el trabajo corrió.
- **El diferimiento por cupo ya tiene quien despierte, y sigue esperando saldo fresco.**
  El productor one-shot existe; la hora que calcula es correcta sobre el dato que haya en
  `saldo.yaml`, y ese dato hoy se carga a mano (`medicion-de-consumo`).
- **Un trabajo programado no puede consultar al Usuario** (ADR-0024), así que se apoya en
  la conmutación automática de ADR-0026 para no quedarse trabado — y, cuando conmutar no
  tiene destino, en diferir.
