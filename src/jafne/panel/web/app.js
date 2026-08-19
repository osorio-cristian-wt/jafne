/* Panel de JAFNE (ADR-0013). JS plano, sin build ni framework (ADR-0015). */

const ETIQUETAS_ESTADO = {
  iniciando: "Iniciando",
  interactuando_con_el_usuario: "Interactuando",
  esperando_respuesta: "Esperando respuesta",
  cerrando: "Cerrando",
  cerrado: "Cerrado",
};

const vista = document.getElementById("vista");
const miga = document.getElementById("miga");

/* ── utilidades ─────────────────────────────────────────────────────────── */

function el(tag, props = {}, hijos = []) {
  const nodo = document.createElement(tag);
  for (const [clave, valor] of Object.entries(props)) {
    if (valor === null || valor === undefined) continue;
    if (clave === "clase") nodo.className = valor;
    else if (clave === "texto") nodo.textContent = valor;
    else if (clave.startsWith("on")) nodo.addEventListener(clave.slice(2), valor);
    else if (
      clave.startsWith("data-") ||
      clave === "title" ||
      clave === "hidden" ||
      clave === "style"
    )
      nodo.setAttribute(clave, valor);
    else nodo[clave] = valor;
  }
  for (const hijo of [].concat(hijos)) {
    if (hijo) nodo.append(hijo);
  }
  return nodo;
}

async function api(ruta, opciones) {
  try {
    const respuesta = await fetch(ruta, opciones);
    const datos = await respuesta.json().catch(() => null);
    return { ok: respuesta.ok, status: respuesta.status, datos };
  } catch (error) {
    return { ok: false, status: 0, datos: { detalle: String(error) } };
  }
}

function hace(iso) {
  if (!iso) return "sin actividad registrada";
  const segundos = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (segundos < 60) return `hace ${segundos}s`;
  if (segundos < 3600) return `hace ${Math.round(segundos / 60)} min`;
  if (segundos < 86400) return `hace ${Math.round(segundos / 3600)} h`;
  return `hace ${Math.round(segundos / 86400)} d`;
}

function chip(estado, cantidad) {
  const texto = ETIQUETAS_ESTADO[estado] || estado;
  return el("span", {
    clase: "chip",
    "data-estado": estado,
    texto: cantidad === undefined ? texto : `${texto}: ${cantidad}`,
  });
}

/** Un bloque que explica por qué algo no está implementado, en vez de mentir con datos. */
function bloqueado(pendiente, detalle) {
  return el("div", { clase: "bloqueado" }, [
    el("div", {}, [
      el("strong", { texto: "Falta decidir. " }),
      document.createTextNode(pendiente?.pregunta || detalle || "Decisión pendiente."),
    ]),
    el("span", {
      clase: "fuente",
      texto: pendiente ? `bloqueado por ${pendiente.bloqueado_por}` : "",
    }),
  ]);
}

function tarjeta(titulo, etiqueta, cuerpo, cuerpoPlano = false) {
  return el("section", { clase: "tarjeta" }, [
    el("header", { clase: "tarjeta-cab" }, [
      el("h2", { texto: titulo }),
      etiqueta ? el("span", { clase: "etiqueta", texto: etiqueta }) : null,
    ]),
    cuerpoPlano ? cuerpo : el("div", { clase: "tarjeta-cuerpo" }, cuerpo),
  ]);
}

/* ── saldo de suscripciones (ADR-0025) ──────────────────────────────────── */

function cuando(iso) {
  if (!iso) return "sin reset conocido";
  const minutos = Math.round((new Date(iso).getTime() - Date.now()) / 60000);
  if (minutos <= 0) return "resetea ya";
  if (minutos < 60) return `resetea en ${minutos} min`;
  if (minutos < 1440) return `resetea en ${Math.round(minutos / 60)} h`;
  return `resetea en ${Math.round(minutos / 1440)} d`;
}

/** Una ventana con su barra. El color solo distingue agotada de no agotada; el umbral de
 *  ADR-0026 y qué hacer al cruzarlo —conmutar de proveedor o esperar el reset— viven en
 *  `nucleo/senal_saldo.py`. El panel muestra el dato, no decide sobre él (ADR-0013). */
function ventana(v) {
  const porcentaje = v.restante === null ? null : Math.round(v.restante * 100);
  return el("div", { clase: "ventana" }, [
    el("div", { clase: "ventana-cab" }, [
      el("span", { clase: "nombre", texto: v.nombre }),
      el("span", { texto: porcentaje === null ? "sin observar" : `queda ${porcentaje}%` }),
    ]),
    el("div", { clase: "barra-saldo", "data-agotada": String(v.agotada) }, [
      el("span", { style: `width: ${porcentaje === null ? 0 : porcentaje}%` }),
    ]),
    el("span", { clase: "fuente", texto: cuando(v.resetea), title: v.resetea || "" }),
  ]);
}

