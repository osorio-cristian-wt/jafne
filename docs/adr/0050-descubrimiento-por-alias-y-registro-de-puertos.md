# ADR-0050 — Descubrimiento por alias de red, y un registro de puertos para la malla

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0011](./0011-redes-y-puertos-de-workspace.md)

## Contexto

[ADR-0011](./0011-redes-y-puertos-de-workspace.md) puso la red y los puertos del lado de
Infraestructura —*"el Workspace, vía Infraestructura, es responsable de la red y los
puertos, no el Agente ni el Encargado"*— y dejó abierta, por escrito, la parte difícil:
*"falta definir el mecanismo exacto de descubrimiento de servicios dentro de un proyecto
(¿DNS por nombre de servicio, IP fija, variables de entorno inyectadas?)"*.

El Usuario planteó el caso que la vuelve concreta: **dos proyectos, cada uno con back, bff
y front en repos distintos**, o sea seis contenedores con tres nombres de servicio
repetidos. *"La infraestructura debería poder permitir a esos contenedores comunicarse
entre sí, sin chocarse; esa es la complejidad."*

Se midió contra el motor real el 2026-08-19, y aparecieron dos cosas — una buena y una
grave.

**La buena: adentro no hay choque, y no hace falta registro.** Cada contenedor tiene su
propia IP en la red de su proyecto. Dos proyectos con un `back` cada uno resolvieron a
`10.89.1.2` y `10.89.2.2`, y el bff de cada uno llegó **al suyo**. El espacio de nombres y
el de puertos internos ya están separados por la red; no hay nada que administrar.

**La grave: el aislamiento entre proyectos que ADR-0011 promete no existía.** Con redes de
Podman por defecto, el bff de un proyecto pingueó el back de otro por IP directa con **0%
de pérdida**. La frase de ADR-0011 —*"el Encargado de BoRR no llega a un contenedor de Casa
Justina"*— era falsa en la máquina real. La opción `--opt isolate=true` la vuelve cierta:
con ella el cruce falla y la resolución dentro del propio proyecto sigue funcionando.

## Decisión

**1. Los servicios de un proyecto se encuentran por alias de red, y el alias es el nombre
del repo.** Al crear el contenedor se le pone `--network <red>:alias=<repo>`. El bff llama
a `http://back:3000` y funciona, sin saber en qué Asunto está ni cómo se llama el
contenedor. Es la opción *"DNS por nombre de servicio"* que ADR-0011 listaba, y se elige
porque no exige inyectar nada ni fijar IPs.

Que dos proyectos tengan los dos un `back` **no es un problema a resolver**: es la
consecuencia natural de una red por proyecto, y está verificado.

**2. La red del proyecto se crea con `isolate=true`, siempre.** No es una opción de
endurecimiento: es lo que hace verdadera la promesa de ADR-0011. Sin eso, el aislamiento
entre proyectos es una frase en un documento.

**3. Publicar hacia la malla pasa por un registro de puertos, en Infraestructura.** Ahí sí
el espacio es compartido —la IP de ZeroTier es una sola— y hay que llevar la cuenta:

- Rango propio y alto (`9000-9999`), para no pelearse con lo que el Usuario ya corra.
- Se asigna el **primer libre**, y se anota en `~/.jafne/puertos.json`.
- Es **idempotente por (contenedor, puerto interno)**: pedir dos veces lo mismo da el mismo
  puerto. Sin eso, rearmar un contenedor le cambiaría el número y el link que el Usuario ya
  tenía dejaría de servir.
- Se **libera al destruir**. Un puerto reservado para un contenedor que ya no existe agota
  el rango de a poco, y el síntoma aparece mucho después de la causa.

**Es programado, no agéntico.** El Usuario planteó las dos formas; elegir el primer puerto
libre de un rango es una cuenta, no un juicio, y un modelo haciéndola sería más caro, más
lento y no más correcto. Lo que sí es criterio —**qué** servicio merece publicarse— lo
decide el Encargado; este registro solo le da el número.

## Alternativas descartadas

- **Variables de entorno inyectadas con las IPs:** descartada — hay que reinyectarlas cada
  vez que un contenedor se recrea y cambia de IP, y un servicio que arrancó antes que otro
  se queda con un valor viejo. El DNS resuelve al momento de usarse.
- **IPs fijas por servicio:** descartada — obliga a administrar subredes por proyecto a
  mano, y reintroduce exactamente el problema de choque que la red por proyecto ya evita.
- **Un registro de puertos también para lo interno:** descartada — no hay nada que
  registrar. Está medido: dos `back` en dos proyectos conviven sin tocarse.
- **Que el registro de puertos sea agéntico:** descartada por lo dicho arriba. Se deja
  anotado que el Usuario lo planteó como opción válida y que la decisión fue por costo y
  determinismo, no porque no se pudiera.
- **Preguntarle al sistema operativo un puerto libre en vez de llevar registro:**
  descartada — más simple, pero el puerto cambia en cada rearmado y rompe la idempotencia
  que hace que un link siga sirviendo.

## Consecuencias

- **Una red creada antes de este ADR no aísla.** `asegurar_red` es idempotente, así que una
  red que ya existe no se recrea y se queda sin `isolate=true`. Hay que borrarla a mano
  para que se vuelva a crear bien. Vale para cualquier `jafne-*` que haya quedado dando
  vueltas.
- **Se cierra la pregunta de descubrimiento** que ADR-0011 dejó abierta y que
  `workspace-broker` arrastraba. Lo que le queda a ese pendiente es más chico: los
  servicios que **no** son repos del proyecto —una base de datos, una cola—, que no tienen
  contenedor propio de JAFNE y por lo tanto no tienen alias.
- **La prueba de integración que el Usuario quiere ya es posible**: levantar back, bff y
  front de un proyecto, que se vean entre sí por alias, y publicar solo el front hacia la
  malla. No hace falta nada más que lo que este ADR fija.
- **El rango puede agotarse**, y cuando pase se dice con el rango y la cuenta de
  publicaciones vivas, en vez de fallar con un error de Podman sobre un puerto ocupado.
- **`~/.jafne/puertos.json` es estado nuevo** que sobrevive al proceso. Es a propósito: un
  reinicio de Infraestructura no puede soltar puertos que siguen ocupados por contenedores
  vivos.
