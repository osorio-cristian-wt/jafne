"""El motor y el Workspace Broker (ADR-0012, ADR-0045, ADR-0047, ADR-0048).

Ningún test toca Podman: se sustituye el ejecutor y se verifica **qué comando se arma** y
**cómo se interpreta la respuesta**. No es solo por velocidad — la suite tiene que correr
en una máquina sin motor instalado.

Lo que sí se probó contra el motor real el 2026-08-19, y que es de donde salió ADR-0045:
con el default `crun` andan `exec`, `pause` y `unpause`; con `krun` andan `pause`/`unpause`
pero `exec` contesta `the handler does not support exec`. Montar un repo de Windows desde
`/mnt/c` funciona con los dos.
"""

import pytest

from jafne.nucleo import motor as motor_mod
from jafne.nucleo.motor import Motor, Salida
from jafne.nucleo.workspaces import (
    PREFIJO,
    Broker,
    Pedido,
    PedidoInvalido,
    WorkspaceRechazado,
    nombre_de,
    red_de,
)


class MotorFalso(Motor):
    """Un motor que anota lo que le pidieron y contesta lo que se le diga."""

    def __init__(self, runtimes=("crun", "krun"), fallar=(), vivos=(), **kwargs):
        super().__init__(podman="podman-de-mentira", **kwargs)
        self.guiones: list[str] = []
        self._runtimes = frozenset(runtimes)
        self._fallar = tuple(fallar)
        self._vivos = tuple(vivos)
        self._remoto = True

    def _en_el_motor(self, guion: str) -> Salida:
        self.guiones.append(guion)
        if any(marca in guion for marca in self._fallar):
            return Salida(1, "", "el motor dijo que no")
        if guion.startswith("podman wait"):
            return Salida(0, "0\n", "")
        if guion.startswith("podman logs"):
            return Salida(0, "lo que escribió la tarea\n", "")
        if guion.startswith("podman ps"):
            return Salida(0, "".join(f"{n}\n" for n in self._vivos), "")
        return Salida(0, "", "")

    def _correr(self, argumentos: list[str]) -> Salida:
        """Lo que consulta al cliente y no al motor: `info`, `--version`."""
        if argumentos[:1] == ["--version"]:
            return Salida(0, "podman de mentira 0.0", "")
        return Salida(0, "true", "")

    def runtimes(self):
        return self._runtimes


def _pedido(**kwargs) -> Pedido:
    base = {"proyecto": "borr", "asunto": "rediseno", "repo": "bff"}
    return Pedido(**{**base, **kwargs})


# ── el pedido ────────────────────────────────────────────────────────────────


def test_un_pedido_necesita_los_tres_niveles():
    """Proyecto, Asunto y repo (ADR-0047): los tres nombran al contenedor.

    Sin el nivel de repo, dos Agentes del mismo Asunto sobre repos distintos pedirían el
    mismo contenedor y se pisarían.
    """
    for campo in ("proyecto", "asunto", "repo"):
        with pytest.raises(PedidoInvalido):
            _pedido(**{campo: "../fuera"})


def test_un_proyecto_con_nombre_raro_se_rechaza():
    with pytest.raises(PedidoInvalido):
        _pedido(proyecto="../fuera")


def test_el_nombre_del_workspace_es_derivado_y_no_azaroso():
    # Pedir dos veces el mismo Workspace tiene que dar el mismo, y quien mire `podman ps`
    # tiene que poder decir de qué Asunto es sin preguntarle a JAFNE.
    assert nombre_de("borr", "rediseno", "bff") == f"{PREFIJO}borr-rediseno-bff"


def test_la_red_es_por_proyecto_no_por_workspace():
    # ADR-0011: dos Workspaces del mismo proyecto se ven; los de proyectos distintos no.
    assert red_de("borr") == red_de("borr") != red_de("otro")


# ── el ciclo de un Workspace persistente (ADR-0016) ──────────────────────────


