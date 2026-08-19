"""Lo único de JAFNE que sabe que Podman existe (ADR-0012).

Todo lo que hay arriba —el Broker, Infraestructura, el Encargado— habla de *repos* y de
*Workspaces*. Acá abajo eso se vuelve un comando, y aislarlo en un módulo es lo que
sostiene que ADR-0012 diga que los Agentes nunca hablan con el motor.

**El cliente de Windows es remoto, y eso cambia cómo se invoca.** `podman.exe` en Windows
no corre contenedores: habla con una máquina Podman sobre WSL2. Lo que necesita resolverse
del lado donde están los archivos y los procesos —construir una imagen, leer un registro,
listar runtimes— viaja por `podman machine ssh`. En Linux, donde el cliente es local, va
derecho.

Desde [ADR-0045](../../../docs/adr/0045-para-que-existen-los-contenedores.md) **JAFNE no
elige runtime**: usa el default de Podman, que es donde `podman exec` funciona. `runtimes()`
sigue existiendo pero solo para **informar** qué tiene la máquina.

Verificado contra el motor real el 2026-08-19 en la máquina del Usuario: Podman 5.8.3
remoto sobre WSL2, default `crun`. Con `crun` andan `exec`, `pause` y `unpause`; con `krun`
andan `pause`/`unpause` pero **no** `exec`.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

#: Cuánto esperar a un comando del motor. Crear un Workspace arranca una microVM, que tarda
#: bastante más que un contenedor común.
ESPERA = 180

#: Los runtimes OCI que JAFNE sabe nombrar, para preguntarle al motor cuáles tiene.
#:
#: Es una lista de *candidatos a buscar* y **ya no un catálogo de decisiones**: desde
#: ADR-0045 JAFNE no elige runtime. Se mantiene porque el valor de este módulo es
#: **reportar lo que la máquina tiene**, y eso sigue sirviendo para diagnosticar.
CANDIDATOS = ("crun", "krun", "runc", "runsc", "kata-runtime")


class MotorNoDisponible(RuntimeError):
    """No hay Podman, o su máquina no está corriendo.

    Se levanta cuando no hay Podman instalado o su máquina no contesta — dos cosas que se
    arreglan distinto que un fallo al crear un contenedor, y por eso tienen tipo propio.
    """


@dataclass(frozen=True)
class Salida:
    """Lo que devolvió un comando del motor."""

    codigo: int
    texto: str
    error: str

    @property
    def bien(self) -> bool:
        return self.codigo == 0


class Motor:
    """Podman, visto desde JAFNE.

    El ejecutable y el ejecutor son inyectables a propósito: los tests no pueden depender
    de que la máquina que corre la suite tenga Podman instalado y una VM levantada. Es la
    misma decisión que en el adaptador de Anthropic, y por la misma razón.
    """

    def __init__(self, podman: str | None = None, espera: int = ESPERA) -> None:
        self._podman = podman
        self._espera = espera
        self._remoto: bool | None = None

    # ── el ejecutable ─────────────────────────────────────────────────────────

    def ruta(self) -> str | None:
        """Dónde está `podman`, o `None` si no está instalado."""
        return self._podman or shutil.which("podman")

    def _exigir(self) -> str:
        podman = self.ruta()
        if not podman:
            raise MotorNoDisponible(
                "No encuentro `podman`. El motor de contenedores de JAFNE es Podman "
                "(ADR-0012): instalalo, o pasá su ruta. Sin motor no se pueden crear "
                "Workspaces, pero el resto de JAFNE funciona."
            )
        return podman

    def _correr(self, argumentos: list[str]) -> Salida:
        try:
            completado = subprocess.run(
                [self._exigir(), *argumentos],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._espera,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            raise MotorNoDisponible(
                f"El motor no contestó en {self._espera}s. Si la máquina de Podman está "
                f"apagada, `podman machine start` la levanta."
            ) from error
        except OSError as error:
            raise MotorNoDisponible(f"No se pudo invocar a podman: {error}") from error
        return Salida(completado.returncode, completado.stdout or "", completado.stderr or "")

    # ── local o remoto ────────────────────────────────────────────────────────

    def es_remoto(self) -> bool:
        """Si este cliente habla con una máquina en vez de correr contenedores él mismo.

        En Windows siempre es remoto: los contenedores corren en la VM de WSL2. Se
        pregunta una vez y se recuerda — no cambia mientras el proceso vive, y es una
        invocación de subproceso por consulta.
        """
        if self._remoto is None:
            salida = self._correr(["info", "--format", "{{.Host.ServiceIsRemote}}"])
            self._remoto = salida.bien and salida.texto.strip().lower() == "true"
        return self._remoto

    def _en_el_motor(self, guion: str) -> Salida:
        """Corre un comando **dentro** del motor, donde están los archivos y los procesos."""
        if self.es_remoto():
            return self._correr(["machine", "ssh", guion])
        return self._correr_local(guion)

    def _correr_local(self, guion: str) -> Salida:
        """El mismo comando, sin máquina de por medio (Linux)."""
        try:
            completado = subprocess.run(
                guion,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._espera,
                shell=True,
            )
        except subprocess.TimeoutExpired as error:
            raise MotorNoDisponible(f"El motor no contestó en {self._espera}s.") from error
        except OSError as error:
            raise MotorNoDisponible(f"No se pudo invocar al motor: {error}") from error
        return Salida(completado.returncode, completado.stdout or "", completado.stderr or "")

    # ── lo que el Broker necesita saber ───────────────────────────────────────

    def encendido(self) -> bool:
        """Si el motor contesta. Con la máquina apagada, no."""
        if not self.ruta():
            return False
        return self._correr(["info", "--format", "{{.Host.Arch}}"]).bien

    def runtimes(self) -> frozenset[str]:
        """Qué runtimes OCI tiene esta máquina, de los que JAFNE sabe nombrar.

        Es **informativo**: desde ADR-0045 JAFNE no elige runtime. Se le pregunta al motor
        por los binarios en vez de leer su configuración, porque un runtime declarado en
        `containers.conf` pero no instalado daría un informe que miente.
        """
        salida = self._en_el_motor("command -v " + " ".join(CANDIDATOS))
        if not salida.texto.strip():
            return frozenset()
        # `command -v` imprime la ruta de cada uno que encontró, uno por línea.
        hallados = {linea.strip().rsplit("/", 1)[-1] for linea in salida.texto.splitlines()}
        return frozenset(h for h in hallados if h in CANDIDATOS)

    def version(self) -> str | None:
        """La versión del motor, para el informe de estado."""
        salida = self._correr(["--version"])
        return salida.texto.strip() or None if salida.bien else None

    # ── Workspaces ────────────────────────────────────────────────────────────

    def asegurar_red(self, red: str) -> Salida:
        """Crea la red del proyecto si no existe (ADR-0011).

        **`isolate=true` no es opcional.** Sin esa opción, dos redes de Podman se alcanzan
        entre sí por IP directa: verificado el 2026-08-19 contra el motor real, el bff de
        un proyecto pingueó el back de otro con 0% de pérdida. El aislamiento entre
        proyectos que ADR-0011 promete —*"el Encargado de BoRR no llega a un contenedor de
        Casa Justina"*— era falso con la red por defecto. Con `isolate=true` el cruce
        falla y la resolución dentro del propio proyecto sigue andando.

        Es idempotente: crear una red que ya está no es un error que valga la pena
        propagar. Ojo con eso — una red creada **antes** de este arreglo sigue sin aislar,
        y hay que borrarla para que se recree.
        """
        return self._en_el_motor(
            f"podman network exists {_citar(red)} || "
            f"podman network create --opt isolate=true {_citar(red)}"
        )

    def construir_imagen(self, etiqueta: str, contexto: str, dockerfile: str) -> Salida:
        """Construye la imagen que el repo declara en su `Dockerfile.dev` (ADR-0048).

        El contexto es la raíz del repo, para que el `Dockerfile.dev` pueda copiar
        archivos suyos. Va por `_en_el_motor` como todo lo demás: en Windows el cliente es
        remoto y el contexto tiene que resolverse del lado donde están los archivos.
        """
        return self._en_el_motor(
            f"podman build --tag {_citar(etiqueta)} "
            f"--file {_citar(dockerfile)} {_citar(contexto)}"
        )

    def crear_contenedor(
        self,
        nombre: str,
        imagen: str,
        red: str,
        comando: tuple[str, ...] | list[str],
        montajes: dict[str, str] | None = None,
        alias: str | None = None,
        publicar: dict[int, int] | None = None,
    ) -> Salida:
        """Lanza el contenedor de un repo, en segundo plano.

        **No pasa `--runtime`**: desde ADR-0045 JAFNE no elige runtime y usa el default de
        Podman. Con el default `podman exec` funciona, que es como entra el trabajo del
        Agente.

        El comando es obligatorio igual: un contenedor vive mientras viva su proceso
        principal. El Broker le pasa un keep-alive (ADR-0048).
        """
        # El alias es cómo los otros contenedores del proyecto lo encuentran (ADR-0011).
        # Va el nombre del repo, no el del contenedor: así el bff de cualquier proyecto
        # llama a `back` y funciona, sin saber en qué Asunto está.
        destino_red = f"{red}:alias={alias}" if alias else red
        partes = [
            "podman run --detach",
            f"--name {_citar(nombre)}",
            f"--network {_citar(destino_red)}",
        ]
        for host, adentro in (publicar or {}).items():
            # Sobre la IP de la malla y nunca sobre 0.0.0.0 (ADR-0011, ADR-0020).
            partes.append(f"--publish {_citar(f'{host}:{adentro}')}")
        for origen, destino in (montajes or {}).items():
            partes.append(f"--volume {_citar(f'{origen}:{destino}')}")
        partes.append(_citar(imagen))
        partes.extend(_citar(a) for a in comando)
        return self._en_el_motor(" ".join(partes))

    def ejecutar_en(self, nombre: str, comando: tuple[str, ...] | list[str]) -> Salida:
        """Corre un comando **adentro** de un contenedor vivo (ADR-0045).

        Es como entra el trabajo del Agente: el proceso principal solo mantiene el
        contenedor en pie, y todo lo demás pasa por acá.
        """
        argumentos = " ".join(_citar(a) for a in comando)
        return self._en_el_motor(f"podman exec {_citar(nombre)} {argumentos}")

    def registro(self, nombre: str) -> Salida:
        """Lo que el Workspace escribió. Con `krun` es la única forma de ver qué hizo."""
        return self._en_el_motor(f"podman logs {_citar(nombre)}")

    def estado_contenedor(self, nombre: str) -> str | None:
        """`running`, `exited`, … o `None` si ese Workspace no existe."""
        salida = self._en_el_motor(
            f"podman inspect --format '{{{{.State.Status}}}}' {_citar(nombre)}"
        )
        return salida.texto.strip() or None if salida.bien else None

    def pausar_contenedor(self, nombre: str) -> Salida:
        """Congela el Workspace sin destruirlo: es `suspendido` de ADR-0016.

        `pause` y no `stop`: congela los procesos dejando la memoria en pie, así que al
        reanudar el proceso de larga vida sigue donde estaba. Un `stop` lo mataría, y con
        `krun` no habría forma de volver a levantarlo adentro sin recrear el contenedor.
        """
        return self._en_el_motor(f"podman pause {_citar(nombre)}")

    def reanudar_contenedor(self, nombre: str) -> Salida:
        """Descongela un Workspace suspendido y lo devuelve a `activo`."""
        return self._en_el_motor(f"podman unpause {_citar(nombre)}")

    def eliminar_contenedor(self, nombre: str) -> Salida:
        """Destruye un Workspace. Es el `destruido` de ADR-0016, y no tiene vuelta."""
        return self._en_el_motor(f"podman rm --force {_citar(nombre)}")

    def contenedores(self, prefijo: str = "") -> list[str]:
        """Los Workspaces vivos, por nombre."""
        salida = self._en_el_motor("podman ps --all --format '{{.Names}}'")
        nombres = [n.strip() for n in salida.texto.splitlines() if n.strip()]
        return [n for n in nombres if n.startswith(prefijo)]


def _citar(valor: str) -> str:
    """Comilla para el shell del motor, que siempre es POSIX aunque el cliente sea Windows.

    No se usa `shlex.quote` de la plataforma que corre JAFNE: en Windows citaría con las
    reglas de `cmd`, y del otro lado hay un `sh` de Linux. El destino manda, no el origen.
    """
    return "'" + str(valor).replace("'", "'\\''") + "'"
