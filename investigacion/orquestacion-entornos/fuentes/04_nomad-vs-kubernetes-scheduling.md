# Nomad vs Kubernetes — scheduling multi-nodo

- **Consultado:** 2026-07-23

## Comparación clave

- **Setup:** Nomad se despliega en ~10 minutos con 3 nodos; Kubernetes toma más de una
  hora y típicamente necesita 5+ nodos para separar control plane de workloads.
- **GPU:** Nomad reserva GPUs nativamente (`resources { cores = 4 }`); Kubernetes
  necesita device plugins + RBAC extra. En un benchmark, Nomad logró 1.560 jobs/hora —
  42% más que el Job controller de Kubernetes en el mismo cluster (8 nodos, 32 GPUs).
- **Cargas heterogéneas:** Nomad soporta nativamente contenedores (Docker, Podman),
  ejecutables raw, JARs de Java, y VMs (QEMU) en un solo scheduler, sin capas
  adicionales.
- **Workspaces efímeros:** Nomad soporta cargas con estado vía host volumes, plugins
  CSI, y el stanza `ephemeral_disk`.

## Relevancia para JAFNE

Esto responde directo la pregunta abierta de "¿cómo se ubican los workspaces en nodos
(scheduling)?" de [orquestación de entornos](../research.md). Nomad, al soportar
contenedores y VMs en el mismo scheduler, encajaría con la necesidad de mezclar
Docker/Podman (para la mayoría de las tareas) y microVMs (para agentes ejecutando código
generado, ver
[`03_aislamiento-microvm-vs-contenedores.md`](./03_aislamiento-microvm-vs-contenedores.md))
sin dos sistemas de scheduling separados. También es más simple de operar que Kubernetes
para un cluster chico (GPU/build/lab), justo el escenario de "nodos distribuidos" que ya
describe orquestación de entornos.

## Fuentes originales

- [Nomad vs Kubernetes: 5 Use Cases Where Nomad Wins — Markaicode](https://markaicode.com/usecases/nomad-use-cases-production-workflows/)
- [Efficient GPU Job Scheduling with HashiCorp Nomad — Medium](https://medium.com/@ycp11111/efficient-gpu-job-scheduling-with-hashicorp-nomad-a-lightweight-alternative-to-kubernetes-7dc5da70d244)
- [Nomad vs Kubernetes: Understanding the Tradeoffs — NetApp](https://www.netapp.com/learn/cvo-blg-kubernetes-vs-nomad-understanding-the-tradeoffs/)
- [Nomad for Kubernetes practitioners — HashiCorp Developer](https://developer.hashicorp.com/nomad/docs/k8s-nomad)
