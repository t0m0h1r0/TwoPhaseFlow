"""UCCD6 GPU/CPU parity smoke tests.

Skipped unless pytest is invoked with ``--gpu`` on a CuPy/CUDA host.
Verifies UCCD6Operator produces bit-close results on GPU vs the NumPy
reference (rtol 1e-10 for the full 4-call CCD chain).
"""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.uccd6 import UCCD6Operator


pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module")
def tiny_grid_factory():
    def _make(backend: Backend, N: int = 32):
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        return Grid(gc, backend)
    return _make


def _sample(xp, shape):
    X, Y = xp.meshgrid(
        xp.linspace(0.0, 1.0, shape[0], endpoint=True),
        xp.linspace(0.0, 1.0, shape[1], endpoint=True),
        indexing="ij",
    )
    return xp.sin(2.0 * np.pi * X) * xp.cos(2.0 * np.pi * Y)


def _assert_parity(gpu_val, cpu_val, gpu_backend, rtol=1e-10, atol=1e-12):
    np.testing.assert_allclose(
        gpu_backend.to_host(gpu_val), np.asarray(cpu_val),
        rtol=rtol, atol=atol,
    )


def test_uccd6_apply_rhs_gpu_matches_cpu(
    tiny_grid_factory, cpu_backend, gpu_backend,
):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)
    op_cpu = UCCD6Operator(g_cpu, cpu_backend, sigma=1.0, bc_type="periodic")
    op_gpu = UCCD6Operator(g_gpu, gpu_backend, sigma=1.0, bc_type="periodic")

    f_cpu = _sample(cpu_backend.xp, g_cpu.shape)
    f_gpu = gpu_backend.xp.asarray(f_cpu)

    for axis in range(2):
        rhs_cpu = op_cpu.apply_rhs(f_cpu, axis=axis, a=1.0)
        rhs_gpu = op_gpu.apply_rhs(f_gpu, axis=axis, a=1.0)
        _assert_parity(rhs_gpu, rhs_cpu, gpu_backend)


def test_uccd6_rk3_step_gpu_matches_cpu(
    tiny_grid_factory, cpu_backend, gpu_backend,
):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)
    op_cpu = UCCD6Operator(g_cpu, cpu_backend, sigma=1.0, bc_type="periodic")
    op_gpu = UCCD6Operator(g_gpu, gpu_backend, sigma=1.0, bc_type="periodic")

    f_cpu = _sample(cpu_backend.xp, g_cpu.shape)
    f_gpu = gpu_backend.xp.asarray(f_cpu)

    h = 1.0 / g_cpu.N[0]
    dt = 0.5 * h

    u_cpu = f_cpu
    u_gpu = f_gpu
    for _ in range(4):
        u_cpu = op_cpu.rk3_step(u_cpu, axis=0, a=1.0, dt=dt)
        u_gpu = op_gpu.rk3_step(u_gpu, axis=0, a=1.0, dt=dt)

    _assert_parity(u_gpu, u_cpu, gpu_backend, rtol=1e-9)


def test_uccd6_energy_monotone_gpu(
    tiny_grid_factory, cpu_backend, gpu_backend,
):
    """Energy monotonicity on GPU (sanity + no-NaN check)."""
    g = tiny_grid_factory(gpu_backend)
    op = UCCD6Operator(g, gpu_backend, sigma=1.0, bc_type="periodic")
    xp = gpu_backend.xp

    X, Y = xp.meshgrid(
        xp.linspace(0.0, 1.0, g.shape[0], endpoint=True),
        xp.linspace(0.0, 1.0, g.shape[1], endpoint=True),
        indexing="ij",
    )
    u = xp.sin(2.0 * np.pi * X) + 0.5 * xp.sin(8.0 * np.pi * X)

    h = 1.0 / g.N[0]
    dt = 0.4 * h
    e_prev = op.energy(u)
    for _ in range(20):
        u = op.rk3_step(u, axis=0, a=1.0, dt=dt)
        e_next = op.energy(u)
        assert e_next <= e_prev + 1e-12 * e_prev
        e_prev = e_next
