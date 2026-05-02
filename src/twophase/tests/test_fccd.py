"""
Tests for the FCCD (face-centered CCD) solver — CHK-158.

Verified properties:
  V1  face_gradient        : O(H^4) convergence, uniform periodic.
  V2  periodic_symbol      : DFT leading truncation coefficient = -7/5760.
  V3  face_value           : O(H^4) face-value interpolation convergence.
  V4  node_gradient (R_4)  : O(H^4) node gradient via Hermite reconstruction.
  V5  wall Option III      : face_divergence zero at boundary nodes.
  V6  wall Option IV       : face_value = 0 at first face when Dirichlet u_wall=0.
  V7  periodic nonuniform  : face_divergence uses nodal control-volume width.
"""

import numpy as np
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def make_grid(N: int, backend, L: float = 1.0, ndim: int = 2):
    """Build an N x 4 (or N x 4 x 4) grid of length L along axis 0."""
    other_N = tuple([4] * (ndim - 1))
    other_L = tuple([1.0] * (ndim - 1))
    cfg = SimulationConfig(
        grid=GridConfig(ndim=ndim, N=(N,) + other_N, L=(L,) + other_L)
    )
    return Grid(cfg.grid, backend)


def _face_coords(coords):
    """Cell-centered face coordinates (N,) from node coordinates (N+1,)."""
    return 0.5 * (coords[:-1] + coords[1:])


# ── V1: face_gradient O(H^4) uniform periodic ────────────────────────────

@pytest.mark.parametrize("N", [16, 32, 64, 128])
def test_face_gradient_order_periodic(N, backend):
    """Periodic f = sin(2πx) face gradient: error decreases with N."""
    L = 1.0
    grid = make_grid(N, backend, L=L)
    fccd = FCCDSolver(grid, backend, bc_type="periodic")

    x = np.asarray(grid.coords[0])
    f = np.sin(2 * np.pi * x)
    f2d = np.broadcast_to(f[:, None], (N + 1, 5)).copy()

    d_face = fccd.face_gradient(f2d, axis=0)
    x_face = _face_coords(x)
    df_exact = 2 * np.pi * np.cos(2 * np.pi * x_face)

    err = float(np.max(np.abs(d_face[:, 2] - df_exact)))
    # Very loose bound; precise O(H^4) is checked by the convergence test.
    assert err < 10.0 / N


def test_face_gradient_convergence_rate(backend):
    """Face gradient O(H^4): err(N) / err(2N) ≈ 16 at high resolution."""
    Ns = [16, 32, 64, 128]
    errs = []
    for N in Ns:
        L = 1.0
        grid = make_grid(N, backend, L=L)
        fccd = FCCDSolver(grid, backend, bc_type="periodic")
        x = np.asarray(grid.coords[0])
        f = np.sin(2 * np.pi * x)
        f2d = np.broadcast_to(f[:, None], (N + 1, 5)).copy()
        d_face = fccd.face_gradient(f2d, axis=0)
        x_face = _face_coords(x)
        df_exact = 2 * np.pi * np.cos(2 * np.pi * x_face)
        errs.append(float(np.max(np.abs(d_face[:, 2] - df_exact))))

    ratios = [errs[i] / errs[i + 1] for i in range(len(errs) - 1)]
    assert ratios[-1] > 12.0, (
        f"Face gradient must converge at least O(H^4): ratios={ratios}"
    )


# ── V2: Periodic DFT leading coefficient −7/5760 ─────────────────────────

def test_periodic_symbol_leading_coefficient(backend):
    """Numerical DFT of face gradient matches symbol iω·[1 − 7(ωH)^4/5760]."""
    N = 64
    L = 1.0
    H = L / N
    grid = make_grid(N, backend, L=L)
    fccd = FCCDSolver(grid, backend, bc_type="periodic")

    x = np.asarray(grid.coords[0])
    x_face = _face_coords(x)

    # Low-frequency mode m: f(x) = cos(2π m x / L).
    # Choose m = 4 so ωH = 2πm/N = π/8 ≈ 0.393; (ωH)^4 ≈ 2.37e-2.
    m = 4
    omega = 2 * np.pi * m / L
    f = np.cos(omega * x)
    f2d = np.broadcast_to(f[:, None], (N + 1, 5)).copy()

    d_face = fccd.face_gradient(f2d, axis=0)
    df_exact = -omega * np.sin(omega * x_face)   # analytic gradient at face

    # Leading truncation: relative error ≈ -7(ωH)^4/5760 (purely real amplitude).
    # Evaluate at a point where df_exact is largest (sin = ±1).
    idx = int(np.argmax(np.abs(df_exact)))
    ratio = float(d_face[idx, 2] / df_exact[idx]) - 1.0

    predicted = -7.0 * (omega * H) ** 4 / 5760.0
    rel = abs(ratio - predicted) / abs(predicted)
    assert rel < 0.05, (
        f"Leading truncation coefficient off: measured={ratio:.6e}, "
        f"predicted={predicted:.6e}, rel_err={rel:.3e}"
    )


