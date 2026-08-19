# ADR-0041 — El driver de la clase `generado` es krun, no kata

- **Estado**: Reemplazada por [ADR-0045](./0045-para-que-existen-los-contenedores.md)
- **Fecha**: 2026-08-19
- **Reemplaza a**: [ADR-0032](./0032-driver-de-la-clase-generado.md)

## Contexto

[ADR-0032](./0032-driver-de-la-clase-generado.md) eligió **kata** como runtime de la clase
`generado`, con un argumento que sigue siendo correcto: el límite de aislamiento no puede
vivir donde el agente razona, así que el código recién generado corre en una **microVM** y
no en un contenedor reforzado. Y eligió kata concretamente por una razón de costo: sería
*"un runtime OCI del mismo Podman"*, de modo que no hubiera que operar dos stacks.

Al montar el motor por primera vez en la máquina del Usuario —2026-08-19, Windows 11 con
Podman 5.8.3 sobre WSL2— esa premisa resultó **falsa por un cambio del propio kata**:

- kata 3.x **dejó de ser un runtime OCI**. El binario `kata-runtime` ya no implementa
  `create`/`delete`; ahora kata se invoca como shim de containerd
  (`containerd-shim-kata-v2`). Podman lo llama y recibe `Invalid command "create"`.
- Su imagen invitada tampoco se construye sola bajo WSL2: el postinstall busca un `vmlinuz`
  en los módulos del kernel **en ejecución**, que es el de WSL2 y no lo trae. Hay que
  apuntar el osbuilder al kernel Fedora de la VM a mano.

O sea: ADR-0032 nombró un driver que hoy **no puede cumplir la frase con la que se lo
eligió**. Usar kata exigiría meter containerd al lado de Podman, que es exactamente el
segundo stack que ADR-0032 quiso evitar.

Existe otro runtime que sí cumple esa frase: **krun** —`crun` compilado con `libkrun`—, que
es un runtime OCI del mismo Podman y arranca cada contenedor dentro de una microVM sobre
KVM.

## Decisión

**La clase `generado` corre con `krun`.** `revisado` sigue con `crun`, sin cambios.

Lo demás de ADR-0032 queda en pie y por eso este ADR lo reemplaza en vez de contradecirlo:
siguen siendo **dos runtimes del mismo Podman** elegidos por contenedor, `generado` sigue
yendo a microVM porque ese límite lo impone el hardware, y si el runtime falta el Workspace
se **rechaza** en vez de degradarse en silencio.

Verificado contra el motor real antes de fijarlo, porque un aislamiento que no se probó no
es un aislamiento. Corriendo `uname -r` dentro de un contenedor de cada clase:

| Clase | Runtime | Kernel que ve el contenedor |
|---|---|---|
| `revisado` | `crun` | `6.18.33.2-microsoft-standard-WSL2` — el del host |
| `generado` | `krun` | `6.12.91` — **propio** |

Ese segundo número es la prueba: kernel distinto significa microVM real, no namespace. Es
posible porque el Ryzen expone `svm` (AMD-V) y `/dev/kvm` llega hasta adentro de WSL2.

## Alternativas descartadas

- **Seguir con kata, sumando containerd:** descartada — es el segundo stack que ADR-0032
  eligió kata justamente para no tener. El costo que hacía barata a esa decisión desapareció.
- **Degradar `generado` a `crun` mientras no haya microVM:** descartada — le daría al
  Encargado una garantía de aislamiento que no tiene, que es lo que ADR-0032 prohibió en su
  última línea y lo que `RuntimeNoDisponible` existe para impedir.
- **Cambiar el default de `generado` a `revisado`:** descartada — mueve el riesgo en vez de
  contenerlo, y contradice ADR-0027, que eligió la clase estricta por defecto a propósito.
- **gVisor (`runsc`):** descartada por ahora — es aislamiento por interposición de syscalls,
  no por hardware, así que vuelve a poner el límite en software. Si alguna vez la microVM no
  fuera viable en la máquina del Usuario, es la primera alternativa a evaluar.

## Consecuencias

- **El aislamiento de ADR-0027 dejó de ser teórico.** Las dos clases tienen driver que corre
  de verdad en la máquina del Usuario, así que el Workspace Broker puede crear Workspaces en
  vez de rechazarlos todos.
- **El runtime se declara del lado del servidor, no por comando.** El `podman.exe` de
  Windows es un cliente **remoto** y no acepta `--runtime`: la elección viaja en la
  configuración de la máquina Podman. Es una restricción del transporte, no del diseño, pero
  condiciona cómo el Broker pide un Workspace.
- **La imagen invitada es un artefacto de la instalación, no del repo.** Vive en la máquina
  Podman (`/var/cache/kata-containers/`, construida contra el kernel Fedora de la VM) y una
  recreación de esa máquina la borra. Recrearla es parte de poner en pie el entorno, y está
  documentado en `estado-de-implementacion.md`.
- **El argumento de ADR-0032 sobrevive a su driver.** Lo que caducó fue un hecho sobre kata,
  no el razonamiento: el límite sigue teniendo que estar en el hardware. Si mañana krun
  también deja de servir, lo que hay que buscar es otra microVM, no otra capa de software.
