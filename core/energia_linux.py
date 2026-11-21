"""Adaptadores locales para XFCE y el servicio login1 (systemd o elogind)."""
import json
import os
from pathlib import Path
import re
from shutil import which
import subprocess
from time import sleep


_METODOS = {"apagar": "PowerOff", "reiniciar": "Reboot", "suspender": "Suspend"}


def _ejecutar(programa, *argumentos):
    comando = which(programa)
    if not comando:
        raise RuntimeError(f"Falta {programa}.")
    try:
        return subprocess.run(
            [comando, *argumentos], capture_output=True, text=True, check=True,
            stdin=subprocess.DEVNULL, timeout=5, env={**os.environ, "LC_ALL": "C"},
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("El servicio de energía o de sesión no confirmó la solicitud.") from exc


def _login1(metodo, *argumentos):
    return _ejecutar(
        "busctl", "--system", "--json=short", "--timeout=4",
        "--allow-interactive-authorization=no", "call", "org.freedesktop.login1",
        "/org/freedesktop/login1", "org.freedesktop.login1.Manager", metodo, *argumentos,
    )


def _respuesta(metodo):
    try:
        dato, = json.loads(_login1(metodo))["data"]
        return dato
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("login1 devolvió una respuesta inesperada.") from exc


def impedimentos(accion):
    if accion == "bloquear":
        _ejecutar("xfce4-screensaver-command", "--query")
        return []
    if accion == "cerrar sesión":
        if not os.environ.get("SESSION_MANAGER") or not which("xfce4-session-logout"):
            return ["No encontré una sesión XFCE que admita el cierre normal."]
        return []

    if _respuesta("Can" + _METODOS[accion]) != "yes":
        return ["login1 no autoriza esta acción con los permisos actuales."]
    categoria = "sleep" if accion == "suspender" else "shutdown"
    inhibidores = _respuesta("ListInhibitors")
    try:
        return [f"{quien}: {motivo}" for que, quien, motivo, modo, _, _ in inhibidores
                if categoria in que.split(":") and modo in {"block", "block-weak"}]
    except (AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError("No pude comprobar los inhibidores de login1.") from exc


def diagnosticar_activacion():
    if not which("ethtool"):
        return "Falta ethtool para comprobar Wake-on-LAN en las interfaces Ethernet."
    interfaces = Path("/sys/class/net")
    try:
        cableadas = sorted(
            interfaz.name for interfaz in interfaces.iterdir()
            if (interfaz / "device").exists() and not (interfaz / "wireless").exists()
            and (interfaz / "type").read_text().strip() == "1"
        )
    except OSError:
        return "No pude leer las interfaces Ethernet del equipo."
    if not cableadas:
        return "No identifiqué una interfaz Ethernet física para consultar."
    resultados = []
    for interfaz in cableadas[:4]:
        try:
            informe = _ejecutar("ethtool", interfaz)
        except RuntimeError:
            resultados.append(f"{interfaz}: sin datos accesibles de Wake-on-LAN.")
            continue
        admite = re.search(r"^\s*Supports Wake-on:\s*([a-z]+)", informe, re.M)
        estado = re.search(r"^\s*Wake-on:\s*([a-z]+)", informe, re.M)
        if estado and "g" in estado[1]:
            resultados.append(f"{interfaz}: el controlador indica activación por paquete mágico habilitada.")
        elif admite and "g" in admite[1]:
            resultados.append(f"{interfaz}: el controlador anuncia compatibilidad con paquete mágico.")
        else:
            resultados.append(f"{interfaz}: compatibilidad con paquete mágico sin confirmar.")
    return "\n".join(resultados)


def solicitar(accion):
    if accion == "bloquear":
        _ejecutar("xfce4-screensaver-command", "--lock")
        for _ in range(5):
            if "The screensaver is active" in _ejecutar("xfce4-screensaver-command", "--query").splitlines():
                return True
            sleep(.12)
        return False
    if accion == "cerrar sesión":
        _ejecutar("xfce4-session-logout", "--logout")
    else:
        _login1(_METODOS[accion], "b", "false")
    return None
