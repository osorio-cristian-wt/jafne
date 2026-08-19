# ADR-0029 — El reloj corre en el proceso del panel, con una sola cola y dos productores

- **Estado**: Reemplazada por [ADR-0035](./0035-el-reloj-corre-en-su-propio-proceso.md)
- **Fecha**: 2026-08-18

## Contexto

[ADR-0024](./0024-trabajo-programado-asuntos-disparados-por-tiempo.md) decidió que hay
Asuntos que se abren solos por cadencia, y dejó abierto **quién corre el reloj**.
[ADR-0017](./0017-timeout-derivado-y-pregunta-pendiente.md) había esquivado el problema una
vez, derivando el timeout de 3 minutos al leer en vez de persistir nada — pero una cadencia
semanal no se puede derivar: si nadie está despierto el lunes, no pasa nada.

[ADR-0026](./0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md) sumó un
segundo cliente para el mismo mecanismo: un Asunto diferido por falta de cupo necesita que
algo lo despierte después del reset.

El reloj tampoco puede vivir dentro de un Workspace, que es efímero por
[ADR-0006](./0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md).

## Decisión

- **El reloj corre dentro del proceso del panel.** Es el único proceso de larga vida que
  JAFNE ya tiene; agregar un segundo proceso sería agregar una segunda cosa que arrancar,
  supervisar y explicar.

- **Una sola cola de despertares, con dos productores:**

  | Productor | Qué encola | Origen |
  |---|---|---|
  | Cadencias declaradas por el Usuario | Repetitivo (semanal, diario) | ADR-0024 |
  | El propio sistema, al diferir por cupo | One-shot, con hora exacta | ADR-0026 |

  Son el mismo mecanismo —*despertar en el instante T y hacer X*—, así que es una cola, no
  dos.

- **Las cadencias se declaran en `~/.jafne/programado.yaml`**, junto al resto del estado
  operativo del Asistente ([ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md)).
  Cada entrada necesita las tres cosas que ADR-0024 pidió: la skill, la cadencia y a qué
  proyecto aplica.

- **Los despertares one-shot no se declaran ni se persisten aparte.** Salen de un dato que
  ya existe: `resetea` en `saldo.yaml`. Un diferimiento no agrega estado, agrega una razón
  para volver a mirar.

- **El panel deja de ser solo lectura, y queda dicho.**
  [ADR-0008](./0008-estado-de-asuntos-y-panel-web.md) y
  [ADR-0013](./0013-panel-web-como-dashboard-visual.md) lo definieron como observador que
  muestra el estado sin escribirlo. Correr el reloj lo convierte en un componente que
  **abre Asuntos**. Es un cambio de rol real y es mejor declararlo que dejar que se filtre
  por la puerta de atrás.

## Alternativas descartadas

- **El scheduler del sistema operativo (Task Scheduler / cron) invocando `jafne`:**
  descartada — parte la declaración en dos lugares, deja fuera del repo la mitad de la
  configuración y en Windows es incómoda de versionar. Gana en robustez frente al reboot,
  que es lo que hay que compensar (ver consecuencias).
- **Un proceso demonio propio, separado del panel:** descartada — es la misma cantidad de
  código de scheduling y una pieza más de operación. Se puede separar más adelante sin
  cambiar el contrato.
- **Un scheduler en la nube del proveedor:** descartada por el mismo muro que la medición
  de consumo: requiere organización y clave de API, y ADR-0025 fijó suscripciones
  personales.
- **Derivar también las cadencias al leer, como ADR-0017:** descartada porque no funciona.
  Derivar sirve para *interpretar* un estado cuando alguien pregunta; no sirve para
  *iniciar* trabajo cuando no hay nadie preguntando.

## Consecuencias

- **Si el panel no corre, no hay trabajo programado.** Es la contrapartida directa de
  meter el reloj adentro, y se acepta explícitamente: la alternativa era delegar en el SO
  y perder la declaración unificada. Un trabajo programado que no corrió tiene que ser
  **visible** en el panel cuando vuelva a levantar, no silencioso.

- **Dos máquinas con el panel abierto disparan el mismo trabajo dos veces.** Esto convierte
  a `sincronia-entre-maquinas` de problema teórico en consecuencia concreta: hasta que se
  decida, correr el panel en dos lugares con el mismo `~/.jafne/` no es seguro para
  cadencias. Sigue abierto.

- **El diferimiento por cupo no se puede implementar antes que el adaptador.** El reloj
  puede existir ya; saber *cuándo* despertar depende de que el saldo esté fresco, y eso lo
  reporta el adaptador del proveedor (ADR-0025, ADR-0028).

- **Un trabajo programado no puede consultar al Usuario** (ADR-0024), así que se apoya en
  la conmutación automática de ADR-0026 para no quedarse trabado — y, cuando conmutar no
  tiene destino, en diferir.
