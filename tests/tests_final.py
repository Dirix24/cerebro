# -*- coding: utf-8 -*-
"""
Pruebas de integridad de Cerebro. Sin frameworks de testing (solo `assert`):

    python3 tests/tests_final.py            # todas las pruebas
    python3 tests/tests_final.py -k gradientes   # solo las que contienen "gradientes"

Cubre lo importante de verdad:
  * los gradientes calculados a mano == diferencias finitas (float64),
    con y sin pesos compartidos y con dropout;
  * el modelo es causal (el futuro no influye en el pasado) y el lote da lo
    mismo que las secuencias por separado;
  * el tokenizador BPE es reversible con tildes, ñ y emojis;
  * el modelo aprende de verdad (memoriza una secuencia; reduce pérdida);
  * los checkpoints reproducen el modelo bit a bit y permiten reanudar;
  * seguridad del agente: calculadora, path traversal, permisos, límites.
"""

import os
import shutil
import sys
import tempfile
import time
import traceback

import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
from agent.controlled_agent import ControlledAgent
from agent.intents import detectar_intencion
from agent.tools.registry import ToolRegistry, evaluar_expresion_segura
from benchmarks.benchmark_engine import BenchmarkEngine
from chat import Conversacion
from core.checkpoint import cargar_checkpoint, guardar_checkpoint
from core.data import (CargadorBatches, Stream, construir_stream, documentos_desde_texto,
                       ventanas_secuenciales)
from core.optim import AdamW, lr_coseno_con_calentamiento, recortar_norma_global
from core.sampling import muestrear
from core.tokenizer import (ID_EOS, TokenizadorBPE, TokenizadorPalabras,
                            tokenizador_desde_dict)
from core.transformer.optimized_llm import ModeloConfig, OptimizedTransformerLLM
from memory.advanced_memory import AdvancedMemoryManager
from trainer_engine import ConfigEntrenamiento, TrainerEngine, evaluar_stream

TEXTO_ES = "Hola, ¿cómo estás? El niño comió piña 🍍 y añadió 42 años.\nusuario: hola\ncerebro: hola"


def modelo_chico(seed=0, **kw):
    base = dict(vocab_size=23, block_size=8, dim=12, n_heads=3, n_layers=2,
                dim_ffn=20, dropout=0.0, tie_weights=True, dtype="float64")
    base.update(kw)
    m = OptimizedTransformerLLM(ModeloConfig(**base), seed=seed)
    rng = np.random.default_rng(seed)
    for v in m.params.values():           # pesos no triviales para que el gradiente importe
        v += rng.standard_normal(v.shape) * 0.1
    return m


def error_relativo_max(m, ids, tg, entrenando=False, semilla_dropout=None, muestras=10):
    """Compara el gradiente analítico con diferencias finitas centrales."""
    def perdida():
        if semilla_dropout is not None:
            m.rng = np.random.default_rng(semilla_dropout)
        return m.perdida(m.forward(ids, entrenando=entrenando), tg)[0]

    if semilla_dropout is not None:
        m.rng = np.random.default_rng(semilla_dropout)
    _, grads = m.perdida_y_gradientes(ids, tg, entrenando=entrenando)
    rng = np.random.default_rng(1)
    peor = 0.0
    for nombre, valor in m.params.items():
        plano, g = valor.reshape(-1), grads[nombre].reshape(-1)
        for j in rng.choice(plano.size, size=min(muestras, plano.size), replace=False):
            viejo, h = plano[j], 1e-5
            plano[j] = viejo + h
            lp = perdida()
            plano[j] = viejo - h
            lm = perdida()
            plano[j] = viejo
            num = (lp - lm) / (2 * h)
            peor = max(peor, abs(num - g[j]) / max(1e-6, abs(num) + abs(g[j])))
    return peor


# =============================================================================
#  Modelo
# =============================================================================

def test_gradientes_coinciden_con_diferencias_finitas():
    rng = np.random.default_rng(0)
    ids = rng.integers(0, 23, size=(3, 7))
    tg = rng.integers(0, 23, size=(3, 7))
    tg[0, 2] = -1                                   # posición ignorada (relleno)
    for tie in (True, False):
        m = modelo_chico(tie_weights=tie)
        err = error_relativo_max(m, ids, tg)
        assert err < 1e-4, f"Gradiente incorrecto (tie={tie}): error relativo {err:.2e}"
    print("[OK] Backward manual == diferencias finitas (con y sin pesos compartidos).")


