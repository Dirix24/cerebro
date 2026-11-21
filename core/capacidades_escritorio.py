"""Estado de herramientas observado sin abrir ni modificar ventanas."""
from shutil import which

from core import aplicaciones_linux, documentos_usuario, ventanas_x11


def inspeccionar(nucleo):
    permisos = nucleo.agente
    if not permisos.tiene_permisos("READ"):
        return [{"capacidad": "escritorio", "estado": "bloqueada", "evidencia": "Permiso READ requerido."}]
    if not nucleo.documentos_usuario:
        return [{"capacidad": "escritorio", "estado": "bloqueada", "evidencia": "Acceso de escritorio desactivado."}]
    salida = []

    def registrar(capacidad, estado, evidencia):
        salida.append({"capacidad": capacidad, "estado": estado, "evidencia": evidencia})

    try:
        apps = aplicaciones_linux.listar()
        registrar("Abrir aplicaciones", "inventario comprobado", f"GIO encontró {len(apps)} aplicaciones visibles.")
    except RuntimeError as exc:
        registrar("Abrir aplicaciones", "no disponible", str(exc))
    try:
        ventanas = ventanas_x11.listar()
        x11 = True
        registrar("Listar ventanas", "comprobada", f"X11 respondió con {len(ventanas)} ventanas.")
    except RuntimeError as exc:
        x11 = False
        registrar("Listar ventanas", "no disponible", str(exc))
    for capacidad, programa in (("Enfocar y maximizar", "xprop"), ("Minimizar", "xdotool"),
                                ("Colocar ventanas", "xrandr")):
        lista = x11 and which(programa) and which("xprop") and (programa != "xrandr" or which("xwininfo"))
        registrar(capacidad, "disponible" if lista else "no disponible",
                  "Dependencias comprobadas." if lista else "Falta el entorno X11 o una utilidad requerida.")
    cerrar = x11 and permisos.tiene_permisos("WRITE")
    registrar("Cerrar programas", "requiere confirmación" if cerrar else "bloqueada",
              "Cierre normal mediante X11." if cerrar else "Requiere X11 y permiso WRITE.")
    carpetas = documentos_usuario.carpetas()
    registrar("Buscar archivos", "ámbito comprobado", f"{len(carpetas)} carpetas autorizadas.")
    try:
        navegador = aplicaciones_linux.navegador_predeterminado()
    except RuntimeError:
        navegador = None
    registrar("Navegar a YouTube",
              "disponible" if nucleo.internet and navegador else "bloqueada",
              "Asociación HTTPS comprobada." if nucleo.internet and navegador
              else "Requiere internet autorizado y un navegador predeterminado.")
    registrar("Profesor local", "configurado" if nucleo.profesor.configurado else "desactivado",
              "Las órdenes simples usan el agente local.")
    return salida
