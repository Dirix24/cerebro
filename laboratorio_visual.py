"""Genera un panel HTML local y estático del estado de Cerebro.

No ejecuta comandos del sistema ni controla el ordenador. La red neuronal
animada es una ilustración, no una captura de activaciones reales.
"""
import argparse
import html
import json
from pathlib import Path


def _leer_jsonl(ruta, limite=30):
    ruta = Path(ruta)
    if not ruta.is_file() or ruta.is_symlink():
        return []
    salida = []
    for linea in ruta.read_text(encoding="utf-8").splitlines()[-limite:]:
        try:
            dato = json.loads(linea)
            if isinstance(dato, dict):
                salida.append(dato)
        except ValueError:
            continue
    return salida


def estado(raiz):
    raiz = Path(raiz)
    ckpts = []
    for nombre in ("best.npz", "last.npz"):
        ruta = raiz / "checkpoints" / nombre
        if ruta.is_file() and not ruta.is_symlink():
            ckpts.append({"archivo": nombre, "bytes": ruta.stat().st_size,
                          "actualizado": ruta.stat().st_mtime})
    evolucion = raiz / "data" / "aprendizaje_internet" / "evolucion.json"
    historia_evolucion = []
    if evolucion.is_file() and not evolucion.is_symlink():
        try:
            dato = json.loads(evolucion.read_text(encoding="utf-8"))
            historia_evolucion = dato if isinstance(dato, list) else [dato]
        except (ValueError, OSError):
            pass
    return {
        "version": "integracion-experimental",
        "checkpoints": ckpts,
        "evaluaciones": _leer_jsonl(raiz / "data" / "historial_evaluaciones.jsonl"),
        "experimentos": _leer_jsonl(raiz / "learning" / "evolution" / "experimentos.jsonl"),
        "evolucion": historia_evolucion[-30:],
        "modo": "Solo lectura; visualización neuronal ilustrativa",
    }


