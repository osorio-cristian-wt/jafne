# ADR-0048 — El repositorio declara su entorno de trabajo con un `Dockerfile.dev`

- **Estado**: Aceptada. *Matizada por [ADR-0049](./0049-el-encargado-siembra-el-entorno-y-las-skills-de-un-repo.md).*
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0012](./0012-motor-de-contenedores-podman.md)

## Contexto

El Workspace Broker venía usando `alpine` como imagen, y el propio código lo declaraba como
lo que era: *"elegida por ser mínima y estar en todos lados; **no es una decisión de
diseño**"*. Un `alpine` pelado no trae git, ni Node, ni Python — o sea que un Agente ahí
adentro no puede hacer su trabajo. Elegir la imagen de verdad era lo que faltaba para poder
crear contenedores útiles.

La pregunta cruzaba con [ADR-0004](./0004-capacidades-por-repositorio.md), que ya había
decidido que **las capacidades de un Agente viven versionadas dentro del repo al que
pertenecen**. El Usuario extendió ese mismo criterio al entorno: *"me parece perfecto que
se versione en el repositorio a trabajar la imagen del mismo, así es ajeno a JAFNE; solo
que JAFNE tiene como obligación crear uno y utilizar uno"*.

Que el entorno viaje con el repo es además lo que hace realizable el motivo 3 de
[ADR-0045](./0045-para-que-existen-los-contenedores.md), la portabilidad. Conviene ser
preciso sobre qué portabilidad se consigue: `pause`/`unpause` es **local** y no mueve un
contenedor vivo a otra máquina. Lo que viaja es la **definición** del entorno, y el
contenedor se recrea del otro lado.

## Decisión

**Cada repositorio declara su entorno de trabajo en un `Dockerfile.dev` en su raíz.** JAFNE
lo construye y lo usa.

- **`Dockerfile.dev`, no `Dockerfile`.** El `Dockerfile` de la raíz, cuando existe, es casi
  siempre el de **producción**: chico, sin git y sin herramientas de desarrollo. Construir
  el contenedor del Agente con eso daría un lugar donde no se puede trabajar. Son dos
  artefactos con propósitos distintos y merecen dos archivos.
- **Es ajeno a JAFNE.** El archivo no menciona a JAFNE ni necesita nada suyo adentro —
  ADR-0046 sacó el cerebro afuera justamente para que esto fuera posible. Un repo con
  `Dockerfile.dev` sigue siendo un repo normal, y el archivo sirve igual para un humano que
  quiera levantar el entorno a mano.
- **JAFNE construye y cachea.** Se reconstruye cuando cambia el contenido del
  `Dockerfile.dev`, y no en cada delegación: construir es caro y la mayoría de las veces el
  archivo no cambió.
- **El contenedor lo mantiene en pie un keep-alive que impone JAFNE**, no el `CMD` del
  repo. Si el contenedor dependiera del `CMD`, un servidor de desarrollo que crashea se
  llevaría puesto el lugar de trabajo del Agente. Levantar el entorno de desarrollo es algo
  que el Agente hace con `exec` cuando lo necesita.
- El repo se monta en `/repos/<nombre>`. Verificado el 2026-08-19 que un repo del disco de
  Windows se monta desde `/mnt/c` sin problema.

## Alternativas descartadas

- **Una referencia a una imagen publicada** (`ghcr.io/…`) en vez de un Dockerfile:
  descartada por el Usuario. Viaja mejor y arranca más rápido, pero obliga a que alguien
  publique y mantenga esas imágenes en un registry — infraestructura que hoy no existe y
  que volvería a poner el entorno afuera del repo.
- **`.agents/Dockerfile`**, junto a las skills: descartada por el Usuario a favor de la
  raíz. Habría evitado la colisión de nombres por ubicación en vez de por nombre.
- **Una imagen por stack mantenida por JAFNE** (`jafne/workspace-node`…): descartada —
  arranque rápido y predecible, pero pone a JAFNE a mantener un registry y a adivinar el
  stack de cada repo, que es exactamente lo que este ADR le saca de encima.
- **Seguir con `alpine`:** descartada — no es una imagen de trabajo, es un placeholder, y
  ya estaba marcado como tal en el código.

## Consecuencias

- **Hace falta construir imágenes**, que es capacidad nueva del motor: hoy solo sabe correr
  contenedores. Va por `podman build`, y como todo lo que necesita el motor de verdad, por
  `podman machine ssh` en Windows (ADR-0012 y la nota de `motor.py`).
- **La primera delegación a un repo es lenta**, porque construye. Las siguientes no.
- **Dos máquinas pueden construir imágenes distintas** del mismo `Dockerfile.dev` si el
  archivo no pinea versiones. Es una propiedad de Docker, no de JAFNE, pero le pone un
  límite real al motivo de portabilidad y conviene decirlo en vez de descubrirlo.
- **Queda abierto qué hace JAFNE con un repo sin `Dockerfile.dev`.** El Usuario propuso que
  el Encargado lo genere al delegar por primera vez, junto con las skills del Agente. Eso
  choca con la cadena de escalación de ADR-0004, que prohíbe explícitamente que el Encargado
  cree capacidades por su cuenta, así que **no se decide en este ADR**: hoy ningún repo
  tiene `Dockerfile.dev`, con lo cual esto es el caso normal al arrancar y no un borde.
- **`workspace-broker` se achica pero no cierra.** El entorno ya está declarado; lo que
  sigue abierto es cómo un Workspace descubre los **servicios** del proyecto —base de
  datos, colas, otros repos— con la red restringida de ADR-0011.
