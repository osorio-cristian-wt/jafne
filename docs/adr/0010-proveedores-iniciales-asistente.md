# ADR-0010 — Proveedores iniciales soportados para el rol de Asistente

- **Estado**: Aceptada, matizada por [ADR-0028](./0028-anthropic-primero-alcance-de-adaptadores.md)
- **Fecha**: 2026-07-23

## Contexto

[ADR-0003](./0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md) estableció que JAFNE es
agnóstico de proveedor de IA (`.agents/`, `~/.jafne/cerebros.yaml` —
[ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md)). Falta fijar, en la
práctica, con qué proveedores arranca el rol de **Asistente**.

## Decisión

Por ahora, el Asistente puede correr sobre:

- **Claude Code** (Anthropic).
- **La familia de modelos de OpenAI**, con su nomenclatura vigente **Luna / Tierra /
  Sol**.

Esto no reemplaza el principio de agnosticismo (ADR-0003) — es la lista inicial concreta
que se declara en `cerebros.yaml` (ADR-0007); agregar un proveedor nuevo es una
actualización de esa lista, no un cambio de arquitectura.

## Alternativas descartadas

- **Lanzar con un solo proveedor soportado:** descartado — contradice el principio de
  agnosticismo recién decidido (ADR-0003); con un solo proveedor implementado, la
  agnosticidad queda sin probar desde el día uno.

## Consecuencias

- El adaptador `.agents/` ↔ proveedor concreto (abierto desde ADR-0003) tiene, como
  primer caso real, que traducir a Claude Code y a la familia Luna/Tierra/Sol de OpenAI.
- Falta confirmar el mapeo de tier dentro de la familia OpenAI — se asume por analogía de
  tamaño (Sol > Tierra > Luna) para saber cuál es el equivalente pesado/frontier que
  necesita el Encargado (ADR-0003), pero sin confirmación explícita del usuario todavía.
