# Fuente 01 — Engineering OS v0.2, sección 12A

> Material heredado, transcrito tal cual del documento original
> `Engineering_OS_v0.2_Agregados.md` (sección **12A. Orquestación de Entornos de
> Ejecución**). Se cita como fuente; JAFNE es el rebrand de "Engineering OS"
> (ver [ADR-0001](../../../docs/adr/0001-rebrand-engineering-os-a-jafne.md)). El resto del
> documento v0.2 aparecía "resumido por brevedad" y no se conserva.

## Principio

El Engineering OS no solo orquesta agentes: también orquesta entornos de ejecución.

Los agentes nunca preparan manualmente sus dependencias ni ejecutan Docker directamente.
Solicitan un **Workspace** al sistema de infraestructura.

## Infrastructure Manager

Componente responsable de administrar toda la infraestructura de ejecución.
Responsabilidades: crear/destruir workspaces; gestionar Docker y Docker Compose; escalar a
Podman o Kubernetes sin afectar a los agentes; administrar recursos (CPU, RAM, GPU);
gestionar ZeroTier, túneles, certificados y puertos; limpiar recursos finalizados.

## Workspaces

Cada tarea que requiera ejecutar código se realiza dentro de un workspace aislado y
efímero (ej. Flutter + Android SDK, Node.js + Vite, ESP-IDF + PlatformIO, Python +
Jupyter, PostgreSQL + Redis + Supabase). Vive durante la tarea y luego puede destruirse,
suspenderse o convertirse en snapshot.

## engineering.yaml

```yaml
project: Gustagua
workspace:
  image: flutter:latest
  cpu: 4
  ram: 8G
services:
  - postgres
  - redis
  - supabase
tools:
  - flutter
  - dart
  - adb
  - git
```

## Workspace Broker

Los agentes solicitan un workspace (`Create Workspace / Proyecto / Perfil`) y obtienen:

```json
{ "workspace": "ws-481", "status": "running", "url": "http://ws481.internal" }
```

Luego pueden destruirlo, suspenderlo o generar snapshots.

## Infraestructura distribuida

El Infrastructure Manager decide en qué nodo ejecutar cada workspace (Nodo GPU →
inferencia; Nodo Build → compilaciones; Nodo Laboratorio → hardware ESP32). Los nodos se
interconectan por ZeroTier.

## Arquitectura (v0.2)

```
Usuario → Engineering Coordinator → Infrastructure Manager
  ├── Workspace Broker ├── Docker Engine ├── Redis
  ├── PostgreSQL ├── OpenClaw └── Workspaces efímeros
```

**Principio fundamental:** los agentes conocen únicamente el concepto de Workspace; la
tecnología de virtualización queda completamente desacoplada.
