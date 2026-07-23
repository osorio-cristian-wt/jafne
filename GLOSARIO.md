# Glosario de JAFNE

Términos del proyecto. Un término por fila, estable.

| Término | Definición |
|---|---|
| **JAFNE** | *Jarvis Assistant For N→ Software Engineering*. El sistema completo. Antes "Engineering OS". |
| **Asistente** | Nivel superior de la jerarquía: la capa que habla con el usuario y orquesta. Corresponde a Claude Code / OpenClaw. |
| **Encargado** | Rol a nivel **proyecto** (cruza varios repos). Documenta estilo Casa Justina, por fuera de los repos. |
| **Agente** | Rol a nivel **repositorio**. Documenta según el estándar de ese repo (arc42 o ADR). |
| **Engineering Coordinator** | Componente v0.2 que orquesta el plano de agentes. Relación con "Encargado" por definir. |
| **Infrastructure Manager** | Componente que administra toda la infraestructura de ejecución. |
| **Workspace** | Entorno de ejecución aislado y efímero donde un agente corre código. |
| **Workspace Broker** | Interfaz por la que los agentes piden/gestionan workspaces sin tocar Docker. |
| **OpenClaw** | Componente de la arquitectura v0.2; rol exacto por definir. |
| **engineering.yaml** | Archivo por repo que declara el entorno de ejecución necesario. |
| **snapshot** | Copia congelada de un workspace, para reanudar o reproducir estado. |
| **graduación** | Pasar un hallazgo de `investigacion/` (Casa Justina) a una decisión congelada (ADR). |
| **Casa Justina** | Estándar de documentación evolutivo/exploratorio (research + análisis + fuentes). |
| **ADR** | *Architecture Decision Record*: decisión congelada, numerada, append-only. |
| **arc42** | Plantilla de arquitectura formal (12 secciones); destino cuando JAFNE se formalice. |
