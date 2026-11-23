"""Estado y operaciones compartidos por las cuatro interfaces."""
import ast
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
from statistics import median
from tempfile import NamedTemporaryFile
from threading import RLock
from time import monotonic, perf_counter

import config
from agent.controlled_agent import ControlledAgent
from agent.lenguaje_natural import interpretar
from chat import Conversacion
from core.actividad_neuronal import publicar, ultimos
from core.conversaciones import Conversaciones
from core import competencias
from core.aprendizaje_autonomo import GestorAprendizaje, debiles
from core.entorno_portatil import detectar_entorno
from core.legado_identidad import leer_origen
from core.profesor_local import GIB, ProfesorLocal, diagnostico as diagnostico_profesor
from core.especialista_escritorio import Especialista
from universe.ensenanza import Ensenanza
from universe.especialidades import Coordinacion
from universe.herramientas import DescargaGit
from core.repaso_espaciado import cargar
from memory.advanced_memory import AdvancedMemoryManager
from universe.cazel import construir_orden, parsear_ayuda
from universe.escritorio import CATEGORIA as CATEGORIA_DOCUMENTO, Escritorio

MIB = 1024 * 1024
PERFILES = {"usb": 32, "local": 256, "servidor": 512, "robot": 16}
ARCHIVOS = {".py", ".txt", ".md", ".json", ".csv", ".css", ".js", ".html", ".svg"}
SIMULADOR = parsear_ayuda([
    "CAZEL 1 simulador", "ORDEN avanzar cm:0:50", "ORDEN girar grados:-180:180",
    "LECTURA posicion cm", "FIN",
])
COMANDOS = {
    "/ayuda", "/estado", "/limpiar", "/calc", "/calcular-local", "/deducir", "/razonar",
    "/memoria", "/recuerdo", "/recordar", "/olvidar", "/extraer-recuerdos", "/insertar-recuerdo",
    "/origen", "/configurar-creador", "/conocimiento", "/enseñar-habilidad", "/corregir-habilidad",
    "/usar-habilidad", "/encadenar-habilidades", "/aprender-ficha", "/internet",
    "/recordar-tarea", "/recordatorios", "/cancelar-recordatorio",
    "/buscar-corpus", "/resumir", "/palabras-clave", "/github-explorar", "/github-leer", "/web",
}
EVENTOS = {
    "analizando": "procesamiento", "aprendido": "aprendizaje", "investigando": "investigación",
    "consolidado": "procesamiento", "asociando": "relaciones", "observando": "inactividad",
    "error": "errores", "razonando": "razonamiento", "recuperando": "memoria",
    "creando": "creación", "verificado": "conocimiento",
}


