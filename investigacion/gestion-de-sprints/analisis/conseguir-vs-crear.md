# Conseguir un MCP de sprints vs. crear el propio

- **Estado:** explorando (2026-08-11)
- **Sub-problema de:** [gestión de sprints](../research.md)

## El problema

[ADR-0014](../../../docs/adr/0014-gestion-de-sprints-via-mcp.md) congeló el requisito
—planificar es trabajo regular, se accede vía MCP— y dejó abierta la rama: se consigue un
MCP existente o se crea uno. Con las fuentes relevadas
([01](../fuentes/01_mcp-oficiales-atlassian-y-linear.md),
[02](../fuentes/02_mcp-comunitarios-y-github-projects.md)) ya se puede comparar.

## Las opciones

| Opción | A favor | En contra |
|---|---|---|
| **Atlassian oficial** (Jira) | GA desde feb-2026, primera parte, OAuth 2.1, sprints y boards nativos | Trae Jira entero como dependencia: cuenta, vendor, superficie enorme para lo que ADR-0014 pide. Endpoint remoto que cada Workspace tiene que poder alcanzar (ADR-0011) |
| **Linear oficial** | Primera parte, conector nativo en Claude, ampliado en feb-2026 | Linear no tiene sprints, tiene **cycles** — ventana de tiempo fija, no contenedor de trabajo. El desajuste conceptual es real, no de nombre |
| **MCP comunitario de Jira** | `mcp-atlassian-extended` cubre sprints, backlog y capacidad | Seis implementaciones sin una dominante; sumar una capacidad de un repo que no controla nadie del proyecto requiere aprobación por la cadena completa (ADR-0004) sobre un tercero |
| **GitHub Projects (comunitario)** | Los repos de Agente ya viven en GitHub (ADR-0004): cero cuentas, vendors ni auth nuevos | Implementaciones comunitarias; GitHub Projects es más flexible y menos opinado que Jira sobre qué es un sprint |
| **Crear el MCP propio de JAFNE** | Modela exactamente la relación Sprint ↔ Asunto que JAFNE necesite; el estado vive donde JAFNE decida | Hay que construirlo y mantenerlo; y si el equipo ya planifica en otra herramienta, JAFNE queda con un segundo lugar donde mirar |

## Lo que las fuentes cambiaron respecto de la intuición inicial

**Ninguna opción externa contesta la pregunta que importa.** Las cinco asumen que el
sprint vive en la herramienta y que el MCP es un cliente. La pregunta de ADR-0014 —¿dónde
vive el estado de un sprint y qué relación tiene con un Asunto?— se **esquiva**, no se
responde. Elegir herramienta primero sería elegir sin haber decidido el modelo.

**Es la pregunta de modelo la que decide la herramienta, no al revés.** Hay dos formas
posibles y no son equivalentes:

- **Un Sprint agrupa Asuntos** — el sprint es el contenedor y el Asunto la unidad de
  ejecución adentro. Encaja con el sprint de Jira y con la práctica habitual.
- **Sprint y Asunto son ejes independientes** — como `estado_asunto` y `estado_contenedor`
  en [ADR-0008](../../../docs/adr/0008-estado-de-asuntos-y-panel-web.md). Un Asunto podría
  no pertenecer a ningún sprint (un bug urgente) y un sprint podría contener trabajo que
  no es un Asunto de JAFNE. Encaja con el *cycle* de Linear.

La segunda es más fiel a cómo JAFNE ya modela sus otros ejes, y admite que el Usuario
planifique en su herramienta sin que JAFNE le imponga que todo pase por un Asunto.

## Lean actual (no decidido)

- **Decidir el modelo Sprint ↔ Asunto antes que la herramienta.** Es lo único que después
  no se puede cambiar barato.
- Si el modelo termina siendo **ejes independientes**, la herramienta pasa a ser un
  detalle reemplazable y conviene un cliente MCP existente sobre lo que el equipo ya use.
- Si el modelo termina siendo **el sprint como contenedor de Asuntos**, JAFNE necesita
  estado propio del sprint, y ahí un MCP propio deja de ser sobreingeniería.
- **GitHub Projects es el candidato externo más barato** si se elige adoptar: no suma
  vendor, cuenta ni auth, y los repos ya están ahí (ADR-0004).

## Abierto

- La pregunta de modelo, que es la que bloquea todo lo demás.
- ¿El Usuario ya planifica en alguna herramienta hoy? Si la respuesta es sí, el espacio de
  opciones se reduce a una y esta comparación deja de importar.
- Alcance de red: los MCP oficiales son endpoints remotos, y un Workspace tiene la red
  restringida por proyecto (ADR-0011). ¿Quién habla con el MCP — el Encargado desde su
  Workspace, o el Asistente desde afuera?
- Manejo del OAuth de esos servidores, que sigue abierto junto con el resto de los
  secretos.
