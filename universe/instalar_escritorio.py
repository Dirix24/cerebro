"""Instala el comando y las entradas de menú para el usuario de MX Linux."""
from argparse import ArgumentParser
import os
from pathlib import Path
from shlex import quote
import sys


def desktop_exec(ruta):
    # Exec de desktop-entry aplica su propio escapado y expansión de %.
    return '"' + str(ruta).replace("\\", "\\\\\\\\").replace('"', '\\\\"').replace(
        "$", "\\\\$").replace("`", "\\\\`").replace("%", "%%") + '"'


def instalar(automatico=True):
    raiz = Path(__file__).resolve().parent.parent
    home = Path.home()
    base = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    binario = home / ".local" / "bin" / "cerebro"
    binario.parent.mkdir(parents=True, exist_ok=True)
    lanzador = ("#!/bin/sh\n# Lanzador de Cerebro\n"
                f"cd {quote(str(raiz))} || exit 1\n"
                f'exec {quote(sys.executable)} -m universe.lanzador "$@"\n')
    escribir(binario, lanzador, "# Lanzador de Cerebro", 0o755)
    modos = {"terminal": "Cerebro Terminal", "escritorio": "Cerebro Escritorio",
             "chat": "Cerebro Chat", "studio": "Cerebro Studio"}
    for modo, nombre in modos.items():
        entrada = ("[Desktop Entry]\nType=Application\nX-Cerebro-Launcher=true\n"
                   f"Name={nombre}\nExec={desktop_exec(binario)} {modo}\n"
                   f"Icon={raiz / 'universe' / 'web' / 'cerebro-logo.png'}\n"
                   f"Terminal={'true' if modo == 'terminal' else 'false'}\n"
                   "Categories=Utility;\nStartupNotify=false\n")
        escribir(base / "applications" / f"cerebro-{modo}.desktop", entrada, "X-Cerebro-Launcher=true")
    configurar_autoinicio(automatico)
    print(f"Comando: {binario}\nBusca Cerebro en el menú de aplicaciones.")
    if str(binario.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        print('Para esta terminal: export PATH="$HOME/.local/bin:$PATH"')


def configurar_autoinicio(activar):
    home = Path.home()
    config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    ruta = config / "autostart" / "cerebro-escritorio.desktop"
    if not activar:
        retirar_entrada(ruta)
        return
    binario = home / ".local" / "bin" / "cerebro"
    if not binario.is_file() or binario.is_symlink() or "# Lanzador de Cerebro" not in binario.read_text():
        raise ValueError("Instala primero el lanzador de Cerebro.")
    entrada = ("[Desktop Entry]\nType=Application\nX-Cerebro-Launcher=true\n"
               "Name=Cerebro Escritorio\nOnlyShowIn=XFCE;\n"
               f"Exec={desktop_exec(binario)} escritorio\nTerminal=false\nStartupNotify=false\n")
    escribir(ruta, entrada, "X-Cerebro-Launcher=true")


def retirar_entrada(ruta):
    if ruta.is_file() and not ruta.is_symlink() and "X-Cerebro-Launcher=true" in ruta.read_text():
        ruta.unlink()


def retirar(raiz):
    home = Path.home()
    binario = home / ".local" / "bin" / "cerebro"
    if (not binario.is_file() or binario.is_symlink() or
            f"cd {quote(str(raiz))} || exit 1" not in binario.read_text()):
        return
    base = Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
    config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    for modo in ("terminal", "escritorio", "chat", "studio"):
        retirar_entrada(base / "applications" / f"cerebro-{modo}.desktop")
    retirar_entrada(config / "autostart" / "cerebro-escritorio.desktop")
    binario.unlink()


def escribir(ruta, contenido, marca, modo=0o644):
    if ruta.is_symlink() or (ruta.exists() and marca not in ruta.read_text()):
        raise FileExistsError(f"Ya existe un archivo ajeno a Cerebro: {ruta}")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    ruta.chmod(modo)


def confirmar(mensaje):
    if not sys.stdin.isatty():
        return False
    try:
        return input(mensaje + " [s/N] ").strip().casefold() in {"s", "sí", "si"}
    except EOFError:
        return False


def preparar_especialistas(args):
    import config
    from core.configuracion_especialistas import MODULOS, configurar, obtener
    from core.motores_instalados import _adaptador_vecino
    from universe.especialidades import _consulta

    rutas = {"CAZEL": args.cazel_raiz, "DARAS": args.daras_raiz}
    for nombre, modulo in MODULOS.items():
        if not rutas[nombre] and not obtener(nombre + "_RAIZ"):
            vecino = _adaptador_vecino(nombre, modulo)
            if vecino and confirmar(f"¿Conectar {nombre} y ejecutar su adaptador local de confianza en {vecino}?"):
                rutas[nombre] = vecino
    proyecto = args.proyecto_cazel or obtener("CAZEL_PROYECTO")
    if not proyecto and (rutas["CAZEL"] or obtener("CAZEL_RAIZ")):
        if confirmar(f"¿Autorizar a CAZEL a analizar proyectos en {config.WORKSPACE_DIR}?"):
            proyecto = Path(config.WORKSPACE_DIR)
            proyecto.mkdir(parents=True, exist_ok=True)
    if any(rutas.values()) or args.proyecto_cazel or (proyecto and not obtener("CAZEL_PROYECTO")):
        configurar(rutas["CAZEL"], rutas["DARAS"], proyecto)
    for nombre in rutas:
        if obtener(nombre + "_RAIZ"):
            prueba = _consulta(nombre, "capacidades", "", red=False)
            print(f"{nombre} · comprobación de conexión: {prueba['estado']}. "
                  + prueba.get("error", ""))


def main():
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--sin-autoinicio", action="store_true", help="no registrar el acompañante al iniciar sesión")
    ap.add_argument("--gestos", choices=("auto", "manos", "marcador", "ninguno"), default="auto",
                    help="prepara los gestos en el entorno virtual (predeterminado: auto)")
    ap.add_argument("--modelo-manos", metavar="RUTA", help="registra un modelo .task ya descargado")
    modelos = ap.add_mutually_exclusive_group()
    modelos.add_argument("--modelo-ollama", metavar="NOMBRE", help="verifica y configura un modelo ya instalado")
    modelos.add_argument("--descargar-modelo-ligero", action="store_true",
                        help="descarga Qwen2.5 0.5B en un Ollama ya instalado (aprox. 400 MB)")
    modelos.add_argument("--sin-modelo-auto", action="store_true", help="no seleccionar un modelo automáticamente")
    ap.add_argument("--cazel-raiz", help="autoriza y guarda la ruta del adaptador de CAZEL")
    ap.add_argument("--daras-raiz", help="autoriza y guarda la ruta del adaptador de DARAS")
    ap.add_argument("--proyecto-cazel", help="selecciona el proyecto local para CAZEL")
    ap.add_argument("--sin-diagnostico", action="store_true", help="omite el diagnóstico final")
    args = ap.parse_args()
    instalar(automatico=not args.sin_autoinicio)
    import config
    raiz = config.raiz_datos()
    from universe.diagnostico_instalacion import configurar_modelo_manos, diagnosticar, instalar_gestos, preparar_gestos_automaticos
    if args.modelo_manos:
        try:
            configurar_modelo_manos(args.modelo_manos)
        except (OSError, ValueError) as error:
            print(f"No se registró el modelo de manos: {error}")
    if args.gestos == "auto":
        print(preparar_gestos_automaticos())
    elif args.gestos != "ninguno" and not instalar_gestos(args.gestos):
        print("La instalación básica sigue disponible. El modo gestual elegido requiere revisión.")
    if args.modelo_ollama or not args.sin_modelo_auto:
        import subprocess
        from core.configuracion_modelo_local import descargar_ligero, leer, preparar_instalacion
        from core.provision_modelo import ofrecer

        try:
            anterior = leer(raiz)
            print(descargar_ligero(raiz) if args.descargar_modelo_ligero
                  else preparar_instalacion(raiz, args.modelo_ollama))
            explicito = any(os.environ.get("CEREBRO_" + nombre) for nombre in
                            ("OLLAMA_MODELO", "PROFESOR_PUERTO", "PROFESOR_MOTOR", "PROFESOR_MODELO"))
            if anterior or explicito:
                from core.profesor_local import ProfesorLocal

                motor = ProfesorLocal.desde_entorno()
                try:
                    motor.conversar("Responde hola en español.")
                    print("Modelo conversacional existente: inferencia de prueba ejecutada.")
                except (OSError, RuntimeError, ValueError) as error:
                    print(f"Modelo conversacional existente conservado, sin inferencia verificada. {error}")
                finally:
                    if hasattr(motor, "cerrar"):
                        motor.cerrar()
            elif not (leer(raiz) or args.modelo_ollama or args.descargar_modelo_ligero):
                print(ofrecer(raiz, confirmar))
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            print(f"Modelo local: no se guardó la selección. {error}")
    try:
        preparar_especialistas(args)
    except (OSError, ValueError) as error:
        print(f"No se registraron los especialistas: {error}")
    if not args.sin_diagnostico:
        diagnosticar(Path(raiz))
    if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) and confirmar("¿Abrir Studio ahora?"):
        from universe.lanzador import lanzar_estudio

        if not lanzar_estudio():
            print("Abre Cerebro Studio desde el menú de aplicaciones.")


if __name__ == "__main__":
    main()
