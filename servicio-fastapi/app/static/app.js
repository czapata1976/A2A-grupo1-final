"use strict";

const CLAVE_STORAGE = "a2a_api_key";
const SESION_STORAGE = "a2a_session_id";

const el = {
  panelAcceso: document.getElementById("panel-acceso"),
  app: document.getElementById("app"),
  formAcceso: document.getElementById("form-acceso"),
  clave: document.getElementById("clave"),
  btnVer: document.getElementById("btn-ver"),
  btnConectar: document.getElementById("btn-conectar"),
  errorAcceso: document.getElementById("error-acceso"),
  estadoPunto: document.getElementById("estado-punto"),
  estadoTexto: document.getElementById("estado-texto"),
  btnConfig: document.getElementById("btn-config"),
  listaAgentes: document.getElementById("lista-agentes"),
  btnAutomatico: document.getElementById("btn-automatico"),
  modo: document.getElementById("modo"),
  ayudaModo: document.getElementById("ayuda-modo"),
  btnNueva: document.getElementById("btn-nueva"),
  sesionId: document.getElementById("sesion-id"),
  mensajes: document.getElementById("mensajes"),
  formConsulta: document.getElementById("form-consulta"),
  consulta: document.getElementById("consulta"),
  btnEnviar: document.getElementById("btn-enviar"),
  contador: document.getElementById("contador"),
  trazaVacia: document.getElementById("traza-vacia"),
  traza: document.getElementById("traza"),
  trazaSolicitud: document.getElementById("traza-solicitud"),
  trazaEstado: document.getElementById("traza-estado"),
  trazaAgentes: document.getElementById("traza-agentes"),
  trazaAportes: document.getElementById("traza-aportes"),
  trazaPasos: document.getElementById("traza-pasos"),
  flujo: document.getElementById("flujo"),
  flujoEstado: document.getElementById("flujo-estado"),
  flujoAgentes: document.getElementById("flujo-agentes"),
  etapaUsuario: document.getElementById("etapa-usuario"),
  etapaEnrutador: document.getElementById("etapa-enrutador"),
  etapaSintesis: document.getElementById("etapa-sintesis"),
  etapaRespuesta: document.getElementById("etapa-respuesta"),
  usuarioDetalle: document.getElementById("usuario-detalle"),
  enrutadorDetalle: document.getElementById("enrutador-detalle"),
  sintesisDetalle: document.getElementById("sintesis-detalle"),
  respuestaDetalle: document.getElementById("respuesta-detalle"),
};

const estado = {
  clave: "",
  agentes: [],
  seleccion: new Set(),
  modo: "auto",
  sessionId: "",
  enviando: false,
  conectado: false,
  flujoId: 0,
  flujoConResultado: false,
};

const ETIQUETAS_MODO = {
  auto: "automático",
  individual: "individual",
  paralelo: "paralelo",
  colaborativo: "colaborativo",
};

function crearSesionId() {
  const base = typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return base.replace(/[^a-zA-Z0-9]/g, "").slice(0, 32);
}

function ponerEstado(texto, tipo) {
  el.estadoTexto.textContent = texto;
  el.estadoPunto.className = "punto";
  if (tipo === "activo") {
    el.estadoPunto.classList.add("punto-activo");
  } else if (tipo === "error") {
    el.estadoPunto.classList.add("punto-error");
  } else {
    el.estadoPunto.classList.add("punto-espera");
  }
}

function mostrarErrorAcceso(mensaje) {
  el.errorAcceso.textContent = mensaje;
  el.errorAcceso.hidden = false;
}

function limpiarErrorAcceso() {
  el.errorAcceso.hidden = true;
  el.errorAcceso.textContent = "";
}

function mostrarAcceso() {
  el.panelAcceso.hidden = false;
  el.app.hidden = true;
  el.clave.focus();
}

function mostrarApp() {
  el.panelAcceso.hidden = true;
  el.app.hidden = false;
}

function actualizarSesion() {
  if (!estado.sessionId) {
    el.sesionId.textContent = "—";
    return;
  }
  el.sesionId.textContent = `${estado.sessionId.slice(0, 8)}…`;
  el.sesionId.title = estado.sessionId;
}

