# Contabilidad propia vs. API del proveedor

- **Estado:** explorando (2026-08-11)
- **Sub-problema de:** [medición de consumo](../research.md)

## El problema

El panel tiene que mostrar consumo ([ADR-0013](../../../docs/adr/0013-panel-web-como-dashboard-visual.md)).
Hay tres formas de conseguir el número y no son excluyentes.

## Las opciones

| Opción | Cómo funciona | A favor | En contra |
|---|---|---|---|
| **A. API del proveedor** | El panel consulta las APIs de uso/costo de Anthropic y OpenAI | El dato es el de facturación: exacto y reconciliable | Solo existe para organizaciones con clave de administrador ([`fuentes/01`](../fuentes/01_anthropic-usage-cost-api.md), [`fuentes/02`](../fuentes/02_openai-usage-costs-api.md)). **No cubre suscripciones personales.** Costo con granularidad diaria. Guardar una clave de administrador es un riesgo aparte |
| **B. Contabilidad propia** | JAFNE registra el consumo de cada llamada que hace | Funciona en los dos modelos de facturación y con cualquier proveedor; en vivo, sin latencia de reporte; sin credenciales privilegiadas | Es una estimación, no facturación: no ve consumo que no pase por JAFNE, y los precios hay que mantenerlos |
| **C. Las dos** | B como fuente en vivo, A como reconciliación periódica cuando hay organización | Cubre los dos modelos y además detecta desvíos entre lo estimado y lo facturado | Más piezas |

## Por qué el lean es C, con B como base

- **B es lo único que funciona siempre.** El caso "el Asistente corre sobre una
  suscripción personal" no tiene API del proveedor, y es un caso perfectamente posible con
  lo que [ADR-0010](../../../docs/adr/0010-proveedores-iniciales-asistente.md) declaró.
  Un diseño que arranca por A no tiene qué mostrar en ese caso.
- **B es lo consistente con [ADR-0003](../../../docs/adr/0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md).**
  Contar lo que JAFNE gasta es agnóstico de proveedor por construcción. Depender de la API
  de administración de cada vendor es lo contrario: un adaptador nuevo por proveedor, con
  una forma distinta cada uno (Anthropic concentra en un endpoint con `group_by`, OpenAI
  reparte en varios por tipo de actividad).
- **B no necesita credenciales privilegiadas.** Una Admin API key da lectura de la
  facturación de toda la organización; ponerla en el servidor del panel es una decisión de
  seguridad de otro orden, y el panel ya arrastra su propia discusión de acceso
  ([ADR-0020](../../../docs/adr/0020-hosting-y-autenticacion-del-panel.md)).
- **A aporta lo que B no puede: la verdad.** Contabilidad propia estima; la Cost API
  factura. Con las dos se puede mostrar el número en vivo y avisar cuando la estimación se
  aleja — que es señal de que algo consume por fuera de JAFNE.

## Lo que ninguna de las tres contesta

**Cuánto queda del plan.** Las tres miden *gasto*; ninguna mide *saldo*. Si lo que el
Usuario quiere ver es "cuánto me queda antes de que me limiten", eso no sale de acá —
requiere saber el límite del plan, que estas APIs no exponen. Vale la pena confirmar cuál
de las dos preguntas es la que importa antes de construir cualquiera de las tres.

## Abierto

- ¿La pregunta del Usuario es gasto o saldo?
- Si es contabilidad propia: ¿dónde se guarda el registro? `~/.jafne/` es estado operativo
  y se puede perder ([ADR-0021](../../../docs/adr/0021-bitacora-de-cierre-en-el-repo-encargado.md)
  resolvió eso para las decisiones, no para las métricas).
- ¿La contabilidad se atribuye por rol (Asistente / Encargado / Agente) o solo total? Por
  rol sería mucho más útil dada la política de "más tokens antes que rehacer" — permitiría
  ver qué cuesta esa política —, pero requiere que cada llamada sepa de qué rol viene.
- Mantener una tabla de precios propia envejece. ¿Se acepta esa deuda, o se limita la
  contabilidad propia a tokens y se deja el dinero para la API del proveedor?
