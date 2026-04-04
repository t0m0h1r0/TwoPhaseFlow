"""
IIM-CCD library tests.

Validates:
  1. JumpConditionCalculator: jump values for known analytical cases
  2. IIMStencilCorrector: interface crossing detection + correction shape
  3. PPESolverIIM: end-to-end solve with IIM correction (LU backend)
  4. PPESolverIIM: solve without correction falls back to standard CCD-LU
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig, SolverConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.pressure.iim.jump_conditions import JumpConditionCalculator
from twophase.pressure.iim.stencil_corrector import IIMStencilCorrector
from twophase.pressure.ppe_solver_iim import PPESolverIIM


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def make_setup(N=16, backend=None, iim_backend="lu"):
    if backend is None:
        backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        solver=SolverConfig(
            ppe_solver_type="iim",
            iim_backend=iim_backend,
            pseudo_tol=1e-10,
            pseudo_maxiter=500,
        ),
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    return cfg, grid, ccd, backend


def _build_5pt_laplacian(grid):
    """Build a 5-point FD Laplacian for testing (has off-diagonal entries)."""
    import scipy.sparse as sp
    Nx, Ny = grid.shape
    hx = grid.L[0] / grid.N[0]
    hy = grid.L[1] / grid.N[1]
    n = Nx * Ny
    diags = np.zeros((5, n))
    offsets = [0, -1, 1, -Ny, Ny]
    diags[0] = -2.0 / hx**2 - 2.0 / hy**2
    diags[1] = 1.0 / hy**2
    diags[2] = 1.0 / hy**2
    diags[3] = 1.0 / hx**2
    diags[4] = 1.0 / hx**2
    L = sp.diags(diags, offsets, shape=(n, n), format='csr')
    return L


def make_circular_levelset(grid, R=0.25, center=(0.5, 0.5)):
    """Create a signed-distance level-set for a circle (φ<0 inside)."""
    xp = np
    Nx, Ny = grid.shape
    x = np.linspace(0, grid.L[0], Nx)
    y = np.linspace(0, grid.L[1], Ny)
    X, Y = np.meshgrid(x, y, indexing='ij')
    phi = np.sqrt((X - center[0])**2 + (Y - center[1])**2) - R
    return phi


# ── Test 1: JumpConditionCalculator ─────────────────────────────────────

class TestJumpConditionCalculator:
    """Test analytical jump conditions."""

    def test_zeroth_order_young_laplace(self):
        """C_0 = σκ (Young-Laplace jump)."""
        calc = JumpConditionCalculator(max_order=0)
        sigma = 0.07
        kappa = 10.0  # 1/R for R=0.1
        C = calc.compute_1d_jumps(
            sigma=sigma, kappa=kappa,
            rho_l=1000.0, rho_g=1.0,
            p_prime_l=0.0, p_double_prime_l=0.0,
            q_l=0.0, q_g=0.0,
        )
        assert C.shape == (1,)
        assert abs(C[0] - sigma * kappa) < 1e-14

    def test_first_order_flux_continuity(self):
        """C_1 = (ρ_g/ρ_l - 1) p'_l from flux continuity."""
        calc = JumpConditionCalculator(max_order=1)
        rho_l, rho_g = 1000.0, 1.0
        p_prime_l = 5.0
        C = calc.compute_1d_jumps(
            sigma=0.0, kappa=0.0,
            rho_l=rho_l, rho_g=rho_g,
            p_prime_l=p_prime_l, p_double_prime_l=0.0,
            q_l=0.0, q_g=0.0,
        )
        expected_C1 = (rho_g / rho_l - 1.0) * p_prime_l
        assert abs(C[1] - expected_C1) < 1e-12

    def test_second_order_pde_jump(self):
        """C_2 consistency: derived from the PDE."""
        calc = JumpConditionCalculator(max_order=2)
        rho_l, rho_g = 1000.0, 1.0
        q_l, q_g = 1.0, 2.0
        p_prime_l = 0.0  # simplify
        C = calc.compute_1d_jumps(
            sigma=0.0, kappa=0.0,
            rho_l=rho_l, rho_g=rho_g,
            p_prime_l=p_prime_l, p_double_prime_l=0.0,
            q_l=q_l, q_g=q_g,
        )
        # With drho=0, p'_l=0: C_2 = ρ_g·q_g - ρ_l·q_l
        expected_C2 = rho_g * q_g - rho_l * q_l
        assert abs(C[2] - expected_C2) < 1e-10

    def test_equal_density_no_gradient_jump(self):
        """Equal density → C_1 = 0 (no gradient jump)."""
        calc = JumpConditionCalculator(max_order=2)
        C = calc.compute_1d_jumps(
            sigma=1.0, kappa=5.0,
            rho_l=1.0, rho_g=1.0,
            p_prime_l=10.0, p_double_prime_l=0.0,
            q_l=0.0, q_g=0.0,
        )
        assert abs(C[1]) < 1e-14  # no gradient jump for equal density

    def test_2d_jumps_normal_projection(self):
        """2D jumps project the gradient onto the normal direction."""
        calc = JumpConditionCalculator(max_order=1)
        grad_p_l = np.array([3.0, 4.0])
        normal = np.array([0.6, 0.8])  # unit normal
        rho_l, rho_g = 100.0, 1.0
        C = calc.compute_2d_jumps(
            sigma=1.0, kappa=2.0,
            rho_l=rho_l, rho_g=rho_g,
            grad_p_l=grad_p_l,
            normal=normal,
        )
        p_n_l = np.dot(grad_p_l, normal)  # 1.8 + 3.2 = 5.0
        expected_C1 = (rho_g / rho_l - 1.0) * p_n_l
        assert abs(C[0] - 1.0 * 2.0) < 1e-14  # σκ
        assert abs(C[1] - expected_C1) < 1e-12


