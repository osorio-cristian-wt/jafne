# ADR-0005 — Cuándo documentar como investigación y cuándo directo como ADR

- **Estado**: Aceptada
- **Fecha**: 2026-07-23

## Contexto

Al documentar la jerarquía de roles, el cerebro por rol y las capacidades por
repositorio, se redactó primero como investigación (Casa Justina), con secciones de
"alternativas descartadas" — pero esas decisiones eran **requisitos directos del
Usuario**, sin alternativas genuinamente buscadas o comparadas. Hace falta una regla
explícita para que el Asistente, los Encargados y los Agentes sepan, sin ambigüedad,
dónde documentar algo.

## Decisión

- **Investigación (Casa Justina, en `investigacion/`)** aplica solo cuando hace falta
  **buscar información externa y comparar alternativas reales** antes de decidir (ej.
  motor de virtualización, trade-offs técnicos todavía sin resolver). Ahí se documenta el
  proceso completo: `research.md` + `analisis/` + `fuentes/`. Cuando la decisión se
  congela, gradúa a un ADR.
- **ADR directo (en `docs/adr/`)** aplica cuando lo que se recibe es un **requisito o
  decisión ya tomada** — típicamente por el Usuario, dueño del proyecto — sin
  alternativas que investigar. No corresponde crear una investigación con alternativas
  inventadas para simular un proceso que no ocurrió; se documenta directo como ADR,
  citando el contexto real (ej. "requisito directo del usuario, fecha X").
- **Litmus test** para cualquier nivel de la jerarquía antes de documentar: *¿esto
  necesita buscarse/compararse, o ya me lo decidieron?* Lo primero es investigación; lo
  segundo es ADR directo.

## Alternativas descartadas

- **Documentar todo como investigación "por prolijidad", incluso decisiones directas:**
  descartado — fabrica alternativas y descartes que nunca existieron, lo cual vacía de
  sentido a Casa Justina (su valor es que el razonamiento documentado sea real).
- **Documentar todo directo como ADR, sin dejar lugar a investigación genuina:**
  descartado — hay temas (ej. motor de virtualización, decisiones que sí requieren
  comparar opciones) que necesitan el proceso exploratorio antes de congelarse.

## Consecuencias

- Antes de escribir, el Asistente/Encargado/Agente clasifica el tema con el litmus test
  y elige destino: `investigacion/<tema>/` o `docs/adr/NNNN-*.md`.
- [`WORKFLOW.md`](../../WORKFLOW.md) referencia esta regla como parte de cómo se decide
  dónde documentar.
- ADR-0002, ADR-0003 y ADR-0004 son el primer caso de aplicación: requisitos directos del
  usuario documentados directo como ADR, sin pasar por investigación.
