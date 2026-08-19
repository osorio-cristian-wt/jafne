# ADR-0028 — Anthropic primero: un solo adaptador implementado, sin cambiar lo soportado

- **Fecha**: 2026-08-18
- **Estado**: Aceptada, matizada por [ADR-0034](./0034-el-adaptador-usa-la-sesion-de-claude-code.md)
- **Matiza a**: [ADR-0010](./0010-proveedores-iniciales-asistente.md)

## Contexto

[ADR-0010](./0010-proveedores-iniciales-asistente.md) declaró los proveedores soportados
para el rol de Asistente: Claude Code y la familia OpenAI. La decisión sobre la propiedad
del proceso del agente (2026-08-18) eligió un **contrato neutral de sesión** con un
adaptador por proveedor debajo, y dejó como último paso previo relevar si la familia
OpenAI ofrece un modo sesión adjuntable — lo único sin averiguar.

El Usuario planteó (2026-08-18) salir antes trabajando solo con Anthropic. Del lado
Anthropic hay certeza: el Agent SDK existe, expone sesiones y es *harness-only* —el
proceso lo hospeda JAFNE—, que es exactamente la forma que el contrato necesita. Del lado
OpenAI, todavía no se sabe si aplica la opción B o hay que caer al piso genérico sobre CLI.

## Decisión

- **Se implementa un solo adaptador: Anthropic.** Los demás quedan declarados y sin
  implementar.

- **ADR-0010 no cambia.** Los proveedores **soportados por diseño** siguen siendo Claude
  Code y la familia OpenAI. Esta decisión es de **alcance de implementación**, no de
  diseño, y las dos cosas se leen juntas o no se entienden:

  > Proveedores soportados: Claude Code y la familia OpenAI (ADR-0010).
  > Adaptador implementado: solo Anthropic (este ADR).

- **El contrato de sesión se escribe antes que el adaptador, y aparte.** Es la condición
  que hace que esto sea alcance y no diseño. Si el adaptador se escribe primero, el
  adaptador *se vuelve* el contrato y el agnosticismo de
  [ADR-0003](./0003-cerebro-por-rol-y-agnosticismo-de-proveedor.md) pasa a ser una
  declaración sin respaldo.

- **Regla de validación del contrato, para cada una de sus operaciones** —abrir sesión,
  adjuntarse, rehidratar historial, leer saldo—: hay que poder contestar *"¿cómo
  implementaría esto el piso genérico sobre un CLI?"*. Una operación sin respuesta tiene
  forma de un proveedor y se rediseña. No requiere escribir ese piso: requiere que exista
  la respuesta.

- **Aparece una categoría que JAFNE no sabía expresar: decidido pero no implementado.**
  No va a `pendientes.py`, que es explícitamente el registro de *decisiones que todavía no
  se tomaron* — acá la decisión **está** tomada y falta el trabajo. Confundirlas vaciaría
  de significado al registro que hace legible el estado de diseño.

- **El hecho viaja en el cerebro.** `Almacen.cerebros()` ya fusiona al leer el saldo del
  proveedor ([ADR-0025](./0025-presupuesto-por-proveedor-y-conmutacion-por-saldo.md)); el
  mismo lugar marca si hay adaptador. Se ve gratis en el panel, que ya lista cerebros, y
  elegir uno sin adaptador falla con un error **propio y distinto** de `DecisionPendiente`.

## Alternativas descartadas

- **Implementar los dos adaptadores a la vez:** descartada por tiempo, y porque uno de los
  dos todavía no tiene relevado si su proveedor ofrece modo sesión. Escribir un adaptador
  contra una incógnita es la forma más cara de averiguarlo.
- **Sacar los cerebros de OpenAI de `cerebros.yaml`:** descartada — desaparecerían de la
  vista y nadie sabría que faltan. Un cerebro visible que falla explícito informa; uno
  ausente miente por omisión. Es el mismo criterio que ADR-0015 aplica a las
  funcionalidades bloqueadas.
- **Anotarlo en `pendientes.py`:** descartada — ese registro responde *"¿qué falta
  decidir?"*. Meter trabajo pendiente ahí haría que la respuesta deje de ser confiable.
- **Declarar a Anthropic como único proveedor soportado y reemplazar ADR-0010:**
  descartada — sería tirar una decisión de diseño válida para reflejar un orden de
  implementación temporal. El agnosticismo de ADR-0003 no se suspende porque haya un solo
  adaptador escrito.

## Consecuencias

- **Tres de los cuatro cerebros de fábrica quedan sin adaptador.** `jafne init` escribe
  hoy un cerebro Anthropic y tres de OpenAI; elegir cualquiera de esos tres falla explícito
  hasta que exista su adaptador.

- **`CONMUTAR` puede quedarse sin destino.** La señal de
  [ADR-0026](./0026-umbral-de-conmutacion-y-diferimiento-por-ventana-corta.md) sigue siendo
  correcta, pero con un solo adaptador no hay a dónde conmutar. El Encargado tiene que
  tratarla como una recomendación sin destino disponible.

- **El camino crítico se acorta.** Relevar el modo sesión de OpenAI deja de bloquear la
  escritura del contrato y pasa a ser trabajo del segundo adaptador.

- **Riesgo asumido, y conviene decirlo:** un contrato con una sola implementación es una
  **hipótesis**, no un contrato validado. La regla de validación de arriba lo mitiga; no lo
  elimina. La prueba real llega con el segundo adaptador, y es esperable que ahí aparezca
  algún ajuste.

- **El piso genérico sobre CLI sigue siendo parte del diseño**, aunque no se implemente
  ahora: es lo que garantiza que un proveedor sin modo sesión pueda entrar igual.