class Nucleo:
    def __init__(self, perfil, cuota=None, modelo=None, internet=False, solo_lectura=False, meta=None, investigar_auto=False, documentos_usuario=False, *, conversaciones_dir=None, agente=None, profesor=None, especialista=None, aprendizaje=None, ensenanza=None, descarga_git=None, coordinacion=None):
        self.perfil = perfil
        self.cuota = PERFILES[perfil] * MIB if cuota is None else cuota
        if self.cuota <= 0:
            raise ValueError("La cuota debe ser positiva.")
        self.raiz = Path(config.raiz_datos())
        self.estudio = self.raiz / "universe-datos"
        if self.estudio.is_symlink():
            raise ValueError("El directorio de Universe no puede ser un enlace simbólico.")
        self.estudio.mkdir(mode=0o700, exist_ok=True)
        self.agente = agente if agente is not None else ControlledAgent()
        self.aprendizaje = aprendizaje if aprendizaje is not None else GestorAprendizaje()
        self.raiz_alumno = self.raiz / "learning"
        self.descarga_git = descarga_git if descarga_git is not None else DescargaGit()
        self.ensenanza = ensenanza if ensenanza is not None else Ensenanza()
        self.coordinacion = coordinacion if coordinacion is not None else Coordinacion()
        self.profesor = profesor if profesor is not None else ProfesorLocal.desde_entorno()
        self.especialista = especialista if especialista is not None else Especialista.cargar(
            self.raiz / "learning" / "especialista.npz", modelo)
        self.memoria = AdvancedMemoryManager()
        self.chat = Conversacion(modelo, self.memoria, self.agente, info_checkpoint=meta, modo_local=True)
        self.internet = internet
        self.investigar_auto = internet and investigar_auto
        self.documentos_usuario = documentos_usuario
        self.escritorio = Escritorio(self)
        self.solo_lectura = solo_lectura
        self.cerrojo = RLock()
        self.cerrojo_body = RLock()
        self.cerrojo_interfaz = RLock()
        self.interfaces = {}
        self.archivo_en_contexto = None
        self.proyectos_studio = {}
        self.generaciones_studio = OrderedDict()
        self.archivos_sueltos_studio = {}
        self.ejercicios_studio = {}
        self.ejercicios_recientes = OrderedDict()
        self.dialogos_profesor = OrderedDict()
        self.conversaciones = Conversaciones(conversaciones_dir or self.raiz / "data")
        if self.agente.tiene_permisos("READ"):
            self._recuperar_contexto(self.historial()["turnos"])
        self.latencias = deque(maxlen=100)
        self.tareas = deque(maxlen=24)
        self.ejecutor = ThreadPoolExecutor(max_workers=1)
        self.parado = True
        self.posicion = [0.0, 0.0]
        self.angulo = 0.0
        self.telemetria = {}

    def nucleo_terminal(self):
        carpeta = self.raiz / "data" / "terminal"
        if carpeta.is_symlink():
            raise PermissionError("La carpeta de conversaciones de Terminal debe ser local.")
        return Nucleo(self.perfil, cuota=self.cuota, modelo=self.chat.modelo, internet=self.internet,
                      solo_lectura=self.solo_lectura, meta=self.chat.info,
                      investigar_auto=self.investigar_auto, documentos_usuario=self.documentos_usuario,
                      conversaciones_dir=carpeta, agente=self.agente, profesor=self.profesor, especialista=self.especialista,
                      aprendizaje=self.aprendizaje, ensenanza=self.ensenanza, descarga_git=self.descarga_git,
                      coordinacion=self.coordinacion)

    def exigir_permisos(self, *permisos):
        if self.solo_lectura and "WRITE" in permisos:
            raise PermissionError("La sesión es de solo lectura.")
        self.agente.exigir_permisos(*permisos)

    def estado(self):
        entorno = detectar_entorno(self.raiz)
        entorno["ruta_datos"] = entorno.pop("disco_ruta")
        drm = Path("/sys/class/drm")
        entorno["gpu"] = (sorted(tarjeta.name for tarjeta in drm.glob("card[0-9]*")
                                 if tarjeta.name[4:].isdigit() and (tarjeta / "device").exists())
                          if drm.is_dir() else None)
        modelo = self.chat.modelo
        return {
            "perfil": self.perfil, "entorno": entorno, "cuota": self.cuota,
            "uso": self._uso(), "identidad": leer_origen(self.raiz),
            "internet": self.internet, "investigar_auto": self.investigar_auto,
            "solo_lectura": self.solo_lectura,
            "permisos": sorted(self.agente.permisos_concedidos),
            "recuerdos": len(self.memoria.long_term_memory), "turnos_medidos": len(self.latencias),
            "p50_ms": round(median(self.latencias), 2) if self.latencias else None,
            "parametros": modelo.n_parametros() if modelo is not None else None,
            "checkpoint": {clave: valor for clave, valor in self.chat.info.items()
                           if clave in {"paso", "val_bpb", "val_ppl"} and type(valor) in {int, float}
                           and math.isfinite(valor)},
        }

    def interfaz(self, identificador=None, modo=None, visible=True, enfocar=False):
        modos = ("terminal", "chat", "studio")
        with self.cerrojo_interfaz:
            ahora = monotonic()
            self.interfaces = {clave: entrada for clave, entrada in self.interfaces.items()
                               if ahora - entrada[1] < 7}
            if identificador is not None:
                if (not isinstance(identificador, str) or not re.fullmatch(r"[a-f0-9]{24}", identificador)
                        or modo not in modos or type(visible) is not bool or type(enfocar) is not bool):
                    raise ValueError("Interfaz inválida.")
                if visible:
                    if len(self.interfaces) >= 64 and identificador not in self.interfaces:
                        raise ValueError("Hay demasiadas interfaces abiertas.")
                    previa = self.interfaces.get(identificador)
                    activada = ahora if enfocar or previa is None else previa[2]
                    self.interfaces[identificador] = (modo, ahora, activada)
                else:
                    self.interfaces.pop(identificador, None)
            activa = max(self.interfaces.values(), key=lambda dato: dato[2],
                         default=("escritorio", ahora, ahora))
            return {"activa": activa[0]}

    def _modelo_codigo(self):
        modelo = os.environ.get("CEREBRO_OLLAMA_CODIGO")
        if not modelo:
            return self.profesor
        motor = ProfesorLocal(int(os.environ.get("CEREBRO_OLLAMA_PUERTO", "11434")), ollama=modelo)
        motor.ocupado = getattr(self.profesor, "ocupado", motor.ocupado)
        return motor

    def operar_proyecto(self, datos):
        from core.proyecto_studio import ProyectoStudio

        cliente = datos.get("cliente")
        if not isinstance(cliente, str) or not re.fullmatch(r"[a-f0-9]{24}", cliente):
            raise ValueError("Identificador de Studio inválido.")
        self.exigir_permisos("READ")
        accion = datos.get("accion")
        from core.escritorio_studio import (HERRAMIENTAS, abrir_carpeta, analizar_texto, archivo_soltado,
                                            cargar_preferencias, carpetas_personales, guardar_preferencias,
                                            validar_archivo)
        preferencias = self.estudio / "studio-escritorio.json"
        if accion == "escritorio":
            guardadas = cargar_preferencias(preferencias)
            return {"carpetas": carpetas_personales(), "favoritas": guardadas.get("favoritas", []),
                    "tactil": guardadas.get("tactil") is True, "herramientas": HERRAMIENTAS}
        if accion == "tactil":
            self.exigir_permisos("WRITE")
            if type(datos.get("valor")) is not bool:
                raise ValueError("Indica si el modo táctil debe activarse.")
            with self.cerrojo:
                guardadas = cargar_preferencias(preferencias)
                guardadas["tactil"] = datos["valor"]
                guardar_preferencias(preferencias, guardadas)
            return {"tactil": datos["valor"]}
        if accion == "abrir_suelto":
            if datos.get("confirmar") is not True:
                raise PermissionError("Autoriza el archivo elegido.")
            ruta = archivo_soltado(datos.get("ruta"))
            if ruta.parent.resolve(strict=True) != ruta.parent:
                raise PermissionError("Selecciona un archivo dentro de una carpeta real.")
            suelto = ProyectoStudio(str(ruta.parent), lectura_individual=True)
            vista = suelto.inspeccionar(ruta.name)
            if vista["tipo"] != "archivo":
                raise ValueError("Selecciona un archivo, no una carpeta.")
            if cliente not in self.archivos_sueltos_studio and len(self.archivos_sueltos_studio) >= 32:
                self.archivos_sueltos_studio.pop(next(iter(self.archivos_sueltos_studio)))
            self.archivos_sueltos_studio[cliente] = suelto, ruta.name
            return {**vista, "suelto": True}
        if accion in {"suelto", "estado_suelto", "herramienta_suelto", "buscar_pdf_suelto", "abrir_suelto_externo"}:
            referencia = self.archivos_sueltos_studio.get(cliente)
            if referencia is None:
                raise ValueError("Abre y autoriza un archivo primero.")
            suelto, nombre_suelto = referencia
            if accion == "abrir_suelto_externo":
                if datos.get("nombre") != nombre_suelto:
                    raise ValueError("El archivo activo cambió.")
                return self._abrir_original(suelto, nombre_suelto, datos)
            if accion == "buscar_pdf_suelto":
                return suelto.buscar_pdf(nombre_suelto, datos.get("consulta"))
            vista = suelto.inspeccionar(nombre_suelto, contenido=accion != "estado_suelto",
                                        pagina=datos.get("pagina", 1), resolucion=datos.get("resolucion", 980))
            if accion == "herramienta_suelto" and datos.get("herramienta") == "preguntar":
                return self._preguntar_documento(suelto, nombre_suelto, vista, datos.get("consulta"))
            if accion == "herramienta_suelto" and vista.get("extension") == ".pdf":
                return self._herramienta_pdf(suelto, nombre_suelto, vista, cliente, datos, analizar_texto)
            if accion in {"suelto", "estado_suelto"}:
                return {**vista, "suelto": True}
            return self._herramienta_documento(cliente, vista, datos, analizar_texto)
        if accion == "responder_ejercicio":
            ejercicio = self.ejercicios_studio.get(cliente)
            respuesta = datos.get("respuesta")
            if ejercicio is None or not isinstance(respuesta, str) or not 1 <= len(respuesta) <= 300:
                raise ValueError("Abre un ejercicio y escribe una respuesta de hasta 300 caracteres.")
            correcta = respuesta.strip().casefold() == ejercicio["respuesta_esperada"].casefold()
            if datos.get("guardar") is True:
                self.exigir_permisos("WRITE")
                with self.cerrojo:
                    guardadas = cargar_preferencias(preferencias)
                    historial = guardadas.get("evaluaciones", [])[-49:]
                    guardadas["evaluaciones"] = [*historial, {"archivo": ejercicio["archivo"], "correcta": correcta}]
                    guardar_preferencias(preferencias, guardadas)
            return {"correcta": correcta, "salida": ("Correcto." if correcta else
                        f"El término omitido era «{ejercicio['respuesta_esperada']}».")
                    + "\nPasaje: " + ejercicio["referencia"]}
        if accion == "recordado":
            ruta = self.estudio / "studio-proyecto.json"
            if not ruta.is_file() or ruta.is_symlink() or ruta.stat().st_size > 8192:
                return {}
            try:
                recordado = json.loads(ruta.read_text(encoding="utf-8"))
                return recordado if isinstance(recordado, dict) else {}
            except (OSError, ValueError):
                return {}
        if accion == "abrir":
            if datos.get("confirmar") is not True:
                raise PermissionError("Autoriza la carpeta elegida en Studio.")
            proyecto = ProyectoStudio(datos.get("carpeta"))
            if cliente not in self.proyectos_studio and len(self.proyectos_studio) >= 32:
                self.proyectos_studio.pop(next(iter(self.proyectos_studio)))
            self.proyectos_studio[cliente] = proyecto
            return {**proyecto.listar(), "carpeta": str(proyecto.raiz)}
        proyecto = self.proyectos_studio.get(cliente)
        if proyecto is None:
            raise ValueError("Abre y autoriza una carpeta de proyecto en esta ventana.")
        if datos.get("carpeta_esperada") != str(proyecto.raiz):
            raise ValueError("La carpeta activa cambió. Vuelve a seleccionar el proyecto.")
        if proyecto.raiz.resolve() != proyecto.raiz or not proyecto.raiz.is_dir():
            raise PermissionError("La carpeta original dejó de estar disponible.")
        nombre = datos.get("nombre")
        if accion == "listar":
            return proyecto.listar()
        if accion == "favorita":
            self.exigir_permisos("WRITE")
            destino = str(proyecto.raiz)
            with proyecto._directorio(), self.cerrojo:
                guardadas = cargar_preferencias(preferencias)
                favoritas = guardadas.get("favoritas", [])
                favoritas = [p for p in favoritas if p != destino] if destino in favoritas else [*favoritas[-19:], destino]
                guardadas["favoritas"] = favoritas
                guardar_preferencias(preferencias, guardadas)
            return {"favoritas": favoritas}
        if accion == "gestor":
            if datos.get("confirmar") is not True:
                raise PermissionError("Autoriza abrir la carpeta en el gestor local.")
            partes = proyecto._partes(nombre) if nombre else []
            with proyecto._directorio(partes):
                programa = abrir_carpeta(proyecto.raiz.joinpath(*partes))
            return {"salida": "Se solicitó abrir la carpeta con " + programa + "."}
        if accion == "herramienta":
            vista = proyecto.inspeccionar(nombre, pagina=datos.get("pagina", 1))
            if datos.get("herramienta") == "explicar":
                if vista.get("extension") != ".pdf":
                    raise ValueError("Abre primero un archivo PDF.")
                return self._herramienta_pdf(proyecto, nombre, vista, cliente, datos, analizar_texto)
            if datos.get("herramienta") == "preguntar":
                return self._preguntar_documento(proyecto, nombre, vista, datos.get("consulta"))
            if vista.get("extension") == ".pdf":
                return self._herramienta_pdf(proyecto, nombre, vista, cliente, datos, analizar_texto)
            return self._herramienta_documento(cliente, vista, datos, analizar_texto)
        if accion == "buscar_pdf":
            return proyecto.buscar_pdf(nombre, datos.get("consulta"))
        if accion == "leer":
            return {"texto": proyecto.leer(nombre)}
        if accion in {"inspeccionar", "estado_archivo"}:
            return proyecto.inspeccionar(nombre, contenido=accion == "inspeccionar",
                                         pagina=datos.get("pagina", 1), resolucion=datos.get("resolucion", 980))
        if accion == "abrir_externo":
            return self._abrir_original(proyecto, nombre, datos)
        if accion == "fragmento":
            from textwrap import dedent

            proyecto.ruta(nombre)
            texto, pregunta = datos.get("texto"), datos.get("pregunta")
            if not isinstance(texto, str) or not 1 <= len(texto) <= 4000 or not isinstance(pregunta, str) or not 1 <= len(pregunta) <= 300:
                raise ValueError("Selecciona un fragmento y escribe una pregunta breve.")
            observaciones = f"El fragmento de «{nombre}» tiene {len(texto.splitlines())} líneas."
            if nombre.lower().endswith(".py"):
                try:
                    analizado = ast.parse(dedent(texto))
                    funciones = [n.name for n in ast.walk(analizado) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    observaciones += " El fragmento tiene sintaxis Python válida."
                    if funciones:
                        observaciones += " Funciones: " + ", ".join(funciones[:8]) + "."
                except SyntaxError as error:
                    observaciones += f" La selección no forma un bloque Python completo: {error.msg}."
            if self.profesor.configurado and len(texto) + len(pregunta) <= 550:
                try:
                    respuesta = self.profesor.conversar("Revisa este fragmento sin ejecutar código. " + pregunta + "\n" + texto)
                    return {"respuesta": respuesta + "\n\n" + observaciones}
                except RuntimeError:
                    observaciones += " El modelo local de revisión no está disponible."
            return {"respuesta": observaciones}
        if accion == "generar":
            from core.generacion_proyecto import diferencias, validar

            motor = self._modelo_codigo()
            if not motor.configurado:
                raise ValueError("Configura un modelo local de código con Ollama o llama.cpp.")
            archivos = validar(motor.proponer_proyecto(datos.get("objetivo")))
            identificador = os.urandom(12).hex()
            if len(self.generaciones_studio) >= 16:
                self.generaciones_studio.popitem(last=False)
            self.generaciones_studio[identificador] = (cliente, proyecto, archivos)
            return {"id": identificador, "archivos": list(archivos), "diff": diferencias(archivos)}
        if accion == "publicar_generado":
            self.exigir_permisos("WRITE")
            if datos.get("confirmar") is not True:
                raise PermissionError("Confirma la escritura del proyecto revisado.")
            identificador = datos.get("id")
            propuesta = self.generaciones_studio.get(identificador) if isinstance(identificador, str) else None
            if not propuesta or propuesta[:2] != (cliente, proyecto):
                raise ValueError("La propuesta caducó o pertenece a otro proyecto.")
            try:
                resultado = proyecto.publicar_generado(nombre, propuesta[2])
            except FileExistsError:
                raise ValueError("La carpeta de destino ya existe.") from None
            del self.generaciones_studio[identificador]
            return resultado
        if accion == "recordar":
            if self.solo_lectura or not self.agente.tiene_permisos("WRITE"):
                return {"guardado": False}
            if nombre is not None:
                proyecto.inspeccionar(nombre, contenido=False)
            with NamedTemporaryFile(dir=self.estudio, mode="w", encoding="utf-8", delete=False) as tmp:
                json.dump({"carpeta": str(proyecto.raiz), "archivo": nombre}, tmp)
            try:
                Path(tmp.name).replace(self.estudio / "studio-proyecto.json")
            finally:
                Path(tmp.name).unlink(missing_ok=True)
            return {"guardado": True}
        if accion in {"crear", "crear_pagina", "carpeta", "mover", "copiar", "papelera"}:
            self.exigir_permisos("WRITE")
            if datos.get("confirmar") is not True:
                raise PermissionError("Confirma la operación en el proyecto.")
            texto = datos.get("texto", "")
            if accion == "crear_pagina":
                from core.visores_studio import HTML_INICIAL
                if not isinstance(nombre, str) or Path(nombre).suffix.lower() != ".html":
                    raise ValueError("La página requiere extensión .html.")
                accion, texto = "crear", HTML_INICIAL
            try:
                return proyecto.gestionar(accion, nombre, datos.get("destino"), texto=texto)
            except FileExistsError:
                raise ValueError("Ya existe un archivo o carpeta con ese nombre.") from None
            except FileNotFoundError:
                raise ValueError("El origen o la carpeta de destino ya no existe.") from None
        if accion == "analizar":
            return proyecto.analizar()
        if accion == "validar":
            return {"salida": validar_archivo(proyecto.leer(nombre), nombre)}
        if accion in {"guardar", "aplicar", "rechazar", "revertir", "pruebas"}:
            self.exigir_permisos("WRITE")
            if datos.get("confirmar") is not True:
                raise PermissionError("Confirma la operación en el proyecto.")
            if accion == "guardar":
                proyecto.guardar(nombre, datos.get("texto"), datos.get("original"))
                return {"archivo": nombre}
            if accion in {"aplicar", "rechazar", "revertir"}:
                return proyecto.cambiar_propuesta(accion, datos.get("id"))
            if sum(t["estado"] in {"en cola", "en ejecución"} for t in self.tareas) >= 4:
                raise ValueError("Ya hay cuatro tareas en curso.")
            tarea = {"id": os.urandom(6).hex(), "accion": "pruebas", "estado": "en cola", "salida": ""}
            self.tareas.append(tarea)
            self.ejecutor.submit(self._probar_proyecto, tarea, proyecto, cliente)
            return {"id": tarea["id"]}
        raise ValueError("Acción de proyecto desconocida.")

    def _abrir_original(self, proyecto, nombre, datos):
        if not self.documentos_usuario or datos.get("confirmar") is not True:
            raise PermissionError("Autoriza la aplicación local para abrir este documento.")
        if not proyecto.inspeccionar(nombre, contenido=False)["app_externa"]:
            raise ValueError("Este tipo no se admite para abrir en otra aplicación.")
        from core.aplicaciones_linux import abrir_documento
        resultado = abrir_documento(proyecto.raiz / nombre)
        if not resultado.get("aceptado"):
            raise ValueError("La aplicación predeterminada no aceptó el documento.")
        return {"salida": resultado["aplicacion"] + " aceptó la solicitud de apertura."}

    def _preguntar_documento(self, proyecto, nombre, vista, consulta):
        from core.escritorio_studio import recuperar_fragmentos
        from core.visores_studio import html_estatico

        if not isinstance(consulta, str) or not 2 <= len(consulta) <= 350:
            raise ValueError("Escribe una pregunta de hasta 350 caracteres.")
        es_pdf = vista["extension"] == ".pdf"
        texto = vista.get("texto", "")
        if vista["extension"] == ".html":
            texto = "".join(t for t, _ in html_estatico(texto))
        paginas, total = proyecto.texto_pdf(nombre) if es_pdf else ([texto], 1)
        fragmentos = recuperar_fragmentos(consulta, paginas)
        salida = ("Fragmentos relevantes del documento:" if fragmentos
                  else "No encontré un fragmento con términos de la pregunta.")
        for pagina, fragmento in fragmentos:
            referencia = f"Página {pagina}" if es_pdf else nombre
            salida += f"\n\n{referencia} · {fragmento}"
        if fragmentos and self.profesor.configurado and hasattr(self.profesor, "explicar_fragmentos"):
            evidencias = [{"referencia": f"Página {pagina}" if es_pdf else nombre, "texto": texto[:280]}
                          for pagina, texto in fragmentos]
            try:
                explicacion = self.profesor.explicar_fragmentos(consulta, evidencias)
            except RuntimeError:
                salida += "\n\nEl modelo local no respondió. Los extractos siguen disponibles."
            else:
                salida += "\n\nInterpretación del modelo local:\n" + explicacion
        if len(paginas) < total:
            salida += f"\n\nRevisé {len(paginas)} de {total} páginas."
        return {"archivo": nombre, "salida": salida}

    def _herramienta_pdf(self, proyecto, nombre, vista, cliente, datos, analizar):
        pagina = datos.get("pagina")
        if pagina is not None:
            if "pagina" not in vista:
                raise ValueError(vista.get("aviso", "Página de PDF no disponible."))
            resultado = self._herramienta_documento(cliente, vista, datos, analizar)
            if "salida" in resultado:
                resultado["salida"] = f"Página {pagina}\n\n" + resultado["salida"]
            return resultado
        paginas, total = proyecto.texto_pdf(nombre)
        if datos.get("herramienta") in {"resumir", "explicar"}:
            extractos = [f"Página {n}: {' '.join(texto.split())[:240]}"
                         for n, texto in enumerate(paginas, 1) if texto]
            if not extractos:
                raise ValueError("El PDF no contiene texto extraíble. Puede requerir OCR.")
            salida = f"Extractos de {len(paginas)} de {total} páginas.\n\n" + "\n\n".join(extractos)
            if datos.get("herramienta") == "explicar" and self.profesor.configurado and hasattr(self.profesor, "explicar_fragmentos"):
                try:
                    explicacion = self.profesor.explicar_fragmentos("Explica las ideas principales del PDF.", extractos[:4])
                except RuntimeError:
                    salida += "\n\nEl modelo local no respondió. Los extractos siguen disponibles."
                else:
                    salida += "\n\nInterpretación del modelo local sobre los primeros extractos:\n" + explicacion
            return {"archivo": nombre, "salida": salida}
        return self._herramienta_documento(cliente, {**vista, "texto": "\n".join(paginas)}, datos, analizar)

    def _herramienta_documento(self, cliente, vista, datos, analizar):
        herramienta = datos.get("herramienta")
        if herramienta == "analizar" and vista.get("visor") == "imagen":
            modelo = os.environ.get("CEREBRO_OLLAMA_VISION")
            if not modelo:
                return {"archivo": vista["archivo"], "salida": "Configura CEREBRO_OLLAMA_VISION con un modelo visual local de Ollama."}
            from core.profesor_local import ProfesorLocal

            try:
                vision = ProfesorLocal(int(os.environ.get("CEREBRO_OLLAMA_PUERTO", "11434")), ollama=modelo)
                vision.ocupado = getattr(self.profesor, "ocupado", vision.ocupado)
                descripcion = vision.describir_imagen(vista.get("base64"))
            except (ValueError, RuntimeError) as error:
                return {"archivo": vista["archivo"], "salida": f"No pude analizar la imagen con el motor local: {error}"}
            return {"archivo": vista["archivo"], "salida": "Descripción del modelo visual local:\n" + descripcion}
        if herramienta not in ("analizar", "resumir", "evaluar", "validar") or not vista.get("texto"):
            raise ValueError("La herramienta requiere un formato con texto compatible.")
        resultado = analizar(vista["archivo"], vista["texto"], herramienta)
        if "ejercicio" in resultado:
            ejercicio = resultado["ejercicio"]
            if cliente not in self.ejercicios_studio and len(self.ejercicios_studio) >= 32:
                self.ejercicios_studio.pop(next(iter(self.ejercicios_studio)))
            self.ejercicios_studio[cliente] = {"archivo": vista["archivo"], **ejercicio}
            resultado["ejercicio"] = {"pregunta": ejercicio["pregunta"]}
        return resultado

    def _probar_proyecto(self, tarea, proyecto, cliente):
        from core.proyecto_studio import ejecutar_pruebas

        with self.cerrojo:
            if (self.solo_lectura or not self.agente.tiene_permisos("READ", "WRITE")
                    or self.proyectos_studio.get(cliente) is not proyecto):
                tarea.update(estado="error", salida="La autorización del proyecto cambió.")
                return
            tarea["estado"] = "en ejecución"
        try:
            correcto, salida = ejecutar_pruebas(proyecto.raiz)
        except (OSError, ValueError) as exc:
            correcto, salida = False, str(exc)
        with self.cerrojo:
            tarea.update(estado="terminada" if correcto else "error", salida=salida)
        publicar("consolidado" if correcto else "error", "herramienta")

    @property
    def ruta_historial(self):
        return self.conversaciones.ruta(self.conversaciones.activa())

    def historial(self):
        self.exigir_permisos("READ")
        return {"turnos": self.conversaciones.turnos()}

    def estado_conversaciones(self):
        self.exigir_permisos("READ")
        return self.conversaciones.estado()

    def cambiar_conversacion(self, accion, identificador=None):
        self.exigir_permisos("READ", "WRITE")
        if accion == "nueva":
            self.conversaciones.nueva()
        elif accion == "seleccionar":
            self.conversaciones.seleccionar(identificador)
        else:
            raise ValueError("Acción de conversación desconocida.")
        self._limpiar_contexto()
        estado = self.conversaciones.estado()
        self._recuperar_contexto(estado["turnos"])
        return estado

    def _recuperar_contexto(self, turnos):
        for turno in turnos:
            self.memoria.agregar_contexto("usuario" if turno["rol"] == "usuario" else "ia", turno["texto"])

    def borrar_historial(self, confirmar, identificador=None):
        self.exigir_permisos("READ", "WRITE")
        if confirmar is not True:
            raise ValueError("Confirma el borrado de la conversación.")
        activa = self.conversaciones.activa()
        if identificador is not None and identificador != activa:
            raise ValueError("La conversación activa cambió. Actualiza antes de eliminarla.")
        ruta = self.ruta_historial
        self.conversaciones.nueva()
        ruta.unlink(missing_ok=True)
        self.conversaciones.quitar_temporal(activa)
        self._limpiar_contexto()
        return {"turnos": []}

    def borrar_conversaciones(self, confirmar, identificadores):
        self.exigir_permisos("READ", "WRITE")
        if confirmar is not True:
            raise ValueError("Confirma la eliminación de las conversaciones seleccionadas.")
        if (not isinstance(identificadores, list) or not identificadores
                or any(not isinstance(valor, str) for valor in identificadores)):
            raise ValueError("Selecciona al menos una conversación.")
        ids = list(dict.fromkeys(identificadores))
        rutas = [self.conversaciones.ruta(valor) for valor in ids]
        if any(ruta.is_symlink() or (not ruta.is_file() and nombre not in self.conversaciones.temporales)
               for nombre, ruta in zip(ids, rutas)):
            raise ValueError("La lista cambió. Actualiza la selección e inténtalo otra vez.")
        if self.conversaciones.activa() in ids:
            self.conversaciones.nueva()
            self._limpiar_contexto()
        for nombre, ruta in zip(ids, rutas):
            ruta.unlink(missing_ok=True)
            self.conversaciones.quitar_temporal(nombre)
        return {**self.conversaciones.estado(), "eliminadas": len(rutas)}

    def _limpiar_contexto(self):
        self.memoria.limpiar_corto_plazo()
        self.chat.tema_local = None
        self.chat.pregunta_repaso = None
        with self.cerrojo:
            self.dialogos_profesor.clear()
        self.escritorio.limpiar()
        self.archivo_en_contexto = None

    def _registrar_turno(self, pregunta, respuesta):
        if not self.agente.tiene_permisos("WRITE") or self.solo_lectura:
            return
        from core.historial_local import guardar
        # Los comandos de identidad, memoria y archivos pueden contener datos privados.
        if not pregunta.startswith("/") and respuesta and not re.match(
            r"(?i)¿?(?:(?:busca|encuentra)(?:me)? (?:(?:un|el|mi) )?documento|aprende de (?:este|el) modelo|recuerda que|guarda (?:esta memoria|lo aprendido|un resumen)|recuerda (?:lo aprendido|un resumen)|inserta|extrae|exporta|lee|resume|analiza|"
            r"qu[eé] dice (?:el|este) (?:documento|archivo|pdf)|revisa|expl[ií]ca(?:me|lo)?|hazme preguntas|corrige mi respuesta|qu[eé] recuerdas|c[oó]mo me llamo|cu[aá]l es mi nombre)\b", pregunta
        ):
            try:
                guardar(self.ruta_historial, "usuario", pregunta[:2000])
                guardar(self.ruta_historial, "cerebro", respuesta[:2000])
            except OSError:
                publicar("error", "fallo")

    def conversar(self, pregunta, modo=None, cliente=None, documento=None):
        if not isinstance(pregunta, str) or not pregunta.strip() or len(pregunta) > 24000:
            raise ValueError("Escribe un mensaje de hasta 24 000 caracteres.")
        pregunta = pregunta.strip()
        comando = pregunta.partition(" ")[0].casefold() if pregunta.startswith("/") else ""
        if comando and comando not in COMANDOS | {"/modelo"}:
            raise PermissionError("Ese comando está disponible únicamente en la terminal local.")
        if not self.internet and (comando == "/internet" or
                re.match(r"(?i)(?:busca|consulta) en internet\b", pregunta) or
                (interpretar(pregunta) or {}).get("accion", "").startswith("github_")):
            raise PermissionError("El permiso de internet de esta sesión está desactivado.")
        if self.solo_lectura:
            raise PermissionError("La conversación está desactivada en modo de solo lectura.")
        if cliente is not None and (not isinstance(cliente, str) or not re.fullmatch(r"[a-f0-9]{24}", cliente)):
            raise ValueError("Identificador de conversación inválido.")
        from core.documentos_usuario import _normalizar

        intencion = re.sub(r"^cerebro[, ]+", "", _normalizar(pregunta)).strip(" ¿?¡!.")
        if modo == "studio" and not comando:
            orden_generar = re.fullmatch(
                r"(?:haz|crea|disena|programa|genera) (?:una? |el |la )?"
                r"(?:calculadora|web|pagina web|programa|proyecto|script)(?: .*)?", intencion)
            if orden_generar and intencion not in {"crea una pagina web", "crea pagina web"}:
                proyecto = self.proyectos_studio.get(cliente)
                generacion = None
                if not proyecto:
                    respuesta = "Abre y autoriza una carpeta en Studio para preparar el proyecto."
                else:
                    try:
                        generacion = self.operar_proyecto({"accion": "generar", "cliente": cliente,
                            "carpeta_esperada": str(proyecto.raiz), "objetivo": pregunta})
                        respuesta = "Preparé una propuesta. Revisa las diferencias antes de crear los archivos."
                    except (RuntimeError, ValueError) as error:
                        respuesta = f"No pude preparar una propuesta válida: {error}"
                self._registrar_turno(pregunta, respuesta)
                return {"respuesta": respuesta, "generacion": generacion}
        if modo == "studio" and isinstance(documento, dict) and cliente:
            from core.escritorio_studio import intencion_archivo

            herramienta = intencion_archivo(pregunta)
            from core.escritorio_studio import pagina_solicitada, pregunta_documental

            pagina = pagina_solicitada(pregunta)
            consulta = pregunta_documental(pregunta)
            if herramienta or pagina is not None or consulta:
                resultado = self.operar_proyecto({
                    "accion": "herramienta", "cliente": cliente, "nombre": documento.get("nombre"),
                    "carpeta_esperada": documento.get("carpeta"),
                    "herramienta": "preguntar" if consulta else herramienta or "analizar", "consulta": consulta,
                    **({"pagina": pagina} if pagina is not None else {}),
                })
                respuesta = resultado.get("salida") or resultado["ejercicio"]["pregunta"]
                resultado["salida"] = respuesta
                self._registrar_turno(pregunta, respuesta)
                return {"respuesta": respuesta, "documento": resultado}
        if modo == "terminal" and not comando:
            from core.analizador_codigo_local import consultar as consultar_codigo

            analisis = consultar_codigo(pregunta)
            if analisis is not None:
                self.exigir_permisos("READ")
                self._registrar_turno(pregunta, analisis)
                return {"respuesta": analisis, "origen": "analisis_python"}
        if modo == "studio" and re.fullmatch(r"(?:muestrame|ensename|quiero ver) (?:el )?robot(?: simulado)?", intencion):
            simulado = self.body()
            respuesta = "Abrí la vista del simulador local."
            self._registrar_turno(pregunta, respuesta)
            return {"respuesta": respuesta, "vista": "robot", "robot": simulado}
        if not comando:
            from core.matematicas_local import consultar as consultar_matematicas

            calculo = consultar_matematicas(intencion)
            if calculo is not None:
                self._registrar_turno(pregunta, calculo)
                return {"respuesta": calculo, "origen": "matematicas_local"}

            from universe.especialidades import consultar as consultar_especialidades
            from universe.herramientas import resolver

            coordinacion = consultar_especialidades(self, pregunta, intencion)
            if coordinacion is not None:
                if modo == "studio":
                    from core.visores_studio import narrar
                    resultados = coordinacion.get("especialistas", [])
                    if not resultados:
                        resultados = [r for exp in coordinacion.get("experiencias", [])
                                      for r in exp["resultados"]]
                    if resultados and not any(r.get("conclusion") for r in resultados):
                        coordinacion["respuesta"] = narrar(resultados)
                        if any(r.get("sesion") for r in resultados):
                            coordinacion["respuesta"] += "\n\nLa sesión de revisión está en Resultados."
                self._registrar_turno(pregunta, coordinacion["respuesta"])
                return coordinacion

            resultado = self.ensenanza.consultar(self, intencion, (cliente, self.conversaciones.activa()))
            if resultado is not None:
                return resultado
            resultado = resolver(self, pregunta, intencion, (cliente, self.conversaciones.activa()))
            if resultado is not None:
                return resultado
            resultado = self.ensenanza.inferir(self, pregunta)
            if resultado is not None:
                self._registrar_turno(pregunta, resultado["respuesta"])
                return resultado
            estado_aprendizaje = self.aprendizaje.consultar(intencion, self, cliente)
            if estado_aprendizaje is not None:
                return {"respuesta": estado_aprendizaje}
            ensenanza = self._consultar_competencias(intencion, cliente)
            if ensenanza is not None:
                return ensenanza
        if intencion in {"muestrame mis repositorios", "muestrame mis repositorios de github", "lista mis repositorios de github"}:
            from core.github_local import repositorios_cuenta

            self.exigir_permisos("READ")
            if not self.internet:
                raise PermissionError("Activa Internet para consultar tu cuenta de GitHub.")
            try:
                repositorios = repositorios_cuenta()
            except RuntimeError as error:
                return {"respuesta": str(error)}
            return {"respuesta": "Repositorios accesibles (hasta 20):\n" + "\n".join(repositorios)
                    if repositorios else "GitHub no devolvió repositorios accesibles.", "repositorios": repositorios}
        comparacion = re.fullmatch(r"(?:compara|comparar) github ([^ ]+) ([^ ]+) (?:con )?([^ ]+)", pregunta, re.I)
        if comparacion:
            from core.github_local import comparar_publico

            self.exigir_permisos("READ")
            if not self.internet:
                raise PermissionError("Activa Internet para comparar ramas en GitHub.")
            try:
                datos = comparar_publico(*comparacion.groups())
            except (OSError, ValueError) as error:
                return {"respuesta": f"No pude comparar las referencias de GitHub: {error}"}
            return {"respuesta": f"{datos['repositorio']} · {datos['destino']} frente a {datos['base']}: "
                    f"{datos['adelante']} commits por delante y {datos['atras']} por detrás.",
                    "comparacion": datos}
        if intencion in {"cuantos programas tengo instalados", "cuantas aplicaciones tengo instaladas"}:
            from core.aplicaciones_linux import listar

            self.exigir_permisos("READ")
            try:
                cantidad = len({app["id"] for app in listar() if app.get("id")})
            except RuntimeError as error:
                return {"respuesta": str(error)}
            return {"respuesta": f"GIO encontró {cantidad} aplicaciones visibles en el menú de escritorio. "
                    "El conteo incluye identificadores únicos del menú, con independencia de los paquetes instalados.",
                    "aplicaciones_visibles": cantidad}
        if intencion in {"descubre modelos locales", "detecta inteligencias instaladas", "motores locales instalados"}:
            from core.motores_instalados import descubrir, resumir

            self.exigir_permisos("READ")
            motores = descubrir(self.profesor)
            return {"respuesta": resumir(motores), "motores": motores}
        if intencion in {"diagnostico del equipo", "recursos del equipo", "que hardware tengo",
                         "analiza mi ordenador", "analiza mi ordenador y dime que puedo mejorar",
                         "analiza mi rendimiento", "diagnostica mi ordenador"}:
            from core.recursos_locales import inspeccionar, resumir, sugerir

            self.exigir_permisos("READ")
            recursos = inspeccionar(self.raiz)
            recomendaciones = sugerir(recursos)
            salida = resumir(recursos)
            if recomendaciones:
                salida += "\n\n" + "\n".join(recomendaciones)
            return {"respuesta": salida, "recursos": recursos, "recomendaciones": recomendaciones}
        if not comando and intencion in {"que puedo hacer", "que puedes hacer", "capacidades reales"}:
            from core.capacidades_escritorio import inspeccionar
            capacidades = inspeccionar(self)
            texto = "\n".join(f"{c['capacidad']}: {c['estado']}. {c['evidencia']}" for c in capacidades)
            return {"respuesta": texto, "capacidades": capacidades}
        consulta_especialista = re.fullmatch(r"(?:clasifica|detecta) la intencion(?: de)?[: ]+(.+)", intencion)
        if not comando and consulta_especialista:
            self.exigir_permisos("READ")
            return self._sugerir_intencion(consulta_especialista[1]) or {
                "respuesta": "El alumno se abstiene: faltan pruebas suficientes para proponer una intención."}
        if not comando and re.fullmatch(r"(?:estado del profesor|profesor local|que profesor recomiendas)", intencion):
            self.exigir_permisos("READ")
            ficha = diagnostico_profesor(self.raiz)
            recomendacion = ficha["recomendacion"]
            disponible = ficha["ram_disponible_bytes"]
            memoria = f"{disponible / GIB:.1f} GiB disponibles" if disponible is not None else "RAM disponible sin medir"
            estado = "Profesor local configurado" if self.profesor.configurado else "Profesor desactivado"
            detalle = (f"Candidato para probar en CPU: {recomendacion['modelo']} ({recomendacion['licencia']})."
                       if recomendacion else "Los recursos medidos no permiten recomendar un modelo del catálogo.")
            return {"respuesta": f"{estado}. {memoria}. {detalle}", "profesor": ficha}
        if not comando and re.fullmatch(
                r"(?:vamos a programar|programemos|pongamonos a programar|"
                r"empecemos a programar)(?: por favor)?",
                intencion):
            self.exigir_permisos("READ")
            return {"respuesta": "¿Continuamos un proyecto o empezamos uno nuevo? "
                                 "Puedes decir «Abre Studio» o «Abre la terminal».",
                    "compartir_temporal": True}
        if not comando and re.fullmatch(
                r"(?:abre|abreme|inicia) (?:la )?terminal(?: de cerebro)?", intencion):
            self.exigir_permisos("READ")
            return {"respuesta": "La Terminal de Cerebro se abre desde el lanzador local.",
                    "abrir": "terminal", "compartir_temporal": True}
        if not comando:
            from agent.preguntas_locales import calculo_dictado, preguntas_multiples

            preguntas = preguntas_multiples(pregunta)
            if preguntas:
                respuestas = []
                for indice, item in enumerate(preguntas, 1):
                    respuesta = self.conversar(item, modo=modo, cliente=cliente)["respuesta"]
                    respuestas.append(f"{indice}. {item}\n{respuesta}")
                return {"respuesta": "\n\n".join(respuestas)}
            expresion = calculo_dictado(pregunta)
            if expresion is not None:
                respuesta, _ = self.chat.procesar("/calc " + expresion)
                self._registrar_turno(pregunta, respuesta)
                return {"respuesta": respuesta}
        if re.fullmatch(r"(?:cerebro[, ]+)?(?:ponte a analizar|analiza (?:el )?aprendizaje)[.!]?", pregunta, re.I):
            informe = self.analizar_aprendizaje()
            objetivos = "\n".join("• " + tarea["objetivo"] for tarea in informe["propuestas"])
            return {"respuesta": (f"Evaluaciones registradas: {informe['evaluaciones']}. "
                                  f"Correcciones pendientes: {informe['correcciones_pendientes']}.\n"
                                  + informe["resumen_competencias"] + "\n" + objetivos
                                  + "\nMaterias a practicar: " + ", ".join(informe["prioridades_autonomas"])
                                  + ". Di «Prepara entrenamiento autónomo» para revisar la propuesta.")}
        if re.fullmatch(r"(?:cerebro[, ]+)?(?:activa|abre) (?:el )?modo (?:t[aá]ctil|gestual(?: por c[aá]mara)?)[.!]?", pregunta, re.I):
            self.exigir_permisos("READ")
            return {"respuesta": "Abre el modo gestual por cámara desde el lanzador local.", "abrir": "tactil"}
        compuesto = re.fullmatch(
            r"(?:cerebro[, ]+)?abre (?:el )?navegador (?:e|y) investiga (?:sobre )?(.+)", pregunta, re.I)
        if compuesto:
            self.exigir_permisos("READ")
            from universe.consultas import tema_publico
            if not self.internet:
                raise PermissionError("El permiso de internet de esta sesión está desactivado.")
            tema = tema_publico(compuesto[1])
            if tema is None:
                return {"respuesta": "Indica un tema público para investigar."}
            consulta = self.conversar("Investiga " + tema, modo=modo, cliente=cliente)
            return {"respuesta": consulta["respuesta"], "abrir": "navegador", "conservar_respuesta": True}
        if comando == "":
            plan = self.escritorio.planificar(pregunta, cliente)
            if plan is not None:
                return {**plan, "compartir_temporal": True}
            resultado_escritorio = self.escritorio.consultar(pregunta, cliente)
            if resultado_escritorio is not None:
                return {"respuesta": resultado_escritorio, "compartir_temporal": True}
        from universe.consultas import destino_desktop
        destino = destino_desktop(pregunta)
        if destino:
            self.exigir_permisos("READ")
            if destino == "youtube" and not self.internet:
                raise PermissionError("El permiso de internet de esta sesión está desactivado.")
            return {"respuesta": "La apertura requiere el lanzador local de Cerebro.", "abrir": destino,
                    **({"compartir_temporal": True} if destino == "youtube" else {})}
        inicio = perf_counter()
        origen = None
        if self.agente.tiene_permisos("READ"):
            self.memoria.cargar_memoria()
        if comando == "/modelo":
            self.exigir_permisos("READ")
            if self.chat.modelo is None:
                raise ValueError("Inicia con --modelo para cargar un checkpoint propio.")
            texto = pregunta.partition(" ")[2].strip()
            if not texto:
                raise ValueError("Uso: /modelo pregunta")
            respuesta = self.chat.responder_modelo(texto)
            origen = "alumno_neuronal"
        else:
            from universe.consultas import alternativa_publica, consulta_directa, tema_publico

            explicacion = re.fullmatch(r"(?:explicame|explica) (.+)", intencion) if not comando else None
            tema = tema_publico(explicacion[1]) if explicacion else None
            respuesta = consulta_directa(self, pregunta, modo=modo)
            if respuesta is not None and re.match(
                    r"(?:busca|encuentra)(?:me)?\s+(?:(?:un|el|mi)\s+)?documento\b", pregunta, re.I):
                return {"respuesta": respuesta, "compartir_temporal": True}
            if respuesta is None:
                respuesta, _ = self.chat.procesar(pregunta)
                memoria_solicitada = comando == "/recuerdo" or re.fullmatch(
                    r"que recuerdas(?: (?:sobre|de) .+)?", intencion)
                if memoria_solicitada:
                    origen = ("consulta_memoria" if respuesta in {"No tengo recuerdos sobre ese tema.",
                                                                  "Permiso READ requerido."}
                              else "memoria")
                falta_respuesta = respuesta.startswith((
                    "No tengo una respuesta fiable", "No encontré una definición"))
                if (falta_respuesta and not comando
                        and re.search(r"\b(?:archivo|fichero|documento)\b", intencion)
                        and self.agente.tiene_permisos("READ")):
                    sugerencia = self._sugerir_intencion(pregunta)
                    if sugerencia is not None:
                        return {**sugerencia, "compartir_temporal": True}
                conversacion = (not comando and explicacion is None and 2 <= len(pregunta) <= 700
                                and not re.match(r"^(?:abre|cierra|borra|elimina|instala|ejecuta|apaga|reinicia)\b",
                                                 intencion))
                explicita = bool(re.match(r"^(?:cuentame |conversa conmigo sobre |dialoga conmigo sobre )", intencion))
                if (falta_respuesta or explicita) and self.profesor.configurado and (tema or conversacion):
                    self.exigir_permisos("READ")
                    publicar("razonando", "profesor_local")
                    clave_dialogo = (cliente, self.conversaciones.activa())
                    try:
                        if tema:
                            explicada = self.profesor.explicar(tema)
                        else:
                            with self.cerrojo:
                                contexto = self.dialogos_profesor.get(clave_dialogo, ())
                            explicada = self.profesor.conversar(pregunta, contexto)
                        with self.cerrojo:
                            previos = self.dialogos_profesor.get(clave_dialogo, ())
                            self.dialogos_profesor[clave_dialogo] = (*previos, (pregunta, explicada))[-2:]
                            self.dialogos_profesor.move_to_end(clave_dialogo)
                            if len(self.dialogos_profesor) > 64:
                                self.dialogos_profesor.popitem(last=False)
                    except RuntimeError as exc:
                        respuesta += "\nProfesor local: " + str(exc)
                    else:
                        respuesta = "Profesor local: " + explicada
                        origen = "profesor_local"
                if origen != "profesor_local":
                    alternativa = alternativa_publica(self, pregunta, respuesta)
                    if alternativa != respuesta:
                        origen = "consulta_publica"
                    respuesta = alternativa
        self.latencias.append((perf_counter() - inicio) * 1000)
        self._registrar_turno(pregunta, respuesta)
        from universe.consultas import desea_studio
        return {"respuesta": respuesta, **({"origen": origen} if origen else {}),
                **({"abrir": "studio"} if desea_studio(pregunta) else {})}

    def _sugerir_intencion(self, texto):
        if self.especialista is None:
            return None
        from agent.coordinador_hibrido import ACCIONES
        etiqueta = self.especialista.sugerir(texto)
        if etiqueta not in ACCIONES:
            return None
        verbo, permisos = ACCIONES[etiqueta]
        return {"respuesta": f"El alumno propone «{verbo}». Indica el objetivo en una orden directa. "
                             f"La herramienta exige {', '.join(permisos)}.",
                "origen": "alumno_especialista", "intencion": etiqueta, "permisos": list(permisos)}

    def _consultar_competencias(self, intencion, cliente):
        tema = re.fullmatch(r"(ejercicio de|explica ejercicio de|revisa al alumno en) (.+)", intencion)
        if intencion in {"competencias del alumno", "progreso del alumno"}:
            self.exigir_permisos("READ")
            historia = competencias.historial(self.raiz)
            return {"respuesta": competencias.resumen(historia[0] if historia else None),
                    "competencias": historia[:2]}
        if intencion in {"evalua competencias", "evalua las competencias"}:
            self.exigir_permisos("READ", "WRITE")
            if self.chat.modelo is None:
                return {"respuesta": "Carga el modelo alumno para evaluar competencias."}
            informe = competencias.evaluar(self.chat.modelo)
            self.exigir_permisos("WRITE")
            competencias.guardar(self.raiz, informe)
            return {"respuesta": competencias.resumen(informe), "competencias": [informe]}
        materias = {"matematicas": "matemáticas", "espanol": "español", "programacion": "programación",
                    "razonamiento": "razonamiento", "herramientas": "herramientas"}
        if not tema or tema[2] not in materias:
            return None
        self.exigir_permisos("READ")
        materia = materias[tema[2]]
        clave = (cliente, materia)
        if tema[1] == "ejercicio de":
            variante = None
            if self.profesor.configurado:
                try:
                    variante = self.profesor.proponer_variante(materia)
                except RuntimeError:
                    pass
            with self.cerrojo:
                self.ejercicios_recientes[clave] = variante
                self.ejercicios_recientes.move_to_end(clave)
                if len(self.ejercicios_recientes) > 64:
                    self.ejercicios_recientes.popitem(last=False)
        else:
            with self.cerrojo:
                variante = self.ejercicios_recientes.get(clave)
        pregunta, referencia = competencias.ejercicio(materia, variante)
        texto = pregunta
        if tema[1] == "ejercicio de":
            origen = "variante_profesor_verificada" if variante is not None else "catalogo_local"
            return {"respuesta": texto, "materia": materia, "origen": origen}
        salida = None
        if tema[1] == "explica ejercicio de":
            texto += "\nReferencia verificada: " + referencia
        if tema[1] == "revisa al alumno en":
            if self.chat.modelo is None:
                return {"respuesta": "Carga el modelo alumno para revisar su respuesta."}
            nota = competencias.revisar(self.chat.modelo, pregunta, referencia)
            salida = nota["respuesta"]
            texto += f"\nAlumno: {salida or '(sin respuesta)'}. Referencia: {referencia}."
            texto += "\nResultado independiente: " + ("correcto." if nota["correcta"] else "incorrecto.")
        if self.profesor.configurado:
            self.exigir_permisos("READ")
            try:
                explicacion = self.profesor.ensenar(materia, pregunta, referencia, salida)
            except RuntimeError as exc:
                texto += "\nProfesor local: " + str(exc)
            else:
                texto += "\nComentario del profesor local: " + explicacion
        return {"respuesta": texto, "materia": materia}

    def analizar_aprendizaje(self):
        from collections import Counter
        from core.automejora import analizar

        self.exigir_permisos("READ")
        tipos = Counter(nodo["tipo"] for nodo in self.nodos()["nodos"])
        informe = analizar(self.raiz)
        informe["tipos"] = dict(tipos)
        informe["profesor_configurado"] = self.profesor.configurado
        progreso = competencias.historial(self.raiz)
        informe["entrenamientos_registrados"] += sum(bool(r.get("entrenamiento_autonomo")) for r in progreso)
        informe["competencias"] = progreso[:2]
        informe["prioridades_autonomas"] = debiles(progreso)
        informe["estado_autonomo"] = self.aprendizaje.estado()
        informe["puede_preparar_entrenamiento"] = self.chat.modelo is not None and self.agente.tiene_permisos("WRITE")
        informe["resumen_competencias"] = competencias.resumen(progreso[0] if progreso else None)
        informe["especialista"] = self.especialista.informe if self.especialista else None
        if self.especialista:
            medidas = self.especialista.informe["certificado"]
            etiquetas = ", ".join(self.especialista.informe["umbrales"]) or "ninguna"
            informe["resumen_competencias"] += (f"\nIntenciones admitidas del alumno: {etiquetas}. "
                                                f"Abstenciones: {medidas['abstenciones']}/{medidas['total']}.")
        return informe

    def evaluar_alumno(self):
        from tempfile import TemporaryDirectory
        from core.autoevaluacion import ejecutar

        self.exigir_permisos("READ")
        if self.chat.modelo is None:
            return {"evaluadas": 0, "aciertos": 0, "aviso": "El núcleo no tiene un modelo alumno cargado."}
        with TemporaryDirectory(prefix="cerebro-evaluar-") as temporal:
            memoria_prueba = AdvancedMemoryManager(filepath=str(Path(temporal) / "memoria.json"))
            evaluador = Conversacion(self.chat.modelo, memoria_prueba, self.agente, seed=0, modo_local=True)
            evaluador.gen["temperatura"] = 0
            evaluador.gen["max_nuevos"] = min(40, evaluador.gen["max_nuevos"])

            def responder(pregunta):
                memoria_prueba.limpiar_corto_plazo()
                return evaluador.responder_modelo(pregunta)

            notas = ejecutar(self.raiz / "data" / "repaso_espaciado.json", responder, limite=3)
        return {"evaluadas": len(notas), "aciertos": sum(nota["correcto"] for nota in notas),
                "aviso": ("Coincidencia exacta sobre fichas locales. No mide el rendimiento general."
                          if notas else "No hay fichas aprobadas para evaluar.")}

    def nodos(self):
        self.exigir_permisos("READ")
        self.memoria.cargar_memoria()
        nodos = []
        from core.alumno_supervisado import cargar_activo

        _, activo = cargar_activo(self.raiz_alumno)
        _, ultimo = cargar_activo(self.raiz_alumno, "ultimo")
        for informe in (activo, ultimo if ultimo != activo else None):
            if informe is None:
                continue
            antes, despues = informe["antes"], informe["despues"]
            nodos.append({"id": "alumno:" + informe["id"], "tipo": "aprendizaje",
                          "titulo": "Alumno activo de hora y fecha" if informe == activo else "Último candidato",
                          "detalle": f"{antes['aciertos']} → {despues['aciertos']}/{despues['total']}. "
                                     f"{despues['falsos_positivos']} falsos positivos. "
                                     f"{len(informe['generados'])} ejemplos validados de Qwen.",
                          "origen": "Entrenamiento supervisado NumPy"})
        if self.especialista:
            informe = self.especialista.informe
            for etiqueta, ficha in informe["certificado"]["materias"].items():
                estado = "puede sugerir" if etiqueta in informe["umbrales"] else "se abstiene"
                nodos.append({"id": f"competencia-neuronal:{etiqueta}", "tipo": "razonamiento",
                              "titulo": f"Intención neuronal: {etiqueta}",
                              "detalle": f"{estado} · {ficha['aciertos']}/{ficha['total']} aciertos · "
                                         f"{ficha['falsos_positivos']} falsos positivos",
                              "origen": "Evaluación reservada del cabezal del alumno"})
        acciones_aprendidas = set()
        categorias = {}
        for clave, entrada in list(self.memoria.long_term_memory.items())[-120:]:
            if isinstance(entrada, dict):
                categoria = entrada.get("categoria", "general")
                valor = entrada.get("valor")
                if categoria == "ejecucion_demostracion" and isinstance(valor, dict):
                    nombre = clave.partition(":")[2]
                    original = "demostracion_escritorio:" + nombre
                    pasos = valor.get("pasos", [])
                    resumen = ", ".join(f"{p['paso']}: {p['estado']}" for p in pasos
                                        if isinstance(p, dict) and "paso" in p and "estado" in p)
                    nodos.append({"id": "ejecucion:" + sha256(clave.encode()).hexdigest()[:24],
                                  "tipo": "conocimiento" if valor.get("verificados") == valor.get("total") else "errores",
                                  "titulo": "Última ejecución: " + nombre,
                                  "detalle": f"{valor.get('verificados')}/{valor.get('total')} pasos verificados"
                                             + (f" · {resumen}" if resumen else ""),
                                  "vinculos": ["procedimiento:" + sha256(original.encode()).hexdigest()[:24]],
                                  "origen": "Comprobación de estado AT-SPI", "fecha": entrada.get("fecha")})
                    continue
                if categoria == "demostracion_escritorio" and isinstance(valor, list):
                    from agent.demostracion_escritorio import ACCIONES
                    acciones = {p["accion"] for p in valor if isinstance(p, dict)
                                and isinstance(p.get("accion"), str) and p["accion"] in ACCIONES}
                    acciones_aprendidas.update(acciones)
                    nodos.append({"id": "procedimiento:" + sha256(clave.encode()).hexdigest()[:24],
                                  "tipo": "aprendizaje", "titulo": "Procedimiento: " + clave.partition(":")[2],
                                  "detalle": f"{len(valor)} pasos autorizados guardados",
                                  "origen": "Demostración autorizada", "fecha": entrada.get("fecha"),
                                  "vinculos": ["accion-aprendida:" + a for a in sorted(acciones)]})
                    continue
                if categoria == CATEGORIA_DOCUMENTO and isinstance(valor, dict):
                    identificador = sha256(clave.encode()).hexdigest()[:24]
                    nodos.append({"id": "documento:" + identificador, "tipo": "aprendizaje",
                                  "titulo": "Selección de documento confirmada",
                                  "detalle": f"Formato: {valor.get('formato', '')} · {valor.get('aplicacion', '')}",
                                  "origen": "Apertura aceptada y confirmada por el usuario",
                                  "fecha": entrada.get("fecha")})
                    continue
                nodos.append({"id": "memoria:" + clave, "tipo": "memoria", "titulo": clave,
                              "detalle": str(entrada.get("valor", ""))[:500], "origen": "Memoria de largo plazo"})
                if isinstance(categoria, str):
                    categorias.setdefault(categoria, []).append("memoria:" + clave)
                valor = entrada.get("valor")
                if (clave.startswith("modelo3d_") and isinstance(valor, dict)
                        and valor.get("formato") == "malla-obj-v1"):
                    from core.modelos_3d import resumir_malla
                    try:
                        detalle = resumir_malla(valor)
                    except (KeyError, TypeError, ValueError):
                        continue
                    nodos.append({"id": "malla:" + clave, "tipo": "aprendizaje",
                                  "titulo": Path(str(valor.get("archivo", clave))).name,
                                  "detalle": detalle, "origen": "Medición local de un OBJ",
                                  "fecha": entrada.get("fecha"),
                                  "vinculos": ["memoria:" + clave]})
        for accion in sorted(acciones_aprendidas):
            nodos.append({"id": "accion-aprendida:" + accion, "tipo": "relaciones",
                          "titulo": "Acción compartida: " + accion,
                          "detalle": "Presente en al menos una demostración guardada.",
                          "origen": "Pasos de procedimientos autorizados"})
        recientes = competencias.historial(self.raiz)
        informe = next((r for r in recientes if "materias" in r), None)
        if informe:
            for materia, nota in informe["materias"].items():
                nodos.append({"id": "competencia:" + materia, "tipo": "razonamiento", "titulo": materia,
                              "detalle": f"{nota['aciertos']}/{nota['total']} respuestas del alumno",
                              "origen": "Evaluación neuronal reservada", "fecha": informe.get("fecha")})
                errores = [r for r in nota["resultados"] if not r["correcta"]][:2]
                for i, error in enumerate(errores):
                    nodos.append({"id": f"error-competencia:{materia}:{i}", "tipo": "errores",
                                  "titulo": f"Error del alumno: {materia}",
                                  "detalle": f"{error['pregunta']} · Esperado: {error['esperada']} · "
                                             f"Respuesta: {error['respuesta'] or '(vacía)'}",
                                  "vinculos": ["competencia:" + materia], "origen": "Prueba reservada"})
        for i, resultado in enumerate(r for r in recientes[:8] if r.get("entrenamiento_autonomo")):
            materias = resultado["entrenamiento_autonomo"]
            nodos.append({"id": f"entrenamiento:{i}", "tipo": "aprendizaje",
                          "titulo": "Candidato evaluado",
                          "detalle": ("Elegible para revisión" if resultado["elegible_para_revision"] else "Rechazado")
                          + f" · pérdida {resultado['bpb_antes']:.3f} → {resultado['bpb_despues']:.3f}"
                          + " · mejoras: " + (", ".join(resultado["mejoras"]) or "ninguna")
                          + " · regresiones en competencias: " + (", ".join(resultado["regresiones"]) or "ninguna"),
                          "vinculos": ["competencia:" + m for m in materias],
                          "origen": "Entrenamiento aislado", "fecha": resultado.get("fecha")})
        for categoria, relacionados in categorias.items():
            if len(relacionados) > 1:
                nodos.append({"id": "categoria:" + categoria, "tipo": "relaciones", "titulo": categoria,
                              "origen": "Categoría de memoria registrada",
                              "detalle": f"{len(relacionados)} recuerdos en esta categoría",
                              "vinculos": relacionados})
        for i, evento in enumerate(ultimos(80)):
            estado = evento["estado"]
            nodos.append({"id": f"evento:{evento['fecha']}:{i}", "tipo": EVENTOS[estado],
                          "titulo": estado, "detalle": evento["texto"],
                          "origen": "Registro de actividad", "fecha": evento["fecha"]})
        db = self.raiz / "data" / "habilidades.sqlite3"
        if db.is_file() and not db.is_symlink():
            with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as con:
                for nombre, rev, ejemplos in con.execute(
                    "SELECT name, revision, examples FROM skills ORDER BY name LIMIT 100"
                ):
                    nodos.append({"id": f"habilidad:{nombre}", "tipo": "aprendizaje", "titulo": nombre,
                                  "detalle": f"Revisión {rev} · {ejemplos} ejemplos",
                                  "origen": "Base de habilidades"})
        db = self.raiz / "data" / "conocimiento.sqlite3"
        if db.is_file() and not db.is_symlink():
            with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as con:
                for i, pregunta, respuesta, fuente in con.execute(
                    "SELECT id,pregunta,respuesta,fuente FROM hechos ORDER BY id DESC LIMIT 60"
                ):
                    nodos.append({"id": f"ficha:{i}", "tipo": "conocimiento", "titulo": pregunta,
                                  "detalle": respuesta[:600], "origen": fuente, "grupo": "Fuente registrada"})
        for i, ficha in enumerate(cargar(self.raiz / "data" / "repaso_espaciado.json")[:40]):
            nodos.append({"id": f"repaso:{i}", "tipo": "conocimiento", "titulo": ficha["pregunta"],
                          "detalle": ficha["respuesta"], "origen": "Ficha de repaso aprobada"})
        from universe.especialidades import Experiencias

        nodos.extend(Experiencias(self.estudio / "experiencias-v1.sqlite3").nodos())
        return {"nodos": nodos}

    def respaldo(self, datos=None):
        self.exigir_permisos("READ" if datos is None else "WRITE")
        self.memoria.cargar_memoria()
        formato = "cerebro-memoria-v1"
        if datos is None:
            publicar("recuperando", "memoria")
            return {"formato": formato, "long_term": self.memoria.long_term_memory}
        if self.solo_lectura:
            raise PermissionError("La sesión es de solo lectura.")
        entradas = datos.get("long_term")
        if datos.get("formato") != formato or not isinstance(entradas, dict):
            raise ValueError("El archivo debe ser un respaldo de recuerdos de Cerebro.")
        anterior = self.memoria.long_term_memory
        nuevos = {}
        for clave, entrada in entradas.items():
            if (not clave.strip() or not isinstance(entrada, dict) or "valor" not in entrada
                    or not isinstance(entrada.get("categoria"), str)
                    or not isinstance(entrada.get("fecha"), str)
                    or type(entrada.get("importancia")) not in {int, float}
                    or abs(entrada["importancia"]) > 100):
                raise ValueError("Hay recuerdos con metadatos inválidos.")
            if clave in anterior and anterior[clave] != entrada:
                raise ValueError(f"Conflicto en «{clave}». Se conservó la memoria existente.")
            if clave not in anterior:
                nuevos[clave] = entrada
        combinado = {**anterior, **nuevos}
        if len(json.dumps(combinado, allow_nan=False).encode()) > 6 * MIB:
            raise ValueError("El respaldo combinado supera 6 MiB.")
        if nuevos:
            self.memoria.long_term_memory = combinado
            try:
                self.memoria.persistir()
            except (OSError, ValueError, TypeError, RecursionError):
                self.memoria.long_term_memory = anterior
                raise
            publicar("aprendido", "memoria")
        return {"importados": len(nuevos)}

    def guardar_canvas(self, datos):
        formas = datos.get("formas")
        if not isinstance(formas, list) or len(formas) > 200:
            raise ValueError("El lienzo admite hasta 200 figuras.")
        for forma in formas:
            if (not isinstance(forma, dict) or forma.get("tipo") not in
                    ("trazo", "rectangulo", "linea", "texto")
                    or not isinstance(forma.get("color"), str)
                    or not re.fullmatch(r"#[a-fA-F0-9]{6}", forma["color"])
                    or not isinstance(forma.get("texto"), str) or len(forma["texto"]) > 180):
                raise ValueError("Figura o color inválido.")
            puntos = forma.get("puntos")
            if not isinstance(puntos, list) or not 1 <= len(puntos) <= 250 or any(
                not isinstance(punto, list) or len(punto) != 2
                or any(type(x) is not int or abs(x) > 100000 for x in punto) for punto in puntos
            ):
                raise ValueError("Coordenadas inválidas.")
        return self.guardar("canvas.json", json.dumps({"formas": formas}, allow_nan=False), canvas=True)

    def _archivos(self):
        for base, dirs, files in os.walk(self.estudio):
            dirs[:] = [nombre for nombre in dirs if not nombre.startswith(".")
                       and not (Path(base) / nombre).is_symlink()]
            for nombre in files:
                ruta = Path(base) / nombre
                if not ruta.is_symlink() and ruta.is_file():
                    yield ruta

    def _uso(self):
        return sum(ruta.stat().st_size for ruta in self._archivos())

    def archivos(self):
        self.exigir_permisos("READ")
        return {"archivos": sorted(ruta.relative_to(self.estudio).as_posix() for ruta in self._archivos()
                                   if ruta.suffix in ARCHIVOS and ruta.name != "canvas.json")}

    def ruta(self, nombre, *, lectura=False):
        if not isinstance(nombre, str) or not re.fullmatch(r"[\w ./-]{1,160}", nombre):
            raise ValueError("Ruta de archivo inválida.")
        partes = nombre.split("/")
        if any(not parte or parte.startswith(".") for parte in partes):
            raise ValueError("Usa una ruta relativa sin archivos ocultos.")
        ruta = self.estudio
        for parte in partes:
            ruta = ruta / parte
            if ruta.is_symlink():
                raise PermissionError("Los enlaces simbólicos están fuera del explorador.")
        from universe.consultas import DOCUMENTOS, IMAGENES, VIDEOS
        if ruta.suffix.lower() not in (DOCUMENTOS | IMAGENES | set(VIDEOS) if lectura else ARCHIVOS):
            raise ValueError("Tipo de archivo no admitido.")
        return ruta

    def leer(self, nombre):
        self.exigir_permisos("READ")
        ruta = self.ruta(nombre)
        if not ruta.is_file() or ruta.stat().st_size > MIB:
            raise ValueError("El archivo no existe o supera 1 MiB.")
        return {"texto": ruta.read_text(encoding="utf-8")}

    def guardar(self, nombre, texto, *, canvas=False):
        self.exigir_permisos("WRITE")
        ruta = self.ruta(nombre)
        if ruta == self.estudio / "canvas.json" and not canvas:
            raise PermissionError("Abre el documento desde Canvas.")
        if not isinstance(texto, str):
            raise ValueError("Se espera texto UTF-8.")
        datos = texto.encode("utf-8")
        actual = ruta.stat().st_size if ruta.is_file() else 0
        if len(datos) > MIB or self._uso() - actual + len(datos) > self.cuota:
            raise ValueError("Se excedió la cuota de Studio y Canvas.")
        if shutil.disk_usage(self.estudio).free < len(datos) + MIB:
            raise ValueError("Espacio insuficiente para guardar de forma atómica.")
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=ruta.parent, delete=False) as archivo:
            tempora = Path(archivo.name)
            try:
                archivo.write(datos)
                archivo.close()
                os.replace(tempora, ruta)
            finally:
                tempora.unlink(missing_ok=True)
        publicar("creando", "herramienta")
        return {"guardado": nombre}

    def adjuntar(self, nombre, contenido):
        from base64 import b64decode
        self.exigir_permisos("WRITE")
        if not isinstance(nombre, str) or "/" in nombre or not isinstance(contenido, str):
            raise ValueError("Adjunta un archivo con nombre simple.")
        ruta = self.ruta("adjuntos/" + nombre, lectura=True)
        datos = b64decode(contenido, validate=True)
        if not datos or len(datos) > 16 * MIB or self._uso() + len(datos) > self.cuota:
            raise ValueError("El adjunto está vacío o excede el límite de 16 MiB o la cuota.")
        if shutil.disk_usage(self.estudio).free < len(datos) + MIB:
            raise ValueError("Espacio insuficiente para guardar el adjunto.")
        ruta.parent.mkdir(parents=True, exist_ok=True)
        try:
            archivo = ruta.open("xb")
        except FileExistsError:
            if ruta.is_file() and ruta.stat().st_size == len(datos) and ruta.read_bytes() == datos:
                return {"nombre": ruta.relative_to(self.estudio).as_posix()}
            raise ValueError("Ya hay un adjunto distinto con ese nombre.")
        try:
            with archivo:
                archivo.write(datos)
        except OSError:
            ruta.unlink(missing_ok=True)
            raise
        return {"nombre": ruta.relative_to(self.estudio).as_posix()}

    def consultar_tareas(self):
        self.exigir_permisos("READ")
        return [tarea.copy() for tarea in reversed(self.tareas)]

    def limpiar_cache(self):
        self.exigir_permisos("WRITE")
        anteriores = len(self.tareas)
        vigentes = [tarea for tarea in self.tareas if tarea["estado"] in {"en cola", "en ejecución"}]
        self.tareas.clear()
        self.tareas.extend(vigentes)
        return {"tareas_retiradas": anteriores - len(vigentes)}

    def crear_tarea(self, accion, nombre=None):
        if self.solo_lectura:
            raise PermissionError("La sesión es de solo lectura.")
        if accion not in {"estado", "sintaxis"}:
            raise ValueError("Acción disponible: estado o sintaxis.")
        codigo = self.leer(nombre)["texto"] if accion == "sintaxis" else None
        if codigo is not None and len(codigo) > 128 * 1024:
            raise ValueError("La validación de sintaxis admite archivos de hasta 128 KiB.")
        if sum(tarea["estado"] in {"en cola", "en ejecución"} for tarea in self.tareas) >= 4:
            raise ValueError("Ya hay cuatro tareas en curso.")
        tarea = {"id": os.urandom(6).hex(), "accion": accion, "estado": "en cola", "salida": ""}
        self.tareas.append(tarea)
        self.ejecutor.submit(self._ejecutar, tarea, codigo)
        return {"id": tarea["id"]}

    def _ejecutar(self, tarea, codigo):
        inicio = perf_counter()
        with self.cerrojo:
            tarea["estado"] = "en ejecución"
        try:
            if codigo is not None:
                ast.parse(codigo)
                salida = "Sintaxis Python válida."
            else:
                with self.cerrojo:
                    salida = json.dumps(self.estado(), ensure_ascii=False, indent=2)
            estado = "terminada"
        except (SyntaxError, ValueError, OSError, RecursionError) as exc:
            estado, salida = "error", str(exc)
        with self.cerrojo:
            tarea.update(estado=estado, salida=salida, ms=round((perf_counter() - inicio) * 1000, 2))
        publicar("error" if estado == "error" else "consolidado", "herramienta")

    def body(self, accion=None, valor=None):
        self.exigir_permisos("READ" if accion is None else "WRITE")
        if accion not in (None, "armar", "parar", "girar", "avanzar"):
            raise ValueError("Orden del simulador desconocida.")
        if accion == "parar":
            self.parado = True
        elif accion == "armar":
            self.parado = False
        elif accion:
            if self.parado:
                raise PermissionError("El simulador está detenido. Ármalo para continuar.")
            orden = construir_orden(SIMULADOR, accion, valor)
            nombre, cantidad = orden.split()
            if nombre == "girar":
                self.angulo = (self.angulo + float(cantidad)) % 360
            else:
                for i, eje in enumerate((math.cos, math.sin)):
                    self.posicion[i] += eje(math.radians(self.angulo)) * float(cantidad)
        return {"simulado": True, "parado": self.parado, "posicion": self.posicion.copy(),
                "angulo": self.angulo, "perfil_cazel": SIMULADOR, "telemetria": self.telemetria.copy()}

    def recibir_telemetria(self, datos):
        from datetime import datetime, timezone
        identificador, sensores = datos.get("id"), datos.get("sensores")
        if not isinstance(identificador, str) or not re.fullmatch(r"[\w-]{1,32}", identificador):
            raise ValueError("Identificador de cuerpo inválido.")
        if not isinstance(sensores, dict) or len(sensores) > 16 or any(
            not re.fullmatch(r"[\w-]{1,32}", clave) or type(valor) not in (int, float)
            or abs(valor) > 1e12 or not math.isfinite(valor) for clave, valor in sensores.items()
        ):
            raise ValueError("Se admiten hasta 16 lecturas numéricas finitas.")
        if identificador not in self.telemetria and len(self.telemetria) >= 16:
            raise ValueError("Se alcanzó el límite de 16 cuerpos por sesión.")
        self.telemetria[identificador] = {"sensores": sensores, "recibido": datetime.now(timezone.utc).isoformat()}
        publicar("observando", "herramienta")
        return {"recibido": True}
