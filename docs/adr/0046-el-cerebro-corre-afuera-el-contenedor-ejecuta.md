# ADR-0046 — El cerebro corre afuera; el contenedor solo ejecuta

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0012](./0012-motor-de-contenedores-podman.md)

## Contexto

Al preguntarse qué proceso de larga vida corre adentro de un Workspace, apareció que la
pregunta estaba mal planteada: antes de eso hay que decidir **dónde corre el modelo**, y de
ahí se sigue casi todo lo demás — qué necesita la imagen, qué red hace falta, y dónde viven
las credenciales.

Las dos formas son incompatibles entre sí:

- **El cerebro adentro.** El contenedor ejecuta `claude` como su proceso principal. La
  imagen necesita Node, hace falta salida a `api.anthropic.com`, y hay que meter la
  credencial adentro.
- **El cerebro afuera.** JAFNE corre el modelo en el host y las herramientas —leer,
  escribir, ejecutar— se aplican adentro del contenedor.

La primera choca con dos decisiones ya tomadas.
[ADR-0034](./0034-el-adaptador-usa-la-sesion-de-claude-code.md) dice que **JAFNE no maneja
credenciales**: invoca la CLI y esta usa la sesión que el Usuario ya inició. Meter esa
sesión adentro de un contenedor la convierte en algo que JAFNE transporta y deposita, que
es justo lo que ese ADR evita. Y [ADR-0011](./0011-redes-y-puertos-de-workspace.md)
restringe la red por proyecto: darle salida a internet a cada Workspace le abre un agujero
a esa restricción.

## Decisión

**El cerebro corre afuera del contenedor. El contenedor es donde se ejecuta el trabajo, no
donde se piensa.**

- JAFNE invoca al modelo en el host, con la sesión del Usuario, exactamente como ya lo hace
  hoy para el Asistente y el Encargado (ADR-0034).
- Las herramientas del Agente se aplican **adentro** del contenedor de su repo, entrando
  con `podman exec` ([ADR-0045](./0045-para-que-existen-los-contenedores.md)).
- **La credencial nunca entra al contenedor.** Ni montada, ni por variable de entorno, ni
  copiada.
- El contenedor **no necesita salida a internet** para que el Agente piense. Si la necesita
  para su trabajo —bajar dependencias, por ejemplo— eso es una decisión del repo y de
  ADR-0011, no un requisito del modelo.

## Alternativas descartadas

- **El cerebro adentro del contenedor:** descartada — obliga a matizar ADR-0034 y ADR-0011
  a la vez, y pone la credencial del Usuario en el mismo lugar donde corre el código que el
  modelo acaba de escribir. Es el reparto de confianza al revés.
- **Un híbrido según la clase de riesgo** —cerebro adentro para lo confiable, afuera para
  lo generado—: descartada. Son dos caminos que mantener y probar, y ADR-0045 acaba de
  sacar la clase de riesgo del modelo, así que ni siquiera queda de dónde colgar la
  condición.

## Consecuencias

- **La imagen del contenedor se simplifica mucho.** No necesita Node para la CLI ni nada de
  JAFNE adentro: solo git y el stack del repo. Eso es lo que hace viable que la imagen la
  declare el repo sin saber que JAFNE existe
  ([ADR-0048](./0048-el-repo-declara-su-entorno-de-desarrollo.md)).
- **ADR-0034 y ADR-0011 quedan intactos**, que era el punto.
- **El contenedor no necesita ningún proceso propio de JAFNE.** Solo tiene que seguir en
  pie para que `exec` tenga a dónde entrar; qué proceso lo mantiene vivo lo fija ADR-0048.
- **El consumo del modelo se sigue midiendo afuera**, donde ya estaba. No cambia nada de lo
  que `medicion-de-consumo` tiene abierto, pero tampoco lo empeora: si el cerebro hubiera
  ido adentro, cada contenedor habría sido un punto de gasto más que observar.