function tarjetaSaldo(uso) {
  const datos = uso.datos || {};
  const cuerpo = [];

  for (const s of datos.suscripciones || []) {
    cuerpo.push(
      el("div", { clase: "suscripcion" }, [
        el("div", { clase: "suscripcion-cab" }, [
          el("strong", { texto: s.proveedor }),
          s.plan ? el("span", { clase: "etiqueta", texto: s.plan }) : null,
          el("span", {
            clase: "fuente",
            texto: s.observado ? `observado ${hace(s.observado)}` : "nunca observado",
            title: s.fuente || "",
          }),
        ]),
        ...(s.ventanas.length
          ? s.ventanas.map(ventana)
          : [
              el("p", {
                clase: "vacio",
                texto:
                  "Infraestructura todavía no registró saldo. Se carga con `jafne saldo`.",
              }),
            ]),
      ])
    );
  }

  // El dato se sirve, pero medirlo solo sigue abierto: se dice, no se disimula.
  cuerpo.push(bloqueado(datos.medicion_automatica));
  return tarjeta("Saldo de suscripciones", "ADR-0025", cuerpo);
}

/* ── cerebros por rol (ADR-0033) ────────────────────────────────────────── */

/** Sobre qué modelo corre cada rol. Se deriva al leer, así que refleja cerebros.yaml sin
 *  copia intermedia. Un rol sin tamaño por defecto no es un error: su cerebro lo elige el
 *  Encargado tarea por tarea (ADR-0003), y eso se dice en vez de mostrarlo vacío. */
function tarjetaRoles(roles) {
  const cuerpo = (roles.datos || []).map((r) => {
    let detalle;
    if (r.problema) {
      detalle = el("span", { clase: "vacio", texto: r.problema });
    } else if (r.por_tarea) {
      detalle = el("span", {
        clase: "fuente",
        texto: "lo elige el Encargado por tarea",
      });
    } else {
      detalle = el("span", {}, [
        el("strong", { texto: r.cerebro.modelo || r.cerebro.id }),
        el("span", { clase: "etiqueta", texto: r.tamano }),
      ]);
    }
    return el("div", { clase: "suscripcion-cab", title: r.descripcion }, [
      el("strong", { texto: r.rol }),
      detalle,
    ]);
  });
  return tarjeta("Cerebro por rol", "ADR-0033", cuerpo);
}

/* ── credencial (ADR-0034) ──────────────────────────────────────────────── */

/** Con qué credencial habla JAFNE. No hay formulario de login a propósito: la sesión es
 *  de Claude Code y JAFNE la hereda, así que no hay secreto que pedir ni que guardar. El
 *  panel mira y reporta — meterle entrada de credenciales lo volvería depositario de
 *  secretos del proveedor, que es justo lo que ADR-0034 evita. */
function tarjetaCredencial(credencial) {
  const d = credencial.datos || {};
  const cuerpo = [
    el("div", { clase: "suscripcion-cab" }, [
      el("strong", { texto: "Sesión" }),
      el("span", {
        clase: d.listo ? "etiqueta" : "vacio",
        texto: d.listo ? "lista" : "sin configurar",
      }),
    ]),
    el("div", { clase: "suscripcion-cab" }, [
      el("span", { clase: "nombre", texto: "CLI de Claude Code" }),
      el("span", {
        clase: "fuente",
        texto: d.ruta_cli || "no encontrada",
        title: d.ruta_cli || "",
      }),
    ]),
  ];

  // El aviso que más importa: una API key en el entorno factura por token en vez de
  // consumir la suscripción, y nadie se entera hasta que llega la cuenta.
  for (const aviso of d.avisos || []) {
    cuerpo.push(el("p", { clase: "vacio", texto: aviso }));
  }
  if (d.sugerencia) {
    cuerpo.push(el("p", { clase: "vacio", texto: d.sugerencia }));
  }
  if (d.listo) {
    cuerpo.push(
      el("span", {
        clase: "fuente",
        texto:
          "No hay nada que iniciar acá: la sesión la maneja Claude Code. JAFNE no guarda credenciales.",
      })
    );
  }
  return tarjeta("Credencial", "ADR-0034", cuerpo);
}

