"""FCCD GPU/CPU parity smoke tests — CHK-158 V7.

Skipped unless pytest is invoked with ``--gpu`` on a CuPy/CUDA host.
Verifies FCCDSolver primitives produce bit-close results on GPU vs NumPy
reference (rtol 1e-12 for elementwise kernels).
"""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.fccd import FCCDSolver


pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module")
def tiny_grid_factory():
    def _make(backend: Backend, N: int = 32):
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        return Grid(gc, backend)
    return _make


def _sample(xp, shape):
    X, Y = xp.meshgrid(
        xp.linspace(-1.0, 1.0, shape[0]),
        xp.linspace(-1.0, 1.0, shape[1]),
        indexing="ij",
    )
    return xp.exp(-(X * X + Y * Y) * 3.0) * xp.cos(4.0 * X) * xp.sin(3.0 * Y)


def _assert_parity(gpu_val, cpu_val, gpu_backend, rtol=1e-12, atol=1e-13):
    np.testing.assert_allclose(
        gpu_backend.to_host(gpu_val), np.asarray(cpu_val),
        rtol=rtol, atol=atol,
    )


def test_fccd_face_gradient_gpu_matches_cpu(
    tiny_grid_factory, cpu_backend, gpu_backend,
):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)
    fccd_cpu = FCCDSolver(g_cpu, cpu_backend)
    fccd_gpu = FCCDSolver(g_gpu, gpu_backend)

    f_cpu = _sample(cpu_backend.xp, g_cpu.shape)
    f_gpu = gpu_backend.xp.asarray(f_cpu)

    for axis in range(2):
        d_cpu = fccd_cpu.face_gradient(f_cpu, axis)
        d_gpu = fccd_gpu.face_gradient(f_gpu, axis)
        _assert_parity(d_gpu, d_cpu, gpu_backend)


def test_fccd_face_value_gpu_matches_cpu(
    tiny_grid_factory, cpu_backend, gpu_backend,
):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)
    fccd_cpu = FCCDSolver(g_cpu, cpu_backend)
    fccd_gpu = FCCDSolver(g_gpu, gpu_backend)

    f_cpu = _sample(cpu_backend.xp, g_cpu.shape)
    f_gpu = gpu_backend.xp.asarray(f_cpu)

    for axis in range(2):
        u_cpu = fccd_cpu.face_value(f_cpu, axis)
        u_gpu = fccd_gpu.face_value(f_gpu, axis)
        _assert_parity(u_gpu, u_cpu, gpu_backend)


def test_fccd_pressure_flux_public_scheme_stays_on_gpu(
    tiny_grid_factory, gpu_backend,
):
    from twophase.simulation.divergence_ops import FCCDDivergenceOperator

    grid = tiny_grid_factory(gpu_backend)
    fccd = FCCDSolver(grid, gpu_backend)
    div_op = FCCDDivergenceOperator(fccd)
    pressure = _sample(gpu_backend.xp, grid.shape)
    rho = gpu_backend.xp.ones(grid.shape, dtype=pressure.dtype)

    fluxes = div_op.pressure_fluxes(
        pressure,
        rho,
        pressure_gradient="fccd_flux",
        coefficient_scheme="phase_separated",
        interface_coupling_scheme="affine_jump",
    )

    assert all(hasattr(flux, "__cuda_array_interface__") for flux in fluxes)


def test_fccd_node_gradient_gpu_matches_cpu(
    tiny_grid_factory, cpu_backend, gpu_backend,
):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)
    fccd_cpu = FCCDSolver(g_cpu, cpu_backend)
    fccd_gpu = FCCDSolver(g_gpu, gpu_backend)

    f_cpu = _sample(cpu_backend.xp, g_cpu.shape)
    f_gpu = gpu_backend.xp.asarray(f_cpu)

    for axis in range(2):
        d_cpu = fccd_cpu.node_gradient(f_cpu, axis)
        d_gpu = fccd_gpu.node_gradient(f_gpu, axis)
        _assert_parity(d_gpu, d_cpu, gpu_backend)


@pytest.mark.parametrize("mode", ["node", "flux"])
def test_fccd_advection_rhs_gpu_matches_cpu(
    mode, tiny_grid_factory, cpu_backend, gpu_backend,
):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)
    fccd_cpu = FCCDSolver(g_cpu, cpu_backend)
    fccd_gpu = FCCDSolver(g_gpu, gpu_backend)

    u_cpu = _sample(cpu_backend.xp, g_cpu.shape)
    v_cpu = _sample(cpu_backend.xp, g_cpu.shape) * 0.7
    u_gpu = gpu_backend.xp.asarray(u_cpu)
    v_gpu = gpu_backend.xp.asarray(v_cpu)

    out_cpu = fccd_cpu.advection_rhs([u_cpu, v_cpu], mode=mode)
    out_gpu = fccd_gpu.advection_rhs([u_gpu, v_gpu], mode=mode)

    for arr_gpu, arr_cpu in zip(out_gpu, out_cpu):
        _assert_parity(arr_gpu, arr_cpu, gpu_backend)


def test_fccd_periodic_advection_rhs_gpu_matches_cpu(
    tiny_grid_factory, cpu_backend, gpu_backend,
):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)
    fccd_cpu = FCCDSolver(g_cpu, cpu_backend, bc_type="periodic")
    fccd_gpu = FCCDSolver(g_gpu, gpu_backend, bc_type="periodic")

    u_cpu = _sample(cpu_backend.xp, g_cpu.shape)
    v_cpu = _sample(cpu_backend.xp, g_cpu.shape) * 0.7
    u_gpu = gpu_backend.xp.asarray(u_cpu)
    v_gpu = gpu_backend.xp.asarray(v_cpu)

    out_cpu = fccd_cpu.advection_rhs([u_cpu, v_cpu], mode="flux")
    out_gpu = fccd_gpu.advection_rhs([u_gpu, v_gpu], mode="flux")

    for arr_gpu, arr_cpu in zip(out_gpu, out_cpu):
        _assert_parity(arr_gpu, arr_cpu, gpu_backend)
