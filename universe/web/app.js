import {colores, escena} from "./escena.js";

const $ = id => document.getElementById(id);
const botonesTab = [...document.querySelectorAll("[data-tab]")];
let token = "";
const modoWeb = location.pathname === "/chat" ? "chat" : "studio";
const idInterfaz = Array.from(crypto.getRandomValues(new Uint8Array(12)),
  byte => byte.toString(16).padStart(2, "0")).join("");
document.body.dataset.interfaz = modoWeb === "chat" ? "chat" : "estudio";
const esChat = modoWeb === "chat";
document.title = esChat ? "Cerebro Chat" : "Cerebro Studio";
$("marca-modo").textContent = esChat ? "Chat" : "Studio";
$(esChat ? "enlace-chat" : "enlace-proyecto").setAttribute("aria-current", "page");

function anunciar(visible, enfocar = false) {
  if (!token) return;
  fetch("/api/interfaz", {method: "POST", keepalive: true, headers: {
    Authorization: "Bearer " + token, "Content-Type": "application/json",
  }, body: JSON.stringify({id: idInterfaz, modo: modoWeb, visible, enfocar})}).catch(() => {});
}
let acompananteSolicitado = false;
function activarVista() {
  acompananteSolicitado = false;
  anunciar(!document.hidden && document.hasFocus(), true);
}
document.addEventListener("visibilitychange", activarVista);
window.addEventListener("focus", activarVista);
window.addEventListener("blur", () => anunciar(false));
window.addEventListener("pagehide", () => anunciar(false));
setInterval(() => {
  if (!acompananteSolicitado && !document.hidden && document.hasFocus()) anunciar(true);
}, 2000);
let vista = "studio";
let cambioVista = 0;
let nodos = [];
let formas = [];
let trazo = null;
let canvasCargado = false;
let sondeoOcupado = false;
let chatOcupado = false;
let chatActivo = null;
let revisionVisible = null;
let proyectoActivo = "";
let documentoVisible = null;
let archivoAbierto = null;
let original = "";
let inventarioProyecto = [];
let carpetaActual = "";
let revisionArchivo = 0;
let firmaArchivos = "";
let proyectoRecordado = null;

async function api(ruta, datos) {
  const headers = {Authorization: "Bearer " + token};
  const opciones = {headers, cache: "no-store"};
  if (datos !== undefined) {
    headers["Content-Type"] = "application/json";
    opciones.method = "POST";
    opciones.body = JSON.stringify(datos);
  }
  const respuesta = await fetch("/api/" + ruta, opciones);
  const salida = await respuesta.json();
  if (!respuesta.ok) throw new Error(salida.error || "Error de conexión.");
  return salida;
}

function aviso(texto = "") { $("aviso").textContent = texto; }

async function ejecutar(boton, operacion) {
  boton.disabled = true;
  aviso();
  try { await operacion(); }
  catch (error) { aviso(error.message); }
  finally { boton.disabled = false; }
}

function lista(contenedor, datos, crear) { contenedor.replaceChildren(...datos.map(crear)); }
function boton(texto, accion) {
  const elemento = document.createElement("button");
  elemento.type = "button";
  elemento.textContent = texto;
  elemento.addEventListener("click", () => ejecutar(elemento, accion));
  return elemento;
}

function grafoActivo() { grafico.activar(vista === "universe" && $("activar-grafo").checked); }

async function mostrar(tab) {
  const cambio = ++cambioVista;
  if (tab === "canvas" && !canvasCargado) {
    const dibujo = await api("canvas");
    if (cambio !== cambioVista) return;
    formas = dibujo.formas;
    canvasCargado = true;
    redibujar();
  }
  vista = tab;
  for (const elemento of botonesTab) {
    const activo = elemento.dataset.tab === tab;
    elemento.setAttribute("aria-pressed", activo);
    $(elemento.dataset.tab).hidden = !activo;
  }
  grafoActivo();
  await sondear();
}

async function conectar(nuevaClave) {
  token = nuevaClave;
  try { await estado(); }
  catch (error) {
    token = "";
    sessionStorage.removeItem("cerebro-sesion");
    throw error;
  }
  sessionStorage.setItem("cerebro-sesion", token);
  $("acceso").hidden = true;
  $("clave").value = "";
  $("conexion").textContent = "Núcleo conectado";
  $("metricas").hidden = false;
  activarVista();
  await mostrar(location.pathname === "/universe" ? "universe" : "studio");
  cargarConversacion(await api("conversaciones"));
  if (modoWeb === "studio") {
    await actualizarArchivos();
    if (!$("elegir-proyecto").disabled) {
      proyectoRecordado = await solicitarProyecto("recordado");
      $("recuperar-proyecto").hidden = !proyectoRecordado.carpeta;
    }
  }
}

$("acceso").addEventListener("submit", evento => {
  evento.preventDefault();
  ejecutar(evento.submitter, () => conectar($("clave").value.trim()));
});
for (const elemento of botonesTab) elemento.addEventListener("click", () => {
  if (token) ejecutar(elemento, () => mostrar(elemento.dataset.tab));
});
const claveDelEnlace = location.hash.slice(1);
const claveInicial = claveDelEnlace || sessionStorage.getItem("cerebro-sesion");
if (claveDelEnlace) history.replaceState(null, "", location.pathname);
if (claveInicial) conectar(claveInicial).catch(error => aviso(error.message));

$("ir-universe").addEventListener("click", () => ejecutar($("ir-universe"), async () => {
  if (!token) return;
  if (modoWeb === "chat") {
    await api("escritorio", {accion: "universe"});
    anunciar(false);
  } else {
    await mostrar("universe");
  }
}));

$("abrir-terminal").addEventListener("click", () => ejecutar($("abrir-terminal"), async () => {
  await api("escritorio", {accion: "terminal"});
  anunciar(false);
  aviso("Terminal solicitada.");
}));
$("mostrar-acompanante").addEventListener("click", () => ejecutar($("mostrar-acompanante"), async () => {
  await api("escritorio", {accion: "acompanante"});
  acompananteSolicitado = true;
  anunciar(false);
}));

