# ADR-0015 — Stack inicial de implementación: Python + FastAPI, panel sin build

- **Estado**: Aceptada
- **Fecha**: 2026-08-11

## Contexto

Hasta 2026-08-11 JAFNE era solo diseño: doce ADRs y tres investigaciones, sin una línea de
código. Con el panel web congelado como requisito
([ADR-0013](./0013-panel-web-como-dashboard-visual.md)), el Usuario pidió **arrancar la
implementación**, con una restricción explícita: *lo que todavía no está decidido, no se
programa*.

Elegir stack es una decisión de las que restringen el código hacia adelante, así que va a
ADR aunque no sea una decisión de arquitectura de JAFNE en sí.

## Decisión

- **Núcleo y API en Python** (3.12+), con **FastAPI** + **Uvicorn** para el panel y
  **PyYAML** para leer y escribir `~/.jafne/`
  ([ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md)).
- **El panel se sirve como HTML/CSS/JS estático desde el mismo proceso**, sin paso de
  build ni framework de frontend. No hay `npm` en el camino crítico.
- **CLI con `argparse`** (biblioteca estándar), sin dependencia extra.
- **Regla de implementación — lo no decidido no se programa.** Toda función que dependa de
  una pregunta abierta se expone, pero levanta `DecisionPendiente` citando el ADR o la
  investigación que la bloquea. Nada de defaults improvisados que después haya que
  desarmar.

## Alternativas descartadas

- **TypeScript de punta a punta (Node + React/Vite):** descartado — mete un paso de build
  desde el día uno, y deja menos directos tanto los SDKs de Anthropic/OpenAI (que el panel
  necesita para el uso de suscripciones, ADR-0013) como el control de Podman
  ([ADR-0012](./0012-motor-de-contenedores-podman.md)).
- **Backend Python + frontend React/Vite:** descartado por ahora — dos toolchains desde el
  día uno para un panel que todavía tiene la mitad de sus funciones bloqueadas por
  decisiones abiertas. Si la UI crece, migrar el frontend no toca el núcleo.
- **Implementar también el chat y el uso de suscripciones en esta primera tanda:**
  descartado — obligaría a decidir por dentro del código el transporte hacia el
  Asistente/Encargado y el manejo de credenciales, dos preguntas explícitamente abiertas
  (ADR-0013).

## Consecuencias

- El árbol de código arranca en `src/jafne/`: `nucleo/` (estado de Asuntos y almacén
  `~/.jafne/`), `panel/` (API + web estático) y `cli.py`.
- `DecisionPendiente` no es solo una excepción: el registro de decisiones pendientes es
  **consultable** (`GET /api/pendientes`) y el panel lo muestra, así que el estado de
  diseño de JAFNE es visible desde el propio JAFNE.
- Los endpoints bloqueados responden **501 Not Implemented** con el ADR/investigación que
  los bloquea, en vez de fallar de forma opaca o devolver datos falsos.
- Esta decisión es reemplazable con costo bajo mientras el código sea chico; si más
  adelante conviene otro stack, se escribe un ADR nuevo que reemplace a este.
