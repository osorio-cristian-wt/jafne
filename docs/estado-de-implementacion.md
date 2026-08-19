---
fuentes:
  - docs/adr/0015-stack-inicial-de-implementacion.md
  - docs/adr/0013-panel-web-como-dashboard-visual.md
  - docs/adr/0016-catalogo-cerrado-estado-contenedor.md
  - docs/adr/0017-timeout-derivado-y-pregunta-pendiente.md
  - docs/adr/0018-reapertura-de-asuntos.md
  - docs/adr/0019-validaciones-del-cierre-de-asunto.md
  - docs/adr/0020-hosting-y-autenticacion-del-panel.md
  - docs/adr/0021-bitacora-de-cierre-en-el-repo-encargado.md
  - docs/adr/0023-sprints-ejes-independientes-y-estado-externo.md
  - docs/adr/0024-trabajo-programado-asuntos-disparados-por-tiempo.md
  - docs/adr/0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md
  - docs/adr/0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md
  - docs/adr/0027-clase-de-riesgo-declarada-por-el-encargado.md
  - docs/adr/0028-anthropic-primero-alcance-de-adaptadores.md
  - docs/adr/0029-el-reloj-corre-en-el-proceso-del-panel.md
  - docs/adr/0030-tamanos-de-cerebro-catalogo-comun-entre-proveedores.md
  - docs/adr/0031-contrato-de-sesion-reanudable.md
  - docs/adr/0032-driver-de-la-clase-generado.md
  - docs/adr/0033-tamano-por-defecto-del-rol-asistente.md
  - docs/adr/0034-el-adaptador-usa-la-sesion-de-claude-code.md
  - docs/adr/0035-el-reloj-corre-en-su-propio-proceso.md
  - docs/adr/0036-dictado-por-voz-con-whisper-local.md
  - docs/adr/0037-el-dictado-puede-delegarse-a-un-nodo-con-gpu.md
  - src/jafne/pendientes.py
verificado: 2026-08-19
---

# Estado de la implementación

Qué del diseño ya corre y qué está esperando una decisión. La regla de
[ADR-0015](./adr/0015-stack-inicial-de-implementacion.md) es que **lo que no está decidido
no se programa**: no hay defaults improvisados que después haya que desarmar.

La lista viva de bloqueos está en el código, no acá: `src/jafne/pendientes.py` es la
fuente de verdad, y se consulta con `jafne pendientes` o `GET /api/pendientes`. Este
documento la explica; el código la aplica.

Qué está **decidido** —que no es lo mismo que qué corre— vive en
[`estado-del-diseno.md`](./estado-del-diseno.md). Los dos son documentos derivados de
[`docs/adr/`](./adr/README.md) y se actualizan en el mismo commit que su fuente.

## Cómo correrlo

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"    # Linux/macOS: .venv/bin/pip

jafne init                                # crea ~/.jafne/ (ADR-0007)
jafne abrir borr rediseno --titulo "Rediseño del panel" --rama feature/panel --repo /ruta/al/repo
jafne estado borr rediseno interactuando_con_el_usuario
jafne anotar borr rediseno usuario "arranquemos por el header"
jafne pregunta borr rediseno si           # habilita el timeout de 3 min (ADR-0017)
jafne cerrar borr rediseno --resumen "Lo que se hizo y lo que quedó abierto."
jafne reabrir borr rediseno               # vuelve el contexto, no el contenedor
jafne pendientes                          # qué falta decidir y qué bloquea cada cosa
jafne panel                               # http://127.0.0.1:8730
```

El reloj del trabajo programado corre **aparte del panel** (ADR-0035): son dos procesos
independientes, y cerrar el dashboard ya no apaga las cadencias.

```bash
jafne reloj --ver                          # la cola de despertares, sin disparar nada
jafne reloj                                # el proceso: espera y dispara
```

Las cadencias se declaran en `~/.jafne/programado.yaml`, con las tres cosas que pide
ADR-0024 y un vocabulario cerrado para la cadencia:

```yaml
trabajos:
  sprint-semanal:
    skill: armar-sprint
    cadencia: semanal lunes 08:00   # o `diaria HH:MM`; la hora es la local
    proyecto: borr
