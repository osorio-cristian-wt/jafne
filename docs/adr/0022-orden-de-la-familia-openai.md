# ADR-0022 — Orden de tier de la familia OpenAI: Sol > Tierra > Luna

- **Estado**: Aceptada, matizada por [ADR-0030](./0030-tamanos-de-cerebro-catalogo-comun-entre-proveedores.md)
- **Fecha**: 2026-08-11

## Contexto

[ADR-0010](./0010-proveedores-iniciales-asistente.md) declaró a la familia OpenAI
(Luna / Tierra / Sol) como proveedor inicial, y dejó anotado que el orden de tier se
asumía "por analogía de tamaño (Sol > Tierra > Luna)" pero **sin confirmación explícita del
usuario**. El orden importa porque
[ADR-0003](./0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md) exige que el Encargado
corra en un modelo pesado/frontier: sin saber cuál es el pesado, no se puede asignar
cerebro a un rol.

Confirmación directa del Usuario (2026-08-11).

## Decisión

**Sol > Tierra > Luna**, de mayor a menor capacidad.

- **Sol** — el equivalente pesado/frontier. Es el que corresponde al rol de **Encargado**
  (ADR-0003), y al de Asistente.
- **Tierra** — intermedio.
- **Luna** — el más liviano; para tareas acotadas de Agente donde el Encargado juzgue que
  alcanza.

Esto llena el campo `tier` de `cerebros.yaml`
([ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md)), que hasta ahora se
dejaba vacío a propósito por no estar confirmado.

## Alternativas descartadas

- **Luna > Tierra > Sol** (el orden inverso): descartado — el Usuario confirmó el orden
  asumido, no el inverso.
- **Seguir dejando `tier` vacío y que el Encargado elija por nombre:** descartado — obliga
  a cada Encargado a conocer la nomenclatura de cada proveedor, que es exactamente el
  acople que `.agents/` (ADR-0003) existe para evitar.

## Consecuencias

- Confirma la suposición de ADR-0010; ese ADR queda sin preguntas abiertas.
- `cerebros.yaml` puede declarar `tier` para los tres modelos de la familia, y la
  asignación de cerebro por rol deja de depender de que alguien reconozca los nombres.
- El mapeo entre tiers de proveedores distintos (¿Sol equivale a la clase Opus de Claude?)
  sigue sin definirse. Alcanza para elegir *dentro* de un proveedor; no para comparar
  entre proveedores.
