"""Segundo motor neuronal PROPIO de Cerebro: PyTorch opcional.

Transformer causal entrenado desde cero, sin pesos ni APIs de otras IA.
Checkpoints independientes: checkpoints/torch_cerebro.pt.
"""
import argparse
import hashlib
import os
from pathlib import Path

import config
from core.tokenizer import ID_EOS, TokenizadorBPE


def construir_modelo(perfil, vocab):
    import torch
    from torch import nn

    class Bloque(nn.Module):
        def __init__(self, dim, heads, ffn, dropout):
            super().__init__()
            self.ln1 = nn.LayerNorm(dim)
            self.att = nn.MultiheadAttention(dim, heads, dropout=dropout, batch_first=True)
            self.ln2 = nn.LayerNorm(dim)
            self.ff = nn.Sequential(nn.Linear(dim, ffn), nn.GELU(),
                                    nn.Linear(ffn, dim), nn.Dropout(dropout))

        def forward(self, x):
            import torch
            t = x.shape[1]
            mask = torch.ones(t, t, dtype=torch.bool, device=x.device).triu(1)
            h = self.ln1(x)
            x = x + self.att(h, h, h, attn_mask=mask, need_weights=False)[0]
            return x + self.ff(self.ln2(x))

    class Modelo(nn.Module):
        def __init__(self):
            super().__init__()
            p = config.PERFILES[perfil]
            self.block_size = p["block_size"]
            d = p["dim"]
            self.tokens = nn.Embedding(vocab, d)
            self.posiciones = nn.Embedding(self.block_size, d)
            self.bloques = nn.ModuleList(
                [Bloque(d, p["n_heads"], p["dim_ffn"], p["dropout"])
                 for _ in range(p["n_layers"])])
            self.norm = nn.LayerNorm(d)
            self.salida = nn.Linear(d, vocab, bias=False)
            self.salida.weight = self.tokens.weight

        def forward(self, ids):
            import torch
            t = ids.shape[1]
            if t > self.block_size:
                raise ValueError("Secuencia excede ventana de contexto")
            x = self.tokens(ids) + self.posiciones(torch.arange(t, device=ids.device))
            for bloque in self.bloques:
                x = bloque(x)
            return self.salida(self.norm(x))

    return Modelo()


def entrenar(corpus, perfil="pequeno", pasos=100, batch=4, lr=3e-4, salida=None,
             dispositivo="auto", semilla=1234, resume=False, guardar_cada=0):
    import torch
    import torch.nn.functional as F

    if pasos < 1 or batch < 1 or lr <= 0 or guardar_cada < 0:
        raise ValueError("pasos, batch y lr deben ser positivos")
    ruta = Path(corpus).expanduser()
    if not ruta.is_file():
        raise ValueError("Indica un archivo de corpus .txt existente")
    texto = ruta.read_text(encoding="utf-8")
    huella = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    if not texto.strip():
        raise ValueError("El corpus está vacío")
    if dispositivo == "auto":
        dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    if dispositivo == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA no está disponible")
    torch.manual_seed(semilla)
    p = config.PERFILES[perfil]
    destino = Path(salida) if salida else Path(config.DIR_CHECKPOINTS) / "torch_cerebro.pt"
    anterior = None
    if resume:
        if not destino.is_file() or destino.is_symlink():
            raise ValueError("No existe un checkpoint válido para reanudar")
        anterior = torch.load(destino, map_location="cpu", weights_only=True)
        if (anterior.get("formato") != "cerebro-torch-v2" or
                anterior.get("perfil") != perfil or anterior.get("corpus_sha256") != huella):
            raise ValueError("Checkpoint incompatible: perfil, corpus o formato distintos")
        tok = TokenizadorBPE.from_dict(anterior["tokenizador"])
    else:
        tok = TokenizadorBPE(p["vocab_objetivo"]).entrenar([texto])
    ids = torch.tensor([ID_EOS] + tok.codificar(texto) + [ID_EOS], dtype=torch.long)
    longitud = min(p["block_size"], len(ids) - 1)
    if longitud < 2:
        raise ValueError("Corpus insuficiente para entrenamiento")
    modelo = construir_modelo(perfil, len(tok)).to(dispositivo)
    opt = torch.optim.AdamW(modelo.parameters(), lr=lr, weight_decay=0.01)
    inicio = 0
    if anterior is not None:
        modelo.load_state_dict(anterior["pesos"], strict=True)
        opt.load_state_dict(anterior["optimizador"])
        inicio = int(anterior["paso"])
        torch.set_rng_state(anterior["rng_cpu"])
        if dispositivo == "cuda" and anterior.get("rng_cuda") is not None:
            torch.cuda.set_rng_state(anterior["rng_cuda"], device=dispositivo)
    def guardar(paso_actual):
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.is_symlink():
            raise ValueError("No se admite checkpoint simbólico")
        temporal = destino.with_name(destino.name + ".tmp")
        if temporal.is_symlink():
            raise ValueError("No se admite checkpoint temporal simbólico")
        estado = {"formato": "cerebro-torch-v2", "perfil": perfil,
                  "tokenizador": tok.to_dict(), "pesos": modelo.state_dict(),
                  "optimizador": opt.state_dict(), "paso": paso_actual,
                  "corpus_sha256": huella, "rng_cpu": torch.get_rng_state(),
                  "rng_cuda": torch.cuda.get_rng_state(device=dispositivo)
                  if dispositivo == "cuda" else None}
        torch.save(estado, temporal)
        os.replace(temporal, destino)
    modelo.train()
    for paso in range(inicio + 1, inicio + pasos + 1):
        inicios = torch.randint(0, len(ids) - longitud, (batch,))
        x = torch.stack([ids[i:i + longitud] for i in inicios]).to(dispositivo)
        y = torch.stack([ids[i + 1:i + longitud + 1] for i in inicios]).to(dispositivo)
        opt.zero_grad(set_to_none=True)
        loss = F.cross_entropy(modelo(x).reshape(-1, len(tok)), y.reshape(-1))
        if not torch.isfinite(loss):
            raise RuntimeError("Pérdida no finita")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
        opt.step()
        if paso == inicio + 1 or paso == inicio + pasos or paso % 25 == 0:
            print(f"paso {paso}/{inicio + pasos}: loss={loss.item():.4f}")
        if guardar_cada and paso % guardar_cada == 0:
            guardar(paso)
    guardar(inicio + pasos)
    return destino, sum(p.numel() for p in modelo.parameters())