def generar(raiz, salida):
    datos = estado(raiz)
    # Escapar caracteres especiales para impedir cierre de script con datos locales.
    serializado = json.dumps(datos, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    plantilla = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cerebro | Laboratorio visual</title>
<style>
:root{color-scheme:dark;font-family:system-ui,Arial,sans-serif;background:#0b1120;color:#edf3ff}
body{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:2rem;margin-bottom:4px}p{color:#aabbd2;line-height:1.5}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
article{background:#151f33;border:1px solid #33435c;border-radius:16px;padding:18px}
strong{font-size:1.6rem;color:#86e5d0}small{color:#aabbd2}
svg{width:100%;height:auto;background:#0c1729;border-radius:12px}
circle{fill:#7ce5d0;animation:brillo 2.4s infinite alternate}
line{stroke:#4a9bba;stroke-width:1;opacity:.35}
@keyframes brillo{from{opacity:.25}to{opacity:1}}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.85rem;color:#c5d6ed}
button{background:#275d77;color:white;border:0;border-radius:8px;padding:10px;cursor:pointer}
.badge{color:#ffd18c;font-weight:bold}
</style></head><body>
<h1>🧠 Cerebro — Laboratorio visual</h1>
<p>Panel local generado a partir de archivos de Cerebro. No está conectado en directo: vuelve a ejecutar el comando para actualizarlo.</p>
<div class="grid">
<article><small>Versión</small><h2 id="version"></h2></article>
<article><small>Checkpoints encontrados</small><p><strong id="ckpts">0</strong></p></article>
<article><small>Evaluaciones registradas</small><p><strong id="evaluaciones">0</strong></p></article>
<article><small>Experimentos</small><p><strong id="experimentos">0</strong></p></article>
</div>
<h2>Red neuronal animada <span class="badge">SIMULACIÓN VISUAL</span></h2>
<p>Los puntos y conexiones son una animación conceptual. <b>No representan neuronas reales, pesos, activaciones ni aprendizaje en tiempo real.</b></p>
<article><svg id="red" viewBox="0 0 850 310" role="img" aria-label="Diagrama animado ilustrativo de una red neuronal"></svg></article>
<h2>Progreso registrado</h2>
<article><p id="progreso"></p><svg id="grafico" viewBox="0 0 850 210" role="img" aria-label="Gráfico de precisión de evaluaciones registradas"></svg></article>
<h2>Versiones de pesos</h2><article><pre id="pesos"></pre></article>
<h2>Simulador de planificación segura</h2>
<p>Una simulación no controla el ordenador ni ejecuta programas.</p>
<article><button id="simular">Simular organización de archivos</button><pre id="simulacion">Pulsa para simular una tarea sin modificar nada.</pre></article>
<h2>Registro de experimentos</h2><article><pre id="registro"></pre></article>
<script>
const datos = __DATOS__;
const $=id=>document.getElementById(id);
$('version').textContent=datos.version;
$('ckpts').textContent=datos.checkpoints.length;
$('evaluaciones').textContent=datos.evaluaciones.length;
$('experimentos').textContent=datos.experimentos.length;
$('pesos').textContent=datos.checkpoints.length?datos.checkpoints.map(x=>x.archivo+' · '+(x.bytes/1048576).toFixed(2)+' MiB · '+new Date(x.actualizado*1000).toLocaleString()).join('\n'):'No se encontraron checkpoints.';
$('registro').textContent=datos.experimentos.length?JSON.stringify(datos.experimentos.slice(-5),null,2):'Sin experimentos registrados.';
const vals=datos.evaluaciones.filter(x=>typeof x.precision==='number'&&Number.isFinite(x.precision));
$('progreso').textContent=vals.length?'Última precisión exacta: '+(vals[vals.length-1].precision*100).toFixed(1)+'%. No es una medida de inteligencia general.':'No hay evaluaciones. Usa /progreso para registrar una.';
const ns='http://www.w3.org/2000/svg';
function el(svg,t,attrs){const e=document.createElementNS(ns,t);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);svg.appendChild(e);return e;}
const red=$('red');const capas=[4,6,7,6,3];const nodos=capas.map((n,c)=>Array.from({length:n},(_,i)=>[85+c*170,35+i*240/Math.max(1,n-1)]));
for(let c=0;c<nodos.length-1;c++)for(const a of nodos[c])for(const b of nodos[c+1])el(red,'line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1]});
let indice=0;for(const capa of nodos)for(const [x,y] of capa){const circulo=el(red,'circle',{cx:x,cy:y,r:8});circulo.style.animationDelay=(indice++*.13)+'s';}
const grafico=$('grafico');el(grafico,'line',{x1:35,y1:185,x2:820,y2:185});
if(vals.length){const puntos=vals.map((v,i)=>[40+(vals.length===1?0:i*760/(vals.length-1)),180-v.precision*155]);for(let i=1;i<puntos.length;i++)el(grafico,'line',{x1:puntos[i-1][0],y1:puntos[i-1][1],x2:puntos[i][0],y2:puntos[i][1],stroke:'#7ce5d0','stroke-width':3,opacity:1});for(const p of puntos)el(grafico,'circle',{cx:p[0],cy:p[1],r:5});}
$('simular').addEventListener('click',()=>{$('simulacion').textContent='SIMULACIÓN — 1. Inspeccionar carpeta permitida.\n2. Proponer categorías.\n3. Mostrar cambios previstos.\n4. Pedir aprobación explícita antes de cualquier acción real.\n\nNo se ha accedido a archivos ni ejecutado ninguna acción.';});
</script></body></html>"""
    destino = Path(salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(plantilla.replace("__DATOS__", serializado), encoding="utf-8")
    return destino


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generar laboratorio visual estático")
    ap.add_argument("--salida", default="data/laboratorio_cerebro.html")
    args = ap.parse_args(argv)
    raiz = Path(__file__).resolve().parent
    print("Panel generado:", generar(raiz, raiz / args.salida))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
