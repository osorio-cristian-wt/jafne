# ADR-0042 — Infraestructura es un proceso propio, y el servidor MCP vive adentro

- **Estado**: Aceptada. *Matizada por [ADR-0047](./0047-los-contenedores-son-por-repositorio.md).*
- **Fecha**: 2026-08-19
- **Matiza a**: [ADR-0025](./0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md),
  [ADR-0012](./0012-motor-de-contenedores-podman.md)

## Contexto

El Usuario pidió *"un acceso rápido al estado de los distintos proyectos y poder delegar a
uno de los encargados"*, y eligió **un servidor MCP** como la forma de dárselo — coherente
con [ADR-0004](./0004-capacidades-por-repositorio.md) y
[ADR-0014](./0014-gestion-de-sprints-via-mcp.md), que ya habían elegido MCP para dar
capacidades.

Al preguntarle **dónde correrlo** —proceso propio, servicio HTTP o embebido en el panel—,
el Usuario replanteó la pregunta: *"¿no debería ser un proceso aparte, corriendo también el
encargado de la infraestructura, manteniendo los Asuntos y las VM corriendo?"*

Y tenía razón sobre el fondo. **Infraestructura ya estaba diseñada y nunca tuvo proceso**:

- `arquitectura.md` la dibuja desde el día uno como un plano propio, con un Infrastructure
  Manager y un Workspace Broker adentro.
- ADR-0012 le dio el motor y la regla de que *los Agentes nunca hablan con el motor*.
- ADR-0025 le encargó el saldo llamándola *"la única con vista de todos los agentes"*.
- ADR-0027 y [ADR-0041](./0041-el-driver-de-generado-es-krun.md) le encargaron traducir
  clase de riesgo a runtime de aislamiento.

Nada de eso podía ocurrir sin un proceso de larga vida, porque las tres cosas son **dueñas
de algo que sobrevive al turno que lo pidió**: un contenedor, una microVM, una cuenta
global. Mientras tanto `jafne saldo` escribía el archivo directo, o sea que la frase de
ADR-0025 sobre quién lleva la cuenta era literalmente falsa.

## Decisión

**Infraestructura es el cuarto proceso de JAFNE** (`jafne infra`), después del panel, el
reloj y el nodo de voz. Tiene tres responsabilidades, y las tres son cosas que ningún
proceso efímero puede tener:

1. **Los Workspaces.** Crea, observa y destruye, con el aislamiento de ADR-0027/ADR-0041 y
   la red por proyecto de ADR-0011.
2. **El saldo.** Es **el** escritor: `jafne saldo` pasa a ser cliente suyo. Con
   Infraestructura apagada, registrar saldo **falla diciéndolo** en vez de escribir el
   archivo por atrás — un camino alternativo silencioso devuelve los dos escritores sin
   coordinación que esto vino a sacar.
3. **El servidor MCP**, que es cómo el Asistente y los Encargados ven todo lo anterior sin
   que JAFNE se lo inyecte en cada turno.

**El alcance del MCP viaja en la URL, no en lo que el agente dice de sí mismo.** El
Asistente habla por `/mcp/asistente` y ve todos los proyectos; un Encargado habla por
`/mcp/proyecto/<id>` y ve el suyo. Quien arma esa URL es JAFNE al lanzar al agente. Si el
rol fuera un campo del mensaje, un Encargado podría declararse Asistente y la jerarquía de
ADR-0002 se caería con una línea de texto. Por lo mismo, a un Encargado **ni se le listan**
las herramientas con parámetro `proyecto`: una herramienta listada es una promesa, y no
alcanza con que falle si la llama.

**El MCP puede abrir Asuntos**, no solo leer. Es lo que habilita delegar
([ADR-0044](./0044-la-cadena-de-delegacion.md)), y no introduce una clase nueva de
escritor: abrir un Asunto es lo que `jafne abrir` ya hacía.

**Un Workspace persiste mientras su Asunto lo necesite**, tal como fijó
[ADR-0016](./0016-catalogo-cerrado-estado-contenedor.md): se crea, queda `activo`
aceptando trabajo, puede pasar a `suspendido` sin consumir cómputo, y se destruye al
cerrar. Es lo que el Usuario pidió al plantear este proceso —*"manteniendo los Asuntos y
las VM corriendo"*— y este ADR no lo altera.

