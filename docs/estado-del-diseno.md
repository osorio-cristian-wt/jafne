---
fuentes:
  - docs/adr/
verificado: 2026-08-19
---

# Estado del diseño

**Qué es verdad hoy en JAFNE**, en presente y en un solo lugar. Cada fila cita el ADR que
la fija; se baja al ADR solo cuando hace falta el *por qué* o los descartes.

Este documento y [`estado-de-implementacion.md`](./estado-de-implementacion.md) son el
punto de entrada. [`docs/adr/`](./adr/README.md) es el **historial** de decisiones: conserva
el razonamiento, pero reconstruir el estado actual leyéndolo entero es caro y sale mal.
Misma relación que un Asunto tiene entre su `historial.jsonl` y su `meta.yaml`.

> Este documento dice qué está **decidido**. Qué de eso ya **corre** está en
> [`estado-de-implementacion.md`](./estado-de-implementacion.md), y qué falta **decidir**
> en `src/jafne/pendientes.py` (`jafne pendientes`). Los tres se leen juntos.

## Roles y trabajo

| Tema | Hoy | Fija |
|---|---|---|
| Jerarquía | Usuario → Asistente → Encargado → Agentes, con escalación por la cadena | [ADR-0002](./adr/0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md) |
| Modos de comunicación | Directo (attached) y delegado (con resumen) | ADR-0002 |
| Unidad de trabajo | El **Asunto**: persistente, del Encargado, con ciclo de vida propio | [ADR-0006](./adr/0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md) |
| Quién abre un Asunto | El Usuario, **o el reloj** por cadencia declarada | ADR-0006 + [ADR-0024](./adr/0024-trabajo-programado-asuntos-disparados-por-tiempo.md) |
| Capacidades de un repo | Skills + MCP por repositorio, con aprobación del Usuario | [ADR-0004](./adr/0004-capacidades-por-repositorio.md) |

## Estado de un Asunto

| Tema | Hoy | Fija |
|---|---|---|
| Ejes de estado | Dos, **independientes**: `estado_asunto` y `estado_contenedor` | [ADR-0008](./adr/0008-estado-de-asuntos-y-panel-web.md) |
| `estado_asunto` | Catálogo cerrado de 5, lo escribe el Encargado | [ADR-0009](./adr/0009-catalogo-cerrado-estado-asunto.md) |
| `estado_contenedor` | Catálogo cerrado de 4, lo escribe el Workspace Broker. Su ausencia ≠ `destruido` | [ADR-0016](./adr/0016-catalogo-cerrado-estado-contenedor.md) |
| Timeout de 3 min | **Derivado al leer**, nunca persistido, y solo si `pregunta_pendiente` | [ADR-0017](./adr/0017-timeout-derivado-y-pregunta-pendiente.md) |
| Reapertura | Vuelven historial y contexto; el contenedor **no** | [ADR-0018](./adr/0018-reapertura-de-asuntos.md) |
| Cierre | 5 validaciones, catálogo cerrado, todo-o-nada | [ADR-0019](./adr/0019-validaciones-del-cierre-de-asunto.md) |
| Memoria durable | El cierre deja bitácora en el repo `encargado/` del proyecto | [ADR-0021](./adr/0021-bitacora-de-cierre-en-el-repo-encargado.md) |
| Esperando cupo | **Derivado**, no persistido: `interactuando_con_el_usuario` + `suspendido` | [ADR-0026](./adr/0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md) |

## Cerebros