function actualizarContador() {
  el.contador.textContent = String(el.consulta.value.length);
}

async function api(ruta, opciones = {}) {
  const cabeceras = new Headers(opciones.headers || {});
  if (estado.clave) {
    cabeceras.set("X-API-Key", estado.clave);
  }
  let cuerpo;
  if (opciones.body !== undefined) {
    cabeceras.set("Content-Type", "application/json");
    cuerpo = JSON.stringify(opciones.body);
  }
  const respuesta = await fetch(ruta, {
    method: opciones.method || "GET",
    headers: cabeceras,
    body: cuerpo,
    cache: "no-store",
  });
  let datos = null;
  try {
    datos = await respuesta.json();
  } catch (_error) {
    datos = null;
  }
  if (!respuesta.ok) {
    const mensaje =
      (datos && datos.error && datos.error.mensaje) ||
      (datos && datos.detail) ||
      `Error HTTP ${respuesta.status}`;
    const error = new Error(mensaje);
    error.status = respuesta.status;
    error.datos = datos;
    error.retryAfter = respuesta.headers.get("Retry-After");
    throw error;
  }
  return datos;
}

async function comprobarSalud() {
  if (estado.conectado) {
    return;
  }
  try {
    const respuesta = await fetch("/salud", { cache: "no-store" });
    if (!respuesta.ok) {
      throw new Error("sin salud");
    }
    ponerEstado("Servicio local activo", "activo");
  } catch (_error) {
    ponerEstado("Servicio sin conexión", "error");
  }
}

async function conectar(clave, opciones = {}) {
  const limpia = String(clave || "").trim();
  if (limpia.length < 12) {
    mostrarErrorAcceso("La clave debe tener al menos 12 caracteres.");
    el.clave.focus();
    return;
  }
  limpiarErrorAcceso();
  estado.clave = limpia;
  el.btnConectar.disabled = true;
  el.btnConectar.textContent = "Conectando…";
  try {
    const datos = await api("/v1/agentes");
    estado.clave = limpia;
    sessionStorage.setItem(CLAVE_STORAGE, limpia);
    estado.agentes = Array.isArray(datos.agentes) ? datos.agentes : [];
    estado.conectado = true;
    mostrarApp();
    renderAgentes();
    actualizarSeleccion();
    ponerEstado(
      estado.agentes.length
        ? `Conectado · ${estado.agentes.length} agente${estado.agentes.length === 1 ? "" : "s"}`
        : "Conectado · sin agentes",
      estado.agentes.length ? "activo" : "espera",
    );
    if (estado.agentes.length === 0) {
      agregarSistema(
        "No se descubrieron agentes A2A. Levanta al menos un servidor LangGraph y vuelve a conectar desde «Clave API».",
      );
    }
    if (Array.isArray(datos.errores) && datos.errores.length) {
      agregarSistema(`Aviso de descubrimiento: ${datos.errores.join(" · ")}`);
    }
  } catch (error) {
    estado.clave = "";
    estado.conectado = false;
    sessionStorage.removeItem(CLAVE_STORAGE);
    if (error.status === 401) {
      mostrarErrorAcceso("La clave fue rechazada. Revisa el valor de API_KEYS en el servidor.");
      ponerEstado("Clave rechazada", "error");
    } else if (error.status === 429) {
      mostrarErrorAcceso("El servicio está limitando solicitudes. Espera un momento e intenta de nuevo.");
      ponerEstado("Límite alcanzado", "error");
    } else if (error instanceof TypeError) {
      mostrarErrorAcceso("No se pudo conectar con el servicio local. Verifica que FastAPI esté arriba.");
      ponerEstado("Servicio no disponible", "error");
    } else {
      mostrarErrorAcceso(`No se pudo conectar: ${error.message}`);
      ponerEstado("Servicio no disponible", "error");
    }
    if (opciones.silencioso) {
      el.clave.value = limpia;
    }
    mostrarAcceso();
  } finally {
    el.btnConectar.disabled = false;
    el.btnConectar.textContent = "Conectar";
  }
}

