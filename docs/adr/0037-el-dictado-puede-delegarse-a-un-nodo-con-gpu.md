# ADR-0037 — El dictado puede delegarse a un nodo con GPU de la malla

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0036](./0036-dictado-por-voz-con-whisper-local.md)

## Contexto

[ADR-0036](./0036-dictado-por-voz-con-whisper-local.md) decidió que el dictado corre local
con Whisper, y anotó su costo medido: **tres veces el largo del audio** —14 s para un clip
de 4,7 s— porque la GPU de esta máquina es AMD y CTranslate2 no la usa en Windows, así que
`large-v3` va a CPU. Dictar una instrucción de quince segundos son tres cuartos de minuto
mirando el botón.

El Usuario tiene otra máquina en la malla ZeroTier —`10.144.0.2`, con una NVIDIA 3060 Ti—
y preguntó el 2026-08-19 si el dictado se puede dirigir hacia allá. La placa está ociosa y
el trabajo es exactamente el que sabe hacer.

Lo que hay que cuidar es que ADR-0036 **no decidió "local" por capricho**: decidió no
mandar el audio a la nube porque ADR-0025 fijó suscripciones personales y ADR-0034 que
JAFNE no maneja credenciales. Delegar en otra máquina se parece peligrosamente a lo que
esa decisión descartó, y la diferencia —de quién es la máquina, por dónde viaja el audio—
es justo lo que hay que dejar escrito para no perderla.

## Decisión

- **El dictado se puede delegar a un nodo de la malla, y a dónde se declara.** Con
  `$JAFNE_VOZ_NODO` apuntando a un nodo, el panel le manda el audio; **sin declararlo se
  transcribe acá**, que sigue siendo el comportamiento de ADR-0036. No hay descubrimiento
  automático: si nadie declaró un nodo, no hay tráfico.

- **Lo que ADR-0036 protegía sigue en pie, con una frontera nueva.** No hay nube, no hay
  clave de API y el audio no sale de máquinas del Usuario. Lo que cambia es el alcance de
  "no sale de la máquina": ahora **no sale de la malla**. Es un debilitamiento real y se
  declara acá en vez de dejarlo implícito — el audio pasa de no cruzar nunca una red a
  cruzar una, aunque sea la propia y cifrada de [ADR-0011](./0011-redes-y-puertos-de-workspace.md).

- **El nodo corre el mismo JAFNE** (`jafne voz`), no un servidor de transcripción de
  terceros. El mismo `nucleo/transcripcion.py` de los dos lados: un solo contrato, un solo
  catálogo de modelos y errores que ya vienen con la forma correcta.

- **El nodo presta cómputo y nada más.** No lee `~/.jafne/`, no tiene almacén y no puede
  escribir estado ni por error. Es la misma línea que ADR-0035 trazó para el panel, aplicada
  antes de que se cruce: una máquina que transcribe no es un segundo JAFNE.

- **Al nodo le aplica [ADR-0020](./0020-hosting-y-autenticacion-del-panel.md) completo**:
  nunca todas las interfaces, y fuera de loopback exige token. La comprobación es
  literalmente la misma función que la del panel — dos servicios con reglas de acceso
  copiadas terminan, tarde o temprano, con reglas distintas.

- **Si el nodo declarado no contesta, se rechaza.** No hay caída automática a la CPU de
  acá. Un segundo contra catorce es una diferencia que el Usuario tiene que **ver**, no
  padecer: un dictado que de golpe tarda diez veces más parece un panel roto, no un nodo
  apagado.

- **El dispositivo también se declara** (`auto`, `cuda`, `cpu`). `auto` eligiendo CPU no es
  degradar —es lo que el Usuario pidió al no elegir—, pero declarar `cuda` y que no haya
  GPU usable **se rechaza**: si no, un nodo con CUDA mal instalada transcribiría a 3x
  tiempo real y nadie se enteraría hasta cronometrarlo.

## Alternativas descartadas

- **Correr `jafne panel` en la máquina con GPU y apuntarle el dictado:** descartada —
  arrastra un dashboard entero y un almacén que ahí no significa nada, para exponer una
  placa de video. Es el mismo acoplamiento que ADR-0035 acaba de sacar, en la otra
  dirección.
- **Un servidor Whisper de terceros en el nodo** (`speaches`, `wyoming-faster-whisper`,
  `whisper.cpp --server`): descartada — funcionan, pero atan JAFNE al contrato de API de
  un proyecto externo, que hay que seguir versionando y traducir de los dos lados. El nodo
  ya podía ser JAFNE con dos endpoints y el módulo que ya existía.
- **Caer a la CPU local cuando el nodo no responde:** descartada por lo de arriba. Si
  alguna vez se quiere, tiene que ser **declarado** y visible en la respuesta, no un
  default silencioso.
- **Exponer el nodo por internet en vez de por ZeroTier:** descartada por ADR-0011, que ya
  fijó la malla como el único transporte entre máquinas, y porque publicar un endpoint que
  recibe audio es exactamente lo que no se quiere hacer sin necesidad.
- **Dejarlo como está y bancarse los 14 s:** descartada — es la opción por defecto si el
  Usuario no declara nada, así que no se pierde; pero teniendo la placa ociosa a un salto
  de distancia, no declararla nunca sería desperdiciar la única pieza de hardware que
  resuelve el problema.

## Consecuencias

- **La latencia deja de depender de la CPU y pasa a depender de la red.** Medido desde
  esta máquina, el nodo está a **92 ms de RTT** —va por relay, no por LAN—, contra 14 s de
  transcripción local. Aun con el peor viaje, delegar gana por un orden de magnitud.
- **Hay una tercera cosa que arrancar, y en otra máquina.** Van el panel, el reloj
  (ADR-0035) y ahora el nodo. Si la máquina con GPU está apagada, no hay dictado — y se ve,
  porque el botón aparece deshabilitado con el motivo en vez de fallar al apretarlo.
- **El panel muestra en qué máquina se transcribió.** Después de esta decisión dejó de ser
  obvio, y "dónde estuvo mi audio" no es una pregunta que deba contestarse leyendo
  variables de entorno.
- **Segunda superficie con el mismo problema de token.** `tls-y-rotacion-de-token` sigue
  abierto y ahora aplica a dos servicios: cada uno con su token, ninguno con rotación
  decidida.
- **El modelo se descarga en el nodo, no acá.** Cada máquina mantiene su propio caché, así
  que declarar un modelo distinto de los dos lados es posible y silencioso: el estado que
  el panel muestra viene del nodo, precisamente para que se vea cuál se está usando de
  verdad.
