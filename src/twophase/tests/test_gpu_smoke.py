"""GPU smoke tests.

These tests are skipped unless pytest is invoked with ``--gpu`` on a host
with a working CuPy/CUDA setup. They verify that the hot-path modules
produce bit-close results on GPU relative to the NumPy reference.

Tolerance rationale
-------------------
- Elementwise pipelines (compact filters, CCD derivatives): ``rtol=1e-12``
  — FP64 CuPy and NumPy differ only by operation ordering, well below
  this.
- Sparse LU (PPE): ``rtol=1e-10`` — cuDSS / cuSPARSE pivoting can differ
  from SuperLU by a few ULPs on variable-density matrices.
- End-to-end short integration: ``max|ψ| < 1e-10`` on a 5-step run of a
  small 2-D bubble.
"""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.compact_filters import HelmholtzKappaFilter, LeleCompactFilter


pytestmark = pytest.mark.gpu


@pytest.fixture(scope="module")
def tiny_grid_factory():
    """Return a callable that builds a 2-D grid on the requested backend."""

    def _make(backend: Backend, N: int = 32):
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        return Grid(gc, backend)

    return _make


def _sample_field(xp, shape):
    coords = [xp.linspace(-1.0, 1.0, n) for n in shape]
    X, Y = xp.meshgrid(*coords, indexing="ij")
    return xp.exp(-(X * X + Y * Y) * 3.0) * xp.cos(4.0 * X) * xp.sin(3.0 * Y)


def test_ccd_derivative_gpu_matches_cpu(tiny_grid_factory, cpu_backend, gpu_backend):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)

    ccd_cpu = CCDSolver(g_cpu, cpu_backend)
    ccd_gpu = CCDSolver(g_gpu, gpu_backend)

    f_cpu = _sample_field(cpu_backend.xp, g_cpu.shape)
    f_gpu = gpu_backend.xp.asarray(f_cpu)

    for axis in range(2):
        d1_cpu, d2_cpu = ccd_cpu.differentiate(f_cpu, axis)
        d1_gpu, d2_gpu = ccd_gpu.differentiate(f_gpu, axis)

        np.testing.assert_allclose(
            gpu_backend.to_host(d1_gpu), np.asarray(d1_cpu),
            rtol=1e-12, atol=5e-13,
        )
        np.testing.assert_allclose(
            gpu_backend.to_host(d2_gpu), np.asarray(d2_cpu),
            rtol=1e-12, atol=5e-13,
        )


def test_helmholtz_filter_gpu_matches_cpu(tiny_grid_factory, cpu_backend, gpu_backend):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)
    ccd_cpu = CCDSolver(g_cpu, cpu_backend)
    ccd_gpu = CCDSolver(g_gpu, gpu_backend)

    filt_cpu = HelmholtzKappaFilter(cpu_backend, ccd_cpu, alpha=1.0)
    filt_gpu = HelmholtzKappaFilter(gpu_backend, ccd_gpu, alpha=1.0)

    kappa_cpu = _sample_field(cpu_backend.xp, g_cpu.shape)
    psi_cpu = 0.5 + 0.4 * cpu_backend.xp.tanh(
        _sample_field(cpu_backend.xp, g_cpu.shape) * 2.0
    )
    kappa_gpu = gpu_backend.xp.asarray(kappa_cpu)
    psi_gpu = gpu_backend.xp.asarray(psi_cpu)

    out_cpu = filt_cpu.apply(kappa_cpu, psi_cpu)
    out_gpu = filt_gpu.apply(kappa_gpu, psi_gpu)

    np.testing.assert_allclose(
        gpu_backend.to_host(out_gpu), np.asarray(out_cpu),
        rtol=1e-12, atol=1e-13,
    )


