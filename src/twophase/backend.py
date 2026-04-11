"""
GPU / CPU array-namespace abstraction.

All numerical modules receive ``xp`` (the array namespace) through their
constructors and never import numpy or cupy directly in hot paths.

Usage::

    backend = Backend()                 # honours TWOPHASE_USE_GPU env var
    xp = backend.xp                     # numpy or cupy
    sp = backend.scipy.sparse           # scipy.sparse or cupyx.scipy.sparse
    la = backend.scipy.linalg           # scipy.linalg or cupyx.scipy.linalg
    arr = xp.zeros((10, 10))
    x = backend.solve_banded_batched(ab, rhs, axis=0)

The ``scipy`` namespace is lazily resolved on first access and cached.
"""

from __future__ import annotations

import os
import sys
from functools import cached_property


class Backend:
    """Transparent numpy / cupy switcher.

    Attributes
    ----------
    xp : module
        The array namespace (numpy or cupy).
    device : str
        ``"gpu"`` or ``"cpu"``.
    """

    def __init__(self, use_gpu: bool | None = None):
        if use_gpu is None:
            use_gpu = os.environ.get("TWOPHASE_USE_GPU", "0") == "1"
        if use_gpu and self._cupy_available():
            import cupy as cp
            self.xp = cp
            self.device = "gpu"
        else:
            if use_gpu:
                print(
                    "WARNING: TWOPHASE_USE_GPU=1 but CuPy/CUDA unavailable; "
                    "falling back to NumPy",
                    file=sys.stderr,
                )
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

    # ── SciPy dispatch (lazy; matches xp device) ─────────────────────────

    @cached_property
    def scipy(self):
        """SciPy-compatible namespace for the active device.

        Returns the real ``scipy`` module on CPU and ``cupyx.scipy`` on GPU.
        Both expose ``sparse``, ``sparse.linalg``, and ``linalg`` submodules
        with matching call signatures for ``csr_matrix``, ``csc_matrix``,
        ``spsolve``, ``splu``, ``lu_factor``, ``lu_solve``.
        """
        if self.device == "gpu":
            import cupyx.scipy as _cusp
            # Ensure the submodules are loaded so attribute access is cheap.
            import cupyx.scipy.sparse  # noqa: F401
            import cupyx.scipy.sparse.linalg  # noqa: F401
            import cupyx.scipy.linalg  # noqa: F401
            return _cusp
        import scipy as _sp
        import scipy.sparse  # noqa: F401
        import scipy.sparse.linalg  # noqa: F401
        import scipy.linalg  # noqa: F401
        return _sp

    @cached_property
    def sparse(self):
        """Shortcut for ``self.scipy.sparse``."""
        return self.scipy.sparse

    @cached_property
    def sparse_linalg(self):
        """Shortcut for ``self.scipy.sparse.linalg``."""
        return self.scipy.sparse.linalg

    @cached_property
    def linalg(self):
        """Shortcut for ``self.scipy.linalg`` (dense LAPACK wrappers).

        Note: ``self.xp.linalg`` (numpy.linalg / cupy.linalg) remains the
        array-namespace linalg. This property exposes the scipy-side
        linalg (``lu_factor``, ``lu_solve``, ``solve_banded``, …).
        """
        return self.scipy.linalg

    # ── Host/device transfer helpers ─────────────────────────────────────

    def to_host(self, arr):
        """Transfer array to CPU (no-op on CPU backend or for NumPy inputs)."""
        if self.device == "gpu" and hasattr(arr, "get"):
            return arr.get()
        return arr

    def asnumpy(self, arr):
        """CuPy-idiomatic alias of :meth:`to_host`."""
        return self.to_host(arr)

    def to_device(self, arr):
        """Transfer array to the configured device (no-op on CPU backend)."""
        if self.device == "gpu":
            import cupy as cp
            return cp.asarray(arr)
        return arr

    def is_gpu(self) -> bool:
        return self.device == "gpu"

    # ── Batched banded solver (axis-aligned tridiagonal) ────────────────

    def solve_banded_batched(self, ab, rhs, axis: int, l_and_u=(1, 1)):
        """Banded solve along ``axis`` of ``rhs``.

        Parameters
        ----------
        ab : (l+u+1, n) array
            Banded matrix in :func:`scipy.linalg.solve_banded` layout.
        rhs : ndarray
            ``rhs.shape[axis] == n``; arbitrary batch dims otherwise.
        axis : int
            Axis along which to solve.
        l_and_u : tuple[int, int]
            Lower/upper bandwidth. Currently only ``(1, 1)`` is supported on
            GPU (routed to :func:`linalg_backend.thomas_batched`). On CPU
            all values are supported via :func:`scipy.linalg.solve_banded`.

        Returns
        -------
        x : ndarray
            Same shape as ``rhs``.
        """
        if self.device == "gpu":
            if l_and_u != (1, 1):
                raise NotImplementedError(
                    f"GPU solve_banded_batched currently supports l_and_u=(1,1) only, "
                    f"got {l_and_u}"
                )
            from .linalg_backend import thomas_batched
            return thomas_batched(self.xp, ab, rhs, axis)

        # CPU: scipy.linalg.solve_banded, axis-agnostic wrapper.
        import numpy as _np
        from scipy.linalg import solve_banded as _solve_banded
        n = rhs.shape[axis]
        moved = _np.moveaxis(rhs, axis, 0)
        batch_shape = moved.shape[1:]
        rhs_2d = moved.reshape(n, -1)
        x_2d = _solve_banded(l_and_u, ab, rhs_2d)
        x_moved = x_2d.reshape((n,) + batch_shape)
        return _np.moveaxis(x_moved, 0, axis)

    def __repr__(self) -> str:
        return f"Backend(device='{self.device}')"
