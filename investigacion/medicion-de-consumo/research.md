# Medición de consumo de los proveedores de IA

- **Estado:** explorando (abierta y relevada el 2026-08-11)
- **Origen:** [ADR-0013](../../docs/adr/0013-panel-web-como-dashboard-visual.md) — el panel
  tiene que mostrar el uso de las suscripciones de Anthropic y OpenAI, y ese ADR dejó
  abierto de qué fuente sale el dato y dónde viven las credenciales.

## El tema

El requisito está congelado: el panel muestra consumo. Lo que falta es **de dónde sale el
número**. La intuición inicial era "hay una API de cada proveedor, se la consulta"; el
relevamiento muestra que el problema tiene una división previa que hay que resolver antes.

## El hallazgo que reordena todo

**"Suscripción" y "API key" no son lo mismo, y no se reportan por el mismo lugar.**

Los dos proveedores tienen APIs de uso y costo, y las dos son **de organización y con
clave de administrador**. La documentación de Anthropic lo dice sin rodeos: *"The Admin
API is unavailable for individual accounts"*. Es decir:

- Si JAFNE consume por **API key dentro de una organización** → las APIs sirven, y son
  buenas (ver [`fuentes/01`](./fuentes/01_anthropic-usage-cost-api.md) y
  [`fuentes/02`](./fuentes/02_openai-usage-costs-api.md)).
- Si el Asistente corre sobre una **suscripción personal** (un plan de Claude Code, un
  plan de ChatGPT) → esa vía no aplica. Anthropic tiene superficies aparte para eso
  —Claude Enterprise Analytics API, Claude Code Analytics API—, pero también están
  atadas a una organización, no a una cuenta individual.

[ADR-0010](../../docs/adr/0010-proveedores-iniciales-asistente.md) dice que el Asistente
corre sobre Claude Code o la familia OpenAI, sin decir bajo qué modelo de facturación. Esa
omisión es exactamente lo que ahora bloquea el diseño.

## Lo que se resolvió (2026-08-11)

El Usuario contestó las dos preguntas que no se investigan y graduó lo que salió de acá a
[ADR-0025](../../docs/adr/0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md):

- **Consume con suscripciones personales**, no con una organización → el camino de las
  APIs de administración queda descartado para el caso principal.
- **Quiere ver saldo, no gasto** — cuánto uso le queda, no cuántos dólares lleva.
- **Y quiere que sea accionable**: que un Encargado que ve Anthropic cerca del límite
  conmute a OpenAI.
- **Infraestructura lleva la cuenta**, porque es el único componente con vista de todos
  los agentes a la vez.

Y [`fuentes/03`](./fuentes/03_saldo-visible-en-el-cliente-del-proveedor.md) destrabó lo
que parecía un callejón sin salida: **el saldo de un plan personal sí es legible, por el
cliente del proveedor**. Claude Code expone `/usage` con las ventanas de 5 h y semanal,
sus horarios de reset y el desglose por subagente y MCP — justo la granularidad que un
Encargado necesita.

## Preguntas que siguen abiertas

1. **¿Cómo ve Infraestructura el consumo?** El Broker crea los Workspaces, pero las
   llamadas al modelo las hacen los agentes adentro. O pasan por un punto de paso que mide,
   o cada agente reporta lo suyo — y son dos arquitecturas distintas. **Es la que bloquea
   la implementación de ADR-0025.**
2. **¿`/usage` se puede leer programáticamente?** Es un comando interactivo de terminal; si
   no tiene salida estructurada, hay que calibrar contabilidad propia contra lo que muestra.
3. **¿Cuál es el equivalente del lado de OpenAI** para un plan personal? Sin relevar.
4. ~~¿Cómo se combinan dos ventanas en una sola señal?~~ — **contestada por
   [ADR-0026](../../docs/adr/0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md)**:
   no se combinan. Producen acciones distintas, y lo que las separa es el horizonte de
   reset — la corta se espera, la larga hace conmutar.
5. ~~¿La conmutación aplica a mitad de un Asunto?~~ — **contestada por ADR-0026**: no,
   solo a Asuntos nuevos. Un Asunto empezado se termina con el cerebro que lo empezó.

## Qué restringe la respuesta

- **[ADR-0003](../../docs/adr/0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md)** —
  agnosticismo de proveedor. Una solución que solo funcione con la API de administración
  de Anthropic deja a OpenAI sin cubrir y viceversa; y ninguna de las dos cubre el caso
  suscripción.
- **ADR-0003 otra vez, por otro lado** — la política de "más tokens antes que rehacer"
  hace que el gasto sea una señal operativa esperada, no una anomalía. El panel muestra
  consumo para que el Usuario decida, no para alarmar.
- **ADR-0013** — el panel es de solo lectura sobre el estado; mostrar consumo no lo
  convierte en un sistema de facturación.

## Análisis

Ver [`analisis/README.md`](./analisis/README.md).

## Fuentes

Ver el índice en [`fuentes/README.md`](./fuentes/README.md).

## Graduación

**Graduado a [ADR-0025](../../docs/adr/0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md)**
(2026-08-11): la métrica es el saldo, Infraestructura lleva la cuenta, el saldo entra como
variable de la decisión de cerebro de ADR-0003, y leerlo es trabajo del adaptador por
proveedor. Sigue abierto el **cómo** — pregunta 1 de arriba.
