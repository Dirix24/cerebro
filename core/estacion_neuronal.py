"""Estación neuronal explorable (grafo de recuerdos, no neuronas del modelo).

Genera HTML local autónomo con canvas, sin CDN ni llamadas de red.
"""
import json
from pathlib import Path
from core.mapa_memoria import grafo

ESTADOS = {
    "analizando": "#facc15", "aprendido": "#3b82f6",
    "investigando": "#fb923c", "consolidado": "#22c55e",
    "asociando": "#a855f7", "observando": "#22d3ee",
    "error": "#ef4444",
}


def construir_estacion(memoria, actividad=None, limite=160):
    nodos, enlaces = grafo(memoria, limite=limite)
    eventos = actividad or []
    if not isinstance(eventos, list):
        raise ValueError("La actividad debe ser una lista")
    estados = set(ESTADOS)
    eventos = [e for e in eventos[:120] if isinstance(e, dict)
               and e.get("estado") in estados and isinstance(e.get("texto", ""), str)]
    datos = {"nodos": nodos, "enlaces": enlaces, "eventos": eventos,
             "colores": ESTADOS}
    carga = json.dumps(datos, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return PLANTILLA.replace("__DATOS__", carga)


def guardar_estacion(memoria, destino, actividad=None):
    ruta = Path(destino)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("x", encoding="utf-8") as archivo:
        archivo.write(construir_estacion(memoria, actividad))
    return str(ruta)


PLANTILLA = r'''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cerebro · Estación neuronal</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#080e1d;color:#e2e8f0;font:14px system-ui,sans-serif}
header{padding:12px 18px;display:flex;flex-wrap:wrap;gap:14px;align-items:center;background:#111b32}
h1{font-size:18px;margin:0}button{background:#253454;color:white;border:1px solid #486085;border-radius:8px;padding:8px 12px;cursor:pointer}
button:hover,button:focus{background:#354f7c}main{display:grid;grid-template-columns:minmax(0,1fr) 280px;height:calc(100vh - 62px);min-height:450px}
#area{position:relative;overflow:hidden}canvas{width:100%;height:100%;display:block;touch-action:none;cursor:grab}
aside{background:#101b31;padding:18px;overflow:auto;border-left:1px solid #263755}
.legend{display:flex;flex-wrap:wrap;gap:9px;padding:8px 16px;background:#0e162a}
.legend span{display:flex;align-items:center;gap:5px}.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
small{color:#9baecc}#detalle{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}
@media(max-width:700px){main{grid-template-columns:1fr;grid-template-rows:minmax(350px,60vh) auto;height:auto}aside{border-left:0;border-top:1px solid #263755}}
</style></head><body>
<header><h1>◉ CEREBRO · Estación neuronal</h1>
<button id="mas" aria-label="Acercar">＋</button><button id="menos" aria-label="Alejar">－</button>
<button id="centrar">Centrar</button><button id="pausa">Pausar</button>
<small id="contador"></small></header>
<div class="legend" id="leyenda"></div>
<main><div id="area"><canvas id="red" aria-label="Mapa interactivo de recuerdos y conexiones"></canvas></div>
<aside><h2>Núcleo</h2><p id="detalle">Selecciona un nodo para explorar su recuerdo. Arrastra para moverte; usa la rueda o los botones para ampliar.</p>
<p><small>Representación de recuerdos y eventos registrados. El movimiento es una animación, no actividad neuronal medida en tiempo real.</small></p></aside></main>
<script id="datos" type="application/json">__DATOS__</script>
<script>
"use strict";
let d=JSON.parse(document.getElementById("datos").textContent);
const canvas=document.getElementById("red"),ctx=canvas.getContext("2d");
const detalle=document.getElementById("detalle");
let nodos=d.nodos.map((n,i)=>({...n,angle:i*2.399963,rad:110+38*Math.sqrt(i),fase:i*.73}));
let zoom=1,panX=0,panY=0,pausa=false,t=0,seleccion=-1,drag=null,ultimo=0;
const estadoColor=e=>d.colores[e]||d.colores.aprendido;
document.getElementById("leyenda").replaceChildren(...Object.entries(d.colores).map(([k,v])=>{
 const el=document.createElement("span"),dot=document.createElement("i");dot.className="dot";dot.style.background=v;
 el.append(dot,document.createTextNode(k));return el;
}));
document.getElementById("contador").textContent=nodos.length+" recuerdos · "+d.enlaces.length+" conexiones";
// Solo solicita datos al servidor local cuando la estación se abre por HTTP.
let ultimaFirma="";
async function actualizar(){
 if(location.protocol!=="http:" || location.hostname!=="127.0.0.1")return;
 try{
  const respuesta=await fetch("/snapshot",{cache:"no-store"});
  if(!respuesta.ok)return;
  const nuevo=await respuesta.json();
  if(!nuevo||!Array.isArray(nuevo.nodos)||!Array.isArray(nuevo.enlaces)||!Array.isArray(nuevo.eventos))return;
  const firma=JSON.stringify(nuevo);
  if(firma===ultimaFirma)return;
  ultimaFirma=firma;
  const anterior=nodos.length;
  d=nuevo;
  nodos=d.nodos.map((n,i)=>({...n,angle:i*2.399963,rad:110+38*Math.sqrt(i),fase:i*.73}));
  if(nodos.length!==anterior)seleccion=-1;
  document.getElementById("contador").textContent=nodos.length+" recuerdos · "+d.enlaces.length+" conexiones";
  const reciente=d.eventos[d.eventos.length-1];
  if(reciente && seleccion<0)detalle.textContent="Actividad registrada: "+reciente.estado+" · "+reciente.texto+
   "\\n"+reciente.fecha+"\\n\\nSelecciona un recuerdo para explorar.";
 }catch(_){/* El visor sigue funcionando con los datos iniciales. */}
}
if(location.protocol==="http:" && location.hostname==="127.0.0.1"){
 actualizar();setInterval(actualizar,1500);
}
function resize(){const r=canvas.getBoundingClientRect(),scale=devicePixelRatio||1;
 canvas.width=Math.max(1,Math.round(r.width*scale));canvas.height=Math.max(1,Math.round(r.height*scale));
 ctx.setTransform(scale,0,0,scale,0,0)}
new ResizeObserver(resize).observe(canvas);resize();
function centro(){return {x:canvas.clientWidth/2+panX,y:canvas.clientHeight/2+panY}}
function pos(n){const wobble=pausa?0:Math.sin(t*.0007+n.fase)*7;
 return {x:Math.cos(n.angle)*(n.rad+wobble),y:Math.sin(n.angle)*(n.rad+wobble)}}
function pintar(ms){
 if(!pausa)t+=Math.min(40,ms-ultimo||16);ultimo=ms;
 const w=canvas.clientWidth,h=canvas.clientHeight,c=centro();
 ctx.clearRect(0,0,w,h);ctx.fillStyle="#080e1d";ctx.fillRect(0,0,w,h);
 ctx.save();ctx.translate(c.x,c.y);ctx.scale(zoom,zoom);
 for(const [a,b] of d.enlaces){if(!nodos[a]||!nodos[b])continue;
 const p=pos(nodos[a]),q=pos(nodos[b]);
 ctx.strokeStyle="#5d709b";ctx.globalAlpha=.23;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.stroke();
 if(!pausa){const f=(t*.00015+(a+b)*.19)%1;
 ctx.fillStyle="#b4c8ff";ctx.globalAlpha=.8;ctx.beginPath();ctx.arc(p.x+(q.x-p.x)*f,p.y+(q.y-p.y)*f,2.3,0,Math.PI*2);ctx.fill()}
 }
 ctx.globalAlpha=1;
 const pulso=1+Math.sin(t*.0018)*.08;
 ctx.shadowBlur=25;ctx.shadowColor="#7c3aed";ctx.fillStyle="#6d28d9";
 ctx.beginPath();ctx.arc(0,0,40*pulso,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
 ctx.fillStyle="white";ctx.font="bold 13px system-ui";ctx.textAlign="center";ctx.fillText("NÚCLEO",0,4);
 for(let i=0;i<nodos.length;i++){const n=nodos[i],p=pos(n);
 const color=i===seleccion?"#fff":estadoColor(n.estado);
 ctx.shadowBlur=i===seleccion?22:10;ctx.shadowColor=color;ctx.fillStyle=color;
 ctx.beginPath();ctx.arc(p.x,p.y,i===seleccion?10:6,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
 if(zoom>.75||i===seleccion){ctx.fillStyle="#dce7ff";ctx.font="11px system-ui";ctx.textAlign="left";
 ctx.fillText(n.etiqueta.slice(0,22),p.x+12,p.y+4)}
 }
 for(let i=0;i<d.eventos.length;i++){const e=d.eventos[i],a=(i*2.39996+t*.0001)%(Math.PI*2),r=58+i%4*13;
 ctx.fillStyle=estadoColor(e.estado);ctx.globalAlpha=.85;ctx.beginPath();ctx.arc(Math.cos(a)*r,Math.sin(a)*r,3,0,Math.PI*2);ctx.fill()}
 ctx.globalAlpha=1;ctx.restore();requestAnimationFrame(pintar)}
requestAnimationFrame(pintar);
function zoomEn(f){zoom=Math.max(.2,Math.min(4,zoom*f))}
document.getElementById("mas").onclick=()=>zoomEn(1.2);
document.getElementById("menos").onclick=()=>zoomEn(1/1.2);
document.getElementById("centrar").onclick=()=>{zoom=1;panX=panY=0};
document.getElementById("pausa").onclick=e=>{pausa=!pausa;e.target.textContent=pausa?"Reanudar":"Pausar"};
canvas.addEventListener("wheel",e=>{e.preventDefault();zoomEn(e.deltaY<0?1.12:1/1.12)},{passive:false});
canvas.addEventListener("pointerdown",e=>{canvas.setPointerCapture(e.pointerId);drag={x:e.clientX,y:e.clientY,movio:false}});
canvas.addEventListener("pointermove",e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
 if(Math.abs(dx)+Math.abs(dy)>2)drag.movio=true;panX+=dx;panY+=dy;drag.x=e.clientX;drag.y=e.clientY});
canvas.addEventListener("pointerup",e=>{if(!drag)return;const movio=drag.movio;drag=null;if(movio)return;
 const r=canvas.getBoundingClientRect(),c=centro(),x=(e.clientX-r.left-c.x)/zoom,y=(e.clientY-r.top-c.y)/zoom;
 let elegido=-1,dist=18/zoom;for(let i=0;i<nodos.length;i++){const p=pos(nodos[i]),v=Math.hypot(p.x-x,p.y-y);
 if(v<dist){elegido=i;dist=v}}
 seleccion=elegido;if(elegido<0){detalle.textContent="Núcleo Cerebro. Selecciona un recuerdo para ver sus detalles.";return}
 const n=nodos[elegido];detalle.textContent="Recuerdo: "+n.etiqueta+"\nEstado: "+n.estado+"\nContenido: "+n.texto+
 "\nConexiones: "+d.enlaces.filter(([a,b])=>a===elegido||b===elegido).length;
});
</script></body></html>'''
