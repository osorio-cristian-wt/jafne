# ADR-0034 — El adaptador maneja la CLI de Claude Code y hereda la sesión del Usuario

- **Estado**: Aceptada
- **Fecha**: 2026-08-18
- **Matiza a**: [ADR-0028](./0028-anthropic-primero-alcance-de-adaptadores.md)

## Contexto

[ADR-0031](./0031-contrato-de-sesion-reanudable.md) dejó anotado en sus consecuencias que
los términos del Agent SDK chocaban con
[ADR-0025](./0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md): la documentación
dice que para productos hay que usar autenticación por **API key**, y ADR-0025 había
elegido **suscripciones personales**.

Al bajar a lo concreto —*"¿cómo inicio sesión?"*— apareció que las dos vías que parecían
alternativas facturan igual:

| Vía | Qué consume |
|---|---|
| `ANTHROPIC_API_KEY` | API, por token. Facturación aparte |
| Perfil OAuth de `ant auth login` | API, por token. Solo evita el secreto estático en disco |
| `/login` de Claude Code | **La suscripción**, con sus ventanas de 5 h y semanal |

El perfil OAuth no da acceso a la suscripción: es acceso a la API con credencial de
organización. Así que la elección real no era entre dos formas de autenticarse, sino entre
**gastar aparte** o **usar lo que el Usuario ya paga**.

El Usuario decidió (2026-08-18) y declaró el alcance que lo habilita: *"solo yo accedo a
JAFNE"*.

## Decisión

- **El primer adaptador maneja la CLI de Claude Code como subproceso**, con `-p`,
  `--resume` y `--output-format json`, en vez de usar el Agent SDK como librería. Es
  exactamente el **piso genérico** que ADR-0031 ya había dejado previsto, y resulta ser el
  camino principal en vez del de emergencia.

- **JAFNE nunca maneja credenciales.** No las pide, no las guarda, no las muestra y no
  tiene login propio. La sesión es de Claude Code; JAFNE la hereda por ser el proceso que
  lo invoca. *Iniciar sesión en JAFNE* no existe como operación, y esa ausencia es una
  propiedad del diseño, no una carencia.

- **El alcance declarado es un solo Usuario: el dueño de la cuenta.** Es la condición que
  hace válida esta lectura de los términos, cuya cláusula apunta a *ofrecer* el login de
  claude.ai a terceros. Queda escrito para que se sepa qué habría que revisar si deja de
  ser cierto.

- **JAFNE detecta y reporta el estado de la credencial, sin tocarla.** Incluye avisar
  cuando `ANTHROPIC_API_KEY` está definida: esa variable **pisa** la sesión de la
  suscripción y factura por token, que es precisamente lo que esta decisión evita. Un
  usuario que la tenga puesta de otro proyecto pagaría aparte sin enterarse.

- **La ruta del ejecutable es configurable.** No está garantizado que `claude` esté en el
  `PATH` — en la máquina del Usuario **no lo está**, porque usa Claude Code desde la
  extensión, que trae su propio binario. Asumir el `PATH` sería asumir una instalación que
  no es la más común.

## Alternativas descartadas

- **Agent SDK con API key o perfil OAuth (opción A):** descartada por costo y por premisa.
  Es la vía sancionada y la más prolija, pero introduce gasto nuevo por token y deja sin
  sentido la métrica de ADR-0025: si JAFNE corre sobre API, "saldo de la suscripción" no
  existe y la conmutación de [ADR-0026](./0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md)
  pasa a medir otra cosa. Sigue siendo el camino si JAFNE deja de ser personal.
- **Pedir aprobación previa a Anthropic (opción C):** no descartada, aplazada. Los términos
  la contemplan y es lo que correspondería antes de compartir JAFNE. Hoy no bloquea nada.
- **Un formulario de login en el panel:** descartada. Con esta decisión **no hay ningún
  secreto que pegar**, y agregarlo convertiría al panel —que es una consola de control
  (ADR-0013, [ADR-0020](./0020-hosting-y-autenticacion-del-panel.md))— en depositario de
  credenciales del proveedor. El panel muestra el **estado** de la credencial; no la toca.
- **Asumir que `claude` está en el `PATH`:** descartada por evidencia directa — no lo está
  en la máquina donde JAFNE corre.

## Consecuencias

- **El contrato de ADR-0031 se valida antes de lo esperado.** ADR-0028 advirtió que un
  contrato con una sola implementación es una hipótesis, y que la prueba llegaría con el
  segundo adaptador. Acá el primer adaptador resulta ser el piso genérico sobre CLI, que
  era justamente el caso contra el que había que validar el contrato. Es mejor noticia de
  la que parece: si las cuatro operaciones se implementan sobre `-p` / `--resume` /
  `--output-format json`, el contrato no tiene forma de un SDK.

- **ADR-0025 sobrevive intacta.** El saldo sigue siendo el de una suscripción, con sus
  ventanas de 5 h y semanal, y la señal de ADR-0026 sigue significando lo que dice.

- **`medicion-de-consumo` no se cierra, pero se acota.** Con la CLI en juego, la fuente
  natural del saldo es `/usage`, y la pregunta se reduce a si tiene salida consumible por
  un proceso — que es la duda que la investigación ya tenía anotada.

- **El alcance de un solo usuario es una premisa que puede expirar**, y es del tipo que
  expira en silencio. Compartir JAFNE con el equipo obliga a volver acá: no es un detalle
  de despliegue, cambia qué opción es legítima.

- **ADR-0028 se sostiene y se precisa.** Anthropic sigue siendo el primer y único
  adaptador; lo que cambia es *sobre qué* se escribe: la CLI, no la librería.
