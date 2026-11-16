"""Planificación local sin ejecución automática ni permisos implícitos."""
from dataclasses import dataclass, field


@dataclass
class Plan:
    objetivo: str
    pasos: list = field(default_factory=list)
    aprobados: set = field(default_factory=set)

    def agregar(self, descripcion, requiere_permiso=True):
        if not descripcion.strip() or len(self.pasos) >= 20:
            raise ValueError("Paso vacío o límite de pasos alcanzado")
        self.pasos.append({"descripcion": descripcion, "requiere_permiso": requiere_permiso,
                           "completado": False})

    def aprobar(self, indice):
        if not 0 <= indice < len(self.pasos):
            raise IndexError(indice)
        self.aprobados.add(indice)

    def completar(self, indice):
        paso = self.pasos[indice]
        if paso["requiere_permiso"] and indice not in self.aprobados:
            raise PermissionError("Debes aprobar el paso antes de completarlo")
        paso["completado"] = True