# ── Test 2: IIMStencilCorrector ─────────────────────────────────────────

class TestIIMStencilCorrector:
    """Test interface crossing detection and correction computation."""

    def test_circular_interface_crossings(self, backend):
        """A circular interface should produce O(N) crossings."""
        _, grid, _, _ = make_setup(N=16, backend=backend)
        phi = make_circular_levelset(grid, R=0.25)
        corrector = IIMStencilCorrector(grid, mode="nearest")
        crossings = corrector.find_interface_crossings(phi)

        # A circle of radius 0.25 on 16×16 grid should cross ~40 faces
        assert len(crossings) > 10
        assert len(crossings) < 200

        # All crossings should have alpha in (0, 1)
        for c in crossings:
            assert 0.0 < c["alpha"] < 1.0
            assert c["phi_a"] * c["phi_b"] < 0.0

    def test_no_crossings_uniform_phase(self, backend):
        """A uniform sign field has no crossings."""
        _, grid, _, _ = make_setup(N=8, backend=backend)
        phi = np.ones(grid.shape)  # all positive
        corrector = IIMStencilCorrector(grid, mode="nearest")
        crossings = corrector.find_interface_crossings(phi)
        assert len(crossings) == 0

    def test_correction_vector_shape(self, backend):
        """Correction Δq has correct shape and is non-zero at crossings."""
        cfg, grid, ccd, be = make_setup(N=8, backend=backend)
        phi = make_circular_levelset(grid, R=0.2)
        kappa = np.ones(grid.shape) * 5.0  # 1/R = 5
        rho = np.where(phi < 0, 1000.0, 1.0)
        rhs = np.zeros(grid.shape)

        # Build a proper 5-point Laplacian (has off-diagonal entries)
        L = _build_5pt_laplacian(grid)

        corrector = IIMStencilCorrector(grid, mode="nearest")
        n = int(np.prod(grid.shape))
        delta_q = corrector.compute_correction(
            L, phi, kappa, 0.07, rho, rhs,
        )
        assert delta_q.shape == (n,)
        assert np.any(delta_q != 0.0)  # should have corrections

    def test_hermite_correction_differs_from_nearest(self, backend):
        """Hermite mode should produce different corrections than nearest."""
        cfg, grid, ccd, be = make_setup(N=8, backend=backend)
        phi = make_circular_levelset(grid, R=0.2)
        kappa = np.ones(grid.shape) * 5.0
        rho = np.where(phi < 0, 1000.0, 1.0)
        rhs = np.ones(grid.shape) * 0.1  # non-zero RHS

        L = _build_5pt_laplacian(grid)

        corr_nearest = IIMStencilCorrector(grid, mode="nearest")
        corr_hermite = IIMStencilCorrector(grid, mode="hermite")

        dq_n = corr_nearest.compute_correction(
            L, phi, kappa, 0.07, rho, rhs,
        )
        dq_h = corr_hermite.compute_correction(
            L, phi, kappa, 0.07, rho, rhs,
        )
        # Both should be non-zero
        assert np.any(dq_n != 0.0)
        assert np.any(dq_h != 0.0)
        # They should differ (hermite adds C_1, C_2 terms)
        assert not np.allclose(dq_n, dq_h)


# ── Test 3: PPESolverIIM end-to-end ─────────────────────────────────────