/* ── dictado por voz (ADR-0036) ─────────────────────────────────────────── */
//
// El audio se graba en el navegador, se manda crudo al panel y vuelve texto. No se guarda
// nada: ni acá ni del lado del servidor. El resultado va al campo de texto, no al hilo —
// el Usuario lo edita o lo borra antes de mandarlo, como cualquier mensaje tipeado.

let vozConsultada = null;

async function voz() {
  if (!vozConsultada) {
    const respuesta = await api("/api/voz");
    vozConsultada = respuesta.datos || {
      disponible: false,
      detalle: "No se pudo consultar el estado del dictado.",
    };
  }
  return vozConsultada;
}

function activarDictado(seccion, entrada) {
  const boton = seccion.querySelector('[data-rol="dictar"]');
  const aviso = seccion.querySelector('[data-rol="aviso"]');
  if (!boton) return;

  const avisar = (texto, clase = "") => {
    aviso.textContent = texto || "";
    aviso.className = `chat-aviso ${clase}`.trim();
    aviso.hidden = !texto;
  };

  const apagar = (motivo) => {
    boton.disabled = true;
    boton.title = motivo;
    avisar(motivo);
  };

  voz().then((estado) => {
    if (!estado.disponible) return apagar(estado.detalle);
    // Fuera de un contexto seguro el navegador ni ofrece el micrófono. Cruza con el
    // pendiente `tls-y-rotacion-de-token`: dictar desde la malla ZeroTier necesita TLS.
    if (!navigator.mediaDevices?.getUserMedia)
      return apagar(
        "El navegador no da acceso al micrófono fuera de loopback o HTTPS (ADR-0020)."
      );
    boton.disabled = false;
    boton.title = estado.detalle;
  });

  let grabadora = null;

  boton.addEventListener("click", async () => {
    if (grabadora?.state === "recording") {
      grabadora.stop();
      return;
    }

    let flujo;
    try {
      flujo = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      avisar("Sin permiso de micrófono: el navegador lo rechazó.", "malo");
      return;
    }

    const trozos = [];
    grabadora = new MediaRecorder(flujo);
    grabadora.addEventListener("dataavailable", (evento) => {
      if (evento.data.size) trozos.push(evento.data);
    });

    grabadora.addEventListener("stop", async () => {
      flujo.getTracks().forEach((pista) => pista.stop());
      boton.classList.remove("grabando");
      boton.classList.add("transcribiendo");
      boton.disabled = true;
      avisar("Transcribiendo…");

      const audio = new Blob(trozos, { type: grabadora.mimeType });
      const respuesta = await api("/api/transcribir", { method: "POST", body: audio });

      boton.classList.remove("transcribiendo");
      boton.disabled = false;

      if (!respuesta.ok) {
        avisar(respuesta.datos?.detalle || "No se pudo transcribir.", "malo");
        return;
      }
      const texto = (respuesta.datos?.texto || "").trim();
      if (!texto) {
        avisar("No se entendió nada en ese audio.", "malo");
        return;
      }
      entrada.value = entrada.value.trim()
        ? `${entrada.value.trim()} ${texto}`
        : texto;
      entrada.focus();
      // Dónde se transcribió dejó de ser obvio con ADR-0037, así que se muestra: "dónde
      // estuvo mi audio" no es una pregunta que deba contestarse leyendo variables de
      // entorno.
      const donde =
        respuesta.datos.donde && respuesta.datos.donde !== "local"
          ? ` · nodo ${respuesta.datos.donde}`
          : "";
      avisar(
        `Dictado en ${respuesta.datos.duracion}s · ${respuesta.datos.idioma || "?"} · ` +
          `${respuesta.datos.modelo}${donde}. Revisalo antes de enviar.`
      );
    });

    grabadora.start();
    boton.classList.add("grabando");
    avisar("Grabando… tocá de nuevo para cortar.");
  });
}

/* ── chat (ADR-0013, ADR-0031, ADR-0034) ────────────────────────────────── */

/** Qué burbujas mostrar para una respuesta del chat.
 *
 *  Cada fallo se muestra distinto porque cada uno lleva a otra acción: falta una decisión
 *  (se lee el pendiente), falta código, falta la sesión de Claude Code, o se cayó la red.
 *  Un "sin respuesta" genérico para todos los casos no le dice a nadie qué hacer.
 */
