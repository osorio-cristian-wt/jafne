---
fuentes:
  - docs/estado-del-diseno.md
  - docs/estado-de-implementacion.md
  - docs/adr/
verificado: 2026-08-19
---

# Encargo pendiente — para delegar

Trabajo pedido y todavía no hecho. Este documento es el **traspaso**: lo que hay que
construir, qué ya está decidido, y —sobre todo— **qué falta preguntarle al Usuario antes de
escribir una línea**.

No es documentación de diseño: cuando un encargo se termina, su sección se borra de acá y lo
que quede vive en su ADR y en los dos derivados.

---

## Regla nº 1: las decisiones son del Usuario

**No tomes decisiones de diseño. Presentá opciones y esperá.**

El 2026-08-19 el Usuario cortó una sesión larga por esto. Lo que había pasado: se
escribieron como ADR varias decisiones que el agente tomó por su cuenta —apagarle las
herramientas al chat, el catálogo cerrado de cadencias, no reponer despertares vencidos,
que `saldo()` devolviera `None`—. Lo grave no fue elegir: fue **congelarlas en un ADR**,
que las deja con apariencia de acordadas.

Concretamente:

- Ante una bifurcación con consecuencias, preguntá con las opciones y su costo.
- El ADR se escribe **después** de que el Usuario decidió, y registra **su** decisión.
- Sí te corresponde sin preguntar: bugs, consecuencias mecánicas, y trabajo ya decidido.
- Si dudás de si algo es decisión, es decisión.

Esto vale también para lo que **descubrís mientras construís**. El 2026-08-19 apareció que
`krun` no permite `podman exec`, y ahí se cometió el error en las dos direcciones: primero
se preguntó bien y salió ADR-0042, pero adentro de ese ADR se coló una cláusula que nadie
había pedido —*"un Workspace es una tarea y muere"*— derivada mal de ese mismo hallazgo. El
Usuario la detectó y hubo que revertirla con seis ADR encima. Un hallazgo técnico acota lo
que es posible; **no decide** lo que se hace con eso.

---

## Antes de empezar

Leé en este orden, y nada más:

1. [`WORKFLOW.md`](../WORKFLOW.md) — cómo se documenta este repo. Es obligatorio.
2. [`docs/estado-del-diseno.md`](./estado-del-diseno.md) — qué está decidido hoy.
3. [`docs/estado-de-implementacion.md`](./estado-de-implementacion.md) — qué corre.

**No leas `docs/adr/` entero**: es el historial. Bajá a un ADR puntual cuando necesites el
*por qué* de algo concreto.

Las reglas que más se rompen sin querer:

- El **cuerpo de un ADR nunca se edita**. Solo su campo `Estado`, para registrar si fue
  *reemplazada* o *matizada*.
- Los dos derivados y el índice de `docs/adr/README.md` se actualizan **en el mismo
  commit** que el ADR.
- **Lo que no está decidido no se programa**: se declara en `src/jafne/pendientes.py` y
  falla citando qué lo bloquea.
- Tests: nombres descriptivos en español, un comportamiento por test, y comentarios que
  citan el ADR que fijan. `.venv/Scripts/python -m pytest` — 386 en verde al 2026-08-19.

---

## Lo que se cerró el 2026-08-19

Se dejan nombrados —no descritos— para que nadie los vuelva a abrir creyendo que faltan.

**Primera tanda:**

| Encargo | Dónde vive ahora |
|---|---|
| El prompt del Asistente | [ADR-0040](./adr/0040-identidad-de-rol-en-el-system-prompt.md) |
| Los chats versionados | [ADR-0043](./adr/0043-los-chats-del-asistente-se-guardan.md) |
| El servidor MCP | [ADR-0042](./adr/0042-infraestructura-es-un-proceso-con-el-mcp-adentro.md) |
| La cadena de delegación | [ADR-0044](./adr/0044-la-cadena-de-delegacion.md) |

