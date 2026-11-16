"""Bloque Transformer experimental: RMSNorm, RoPE, SwiGLU, SDPA.

Arquitectura propia; PyTorch solo aporta tensores/autograd.
No compatible con checkpoints del Transformer clásico.
"""


def construir_modelo_avanzado(perfil, vocab):
    import torch
    from torch import nn
    from torch.nn import functional as F
    import config

    p = config.PERFILES[perfil]
    dim, heads = p["dim"], p["n_heads"]
    if dim % heads:
        raise ValueError("dim debe ser divisible entre n_heads")
    hd = dim // heads
    if hd % 2:
        raise ValueError("RoPE requiere dimensión por cabeza par")

    class RMSNorm(nn.Module):
        def __init__(self, n):
            super().__init__()
            self.peso = nn.Parameter(torch.ones(n))
        def forward(self, x):
            return F.rms_norm(x, (x.shape[-1],), self.peso)

    class Atencion(nn.Module):
        def __init__(self):
            super().__init__()
            self.qkv = nn.Linear(dim, 3 * dim, bias=False)
            self.proj = nn.Linear(dim, dim, bias=False)
        def forward(self, x):
            b, t, _ = x.shape
            q, k, v = self.qkv(x).view(b, t, 3, heads, hd).unbind(2)
            q, k, v = (z.transpose(1, 2) for z in (q, k, v))
            inv = 1.0 / (10000 ** (torch.arange(0, hd, 2, device=x.device).float() / hd))
            ang = torch.arange(t, device=x.device).float()[:, None] * inv[None, :]
            cos, sin = ang.cos()[None, None], ang.sin()[None, None]
            def rotar(z):
                a, b = z[..., ::2], z[..., 1::2]
                return torch.stack((a * cos - b * sin, a * sin + b * cos), -1).flatten(-2)
            q, k = rotar(q), rotar(k)
            y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
            return self.proj(y.transpose(1, 2).contiguous().view(b, t, dim))

    class Bloque(nn.Module):
        def __init__(self):
            super().__init__()
            self.norm1, self.norm2 = RMSNorm(dim), RMSNorm(dim)
            self.att = Atencion()
            self.gate = nn.Linear(dim, p["dim_ffn"], bias=False)
            self.up = nn.Linear(dim, p["dim_ffn"], bias=False)
            self.down = nn.Linear(p["dim_ffn"], dim, bias=False)
        def forward(self, x):
            x = x + self.att(self.norm1(x))
            h = self.norm2(x)
            return x + self.down(F.silu(self.gate(h)) * self.up(h))

    class Modelo(nn.Module):
        def __init__(self):
            super().__init__()
            self.block_size = p["block_size"]
            self.tokens = nn.Embedding(vocab, dim)
            self.bloques = nn.ModuleList(Bloque() for _ in range(p["n_layers"]))
            self.norm = RMSNorm(dim)
            self.salida = nn.Linear(dim, vocab, bias=False)
            self.salida.weight = self.tokens.weight
        def forward(self, ids):
            if ids.shape[1] > self.block_size:
                raise ValueError("Contexto excedido")
            x = self.tokens(ids)
            for bloque in self.bloques:
                x = bloque(x)
            return self.salida(self.norm(x))
    return Modelo()
