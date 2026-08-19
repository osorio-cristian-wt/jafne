---
fuentes:
  - docs/estado-del-diseno.md
  - docs/estado-de-implementacion.md
  - docs/adr/
verificado: 2026-08-19
---

# Encargo pendiente — para delegar

Los trabajos que el Usuario pidió el 2026-08-19 y que quedaron sin hacer. Este documento
es el **traspaso**: lo que hay que construir, qué ya está decidido, y —sobre todo— **qué
falta preguntarle al Usuario antes de escribir una línea**.

Eran cuatro. El primero —la identidad del Asistente en el system prompt— se terminó el
mismo día y su sección ya no está acá: vive en
[ADR-0040](./adr/0040-identidad-de-rol-en-el-system-prompt.md).

No es documentación de diseño: cuando un encargo se termina, su sección se borra de acá y
lo que quede vive en su ADR y en los dos derivados.

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

En cada encargo de abajo hay una sección **"Preguntar antes"**. No la saltees.

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
  citan el ADR que fijan. `.venv/Scripts/python -m pytest` — 295 en verde al 2026-08-19.

---

## Encargo 2 — Los chats, versionados en `~/.jafne/chats/`

### Lo que el Usuario pidió y decidió

> *"si es importante versionar los chats que tengo con el asistente, por defecto debería
> ser nuevo pero con un histórico"*

Y eligió, entre tres opciones: **el panel escribe en `~/.jafne/chats/`**.

### Por qué no es solo escribir un archivo

Choca de frente con una propiedad que se acaba de recuperar. Hoy el chat guarda la sesión
**en memoria del proceso** justamente para no romperla:

- [ADR-0008](./adr/0008-estado-de-asuntos-y-panel-web.md) y
  [ADR-0013](./adr/0013-panel-web-como-dashboard-visual.md) definieron el panel como
  observador que **no escribe estado**.
- [ADR-0029](./adr/0029-el-reloj-corre-en-el-proceso-del-panel.md) le abrió una excepción
  al meterle el reloj adentro.
- [ADR-0035](./adr/0035-el-reloj-corre-en-su-propio-proceso.md) revirtió eso y le devolvió
  la propiedad **entera, sin excepciones**. Tiene menos de un día.

Que el panel escriba chats la vuelve a mover. Eso **no** lo invalida —el Usuario decidió—
pero exige un ADR que lo diga con todas las letras y acote la regla: probablemente de *"el
panel no escribe estado"* a *"el panel no escribe estado **de Asuntos**"*. Escribirlo sin
ese ADR sería erosionar por la puerta de atrás lo que ADR-0035 arregló por la puerta de
adelante.

### Preguntar antes

- ¿Qué se guarda? ¿Solo `(id de sesión, título, fecha)` y el contenido lo tiene el
  proveedor, o el transcript completo del lado de JAFNE? Lo segundo es agnóstico
  ([ADR-0003](./adr/0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md)) y duplica datos.
- "Nuevo por defecto": ¿el chat viejo se lista y se puede reanudar, o queda solo de
  lectura?
- ¿Se borran? ¿Caducan? Un chat por día llena el directorio en un año.
- ¿Los chats de Encargado se guardan igual, o esos sí deberían ser Asuntos?

### Dónde tocar

- `src/jafne/nucleo/almacen.py` — `ruta_chats`, plantilla, lectura y escritura. Fijate
  cómo está hecho `programado.yaml` para el estilo.
- `src/jafne/panel/api.py` — hoy `app.state.sesiones` es un dict en memoria; ahí está el
  comentario que explica por qué.
- El panel necesita UI para listar y retomar.

---

## Encargo 3 — Servidor MCP de JAFNE

### Lo que el Usuario pidió y decidió

> *"el asistente debería de tener un acceso rápido al estado de los distintos proyectos y
> poder delegarme con uno de los encargados"*

Eligió, entre tres opciones: **un servidor MCP que el agente consulta**.

Es coherente con [ADR-0004](./adr/0004-capacidades-por-repositorio.md), que ya había
elegido MCP como la forma de dar capacidades, y con
[ADR-0014](./adr/0014-gestion-de-sprints-via-mcp.md).

### Qué expondría

Como mínimo, lo que ya existe y hoy solo se ve por HTTP: proyectos, Asuntos y su estado,
saldo. Y lo que habilita la delegación: abrir un Asunto, y derivar la conversación a un
Encargado.

