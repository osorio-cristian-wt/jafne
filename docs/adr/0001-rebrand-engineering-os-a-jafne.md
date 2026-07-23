# ADR-0001 — Rebrand Engineering OS → JAFNE

- **Estado**: Aceptada
- **Fecha**: 2026-07-23

## Contexto

El diseño nació bajo el nombre *Engineering OS* (documentado hasta la v0.2, incluyendo la
sección 12A sobre orquestación de entornos de ejecución). Se busca una identidad propia y
un nombre memorable para el producto.

## Decisión

El proyecto pasa a llamarse **JAFNE** — *Jarvis Assistant For N→ Software Engineering*.
Toda la documentación heredada se porta bajo este nombre; "Engineering OS" queda deprecado
como nombre de producto.

## Alternativas descartadas

- **Mantener "Engineering OS":** genérico, sin identidad de marca. Descartado.

## Consecuencias

- El repositorio se funda como `jafne` con la identidad de JAFNE en el README.
- Los nombres internos de componentes (Engineering Coordinator, Infrastructure Manager,
  Workspace Broker) se conservan por ahora; solo cambia el nombre del producto.
- El material heredado de Engineering OS se cita como fuente en
  [`investigacion/orquestacion-entornos/fuentes/`](../../investigacion/orquestacion-entornos/fuentes/),
  no como documentación vigente.
