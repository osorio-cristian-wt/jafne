# Frameworks de orquestación multi-agente — AutoGen, CrewAI, LangGraph

- **Consultado:** 2026-07-23

## Tres filosofías distintas

- **CrewAI** — roles + Tasks, delegación jerárquica explícita (Agents con rol y
  objetivo, Tasks asignadas, Crew como coordinador).
- **LangGraph** — el trabajo se modela como grafo/máquina de estados; agentes se pasan
  información entre nodos; fuerte en orquestación con múltiples puntos de decisión y
  procesamiento paralelo.
- **AutoGen** — modela todo como conversación entre agentes (GroupChat); un selector
  decide quién habla a continuación.

## Patrón común

Un agente coordinador recibe una tarea de alto nivel, la descompone en subtareas, las
despacha a agentes especialistas (con rol definido: researcher, coder, reviewer, etc.), y
sintetiza los resultados.

## Relevancia para JAFNE

El patrón común (coordinador → descompone → despacha → sintetiza) es exactamente el rol
que ya tiene el Encargado. De los tres, **CrewAI** es conceptualmente el más cercano
(roles + delegación jerárquica explícita), pero es un framework propio, no un protocolo
abierto interoperable como A2A.

## Fuentes originales

- [Autogen vs LangChain vs CrewAI — instinctools](https://www.instinctools.com/blog/autogen-vs-langchain-vs-crewai/)
- [Multi-Agent Orchestration and Architecture — RunPod](https://www.runpod.io/articles/guides/multi-agent-orchestration-and-architecture)
- [CrewAI vs LangGraph vs AutoGen — DataCamp](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [Best Multi-Agent Frameworks in 2026 — GuruSup](https://gurusup.com/blog/best-multi-agent-frameworks-2026)
