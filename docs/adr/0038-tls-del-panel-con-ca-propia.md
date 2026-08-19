# ADR-0038 — El panel sirve TLS con una CA propia, para desbloquear el micrófono

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0020](./0020-hosting-y-autenticacion-del-panel.md)

## Contexto

[ADR-0020](./0020-hosting-y-autenticacion-del-panel.md) dejó anotado el pendiente
`tls-y-rotacion-de-token`: faltaba decidir TLS propio del panel, cada cuánto rota el token
y qué hacer si se filtra. Quedó abierto porque **no había urgencia real**: el panel viaja
por la malla ZeroTier, que ya cifra extremo a extremo
([ADR-0011](./0011-redes-y-puertos-de-workspace.md)), así que agregar TLS parecía cifrar
dos veces lo mismo.

[ADR-0036](./0036-dictado-por-voz-con-whisper-local.md) cambió eso, y por un motivo que no
tiene nada que ver con la confidencialidad. El Usuario pidió el 2026-08-19 poder dictar
desde cualquier nodo de la malla, y los navegadores **se niegan a entregar el micrófono a
un origen que no sea un contexto seguro**: HTTPS, o `localhost`. Sobre `http://10.144.0.1:8730`
el botón de dictado queda muerto, sin importar cuán cifrado esté el transporte por debajo.

Vale registrar la alternativa que se evaluó y no funciona, porque es la primera que se le
ocurre a cualquiera: **mudar el panel a la máquina con GPU no resuelve nada**. La regla del
navegador mira el origen que carga, no dónde está el servidor; desde un tercer nodo,
`http://10.144.0.2:8730` es igual de inseguro que el otro. El único atajo sería abrir el
navegador en esa misma máquina contra `127.0.0.1`, que es justo lo contrario de "desde
cualquier lugar".

## Decisión

- **El panel y el nodo de voz pueden servir TLS**, con `--cert` y `--clave` (o
  `$JAFNE_PANEL_CERT` / `$JAFNE_PANEL_CLAVE`). Lo sirve el mismo proceso: uvicorn ya lo
  hace, y no hace falta un proxy inverso adelante.

- **El motivo es la capacidad del navegador, no la confidencialidad.** Queda escrito
  porque cambia qué se exige: el transporte ya iba cifrado por ADR-0011, así que TLS no
  agrega secreto — **desbloquea el micrófono**. De ahí sale todo lo demás.

- **Por eso TLS no es obligatorio fuera de loopback.** Sin certificado el panel sigue
  sirviendo HTTP, porque mirar el dashboard por la malla es legítimo y ya va cifrado.
  Exigirlo rompería ese uso para arreglar otro. Lo que **sí** se hace es avisar al
  arrancar: sin TLS, el dictado remoto no va a funcionar, y es mejor leerlo en la consola
  que descubrirlo con un botón gris.

- **Los certificados salen de una CA propia** (`mkcert`), no de una autoridad pública. Las
  IPs de la malla son privadas: una autoridad pública exigiría un dominio propio y un
  desafío DNS-01, y ataría una red que es del Usuario a un tercero y a una renovación cada
  90 días. Con CA propia se emite para `10.144.0.1` y se termina.

- **Ni el certificado ni su clave entran al repo ni a `~/.jafne/`.** El almacén es estado
  operativo de Asuntos ([ADR-0007](./0007-jerarquia-de-directorios-de-jafne-implementado.md));
  una clave privada no es eso. Se declaran por ruta, como todo lo demás.

- **Esto decide TLS y nada más.** La rotación del token sigue abierta: el pendiente se
  **acota** a `rotacion-de-token` en vez de cerrarse. Dar por contestado lo que no se
  contestó es exactamente lo que vuelve inútil a `pendientes.py`.

## Alternativas descartadas

- **Un certificado autofirmado suelto, sin CA:** descartada — cada dispositivo muestra la
  advertencia y hay que aceptarla a mano, en cada navegador; en iOS/Safari es peor que
  molesto. Con una CA propia la advertencia se paga **una vez por dispositivo**, instalando
  la raíz, y después no aparece nunca más.
- **Let's Encrypt por desafío DNS-01:** descartada — es la opción más limpia si ya hubiera
  un dominio, pero pide dominio propio, credenciales de la API del DNS y renovación
  automática cada 90 días, para una red privada que no necesita que nadie de afuera valide
  nada.
- **Un proxy inverso (Caddy, nginx) que resuelva HTTPS:** descartada — es una pieza más de
  operación, y ya van tres procesos. Uvicorn sirve TLS con dos parámetros; meter un proxy
  para eso sería agregar un servicio para no pasar dos rutas.
- **Un túnel SSH que exponga el panel como `localhost` en cada dispositivo:** descartada —
  funciona y hasta da contexto seguro gratis, pero hay que levantarlo en cada máquina cada
  vez, y en un celular no es una opción realista.
- **Mudar el panel al nodo con GPU:** descartada porque **no resuelve el problema** (ver
  contexto). Además arrastraría `~/.jafne/` a la otra máquina —los Asuntos, el historial y
  el reloj— y eso toca `sincronia-entre-maquinas`, que sigue sin decidirse.
- **Exigir TLS fuera de loopback:** descartada — rompe mirar el dashboard por la malla, que
  ya va cifrado por ADR-0011, para arreglar un problema que solo tiene el micrófono.

## Consecuencias

- **El dictado funciona desde cualquier nodo** que tenga instalada la raíz de la CA. Es lo
  que se buscaba, y es lo único que lo consigue sin depender de nadie de afuera.
- **Aparece una CA propia, y su clave privada es un activo.** Quien la tenga puede firmar
  un certificado para *cualquier* dominio y los dispositivos con esa raíz instalada le van
  a creer, incluso fuera de la malla. Vive donde `mkcert` la deja, no se copia y no entra
  al repo. Es un poder nuevo que antes no existía y conviene tenerlo presente.
- **Instalar la raíz en cada dispositivo es trabajo manual**, y en Android e iOS es más
  incómodo que en una PC. Es el precio elegido a cambio de no ver advertencias nunca más.
- **Cada IP nueva de la malla necesita entrar en el certificado.** Un nodo que se suma
  obliga a reemitir, o a haberlo previsto listando varias IPs desde el principio.
- **El token sigue viajando igual y sin rotación decidida.** Con TLS va cifrado dos veces;
  qué hacer si se filtra sigue sin respuesta y sigue anotado.
- **`~/.jafne/` no cambia.** Ni el panel ni el nodo guardan nada nuevo: el certificado es
  configuración de arranque, no estado.