```

El saldo de las suscripciones lo escribe Infraestructura (ADR-0025), igual que el estado
del contenedor. Cada llamada actualiza una ventana y conserva las otras:

```bash
jafne saldo anthropic 5h 0.18 --plan max --fuente "claude-code /usage" \
  --resetea 2026-08-11T21:40:00Z
jafne saldo anthropic semanal 0.62 --resetea 2026-08-17T00:00:00Z
jafne saldo                               # lo observado, por proveedor
jafne cerebros                            # tamaño, adaptador y qué dice el saldo
jafne credencial                          # con qué credencial habla JAFNE (ADR-0034)
```

`jafne cerebros` junta en una vista las tres decisiones que se cruzan al elegir cerebro: el
tamaño común de ADR-0030, si el proveedor tiene adaptador (ADR-0028) y la señal de saldo de
ADR-0026 —`proceder`, `conmutar` o `diferir`, con hora de reanudación si hay que esperar—.

El dictado por voz del panel es un extra opcional (ADR-0036). Sin él, JAFNE corre entero
y el botón aparece deshabilitado con el motivo:

```bash
.venv/Scripts/pip install -e ".[voz]"     # motor de voz (faster-whisper)
JAFNE_VOZ_MODELO=medium jafne panel        # el default es large-v3
```

El audio se graba en el navegador, se transcribe y se descarta: no toca el disco de
ninguno de los dos lados. El texto va al campo del chat, para revisarlo antes de enviarlo.

Si hay otra máquina en la malla con GPU NVIDIA, el dictado se le puede delegar (ADR-0037).
En **esa** máquina:

```bash
jafne voz --host 10.144.0.2 --token <token>     # presta la GPU a la malla
```

y en la del panel:

```bash
JAFNE_VOZ_NODO=http://10.144.0.2:8731 JAFNE_VOZ_TOKEN=<token> jafne panel
```

Sin `$JAFNE_VOZ_NODO` se transcribe acá, que es el default de ADR-0036. Si el nodo está
apagado el botón aparece deshabilitado con el motivo: no hay caída silenciosa a la CPU
local, porque un segundo contra catorce es una diferencia que tiene que verse.

Fuera de loopback el panel exige token (ADR-0020):

```bash
JAFNE_PANEL_TOKEN=… jafne panel --host <IP-ZeroTier>
```

Tests: `.venv/Scripts/python -m pytest` (240 casos, verde al 2026-08-19).

## Estructura

```
src/jafne/
  pendientes.py        registro de decisiones abiertas + DecisionPendiente
  nucleo/
    estados.py         los dos ejes de estado de un Asunto (ADR-0009, ADR-0016)
    tamanos.py         tamaño de cerebro común entre proveedores (ADR-0030)
    riesgo.py          clase de riesgo y su mapeo a driver (ADR-0027)
    adaptadores.py     qué proveedores se pueden usar hoy (ADR-0028)
    senal_saldo.py     proceder / conmutar / diferir (ADR-0026)
    roles.py           roles y su tamaño por defecto (ADR-0033)
    sesion.py          el contrato neutral de sesión (ADR-0031)
    credenciales.py    estado de la credencial, sin tocarla (ADR-0034)
    despertares.py     la cola de despertares, como función del tiempo (ADR-0035)
    transcripcion.py   dictado por voz: local o delegado (ADR-0036, ADR-0037)
    modelos.py         Proyecto, Cerebro, Asunto, Mensaje, Suscripcion, Ventana
    almacen.py         lectura/escritura de ~/.jafne/ (ADR-0007, ADR-0018, ADR-0025)
    cierre.py          skill de cierre: 5 validaciones + bitácora (ADR-0019, ADR-0021)
  panel/
    api.py             FastAPI: JSON, estáticos y token (ADR-0013, ADR-0020)
    web/               index.html + estilo.css + app.js, sin build (ADR-0015)
  acceso.py            bind y token, compartidos por panel y nodo (ADR-0020)
  voz.py               el nodo que presta una GPU a la malla (ADR-0037)
  reloj.py             el proceso del reloj: candado, espera y disparo (ADR-0035)
  cli.py               jafne <comando>
