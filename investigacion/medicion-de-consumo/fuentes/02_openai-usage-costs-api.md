# OpenAI — Usage API y Costs API

- **Relevado:** 2026-08-11
- **Para:** [medición de consumo](../research.md)
- **Fuente:** [How to use the Usage API and Cost API to monitor your OpenAI usage](https://developers.openai.com/cookbook/examples/completions_usage_api)

## Qué hay

| Endpoint | Qué devuelve |
|---|---|
| `GET /v1/organization/usage/{completions,images,audio,embeddings,moderations,vector_stores,code_interpreter_sessions}` | Uso en tiempo casi real por tipo de actividad |
| `GET /v1/organization/costs` | Desglose de gasto diario |

## Detalles que importan

- **Ámbito de organización**, con clave de administrador — misma forma que Anthropic.
- El endpoint de completions acepta `start_time`, `bucket_width`, `project_ids`,
  `user_ids`, `api_key_ids` y `models`.
- El uso está **partido por tipo de actividad** (un endpoint por familia), a diferencia de
  Anthropic que tiene uno solo para mensajes.

## Lo que importa para JAFNE

1. **Simetría con Anthropic**: organización + clave de administrador. La misma frontera
   —y la misma exclusión del caso suscripción personal.
2. **Asimetría de forma**: OpenAI reparte el uso en varios endpoints por tipo de
   actividad; Anthropic lo concentra en uno con `group_by`. Un cliente que hable con los
   dos necesita normalizar, que es exactamente el tipo de adaptador que ADR-0003 ya prevé
   para el cerebro.
3. **`user_ids` como dimensión** es interesante para JAFNE: permitiría atribuir consumo
   por rol si cada rol usara su propia identidad. No está decidido que lo haga.

## Nota sobre precios

Los precios de lista de OpenAI cambian seguido y no se relevan acá a propósito: un
análisis de diseño que se apoye en un número de precio queda desactualizado antes de
graduarse. Lo que importa para la decisión es **qué se puede consultar y con qué clave**,
no cuánto sale hoy.
