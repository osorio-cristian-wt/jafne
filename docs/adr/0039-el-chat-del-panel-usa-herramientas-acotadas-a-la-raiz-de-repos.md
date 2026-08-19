# ADR-0039 — El chat del panel usa herramientas, acotadas a la raíz de repos

- **Estado**: Aceptada
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0013](./0013-panel-web-como-dashboard-visual.md)

## Contexto

El adaptador de Anthropic llegó con el chat del panel deliberadamente **sin herramientas**:
lista blanca vacía, con el argumento de que una pestaña del navegador no debería poder
tocar el disco del Usuario sin que nadie apruebe nada.

El Usuario lo corrigió el 2026-08-19, y la corrección es de fondo: **el dashboard existe
justamente para acceder al agente** — al Asistente o a un Encargado—, así que un agente sin
herramientas no es una versión prudente de lo pedido, es otra cosa. La misma conversación
dejó claro hacia dónde va: el Asistente tiene que poder *generar un proyecto* delegando en
Encargados, y el Encargado delegar Agentes de código. Nada de eso ocurre sin herramientas.

Queda una restricción dura, y no es de diseño sino del medio: **desde una página web no hay
forma de contestar un pedido de permiso a mitad de un turno**. El alcance se fija de
antemano o el agente se cuelga esperando a alguien que no puede responderle — el mismo
problema que [ADR-0024](./0024-trabajo-programado-asuntos-disparados-por-tiempo.md) ya había
encontrado para el trabajo programado.

## Decisión

- **El chat del panel usa herramientas.** Sin lista blanca: el agente tiene las suyas, y lo
  que se acota no es *cuáles* sino *dónde*.

- **El borde es la raíz de repos del Usuario** — `C:/Repos` en esta máquina, declarable con
  `$JAFNE_RAIZ_TRABAJO`. Adentro trabaja; afuera el proveedor deniega la operación.

- **No se saltean los permisos.** `acceptEdits` dentro de la raíz, nunca
  `bypassPermissions`: con bypass no habría borde alguno y el límite que el Usuario pidió
  dejaría de existir. La diferencia entre "el agente trabaja" y "el agente puede todo" es
  justamente esta decisión.

- **Fuera del borde se deniega y el turno termina.** No se cuelga: el agente contesta
  diciendo que necesita permiso para eso. Es lo que hace que el borde sea usable y no una
  trampa que congela el chat.

Verificado contra la CLI real antes de fijarlo, porque una garantía de aislamiento que no
se probó no es una garantía: adentro de `C:/Repos` escribió y leyó un archivo; un `Read` a
un archivo de `%TEMP%` cayó en `permission_denials`, el contenido **no** se filtró, y el
turno terminó pidiendo autorización.

## Alternativas descartadas

- **Sin herramientas (lo que estaba escrito):** descartada por el Usuario — deja al
  dashboard sin su razón de ser. Conversar con un agente que no puede mirar nada obliga a
  copiarle y pegarle el contexto a mano, que es el trabajo que JAFNE viene a sacar.
- **Todas las herramientas sin límite (`bypassPermissions`):** descartada — el panel es
  alcanzable desde toda la malla ZeroTier ([ADR-0020](./0020-hosting-y-autenticacion-del-panel.md)),
  así que cualquiera con el token podría escribir en cualquier parte del disco. El costo de
  acotar es casi nulo; el de no acotar es todo el disco.
- **Solo lectura:** descartada — alcanza para conversar y planear, y no alcanza para lo que
  el Usuario pidió, que es que el Asistente **genere** proyectos.
- **Pedir permiso de verdad, con la aprobación en el panel:** descartada por ahora, no por
  mala: es la opción correcta a futuro y exige que el chat sea un flujo bidireccional
  (streaming, un turno que se pausa esperando respuesta). Hoy el chat es un POST que
  espera, así que no hay dónde contestar. Cuando el panel sepa consumir `stream-json`, esta
  decisión merece revisarse.

## Consecuencias

- **El agente puede modificar cualquier repo bajo la raíz**, incluido el de JAFNE. Es lo
  buscado —el Usuario quiere desarrollar JAFNE con JAFNE— y conviene decirlo sin adornos:
  un turno puede dejar el árbol de trabajo cambiado. Git es la red de contención, no este
  ADR.
- **El token del panel pasa a valer más.** Antes daba lectura del estado; ahora da acceso a
  un agente que escribe en `C:/Repos`. Sube la apuesta de `rotacion-de-token`, que sigue
  abierto, y de que el panel no escuche donde no debe.
- **El borde depende del proveedor.** Es la CLI la que deniega fuera de los directorios
  permitidos, no JAFNE. Un adaptador futuro que no ofrezca ese control tendría que
  conseguir el mismo efecto por otro lado —un Workspace, que es donde
  [ADR-0027](./0027-clase-de-riesgo-declarada-por-el-encargado.md) puso el aislamiento de
  verdad— antes de habilitarle herramientas.
- **Los turnos se vuelven más lentos y más caros.** Un agente que lee archivos consume más
  contexto que uno que solo conversa, y `medicion-de-consumo` sigue sin resolver cómo se
  observa eso.