function renderAgentes() {
  el.listaAgentes.replaceChildren();
  renderFlujoAgentes();
  if (estado.agentes.length === 0) {
    const aviso = document.createElement("p");
    aviso.className = "ayuda";
    aviso.textContent = "No hay agentes disponibles en este momento.";
    el.listaAgentes.appendChild(aviso);
    return;
  }
  for (const agente of estado.agentes) {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "agente";
    boton.dataset.grafo = agente.grafo;
    boton.title = agente.descripcion || agente.especialidad || agente.grafo;

    const nombre = document.createElement("span");
    nombre.className = "agente-nombre";
    nombre.textContent = agente.autor || agente.grafo;

    const detalle = document.createElement("span");
    detalle.className = "agente-detalle";
    detalle.textContent = agente.especialidad || agente.descripcion || agente.grafo;

    boton.append(nombre, detalle);
    boton.addEventListener("click", () => alternarAgente(agente.grafo));
    el.listaAgentes.appendChild(boton);
  }
}

function actualizarSeleccion() {
  for (const boton of el.listaAgentes.querySelectorAll(".agente")) {
    const seleccionado = estado.seleccion.has(boton.dataset.grafo);
    boton.classList.toggle("seleccionado", seleccionado);
    boton.setAttribute("aria-pressed", seleccionado ? "true" : "false");
  }
  actualizarAyudaModo();
  actualizarFlujoSeleccion();
}

function nombreVisible(agente) {
  return agente.autor || agente.grafo;
}

function esperar(ms) {
  return new Promise((resolver) => {
    setTimeout(resolver, ms);
  });
}

function renderFlujoAgentes() {
  el.flujoAgentes.replaceChildren();
  if (estado.agentes.length === 0) {
    const aviso = document.createElement("p");
    aviso.className = "flujo-vacio";
    aviso.textContent = "Sin agentes descubiertos.";
    el.flujoAgentes.appendChild(aviso);
    return;
  }
  for (const agente of estado.agentes) {
    const nodo = document.createElement("div");
    nodo.className = "flujo-agente pendiente";
    nodo.dataset.grafo = agente.grafo;
    nodo.setAttribute("role", "listitem");
    nodo.title = agente.descripcion || agente.especialidad || agente.grafo;

    const nombre = document.createElement("span");
    nombre.className = "fa-nombre";
    nombre.textContent = nombreVisible(agente);

    const detalle = document.createElement("span");
    detalle.className = "fa-estado";
    detalle.textContent = "disponible";

    nodo.append(nombre, detalle);
    el.flujoAgentes.appendChild(nodo);
  }
}

function nodoFlujo(grafo) {
  return el.flujoAgentes.querySelector(`.flujo-agente[data-grafo="${CSS.escape(grafo)}"]`);
}

function flecha(indice, activa) {
  const flechas = el.flujo.querySelectorAll(".flujo-flecha");
  const elemento = flechas[indice];
  if (elemento) {
    elemento.classList.toggle("activa", Boolean(activa));
  }
}

function marcarEtapa(nodo, clase) {
  if (!nodo) {
    return;
  }
  nodo.classList.remove("activo", "ok", "error");
  if (clase) {
    nodo.classList.add(clase);
  }
}

function reiniciarFlujo() {
  estado.flujoId += 1;
  estado.flujoConResultado = false;
  for (const etapa of el.flujo.querySelectorAll(".flujo-etapa")) {
    etapa.classList.remove("activo", "ok", "error");
  }
  for (const lambda of el.flujo.querySelectorAll(".flujo-flecha")) {
    lambda.classList.remove("activa");
  }
  for (const nodo of el.flujoAgentes.querySelectorAll(".flujo-agente")) {
    nodo.className = "flujo-agente pendiente";
    const detalle = nodo.querySelector(".fa-estado");
    if (detalle) {
      detalle.textContent = "disponible";
    }
  }
  el.flujoEstado.className = "insignia";
  el.flujoEstado.textContent = "en espera";
  el.usuarioDetalle.textContent = "consulta";
  el.enrutadorDetalle.textContent = "elige agentes";
  el.sintesisDetalle.textContent = "une aportes";
  el.respuestaDetalle.textContent = "—";
}

