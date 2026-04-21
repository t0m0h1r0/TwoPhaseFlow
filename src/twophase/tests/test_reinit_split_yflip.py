"""CHK-168 regression — split-reinit y-flip equivariance.

Pre-CHK-168 the ``safe_grad`` floor in ``compute_gradient_normal`` was
``1e-14``, turning ULP-level ∂ψ/∂y noise at the fixed row (j=N/2) into
O(1e-3) noise in ``n̂_y`` → O(1e-6) y-flip asymmetry after one
``SplitReinitializer`` call on an α=2 stretched grid
(``ch13_04_sym_B_alpha2_split``).

Raising the floor to ``1e-6`` restores ULP equivariance for a single
inner iteration.  Composing 4 iterations still hits Lyapunov
amplification (ASM-122-A), but the operator itself is now
y-flip-equivariant at the single-iteration level on **any** grid.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from twophase.backend import Backend  # noqa: E402
from twophase.ccd.ccd_solver import CCDSolver  # noqa: E402
from twophase.config import GridConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.levelset.reinit_ops import (  # noqa: E402
    dccd_compression_div,
    cn_diffusion_axis,
    compute_gradient_normal,
)
from twophase.levelset.reinit_split import SplitReinitializer  # noqa: E402
from twophase.simulation.initial_conditions.shapes import PerturbedCircle  # noqa: E402


def _build(alpha_grid: float, N: int = 64):
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha_grid)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend)
    eps = 1.4 * 1.5 / N
    shape = PerturbedCircle(
        center=(0.5, 0.5), radius=0.25, epsilon=0.05, mode=2,
        interior_phase="liquid",
    )
    X, Y = grid.meshgrid()
    phi = shape.sdf(np.asarray(X), np.asarray(Y))
    psi0 = 0.5 * (1.0 - np.tanh(phi / (2.0 * eps)))
    grid.update_from_levelset(psi0, eps, ccd=ccd)
    X, Y = grid.meshgrid()
    phi = shape.sdf(np.asarray(X), np.asarray(Y))
    psi0 = 0.5 * (1.0 - np.tanh(phi / (2.0 * eps)))
    return backend, grid, ccd, eps, psi0


def _sym_err(arr: np.ndarray, axis: int) -> float:
    flip = np.flip(arr, axis=axis)
    denom = float(np.max(np.abs(arr)))
    if denom == 0.0:
        return 0.0
    return float(np.max(np.abs(arr - flip))) / denom


# ── core bug fix: safe_grad floor ───────────────────────────────────────


@pytest.mark.parametrize("alpha_grid", [1.0, 2.0])
def test_compute_gradient_normal_floor_is_1e6(alpha_grid):
    """CHK-168 fix: safe_grad floor must be 1e-6, not 1e-14."""
    _, grid, ccd, _, psi0 = _build(alpha_grid)
    _, _, safe_grad = compute_gradient_normal(np, psi0, ccd)
    assert float(np.min(safe_grad)) >= 1e-6 - 1e-20, (
        f"safe_grad min = {float(np.min(safe_grad)):.3e}, expected ≥ 1e-6 (CHK-168)"
    )


# ── per-operator y-flip equivariance (interior physics) ────────────────


@pytest.mark.parametrize("alpha_grid", [1.0, 2.0])
def test_dccd_compression_div_y_flip_equivariant(alpha_grid):
    """∇·[ψ(1-ψ)n̂] is EVEN under y-flip when input ψ is y-symmetric."""
    backend, grid, ccd, _, psi0 = _build(alpha_grid)
    div = dccd_compression_div(np, psi0, ccd, grid, "zero", 0.05)
    # EVEN parity: div(ψ) == flip_y(div(flip_y(ψ)))
    div_flipped = np.flip(
        dccd_compression_div(np, np.flip(psi0, axis=1), ccd, grid, "zero", 0.05),
        axis=1,
    )
    err = _sym_err(div - div_flipped, axis=1)
    # Core CCD + flux is ULP-equivariant; allow small headroom for FP rounding.
    assert np.max(np.abs(div - div_flipped)) / max(1.0, float(np.max(np.abs(div)))) < 1e-11, (
        f"dccd_compression_div y-flip err = "
        f"{np.max(np.abs(div - div_flipped))/max(1.0, float(np.max(np.abs(div)))):.3e}"
    )


# ── single-iteration reinit preserves y-flip symmetry ──────────────────


@pytest.mark.parametrize("alpha_grid", [1.0, 2.0])
def test_split_reinit_single_iteration_y_flip_equivariant(alpha_grid):
    """One inner iteration of split-reinit is y-flip equivariant to ULP.

    This is the direct target of CHK-168: pre-fix the α=2 case gave
    4.47e-6 y-flip err; post-fix it must be ≤ 1e-12.
    """
    backend, grid, ccd, eps, psi0 = _build(alpha_grid)
    reinit = SplitReinitializer(
        backend=backend, grid=grid, ccd=ccd, eps=eps,
        n_steps=1, bc="zero", eps_d_comp=0.05, mass_correction=False,
    )
    out_f = reinit.reinitialize(psi0)
    out_b = np.flip(reinit.reinitialize(np.flip(psi0, axis=1)), axis=1)
    err = float(np.max(np.abs(out_f - out_b))) / max(1.0, float(np.max(np.abs(out_f))))
    assert err < 1e-12, (
        f"Single-iteration split-reinit y-flip err = {err:.3e} "
        f"(pre-CHK-168: 4.47e-6 for α=2)"
    )


@pytest.mark.parametrize("alpha_grid", [1.0, 2.0])
def test_split_reinit_y_flip_magnitude(alpha_grid):
    """After CHK-168 fix, single-reinit y-flip err is O(1e-6) or better.

    Pre-fix sym_B (α=2) hit 4.47e-6 at step 5 within a solver run;
    post-fix single-reinit output asymmetry drops to O(1e-7).
    4-iter composition still picks up Lyapunov amplification
    (ASM-122-A), but the absolute magnitude is much smaller.
    """
    backend, grid, ccd, eps, psi0 = _build(alpha_grid)
    reinit = SplitReinitializer(
        backend=backend, grid=grid, ccd=ccd, eps=eps,
        n_steps=4, bc="zero", eps_d_comp=0.05, mass_correction=True,
    )
    out = reinit.reinitialize(psi0)
    denom = max(1.0, float(np.max(np.abs(out))))
    y_err = float(np.max(np.abs(out - np.flip(out, axis=1)))) / denom
    # Pre-CHK-168: 4.47e-6 on α=2 at sim step 5; post-fix ~6e-7 on fresh input.
    assert y_err < 2e-6, (
        f"Single-reinit y-flip err = {y_err:.3e} on α={alpha_grid} "
        f"(pre-CHK-168: ≥ 4.47e-6)"
    )
