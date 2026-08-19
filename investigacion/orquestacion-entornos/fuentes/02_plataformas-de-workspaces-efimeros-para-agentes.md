# Plataformas de workspaces efímeros — prior art directo

- **Consultado:** 2026-07-23

## Qué hay

- **Daytona** — arrancó como gestor de entornos de desarrollo y pivotó a
  infraestructura para agentes de IA a inicios de 2025; el producto hoy es un runtime de
  sandbox que levanta entornos aislados en menos de 90ms. Levantó una Serie A de $24M en
  febrero 2026.
- **Coder** — entornos self-hosted definidos como código Terraform; a partir de 10+
  desarrolladores el costo de self-hosting ($300-500/mes) le gana a Gitpod por usuario
  ($1000+/mes).
- **Gitpod** — Classic (pay-as-you-go) cerró el 15 de octubre de 2025; el reemplazo
  (Flex) es solo self-hosted. El mercado completo se movió hacia self-hosted en 2026.

## Relevancia para JAFNE

Daytona en particular es **prior art casi directo** del Workspace Broker: es
literalmente "pedir un entorno aislado para que un agente de IA trabaje, sin que le
importe la infraestructura de abajo" — la misma idea que ya define
[`docs/arquitectura.md`](../../../docs/arquitectura.md). Vale la pena estudiar su
arquitectura concreta antes de diseñar el Workspace Broker desde cero.

## Fuentes originales

- [Top 10 GitHub Codespaces Alternatives in 2026 — Bunnyshell](https://www.bunnyshell.com/comparisons/github-codespaces-alternative/)
- [Gitpod Alternatives: 6 Cloud Dev Environments Compared (2026) — MorphLLM](https://www.morphllm.com/comparisons/gitpod-alternative)
- [Coder vs Gitpod vs DevPod: Honest Review 2026 — DevOpsBoys](https://devopsboys.com/blog/coder-vs-gitpod-vs-devpod-cloud-dev-environments-review-2026)
- [Best Self-Hosted Cloud IDEs & Dev Environments 2026 — Pi Stack](https://www.pistack.xyz/posts/self-hosted-cloud-dev-environments-coder-devpod-vscode-guide/)
