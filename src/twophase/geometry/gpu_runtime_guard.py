"""Fail-closed GPU guards for dense exact AO geometry runtime.

Symbol mapping:
    ``GPU AO-Fast`` -> active compact/fused kernels.
    ``dense exact AO`` -> CPU exact/runtime-oracle implementation.

Dense direct-AO geometry is useful as an exact CPU runtime and oracle, but it
uses Python-controlled scalar reductions and dense fixed-stratum CG.  Under the
AO-Fast YAML contract, CUDA execution must use active fused kernels instead of
quietly synchronizing through the host.
"""

from __future__ import annotations

from ..backend import is_device_array


_GPU_FAIL_CLOSE = (
    "GPU execution requires active fused AO-Fast kernels; dense exact AO "
    "runtime is CPU-only and host synchronization is disabled"
)


def reject_gpu_namespace(xp, *, context: str) -> None:
    """Raise when a dense exact AO path is entered with a CuPy namespace."""
    module = getattr(xp, "__name__", type(xp).__module__)
    if str(module).split(".", 1)[0] == "cupy":
        raise ValueError(f"{context}: {_GPU_FAIL_CLOSE}")


def reject_device_value(value, *, context: str) -> None:
    """Raise before a CUDA array/scalar can cross a hidden host boundary."""
    if is_device_array(value):
        raise ValueError(f"{context}: {_GPU_FAIL_CLOSE}")
