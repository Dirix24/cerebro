import {colores, escena} from "./escena.js";

const $ = id => document.getElementById(id);
const botonesTab = [...document.querySelectorAll("[data-tab]")];
let token = "";
const modoWeb = location.pathname === "/chat" ? "chat" : "studio";
const idInterfaz = Array.from(crypto.getRandomValues(new Uint8Array(12)),
  byte => byte.toString(16).padStart(2, "0")).join("");
document.body.dataset.interfaz = modoWeb === "chat" ? "chat" : "estudio";
if (modoWeb === "chat") $("titulo-interfaz").textContent = "Chat";

function anunciar(visible) {
  if (!token) return;
  fetch("/api/interfaz", {method: "POST", keepalive: true, headers: {
    Authorization: "Bearer " + token, "Content-Type": "application/json",
  }, body: JSON.stringify({id: idInterfaz, modo: modoWeb, visible})}).catch(() => {});
}
document.addEventListener("visibilitychange", () => anunciar(!document.hidden));
window.addEventListener("pagehide", () => anunciar(false));
setInterval(() => { if (!document.hidden) anunciar(true); }, 2000);
let vista = "studio";
let cambioVista = 0;
let nodos = [];
let formas = [];
let trazo = null;
let canvasCargado = false;
let sondeoOcupado = false;

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
  catch (error) { token = ""; throw error; }
  $("acceso").hidden = true;
  $("clave").value = "";
  $("conexion").textContent = "Núcleo conectado";
  $("metricas").hidden = false;
  anunciar(!document.hidden);
  await mostrar("studio");
  const historial = await api("historial");
  if ($("mensajes").childElementCount === 0) {
    for (const turno of historial.turnos) agregarMensaje(turno.rol === "usuario" ? "Tú" : "Cerebro", turno.texto);
  }
  if (modoWeb === "studio") await actualizarArchivos();
}

$("acceso").addEventListener("submit", evento => {
  evento.preventDefault();
  ejecutar(evento.submitter, () => conectar($("clave").value.trim()));
});
for (const elemento of botonesTab) elemento.addEventListener("click", () => {
  if (token) ejecutar(elemento, () => mostrar(elemento.dataset.tab));
});
const claveInicial = location.hash.slice(1);
if (claveInicial) {
  history.replaceState(null, "", location.pathname);
  conectar(claveInicial).catch(error => aviso(error.message));
}

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
}

async function sondear() {
  if (!token || sondeoOcupado || document.hidden) return;
  sondeoOcupado = true;
  try {
    await estado();
    if (vista === "studio" && modoWeb === "studio") await actualizarTareas();
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
  mensaje.append(rol + " · ");
  const partes = rol === "Cerebro" ? texto.split(/(https:\/\/[^\s<>"']+)/u) : [texto];
  for (const [indice, parte] of partes.entries()) {
    if (indice % 2 === 0) {
      mensaje.append(parte);
      continue;
    }
    const enlace = document.createElement("a");
    enlace.href = parte;
    enlace.textContent = parte;
    enlace.target = "_blank";
    enlace.rel = "noopener noreferrer";
    mensaje.append(enlace);
  }
  $("mensajes").append(mensaje);
  if ($("mensajes").children.length > 100) $("mensajes").firstElementChild.remove();
  $("mensajes").scrollTop = $("mensajes").scrollHeight;
}

async function conversar(texto) {
  agregarMensaje("Tú", texto);
  const salida = await api("chat", {mensaje: texto});
  agregarMensaje("Cerebro", salida.respuesta);
  if (salida.abrir === "studio" && modoWeb === "chat") location.assign("/studio#" + token);
}

$("chat").addEventListener("submit", evento => {
  evento.preventDefault();
  const texto = $("mensaje").value.trim();
  if (!texto) return;
  ejecutar(evento.submitter, async () => {
    await conversar(texto);
    if ($("mensaje").value.trim() === texto) $("mensaje").value = "";
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
    if (!/\.(?:srt|vtt)$/i.test(salida.nombre)) $("mensaje").value = "Analiza " + salida.nombre;
    aviso("Adjunto disponible: " + salida.nombre);
  } catch (error) { aviso(error.message); }
  finally { $("adjunto").value = ""; }
});

async function abrirArchivo(nombre) {
  $("contenido").value = (await api("archivo?nombre=" + encodeURIComponent(nombre))).texto;
  $("archivo").value = nombre;
}
async function actualizarArchivos() {
  lista($("archivos"), (await api("archivos")).archivos, nombre => boton(nombre, () => abrirArchivo(nombre)));
}
$("abrir-archivo").addEventListener("submit", evento => {
  evento.preventDefault();
  ejecutar(evento.submitter, () => abrirArchivo($("archivo").value.trim()));
});
$("guardar").addEventListener("click", () => ejecutar($("guardar"), async () => {
  await api("archivo", {nombre: $("archivo").value.trim(), texto: $("contenido").value});
  await actualizarArchivos();
  aviso("Archivo guardado.");
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
    await api("tarea", {accion: elemento.dataset.tarea, nombre: $("archivo").value.trim()});
    await actualizarTareas();
  }));
}
$("limpiar-tareas").addEventListener("click", () => ejecutar($("limpiar-tareas"), async () => {
  await api("cache", {});
  await actualizarTareas();
}));

function inspeccionar(nodo) {
  grafico.seleccionar(nodo.id);
  $("detalle").textContent = [nodo.titulo, nodo.grupo || nodo.tipo, nodo.detalle, nodo.origen, nodo.fecha]
    .filter(Boolean).join("\n");
}

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
  const visibles = nodos.filter(nodo => (!tipo || nodo.tipo === tipo) &&
    [nodo.titulo, nodo.detalle, nodo.origen].join(" ").toLocaleLowerCase("es").includes(consulta));
  const firma = JSON.stringify(visibles);
  if (firma === firmaNodos) return;
  firmaNodos = firma;
  lista($("nodos"), visibles, nodo => boton(nodo.titulo, () => inspeccionar(nodo)));
  if (!visibles.length) $("nodos").textContent = "No hay nodos que coincidan.";
  grafico.nodos(visibles);
}
$("filtro").addEventListener("change", filtrar);
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
