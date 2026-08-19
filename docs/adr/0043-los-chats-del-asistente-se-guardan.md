# ADR-0043 — Los chats del Asistente se guardan, y el panel escribe solo eso

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0008](./0008-estado-de-asuntos-y-panel-web.md),
  [ADR-0013](./0013-panel-web-como-dashboard-visual.md),
  [ADR-0035](./0035-el-reloj-corre-en-su-propio-proceso.md)

## Contexto

El Usuario pidió *"si es importante versionar los chats que tengo con el asistente, por
defecto debería ser nuevo pero con un histórico"*, y eligió que **el panel escriba en
`~/.jafne/chats/`**.

Eso choca de frente con una propiedad que se acababa de recuperar. El chat guardaba la
sesión en memoria del proceso justamente para no romperla:

- ADR-0008 y ADR-0013 definieron el panel como observador que **no escribe estado**.
- [ADR-0029](./0029-el-reloj-corre-en-el-proceso-del-panel.md) le abrió una excepción al
  meterle el reloj adentro.
- ADR-0035 revirtió eso y le devolvió la propiedad **entera, sin excepciones**, con menos
  de un día de antigüedad al momento de este ADR.

Que el panel escriba chats la vuelve a mover. El Usuario decidió, así que no está en
discusión *si* se hace — pero hacerlo sin decirlo con todas las letras sería erosionar por
la puerta de atrás lo que ADR-0035 arregló por la de adelante.

## Decisión

**El panel escribe chats del Asistente en `~/.jafne/chats/`, y nada más.**

La regla de ADR-0008/ADR-0013 se **acota**, no se levanta: pasa de *"el panel no escribe
estado"* a **"el panel no escribe estado de Asuntos"**. Ese es el eje que esos ADR
protegen, y sigue intacto: un chat no tiene estado, ni contenedor, ni cierre, ni
validaciones. Es la charla previa a que haya trabajo.

Con la forma que el repo ya usa para lo mismo — `meta.yaml` chico y actual,
`historial.jsonl` append-only, igual que un Asunto:

- **Se guardan las dos cosas.** El `id_sesion` del proveedor, que permite reanudar sin
  reinyectar el historial (ADR-0031), y el **transcript propio**, que mantiene el histórico
  legible aunque el proveedor pierda la sesión o se cambie de proveedor
  ([ADR-0003](./0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md)). Cuando discrepan,
  gana el transcript para *mostrar* y el id para *reanudar*: cada uno es fuente de lo suyo.
- **Nuevo por defecto, y los viejos se listan y se retoman.** Un turno sin chat declarado
  abre uno nuevo. Retomar uno viejo reanuda la sesión del proveedor por id.
- **No caducan y no se borran solos.** Los saca el Usuario. Un chat que desaparece porque
  pasaron 90 días es un chat que no estaba cuando se lo necesitó.
- **Los chats de Encargado no se guardan acá.** El trabajo con un Encargado es un Asunto
  ([ADR-0006](./0006-asuntos-unidad-de-trabajo-y-ciclo-de-vida.md)); duplicarlo como chat
  dejaría dos lugares donde vive lo mismo y ninguno sería claramente el bueno.

El título sale del primer mensaje del Usuario y no se vuelve a pisar: recién ahí se sabe de
qué es la conversación, y pedirlo antes de empezar es fricción por nada.

## Alternativas descartadas

- **Guardar solo el índice (id de sesión, título, fecha):** descartada por el Usuario — no
  duplica datos, pero deja el histórico vacío el día que el proveedor pierda la sesión o se
  cambie de proveedor. Quedaría el nombre de la conversación y nada adentro.
- **Guardar solo el transcript, sin el id de sesión:** descartada — retomar exigiría
  reinyectar toda la conversación en el primer turno, que es exactamente lo que ADR-0031
  eligió no hacer.
- **Histórico de solo lectura, sin retomar:** descartada por el Usuario — más simple, pero
  tira una capacidad que el adaptador ya tiene.
- **Caducidad por antigüedad o tope de N:** descartada por el Usuario — acota el
  directorio, pero borra sin avisar y hace falta alguien que corra la limpieza.
- **Guardar también los chats de Encargado:** descartada por el Usuario — sería uniforme, y
  a cambio pondría el trabajo de un proyecto en dos lugares distintos.

## Consecuencias

- **El panel dejó de ser de solo lectura, y hay que decirlo así.** La frase corta *"el panel
  no escribe estado"* ya no es cierta; la correcta es *"no escribe estado de Asuntos"*.
  Quien lea ADR-0008, ADR-0013 o ADR-0035 sueltos va a leer la versión vieja, que es
  justamente para lo que están los derivados.
- **Las conversaciones sobreviven al reinicio del panel.** Era el costo declarado de la
  decisión anterior, y se pagó hasta hoy.
- **El adaptador vivo sigue en memoria.** Es un subproceso corriendo y eso no se serializa:
  lo que se guarda es cómo volver a él, no él.
- **`~/.jafne/chats/` crece sin techo.** Es lo elegido. Si algún día molesta, la respuesta
  es un comando que borre, no una caducidad automática.
- **El transcript duplica lo que el proveedor ya tiene.** Es el precio del agnosticismo de
  ADR-0003, y se paga en disco, que es barato.