function actualizarFlujoSeleccion() {
  if (estado.enviando || estado.flujoConResultado) {
    return;
  }
  const total = estado.seleccion.size;
  el.enrutadorDetalle.textContent = total
    ? `${total} seleccionado${total === 1 ? "" : "s"}`
    : "elige agentes";
  for (const nodo of el.flujoAgentes.querySelectorAll(".flujo-agente")) {
    const elegido = estado.seleccion.has(nodo.dataset.grafo);
    nodo.classList.toggle("elegido", elegido);
    nodo.classList.toggle("pendiente", !elegido);
  }
}

function iniciarFlujoEnvio(cuerpo) {
  reiniciarFlujo();
  const id = estado.flujoId;
  el.flujoEstado.className = "insignia activo";
  el.flujoEstado.textContent = "consultando";
  el.usuarioDetalle.textContent = "consulta enviada";
  marcarEtapa(el.etapaUsuario, "activo");

  const elegidos = Array.isArray(cuerpo.agentes) && cuerpo.agentes.length
    ? cuerpo.agentes
    : Array.from(estado.seleccion);
  for (const grafo of elegidos) {
    const nodo = nodoFlujo(grafo);
    if (!nodo) {
      continue;
    }
    nodo.className = "flujo-agente activo";
    const detalle = nodo.querySelector(".fa-estado");
    if (detalle) {
      detalle.textContent = "en curso";
    }
  }

  setTimeout(() => {
    if (id !== estado.flujoId) {
      return;
    }
    marcarEtapa(el.etapaUsuario, "ok");
    marcarEtapa(el.etapaEnrutador, "activo");
    flecha(0, true);
    el.enrutadorDetalle.textContent = ETIQUETAS_MODO[cuerpo.modo] || cuerpo.modo;
  }, 220);

  setTimeout(() => {
    if (id !== estado.flujoId) {
      return;
    }
    marcarEtapa(el.etapaEnrutador, "ok");
    flecha(1, true);
  }, 520);
}

async function animarResultadoFlujo(datos) {
  const id = estado.flujoId;
  estado.flujoConResultado = true;
  const consultados = Array.isArray(datos.agentes_consultados) ? datos.agentes_consultados : [];
  const aportes = Array.isArray(datos.aportes) ? datos.aportes : [];
  const porAgente = new Map(aportes.map((aporte) => [aporte.agente, aporte]));

  for (const nodo of el.flujoAgentes.querySelectorAll(".flujo-agente")) {
    const grafo = nodo.dataset.grafo;
    const detalle = nodo.querySelector(".fa-estado");
    const aporte = porAgente.get(grafo);
    if (aporte) {
      const correcto = aporte.estado === "ok";
      nodo.className = `flujo-agente ${correcto ? "ok" : "error"}`;
      const textoEstado = correcto
        ? `ok · ${aporte.duracion_ms || 0} ms`
        : aporte.codigo_error || "error";
      if (detalle) {
        detalle.textContent = textoEstado;
      }
      nodo.title = aporte.error
        ? `${grafo} · ${textoEstado}: ${aporte.error}`
        : `${grafo} · ${textoEstado}`;
    } else if (consultados.includes(grafo)) {
      nodo.className = "flujo-agente activo";
      if (detalle) {
        detalle.textContent = "en curso";
      }
    } else {
      nodo.className = "flujo-agente omitido";
      if (detalle) {
        detalle.textContent = "no usado";
      }
      nodo.title = `${grafo} · no consultado en esta ejecución`;
    }
  }

  marcarEtapa(el.etapaUsuario, "ok");
  marcarEtapa(el.etapaEnrutador, "ok");
  flecha(0, true);
  flecha(1, true);

  marcarEtapa(el.etapaSintesis, "activo");
  flecha(2, true);
  el.sintesisDetalle.textContent = `${consultados.length} aporte${consultados.length === 1 ? "" : "s"}`;
  await esperar(180);
  if (id !== estado.flujoId) {
    return;
  }
  marcarEtapa(el.etapaSintesis, "ok");

  marcarEtapa(el.etapaRespuesta, "activo");
  flecha(3, true);
  el.respuestaDetalle.textContent = datos.estado || "—";
  await esperar(160);
  if (id !== estado.flujoId) {
    return;
  }
  marcarEtapa(el.etapaRespuesta, datos.estado === "error" ? "error" : "ok");

  const clase = datos.estado === "ok" ? "ok" : datos.estado === "parcial" ? "parcial" : "error";
  el.flujoEstado.className = `insignia ${clase}`;
  el.flujoEstado.textContent = datos.estado || "—";
}

