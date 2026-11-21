export const colores = {
  aprendizaje: "#63a7ff", relaciones: "#ffdd72", conocimiento: "#87db92",
  razonamiento: "#c298fa", "investigación": "#ff9c57", errores: "#ff6576",
  memoria: "#61e1e9", "creación": "#f18ed0", procesamiento: "#f3f5ff", inactividad: "#9da9b2"
};

export function escena(canvas, elegir) {
  const contexto = canvas.getContext("2d");
  let objetos = [], visibles = [], giro = .6, inclinacion = .2, zoom = 1;
  let arrastre = null, ultimo = 0, fotograma = 0;
  let activada = false, rotar = true, seleccion = null;

  function proyectar({x, y, z}, ancho, alto) {
    const horizontal = x * Math.cos(giro) - z * Math.sin(giro);
    const profundidad = x * Math.sin(giro) + z * Math.cos(giro);
    const vertical = y * Math.cos(inclinacion) - profundidad * Math.sin(inclinacion);
    const fondo = y * Math.sin(inclinacion) + profundidad * Math.cos(inclinacion);
    const escala = 3 / (3 + fondo);
    const tam = Math.min(ancho / 3.3, alto / 2.45) * zoom * escala;
    return {x: ancho / 2 + horizontal * tam, y: alto / 2 + vertical * tam, z: fondo, escala};
  }

  function pintar(ahora) {
    fotograma = 0;
    if (!activada || !contexto || canvas.hidden || canvas.clientWidth === 0) return;
    const ancho = canvas.clientWidth;
    const alto = canvas.clientHeight;
    const resolucion = Math.min(devicePixelRatio, 2);
    if (canvas.width !== Math.round(ancho * resolucion) || canvas.height !== Math.round(alto * resolucion)) {
      canvas.width = Math.round(ancho * resolucion);
      canvas.height = Math.round(alto * resolucion);
    }
    contexto.setTransform(resolucion, 0, 0, resolucion, 0, 0);
    contexto.clearRect(0, 0, ancho, alto);
    if (rotar && !arrastre && ultimo) giro += Math.min(35, ahora - ultimo) * .00014;
    ultimo = ahora;
    const centro = proyectar({x: 0, y: 0, z: 0}, ancho, alto);
    contexto.strokeStyle = "#334b5a";
    for (const radio of [1.1, 1.38]) {
      contexto.beginPath();
      for (let i = 0; i <= 64; i++) {
        const paso = i * Math.PI / 32;
        const p = proyectar({x: Math.cos(paso) * radio, y: Math.sin(paso) * .24,
          z: Math.sin(paso) * radio * .68}, ancho, alto);
        if (i === 0) contexto.moveTo(p.x, p.y);
        else contexto.lineTo(p.x, p.y);
      }
      contexto.stroke();
    }
    const radioNucleo = 19 * zoom;
    const halo = contexto.createRadialGradient(centro.x, centro.y, 0, centro.x, centro.y, radioNucleo * 2.1);
    halo.addColorStop(0, "#dbfff0");
    halo.addColorStop(.25, "#61e4c8");
    halo.addColorStop(.48, "#2e878c88");
    halo.addColorStop(1, "#2e878c00");
    contexto.fillStyle = halo;
    contexto.beginPath();
    contexto.arc(centro.x, centro.y, radioNucleo * 2.1, 0, Math.PI * 2);
    contexto.fill();
    contexto.strokeStyle = "#91e3d29a";
    contexto.beginPath();
    contexto.arc(centro.x, centro.y, radioNucleo, 0, Math.PI * 2);
    contexto.stroke();
    visibles = objetos.map(objeto => ({...objeto, ...proyectar(objeto, ancho, alto)}))
      .sort((a, b) => b.z - a.z);
    const porId = new Map(visibles.map(nodo => [nodo.nodo.id, nodo]));
    contexto.strokeStyle = "#a2894390";
    for (const origen of visibles) {
      for (const id of origen.nodo.vinculos || []) {
        const destino = porId.get(id);
        if (!destino) continue;
        contexto.beginPath();
        contexto.moveTo(origen.x, origen.y);
        contexto.lineTo(destino.x, destino.y);
        contexto.stroke();
      }
    }
    for (const nodo of visibles) {
      contexto.beginPath();
      const size = (seleccion === nodo.nodo.id ? 7 : 4) * nodo.escala;
      contexto.arc(nodo.x, nodo.y, size, 0, Math.PI * 2);
      contexto.fillStyle = colores[nodo.nodo.tipo] || colores.inactividad;
      contexto.fill();
    }
    if (rotar) actualizar();
  }

  function actualizar() {
    if (activada && !fotograma) fotograma = requestAnimationFrame(pintar);
  }

  canvas.addEventListener("pointerdown", evento => {
    canvas.setPointerCapture(evento.pointerId);
    arrastre = {x: evento.offsetX, y: evento.offsetY, distancia: 0};
  });
  canvas.addEventListener("pointermove", evento => {
    if (!arrastre) return;
    const dx = evento.offsetX - arrastre.x;
    const dy = evento.offsetY - arrastre.y;
    giro += dx * .01;
    inclinacion += dy * .01;
    arrastre = {x: evento.offsetX, y: evento.offsetY, distancia: arrastre.distancia + Math.hypot(dx, dy)};
    actualizar();
  });
  canvas.addEventListener("pointerup", evento => {
    if (arrastre?.distancia < 6) {
      const candidato = [...visibles].reverse().find(nodo =>
        Math.hypot(nodo.x - evento.offsetX, nodo.y - evento.offsetY) < 12);
      if (candidato) elegir(candidato.nodo);
    }
    arrastre = null;
  });
  canvas.addEventListener("pointercancel", () => { arrastre = null; });
  canvas.addEventListener("wheel", evento => {
    evento.preventDefault();
    zoom = Math.max(.45, Math.min(2.5, zoom * Math.exp(-evento.deltaY * .001)));
    actualizar();
  }, {passive: false});
  new ResizeObserver(actualizar).observe(canvas);

  return {
    nodos(nodos) {
      objetos = nodos.map((nodo, i) => {
        // Dos lóbulos geométricos en 3D. Las coordenadas no son datos neuronales.
        const latitud = Math.acos(1 - 2 * (((i * .61803398875) % 1 + .035) % 1));
        const longitud = i * 2.3999632;
        const centroLobulo = i % 2 ? -.49 : .49;
        return {nodo, x: centroLobulo + Math.sin(latitud) * Math.cos(longitud) * .60,
          y: Math.cos(latitud) * .72, z: Math.sin(latitud) * Math.sin(longitud) * .87};
      });
      actualizar();
    },
    activar(valor) {
      activada = valor;
      ultimo = 0;
      if (!valor && fotograma) cancelAnimationFrame(fotograma);
      if (!valor) fotograma = 0;
      actualizar();
    },
    rotar(valor) { rotar = valor && !matchMedia("(prefers-reduced-motion: reduce)").matches; actualizar(); },
    seleccionar(id) { seleccion = id; actualizar(); }
  };
}
