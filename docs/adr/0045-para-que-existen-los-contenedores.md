# ADR-0045 — Para qué existen los contenedores: dormir, despertar y viajar

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Reemplaza a**: [ADR-0027](./0027-clase-de-riesgo-declarada-por-el-encargado.md),
  [ADR-0032](./0032-driver-de-la-clase-generado.md),
  [ADR-0041](./0041-el-driver-de-generado-es-krun.md)

## Contexto

Los contenedores de JAFNE se diseñaron alrededor del **aislamiento**. ADR-0027 hizo que el
Encargado declarara una *clase de riesgo* —`revisado` o `generado`—, ADR-0032 mapeó
`generado` a una microVM y ADR-0041 eligió `krun` como su runtime. Todo ese andamiaje
existe por una sola premisa: el código generado por un modelo no es confiable, así que hay
que correrlo con kernel propio.

Al decidir que **el cerebro corre afuera del contenedor**
([ADR-0046](./0046-el-cerebro-corre-afuera-el-contenedor-ejecuta.md)), el Usuario revisó
esa premisa y la bajó de categoría: la credencial de Anthropic ya no entra al contenedor,
que era la parte del riesgo que más pesaba. Preguntado por qué quiere contenedores
entonces, dio tres motivos, en este orden:

1. Aislamiento — **descartado como motivo**, por lo anterior.
2. **Poder dormirlos y despertarlos** para ahorrar recursos.
3. **Portabilidad entre computadoras**, para poder probar en distintos lados sin problema.

Eso deja a `krun` sin justificación, y conviene medir qué costaba. Verificado contra el
motor real el 2026-08-19, sobre `podman machine` en WSL2:

| | `krun` | `crun` (default) |
|---|---|---|
| `pause` / `unpause` (motivo 2) | ok | ok |
| Montar un repo de Windows desde `/mnt/c` | ok | ok |
| `podman exec` | **falla**: `the handler does not support exec` | ok |
| Kernel propio | sí | no |

O sea que `krun` **no aporta nada a los dos motivos que quedaron en pie**, y sí cobra caro:
sin `exec` no se puede entrar a un contenedor, lo que obligaba a inventar un canal por red
—un servidor adentro, un protocolo, un binario inyectado— que es la mayor parte del trabajo
que `protocolo-asignacion-tareas` tenía por delante.

## Decisión

**Los contenedores de JAFNE existen para dormir/despertar y para viajar.** El aislamiento
sigue siendo un beneficio —un contenedor contiene lo que el código hace con el disco y la
red— pero pasa a ser **consecuencia y no motivo**, y por lo tanto no manda sobre el diseño.

De ahí se sigue lo demás:

- **JAFNE no elige runtime.** Deja de pasar `--runtime` y usa el default de Podman, que en
  la máquina de referencia es `crun`. La decisión de runtime desaparece; el runtime no.
- **Se entra a un contenedor con `podman exec`.** Es el camino normal y el único que hace
  falta, para todos los contenedores por igual.
- **Se cae la clase de riesgo.** `ClaseRiesgo`, `riesgo.py`, `exigir_runtime()` y el campo
  `clase` del pedido de Workspace existían **solo** para mapear riesgo a runtime. Sin ese
  mapeo son peso muerto, y peso muerto que miente: sugiere una garantía de aislamiento que
  ya no se está dando.

Que se caiga la clase **no** es que el riesgo deje de existir. Es que JAFNE deja de
prometer que lo mitiga con el runtime, que es distinto de fingir que lo sigue haciendo.

## Alternativas descartadas

- **Mantener `krun` para `generado`:** descartada por el Usuario. Conserva la microVM, pero
  a cambio de quedarse sin `exec` para justo la clase que más trabajo hace, y de sostener
  el canal por red entero. Se paga el costo alto de una garantía que dejó de ser el motivo.
- **Dejar la clase de riesgo viva pero mapeando las dos al default:** descartada — un campo
  que el Encargado completa y que no cambia nada es peor que no tenerlo: se lee como que
  algo está pasando. Si el aislamiento vuelve a ser un motivo, se reintroduce con su ADR.
- **Conservar ADR-0027 y matizarlo:** descartada — ADR-0027 no es *"el Encargado declara
  riesgo"* a secas, es *"…y Infraestructura lo mapea a driver"*. Sin la segunda mitad no
  queda decisión, queda un título.

## Consecuencias

- **`protocolo-asignacion-tareas` se disuelve en su mayor parte.** No hace falta servidor
  MCP adentro del contenedor, ni protocolo por red, ni inyectar binarios: el Agente corre
  afuera y entra con `exec`. Lo que quede de esa pregunta es mucho más chico.
- **Se borra código.** `nucleo/riesgo.py` entero, `ClaseRiesgo`, `exigir_runtime()`, el
  campo `clase` de `Pedido`, el parámetro `runtime` de `Motor.crear_contenedor()`, y los
  tests que fijaban el mapeo riesgo→runtime.
- **JAFNE deja de correr código no confiable con kernel propio.** Es el costo elegido. Si
  algún día se corren repos de terceros, o el modelo ejecuta código de origen desconocido,
  esta decisión merece revisarse — y la vuelta ya está medida: `krun` está instalado y
  funciona, lo único que hay que reponer es el canal que reemplaza a `exec`.
- **La portabilidad todavía no está resuelta por este ADR.** Dormir y despertar es local:
  `pause`/`unpause` no mueven un contenedor vivo a otra máquina. Lo que viaja es la
  *definición* del entorno, y de eso se ocupa
  [ADR-0048](./0048-el-repo-declara-su-entorno-de-desarrollo.md).