tests/                 estados, catálogos, señal de saldo, almacén, cierre, reloj, voz y API
```

## Implementado

| Pieza | Qué hace | Decisión que lo habilita |
|---|---|---|
| Almacén `~/.jafne/` | `jafne init` crea `proyectos.yaml`, `cerebros.yaml`, `saldo.yaml`, `programado.yaml` y `asuntos/`; lectura y escritura de `meta.yaml`, `cierre.md` e `historial.jsonl`. | [ADR-0007](./adr/0007-jerarquia-de-directorios-de-jafne-implementado.md) |
| Catálogo cerrado de `estado_asunto` | Cinco valores; un valor fuera del catálogo se rechaza al leer. | [ADR-0009](./adr/0009-catalogo-cerrado-estado-asunto.md) |
| Catálogo cerrado de `estado_contenedor` | Cuatro valores + sus transiciones. Su ausencia significa "nunca tuvo Workspace", distinto de `destruido`. | [ADR-0016](./adr/0016-catalogo-cerrado-estado-contenedor.md) |
| Máquinas de estados | Las transiciones de los dos diagramas, incluidas `cerrando → interactuando` (cierre fallido) y `cerrado → iniciando` (reapertura). Un salto que el diagrama no tiene se rechaza. | ADR-0009, ADR-0016 |
| Timeout derivado | El estado efectivo se calcula al leer y **solo** si `pregunta_pendiente` está en `true`. No hay scheduler y nada se persiste. | [ADR-0017](./adr/0017-timeout-derivado-y-pregunta-pendiente.md) |
| Historial de conversación | Se escribe incrementalmente (`jafne anotar`), se lee en orden, y una línea corrupta no invalida el resto. | [ADR-0018](./adr/0018-reapertura-de-asuntos.md) |
| Reapertura con contexto | `jafne reabrir` vuelve a `iniciando` conservando historial, `cierre.md` y rama; el contenedor queda `destruido` y hay que pedir uno nuevo. | ADR-0018 |
| Skill de cierre | Las cinco validaciones, en orden, con veredicto y motivo por cada una. Todo-o-nada: si alguna falla, el Asunto vuelve a `interactuando_con_el_usuario` con la causa. Las de git corren `git status` / `merge-base` de verdad. | [ADR-0019](./adr/0019-validaciones-del-cierre-de-asunto.md) |
| Bitácora durable | El cierre escribe `encargado/bitacora/AAAA-MM-DD-<asunto>.md` en el repo del proyecto, y la validación 3 verifica que quedó. | [ADR-0021](./adr/0021-bitacora-de-cierre-en-el-repo-encargado.md) |
| Panel: proyectos y Asuntos | Grilla con conteo por estado, vista de proyecto con Asuntos, rama, contenedor, mensajes, motivo y preview. | [ADR-0013](./adr/0013-panel-web-como-dashboard-visual.md) |
| Panel: bind y token | Se niega a escuchar en todas las interfaces, y fuera de loopback exige token (query, cabecera o cookie). | [ADR-0020](./adr/0020-hosting-y-autenticacion-del-panel.md) |
| Panel: solo lectura del estado | Muestra estado e historial, no los escribe: los escriben el Encargado y el Workspace Broker. | [ADR-0008](./adr/0008-estado-de-asuntos-y-panel-web.md) |
| Tamaño de cerebro | Catálogo cerrado común a proveedores: `chico`/`medio`/`grande`/`gigante`. El vocabulario que reemplaza (`liviano`/`intermedio`/`pesado`) se traduce al leer para no romper un `~/.jafne/` viejo, y uno fuera del catálogo se rechaza. | [ADR-0030](./adr/0030-tamanos-de-cerebro-catalogo-comun-entre-proveedores.md) |
| Degradación al conmutar | `degradar()` da el mayor tamaño que cubre el proveedor destino: `gigante` → `grande` al pasar a OpenAI. La consecuencia de ADR-0026 hecha código. | ADR-0030 + ADR-0026 |
| Señal de saldo | Función pura: entra una `Suscripcion` y un instante, sale `proceder`, `conmutar` o `diferir` con hora de reanudación. Las ventanas no se colapsan: lo que clasifica es el horizonte de reset, no el nombre. | [ADR-0026](./adr/0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md) |
| Clase de riesgo | Catálogo cerrado de 2 con default `generado`. Sin declarar es el default; mal declarada se rechaza. `revisado` mapea a Podman; `generado` **rechaza** en vez de servirse con menos aislamiento. | [ADR-0027](./adr/0027-clase-de-riesgo-declarada-por-el-encargado.md) |
| Cerebros sin adaptador | Se listan igual, marcados, y usarlos falla con `AdaptadorNoImplementado` — un error propio, distinto de `DecisionPendiente`. | [ADR-0028](./adr/0028-anthropic-primero-alcance-de-adaptadores.md) |
| Runtime por clase de riesgo | `revisado` → `crun`, `generado` → `kata`. `exigir_runtime()` rechaza si la máquina no lo tiene, en vez de degradar. | [ADR-0032](./adr/0032-driver-de-la-clase-generado.md) |
| Contrato de sesión | `Protocol` con las cuatro operaciones. Verificable sin implementación: un adaptador lo cumple sin heredar del núcleo, que es lo que permite congelarlo antes que el primer adaptador. | [ADR-0031](./adr/0031-contrato-de-sesion-reanudable.md) |
| Cerebro por rol | Catálogo cerrado de roles y resolución **derivada** de `cerebros.yaml`: el Asistente sale en `medio` y salta a otro cerebro si cambia el archivo. Un rol sin default devuelve `None`, que es la decisión de ADR-0003, no un hueco. | [ADR-0033](./adr/0033-tamano-por-defecto-del-rol-asistente.md) |
| Sobre qué modelo corre cada rol | `GET /api/roles`, la tarjeta del panel y `jafne cerebros`. Lo consulta el Usuario y **el propio agente**. | ADR-0033 |
| Estado de la credencial | `jafne credencial`, `GET /api/credencial` y tarjeta en el panel: dónde está la CLI, si hay sesión y el aviso de que `ANTHROPIC_API_KEY` pisaría la suscripción. Mira y reporta; nunca lee un secreto ni pide uno. | [ADR-0034](./adr/0034-el-adaptador-usa-la-sesion-de-claude-code.md) |
| Saldo por suscripción | `saldo.yaml` guarda, por proveedor, cuánto queda de cada ventana y cuándo resetea. Cada cerebro llega con el saldo del suyo: `cerebros.yaml` dejó de ser una lista estática. | [ADR-0025](./adr/0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md) |
| Panel: saldo | Tarjeta con una barra por ventana y su reset, más el pendiente de la medición al lado. Un proveedor sin observar aparece vacío, no en cero. | ADR-0013 + ADR-0025 |
| Cola de despertares | Función del tiempo, sin dormir ni leer el reloj del sistema: entra un instante, sale qué despertar y cuándo. Los dos productores —cadencias y diferimientos por cupo— salen ordenados en **una** cola. | [ADR-0035](./adr/0035-el-reloj-corre-en-su-propio-proceso.md) + ADR-0024 + ADR-0026 |
| Cadencias en `programado.yaml` | Las tres cosas de ADR-0024 por entrada, con vocabulario cerrado (`diaria HH:MM`, `semanal <día> HH:MM`). Al revés que el saldo, se **rechaza** al leer: una cadencia degradada a nada nunca dispararía, en silencio. | ADR-0035 + ADR-0024 |
| Proceso del reloj | `jafne reloj` espera al primer despertar y lo dispara; `jafne reloj --ver` muestra la cola sin tocar nada. Un despertar vencido no se repone, y un cerrojo del sistema operativo sobre el almacén impide dos relojes — el kernel lo suelta al morir el proceso, así que un corte de luz no deja el arranque siguiente bloqueado. | ADR-0035 |
| Disparo de una cadencia | Abre un Asunto normal en `iniciando` (ADR-0024: no hay segunda clase de Asunto), con id derivado de la entrada y la fecha —así el mismo despertar no abre dos— y deja anotado en el historial qué skill falta correr. | ADR-0035 + ADR-0006 |
| Panel: sin excepciones sobre el estado | Al salir el reloj del proceso del panel, la excepción que ADR-0029 había declarado contra ADR-0008/ADR-0013 desaparece del código, no solo del documento. | ADR-0035 |
| Dictado por voz | `GET /api/voz` dice si se puede dictar y con qué; `POST /api/transcribir` devuelve el texto. El modelo se carga **perezoso** y queda caliente: un panel que nadie usó para dictar no paga memoria. | [ADR-0036](./adr/0036-dictado-por-voz-con-whisper-local.md) |
| Voz: botón del chat | Graba con `MediaRecorder`, manda el audio crudo y pega el texto en el campo —no en el hilo—, para revisarlo antes de enviarlo. Sin motor, o fuera de un contexto seguro, aparece deshabilitado **con el motivo**. | ADR-0036 + ADR-0013 |
| Voz: sin degradar en silencio | Si falta el paquete o el modelo declarado, responde 501 diciendo qué falta, con `decidido: true`. Nunca sirve una transcripción de un modelo más chico que el pedido. | ADR-0036 + ADR-0032 |
| Voz: delegar en un nodo | `$JAFNE_VOZ_NODO` manda el audio a otra máquina de la malla; sin declararlo se transcribe acá. El panel muestra en cuál se transcribió. | [ADR-0037](./adr/0037-el-dictado-puede-delegarse-a-un-nodo-con-gpu.md) |
| Voz: el nodo | `jafne voz` levanta dos endpoints y nada más: no lee `~/.jafne/` y no puede escribir estado. Un nodo con `$JAFNE_VOZ_NODO` puesto transcribe igual, no se reenvía a sí mismo. | ADR-0037 |
| Voz: nodo caído | `NodoInalcanzable` → 501 con el motivo. **No** cae a la CPU local: la diferencia de latencia tiene que verse. | ADR-0037 |
| Voz: GPU o CPU | `auto` elige CUDA si CTranslate2 la ve, con `float16`; en CPU, `int8`. Declarar `cuda` y que no haya se rechaza. | ADR-0037 |
| Bind y token compartidos | La comprobación de ADR-0020 es una sola función para el panel y para el nodo: dos servicios con reglas de acceso copiadas terminan con reglas distintas. | ADR-0020 + ADR-0037 |
| CLI | `init`, `proyectos`, `asuntos`, `abrir`, `estado`, `contenedor`, `pregunta`, `anotar`, `historial`, `reabrir`, `cerrar`, `saldo`, `cerebros`, `credencial`, `pendientes`, `panel`, `reloj`, `voz`. Fuerza UTF-8 en la salida: la consola de Windows es cp1252 y `jafne pendientes` moría con el `→` del hop 4. | ADR-0007/0009/0013/0016-0021/0025-0035 |

## No implementado, y por qué

Cada fila corresponde a una entrada de `src/jafne/pendientes.py`. Nada se sirve inventado:
o se responde **501** citando qué lo bloquea, o —cuando lo decidido alcanza para parte de
la funcionalidad— se sirve **lo que se sabe** con el pendiente adjunto en la misma
respuesta. `/api/uso-suscripciones` es el segundo caso: da el saldo que Infraestructura
registró y dice, al lado, que medirlo solo todavía no está decidido.

| Clave | Qué falta | Bloqueado por |
|---|---|---|
| `medicion-de-consumo` | **Cómo** observa Infraestructura el consumo. El saldo se sirve, pero se carga a mano: falta si las llamadas pasan por un punto que mide o si cada agente reporta lo suyo. | ADR-0025 + [medicion-de-consumo](../investigacion/medicion-de-consumo/research.md) |
| `historial-desbordado` | Qué hacer si el historial de un Asunto reabierto no entra en la ventana de contexto. | ADR-0018 |
| `workspace-broker` | **Descubrimiento de servicios del proyecto** — base de datos, colas, otros repos— con la red restringida de ADR-0011. Crear Workspaces ya no está bloqueado por una decisión: ADR-0027 fijó quién declara el aislamiento y ADR-0032 a qué runtime mapea. | [ADR-0011](./adr/0011-redes-y-puertos-de-workspace.md) |
| `sprints` | El modelo está decidido (ejes independientes, estado afuera); falta **cuál** herramienta y qué vocabulario mínimo sirve para hablarle a cualquiera. Sin eso no hay contrato MCP que programar. | [ADR-0023](./adr/0023-sprints-ejes-independientes-y-estado-externo.md) + [ADR-0014](./adr/0014-gestion-de-sprints-via-mcp.md) |
| `protocolo-asignacion-tareas` | El mensaje Encargado → Agente (hop 4). No bloquea al panel: se puede decidir aparte. | [protocolo-de-asignacion-de-tareas](../investigacion/protocolo-de-asignacion-de-tareas/research.md) |
| `tls-y-rotacion-de-token` | TLS propio del panel, cada cuánto rota el token y qué hacer si se filtra. | ADR-0020 |
| `sincronia-entre-maquinas` | Qué pasa si el Usuario opera JAFNE desde dos máquinas con estado operativo distinto. | ADR-0021 |

## Decidido, y todavía no implementado

Categoría nueva desde [ADR-0028](./adr/0028-anthropic-primero-alcance-de-adaptadores.md).
No es lo mismo que la tabla de arriba y **no va a `pendientes.py`**: ahí se registra qué
falta *decidir*, y acá la decisión ya está tomada — falta el trabajo. Mezclarlas haría que
la pregunta *"¿qué falta decidir?"* deje de tener una respuesta confiable, que es lo único
que vuelve útil a ese registro.

| Pieza | Decidida en | Qué falta escribir |
|---|---|---|
| Adaptador de la familia OpenAI | ADR-0010 + ADR-0028 | Sus cerebros se declaran y se listan; usarlos falla con `AdaptadorNoImplementado`. Relevar si su proveedor ofrece modo sesión adjuntable es parte de este trabajo, y ya no bloquea al contrato. |
| Adaptador de Anthropic | ADR-0028 + ADR-0031 + [ADR-0034](./adr/0034-el-adaptador-usa-la-sesion-de-claude-code.md) | El contrato está congelado y verificado, y ADR-0034 fijó que se escribe sobre la **CLI** de Claude Code (`-p`, `--resume`, `--output-format json`), heredando la sesión del Usuario. Es lo que hoy deja al chat en 501. |
| La skill de un trabajo programado | ADR-0024 + ADR-0035 | El reloj abre el Asunto y anota qué skill hay que correr; correrla es el adaptador otra vez. Hasta entonces el Asunto queda en `iniciando` con el pedido visible, que es lo honesto: el trabajo programado dispara de verdad, y lo que no pasa se ve. |
| Chat del panel con Asistente y Encargado | ADR-0013 + ADR-0031 | La interfaz está y el diseño también: JAFNE es dueño del proceso y multiplexa. Falta escribirlo. Responde 501 diciendo que falta código, no decisión. |
| `session_id` del proveedor en `meta.yaml` | ADR-0031 | El campo se decidió; se agrega cuando exista el adaptador que lo escriba, para no dejar superficie muerta. |
| Retomar el trabajo diferido por cupo | ADR-0026 + ADR-0035 | **Quien despierta ya existe**: el reloj encola el reset de `saldo.yaml` y llega a horario. Lo que falta es retomar el Asunto cuando llega, que es el adaptador. El disparo lo informa en vez de aparentar que corrió, y la hora sigue siendo correcta sobre un dato que hoy se carga a mano. |

## Detalles de implementación que ningún ADR fija

Cosas que el código necesita y que se resolvieron por consecuencia mecánica, no por
decisión de diseño. Si alguna resulta ser una decisión de verdad, gradúa a ADR:

- **`repos` en `meta.yaml`** — las validaciones 1 y 2 del cierre (ADR-0019) necesitan
  saber *dónde* mirar el estado de git. El Asunto registra qué repos tocó (`jafne abrir
  --repo`); sin eso, esas validaciones no aplican en vez de fallar.
- **Rama principal por descubrimiento** — ADR-0006 dice "develop o staging, según el
  repo". La validación 2 busca la primera de `develop`, `staging`, `main`, `master` que
  exista y contenga la rama del Asunto, en vez de asumir una.
- **`historial.jsonl`** — una línea JSON por mensaje: append-only, sin reescrituras, y una
  línea corrupta no se lleva el resto del historial.
- **`saldo.yaml` aparte de `cerebros.yaml`** — ADR-0025 dice que "cada entrada de
  `cerebros.yaml` necesita además un saldo observado", pero el mismo ADR dice que el
  límite es **del proveedor** y se comparte entre todos los proyectos. Guardarlo por
  cerebro serían tres copias del mismo número para OpenAI, que pueden discrepar. Se guarda
  entonces por proveedor, y en otro archivo: `cerebros.yaml` es lo que el Usuario declara
  y `saldo.yaml` lo que Infraestructura observa, y una máquina que reescribe el primero se
  lleva puestos los comentarios y las declaraciones. `Almacen.cerebros()` los une al leer,
  así que para quien elige cerebro la lista efectivamente dejó de ser estática. **Si esto
  cuenta como decisión y no como consecuencia, merece un ADR que lo diga.**
- **Qué palabras entran en el vocabulario de cadencias** — ADR-0035 decidió que el
  vocabulario es **cerrado** y que lo que no entra se rechaza al leer; cuáles son las dos
  formas concretas (`diaria HH:MM` y `semanal <día> HH:MM`) salió de lo que ADR-0024 pide
  como caso real —el sprint semanal— y nada más. Agregar `mensual` o un cron completo es
  ampliar el catálogo, y por ser catálogo cerrado eso **se decide, no se agrega**.
- **El id del Asunto que abre una cadencia** — `<entrada>-AAAA-MM-DD`. Derivarlo en vez de
  sortearlo es lo que hace idempotente al disparo, así que no es solo un formato: es la
  mitad de cómo ADR-0035 evita duplicados. Su contrapartida es que el id de la entrada no
  puede pasar de 48 caracteres, y se valida al declararlo.
- **El límite de 25 MB de audio y los hilos de CPU del dictado** — ADR-0036 pidió acotar
  el tamaño; el número salió de cuánto pesa un dictado largo con margen. Los hilos son
  `cpu_count() - 2`, elegidos para que el panel siga respondiendo mientras transcribe — y
  medidos después: en el Ryzen 9 6900HS, 14 hilos dan 3,0x tiempo real contra 3,3x con 8 y
  3,2x con los 16, así que dejar dos libres además resultó ser lo más rápido. Los dos
  valores se declaran por variable de entorno.
- **El intervalo ocioso del reloj** — 15 minutos. No es una cadencia: es cada cuánto el
  proceso se entera de que alguien editó `programado.yaml`.
- ~~**Ventanas sin colapsar**~~ — **graduó a ADR-0026.** Era un detalle por prudencia
  —servir las ventanas por separado para no elegir por el Encargado— y resultó ser la
  decisión correcta por una razón mejor que la que se había anotado: no se colapsan porque
  **producen acciones distintas**, no porque falte decidir cómo combinarlas.

## Cómo se saca algo de la lista de pendientes

1. La decisión se congela: gradúa una investigación a ADR, o se escribe un ADR directo
   ([ADR-0005](./adr/0005-cuando-investigar-vs-adr-directo.md)).
2. Se implementa la pieza y se borra su entrada de `src/jafne/pendientes.py`.
3. Se actualiza este documento en el mismo commit.

Los tests fijan el contrato en las dos direcciones: verifican lo implementado **y**
verifican que lo pendiente siga fallando explícito. Si alguien implementa algo sin decidir,
un test se cae.
