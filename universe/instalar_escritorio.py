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


def main():
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--sin-autoinicio", action="store_true", help="no registrar el acompañante al iniciar sesión")
    ap.add_argument("--gestos", choices=("auto", "manos", "marcador", "ninguno"), default="auto",
                    help="prepara los gestos en el entorno virtual (predeterminado: auto)")
    ap.add_argument("--modelo-manos", metavar="RUTA", help="registra un modelo .task ya descargado")
    ap.add_argument("--sin-diagnostico", action="store_true", help="omite el diagnóstico final")
    args = ap.parse_args()
    instalar(automatico=not args.sin_autoinicio)
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
    if not args.sin_diagnostico:
        diagnosticar(Path(__file__).resolve().parent.parent)


if __name__ == "__main__":
    main()