def generar(checkpoint, prompt, max_tokens=60, dispositivo="cpu"):
    import torch
    ruta = Path(checkpoint)
    if not ruta.is_file():
        raise ValueError("No existe el checkpoint")
    # weights_only evita deserializar objetos Python arbitrarios.
    datos = torch.load(ruta, map_location="cpu", weights_only=True)
    if datos.get("formato") not in ("cerebro-torch-v1", "cerebro-torch-v2"):
        raise ValueError("Formato de checkpoint incompatible")
    tok = TokenizadorBPE.from_dict(datos["tokenizador"])
    modelo = construir_modelo(datos["perfil"], len(tok))
    modelo.load_state_dict(datos["pesos"], strict=True)
    modelo.to(dispositivo).eval()
    ids = [ID_EOS] + tok.codificar(prompt)
    with torch.inference_mode():
        for _ in range(max_tokens):
            x = torch.tensor([ids[-modelo.block_size:]], device=dispositivo)
            siguiente = int(modelo(x)[0, -1].argmax().item())
            if siguiente == ID_EOS:
                break
            ids.append(siguiente)
    return tok.decodificar(ids[1 + len(tok.codificar(prompt)):])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Entrenar el Transformer propio Cerebro con PyTorch")
    ap.add_argument("--corpus", help="Archivo .txt para entrenamiento desde cero")
    ap.add_argument("--perfil", choices=sorted(config.PERFILES), default="pequeno")
    ap.add_argument("--pasos", type=int, default=100)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--salida", help="Checkpoint PyTorch independiente")
    ap.add_argument("--dispositivo", choices=("auto", "cpu", "cuda"), default="auto")
    ap.add_argument("--generar", metavar="PROMPT", help="Generar con un checkpoint PyTorch existente")
    ap.add_argument("--max-tokens", type=int, default=60)
    ap.add_argument("--resume", action="store_true", help="Continuar entrenamiento del checkpoint v2")
    ap.add_argument("--guardar-cada", type=int, default=0, help="Guardar cada N pasos (0: solo al final)")
    args = ap.parse_args(argv)
    if args.generar is not None:
        if args.max_tokens < 1:
            ap.error("--max-tokens debe ser positivo")
        print(generar(args.salida or str(Path(config.DIR_CHECKPOINTS) / "torch_cerebro.pt"),
                      args.generar, args.max_tokens,
                      "cpu" if args.dispositivo == "auto" else args.dispositivo))
    else:
        if not args.corpus:
            ap.error("Para entrenar indica --corpus")
        destino, cantidad = entrenar(args.corpus, args.perfil, args.pasos, args.batch,
                                    args.lr, args.salida, args.dispositivo,
                                    resume=args.resume, guardar_cada=args.guardar_cada)
        print(f"Modelo propio: {cantidad:,} parámetros; checkpoint: {destino}")


if __name__ == "__main__":
    main()
