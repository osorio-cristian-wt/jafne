"""El registro de puertos publicados hacia la malla (ADR-0011).

ADR-0011 puso los puertos del lado de Infraestructura —*"el Workspace, vía Infraestructura,
es responsable de la red y los puertos, no el Agente ni el Encargado"*— pero no dijo cómo
se lleva la cuenta. Esto es ese cómo.

**Adentro de un proyecto no hace falta registro, y conviene entender por qué.** Cada
contenedor tiene su propia IP en la red de su proyecto, así que el back de un proyecto y el
back de otro pueden escuchar los dos en el 3000 sin enterarse. Se encuentran por **alias de
red** —el nombre del repo— y cada uno resuelve dentro de la suya. Verificado el 2026-08-19:
dos proyectos con un `back` cada uno resolvieron a IPs distintas, cada bff al suyo.

El choque aparece **solo al publicar hacia afuera**, porque la IP de la malla es una sola y
su espacio de puertos es compartido por todo el servidor. Eso es lo que se registra acá.

Es **programado y no agéntico** a propósito: elegir el primer puerto libre de un rango es
una cuenta, no un juicio. Un modelo decidiendo esto sería más caro, más lento y no más
correcto. Lo que sí es criterio —*qué servicio merece publicarse*— lo decide el Encargado,
y este módulo solo le da el número.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

#: El rango que JAFNE se reserva para publicar servicios de Workspaces.
#:
#: Alto y contiguo, para no pelearse con nada que el Usuario ya corra en la máquina. No es
#: una decisión de diseño: si choca con algo, se mueve.
RANGO = range(9000, 10000)

#: Dónde se anota. Junto al resto del estado de JAFNE (ADR-0007), y no en memoria: un
#: reinicio de Infraestructura no tiene que soltar puertos que siguen ocupados.
ARCHIVO = "puertos.json"


class SinPuertosLibres(RuntimeError):
    """El rango se llenó. Es un problema operativo, no de diseño."""


@dataclass(frozen=True)
class Publicacion:
    """Un puerto de la malla, asignado a un servicio de un contenedor."""

    puerto: int
    contenedor: str
    interno: int

    def a_dict(self) -> dict:
        return {"puerto": self.puerto, "contenedor": self.contenedor, "interno": self.interno}


class Registro:
    """Quién tiene qué puerto de la malla.

    Se guarda en disco y se relee en cada operación en vez de cachear: Infraestructura es
    un proceso largo, y una copia en memoria que se desincroniza del archivo daría dos
    verdades sobre el mismo puerto.
    """

    def __init__(self, raiz: Path | str) -> None:
        self._ruta = Path(raiz) / ARCHIVO

    def _leer(self) -> dict[str, dict]:
        if not self._ruta.is_file():
            return {}
        try:
            datos = json.loads(self._ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # Un archivo corrupto no puede dejar a Infraestructura sin poder publicar: se
            # empieza de cero. El costo es reasignar puertos, no perder trabajo.
            return {}
        return datos if isinstance(datos, dict) else {}

    def _escribir(self, datos: dict[str, dict]) -> None:
        self._ruta.parent.mkdir(parents=True, exist_ok=True)
        self._ruta.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def publicaciones(self) -> list[Publicacion]:
        """Todo lo publicado hoy, ordenado por puerto."""
        return sorted(
            (
                Publicacion(int(p), d["contenedor"], int(d["interno"]))
                for p, d in self._leer().items()
            ),
            key=lambda p: p.puerto,
        )

    def de(self, contenedor: str) -> list[Publicacion]:
        """Lo que tiene publicado ese contenedor."""
        return [p for p in self.publicaciones() if p.contenedor == contenedor]

    def reservar(self, contenedor: str, interno: int) -> Publicacion:
        """Le da a ese servicio un puerto libre de la malla, y lo anota.

        Es **idempotente por (contenedor, puerto interno)**: pedir dos veces lo mismo
        devuelve el mismo puerto. Sin eso, rearmar un contenedor le cambiaría el puerto y
        el link que el Usuario ya tenía dejaría de servir.
        """
        datos = self._leer()
        for puerto, d in datos.items():
            if d.get("contenedor") == contenedor and int(d.get("interno", 0)) == interno:
                return Publicacion(int(puerto), contenedor, interno)

        ocupados = {int(p) for p in datos}
        for candidato in RANGO:
            if candidato not in ocupados:
                datos[str(candidato)] = {"contenedor": contenedor, "interno": interno}
                self._escribir(datos)
                return Publicacion(candidato, contenedor, interno)

        raise SinPuertosLibres(
            f"No queda ningún puerto libre entre {RANGO.start} y {RANGO.stop - 1}. "
            f"Hay {len(ocupados)} publicaciones vivas; liberá alguna o ampliá el rango."
        )

    def liberar(self, contenedor: str) -> list[int]:
        """Suelta todo lo de ese contenedor. Devuelve qué puertos quedaron libres.

        Se llama al destruir: un puerto que queda reservado para un contenedor que ya no
        existe agota el rango de a poco, y el síntoma aparece mucho después de la causa.
        """
        datos = self._leer()
        sueltos = [int(p) for p, d in datos.items() if d.get("contenedor") == contenedor]
        if sueltos:
            for puerto in sueltos:
                datos.pop(str(puerto), None)
            self._escribir(datos)
        return sorted(sueltos)