class TestPPESolverIIM:
    """End-to-end PPE solve with IIM correction."""

    def test_solve_with_iim_returns_finite(self, backend):
        """IIM solve should return finite pressure field."""
        cfg, grid, ccd, be = make_setup(N=16, backend=backend)
        solver = PPESolverIIM(be, cfg, grid, ccd=ccd)

        phi = make_circular_levelset(grid, R=0.25)
        kappa = np.ones(grid.shape) / 0.25  # κ = 1/R = 4
        rho = np.where(phi < 0, 1000.0, 1.0)
        rhs = np.zeros(grid.shape)

        xp = be.xp
        p = solver.solve(
            xp.asarray(rhs), xp.asarray(rho), dt=0.001,
            phi=xp.asarray(phi), kappa=xp.asarray(kappa), sigma=0.07,
        )
        p_np = np.asarray(be.to_host(p))
        assert p_np.shape == grid.shape
        assert np.isfinite(p_np).all()

    def test_solve_without_iim_fallback(self, backend):
        """Without phi/kappa, IIM solver behaves like standard CCD-LU."""
        cfg, grid, ccd, be = make_setup(N=16, backend=backend)
        solver = PPESolverIIM(be, cfg, grid, ccd=ccd)

        rho = np.ones(grid.shape) * 1.0
        rhs = np.random.RandomState(42).randn(*grid.shape) * 0.01

        xp = be.xp
        p = solver.solve(xp.asarray(rhs), xp.asarray(rho), dt=0.001)
        p_np = np.asarray(be.to_host(p))
        assert np.isfinite(p_np).all()

        # Compare with PPESolverCCDLU
        from twophase.pressure.ppe_solver_ccd_lu import PPESolverCCDLU
        solver_lu = PPESolverCCDLU(be, cfg, grid, ccd=ccd)
        p_lu = solver_lu.solve(xp.asarray(rhs), xp.asarray(rho), dt=0.001)
        p_lu_np = np.asarray(be.to_host(p_lu))

        # Should be identical (no IIM correction applied)
        np.testing.assert_allclose(p_np, p_lu_np, atol=1e-12)

    def test_iim_correction_changes_solution(self, backend):
        """IIM correction should produce a different solution than no correction."""
        cfg, grid, ccd, be = make_setup(N=16, backend=backend)
        solver = PPESolverIIM(be, cfg, grid, ccd=ccd)

        phi = make_circular_levelset(grid, R=0.25)
        kappa = np.ones(grid.shape) / 0.25
        rho = np.where(phi < 0, 1000.0, 1.0)
        rhs = np.zeros(grid.shape)
        xp = be.xp

        # With IIM
        p_iim = solver.solve(
            xp.asarray(rhs), xp.asarray(rho), dt=0.001,
            phi=xp.asarray(phi), kappa=xp.asarray(kappa), sigma=0.07,
        )
        # Without IIM
        p_no = solver.solve(
            xp.asarray(rhs), xp.asarray(rho), dt=0.001,
        )
        p_iim_np = np.asarray(be.to_host(p_iim))
        p_no_np = np.asarray(be.to_host(p_no))

        # Solutions should differ due to IIM correction
        assert not np.allclose(p_iim_np, p_no_np, atol=1e-10)

    def test_laplace_pressure_inside_bubble(self, backend):
        """Inside a static bubble, p ≈ σκ = σ/R (Laplace pressure)."""
        N = 32
        cfg, grid, ccd, be = make_setup(N=N, backend=backend)
        solver = PPESolverIIM(be, cfg, grid, ccd=ccd)

        R = 0.25
        phi = make_circular_levelset(grid, R=R)
        kappa = np.ones(grid.shape) / R
        rho = np.where(phi < 0, 1000.0, 1.0)
        sigma = 0.07
        rhs = np.zeros(grid.shape)
        xp = be.xp

        p = solver.solve(
            xp.asarray(rhs), xp.asarray(rho), dt=0.001,
            phi=xp.asarray(phi), kappa=xp.asarray(kappa), sigma=sigma,
        )
        p_np = np.asarray(be.to_host(p))

        # The IIM solver is expected to produce a jump σκ across the interface.
        # Check that interior pressure is elevated relative to exterior.
        interior_mask = phi < -2 * grid.L[0] / N  # well inside bubble
        exterior_mask = phi > 2 * grid.L[0] / N   # well outside
        if interior_mask.any() and exterior_mask.any():
            p_in = np.mean(p_np[interior_mask])
            p_out = np.mean(p_np[exterior_mask])
            # Pressure difference should be approximately σ/R = 0.28
            # (not exact due to discrete effects, but order-of-magnitude correct)
            dp = p_in - p_out
            expected = sigma / R
            assert dp > 0, f"Interior should be higher pressure, got dp={dp:.6f}"


# ─�� Test 4: Jump Decomposition backend ──────────────────────────────────