def test_periodic_symbol_analytic_form(backend):
    """FCCDSolver.periodic_symbol() returns the documented leading form."""
    grid = make_grid(32, backend, L=1.0)
    fccd = FCCDSolver(grid, backend, bc_type="periodic")
    H = 1.0 / 32
    omega = 2 * np.pi
    val = fccd.periodic_symbol(omega, axis=0)
    expected = 1j * omega * (1.0 - 7.0 * (omega * H) ** 4 / 5760.0)
    assert abs(val - expected) < 1e-14


# ── V3: face_value O(H^4) ────────────────────────────────────────────────

def test_face_value_convergence_rate(backend):
    """Face-value interpolation converges at O(H^4)."""
    Ns = [16, 32, 64, 128]
    errs = []
    for N in Ns:
        L = 1.0
        grid = make_grid(N, backend, L=L)
        fccd = FCCDSolver(grid, backend, bc_type="periodic")
        x = np.asarray(grid.coords[0])
        f = np.sin(2 * np.pi * x)
        f2d = np.broadcast_to(f[:, None], (N + 1, 5)).copy()
        u_face = fccd.face_value(f2d, axis=0)
        x_face = _face_coords(x)
        u_exact = np.sin(2 * np.pi * x_face)
        errs.append(float(np.max(np.abs(u_face[:, 2] - u_exact))))

    ratios = [errs[i] / errs[i + 1] for i in range(len(errs) - 1)]
    assert ratios[-1] > 12.0, (
        f"Face value must converge at least O(H^4): ratios={ratios}"
    )


# ── V3b: face jet and Taylor-HFE upwind state ────────────────────────────

def test_face_jet_matches_existing_primitives(backend):
    """face_jet exposes the existing face_value and face_gradient operators."""
    N = 32
    grid = make_grid(N, backend, L=1.0)
    fccd = FCCDSolver(grid, backend, bc_type="periodic")

    x = np.asarray(grid.coords[0])
    field = np.sin(2 * np.pi * x)
    field_2d = np.broadcast_to(field[:, None], (N + 1, 5)).copy()

    jet = fccd.face_jet(field_2d, axis=0)

    assert np.allclose(jet.value, fccd.face_value(field_2d, axis=0))
    assert np.allclose(jet.gradient, fccd.face_gradient(field_2d, axis=0))
    assert jet.curvature.shape == jet.value.shape


def test_face_second_derivative_convergence_rate(backend):
    """Face-carried q_f converges at second order for smooth periodic fields."""
    Ns = [32, 64, 128, 256]
    errs = []
    for N in Ns:
        grid = make_grid(N, backend, L=1.0)
        fccd = FCCDSolver(grid, backend, bc_type="periodic")
        x = np.asarray(grid.coords[0])
        field = np.sin(2 * np.pi * x)
        field_2d = np.broadcast_to(field[:, None], (N + 1, 5)).copy()

        q_face = fccd.face_second_derivative(field_2d, axis=0)
        x_face = _face_coords(x)
        exact = -(2 * np.pi) ** 2 * np.sin(2 * np.pi * x_face)
        errs.append(float(np.max(np.abs(q_face[:, 2] - exact))))

    ratios = [errs[i] / errs[i + 1] for i in range(len(errs) - 1)]
    assert ratios[-1] > 3.5, (
        f"Face second derivative bridge must converge at O(H^2): ratios={ratios}"
    )


