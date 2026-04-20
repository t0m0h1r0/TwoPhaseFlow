"""
Tests for FCCDConvectionTerm — CHK-158 V8/V9.

V8: TGV agreement — FCCDConvectionTerm vs ConvectionTerm on smooth
    Taylor–Green vortex; both agree to O(H^2) (base accuracy of node-CCD
    at interior), and Option C refines to O(H^4) at high resolution.

V9: AB2 buffer compatibility — output is a list of ndim arrays matching
    grid.shape; values finite.
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
from twophase.ns_terms.convection import ConvectionTerm
from twophase.ns_terms.fccd_convection import FCCDConvectionTerm


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def make_grid(N: int, backend, L: float = 1.0):
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(L, L)))
    return Grid(cfg.grid, backend)


def tgv(grid, L=1.0):
    X, Y = grid.meshgrid()
    u = np.sin(np.pi * X / L) * np.cos(np.pi * Y / L)
    v = -np.cos(np.pi * X / L) * np.sin(np.pi * Y / L)
    return u, v


def tgv_exact_conv(grid, L=1.0):
    """Exact −(u·∇)u for TGV: (−(π/L) sin(2πx/L) cos²(πy/L) + π sin²·cos·...).

    Closed form: u = sin(πX) cos(πY), v = -cos(πX) sin(πY) (L=1).
      u·∇u = u ∂u/∂x + v ∂u/∂y
           = π sin(πX) cos²(πY) cos(πX) − π cos²(πX) sin(πY)(−sin(πY))·...

    Easier: for L=1, TGV ω = π, and exact −(u·∇)u = (0.5 π sin(2πX), −0.5 π sin(2πY))
    ... actually that's for the 4π-periodic version; here we use the analytic form:
      − u · ∂u/∂x − v · ∂u/∂y
      ∂u/∂x = π cos(πX) cos(πY), ∂u/∂y = −π sin(πX) sin(πY)
      − u ∂u/∂x = − π sin(πX) cos(πY) · cos(πX) cos(πY) = −π/2 sin(2πX)/2 cos²(πY) · 2
                = − (π/2) sin(2πX) cos²(πY)
      − v ∂u/∂y = − (−cos(πX) sin(πY)) · (−π sin(πX) sin(πY))
                = − π cos(πX) sin(πX) sin²(πY) = − (π/2) sin(2πX) sin²(πY)
      Sum: − (π/2) sin(2πX) [cos² + sin²](πY) = − (π/2) sin(2πX)
    """
    X, Y = grid.meshgrid()
    cx = -0.5 * np.pi * np.sin(2 * np.pi * X / L)
    cy = -0.5 * np.pi * np.sin(2 * np.pi * Y / L)
    # By symmetry: −(u·∇)v = + (π/2) sin(2πY).
    return cx, cy


def _interior(arr, pad=2):
    """Drop ``pad`` boundary nodes on each side along both spatial axes."""
    return arr[pad:-pad, pad:-pad]


# ── V8: TGV agreement between ConvectionTerm and FCCDConvectionTerm ──────
# TGV u=sin(πX)cos(πY), v=-cos(πX)sin(πY) vanishes on {x=0,1}; wall BC fits.
# Interior nodes avoid boundary one-sided stencils.

@pytest.mark.parametrize("mode", ["node", "flux"])
def test_tgv_agreement_vs_baseline(mode, backend):
    """FCCD and CCD convection agree on TGV in the interior."""
    N = 64
    L = 1.0
    grid = make_grid(N, backend, L=L)

    u, v = tgv(grid, L=L)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    fccd = FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd)

    base = ConvectionTerm(backend)
    fccd_term = FCCDConvectionTerm(backend, fccd, mode=mode)

    rhs_base = base.compute([u, v], ccd)
    rhs_fccd = fccd_term.compute([u, v])

    diff_u = float(np.max(np.abs(_interior(rhs_base[0]) - _interior(rhs_fccd[0]))))
    diff_v = float(np.max(np.abs(_interior(rhs_base[1]) - _interior(rhs_fccd[1]))))
    assert diff_u < 0.15, (
        f"mode={mode}: u-component diverges from CCD in interior: {diff_u}"
    )
    assert diff_v < 0.15, (
        f"mode={mode}: v-component diverges from CCD in interior: {diff_v}"
    )


@pytest.mark.parametrize("mode", ["node", "flux"])
def test_tgv_accuracy_vs_exact(mode, backend):
    """FCCD convection matches the exact TGV RHS in the interior."""
    L = 1.0
    errs = []
    for N in [32, 64, 128]:
        grid = make_grid(N, backend, L=L)
        u, v = tgv(grid, L=L)
        fccd = FCCDSolver(grid, backend, bc_type="wall")
        term = FCCDConvectionTerm(backend, fccd, mode=mode)
        rhs = term.compute([u, v])

        ex_u, ex_v = tgv_exact_conv(grid, L=L)
        err = float(max(
            np.max(np.abs(_interior(rhs[0]) - _interior(ex_u))),
            np.max(np.abs(_interior(rhs[1]) - _interior(ex_v))),
        ))
        errs.append(err)
    ratios = [errs[i] / errs[i + 1] for i in range(len(errs) - 1)]
    # At least O(H²) in interior; Option C/flux typically hit higher.
    assert ratios[-1] > 3.5, (
        f"mode={mode}: FCCD convection must converge (≥ O(H²)) in interior: "
        f"errs={errs}, ratios={ratios}"
    )


# ── V9: AB2 buffer shape compatibility ───────────────────────────────────

@pytest.mark.parametrize("mode", ["node", "flux"])
def test_ab2_buffer_shape(mode, backend):
    """Output list layout matches ConvectionTerm (same ndim, same shapes)."""
    N = 16
    grid = make_grid(N, backend, L=1.0)
    u, v = tgv(grid, L=1.0)
    fccd = FCCDSolver(grid, backend, bc_type="periodic")
    term = FCCDConvectionTerm(backend, fccd, mode=mode)

    out = term.compute([u, v])
    assert isinstance(out, list) and len(out) == 2
    for arr in out:
        assert arr.shape == grid.shape
        assert np.all(np.isfinite(arr))


def test_fccd_convection_invalid_mode(backend):
    """Constructor rejects unknown mode."""
    grid = make_grid(8, backend, L=1.0)
    fccd = FCCDSolver(grid, backend, bc_type="wall")
    with pytest.raises(ValueError, match="mode must be"):
        FCCDConvectionTerm(backend, fccd, mode="weno5")