async function estado() {
  const datos = await api("estado");
  const mib = bytes => (bytes / 1048576).toLocaleString("es", {maximumFractionDigits: 1}) + " MiB";
  const metricas = [datos.perfil, datos.entorno.cpus_logicas + " CPU",
    datos.entorno.ram_bytes ? mib(datos.entorno.ram_bytes) + " RAM" : "RAM sin medir",
    datos.entorno.gpu === null ? "GPU sin medir" : datos.entorno.gpu.length + " GPU DRM · inferencia en CPU",
    mib(datos.entorno.disco_libre_bytes) + " libres", mib(datos.uso) + " / " + mib(datos.cuota) + " en Studio y Canvas",
    datos.recuerdos + " recuerdos", datos.parametros ? datos.parametros.toLocaleString("es") + " parámetros" : "Herramientas locales",
    datos.checkpoint.val_bpb === undefined ? "" : datos.checkpoint.val_bpb + " bits/byte (validación del checkpoint)",
    datos.internet ? "Wikipedia habilitada" : "Internet desactivado",
    datos.p50_ms === null ? "Latencia sin medir" : datos.p50_ms + " ms p50 · " + datos.turnos_medidos + " turnos"];
  $("metricas").textContent = metricas.filter(Boolean).join("  ·  ");
  const origen = datos.identidad.creador ? "Creador declarado: " + datos.identidad.creador : "Identidad sin configurar";
  $("identidad").textContent = origen + " · " + (datos.solo_lectura ? "Solo lectura" : datos.permisos.join(", "));
  $("elegir-proyecto").disabled = !datos.proyectos_autorizables;
  if (!datos.proyectos_autorizables) $("proyecto-activo").textContent = "Abre con el lanzador de escritorio para autorizar carpetas.";

}

async function sondear() {
  if (!token || sondeoOcupado || document.hidden) return;
  sondeoOcupado = true;
  try {
    await estado();
    if (chatActivo !== null && !chatOcupado) {
      const version = await api("conversacion-activa");
      if (version.activa !== chatActivo || version.revision !== revisionVisible) {
        const datos = await api("conversaciones");
        if (!chatOcupado) cargarConversacion(datos);
      }
    }
    if (vista === "studio" && modoWeb === "studio") {
      await actualizarTareas();
      if (proyectoActivo) await actualizarArchivos();
    }
    if (vista === "universe") {
      nodos = (await api("nodos")).nodos;
      filtrar();
    }
    if (vista === "body") representarBody(await api("body"));
  } catch (error) { aviso(error.message); }
  finally { sondeoOcupado = false; }
}
setInterval(sondear, 3000);