function respuestaDelChat(respuesta) {
  const d = respuesta.datos || {};

  if (respuesta.status === 0)
    return [
      el("div", {
        clase: "burbuja error",
        texto: `No se pudo hablar con el panel: ${d.detalle || "sin detalle"}`,
      }),
    ];

  // Los dos 501 no significan lo mismo, y el repo se toma en serio la diferencia: uno
  // dice "nadie decidió esto todavía", el otro "está decidido, falta escribirlo".
  if (respuesta.status === 501)
    return [
      d.pendiente
        ? bloqueado(d.pendiente)
        : el("div", { clase: "bloqueado" }, [
            el("strong", { texto: "Falta código. " }),
            document.createTextNode(d.detalle || "Decidido, pero todavía sin escribir."),
          ]),
    ];

  if (!respuesta.ok)
    return [
      el("div", {
        clase: "burbuja error",
        texto: d.detalle || `El panel respondió ${respuesta.status}.`,
      }),
    ];

  // Turno atendido: puede traer texto, o un error del propio proveedor —sin cupo, sesión
  // caída— que llega con 200 porque el panel sí funcionó.
  const burbujas = [];
  for (const evento of d.eventos || []) {
    if (evento.tipo === "error")
      burbujas.push(el("div", { clase: "burbuja error", texto: evento.texto }));
    else if (evento.tipo === "texto" && evento.texto)
      burbujas.push(el("div", { clase: "burbuja sistema", texto: evento.texto }));
  }

  if (!burbujas.length)
    burbujas.push(
      el("div", {
        clase: "burbuja error",
        texto:
          "El proveedor contestó sin texto. Probá `jafne credencial` para ver si la " +
          "sesión de Claude Code sigue viva.",
      })
    );
  return burbujas;
}

function montarChat({ titulo, modo, endpoint }) {
  const nodo = document.getElementById("tpl-chat").content.cloneNode(true);
  const seccion = nodo.querySelector("section");
  seccion.querySelector('[data-rol="titulo"]').textContent = titulo;
  seccion.querySelector('[data-rol="modo"]').textContent = modo;

  const hilo = seccion.querySelector('[data-rol="hilo"]');
  const form = seccion.querySelector('[data-rol="form"]');
  const entrada = seccion.querySelector('[data-rol="entrada"]');
  activarDictado(seccion, entrada);

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const mensaje = entrada.value.trim();
    if (!mensaje) return;
    hilo.append(el("div", { clase: "burbuja usuario", texto: mensaje }));
    entrada.value = "";
    hilo.scrollTop = hilo.scrollHeight;

    // Un turno tarda entre varios segundos y un minuto: sin esto la pantalla queda
    // muerta y no se distingue "pensando" de "se colgó".
    const esperando = el("div", { clase: "burbuja sistema pensando", texto: "Pensando…" });
    hilo.append(esperando);
    hilo.scrollTop = hilo.scrollHeight;

    const respuesta = await api(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje }),
    });
    esperando.remove();
    hilo.append(...respuestaDelChat(respuesta));
    hilo.scrollTop = hilo.scrollHeight;
  });

  return seccion;
}

/* ── vistas ─────────────────────────────────────────────────────────────── */

async function vistaInicio() {
  miga.hidden = true;
  vista.replaceChildren(el("p", { clase: "vacio", texto: "Cargando…" }));

  const [proyectos, pendientes, uso, roles, credencial] = await Promise.all([
    api("/api/proyectos"),
    api("/api/pendientes"),
    api("/api/uso-suscripciones"),
    api("/api/roles"),
    api("/api/credencial"),
  ]);

  const grilla = el("div", { clase: "grilla" });
  const lista = proyectos.datos || [];
  if (!lista.length) {
    grilla.append(
      el("p", {
        clase: "vacio",
        texto:
          "No hay proyectos registrados. Agregalos en ~/.jafne/proyectos.yaml (ADR-0007).",
      })
    );
  }
  for (const proyecto of lista) {
    grilla.append(
      el(
        "button",
        { clase: "proyecto", onclick: () => (location.hash = `#/proyecto/${proyecto.id}`) },
        [
          el("h3", { texto: proyecto.nombre }),
          el("p", {
            clase: "ruta",
            texto: proyecto.encargado || (proyecto.sin_registrar
              ? "sin entrada en proyectos.yaml"
              : "sin repo encargado/ declarado"),
          }),
          el(
            "div",
            { clase: "conteos" },
            proyecto.total_asuntos
              ? Object.entries(proyecto.por_estado)
                  .filter(([, n]) => n > 0)
                  .map(([estado, n]) => chip(estado, n))
              : [el("span", { clase: "chip", texto: "sin asuntos" })]
          ),
        ]
      )
    );
  }

  const listaPendientes = el(
    "ul",
    { clase: "pendientes" },
    (pendientes.datos || []).map((p) =>
      el("li", {}, [
        el("span", { clase: "titulo", texto: p.titulo }),
        el("span", { clase: "fuente", texto: p.bloqueado_por }),
        el("p", { clase: "pregunta", texto: p.pregunta }),
      ])
    )
  );

  vista.replaceChildren(
    el("div", { clase: "columnas" }, [
      el("div", { clase: "pila" }, [
        tarjeta("Proyectos", `${lista.length}`, grilla),
        tarjetaRoles(roles),
        tarjetaCredencial(credencial),
        tarjetaSaldo(uso),
      ]),
      el("div", { clase: "pila" }, [
        montarChat({
          titulo: "Chat con el Asistente",
          modo: "nivel raíz",
          endpoint: "/api/chat/asistente",
        }),
        tarjeta(
          "Decisiones pendientes",
          `${(pendientes.datos || []).length}`,
          listaPendientes,
          true
        ),
      ]),
    ])
  );
}

