"""GPU fail-close gates for dense exact AO runtime pieces."""

from __future__ import annotations

import pytest
import numpy as np

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.geometry.p1_cut_geometry import cut_geometry_2d
from twophase.simulation.geometric_phase_runtime_gpu import _host_scalar_packet_float


class _CountingBackend:
    xp = np

    def __init__(self):
        self.host_transfer_count = 0

    def to_host(self, value):
        self.host_transfer_count += 1
        return value


def test_gpu_scalar_packet_uses_one_host_transfer():
    backend = _CountingBackend()
    values = _host_scalar_packet_float(
        backend,
        [
            ("compatibility", np.asarray(1.0e-12)),
            ("normal", np.asarray(2.0e-12)),
            ("predictor", np.asarray(3.0e-12)),
        ],
    )

    assert values == {
        "compatibility": pytest.approx(1.0e-12),
        "normal": pytest.approx(2.0e-12),
        "predictor": pytest.approx(3.0e-12),
    }
    assert backend.host_transfer_count == 1


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
