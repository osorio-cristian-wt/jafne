# ADR-0036 — El dictado por voz del panel corre con Whisper local

- **Estado**: Aceptada, matizada por [ADR-0037](./0037-el-dictado-puede-delegarse-a-un-nodo-con-gpu.md)
- **Fecha**: 2026-08-19

## Contexto

El panel es el punto de entrada gráfico a JAFNE, y su entrada principal es el chat con el
Asistente y con el Encargado
([ADR-0013](./0013-panel-web-como-dashboard-visual.md)). El Usuario pidió el 2026-08-19
poder **dictar** ese mensaje en vez de tipearlo: un botón de voz a texto en el dashboard.

Lo que hace interesante a la decisión no es el botón sino de dónde sale la transcripción,
porque JAFNE ya tiene dos reglas que la acotan:

- [ADR-0025](./0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md) fijó
  **suscripciones personales**, no organización, y
  [ADR-0034](./0034-el-adaptador-usa-la-sesion-de-claude-code.md) que JAFNE **no pide, no
  guarda y no ve** credenciales. Una API de transcripción en la nube pide exactamente lo
  que esas dos decisiones dijeron que no íbamos a tener: una clave propia.
- [ADR-0035](./0035-el-reloj-corre-en-su-propio-proceso.md) acaba de devolverle al panel la
  propiedad de **no escribir estado**. Agregarle una función nueva es justo el momento en
  que esa propiedad se pierde por descuido.

## Decisión

- **El dictado corre local, con Whisper**, dentro del proceso del panel. El audio no sale
  de la máquina, no se manda a ningún proveedor y **no se persiste**: entra por la
  request, se transcribe en memoria y se descarta. Lo que el Usuario ve es texto en el
  campo del chat, que después manda —o edita, o borra— como cualquier mensaje tipeado.

- **Transcribir no es escribir estado, y el panel sigue siendo de solo lectura.** Es
  cómputo sobre lo que el Usuario acaba de decir, no una lectura ni una escritura de
  `~/.jafne/`. La propiedad que ADR-0035 devolvió —quién puede mover un Asunto es una
  lista corta y la UI no está en ella— se mantiene intacta, y queda dicho acá para que no
  se erosione con la próxima función que se agregue.

- **El modelo por defecto es el grande** (`large-v3`), que es lo que el Usuario pidió y lo
  que esta máquina sostiene. Se puede cambiar por configuración, con la misma forma que el
  resto del almacén: se declara, no se adivina.

- **Si falta el motor o el modelo, se rechaza; no se degrada en silencio.** Misma regla que
  [ADR-0032](./0032-driver-de-la-clase-generado.md) con el runtime de aislamiento: servir
  una transcripción de un modelo más chico que el declarado es entregar algo peor de lo
  pedido sin decirlo. El panel responde explicando qué falta y el botón se muestra
  deshabilitado con el motivo.

- **La dependencia es opcional.** JAFNE arranca, corre y pasa sus tests sin el motor de
  voz instalado: se instala con el extra `voz`. Un panel sin voz es un panel completo
  menos un botón, no un panel roto.

- **Que falte el motor de voz no es una decisión pendiente.** Falla con su propio error,
  igual que un adaptador no escrito falla con `AdaptadorNoImplementado`
  ([ADR-0028](./0028-anthropic-primero-alcance-de-adaptadores.md)) y no con
  `DecisionPendiente`. Mezclarlos volvería a arruinar la pregunta *"¿qué falta decidir?"*,
  que es lo único que hace útil a `pendientes.py`.

## Alternativas descartadas

- **Una API de transcripción en la nube (OpenAI, Deepgram, Google):** descartada por
  ADR-0025 y ADR-0034 — pide una clave propia que JAFNE decidió no tener, y manda fuera de
  la máquina audio del Usuario hablando de sus proyectos. El costo que ahorra es CPU, que
  es justamente lo que sobra acá.
- **La Web Speech API del navegador:** descartada — parece local y no lo es: en Chrome
  manda el audio a los servidores de Google. Además depende del navegador y de que haya
  internet, para una función que tiene que andar en una máquina de trabajo sin depender de
  nada externo.
- **`openai-whisper` (la implementación de referencia, sobre PyTorch):** descartada frente
  a `faster-whisper` (CTranslate2) — el mismo modelo y la misma calidad, con bastante menos
  memoria y bastante más velocidad en CPU, que es el escenario real de esta máquina. La
  decisión de *qué* modelo no cambia; cambia con qué motor se lo corre.
- **Un modelo chico (`base`, `small`) por defecto:** descartada — el Usuario pidió el
  grande y el hardware lo sostiene. Dictar una instrucción técnica en español mezclada con
  nombres propios y términos en inglés es justo el caso donde un modelo chico obliga a
  corregir a mano lo que se quiso ahorrar tipeando.
- **Un proceso propio para la voz, como el reloj de ADR-0035:** descartada — no comparten
  el motivo. El reloj se separó porque tenía que sobrevivir al panel cerrado; el dictado
  **solo existe mientras alguien mira el panel**, así que vive donde vive su único
  consumidor.

## Consecuencias

- **El audio no sale de la máquina ni toca el disco.** Es la consecuencia que justifica el
  costo en CPU, y la que hace que dictar sea aceptable para hablar de código y clientes.
- **Se paga en CPU y en memoria del proceso del panel.** El modelo se carga **perezoso**
  —en la primera transcripción, no al arrancar— y queda caliente después: un panel que
  nadie usó para dictar no paga nada.
- **Esta máquina no tiene CUDA** (GPU AMD), así que corre en CPU con cuantización int8, y
  eso se paga en latencia: medido sobre `large-v3` en el Ryzen 9 6900HS, transcribir tarda
  **unas tres veces lo que dura el audio** —14 s para un clip de 4,7 s—, estable entre
  corridas. Dictar una instrucción de quince segundos son tres cuartos de minuto de espera.
  Es el precio de tener el modelo grande sin GPU compatible, y es la palanca que el Usuario
  tiene a mano: declarar un modelo más chico con `$JAFNE_VOZ_MODELO`. Se deja anotado acá
  para que la próxima persona que lo lea no descubra el número apretando el botón.
- **El panel gana su primer endpoint que recibe algo pesado del navegador.** Se acota el
  tamaño del audio aceptado, porque un endpoint sin límite es una forma barata de tumbar el
  proceso — incluso sin querer, con el micrófono abierto y olvidado.
- **La superficie de red no cambia.** Sigue valiendo
  [ADR-0020](./0020-hosting-y-autenticacion-del-panel.md): loopback o interfaz ZeroTier, y
  fuera de loopback con token. El endpoint de dictado va por la misma puerta y con la misma
  llave que el resto.
- **El navegador va a pedir permiso de micrófono**, y fuera de loopback solo lo da sobre
  un contexto seguro. Cruza con el pendiente `tls-y-rotacion-de-token`: dictar desde otra
  máquina de la malla ZeroTier va a necesitar el TLS que todavía no está decidido.
