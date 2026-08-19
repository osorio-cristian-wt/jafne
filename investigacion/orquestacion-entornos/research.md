# Orquestación de entornos de ejecución

- **Estado:** explorando
- **Origen:** heredado de *Engineering OS v0.2* (ver [`fuentes/01_engineering-os-v0.2.md`](./fuentes/01_engineering-os-v0.2.md)).

## El tema

Los agentes de JAFNE necesitan ejecutar código (builds, tests, servicios) sin preparar
dependencias a mano ni tocar Docker. La apuesta de diseño es que **piden un Workspace** a
la infraestructura y trabajan dentro de él; la tecnología de virtualización queda
**desacoplada** de los agentes.

Piezas que aparecen en la fuente v0.2:

- **Infrastructure Manager** — administra toda la infraestructura de ejecución (crear/
  destruir workspaces, Docker/Compose, recursos, ZeroTier, limpieza).
- **Workspace Broker** — la interfaz que usan los agentes: `Create Workspace` →
  `{ workspace, status, url }`. Los agentes nunca hablan con Docker.
- **Workspaces efímeros** — entornos aislados por tarea; luego se destruyen, suspenden o
  snapshotean.
- **`engineering.yaml`** — cada repo declara su entorno (ver
  [`examples/engineering.yaml`](../../examples/engineering.yaml)). Propuesta, no congelada.
- **Nodos distribuidos** — GPU / build / laboratorio de hardware, interconectados por
  ZeroTier.

## Preguntas abiertas

- ¿Motor de virtualización por defecto y estrategia de escalado? →
  [`analisis/desacople-de-virtualizacion.md`](./analisis/desacople-de-virtualizacion.md)
  — lean actual: Docker/Compose + Nomad para scheduling multi-nodo (revisado
  2026-07-23, ver [`fuentes/04`](./fuentes/04_nomad-vs-kubernetes-scheduling.md)).
- ¿Esquema definitivo de `engineering.yaml` (servicios, tools, recursos, secretos)?
- ¿Ciclo de vida completo de un workspace y quién decide destruir/snapshot?
- ~~¿Cómo se ubican los workspaces en nodos (scheduling)?~~ — lean encontrado: Nomad
  (ver arriba); falta confirmar con el usuario.
- **Nuevo:** ¿qué nivel de aislamiento (contenedor simple vs microVM/gVisor) necesita un
  Workspace según el riesgo de la tarea? →
  [`analisis/aislamiento-de-workspaces.md`](./analisis/aislamiento-de-workspaces.md)
- ~~¿quién fija ese nivel sin que el Agente conozca la tecnología?~~ — **graduado a
  [ADR-0027](../../docs/adr/0027-clase-de-riesgo-declarada-por-el-encargado.md)**: el
  Encargado declara clase de riesgo (`revisado` / `generado`, default `generado`) y el
  Broker mapea a driver. Ver
  [`analisis/quien-decide-el-aislamiento.md`](./analisis/quien-decide-el-aislamiento.md).
- **Lo que quedó de eso:** a qué driver mapea `generado`, que es el default. ADR-0012
  eligió Podman y ADR-0027 lo acotó a `revisado`, así que hoy un pedido `generado` no
  tiene con qué servirse. La pregunta real es si conviene operar dos drivers.

## Análisis

Ver el índice en [`analisis/README.md`](./analisis/README.md).

## Graduación

**Graduó [ADR-0027](../../docs/adr/0027-clase-de-riesgo-declarada-por-el-encargado.md)**
(2026-08-18): quién decide el aislamiento. El Encargado declara una clase de riesgo y el
Broker la mapea a driver, con lo que el principio 1 —agentes agnósticos de
infraestructura— queda intacto.

Graduar movió la pregunta en vez de vaciarla, como suele pasar: contestado el *quién*,
lo que queda abierto es el *con qué* —a qué driver mapea `generado`— y si conviene operar
dos drivers a la vez. El resto de los principios de alto nivel ya aceptados están
resumidos en [`docs/arquitectura.md`](../../docs/arquitectura.md).
