"""Tareas de escritorio compartidas por los clientes del núcleo."""
from collections import OrderedDict
from pathlib import Path
import re
from time import monotonic

from core import aplicaciones_linux, documentos_usuario, ventanas_x11


CATEGORIA = "documento_escritorio"
_CONFIRMAR = {"si", "si recuerdalo", "si recuerdalo por favor", "recuerdalo"}
_RECHAZAR = {"no", "no gracias", "no lo recuerdes", "cancelar", "cancela"}
_ABRIR = r"(abre|abreme|abrir|abri|abra|habre|habreme)"
_DOCUMENTO = r"(?:(?:el|mi|un)\s+)?documento"


class Escritorio:
    def __init__(self, nucleo):
        self.nucleo = nucleo
        self.pendientes = OrderedDict()
        self.enlaces = OrderedDict()

    def limpiar(self):
        self.pendientes.clear()
        self.enlaces.clear()

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

    def _aplicacion(self, app):
        self._autorizar()
        if aplicaciones_linux.lanzar_aplicacion(app["id"]):
            return f'{app["nombre"]} aceptó la solicitud de apertura.'
        return f'No pude iniciar {app["nombre"]}.'

    def _ventana(self, cliente, accion, ventana):
        self._autorizar()
        titulo = ventana["titulo"]
        if accion == "cierra":
            self._autorizar_escritura()
            self._guardar_pendiente(cliente, cierre=ventana)
            return f'¿Cerrar «{titulo}»? Responde «Confirmar cierre» o «Cancelar».'
        verificado = ventanas_x11.actuar(accion, ventana)
        return (f'Minimicé «{titulo}».' if verificado
                else f'Solicité minimizar «{titulo}», pero el gestor no confirmó el cambio.')

    def _controlar(self, texto, normal, cliente):
        from universe.consultas import destino_desktop, desea_studio

        control = re.fullmatch(r"(cierra|minimiza)\s+(.{2,100})", normal)
        apertura = re.fullmatch(rf"{_ABRIR}\s+(?:la aplicacion |el programa )?(.{{2,100}})", normal)
        buscar = re.fullmatch(r"(?:busca|encuentra) (?:el |un |mi )?archivo (.+)", normal)
        if buscar:
            self._autorizar()
            archivos = documentos_usuario.buscar(buscar[1])
            return ("Archivos encontrados:\n" + "\n".join(f"• {ruta.relative_to(Path.home())}" for ruta in archivos)
                    if archivos else "No encontré ese archivo en las carpetas autorizadas.")
        if control:
            self._autorizar()
            self.pendientes.pop(cliente, None)
            accion, nombre = control.groups()
            nombre = re.sub(r"^(?:la ventana de|el programa|la aplicacion) ", "", nombre)
            ventanas = ventanas_x11.listar()
            if nombre in {"esta ventana", "ventana activa"}:
                ventana = ventanas_x11.activa()
                return self._ventana(cliente, accion, ventana) if ventana else "No identifiqué la ventana activa."
            candidatos = [v for v in ventanas if nombre in documentos_usuario._normalizar(v["titulo"] + " " + v["clase"])]
            if not candidatos:
                return "No encontré una ventana que coincida con ese nombre."
            if len(candidatos) == 1:
                return self._ventana(cliente, accion, candidatos[0])
            self._guardar_pendiente(cliente, ventanas=candidatos[:12], accion=accion)
            return "Elige una ventana por número o responde «Cancelar».\n" + "\n".join(
                f"{i}. {v['titulo']}" for i, v in enumerate(candidatos[:12], 1))
        if (apertura and not destino_desktop(texto) and not desea_studio(texto)
                and re.fullmatch(r"[\w .()+-]+", apertura[2])):
            self._autorizar()
            self.pendientes.pop(cliente, None)
            nombre = apertura[2]
            apps = [a for a in aplicaciones_linux.listar() if a["id"]]
            exactas = [a for a in apps if nombre == documentos_usuario._normalizar(a["nombre"])]
            candidatas = exactas or [a for a in apps if nombre in documentos_usuario._normalizar(a["nombre"])]
            if not candidatas:
                return "No encontré una aplicación instalada con ese nombre."
            if len(candidatas) == 1:
                return self._aplicacion(candidatas[0])
            self._guardar_pendiente(cliente, aplicaciones=candidatas[:12])
            return "Elige una aplicación por número o responde «Cancelar».\n" + "\n".join(
                f"{i}. {app['nombre']}" for i, app in enumerate(candidatas[:12], 1))
        return None

    def planificar(self, pregunta, cliente):
        from agent.plan_escritorio import elaborar

        pasos = elaborar(pregunta)
        if not pasos:
            return None
        primero, *resto = pasos
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
            lectura_pdf = "disponible" if which("pdftotext") else "bloqueada: falta pdftotext"
            red = "habilitadas" if self.nucleo.internet else "bloqueadas por configuración"
            return {"respuesta": (f"{inventario}\nBúsqueda local en {len(documentos_usuario.carpetas())} carpetas autorizadas."
                                  f"\nExtracción de PDF: {lectura_pdf}. Aperturas aún sin verificar en esta consulta."
                                  f"\nConsultas públicas: {red}. Aprendizaje por demostración: pendiente.")}
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
            caminos, limitado = documentos_usuario.buscar_filtrado(**criterios)
            nombre = (criterios["tipo"] + " " + criterios.get("nombre", "")).strip()
        if any(paso.herramienta == "resumir_pdf" for paso in resto):
            from subprocess import SubprocessError
            from universe.consultas import _extracto, _leer_texto

            self.nucleo.exigir_permisos("WRITE")
            if limitado or not caminos:
                return {"respuesta": "No pude identificar con seguridad el PDF más reciente. Acota la búsqueda."}
            ruta = max(caminos, key=lambda item: item.stat().st_mtime_ns)
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

    def consultar(self, pregunta, cliente):
        texto = re.sub(r"^cerebro(?:[,\s]+)", "", pregunta.strip(" ¡!¿?."), flags=re.I)
        normal = documentos_usuario._normalizar(texto)
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
            return "De acuerdo. No guardé una selección nueva."
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
        if "cierre" in datos and confirmacion == "confirmar cierre":
            self._autorizar()
            self._autorizar_escritura()
            ventana = datos["cierre"]
            self.pendientes.pop(cliente)
            cerrado = ventanas_x11.actuar("cierra", ventana)
            return (f'La ventana «{ventana["titulo"]}» se cerró.' if cerrado
                    else "La ventana sigue abierta. Comprueba si la aplicación muestra un aviso.")
        if eleccion and ("aplicaciones" in datos or "ventanas" in datos):
            opciones = datos.get("aplicaciones", datos.get("ventanas"))
            indice = int(eleccion[1]) - 1
            if not 0 <= indice < len(opciones):
                return "Elige un número de la lista."
            self.pendientes.pop(cliente)
            return (self._aplicacion(opciones[indice]) if "aplicaciones" in datos
                    else self._ventana(cliente, datos["accion"], opciones[indice]))
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
