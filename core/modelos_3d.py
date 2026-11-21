"""Extrae propiedades verificables de mallas Wavefront OBJ locales."""
from hashlib import sha256
from math import isfinite

FORMATO = "malla-obj-v1"
MAX_BYTES = 16 * 1024 * 1024
MAX_LINEA = 8192


def analizar_obj(ruta):
    minimo = [float("inf")] * 3
    maximo = [-float("inf")] * 3
    vertices = caras = triangulos = cuadrilateros = caras_colapsadas = mayor_indice = 0
    firma = sha256()
    consumido = 0

    with ruta.open("rb") as archivo:
        while linea := archivo.readline(MAX_LINEA + 1):
            consumido += len(linea)
            if consumido > MAX_BYTES or len(linea) > MAX_LINEA:
                raise ValueError("El OBJ supera los límites de tamaño de archivo o línea.")
            firma.update(linea)
            campos = linea.partition(b"#")[0].split()
            if not campos:
                continue
            try:
                if campos[0] == b"v":
                    if len(campos) < 4:
                        raise ValueError
                    punto = [float(valor) for valor in campos[1:4]]
                    if any(not isfinite(valor) or abs(valor) > 1e100 for valor in punto):
                        raise ValueError
                    if len(campos) == 5:
                        peso = float(campos[4])
                        if peso != 1:
                            raise ValueError
                    for eje, valor in enumerate(punto):
                        minimo[eje] = min(minimo[eje], valor)
                        maximo[eje] = max(maximo[eje], valor)
                    vertices += 1
                elif campos[0] == b"f":
                    if not 3 <= len(campos) - 1 <= 256:
                        raise ValueError
                    indices = []
                    for campo in campos[1:]:
                        indice = int(campo.split(b"/", 1)[0])
                        if indice < 0:
                            indice = vertices + indice + 1
                        if indice < 1:
                            raise ValueError
                        indices.append(indice)
                    mayor_indice = max(mayor_indice, max(indices))
                    caras += 1
                    triangulos += len(indices) == 3
                    cuadrilateros += len(indices) == 4
                    caras_colapsadas += len(set(indices)) < len(indices)
            except (ValueError, OverflowError):
                raise ValueError(f"Vértice o cara OBJ inválido cerca del byte {consumido}.") from None

    if not vertices or mayor_indice > vertices:
        raise ValueError("El OBJ necesita vértices válidos y las caras deben referenciarlos.")
    return {
        "formato": FORMATO, "sha256": firma.hexdigest(), "vertices": vertices,
        "caras": caras, "triangulos": triangulos, "cuadrilateros": cuadrilateros,
        "caras_con_vertices_repetidos": caras_colapsadas,
        "dimensiones_xyz": [alto - bajo for bajo, alto in zip(minimo, maximo)],
    }


def resumir_malla(datos):
    ejes = " · ".join(f"{eje}: {valor:.6g}" for eje, valor in zip("XYZ", datos["dimensiones_xyz"]))
    return (
        f"{datos['vertices']} vértices · {datos['caras']} caras "
        f"({datos['triangulos']} triangulares y {datos['cuadrilateros']} cuadrangulares).\n"
        f"Dimensiones de la caja envolvente en las unidades del OBJ: {ejes}.\n"
        f"Caras con referencias repetidas: {datos['caras_con_vertices_repetidos']}."
    )
