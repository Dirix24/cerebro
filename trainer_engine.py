# -*- coding: utf-8 -*-
"""
Motor de entrenamiento de Cerebro.

Un paso de entrenamiento real:
    lote aleatorio (B ventanas de T tokens) -> forward -> entropía cruzada ->
    backward manual -> recorte de norma global -> AdamW con lr coseno.

Métricas de validación (sobre documentos que el modelo NO ve al entrenar):
    loss   entropía cruzada media por token (nats)
    ppl    perplejidad = exp(loss)
    bpb    bits por byte de texto = nll_total / (ln 2 · bytes). Es la métrica
           para COMPARAR modelos con tokenizadores distintos (la loss por
           token no es comparable entre ellos; los bits por byte sí).
"""

import math
import time
import hashlib
from dataclasses import dataclass

import numpy as np

import config
from core.checkpoint import cargar_checkpoint, guardar_checkpoint
from core.data import CargadorBatches, construir_stream, ventanas_secuenciales
from core.optim import crear_optimizador, lr_coseno_con_calentamiento, recortar_norma_global
from core.tokenizer import ID_EOS, crear_tokenizador
from core.transformer.optimized_llm import ModeloConfig, OptimizedTransformerLLM


# =============================================================================
#  Evaluación
# =============================================================================

def evaluar_stream(modelo, stream, tokenizador=None, tam_lote=16):
    """Evalúa el modelo sobre TODO el stream (ventanas sin solape), contando
    solo los tokens que son objetivo (respuestas). dict(loss, ppl, bpb, n_tokens)."""
    tokenizador = tokenizador or modelo.tokenizer
    completas, cola = ventanas_secuenciales(stream, modelo.cfg.block_size)
    nll_total, n_total, bytes_total = 0.0, 0, 0

    def acumular(xs, ys):
        nonlocal nll_total, n_total, bytes_total
        x = np.stack(xs).astype(np.int64)
        y = np.stack(ys).astype(np.int64)
        logits = modelo.forward(x, entrenando=False)
        loss, _, n = modelo.perdida(logits, y)
        nll_total += loss * n
        n_total += n
        bytes_total += tokenizador.bytes_de(y[y >= 0])

    for i in range(0, len(completas), tam_lote):
        trozo = completas[i:i + tam_lote]
        acumular([t[0] for t in trozo], [t[1] for t in trozo])
    if cola is not None:
        acumular([cola[0]], [cola[1]])

    if n_total == 0:
        raise ValueError("El conjunto de evaluación no contiene tokens objetivo válidos.")
    loss = nll_total / n_total
    bpb = nll_total / (math.log(2) * max(bytes_total, 1))
    return {"loss": loss, "ppl": math.exp(min(loss, 50.0)), "bpb": bpb, "n_tokens": n_total}


