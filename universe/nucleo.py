"""Estado y operaciones compartidos por las cuatro interfaces."""
import ast
from collections import deque
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
from core.entorno_portatil import detectar_entorno
from core.legado_identidad import leer_origen
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
    "/buscar-corpus", "/resumir", "/palabras-clave", "/github-explorar", "/github-leer", "/web",
}
EVENTOS = {
    "analizando": "procesamiento", "aprendido": "aprendizaje", "investigando": "investigación",
    "consolidado": "procesamiento", "asociando": "relaciones", "observando": "inactividad",
    "error": "errores", "razonando": "razonamiento", "recuperando": "memoria",
    "creando": "creación", "verificado": "conocimiento",
}


class Nucleo:
    def __init__(self, perfil, cuota=None, modelo=None, internet=False, solo_lectura=False, meta=None, investigar_auto=False, documentos_usuario=False):
        self.perfil = perfil
        self.cuota = PERFILES[perfil] * MIB if cuota is None else cuota
        if self.cuota <= 0:
            raise ValueError("La cuota debe ser positiva.")
        self.raiz = Path(config.raiz_datos())
        self.estudio = self.raiz / "universe-datos"
        if self.estudio.is_symlink():
            raise ValueError("El directorio de Universe no puede ser un enlace simbólico.")
        self.estudio.mkdir(mode=0o700, exist_ok=True)
        self.agente = ControlledAgent()
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
        self.conversaciones = Conversaciones(self.raiz / "data")
        if self.agente.tiene_permisos("READ"):
            self._recuperar_contexto(self.historial()["turnos"])
        self.latencias = deque(maxlen=100)
        self.tareas = deque(maxlen=24)
        self.ejecutor = ThreadPoolExecutor(max_workers=1)
        self.parado = True
        self.posicion = [0.0, 0.0]
        self.angulo = 0.0
        self.telemetria = {}

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

    def operar_proyecto(self, datos):
        from core.proyecto_studio import ProyectoStudio, comprobar_python

        cliente = datos.get("cliente")
        if not isinstance(cliente, str) or not re.fullmatch(r"[a-f0-9]{24}", cliente):
            raise ValueError("Identificador de Studio inválido.")
        self.exigir_permisos("READ")
        accion = datos.get("accion")
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
        if accion == "leer":
            return {"texto": proyecto.leer(nombre)}
        if accion == "analizar":
            return proyecto.analizar()
        if accion == "validar":
            comprobar_python(proyecto.leer(nombre), nombre)
            return {"salida": "Sintaxis Python válida."}
        if accion in {"guardar", "aplicar", "pruebas"}:
            self.exigir_permisos("WRITE")
            if datos.get("confirmar") is not True:
                raise PermissionError("Confirma la operación en el proyecto.")
            if accion == "guardar":
                proyecto.guardar(nombre, datos.get("texto"), datos.get("original"))
                return {"archivo": nombre}
            if accion == "aplicar":
                return proyecto.aplicar(datos.get("id"))
            if sum(t["estado"] in {"en cola", "en ejecución"} for t in self.tareas) >= 4:
                raise ValueError("Ya hay cuatro tareas en curso.")
            tarea = {"id": os.urandom(6).hex(), "accion": "pruebas", "estado": "en cola", "salida": ""}
            self.tareas.append(tarea)
            self.ejecutor.submit(self._probar_proyecto, tarea, proyecto, cliente)
            return {"id": tarea["id"]}
        raise ValueError("Acción de proyecto desconocida.")

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

    def conversar(self, pregunta, modo=None, cliente=None):
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
                                  f"Correcciones pendientes: {informe['correcciones_pendientes']}.\n" + objetivos)}
        if re.fullmatch(r"(?:cerebro[, ]+)?(?:activa|abre) (?:el )?modo t[aá]ctil[.!]?", pregunta, re.I):
            self.exigir_permisos("READ")
            return {"respuesta": "Abre el modo táctil desde el lanzador local.", "abrir": "tactil"}
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
        else:
            from universe.consultas import alternativa_publica, consulta_directa
            respuesta = consulta_directa(self, pregunta, modo=modo)
            if respuesta is not None and re.match(
                    r"(?:busca|encuentra)(?:me)?\s+(?:(?:un|el|mi)\s+)?documento\b", pregunta, re.I):
                return {"respuesta": respuesta, "compartir_temporal": True}
            if respuesta is None:
                respuesta, _ = self.chat.procesar(pregunta)
                respuesta = alternativa_publica(self, pregunta, respuesta)
        self.latencias.append((perf_counter() - inicio) * 1000)
        self._registrar_turno(pregunta, respuesta)
        from universe.consultas import desea_studio
        return {"respuesta": respuesta, **({"abrir": "studio"} if desea_studio(pregunta) else {})}

    def analizar_aprendizaje(self):
        from collections import Counter
        from core.automejora import analizar

        self.exigir_permisos("READ")
        tipos = Counter(nodo["tipo"] for nodo in self.nodos()["nodos"])
        informe = analizar(self.raiz)
        informe["tipos"] = dict(tipos)
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
        categorias = {}
        for clave, entrada in list(self.memoria.long_term_memory.items())[-120:]:
            if isinstance(entrada, dict):
                categoria = entrada.get("categoria", "general")
                valor = entrada.get("valor")
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
                    nodos.append({"id": f"ficha:{i}", "tipo": "inactividad", "titulo": pregunta,
                                  "detalle": respuesta[:600], "origen": fuente, "grupo": "Fuente registrada"})
        for i, ficha in enumerate(cargar(self.raiz / "data" / "repaso_espaciado.json")[:40]):
            nodos.append({"id": f"repaso:{i}", "tipo": "conocimiento", "titulo": ficha["pregunta"],
                          "detalle": ficha["respuesta"], "origen": "Ficha de repaso aprobada"})
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
        from universe.consultas import DOCUMENTOS, VIDEOS
        if ruta.suffix.lower() not in (DOCUMENTOS | set(VIDEOS) if lectura else ARCHIVOS):
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