@pytest.mark.parametrize("velocity_sign", [1.0, -1.0])
def test_upwind_face_value_taylor_hfe_order(velocity_sign, backend):
    """Directional Taylor-HFE face state converges at third order."""
    Ns = [32, 64, 128, 256]
    errs = []
    for N in Ns:
        grid = make_grid(N, backend, L=1.0)
        fccd = FCCDSolver(grid, backend, bc_type="periodic")
        x = np.asarray(grid.coords[0])
        field = np.sin(2 * np.pi * x)
        field_2d = np.broadcast_to(field[:, None], (N + 1, 5)).copy()
        velocity_face = np.full((N, 5), velocity_sign)

        upwind = fccd.upwind_face_value(field_2d, velocity_face, axis=0)
        exact = np.sin(2 * np.pi * _face_coords(x))
        errs.append(float(np.max(np.abs(upwind[:, 2] - exact))))

    ratios = [errs[i] / errs[i + 1] for i in range(len(errs) - 1)]
    assert ratios[-1] > 7.0, (
        f"Taylor-HFE upwind state must converge at O(H^3): ratios={ratios}"
    )


# ── V4: node_gradient R_4 O(H^4) ─────────────────────────────────────────

def test_node_gradient_hermite_order(backend):
    """R_4 Hermite node reconstructor converges at O(H^4) interior."""
    Ns = [16, 32, 64, 128]
    errs = []
    for N in Ns:
        L = 1.0
        grid = make_grid(N, backend, L=L)
        fccd = FCCDSolver(grid, backend, bc_type="periodic")
        x = np.asarray(grid.coords[0])
        f = np.sin(2 * np.pi * x)
        f2d = np.broadcast_to(f[:, None], (N + 1, 5)).copy()
        dnode = fccd.node_gradient(f2d, axis=0)
        df_exact = 2 * np.pi * np.cos(2 * np.pi * x)
        errs.append(float(np.max(np.abs(dnode[:, 2] - df_exact))))

    ratios = [errs[i] / errs[i + 1] for i in range(len(errs) - 1)]
    assert ratios[-1] > 12.0, (
        f"R_4 node gradient must converge at least O(H^4): ratios={ratios}"
    )


def test_node_gradient_wall_bc_interior_order(backend):
    """Interior nodes (1..N-1) with wall BC still converge at O(H^4)."""
    Ns = [32, 64, 128]
    errs = []
    for N in Ns:
        L = 1.0
        grid = make_grid(N, backend, L=L)
        fccd = FCCDSolver(grid, backend, bc_type="wall")
        x = np.asarray(grid.coords[0])
        # Use a function with trivial boundary layer so interior is smooth.
        f = np.sin(np.pi * x)   # vanishes at x=0,1
        f2d = np.broadcast_to(f[:, None], (N + 1, 5)).copy()
        dnode = fccd.node_gradient(f2d, axis=0)
        df_exact = np.pi * np.cos(np.pi * x)
        # Interior max (drop first + last where R_4 is one-sided).
        err = float(np.max(np.abs(dnode[1:-1, 2] - df_exact[1:-1])))
        errs.append(err)
    ratios = [errs[i] / errs[i + 1] for i in range(len(errs) - 1)]
    assert ratios[-1] > 12.0, (
        f"Interior node gradient (wall) must be O(H^4): ratios={ratios}"
    )


# ── V5: Wall Option III (Neumann ψ, p) face_divergence boundary zero ─────

def test_wall_option_iii_boundary_zero(backend):
    """face_divergence output is zero at boundary nodes on wall BC."""
    N = 32
    grid = make_grid(N, backend, L=1.0)
    fccd = FCCDSolver(grid, backend, bc_type="wall")

    # Build an arbitrary face array — divergence boundary nodes must still be 0.
    x = np.asarray(grid.coords[0])
    u = np.cos(np.pi * x) ** 2
    u2d = np.broadcast_to(u[:, None], (N + 1, 5)).copy()
    u_face = fccd.face_value(u2d, axis=0)

    div = fccd.face_divergence(u_face, axis=0)

    # Option III convention: boundary nodes of face_divergence are zero.
    assert np.allclose(div[0, :], 0.0), "Left boundary divergence must be 0"
    assert np.allclose(div[-1, :], 0.0), "Right boundary divergence must be 0"


def test_periodic_nonuniform_face_divergence_uses_control_volume_width(backend):
    """Periodic nonuniform divergence divides by nodal control-volume width."""
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(3, 4), L=(1.0, 1.0), alpha_grid=2.0)
    )
    grid = Grid(cfg.grid, backend)
    grid.coords[0] = np.asarray([0.0, 0.2, 0.7, 1.0])
    fccd = FCCDSolver(grid, backend, bc_type="periodic")

    flux_axis = np.asarray([10.0, 13.0, 4.0])
    face_flux = np.broadcast_to(flux_axis[:, None], (3, 5)).copy()
    div = np.asarray(fccd.face_divergence(face_flux, axis=0))

    widths = np.asarray([0.25, 0.35, 0.4])
    expected_axis = np.asarray([
        (flux_axis[0] - flux_axis[2]) / widths[0],
        (flux_axis[1] - flux_axis[0]) / widths[1],
        (flux_axis[2] - flux_axis[1]) / widths[2],
        (flux_axis[0] - flux_axis[2]) / widths[0],
    ])
    np.testing.assert_allclose(div, np.broadcast_to(expected_axis[:, None], div.shape))


