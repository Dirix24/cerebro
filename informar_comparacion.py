"""Valida los presupuestos de la comparación y registra métricas legibles en Universe."""
import argparse
import json
from pathlib import Path

from core import competencias


def resumen(datos):
    def abreviar(medida):
        return {materia: {clave: fila[clave] for clave in
                          ("exactos", "exitos", "total", "contextos_completos")}
                for materia, fila in medida["materias"].items()}

    def contrafactuales(medida):
        resultados = medida["materias"]["razonamiento"]["resultados"]
        return {"ambos_correctos": sum(a["exito"] and b["exito"]
                                       for a, b in zip(resultados[::2], resultados[1::2])),
                "pares": len(resultados) // 2}

    for d in datos:
        antes, despues = d["antes"], d["despues"]
        yield {"perfil": d["perfil"], "semilla": d["semilla"], "estrategia": d["estrategia"],
               "parametros": d["parametros"], "contexto": d["contexto"], "rss_mib": d["rss_mib"],
               "cpu_s": d["cpu_s"], "elegible_para_revision": d["elegible_para_revision"],
               "fase_base": d["fase_base"], "ajuste": d["ajuste"],
               "validacion_antes": antes["validacion"]["exactas"], "validacion_despues": despues["validacion"]["exactas"],
               "test_anterior_antes": antes["final_anterior"], "test_anterior_despues": despues["final_anterior"],
               "bpb_antes": antes["perdida_bpb"], "bpb_despues": despues["perdida_bpb"],
               "competencias_antes": abreviar(antes["nuevo_banco"]),
               "competencias_despues": abreviar(despues["nuevo_banco"]),
               "curriculo_reservado_antes": abreviar(antes["curriculo_reservado"]),
               "curriculo_reservado_despues": abreviar(despues["curriculo_reservado"]),
               "dialogos": abreviar(despues["dialogo_largo"]),
               "dialogos_112": abreviar(despues["dialogo_largo_112"]),
               "pares_largos": contrafactuales(despues["dialogo_largo"]),
               "pares_largos_112": contrafactuales(despues["dialogo_largo_112"]),
               "latencia_mediana_ms": despues["nuevo_banco"]["latencia_mediana_ms"],
               "segundos_entrenamiento": d["ajuste"]["segundos"] + (d["fase_base"]["segundos"] if d["fase_base"] else 0)}


def agrupar(datos):
    ensayos = {(d["perfil"], d["semilla"], d["estrategia"]): d for d in datos}
    if len(ensayos) != len(datos):
        raise ValueError("Hay ensayos repetidos con el mismo perfil, semilla y estrategia.")
    for semilla in {d["semilla"] for d in datos if d["perfil"] != "activo"}:
        perfiles = [ensayos.get((p, semilla, "mixta")) for p in ("pequeno", "v2")]
        if any(p is None for p in perfiles):
            raise ValueError(f"Falta la pareja de arquitecturas para semilla {semilla}.")
        a, b = perfiles
        for fase in ("fase_base", "ajuste"):
            for clave in ("pasos", "tokens_objetivo", "huella_objetivos", "huella_parejas"):
                if a[fase][clave] != b[fase][clave]:
                    raise ValueError(f"El presupuesto no coincide ({semilla}, {fase}, {clave}).")
    return {"tipo": "comparacion_arquitecturas", "ensayos": list(resumen(datos))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("informes", nargs="+", type=Path)
    parser.add_argument("--registrar", type=Path)
    parser.add_argument("--json", type=Path, help="exportar el resumen verificable")
    args = parser.parse_args()
    registro = agrupar([json.loads(ruta.read_text()) for ruta in args.informes])
    if args.registrar:
        competencias.guardar(args.registrar, registro)
    if args.json:
        with args.json.open("x", encoding="utf-8") as destino:
            json.dump(registro, destino, ensure_ascii=False, indent=2)
            destino.write("\n")
    print(competencias.resumen(registro))


if __name__ == "__main__":
    main()