def test_gradientes_con_dropout():
    rng = np.random.default_rng(3)
    ids = rng.integers(0, 23, size=(2, 6))
    tg = rng.integers(0, 23, size=(2, 6))
    m = modelo_chico(dropout=0.3)
    err = error_relativo_max(m, ids, tg, entrenando=True, semilla_dropout=99)
    assert err < 1e-4, f"Gradiente con dropout incorrecto: {err:.2e}"
    print("[OK] Backward correcto también con dropout activo.")


def test_causalidad():
    m = modelo_chico(seed=1)
    a = np.array([[1, 2, 3, 4, 5, 6]])
    b = a.copy()
    b[0, 4:] = [9, 9]
    la, lb = m.forward(a), m.forward(b)
    assert np.allclose(la[0, :4], lb[0, :4]), "El futuro influye en el pasado: máscara rota."
    assert not np.allclose(la[0, 4:], lb[0, 4:]), "Cambiar la entrada no cambia la salida."
    print("[OK] El modelo es causal (no mira tokens futuros).")


def test_lote_equivale_a_secuencias_sueltas():
    m = modelo_chico(seed=2)
    x = np.random.default_rng(0).integers(0, 23, size=(4, 6))
    lote = m.forward(x)
    for i in range(4):
        assert np.allclose(m.forward(x[i])[0], lote[i]), "El lote no equivale a la secuencia suelta."
    print("[OK] Procesar en lote == procesar cada secuencia por separado.")


def test_dtype_float32_se_mantiene():
    cfg = ModeloConfig(vocab_size=30, block_size=8, dim=16, n_heads=2, n_layers=2,
                       dim_ffn=32, dropout=0.1, dtype="float32")
    m = OptimizedTransformerLLM(cfg)
    x = np.random.default_rng(0).integers(0, 30, size=(2, 8))
    loss, grads = m.perdida_y_gradientes(x, np.roll(x, -1, axis=1))
    assert m.forward(x).dtype == np.float32
    assert all(g.dtype == np.float32 for g in grads.values()), "Algún gradiente subió a float64."
    print("[OK] float32 se mantiene de punta a punta (rápido y con poca RAM).")


def test_el_modelo_aprende_y_memoriza():
    cfg = ModeloConfig(vocab_size=40, block_size=16, dim=32, n_heads=2, n_layers=2,
                       dim_ffn=64, dropout=0.0, dtype="float32")
    m = OptimizedTransformerLLM(cfg, seed=5)
    secuencia = np.array([[3, 7, 11, 5, 9, 13, 21, 4, 8, 30, 12, 6, 17, 25, 2]])
    x, y = secuencia[:, :-1], secuencia[:, 1:]
    opt = AdamW(m.params, lr=5e-3)
    inicial = None
    for _ in range(150):
        loss, grads = m.perdida_y_gradientes(x, y)
        inicial = inicial if inicial is not None else loss
        opt.step(grads)
    assert loss < 0.2 and loss < inicial / 5, f"No memorizó: {inicial:.3f} -> {loss:.3f}"
    pred = m.forward(x)[0].argmax(-1)
    assert (pred == y[0]).all(), "No predice la secuencia memorizada."
    print(f"[OK] El modelo aprende de verdad: pérdida {inicial:.3f} -> {loss:.4f}.")


def test_generacion_reproducible_y_controlada():
    tok = TokenizadorBPE(300).entrenar([TEXTO_ES] * 3)
    m = OptimizedTransformerLLM(ModeloConfig(vocab_size=len(tok), block_size=16, dim=16,
                                             n_heads=2, n_layers=1, dim_ffn=32), tokenizer=tok)
    a = m.generar("hola", max_nuevos=12, seed=7)
    b = m.generar("hola", max_nuevos=12, seed=7)
    assert a == b, "Con la misma semilla la generación debe ser idéntica."
    voraz1 = m.generar("hola", max_nuevos=8, temperatura=0, seed=1)
    voraz2 = m.generar("hola", max_nuevos=8, temperatura=0, seed=2)
    assert voraz1 == voraz2, "Temperatura 0 debe ser determinista."
    largo = m.generar("hola " * 40, max_nuevos=5, seed=0)      # prompt > block_size
    assert isinstance(largo, str)
    print("[OK] Generación reproducible con semilla; temperatura 0 determinista; contexto largo OK.")


