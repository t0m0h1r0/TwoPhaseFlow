"""Tests for the matrix-free FVM PPE solver."""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig, SolverConfig
from twophase.core.grid import Grid
from twophase.ppe.factory import create_ppe_solver
from twophase.ppe.fd_direct import PPESolverFDDirect
from twophase.ppe.fd_matrixfree import PPESolverFDMatrixFree
from twophase.ppe.fvm_defect_correction import PPESolverFVMDefectCorrection
from twophase.ppe.fvm_matrixfree import PPESolverFVMMatrixFree
from twophase.ppe.fvm_spsolve import PPESolverFVMSpsolve
from twophase.ppe.ppe_builder import PPEBuilder


def _make_cfg(N=8):
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        solver=SolverConfig(
            ppe_solver_type="fvm_iterative",
            pseudo_tol=1e-10,
            pseudo_maxiter=200,
            pseudo_c_tau=2.0,
        ),
    )


def test_fvm_matrixfree_apply_matches_builder():
    backend = Backend(use_gpu=False)
    cfg = _make_cfg(8)
    grid = Grid(cfg.grid, backend)

    solver = PPESolverFVMMatrixFree(backend, cfg, grid, bc_type="wall")
    builder = PPEBuilder(backend, grid, bc_type="wall")
    builder.build_structure()

    rng = np.random.default_rng(123)
    rho = 1.0 + rng.uniform(0.0, 1.0, grid.shape)
    p = rng.standard_normal(grid.shape)

    solver._operator_coeffs = [solver.build_line_coeffs(rho, ax) for ax in range(grid.ndim)]
    out_mf = np.asarray(solver.apply(p)).ravel()

    data = builder.build_values(rho)
    n = builder.n_dof
    A = sp.csr_matrix(
        (data, (builder._struct_rows, builder._struct_cols)), shape=(n, n)
    )
    out_ref = A @ p.ravel()

    np.testing.assert_allclose(out_mf, out_ref, rtol=1e-12, atol=1e-12)


def test_fvm_matrixfree_solve_matches_direct_fvm():
    backend = Backend(use_gpu=False)
    cfg = _make_cfg(8)
    grid = Grid(cfg.grid, backend)

    solver_mf = PPESolverFVMMatrixFree(backend, cfg, grid, bc_type="wall")
    solver_ref = PPESolverFVMSpsolve(backend, grid, bc_type="wall")

    rng = np.random.default_rng(456)
    rho = 1.0 + rng.uniform(0.0, 1.0, grid.shape)
    rhs = rng.standard_normal(grid.shape)

    p_mf = np.asarray(solver_mf.solve(rhs, rho, dt=1e-3))
    p_ref = np.asarray(solver_ref.solve(rhs, rho, dt=1e-3))

    np.testing.assert_allclose(p_mf, p_ref, rtol=1e-9, atol=1e-10)

def test_fvm_defect_correction_with_direct_base_matches_direct_fvm():
    backend = Backend(use_gpu=False)
    cfg = _make_cfg(8)
    grid = Grid(cfg.grid, backend)
    base_solver = PPESolverFVMSpsolve(backend, grid, bc_type="wall")
    operator = PPESolverFVMMatrixFree(backend, cfg, grid, bc_type="wall")
    solver_dc = PPESolverFVMDefectCorrection(
        backend,
        grid,
        base_solver,
        operator,
        max_corrections=2,
        tolerance=1.0e-10,
        relaxation=1.0,
    )

    rng = np.random.default_rng(789)
    rho = 1.0 + rng.uniform(0.0, 1.0, grid.shape)
    rhs = rng.standard_normal(grid.shape)

    pressure_dc = np.asarray(solver_dc.solve(rhs, rho, dt=1e-3))
    pressure_ref = np.asarray(base_solver.solve(rhs, rho, dt=1e-3))
    np.testing.assert_allclose(pressure_dc, pressure_ref, rtol=1e-9, atol=1e-10)


def test_fvm_matrixfree_jacobi_preconditioner_matches_direct_fvm():
    backend = Backend(use_gpu=False)
    cfg = _make_cfg(8)
    cfg.solver.ppe_preconditioner = "jacobi"
    grid = Grid(cfg.grid, backend)

    solver_mf = PPESolverFVMMatrixFree(backend, cfg, grid, bc_type="wall")
    solver_ref = PPESolverFVMSpsolve(backend, grid, bc_type="wall")

    rng = np.random.default_rng(789)
    rho = 1.0 + rng.uniform(0.0, 1.0, grid.shape)
    rhs = rng.standard_normal(grid.shape)

    p_mf = np.asarray(solver_mf.solve(rhs, rho, dt=1e-3))
    p_ref = np.asarray(solver_ref.solve(rhs, rho, dt=1e-3))

    np.testing.assert_allclose(p_mf, p_ref, rtol=1e-9, atol=1e-10)


def test_fd_matrixfree_cg_matches_fd_direct():
    backend = Backend(use_gpu=False)
    cfg = _make_cfg(8)
    cfg.solver.ppe_solver_type = "fd_iterative"
    cfg.solver.ppe_iteration_method = "cg"
    cfg.solver.ppe_preconditioner = "jacobi"
    grid = Grid(cfg.grid, backend)

    solver_cg = PPESolverFDMatrixFree(backend, cfg, grid, bc_type="wall")
    solver_ref = PPESolverFDDirect(backend, grid, bc_type="wall")

    rng = np.random.default_rng(987)
    rho = 1.0 + rng.uniform(0.0, 1.0, grid.shape)
    rhs = rng.standard_normal(grid.shape)

    p_cg = np.asarray(solver_cg.solve(rhs, rho, dt=1e-3))
    p_ref = np.asarray(solver_ref.solve(rhs, rho, dt=1e-3))

    assert solver_cg.allow_direct_fallback is False
    np.testing.assert_allclose(p_cg, p_ref, rtol=1e-8, atol=1e-9)


def test_factory_creates_fvm_iterative_solver():
    backend = Backend(use_gpu=False)
    cfg = _make_cfg(8)
    grid = Grid(cfg.grid, backend)

    solver = create_ppe_solver(cfg, backend, grid)
    assert isinstance(solver, PPESolverFVMMatrixFree)


def test_fvm_matrixfree_update_grid_refreshes_spacing_cache():
    backend = Backend(use_gpu=False)
    cfg = _make_cfg(8)
    grid = Grid(cfg.grid, backend)
    solver = PPESolverFVMMatrixFree(backend, None, grid, bc_type="wall")

    old_h_min = solver._h_min
    grid.coords[0] = grid.coords[0] ** 1.2
    solver.update_grid(grid)

    assert solver._h_min != old_h_min
    assert solver._operator_coeffs is None
    assert solver._precond_coeffs is None
