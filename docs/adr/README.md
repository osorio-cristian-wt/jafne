# Architecture Decision Records (ADRs)

Registro de decisiones de diseño **congeladas**. Cada archivo es **una decisión**,
numerada e inmutable.

La exploración previa (opciones y descartes) vive en [`investigacion/`](../../investigacion/);
acá va solo lo que ya se decidió.

## Esto no es la superficie de lectura

Este directorio es el **historial** del diseño: conserva el *por qué*, incluidos los
descartes. No es de donde se saca *qué es verdad hoy* — para eso hace falta aplicar
mentalmente treinta decisiones en orden, que es caro y sale mal.

La verdad actual vive en dos documentos derivados, y son el punto de entrada:

- [`docs/estado-del-diseno.md`](../estado-del-diseno.md) — qué está decidido hoy, una línea
  por tema, citando el ADR que lo fija.
- [`docs/estado-de-implementacion.md`](../estado-de-implementacion.md) — qué de eso ya
  corre, y qué espera una decisión.

Se baja a un ADR cuando hace falta el porqué de algo puntual, no para reconstruir el
estado. Es la misma relación que un Asunto tiene entre su `historial.jsonl` —append-only,
completo— y su `meta.yaml` —chico, actual, el que se lee para decidir—.

## Cómo evoluciona una decisión

El cuerpo de un ADR **nunca se edita**. El campo `Estado` sí, porque es donde se registra
qué le pasó después:

| Situación | En el ADR viejo | En el ADR nuevo |
|---|---|---|
| La decisión quedó **sin efecto** | `Reemplazada por ADR-YYYY` | `Reemplaza a ADR-XXXX` |
| La decisión **sigue vigente**, pero otra la acota | `Aceptada, matizada por ADR-YYYY` | `Matiza a ADR-XXXX` |

La segunda fila importa más de lo que parece: casi ninguna decisión real se reemplaza, se
**acota**. Sin ella, dos ADR vigentes parecen contradecirse —uno dice que se soportan dos
proveedores, otro que se implementa uno— y quien los lea suelto va a elegir mal.

## Índice

- [ADR-0001](./0001-rebrand-engineering-os-a-jafne.md) — Rebrand *Engineering OS* → JAFNE.
- [ADR-0002](./0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md) — Jerarquía
  de roles, escalación y modos de comunicación. *Matizada por ADR-0044.*
- [ADR-0003](./0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md) — Cerebro por rol y
  agnosticismo de proveedor de IA.
- [ADR-0004](./0004-capacidades-por-repositorio.md) — Capacidades (skills + MCP) por
  repositorio. *Su cadena de escalación fue reemplazada por ADR-0049.*
- [ADR-0005](./0005-cuando-investigar-vs-adr-directo.md) — Cuándo documentar como
  investigación y cuándo directo como ADR.
- [ADR-0006](./0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md) — Asuntos: unidad de
  trabajo persistente del Encargado y su ciclo de vida. *Matizada por ADR-0047.*
- [ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md) — Jerarquía de
  directorios de un JAFNE implementado.
- [ADR-0008](./0008-estado-de-asuntos-y-panel-web.md) — Estado de Asuntos, estado de
  contenedor y panel web de observabilidad. *Matizada por ADR-0043.*
- [ADR-0009](./0009-catalogo-cerrado-estado-asunto.md) — Catálogo cerrado de
  `estado_asunto`.
- [ADR-0010](./0010-proveedores-iniciales-asistente.md) — Proveedores iniciales
  soportados para el rol de Asistente (Claude Code, OpenAI Luna/Tierra/Sol).
  *Matizada por ADR-0028.*
- [ADR-0011](./0011-redes-y-puertos-de-workspace.md) — Redes y puertos de un Workspace:
  aislamiento por proyecto, comunicación intra-proyecto y exposición vía ZeroTier.
  *Matizada por ADR-0050.*
- [ADR-0012](./0012-motor-de-contenedores-podman.md) — Motor de contenedores por
  defecto: Podman. *Matizada por ADR-0032, ADR-0042, ADR-0046 y ADR-0048.*
- [ADR-0013](./0013-panel-web-como-dashboard-visual.md) — Panel web como dashboard visual:
  proyectos, chat con Asistente/Encargado y uso de suscripciones.
  *Matizada por ADR-0039 y ADR-0043.*
- [ADR-0014](./0014-gestion-de-sprints-via-mcp.md) — La gestión de sprints es parte del
  trabajo regular, y se accede vía MCP.
