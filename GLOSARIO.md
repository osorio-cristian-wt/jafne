# Glosario de JAFNE

Términos del proyecto. Un término por fila, estable.

| Término | Definición |
|---|---|
| **JAFNE** | *Jarvis Assistant For N→ Software Engineering*. El sistema completo. Antes "Engineering OS". |
| **Asistente** | Nivel superior de la jerarquía: la capa que habla con el usuario y orquesta. Corresponde a Claude Code / OpenClaw. |
| **Encargado** | Rol a nivel **proyecto** (cruza varios repos). Documenta estilo Casa Justina, por fuera de los repos. Corre en un cerebro pesado/frontier ([ADR-0003](docs/adr/0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md)). |
| **Agente** | Rol a nivel **repositorio**. Documenta según el estándar de ese repo (arc42 o ADR). |
| **Usuario** | Autoridad final de la cadena de escalación; el único que aprueba capacidades nuevas. Habla con el Asistente, o directo con un Encargado en modo directo. |
| **Cadena de escalación** | Regla de JAFNE: Agente → Encargado → Asistente → Usuario, sin saltar capas ([ADR-0002](docs/adr/0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md)). |
| **Modo directo (attached)** | El Usuario habla con el Encargado sin resumen del Asistente en el medio (ADR-0002). |
| **Modo delegado (async)** | El Usuario delega una tarea; el Asistente resume el resultado del Encargado al terminar, preservando su voz (ADR-0002). |
| **"Jafne"** | Palabra clave para invocar al Asistente y mediar el cambio a modo directo (ADR-0002). |
| **Cerebro** | El proveedor + modelo de IA concreto que ejecuta un rol (Asistente, Encargado o Agente) ([ADR-0003](docs/adr/0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md)). Proveedores iniciales: Claude Code, y la familia OpenAI Luna/Tierra/Sol ([ADR-0010](docs/adr/0010-proveedores-iniciales-asistente.md)). |
| **`.agents/`** | Convención neutral de proveedor para declarar cerebro y capacidades de un repo, en vez de atarse a `.claude/` u otra convención de vendor (ADR-0003). |
| **Capacidad / Skill** | Algo que un Agente sabe hacer en su repo; vive versionada en ese repo y se publica vía GitHub ([ADR-0004](docs/adr/0004-capacidades-por-repositorio.md)). |
| **Asunto** | Unidad persistente de trabajo del Encargado (no una sesión de chat suelta): tiene su propio contenedor/workspace y ciclo de vida — apertura, trabajo, cierre explícito ("cerramos asunto"), reapertura ([ADR-0006](docs/adr/0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md)). Su fuente de verdad vive en `~/.jafne/`, no en el repo del proyecto ([ADR-0007](docs/adr/0007-jerarquia-de-directorios-de-jafne-implementado.md)). |
| **`~/.jafne/`** | Estado local del Asistente: registro de proyectos, cerebros disponibles, saldo observado por proveedor y Asuntos (abiertos y cerrados). No es documentación versionada del proyecto ([ADR-0007](docs/adr/0007-jerarquia-de-directorios-de-jafne-implementado.md)). |
| **`encargado/` (repo)** | Repo único por proyecto para el Encargado: `investigacion/` + `docs/adr/` juntos, misma forma que el propio repo `jafne`. Reemplaza el rol que hoy cumplen por separado `docs-organizacion` y `.github` en BoRR (ADR-0007). |
| **Estado del Asunto** | Catálogo **cerrado** de 5 valores que actualiza el Encargado: `iniciando`, `interactuando_con_el_usuario`, `esperando_respuesta` (timeout de 3 min sin respuesta), `cerrando`, `cerrado`. Independiente del estado del contenedor ([ADR-0009](docs/adr/0009-catalogo-cerrado-estado-asunto.md)). |
| **Estado del contenedor** | Eje de estado que gestiona Infraestructura/Workspace Broker, independiente del estado del Asunto (ADR-0008). Catálogo **cerrado** de 4 valores: `creando`, `activo`, `suspendido`, `destruido` ([ADR-0016](docs/adr/0016-catalogo-cerrado-estado-contenedor.md)). Su ausencia significa que el Asunto nunca tuvo Workspace, que no es lo mismo que `destruido`. |
| **`pregunta_pendiente`** | Marca en `meta.yaml` que el Encargado sube al preguntarle algo al Usuario. Es lo que habilita el timeout de 3 minutos: sin ella, un Asunto callado está trabajando en modo delegado, no esperando ([ADR-0017](docs/adr/0017-timeout-derivado-y-pregunta-pendiente.md)). |
| **Historial** | La conversación de un Asunto, persistida incrementalmente en `~/.jafne/asuntos/<proyecto>/<asunto-id>/historial.jsonl`. Es artefacto del **Asunto**, no del contenedor: sobrevive a que el Workspace se destruya y vuelve al reabrir ([ADR-0018](docs/adr/0018-reapertura-de-asuntos.md)). |
| **Bitácora** | Entrada versionada en `encargado/bitacora/` que escribe el cierre: el resumen durable de qué se hizo en un Asunto. Vive en git para que perder `~/.jafne/` cueste estado operativo, no memoria ([ADR-0021](docs/adr/0021-bitacora-de-cierre-en-el-repo-encargado.md)). |
| **Skill de cierre** | Las cinco validaciones que corren al decir "cerramos asunto": trabajo guardado, merge cerrado, lo hablado documentado, sin Agentes en vuelo, workspace liberado. Es todo-o-nada ([ADR-0019](docs/adr/0019-validaciones-del-cierre-de-asunto.md)). |
| **Panel web** | Punto de entrada gráfico a JAFNE: lista proyectos, permite chatear con el Asistente y —al entrar a un proyecto— con su Encargado, y muestra el uso de las suscripciones ([ADR-0013](docs/adr/0013-panel-web-como-dashboard-visual.md)). El estado de Asuntos lo lee de `~/.jafne/asuntos/`, sin almacén propio (ADR-0008). |
| **Sprint** | Unidad de **planificación** a nivel proyecto. Su estado vive en la herramienta externa que el equipo ya mira —su destinatario son los desarrolladores, no JAFNE— y es un **eje independiente** del Asunto: armar el sprint es en sí mismo el trabajo de un Asunto, no su contenedor ([ADR-0023](docs/adr/0023-sprints-ejes-independientes-y-estado-externo.md)). Se gestiona vía MCP ([ADR-0014](docs/adr/0014-gestion-de-sprints-via-mcp.md)). |
| **Trabajo programado** | Una skill del Encargado más una cadencia. Al dispararse abre un **Asunto normal**, con el mismo ciclo de vida que uno pedido por el Usuario; si necesita una decisión que solo el Usuario puede tomar, se detiene y la deja anotada ([ADR-0024](docs/adr/0024-trabajo-programado-asuntos-disparados-por-tiempo.md)). |
| **Reloj** | El proceso de larga vida que consume la **cola de despertares** y dispara el trabajo programado (`jafne reloj`). Corre **aparte del panel**, que es solo observador: si el reloj no corre, no hay Asuntos disparados por tiempo ([ADR-0035](docs/adr/0035-el-reloj-corre-en-su-propio-proceso.md)). |
| **Cola de despertares** | Una sola cola con dos productores: las cadencias declaradas en `~/.jafne/programado.yaml` (ADR-0024) y los diferimientos one-shot por falta de cupo (ADR-0026). Son el mismo mecanismo —despertar en el instante T y hacer X—, así que no se separan (ADR-0035). |
| **Dictado** | El botón de voz a texto del chat del panel. Corre **local** con Whisper: el audio no sale de la máquina, no se guarda, y el texto va al campo de entrada para revisarlo antes de enviarlo ([ADR-0036](docs/adr/0036-dictado-por-voz-con-whisper-local.md)). |
| **Nodo de voz** | Una máquina de la malla que presta su GPU para transcribir (`jafne voz`). Corre el mismo JAFNE, no lee `~/.jafne/` y no escribe estado: presta cómputo. El panel le delega el dictado declarando `$JAFNE_VOZ_NODO`; sin eso transcribe él mismo ([ADR-0037](docs/adr/0037-el-dictado-puede-delegarse-a-un-nodo-con-gpu.md)). |
| **Saldo** | Cuánto uso queda de una suscripción antes de su límite, con su horizonte de reset — distinto del *gasto* acumulado. Es la métrica operativa: Infraestructura la lleva y el Encargado conmuta de proveedor con ella ([ADR-0025](docs/adr/0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md)). Es del **proveedor**, no del cerebro: el límite es de la suscripción y se comparte entre todos los proyectos. Vive en `~/.jafne/saldo.yaml`. |
| **Ventana** | El período en que un proveedor cuenta su límite, con su propio reset: Claude Code expone una de 5 h y una semanal. Son de **tiempo, no de dinero**, por eso el saldo sin su horizonte de reset no alcanza para decidir (ADR-0025). |
| **Decisión pendiente** | Convención de implementación: una función que depende de una pregunta abierta se expone pero levanta `DecisionPendiente` citando el ADR o la investigación que la bloquea, en vez de improvisar un default ([ADR-0015](docs/adr/0015-stack-inicial-de-implementacion.md)). |
| **Engineering Coordinator** | Componente v0.2 que orquesta el plano de agentes. Relación con "Encargado" por definir. |
| **Infrastructure Manager** | Componente que administra toda la infraestructura de ejecución. A veces referido informalmente como "Encargado de infraestructura". |
| **Workspace** | Entorno de ejecución aislado y efímero donde un agente corre código. Responsable de la red y los puertos: aislamiento entre proyectos, comunicación abierta intra-proyecto, exposición vía ZeroTier ([ADR-0011](docs/adr/0011-redes-y-puertos-de-workspace.md)). |
| **Workspace Broker** | Interfaz por la que los agentes piden/gestionan workspaces sin tocar Docker. |
| **OpenClaw** | Componente de la arquitectura v0.2; rol exacto por definir. |
| **engineering.yaml** | Archivo por repo que declara el entorno de ejecución necesario. |
| **snapshot** | Copia congelada de un workspace, para reanudar o reproducir estado. |
| **graduación** | Pasar un hallazgo de `investigacion/` (Casa Justina) a una decisión congelada (ADR). |
| **Casa Justina** | Estándar de documentación evolutivo/exploratorio (research + análisis + fuentes). |
| **ADR** | *Architecture Decision Record*: decisión congelada, numerada, append-only. |
| **arc42** | Plantilla de arquitectura formal (12 secciones); destino cuando JAFNE se formalice. |