function marcarFlujoError(error) {
  estado.flujoConResultado = true;
  marcarEtapa(el.etapaEnrutador, "error");
  for (const nodo of el.flujoAgentes.querySelectorAll(".flujo-agente.activo")) {
    nodo.className = "flujo-agente error";
    const detalle = nodo.querySelector(".fa-estado");
    if (detalle) {
      detalle.textContent = "sin respuesta";
    }
  }
  marcarEtapa(el.etapaRespuesta, "error");
  el.respuestaDetalle.textContent = "sin respuesta";
  el.flujoEstado.className = "insignia error";
  el.flujoEstado.textContent = error && error.status ? `error ${error.status}` : "error";
}

function actualizarAyudaModo() {
  const textos = {
    auto: "El servicio elige al especialista según tu consulta.",
    individual: "Un agente; si no eliges, el servicio elige el mejor para la consulta.",
    paralelo: "Se consultan todos los agentes elegidos a la vez. Si no eliges, se usan los que coincidan con la consulta.",
    colaborativo: "En orden, cada agente recibe los aportes anteriores. La respuesta final conserva cada texto íntegro.",
  };
  el.ayudaModo.textContent = textos[estado.modo] || textos.auto;
}

function alternarAgente(grafo) {
  if (estado.seleccion.has(grafo)) {
    estado.seleccion.delete(grafo);
  } else {
    estado.seleccion.add(grafo);
  }
  if (estado.seleccion.size > 1 && (estado.modo === "auto" || estado.modo === "individual")) {
    estado.modo = "paralelo";
  } else if (estado.seleccion.size === 1 && estado.modo === "auto") {
    estado.modo = "individual";
  } else if (estado.seleccion.size === 0) {
    estado.modo = "auto";
  }
  el.modo.value = estado.modo;
  actualizarSeleccion();
}

function cambiarModo() {
  estado.modo = el.modo.value;
  if (estado.modo === "auto") {
    estado.seleccion.clear();
  } else if (estado.modo === "individual" && estado.seleccion.size > 1) {
    const primero = Array.from(estado.seleccion)[0];
    estado.seleccion.clear();
    estado.seleccion.add(primero);
  }
  actualizarSeleccion();
}

function agregarMensaje(tipo, texto, meta) {
  const contenedor = document.createElement("div");
  contenedor.className = `mensaje mensaje-${tipo}`;
  const parrafo = document.createElement("p");
  parrafo.textContent = texto;
  contenedor.appendChild(parrafo);
  if (meta) {
    const pie = document.createElement("p");
    pie.className = "meta-mensaje";
    pie.textContent = meta;
    contenedor.appendChild(pie);
  }
  el.mensajes.appendChild(contenedor);
  el.mensajes.scrollTop = el.mensajes.scrollHeight;
  return contenedor;
}

function agregarSistema(texto) {
  const contenedor = document.createElement("div");
  contenedor.className = "mensaje mensaje-sistema";
  const parrafo = document.createElement("p");
  parrafo.textContent = texto;
  contenedor.appendChild(parrafo);
  el.mensajes.appendChild(contenedor);
  el.mensajes.scrollTop = el.mensajes.scrollHeight;
}

function agregarErrorSistema(texto) {
  const contenedor = document.createElement("div");
  contenedor.className = "mensaje mensaje-error-sistema";
  const parrafo = document.createElement("p");
  parrafo.textContent = texto;
  contenedor.appendChild(parrafo);
  el.mensajes.appendChild(contenedor);
  el.mensajes.scrollTop = el.mensajes.scrollHeight;
}