| Tema | Hoy | Fija |
|---|---|---|
| Elección | Un cerebro por rol; JAFNE es agnóstico de proveedor | [ADR-0003](./adr/0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md) |
| Política de gasto | Más tokens antes que rehacer | ADR-0003 |
| Proveedores **soportados** | Claude Code y la familia OpenAI (Luna / Tierra / Sol) | [ADR-0010](./adr/0010-proveedores-iniciales-asistente.md) |
| Adaptador **implementado** | Solo Anthropic. Los cerebros de OpenAI se declaran y fallan explícito | [ADR-0028](./adr/0028-anthropic-primero-alcance-de-adaptadores.md) |
| Tamaño | Catálogo cerrado común: `chico` / `medio` / `grande` / `gigante` | [ADR-0030](./adr/0030-tamanos-de-cerebro-catalogo-comun-entre-proveedores.md) |
| Correspondencia | chico=Haiku/Luna · medio=Sonnet/Tierra · grande=Opus/Sol · gigante=Fable | ADR-0030 |
| Tamaño del Asistente | `medio`. Conversa, enruta y delega; el trabajo difícil va abajo | [ADR-0033](./adr/0033-tamano-por-defecto-del-rol-asistente.md) |
| Tamaño de Encargado y Agente | Sin default: lo elige el Encargado **por tarea** | ADR-0003 + ADR-0033 |
| Roles con cerebro | Catálogo cerrado: `asistente`, `encargado`, `agente`. El Usuario no está | ADR-0002 + ADR-0033 |
| Facturación | **Suscripciones personales**, no organización | [ADR-0025](./adr/0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md) |
| Métrica | **Saldo** (cuánto queda), no gasto. La lleva Infraestructura | ADR-0025 |
| Umbral | 20 % restante de una ventana | ADR-0026 |
| Ventana larga bajo umbral | **Conmutar** de proveedor | ADR-0026 |
| Ventana corta bajo umbral | **Diferir**: esperar el reset, no conmutar | ADR-0026 |
| Conmutar a mitad de un Asunto | **No.** Solo Asuntos nuevos | ADR-0026 |

> Las dos primeras filas de proveedor se leen juntas: *soportado* es diseño, *implementado*
> es alcance. Que haya un solo adaptador no suspende el agnosticismo de ADR-0003.

## Workspaces

| Tema | Hoy | Fija |
|---|---|---|
| Quién los crea | El Workspace Broker. Los Agentes **nunca** hablan con el motor | [ADR-0012](./adr/0012-motor-de-contenedores-podman.md) |
| Motor por defecto | Podman | ADR-0012 |
| Red | Aislada por proyecto; exposición solo vía ZeroTier | [ADR-0011](./adr/0011-redes-y-puertos-de-workspace.md) |
| Aislamiento | El Encargado declara clase de riesgo; Infraestructura mapea a driver | [ADR-0027](./adr/0027-clase-de-riesgo-declarada-por-el-encargado.md) |
| Runtime por clase | `revisado` → `crun`; `generado` → `kata` (microVM). Dos runtimes del **mismo** Podman | [ADR-0032](./adr/0032-driver-de-la-clase-generado.md) |
| Si falta el runtime | Se **rechaza** el Workspace. Nunca se degrada en silencio | ADR-0032 |
| Clases de riesgo | Catálogo cerrado de 2: `revisado` / `generado`. **Default `generado`** | ADR-0027 |
| Dónde viaja el riesgo | En el pedido de Workspace — es propiedad de la tarea, no del repo | ADR-0027 |

## Panel y procesos

| Tema | Hoy | Fija |
|---|---|---|
| Qué es | Dashboard visual: proyectos, Asuntos, chat y uso de suscripciones | [ADR-0013](./adr/0013-panel-web-como-dashboard-visual.md) |
| Sobre el estado | Solo lectura, **sin excepciones**: lo muestra, no lo escribe | ADR-0008 + ADR-0013 + [ADR-0035](./adr/0035-el-reloj-corre-en-su-propio-proceso.md) |
| Hosting | Nunca en todas las interfaces; fuera de loopback exige token | [ADR-0020](./adr/0020-hosting-y-autenticacion-del-panel.md) |
| Quién corre el reloj | Un **proceso propio** (`jafne reloj`), no el panel | ADR-0035 |
| Reloj | Una cola de despertares, dos productores: cadencias y diferimientos | ADR-0035 |
| Dónde se declaran | `~/.jafne/programado.yaml` | ADR-0035 + [ADR-0007](./adr/0007-jerarquia-de-directorios-de-jafne-implementado.md) |
| Forma de una cadencia | Vocabulario **cerrado**; una que no se entiende se rechaza al leer | ADR-0035 |
| Hora de una cadencia | La **local** de la máquina que corre el reloj, no UTC | ADR-0035 |
| Despertar vencido | **No se repone**: el reloj caído no dispara lo atrasado al levantar | ADR-0035 |
| Cuántos relojes | Uno por almacén: candado + id de Asunto derivado de entrada y fecha | ADR-0035 |
| Dictado por voz | Botón de voz a texto en el chat del panel, con **Whisper local** | [ADR-0036](./adr/0036-dictado-por-voz-con-whisper-local.md) |
| Dónde va el audio | No sale de **las máquinas del Usuario** y **no se persiste** | ADR-0036 + [ADR-0037](./adr/0037-el-dictado-puede-delegarse-a-un-nodo-con-gpu.md) |
| Modelo de voz | El grande (`large-v3`) por defecto; se declara, no se adivina | ADR-0036 |
| Si falta el motor de voz | Se **rechaza** y se dice qué falta. Nunca se degrada a un modelo más chico | ADR-0036 |
| El dictado y el estado | Transcribir es cómputo, no escritura: el panel **sigue** siendo solo lectura | ADR-0036 + ADR-0035 |
| Dónde transcribe | Acá por defecto; con `$JAFNE_VOZ_NODO` en un nodo con GPU de la malla | ADR-0037 |
| Qué corre el nodo | El **mismo JAFNE** (`jafne voz`), no un servidor de terceros | ADR-0037 |
| Qué sabe el nodo | Nada: presta cómputo, no lee `~/.jafne/` y no escribe estado | ADR-0037 |
| Si el nodo no contesta | Se **rechaza**. Nunca cae a la CPU local en silencio | ADR-0037 |
| Acceso al nodo | ADR-0020 completo: nunca todas las interfaces, token fuera de loopback | ADR-0037 + ADR-0020 |

