"""Crea una plantilla de firmware revisable; nunca compila ni flashea."""
from pathlib import Path
import re
import config

_NOMBRE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,49}$")
_PLACAS = {"arduino": "arduino", "esp32": "esp32"}


def preparar_robot(nombre, placa, raiz=None):
    if not _NOMBRE.fullmatch(nombre) or placa not in _PLACAS:
        raise ValueError("Nombre o placa no admitidos (arduino, esp32).")
    base = Path(raiz or config.WORKSPACE_DIR).resolve()
    base.mkdir(parents=True, exist_ok=True)
    destino = base / nombre
    destino.mkdir()  # no sobrescribir ni seguir enlaces existentes
    codigo = '''// Plantilla de Cerebro: LED integrado, sin comunicaciones externas.
// REVISA el pin y el circuito de tu placa antes de compilar.
// No incluye control de motores ni actuadores.
#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif
void setup() { pinMode(LED_BUILTIN, OUTPUT); }
void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
}
'''
    (destino / (nombre + ".ino")).write_text(codigo, encoding="utf-8")
    (destino / "README.md").write_text(
        "# Proyecto de robot Cerebro\n\nPlaca objetivo: " + placa +
        "\n\nPlantilla de parpadeo del LED. El pin LED_BUILTIN depende de la placa. "
        "No se ha compilado, conectado, subido firmware ni controlado hardware. "
        "Comprueba pines, tensión, alimentación y periféricos antes de probar.\n",
        encoding="utf-8")
    return {"ruta": str(destino), "placa": placa, "flasheado": False}
