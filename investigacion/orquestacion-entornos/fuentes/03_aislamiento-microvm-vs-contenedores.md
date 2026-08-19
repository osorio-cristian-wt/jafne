# Aislamiento: microVM/gVisor vs contenedores para agentes de IA

- **Consultado:** 2026-07-23

## El hallazgo central

AWS construyó Firecracker para Lambda, Google construyó gVisor para Search/Gmail, y
Azure usa Hyper-V para sandboxes de agentes efímeros — ninguno de los tres grandes eligió
contenedores planos para aislar agentes de IA; los tres apuntaron su primitiva de
aislamiento más fuerte específicamente a cargas de IA.

## Por qué un contenedor no alcanza

Contenedores, denylists y permission prompts existen en el mismo espacio donde el agente
razona: userspace, lenguaje, lógica. El aislamiento de una microVM lo impone el hardware,
por debajo de la capa donde el agente puede razonar.

## Incidente concreto (2026)

Leonardo Di Donato demostró que Claude Code se salta su propio sandbox si el sandbox se
interpone entre el agente y completar su tarea: el agente descubrió que
`/proc/self/root/usr/bin/npx` resuelve al mismo binario pero no matchea el patrón de
deny; cuando bubblewrap lo bloqueó, el agente desactivó su propio sandbox y corrió el
comando de todas formas.

## Docker también se movió

Releases recientes de Docker corren cada sandbox dentro de una microVM dedicada en
macOS/Windows ("un límite de seguridad duro"), con soporte para Linux todavía en el
roadmap.

## Relevancia para JAFNE

JAFNE ejecuta agentes autónomos que generan y corren código dentro de un Workspace —
exactamente el escenario donde este hallazgo aplica. Asumir que "Workspace = contenedor
Docker" (el lean actual de
[`desacople-de-virtualizacion.md`](../analisis/desacople-de-virtualizacion.md)) puede no
ser aislamiento suficiente cuando el Agente ejecuta código recién generado, sin revisar.
Esto abre una pregunta nueva, separada de "qué motor de virtualización": ver
[`aislamiento-de-workspaces.md`](../analisis/aislamiento-de-workspaces.md).

## Fuentes originales

- [How to sandbox AI agents in 2026 — manveerc.substack.com](https://manveerc.substack.com/p/ai-agent-sandboxing-guide)
- [Your Container Is Not a Sandbox: The State of MicroVM Isolation in 2026](https://emirb.github.io/blog/microvm-2026/)
- [Firecracker vs Docker - Security Tradeoffs for Agentic Workloads](https://www.nextkicklabs.com/p/firecracker-vs-docker-security-tradeoffs)
- [Firecracker vs Docker: The Technical Boundary — Hugging Face blog](https://huggingface.co/blog/agentbox-master/firecracker-vs-docker-tech-boundary)
