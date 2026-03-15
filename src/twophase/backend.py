"""
GPU / CPU array-namespace abstraction.

All numerical modules receive ``xp`` (the array namespace) through their
constructors and never import numpy or cupy directly.

Usage::

    backend = Backend(use_gpu=False)
    xp = backend.xp          # numpy or cupy
    arr = xp.zeros((10, 10))
"""


class Backend:
    """Transparent numpy / cupy switcher.

    Attributes
    ----------
    xp : module
        The array namespace (numpy or cupy).
    device : str
        ``"gpu"`` or ``"cpu"``.
    """

    def __init__(self, use_gpu: bool = False):
        if use_gpu and self._cupy_available():
            import cupy as cp
            self.xp = cp
            self.device = "gpu"
        else:
            import numpy as np
            self.xp = np
            self.device = "cpu"

    @staticmethod
    def _cupy_available() -> bool:
        try:
            import cupy
            cupy.cuda.Device(0).compute_capability  # raises if no GPU
            return True
        except Exception:
            return False

    def to_host(self, arr):
        """Transfer array to CPU (no-op on CPU backend)."""
        return arr.get() if self.device == "gpu" else arr

    def to_device(self, arr):
        """Transfer array to the configured device (no-op on CPU backend)."""
        if self.device == "gpu":
            import cupy as cp
            return cp.asarray(arr)
        return arr

    def __repr__(self) -> str:
        return f"Backend(device='{self.device}')"
