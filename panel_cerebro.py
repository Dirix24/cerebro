"""Panel local de Cerebro: biblioteca, cálculo, planes, código y experimentos.

Interfaz Tkinter estándar, sin servidor ni dependencias externas.
"""
import argparse
import json
from pathlib import Path

from core.razonamiento_local import calcular
from core.biblioteca_local import buscar_en_biblioteca
from core.analizador_codigo_local import analizar
from core.laboratorio_local import historial
from core.estudio_local import resumir, palabras_clave
from core.herramientas_texto import estadisticas, comparar_textos, fichas_estudio

RAIZ = Path(__file__).resolve().parent


def ejecutar(accion, valor=""):
    if accion == "calcular":
        return str(calcular(valor))
    if accion == "biblioteca":
        return json.dumps(buscar_en_biblioteca(valor, RAIZ / "data"), ensure_ascii=False, indent=2)
    if accion == "codigo":
        return json.dumps(analizar(valor), ensure_ascii=False, indent=2)
    if accion == "resumir":
        return resumir(valor)
    if accion == "palabras-clave":
        return ", ".join(palabras_clave(valor))
    if accion == "estadisticas":
        return json.dumps(estadisticas(valor), ensure_ascii=False, indent=2)
    if accion == "comparar":
        if " || " not in valor:
            raise ValueError("Separa los dos textos con:  ||  ")
        a, b = valor.split(" || ", 1)
        return json.dumps(comparar_textos(a, b), ensure_ascii=False, indent=2)
    if accion == "fichas":
        return json.dumps(fichas_estudio(valor), ensure_ascii=False, indent=2)
    if accion == "metricas":
        return json.dumps(historial(RAIZ / "learning/evolution/experimentos.jsonl"), ensure_ascii=False, indent=2)
    raise ValueError("Acción no disponible")


def ventana():
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.title("Cerebro · Herramientas locales")
    root.geometry("800x560")
    ttk.Label(root, text="Cerebro · Panel de herramientas", font=("Arial", 16)).pack(pady=10)
    accion = tk.StringVar(value="calcular")
    ttk.Combobox(root, textvariable=accion,
                 values=("calcular", "biblioteca", "codigo", "metricas", "resumir", "palabras-clave", "estadisticas", "comparar", "fichas"), state="readonly").pack(fill="x", padx=12)
    entrada = tk.Text(root, height=5)
    entrada.pack(fill="x", padx=12, pady=8)
    salida = tk.Text(root, height=18)
    salida.pack(fill="both", expand=True, padx=12, pady=8)
    def procesar():
        salida.delete("1.0", "end")
        try:
            resultado = ejecutar(accion.get(), entrada.get("1.0", "end").strip())
        except Exception as exc:
            resultado = f"Error: {exc}"
        salida.insert("end", resultado)
    ttk.Button(root, text="Ejecutar herramienta", command=procesar).pack(pady=6)
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description="Panel local de Cerebro")
    ap.add_argument("--accion", choices=("calcular", "biblioteca", "codigo", "metricas"))
    ap.add_argument("--texto", default="")
    args = ap.parse_args()
    if args.accion:
        print(ejecutar(args.accion, args.texto))
    else:
        ventana()


if __name__ == "__main__":
    main()
