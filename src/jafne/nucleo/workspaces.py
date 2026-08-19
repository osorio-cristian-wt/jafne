"""El Workspace Broker: quien crea y destruye los entornos donde trabajan los Agentes.

Junta las decisiones que hasta ahora vivían sueltas y no tenían quién las ejecutara:

- **Los Agentes nunca hablan con el motor** (ADR-0012). Piden un Workspace y lo reciben;
  qué es Podman lo sabe `motor.py` y nadie más.
- **Un contenedor por repositorio** (ADR-0047), creado al delegar un Agente. El Asunto no
  tiene contenedor propio, y el Encargado corre en el host.
- **Persiste mientras su repo lo necesite** (ADR-0016). Se crea, queda `activo`, puede
  pasar a `suspendido` sin consumir cómputo, y se destruye al cerrar.
- **Se entra con `podman exec`** (ADR-0045). JAFNE ya no elige runtime: usa el default, y
  con él `exec` funciona. El proceso principal solo mantiene el contenedor en pie.
- **La imagen la declara el repo** en su `Dockerfile.dev` (ADR-0048). Este módulo la
  construye y la usa; no adivina stacks ni mantiene imágenes propias.

La red es **por proyecto** (ADR-0011): dos Workspaces del mismo proyecto se ven, y los de
proyectos distintos no. Se llama `jafne-<proyecto>` y la crea el Broker si falta.

Lo que este módulo **no** hace: descubrir los servicios del proyecto —base de datos, colas,
otros repos—. Eso sigue siendo la pregunta abierta `workspace-broker` en `pendientes.py`.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, replace

from .motor import Motor, MotorNoDisponible, Salida

#: Imagen de un Workspace cuando el repo todavía no declara la suya.
#:
#: Es un piso para no quedarse sin nada, **no** la forma normal: ADR-0048 dice que la
#: imagen sale del `Dockerfile.dev` del repo, y ADR-0049 que el Encargado lo siembra
#: cuando falta.
IMAGEN_POR_DEFECTO = "docker.io/library/alpine:latest"

#: El archivo con el que un repositorio declara su entorno de trabajo (ADR-0048).
#:
#: `Dockerfile.dev` y no `Dockerfile`: el de la raíz, cuando existe, suele ser el de
#: producción —chico, sin git ni herramientas— y daría un contenedor donde el Agente no
#: puede trabajar.
DOCKERFILE_DEV = "Dockerfile.dev"

#: Lo que corre adentro para que el contenedor siga en pie (ADR-0048).
#:
#: Lo impone JAFNE y no el `CMD` del repo: si dependiera del `CMD`, un servidor de
#: desarrollo que crashea se llevaría puesto el lugar de trabajo del Agente. Levantar el
#: entorno es algo que el Agente hace con `exec` cuando lo necesita.
KEEP_ALIVE: tuple[str, ...] = ("sleep", "infinity")

#: Prefijo de todo lo que crea JAFNE, para poder listar lo suyo y no tocar lo ajeno.
PREFIJO = "jafne-"

#: Dónde se montan los repos del proyecto adentro del Workspace.
MONTAJE_REPOS = "/repos"

_NOMBRE_VALIDO = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class PedidoInvalido(ValueError):
    """El pedido de Workspace no se puede cumplir tal como vino."""


@dataclass(frozen=True)
class Pedido:
    """Lo que se pide al delegar un Agente a un repositorio (ADR-0047).

    Los tres primeros campos son el nombre del contenedor: **proyecto, Asunto y repo**. Un
    Agente trabaja sobre un repo dentro de un Asunto, y los tres niveles hacen falta para
    que dos trabajos sobre el mismo repo no se pisen.

    Ya **no lleva clase de riesgo**: ADR-0045 sacó el aislamiento de los motivos y JAFNE
    dejó de elegir runtime. El comando tampoco viene de afuera — lo impone el Broker
    (`KEEP_ALIVE`), porque el trabajo entra por `exec` y no por el proceso principal.
    """

    proyecto: str
    asunto: str
    repo: str
    imagen: str = IMAGEN_POR_DEFECTO
    montajes: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for campo, valor in (
            ("proyecto", self.proyecto),
            ("Asunto", self.asunto),
            ("repo", self.repo),
        ):
            if not _NOMBRE_VALIDO.match(valor or ""):
                raise PedidoInvalido(
                    f"'{valor}' no es un id de {campo} válido: minúsculas, dígitos, punto, "
                    f"guion y guion bajo, hasta 64 caracteres."
                )


@dataclass(frozen=True)
class Workspace:
    """Un contenedor de repositorio en pie (ADR-0047)."""

    nombre: str
    proyecto: str
    asunto: str
    repo: str
    red: str
    imagen: str
    comando: tuple[str, ...]

    def a_dict(self) -> dict:
        crudo = asdict(self)
        crudo["comando"] = list(self.comando)
        return crudo


@dataclass(frozen=True)
class Resultado:
    """Cómo terminó un comando corrido adentro de un contenedor."""

    nombre: str
    codigo: int | None
    salida: str

    @property
    def bien(self) -> bool:
        return self.codigo == 0


class WorkspaceRechazado(RuntimeError):
    """El motor no pudo crear el Workspace.

    Distinto de `MotorNoDisponible` —*no hay motor*—: acá el motor estaba y aun así falló,
    que es un problema operativo y no de diseño.
    """


def nombre_de(proyecto: str, asunto: str, repo: str) -> str:
    """Cómo se llama el contenedor de ese repo, en ese Asunto (ADR-0047).

    Los tres niveles, derivados y no aleatorios: pedir dos veces el mismo contenedor tiene
    que dar el mismo, y quien mire `podman ps` tiene que poder decir de qué trabajo es sin
    consultarle a JAFNE.
    """
    return f"{PREFIJO}{proyecto}-{asunto}-{repo}"


def etiqueta_de(proyecto: str, repo: str) -> str:
    """Cómo se llama la imagen construida del `Dockerfile.dev` de ese repo (ADR-0048)."""
    return f"{PREFIJO}{proyecto}-{repo}:dev"


def red_de(proyecto: str) -> str:
    """La red del proyecto (ADR-0011). Una por proyecto, no una por Workspace."""
    return f"{PREFIJO}{proyecto}"


class Broker:
    """Lanza, observa y destruye Workspaces.

    Recibe el `Motor` en vez de construirlo para poder probarse sin Podman instalado — la
    suite no puede depender de que la máquina que la corre tenga una VM levantada.
    """

    def __init__(self, motor: Motor | None = None) -> None:
        self._motor = motor or Motor()

    @property
    def motor(self) -> Motor:
        return self._motor

    def estado(self) -> dict:
        """Qué puede hacer Infraestructura hoy. Es lo que se sirve por HTTP y por MCP."""
        ruta = self._motor.ruta()
        if not ruta:
            return {
                "motor": None,
                "encendido": False,
                "runtimes": [],
                "detalle": "No hay Podman instalado (ADR-0012).",
            }
        encendido = self._motor.encendido()
        return {
            "motor": ruta,
            "version": self._motor.version(),
            "encendido": encendido,
            "remoto": self._motor.es_remoto() if encendido else None,
            "runtimes": sorted(self._motor.runtimes()) if encendido else [],
            "detalle": (
                None
                if encendido
                else "Podman está instalado pero su máquina no contesta: `podman machine start`."
            ),
        }

    def construir(self, pedido: Pedido, raiz_repo: str) -> str | None:
        """Construye la imagen que el repo declara, y devuelve su etiqueta.

        Devuelve `None` si el repo **no tiene `Dockerfile.dev`**, que hoy es el caso de
        todos: ADR-0049 le dio al Encargado la tarea de sembrarlo, y hasta que eso corra el
        Broker cae a `IMAGEN_POR_DEFECTO`. Devolver `None` en vez de fallar es lo que
        permite que ese camino conviva con el sembrado.
        """
        from pathlib import Path

        dockerfile = Path(raiz_repo) / DOCKERFILE_DEV
        if not dockerfile.is_file():
            return None

        etiqueta = etiqueta_de(pedido.proyecto, pedido.repo)
        construida = self._motor.construir_imagen(
            etiqueta=etiqueta,
            contexto=str(raiz_repo),
            dockerfile=str(dockerfile),
        )
        if not construida.bien:
            raise WorkspaceRechazado(
                f"No se pudo construir la imagen de '{pedido.repo}' desde su "
                f"{DOCKERFILE_DEV} (ADR-0048): {_motivo(construida)}"
            )
        return etiqueta

    def lanzar(self, pedido: Pedido) -> Workspace:
        """Un contenedor de repo en pie, o una excepción que dice por qué no.

        Corre `KEEP_ALIVE` y nada más: el trabajo del Agente entra después con `exec`
        (ADR-0045). Lo que el repo quiera levantar —un servidor de desarrollo, por
        ejemplo— se arranca por `exec`, para que un proceso que crashea no se lleve puesto
        el contenedor.
        """
        red = red_de(pedido.proyecto)
        preparada = self._motor.asegurar_red(red)
        if not preparada.bien:
            raise WorkspaceRechazado(
                f"No se pudo preparar la red '{red}' del proyecto (ADR-0011): "
                f"{_motivo(preparada)}"
            )

        nombre = nombre_de(pedido.proyecto, pedido.asunto, pedido.repo)
        # Un pedido repetido no debe apilar contenedores con el mismo nombre: el motor
        # fallaría con un choque de nombres, que es un mensaje mucho peor que este.
        self._motor.eliminar_contenedor(nombre)

        lanzado = self._motor.crear_contenedor(
            nombre=nombre,
            imagen=pedido.imagen,
            red=red,
            comando=KEEP_ALIVE,
            montajes=pedido.montajes,
            # El alias es el nombre del repo: dos proyectos pueden tener los dos un `back`
            # sin chocarse, porque cada uno resuelve dentro de su propia red (ADR-0011).
            alias=pedido.repo,
        )
        if not lanzado.bien:
            raise WorkspaceRechazado(
                f"El motor no pudo lanzar el contenedor '{nombre}': {_motivo(lanzado)}"
            )

        return Workspace(
            nombre=nombre,
            proyecto=pedido.proyecto,
            asunto=pedido.asunto,
            repo=pedido.repo,
            red=red,
            imagen=pedido.imagen,
            comando=KEEP_ALIVE,
        )

    def delegar(self, pedido: Pedido, raiz_repo: str) -> Workspace:
        """El disparador: delegar un Agente a un repo le da su contenedor (ADR-0047).

        Es construir y lanzar en un solo paso, porque son un solo acto: al delegar por
        primera vez a un repo hay que tener su imagen, y tenerla es haberla construido.

        Si el repo no declara `Dockerfile.dev` se usa `IMAGEN_POR_DEFECTO` y **se avisa en
        el Workspace devuelto**: es el caso que ADR-0049 le dio al Encargado para sembrar,
        y taparlo con un default silencioso haría que nunca se note que falta.
        """
        construida = self.construir(pedido, raiz_repo)
        efectivo = replace(pedido, imagen=construida) if construida else pedido
        # El repo se monta adentro para que el Agente trabaje sobre él, no sobre una copia.
        montajes = {**pedido.montajes, raiz_repo: f"{MONTAJE_REPOS}/{pedido.repo}"}
        return self.lanzar(replace(efectivo, montajes=montajes))

    def ejecutar(self, nombre: str, comando: tuple[str, ...] | list[str]) -> Resultado:
        """Corre un comando adentro de un contenedor vivo (ADR-0045).

        Es **el** camino por el que entra el trabajo del Agente. Reemplazó a un par
        `esperar`/`correr` que esperaba a que el contenedor terminara: con un contenedor
        que persiste y corre un keep-alive, esperar a que termine es esperar para siempre.
        """
        salida = self._motor.ejecutar_en(nombre, comando)
        return Resultado(
            nombre=nombre,
            codigo=salida.codigo,
            salida=salida.texto or salida.error,
        )

    def suspender(self, nombre: str) -> bool:
        """Congela un contenedor sin destruirlo: `activo` → `suspendido` (ADR-0016).

        Es **el motivo 2 de ADR-0045**: dormir para no gastar cómputo mientras nadie
        trabaja en ese repo. Verificado el 2026-08-19 que `pause`/`unpause` funcionan.
        """
        return self._motor.pausar_contenedor(nombre).bien

    def reanudar(self, nombre: str) -> bool:
        """Descongela un Workspace: `suspendido` → `activo` (ADR-0016)."""
        return self._motor.reanudar_contenedor(nombre).bien

    def registro(self, nombre: str) -> str:
        """La salida del proceso principal del contenedor, tal cual."""
        return self._motor.registro(nombre).texto

    def destruir(self, nombre: str) -> bool:
        """Saca un Workspace. Devuelve si había algo que sacar."""
        return self._motor.eliminar_contenedor(nombre).bien

    def vivos(self) -> list[str]:
        """Los Workspaces de JAFNE que hay ahora, por nombre."""
        try:
            return self._motor.contenedores(PREFIJO)
        except MotorNoDisponible:
            return []


def _motivo(salida: Salida) -> str:
    detalle = (salida.error or salida.texto or "").strip()
    return detalle.splitlines()[-1] if detalle else f"exit {salida.codigo}"
