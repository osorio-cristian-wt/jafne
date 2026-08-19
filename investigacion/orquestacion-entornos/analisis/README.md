# Análisis — orquestación de entornos

Deep-dives por sub-problema. Acá viven las opciones evaluadas y **descartadas**.

- [`desacople-de-virtualizacion.md`](./desacople-de-virtualizacion.md) — Cómo mantener a
  los agentes agnósticos del motor de virtualización (Docker / Podman / K8s / Nomad).
- [`aislamiento-de-workspaces.md`](./aislamiento-de-workspaces.md) — Contenedores vs
  microVM/gVisor: qué tan fuerte debe ser la frontera de un Workspace para un agente
  autónomo.
- [`quien-decide-el-aislamiento.md`](./quien-decide-el-aislamiento.md) — Quién completa
  ese parámetro sin romper el principio de agentes agnósticos de infraestructura: el
  Encargado declara clase de riesgo, Infraestructura mapea riesgo → aislamiento.