def test_lanzar_prepara_la_red_del_proyecto():
    motor = MotorFalso()
    Broker(motor).lanzar(_pedido())
    assert any("network" in g and "jafne-borr" in g for g in motor.guiones)


def test_el_contenedor_corre_un_keep_alive_y_no_la_tarea():
    # ADR-0048: el proceso principal solo mantiene el contenedor en pie. Si corriera la
    # tarea, terminar la tarea mataría el lugar de trabajo del Agente.
    motor = MotorFalso()
    Broker(motor).lanzar(_pedido())
    assert "'sleep' 'infinity'" in motor.guiones[-1]


def test_no_se_pasa_runtime_al_motor():
    # ADR-0045: JAFNE dejó de elegir runtime. Pasarlo volvería a prometer un aislamiento
    # que ya no se está dando.
    motor = MotorFalso()
    Broker(motor).lanzar(_pedido())
    assert not any("--runtime" in g for g in motor.guiones)


def test_el_trabajo_del_agente_entra_por_exec():
    # Es **el** camino desde ADR-0045, y lo que reemplazó al par esperar/correr: con un
    # contenedor que persiste, esperar a que termine es esperar para siempre.
    motor = MotorFalso()
    resultado = Broker(motor).ejecutar("jafne-borr-x-bff", ("pytest", "-q"))
    assert resultado.codigo == 0
    assert any(g.startswith("podman exec") and "'pytest' '-q'" in g for g in motor.guiones)


def test_suspender_congela_sin_destruir():
    # `suspendido` de ADR-0016 tiene que dejar el Workspace en pie: se usa `pause`, que
    # congela los procesos con la memoria intacta, y nunca `stop`, que los mata.
    motor = MotorFalso()
    assert Broker(motor).suspender("jafne-borr-uno")
    assert any(g.startswith("podman pause") for g in motor.guiones)
    assert not any(g.startswith("podman stop") for g in motor.guiones)
    assert not any(g.startswith("podman rm") for g in motor.guiones)


def test_reanudar_devuelve_el_workspace_a_activo():
    # La vuelta de `suspendido` a `activo`, que es la transición que ADR-0016 permite.
    motor = MotorFalso()
    assert Broker(motor).reanudar("jafne-borr-uno")
    assert any(g.startswith("podman unpause") for g in motor.guiones)


def test_el_registro_trae_la_salida_del_proceso_principal():
    motor = MotorFalso()
    assert "lo que escribió la tarea" in Broker(motor).registro("jafne-borr-uno")


def test_un_pedido_repetido_no_apila_contenedores():
    motor = MotorFalso()
    Broker(motor).lanzar(_pedido(asunto="uno"))
    assert any(g.startswith("podman rm") for g in motor.guiones)


def test_si_el_motor_falla_al_lanzar_se_dice_con_el_nombre():
    motor = MotorFalso(fallar=("podman run",))
    with pytest.raises(WorkspaceRechazado) as error:
        Broker(motor).lanzar(_pedido())
    assert "jafne-borr-rediseno-bff" in str(error.value)


def test_si_la_red_no_se_puede_preparar_no_se_lanza_nada():
    motor = MotorFalso(fallar=("network",))
    with pytest.raises(WorkspaceRechazado):
        Broker(motor).lanzar(_pedido())
    assert not any(g.startswith("podman run") for g in motor.guiones)


# ── el motor ─────────────────────────────────────────────────────────────────


def test_sin_podman_el_estado_lo_dice_en_vez_de_reventar():
    motor = Motor(podman=None)
    motor._podman = None
    estado = Broker(motor).estado()
    if estado["motor"] is None:  # la máquina que corre la suite no tiene Podman
        assert estado["encendido"] is False
        assert "ADR-0012" in estado["detalle"]


def test_el_citado_es_del_shell_de_destino_no_del_de_origen():
    """El motor siempre es un `sh` de Linux, aunque JAFNE corra en Windows.

    Usar el `shlex.quote` de la plataforma que corre JAFNE citaría con reglas de `cmd` y
    del otro lado llegaría cualquier cosa.
    """
    assert motor_mod._citar("con espacio") == "'con espacio'"
    assert motor_mod._citar("com'illa") == "'com'\\''illa'"


