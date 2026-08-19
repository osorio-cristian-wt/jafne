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
  - docs/adr/0038-tls-del-panel-con-ca-propia.md
  - docs/adr/0039-el-chat-del-panel-usa-herramientas-acotadas-a-la-raiz-de-repos.md
  - docs/adr/0040-identidad-de-rol-en-el-system-prompt.md
  - docs/adr/0041-el-driver-de-generado-es-krun.md
  - docs/adr/0042-infraestructura-es-un-proceso-con-el-mcp-adentro.md
  - docs/adr/0043-los-chats-del-asistente-se-guardan.md
  - docs/adr/0044-la-cadena-de-delegacion.md
  - docs/adr/0045-para-que-existen-los-contenedores.md
  - docs/adr/0046-el-cerebro-corre-afuera-el-contenedor-ejecuta.md
  - docs/adr/0047-los-contenedores-son-por-repositorio.md
  - docs/adr/0048-el-repo-declara-su-entorno-de-desarrollo.md
  - docs/adr/0049-el-encargado-siembra-el-entorno-y-las-skills-de-un-repo.md
  - docs/adr/0050-descubrimiento-por-alias-y-registro-de-puertos.md
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

Infraestructura corre aparte (ADR-0042). Es el cuarto proceso, y el que crea Workspaces,
lleva el saldo y sirve el MCP que consultan el Asistente y los Encargados:

```bash
jafne infra                                # http://127.0.0.1:8732
```

Necesita **Podman** para crear Workspaces (ADR-0012). En Windows va sobre WSL2:

```bash
winget install RedHat.Podman
podman machine init && podman machine start
```

Y nada más: desde [ADR-0045](./adr/0045-para-que-existen-los-contenedores.md) JAFNE **no
elige runtime**, usa el default (`crun`) y entra a los contenedores con `podman exec`. Ya no
hace falta instalar `krun` ni `libkrun`, que era lo que pedía ADR-0041 cuando el aislamiento
todavía era el motivo.

El saldo lo escribe **solo Infraestructura** (ADR-0025, ADR-0042): `jafne saldo` es cliente
suyo y falla diciéndolo si está apagada. Cada llamada actualiza una ventana y conserva las
otras:

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