- [ADR-0015](./0015-stack-inicial-de-implementacion.md) — Stack inicial de implementación:
  Python + FastAPI, panel sin build.
- [ADR-0016](./0016-catalogo-cerrado-estado-contenedor.md) — Catálogo cerrado de
  `estado_contenedor`. *Matizada por ADR-0047.*
- [ADR-0017](./0017-timeout-derivado-y-pregunta-pendiente.md) — El timeout de 3 minutos es
  derivado, no persistido; `pregunta_pendiente` en `meta.yaml`.
- [ADR-0018](./0018-reapertura-de-asuntos.md) — Reapertura de un Asunto: el contexto y el
  historial vuelven, el contenedor no.
- [ADR-0019](./0019-validaciones-del-cierre-de-asunto.md) — Catálogo cerrado de las cinco
  validaciones del cierre.
- [ADR-0020](./0020-hosting-y-autenticacion-del-panel.md) — Hosting y autenticación del
  panel: interfaz ZeroTier y token. *Matizada por ADR-0038.*
- [ADR-0021](./0021-bitacora-de-cierre-en-el-repo-encargado.md) — El cierre deja un rastro
  durable en el repo `encargado/`.
- [ADR-0022](./0022-orden-de-la-familia-openai.md) — Orden de tier de la familia OpenAI:
  Sol > Tierra > Luna. *Matizada por ADR-0030.*
- [ADR-0023](./0023-sprints-ejes-independientes-y-estado-externo.md) — Sprint y Asunto son
  ejes independientes; el sprint vive en la herramienta que ve el equipo.
- [ADR-0024](./0024-trabajo-programado-asuntos-disparados-por-tiempo.md) — Trabajo
  programado: Asuntos que se abren solos, por cadencia.
- [ADR-0025](./0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md) — Presupuesto por
  proveedor: la métrica es el saldo, Infraestructura lleva la cuenta, y el Encargado
  conmuta de proveedor. *Matizada por ADR-0042.*
- [ADR-0026](./0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md) — Umbral de
  conmutación: la ventana larga conmuta de proveedor, la corta difiere el trabajo.
- [ADR-0027](./0027-clase-de-riesgo-declarada-por-el-encargado.md) — El Encargado declara
  una clase de riesgo (`revisado` / `generado`); Infraestructura la mapea a driver.
  *Reemplazada por ADR-0045.*
- [ADR-0028](./0028-anthropic-primero-alcance-de-adaptadores.md) — Anthropic primero: un
  solo adaptador implementado, sin cambiar los proveedores soportados. *Matiza a ADR-0010.*
  *Matizada por ADR-0034.*
- [ADR-0029](./0029-el-reloj-corre-en-el-proceso-del-panel.md) — El reloj corre en el
  proceso del panel, con una sola cola de despertares y dos productores.
  *Reemplazada por ADR-0035.*
- [ADR-0030](./0030-tamanos-de-cerebro-catalogo-comun-entre-proveedores.md) — Tamaños de
  cerebro: catálogo común `chico` / `medio` / `grande` / `gigante`. *Matiza a ADR-0022.*
- [ADR-0031](./0031-contrato-de-sesion-reanudable.md) — El contrato de sesión es
  reanudable, no adjuntable, y el proceso del agente es de JAFNE.
- [ADR-0032](./0032-driver-de-la-clase-generado.md) — La clase `generado` corre en
  microVM, como runtime OCI del mismo Podman. *Matiza a ADR-0012.*
  *Reemplazada por ADR-0041, y con ella por ADR-0045.*
- [ADR-0033](./0033-tamano-por-defecto-del-rol-asistente.md) — El Asistente corre en
  `medio`; Encargado y Agente se eligen por tarea. *Matizada por ADR-0044.*
- [ADR-0034](./0034-el-adaptador-usa-la-sesion-de-claude-code.md) — El adaptador maneja la
  CLI de Claude Code y hereda la sesión del Usuario; JAFNE no maneja credenciales.
  *Matiza a ADR-0028.* *Matizada por ADR-0040.*
- [ADR-0035](./0035-el-reloj-corre-en-su-propio-proceso.md) — El reloj corre en su propio
  proceso, separado del panel, que vuelve a ser de solo lectura sobre el estado.
  *Reemplaza a ADR-0029.* *Matizada por ADR-0043.*
- [ADR-0036](./0036-dictado-por-voz-con-whisper-local.md) — El dictado por voz del panel
  corre con Whisper local: el audio no sale de la máquina ni se persiste.
  *Matizada por ADR-0037.*