Ojo con una asimetría: **leer es inofensivo, escribir no**. Abrir un Asunto desde el chat
convierte al agente en escritor de estado, que es la misma frontera del encargo 2.

### Preguntar antes

- ¿El MCP es de **solo lectura** al principio, o desde el día uno puede abrir Asuntos?
- ¿Corre como proceso propio —van cuatro contando panel, reloj y nodo de voz— o embebido
  en el panel? Ojo:
  [ADR-0035](./adr/0035-el-reloj-corre-en-su-propio-proceso.md) es la referencia de cómo
  se separó el último, y por qué.
- ¿Cómo se le declara al agente? La CLI toma `--mcp-config`.
- ¿El Encargado ve lo mismo que el Asistente, o menos?

### No te olvides de esto al terminar

[ADR-0040](./adr/0040-identidad-de-rol-en-el-system-prompt.md) dejó en
`src/jafne/nucleo/prompts/asistente.md` una sección que **declara que el agente todavía no
puede consultar el estado de los proyectos**, para que conteste que no sabe en vez de salir
a mirar el disco a mano. Cuando el MCP exista esa sección pasa a ser mentira: hay que
sacarla en el mismo commit.

---

## Encargo 4 — La cadena de delegación

### Lo que el Usuario pidió

> *"el asistente con mi comando de texto debería de poder ser capaz de generar el proyecto
> con sus necesidades delegando a los encargados con un modelo grande, luego el encargado
> puede delegar agentes de código con sus decisiones de cerebro"*

De ahí salen dos cosas ya decididas por él:

- **El Encargado conversa en modelo `grande`.**
- **El Encargado elige el cerebro de sus Agentes**, que es lo que ADR-0003 ya decía.

### Lo que eso desbloquea

Hay una entrada en `src/jafne/pendientes.py` llamada `cerebro-del-encargado-conversando`,
declarada el 2026-08-19 justamente porque
[ADR-0033](./adr/0033-tamano-por-defecto-del-rol-asistente.md) no le dio tamaño por defecto
al Encargado —*"lo elige por tarea"*— y una conversación todavía no es una tarea. Hoy
`POST /api/proyectos/{id}/chat` responde **501** citando ese pendiente.

Que el Usuario haya dicho "modelo grande" **contesta** esa pregunta. Hace falta un ADR que
matice a ADR-0033 y, en el mismo commit, sacar la entrada de `pendientes.py` y actualizar
los dos derivados.

### Preguntar antes

- ¿El Asistente delega **solo** o propone y el Usuario confirma? Es la diferencia entre un
  orquestador y un ejecutor, y roza la regla nº 1.
- ¿Delegar abre un Asunto (ADR-0006) o es una conversación aparte?
- ¿El Encargado corre en el mismo proceso, o en un Workspace? Ojo
  [ADR-0027](./adr/0027-clase-de-riesgo-declarada-por-el-encargado.md) y
  [ADR-0032](./adr/0032-driver-de-la-clase-generado.md): el aislamiento de agentes que
  escriben código ya está decidido, y el `workspace-broker` sigue sin construirse.
- "Generar el proyecto con sus necesidades": ¿qué es un proyecto generado? ¿Repo, scaffold,
  `engineering.yaml`, entrada en `proyectos.yaml`? Esto solo lo puede contestar el Usuario.

---

## Trampas conocidas de este entorno

Cuestan una hora cada una si se descubren solas.

- **No pases Python por heredoc del tool Bash si el código tiene `\n` u otros escapes**: se
  desescapan por el camino y el `str.replace` no matchea. Usá Edit/Write.
- **Los archivos del repo son CRLF**, con `core.autocrlf=true`. Git normaliza; no te
  pelees.
- **Un proceso en segundo plano muere al terminar la invocación del tool.** Para probar un
  servidor, levantalo y consultalo **en la misma llamada**.
- **`Stop-ScheduledTask` no espera a que se suelte el puerto.** Poné `Start-Sleep 3` antes
  de `Start-ScheduledTask` o el arranque falla con exit 3 (`address in use`).
- **`curl` en Windows usa schannel e ignora `--cacert`.** Para probar el TLS del panel usá
  `Invoke-WebRequest`, que valida contra el almacén de Windows como el navegador.
- **Los tests no deben invocar la CLI de verdad**: gastarían el saldo del Usuario en cada
  corrida. Mirá `tests/test_adaptador_anthropic.py` — sustituye `subprocess.run` con la
  forma real del JSON.