Cómo dejar los tres procesos corriendo solos en Windows —tareas programadas, reglas de
firewall y el acceso al panel desde la malla ZeroTier— está en la sección **Operación** del
[README](../README.md#operación).

Tests: `.venv/Scripts/python -m pytest` (386 casos, verde al 2026-08-19). Ninguno toca
Podman ni la CLI de Claude: los dos se sustituyen, porque la suite tiene que correr en una
máquina sin motor instalado y sin gastar el saldo del Usuario.

## Estructura

```
src/jafne/
  pendientes.py        registro de decisiones abiertas + DecisionPendiente
  nucleo/
    estados.py         los dos ejes de estado de un Asunto (ADR-0009, ADR-0016)
    tamanos.py         tamaño de cerebro común entre proveedores (ADR-0030)
    adaptadores.py     qué proveedores se pueden usar hoy (ADR-0028)
    senal_saldo.py     proceder / conmutar / diferir (ADR-0026)
    roles.py           roles y su tamaño por defecto (ADR-0033)
    sesion.py          el contrato neutral de sesión (ADR-0031)
    adaptador_anthropic.py  el contrato sobre la CLI de Claude Code (ADR-0034)
    prompts/           la identidad de cada rol, uno por rol: los tres (ADR-0040, ADR-0044)
    mcp.py             cómo se le declara el MCP a cada rol, acotado (ADR-0042)
    credenciales.py    estado de la credencial, sin tocarla (ADR-0034)
    motor.py           lo único que sabe que Podman existe (ADR-0012, ADR-0041)
    workspaces.py      el Workspace Broker: el Workspace persiste (ADR-0016, ADR-0042)
    capacidades.py     lector de `.agents/`: skills y MCP del repo (ADR-0004, ADR-0003)
    puertos.py         registro de puertos publicados hacia la malla (ADR-0050)
    despertares.py     la cola de despertares, como función del tiempo (ADR-0035)
    transcripcion.py   dictado por voz: local o delegado (ADR-0036, ADR-0037)
    modelos.py         Proyecto, Cerebro, Asunto, Mensaje, Suscripcion, Ventana
    almacen.py         lectura/escritura de ~/.jafne/ (ADR-0007, ADR-0018, ADR-0025)
    cierre.py          skill de cierre: 5 validaciones + bitácora (ADR-0019, ADR-0021)
  panel/
    api.py             FastAPI: JSON, estáticos y token (ADR-0013, ADR-0020)
    web/               index.html + estilo.css + app.js, sin build (ADR-0015)
  infraestructura.py   el 4º proceso: Workspaces, saldo y servidor MCP (ADR-0042)
  acceso.py            bind, token y TLS, compartidos por panel y nodo (ADR-0020, ADR-0038)
  servicio.py          ciclo de vida común de panel y nodo: log sin ruido inofensivo
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
| Por qué un Asunto no avanza | Derivado de los dos ejes al leer, nunca guardado: un Asunto en `iniciando` dice si nunca se le pidió Workspace, si se está creando, si se destruyó, o si falta el primer turno del Encargado. | ADR-0009 + ADR-0016 |
| Ciclo de vida del Workspace | `lanzar`, `suspender` (`podman pause`), `reanudar` (`unpause`), `registro` (`logs`) y `destruir`. Crear**lo al abrir un Asunto** sigue pendiente: falta la imagen y qué proceso corre adentro. | [ADR-0016](./adr/0016-catalogo-cerrado-estado-contenedor.md) + ADR-0042 |
| Registro de un contenedor | `GET /api/workspaces/<n>/registro` en Infraestructura; el panel lo pide **por repo** (`?repo=`), porque un Asunto ya no tiene un solo contenedor. | ADR-0042 + ADR-0047 |
| Identidad de un rol, visible | `GET /api/roles/<rol>/identidad`: el prompt que se le agrega, su punto de entrada MCP y las herramientas que ve, preguntadas en vivo con el acotamiento por URL ya aplicado. | ADR-0040 + ADR-0042 |
| Capacidades de un repo | Lector de `.agents/skills/*/SKILL.md` y `.mcp.json`, acotado a la raíz de trabajo. Del MCP salen **solo los nombres**, nunca las URLs. No inyecta nada en un Workspace ni crea capacidades. | [ADR-0004](./adr/0004-capacidades-por-repositorio.md) + ADR-0003 |
| Panel: bind y token | Se niega a escuchar en todas las interfaces, y fuera de loopback exige token (query, cabecera o cookie). | [ADR-0020](./adr/0020-hosting-y-autenticacion-del-panel.md) |
| Panel: solo lectura del estado | Muestra estado e historial, no los escribe: los escriben el Encargado y el Workspace Broker. | [ADR-0008](./adr/0008-estado-de-asuntos-y-panel-web.md) |
| Tamaño de cerebro | Catálogo cerrado común a proveedores: `chico`/`medio`/`grande`/`gigante`. El vocabulario que reemplaza (`liviano`/`intermedio`/`pesado`) se traduce al leer para no romper un `~/.jafne/` viejo, y uno fuera del catálogo se rechaza. | [ADR-0030](./adr/0030-tamanos-de-cerebro-catalogo-comun-entre-proveedores.md) |
| Degradación al conmutar | `degradar()` da el mayor tamaño que cubre el proveedor destino: `gigante` → `grande` al pasar a OpenAI. La consecuencia de ADR-0026 hecha código. | ADR-0030 + ADR-0026 |
| Señal de saldo | Función pura: entra una `Suscripcion` y un instante, sale `proceder`, `conmutar` o `diferir` con hora de reanudación. Las ventanas no se colapsan: lo que clasifica es el horizonte de reset, no el nombre. | [ADR-0026](./adr/0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md) |
| Sin clase de riesgo ni runtime elegido | `riesgo.py` **borrado**. `crear_contenedor()` ya no pasa `--runtime`: se usa el default de Podman, que es donde `podman exec` funciona. `runtimes()` queda solo para informar. | [ADR-0045](./adr/0045-para-que-existen-los-contenedores.md) |
| Cerebros sin adaptador | Se listan igual, marcados, y usarlos falla con `AdaptadorNoImplementado` — un error propio, distinto de `DecisionPendiente`. | [ADR-0028](./adr/0028-anthropic-primero-alcance-de-adaptadores.md) |
| Contenedor por repositorio | `Pedido` lleva proyecto, Asunto y repo; el contenedor se llama `jafne-<proyecto>-<asunto>-<repo>`. El Asunto no tiene contenedor propio. | [ADR-0047](./adr/0047-los-contenedores-son-por-repositorio.md) |
| Entrar al contenedor | `Broker.ejecutar()` sobre `podman exec`. Reemplazó al par `esperar`/`correr`: con un contenedor que persiste, esperar a que termine es esperar para siempre. | ADR-0045 |
| Imagen del repo | `Broker.construir()` corre `podman build` con el `Dockerfile.dev` del repo. Sin ese archivo devuelve `None` y se cae a la imagen por defecto, que hoy es el caso de todos los repos. | [ADR-0048](./adr/0048-el-repo-declara-su-entorno-de-desarrollo.md) |
| Disparador de la delegación | `Broker.delegar()` construye y lanza en un paso, y monta el repo en `/repos/<repo>`. Expuesto como `POST /api/workspaces` y como la herramienta MCP `agente_delegar` del Encargado. El repo se valida contra la raíz de trabajo antes de montarlo. | [ADR-0047](./adr/0047-los-contenedores-son-por-repositorio.md) + ADR-0039 |
| Identidad del Agente | `nucleo/prompts/agente.md`: alcance de un repositorio, trabaja en su contenedor, y **pide al Encargado que rearme** en vez de instalar a mano. Tiene prompt pero **no** MCP: son cosas separadas. | ADR-0040 + ADR-0044 + [ADR-0049](./adr/0049-el-encargado-siembra-el-entorno-y-las-skills-de-un-repo.md) |
| Aislamiento real entre proyectos | La red se crea con `--opt isolate=true`. Sin eso, verificado el 2026-08-19, el bff de un proyecto pinguea el back de otro con 0% de pérdida — la garantía de ADR-0011 era falsa. | [ADR-0050](./adr/0050-descubrimiento-por-alias-y-registro-de-puertos.md) |
| Descubrimiento por alias | El contenedor entra a la red con `alias=<repo>`, así que el bff llama a `back` y funciona en cualquier proyecto. | ADR-0050 |
| Registro de puertos | `nucleo/puertos.py`: primer libre del rango 9000-9999, idempotente por (contenedor, puerto interno), liberado al destruir, persistido en `~/.jafne/puertos.json`. | ADR-0050 |
| Keep-alive impuesto | El contenedor corre `sleep infinity` y no el `CMD` del repo, para que un servicio que crashea no se lleve puesto el lugar de trabajo del Agente. | ADR-0048 |
| Resumen de contenedores | `resumir_contenedores()` deriva el `estado_contenedor` del Asunto de los de sus Agentes: `activo` gana sobre `suspendido`, y sin Agentes es `None`. | ADR-0047 + ADR-0016 |
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
| Adaptador de Anthropic | Las cuatro operaciones de ADR-0031 sobre la CLI: `abrir` inventa el id y lo impone con `--session-id`, `reanudar` usa `--resume`, `emitir` corre `-p … --output-format json`. `abrir` y `reanudar` no gastan un token. | [ADR-0034](./adr/0034-el-adaptador-usa-la-sesion-de-claude-code.md) + ADR-0028 + ADR-0031 |
| Chat del panel con el Asistente | Conversa de verdad, con memoria entre turnos: el segundo turno reanuda la sesión del proveedor en vez de reinyectar el historial. La sesión vive en memoria del proceso —el panel no escribe estado—. | [ADR-0013](./adr/0013-panel-web-como-dashboard-visual.md) + ADR-0031 |
| Chat con herramientas acotadas | El agente trabaja dentro de `C:/Repos` (`--add-dir` + `acceptEdits`); afuera el proveedor deniega y el turno termina pidiendo permiso. Verificado contra la CLI real: adentro escribe y lee, afuera no filtró el contenido. | [ADR-0039](./adr/0039-el-chat-del-panel-usa-herramientas-acotadas-a-la-raiz-de-repos.md) |
| Identidad del Asistente | `--append-system-prompt-file` con el texto de `nucleo/prompts/asistente.md`: rol, jerarquía, borde y que las decisiones son del Usuario. Verificado contra la CLI real: preguntado quién es, contesta las cuatro cosas sin que el mensaje se las diga. | [ADR-0040](./adr/0040-identidad-de-rol-en-el-system-prompt.md) |
| Identidad del Encargado | `nucleo/prompts/encargado.md`: alcance de **organización** —no de repositorio—, que delega un Agente por repo, y que escala al Asistente en vez de decidir. | [ADR-0044](./adr/0044-la-cadena-de-delegacion.md) |
| Chat del Encargado | Dejó de responder 501: conversa en `grande`, que es lo que el Usuario fijó. La entrada `cerebro-del-encargado-conversando` salió de `pendientes.py` en el mismo commit. | ADR-0044 + ADR-0033 |
| Chats guardados | `~/.jafne/chats/<id>/` con `meta.yaml` + `historial.jsonl`, la misma forma que un Asunto. Guarda el id de sesión **y** el transcript; nuevo por defecto, los viejos se listan, se retoman por id y se borran a mano. El título sale del primer mensaje. | [ADR-0043](./adr/0043-los-chats-del-asistente-se-guardan.md) |
| El motor de contenedores | `nucleo/motor.py`: encuentra Podman, dice si está encendido y qué runtimes tiene. Sabe que en Windows el cliente es **remoto** y que `--runtime` no viaja por ahí, así que lo que necesita elegir runtime va por `podman machine ssh`. | ADR-0012 + [ADR-0041](./adr/0041-el-driver-de-generado-es-krun.md) |
| Workspace Broker | Construye, lanza, suspende, reanuda, ejecuta y destruye. Crea la red por proyecto con `isolate=true` y le pone al contenedor el alias de su repo. Verificado contra Podman real el 2026-08-19: `pause`/`unpause` y el montaje desde `/mnt/c` funcionan. | [ADR-0042](./adr/0042-infraestructura-es-un-proceso-con-el-mcp-adentro.md) + [ADR-0050](./adr/0050-descubrimiento-por-alias-y-registro-de-puertos.md) |
| Infraestructura | `jafne infra`, el cuarto proceso. Sirve el estado del motor, los Workspaces vivos y el saldo, con ADR-0020 completo por `acceso.py`. | ADR-0042 |
| Servidor MCP | JSON-RPC sobre HTTP, sin SDK: `initialize`, `ping`, `tools/list` y `tools/call`. Seis herramientas — proyectos, Asuntos, detalle, abrir Asunto, saldo y estado del motor. Un fallo de herramienta vuelve como resultado con `isError`, no como error de protocolo, para que el agente pueda leerlo. | ADR-0042 + [ADR-0004](./adr/0004-capacidades-por-repositorio.md) |
| Alcance por rol del MCP | El Asistente entra por `/mcp/asistente` y ve todo; un Encargado por `/mcp/proyecto/<id>` y ve el suyo. Un argumento `proyecto` de un Encargado se **ignora**, y sus herramientas ni siquiera lo listan. | ADR-0042 + ADR-0002 |
| El MCP declarado al agente | `nucleo/mcp.py` arma la config y el adaptador la pasa inline con `--mcp-config`, más `--allowed-tools mcp__jafne`. La URL —y con ella el alcance— la arma JAFNE a partir del rol y del proyecto, nunca el agente. El token va en la cabecera, no en la URL, que se ve en un listado de procesos. Verificado contra la CLI real: el Asistente lista los proyectos, y un Encargado que intenta pasar otro proyecto por argumento no puede. | ADR-0042 + ADR-0044 |
| El saldo lo escribe Infraestructura | `POST /api/saldo` es el único escritor; `jafne saldo` es cliente. Apagada, la CLI falla diciendo cómo levantarla en vez de escribir el archivo por atrás. | ADR-0042 + ADR-0025 |
| `saldo()` del adaptador | Devuelve `None` a propósito: la CLI informa **gasto** del turno y ADR-0025 fijó que la métrica es el **saldo**. Inventar uno desde el otro sería resolver `medicion-de-consumo` por la puerta de atrás. | ADR-0025 + ADR-0031 |
| Voz: delegar en un nodo | `$JAFNE_VOZ_NODO` manda el audio a otra máquina de la malla; sin declararlo se transcribe acá. El panel muestra en cuál se transcribió. | [ADR-0037](./adr/0037-el-dictado-puede-delegarse-a-un-nodo-con-gpu.md) |
| Voz: el nodo | `jafne voz` levanta dos endpoints y nada más: no lee `~/.jafne/` y no puede escribir estado. Un nodo con `$JAFNE_VOZ_NODO` puesto transcribe igual, no se reenvía a sí mismo. | ADR-0037 |
| Voz: nodo caído | `NodoInalcanzable` → 501 con el motivo. **No** cae a la CPU local: la diferencia de latencia tiene que verse. | ADR-0037 |
| Voz: GPU o CPU | `auto` elige CUDA si CTranslate2 la ve, con `float16`; en CPU, `int8`. Declarar `cuda` y que no haya se rechaza. | ADR-0037 |
| TLS del panel y del nodo | `--cert`/`--clave` (o sus variables) hacen que uvicorn sirva HTTPS. Se exigen los dos o ninguno, y se comprueba que los archivos existan **antes** de escuchar. | [ADR-0038](./adr/0038-tls-del-panel-con-ca-propia.md) |
| Aviso al servir sin TLS | Fuera de loopback avisa que el navegador no va a dar micrófono, aclarando que el tráfico igual va cifrado por la malla. No se rechaza: mirar el dashboard sin TLS es legítimo. | ADR-0038 + ADR-0011 |
| Bind y token compartidos | La comprobación de ADR-0020 es una sola función para el panel y para el nodo: dos servicios con reglas de acceso copiadas terminan con reglas distintas. | ADR-0020 + ADR-0037 |
| CLI | `init`, `proyectos`, `asuntos`, `abrir`, `estado`, `contenedor`, `pregunta`, `anotar`, `historial`, `reabrir`, `cerrar`, `saldo`, `cerebros`, `credencial`, `pendientes`, `panel`, `reloj`, `voz`, `infra`. Fuerza UTF-8 en la salida: la consola de Windows es cp1252 y `jafne pendientes` moría con el `→` del hop 4. | ADR-0007/0009/0013/0016-0021/0025-0035/0042 |

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
| `workspace-broker` | **Descubrimiento de servicios que no son repos** —base de datos, colas— y por lo tanto no tienen alias de red. Los repos del proyecto ya se resuelven por alias (ADR-0050), y crear contenedores tampoco está bloqueado: el disparador corre. | [ADR-0011](./adr/0011-redes-y-puertos-de-workspace.md) + [ADR-0050](./adr/0050-descubrimiento-por-alias-y-registro-de-puertos.md) |
| `sprints` | El modelo está decidido (ejes independientes, estado afuera); falta **cuál** herramienta y qué vocabulario mínimo sirve para hablarle a cualquiera. Sin eso no hay contrato MCP que programar. | [ADR-0023](./adr/0023-sprints-ejes-independientes-y-estado-externo.md) + [ADR-0014](./adr/0014-gestion-de-sprints-via-mcp.md) |
| `rotacion-de-token` | Cada cuánto rota el token, quién lo rota y qué hacer si se filtra. Ahora son **dos** tokens, uno por servicio. El TLS ya se decidió (ADR-0038). | ADR-0020 + ADR-0038 |
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
| La skill de un trabajo programado | ADR-0024 + ADR-0035 | El reloj abre el Asunto y anota qué skill hay que correr; correrla es el adaptador otra vez. Hasta entonces el Asunto queda en `iniciando` con el pedido visible, que es lo honesto: el trabajo programado dispara de verdad, y lo que no pasa se ve. |
| `session_id` del proveedor en `meta.yaml` | ADR-0031 | El adaptador ya lo produce, pero quien lo escribiría es el Encargado trabajando un Asunto, y ese camino no existe todavía. El chat del panel **no** puede persistirlo: escribiría estado (ADR-0035). Se agrega cuando haya quien lo escriba. |
| Retomar el trabajo diferido por cupo | ADR-0026 + ADR-0035 | **Quien despierta ya existe**: el reloj encola el reset de `saldo.yaml` y llega a horario. Lo que falta es retomar el Asunto cuando llega, que es el adaptador. El disparo lo informa en vez de aparentar que corrió, y la hora sigue siendo correcta sobre un dato que hoy se carga a mano. |
| Generar un proyecto | ADR-0044 | Está decidido qué es: entrada en `proyectos.yaml`, uno o más repos, scaffold y `engineering.yaml` con sus capacidades (ADR-0004). Falta escribirlo, y depende de qué scaffolds existan. |

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
