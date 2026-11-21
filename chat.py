# -*- coding: utf-8 -*-
"""
Lógica de la conversación de Cerebro (separada de main.py para poder probarla).

Cómo decide qué hacer con cada mensaje:
  1. Si empieza por "/" es un comando explícito.
  2. Si es una cuenta o una pregunta por la hora, el agente usa la
     herramienta correspondiente (reglas, no el modelo: un modelo tan pequeño
     no sabe calcular).
  3. Si el usuario dice cómo se llama, se guarda en la memoria de largo plazo.
  4. Todo lo demás lo responde el modelo de lenguaje, condicionado por los
     últimos turnos de la conversación.
"""

import re

import config
from agent.intents import detectar_intencion
from core.tokenizer import ID_EOS

AYUDA = """Comandos:
  /ayuda                    esta ayuda
  /razonar A2+3*4            dos pasos verificados con el modelo experimental V3
  /origen                   identidad histórica declarada del creador
  /configurar-creador nombre establece creador una sola vez
  /exportar-legado ruta     exporta identidad pública, sin datos privados
  /examinar-legado ruta     inspecciona respaldo sin importarlo
  /recordar-tarea FECHA_ISO texto  guarda recordatorio con zona horaria
  /recordatorios            muestra tareas guardadas y vencidas
  /github-estado dueño/repo consulta repositorio público, solo lectura
  /github-errores dueño/repo lista incidencias públicas abiertas
  /aprender-ficha pregunta || respuesta   añade una tarjeta aprobada
  /enseñar-habilidad nombre || 0:1; 1:3; 2:5    aprende una regla afín
  /usar-habilidad nombre || número             aplica la regla a otra entrada
  /corregir-habilidad nombre || ejemplos       revisa una habilidad guardada
  /encadenar-habilidades primera, segunda || número   combina reglas aprendidas
  /repasar                  muestra una pregunta pendiente
  /autoevaluar              evalúa el modelo con fichas aprobadas
  /progreso                 registra la precisión y su evolución
  /registrar-error pregunta || respuesta  registra corrección para revisión
  /errores-pendientes       consulta correcciones pendientes
  /motor-para pregunta      explica qué motor usaría Cerebro
  /calificar bien|mal       califica manualmente un repaso (opcional)
  /estado                   información del modelo y de la memoria
  /deducir hecho; regla ? clase  encadena premisas y muestra la conclusión
  /recuerdo tema             recupera recuerdos por clave o tema
  /extraer-recuerdos [tema]  muestra recuerdos como JSON reutilizable
  /insertar-recuerdo datos   guarda clave = valor o recuerdos en JSON
  /internet tema             consulta Wikipedia en español y muestra la fuente
  /memoria                  muestra lo que hay en la memoria de largo plazo
  /recordar clave = valor   guarda un dato
  /olvidar clave            borra un dato
  /calc 12 * (3 + 4)        calculadora segura
  /buscar-corpus texto      busca información en el corpus local indexado
  /conocimiento texto       consulta la memoria con fuentes
  /biblioteca texto         busca en documentos locales\n  /mis-documentos tema      busca en el índice privado de exploración autónoma
  /calcular-local cuenta    calcula expresiones aritmeticas
  /analizar-codigo texto    analiza Python sin ejecutarlo
  /crear-proyecto nombre [cli|biblioteca]   crea proyecto Python en workspace
  /motor-especializado texto recomienda motor sin ejecutar
  /descubrir-i2c 0x3c 0x68 interpreta direcciones I2C aportadas, sin sondear
  /analizar-robot archivo.py analiza interfaces de código sin ejecutarlo
  /usb                      lista puertos serie del equipo, sin abrirlos
  /preparar-robot nombre placa archivo.py   prepara proyecto MicroPython (WRITE)
  /usb                      enumera puertos serie sin abrirlos (pyserial opcional)\n  /crear-robot nombre arduino|esp32  prepara firmware de ejemplo sin instalarlo\n  /motores                  lista motores disponibles y futuros
  /laboratorio archivo.py   inspecciona archivo del workspace sin ejecutarlo
  /crear-pdf nombre texto   crea PDF local (requiere reportlab)
  /criterio petición        evalúa ruta, permisos y riesgos sin actuar
  /materias                 lista materias disponibles
  /estudiar materia         propone temas y práctica local
  /experimentos             muestra metricas registradas
  /resumir texto            resumen extractivo local
  /palabras-clave texto     palabras frecuentes del texto
  /estadisticas texto      cuenta palabras, frases y lineas
  /comparar A || B          compara dos textos
  /fichas concepto: dato   crea fichas de estudio
  /preguntas texto         preguntas de repaso desde frases X es Y
  /duplicados A || B      detecta textos similares
  /historial               consulta las últimas respuestas guardadas
  /guardar-turno rol texto guarda un turno explícitamente
  /aprobar-ejemplo pregunta || respuesta  aprueba un ejemplo local
  /ejemplos-aprobados       muestra ejemplos aprobados
  /hora                     fecha y hora del sistema
  /archivos                 lista los archivos del espacio de trabajo
  /leer nombre.txt          lee un archivo del espacio de trabajo
  /escribir nombre.txt txt  escribe un archivo en el espacio de trabajo
  /temp 0.7                 cambia la temperatura de generación (0 = determinista)
  /limpiar                  olvida la conversación actual (no la memoria de largo plazo)
  /salir                    termina
También entiendo cosas como «cuánto es 12 por 7» o «qué hora es»."""

_NOMBRE = re.compile(
    r"\b(?:me\s+llamo|mi\s+nombre\s+es|soy)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]{2,20})\b", re.IGNORECASE)
_PREGUNTA_NOMBRE = re.compile(r"(c[oó]mo\s+me\s+llamo|cu[aá]l\s+es\s+mi\s+nombre|sabes\s+mi\s+nombre)",
                              re.IGNORECASE)
_NO_SON_NOMBRES = {"un", "una", "el", "la", "tu", "yo", "muy", "bien", "pequeño", "cerebro",
                   "nuevo", "programador", "estudiante", "de"}