function agregarCargando() {
  const contenedor = document.createElement("div");
  contenedor.className = "mensaje mensaje-agente";
  const linea = document.createElement("div");
  linea.className = "mensaje-cargando";
  const texto = document.createElement("span");
  texto.textContent = "Consultando agentes";
  const puntos = document.createElement("span");
  puntos.className = "cargando-puntos";
  for (let i = 0; i < 3; i += 1) {
    puntos.appendChild(document.createElement("span"));
  }
  linea.append(texto, puntos);
  contenedor.appendChild(linea);
  el.mensajes.appendChild(contenedor);
  el.mensajes.scrollTop = el.mensajes.scrollHeight;
  return contenedor;
}

function agregarRespuesta(datos) {
  const contenedor = document.createElement("div");
  contenedor.className = "mensaje mensaje-agente";

  const parrafo = document.createElement("p");
  parrafo.textContent = datos.respuesta || "(El servicio no devolvió texto)";
  contenedor.appendChild(parrafo);

  const agentes = Array.isArray(datos.agentes_consultados) ? datos.agentes_consultados.join(", ") : "—";
  const meta = document.createElement("p");
  meta.className = "meta-mensaje";
  meta.textContent = `Solicitud ${String(datos.solicitud_id || "").slice(0, 12)}… · ${agentes} · ${datos.estado || "—"}`;
  contenedor.appendChild(meta);

  if (datos.estado === "parcial" && Array.isArray(datos.errores) && datos.errores.length) {
    const aviso = document.createElement("p");
    aviso.className = "aviso-parcial";
    aviso.textContent = `Respuesta parcial. No respondieron: ${datos.errores.join(" · ")}`;
    contenedor.appendChild(aviso);
  }

  if (datos.posible_falta_de_datos) {
    const aviso = document.createElement("p");
    aviso.className = "aviso-dato";
    aviso.textContent = "El agente pidió un dato faltante. Completa la información en el mismo hilo para continuar.";
    contenedor.appendChild(aviso);
  }

  el.mensajes.appendChild(contenedor);
  el.mensajes.scrollTop = el.mensajes.scrollHeight;
}

function renderTraza(datos) {
  el.trazaVacia.hidden = true;
  el.traza.hidden = false;
  el.trazaSolicitud.textContent = datos.solicitud_id || "—";
  el.trazaSolicitud.title = datos.solicitud_id || "";

  const estadoConsulta = datos.estado || "error";
  el.trazaEstado.textContent = estadoConsulta;
  el.trazaEstado.className = `insignia ${estadoConsulta}`;

  const agentes = Array.isArray(datos.agentes_consultados) ? datos.agentes_consultados : [];
  el.trazaAgentes.textContent = agentes.length ? agentes.join(", ") : "—";

  el.trazaAportes.replaceChildren();
  const aportes = Array.isArray(datos.aportes) ? datos.aportes : [];
  if (aportes.length === 0) {
    const vacio = document.createElement("p");
    vacio.className = "ayuda";
    vacio.textContent = "La consulta no dejó aportes para mostrar.";
    el.trazaAportes.appendChild(vacio);
  }
  for (const aporte of aportes) {
    const articulo = document.createElement("article");
    articulo.className = "aporte";

    const cabecera = document.createElement("div");
    cabecera.className = "aporte-cabecera";

    const titulo = document.createElement("span");
    titulo.className = "aporte-titulo";
    titulo.textContent = aporte.autor ? `${aporte.autor} · ${aporte.agente}` : aporte.agente;

    const insignia = document.createElement("span");
    insignia.className = `insignia ${aporte.estado}`;
    insignia.textContent = aporte.estado;

    const meta = document.createElement("span");
    meta.className = "aporte-meta";
    const partesMeta = [`${aporte.duracion_ms || 0} ms`];
    if (aporte.context_id) {
      partesMeta.push(`ctx ${aporte.context_id}`);
    }
    if (aporte.contexto_reutilizado) {
      partesMeta.push("memoria");
    }
    meta.textContent = partesMeta.join(" · ");

    cabecera.append(titulo, insignia, meta);

    const cuerpo = document.createElement("pre");
    cuerpo.className = "aporte-cuerpo";
    if (aporte.estado === "ok") {
      cuerpo.textContent = aporte.respuesta || "";
    } else {
      cuerpo.classList.add("aporte-error");
      cuerpo.textContent = `${aporte.codigo_error || "ERROR"}: ${aporte.error || "sin detalle"}`;
    }

    articulo.append(cabecera, cuerpo);
    el.trazaAportes.appendChild(articulo);
  }

  el.trazaPasos.replaceChildren();
  const pasos = Array.isArray(datos.traza) ? datos.traza : [];
  for (const paso of pasos) {
    const item = document.createElement("li");
    const encabezado = document.createElement("span");
    encabezado.className = "paso-agente";
    encabezado.textContent = `#${paso.paso} ${paso.accion}${paso.agente ? ` · ${paso.agente}` : ""}`;
    const detalle = document.createElement("span");
    detalle.className = "paso-detalle";
    detalle.textContent = `${paso.detalle}${paso.duracion_ms != null ? ` · ${paso.duracion_ms} ms` : ""}`;
    item.append(encabezado, detalle);
    el.trazaPasos.appendChild(item);
  }
}