def test_lele_compact_filter_gpu_matches_cpu(tiny_grid_factory, cpu_backend, gpu_backend):
    g_cpu = tiny_grid_factory(cpu_backend)
    g_gpu = tiny_grid_factory(gpu_backend)
    ccd_cpu = CCDSolver(g_cpu, cpu_backend)
    ccd_gpu = CCDSolver(g_gpu, gpu_backend)

    lele_cpu = LeleCompactFilter(cpu_backend, ccd_cpu, xi_c=np.pi / 2)
    lele_gpu = LeleCompactFilter(gpu_backend, ccd_gpu, xi_c=np.pi / 2)

    f_cpu = _sample_field(cpu_backend.xp, g_cpu.shape)
    f_gpu = gpu_backend.xp.asarray(f_cpu)

    out_cpu = lele_cpu.apply(f_cpu)
    out_gpu = lele_gpu.apply(f_gpu)

    np.testing.assert_allclose(
        gpu_backend.to_host(out_gpu), np.asarray(out_cpu),
        rtol=1e-12, atol=1e-13,
    )


def test_ppe_ccd_lu_gpu_matches_cpu(cpu_backend, gpu_backend):
    """Direct PPE solve on a 24x24 static droplet RHS."""
    from twophase.ppe.ccd_lu import PPESolverCCDLU

    def _build(backend):
        cfg = SimulationConfig(
            grid=GridConfig(ndim=2, N=(24, 24), L=(1.0, 1.0)),
            fluid=FluidConfig(Re=100.0),
            numerics=NumericsConfig(),
            solver=SolverConfig(ppe_solver_type="ccd_lu", allow_kronecker_lu=True),
            use_gpu=backend.is_gpu(),
        )
        grid = Grid(cfg.grid, backend)
        ccd = CCDSolver(grid, backend)
        ppe = PPESolverCCDLU(backend, cfg, grid, ccd=ccd)
        return grid, ppe

    grid_cpu, ppe_cpu = _build(cpu_backend)
    grid_gpu, ppe_gpu = _build(gpu_backend)

    shape = grid_cpu.shape
    rng = np.random.default_rng(2026)
    rhs_np = rng.standard_normal(shape)
    rho_np = np.ones(shape) + 0.1 * rng.standard_normal(shape) ** 2

    p_cpu = ppe_cpu.solve(rhs_np, rho_np, dt=1e-3)
    rhs_gpu = gpu_backend.xp.asarray(rhs_np)
    rho_gpu = gpu_backend.xp.asarray(rho_np)
    p_gpu = ppe_gpu.solve(rhs_gpu, rho_gpu, dt=1e-3)

    np.testing.assert_allclose(
        gpu_backend.to_host(p_gpu), np.asarray(p_cpu),
        rtol=1e-10, atol=1e-12,
    )


def test_ppe_fvm_builder_gpu_matches_cpu(cpu_backend, gpu_backend):
    """build_values() unified xp path: GPU result matches CPU to rtol=1e-10."""
    import scipy.sparse as sp
    from twophase.ppe.ppe_builder import PPEBuilder

    def _build(backend, N=32):
        from twophase.core.grid import Grid
        from twophase.config import GridConfig
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ppb = PPEBuilder(backend, grid, bc_type='wall')
        ppb.build_structure()
        return ppb

    ppb_cpu = _build(cpu_backend)
    ppb_gpu = _build(gpu_backend)

    rng = np.random.default_rng(42)
    rho_np = 1.0 + rng.uniform(0, 1, ppb_cpu.shape_field)

    # CPU reference: build_values() returns numpy array on CPU backend
    data_cpu = ppb_cpu.build_values(rho_np)
    n = ppb_cpu.n_dof
    A_cpu = sp.csr_matrix(
        (data_cpu, (ppb_cpu._struct_rows, ppb_cpu._struct_cols)), shape=(n, n)
    ).toarray()

    # GPU: build_values() returns cupy array; _struct_rows/cols are cupy arrays
    rho_gpu = gpu_backend.xp.asarray(rho_np)
    data_dev = ppb_gpu.build_values(rho_gpu)
    data_h = gpu_backend.to_host(data_dev)
    rows_h = np.asarray(gpu_backend.to_host(ppb_gpu._struct_rows))
    cols_h = np.asarray(gpu_backend.to_host(ppb_gpu._struct_cols))
    A_gpu = sp.csr_matrix((data_h, (rows_h, cols_h)), shape=(n, n)).toarray()

    np.testing.assert_allclose(A_gpu, A_cpu, rtol=1e-10, atol=1e-15)