def test_muestreo_top_k_top_p_penalizacion():
    rng = np.random.default_rng(0)
    logits = np.array([5.0, 4.0, 1.0, 0.0, -1.0])
    salidas = {muestrear(logits, rng, top_k=2) for _ in range(200)}
    assert salidas <= {0, 1}, f"top_k=2 devolvió {salidas}"
    salidas = {muestrear(logits, rng, top_p=0.5) for _ in range(200)}
    assert salidas == {0}, f"top_p=0.5 debería dejar solo el token 0, dejó {salidas}"
    assert muestrear(logits, rng, temperatura=0) == 0
    assert muestrear(logits, rng, temperatura=0, penalizacion=100.0, ids_previos=[0]) == 1
    assert muestrear(logits, rng, temperatura=0, ids_prohibidos=[0, 1]) == 2
    print("[OK] Muestreo: top-k, top-p, penalización de repetición y tokens prohibidos.")


def test_perdida_ignora_relleno():
    m = modelo_chico()
    x = np.array([[1, 2, 3, 4]])
    logits = m.forward(x)
    l_todo, _, n1 = m.perdida(logits, np.array([[2, 3, 4, 5]]))
    l_parcial, _, n2 = m.perdida(logits, np.array([[2, 3, -1, -1]]))
    assert n1 == 4 and n2 == 2 and l_todo != l_parcial
    print("[OK] La pérdida ignora las posiciones marcadas con -1.")


# =============================================================================
#  Tokenizador y datos
# =============================================================================

def test_bpe_reversible_y_persistente():
    tok = TokenizadorBPE(320).entrenar([TEXTO_ES] * 4)
    ids = tok.codificar(TEXTO_ES)
    assert tok.decodificar(ids) == TEXTO_ES, "BPE no es reversible."
    assert tok.bytes_de(ids) == len(TEXTO_ES.encode("utf-8"))
    raro = "ñandú 🚀 日本語 ~~ \t\n"
    assert tok.decodificar(tok.codificar(raro)) == raro, "Falla con texto nunca visto."
    tok2 = tokenizador_desde_dict(tok.to_dict())
    assert tok2.codificar(TEXTO_ES) == ids, "El tokenizador restaurado codifica distinto."
    assert len(ids) < len(TEXTO_ES.encode("utf-8")), "BPE no comprimió nada."
    print(f"[OK] BPE: reversible con tildes/ñ/emojis, sin <UNK>, persistente ({len(TEXTO_ES.encode())} bytes -> {len(ids)} tokens).")


def test_bpe_determinista():
    a = TokenizadorBPE(300).entrenar([TEXTO_ES] * 3).to_dict()
    b = TokenizadorBPE(300).entrenar([TEXTO_ES] * 3).to_dict()
    assert a == b
    print("[OK] El entrenamiento del tokenizador es determinista.")


def test_tokenizador_palabras():
    tok = TokenizadorPalabras(20).entrenar(["hola mundo hola cpu local", "hola cpu"])
    ids = tok.codificar("hola mundo desconocida")
    assert ids[0] == tok.stoi["hola"] and ids[-1] == 1, "Palabra desconocida debe ser <UNK>."
    assert "hola" in tok.decodificar(ids)
    assert tokenizador_desde_dict(tok.to_dict()).codificar("hola cpu") == tok.codificar("hola cpu")
    print("[OK] Tokenizador por palabras (el original) sigue funcionando.")