function ocultarTraza() {
  el.traza.hidden = true;
  el.trazaVacia.hidden = false;
  el.trazaAportes.replaceChildren();
  el.trazaPasos.replaceChildren();
}

function mensajeDeError(error) {
  if (error instanceof TypeError) {
    return "No se pudo conectar con el servicio local. Verifica que FastAPI esté arriba.";
  }
  return error.message || "Ocurrió un error inesperado.";
}

function manejarErrorConsulta(error) {
  if (error.status === 401) {
    estado.clave = "";
    estado.conectado = false;
    sessionStorage.removeItem(CLAVE_STORAGE);
    mostrarErrorAcceso("La clave dejó de ser válida. Vuelve a ingresarla para continuar.");
    ponerEstado("Clave rechazada", "error");
    mostrarAcceso();
  }

  const solicitud = error.datos && error.datos.error ? error.datos.error.solicitud_id : "";
  let texto = mensajeDeError(error);
  if (error.status === 429) {
    texto = `Demasiadas solicitudes. ${error.retryAfter ? `Reintenta en ${error.retryAfter} s.` : "Espera un momento."}`;
  }
  if (error.datos && error.datos.error && Array.isArray(error.datos.error.detalles) && error.datos.error.detalles.length) {
    texto = `${texto} ${error.datos.error.detalles.join(" · ")}`;
  }
  if (solicitud) {
    texto = `${texto} (solicitud ${solicitud.slice(0, 12)}…)`;
  }
  agregarErrorSistema(texto);
}

async function enviarConsulta(evento) {
  evento.preventDefault();
  const texto = el.consulta.value.trim();
  if (!texto || estado.enviando) {
    return;
  }
  if (!estado.clave) {
    mostrarAcceso();
    mostrarErrorAcceso("Configura la clave API antes de consultar.");
    return;
  }

  const cuerpo = {
    mensaje: texto,
    modo: estado.modo,
    session_id: estado.sessionId,
  };
  if (estado.seleccion.size > 0) {
    cuerpo.agentes = Array.from(estado.seleccion);
  }
  if ((cuerpo.modo === "auto" || cuerpo.modo === "individual") && cuerpo.agentes && cuerpo.agentes.length > 1) {
    cuerpo.modo = "paralelo";
  }

  estado.enviando = true;
  el.btnEnviar.disabled = true;
  el.btnEnviar.textContent = "Consultando…";
  agregarMensaje("usuario", texto);
  el.consulta.value = "";
  actualizarContador();
  const cargando = agregarCargando();
  iniciarFlujoEnvio(cuerpo);

  try {
    const datos = await api("/v1/consultas", { method: "POST", body: cuerpo });
    cargando.remove();
    if (datos.session_id) {
      estado.sessionId = datos.session_id;
      sessionStorage.setItem(SESION_STORAGE, datos.session_id);
      actualizarSesion();
    }
    agregarRespuesta(datos);
    renderTraza(datos);
    animarResultadoFlujo(datos);
  } catch (error) {
    cargando.remove();
    manejarErrorConsulta(error);
    marcarFlujoError(error);
  } finally {
    estado.enviando = false;
    el.btnEnviar.disabled = false;
    el.btnEnviar.textContent = "Enviar";
    el.consulta.focus();
  }
}