# ── V6: Wall Option IV (Dirichlet u no-slip) ─────────────────────────────

def test_wall_option_iv_face_value_consistency(backend):
    """For u with u(0)=u(L)=0, face_value interpolation is O(H^4) in interior,
    with O(H^2) boundary faces (first/last). Global error decays with N."""
    errs = []
    for N in [32, 64, 128]:
        L = 1.0
        grid = make_grid(N, backend, L=L)
        fccd = FCCDSolver(grid, backend, bc_type="wall")

        x = np.asarray(grid.coords[0])
        u = np.sin(np.pi * x / L)     # exactly zero at walls
        u2d = np.broadcast_to(u[:, None], (N + 1, 5)).copy()
        u_face = fccd.face_value(u2d, axis=0)

        x_face = _face_coords(x)
        u_exact = np.sin(np.pi * x_face / L)
        # Interior faces only (exclude first + last boundary face).
        err = float(np.max(np.abs(u_face[1:-1, 2] - u_exact[1:-1])))
        errs.append(err)
    ratios = [errs[i] / errs[i + 1] for i in range(len(errs) - 1)]
    # Interior is O(H^4); ratio should exceed 12 at sufficient resolution.
    assert ratios[-1] > 12.0, (
        f"Option IV interior face_value must be O(H^4): ratios={ratios}"
    )


def test_wall_option_iv_face_gradient_nonzero_shear(backend):
    """d_f at first interior face is the physical shear rate, not zero."""
    N = 32
    L = 1.0
    grid = make_grid(N, backend, L=L)
    fccd = FCCDSolver(grid, backend, bc_type="wall")

    x = np.asarray(grid.coords[0])
    u = np.sin(np.pi * x / L)
    u2d = np.broadcast_to(u[:, None], (N + 1, 5)).copy()

    d_face = fccd.face_gradient(u2d, axis=0)
    x_face = _face_coords(x)
    d_exact = (np.pi / L) * np.cos(np.pi * x_face / L)

    # First face near x=0: analytic shear ≈ π/L; must not be zero, must match.
    assert abs(d_face[0, 2] - d_exact[0]) < 2e-2, (
        "Wall BC face gradient at near-wall face must match physical shear"
    )
    assert abs(d_face[0, 2]) > 1.0, "Shear at wall must be non-zero"


# ── Smoke: advection_rhs integrates without shape errors ─────────────────

@pytest.mark.parametrize("mode", ["node", "flux"])
def test_advection_rhs_momentum_shape(mode, backend):
    """advection_rhs returns a list of ndim arrays matching grid shape."""
    N = 16
    grid = make_grid(N, backend, L=1.0, ndim=2)
    fccd = FCCDSolver(grid, backend, bc_type="wall")

    X, Y = grid.meshgrid()
    u = np.sin(np.pi * X) * np.cos(np.pi * Y)
    v = -np.cos(np.pi * X) * np.sin(np.pi * Y)   # divergence-free TGV

    rhs = fccd.advection_rhs([u, v], mode=mode)
    assert len(rhs) == 2
    assert rhs[0].shape == grid.shape
    assert rhs[1].shape == grid.shape
    assert np.all(np.isfinite(rhs[0])) and np.all(np.isfinite(rhs[1]))


@pytest.mark.parametrize("mode", ["node", "flux"])
def test_advection_rhs_scalar_shape(mode, backend):
    """advection_rhs scalar form returns a 1-element list."""
    N = 16
    grid = make_grid(N, backend, L=1.0, ndim=2)
    fccd = FCCDSolver(grid, backend, bc_type="wall")

    X, Y = grid.meshgrid()
    u = np.ones_like(X)
    v = np.zeros_like(X)
    psi = np.exp(-((X - 0.5) ** 2 + (Y - 0.5) ** 2) / 0.05)

    rhs = fccd.advection_rhs([u, v], scalar=psi, mode=mode)
    assert len(rhs) == 1
    assert rhs[0].shape == grid.shape
    assert np.all(np.isfinite(rhs[0]))
