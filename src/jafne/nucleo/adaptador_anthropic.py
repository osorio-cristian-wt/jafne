"""El adaptador de Anthropic: maneja la CLI de Claude Code (ADR-0028, ADR-0031, ADR-0034).

Es el primer adaptador real, y llega con todo decidido de antemano — que era el punto de
haber congelado el contrato antes (ADR-0028): si se hubiera escrito al revés, este archivo
*sería* el contrato y el agnosticismo de ADR-0003 no tendría respaldo.

Las cuatro operaciones de `AdaptadorSesion` se apoyan en la CLI, no en el SDK, tal como
fijó ADR-0034:

| Contrato | Cómo |
|---|---|
| `abrir` | Se **inventa** el id (UUID) y se lo pasa a la CLI con `--session-id` |
| `reanudar` | `--resume <id>`: la sesión la rehidrata el proveedor, no JAFNE |
| `emitir` | `-p <mensaje> --output-format json` |
| `saldo` | `None` — ver abajo, y no es un hueco |

**JAFNE no maneja credenciales** (ADR-0034): se invoca la CLI y esta usa la sesión que el
Usuario ya inició. Acá no se lee, ni se pasa, ni se registra ningún secreto.

Dos decisiones que conviene leer antes de tocar esto:

- **`abrir` no llama a la CLI.** El id se genera de este lado y se le impone al proveedor
  con `--session-id`. La alternativa era mandar un turno de mentira solo para que el
  proveedor devolviera un id, o sea cobrarle al Usuario por abrir una conversación vacía.
- **`saldo()` devuelve `None`, y es lo correcto.** La CLI informa `total_cost_usd` del
  turno, que es **gasto**; ADR-0025 fijó que la métrica es el **saldo** —cuánto queda—, que
  es otra cosa. Derivar uno del otro sería inventar el dato que `medicion-de-consumo`
  todavía tiene abierto, y el contrato ya dice que `None` no significa cero.

Un tercer parámetro opcional, `rol`, agrega la identidad del rol al system prompt de la
CLI vía `--append-system-prompt-file` (ADR-0040): quién es, hasta dónde llega y que las
decisiones son del Usuario. Se **agrega**, nunca reemplaza — el agente conserva todo lo
que Claude Code ya sabe de sí mismo. Los textos viven en `nucleo/prompts/`, versionados,
uno por rol; hoy solo existe el del Asistente.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from collections.abc import Iterator

from . import credenciales, mcp, prompts
from .modelos import Suscripcion
from .roles import Rol
from .sesion import Evento, TipoEvento
from .tamanos import Tamano

#: Cuánto esperar a un turno antes de cortarlo. Generoso: del otro lado hay un modelo
#: pensando, y cortar a mitad pierde el turno entero sin devolver nada útil.
ESPERA_TURNO = 600

#: Hasta dónde puede llegar el agente con sus herramientas (ADR-0039).
#:
#: El Usuario decidió el 2026-08-19 que el chat **sí** usa herramientas —el dashboard
#: existe justamente para acceder al agente— y que el borde es su carpeta de repos. Fuera
#: de acá el proveedor deniega la operación: verificado contra la CLI real, un `Read` a un
#: archivo de afuera cae en `permission_denials` y el turno termina pidiendo permiso en vez
#: de colgarse.
RAIZ_TRABAJO_POR_DEFECTO = "C:/Repos"

VARIABLE_RAIZ_TRABAJO = "JAFNE_RAIZ_TRABAJO"

#: Cómo se resuelven los permisos dentro de esa raíz.
#:
#: `acceptEdits` y no `bypassPermissions`: con bypass no habría borde ninguno —el agente
#: podría tocar cualquier cosa del disco— y el límite que el Usuario pidió dejaría de
#: existir. Tampoco sirve pedir permiso de verdad: desde una página web no hay forma de
#: contestar a mitad de un turno.
MODO_PERMISOS = "acceptEdits"


def raiz_de_trabajo() -> str:
    """Hasta dónde llega el agente con sus herramientas (ADR-0039)."""
    return os.environ.get(VARIABLE_RAIZ_TRABAJO) or RAIZ_TRABAJO_POR_DEFECTO


class ErrorDelProveedor(RuntimeError):
    """La CLI falló, o devolvió algo que no se puede interpretar."""


class AdaptadorAnthropic:
    """Implementa `AdaptadorSesion` sobre la CLI de Claude Code.

    Es de un solo hilo y de una sola sesión: guarda la sesión activa y la usa para los
    turnos siguientes. Multiplexar observadores sobre una misma sesión es trabajo de JAFNE
    (ADR-0031), no de este objeto.
    """

    proveedor = "anthropic"

    def __init__(
        self,
        modelo: str | None = None,
        cli: str | None = None,
        raiz_trabajo: str | None = None,
        espera: int = ESPERA_TURNO,
        rol: Rol | None = None,
        proyecto: str | None = None,
    ) -> None:
        self._modelo = modelo
        self._cli = cli
        self._raiz = raiz_trabajo or raiz_de_trabajo()
        self._espera = espera
        self._rol = rol
        self._proyecto = proyecto
        self._id_sesion: str | None = None
        self._directorio: str | None = None
        self._estrenada = False

    # ── contrato (ADR-0031) ───────────────────────────────────────────────────

    def abrir(self, directorio: str, tamano: Tamano) -> str:
        """Arranca una sesión nueva y devuelve su id, sin gastar un solo token."""
        self._id_sesion = str(uuid.uuid4())
        self._directorio = directorio
        self._estrenada = False
        return self._id_sesion

    def reanudar(self, id_sesion: str) -> None:
        """Vuelve a una sesión existente.

        No se reinyecta el historial: lo tiene el proveedor y lo rehidrata él con
        `--resume` (ADR-0018, ADR-0031). Por eso `reanudar` tampoco gasta nada — el
        contexto vuelve recién en el próximo turno.
        """
        self._id_sesion = id_sesion
        self._estrenada = True

    def emitir(self, mensaje: str) -> Iterator[Evento]:
        """Manda un turno y devuelve lo que produjo.

        Hoy el turno se resuelve entero antes de emitir el primer evento: la CLI también
        sabe `--output-format stream-json`, y pasar a streaming real **no cambia el
        contrato** —ya devuelve un iterador— sino solo este método. Se deja para cuando el
        panel sepa consumir un flujo, que hoy hace un POST y espera.
        """
        if not self._id_sesion:
            raise ErrorDelProveedor(
                "No hay sesión: hay que llamar a `abrir()` o `reanudar()` antes de emitir."
            )

        completado = self._correr(self._comando(mensaje))
        self._estrenada = True

        if completado.returncode != 0:
            yield Evento(
                tipo=TipoEvento.ERROR,
                texto=self._motivo(completado),
                datos={"codigo": completado.returncode},
            )
            return

        try:
            crudo = json.loads(completado.stdout)
        except (json.JSONDecodeError, TypeError) as error:
            yield Evento(
                tipo=TipoEvento.ERROR,
                texto=f"La CLI devolvió algo que no es JSON: {error}",
            )
            return

        if crudo.get("is_error"):
            yield Evento(
                tipo=TipoEvento.ERROR,
                texto=str(crudo.get("result") or crudo.get("subtype") or "turno fallido"),
                datos={"subtype": crudo.get("subtype")},
            )
            return

        # El proveedor manda su propio id: se adopta. Con `--session-id` coincide con el
        # que pusimos, pero con `--resume` puede cambiar —`--fork-session` es un caso— y
        # quedarse con el viejo dejaría la conversación colgada del turno siguiente.
        if crudo.get("session_id"):
            self._id_sesion = str(crudo["session_id"])

        texto = str(crudo.get("result") or "")
        if texto:
            yield Evento(tipo=TipoEvento.TEXTO, texto=texto)

        yield Evento(
            tipo=TipoEvento.RESULTADO,
            datos={
                "id_sesion": self._id_sesion,
                "costo_usd": crudo.get("total_cost_usd"),
                "turnos": crudo.get("num_turns"),
                "duracion_ms": crudo.get("duration_ms"),
                "modelo": self._modelo,
            },
        )

    def saldo(self) -> Suscripcion | None:
        """Lo que la CLI sabe decir del saldo: nada (ADR-0025).

        Informa el **gasto** del turno, no cuánto queda de la suscripción. Convertir uno en
        otro exigiría conocer el límite, que es justamente lo que `medicion-de-consumo`
        tiene abierto. `None` es la respuesta honesta, y el contrato la contempla.
        """
        return None

    # ── el subproceso ─────────────────────────────────────────────────────────

    @property
    def id_sesion(self) -> str | None:
        """El id de la sesión activa, que el Asunto guarda en su `meta.yaml` (ADR-0031)."""
        return self._id_sesion

    def _ejecutable(self) -> str:
        cli = self._cli or credenciales.ruta_cli()
        if not cli:
            raise ErrorDelProveedor(
                "No encuentro el ejecutable de Claude Code. Instalá la CLI o apuntá "
                f"${credenciales.VARIABLE_CLI} al binario (ADR-0034). `jafne credencial` "
                f"lo diagnostica."
            )
        return cli

    def _comando(self, mensaje: str) -> list[str]:
        """El comando exacto, con la sesión enganchada según sea el primer turno o no."""
        comando = [self._ejecutable(), "-p", mensaje, "--output-format", "json"]
        if self._estrenada:
            comando += ["--resume", str(self._id_sesion)]
        else:
            comando += ["--session-id", str(self._id_sesion)]
        if self._modelo:
            comando += ["--model", self._modelo]
        # Sin herramientas no hace falta pedir permisos, y sin permisos que pedir la CLI no
        # se queda esperando una respuesta interactiva que del otro lado no hay nadie para
        # dar (ADR-0024 ya había marcado ese problema para el trabajo programado).
        # El borde (ADR-0039). No se pasa `--allowed-tools`: el agente tiene las suyas, y
        # lo que lo acota es *dónde* puede usarlas, no cuáles. Fuera de la raíz el
        # proveedor deniega y el turno termina pidiendo permiso, que en el panel se ve
        # como una respuesta y no como un cuelgue.
        comando += ["--add-dir", self._raiz]
        comando += ["--permission-mode", MODO_PERMISOS]
        # Identidad de rol (ADR-0040): se agrega al system prompt de la CLI, nunca lo
        # reemplaza — el agente conserva todo lo que Claude Code ya sabe de sí mismo.
        if self._rol is not None:
            ruta_prompt = prompts.ruta_prompt(self._rol)
            if ruta_prompt is not None:
                comando += ["--append-system-prompt-file", str(ruta_prompt)]

            # El MCP de JAFNE, acotado al rol (ADR-0042). La URL la arma JAFNE, así que el
            # alcance no depende de lo que el agente diga de sí mismo.
            configuracion = mcp.configuracion(self._rol, self._proyecto)
            if configuracion:
                comando += ["--mcp-config", configuracion]
                # Sin esto el agente **ve** las herramientas y no las puede usar: la
                # llamada queda esperando una aprobación que desde el panel no hay quién
                # dar. Verificado contra la CLI real el 2026-08-19.
                comando += ["--allowed-tools", mcp.HERRAMIENTAS_PERMITIDAS]
        return comando

    def _correr(self, comando: list[str]) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                comando,
                cwd=self._directorio,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._espera,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ErrorDelProveedor(
                f"El turno pasó de {self._espera}s sin contestar y se cortó."
            ) from error
        except OSError as error:
            raise ErrorDelProveedor(f"No se pudo invocar la CLI: {error}") from error

    @staticmethod
    def _motivo(completado: subprocess.CompletedProcess) -> str:
        detalle = (completado.stderr or completado.stdout or "").strip()
        return detalle.splitlines()[-1] if detalle else "la CLI terminó con error"


def construir(
    modelo: str | None = None,
    raiz_trabajo: str | None = None,
    rol: Rol | None = None,
    proyecto: str | None = None,
) -> AdaptadorAnthropic:
    """Un adaptador listo para usar, con el modelo del cerebro que lo pidió."""
    return AdaptadorAnthropic(
        modelo=modelo, raiz_trabajo=raiz_trabajo, rol=rol, proyecto=proyecto
    )