class Conversacion:
    modo_local = False
    tema_local = None
    def __init__(self, modelo, memoria, agente, info_checkpoint=None, seed=None, modo_local=False):
        self.modelo = modelo
        self.memoria = memoria
        self.agente = agente
        self.info = info_checkpoint or {}
        self.gen = dict(max_nuevos=config.GEN_MAX_NUEVOS, temperatura=config.GEN_TEMPERATURA,
                        top_k=config.GEN_TOP_K, top_p=config.GEN_TOP_P,
                        penalizacion=config.GEN_PENALIZACION_REPETICION)
        import numpy as np
        self.rng = np.random.default_rng(seed)
        self.pregunta_repaso = None
        self.modo_local = modo_local

    # -- entrada principal ------------------------------------------------------------

    def procesar(self, entrada):
        """Devuelve (texto de respuesta, terminar: bool)."""
        entrada = entrada.strip()
        if not entrada:
            return "", False
        # Telemetría real de recepción; sin registrar el texto del usuario.
        try:
            from core.actividad_neuronal import registrar as _registrar_actividad
            _registrar_actividad("analizando", "mensaje")
        except OSError:
            _registrar_actividad = lambda *_args: None
        tema_anterior, self.tema_local = self.tema_local, None
        if entrada.startswith("/"):
            return self._comando(entrada)

        # Durante un repaso, la respuesta se comprueba contra la ficha aprobada.
        # No se envía al modelo generativo ni al detector de intenciones.
        if self.pregunta_repaso is not None:
            from pathlib import Path
            from core.repaso_espaciado import cargar, calificar
            from core.autoevaluacion import evaluar_respuesta
            ruta = Path(config.raiz_datos()) / "data" / "repaso_espaciado.json"
            ficha = next((t for t in cargar(ruta)
                          if t["pregunta"] == self.pregunta_repaso), None)
            if ficha is None:
                self.pregunta_repaso = None
                return "La ficha del repaso ya no existe.", False
            correcto = evaluar_respuesta(entrada, ficha["respuesta"])
            tarjeta = calificar(ruta, self.pregunta_repaso, correcto)
            self.pregunta_repaso = None
            resultado = "Correcto" if correcto else "Incorrecto"
            return (f"{resultado}. Respuesta esperada: {tarjeta['respuesta']}. "
                    f"Próximo repaso: {tarjeta['fecha']}."), False

        rutas_directas = (
            (r"(?:busca|consulta) en internet(?:[: ]+(.+))?", "/internet"),
            (r"(?:extrae(?:r)?(?: (?:mis|los))? recuerdos?|exporta toda tu memoria)(?:[: ]+(.+))?", "/extraer-recuerdos"),
            (r"(?:inserta(?:r)?(?: un)? recuerdo|guarda esta memoria)(?:[: ]+(.+))?", "/insertar-recuerdo"),
            (r"¿?qu[eé] recuerdas(?: (?:sobre|de) (.+?))?\??", "/recuerdo"),
            (r"deduce[: ]+(.+)", "/deducir"),
        )
        for patron, comando in rutas_directas:
            solicitud = re.fullmatch(patron, entrada, re.IGNORECASE)
            if solicitud:
                return self._comando(f"{comando} {solicitud.group(1) or ''}")

        from agent.dialogo_local import respuesta_breve
        respuesta = respuesta_breve(entrada)
        if respuesta == "capacidades":
            return ("Puedo calcular, deducir a partir de premisas, guardar y recuperar recuerdos, "
                    "aprender habilidades de ejemplos aprobados y consultar Wikipedia. "
                    "Escribe /ayuda para ver cómo."), False
        if respuesta == "creador":
            return ("Para registrar la identidad declarada del creador, usa "
                    "«/configurar-creador Nombre». Es una configuración de una sola vez."), False
        if respuesta == "aclarar_definicion":
            tema = entrada.split(maxsplit=2)[2].strip(" ?")
            return f"¿Querías decir «qué es {tema}»? Para consultar Wikipedia, escribe «busca en internet {tema}».", False

        sencillas = {
            "ok": "De acuerdo. ¿Qué quieres hacer ahora?",
            "vale": "De acuerdo. ¿Qué quieres hacer ahora?",
            "de acuerdo": "De acuerdo. ¿Qué quieres hacer ahora?",
            "gracias": "De nada.",
            "muchas gracias": "De nada.",
            "hola": "Hola. Puedo ayudarte con cálculos, fuentes locales y habilidades que me enseñes.",
            "buenas": "Hola. ¿En qué te ayudo?",
        }
        saludo = entrada.casefold().rstrip(" .!¡")
        if saludo in sencillas:
            if saludo not in ("hola", "buenas"):
                self.tema_local = tema_anterior
            return sencillas[saludo], False

        # Las peticiones de aprendizaje tienen sintaxis explícita y no ejecutan texto libre.
        nombre = r"[\w-]+"
        numero = r"[+-]?\d{1,9}(?:[.,]\d{1,6})?"
        solicitud = re.fullmatch(
            rf"(?:usa|aplica) (?:la habilidad )?({nombre})(?: y (?:luego|después) ({nombre}))? "
            rf"(?:a|con) ({numero})[.!]?", entrada, re.IGNORECASE,
        )
        if solicitud:
            primera, segunda, valor = solicitud.groups()
            comando = (f"/encadenar-habilidades {primera}, {segunda}" if segunda
                       else f"/usar-habilidad {primera}")
            return self._comando(f"{comando} || {valor}")
        leccion = re.fullmatch(
            rf"(enséñate|aprende|corrige) (?:la habilidad )?({nombre}) con estos ejemplos: (.+)",
            entrada, re.IGNORECASE,
        )
        if leccion:
            accion, habilidad, ejemplos = leccion.groups()
            comando = "/corregir-habilidad" if accion.casefold() == "corrige" else "/enseñar-habilidad"
            return self._comando(f"{comando} {habilidad} || {ejemplos}")

        dato_ensenado = re.fullmatch(r"aprende esta respuesta: *(.+?) *\|\| *(.+)", entrada, re.IGNORECASE)
        if dato_ensenado:
            if "WRITE" not in config.PERMISOS_AGENTE:
                return "Necesito permiso WRITE para guardar la respuesta.", False
            import sqlite3
            from core.conocimiento import guardar, respuesta_exacta
            pregunta, respuesta = dato_ensenado.groups()
            try:
                guardar(pregunta.strip(), respuesta.strip(), "Declarado por el usuario")
                if not respuesta_exacta(pregunta):
                    return "Guardé la respuesta, pero hay versiones distintas. Me abstendré de elegir una.", False
                return "Guardé la respuesta con tu atribución. Puedes preguntármela en otra sesión.", False
            except (ValueError, OSError, sqlite3.Error) as exc:
                return f"No pude guardar la respuesta: {exc}", False

        # La visualización se puede solicitar hablando, sin memorizar comandos.
        if re.search(r"\b(estacion neuronal|mapa neuronal|visualiza (?:tus )?neuronas)\b",
                       entrada.lower()):
            return self._comando("/estacion-neuronal")

        # Guardado solicitado expresamente; no se considera verdad verificada.
        recuerdo = re.match(r"^(?:cerebro[, ]+)?recuerda que\s+(.{3,400})$",
                              entrada, flags=re.IGNORECASE)
        if recuerdo:
            if "WRITE" not in config.PERMISOS_AGENTE:
                return "Necesito permiso WRITE para guardar el recuerdo.", False
            from hashlib import sha256
            texto = recuerdo.group(1).strip()
            clave = "declaracion_" + sha256(texto.encode("utf-8")).hexdigest()[:16]
            self.memoria.guardar_largo_plazo(clave, texto, categoria="declarado_por_usuario",
                                             importancia=2)
            _registrar_actividad("aprendido", "memoria")
            return ("He guardado ese recuerdo como información declarada por ti, "
                    "no como un hecho verificado."), False

        # La identidad pública del creador se consulta sin acceder a memorias privadas.
        if re.search(r"\b(quien\s*te\s*creo|quien fue tu creador|quien es tu creador)\b",
                      entrada.lower().replace("é", "e")):
            from core.legado_identidad import leer_origen
            origen = leer_origen()
            if origen["creador"]:
                return ("Mi creador registrado es " + origen["creador"] +
                        ". Es una identidad declarada, no verificada criptográficamente."), False
            return "Todavía no tengo registrada la identidad de mi creador.", False

        # Peticiones cotidianas: consultar herramientas sin memorizar comandos.
        from agent.lenguaje_natural import interpretar
        solicitud = interpretar(entrada)
        if solicitud:
            accion = solicitud["accion"]
            if solicitud["requiere_confirmacion"]:
                respuestas = {
                    "camara": "Puedo capturar una imagen, pero necesito tu autorización explícita. "
                              "La captura puntual está disponible en camara_local.py --confirmar; "
                              "todavía no identifico objetos con un modelo entrenado.",
                    "github_escritura": "Puedo consultar GitHub, pero todavía no modifico repositorios "
                                       "automáticamente. No haré cambios sin revisar una propuesta contigo.",
                    "recordatorio_nuevo": "Claro. Dime la fecha y la hora con zona horaria "
                                          "(por ejemplo, 2027-01-20T10:00:00+01:00) "
                                          "y el texto que quieres recordar.",
                }
                return respuestas[accion], False
            if accion == "usb":
                return self._comando("/usb")
            if accion == "recordatorios":
                return self._comando("/recordatorios")
            if accion.startswith("github_"):
                m = re.search(r"(?<![\w.-])([\w.-]+/[\w.-]+)(?![\w.-])", entrada)
                if not m:
                    return ("¿Qué repositorio de GitHub quieres consultar? "
                            "Dime propietario/nombre, por ejemplo Dirix24/cerebro."), False
                return self._comando(("/github-errores " if accion == "github_errores"
                                      else "/github-estado ") + m.group(1))

        plan = detectar_intencion(entrada)
        if plan:
            return self._responder_con_agente(plan), False

        if _PREGUNTA_NOMBRE.search(entrada):
            nombre = self.memoria.recuperar_largo_plazo("nombre")
            return (f"Te llamas {nombre}." if nombre
                    else "Todavía no sé tu nombre. Dímelo con «me llamo ...»."), False
        m = _NOMBRE.search(entrada)
        if m and m.group(1).lower() not in _NO_SON_NOMBRES:
            nombre = m.group(1).capitalize()
            self.memoria.guardar_largo_plazo("nombre", nombre, categoria="usuario", importancia=3)
            _registrar_actividad("aprendido", "memoria")
            return f"Mucho gusto, {nombre}. Lo guardé en mi memoria. ¿En qué te puedo ayudar?", False

        # Consultar documentos privados solo si el usuario lo pide explícitamente.
        peticion_docs = re.match(
            r"^\s*(?:busca\s+en\s+mis\s+documentos|consulta\s+mis\s+documentos|en\s+mis\s+documentos)\s+(.+)$",
            entrada, re.IGNORECASE,
        )
        if peticion_docs:
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            from core.consulta_exploracion import respuesta_documental
            return respuesta_documental(peticion_docs.group(1)), False

        if self.modo_local:
            import sqlite3
            from core.conocimiento import respuesta_exacta
            try:
                dato = respuesta_exacta(entrada)
            except (OSError, ValueError, sqlite3.Error):
                dato = None
            if dato:
                return dato["respuesta"] + "\nFuente: " + dato["fuente"], False
        if self.modo_local:
            from core.temas_locales import responder_tema
            respuesta, self.tema_local = responder_tema(entrada, tema_anterior)
            if respuesta is not None:
                return respuesta, False

        # Definiciones: comprobar evidencia precisa antes de usar similitud o generar.
        from core.respuestas_con_fuentes import (
            concepto_definicion, responder_definicion, respuesta_clara,
            consultar_internet_si_falta,
        )
        if concepto_definicion(entrada):
            _registrar_actividad("investigando", "consulta")
            dato = responder_definicion(entrada)
            if not dato and not self.modo_local:
                # Solo se consulta el tema público de una definición, nunca
                # recuerdos, archivos locales ni el historial del usuario.
                dato = consultar_internet_si_falta(entrada)
            respuesta = (respuesta_clara(dato[0]) + "\nFuente: " + dato[1] if dato else
                         "No encontré una definición fiable. Puedes aportar una fuente local "
                         "o guardar una tarjeta con /aprender-ficha.")
            self.memoria.agregar_contexto("usuario", entrada)
            self.memoria.agregar_contexto("ia", respuesta)
            _registrar_actividad("consolidado", "respuesta")
            return respuesta, False

        # Orquestador: usar fuentes locales verificables antes de generar texto.
        from agent.orquestador import seleccionar, extraer_consulta_local
        ruta = seleccionar(entrada)
        if ruta == "busqueda_local":
            _registrar_actividad("investigando", "consulta")
            from core.local_search import buscar
            consulta = extraer_consulta_local(entrada)
            resultados = buscar(consulta) if consulta else []
            if resultados:
                return "\n\n".join(f"[{origen}] {texto}" for texto, origen in resultados), False
            return "No encontré información en el corpus local.", False
        if ruta == "conocimiento" and not self.modo_local:
            _registrar_actividad("investigando", "consulta")
            from core.conocimiento import buscar as buscar_conocimiento
            resultados = buscar_conocimiento(entrada, limite=1)
            if resultados:
                dato = resultados[0]
                return dato["respuesta"][:1000] + "\nFuente: " + dato["fuente"], False
        # No inventar conocimiento: respuesta automática solo ante pregunta exacta.
        try:
            from core.conocimiento import respuesta_exacta
            dato = respuesta_exacta(entrada)
            if dato:
                return dato["respuesta"] + "\nFuente: " + dato["fuente"], False
        except (OSError, ValueError):
            pass
        # Preguntas de definición: evitar inventar una respuesta factual.
        # Solo devolver textos de fuentes locales si hay resultados pertinentes.
        pregunta = re.match(r"^\s*¿?\s*(?:qué|que)\s+es\s+(?:(?:un|una|el|la)\s+)?(.+?)\s*\??$", entrada, re.IGNORECASE)
        if pregunta:
            concepto = pregunta.group(1).rstrip(" ?")
            from core.local_search import buscar
            resultados = buscar(concepto)
            if resultados:
                texto, origen = resultados[0]
                respuesta = f"Encontré en el corpus local:\n[{origen}] {texto}"
            else:
                respuesta = "No encontré una definición en mis fuentes locales. Puedes añadir una ficha con /aprender-ficha."
            self.memoria.agregar_contexto("usuario", entrada)
            self.memoria.agregar_contexto("ia", respuesta)
            _registrar_actividad("consolidado", "respuesta")
            return respuesta, False
        if self.modo_local or self.modelo is None:
            return ("No tengo una respuesta fiable con mis datos locales. Puedo calcular, "
                    "buscar en el corpus o aplicar una habilidad que me enseñes. "
                    "Escribe /ayuda para ver ejemplos."), False
        resultado = self.responder_modelo(entrada)
        _registrar_actividad("consolidado", "respuesta")
        return resultado, False

    # -- respuesta del modelo -----------------------------------------------------------

    def _armar_prompt_ids(self, mensaje, max_nuevos):
        tok, B = self.modelo.tokenizer, self.modelo.cfg.block_size
        turnos = list(self.memoria.short_term_context)
        recuerdos = self.memoria.buscar(mensaje, limite=4)
        bloque_memoria = ""
        if recuerdos:
            bloque_memoria = "memoria: " + "; ".join(
                f"{k}={v}" for k, v in recuerdos.items()) + "\n"
        while True:
            partes = [f"{'usuario' if t['rol'] == 'usuario' else 'cerebro'}: {t['contenido']}\n"
                      for t in turnos]
            texto = bloque_memoria + "".join(partes) + f"usuario: {mensaje}\ncerebro:"
            ids = [ID_EOS] + tok.codificar(texto)
            if len(ids) <= B - max_nuevos or not turnos:
                break
            turnos = turnos[2:] if len(turnos) >= 2 else []   # descarta el turno más viejo
        # Preserva al menos el prefijo de generación y evita slicing [-0:]
        # (que devolvería el prompt entero y desbordaría el contexto).
        espacio = max(1, B - max_nuevos)
        return ids[-espacio:]

    def responder_modelo(self, mensaje):
        g = self.gen
        # Nunca solicitar más tokens que los que caben en la ventana.
        max_nuevos = max(1, min(g["max_nuevos"], self.modelo.cfg.block_size - 1))
        ids = self._armar_prompt_ids(mensaje, max_nuevos)
        nuevos, _ = self.modelo.generar_ids(
            ids, max_nuevos=max_nuevos, temperatura=g["temperatura"], top_k=g["top_k"],
            top_p=g["top_p"], penalizacion=g["penalizacion"], parar_en=("\n",), rng=self.rng)
        texto = self.modelo.tokenizer.decodificar(nuevos).split("\n")[0].strip()
        # Filtrar salidas obviamente defectuosas del modelo pequeño.
        # No sustituye una evaluación lingüística completa.
        palabras = re.findall(r"\\w+", texto, flags=re.UNICODE)
        ruido = (not texto or len(texto) > 450 or
                 any(len(palabra) > 30 for palabra in palabras) or
                 texto.count("¿") > texto.count("?") + 1 or
                 texto.count("(") != texto.count(")"))
        if ruido:
            texto = ("No tengo una respuesta fiable para eso. "
                     "Prueba a reformularlo o consulta mis fuentes locales.")
        self.memoria.agregar_contexto("usuario", mensaje)
        self.memoria.agregar_contexto("ia", texto)
        return texto

    # -- agente -------------------------------------------------------------------------

    def _responder_con_agente(self, plan):
        historial = self.agente.ejecutar_plan_autonomo(plan)
        paso = historial[-1]
        if "error" in paso:
            return f"No pude hacerlo: {paso['error']}"
        res = paso["resultado"]
        if "error" in res:
            return f"No pude hacerlo: {res['error']}"
        if paso["herramienta"] == "calculator":
            valor = res["result"]
            if isinstance(valor, float):
                valor = round(valor, 10)
            return f"{plan[0]['arguments']['expression']} = {valor}"
        if paso["herramienta"] == "clock":
            return f"Ahora mismo son: {res['time']}"
        return str(res)

    # -- comandos -----------------------------------------------------------------------

    def _comando(self, entrada):
        partes = entrada.split(None, 1)
        cmd = partes[0].lower()
        resto = partes[1].strip() if len(partes) > 1 else ""
        a = self.agente

        if cmd in ("/enseñar-habilidad", "/usar-habilidad", "/corregir-habilidad", "/encadenar-habilidades"):
            from pathlib import Path
            import sqlite3
            from core.habilidades import apply, chain, teach
            ruta = Path(config.raiz_datos()) / "data" / "habilidades.sqlite3"
            nombre, separador, datos = resto.partition("||")
            if not separador:
                return f"Uso: {cmd} nombre || datos", False
            try:
                if cmd == "/usar-habilidad":
                    resultado, revision, fuera = apply(ruta, nombre, datos)
                    aviso = " Fuera del rango de ejemplos: es una extrapolación." if fuera else ""
                    return f"Regla aprendida (revisión {revision}): {resultado}.{aviso}", False
                if cmd == "/encadenar-habilidades":
                    pasos = chain(ruta, nombre.split(","), datos)
                    return "\n".join(
                        f"{regla} (revisión {revision}) → {valor}" + (" [extrapolación]" if fuera else "")
                        for regla, valor, revision, fuera in pasos
                    ), False
                resultado = teach(ruta, nombre, datos, revise=cmd == "/corregir-habilidad")
                from core.actividad_neuronal import publicar
                publicar("aprendido", "herramienta")
                return resultado, False
            except (OSError, ValueError, sqlite3.Error) as exc:
                return f"No pude completar la habilidad: {exc}", False

        if cmd == "/deducir":
            from core.razonamiento_local import explicar_deduccion
            try:
                resultado = explicar_deduccion(resto)
                from core.actividad_neuronal import publicar
                publicar("razonando", "herramienta")
                if "Conclusión:" in resultado:
                    publicar("asociando", "relacion")
                return resultado, False
            except ValueError as exc:
                return str(exc), False

        if cmd == "/internet":
            from aprendizaje_internet import buscar_tema, explicar_error_red
            if not resto:
                return "Uso: /internet tema público", False
            from core.actividad_neuronal import publicar
            publicar("investigando", "consulta")
            try:
                dato = buscar_tema(resto)
            except ValueError as exc:
                return str(exc), False
            except OSError as exc:
                publicar("error", "fallo")
                return "No pude consultar Wikipedia. " + explicar_error_red(exc), False
            if not dato:
                return "Wikipedia no devolvió un artículo con extracto para esa consulta.", False
            titulo, texto, url = dato
            if len(texto) > 1200:
                texto = texto[:1200].rsplit(" ", 1)[0] + "…"
            return f"{titulo}\n\n{texto}\n\nFuente: {url}", False

        if cmd == "/razonar":
            from pathlib import Path
            from reasoning_v3 import solve
            checkpoint = Path(__file__).resolve().parent / "checkpoints" / "reasoning-v3.pt"
            try:
                return solve(resto, checkpoint), False
            except ImportError:
                return "Cerebro V3 requiere PyTorch local (torch>=2.6).", False
            except (ValueError, OSError, RuntimeError) as exc:
                return f"Cerebro V3: {exc}", False

        if cmd == "/mis-documentos":
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            if not resto:
                return "Uso: /mis-documentos tema", False
            from core.consulta_exploracion import respuesta_documental
            return respuesta_documental(resto), False

        if cmd == "/estacion-neuronal":
            from pathlib import Path
            from core.estacion_neuronal import guardar_estacion
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            try:
                ruta = Path(config.CEREBRO_HOME) / "data" / "estacion_neuronal.html"
                if ruta.exists():
                    return "Ya existe la estación. Muévela o elimínala para generar otra.", False
                guardar_estacion(self.memoria.long_term_memory, ruta)
                return f"Estación neuronal creada: {ruta}. Ábrela en tu navegador para explorar.", False
            except (OSError, ValueError) as exc:
                return f"Estación neuronal: {exc}", False
        if cmd == "/mapa-recuerdos":
            from pathlib import Path
            from core.mapa_memoria import guardar_mapa
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            try:
                ruta = Path(config.CEREBRO_HOME) / "data" / "mapa_recuerdos.svg"
                if ruta.exists():
                    return "El mapa ya existe; mueve o elimina el anterior para generar otro.", False
                guardar_mapa(self.memoria.long_term_memory, ruta)
                return f"Mapa local creado: {ruta}. Ábrelo en un navegador.", False
            except (OSError, ValueError) as exc:
                return f"Mapa de recuerdos: {exc}", False
        if cmd == "/recordar-tarea":
            import json
            from core.recordatorios_locales import crear
            if "WRITE" not in config.PERMISOS_AGENTE:
                return "Permiso WRITE requerido.", False
            fecha, separador, texto = resto.partition(" ")
            if not separador:
                return "Uso: /recordar-tarea 2027-01-20T10:00:00+01:00 revisar proyecto", False
            try:
                return json.dumps(crear(fecha, texto), ensure_ascii=False), False
            except (OSError, ValueError) as exc:
                return f"Recordatorio: {exc}", False
        if cmd == "/recordatorios":
            import json
            from core.recordatorios_locales import listar, pendientes
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            try:
                return json.dumps({"todos": listar(), "vencidos": pendientes()},
                                  ensure_ascii=False, indent=2), False
            except (OSError, ValueError) as exc:
                return f"Recordatorios: {exc}", False
        if cmd in ("/github-errores", "/github-estado") and getattr(self, "modo_local", False):
            return "GitHub no está disponible en el modo local.", False
        if cmd == "/github-errores":
            import json
            from core.github_local import incidencias_publicas
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            try:
                return json.dumps(incidencias_publicas(resto), ensure_ascii=False, indent=2), False
            except (OSError, ValueError, KeyError) as exc:
                return f"GitHub: {exc}", False
        if cmd == "/github-estado":
            import json
            from core.github_local import estado_publico
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            try:
                return json.dumps(estado_publico(resto), ensure_ascii=False, indent=2), False
            except (OSError, ValueError, KeyError) as exc:
                return f"GitHub: {exc}", False
        if cmd in {"/origen", "/configurar-creador", "/exportar-legado", "/examinar-legado"}:
            import json
            from core.legado_identidad import (leer_origen, configurar_creador,
                                                exportar_legado_publico, examinar_legado)
            try:
                if cmd == "/origen":
                    resultado = leer_origen()
                elif cmd == "/configurar-creador":
                    if "WRITE" not in config.PERMISOS_AGENTE:
                        return "Permiso WRITE requerido.", False
                    resultado = configurar_creador(resto)
                elif cmd == "/exportar-legado":
                    if "WRITE" not in config.PERMISOS_AGENTE:
                        return "Permiso WRITE requerido.", False
                    resultado = exportar_legado_publico(resto)
                else:
                    if "READ" not in config.PERMISOS_AGENTE:
                        return "Permiso READ requerido.", False
                    resultado = examinar_legado(resto)
                return json.dumps(resultado, ensure_ascii=False, indent=2), False
            except (OSError, ValueError, KeyError, TypeError) as exc:
                return f"Legado: {exc}", False
        if cmd == "/motor-especializado":
            from agent.enrutador_especializado import proponer_motor
            import json
            try:
                return json.dumps(proponer_motor(resto), ensure_ascii=False, indent=2), False
            except ValueError:
                return "Uso: /motor-especializado tarea que quieres realizar", False
        if cmd == "/descubrir-i2c":
            import json
            from core.descubrimiento_robot import interpretar_inventario_i2c
            if not resto:
                return "Uso: /descubrir-i2c 0x3c 0x68", False
            try:
                tokens = resto.split()
                direcciones = [int(x, 16) for x in tokens]
                return json.dumps(interpretar_inventario_i2c(direcciones),
                                  ensure_ascii=False, indent=2), False
            except ValueError as exc:
                return f"I2C: {exc}", False
        if cmd == "/analizar-robot":
            import json
            from pathlib import Path
            from core.descubrimiento_robot import analizar_codigo_robot
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            if not resto:
                return "Uso: /analizar-robot archivo.py", False
            try:
                base = Path(config.WORKSPACE_DIR).resolve(strict=True)
                archivo = (base / resto).resolve(strict=True)
                if not archivo.is_relative_to(base) or not archivo.is_file() or archivo.stat().st_size > 100000:
                    raise ValueError("Archivo inválido o fuera del workspace.")
                return json.dumps(analizar_codigo_robot(archivo.read_text(encoding="utf-8")),
                                  ensure_ascii=False, indent=2), False
            except (OSError, ValueError, UnicodeError) as exc:
                return f"Robot: {exc}", False
        if cmd == "/usb":
            import json
            from core.dispositivos_usb import listar_puertos
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            try:
                return json.dumps(listar_puertos(), ensure_ascii=False, indent=2), False
            except (RuntimeError, OSError) as exc:
                return f"USB: {exc}", False
        if cmd == "/preparar-robot":
            import json
            from pathlib import Path
            from core.proyectos_robot import preparar_robot
            from core.entorno_portatil import verificar_almacenamiento
            partes = resto.split()
            if len(partes) != 3:
                return "Uso: /preparar-robot nombre esp32|rp2040 archivo.py", False
            if "READ" not in config.PERMISOS_AGENTE or "WRITE" not in config.PERMISOS_AGENTE:
                return "Se requieren permisos READ y WRITE.", False
            try:
                verificar_almacenamiento()
                base = Path(config.WORKSPACE_DIR).resolve(strict=True)
                archivo = (base / partes[2]).resolve(strict=True)
                if not archivo.is_relative_to(base) or not archivo.is_file() or archivo.stat().st_size > 100000:
                    raise ValueError("El código debe ser un archivo regular del workspace de hasta 100 KB.")
                codigo = archivo.read_text(encoding="utf-8")
                resultado = preparar_robot(partes[0], partes[1], codigo)
                return json.dumps(resultado, ensure_ascii=False, indent=2), False
            except (OSError, ValueError, UnicodeError, RuntimeError) as exc:
                return f"Robot: {exc}", False
        if cmd == "/usb":
            import json
            from core.dispositivos_conectados import listar_puertos
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido para consultar dispositivos.", False
            try:
                return json.dumps(listar_puertos(), ensure_ascii=False, indent=2), False
            except (ImportError, OSError) as exc:
                return f"No pude enumerar puertos: {exc}", False
        if cmd == "/crear-robot":
            import json
            from core.robotica_local import preparar_robot
            from core.entorno_portatil import verificar_almacenamiento
            if "WRITE" not in config.PERMISOS_AGENTE:
                return "Permiso WRITE requerido.", False
            partes = resto.split()
            if len(partes) != 2:
                return "Uso: /crear-robot nombre arduino|esp32", False
            try:
                verificar_almacenamiento()
                return json.dumps(preparar_robot(partes[0], partes[1]),
                                  ensure_ascii=False, indent=2), False
            except (OSError, ValueError, RuntimeError) as exc:
                return f"No pude preparar el robot: {exc}", False
        if cmd == "/motores":
            from agent.motores import capacidades
            import json
            return json.dumps(capacidades(), ensure_ascii=False, indent=2), False
        if cmd == "/laboratorio":
            from core.laboratorio_seguridad import inspeccionar_archivo
            from core.entorno_portatil import verificar_almacenamiento
            import json
            if not resto:
                return "Uso: /laboratorio archivo.py", False
            if "READ" not in config.PERMISOS_AGENTE:
                return "Permiso READ requerido.", False
            try:
                verificar_almacenamiento()
                return json.dumps(inspeccionar_archivo(resto, config.WORKSPACE_DIR),
                                  ensure_ascii=False, indent=2), False
            except (OSError, ValueError, RuntimeError) as exc:
                return f"Laboratorio: {exc}", False
        if cmd == "/crear-pdf":
            from core.documentos_pdf import crear_pdf
            from core.entorno_portatil import verificar_almacenamiento
            partes_pdf = resto.split(None, 1)
            if len(partes_pdf) != 2:
                return "Uso: /crear-pdf nombre texto del documento", False
            if "WRITE" not in config.PERMISOS_AGENTE:
                return "Permiso WRITE requerido.", False
            try:
                verificar_almacenamiento()
                ruta_pdf = crear_pdf(partes_pdf[0], partes_pdf[1])
                return f"PDF creado: {ruta_pdf}", False
            except (OSError, ValueError, RuntimeError) as exc:
                return f"No pude crear PDF: {exc}", False
        if cmd == "/criterio":
            from agent.criterio import evaluar_peticion
            if not resto.strip():
                return "Uso: /criterio /crear-proyecto mi_app cli", False
            import json
            evaluacion = evaluar_peticion(resto, config.PERMISOS_AGENTE)
            return json.dumps(evaluacion, ensure_ascii=False, indent=2), False
        if cmd == "/materias":
            from core.materias import listar_materias
            return ("Materias disponibles:\\n" +
                    "\\n".join(f"- {clave}: {titulo}" for clave, titulo in listar_materias())), False
        if cmd == "/estudiar":
            from core.materias import plan_materia
            try:
                return plan_materia(resto.strip().lower()), False
            except ValueError:
                return "Materia desconocida. Escribe /materias para ver las disponibles.", False
        if cmd == "/crear-proyecto":
            from core.proyectos_locales import crear_proyecto
            from core.entorno_portatil import verificar_almacenamiento
            partes_proyecto = resto.split()
            if not 1 <= len(partes_proyecto) <= 2:
                return "Uso: /crear-proyecto nombre [cli|biblioteca]", False
            if "WRITE" not in config.PERMISOS_AGENTE:
                return "No puedo crear proyectos: falta permiso WRITE.", False
            try:
                verificar_almacenamiento()
                creado = crear_proyecto(partes_proyecto[0],
                                       partes_proyecto[1] if len(partes_proyecto) == 2 else "cli")
                return ("Proyecto creado: " + creado["ruta"] +
                        "\\nArchivos: " + ", ".join(creado["archivos"]) +
                        "\\nNo se ha ejecutado código."), False
            except (ValueError, OSError, RuntimeError) as exc:
                return f"No pude crear el proyecto: {exc}", False
        if cmd == "/motor-para":
            from agent.orquestador import explicar_seleccion
            if not resto:
                return "Uso: /motor-para tu pregunta", False
            decision = explicar_seleccion(resto)
            return f"Motor: {decision['motor']}. Motivo: {decision['razon']}.", False
        if cmd in ("/registrar-error", "/errores-pendientes"):
            from pathlib import Path
            from core.errores_aprendizaje import registrar, pendientes
            ruta = Path(config.raiz_datos()) / "data" / "errores_aprendizaje.jsonl"
            if cmd == "/errores-pendientes":
                errores = pendientes(ruta)
                return ("\n".join(f"{e['pregunta']} => {e['correccion']}" for e in errores)
                        if errores else "No hay errores pendientes."), False
            if " || " not in resto:
                return "Uso: /registrar-error pregunta || respuesta correcta", False
            pregunta, respuesta = resto.split(" || ", 1)
            try:
                registrar(ruta, pregunta, respuesta)
                return "Corrección registrada para revisión. No se entrena automáticamente.", False
            except (ValueError, OSError) as exc:
                return f"No pude registrar el error: {exc}", False
        if cmd == "/progreso":
            from pathlib import Path
            from core.medicion_progreso import medir
            raiz = Path(config.raiz_datos()) / "data"
            estado_rng = self.rng.bit_generator.state
            turnos = list(self.memoria.short_term_context)
            try:
                resumen = medir(raiz / "repaso_espaciado.json", self.responder_modelo,
                                raiz / "historial_evaluaciones.jsonl")
            finally:
                self.rng.bit_generator.state = estado_rng
                self.memoria.short_term_context = turnos
            if resumen["precision"] is None:
                return "No hay fichas aprobadas para medir progreso.", False
            variacion = resumen["variacion"]
            cambio = "sin medición comparable anterior" if variacion is None else f"variación {variacion:+.1%}"
            return (f"Evaluación: {resumen['aciertos']}/{resumen['evaluadas']} "
                    f"({resumen['precision']:.1%}); {cambio}. "
                    "La coincidencia exacta no mide inteligencia general."), False
        if cmd == "/autoevaluar":
            from pathlib import Path
            from core.autoevaluacion import ejecutar
            ruta = Path(config.raiz_datos()) / "data" / "repaso_espaciado.json"
            estado_rng = self.rng.bit_generator.state
            turnos = list(self.memoria.short_term_context)
            try:
                resultados = ejecutar(ruta, self.responder_modelo, limite=5)
            finally:
                self.rng.bit_generator.state = estado_rng
                self.memoria.short_term_context = turnos
            if not resultados:
                return "No hay fichas aprobadas. Usa /aprender-ficha pregunta || respuesta.", False
            aciertos = sum(r["correcto"] for r in resultados)
            return (f"Autoevaluación estricta: {aciertos}/{len(resultados)} coincidencias exactas. "
                    "No se usa para entrenar ni modifica fichas.\n" +
                    "\n".join(("OK" if r["correcto"] else "FALLO") + ": " + r["pregunta"]
                              for r in resultados)), False
        if cmd in ("/aprender-ficha", "/repasar", "/calificar"):
            from pathlib import Path
            from core.repaso_espaciado import anadir, pendientes, calificar
            ruta = Path(config.raiz_datos()) / "data" / "repaso_espaciado.json"
            try:
                if cmd == "/aprender-ficha":
                    if " || " not in resto:
                        return "Uso: /aprender-ficha pregunta || respuesta", False
                    pregunta, respuesta = resto.split(" || ", 1)
                    anadir(ruta, pregunta, respuesta)
                    from core.actividad_neuronal import publicar
                    publicar("verificado", "herramienta")
                    return "Tarjeta guardada para repasos posteriores.", False
                if cmd == "/repasar":
                    tarjetas = pendientes(ruta, limite=1)
                    if not tarjetas:
                        self.pregunta_repaso = None
                        return "No hay preguntas pendientes hoy.", False
                    self.pregunta_repaso = tarjetas[0]["pregunta"]
                    return ("Pregunta: " + self.pregunta_repaso +
                            "\nEscribe tu respuesta para comprobarla automáticamente, "
                            "o /calificar bien|mal para calificar manualmente."), False
                if resto not in ("bien", "mal") or not self.pregunta_repaso:
                    return "Primero usa /repasar y después /calificar bien|mal.", False
                tarjeta = calificar(ruta, self.pregunta_repaso, resto == "bien")
                self.pregunta_repaso = None
                return f"Registrado. Próximo repaso: {tarjeta['fecha']}. Respuesta esperada: {tarjeta['respuesta']}", False
            except (ValueError, OSError) as exc:
                return f"No pude actualizar el repaso: {exc}", False
        if cmd in ("/salir", "/exit", "/quit"):
            return "¡Hasta pronto!", True
        if cmd in ("/ayuda", "/help"):
            return AYUDA, False
        if cmd in ("/estado", "/status"):
            return self.estado(), False
        if cmd in ("/recuerdo", "/extraer-recuerdos"):
            import json
            if "READ" not in a.permisos_concedidos:
                return "Permiso READ requerido.", False
            if resto in self.memoria.long_term_memory:
                recuerdos = {resto: self.memoria.recuperar_largo_plazo(resto)}
            elif resto:
                recuerdos = self.memoria.buscar(resto)
            else:
                recuerdos = {clave: entrada["valor"]
                             for clave, entrada in self.memoria.long_term_memory.items()
                             if isinstance(entrada, dict) and "valor" in entrada}
            if recuerdos:
                from core.actividad_neuronal import publicar
                publicar("recuperando", "memoria")
            if cmd == "/extraer-recuerdos":
                return json.dumps(recuerdos, ensure_ascii=False), False
            if not recuerdos:
                return "No tengo recuerdos sobre ese tema.", False
            return "\n".join(f"{clave} = {valor}" for clave, valor in recuerdos.items()), False
        if cmd == "/insertar-recuerdo":
            import json
            if "WRITE" not in a.permisos_concedidos:
                return "Permiso WRITE requerido.", False
            if not resto:
                return 'Uso: /insertar-recuerdo {"clave": "valor"}', False
            try:
                if resto.startswith("{"):
                    recuerdos = json.loads(resto)
                else:
                    clave, separador, valor = resto.partition("=")
                    if not separador or not valor.strip():
                        raise ValueError("Usa clave = valor o pega el JSON extraído.")
                    recuerdos = {clave: valor.strip()}
                cantidad = self.memoria.importar_recuerdos(recuerdos)
            except (OSError, ValueError, RecursionError) as exc:
                return f"No pude insertar los recuerdos: {exc}", False
            if cantidad:
                from core.actividad_neuronal import publicar
                publicar("aprendido", "memoria")
            return (f"Recuerdos nuevos guardados: {cantidad}." if cantidad
                    else "Esos recuerdos ya estaban guardados."), False
        if cmd in ("/memoria", "/memory"):
            if not self.memoria.long_term_memory:
                return "La memoria de largo plazo está vacía. Usa /recordar clave = valor.", False
            return "\n".join(f"  {k} = {v['valor']}   ({v['fecha']})"
                             for k, v in self.memoria.long_term_memory.items()), False
        if cmd == "/recordar":
            if "=" not in resto:
                return "Uso: /recordar clave = valor", False
            clave, valor = (s.strip() for s in resto.split("=", 1))
            if not clave or not valor:
                return "Uso: /recordar clave = valor", False
            self.memoria.guardar_largo_plazo(clave, valor)
            return f"Guardado: {clave} = {valor}", False
        if cmd == "/olvidar":
            return (f"Olvidé «{resto}»." if self.memoria.eliminar_largo_plazo(resto)
                    else f"No tengo nada guardado como «{resto}»."), False
        if cmd == "/conocimiento":
            if not resto:
                return "Uso: /conocimiento palabras a buscar", False
            from core.conocimiento import buscar as buscar_conocimiento
            resultados = buscar_conocimiento(resto, limite=3)
            if not resultados:
                return "No encontré conocimientos relacionados.", False
            return "\n\n".join(x["respuesta"][:500] + "\nFuente: " + x["fuente"]
                                for x in resultados), False
        if cmd == "/buscar-corpus":
            if not resto:
                return "Uso: /buscar-corpus palabras a buscar", False
            from core.local_search import buscar
            resultados = buscar(resto)
            if not resultados:
                from core.local_search import DB
                if not DB.is_file():
                    return ("No existe el índice local. Créalo con "
                            "python3 -m core.local_search --indexar"), False
                return "No encontré coincidencias en el corpus indexado.", False
            return "\n\n".join(f"[{origen}] {texto}" for texto, origen in resultados), False
        if cmd == "/biblioteca":
            if not resto:
                return "Uso: /biblioteca texto", False
            from pathlib import Path
            from core.biblioteca_local import buscar_en_biblioteca
            raiz = Path(config.raiz_datos()) / "data"
            resultados = buscar_en_biblioteca(resto, raiz)
            return ("\n\n".join(f"[{r['archivo']}] {r['fragmento']}" for r in resultados)
                    if resultados else "No encontré documentos relacionados."), False
        if cmd == "/calcular-local":
            from core.razonamiento_local import calcular
            try:
                return f"{resto} = {calcular(resto)}", False
            except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as exc:
                return f"No pude calcularlo: {exc}", False
        if cmd == "/analizar-codigo":
            from core.analizador_codigo_local import analizar
            try:
                return str(analizar(resto)), False
            except (SyntaxError, ValueError) as exc:
                return f"No pude analizarlo: {exc}", False
        if cmd in ("/resumir", "/palabras-clave"):
            if not resto:
                return f"Uso: {cmd} texto", False
            from core.estudio_local import resumir, palabras_clave
            try:
                return (resumir(resto) if cmd == "/resumir"
                        else ", ".join(palabras_clave(resto))), False
            except ValueError as exc:
                return f"No pude procesar el texto: {exc}", False
        if cmd in ("/estadisticas", "/comparar", "/fichas"):
            from core.herramientas_texto import estadisticas, comparar_textos, fichas_estudio
            try:
                if cmd == "/estadisticas":
                    return str(estadisticas(resto)), False
                if cmd == "/comparar":
                    if " || " not in resto:
                        return "Uso: /comparar primer texto || segundo texto", False
                    primero, segundo = resto.split(" || ", 1)
                    return str(comparar_textos(primero, segundo)), False
                fichas = fichas_estudio(resto.replace(" ; ", "\n"))
                return (str(fichas) if fichas
                        else "Uso: /fichas concepto: definición ; otro: definición"), False
            except ValueError as exc:
                return f"No pude procesarlo: {exc}", False
        if cmd in ("/preguntas", "/duplicados"):
            from core.repaso_local import generar_preguntas, detectar_duplicados
            try:
                if cmd == "/preguntas":
                    preguntas = generar_preguntas(resto)
                    return (str(preguntas) if preguntas
                            else "No encontré frases del tipo 'X es Y'."), False
                textos = [t.strip() for t in resto.split(" || ")]
                if len(textos) < 2:
                    return "Uso: /duplicados texto uno || texto dos", False
                return str(detectar_duplicados(textos)), False
            except ValueError as exc:
                return f"No pude procesarlo: {exc}", False
        if cmd in ("/aprobar-ejemplo", "/ejemplos-aprobados"):
            from pathlib import Path
            from core.ejemplos_aprobados import aprobar, listar
            ruta = Path(config.raiz_datos()) / "data" / "ejemplos_aprobados.jsonl"
            if cmd == "/ejemplos-aprobados":
                ejemplos = listar(ruta)
                return ("\n".join(f"P: {e['pregunta']}\nR: {e['respuesta']}"
                                  for e in ejemplos)
                        if ejemplos else "Todavía no hay ejemplos aprobados."), False
            if " || " not in resto:
                return "Uso: /aprobar-ejemplo pregunta || respuesta", False
            pregunta, respuesta = resto.split(" || ", 1)
            try:
                aprobar(ruta, pregunta, respuesta)
                return "Ejemplo aprobado y guardado. No se han modificado los pesos del modelo.", False
            except (ValueError, OSError) as exc:
                return f"No pude aprobar el ejemplo: {exc}", False
        if cmd == "/historial":
            from pathlib import Path
            from core.historial_local import consultar
            ruta = Path(config.raiz_datos()) / "data" / "historial_cerebro.jsonl"
            turnos = consultar(ruta, limite=20)
            return ("\n".join(f"{t['rol']}: {t['texto']}" for t in turnos)
                    if turnos else "No hay turnos guardados."), False
        if cmd == "/guardar-turno":
            from pathlib import Path
            from core.historial_local import guardar
            partes_turno = resto.split(None, 1)
            if len(partes_turno) != 2:
                return "Uso: /guardar-turno usuario|cerebro texto", False
            try:
                ruta = Path(config.raiz_datos()) / "data" / "historial_cerebro.jsonl"
                guardar(ruta, partes_turno[0], partes_turno[1])
                return "Turno guardado localmente.", False
            except (ValueError, OSError) as exc:
                return f"No pude guardar el turno: {exc}", False
        if cmd == "/experimentos":
            from pathlib import Path
            from core.laboratorio_local import historial
            ruta = Path(__file__).resolve().parent / "learning/evolution/experimentos.jsonl"
            registros = historial(ruta, limite=10)
            return ("\n".join(str(r) for r in registros)
                    if registros else "Todavía no hay experimentos registrados."), False
        if cmd == "/calc":
            return self._responder_con_agente(
                [{"tool": "calculator", "arguments": {"expression": resto}}]), False
        if cmd == "/hora":
            return self._responder_con_agente([{"tool": "clock", "arguments": {}}]), False
        if cmd == "/archivos":
            return self._responder_con_agente([{"tool": "list_files", "arguments": {}}]), False
        if cmd == "/leer":
            h = a.ejecutar_plan_autonomo([{"tool": "read_file", "arguments": {"filename": resto}}])[-1]
            r = h.get("resultado", h)
            return r.get("content", f"No pude hacerlo: {r.get('error')}"), False
        if cmd == "/escribir":
            p = resto.split(None, 1)
            if len(p) < 2:
                return "Uso: /escribir nombre.txt texto a guardar", False
            h = a.ejecutar_plan_autonomo(
                [{"tool": "write_file", "arguments": {"filename": p[0], "content": p[1]}}])[-1]
            r = h.get("resultado", h)
            return r.get("message", f"No pude hacerlo: {r.get('error')}"), False
        if cmd == "/temp":
            try:
                self.gen["temperatura"] = max(0.0, float(resto))
                return f"Temperatura = {self.gen['temperatura']}", False
            except ValueError:
                return "Uso: /temp 0.7", False
        if cmd == "/limpiar":
            self.memoria.limpiar_corto_plazo()
            return "Conversación reiniciada.", False
        return f"Comando desconocido: {cmd}. Escribe /ayuda.", False

    def estado(self):
        m = self.modelo
        lineas = [
            "=== ESTADO DE CEREBRO ===",
            f"Memoria de largo plazo: {len(self.memoria.long_term_memory)} datos",
            f"Temperatura: {self.gen['temperatura']}",
        ]
        if m is None:
            lineas.insert(1, "Modelo: herramientas y razonamiento local")
        else:
            c = m.cfg
            lineas[1:1] = [
                f"Modelo: transformer {c.n_layers} capas x {c.n_heads} cabezas, dim {c.dim}, "
                f"contexto {c.block_size}, {m.n_parametros():,} parámetros",
                f"Tokenizador: {m.tokenizer.tipo}, {len(m.tokenizer)} tokens",
            ]
        if "val_bpb" in self.info:
            lineas.append(f"Calidad en validación: {self.info['val_bpb']:.3f} bits/byte "
                          f"(perplejidad {self.info.get('val_ppl', float('nan')):.1f})")
        lineas.append(f"Permisos del agente: {', '.join(sorted(self.agente.permisos_concedidos))}")
        return "\n".join(lineas)