- [ADR-0037](./0037-el-dictado-puede-delegarse-a-un-nodo-con-gpu.md) — El dictado se puede
  delegar a un nodo con GPU de la malla; sin declararlo sigue siendo local.
  *Matiza a ADR-0036.*
- [ADR-0038](./0038-tls-del-panel-con-ca-propia.md) — El panel sirve TLS con una CA
  propia, y el motivo es desbloquear el micrófono del navegador, no la confidencialidad.
  *Matiza a ADR-0020.*
- [ADR-0039](./0039-el-chat-del-panel-usa-herramientas-acotadas-a-la-raiz-de-repos.md) —
  El chat del panel usa herramientas, acotadas a la raíz de repos del Usuario.
  *Matiza a ADR-0013.*
- [ADR-0040](./0040-identidad-de-rol-en-el-system-prompt.md) — La identidad del rol se
  **agrega** al system prompt del proveedor, versionada en el repo y con un archivo por rol.
  *Matiza a ADR-0034.*
- [ADR-0041](./0041-el-driver-de-generado-es-krun.md) — El driver de la clase `generado` es
  **krun**, no kata: kata 3.x dejó de ser un runtime OCI. *Reemplaza a ADR-0032.*
  *Reemplazada por ADR-0045.*
- [ADR-0042](./0042-infraestructura-es-un-proceso-con-el-mcp-adentro.md) — Infraestructura
  es un proceso propio —Workspaces, saldo y servidor MCP—, y el alcance del MCP viaja en la
  URL. *Matiza a ADR-0025 y ADR-0012.* *Matizada por ADR-0047.*
- [ADR-0043](./0043-los-chats-del-asistente-se-guardan.md) — Los chats del Asistente se
  guardan en `~/.jafne/chats/`; el panel escribe **eso y nada más**.
  *Matiza a ADR-0008, ADR-0013 y ADR-0035.*
- [ADR-0044](./0044-la-cadena-de-delegacion.md) — La cadena de delegación: el Encargado
  tiene alcance de organización y conversa en `grande`; el Agente, de un repositorio.
  *Matiza a ADR-0033 y ADR-0002.* *Matizada por ADR-0047.*
- [ADR-0045](./0045-para-que-existen-los-contenedores.md) — Los contenedores existen para
  dormir/despertar y viajar; el aislamiento baja a consecuencia y JAFNE deja de elegir
  runtime. *Reemplaza a ADR-0027, ADR-0032 y ADR-0041.*
- [ADR-0046](./0046-el-cerebro-corre-afuera-el-contenedor-ejecuta.md) — El cerebro corre
  afuera del contenedor; adentro solo se ejecuta, y la credencial nunca entra.
  *Matiza a ADR-0012.*
- [ADR-0047](./0047-los-contenedores-son-por-repositorio.md) — Un contenedor por
  repositorio, creado al delegar; el Asunto no tiene, y su `estado_contenedor` pasa a ser
  un resumen. *Matiza a ADR-0006, ADR-0016, ADR-0042 y ADR-0044.*
- [ADR-0048](./0048-el-repo-declara-su-entorno-de-desarrollo.md) — Cada repositorio declara
  su entorno de trabajo en un `Dockerfile.dev` propio; JAFNE lo construye y lo usa.
  *Matiza a ADR-0012.* *Matizada por ADR-0049.*
- [ADR-0049](./0049-el-encargado-siembra-el-entorno-y-las-skills-de-un-repo.md) — El
  Encargado siembra el `Dockerfile.dev` y las skills de un repo sin escalar; el control pasa
  a ser revisión del diff. *Matiza a ADR-0004 y ADR-0048.*
- [ADR-0050](./0050-descubrimiento-por-alias-y-registro-de-puertos.md) — Los servicios de
  un proyecto se encuentran por **alias de red** (el nombre del repo), la red se crea con
  `isolate=true`, y publicar hacia la malla pasa por un registro de puertos programado.
  *Matiza a ADR-0011.*

## Plantilla

```markdown
# ADR-NNNN — Título en una frase

- **Estado**: Aceptada | Aceptada, matizada por ADR-YYYY | Reemplazada por ADR-YYYY
- **Fecha**: AAAA-MM-DD
- **Matiza a**: ADR-XXXX  *(solo si acota una decisión vigente)*

## Contexto
Qué problema o pregunta motivó la decisión.

## Decisión
Qué se decidió, en afirmativo.

## Alternativas descartadas
Cada alternativa y por qué se descartó.

## Consecuencias
Qué se gana, qué se paga, y qué reglas impone hacia adelante.
```