**Segunda tanda, el mismo día**, y con un replanteo de fondo del Usuario que dio vuelta el
modelo de contenedores:

| Encargo | Dónde vive ahora |
|---|---|
| Para qué existen los contenedores | [ADR-0045](./adr/0045-para-que-existen-los-contenedores.md) |
| El cerebro corre afuera | [ADR-0046](./adr/0046-el-cerebro-corre-afuera-el-contenedor-ejecuta.md) |
| Un contenedor por repositorio | [ADR-0047](./adr/0047-los-contenedores-son-por-repositorio.md) |
| El repo declara su entorno | [ADR-0048](./adr/0048-el-repo-declara-su-entorno-de-desarrollo.md) |
| El Encargado siembra entorno y skills | [ADR-0049](./adr/0049-el-encargado-siembra-el-entorno-y-las-skills-de-un-repo.md) |
| Alias de red y registro de puertos | [ADR-0050](./adr/0050-descubrimiento-por-alias-y-registro-de-puertos.md) |

Salió también `agente.md`, que llevaba tiempo bloqueado, y el **disparador** de la
delegación (`agente_delegar`).

**Dos cosas de esa tanda merecen leerse enteras**, porque son el tipo de error que se repite:

1. **Una cláusula de ADR-0042 se había tomado sin consultar** —*"un Workspace es una tarea y
   muere"*— y contradecía a ADR-0016, que seguía vigente. Peor: contradecía la frase del
   propio Usuario que había dado origen al ADR (*"manteniendo los Asuntos y las VM
   corriendo"*). El razonamiento estaba mal: `krun` bloquea `exec`, no la persistencia.
2. **El aislamiento entre proyectos no existía.** ADR-0011 lo prometía desde 2026-07-23, y
   medido contra el motor real un contenedor de un proyecto alcanzaba al de otro por IP con
   0% de pérdida. Hacía falta `--opt isolate=true`. Una garantía escrita no es una garantía
   probada.

---

## Lo que sigue

### 1 — La siembra de un repo (ADR-0049)

**Decidido y sin preguntas abiertas.** Al delegar por primera vez a un repo sin
`Dockerfile.dev`, el Encargado inspecciona el repo, infiere el stack y escribe **dos cosas**:
el `Dockerfile.dev` y las skills del Agente en `.agents/skills/`. No escala: el control es
la revisión del diff.

Inferir el stack **no necesita investigación** — los manifiestos son deterministas
(`package.json`, `pyproject.toml`, `pubspec.yaml`, `go.mod`, `Cargo.toml`), y para lo raro
hay búsqueda web. Lo único que suelen no traer es la **versión** del runtime, y ahí hay que
pinear una y decirlo en vez de dejar `latest` flotando.

### 2 — Publicar puertos: está construido pero no conectado

`nucleo/puertos.py` lleva el registro y `Motor.crear_contenedor()` acepta `publicar=`, pero
**el Broker todavía no los une**: `lanzar()` no reserva ni publica nada. Es trabajo, no
decisión — ADR-0050 ya fijó el rango, la idempotencia y la liberación al destruir.

Con eso cerrado queda posible lo que el Usuario pidió: levantar back, bff y front de un
proyecto, que se vean entre sí por alias, y publicar solo el front hacia la malla.

### 3 — Generar un proyecto

**Decidido qué es** (ADR-0044): entrada en `proyectos.yaml`, uno o más repos —típicamente
los de una organización—, scaffold del stack, y `engineering.yaml` con las capacidades de
ADR-0004.

**Preguntar antes:**

- ¿Qué scaffolds existen, y quién los mantiene? Sin eso, "scaffold del stack" no se puede
  programar.
- ¿JAFNE crea los repos en GitHub, o toma repos que ya existen? El Usuario mencionó
  [github.com/BoRR-Pizzeria](https://github.com/BoRR-Pizzeria/) como la forma de referencia.

La pregunta de si hace falta aprobación para las capacidades **ya no aplica**: ADR-0049
sacó esa cadena.

### 4 — Las decisiones que siguen abiertas

Las seis de `jafne pendientes`, sin cambios de forma: `medicion-de-consumo`,
`historial-desbordado`, `workspace-broker` (ya solo servicios que **no** son repos),
`sprints`, `rotacion-de-token` y `sincronia-entre-maquinas`.

---

## Trampas conocidas de este entorno

Cuestan una hora cada una si se descubren solas.

- **No pases Python por heredoc del tool Bash si el código tiene `\n` u otros escapes**: se
  desescapan por el camino y el `str.replace` no matchea. Usá Edit/Write.
- **Tampoco pases scripts de shell con `$` o `"` por `podman machine ssh` desde PowerShell**:
  se rompe el quoting. Escribí el script a un archivo y pasalo con `Get-Content -Raw`.
- **Los archivos del repo son CRLF**, con `core.autocrlf=true`. Git normaliza; no te pelees.
- **Un proceso en segundo plano muere al terminar la invocación del tool.** Para probar un
  servidor, levantalo y consultalo **en la misma llamada**.
- **`Stop-ScheduledTask` no espera a que se suelte el puerto.** Poné `Start-Sleep 3` antes
  de `Start-ScheduledTask` o el arranque falla con exit 3 (`address in use`).
- **`curl` en Windows usa schannel e ignora `--cacert`.** Para probar el TLS del panel usá
  `Invoke-WebRequest`, que valida contra el almacén de Windows como el navegador.
- **El `podman.exe` de Windows es un cliente remoto.** Lo que tiene que resolverse del lado
  donde están los archivos y los procesos —construir una imagen, leer un registro, listar
  runtimes— va por `podman machine ssh`. Ya está resuelto en `nucleo/motor.py`.
- **Las redes de Podman NO aíslan por defecto.** Dos redes distintas se alcanzan por IP
  directa: medido el 2026-08-19, un contenedor de un proyecto pingueó el de otro con 0% de
  pérdida. Hace falta `--opt isolate=true`, que ya está en `asegurar_red`. Como esa función
  es idempotente, **una red creada antes de ese arreglo sigue sin aislar**: hay que borrarla
  para que se rehaga.
- **`podman exec` no funciona con `krun`** — contesta `the handler does not support exec`.
  Hoy no molesta porque JAFNE usa el default (`crun`) desde ADR-0045, pero si alguien
  reintroduce `krun` se topa con esto. Y ojo con el salto que ya se hizo mal una vez: eso
  descarta **una forma de entrar**, no la persistencia del contenedor.
- **`podman pause` y `unpause` funcionan con los dos runtimes**, y montar un repo del disco
  de Windows desde `/mnt/c` también. Los dos verificados el 2026-08-19, así que no hace
  falta volver a averiguarlo.
- **`acceptEdits` no alcanza para que el agente *use* las herramientas MCP.** Las **ve** y
  las lista, pero la llamada queda esperando una aprobación que desde el panel no hay quién
  dar. Hay que permitirlas con `--allowed-tools mcp__<servidor>`. Ya está resuelto en
  `nucleo/mcp.py`; el síntoma, si alguien lo saca, es un agente que dice "la herramienta
  está disponible pero no me dejaron ejecutarla".
- **`--mcp-config` acepta el JSON como string**, no solo como archivo. Se pasa inline: un
  archivo temporal por conversación habría que limpiarlo.
- **`claude` no se puede invocar desde `subprocess` en Windows**: hay que llamar a
  `claude.cmd`, o `CreateProcess` falla con *"no es una aplicación Win32 válida"*.
- **Los tests no deben invocar la CLI de verdad ni tocar Podman**: gastarían el saldo del
  Usuario y no correrían en una máquina sin motor. Mirá `tests/test_adaptador_anthropic.py`
  y `tests/test_workspaces.py` — los dos sustituyen el subproceso con la forma real.