def huella_documentos(docs):
    """Huella estable del conjunto de documentos para detectar cambios de datos."""
    h = hashlib.sha256()
    for d in docs:
        h.update(d.replace("\r\n", "\n").encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def evaluar_modelo_en_docs(modelo, docs_val):
    """Evalúa un modelo con SU PROPIO tokenizador sobre unos documentos de
    validación. Permite comparar de forma justa modelos con vocabularios
    distintos (vía bits por byte)."""
    stream = construir_stream(docs_val, modelo.tokenizer)
    return evaluar_stream(modelo, stream)


def precision_de_respuestas(modelo, docs):
    """Mide lo que importa en un chat: para cada diálogo "usuario:/cerebro:"
    de `docs`, genera la respuesta VORAZ (temperatura 0) a la pregunta y la
    compara con la esperada. Devuelve dict(exactas, similitud, n).

    exactas    fracción de respuestas idénticas a la esperada.
    similitud  parecido medio de texto (0-1, difflib) — premia las casi-aciertos."""
    import difflib
    n = exactas = 0
    similitud = 0.0
    for d in docs:
        lineas = d.split("\n")
        if (len(lineas) != 2 or not lineas[0].startswith("usuario:")
                or not lineas[1].startswith("cerebro:")):
            continue
        esperado = lineas[1][len("cerebro:"):].strip()
        prompt = lineas[0] + "\ncerebro:"
        ids = [ID_EOS] + modelo.tokenizer.codificar(prompt)
        max_nuevos = max(8, modelo.cfg.block_size - len(ids))
        nuevos, _ = modelo.generar_ids(ids, max_nuevos=min(max_nuevos, 80), temperatura=0.0,
                                       penalizacion=1.0, parar_en=("\n",), seed=0)
        obtenido = modelo.tokenizer.decodificar(nuevos).split("\n")[0].strip()
        n += 1
        exactas += obtenido == esperado
        similitud += difflib.SequenceMatcher(None, obtenido, esperado).ratio()
    return {"exactas": exactas / max(n, 1), "similitud": similitud / max(n, 1), "n": n}


# =============================================================================
#  Configuración de entrenamiento
# =============================================================================

@dataclass
class ConfigEntrenamiento:
    batch_size: int = config.BATCH_SIZE
    lr: float = config.TASA_APRENDIZAJE
    lr_min_factor: float = config.LR_MIN_FACTOR
    warmup_frac: float = config.WARMUP_FRACCION
    weight_decay: float = config.WEIGHT_DECAY
    grad_clip: float = config.GRAD_CLIP
    eval_cada: int = config.EVAL_CADA
    seed: int = config.SEED
    optimizador: str = config.OPTIMIZADOR
    beta1: float = config.ADAM_BETA1
    beta2: float = config.ADAM_BETA2
    eps: float = config.ADAM_EPS
    momentum: float = config.SGD_MOMENTUM
    fraccion_val: float = config.FRACCION_VALIDACION
    acumulacion_gradientes: int = config.ACUMULACION_GRADIENTES
    paciencia_early_stop: int = config.PACIENCIA_EARLY_STOP


def config_modelo_desde_perfil(perfil=None, vocab_size=None, **cambios):
    """Construye un ModeloConfig a partir de un perfil de config.py."""
    base = dict(config.PERFILES[perfil or config.PERFIL])
    base.pop("vocab_objetivo", None)
    base.update(cambios)
    if vocab_size is not None:
        base["vocab_size"] = vocab_size
    return ModeloConfig(tie_weights=config.TIE_WEIGHTS, dtype=config.DTYPE, **base).validar()


# =============================================================================
#  Motor
# =============================================================================

class TrainerEngine:
    def __init__(self, modelo, docs_train, docs_val, ce=None, opt_state=None, rng_state=None):
        self.modelo = modelo
        self.ce = ce or ConfigEntrenamiento()
        self.docs_train, self.docs_val = docs_train, docs_val
        tok = modelo.tokenizer
        self.stream_train = construir_stream(docs_train, tok)
        self.stream_val = construir_stream(docs_val, tok)
        self.cargador = CargadorBatches(
            self.stream_train, modelo.cfg.block_size, self.ce.batch_size, seed=self.ce.seed)
        self.optim = crear_optimizador(
            self.ce.optimizador, modelo.params, self.ce.lr,
            weight_decay=self.ce.weight_decay, beta1=self.ce.beta1,
            beta2=self.ce.beta2, eps=self.ce.eps, momentum=self.ce.momentum)
        if opt_state is not None:
            self.optim.load_state_dict(opt_state)
        self.paso = self.optim.t
        self.mejor = None            # dict(bpb, loss, paso, estado)
        self.historial = []
        self.mejor_sin_mejora = 0
        # El estado del RNG forma parte de una reanudación reproducible.
        self._restaurar_rng(rng_state)

    def _restaurar_rng(self, estado=None):
        """Restaura el RNG del modelo y del muestreador de batches si existe."""
        if not estado:
            return
        try:
            if estado.get("modelo") is not None:
                self.modelo.rng.bit_generator.state = estado["modelo"]
            if estado.get("batches") is not None:
                self.cargador.rng.bit_generator.state = estado["batches"]
        except (KeyError, TypeError, ValueError):
            # Checkpoints antiguos no contienen estos estados: siguen siendo cargables.
            pass

    def estado_rng(self):
        return {
            "modelo": self.modelo.rng.bit_generator.state,
            "batches": self.cargador.rng.bit_generator.state,
        }

    # -- constructores ----------------------------------------------------------------

    @classmethod
    def desde_cero(cls, docs_train, docs_val, perfil=None, ce=None, tokenizador=None,
                   tipo_tokenizador=None, cambios_modelo=None, seed_modelo=None):
        """Entrena un tokenizador con los documentos de entrenamiento (nunca
        con los de validación, para no filtrar información) y crea un
        modelo nuevo con pesos aleatorios."""
        ce = ce or ConfigEntrenamiento()
        perfil = perfil or config.PERFIL
        if tokenizador is None:
            objetivo = config.PERFILES[perfil]["vocab_objetivo"]
            tokenizador = crear_tokenizador(tipo_tokenizador or config.TOKENIZADOR, objetivo)
            tokenizador.entrenar(docs_train)
        cfg = config_modelo_desde_perfil(perfil, vocab_size=len(tokenizador),
                                         **(cambios_modelo or {}))
        modelo = OptimizedTransformerLLM(
            cfg, tokenizer=tokenizador,
            seed=ce.seed if seed_modelo is None else seed_modelo)
        return cls(modelo, docs_train, docs_val, ce)

    @classmethod
    def desde_checkpoint(cls, ruta, docs_train, docs_val, ce=None, con_optimizador=True):
        """Continúa un entrenamiento (o afina un modelo) desde un checkpoint.
        Reutiliza SU tokenizador; los documentos nuevos se codifican con él."""
        ce = ce or ConfigEntrenamiento()
        datos = cargar_checkpoint(ruta, con_optimizador=con_optimizador)
        return cls(datos["modelo"], docs_train, docs_val, ce, opt_state=datos["opt_state"], rng_state=datos.get("rng_state"))

    # -- evaluación / mejor modelo ----------------------------------------------------------

    def evaluar(self):
        return evaluar_stream(self.modelo, self.stream_val)

    def _registrar_mejor(self, ev):
        if self.mejor is None or ev["bpb"] < self.mejor["bpb"]:
            self.mejor = {"bpb": ev["bpb"], "loss": ev["loss"], "ppl": ev["ppl"],
                          "paso": self.paso, "estado": self.modelo.state_dict()}
            return True
        return False

    # -- bucle de entrenamiento -----------------------------------------------------------

    def entrenar(self, pasos, log=print):
        """Entrena `pasos` pasos con calentamiento + decaimiento coseno del lr.
        Guarda en memoria los mejores pesos según la validación (bpb)."""
        ce, modelo = self.ce, self.modelo
        T = self.cargador.T
        t_inicio = time.time()
        suma_loss, n_loss = 0.0, 0
        ultima_norma = 0.0

        if ce.acumulacion_gradientes < 1:
            raise ValueError("acumulacion_gradientes debe ser >= 1")
        if ce.eval_cada < 1:
            raise ValueError("eval_cada debe ser >= 1")
        total_programado = max(1, self.paso + pasos)
        for i in range(pasos):
            # El scheduler usa el paso GLOBAL: al reanudar no vuelve a empezar en warmup.
            lr = lr_coseno_con_calentamiento(
                self.paso, total_programado, ce.lr, ce.warmup_frac, ce.lr_min_factor)
            grads_acum = None
            loss_acum = 0.0
            for _ in range(ce.acumulacion_gradientes):
                x, y = self.cargador.siguiente()
                loss, grads = modelo.perdida_y_gradientes(x, y, entrenando=True)
                if not math.isfinite(loss):
                    raise RuntimeError(
                        f"La pérdida se volvió {loss} en el paso {self.paso}. "
                        f"Baja la tasa de aprendizaje (TASA_APRENDIZAJE en config.py).")
                loss_acum += loss
                if grads_acum is None:
                    grads_acum = {k: v.copy() for k, v in grads.items()}
                else:
                    for k in grads_acum:
                        grads_acum[k] += grads[k]
            for k in grads_acum:
                grads_acum[k] /= ce.acumulacion_gradientes
            ultima_norma = recortar_norma_global(grads_acum, ce.grad_clip)
            self.optim.step(grads_acum, lr=lr)
            self.paso += 1
            suma_loss += loss_acum / ce.acumulacion_gradientes
            n_loss += 1

            if (i + 1) % ce.eval_cada == 0 or i + 1 == pasos:
                ev = self.evaluar()
                es_mejor = self._registrar_mejor(ev)
                self.mejor_sin_mejora = 0 if es_mejor else self.mejor_sin_mejora + 1
                transcurrido = time.time() - t_inicio
                tok_s = (i + 1) * ce.batch_size * T / max(transcurrido, 1e-9)
                restante = transcurrido / (i + 1) * (pasos - i - 1)
                fila = {"paso": self.paso, "loss_train": suma_loss / n_loss,
                        "loss_val": ev["loss"], "ppl_val": ev["ppl"],
                        "bpb_val": ev["bpb"], "lr": lr, "norma_grad": ultima_norma,
                        "tok_s": tok_s}
                self.historial.append(fila)
                if log:
                    log(f"paso {i + 1:>5}/{pasos} | train {fila['loss_train']:.3f} | "
                        f"val {ev['loss']:.3f} (ppl {ev['ppl']:.1f}, {ev['bpb']:.3f} bpb) | "
                        f"lr {lr:.2e} | {tok_s:,.0f} tok/s | resta ~{restante:.0f}s"
                        f"{'  *mejor*' if es_mejor else ''}")
                suma_loss, n_loss = 0.0, 0
                if ce.paciencia_early_stop and self.mejor_sin_mejora >= ce.paciencia_early_stop:
                    if log:
                        log(f"early-stop: {ce.paciencia_early_stop} evaluaciones sin mejora")
                    break

        return {"pasos": pasos, "mejor_bpb": self.mejor["bpb"] if self.mejor else None,
                "mejor_paso": self.mejor["paso"] if self.mejor else None,
                "segundos": time.time() - t_inicio}

    # -- guardado -------------------------------------------------------------------------

    def _meta(self, extra=None):
        meta = {
            "paso": self.paso,
            "perfil": config.PERFIL,
            "entrenamiento": {k: getattr(self.ce, k) for k in self.ce.__dataclass_fields__},
            "n_tokens_train": int(len(self.stream_train)),
            "n_tokens_val": int(len(self.stream_val)),
            "hash_train": huella_documentos(self.docs_train),
            "hash_val": huella_documentos(self.docs_val),
            "objetivo_de_perdida": "solo respuestas (líneas del usuario enmascaradas)",
            "acumulacion_gradientes": self.ce.acumulacion_gradientes,
        }
        if self.mejor:
            meta.update(val_loss=self.mejor["loss"], val_ppl=self.mejor["ppl"],
                        val_bpb=self.mejor["bpb"], mejor_paso=self.mejor["paso"])
        if extra:
            meta.update(extra)
        return meta

    def guardar_ultimo(self, ruta):
        """Estado final + optimizador (para --resume)."""
        ev = self.evaluar()
        guardar_checkpoint(ruta, self.modelo, optimizador=self.optim,
                           meta_extra=self._meta({"val_bpb": ev["bpb"], "val_loss": ev["loss"],
                                                  "val_ppl": ev["ppl"],
                                                  "rng_state": self.estado_rng()}))

    def guardar_mejor(self, ruta):
        """Guarda los pesos con mejor validación (sin estado del optimizador)."""
        if self.mejor is None:
            raise RuntimeError("Todavía no hay una evaluación de validación.")
        actual = self.modelo.state_dict()
        self.modelo.load_state_dict(self.mejor["estado"])
        try:
            guardar_checkpoint(ruta, self.modelo, optimizador=None, meta_extra=self._meta())
        finally:
            self.modelo.load_state_dict(actual)
