# Architecture Decision Records (ADRs)

Registro de decisiones de diseño **congeladas**. Cada archivo es **una decisión**,
numerada e inmutable: una decisión superada no se edita — se crea un ADR nuevo con estado
*Reemplaza a ADR-XXXX*, y el viejo pasa a *Reemplazada por ADR-YYYY*.

La exploración previa (opciones y descartes) vive en [`investigacion/`](../../investigacion/);
acá va solo lo que ya se decidió.

## Índice

- [ADR-0001](./0001-rebrand-engineering-os-a-jafne.md) — Rebrand *Engineering OS* → JAFNE.

## Plantilla

```markdown
# ADR-NNNN — Título en una frase

- **Estado**: Aceptada | Reemplazada por ADR-YYYY
- **Fecha**: AAAA-MM-DD

## Contexto
Qué problema o pregunta motivó la decisión.

## Decisión
Qué se decidió, en afirmativo.

## Alternativas descartadas
Cada alternativa y por qué se descartó.

## Consecuencias
Qué se gana, qué se paga, y qué reglas impone hacia adelante.
```