> ADR-0035 **reemplaza** a ADR-0029, que había puesto el reloj adentro del panel. Lo que
> sobrevive es la cola única con dos productores y `programado.yaml`; lo que se revierte es
> el proceso — y con él la excepción que ADR-0029 le había abierto al panel para escribir
> estado.

## Sesión con el agente

| Tema | Hoy | Fija |
|---|---|---|
| Forma del contrato | Sesión **reanudable**, no adjuntable: se vuelve por id, no se engancha a un turno vivo | [ADR-0031](./adr/0031-contrato-de-sesion-reanudable.md) |
| Operaciones | Cuatro: `abrir`, `reanudar`, `emitir`, `saldo` | ADR-0031 |
| Dueño del proceso | **JAFNE.** El panel se adjunta a JAFNE, no al proveedor | ADR-0031 |
| Multiplexar observadores | Trabajo de JAFNE — ningún proveedor lo ofrece | ADR-0031 |
| Rehidratar | Reanudar por id; reinyectar el historial es el piso | ADR-0031 + ADR-0018 |
| Dónde vive el id de sesión | En el `meta.yaml` del Asunto | ADR-0031 |
| Sobre qué se escribe el adaptador | La **CLI** de Claude Code como subproceso, no el SDK | [ADR-0034](./adr/0034-el-adaptador-usa-la-sesion-de-claude-code.md) |
| Login de JAFNE | **No existe.** La sesión es de Claude Code y JAFNE la hereda | ADR-0034 |
| Credenciales | JAFNE no las pide, no las guarda, no las ve. Solo reporta su estado | ADR-0034 |
| Alcance de uso | **Un solo Usuario**, dueño de la cuenta. Es lo que valida esta lectura de los términos | ADR-0034 |

## Sprints

| Tema | Hoy | Fija |
|---|---|---|
| Modelo | Sprint y Asunto son **ejes independientes** | [ADR-0023](./adr/0023-sprints-ejes-independientes-y-estado-externo.md) |
| Dónde vive el estado | En la herramienta externa que el equipo ya mira | ADR-0023 |
| Cómo se accede | Como capacidad MCP, durante el trabajo normal | [ADR-0014](./adr/0014-gestion-de-sprints-via-mcp.md) |
| Cuál herramienta | **Sin decidir** — ver `jafne pendientes` | — |

## Cómo se documenta

| Tema | Hoy | Fija |
|---|---|---|
| Estándar | Híbrido ADR + Casa Justina. arc42 queda para cuando se formalice | [WORKFLOW.md](../WORKFLOW.md) |
| Cuándo investigar | Solo si hay que buscar y comparar alternativas reales | [ADR-0005](./adr/0005-cuando-investigar-vs-adr-directo.md) |
| Cuándo ADR directo | Cuando llega un requisito o una decisión ya tomada | ADR-0005 |
| Evolución de un ADR | El cuerpo nunca se edita; el `Estado` registra si fue **reemplazada** o **matizada** | [adr/README](./adr/README.md) |
| Regla de implementación | Lo que no está decidido no se programa: falla citando qué lo bloquea | [ADR-0015](./adr/0015-stack-inicial-de-implementacion.md) |
| Stack | Python + FastAPI, panel sin build | ADR-0015 |

## Cómo se actualiza este documento

En el **mismo commit** que agrega o cambia un ADR. Si un ADR nuevo acota a uno viejo, acá
se ve una sola fila con la verdad combinada — que es justamente lo que evita que dos ADR
vigentes parezcan contradecirse.