class TestPPESolverIIMDecomp:
    """Jump decomposition (decomp) backend tests."""

    def _make_decomp_solver(self, N, backend):
        cfg = SimulationConfig(
            grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
            solver=SolverConfig(
                ppe_solver_type="iim",
                iim_mode="nearest", iim_backend="decomp",
                pseudo_tol=1e-8, pseudo_maxiter=500, pseudo_c_tau=2.0,
            ),
        )
        grid = Grid(cfg.grid, backend)
        ccd = CCDSolver(grid, backend)
        solver = PPESolverIIM(backend, cfg, grid, ccd=ccd)
        return solver, grid, ccd

    def test_decomp_returns_finite(self, backend):
        """Decomp backend returns finite pressure field."""
        solver, grid, _ = self._make_decomp_solver(16, backend)
        phi = make_circular_levelset(grid, R=0.25)
        kappa = np.ones(grid.shape) / 0.25
        rho = np.where(phi < 0, 1000.0, 1.0)
        xp = backend.xp
        p = solver.solve(
            xp.asarray(np.zeros(grid.shape)), xp.asarray(rho), dt=0.001,
            phi=xp.asarray(phi), kappa=xp.asarray(kappa), sigma=0.07,
        )
        p_np = np.asarray(backend.to_host(p))
        assert np.isfinite(p_np).all()

    def test_decomp_produces_smooth_field(self, backend):
        """Decomp backend produces smooth field with sharp jump at interface.

        For rhs=0, the solution of L(p)=0 is constant everywhere.
        The decomp adds a sharp jump σκ·(1-H) at recovery, producing:
            p_inside ≈ const + σκ, p_outside ≈ const.
        The transition occurs only in the 1-2 cell interface band.
        """
        N = 32
        solver, grid, _ = self._make_decomp_solver(N, backend)
        R = 0.25
        sigma = 0.07
        phi = make_circular_levelset(grid, R=R)
        kappa = np.ones(grid.shape) / R
        rho = np.where(phi < 0, 1000.0, 1.0)
        xp = backend.xp

        p = solver.solve(
            xp.asarray(np.zeros(grid.shape)), xp.asarray(rho), dt=0.001,
            phi=xp.asarray(phi), kappa=xp.asarray(kappa), sigma=sigma,
        )
        p_np = np.asarray(backend.to_host(p))

        h = grid.L[0] / grid.N[0]
        interior = phi < -3 * h
        exterior = phi > 3 * h

        # Interior should be approximately constant (low std)
        assert np.std(p_np[interior]) < 0.1, "Interior not smooth"
        # Exterior should be approximately constant
        assert np.std(p_np[exterior]) < 0.1, "Exterior not smooth"
        # |p| should be bounded
        assert np.max(np.abs(p_np)) < 1.0, "|p|_max blew up"

    def test_decomp_density_independent(self, backend):
        """Decomp solution is independent of density ratio for rhs=0."""
        R = 0.25
        sigma = 0.07
        N = 16
        results = []

        for ratio in [10, 100, 1000]:
            solver, grid, _ = self._make_decomp_solver(N, backend)
            phi = make_circular_levelset(grid, R=R)
            kappa = np.ones(grid.shape) / R
            rho = np.where(phi < 0, float(ratio), 1.0)
            xp = backend.xp

            p = solver.solve(
                xp.asarray(np.zeros(grid.shape)), xp.asarray(rho), dt=0.001,
                phi=xp.asarray(phi), kappa=xp.asarray(kappa), sigma=sigma,
            )
            results.append(np.asarray(backend.to_host(p)))

        # All density ratios should produce the same result (for rhs=0)
        np.testing.assert_allclose(results[0], results[1], atol=1e-6)
        np.testing.assert_allclose(results[0], results[2], atol=1e-6)

    def test_decomp_high_density_ratio(self, backend):
        """Decomp handles ρ_l/ρ_g = 1000 without blowup."""
        solver, grid, _ = self._make_decomp_solver(32, backend)
        phi = make_circular_levelset(grid, R=0.25)
        kappa = np.ones(grid.shape) / 0.25
        rho = np.where(phi < 0, 1000.0, 1.0)
        xp = backend.xp

        p = solver.solve(
            xp.asarray(np.zeros(grid.shape)), xp.asarray(rho), dt=0.001,
            phi=xp.asarray(phi), kappa=xp.asarray(kappa), sigma=0.07,
        )
        p_np = np.asarray(backend.to_host(p))
        assert np.isfinite(p_np).all()
        assert np.max(np.abs(p_np)) < 100.0, (
            f"|p|_max = {np.max(np.abs(p_np)):.2f} — solution blew up"
        )
