# El saldo de un plan personal se ve desde el cliente, no desde una API

- **Relevado:** 2026-08-11
- **Para:** [medición de consumo](../research.md)

## El dato que faltaba

[`fuentes/01`](./01_anthropic-usage-cost-api.md) y [`fuentes/02`](./02_openai-usage-costs-api.md)
cerraron la puerta de las APIs de organización para el caso de una suscripción personal.
Queda otra puerta: **el propio cliente del proveedor expone el saldo**.

## Claude Code

- El comando **`/usage`** dentro de Claude Code muestra el consumo de la **ventana de 5
  horas** y de la **ventana semanal**, con el **horario de reset de cada una**.
- Ese mismo comando desglosa el uso reciente **atribuyéndolo a skills, subagentes, plugins
  y servidores MCP individuales**, y permite alternar entre vista de 24 h y de 7 días.
- El comando **`/status`** da una lectura rápida de asignación restante, con avisos a
  medida que se acerca el límite.
- La misma información está en `claude.ai/settings/usage`.
- Los planes Max tienen dos escalones (5× y 20× del Pro) y límites semanales expresados en
  horas de modelo, que varían según concurrencia de sesiones y complejidad del modelo.

## Lo que importa para JAFNE

1. **El saldo de un plan personal es legible** — que era la duda que bloqueaba
   [ADR-0025](../../../docs/adr/0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md).
   No por una API de organización, sino por el cliente del proveedor.
2. **La atribución por subagente y por MCP es exactamente la granularidad que JAFNE
   necesita.** Un Encargado que quiere saber "cuánto están consumiendo mis agentes" tiene
   ahí la respuesta, ya desglosada por la unidad que le importa.
3. **Las ventanas son de tiempo, no de dinero** (5 horas y semanal, con reset conocido).
   Eso confirma que la métrica operativa correcta es el saldo con su horizonte de reset:
   "queda poco pero resetea en 40 minutos" y "queda poco y resetea el lunes" llevan a
   decisiones opuestas.
4. **Es específico de cada proveedor**, así que leerlo es trabajo del adaptador de
   [ADR-0003](../../../docs/adr/0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md), no
   de un cliente HTTP genérico.

## Abierto

- **Cómo se lee `/usage` programáticamente.** Es un comando interactivo de un cliente de
  terminal; no está verificado que exista una salida estructurada consumible por un
  proceso. Si no la hay, la alternativa es contabilidad propia calibrada contra lo que el
  cliente muestra.
- **El equivalente del lado de OpenAI para un plan personal** no se relevó.
- Cómo se combinan dos ventanas (5 h y semanal) en una sola señal de "hay saldo" para que
  el Encargado decida sin razonar sobre las dos.

## Fuentes

- [Claude Code usage limits, explained — the 5-hour window, weekly caps, and how to see your burn](https://bestagent.dev/claude-code-usage-limits/)
- [Use Claude Code with your Pro or Max plan — Claude Help Center](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)
- [Claude Code Rate Limits & Usage Quotas Explained (2026)](https://www.truefoundry.com/blog/claude-code-limits-explained)
