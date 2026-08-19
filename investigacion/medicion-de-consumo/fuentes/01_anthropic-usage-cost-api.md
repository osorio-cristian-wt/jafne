# Anthropic — Usage & Cost Admin API

- **Relevado:** 2026-08-11
- **Para:** [medición de consumo](../research.md)
- **Fuente:** [Usage and Cost API — Claude Platform Docs](https://platform.claude.com/docs/en/manage-claude/usage-cost-api)

## Qué hay

Dos endpoints, ambos bajo la Admin API:

| Endpoint | Qué devuelve |
|---|---|
| `GET /v1/organizations/usage_report/messages` | Consumo de tokens: input sin cachear, input cacheado, creación de caché, output. Más uso de server tools (ej. web search) |
| `GET /v1/organizations/cost_report` | Costo en USD, como strings decimales en centavos |

## Detalles que importan

- **Clave**: Admin API key (`sk-ant-admin01-...`), distinta de una API key normal.
- **`The Admin API is unavailable for individual accounts.`** Hace falta una organización
  configurada en Console → Settings → Organization.
- **Granularidad del Usage API**: buckets de `1m`, `1h` o `1d`.

  | Bucket | Límite por defecto | Máximo |
  |---|---|---|
  | `1m` | 60 | 1.440 |
  | `1h` | 24 | 168 |
  | `1d` | 7 | 31 |

- **Granularidad del Cost API**: **solo diaria** (`1d`).
- **Agrupación y filtro**: por API key, workspace, modelo, service tier, ventana de
  contexto, `inference_geo` y `speed` (beta).
- **Frescura**: el dato aparece típicamente a los ~5 minutos de completarse la request.
- **Polling recomendado**: una vez por minuto de forma sostenida; se recomienda cachear
  para dashboards que refrescan seguido.
- **Costos de Priority Tier no están en el Cost API** — hay que sacarlos del Usage API.
- **No disponible en Claude Platform on AWS** (solo por Console ahí).

## Las otras dos superficies, para el caso suscripción

La documentación separa explícitamente qué API corresponde según el producto:

| Organización | API | Tipo de clave |
|---|---|---|
| Claude Console (Claude Platform) | Usage & Cost Admin API (arriba) | Admin API key |
| Claude Enterprise (claude.ai) | Claude Enterprise Analytics API | Analytics API key |

Y para el caso más cercano a lo que hace JAFNE, la propia doc remite a una tercera:
**Claude Code Analytics API**, que da costos estimados por usuario y métricas de
productividad — recomendada explícitamente por encima de desglosar por muchas API keys.

## Lo que importa para JAFNE

1. **Las tres superficies son de organización.** Ninguna cubre a un individuo con un plan
   personal. Si JAFNE corre sobre una suscripción personal, este camino no existe.
2. **Claude Code Analytics API es la más cercana a lo que JAFNE mide** (costo por usuario
   de un agente de código), pero sigue necesitando una organización.
3. **Una Admin API key es una credencial de peso**: da lectura de la facturación de toda
   la organización. Guardarla en el servidor del panel es una decisión de seguridad, no
   solo de configuración.
4. **La granularidad diaria del Cost API no sirve para un dashboard en vivo.** Para
   "cuánto llevo gastado hoy" hay que derivarlo del Usage API con precios, o llevar
   contabilidad propia.
