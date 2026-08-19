# ADR-0003 — Cerebro por rol y agnosticismo de proveedor de IA

- **Estado**: Aceptada
- **Fecha**: 2026-07-23

## Contexto

JAFNE ya decidió que los agentes son agnósticos de la tecnología de virtualización (ver
[`docs/arquitectura.md`](../arquitectura.md)). Falta la misma garantía para el
**modelo/proveedor de IA** que ejecuta cada rol: no atarse a un vendor.

## Decisión

- JAFNE es **agnóstico de proveedor de IA**: qué "cerebro" (proveedor + modelo) ejecuta
  cada rol es una **configuración**, no un supuesto de diseño. Se declara en una
  convención propia y neutral, **`.agents/`** (análoga en espíritu a `engineering.yaml`
  para infraestructura), en vez de atarse a convenciones de un proveedor específico
  (ej. `.claude/`).
- El **Encargado** corre siempre en un modelo pesado/frontier (clase Opus de Claude, o el
  equivalente pesado de OpenAI — ver proveedores iniciales concretos en
  [ADR-0010](./0010-proveedores-iniciales-asistente.md)).
- El Encargado **decide dinámicamente**, tarea por tarea, qué cerebro y qué nivel de
  esfuerzo de razonamiento delega a cada Agente.
- **Política de tokens:** ante la duda de si una tarea sale bien a la primera, se
  **prefiere gastar más tokens (modelo más caro, más esfuerzo) antes que arriesgarse a
  rehacer trabajo**.

## Alternativas descartadas

- **Atar JAFNE a un único proveedor de IA:** descartado explícitamente — el diseño debe
  permitir cambiar de cerebro sin rediseñar el sistema.
- **Asignación de modelo fija por rol (sin delegación dinámica):** descartado — el
  Encargado necesita poder subir o bajar el cerebro/esfuerzo según qué tan riesgosa es
  cada tarea puntual.
- **Optimizar por ahorro de tokens ante la duda:** descartado a favor de la política
  inversa — el costo de rehacer pesa más que el costo de tokens de más.

## Consecuencias

- Hace falta un adaptador que traduzca el contrato neutral de `.agents/` a lo que cada
  proveedor concreto requiere (ej. generar `.claude/skills/` si el cerebro activo es
  Claude Code). El diseño detallado de ese adaptador queda abierto.
- El mecanismo de delegación dinámica de modelo/esfuerzo por el Encargado ya tiene un
  precedente funcional conocido (el propio entorno de ejecución donde se diseñó JAFNE
  permite lanzar sub-agentes con modelo y esfuerzo explícitos por invocación) — sirve de
  referencia de implementación, no hace falta diseñarlo desde cero.