def test_datos_documentos_y_ventanas():
    docs = documentos_desde_texto("a b\nc d\n\n\ne f\n\n  \ng")
    assert docs == ["a b\nc d", "e f", "g"]
    tok = TokenizadorBPE(270).entrenar(["abcabcabc"])
    stream = construir_stream(["abc", "cab"], tok)
    assert stream.ids[0] == ID_EOS and stream.ids[-1] == ID_EOS and stream.mask[1:].all()
    completas, cola = ventanas_secuenciales(Stream(np.arange(10), np.ones(10, bool)), 4)
    cubierto = sum(len(x) for x, _ in completas) + (len(cola[0]) if cola else 0)
    assert cubierto == 9, "Las ventanas de evaluación deben cubrir todos los tokens objetivo."
    x, y = CargadorBatches(Stream(np.arange(50), np.ones(50, bool)), 8, 4, seed=0).siguiente()
    assert (y == x + 1).all()
    print("[OK] Documentos, stream y ventanas de evaluación/entrenamiento.")


def test_enmascarado_de_lineas_del_usuario():
    tok = TokenizadorBPE(300).entrenar([TEXTO_ES] * 3)
    doc = "usuario: hola\ncerebro: buenas"
    st = construir_stream([doc], tok)
    assert tok.decodificar(st.ids[1:-1]) == doc, "El stream debe reproducir el documento."
    visibles = tok.decodificar(st.ids[st.mask])
    assert "buenas" in visibles and "cerebro" in visibles and "hola" not in visibles, visibles
    completas, cola = ventanas_secuenciales(st, 200)
    _, y = completas[0] if completas else cola
    assert (y == -1).any() and (y >= 0).any(), "Debe haber objetivos enmascarados y visibles."
    prosa = construir_stream(["esto es prosa"], tok)
    assert prosa.mask[1:].all(), "La prosa cuenta entera."
    print("[OK] Enmascarado: solo se entrena a predecir las respuestas del diálogo.")


# =============================================================================
#  Optimizador y entrenamiento
# =============================================================================

def test_optimizador_y_schedule():
    p = {"w": np.array([[1.0, -2.0], [3.0, 4.0]]), "b": np.array([1.0, 1.0])}
    opt = AdamW(p, lr=0.1, weight_decay=0.1)
    opt.step({"w": np.ones((2, 2)), "b": np.ones(2)})
    assert (p["w"] < np.array([[1.0, -2.0], [3.0, 4.0]])).all() and (p["b"] < 1.0).all()
    g = {"a": np.full(4, 3.0), "b": np.full(4, 4.0)}       # norma = 10
    n = recortar_norma_global(g, 1.0)
    assert abs(n - 10.0) < 1e-9 and abs(np.sqrt(sum((v ** 2).sum() for v in g.values())) - 1.0) < 1e-9
    lrs = [lr_coseno_con_calentamiento(i, 100, 1.0, 0.1, 0.1) for i in range(100)]
    assert lrs[0] < lrs[9] and abs(lrs[9] - 1.0) < 1e-9 and lrs[-1] < 0.2
    print("[OK] AdamW, recorte de norma global y schedule de learning rate.")


def _docs_juguete():
    return ["usuario: hola\ncerebro: hola, ¿qué tal?"] * 10 + \
           ["usuario: adiós\ncerebro: hasta luego"] * 10, \
           ["usuario: hola\ncerebro: hola, ¿qué tal?"]


def test_entrenamiento_reduce_perdida_de_validacion():
    tr, va = _docs_juguete()
    ce = ConfigEntrenamiento(batch_size=8, lr=5e-3, eval_cada=20, seed=0)
    t = TrainerEngine.desde_cero(tr, va, perfil="diminuto", ce=ce,
                                 cambios_modelo=dict(n_layers=1, dropout=0.0))
    antes = t.evaluar()["bpb"]
    t.entrenar(80, log=None)
    despues = t.mejor["bpb"]
    assert despues < antes * 0.6, f"La validación no mejoró: {antes:.3f} -> {despues:.3f} bpb"
    print(f"[OK] Entrenamiento real: validación {antes:.2f} -> {despues:.2f} bits/byte.")


