"""Tareas de escritorio compartidas por los clientes del núcleo."""
from collections import OrderedDict
import os
from pathlib import Path
import re
from time import monotonic, sleep

from agent.control_ventanas import buscar, etiquetas, interpretar
from agent import coordinador_hibrido
from agent.demostracion_escritorio import Demostraciones
from core import aplicaciones_linux, documentos_usuario, energia_linux, ventanas_x11


CATEGORIA = "documento_escritorio"
_CONFIRMAR = {"si", "si recuerdalo", "si recuerdalo por favor", "recuerdalo"}
_RECHAZAR = {"no", "no gracias", "no lo recuerdes", "cancelar", "cancela"}
_ABRIR = r"(abre|abreme|abrir|abri|abra|habre|habreme)"
_DOCUMENTO = r"(?:(?:el|mi|un)\s+)?documento"
_VERBOS = {"enfoca": ("Enfoqué", "enfocar"), "minimiza": ("Minimicé", "minimizar"),
           "maximiza": ("Maximicé", "maximizar"), "restaura": ("Restauré", "restaurar"),
           "izquierda": ("Coloqué a la izquierda", "colocar a la izquierda"),
           "derecha": ("Coloqué a la derecha", "colocar a la derecha")}
_NAVEGADOR = {"el navegador", "navegador", "el navegador web", "navegador web"}
_CATEGORIAS = {"calculadora": "Calculator", "gestor de archivos": "FileManager", "editor de codigo": "IDE"}


_ENERGIA = {
    "apagar": r"apaga(?:me)? (?:(?:mi|el) )?(?:ordenador|equipo|portatil)",
    "reiniciar": r"reinicia (?:(?:mi|el) )?(?:ordenador|equipo|portatil)",
    "suspender": r"suspende(?: (?:mi |el )?(?:ordenador|equipo|portatil))?|ponlo a dormir",
    "bloquear": r"bloquea (?:mi |la )?pantalla",
    "cerrar sesión": r"cierra (?:mi |la )?sesion",
}

def _accion_energia(orden):
    orden = orden.removesuffix(" cuando te confirme")
    return next((accion for accion, patron in _ENERGIA.items() if re.fullmatch(patron, orden)), None)


