# ADR-0049 — El Encargado siembra el entorno y las skills de un repo, sin escalar

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0004](./0004-capacidades-por-repositorio.md),
  [ADR-0048](./0048-el-repo-declara-su-entorno-de-desarrollo.md)

## Contexto

[ADR-0048](./0048-el-repo-declara-su-entorno-de-desarrollo.md) dejó que cada repositorio
declare su entorno en un `Dockerfile.dev`, y lo dejó abierto a propósito: **ningún repo del
Usuario tiene uno hoy**, así que "el repo lo declara" describe un futuro, no un presente.
Alguien tiene que escribir el primero, y pedírselo a mano repo por repo convierte una
decisión de diseño en una tarea de tipeo.

El Usuario resolvió que lo haga el Encargado, y que lo haga de a dos: *"al primer momento
de delegar un agente para el repo, revisa si tiene el `.dev`; en caso de que no, revisa el
repositorio, entiende qué stack necesita, y crea el `.dev` en base a eso, así como las
skills para el agente de código — hace un dos por uno. Entiende que por ejemplo necesita de
React y le da skills de React al agente de código. Esto mismo se versiona también en el
repositorio en sí."*

Es la misma inspección del repo la que contesta las dos preguntas —qué stack necesita el
entorno y qué tiene que saber hacer el Agente—, así que separarlas sería hacer dos veces el
mismo trabajo.

Eso choca de frente con [ADR-0004](./0004-capacidades-por-repositorio.md), que había
decidido lo contrario **y lo había puesto entre sus alternativas descartadas**:

> *"El Encargado aprueba y crea capacidades nuevas por su cuenta: descartado — agregar una
> capacidad cambia lo que un repo puede hacer de forma permanente; el Usuario mantiene el
> control humano ahí."*

El choque se le señaló al Usuario antes de escribir este ADR, con la cita textual, y lo
confirmó igual. Queda anotado acá porque un ADR que revierte a otro tiene que decir que
sabía lo que revertía.

## Decisión

**El Encargado siembra el entorno y las capacidades de un repo por su cuenta, sin pasar por
la cadena de escalación.**

Al delegar un Agente a un repo por primera vez:

1. Mira si el repo tiene `Dockerfile.dev`. Si lo tiene, no toca nada.
2. Si no, **inspecciona el repo** para entender su stack.
3. Con esa misma inspección escribe **las dos cosas**: el `Dockerfile.dev` y las skills del
   Agente en `.agents/skills/`.
4. Ambas quedan **versionadas en el repo**, que es donde ADR-0004 ya había decidido que
   viven. Esa mitad de ADR-0004 sigue en pie y no se toca.

**Lo que se reemplaza de ADR-0004 es la cadena de escalación**, y solo eso. Su decisión de
almacenamiento —capacidades versionadas dentro del repo, el repo como unidad y canal de
descubrimiento— queda intacta y es sobre la que se apoya todo esto.

**El control humano se mueve, no desaparece.** Cuando ADR-0004 se escribió, crear una
capacidad era un acto invisible y la única forma de controlarlo era preguntar antes. Ahora
los artefactos son **archivos en un repositorio git**: JAFNE los escribe pero no los
commitea, así que el Usuario los ve como un diff y decide si entran. El control pasa de
*aprobación previa por conversación* a *revisión posterior por diff*.

## Alternativas descartadas

- **Que el Encargado proponga y el Usuario apruebe por la cadena de ADR-0002:** descartada
  por el Usuario. Dejaba ADR-0004 intacto, a costa de una pregunta por cada repo nuevo — y
  con ningún repo declarando entorno hoy, eso es una pregunta por cada repo que existe.
- **Matizar ADR-0004 distinguiendo *sembrar* de *agregar*** —un repo vacío se puede sembrar
  solo, agregar sobre lo ya declarado escala—: descartada por el Usuario a favor de la
  forma simple. Habría conservado el control humano para el caso incremental, a costa de
  dos reglas donde ahora hay una.
- **Que JAFNE traiga imágenes por stack y saltearse el `Dockerfile.dev`:** descartada en
  ADR-0048 y sigue descartada — pone a JAFNE a mantener imágenes y adivinar stacks, que es
  lo que este camino le saca de encima.

## Consecuencias

- **JAFNE escribe en los repos del Usuario.** Es la primera vez: hasta ahora escribía en
  `~/.jafne/` y en la bitácora de cierre (ADR-0021). Escribe archivos, **no commitea**, y
  el borde de ADR-0039 sigue valiendo — no toca nada fuera de la raíz de repos.
- **Una skill mal inferida entra sin que nadie la revise.** Es el costo elegido: el Agente
  puede terminar con skills que no le sirven, o con un `Dockerfile.dev` que no refleja el
  stack real. Se ve en el diff, y se ve tarde.
- **`agente.md` puede describir un repo completo**: su contenedor, su entorno declarado y
  sus capacidades. Las tres cosas ya existen o tienen quién las cree.
- **El caso "repo sin `Dockerfile.dev`" deja de estar abierto** en ADR-0048.
- **Inferir el stack no necesita investigación.** El Usuario lo señaló y tiene razón: los
  manifiestos ya lo dicen casi todo, y son deterministas — `package.json` (y sus
  dependencias distinguen React de Vue de Next), `pyproject.toml`, `requirements.txt`,
  `pubspec.yaml`, `go.mod`, `Cargo.toml`, `pom.xml`, `*.csproj`. Para lo que no reconozca,
  el Encargado tiene búsqueda web. Es trabajo, no una pregunta abierta.
  Lo único que los manifiestos **no** siempre traen es la **versión** del runtime, que es
  justo lo que decide si dos máquinas construyen igual (ADR-0048). Cuando `.nvmrc`,
  `engines` o `requires-python` no están, el Encargado tiene que pinear una y decirlo, en
  vez de dejar la etiqueta flotando en `latest`.