function agregarMensaje(rol, texto) {
  const mensaje = document.createElement("p");
  mensaje.className = rol === "Tú" ? "usuario" : "cerebro";
  const autor = document.createElement("strong");
  autor.textContent = rol;
  mensaje.append(autor);
  const cuerpo = document.createElement("span");
  mensaje.append(cuerpo);
  const partes = rol === "Cerebro" ? texto.split(/(https:\/\/[^\s<>"']+)/u) : [texto];
  for (const [indice, parte] of partes.entries()) {
    if (indice % 2 === 0) {
      cuerpo.append(parte);
      continue;
    }
    const enlace = document.createElement("a");
    enlace.href = parte;
    enlace.textContent = parte;
    enlace.target = "_blank";
    enlace.rel = "noopener noreferrer";
    cuerpo.append(enlace);
  }
  $("mensajes").append(mensaje);
  if ($("mensajes").children.length > 100) $("mensajes").firstElementChild.remove();
  $("mensajes").scrollTop = $("mensajes").scrollHeight;
}

async function conversar(texto) {
  if (chatOcupado) return false;
  chatOcupado = true;
  const controles = [$("enviar-chat"), $("ver-chats"), $("borrar-chat"), $("nuevo-chat"), $("lista-chats"), ...document.querySelectorAll("[data-chat]")];
  controles.forEach(control => { control.disabled = true; });
  $("estado-chat").hidden = false;
  $("cancelar-coordinacion").hidden = esChat;
  activarVista();
  try {
    if ((await api("conversacion-activa")).activa !== chatActivo) {
      cargarConversacion(await api("conversaciones"));
      throw new Error("La conversación cambió en otra interfaz. Revisa el chat y vuelve a enviar el mensaje.");
    }
    if (!esChat && proyectoActivo && /^(?:cerebro[, ]+)?crea (?:una )?p[aá]gina web[.!]?$/iu.test(texto)) {
      const nombre = prompt("Confirma el nombre de la página estática nueva", prefijoProyecto() + "index.html");
      if (!nombre) return false;
      const creado = await solicitarProyecto("crear_pagina", {nombre, confirmar: true});
      agregarMensaje("Tú", texto);
      agregarMensaje("Cerebro", "Creé «" + creado.archivo + "». Puedes abrirlo desde el explorador.");
      await actualizarArchivos();
      if (!cambiosPendientes()) await abrirArchivo(creado.archivo);
      return true;
    }
    const carpetaPropuesta = proyectoActivo;
    const documento = !esChat && documentoVisible?.carpeta === proyectoActivo ? documentoVisible : null;
    const salida = await api("chat", {mensaje: texto, modo: modoWeb, cliente: idInterfaz,
      conversacion: chatActivo, documento});
    if (!esChat && salida.documento && documento === documentoVisible) {
      const area = $("resultado-central");
      area.replaceChildren(elementoTexto("h2", salida.documento.archivo),
        elementoTexto("pre", salida.respuesta));
      if (salida.documento.ejercicio) {
        area.append(boton("Responder ejercicio", async () => {
          if (documentoVisible !== documento) return;
          const respuesta = prompt(salida.documento.ejercicio.pregunta);
          if (!respuesta?.trim()) return;
          const guardar = confirm("¿Guardar el resultado en el progreso?");
          const nota = await solicitarProyecto("responder_ejercicio", {respuesta, guardar});
          if (documentoVisible === documento) area.append(elementoTexto("p", nota.salida));
        }));
      }
      central("resultado-central");
    }
    if (salida.revision_anterior === revisionVisible) revisionVisible = salida.revision;
    $("sugerencias-chat").hidden = true;
    agregarMensaje("Tú", texto);
    agregarMensaje("Cerebro", salida.respuesta);
    if (!esChat) {
      if (salida.generacion && carpetaPropuesta === proyectoActivo) {
        const propuesta = salida.generacion;
        const area = $("resultado-central");
        area.replaceChildren(elementoTexto("h2", "Propuesta de archivos"), elementoTexto("pre", propuesta.diff),
          boton("Guardar propuesta revisada", async () => {
            if (carpetaPropuesta !== proyectoActivo) throw new Error("La carpeta del proyecto cambió.");
            const nombre = prompt("Nombre de la carpeta nueva", "proyecto-generado");
            if (!nombre?.trim()) return;
            const publicado = await solicitarProyecto("publicar_generado",
              {nombre, id: propuesta.id, confirmar: true}, carpetaPropuesta);
            await actualizarArchivos();
            if (!cambiosPendientes()) await abrirArchivo(publicado.archivos.find(n => n.endsWith(".html")) || publicado.archivos[0]);
            aviso("Archivos creados. Las pruebas se ejecutan por separado.");
          }));
        central("resultado-central");
      } else {
        presentarResultados(salida);
      }
      if (salida.vista === "universe") await mostrar("universe");
      if (salida.vista === "robot") await mostrar("body");
    }
    if (salida.abrir === "studio" && modoWeb === "chat") location.assign("/proyecto");
    return true;
  } finally {
    chatOcupado = false;
    controles.forEach(control => { control.disabled = false; });
    $("estado-chat").hidden = true;
    $("cancelar-coordinacion").hidden = true;
  }
}

function cargarConversacion(datos) {
  chatActivo = datos.activa;
  revisionVisible = datos.revision;
  const chats = [...datos.chats];
  if (!chats.some(chat => chat.id === chatActivo)) chats.unshift({id: chatActivo, titulo: "Conversación actual"});
  $("lista-chats").replaceChildren(...chats.map(chat => new Option(chat.titulo, chat.id)));
  $("lista-chats").value = chatActivo;
  $("mensajes").replaceChildren();
  for (const turno of datos.turnos) agregarMensaje(turno.rol === "usuario" ? "Tú" : "Cerebro", turno.texto);
  $("sugerencias-chat").hidden = modoWeb !== "chat" || datos.turnos.length > 0;
}

function gestionarChat(boton, operacion) {
  if (chatOcupado) return;
  chatOcupado = true;
  const controles = ["enviar-chat", "nuevo-chat", "borrar-chat", "lista-chats"].map($);
  controles.forEach(control => { control.disabled = true; });
  ejecutar(boton, async () => {
    try {
      cargarConversacion(await operacion());
    } finally {
      $("lista-chats").value = chatActivo;
      controles.forEach(control => { control.disabled = false; });
      chatOcupado = false;
    }
  });
}

$("nuevo-chat").addEventListener("click", () => gestionarChat($("nuevo-chat"),
  () => api("conversaciones", {accion: "nueva"})));
$("lista-chats").addEventListener("change", () => gestionarChat($("lista-chats"),
  () => api("conversaciones", {accion: "seleccionar", id: $("lista-chats").value})));
$("borrar-chat").addEventListener("click", () => {
  if (chatOcupado || !window.confirm("¿Eliminar la conversación actual?")) return;
  gestionarChat($("borrar-chat"), async () => {
    await api("historial", {confirmar: true, id: chatActivo});
    return api("conversaciones");
  });
});

const gestorChats = $("gestor-chats");
const casillasChats = () => [...$("chats-guardados").querySelectorAll("input")];
function actualizarSeleccionChats() {
  const casillas = casillasChats();
  const cantidad = casillas.filter(casilla => casilla.checked).length;
  $("marcar-chats").checked = cantidad > 0 && cantidad === casillas.length;
  $("marcar-chats").indeterminate = cantidad > 0 && cantidad < casillas.length;
  $("marcar-chats").disabled = casillas.length === 0;
  $("cantidad-chats").textContent = cantidad + " de " + casillas.length + " seleccionados";
  $("borrar-chats-marcados").disabled = cantidad === 0;
  $("abrir-chat-marcado").disabled = cantidad !== 1;
}

$("ver-chats").addEventListener("click", () => ejecutar($("ver-chats"), async () => {
  const datos = await api("conversaciones");
  $("chats-guardados").replaceChildren(...datos.chats.map(chat => {
    const fila = document.createElement("li");
    const etiqueta = document.createElement("label");
    const casilla = document.createElement("input");
    casilla.type = "checkbox";
    casilla.value = chat.id;
    etiqueta.append(casilla, " " + chat.titulo + (chat.id === datos.activa ? " · Actual" : ""));
    fila.append(etiqueta);
    return fila;
  }));
  $("aviso-chats").textContent = datos.chats.length ? "" : "Todavía no hay conversaciones guardadas.";
  actualizarSeleccionChats();
  gestorChats.showModal();
}));
$("chats-guardados").addEventListener("change", actualizarSeleccionChats);
$("marcar-chats").addEventListener("change", evento => {
  for (const casilla of casillasChats()) casilla.checked = evento.target.checked;
  actualizarSeleccionChats();
});

function operarChats(boton, borrar) {
  const ids = casillasChats().filter(casilla => casilla.checked).map(casilla => casilla.value);
  if (chatOcupado || (borrar ? !ids.length : ids.length !== 1)) return;
  if (borrar && !window.confirm("¿Eliminar " + ids.length + " conversaciones seleccionadas?")) return;
  gestionarChat(boton, async () => {
    try {
      const datos = borrar ? await api("borrar-conversaciones", {confirmar: true, ids})
        : await api("conversaciones", {accion: "seleccionar", id: ids[0]});
      gestorChats.close();
      if (borrar) aviso("Conversaciones eliminadas: " + datos.eliminadas + ".");
      return datos;
    } catch (error) {
      $("aviso-chats").textContent = error.message;
      throw error;
    }
  });
}

$("abrir-chat-marcado").addEventListener("click", evento => operarChats(evento.currentTarget, false));
$("borrar-chats-marcados").addEventListener("click", evento => operarChats(evento.currentTarget, true));

const compositor = $("mensaje");
compositor.addEventListener("keydown", evento => {
  if (evento.key === "Enter" && !evento.shiftKey && !evento.isComposing) {
    evento.preventDefault();
    if (!chatOcupado) $("chat").requestSubmit($("enviar-chat"));
  }
});
$("chat").addEventListener("submit", evento => {
  evento.preventDefault();
  const borrador = compositor.value;
  const texto = borrador.trim();
  if (!texto || chatOcupado) return;
  ejecutar($("enviar-chat"), async () => {
    if (await conversar(texto) && compositor.value === borrador) compositor.value = "";
  });
});
for (const elemento of document.querySelectorAll("[data-chat]"))
  elemento.addEventListener("click", () => ejecutar(elemento, () => conversar(elemento.dataset.chat)));

function descargar(nombre, mime, texto) {
  const url = URL.createObjectURL(new Blob([texto], {type: mime}));
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$("exportar").addEventListener("click", () => ejecutar($("exportar"), async () => {
  const memoria = await api("memoria");
  descargar("cerebro-memoria.json", "application/json", JSON.stringify(memoria, null, 2));
}));
$("importar").addEventListener("change", async () => {
  const archivo = $("importar").files[0];
  if (!archivo) return;
  try {
    if (archivo.size > 6 * 1048576) throw new Error("El respaldo supera 6 MiB.");
    const salida = await api("memoria", JSON.parse(await archivo.text()));
    aviso("Recuerdos nuevos: " + salida.importados);
  } catch (error) { aviso(error.message); }
  finally { $("importar").value = ""; }
});

let videoLocal;
$("adjunto").addEventListener("change", async () => {
  const archivo = $("adjunto").files[0];
  if (!archivo) return;
  try {
    if (/\.(?:mp4|mov|webm|mkv)$/i.test(archivo.name)) {
      const reproductor = $("video-adjunto");
      if (videoLocal) URL.revokeObjectURL(videoLocal);
      videoLocal = URL.createObjectURL(archivo);
      reproductor.src = videoLocal;
      reproductor.hidden = false;
    }
    if (archivo.size > 16 * 1048576) throw new Error("El análisis de adjuntos admite hasta 16 MiB.");
    aviso("Guardando adjunto…");
    const contenido = await new Promise((resolver, rechazar) => {
      const lector = new FileReader();
      lector.onload = () => resolver(lector.result.split(",", 2)[1]);
      lector.onerror = () => rechazar(new Error("No se pudo leer el adjunto."));
      lector.readAsDataURL(archivo);
    });
    const salida = await api("adjunto", {nombre: archivo.name, contenido});
    aviso("Adjunto disponible: " + salida.nombre);
    if (!/\.(?:srt|vtt)$/i.test(salida.nombre)) {
      if (!await conversar("Analiza " + salida.nombre)) {
        aviso("Adjunto disponible. Cuando termine la consulta, escribe «Analiza " + salida.nombre + "».");
      }
    }
  } catch (error) { aviso(error.message); }
  finally { $("adjunto").value = ""; }
});

function central(id) {
  for (const control of document.querySelectorAll("[data-central]")) {
    const activo = control.dataset.central === id;
    control.setAttribute("aria-pressed", String(activo));
    $(control.dataset.central).hidden = !activo;
  }
}
for (const control of document.querySelectorAll("[data-central]")) {
  control.addEventListener("click", () => central(control.dataset.central));
}

const historialWeb = [];
let indiceWeb = -1;

function mostrarWeb() {
  if (indiceWeb < 0) return;
  const url = historialWeb[indiceWeb];
  $("direccion-web").value = url;
  $("marco-web").src = url;
  $("web-atras").disabled = indiceWeb === 0;
  $("web-adelante").disabled = indiceWeb === historialWeb.length - 1;
}

$("navegar-web").addEventListener("submit", evento => {
  evento.preventDefault();
  ejecutar(evento.submitter, async () => {
    const estado = await api("estado");
    if (!estado.internet) throw new Error("Activa Internet en el núcleo antes de abrir direcciones externas.");
    const url = new URL($("direccion-web").value);
    if (url.protocol !== "https:" || url.username || url.password) {
      throw new Error("Introduce una URL HTTPS sin credenciales.");
    }
    historialWeb.splice(indiceWeb + 1, historialWeb.length, url.href);
    if (historialWeb.length > 30) historialWeb.shift();
    indiceWeb = historialWeb.length - 1;
    mostrarWeb();
  });
});
$("web-atras").addEventListener("click", () => { if (indiceWeb > 0) { indiceWeb--; mostrarWeb(); } });
$("web-adelante").addEventListener("click", () => { if (indiceWeb < historialWeb.length - 1) { indiceWeb++; mostrarWeb(); } });
$("web-recargar").addEventListener("click", mostrarWeb);

function elementoTexto(etiqueta, texto) {
  const nodo = document.createElement(etiqueta);
  nodo.textContent = texto;
  return nodo;
}

function presentarResultados(datos) {
  const resultados = datos.especialistas || (datos.experiencias || []).flatMap(exp => exp.resultados);
  if (!resultados.length) return;
  const area = $("resultado-central");
  area.replaceChildren(elementoTexto("h2", "Resultados y evidencias"));
  for (const resultado of resultados) {
    const detalle = document.createElement("details");
    detalle.open = true;
    detalle.append(elementoTexto("summary", resultado.especialista + " · " + resultado.estado));
    if (resultado.error) detalle.append(elementoTexto("p", resultado.error));
    if (resultado.plan) {
      const listaPlan = document.createElement("ol");
      for (const paso of resultado.plan) listaPlan.append(elementoTexto("li", paso.titulo + " · " + (paso.estado || "previsto")));
      detalle.append(listaPlan);
    }
    if (resultado.simulacion) {
      const sim = resultado.simulacion;
      detalle.append(elementoTexto("p", "Simulación · " + sim.supuestos));
      for (const clave of ["p50", "p90"]) {
        const valor = sim[clave + "_horas"];
        const medidor = document.createElement("meter");
        medidor.max = Math.max(1, sim.p90_horas, sim.p50_horas);
        medidor.value = valor;
        medidor.setAttribute("aria-label", clave + " · " + valor + " horas");
        detalle.append(elementoTexto("p", clave + " · " + valor + " h"), medidor);
      }
    }
    for (const ev of resultado.evidencia || []) {
      if (ev.tipo === "fuente") {
        const fuente = elementoTexto("p", ev.titulo + " · " + ev.url);
        if (ev.extracto) fuente.append(elementoTexto("small", " " + ev.extracto));
        detalle.append(fuente);
      } else {
        detalle.append(elementoTexto("pre", JSON.stringify(ev, null, 2)));
      }
    }
    if (resultado.sesion) detalle.append(elementoTexto("p", "Sesión de revisión en CAZEL Studio: " + resultado.sesion));
    if (resultado.ejercicio) detalle.append(elementoTexto("p", resultado.ejercicio.pregunta));
    if (resultado.evaluacion) detalle.append(elementoTexto("p", resultado.evaluacion.detalle));
    for (const advertencia of resultado.avisos || []) detalle.append(elementoTexto("p", advertencia));
    area.append(detalle);
  }
  central("resultado-central");
}

function solicitarProyecto(accion, datos = {}, esperado = proyectoActivo) {
  return api("proyecto", {accion, cliente: idInterfaz, carpeta_esperada: esperado, ...datos});
}
function prefijoProyecto() { return carpetaActual ? carpetaActual + "/" : ""; }
function cambiosPendientes() { return $("contenido").value !== original.replace(/\r\n?/g, "\n"); }

function presentarArchivo(datos, ancla = null) {
  const area = $("visor-central");
  area.replaceChildren(elementoTexto("h2", datos.archivo));
  if (datos.aviso) area.append(elementoTexto("p", datos.aviso));
  if (["imagen", "pdf"].includes(datos.visor) && datos.base64) {
    const formatos = {".png": "png", ".gif": "gif", ".jpg": "jpeg", ".jpeg": "jpeg", ".webp": "webp", ".pdf": "png"};
    const tipo = formatos[datos.extension];
    if (tipo) {
      const imagen = document.createElement("img");
      imagen.alt = datos.archivo;
      imagen.src = "data:image/" + tipo + ";base64," + datos.base64;
      const controles = document.createElement("div");
      controles.className = "acciones";
      const superficie = document.createElement("div");
      superficie.className = "visor-desplazable";
      superficie.append(imagen);
      area.append(controles, superficie);
      const referente = documentoVisible;
      let peticion = 0;
      let zoom = 1;
      let escalaPrevia = null;
      const pdf = datos.visor === "pdf";
      imagen.draggable = false;
      const anclar = (centro) => {
        if (!centro) return;
        superficie.scrollLeft = centro.u * imagen.offsetWidth - centro.x;
        superficie.scrollTop = centro.v * imagen.offsetHeight - centro.y;
      };
      if (ancla) imagen.addEventListener("load", () => anclar(ancla), {once: true});
      const solicitarVista = async (pagina, resolucion, centro = null) => {
        const turno = ++peticion;
        const vista = await solicitarProyecto("inspeccionar", {nombre: datos.archivo, pagina,
          resolucion: resolucion === 0 ? 0 : Math.max(128, Math.min(2200, resolucion))}, referente.carpeta);
        if (turno === peticion && documentoVisible === referente) presentarArchivo(vista, centro);
      };
      if (pdf && referente) {
        const anterior = boton("Página anterior", () => solicitarVista(datos.pagina - 1, datos.resolucion));
        const siguiente = boton("Página siguiente", () => solicitarVista(datos.pagina + 1, datos.resolucion));
        anterior.disabled = datos.pagina <= 1;
        siguiente.disabled = datos.pagina >= datos.paginas;
        controles.append(anterior, elementoTexto("span", datos.pagina + " / " + datos.paginas), siguiente,
          boton("Buscar en PDF", async () => {
            const consulta = prompt("Texto a buscar");
            if (!consulta?.trim()) return;
            const resultado = await solicitarProyecto("buscar_pdf", {nombre: datos.archivo, consulta}, referente.carpeta);
            if (documentoVisible !== referente) return;
            aviso("Páginas con coincidencias: " + (resultado.coincidencias.map(x => x.pagina).join(", ") || "ninguna") +
              ". Revisadas: " + resultado.revisadas + " de " + resultado.paginas + ".");
          }),
          boton("Ajustar ancho", () => solicitarVista(datos.pagina,
            Math.round(datos.resolucion * (superficie.clientWidth - 12) / (imagen.naturalWidth || datos.resolucion)))),
          boton("Ajustar página", () => solicitarVista(datos.pagina, Math.round(datos.resolucion * Math.min(
            (superficie.clientWidth - 12) / (imagen.naturalWidth || datos.resolucion),
            (innerHeight * .60) / (imagen.naturalHeight || datos.resolucion))))));
      }
      const escalarImagen = (factor) => {
        zoom = Math.max(.05, Math.min(4, factor));
        imagen.style.width = Math.round(imagen.naturalWidth * zoom) + "px";
      };
      const ajustarImagen = (soloAncho) => escalarImagen(Math.min(
        superficie.clientWidth / imagen.naturalWidth,
        soloAncho ? Infinity : innerHeight * .60 / imagen.naturalHeight));
      const cambiarZoom = async (paso, evento = null) => {
        const factor = paso > 0 ? 1.25 : .8;
        const rect = superficie.getBoundingClientRect();
        const x = evento ? evento.clientX - rect.left : superficie.clientWidth / 2;
        const y = evento ? evento.clientY - rect.top : superficie.clientHeight / 2;
        const centro = {u: (superficie.scrollLeft + x) / (imagen.offsetWidth || 1),
          v: (superficie.scrollTop + y) / (imagen.offsetHeight || 1), x, y};
        if (pdf && referente) {
          return solicitarVista(datos.pagina, paso === 0 ? 0 : Math.round(datos.resolucion * factor), centro);
        }
        escalaPrevia = null;
        escalarImagen(paso === 0 ? 1 : zoom * factor);
        anclar(centro);
      };
      if (!pdf) {
        controles.append(boton("Ajustar ancho", () => ajustarImagen(true)),
          boton("Ajustar ventana", () => ajustarImagen(false)));
      }
      controles.append(boton("Reducir", () => cambiarZoom(-1)), boton("Ampliar", () => cambiarZoom(1)),
        boton("100 %", () => cambiarZoom(0)));
      superficie.addEventListener("wheel", evento => {
        if (!evento.deltaY) return;
        evento.preventDefault();
        cambiarZoom(evento.deltaY < 0 ? 1 : -1, evento).catch(error => aviso(error.message));
      }, {passive: false});
      let arrastre;
      imagen.addEventListener("pointerdown", evento => {
        if (evento.button !== 0) return;
        arrastre = [evento.clientX, evento.clientY, superficie.scrollLeft, superficie.scrollTop];
        imagen.setPointerCapture(evento.pointerId);
      });
      imagen.addEventListener("pointermove", evento => {
        if (!arrastre) return;
        superficie.scrollLeft = arrastre[2] - evento.clientX + arrastre[0];
        superficie.scrollTop = arrastre[3] - evento.clientY + arrastre[1];
      });
      imagen.addEventListener("lostpointercapture", () => { arrastre = null; });
      imagen.addEventListener("dblclick", () => {
        if (pdf) {
          const escala = Math.min(superficie.clientWidth / imagen.naturalWidth, innerHeight * .60 / imagen.naturalHeight);
          solicitarVista(datos.pagina, Math.round(datos.resolucion * escala)).catch(error => aviso(error.message));
        } else if (escalaPrevia === null) {
          escalaPrevia = zoom;
          ajustarImagen(false);
        } else {
          escalarImagen(escalaPrevia);
          escalaPrevia = null;
        }
      });
      const info = document.createElement("details");
      info.append(elementoTexto("summary", "Información del archivo"),
        elementoTexto("pre", datos.bytes + " bytes" + (datos.texto ? "\n\n" + datos.texto : "")));
      area.append(info);
    }
  } else if (datos.fragmentos) {
    const vistaHTML = document.createElement("div");
    vistaHTML.className = "html-estatico";
    area.append(elementoTexto("p", "Vista estática · sin scripts ni recursos externos"), vistaHTML);
    for (const [texto, etiqueta] of datos.fragmentos) {
      vistaHTML.append(elementoTexto(etiqueta === "titulo" ? "strong" : "span", texto));
    }
  } else if (datos.filas) {
    const tabla = document.createElement("table");
    for (const fila of datos.filas) {
      const tr = document.createElement("tr");
      tr.append(...fila.map(celda => elementoTexto("td", celda)));
      tabla.append(tr);
    }
    area.append(tabla);
  } else if (datos.texto !== undefined) {
    area.append(elementoTexto("pre", datos.texto));
  }
  if (datos.app_externa) {
    const esperado = proyectoActivo;
    area.append(boton("Abrir en aplicación local", async () => {
      if (!confirm("¿Abrir el documento en la aplicación predeterminada?")) return;
      const respuesta = await solicitarProyecto("abrir_externo", {nombre: datos.archivo, confirmar: true}, esperado);
      aviso(respuesta.salida);
    }));
  }
  central("visor-central");
}

async function abrirArchivo(nombre) {
  if (cambiosPendientes() && !confirm("¿Abrir otro archivo y descartar los cambios sin guardar?")) return;
  const revision = ++revisionArchivo;
  const esperado = proyectoActivo;
  const contenidoPrevio = $("contenido").value;
  const datos = esperado ? await solicitarProyecto("inspeccionar", {nombre}, esperado)
    : await api("archivo?nombre=" + encodeURIComponent(nombre));
  if (esperado !== proyectoActivo || revision !== revisionArchivo || contenidoPrevio !== $("contenido").value) return;
  documentoVisible = esperado ? {nombre, carpeta: esperado} : null;
  archivoAbierto = (datos.visor === "texto" && !datos.solo_lectura) || !esperado ? nombre : null;
  original = archivoAbierto ? datos.texto : "";
  $("contenido").value = original;
  $("contenido").readOnly = Boolean(esperado && !archivoAbierto);
  $("archivo").value = nombre;
  $("archivo-activo").textContent = nombre;
  if (esperado && (datos.visor !== "texto" || datos.solo_lectura || [".html", ".md", ".csv", ".tsv"].includes(datos.extension))) {
    presentarArchivo(datos);
  } else central("editor-central");
  if (esperado) await solicitarProyecto("recordar", {nombre}, esperado);
}

function pintarArchivos() {
  const filtro = $("filtro-archivos").value.trim().toLocaleLowerCase("es");
  const tipo = $("tipo-archivo").value;
  const entradas = inventarioProyecto.filter(({ruta, tipo: clase}) => {
    const formato = clase === "carpeta" ? "carpeta" : /\.(png|gif|jpe?g|webp)$/iu.test(ruta) ? "imagen"
      : /\.pdf$/iu.test(ruta) ? "pdf" : "texto";
    return (!tipo || formato === tipo) && (filtro ? ruta.toLocaleLowerCase("es").includes(filtro)
      : ruta.split("/").slice(0, -1).join("/") === carpetaActual);
  });
  const firma = JSON.stringify([carpetaActual, entradas]);
  if (firma === firmaArchivos) return;
  firmaArchivos = firma;
  lista($("archivos"), entradas, ({ruta, tipo: clase}) => boton(ruta + (clase === "carpeta" ? "/" : ""), async () => {
    if (clase === "carpeta") {
      carpetaActual = ruta;
      $("filtro-archivos").value = "";
      pintarArchivos();
    } else await abrirArchivo(ruta);
  }));
  if (carpetaActual) $("archivos").prepend(boton("Subir carpeta", async () => {
    carpetaActual = carpetaActual.split("/").slice(0, -1).join("/");
    pintarArchivos();
  }));
}

async function actualizarArchivos() {
  const esperado = proyectoActivo;
  const datos = esperado ? await solicitarProyecto("listar", {}, esperado) : await api("archivos");
  if (esperado !== proyectoActivo) return;
  inventarioProyecto = datos.entradas || datos.archivos.map(ruta => ({ruta, tipo: "archivo"}));
  pintarArchivos();
}

async function abrirProyecto(carpeta) {
  if (!carpeta || !confirm("¿Autorizar esta carpeta en Studio? " + carpeta)) return false;
  if (cambiosPendientes() && !confirm("¿Descartar los cambios sin guardar?")) return false;
  const datos = await solicitarProyecto("abrir", {carpeta, confirmar: true});
  proyectoActivo = datos.carpeta;
  documentoVisible = null;
  carpetaActual = "";
  archivoAbierto = null;
  original = "";
  $("contenido").value = "";
  $("contenido").readOnly = false;
  $("archivo").value = "";
  $("archivo-activo").textContent = "Sin archivo abierto";
  $("proyecto-activo").textContent = proyectoActivo;
  for (const id of ["gestionar-proyecto", "analizar-proyecto", "pruebas-proyecto"]) $(id).hidden = false;
  await solicitarProyecto("recordar");
  await actualizarArchivos();
  central("editor-central");
  return true;
}

$("elegir-proyecto").addEventListener("click", () => ejecutar($("elegir-proyecto"), async () => {
  const carpeta = prompt("Carpeta absoluta de proyecto");
  if (carpeta) await abrirProyecto(carpeta);
}));
$("recuperar-proyecto").addEventListener("click", () => ejecutar($("recuperar-proyecto"), async () => {
  const anterior = proyectoRecordado;
  if (anterior?.carpeta && await abrirProyecto(anterior.carpeta) && anterior.archivo) {
    await abrirArchivo(anterior.archivo);
  }
}));
$("consultar-seleccion").addEventListener("click", () => ejecutar($("consultar-seleccion"), async () => {
  const editor = $("contenido");
  const texto = editor.value.slice(editor.selectionStart, Math.min(editor.selectionEnd, editor.selectionStart + 4000));
  if (!proyectoActivo || !archivoAbierto || !texto) throw new Error("Selecciona código en un proyecto autorizado.");
  const pregunta = prompt("Pregunta sobre la selección", "Explícame este fragmento");
  if (!pregunta) return;
  const resultado = await solicitarProyecto("fragmento", {nombre: archivoAbierto, texto, pregunta});
  agregarMensaje("Tú", pregunta);
  agregarMensaje("Cerebro", resultado.respuesta);
}));
$("filtro-archivos").addEventListener("input", pintarArchivos);
$("tipo-archivo").addEventListener("change", pintarArchivos);

for (const control of document.querySelectorAll("[data-archivo]")) control.addEventListener("click", () => ejecutar(control, async () => {
  if (!proyectoActivo) return;
  const accion = control.dataset.archivo;
  const esNuevo = ["crear", "carpeta"].includes(accion);
  const nombre = prompt(esNuevo ? "Ruta nueva dentro del proyecto" : "Ruta de origen dentro del proyecto",
                        esNuevo ? prefijoProyecto() : $("archivo").value);
  if (!nombre) return;
  const destino = ["mover", "copiar"].includes(accion) ? prompt("Ruta de destino", nombre) : null;
  if (["mover", "copiar"].includes(accion) && (!destino || destino === nombre)) return;
  const afecta = archivoAbierto && (archivoAbierto === nombre || archivoAbierto.startsWith(nombre + "/"));
  if (afecta && cambiosPendientes() && ["mover", "papelera"].includes(accion)) {
    throw new Error("Guarda primero los cambios del archivo abierto.");
  }
  if (accion === "papelera" && !confirm("¿Enviar a la papelera del proyecto? " + nombre)) return;
  const salida = await solicitarProyecto(accion, {nombre, destino, confirmar: true});
  if (afecta && ["mover", "papelera"].includes(accion)) {
    archivoAbierto = null;
    original = "";
    $("contenido").value = "";
    $("archivo-activo").textContent = "Sin archivo abierto";
    $("archivo").value = "";
  }
  await actualizarArchivos();
  aviso(salida.papelera ? "Papelera: " + salida.papelera : "Proyecto actualizado.");
  if (accion === "crear" && !cambiosPendientes()) await abrirArchivo(salida.archivo);
}));

$("abrir-archivo").addEventListener("submit", evento => {
  evento.preventDefault();
  ejecutar(evento.submitter, () => abrirArchivo($("archivo").value.trim()));
});
$("guardar").addEventListener("click", () => ejecutar($("guardar"), async () => {
  const nombre = $("archivo").value.trim();
  const crlf = original.includes("\r\n") && !/(^|[^\r])\n/.test(original);
  const texto = crlf ? $("contenido").value.replace(/\n/g, "\r\n") : $("contenido").value;
  if (proyectoActivo) {
    if (nombre !== archivoAbierto) throw new Error("Abre el archivo desde el explorador antes de guardar.");
    if (!confirm("¿Guardar en el proyecto? " + nombre)) return;
    await solicitarProyecto("guardar", {nombre, texto, original, confirmar: true});
  } else await api("archivo", {nombre, texto});
  original = texto;
  $("archivo-activo").textContent = nombre;
  await actualizarArchivos();
  aviso("Archivo guardado.");
}));

$("analizar-proyecto").addEventListener("click", () => ejecutar($("analizar-proyecto"), async () => {
  const esperado = proyectoActivo;
  const informe = await solicitarProyecto("analizar", {}, esperado);
  if (esperado !== proyectoActivo) return;
  const area = $("resultado-central");
  area.replaceChildren(elementoTexto("h2", "Análisis de proyecto"),
    elementoTexto("p", informe.revisados + " archivos Python revisados."),
    elementoTexto("pre", informe.hallazgos.join("\n")));
  for (const cambio of informe.propuestas) {
    const bloque = document.createElement("details");
    bloque.append(elementoTexto("summary", cambio.archivo), elementoTexto("pre", cambio.diff),
      boton("Aplicar propuesta de " + cambio.archivo, async () => {
        if (esperado !== proyectoActivo) throw new Error("Cambió el proyecto.");
        if (cambiosPendientes()) throw new Error("Guarda primero los cambios del editor.");
        if (!confirm("¿Aplicar el diff mostrado?")) return;
        await solicitarProyecto("aplicar", {id: cambio.id, confirmar: true}, esperado);
        bloque.replaceChildren(elementoTexto("summary", cambio.archivo + " · aplicado"));
        await actualizarArchivos();
        if (archivoAbierto === cambio.archivo) await abrirArchivo(cambio.archivo);
      }));
    area.append(bloque);
  }
  central("resultado-central");
}));
$("pruebas-proyecto").addEventListener("click", () => ejecutar($("pruebas-proyecto"), async () => {
  if (!confirm("¿Ejecutar unittest dentro del aislamiento?")) return;
  await solicitarProyecto("pruebas", {confirmar: true});
  central("pruebas-central");
  await actualizarTareas();
}));
$("cancelar-coordinacion").addEventListener("click", () => ejecutar($("cancelar-coordinacion"), async () => {
  const salida = await api("chat", {mensaje: "Cancela la coordinación", modo: "studio", cliente: idInterfaz});
  aviso(salida.respuesta);
}));

async function actualizarTareas() {
  lista($("tareas"), await api("tareas"), tarea => {
    const detalle = document.createElement("details");
    const resumen = document.createElement("summary");
    resumen.textContent = [tarea.accion, tarea.estado, tarea.ms !== undefined && tarea.ms + " ms"].filter(Boolean).join(" · ");
    const salida = document.createElement("pre");
    salida.textContent = tarea.salida;
    detalle.append(resumen, salida);
    return detalle;
  });
}
for (const elemento of document.querySelectorAll("[data-tarea]")) {
  elemento.addEventListener("click", () => ejecutar(elemento, async () => {
    if (proyectoActivo && elemento.dataset.tarea === "sintaxis") {
      const dato = await solicitarProyecto("validar", {nombre: $("archivo").value.trim()});
      aviso(dato.salida);
    } else {
      await api("tarea", {accion: elemento.dataset.tarea, nombre: $("archivo").value.trim()});
      central("pruebas-central");
      await actualizarTareas();
    }
  }));
}
$("limpiar-tareas").addEventListener("click", () => ejecutar($("limpiar-tareas"), async () => {
  await api("cache", {});
  await actualizarTareas();
}));

let nodoInspeccionado = null;

function inspeccionar(nodo) {
  grafico.seleccionar(nodo.id);
  nodoInspeccionado = nodo;
  const fecha = nodo.fecha ? new Date(nodo.fecha) : null;
  const detalleFecha = fecha && Number.isFinite(fecha.getTime()) ? fecha.toLocaleString("es") : nodo.fecha;
  $("detalle").textContent = [nodo.titulo, "Tipo: " + nodo.tipo,
    "Origen: " + (nodo.origen || "Sin registrar"), "Fecha y hora: " + (detalleFecha || "Sin registrar"), nodo.detalle]
    .filter(Boolean).join("\n");
  $("eliminar-recuerdo").hidden = !nodo.eliminable;
}

$("eliminar-recuerdo").addEventListener("click", () => ejecutar($("eliminar-recuerdo"), async () => {
  const nodo = nodoInspeccionado;
  if (!nodo?.eliminable || !confirm("¿Eliminar este recuerdo? " + nodo.titulo)) return;
  await api("nodos", {id: nodo.id, confirmar: true});
  nodoInspeccionado = null;
  $("eliminar-recuerdo").hidden = true;
  $("detalle").textContent = "Recuerdo eliminado.";
  await mostrar("universe");
}));

const grafico = escena($("cerebro-3d"), inspeccionar);
grafico.rotar($("orbita").checked);
for (const tipo of Object.keys(colores)) {
  $("filtro").add(new Option(tipo, tipo));
  const etiqueta = document.createElement("span");
  etiqueta.style.color = colores[tipo];
  etiqueta.textContent = tipo;
  $("leyenda").append(etiqueta);
}
let firmaNodos = "";
function filtrar() {
  const consulta = $("buscar-nodo").value.trim().toLocaleLowerCase("es");
  const tipo = $("filtro").value;
  const region = $("region-nodo").value;
  const visibles = nodos.filter(nodo => (!tipo || nodo.tipo === tipo) && (!region || nodo.grupo === region) &&
    [nodo.titulo, nodo.detalle, nodo.origen].join(" ").toLocaleLowerCase("es").includes(consulta));
  const firma = JSON.stringify([region, visibles]);
  if (firma === firmaNodos) return;
  firmaNodos = firma;
  lista($("nodos"), visibles, nodo => boton(nodo.titulo, () => inspeccionar(nodo)));
  if (!visibles.length) $("nodos").textContent = "No hay nodos que coincidan.";
  const conexiones = new Set(region ? visibles.flatMap(nodo => nodo.vinculos || []) : []);
  grafico.nodos(region ? nodos.filter(nodo => visibles.includes(nodo) || conexiones.has(nodo.id)) : visibles);
}
$("filtro").addEventListener("change", filtrar);
$("region-nodo").addEventListener("change", filtrar);
$("buscar-nodo").addEventListener("input", filtrar);
$("activar-grafo").addEventListener("change", () => {
  $("cerebro-3d").hidden = !$("activar-grafo").checked;
  grafoActivo();
});
$("orbita").addEventListener("change", () => grafico.rotar($("orbita").checked));

const lienzo = $("lienzo");
const ns = "http://www.w3.org/2000/svg";
const herramientas = {trazo: "polyline", rectangulo: "rect", linea: "line", texto: "text"};

function figura(forma) {
  const etiqueta = herramientas[forma.tipo];
  if (!etiqueta) return null;
  const elemento = document.createElementNS(ns, etiqueta);
  const [x, y] = forma.puntos[0];
  const [u, v] = forma.puntos.at(-1);
  const atributos = forma.tipo === "rectangulo" ? {x: Math.min(x, u), y: Math.min(y, v),
    width: Math.abs(u - x), height: Math.abs(v - y)} : forma.tipo === "linea" ? {x1: x, y1: y, x2: u, y2: v}
      : forma.tipo === "trazo" ? {points: forma.puntos.map(punto => punto.join(",")).join(" ")} : {x, y};
  for (const [nombre, valor] of Object.entries(atributos)) elemento.setAttribute(nombre, valor);
  elemento.setAttribute("stroke-width", "3");
  elemento.setAttribute("stroke-linecap", "round");
  elemento.setAttribute("fill", forma.tipo === "texto" ? forma.color : "none");
  if (forma.tipo === "texto") {
    elemento.textContent = forma.texto;
    elemento.setAttribute("font-family", "sans-serif");
    elemento.setAttribute("font-size", "19");
  } else elemento.setAttribute("stroke", forma.color);
  return elemento;
}

function redibujar() {
  lienzo.replaceChildren(...(trazo ? [...formas, trazo] : formas).map(figura).filter(Boolean));
}

function posicion(evento) {
  const punto = new DOMPoint(evento.clientX, evento.clientY).matrixTransform(lienzo.getScreenCTM().inverse());
  return [Math.round(punto.x), Math.round(punto.y)];
}
lienzo.addEventListener("pointerdown", evento => {
  if (formas.length >= 200 || trazo) return;
  lienzo.setPointerCapture(evento.pointerId);
  trazo = {tipo: $("herramienta").value, color: $("color").value, texto: $("texto-figura").value.slice(0, 180),
    puntos: [posicion(evento)]};
  redibujar();
});
lienzo.addEventListener("pointermove", evento => {
  if (!trazo) return;
  if (trazo.tipo === "trazo" && trazo.puntos.length < 250) trazo.puntos.push(posicion(evento));
  if (trazo.tipo === "linea" || trazo.tipo === "rectangulo") trazo.puntos[1] = posicion(evento);
  redibujar();
});
lienzo.addEventListener("pointerup", () => {
  if (trazo) formas.push(trazo);
  trazo = null;
  redibujar();
});
lienzo.addEventListener("pointercancel", () => {
  trazo = null;
  redibujar();
});
$("deshacer").addEventListener("click", () => { formas.pop(); redibujar(); });
$("organizar").addEventListener("click", () => {
  formas = formas.map((forma, i) => {
    const [x, y] = forma.puntos[0];
    const dx = 40 + (i % 5) * 170 - x;
    const dy = 60 + Math.floor(i / 5) * 85 - y;
    return {...forma, puntos: forma.puntos.map(([px, py]) => [px + dx, py + dy])};
  });
  redibujar();
});
$("guardar-lienzo").addEventListener("click", () => ejecutar($("guardar-lienzo"), async () => {
  await api("canvas", {formas});
  aviso("Lienzo guardado.");
}));
$("exportar-svg").addEventListener("click", () =>
  descargar("cerebro-canvas.svg", "image/svg+xml", new XMLSerializer().serializeToString(lienzo)));

function representarBody(datos) {
  const [x, y] = datos.posicion;
  $("estado-body").textContent = [datos.parado ? "Detenido" : "Armado", Math.round(x) + " cm X",
    Math.round(y) + " cm Y", Math.round(datos.angulo) + "°"].join(" · ");
  $("robot").setAttribute("transform",
    "translate(" + (200 + Math.max(-160, Math.min(160, x))) + " " + (110 + Math.max(-85, Math.min(85, y))) +
    ") rotate(" + datos.angulo + ")");
  $("telemetria").textContent = Object.keys(datos.telemetria).length ? JSON.stringify(datos.telemetria, null, 2) : "Sin lecturas.";
}
for (const elemento of document.querySelectorAll("[data-body]")) {
  elemento.addEventListener("click", () => ejecutar(elemento, async () => {
    const accion = elemento.dataset.body;
    const valor = accion === "avanzar" ? $("cm").value : accion === "girar" ? $("grados").value : null;
    representarBody(await api("body", {accion, valor}));
  }));
}
$("puertos").addEventListener("click", () => ejecutar($("puertos"), async () => {
  const puertos = (await api("dispositivos")).serie;
  $("dispositivos").textContent = puertos.length ? JSON.stringify(puertos, null, 2) : "Sin puertos serie detectados.";
}));
