"""CLI de JAFNE.

Es la boca del **núcleo**, no del panel: las operaciones que escriben estado las corren
el Encargado y el Workspace Broker (ADR-0008), no la UI. El panel se levanta desde acá
(`jafne panel`) pero solo lee.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__, pendientes
from .nucleo import Almacen, EstadoAsunto, EstadoContenedor, Veredicto
from .nucleo.almacen import (
    AlmacenNoInicializado,
    AsuntoDesconocido,
    IdInvalido,
    ProyectoDesconocido,
    SaldoInvalido,
    SinCerebroParaElRol,
)
from .nucleo.roles import Rol, tamano_por_defecto
from .nucleo import credenciales, senal_saldo
from .nucleo.despertares import CadenciaInvalida, TrabajoInvalido
from .nucleo.estados import EstadoDesconocido, TransicionInvalida
from .nucleo.modelos import a_utc
from .panel import ConfiguracionInsegura
from .reloj import Reloj, RelojYaCorriendo, candado
from .pendientes import DecisionPendiente

MARCAS = {Veredicto.OK: "[ok]", Veredicto.FALLA: "[FALLA]", Veredicto.NO_APLICA: "[n/a]"}


def _almacen(args: argparse.Namespace) -> Almacen:
    return Almacen(getattr(args, "home", None))


def _cmd_init(args: argparse.Namespace) -> int:
    ruta = _almacen(args).inicializar()
    print(f"Almacén listo en {ruta}")
    print("  proyectos.yaml  registro de proyectos (ADR-0007)")
    print("  cerebros.yaml   proveedores y tamaños disponibles (ADR-0003, ADR-0030)")
    print("  saldo.yaml      saldo observado por proveedor (ADR-0025)")
    print("  programado.yaml cadencias del trabajo programado (ADR-0024, ADR-0035)")
    print("  asuntos/        estado, cierre e historial de los Asuntos (ADR-0018)")
    return 0


def _cmd_proyectos(args: argparse.Namespace) -> int:
    almacen = _almacen(args)
    proyectos = almacen.proyectos()
    if not proyectos:
        print(f"Sin proyectos registrados en {almacen.ruta_proyectos}.")
        return 0
    for proyecto in proyectos:
        abiertos = sum(1 for a in almacen.asuntos(proyecto.id) if a.abierto)
        print(f"{proyecto.id:<20} {proyecto.nombre}")
        print(f"{'':<20} encargado: {proyecto.encargado or '(sin declarar)'}")
        print(f"{'':<20} asuntos abiertos: {abiertos}")
    return 0


def _cmd_asuntos(args: argparse.Namespace) -> int:
    asuntos = _almacen(args).asuntos(args.proyecto)
    if not asuntos:
        print("Sin Asuntos.")
        return 0
    for asunto in asuntos:
        efectivo = asunto.estado_efectivo
        marca = " (por timeout)" if efectivo is not asunto.estado_asunto else ""
        print(f"{asunto.proyecto}/{asunto.id}")
        print(f"  estado_asunto     {efectivo.value}{marca}")
        contenedor = asunto.estado_contenedor
        print(f"  estado_contenedor {contenedor.value if contenedor else '(nunca tuvo)'}")
        print(f"  mensajes          {asunto.mensajes}")
        if asunto.pregunta_pendiente:
            print("  pregunta_pendiente si")
        if asunto.motivo:
            print(f"  motivo            {asunto.motivo}")
    return 0


def _cmd_abrir(args: argparse.Namespace) -> int:
    asunto = _almacen(args).abrir_asunto(
        args.proyecto,
        args.asunto,
        titulo=args.titulo,
        rama=args.rama,
        repos=tuple(args.repo or ()),
    )
    print(f"Asunto abierto: {asunto.proyecto}/{asunto.id} [{asunto.estado_asunto.value}]")
    print(
        "Nota: solo se registró el Asunto. Crear su contenedor/workspace (ADR-0006) "
        "está pendiente -- ver `jafne pendientes`, clave 'workspace-broker'."
    )
    return 0


def _cmd_estado(args: argparse.Namespace) -> int:
    asunto = _almacen(args).actualizar_estado(
        args.proyecto, args.asunto, args.nuevo, motivo=args.motivo
    )
    print(f"{asunto.proyecto}/{asunto.id} ahora en '{asunto.estado_asunto.value}'.")
    return 0


def _cmd_contenedor(args: argparse.Namespace) -> int:
    asunto = _almacen(args).actualizar_contenedor(args.proyecto, args.asunto, args.estado)
    contenedor = asunto.estado_contenedor
    print(
        f"{asunto.proyecto}/{asunto.id}: estado_contenedor = "
        f"{contenedor.value if contenedor else '(nunca tuvo)'}"
    )
    return 0


def _cmd_pregunta(args: argparse.Namespace) -> int:
    pendiente = args.valor == "si"
    asunto = _almacen(args).marcar_pregunta(args.proyecto, args.asunto, pendiente)
    estado = "hay una pregunta pendiente" if pendiente else "sin pregunta pendiente"
    print(f"{asunto.proyecto}/{asunto.id}: {estado}.")
    if pendiente:
        print("El timeout de 3 minutos (ADR-0009/ADR-0017) ahora aplica a este Asunto.")
    return 0


def _cmd_anotar(args: argparse.Namespace) -> int:
    mensaje = _almacen(args).anotar(args.proyecto, args.asunto, args.rol, args.texto)
    print(f"Anotado [{mensaje.rol}] en {args.proyecto}/{args.asunto}.")
    return 0


def _cmd_historial(args: argparse.Namespace) -> int:
    almacen = _almacen(args)
    almacen.asunto(args.proyecto, args.asunto)
    mensajes = almacen.historial(args.proyecto, args.asunto)
    if not mensajes:
        print("Historial vacío.")
        return 0
    for mensaje in mensajes:
        print(f"[{mensaje.momento.isoformat()}] {mensaje.rol}: {mensaje.texto}")
    return 0


def _cmd_reabrir(args: argparse.Namespace) -> int:
    asunto = _almacen(args).reabrir_asunto(args.proyecto, args.asunto)
    print(f"{asunto.proyecto}/{asunto.id} reabierto en '{asunto.estado_asunto.value}'.")
    print(f"Contexto conservado: {asunto.mensajes} mensajes de historial y su cierre.md.")
    print(
        "El contenedor no se resucita (ADR-0018): hace falta pedir un Workspace nuevo, "
        "que sigue pendiente ('workspace-broker')."
    )
    return 0


def _cmd_cerrar(args: argparse.Namespace) -> int:
    resumen = args.resumen
    if args.resumen_archivo:
        resumen = args.resumen_archivo.read_text(encoding="utf-8")
    asunto, resultado = _almacen(args).cerrar_asunto(args.proyecto, args.asunto, resumen)

    for validacion in resultado.validaciones:
        marca = MARCAS[validacion.veredicto]
        print(f"{marca:<8} {validacion.numero}. {validacion.nombre}: {validacion.detalle}")
    print()
    if resultado.paso:
        print(f"{asunto.proyecto}/{asunto.id} cerrado.")
        return 0
    print(f"Cierre bloqueado. El Asunto volvió a '{asunto.estado_asunto.value}'.")
    print(f"Causa: {resultado.motivo}")
    return 1


def _cmd_saldo(args: argparse.Namespace) -> int:
    almacen = _almacen(args)
    if args.proveedor is None:
        suscripciones = almacen.suscripciones()
        if not suscripciones:
            print(f"Sin saldo observado en {almacen.ruta_saldo}.")
            print(
                "Se carga con `jafne saldo <proveedor> <ventana> <restante>`. Automatizar "
                "la lectura está pendiente -- clave 'medicion-de-consumo'."
            )
            return 0
        for suscripcion in suscripciones.values():
            print(f"{suscripcion.proveedor}{' ' + suscripcion.plan if suscripcion.plan else ''}")
            for ventana in suscripcion.ventanas:
                queda = "?" if ventana.restante is None else f"{ventana.restante:.0%}"
                reset = ventana.resetea.isoformat() if ventana.resetea else "sin reset conocido"
                marca = "  [AGOTADA]" if ventana.agotada else ""
                print(f"  {ventana.nombre:<10} queda {queda:>5}   resetea {reset}{marca}")
            if suscripcion.observado:
                print(f"  observado {suscripcion.observado.isoformat()}", end="")
                print(f" ({suscripcion.fuente})" if suscripcion.fuente else "")
        return 0

    if args.ventana is None or args.restante is None:
        print(
            "Error: registrar saldo pide proveedor, ventana y restante. Ej: "
            "`jafne saldo anthropic 5h 0.42`.",
            file=sys.stderr,
        )
        return 2

    resetea = None
    if args.resetea:
        resetea = a_utc(args.resetea)
        if resetea is None:
            print(f"Error: '{args.resetea}' no es una fecha ISO 8601.", file=sys.stderr)
            return 2

    suscripcion = almacen.registrar_saldo(
        args.proveedor,
        args.ventana,
        args.restante,
        resetea=resetea,
        plan=args.plan,
        fuente=args.fuente,
    )
    print(f"{suscripcion.proveedor}/{args.ventana}: queda {args.restante:.0%}.")
    if suscripcion.agotado:
        print("Alguna ventana quedó en cero: por ahí no entra ninguna llamada.")
    return 0


def _cmd_cerebros(args: argparse.Namespace) -> int:
    """Los cerebros declarados, su tamaño y qué dice el saldo de cada proveedor.

    Junta en una vista las tres decisiones que se cruzan al elegir cerebro: el tamaño
    común de ADR-0030, si hay adaptador (ADR-0028) y la señal de saldo de ADR-0026.
    """
    cerebros = _almacen(args).cerebros()
    if not cerebros:
        print("No hay cerebros declarados en cerebros.yaml.")
        return 0

    ancho = max(len(c.id) for c in cerebros)
    for cerebro in cerebros:
        tamano = cerebro.tamano.value if cerebro.tamano else "?"
        marca = "" if cerebro.adaptador else "   (sin adaptador — ADR-0028)"
        print(
            f"{cerebro.id:<{ancho}}  {cerebro.proveedor:<10} {tamano:<8} "
            f"{cerebro.modelo or '-'}{marca}"
        )

    # Qué cerebro le toca a cada rol (ADR-0033). Es lo que un agente consulta para saber
    # sobre qué modelo está corriendo, en vez de suponerlo.
    print()
    almacen = _almacen(args)
    for rol in Rol:
        tamano = tamano_por_defecto(rol)
        if tamano is None:
            print(f"{rol.value}: lo elige el Encargado por tarea (ADR-0003)")
            continue
        try:
            cerebro = almacen.cerebro_de(rol)
        except SinCerebroParaElRol as error:
            print(f"{rol.value}: SIN CEREBRO — {error}")
            continue
        print(f"{rol.value}: {cerebro.id} ({tamano.value}, {cerebro.modelo})")

    # El saldo es del proveedor, no del cerebro (ADR-0025), así que la señal va aparte.
    print()
    saldos = {c.proveedor: c.saldo for c in cerebros}
    for proveedor in sorted(saldos):
        decision = senal_saldo.evaluar(saldos[proveedor])
        print(f"{proveedor}: {decision.senal.value} — {decision.motivo}")
        if decision.reanudar:
            print(f"  reanudar el {decision.reanudar.isoformat()}")
    return 0


def _cmd_credencial(args: argparse.Namespace) -> int:
    """Con qué credencial va a hablar JAFNE (ADR-0034).

    JAFNE no tiene login propio: la sesión es de Claude Code. Esto mira y reporta.
    """
    estado = credenciales.estado()
    falta_config = "" if estado.config_presente else "  (no existe)"
    print(f"CLI de Claude Code: {estado.ruta_cli or 'NO ENCONTRADA'}")
    print(f"Config de sesión:   {estado.ruta_config}{falta_config}")
    print(f"Listo para usarse:  {'sí' if estado.listo else 'no'}")
    for aviso in estado.avisos:
        print(f"\nAVISO: {aviso}")
    if estado.sugerencia:
        print(f"\n{estado.sugerencia}")
    if estado.listo:
        print("\nNo hay nada que iniciar en JAFNE: la sesión la maneja Claude Code.")
    return 0 if estado.listo else 1


def _cmd_pendientes(args: argparse.Namespace) -> int:
    for pendiente in pendientes.todos():
        print(f"{pendiente.clave}")
        print(f"  {pendiente.titulo}")
        print(f"  bloqueado por: {pendiente.bloqueado_por}")
        print(f"  {pendiente.pregunta}")
        print()
    return 0


def _cmd_reloj(args: argparse.Namespace) -> int:
    """El reloj del trabajo programado, en su propio proceso (ADR-0035).

    Separado del panel a propósito: el trabajo programado no depende de que el dashboard
    esté abierto, y el panel no escribe estado. `--ver` es la mitad de solo lectura —
    muestra la cola sin disparar nada— y es lo que el panel puede hacer también.
    """
    almacen = _almacen(args)
    reloj = Reloj(almacen)

    if args.ver:
        pendientes = reloj.cola()
        if not pendientes:
            print(f"Nada agendado en {almacen.ruta_programado}.")
            print("Se declara con: <id>: {skill, cadencia, proyecto} (ADR-0024).")
            return 0
        for despertar in pendientes:
            print(f"{despertar.momento.isoformat()}  [{despertar.origen.value}]")
            print(f"  {despertar.motivo}")
        return 0

    print(f"Reloj de JAFNE sobre {almacen.ruta}")
    trabajos = almacen.programados()
    print(f"Cadencias declaradas: {len(trabajos)} (ADR-0024, {almacen.ruta_programado})")
    if not trabajos:
        print("Sin cadencias: el reloj igual corre por los diferimientos de ADR-0026.")
    proximo = reloj.cola()
    print(
        f"Próximo despertar: {proximo[0].momento.isoformat()}"
        if proximo
        else "Próximo despertar: nada agendado todavía."
    )

    def informar(disparo) -> None:
        marca = "[ok]" if disparo.hecho else "[--]"
        print(f"{marca} {disparo.despertar.momento.isoformat()}  {disparo.detalle}")

    with candado(almacen):
        try:
            reloj.correr(vueltas=args.vueltas, informar=informar)
        except KeyboardInterrupt:
            print("\nReloj detenido. Sin él no hay trabajo programado (ADR-0035).")
    return 0


def _cmd_voz(args: argparse.Namespace) -> int:
    """Levanta el nodo de voz: presta esta máquina para transcribir (ADR-0037).

    Va en la máquina que tiene la GPU. No lee `~/.jafne/` ni sabe de Asuntos: presta
    cómputo, nada más.
    """
    from . import voz as nodo_voz
    from .nucleo import transcripcion

    estado = transcripcion.estado()
    print(f"Nodo de voz de JAFNE en http://{args.host}:{args.puerto}")
    print(f"  modelo      {estado.modelo}")
    print(f"  dispositivo {estado.dispositivo} ({estado.computo})")
    if not estado.disponible:
        print(f"\nNo puede transcribir: {estado.detalle}", file=sys.stderr)
        return 2
    if estado.dispositivo != "cuda":
        print(
            "\nAviso: está por transcribir en CPU. Si esta máquina tiene GPU NVIDIA, "
            "falta CUDA/cuDNN para que CTranslate2 la vea."
        )
    print(
        f"\nDel lado del panel: JAFNE_VOZ_NODO=http://{args.host}:{args.puerto}"
        + ("  JAFNE_VOZ_TOKEN=…" if args.token else "")
    )
    nodo_voz.servir(host=args.host, puerto=args.puerto, token=args.token)
    return 0


def _cmd_panel(args: argparse.Namespace) -> int:
    from .panel import servir

    print(f"Panel de JAFNE en http://{args.host}:{args.puerto}")
    servir(
        host=args.host,
        puerto=args.puerto,
        ruta_almacen=getattr(args, "home", None),
        token=args.token,
    )
    return 0


def construir_parser() -> argparse.ArgumentParser:
    from pathlib import Path

    parser = argparse.ArgumentParser(
        prog="jafne",
        description="JAFNE -- nucleo y panel web. Ver docs/ para el diseño.",
    )
    parser.add_argument("--version", action="version", version=f"jafne {__version__}")
    parser.add_argument(
        "--home",
        metavar="RUTA",
        help="Almacén a usar en vez de ~/.jafne (también respeta $JAFNE_HOME).",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("init", help="Crea el esqueleto de ~/.jafne/.").set_defaults(
        func=_cmd_init
    )
    sub.add_parser("proyectos", help="Lista los proyectos conocidos.").set_defaults(
        func=_cmd_proyectos
    )

    p_asuntos = sub.add_parser("asuntos", help="Lista Asuntos y su estado.")
    p_asuntos.add_argument("--proyecto", help="Filtra por proyecto.")
    p_asuntos.set_defaults(func=_cmd_asuntos)

    p_abrir = sub.add_parser("abrir", help="Registra un Asunto nuevo en 'iniciando'.")
    p_abrir.add_argument("proyecto")
    p_abrir.add_argument("asunto", help="Id del Asunto (kebab-case).")
    p_abrir.add_argument("--titulo")
    p_abrir.add_argument("--rama")
    p_abrir.add_argument(
        "--repo",
        action="append",
        help="Repo que toca el Asunto; repetible. Sin esto el cierre no tiene "
        "dónde verificar git (ADR-0019).",
    )
    p_abrir.set_defaults(func=_cmd_abrir)

    p_estado = sub.add_parser("estado", help="Mueve el estado_asunto (ADR-0009).")
    p_estado.add_argument("proyecto")
    p_estado.add_argument("asunto")
    p_estado.add_argument("nuevo", choices=[e.value for e in EstadoAsunto])
    p_estado.add_argument("--motivo")
    p_estado.set_defaults(func=_cmd_estado)

    p_cont = sub.add_parser(
        "contenedor", help="Mueve el estado_contenedor (Infraestructura, ADR-0016)."
    )
    p_cont.add_argument("proyecto")
    p_cont.add_argument("asunto")
    p_cont.add_argument("estado", choices=[e.value for e in EstadoContenedor])
    p_cont.set_defaults(func=_cmd_contenedor)

    p_preg = sub.add_parser(
        "pregunta", help="Sube o baja pregunta_pendiente (ADR-0017)."
    )
    p_preg.add_argument("proyecto")
    p_preg.add_argument("asunto")
    p_preg.add_argument("valor", choices=["si", "no"])
    p_preg.set_defaults(func=_cmd_pregunta)

    p_anotar = sub.add_parser("anotar", help="Agrega un mensaje al historial (ADR-0018).")
    p_anotar.add_argument("proyecto")
    p_anotar.add_argument("asunto")
    p_anotar.add_argument("rol", help="usuario, asistente, encargado, agente, sistema…")
    p_anotar.add_argument("texto")
    p_anotar.set_defaults(func=_cmd_anotar)

    p_hist = sub.add_parser("historial", help="Muestra la conversación del Asunto.")
    p_hist.add_argument("proyecto")
    p_hist.add_argument("asunto")
    p_hist.set_defaults(func=_cmd_historial)

    p_reabrir = sub.add_parser(
        "reabrir", help="Reabre un Asunto cerrado con su contexto (ADR-0018)."
    )
    p_reabrir.add_argument("proyecto")
    p_reabrir.add_argument("asunto")
    p_reabrir.set_defaults(func=_cmd_reabrir)

    p_cerrar = sub.add_parser(
        "cerrar", help="Corre la skill de cierre: 5 validaciones (ADR-0019)."
    )
    p_cerrar.add_argument("proyecto")
    p_cerrar.add_argument("asunto")
    grupo = p_cerrar.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--resumen", help="Resumen de cierre, en línea.")
    grupo.add_argument(
        "--resumen-archivo", type=Path, help="Archivo con el resumen de cierre."
    )
    p_cerrar.set_defaults(func=_cmd_cerrar)

    p_saldo = sub.add_parser(
        "saldo",
        help="Muestra o registra el saldo de una suscripción (Infraestructura, ADR-0025).",
        description="Sin argumentos muestra el saldo observado. Con ellos lo registra: "
        "es la escritura de Infraestructura, el análogo de `jafne contenedor` para el "
        "otro eje que gestiona.",
    )
    p_saldo.add_argument("proveedor", nargs="?", help="anthropic, openai…")
    p_saldo.add_argument(
        "ventana", nargs="?", help="Nombre de la ventana del proveedor: 5h, semanal…"
    )
    p_saldo.add_argument(
        "restante",
        nargs="?",
        type=float,
        help="Fracción que queda de esa ventana, de 0 (agotada) a 1 (intacta).",
    )
    p_saldo.add_argument("--resetea", help="Cuándo se llena de nuevo, en ISO 8601.")
    p_saldo.add_argument("--plan", help="Nombre del plan contratado: pro, max…")
    p_saldo.add_argument("--fuente", help="De dónde salió el dato. Ej: 'claude-code /usage'.")
    p_saldo.set_defaults(func=_cmd_saldo)

    sub.add_parser(
        "cerebros",
        help="Lista los cerebros con su tamaño y la señal de saldo (ADR-0026, ADR-0030).",
    ).set_defaults(func=_cmd_cerebros)

    sub.add_parser(
        "credencial",
        help="Con qué credencial habla JAFNE con el proveedor (ADR-0034).",
    ).set_defaults(func=_cmd_credencial)

    sub.add_parser(
        "pendientes", help="Lista las decisiones abiertas que bloquean funcionalidad."
    ).set_defaults(func=_cmd_pendientes)

    p_reloj = sub.add_parser(
        "reloj",
        help="Corre el reloj del trabajo programado, en su propio proceso (ADR-0035).",
        description="El proceso de larga vida que consume la cola de despertares: las "
        "cadencias de programado.yaml (ADR-0024) y los diferimientos por cupo (ADR-0026). "
        "Es independiente del panel a propósito — si el reloj no corre, no hay trabajo "
        "programado.",
    )
    p_reloj.add_argument(
        "--ver",
        action="store_true",
        help="Muestra la cola de despertares y sale, sin disparar ni tomar el candado.",
    )
    p_reloj.add_argument(
        "--vueltas",
        type=int,
        help="Corta después de N vueltas del bucle, en vez de quedarse corriendo.",
    )
    p_reloj.set_defaults(func=_cmd_reloj)

    p_voz = sub.add_parser(
        "voz",
        help="Presta esta máquina a la malla para transcribir (ADR-0037).",
        description="Levanta el nodo de voz en la máquina que tiene la GPU. El panel le "
        "delega el dictado declarando $JAFNE_VOZ_NODO. No lee ~/.jafne/ ni escribe "
        "estado: presta cómputo.",
    )
    p_voz.add_argument(
        "--host",
        default="127.0.0.1",
        help="Loopback, o la IP de la interfaz ZeroTier. Nunca 0.0.0.0 (ADR-0020).",
    )
    p_voz.add_argument("--puerto", type=int, default=8731)
    p_voz.add_argument(
        "--token",
        help="Token compartido; obligatorio fuera de loopback. También $JAFNE_VOZ_TOKEN.",
    )
    p_voz.set_defaults(func=_cmd_voz)

    p_panel = sub.add_parser("panel", help="Levanta el panel web (ADR-0013, ADR-0020).")
    p_panel.add_argument(
        "--host",
        default="127.0.0.1",
        help="Loopback, o la IP de la interfaz ZeroTier. Nunca 0.0.0.0 (ADR-0020).",
    )
    p_panel.add_argument("--puerto", type=int, default=8730)
    p_panel.add_argument(
        "--token",
        help="Token compartido; obligatorio fuera de loopback. También $JAFNE_PANEL_TOKEN.",
    )
    p_panel.set_defaults(func=_cmd_panel)

    return parser


def _salida_en_utf8() -> None:
    """Fuerza UTF-8 en la salida.

    La consola de Windows usa cp1252 por defecto, donde no existen `→`, `≤` ni varios
    caracteres que la documentación de JAFNE usa a diario: sin esto, `jafne pendientes`
    revienta con `UnicodeEncodeError` al imprimir el título del hop 4. Se degrada a
    reemplazo antes que a excepción — que un carácter salga feo es aceptable, que un
    comando se caiga no.
    """
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is not None:
            reconfigurar(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _salida_en_utf8()
    args = construir_parser().parse_args(argv)
    try:
        return args.func(args)
    except DecisionPendiente as error:
        print(f"Falta decidir: {error}", file=sys.stderr)
        print(f"(clave: {error.pendiente.clave})", file=sys.stderr)
        return 3
    except (
        AlmacenNoInicializado,
        AsuntoDesconocido,
        ProyectoDesconocido,
        IdInvalido,
        EstadoDesconocido,
        TransicionInvalida,
        SaldoInvalido,
        ConfiguracionInsegura,
        CadenciaInvalida,
        TrabajoInvalido,
        RelojYaCorriendo,
        FileExistsError,
    ) as error:
        mensaje = error.args[0] if error.args else str(error)
        print(f"Error: {mensaje}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