def test_checkpoint_roundtrip_y_reanudar():
    tr, va = _docs_juguete()
    ce = ConfigEntrenamiento(batch_size=4, lr=3e-3, eval_cada=10, seed=0)
    t = TrainerEngine.desde_cero(tr, va, perfil="diminuto", ce=ce,
                                 cambios_modelo=dict(n_layers=1, dropout=0.0))
    t.entrenar(10, log=None)
    tmp = tempfile.mkdtemp()
    try:
        ruta = os.path.join(tmp, "c.npz")
        t.guardar_ultimo(ruta)
        d = cargar_checkpoint(ruta)
        ids = np.array([[3, 10, 20, 30]])
        assert np.array_equal(t.modelo.forward(ids), d["modelo"].forward(ids)), \
            "El checkpoint no reproduce el modelo exactamente."
        assert d["opt_state"]["t"] == t.optim.t
        assert d["modelo"].tokenizer.codificar("hola") == t.modelo.tokenizer.codificar("hola")
        # Reanudar: continuar desde el checkpoint da el mismo estado del optimizador.
        t2 = TrainerEngine.desde_checkpoint(ruta, tr, va, ce)
        assert t2.optim.t == t.optim.t
        assert np.array_equal(t2.optim.m["l0.wqkv"], t.optim.m["l0.wqkv"])
        t2.entrenar(5, log=None)
        assert t2.optim.t == t.optim.t + 5
        # Un checkpoint sin optimizador (best) también carga.
        t.guardar_mejor(os.path.join(tmp, "b.npz"))
        assert cargar_checkpoint(os.path.join(tmp, "b.npz"))["opt_state"] is None
        # Sin restos de archivos temporales
        assert not [f for f in os.listdir(tmp) if f.endswith(".tmp")]
    finally:
        shutil.rmtree(tmp)
    print("[OK] Checkpoints: reproducen el modelo exactamente y permiten reanudar.")