function nuevaConversacion() {
  if (estado.sessionId && estado.clave) {
    api(`/v1/sesiones/${encodeURIComponent(estado.sessionId)}`, { method: "DELETE" }).catch(() => {});
  }
  estado.sessionId = crearSesionId();
  sessionStorage.setItem(SESION_STORAGE, estado.sessionId);
  actualizarSesion();
  estado.seleccion.clear();
  estado.modo = "auto";
  el.modo.value = "auto";
  actualizarSeleccion();
  el.mensajes.replaceChildren();
  agregarSistema("Nueva conversación. La memoria A2A anterior quedó cerrada.");
  ocultarTraza();
  reiniciarFlujo();
  el.consulta.focus();
}

function configurarClave() {
  estado.conectado = false;
  mostrarAcceso();
  limpiarErrorAcceso();
  el.clave.value = "";
  ponerEstado("Configura tu clave API", "espera");
  el.clave.focus();
}

function aplicarEjemplo(tipo) {
  if (tipo === "accion") {
    el.consulta.value = "¿Cuánto vale AAPL en el mercado US y qué debería revisar antes de invertir?";
    estado.seleccion.clear();
    estado.modo = "auto";
  } else if (tipo === "multiaente") {
    el.consulta.value =
      "Evalúa si conviene invertir en Falabella: quiero el dato de mercado, una revisión de cumplimiento normativo y un plan para automatizar el análisis.";
    estado.seleccion.clear();
    const preferidos = ["agente_czz", "agente_alejandra", "agente_bryhan"];
    for (const agente of estado.agentes) {
      if (preferidos.includes(agente.grafo)) {
        estado.seleccion.add(agente.grafo);
      }
    }
    estado.modo = estado.seleccion.size > 1 ? "paralelo" : "auto";
  } else if (tipo === "faltante") {
    el.consulta.value = "¿Cuánto vale AAPL?";
    estado.seleccion.clear();
    estado.modo = "auto";
  }
  el.modo.value = estado.modo;
  actualizarSeleccion();
  actualizarContador();
  el.consulta.focus();
}

function inicializar() {
  el.formAcceso.addEventListener("submit", (evento) => {
    evento.preventDefault();
    conectar(el.clave.value);
  });

  el.btnVer.addEventListener("click", () => {
    const visible = el.clave.type === "text";
    el.clave.type = visible ? "password" : "text";
    el.btnVer.textContent = visible ? "Ver" : "Ocultar";
    el.btnVer.setAttribute("aria-label", visible ? "Mostrar clave" : "Ocultar clave");
  });

  el.formConsulta.addEventListener("submit", enviarConsulta);
  el.consulta.addEventListener("input", actualizarContador);
  el.consulta.addEventListener("keydown", (evento) => {
    if (evento.key === "Enter" && !evento.shiftKey) {
      evento.preventDefault();
      el.formConsulta.requestSubmit();
    }
  });

  el.modo.addEventListener("change", cambiarModo);
  el.btnAutomatico.addEventListener("click", () => {
    estado.seleccion.clear();
    estado.modo = "auto";
    el.modo.value = "auto";
    actualizarSeleccion();
  });
  el.btnNueva.addEventListener("click", nuevaConversacion);
  el.btnConfig.addEventListener("click", configurarClave);

  for (const boton of document.querySelectorAll("[data-ejemplo]")) {
    boton.addEventListener("click", () => aplicarEjemplo(boton.dataset.ejemplo));
  }

  const sesionGuardada = sessionStorage.getItem(SESION_STORAGE);
  estado.sessionId = sesionGuardada || crearSesionId();
  sessionStorage.setItem(SESION_STORAGE, estado.sessionId);
  actualizarSesion();
  actualizarContador();
  actualizarAyudaModo();
  renderFlujoAgentes();
  comprobarSalud();

  const claveGuardada = sessionStorage.getItem(CLAVE_STORAGE);
  if (claveGuardada) {
    el.clave.value = claveGuardada;
    conectar(claveGuardada, { silencioso: true });
  } else {
    mostrarAcceso();
  }
}

document.addEventListener("DOMContentLoaded", inicializar);

