# WORKFLOW — cómo se documenta JAFNE

Método de trabajo del repo. JAFNE está en fase de **diseño/brainstorming**, así que la
documentación es en su mayoría **exploratoria** y evoluciona.

## Los tres modos de documentar

En estos proyectos se documenta de tres formas, según el grado de madurez:

1. **ADR** — *Architecture Decision Records*. Decisiones congeladas, una por archivo,
   numeradas y **append-only**: el cuerpo de un ADR no se edita nunca. Lo que sí cambia es
   su campo `Estado`, que registra si la decisión fue **reemplazada** (quedó sin efecto) o
   **matizada** (sigue vigente, pero otra la acota). Viven en [`docs/adr/`](docs/adr/).
2. **Casa Justina** — estándar **evolutivo/exploratorio** (inspirado en
   [casaJustina](https://github.com/osorio-cristian-wt/casaJustina) y
   [docs-organizacion](https://github.com/BoRR-Pizzeria/docs-organizacion)). Cada tema de
   diseño vive en [`investigacion/<tema>/`](investigacion/) con `research.md` + `analisis/`
   + `fuentes/`. Es donde se guardan las **opciones descartadas** y el razonamiento — algo
   que un ADR no admite.
3. **arc42** — para cuando el proyecto se **formaliza**. Es una plantilla de arquitectura
   más rígida (12 secciones). JAFNE **todavía no** la usa; se adoptará cuando el diseño
   se estabilice y convenga una vista formal. Ver [arc42.org](https://arc42.org/).

**Hoy JAFNE usa el híbrido ADR + Casa Justina.** arc42 queda como destino futuro.

## Cuándo investigar y cuándo ir directo a ADR

No todo pasa por `investigacion/`. La regla ([ADR-0005](docs/adr/0005-cuando-investigar-vs-adr-directo.md)):

- **Investigación (Casa Justina)** — solo cuando hace falta **buscar y comparar
  alternativas reales** antes de decidir. Ahí sí se documentan opciones y descartes.
- **ADR directo** — cuando lo que llega es un **requisito o decisión ya tomada** (típico:
  una instrucción directa del usuario). No se fabrican alternativas descartadas que
  nunca se evaluaron; se escribe el ADR directo, citando el contexto real.
- **Litmus test:** *¿esto necesita buscarse/compararse, o ya me lo decidieron?*

> Estos tres modos no son arbitrarios: se mapean a la **jerarquía de roles** de JAFNE
> (Asistente → Encargado → Agentes), donde cada nivel documenta con un estándar distinto.
> Ver [`investigacion/jerarquia-de-roles/`](investigacion/jerarquia-de-roles/research.md).

## Flujo: de la exploración a lo congelado

```mermaid
flowchart LR
    F[fuentes/] --> R[research.md<br/>estado: explorando]
    R --> A[analisis/<br/>opciones + descartes]
    A --> R
    R -->|se congela| ADR[docs/adr/NNNN]
    ADR -.->|si se formaliza| ARC[arc42]
```

## La superficie de lectura: historial vs. estado

Los ADR y las investigaciones son el **historial** del diseño: conservan el *por qué* y
los descartes, que es lo único que evita que una decisión se re-litigue dentro de seis
meses. Pero **no son de donde se saca qué es verdad hoy**: para eso habría que aplicar
mentalmente treinta decisiones en orden, lo cual es caro y sale mal — sobre todo cuando
dos ADR vigentes se leen sueltos y parecen contradecirse.

Por eso hay dos documentos **derivados**, y son el punto de entrada de cualquiera —persona
o agente— que necesite el estado actual:

| Documento | Contesta |
|---|---|
| [`docs/estado-del-diseno.md`](docs/estado-del-diseno.md) | ¿Qué está **decidido** hoy? |
| [`docs/estado-de-implementacion.md`](docs/estado-de-implementacion.md) | ¿Qué de eso ya **corre**? |
| `src/jafne/pendientes.py` (`jafne pendientes`) | ¿Qué falta **decidir**? |

Es la misma forma que JAFNE ya usa para un Asunto: `historial.jsonl` es append-only y
completo, `meta.yaml` es chico y actual, y para decidir se lee el segundo. Los derivados se
actualizan **en el mismo commit** que cambia su fuente.

## Estructura de una investigación (Casa Justina)

Cada tema de diseño vive en `investigacion/<tema>/`:

```
investigacion/<tema>/
  research.md      ← síntesis: narra el tema, marca su estado, enlaza análisis y fuentes
  analisis/        ← deep-dives, un archivo por sub-problema (acá viven los descartes)
    README.md      ← índice (una línea por análisis)
    <sub-tema>.md
  fuentes/         ← material citado, numerado
    README.md      ← índice
    NN_slug.md     ← 01_, 02_, ...
```

- **`research.md` es el punto de entrada** y marca el estado: `explorando`,
  `en prototipo`, o `graduado a ADR-XXXX`.
- **`analisis/`** descompone en sub-problemas y deja **por qué se descarta** cada opción.
- **`fuentes/`** guarda material externo o heredado, numerado `NN_slug.md`.

## Reglas transversales

- **Un tema por archivo**, `kebab-case`, nombre estable. Cada carpeta tiene un `README.md`
  índice, actualizado en el mismo commit que agrega o mueve un doc.
- **Docs técnicos congelados** (en `docs/`) llevan front-matter con `fuentes` (de qué
  derivan) y `verificado` (fecha absoluta):

  ```markdown
  ---
  fuentes:
    - investigacion/orquestacion-entornos/research.md
  verificado: 2026-07-23
  ---
  ```

- **Diagramas en Mermaid**, nunca imágenes.
- **Fechas absolutas** (2026-07-23), nunca "hace dos semanas".
- **Idioma español**; términos técnicos en inglés cuando son estándar (workspace,
  snapshot, broker).

## Del documento al código

Desde 2026-08-11 el repo también tiene implementación
([ADR-0015](docs/adr/0015-stack-inicial-de-implementacion.md)), con una regla que extiende
el mismo criterio de los tres modos de documentar: **lo que no está decidido no se
programa**.

- Una funcionalidad que depende de una pregunta abierta se declara en
  `src/jafne/pendientes.py` y falla citando el ADR o la investigación que la bloquea, en
  vez de resolverse con un default improvisado.
- Sacar algo de ese registro requiere primero congelar la decisión (graduación a ADR, o
  ADR directo), y actualizar
  [`docs/estado-de-implementacion.md`](docs/estado-de-implementacion.md) en el mismo commit.

## Git

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`) con cuerpo en español.
  **Sin trailers de atribución de herramientas.**
