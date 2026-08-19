# ADR-0040 — La identidad del rol se agrega al system prompt, versionada y por rol

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0034](./0034-el-adaptador-usa-la-sesion-de-claude-code.md)

## Contexto

Hasta ahora el chat del panel mandaba el mensaje del Usuario **crudo** a `claude -p`. El
agente del otro lado no sabía que era el Asistente de JAFNE: no conocía su rol, ni la
jerarquía de [ADR-0002](./0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md),
ni el borde que [ADR-0039](./0039-el-chat-del-panel-usa-herramientas-acotadas-a-la-raiz-de-repos.md)
le acababa de fijar, ni que las decisiones se escalan al Usuario.

En una prueba contra la CLI real el 2026-08-19 se presentó como *"tu ayudante para tareas
de desarrollo"* — y solo porque el mensaje del Usuario se lo había dicho. Un agente que no
sabe qué rol cumple no puede cumplirlo: no delega porque no sabe que puede, no escala
porque no sabe a quién, y trata su borde como un error en vez de como un límite.

La CLI ya ofrecía la vía (`--system-prompt`, `--append-system-prompt`, y sus variantes
`-file`), así que la pregunta nunca fue técnica sino de diseño, y el Usuario la contestó en
cuatro partes.

## Decisión

- **El texto se agrega, no reemplaza.** Se pasa con `--append-system-prompt-file`. El
  agente conserva íntegro lo que Claude Code ya sabe de sí mismo —sus herramientas, sus
  convenciones— y encima sabe qué rol cumple en JAFNE. El texto se redacta sabiendo que
  convive con esa otra identidad, y lo dice en su primera línea.

- **Vive versionado en el repo**, en `src/jafne/nucleo/prompts/`. Es el contrato de
  comportamiento del rol: cambia con review y queda en el historial, como el código.

- **Un archivo por rol**, no una plantilla parametrizada. Hoy existe solo
  `asistente.md`; Encargado y Agente se agregan cuando les toque el suyo.

- **El estado de los proyectos no se inyecta**: lo consultará por MCP, que el Usuario ya
  eligió como la forma de dárselo. Mientras ese servidor no exista, el prompt **declara
  que no lo tiene** en vez de callarlo — así el agente contesta que no sabe en lugar de
  inventar o de salir a mirar el disco a mano.

El rol lo pasa quien construye el adaptador, no el adaptador por su cuenta: sin `rol` no se
inyecta nada, que es lo correcto para los usos donde la identidad la pone otro.

Verificado contra la CLI real antes de fijarlo. Preguntado *"¿quién sos y qué podés
hacer?"*, sin que el mensaje lo mencionara, el agente contestó con su rol, la jerarquía de
cuatro niveles, el borde de la raíz de repos, la distinción entre lo que resuelve solo y lo
que escala, y que todavía no puede consultar el estado de los proyectos.

## Alternativas descartadas

- **Reemplazar el system prompt (`--system-prompt`):** descartada por el Usuario — perdería
  todo lo que la CLI sabe de sí misma y habría que reescribirlo a mano para recuperarlo. Se
  gana previsibilidad sobre lo que el agente cree ser, y se paga con un agente que sabe
  menos usar sus propias herramientas.
- **Guardarlo en `~/.jafne/`:** descartada por el Usuario — se edita sin tocar el repo, pero
  queda fuera de git: sin historial, sin review, y sin viajar con el repo a otra máquina.
  Cambiar cómo se comporta el Asistente sin dejar rastro es exactamente lo que el repo
  evita documentando.
- **Un solo texto parametrizado por rol:** descartada por el Usuario — evita duplicar la
  parte común (jerarquía, regla de decisiones), pero una plantilla con huecos se lee peor
  que tres textos escritos para su rol, y estos se leen tanto como se editan.
- **Inyectar el estado de los proyectos en cada turno:** descartada por el Usuario —
  funcionaría hoy sin esperar al MCP, pero cuesta tokens en cada turno tenga o no que ver
  con proyectos, y deja el estado congelado al momento de armar el prompt.
- **No decir nada sobre los proyectos hasta que exista el MCP:** descartada — un agente que
  no sabe que no sabe sale a averiguarlo con sus herramientas, que ahora tiene
  (ADR-0039). Declarar el hueco es lo que hace que conteste "no lo tengo".

## Consecuencias

- **Cada turno arrastra el texto entero.** Es la contrapartida de haber elegido `append`:
  el system prompt es más largo, y `medicion-de-consumo` sigue sin resolver cómo se observa
  eso. Mantenerlo corto es parte de mantenerlo.
- **El prompt es código, con su costo y su beneficio.** Cambiar el comportamiento del
  Asistente pasa por un commit; a cambio, un cambio de comportamiento nunca es un misterio.
- **Los tres textos tendrán partes iguales.** La jerarquía y la regla de decisiones valen
  para los tres roles, así que cuando existan `encargado.md` y `agente.md` habrá que
  cambiarlas en tres lugares. Es lo que se aceptó al elegir un archivo por rol; si la
  duplicación termina pesando más que la legibilidad, merece un ADR que lo revierta.
- **El prompt dice lo que el agente no puede hacer, y eso caduca.** Cuando el servidor MCP
  exista, esa sección deja de ser verdad y hay que sacarla en el mismo commit — un prompt
  que declara un hueco ya tapado miente igual que uno que lo calla.
- **El Encargado sigue sin identidad.** Su chat responde 501 por
  `cerebro-del-encargado-conversando`, así que no tiene dónde estrenarla todavía.
