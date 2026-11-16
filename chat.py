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
  /estado                   información del modelo y de la memoria
  /memoria                  muestra lo que hay en la memoria de largo plazo
  /recordar clave = valor   guarda un dato
  /olvidar clave            borra un dato
  /calc 12 * (3 + 4)        calculadora segura
  /buscar-corpus texto      busca información en el corpus local indexado
  /conocimiento texto       consulta la memoria con fuentes
  /biblioteca texto         busca en documentos locales
  /calcular-local cuenta    calcula expresiones aritmeticas
  /analizar-codigo texto    analiza Python sin ejecutarlo
  /experimentos             muestra metricas registradas
  /resumir texto            resumen extractivo local
  /palabras-clave texto     palabras frecuentes del texto
  /estadisticas texto      cuenta palabras, frases y lineas
  /comparar A || B          compara dos textos
  /fichas concepto: dato   crea fichas de estudio
  /preguntas texto         preguntas de repaso desde frases X es Y
  /duplicados A || B      detecta textos similares
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
    def __init__(self, modelo, memoria, agente, info_checkpoint=None, seed=None):
        self.modelo = modelo
        self.memoria = memoria
        self.agente = agente
        self.info = info_checkpoint or {}
        self.gen = dict(max_nuevos=config.GEN_MAX_NUEVOS, temperatura=config.GEN_TEMPERATURA,
                        top_k=config.GEN_TOP_K, top_p=config.GEN_TOP_P,
                        penalizacion=config.GEN_PENALIZACION_REPETICION)
        import numpy as np
        self.rng = np.random.default_rng(seed)

    # -- entrada principal ------------------------------------------------------------

    def procesar(self, entrada):
        """Devuelve (texto de respuesta, terminar: bool)."""
        entrada = entrada.strip()
        if not entrada:
            return "", False
        if entrada.startswith("/"):
            return self._comando(entrada)

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
            return f"Mucho gusto, {nombre}. Lo guardé en mi memoria. ¿En qué te puedo ayudar?", False

        # No inventar conocimiento: respuesta automática solo ante pregunta exacta.
        try:
            from core.conocimiento import respuesta_exacta
            dato = respuesta_exacta(entrada)
            if dato:
                return dato["respuesta"] + "\nFuente: " + dato["fuente"], False
        except (OSError, ValueError):
            pass
        return self.responder_modelo(entrada), False

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
        return ids[-(B - max_nuevos):]

    def responder_modelo(self, mensaje):
        g = self.gen
        max_nuevos = max(8, min(g["max_nuevos"], self.modelo.cfg.block_size - 40))
        ids = self._armar_prompt_ids(mensaje, max_nuevos)
        nuevos, _ = self.modelo.generar_ids(
            ids, max_nuevos=max_nuevos, temperatura=g["temperatura"], top_k=g["top_k"],
            top_p=g["top_p"], penalizacion=g["penalizacion"], parar_en=("\n",), rng=self.rng)
        texto = self.modelo.tokenizer.decodificar(nuevos).split("\n")[0].strip()
        if not texto:
            texto = "No sé qué responder a eso."
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

        if cmd in ("/salir", "/exit", "/quit"):
            return "¡Hasta pronto!", True
        if cmd in ("/ayuda", "/help"):
            return AYUDA, False
        if cmd in ("/estado", "/status"):
            return self.estado(), False
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
                return ("No hay resultados locales. Crea el índice con "
                        "python3 -m core.local_search --indexar"), False
            return "\n\n".join(f"[{origen}] {texto}" for texto, origen in resultados), False
        if cmd == "/biblioteca":
            if not resto:
                return "Uso: /biblioteca texto", False
            from pathlib import Path
            from core.biblioteca_local import buscar_en_biblioteca
            raiz = Path(__file__).resolve().parent / "data"
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
        c = m.cfg
        lineas = [
            "=== ESTADO DE CEREBRO ===",
            f"Modelo: transformer {c.n_layers} capas x {c.n_heads} cabezas, dim {c.dim}, "
            f"contexto {c.block_size}, {m.n_parametros():,} parámetros",
            f"Tokenizador: {m.tokenizer.tipo}, {len(m.tokenizer)} tokens",
            f"Memoria de largo plazo: {len(self.memoria.long_term_memory)} datos",
            f"Temperatura: {self.gen['temperatura']}",
        ]
        if "val_bpb" in self.info:
            lineas.append(f"Calidad en validación: {self.info['val_bpb']:.3f} bits/byte "
                          f"(perplejidad {self.info.get('val_ppl', float('nan')):.1f})")
        lineas.append(f"Permisos del agente: {', '.join(sorted(self.agente.permisos_concedidos))}")
        return "\n".join(lineas)
