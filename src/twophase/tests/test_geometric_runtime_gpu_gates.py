"""GPU fail-close gates for dense exact AO runtime pieces."""

from __future__ import annotations

import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.geometry.p1_cut_geometry import cut_geometry_2d


def test_direct_dense_geometry_rejects_gpu_backend():
    try:
        import cupy  # noqa: F401
    except Exception:
        pytest.skip("CuPy is not importable")
    try:
        backend = Backend(use_gpu=True)
    except RuntimeError as exc:
        pytest.skip(f"GPU backend unavailable: {exc}")

    grid = Grid(GridConfig(ndim=2, N=(8, 8), L=(1.0, 1.0)), backend)
    xp = backend.xp
    x = xp.asarray(grid.coords[0]).reshape((-1, 1))
    phi = x - xp.asarray(0.5)

    with pytest.raises(ValueError, match="active fused AO-Fast kernels"):
        cut_geometry_2d(grid, phi)