**Al Workspace se entra con `podman exec`.** El Workspace se lanza con un proceso de larga
vida que solo lo mantiene en pie, y el trabajo entra por `exec`; el registro del contenedor
sigue siendo de dónde se lee su salida.

Esto quedó fijado recién con [ADR-0045](./0045-para-que-existen-los-contenedores.md), y
vale la pena decir por qué. Mientras `generado` corría sobre `krun`, `exec` no existía
—`the handler does not support exec`, porque la microVM tiene kernel propio— y había que
inventar un canal por red. Al bajar el aislamiento de motivo a consecuencia, JAFNE dejó de
elegir runtime, y con el default `exec` funciona.

El protocolo se implementa a mano, sin SDK, por la misma razón que el panel no tiene build
(ADR-0015): son cuatro métodos de JSON-RPC. Si crece, esa parte merece revisarse.

## Alternativas descartadas

- **El MCP embebido en el panel:** descartada — le sumaría al panel la responsabilidad de
  escribir estado, que es exactamente lo que
  [ADR-0035](./0035-el-reloj-corre-en-su-propio-proceso.md) le sacó al mudarle el reloj.
- **El MCP como proceso stdio, aparte de Infraestructura:** descartada por el Usuario. Era
  más barata —la CLI lo levanta por turno, sin puerto ni token— y habría llegado antes,
  pero deja a Infraestructura sin existir y el saldo con dos escritores. Se prefirió la
  forma final antes que la rápida.
- **Que `jafne saldo` siga escribiendo el archivo y Infraestructura solo lo lea:**
  descartada — deja a Infraestructura sin ser dueña del dato que ADR-0025 le dio.
- **Que el agente declare su rol en el mensaje MCP:** descartada — convierte el
  acotamiento del Encargado en una sugerencia.
- **Exponer el saldo sin su pendiente:** descartada — haría creer que hay una medición
  automática que `medicion-de-consumo` todavía no resolvió. Se sirve el número con el aviso
  pegado, como ya hace `/api/uso-suscripciones`.

## Consecuencias

- **Son cuatro procesos.** Panel, reloj, nodo de voz e Infraestructura. Cada uno con su
  token, y `rotacion-de-token` —abierto— pasa a tener que valer para cuatro.
- **El token de Infraestructura es el que más pesa.** El del panel da acceso a un agente
  que escribe en `C:/Repos`; este crea máquinas y escribe el saldo.
- **`jafne saldo` deja de funcionar sola.** Es el costo elegido de tener un solo escritor,
  y el error lo dice con el comando para levantarla.
- **El Workspace Broker dejó de ser una promesa.** Con ADR-0041 y este ADR, un Workspace se
  crea de verdad: verificado el 2026-08-19, `revisado` sobre `crun` devuelve el kernel del
  host y `generado` sobre `krun` uno propio.
- **Un Workspace vivo cuesta plata mientras vive.** Al persistir (ADR-0016), el cómputo se
  paga hasta que alguien lo suspenda o lo destruya. Por eso `suspendido` no es decorativo:
  es el estado natural de un Asunto que espera respuesta del Usuario, y quien lo mueve es
  Infraestructura, que es la única con la vista global que ADR-0025 le dio.
- **Hace falta decidir qué corre adentro para mantenerlo en pie.** Un Workspace persistente
  necesita un proceso de larga vida que escuche por la red. Qué es ese proceso y con qué
  protocolo recibe trabajo es `protocolo-asignacion-tareas`, todavía abierto.
- **Lo que el MCP expone hoy es lectura, apertura de Asuntos y estado del motor.** Falta
  todo lo que dependa de `workspace-broker` —descubrir los servicios de un proyecto— y de
  `sprints`. Que el servidor exista no cierra esas preguntas.
- **El prompt del Asistente tiene que dejar de decir que no puede ver los proyectos.**
  [ADR-0040](./0040-identidad-de-rol-en-el-system-prompt.md) dejó esa declaración
  explícitamente para sacarla cuando el MCP existiera, y este ADR es ese momento.