def test_los_runtimes_salen_de_los_binarios_que_hay():
    # Se le pregunta al motor por los binarios y no por su configuración: un runtime
    # declarado pero no instalado haría que el Broker prometa un aislamiento inexistente.
    class ConRutas(MotorFalso):
        def _en_el_motor(self, guion):
            return Salida(0, "/usr/bin/crun\n/usr/bin/krun\n", "")

        def runtimes(self):
            return Motor.runtimes(self)

    assert ConRutas().runtimes() == frozenset({"crun", "krun"})


# ── la imagen que declara el repo (ADR-0048) ─────────────────────────────────


def test_se_construye_la_imagen_del_dockerfile_dev_del_repo(tmp_path):
    # ADR-0048: la imagen la declara el repo, JAFNE la construye. El contexto es la raíz
    # del repo para que el Dockerfile pueda copiar archivos suyos.
    (tmp_path / "Dockerfile.dev").write_text("FROM alpine\n", encoding="utf-8")
    motor = MotorFalso()
    etiqueta = Broker(motor).construir(_pedido(), str(tmp_path))
    assert etiqueta == "jafne-borr-bff:dev"
    assert any(g.startswith("podman build") and "Dockerfile.dev" in g for g in motor.guiones)


def test_un_repo_sin_dockerfile_dev_no_falla_todavia(tmp_path):
    # Hoy ningún repo tiene uno: ADR-0049 le dio al Encargado la tarea de sembrarlo, y
    # hasta que eso corra el Broker cae a la imagen por defecto en vez de romper.
    motor = MotorFalso()
    assert Broker(motor).construir(_pedido(), str(tmp_path)) is None
    assert not any(g.startswith("podman build") for g in motor.guiones)


def test_si_la_imagen_no_construye_se_dice_citando_el_archivo(tmp_path):
    (tmp_path / "Dockerfile.dev").write_text("FROM no-existe\n", encoding="utf-8")
    motor = MotorFalso(fallar=("podman build",))
    with pytest.raises(WorkspaceRechazado) as error:
        Broker(motor).construir(_pedido(), str(tmp_path))
    assert "Dockerfile.dev" in str(error.value)


# ── el disparador: delegar le da su contenedor al Agente (ADR-0047) ──────────


def test_delegar_construye_y_lanza_en_un_solo_paso(tmp_path):
    # Al delegar por primera vez a un repo hay que tener su imagen, y tenerla es haberla
    # construido: son un solo acto y no dos llamadas que alguien pueda olvidar de ordenar.
    (tmp_path / "Dockerfile.dev").write_text("FROM node:22\n", encoding="utf-8")
    motor = MotorFalso()
    workspace = Broker(motor).delegar(_pedido(), str(tmp_path))
    assert workspace.imagen == "jafne-borr-bff:dev"
    guiones = " | ".join(motor.guiones)
    assert "podman build" in guiones and "podman run" in guiones


def test_al_delegar_el_repo_se_monta_adentro(tmp_path):
    # El Agente trabaja sobre el repo de verdad, no sobre una copia: lo que escriba tiene
    # que quedar en el disco del Usuario para que se vea como diff (ADR-0049).
    motor = MotorFalso()
    Broker(motor).delegar(_pedido(), str(tmp_path))
    assert f"{tmp_path}:/repos/bff" in motor.guiones[-1]


def test_un_repo_sin_dockerfile_dev_se_delega_igual_con_la_imagen_por_defecto(tmp_path):
    # No se bloquea: hoy ningún repo declara entorno, y ADR-0049 puso al Encargado a
    # sembrarlo. Quien avisa que falta es el que llama, mirando la imagen que salió.
    from jafne.nucleo.workspaces import IMAGEN_POR_DEFECTO

    motor = MotorFalso()
    workspace = Broker(motor).delegar(_pedido(), str(tmp_path))
    assert workspace.imagen == IMAGEN_POR_DEFECTO