async function vistaProyecto(id) {
  miga.hidden = false;
  miga.replaceChildren(
    el("a", { href: "#/", texto: "← Todos los proyectos" })
  );
  vista.replaceChildren(el("p", { clase: "vacio", texto: "Cargando…" }));

  const respuesta = await api(`/api/proyectos/${encodeURIComponent(id)}`);
  if (!respuesta.ok) {
    vista.replaceChildren(
      el("p", {
        clase: "vacio",
        texto: respuesta.datos?.detalle || `No se pudo cargar el proyecto '${id}'.`,
      })
    );
    return;
  }

  const proyecto = respuesta.datos;
  const asuntos = proyecto.asuntos || [];
  const listaAsuntos = el(
    "ul",
    { clase: "asuntos" },
    asuntos.length
      ? asuntos.map((asunto) =>
          el("li", {}, [
            el("span", { clase: "titulo", texto: asunto.titulo || asunto.id }),
            chip(asunto.estado_efectivo),
            el("span", { clase: "meta" }, [
              el("code", { texto: asunto.id }),
              el("span", {
                texto: hace(asunto.ultima_actividad),
                title: asunto.ultima_actividad || "",
              }),
              asunto.rama ? el("code", { texto: asunto.rama }) : null,
              el("span", {
                texto: `contenedor: ${asunto.estado_contenedor || "nunca tuvo"}`,
                title: asunto.descripcion_contenedor || "",
              }),
              el("span", { texto: `${asunto.mensajes} mensajes` }),
              asunto.pregunta_pendiente
                ? el("span", { texto: "pregunta pendiente" })
                : null,
              asunto.estado_por_timeout
                ? el("span", { texto: "por timeout de 3 min (ADR-0009)" })
                : null,
              asunto.reabrible ? el("span", { texto: "reabrible con contexto" }) : null,
              asunto.motivo ? el("span", { texto: asunto.motivo }) : null,
              asunto.preview_url
                ? el("a", {
                    href: asunto.preview_url,
                    texto: "preview",
                    target: "_blank",
                    rel: "noreferrer",
                  })
                : null,
            ]),
          ])
        )
      : [
          el("li", {}, [
            el("span", {
              clase: "vacio",
              texto: "Este proyecto todavía no tiene Asuntos.",
            }),
          ]),
        ]
  );

  vista.replaceChildren(
    el("div", { clase: "columnas" }, [
      el("div", { clase: "pila" }, [
        tarjeta(
          proyecto.nombre,
          `${proyecto.asuntos_abiertos} abiertos de ${proyecto.total_asuntos}`,
          listaAsuntos,
          true
        ),
      ]),
      el("div", { clase: "pila" }, [
        montarChat({
          titulo: `Chat con el Encargado de ${proyecto.nombre}`,
          modo: "modo directo (ADR-0002)",
          endpoint: `/api/proyectos/${encodeURIComponent(id)}/chat`,
        }),
      ]),
    ])
  );
}

/* ── arranque ───────────────────────────────────────────────────────────── */

async function mostrarSalud() {
  const { datos } = await api("/api/salud");
  if (!datos) return;
  const nodos = [el("div", { texto: `v${datos.version} · ${datos.almacen}` })];
  if (datos.sugerencia) nodos.push(el("div", { texto: datos.sugerencia }));
  document.getElementById("salud").replaceChildren(...nodos);
}

function enrutar() {
  const partes = (location.hash || "#/").slice(2).split("/");
  if (partes[0] === "proyecto" && partes[1]) vistaProyecto(decodeURIComponent(partes[1]));
  else vistaInicio();
}

window.addEventListener("hashchange", enrutar);
mostrarSalud();
enrutar();
