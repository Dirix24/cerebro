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

    def limpiar(self):
        self.pendientes.clear()

    def _guardar_pendiente(self, cliente, **datos):
        self.pendientes[cliente] = (monotonic() + 300, datos)
        self.pendientes.move_to_end(cliente)
        if len(self.pendientes) > 64:
            self.pendientes.popitem(last=False)

    def _autorizar(self):
        if (not self.nucleo.documentos_usuario
                or "READ" not in self.nucleo.agente.permisos_concedidos):
            raise PermissionError("Esta acción requiere el lanzador local y permiso de lectura.")

    def _autorizar_escritura(self):
        if "WRITE" not in self.nucleo.agente.permisos_concedidos:
            raise PermissionError("Falta el permiso de escritura para cambiar lo aprendido.")

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
        if "cierre" in datos and confirmacion == "confirmar cierre":
            self._autorizar()
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
