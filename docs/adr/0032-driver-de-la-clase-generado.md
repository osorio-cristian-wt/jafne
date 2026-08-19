# ADR-0032 — La clase `generado` corre en microVM, como runtime OCI del mismo Podman

- **Estado**: Aceptada
- **Fecha**: 2026-08-18
- **Matiza a**: [ADR-0012](./0012-motor-de-contenedores-podman.md)

## Contexto

[ADR-0027](./0027-clase-de-riesgo-declarada-por-el-encargado.md) cerró **quién** declara
el aislamiento —el Encargado, en términos de riesgo— y dejó a Podman
([ADR-0012](./0012-motor-de-contenedores-podman.md)) acotado a la clase `revisado`. El
efecto era incómodo: **`generado` es el default y no tenía con qué servirse**, así que el
Broker no podía atender su propio caso normal.

La investigación ya había respondido *por qué* un contenedor plano no alcanza
([`fuentes/03`](../../investigacion/orquestacion-entornos/fuentes/03_aislamiento-microvm-vs-contenedores.md)):
AWS, Google y Azure apuntaron su primitiva de aislamiento más fuerte específicamente a
cargas de IA, y el aislamiento de una microVM lo impone el hardware, **por debajo de la
capa donde el agente puede razonar**. El incidente de 2026 es el argumento más directo:
Claude Code descubrió que `/proc/self/root/usr/bin/npx` resolvía al mismo binario sin
matchear el patrón de deny y, cuando bubblewrap lo bloqueó, **desactivó su propio sandbox**
para terminar la tarea. Un límite que vive en el mismo espacio donde el agente razona es un
límite que el agente puede razonar para saltearse.

Lo que quedaba abierto no era si conviene aislar más —eso ya estaba claro— sino **si
conviene operar dos drivers a la vez**.

## Decisión

- **`generado` corre en microVM; `revisado` en el runtime por defecto.**

  | Clase | Runtime OCI | Límite |
  |---|---|---|
  | `revisado` | `crun` (el default de Podman) | Namespaces del kernel compartido |
  | `generado` | `kata` (Kata Containers) | microVM: lo impone el hardware |

- **No son dos motores: son dos runtimes del mismo motor.** Podman elige runtime OCI por
  contenedor (`--runtime`). Esa es la respuesta a la pregunta de costo que la investigación
  había dejado abierta: **no hace falta operar dos stacks**, hace falta un flag por
  Workspace. Por eso este ADR *matiza* a ADR-0012 en vez de reemplazarlo — el motor sigue
  siendo Podman, entero.

- **Si el runtime que la clase pide no está disponible, el Broker rechaza el pedido.** No
  lo degrada. Es la misma regla que ADR-0027 ya había fijado y ahora tiene con qué
  romperse: servir `generado` sobre `crun` porque `kata` no está instalado le daría al
  Encargado una garantía que no tiene. **Fallar es el comportamiento correcto acá.**

- **El mapeo es dato de Infraestructura, no de los Encargados.** Cambiar `kata` por otro
  runtime más adelante es una fila de una tabla; ningún Encargado se entera, porque ninguno
  nombra tecnología (ADR-0027).

## Alternativas descartadas

- **gVisor (`runsc`) para `generado`:** descartada como destino, aunque es un escalón real.
  Intercepta syscalls en userspace, así que el límite sigue estando —más arriba— en un
  espacio de software. Dado que el caso de uso es exactamente el del incidente citado, se
  eligió el límite que el agente no puede razonar. Sigue siendo el candidato natural si
  alguna plataforma no puede correr Kata.
- **Firecracker directo, sin runtime OCI:** descartada — da el mismo límite que Kata pero
  fuera del contrato OCI, y entonces sí serían dos stacks de verdad. Kata da el aislamiento
  de microVM *manteniendo* la interfaz que Podman ya habla.
- **Contenedor plano reforzado (seccomp, capabilities, read-only rootfs) para `generado`:**
  descartada — es defensa en profundidad y hay que hacerla igual, pero como *límite* vive
  en el mismo espacio que el agente. El incidente de bubblewrap es precisamente el caso de
  un contenedor plano reforzado que no alcanzó.
- **Bajar `generado` de default a opt-in para evitar el problema:** descartada — invierte
  la política de ADR-0027 (aislar de más antes que arriesgar un escape) para acomodar una
  limitación de implementación. Es resolver el síntoma rompiendo la decisión.

## Consecuencias

- **`driver_para(generado)` deja de fallar**, y el pendiente `workspace-broker` se queda
  solo con lo que de verdad le corresponde: crear Workspaces y descubrir los servicios del
  proyecto.

- **Hay que verificar Kata en la plataforma del Usuario antes de confiar en esto.** JAFNE
  corre hoy en Windows, donde Podman vive dentro de WSL2, y una microVM ahí depende de
  virtualización anidada. **Este ADR no afirma que funcione en esa ruta**: afirma cuál es
  el destino y qué pasa si no está disponible — se rechaza el pedido, que es un fallo
  ruidoso y seguro, no una degradación silenciosa. Verificarlo es parte de implementar el
  Broker.

- **El default es el camino caro.** `generado` arranca una microVM y `revisado` no. El
  costo no es de latencia —Firecracker arranca en ~125 ms— sino de recursos por Workspace,
  y le da al Encargado una razón real para declarar `revisado` cuando corresponde. Eso
  refuerza la pregunta que ADR-0027 dejó abierta: **quién audita que no se declare
  `revisado` de más**, que ahora tiene incentivo económico y no solo de comodidad.

- **La defensa en profundidad no se cancela.** Elegir microVM para `generado` no exime de
  las restricciones de red por proyecto de
  [ADR-0011](./0011-redes-y-puertos-de-workspace.md) ni del endurecimiento habitual del
  contenedor: son capas distintas del mismo problema.
