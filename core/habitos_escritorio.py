"""Preferencias locales derivadas de transiciones entre aplicaciones conocidas."""
from pathlib import Path

from core.escritorio_studio import cargar_preferencias, guardar_preferencias

APLICACIONES = {
    "code": ("VS Code", "programación"), "code-oss": ("VS Code OSS", "programación"),
    "codium": ("VSCodium", "programación"), "geany": ("Geany", "programación"),
    "kicad": ("KiCad", "electrónica"), "pcbnew": ("KiCad PCB Editor", "electrónica"),
    "eeschema": ("KiCad Schematic Editor", "electrónica"),
}


class Habitos:
    def __init__(self, raiz):
        self.ruta = Path(raiz) / "data" / "habitos-escritorio.json"
        self.actual = None

    def leer(self):
        datos = cargar_preferencias(self.ruta) if not self.ruta.parent.is_symlink() else {}
        cuentas = datos.get("cuentas")
        return {"activo": datos.get("activo") is True,
                "cuentas": {clave: valor for clave, valor in cuentas.items()
                            if clave in APLICACIONES and type(valor) is int and 1 <= valor <= 9999}
                if isinstance(cuentas, dict) else {}}

    def _guardar(self, datos):
        if self.ruta.parent.is_symlink():
            raise PermissionError("Los hábitos requieren un directorio de datos local.")
        self.ruta.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        guardar_preferencias(self.ruta, datos)

    def cambiar(self, activo):
        datos = self.leer()
        datos["activo"] = activo
        self._guardar(datos)
        self.actual = None

    def borrar(self):
        self._guardar({"activo": False, "cuentas": {}})
        self.actual = None

    def registrar(self, clase):
        datos = self.leer()
        if not datos["activo"]:
            return
        anterior, self.actual = self.actual, clase if clase in APLICACIONES else None
        if self.actual is None or self.actual == anterior:
            return
        cuentas = datos["cuentas"]
        cuentas[clase] = min(9999, cuentas.get(clase, 0) + 1)
        self._guardar(datos)

    def sugerencia(self, tema):
        datos = self.leer()
        if not datos["activo"]:
            return None
        candidatos = [(cantidad, APLICACIONES[clave][0]) for clave, cantidad in datos["cuentas"].items()
                      if APLICACIONES[clave][1] == tema and cantidad >= 3]
        if not candidatos:
            return None
        return "Según tus hábitos locales, puedes continuar con " + max(candidatos)[1] + "."
