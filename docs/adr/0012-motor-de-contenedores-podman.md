# ADR-0012 — Motor de contenedores por defecto: Podman

- **Estado**: Aceptada, matizada por [ADR-0032](./0032-driver-de-la-clase-generado.md), [ADR-0042](./0042-infraestructura-es-un-proceso-con-el-mcp-adentro.md), [ADR-0046](./0046-el-cerebro-corre-afuera-el-contenedor-ejecuta.md) y [ADR-0048](./0048-el-repo-declara-su-entorno-de-desarrollo.md)
- **Fecha**: 2026-07-23

## Contexto

La investigación de
[orquestación de entornos](../../investigacion/orquestacion-entornos/analisis/desacople-de-virtualizacion.md)
comparó Docker, Podman, Kubernetes y Nomad para implementar el contrato del Workspace
Broker. JAFNE ejecuta Agentes autónomos que a veces corren código recién generado, sin
revisar (ver [`aislamiento-de-workspaces.md`](../../investigacion/orquestacion-entornos/analisis/aislamiento-de-workspaces.md)),
lo que hace relevante el radio de daño de un escape de contenedor.

## Decisión

**Podman** es el motor de contenedores por defecto de JAFNE para implementar Workspaces
(detrás del contrato del Workspace Broker, [ADR-0011](./0011-redes-y-puertos-de-workspace.md)).

## Alternativas descartadas

- **Docker + Compose:** descartado como default — su daemon corre como root, así que un
  escape de contenedor llega a root del host. Queda disponible como driver alternativo
  compatible si algún repo/imagen lo requiere puntualmente.
- **Kubernetes:** descartado como default — pesado para workspaces efímeros cortos
  (~1h de setup, 5+ nodos); no resuelve nada distinto de Podman para el problema actual
  (un servidor con acceso vía ZeroTier).

## Consecuencias

- El Infrastructure Manager implementa el contrato del Workspace Broker sobre Podman:
  redes por proyecto y publicación de puertos sobre la interfaz ZeroTier
  ([ADR-0011](./0011-redes-y-puertos-de-workspace.md)).
- Los repos comitean sus definiciones de contenedor (Dockerfile/compose) de forma
  compatible con Podman (`podman-compose` / Quadlet); la mayoría de Dockerfiles
  estándar funcionan sin cambios.
- Esta decisión **no cierra** dos preguntas que siguen en investigación: si además hace
  falta microVM/gVisor para tareas de alto riesgo
  ([`aislamiento-de-workspaces.md`](../../investigacion/orquestacion-entornos/analisis/aislamiento-de-workspaces.md)),
  y si Nomad reemplaza a Podman como *scheduler* multi-nodo más adelante
  ([`fuentes/04`](../../investigacion/orquestacion-entornos/fuentes/04_nomad-vs-kubernetes-scheduling.md)).
  Podman puede correr como driver dentro de Nomad, así que esta elección no bloquea esa
  decisión futura.
