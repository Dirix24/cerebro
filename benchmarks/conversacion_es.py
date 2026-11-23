"""Banco reservado de conversación española. Evalúa salidas sin editar fuentes ni entrenar."""
import argparse
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter, process_time

# Grupos de palabras esperadas y errores que invalidan una respuesta aparentemente acertada.
BANCO = (
    ("ciencia", "¿Cómo funciona una brújula?", ("magnetic",), ("horario", "reloj")),
    ("tecnología", "¿Qué es la memoria caché de un procesador?", ("memoria", "rapida"), ()),
    ("electrónica", "¿Para qué sirve un fusible eléctrico?", ("corriente", "prote"), ()),
    ("programación", "¿Qué es el alcance léxico en programación?", ("ambito", "variable"), ()),
    ("historia", "¿Quién fue la primera persona en orbitar la Tierra?", ("gagarin",), ()),
    ("matemáticas", "Calcula 13 * 17", ("221",), ()),
    ("cotidiana", "¿Qué significa que un producto sea perecedero?", ("deterior",), ()),
    ("errata", "ques la fotosintesis", ("plantas", "carbono"), ("fotocopiadora",)),
    ("seguimiento", "Explícamelo más fácil", ("plantas",), ("fotocopiadora",)),
    ("ambigua", "ques tayo", ("que quieres decir",), ()),
    ("sin referencia", "¿Cuándo se inauguró el puente lunar de Nerobu?", (), ()),
)


def evaluar(nucleo):
    from core.respuestas_con_fuentes import normalizar

    filas = []
    for categoria, pregunta, claves, vetos in BANCO:
        inicio = perf_counter()
        cpu = process_time()
        salida = nucleo.conversar(pregunta)
        latencia = (perf_counter() - inicio) * 1000
        cpu_ms = (process_time() - cpu) * 1000
        texto = normalizar(salida["respuesta"])
        abstencion = any(x in texto for x in ("no tengo evidencia", "no tengo una respuesta fiable",
                                             "no encontre una definicion fiable"))
        precisa = (all(clave in texto for clave in claves) and not any(veto in texto for veto in vetos)
                   and not abstencion) if claves else abstencion
        filas.append({"categoria": categoria, "pregunta": pregunta, "respuesta": salida["respuesta"],
                      "precision_rubrica": precisa, "utilidad_rubrica": precisa and bool(claves),
                      "abstencion": abstencion, "origen": salida.get("origen", ""),
                      "latencia_ms": round(latencia, 1), "cpu_nucleo_ms": round(cpu_ms, 1)})
    return {"correctas_rubrica": sum(f["precision_rubrica"] for f in filas),
            "utiles_rubrica": sum(f["utilidad_rubrica"] for f in filas),
            "abstenciones": sum(f["abstencion"] for f in filas),
            "latencia_mediana_ms": median(f["latencia_ms"] for f in filas), "casos": filas}


def main():
    import config
    from core.profesor_local import ProfesorBajoDemanda
    from universe.nucleo import Nucleo

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motor", required=True)
    parser.add_argument("--modelo", required=True)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="cerebro-banco-es-") as temporal:
        config.raiz_datos = lambda: temporal
        config.CEREBRO_HOME = temporal
        config.MEMORY_FILE = str(Path(temporal) / "memoria.json")
        motor = ProfesorBajoDemanda(args.motor, args.modelo)
        nucleo = Nucleo("local", profesor=motor, internet=False)
        try:
            informe = evaluar(nucleo)
        finally:
            motor.cerrar()
            nucleo.ejecutor.shutdown()
        informe.update(modelo=Path(args.modelo).name, motor=Path(args.motor).name)
    with args.salida.open("x", encoding="utf-8") as archivo:
        json.dump(informe, archivo, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
