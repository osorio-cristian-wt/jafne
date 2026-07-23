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
- ¿Esquema definitivo de `engineering.yaml` (servicios, tools, recursos, secretos)?
- ¿Ciclo de vida completo de un workspace y quién decide destruir/snapshot?
- ¿Cómo se ubican los workspaces en nodos (scheduling) y cómo se maneja el estado remoto?

## Análisis

Ver el índice en [`analisis/README.md`](./analisis/README.md).

## Graduación

Nada congelado todavía. Los principios de alto nivel ya aceptados están resumidos en
[`docs/arquitectura.md`](../../docs/arquitectura.md); las decisiones concretas graduarán a
ADRs a medida que se cierren.
