"""Memory-saving helpers for running on small (e.g. 2GB RAM) hosts.

CPU inference doesn't need PyTorch's threading pool or full fp32 weights, and
dynamic int8 quantization roughly halves a transformer's Linear-layer memory.
Quantization needs the FBGEMM backend, which is reliable on x86_64 but not on
all ARM builds (e.g. local Apple Silicon dev) -- so failures are swallowed and
the original fp32 module is kept.
"""

import torch

torch.set_num_threads(1)
torch.set_grad_enabled(False)


def quantize(module: torch.nn.Module) -> torch.nn.Module:
    try:
        return torch.quantization.quantize_dynamic(module, {torch.nn.Linear}, dtype=torch.qint8)
    except Exception:
        return module
