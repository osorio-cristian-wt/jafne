# ADR-0044 — La cadena de delegación: alcance por nivel, y el Encargado conversa en `grande`

- **Estado**: Aceptada. *Matizada por [ADR-0047](./0047-los-contenedores-son-por-repositorio.md).*
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0033](./0033-tamano-por-defecto-del-rol-asistente.md),
  [ADR-0002](./0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md)

## Contexto

[ADR-0002](./0002-jerarquia-de-roles-escalacion-y-modos-de-comunicacion.md) fijó la
jerarquía Usuario → Asistente → Encargado → Agentes y cómo se escala hacia arriba. Lo que
nunca fijó es **qué sabe cada nivel** ni **cómo se dispara el trabajo hacia abajo**, y sin
eso la cadena era un organigrama sin mecanismo.

El Usuario lo describió así el 2026-08-19:

> *"El asistente me delega a un encargado del proyecto; este encargado sabe todo lo
> necesario a nivel de **organización, documentación general y arquitectura general**.
> Luego este encargado puede delegar a un agente programador, que es el que va sobre el
> **repositorio específico** y sabe lo que necesita ese repo: skills y MCP individuales. Por
> ejemplo el encargado de BoRR sabe todos los repos que hay y si le pido una nueva
> funcionalidad, orquesta los repositorios involucrados —front, bff y back— generando un
> agente programador para cada entorno, pidiéndoselos al workspace."*

Y quedaba abierta una pregunta concreta que lo bloqueaba: ADR-0033 no le había dado tamaño
por defecto al Encargado —*"lo elige por tarea"* (ADR-0003)—, pero una **conversación
todavía no es una tarea**, así que no había de dónde derivarlo. Eso estaba declarado en
`pendientes.py` como `cerebro-del-encargado-conversando`, y hacía que
`POST /api/proyectos/{id}/chat` respondiera 501.

## Decisión

**Un proyecto es una organización**, no un repositorio. Se le asignan uno o varios repos —
típicamente los de una organización entera.

**El alcance es por nivel, y no se solapa:**

| Nivel | Qué sabe | Qué documenta |
|---|---|---|
| **Encargado** | La organización: qué repos hay, la arquitectura general, los requisitos | Documentación general y de arquitectura |
| **Agente** | **Un** repositorio: su implementación, sus skills y su MCP propios (ADR-0004) | Documentación de la implementación |

Los requisitos viven arriba y la implementación abajo. Un Encargado que entra a decidir
detalles de implementación de un repo está haciendo el trabajo del Agente, y un Agente que
decide arquitectura entre repos está haciendo el del Encargado.

**Un trabajo que toca varios repos es varios Agentes**, uno por repo, cada uno en su
Workspace, pedidos a Infraestructura
([ADR-0042](./0042-infraestructura-es-un-proceso-con-el-mcp-adentro.md)). El Encargado
orquesta; no baja a los repos él.

**El Encargado conversa en `grande`.** Lo fijó el Usuario, y no contradice a ADR-0003: lo
que ese ADR le dejó al Encargado es el cerebro de una **tarea**, y esto es el tamaño con el
que conversa, que es cuando todavía no hay tarea. Su trabajo al conversar es arquitectura y
organización, y ahí la capacidad del modelo es la variable que más pesa. El **Agente** sigue
sin default, y eso ahora se lee mejor: un Agente siempre nace de una tarea concreta, así que
siempre hay de dónde derivarlo.

**Delegar es abrir un Asunto** (ADR-0006), con su estado, su historial y su cierre. Nada de
trabajo queda fuera del sistema.

**El Asistente delega solo si el Asunto ya existe.** Avanzar trabajo que el Usuario ya mandó
a hacer es su tarea; **abrir** un Asunto nuevo se lo propone y espera. El límite queda en
*crear trabajo*, no en *avanzarlo* — que es la regla de escalación de ADR-0002 aplicada a lo
que cuesta plata y tiempo.

**El Encargado trabaja en un Workspace aislado**, con la clase de riesgo de ADR-0027. Es
posible de verdad desde [ADR-0041](./0041-el-driver-de-generado-es-krun.md): `krun` da
microVM con kernel propio, verificado.

## Alternativas descartadas

- **Que el Asistente delegue solo, sin consultar:** descartada por el Usuario — sería un
  orquestador de verdad, y a cambio cada delegación gasta saldo y abre trabajo sin visto
  bueno. Roza exactamente la regla que cortó la sesión del 2026-08-19.
- **Que el Asistente proponga siempre, incluso para avanzar:** descartada por el Usuario —
  pedir permiso para continuar algo ya aprobado es fricción sin decisión adentro.
- **Delegar como conversación aparte, abriendo el Asunto solo si hace falta:** descartada
  por el Usuario — más liviana para preguntas cortas, pero deja trabajo real fuera de todo
  tablero. Y el chat del Encargado no se guarda
  ([ADR-0043](./0043-los-chats-del-asistente-se-guardan.md)), así que se perdería.
- **Que el Encargado corra en el proceso de JAFNE como el Asistente:** descartada por el
  Usuario — es lo que ya funcionaba y no necesitaba trabajo, pero deja al Encargado
  escribiendo código en el disco del Usuario sin la microVM que ahora sí anda.
- **Que el Encargado conversara en `medio` como el Asistente:** descartada — hacen cosas
  distintas. El Asistente enruta; el Encargado piensa la arquitectura de un proyecto entero.
- **Un Agente por trabajo en vez de uno por repo:** descartada — un solo Agente cruzando
  front, bff y back necesita el contexto de los tres, que es justo lo que ADR-0004 acota
  por repositorio.

## Consecuencias

- **Sale `cerebro-del-encargado-conversando` de `pendientes.py`.** La decisión que lo
  bloqueaba está tomada, y el chat del Encargado dejó de responder 501.
- **Dos roles tienen tamaño por defecto y uno no.** Ya no se lee como escalafón: lo tienen
  los que **conversan**, porque conversando no hay tarea de donde derivarlo.
- **El Encargado sale más caro.** `grande` es Opus, y conversar con él cuesta más que con el
  Asistente. Es la elección del Usuario, y `medicion-de-consumo` sigue sin resolver cómo se
  observa ese gasto.
- **Falta el hop 4.** Cómo se le asigna concretamente la tarea a un Agente sigue siendo
  `protocolo-asignacion-tareas` en `pendientes.py`. Este ADR fija **quién delega a quién y
  con qué alcance**, no el formato del mensaje.
- **El Encargado necesita su propio system prompt.** ADR-0040 dejó el patrón y solo escribió
  el del Asistente; ahora que el Encargado conversa, el suyo tiene contenido que decir —
  alcance de organización, y que delega por repo.
- **Los Workspaces del Encargado son tareas, no cuartos** (ADR-0042): con `krun` no se puede
  entrar a un contenedor, así que lo que va a correr se decide al crearlo.
