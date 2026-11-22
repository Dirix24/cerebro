"""Prueba Studio en Chromium con un proyecto temporal y especialistas hermanos."""

from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from collections import deque
from zipfile import ZipFile
import os
import shutil

from playwright.sync_api import sync_playwright, expect
from PIL import Image
import config
from universe.nucleo import Nucleo
from universe.servidor import crear_servidor

from tests.pdf_fixture import pdf_fixture
from tests.modelo_fixture import ModeloDePrueba


with TemporaryDirectory() as temporal:
    base = Path(temporal)
    carpeta = base / "proyecto"
    datos = base / "datos"
    carpeta.mkdir()
    datos.mkdir()
    (carpeta / "robot.py").write_text("def avanzar(x, paso):\n    return x + paso\n")
    (carpeta / "test_robot.py").write_text("import unittest\nfrom robot import avanzar\n"
                                         "class Robot(unittest.TestCase):\n"
                                         "    def test_avanzar(self): self.assertEqual(avanzar(1, 2), 3)\n")
    Image.new("RGB", (12, 9), "green").save(carpeta / "grafico.png")
    (carpeta / "informe.pdf").write_bytes(pdf_fixture())
    (carpeta / "plan.md").write_text("# Plan del robot\nPasos del proyecto.\n")
    with ZipFile(carpeta / "guia.docx", "w") as guia:
        guia.writestr("word/document.xml",
                      '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                      '<w:p><w:r><w:t>La fotosíntesis transforma la energía luminosa.</w:t></w:r></w:p></w:document>')
    (carpeta / "datos.csv").write_text("paso,distancia\nuno,2\n")
    (carpeta / "vista.html").write_text("<h1>Vista local</h1><script>window.pruebaActiva=1</script><p>Seguro</p>")
    (carpeta / "rota.py").write_text("def averia()\n    return 1\n")
    config.raiz_datos = lambda: str(datos)
    config.MEMORY_FILE = str(datos / "memoria.json")
    base_repos = Path(__file__).resolve().parents[3]
    os.environ.update(CEREBRO_DARAS_RAIZ=os.environ.get("CEREBRO_DARAS_RAIZ", str(base_repos / "Daras-IA")),
                      CEREBRO_CAZEL_RAIZ=os.environ.get("CEREBRO_CAZEL_RAIZ", str(base_repos / "CAZEL_IA")),
                      CEREBRO_CAZEL_DATOS=str(datos / "cazel"), CEREBRO_CAZEL_PROYECTO=str(carpeta))
    n = Nucleo("local")
    token = "test-studio-frontend-key-control"
    with crear_servidor(0, n, token, abrir_estudio=lambda: True) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with sync_playwright() as driver:
                browser = driver.chromium.launch(executable_path=shutil.which("chromium"), args=["--no-sandbox"])
                page = browser.new_page(viewport={"width": 1360, "height": 820})
                page.set_default_timeout(7000)
                respuestas = deque()
                errores = []
                page.on("pageerror", lambda exc: errores.append(str(exc)))
                page.on("dialog", lambda d: d.accept(respuestas.popleft()) if d.type == "prompt" else d.accept())
                page.goto(f"http://127.0.0.1:{server.server_port}/proyecto#{token}")
                btn = lambda nombre: page.get_by_role("button", name=nombre, exact=True)
                fila = lambda nombre: page.locator("#archivos").get_by_role("button", name=nombre, exact=True)
                contenido = page.get_by_label("Contenido del archivo")
                respuestas.append(str(carpeta))
                btn("Abrir proyecto").click()
                expect(fila("robot.py")).to_be_visible()
                respuestas.append("nuevo.py")
                btn("Nuevo archivo").click()
                expect(page.locator("#archivo-activo")).to_have_text("nuevo.py")
                contenido.fill("valor = 7\n")
                btn("Guardar").click()
                expect(page.locator("#aviso")).to_contain_text("Archivo guardado")
                assert (carpeta / "nuevo.py").read_text() == "valor = 7\n"
                respuestas.extend(["nuevo.py", "renombrado.py"])
                btn("Mover o renombrar").click()
                expect(fila("renombrado.py")).to_be_visible()
                assert not (carpeta / "nuevo.py").exists()
                page.get_by_label("Buscar archivos").fill("renombrado")
                expect(fila("robot.py")).to_have_count(0)
                expect(fila("renombrado.py")).to_be_visible()
                page.get_by_label("Buscar archivos").fill("")
                fila("grafico.png").click()
                expect(page.locator("#visor-central img")).to_be_visible()
                assert page.locator("#visor-central img").evaluate("(img) => img.naturalWidth") == 12
                if all(shutil.which(cmd) for cmd in ("pdftoppm", "pdftotext", "prlimit")):
                    fila("informe.pdf").click()
                    expect(page.locator("#visor-central img")).to_be_visible()
                    expect(page.locator("#visor-central")).to_contain_text("Informe Cerebro")
                    btn("Página siguiente").click()
                    expect(page.locator("#visor-central")).to_contain_text("2 / 2")
                    expect(page.locator("#visor-central")).to_contain_text("energia solar")
                    assert page.locator("#visor-central img").evaluate("(img) => img.naturalWidth") == 980
                    imagen_anterior = page.locator("#visor-central img").get_attribute("src")
                    btn("Ampliar").click()
                    expect(page.locator("#visor-central img")).not_to_have_attribute("src", imagen_anterior)
                    assert page.locator("#visor-central img").evaluate("(img) => img.naturalWidth") > 980
                    respuestas.append("solar")
                    btn("Buscar en PDF").click()
                    expect(page.locator("#aviso")).to_contain_text("Páginas con coincidencias: 2")
                    page.get_by_label("Mensaje para Cerebro").fill("Según el PDF, ¿qué dice de la energia solar?")
                    btn("Enviar").click()
                    expect(page.locator("#resultado-central")).to_contain_text("Página 2")
                fila("plan.md").click()
                expect(page.locator("#visor-central")).to_contain_text("Pasos del proyecto.")
                fila("guia.docx").click()
                expect(page.locator("#visor-central")).to_contain_text("Texto extraído en solo lectura")
                expect(page.locator("#visor-central")).to_contain_text("fotosíntesis")
                page.get_by_label("Mensaje para Cerebro").fill("Resúmelo")
                btn("Enviar").click()
                expect(page.locator("#resultado-central")).to_contain_text("Resumen extractivo")
                page.get_by_label("Mensaje para Cerebro").fill("Profesor, evalúame")
                btn("Enviar").click()
                expect(btn("Responder ejercicio")).to_be_visible()
                respuestas.append("fotosíntesis")
                btn("Responder ejercicio").click()
                expect(page.locator("#resultado-central")).to_contain_text("Correcto.")
                fila("datos.csv").click()
                expect(page.locator("#visor-central table")).to_contain_text("distancia")
                fila("vista.html").click()
                expect(page.locator("#visor-central")).to_contain_text("Vista local")
                assert page.evaluate("typeof window.pruebaActiva") == "undefined"
                btn("Validaciones").click()
                btn("Analizar proyecto").click()
                expect(page.locator("#resultado-central")).to_contain_text("rota.py")
                page.locator("#resultado-central details summary").click()
                btn("Aplicar propuesta de rota.py").click()
                expect(page.locator("#resultado-central")).to_contain_text("aplicado")
                assert "def averia():" in (carpeta / "rota.py").read_text()
                btn("Validaciones").click()
                btn("Pruebas del proyecto").click()
                expect(page.locator("#tareas")).to_contain_text("pruebas", timeout=27000)
                page.get_by_label("Mensaje para Cerebro").fill("Planifica un robot simulado, revisa el código y comprueba lo aprendido")
                btn("Enviar").click()
                expect(page.locator("#resultado-central")).to_contain_text("Simulación", timeout=30000)
                expect(page.locator("#resultado-central")).to_contain_text("PROFESOR")
                expect(page.locator("#mensajes")).to_contain_text("Preparé un plan")
                assert "DARAS (ok)" not in page.locator("#mensajes").inner_text()
                (carpeta / "externo.md").write_text("# Cambio en disco")
                expect(fila("externo.md")).to_be_visible(timeout=12000)
                fila("externo.md").click()
                expect(page.locator("#archivo-activo")).to_have_text("externo.md")
                page.reload()
                btn("Recuperar proyecto anterior").click()
                expect(page.locator("#archivo-activo")).to_have_text("externo.md")
                expect(page.locator("#mensajes")).to_contain_text("Preparé un plan")
                profesor_original = n.profesor
                n.profesor = ModeloDePrueba()
                page.get_by_label("Mensaje para Cerebro").fill("Diseña una web")
                btn("Enviar").click()
                expect(page.locator("#resultado-central")).to_contain_text("+<h1>Una web</h1>")
                assert not (carpeta / "web-propuesta").exists()
                respuestas.append("web-propuesta")
                btn("Guardar propuesta revisada").click()
                expect(page.locator("#visor-central")).to_contain_text("Una web")
                assert (carpeta / "web-propuesta" / "estilo.css").read_text().strip() == "h1{color:navy}"
                n.profesor = profesor_original
                page.get_by_label("Mensaje para Cerebro").fill("Quiero ver qué aprendiste")
                btn("Enviar").click()
                expect(page.locator("#universe")).to_be_visible()
                page.get_by_label("Región de especialista").select_option("CAZEL")
                candidato = page.locator("#nodos").get_by_role("button", name="CAZEL · ok")
                expect(candidato).to_be_visible()
                candidato.click()
                expect(page.locator("#detalle")).to_contain_text("robot.py")
                assert not errores, errores
                browser.close()
                print("Chromium: creación, edición, renombrado, búsqueda, imagen, navegación PDF, zoom renderizado, búsqueda PDF, consulta con página, documento, CSV, HTML inerte, "
                      "diff aprobado, generación web con doble local y aprobación, solicitud de prueba, simulación y evidencias, actualización automática y reapertura.")
        finally:
            server.shutdown()
            worker.join()
            n.ejecutor.shutdown(wait=True)
