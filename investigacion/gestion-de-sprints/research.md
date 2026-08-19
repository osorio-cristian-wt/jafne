# Gestión de sprints en JAFNE

- **Estado:** explorando (abierta y relevada el 2026-08-11)
- **Origen:** [ADR-0014](../../docs/adr/0014-gestion-de-sprints-via-mcp.md) — el requisito
  (planificar es trabajo regular, y se accede vía MCP) ya está congelado; lo que falta es
  **con qué**, y eso sí hay que buscarlo y compararlo
  ([ADR-0005](../../docs/adr/0005-cuando-investigar-vs-adr-directo.md)).

## El tema

ADR-0014 decidió que el Encargado tiene que poder **crear sprints en medio de una tarea
normal**, consumiendo la gestión de sprints como una capacidad MCP
([ADR-0004](../../docs/adr/0004-capacidades-por-repositorio.md)). No decidió cuál
herramienta, ni dónde vive el estado de un sprint, ni cómo se relaciona un Sprint con un
Asunto.

## Preguntas abiertas

1. **¿Conseguir o crear?** ¿Qué servidores MCP de gestión de sprints/backlog existen hoy
   (Jira, Linear, GitHub Projects, Taiga, Plane, y los MCP oficiales o comunitarios de cada
   uno) y alguno sirve tal cual? Si ninguno sirve, ¿qué mínimo tendría que exponer un MCP
   propio de JAFNE?
2. **¿Dónde vive el estado de un sprint?** Tres candidatos, y no son equivalentes:
   - `~/.jafne/` — junto a los Asuntos, tratándolo como estado operativo del Asistente
     ([ADR-0007](../../docs/adr/0007-jerarquia-de-directorios-de-jafne-implementado.md)).
   - el repo `encargado/` del proyecto — tratándolo como planificación versionada, al lado
     de la investigación y los ADRs de ese proyecto.
   - una herramienta externa — el MCP es solo un cliente, y la verdad vive afuera.
3. **¿Qué relación tiene un Sprint con un Asunto?** ¿Un sprint agrupa Asuntos? ¿Un Asunto
   pertenece a un sprint? ¿O son **ejes independientes**, como el estado de Asunto y el de
   contenedor en [ADR-0008](../../docs/adr/0008-estado-de-asuntos-y-panel-web.md)? Esta es
   la pregunta que más condiciona el modelo de datos.
4. **¿Quién crea el sprint, en qué nivel?** ADR-0014 lo pone en el Encargado (nivel
   proyecto, cruza repos). ¿Un Agente puede al menos proponer ítems de sprint para su repo,
   escalando como siempre (ADR-0002)?
5. **¿Cómo se ve en el panel?** [ADR-0013](../../docs/adr/0013-panel-web-como-dashboard-visual.md)
   deja explícitamente la vista de sprints sin diseñar hasta que esto cierre.

## Qué restringe la respuesta

Decisiones ya congeladas que acotan el espacio de opciones:

- **ADR-0004** — la gestión de sprints entra como capacidad MCP versionada, y sumarla
  requiere aprobación del Usuario por la cadena completa (ADR-0002).
- **ADR-0006** — el Asunto ya es la unidad persistente de trabajo; un sprint no puede
  duplicar ese rol, tiene que ser otra cosa (planificación, no ejecución).
- **ADR-0011** — si la herramienta de sprints es externa, el acceso de red desde un
  Workspace no es gratis: hay aislamiento por proyecto y exposición solo vía ZeroTier.

## Qué se relevó (2026-08-11)

Hay **dos MCP de primera parte** —Atlassian (GA feb-2026) y Linear (ampliado feb-2026)—,
al menos **seis comunitarios de Jira** y **dos de GitHub Projects**. Ver
[`fuentes/`](./fuentes/README.md).

El hallazgo que reordena la investigación: **ninguna opción externa contesta la pregunta
2 ni la 3 de arriba.** Las cinco asumen que el sprint vive en la herramienta y que el MCP
es un cliente; la relación Sprint ↔ Asunto la esquivan. Elegir herramienta primero sería
elegir sin haber decidido el modelo — y el modelo es lo único que después no se cambia
barato.

Dos detalles que no se veían desde afuera:

- **Linear no tiene sprints, tiene *cycles*** — ventana de tiempo fija del equipo, no
  contenedor de trabajo que se abre y se cierra como el sprint de Jira. El desajuste es
  conceptual, no de nombre.
- **Los dos MCP oficiales son endpoints remotos hospedados por el vendor**, con OAuth.
  Eso cruza con [ADR-0011](../../docs/adr/0011-redes-y-puertos-de-workspace.md) (un
  Workspace tiene la red restringida por proyecto) y con el manejo de secretos, que sigue
  abierto.

## Análisis

Ver [`analisis/conseguir-vs-crear.md`](./analisis/conseguir-vs-crear.md) — las cinco
opciones comparadas y el lean actual.

## Fuentes

Ver el índice en [`fuentes/README.md`](./fuentes/README.md).

## Graduación

**El modelo graduó a [ADR-0023](../../docs/adr/0023-sprints-ejes-independientes-y-estado-externo.md)**
(2026-08-11). El caso de uso que dio el Usuario contestó las dos preguntas de una vez:

> *"estoy en un proyecto de piscinas y necesito armar el sprint semanal, se lo encargo al
> agente del proyecto, él usa el MCP para el sprint y **cualquiera de mis desarrolladores
> lo ve**"*

Esa última cláusula decide dónde vive el estado —en la herramienta externa que el equipo
ya mira, porque el destinatario es humano y no va a abrir `~/.jafne/`— y decide el modelo:
**ejes independientes**, porque un sprint contiene trabajo de personas que no son Asuntos
de JAFNE, y armar el sprint es en sí mismo el trabajo de un Asunto, no su contenedor.

También salió un requisito que no era de sprints: la automatización semanal por cron
gradúa a [ADR-0024](../../docs/adr/0024-trabajo-programado-asuntos-disparados-por-tiempo.md)
(Asuntos disparados por tiempo), que rompe el supuesto de ADR-0006 de que todo Asunto lo
abre el Usuario.

**Lo que queda de esta investigación** es la elección de herramienta concreta — y con el
modelo ya decidido pasó de ser una decisión arquitectónica a una práctica: la que el
equipo ya use. Falta también el vocabulario mínimo de sprint que JAFNE necesita para
hablar con cualquiera de ellas (Jira tiene *sprints*, Linear tiene *cycles*).