class Escritorio:
    def __init__(self, nucleo):
        self.nucleo = nucleo
        self.pendientes = OrderedDict()
        self.enlaces = OrderedDict()
        self.ultimas_aplicaciones = OrderedDict()
        self.ultimas_ventanas = OrderedDict()
        self.demostraciones = Demostraciones(self)

    def limpiar(self):
        self.pendientes.clear()
        self.enlaces.clear()
        self.ultimas_aplicaciones.clear()
        self.ultimas_ventanas.clear()
        self.demostraciones.activas.clear()

    def _guardar_pendiente(self, cliente, **datos):
        self.pendientes[cliente] = (monotonic() + 300, datos)
        self.pendientes.move_to_end(cliente)
        if len(self.pendientes) > 64:
            self.pendientes.popitem(last=False)

    def _autorizar(self):
        self.nucleo.exigir_permisos("READ")
        if not self.nucleo.documentos_usuario:
            raise PermissionError("Esta acción requiere el lanzador local y permiso de lectura.")

    def _autorizar_escritura(self):
        self.nucleo.exigir_permisos("WRITE")

    def _clave(self, nombre):
        return "documento_escritorio:" + documentos_usuario._normalizar(nombre)

    def _abrir(self, cliente, nombre, ruta, *, verbo="abre", recordar=True):
        self._autorizar()
        if not documentos_usuario.permitido(ruta):
            return "El documento dejó de estar disponible en las carpetas autorizadas."
        resultado = aplicaciones_linux.abrir_documento(ruta)
        aplicacion = resultado["aplicacion"]
        if not resultado["aceptado"]:
            if not aplicacion:
                return f"No hay una aplicación predeterminada para {resultado['formato']}."
            return f"{aplicacion} no aceptó la solicitud de apertura."
        respuesta = (f"{aplicacion} aceptó la apertura de «{ruta.name}». "
                     "Comprueba que el documento se muestra en pantalla.")
        if recordar:
            self._guardar_pendiente(cliente, nombre=nombre, ruta=ruta, resultado=resultado, verbo=verbo)
            respuesta += " Si lo ves y quieres guardar la selección, responde «Sí, recuérdalo». Puedes responder «No»."
        return respuesta

    @staticmethod
    def _recordar_contexto(contexto, cliente, valor):
        contexto[cliente] = valor
        contexto.move_to_end(cliente)
        if len(contexto) > 64:
            contexto.popitem(last=False)

    def _aplicacion(self, app, cliente, avance=None):
        self._autorizar()
        try:
            anteriores = {v["id"] for v in ventanas_x11.listar()}
        except RuntimeError:
            anteriores = None
        if aplicaciones_linux.lanzar_aplicacion(app["id"]):
            self._recordar_contexto(self.ultimas_aplicaciones, cliente, app)
            if avance is not None:
                avance.append(True)
            if anteriores is not None:
                for _ in range(5):
                    try:
                        nuevas = [v for v in ventanas_x11.listar() if v["id"] not in anteriores]
                    except RuntimeError:
                        break
                    candidatas = self._ventanas_de_app(app, nuevas)
                    if len(candidatas) == 1:
                        ventana = candidatas[0]
                        self._recordar_contexto(self.ultimas_ventanas, cliente, ventana)
                        self.demostraciones.registrar(cliente, "abrir", app["id"])
                        if avance is not None:
                            avance[-1] = "verificado"
                        return f'{app["nombre"]} abrió la ventana «{ventana["titulo"]}».'
                    sleep(.12)
            return f'{app["nombre"]} aceptó la solicitud de apertura.'
        return f'No pude iniciar {app["nombre"]}.'

    def _ventana(self, cliente, accion, ventana, avance=None):
        self._autorizar()
        titulo = ventana["titulo"]
        if accion == "cierra":
            self._autorizar_escritura()
            self._guardar_pendiente(cliente, cierre=ventana)
            return f'¿Cerrar «{titulo}»? Responde «Confirmar cierre» o «Cancelar».'
        verificado = ventanas_x11.actuar(accion, ventana)
        hecho, infinitivo = _VERBOS[accion]
        if verificado:
            self._recordar_contexto(self.ultimas_ventanas, cliente, ventana)
            if ventana["clase"] and ventana["clase"] != "N/A":
                self.demostraciones.registrar(cliente, accion, ventana["clase"])
            if avance is not None:
                avance.append("verificado")
            return f'{hecho} «{titulo}».'
        return f'Solicité {infinitivo} «{titulo}», pero el gestor no confirmó el cambio.'

    def repetir_demostracion(self, pasos, cliente):
        resultados = []
        for indice, paso in enumerate(pasos, 1):
            self._autorizar()
            accion, objetivo = paso["accion"], paso["objetivo"]
            avance = []
            try:
                if accion == "abrir":
                    app = next((a for a in aplicaciones_linux.listar() if a["id"] == objetivo), None)
                    respuesta = (self._aplicacion(app, cliente, avance) if app
                                 else "La aplicación enseñada ya no está disponible.")
                else:
                    ventanas = [v for v in ventanas_x11.listar() if v["clase"] == objetivo]
                    respuesta = (self._ventana(cliente, accion, ventanas[0], avance) if len(ventanas) == 1
                                 else "La ventana enseñada cambió o hay varias coincidencias.")
            except RuntimeError as exc:
                respuesta = str(exc)
            resultados.append(f"{indice}. {respuesta}")
            if avance != ["verificado"]:
                resultados.append("Detuve la demostración. Revisa la aplicación antes de volver a enseñarme este paso.")
                break
        return "\n".join(resultados)

    def _impedimentos_energia(self, accion):
        motivos = energia_linux.impedimentos(accion)
        if accion != "bloquear" and any(
                tarea["estado"] in {"en cola", "en ejecución"} for tarea in self.nucleo.consultar_tareas()):
            motivos.append("Cerebro tiene tareas en cola o en ejecución.")
        if accion in {"apagar", "reiniciar", "cerrar sesión"}:
            abiertas = ventanas_x11.listar()
            if abiertas:
                motivos.append("Hay ventanas abiertas. Comprueba y guarda tu trabajo antes de cerrar la sesión.")
        return motivos

    def _energia(self, accion, cliente):
        self._autorizar()
        self._autorizar_escritura()
        try:
            motivos = self._impedimentos_energia(accion)
        except RuntimeError as exc:
            return f"No pude comprobar si es posible {accion}. {exc}"
        if motivos:
            return f"No está disponible {accion} ahora.\n" + "\n".join(f"• {m}" for m in motivos)
        self._guardar_pendiente(cliente, energia=accion)
        return f"Responde «Confirmar {accion}» para ejecutar la acción o «Cancelar»."

    def _controlar(self, texto, normal, cliente, avance=None):
        from universe.consultas import destino_desktop, desea_studio

        control = interpretar(normal)
        apertura = re.fullmatch(rf"{_ABRIR}\s+(?:la aplicacion |el programa )?(.{{2,100}})", normal)
        archivo = re.fullmatch(r"(?:busca|encuentra) (?:el |un |mi )?archivo (.+)", normal)
        if archivo:
            self._autorizar()
            archivos = documentos_usuario.buscar(archivo[1])
            if avance is not None and archivos:
                avance.append("verificado")
            return ("Archivos encontrados:\n" + "\n".join(f"• {ruta.relative_to(Path.home())}" for ruta in archivos)
                    if archivos else "No encontré ese archivo en las carpetas autorizadas.")
        if avance is not None and apertura and destino_desktop(texto) == "youtube":
            self._autorizar()
            if not self.nucleo.internet:
                raise PermissionError("Permiso de internet desactivado.")
            if aplicaciones_linux.abrir_url("https://www.youtube.com"):
                avance.append(True)
                return "El navegador aceptó abrir YouTube."
            return "El navegador rechazó la apertura de YouTube."
        if control:
            self._autorizar()
            self.pendientes.pop(cliente, None)
            accion, nombre = control
            general = re.fullmatch(
                r"(?:todo(?: menos (.+)| y deja cerebro funcionando)?|todas las ventanas de trabajo)", nombre
            ) if accion == "cierra" else None
            if general:
                return self._preparar_cierre_general(cliente, general[1])
            if accion == "cierra" and nombre.startswith("todo "):
                return "Para el cierre general, indica qué aplicación quieres conservar."
            ventanas = ventanas_x11.listar()
            grupo = re.fullmatch(r"todas las ventanas de (.+)", nombre) if accion == "cierra" else None
            if grupo:
                self._autorizar_escritura()
                apps = buscar(grupo[1], aplicaciones_linux.listar(), etiquetas)
                if len(apps) != 1:
                    return "Indica el nombre exacto de una aplicación instalada para cerrar sus ventanas."
                candidatas = self._ventanas_de_app(apps[0], ventanas)
                if not candidatas:
                    return "No pude vincular ventanas abiertas a esa aplicación."
                self._guardar_pendiente(cliente, cierres=candidatas)
                lista = "\n".join(f'• {v["titulo"]}' for v in candidatas)
                return "Responde «Confirmar cierre» para solicitar el cierre normal, o «Cancelar».\n" + lista
            if accion == "lista":
                return ("Ventanas abiertas:\n" + "\n".join(f'• {v["titulo"]}' for v in ventanas)
                        if ventanas else "No hay ventanas abiertas.")
            if nombre in {"esta ventana", "ventana activa", "la ventana activa"}:
                ventana = ventanas_x11.activa()
                return self._ventana(cliente, accion, ventana, avance) if ventana else "No identifiqué la ventana activa."
            if nombre in {"esa ventana", "la ventana anterior", "la ventana"}:
                anterior = self.ultimas_ventanas.get(cliente)
                if anterior:
                    actual = next((v for v in ventanas if all(
                        v[campo] == anterior[campo] for campo in ("id", "pid", "clase"))), None)
                    if actual:
                        return self._ventana(cliente, accion, actual, avance)
                return "No identifiqué una ventana anterior de esta conversación."
            app = None
            if nombre in _NAVEGADOR:
                app = aplicaciones_linux.navegador_predeterminado()
                if not app:
                    return "No encontré un navegador predeterminado para HTTPS."
            elif nombre in {"el programa que acabas de abrir", "la aplicacion que acabas de abrir",
                             "el que acabas de abrir"}:
                app = self.ultimas_aplicaciones.get(cliente)
                if not app:
                    return "Todavía no he abierto una aplicación en esta conversación."
            if app:
                candidatos = self._ventanas_de_app(app, ventanas)
            else:
                candidatos = buscar(nombre, ventanas, lambda v: [*v["clase"].split("."), v["titulo"]])
            if not candidatos:
                return "No encontré una ventana que coincida con ese nombre."
            if len(candidatos) == 1:
                return self._ventana(cliente, accion, candidatos[0], avance)
            self._guardar_pendiente(cliente, ventanas=candidatos[:12], accion=accion)
            return "Elige una ventana por número o responde «Cancelar».\n" + "\n".join(
                f"{i}. {v['titulo']}" for i, v in enumerate(candidatos[:12], 1))
        destino = destino_desktop(texto)
        if (apertura and destino != "youtube"
                and not desea_studio(texto)
                and re.fullmatch(r"[\w .()+-]+", apertura[2])):
            self._autorizar()
            self.pendientes.pop(cliente, None)
            nombre = re.sub(r" (?:por favor|otra vez|de nuevo)$", "", apertura[2])
            if nombre in _NAVEGADOR:
                app = aplicaciones_linux.navegador_predeterminado()
                candidatas = [app] if app and app["id"] else []
            else:
                apps = [a for a in aplicaciones_linux.listar() if a["id"]]
                candidatas = buscar(nombre, apps, etiquetas, aproximada=True)
                if not candidatas:
                    categoria = _CATEGORIAS.get(re.sub(r"^(?:el|la) ", "", nombre))
                    candidatas = [a for a in apps if categoria in a.get("categorias", [])]
                if not candidatas:
                    candidatas = buscar(nombre, apps, lambda a: a.get("alias", []))
            if not candidatas:
                return "No encontré una aplicación instalada con ese nombre. Puedes pedirme la lista de aplicaciones."
            if len(candidatas) == 1 and (nombre in _NAVEGADOR or buscar(nombre, candidatas, etiquetas)):
                return self._aplicacion(candidatas[0], cliente, avance)
            self._guardar_pendiente(cliente, aplicaciones=candidatas[:12])
            return "Elige una aplicación por número o responde «Cancelar».\n" + "\n".join(
                f"{i}. {app['nombre']}" for i, app in enumerate(candidatas[:12], 1))
        return None

    def _preparar_cierre_general(self, cliente, excepcion):
        self._autorizar_escritura()
        ventanas = ventanas_x11.listar()
        aplicaciones = [app for app in aplicaciones_linux.listar() if app.get("id")]
        conservar = []
        if excepcion in {"el navegador", "navegador", "tu", "cerebro"}:
            # Los navegadores pueden alojar un cliente de Cerebro.
            excepcion = None
        if excepcion:
            apps = buscar(excepcion, aplicaciones, etiquetas)
            if len(apps) != 1:
                return "No pude identificar la excepción con seguridad. Indica el nombre de la aplicación."
            conservar = self._ventanas_de_app(apps[0], ventanas)

        candidatas = []
        excluidas = []
        for ventana in ventanas:
            razon = self._motivo_proteccion(ventana, aplicaciones, conservar)
            if razon:
                excluidas.append(f'• {ventana["titulo"]} ({razon})')
            else:
                candidatas.append(ventana)
        exclusiones = "\nConservaré:\n" + "\n".join(excluidas) if excluidas else ""
        if not candidatas:
            return "No identifiqué ventanas de trabajo aptas para el cierre general." + exclusiones
        self._guardar_pendiente(cliente, cierres=candidatas, general=True)
        nombres = "\n".join(f'• {v["titulo"]}' for v in candidatas)
        return ("Solicitaré el cierre normal de estas ventanas:\n" + nombres + exclusiones +
                "\nRevisa si hay documentos sin guardar o tareas activas. "
                "Responde «Confirmar cierre» o «Cancelar».")

    def _motivo_proteccion(self, ventana, aplicaciones, conservar):
        if ventana in conservar:
            return "excepción solicitada"
        if ventana["pid"] == str(os.getpid()) or any(
                "cerebro" in ventana[campo].casefold() for campo in ("clase", "titulo")):
            return "cliente de Cerebro"
        compatibles = [app for app in aplicaciones if self._ventanas_de_app(app, [ventana])]
        if not compatibles:
            return "aplicación sin identificar"
        for app in compatibles:
            categorias = set(app.get("categorias", []))
            formatos = set(app.get("formatos", []))
            if (categorias.intersection({"TerminalEmulator", "WebBrowser", "System", "Settings"})
                    or formatos.intersection({"x-scheme-handler/http", "x-scheme-handler/https"})):
                return "navegador, terminal o componente del sistema"
        try:
            if ventanas_x11.admite_cierre_general(ventana):
                return None
        except RuntimeError:
            return "la ventana cambió durante la consulta"
        return "ventana especial o proceso no identificado"

    def _secuencia(self, pasos, cliente):
        respuestas = []
        self.pendientes.pop(cliente, None)
        if any(_accion_energia(paso) for paso in pasos[:-1]):
            return "La solicitud de energía o bloqueo debe ser el último paso."
        for indice, paso in enumerate(pasos):
            avance = []
            energia = _accion_energia(paso)
            respuesta = self._energia(energia, cliente) if energia else self._controlar(
                paso, documentos_usuario._normalizar(paso), cliente, avance)
            respuestas.append(respuesta or f"No pude ejecutar «{paso}» como acción de escritorio.")
            if not avance:
                resto = pasos[indice + 1:]
                if resto and cliente in self.pendientes:
                    self.pendientes[cliente][1]["resto"] = resto
                elif resto:
                    respuestas.append("Detuve los pasos restantes.")
                break
        return "\n".join(respuestas)

    def _continuar(self, respuesta, resto, cliente, completado=False):
        if resto and completado:
            return respuesta + "\n" + self._secuencia(resto, cliente)
        if resto and cliente in self.pendientes:
            self.pendientes[cliente][1]["resto"] = resto
        elif resto:
            return respuesta + "\nDetuve los pasos restantes."
        return respuesta

    @staticmethod
    def _ventanas_de_app(app, ventanas):
        clases = {documentos_usuario._normalizar(valor) for valor in etiquetas(app) if valor}
        return [ventana for ventana in ventanas if clases.intersection(
            documentos_usuario._normalizar(ventana["clase"]).split("."))]

    def _descargar_imagen(self, paso, abrir_fuente):
        from base64 import b64encode
        from core import imagenes_publicas
        from core.actividad_neuronal import publicar

        self._autorizar()
        self._autorizar_escritura()
        if not self.nucleo.internet:
            raise PermissionError("Permiso de internet desactivado.")
        tema = paso.argumentos["tema"]
        imagen = imagenes_publicas.CATALOGO.get(tema)
        if not imagen:
            return {"respuesta": "La descarga verificada admite la imagen de la Tierra del catálogo de NASA."}

        estado = ""
        try:
            if abrir_fuente:
                if not aplicaciones_linux.abrir_url(imagen.pagina):
                    return {"respuesta": "El navegador no aceptó abrir la fuente. La descarga quedó pendiente."}
                estado = "El navegador aceptó abrir la ficha de NASA.\n"
            publicar("investigando", "herramienta")
            datos, ancho, alto = imagenes_publicas.descargar(imagen)
            adjunto = self.nucleo.adjuntar(imagen.nombre, b64encode(datos).decode("ascii"))
            ruta = self.nucleo.ruta(adjunto["nombre"], lectura=True)
            if ruta.stat().st_size != len(datos) or ruta.read_bytes() != datos:
                raise ValueError("El archivo guardado no coincide con lo descargado.")
        except (OSError, RuntimeError, ValueError) as exc:
            return {"respuesta": f"{estado}No pude completar la descarga verificada. {exc}"}
        return {"respuesta": (f"{estado}Guardé y verifiqué {adjunto['nombre']} en Studio "
                             f"({ancho} × {alto} px).\nFuente: {imagen.pagina}\nCrédito: {imagen.credito}. "
                             "Para verla, di «Abre la imagen de la Tierra que descargaste».")}

    def planificar(self, pregunta, cliente):
        from agent.plan_escritorio import elaborar

        pasos = elaborar(pregunta)
        if not pasos:
            return None
        primero, *resto = pasos
        if pasos[-1].herramienta == "descargar_imagen":
            return self._descargar_imagen(pasos[-1], primero.herramienta == "abrir_fuente_imagen")
        if primero.herramienta in {"abrir_web", "analizar_web"}:
            self.nucleo.exigir_permisos("READ")
            if not self.nucleo.internet:
                raise PermissionError("Permiso de internet desactivado.")
            url = primero.argumentos.get("url") or self.enlaces.get(cliente)
            if not url:
                return {"respuesta": "Pega un enlace HTTP o HTTPS junto a la orden."}
            self.enlaces[cliente] = url
            self.enlaces.move_to_end(cliente)
            if len(self.enlaces) > 64:
                self.enlaces.popitem(last=False)
            if primero.herramienta == "analizar_web":
                return {"respuesta": self._analizar_enlace(url)}
            return {"respuesta": "El enlace se abrirá desde el lanzador local.", "abrir_url": url}
        if primero.herramienta == "compatibilidad":
            self.nucleo.exigir_permisos("READ")
            actual = self.nucleo.archivo_en_contexto
            if not actual:
                return {"respuesta": "Adjunta y analiza un archivo primero."}
            ruta = self.nucleo.ruta(actual, lectura=True)
            if not ruta.is_file():
                return {"respuesta": "El archivo actual ya no está disponible."}
            dato = aplicaciones_linux.aplicaciones_compatibles(ruta)
            lista = ", ".join(dato["aplicaciones"]) or "ninguna"
            return {"respuesta": f"{ruta.name} · {dato['formato']}. Aplicaciones asociadas: {lista}. "
                                 "La asociación indica compatibilidad de apertura."}
        if primero.herramienta == "capacidades":
            from shutil import which

            if not self.nucleo.agente.tiene_permisos("READ"):
                return {"respuesta": "Bloqueado por permisos: READ. No inspeccioné aplicaciones ni carpetas."}
            if not self.nucleo.documentos_usuario:
                return {"respuesta": "El acceso local a documentos está desactivado en esta sesión."}
            try:
                apps = aplicaciones_linux.listar()
                inventario = f"Comprobado ahora: GIO devolvió {len(apps)} aplicaciones visibles."
            except RuntimeError as exc:
                inventario = f"Inventario no disponible: {exc}"
            try:
                ventanas = ventanas_x11.listar()
                escritorio = f"X11 respondió con {len(ventanas)} ventanas."
                faltan = [programa for programa in ("xprop", "xdotool", "xwininfo", "xrandr") if not which(programa)]
                if faltan:
                    escritorio += " Faltan utilidades de control: " + ", ".join(faltan) + "."
                if not self.nucleo.agente.tiene_permisos("WRITE"):
                    escritorio += " Cierre bloqueado por permisos: WRITE."
                elif which("xprop"):
                    escritorio += " Cierre general selectivo disponible con confirmación."
            except RuntimeError as exc:
                escritorio = f"Control de ventanas no disponible: {exc}"
            lectura_pdf = "disponible" if which("pdftotext") else "bloqueada: falta pdftotext"
            red = "habilitadas" if self.nucleo.internet else "bloqueadas por configuración"
            return {"respuesta": (f"{inventario}\nBúsqueda local en {len(documentos_usuario.carpetas())} carpetas autorizadas."
                                  f"\n{escritorio}"
                                  f"\nExtracción de PDF: {lectura_pdf}. Aperturas aún sin verificar en esta consulta."
                                  f"\nConsultas públicas: {red}. Demostraciones disponibles para aperturas y cambios de ventanas verificados.")}
        self._autorizar()
        self.pendientes.pop(cliente, None)
        if primero.herramienta == "buscar_contenido":
            caminos, limitado = documentos_usuario.buscar_por_contenido(**primero.argumentos)
            criterios, reciente, nombre = {}, False, "documento por contenido"
            if not caminos:
                aviso = "Revisión parcial por límites de cantidad o tamaño." if limitado else ""
                return {"respuesta": "No encontré el texto en los TXT y Markdown revisados. " + aviso}
        else:
            criterios = dict(primero.argumentos)
            reciente = criterios.pop("reciente", False)
            caminos, limitado = documentos_usuario.buscar_filtrado(**criterios, reciente=reciente)
            formato = next(iter(criterios["extensiones"])) if "extensiones" in criterios else criterios["tipo"]
            nombre = (formato + " " + criterios.get("nombre", "")).strip()
        if any(paso.herramienta == "resumir_pdf" for paso in resto):
            from subprocess import SubprocessError
            from universe.consultas import _extracto, _leer_texto

            self.nucleo.exigir_permisos("WRITE")
            if limitado or not caminos:
                return {"respuesta": "No pude identificar con seguridad el PDF más reciente. Acota la búsqueda."}
            ruta = caminos[0]
            if not documentos_usuario.permitido(ruta):
                return {"respuesta": "El PDF dejó de estar disponible."}
            try:
                texto = _leer_texto(ruta)
            except (OSError, ValueError, SubprocessError) as exc:
                return {"respuesta": f"No pude extraer el PDF: {exc}"}
            if not texto.strip():
                return {"respuesta": "El PDF no contiene texto extraíble. El resumen requiere texto u OCR."}
            apertura = aplicaciones_linux.abrir_documento(ruta)
            if not apertura["aceptado"]:
                return {"respuesta": "La aplicación no aceptó abrir el PDF. No preparé el guardado."}
            resumen = _extracto(texto)
            self._guardar_pendiente(cliente, resumen=resumen, fuente=ruta)
            return {"respuesta": (f"La aplicación aceptó abrir «{ruta.name}». Resumen de hasta 12 páginas:\n"
                                  f"{resumen}\nResponde «Confirmar guardar resumen» para escribirlo en Studio.")}
        if resto and criterios.get("nombre"):
            self.nucleo.memoria.cargar_memoria()
            recuerdo = self.nucleo.memoria.recuperar_largo_plazo(self._clave(nombre))
            if isinstance(recuerdo, dict) and isinstance(recuerdo.get("ruta"), str):
                ruta = Path(recuerdo["ruta"])
                if ruta in caminos:
                    return {"respuesta": self._abrir(cliente, nombre, ruta, recordar=False)}
        if not caminos:
            return {"respuesta": "No encontré archivos que coincidan en las carpetas autorizadas."}
        if resto and (reciente or len(caminos) == 1) and not limitado:
            return {"respuesta": self._abrir(cliente, nombre, caminos[0], recordar=not reciente)}
        sufijo = "\nLa búsqueda alcanzó su límite. Usa un nombre o fecha más precisos." if limitado else ""
        opciones = "\n".join(f"{i}. {ruta.relative_to(Path.home())}" for i, ruta in enumerate(caminos, 1))
        self._guardar_pendiente(cliente, nombre=nombre, opciones=caminos, verbo="abre")
        return {"respuesta": "Coincidencias. Responde con el número para abrir un archivo o «Cancelar».\n"
                             + opciones + sufijo}

    def _analizar_enlace(self, url):
        from urllib.parse import unquote, urlencode, urlsplit
        from core.fuentes_publicas import consultar_json
        from universe.consultas import _extracto

        enlace = urlsplit(url)
        if enlace.scheme != "https" or enlace.netloc != "es.wikipedia.org" or not enlace.path.startswith("/wiki/"):
            return "Puedo analizar enlaces públicos de la Wikipedia en español. Esta dirección no se consultó."
        titulo = unquote(enlace.path.removeprefix("/wiki/"))
        if not titulo or len(titulo) > 150 or ":" in titulo or "/" in titulo:
            return "Selecciona el enlace directo a un artículo público."
        parametros = urlencode({"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                                "titles": titulo, "format": "json", "formatversion": 2, "redirects": 1})
        try:
            paginas = consultar_json("https://es.wikipedia.org/w/api.php?" + parametros)["query"]["pages"]
            if not paginas or not (texto := paginas[0].get("extract")):
                return "Wikipedia no devolvió texto legible para ese artículo."
            return f"Resumen de la introducción de {paginas[0]['title']}\n\n{_extracto(texto)}\n\nFuente: {url}"
        except (OSError, ValueError, KeyError, TypeError):
            return "No pude leer el artículo de Wikipedia."

    def _proponer_plan(self, objetivo, cliente):
        self._autorizar()
        if not self.nucleo.profesor.configurado:
            return "El profesor local está desactivado."
        if len(objetivo) > 350:
            return "Describe el objetivo del plan en hasta 350 caracteres."
        self.pendientes.pop(cliente, None)
        try:
            plan = coordinador_hibrido.validar_plan(self.nucleo.profesor.planificar_escritorio(objetivo))
        except (RuntimeError, ValueError) as exc:
            return f"No pude preparar un plan verificable. {exc}"
        coordinador_hibrido.disponible(self.nucleo, plan)
        self._guardar_pendiente(cliente, plan_profesor=plan)
        texto = "\n".join(f"{i}. {coordinador_hibrido.representar(*paso)}" for i, paso in enumerate(plan, 1))
        return ("Propuesta del profesor local. Todavía no se ejecutó ningún paso.\n" + texto
                + "\nResponde «Confirmar plan de escritorio» o «Cancelar».")

    def consultar(self, pregunta, cliente):
        texto = re.sub(r"^cerebro(?:[,\s]+)", "", pregunta.strip(" ¡!¿?."), flags=re.I)
        normal = documentos_usuario._normalizar(texto)
        propuesta = coordinador_hibrido.PREGUNTA_PLAN.fullmatch(texto)
        if propuesta:
            return self._proponer_plan(propuesta[1], cliente)
        if re.fullmatch(r"abre (?:la )?imagen (?:de la tierra )?que descargaste", normal):
            from core.imagenes_publicas import CATALOGO

            self._autorizar()
            nombre = CATALOGO["tierra"].nombre
            ruta = self.nucleo.ruta("adjuntos/" + nombre, lectura=True)
            if not ruta.is_file():
                return "Todavía no encuentro la imagen en los adjuntos de Studio."
            resultado = aplicaciones_linux.abrir_documento(ruta)
            if resultado["aceptado"]:
                return f"El visor aceptó abrir {nombre}."
            return "El escritorio no encontró un visor asociado con JPEG o el visor rechazó la apertura."
        demostracion = self.demostraciones.consultar(normal, cliente)
        if demostracion is not None:
            return demostracion
        accion_energia = _accion_energia(normal)
        if accion_energia:
            self.pendientes.pop(cliente, None)
            return self._energia(accion_energia, cliente)
        if re.fullmatch(r"enciende (?:mi |el )?(?:ordenador|equipo|portatil)", normal):
            self._autorizar()
            diagnostico = energia_linux.diagnosticar_activacion()
            return (f"{diagnostico}\nPara despertar o encender el equipo hace falta un emisor externo autorizado. "
                    "El firmware, el estado de energía y la red determinan si Wake-on-LAN funcionará. "
                    "Esta instalación carece de un emisor configurado.")
        if re.fullmatch(r"apaga(?: (?:mi |el )?(?:ordenador|equipo|portatil))? cuando .+", normal):
            self.pendientes.pop(cliente, None)
            return "El apagado diferido requiere una tarea identificada y todavía no está disponible."
        if re.fullmatch(r"(?:pon|coloca) (?:las )?dos ventanas (?:una al lado de la otra|lado a lado)", normal):
            self._autorizar()
            self.pendientes.pop(cliente, None)
            ventanas = ventanas_x11.listar()[:20]
            if len(ventanas) < 2:
                return "Se necesitan dos ventanas abiertas."
            self._guardar_pendiente(cliente, colocar=ventanas)
            opciones = "\n".join(f"{i}. {v['titulo']}" for i, v in enumerate(ventanas, 1))
            return "Indica dos números en orden de izquierda a derecha, por ejemplo «1 y 2».\n" + opciones
        orden = re.fullmatch(rf"{_ABRIR}\s+{_DOCUMENTO}\s+(.+)", normal)
        olvidar = re.fullmatch(rf"olvida\s+{_DOCUMENTO}\s+(.+)", normal)
        repetir = re.fullmatch(r"(?:abrelo|vuelve a abrirlo)(?: otra vez| de nuevo)?", normal)
        if orden or olvidar:
            if orden:
                self._autorizar()
            self.pendientes.pop(cliente, None)
            referencia = orden[2] if orden else olvidar[1]
            nombre = re.sub(r"^(?:de|llamado)\s+|(?:\s+(?:otra vez|de nuevo|por favor))+$",
                            "", referencia).strip()
            clave = self._clave(nombre)
            self.nucleo.memoria.cargar_memoria()
            if olvidar:
                self._autorizar_escritura()
                borrado = self.nucleo.memoria.eliminar_largo_plazo(clave)
                return "Olvidé la selección." if borrado else "No tengo una selección guardada para ese documento."
            recuerdo = self.nucleo.memoria.recuperar_largo_plazo(clave)
            if isinstance(recuerdo, dict) and isinstance(recuerdo.get("ruta"), str):
                ruta = Path(recuerdo["ruta"])
                if documentos_usuario.permitido(ruta):
                    return self._abrir(cliente, nombre, ruta, recordar=False)
            encontrados = documentos_usuario.buscar(nombre)
            if not encontrados:
                return "No encontré el documento en las carpetas autorizadas."
            if len(encontrados) == 1:
                return self._abrir(cliente, nombre, encontrados[0], verbo=orden[1])
            self._guardar_pendiente(cliente, nombre=nombre, opciones=encontrados, verbo=orden[1])
            opciones = "\n".join(f"{i}. {ruta.relative_to(Path.home())}"
                                  for i, ruta in enumerate(encontrados, 1))
            return "Encontré varios documentos. Responde con el número de opción o «Cancelar».\n" + opciones
        if repetir:
            self._autorizar()
            self.nucleo.memoria.cargar_memoria()
            recuerdos = [(clave, entrada) for clave, entrada in self.nucleo.memoria.long_term_memory.items()
                         if isinstance(entrada, dict) and entrada.get("categoria") == CATEGORIA]
            if len(recuerdos) != 1:
                return "Indica qué documento quieres volver a abrir."
            clave, _ = recuerdos[0]
            return self.consultar("abre el documento llamado " + clave.split(":", 1)[1], cliente)

        if re.fullmatch(r"(?:(?:que|cuales) (?:aplicaciones|programas)(?: estan)? (?:tengo |hay )?instalad[oa]s|"
                        r"(?:lista|muestra|descubre) (?:mis |las |los )?(?:aplicaciones|programas)(?: instalad[oa]s)?)", normal):
            self._autorizar()
            apps = aplicaciones_linux.listar()
            lineas = [f"• {app['nombre']}" + (f" · {', '.join(app['formatos'][:3])}" if app["formatos"] else "")
                      for app in apps[:80]]
            return (f"Aplicaciones visibles instaladas (mostrando {len(lineas)} de {len(apps)})\n" + "\n".join(lineas)
                    if apps else "El escritorio no devolvió aplicaciones visibles.")

        separador = rf"(?:,\s*(?:(?:y|e)\s+)?|\s+(?:y luego|y despues|y|e|despues)\s+)"
        inicio = rf"(?:{_ABRIR[1:-1]}|cierra|minimiza|maximiza|enfoca(?:me)?|restaura|pon|mueve|coloca|cambia a|apaga|reinicia|suspende|bloquea)"
        pasos = re.split(separador + rf"(?={inicio}\s)", normal)
        if 1 < len(pasos) <= 8 and all(_accion_energia(paso) or interpretar(paso) or re.fullmatch(
                rf"{_ABRIR} [\w .()+-]{{2,100}}", paso) for paso in pasos):
            return self._secuencia(pasos, cliente)

        control = self._controlar(texto, normal, cliente)
        if control is not None:
            return control

        pendiente = self.pendientes.get(cliente)
        if pendiente is None:
            return None
        plazo, datos = pendiente
        if monotonic() > plazo:
            self.pendientes.pop(cliente)
            return None
        eleccion = re.fullmatch(r"(?:la (?:opcion )?|opcion |numero )?([0-9]{1,2})", normal)
        confirmacion = re.sub(r"[,\s]+", " ", normal)
        if confirmacion in _RECHAZAR:
            self.pendientes.pop(cliente)
            return "De acuerdo. Cancelé la operación pendiente."
        if "plan_profesor" in datos and confirmacion == "confirmar plan de escritorio":
            self._autorizar()
            plan = datos["plan_profesor"]
            coordinador_hibrido.disponible(self.nucleo, plan)
            return self._secuencia([coordinador_hibrido.representar(*paso) for paso in plan], cliente)
        accion = datos.get("energia")
        if accion and confirmacion == "confirmar " + documentos_usuario._normalizar(accion):
            self._autorizar()
            self._autorizar_escritura()
            self.pendientes.pop(cliente)
            try:
                motivos = self._impedimentos_energia(accion)
                if motivos:
                    return "Cancelé la solicitud.\n" + "\n".join(f"• {m}" for m in motivos)
                verificado = energia_linux.solicitar(accion)
            except RuntimeError as exc:
                return f"No pude completar la solicitud de {accion}. {exc}"
            if accion == "bloquear":
                return ("El protector de pantalla de XFCE se activó tras la orden de bloqueo." if verificado
                        else "XFCE recibió la orden de bloqueo. La activación no se pudo confirmar.")
            return f"El sistema aceptó la solicitud de {accion}."
        if "colocar" in datos:
            seleccion = re.fullmatch(r"(\d{1,2}) (?:y )?(\d{1,2})", confirmacion)
            if seleccion:
                indices = [int(numero) - 1 for numero in seleccion.groups()]
                ventanas = datos["colocar"]
                if indices[0] == indices[1] or any(not 0 <= i < len(ventanas) for i in indices):
                    return "Elige dos números distintos de la lista."
                self._autorizar()
                self.pendientes.pop(cliente)
                elegidas = [ventanas[i] for i in indices]
                estados = ventanas_x11.colocar_juntas(*elegidas)
                respuestas = []
                for lado, ventana, verificado in zip(("izquierda", "derecha"), elegidas, estados):
                    hecho, infinitivo = _VERBOS[lado]
                    respuestas.append(f'{hecho} «{ventana["titulo"]}».' if verificado else
                                      f'No pude verificar si se logró {infinitivo} «{ventana["titulo"]}».')
                return "\n".join(respuestas)
        if "resumen" in datos and confirmacion == "confirmar guardar resumen":
            from secrets import token_hex

            self._autorizar()
            self.nucleo.exigir_permisos("WRITE")
            if not documentos_usuario.permitido(datos["fuente"]):
                return "El PDF original ya no está disponible en las carpetas autorizadas."
            nombre = "resumenes/resumen-" + token_hex(6) + ".txt"
            texto = f"Fuente: {datos['fuente'].name}\n\n{datos['resumen']}\n"
            self.nucleo.guardar(nombre, texto)
            if self.nucleo.leer(nombre)["texto"] != texto:
                raise RuntimeError("No pude verificar el contenido guardado.")
            self.pendientes.pop(cliente)
            return f"Guardé y verifiqué «{nombre}» en el espacio de Studio."
        if "cierres" in datos and confirmacion == "confirmar cierre":
            self._autorizar()
            self._autorizar_escritura()
            self.pendientes.pop(cliente)
            respuestas = []
            cierres = datos["cierres"]
            completado = True
            for indice, ventana in enumerate(cierres):
                self._autorizar_escritura()
                try:
                    if datos.get("general") and not ventanas_x11.admite_cierre_general(ventana):
                        raise RuntimeError("La ventana dejó de cumplir las condiciones de cierre general")
                    cerrada = ventanas_x11.actuar("cierra", ventana)
                except RuntimeError as exc:
                    cerrada = False
                    estado = str(exc)
                else:
                    estado = "cerrada" if cerrada else "sigue abierta, comprueba si hay un aviso"
                respuestas.append(f'«{ventana["titulo"]}»: {estado}.')
                if not cerrada:
                    completado = False
                    respuestas.extend(f'«{v["titulo"]}»: cierre aún no solicitado.' for v in cierres[indice + 1:])
                    break
            return self._continuar("\n".join(respuestas), datos.get("resto"), cliente, completado)
        if "cierre" in datos and confirmacion == "confirmar cierre":
            self._autorizar()
            self._autorizar_escritura()
            ventana = datos["cierre"]
            self.pendientes.pop(cliente)
            cerrado = ventanas_x11.actuar("cierra", ventana)
            respuesta = (f'La ventana «{ventana["titulo"]}» se cerró.' if cerrado
                         else "La ventana sigue abierta. Comprueba si la aplicación muestra un aviso.")
            return self._continuar(respuesta, datos.get("resto"), cliente, cerrado)
        if eleccion and ("aplicaciones" in datos or "ventanas" in datos):
            opciones = datos.get("aplicaciones", datos.get("ventanas"))
            indice = int(eleccion[1]) - 1
            if not 0 <= indice < len(opciones):
                return "Elige un número de la lista."
            self.pendientes.pop(cliente)
            avance = []
            respuesta = (self._aplicacion(opciones[indice], cliente, avance) if "aplicaciones" in datos
                         else self._ventana(cliente, datos["accion"], opciones[indice], avance))
            return self._continuar(respuesta, datos.get("resto"), cliente, bool(avance))
        if "opciones" in datos and eleccion:
            indice = int(eleccion[1]) - 1
            if not 0 <= indice < len(datos["opciones"]):
                return "Ese número no está en la lista. Indica una opción válida."
            self.pendientes.pop(cliente)
            return self._abrir(cliente, datos["nombre"], datos["opciones"][indice], verbo=datos["verbo"])
        if "resultado" in datos and confirmacion in _CONFIRMAR:
            self._autorizar()
            self._autorizar_escritura()
            ruta = datos["ruta"]
            if not documentos_usuario.permitido(ruta):
                self.pendientes.pop(cliente)
                return "El documento dejó de estar disponible. No guardé la selección."
            self.nucleo.memoria.cargar_memoria()
            self.nucleo.memoria.guardar_largo_plazo(self._clave(datos["nombre"]), {
                "ruta": str(ruta), "formato": datos["resultado"]["formato"],
                "aplicacion": datos["resultado"]["aplicacion"],
                "evidencia": "confirmacion_usuario",
            }, categoria=CATEGORIA)
            self._guardar_pendiente(cliente, ejemplo=datos["verbo"])
            return (f"Recordaré «{ruta.name}». Para borrar esta selección, escribe «Olvida el documento {datos['nombre']}». "
                    "Si quieres aportar una frase genérica al entrenamiento, escribe «Aprueba ejemplo de apertura».")
        if "ejemplo" in datos and normal == "aprueba ejemplo de apertura":
            self._autorizar()
            self._autorizar_escritura()
            from core.ejemplos_aprobados import aprobar
            aprobar(self.nucleo.raiz / "data" / "ejemplos_aprobados.jsonl",
                    f"{datos['ejemplo'].capitalize()} mi documento de prueba",
                    "Intención: abrir un documento local. Busca candidatos por nombre, "
                    "pide una elección si hay varios y usa la aplicación predeterminada.")
            self.pendientes.pop(cliente)
            return "Ejemplo genérico aprobado para el alumno. El entrenamiento se ejecuta por separado."
        return None