def test_reanudacion_reproduce_los_mismos_pasos():
    """El checkpoint v4 guarda RNGs: continuar debe ser reproducible."""
    tr, va = _docs_juguete()
    ce = ConfigEntrenamiento(batch_size=2, lr=2e-3, eval_cada=1000, seed=7,
                             acumulacion_gradientes=2, paciencia_early_stop=0)
    t1 = TrainerEngine.desde_cero(tr, va, perfil="diminuto", ce=ce, seed_modelo=9)
    t1.entrenar(4, log=None)
    tmp = tempfile.mkdtemp()
    try:
        ruta = os.path.join(tmp, "resume.npz")
        t1.guardar_ultimo(ruta)
        t2 = TrainerEngine.desde_checkpoint(ruta, tr, va, ce)
        t1.entrenar(3, log=None)
        t2.entrenar(3, log=None)
        for n in t1.modelo.params:
            assert np.array_equal(t1.modelo.params[n], t2.modelo.params[n]), f"No reproducible: {n}"
        assert t1.optim.t == t2.optim.t
        print("[OK] Reanudar conserva RNG + batches + optimizador: continuación reproducible.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_checkpoint_viejo_incompatible_da_error_claro():
    tmp = tempfile.mkdtemp()
    try:
        ruta = os.path.join(tmp, "x.npz")
        np.savez(ruta, meta=np.array('{"formato": "otro"}'))
        try:
            cargar_checkpoint(ruta)
            assert False, "Debió rechazar un formato desconocido."
        except ValueError as e:
            assert "no soportado" in str(e)
    finally:
        shutil.rmtree(tmp)
    print("[OK] Un checkpoint de formato desconocido se rechaza con un error claro.")


# =============================================================================
#  Agente, herramientas y memoria
# =============================================================================

def test_calculadora_correcta_y_segura():
    assert evaluar_expresion_segura("10 + 5 * 2") == 20
    assert evaluar_expresion_segura("2 ** 10") == 1024
    assert abs(evaluar_expresion_segura("sqrt(16) + pi") - (4 + 3.141592653589793)) < 1e-9
    r = ToolRegistry()
    assert r.ejecutar("calculator", {"expression": "2^8"})["result"] == 256
    assert r.ejecutar("calculator", {"expression": "3,5 * 2"})["result"] == 7.0
    peligrosas = [
        "__import__('os').system('echo hackeado')", "open('/etc/passwd').read()",
        "[].__class__.__mro__[1].__subclasses__()", "(lambda: 1)()", "'a' * 3",
        "True + 1", "x + 1", "sqrt(4, 5)", "abs.__call__(1)",
        "9**9**9**9", "10**100000", "(9**9999)**9999", "2**" * 300 + "2",
    ]
    for expr in peligrosas:
        t0 = time.time()
        assert "error" in r.ejecutar("calculator", {"expression": expr}), f"No rechazó: {expr[:40]!r}"
        assert time.time() - t0 < 2, f"Tardó demasiado con {expr[:40]!r} (DoS)."
    assert "error" in r.ejecutar("calculator", {"expression": "1/0"})
    print("[OK] Calculadora: correcta, sin eval(), rechaza código y bombas de cómputo.")


def test_workspace_bloquea_escapes():
    tmp = tempfile.mkdtemp()
    try:
        ws = os.path.join(tmp, "ws")
        hermano = ws + "_secreto"            # empieza igual que ws: rompía a startswith()
        os.makedirs(ws)
        os.makedirs(hermano)
        with open(os.path.join(hermano, "clave.txt"), "w") as f:
            f.write("secreto")
        with open(os.path.join(tmp, "fuera.txt"), "w") as f:
            f.write("fuera")
        os.symlink(os.path.join(tmp, "fuera.txt"), os.path.join(ws, "enlace.txt"))

        r = ToolRegistry(workspace=ws)
        ataques = ["../../../etc/passwd", "../fuera.txt", "../ws_secreto/clave.txt",
                   os.path.join(hermano, "clave.txt"), "/etc/passwd", "enlace.txt", "", ".", "a\0b"]
        for a in ataques:
            res = r.ejecutar("read_file", {"filename": a})
            assert "error" in res and "content" not in res, f"Escape no bloqueado: {a!r} -> {res}"
        w = r.ejecutar("write_file", {"filename": "../pwn.txt", "content": "x"})
        assert "error" in w and not os.path.exists(os.path.join(tmp, "pwn.txt"))
        # Uso legítimo, incluso en subcarpetas
        assert r.ejecutar("write_file", {"filename": "notas/a.txt", "content": "hola"})["status"] == "success"
        assert r.ejecutar("read_file", {"filename": "notas/a.txt"})["content"] == "hola"
        assert "notas/a.txt" in r.ejecutar("list_files", {})["files"]
        # Tope de tamaño
        chico = ToolRegistry(workspace=ws, max_file_bytes=10)
        assert "error" in chico.ejecutar("write_file", {"filename": "g.txt", "content": "x" * 50})
    finally:
        shutil.rmtree(tmp)
    print("[OK] Workspace: bloquea ../, rutas absolutas, carpetas hermanas, enlaces simbólicos y archivos enormes.")


def test_agente_permisos_y_limites():
    tmp = tempfile.mkdtemp()
    try:
        reg = ToolRegistry(workspace=tmp)
        solo_lectura = ControlledAgent(permisos={"READ", "CALCULATE"}, registry=reg)
        h = solo_lectura.ejecutar_plan_autonomo(
            [{"tool": "write_file", "arguments": {"filename": "a.txt", "content": "x"}}])
        assert "Permiso denegado" in h[0]["error"] and not os.listdir(tmp)

        ag = ControlledAgent(max_steps=3, max_tool_calls=2, registry=reg)
        plan = [{"tool": "calculator", "arguments": {"expression": "1+1"}}] * 3
        h = ag.ejecutar_plan_autonomo(plan)
        assert h[0]["resultado"]["result"] == 2 and h[1]["resultado"]["result"] == 2
        assert "MAX_TOOL_CALLS" in h[2]["error"], "Debe respetar el límite de llamadas."
        h = ag.ejecutar_plan_autonomo([{"tool": "calculator", "arguments": {"expression": "1+1"}}] * 6)
        assert "aviso" in h[0] and len(h) <= 1 + ag.max_steps, "Debe recortar a MAX_AGENT_STEPS."
        assert "no autorizada" in ag.ejecutar_plan_autonomo([{"tool": "rm_rf"}])[0]["error"]
        assert "mal formada" in ag.ejecutar_plan_autonomo(["hola"])[0]["error"]
        assert "error" in ag.ejecutar_plan_autonomo([{"tool": "calculator", "arguments": {}}])[0]["resultado"]
        h = ag.ejecutar_plan_autonomo([{"tool": "calculator", "arguments": {"expression": "1/0"}},
                                       {"tool": "clock", "arguments": {}}])
        assert len(h) == 1, "Un paso fallido debe detener el plan."
        assert ag.ejecutar("calculator", expression="6*7")["result"] == 42
    finally:
        shutil.rmtree(tmp)
    print("[OK] Agente: permisos por herramienta, límites de pasos/llamadas y plan que falla cerrado.")


def test_enrutador_de_intenciones():
    casos = {
        "cuánto es 12 por 7": "calculator", "12 * (3 + 4)": "calculator",
        "calcula 2^10": "calculator", "cuánto es 10 entre 4": "calculator",
        "qué hora es": "clock", "¿Qué día es hoy?": "clock",
    }
    for texto, herramienta in casos.items():
        plan = detectar_intencion(texto)
        assert plan and plan[0]["tool"] == herramienta, f"{texto!r} -> {plan}"
    for texto in ["hola", "¿Qué es un token?", "2024", "me llamo Ana", "escribe un archivo"]:
        assert detectar_intencion(texto) is None, f"{texto!r} no debería activar herramientas"
    assert ControlledAgent().ejecutar_plan_autonomo(
        detectar_intencion("cuánto es 12 por 7"))[0]["resultado"]["result"] == 84
    print("[OK] Enrutador de intenciones: cuentas y hora sí; el resto va al modelo.")


def test_memoria():
    tmp = tempfile.mkdtemp()
    try:
        ruta = os.path.join(tmp, "m.json")
        mem = AdvancedMemoryManager(filepath=ruta, max_turnos=4)
        mem.guardar_largo_plazo("color", "azul")
        mem.guardar_largo_plazo("mascota", "un perro llamado Rex")
        assert mem.recuperar_largo_plazo("color") == "azul"
        assert mem.actualizar_largo_plazo("color", "verde") and not mem.actualizar_largo_plazo("x", "y")
        assert mem.buscar("REX") == {"mascota": "un perro llamado Rex"}
        assert AdvancedMemoryManager(filepath=ruta).recuperar_largo_plazo("color") == "verde", "No persiste."
        assert mem.eliminar_largo_plazo("color") and mem.recuperar_largo_plazo("color") is None
        for i in range(10):
            mem.agregar_contexto("usuario", str(i))
        assert [t["contenido"] for t in mem.short_term_context] == ["6", "7", "8", "9"]
        assert not [f for f in os.listdir(tmp) if f.endswith(".tmp")]
        with open(ruta, "w") as f:
            f.write("{ esto no es json")
        assert AdvancedMemoryManager(filepath=ruta).long_term_memory == {}, "Debe sobrevivir a un archivo corrupto."
    finally:
        shutil.rmtree(tmp)
    print("[OK] Memoria: corto/largo plazo, búsqueda, persistencia atómica y tolerancia a archivos corruptos.")


# =============================================================================
#  Conversación de punta a punta
# =============================================================================

def test_conversacion_de_punta_a_punta():
    tmp = tempfile.mkdtemp()
    try:
        tok = TokenizadorBPE(300).entrenar([TEXTO_ES] * 5)
        m = OptimizedTransformerLLM(ModeloConfig(vocab_size=len(tok), block_size=32, dim=16,
                                                 n_heads=2, n_layers=1, dim_ffn=32), tokenizer=tok)
        mem = AdvancedMemoryManager(filepath=os.path.join(tmp, "m.json"))
        ag = ControlledAgent(registry=ToolRegistry(workspace=os.path.join(tmp, "ws")))
        c = Conversacion(m, mem, ag, seed=0)

        assert c.procesar("cuánto es 12 por 7")[0] == "12 * 7 = 84"
        assert c.procesar("/calc 2^8")[0] == "2^8 = 256"
        assert "Ahora mismo" in c.procesar("qué hora es")[0]
        assert "Mucho gusto, Ana" in c.procesar("hola, me llamo Ana")[0]
        assert c.procesar("¿cómo me llamo?")[0] == "Te llamas Ana."
        assert "Guardado" in c.procesar("/recordar color = azul")[0]
        assert "azul" in c.procesar("/memoria")[0]
        assert "Olvidé" in c.procesar("/olvidar color")[0]
        assert "Escrito" in c.procesar("/escribir hola.txt buenas tardes")[0]
        assert c.procesar("/leer hola.txt")[0] == "buenas tardes"
        assert "No pude" in c.procesar("/leer ../../etc/passwd")[0]
        assert "desconocido" in c.procesar("/inventado")[0]
        assert "Temperatura = 0.0" in c.procesar("/temp 0")[0]
        r, salir = c.procesar("¿qué es un token?")
        assert isinstance(r, str) and r and not salir
        assert len(mem.short_term_context) == 2
        assert c.procesar("/salir") == ("¡Hasta pronto!", True)
        # el prompt nunca excede el contexto del modelo, aunque el historial sea enorme
        for i in range(30):
            mem.agregar_contexto("usuario", "palabra " * 20)
        ids = c._armar_prompt_ids("hola " * 200, 16)
        assert len(ids) <= m.cfg.block_size - 16
    finally:
        shutil.rmtree(tmp)
    print("[OK] Conversación completa: comandos, agente, memoria y respuesta del modelo.")


def test_benchmark():
    tok = TokenizadorBPE(300).entrenar([TEXTO_ES] * 5)
    m = OptimizedTransformerLLM(ModeloConfig(vocab_size=len(tok), block_size=32, dim=16,
                                             n_heads=2, n_layers=1, dim_ffn=32), tokenizer=tok)
    b = BenchmarkEngine(m).ejecutar_benchmark_completo()
    assert b["parametros"] == m.n_parametros() > 0
    assert b["tok_s_entrenamiento"] > 0 and b["tok_s_generacion"] > 0
    print(f"[OK] Benchmark real: {b['parametros']:,} parámetros, {b['tok_s_entrenamiento']:,} tok/s entrenando.")


def test_modelo_enviado_funciona():
    """Si el proyecto trae un checkpoint entrenado, debe cargar y rendir mejor
    que un modelo aleatorio sobre la validación."""
    if not os.path.exists(config.CKPT_MEJOR):
        print("[--] Sin checkpoints/best.npz: prueba omitida.")
        return
    from core.data import cargar_validacion
    from trainer_engine import evaluar_modelo_en_docs
    d = cargar_checkpoint(config.CKPT_MEJOR, con_optimizador=False)
    val = cargar_validacion()
    if not val:
        print("[--] Sin data/validacion.txt: prueba omitida.")
        return
    entrenado = evaluar_modelo_en_docs(d["modelo"], val)["bpb"]
    azar = evaluar_modelo_en_docs(OptimizedTransformerLLM(d["modelo"].cfg, tokenizer=d["modelo"].tokenizer),
                                  val)["bpb"]
    assert entrenado < azar * 0.5, f"El modelo entrenado ({entrenado:.2f}) no supera al azar ({azar:.2f})."
    print(f"[OK] checkpoints/best.npz: {entrenado:.2f} bits/byte vs {azar:.2f} de un modelo sin entrenar.")


# =============================================================================

def main():
    filtro = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else ""
    pruebas = [(n, f) for n, f in sorted(globals().items())
               if n.startswith("test_") and callable(f) and filtro in n]
    pruebas.sort(key=lambda p: p[1].__code__.co_firstlineno)   # en orden de escritura
    print(f"--- EJECUTANDO {len(pruebas)} PRUEBAS DE INTEGRIDAD ---\n")
    fallos = []
    t0 = time.time()
    for nombre, f in pruebas:
        try:
            f()
        except Exception:
            fallos.append(nombre)
            print(f"[FALLO] {nombre}")
            traceback.print_exc()
    print()
    if fallos:
        print(f"--- {len(fallos)} PRUEBA(S) FALLARON: {', '.join(fallos)} ---")
        sys.exit(1)
    print(f"--- TODAS LAS PRUEBAS SUPERADAS ({len(pruebas)}) en {time.time() - t0:.1f}s ---")


if __name__ == "__main__":
    main()
