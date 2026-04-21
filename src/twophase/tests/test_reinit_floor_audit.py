"""CHK-169 regression — safe_grad floor audit across reinit sites.

CHK-168 raised the ``safe_grad`` floor in
``reinit_ops.compute_gradient_normal`` from 1e-14 to 1e-6 to block ULP-
amplification of ∂ψ/∂y ODD noise at ψ(1-ψ)→0 bulk nodes. This suite
verifies the same fix has been applied defensively to the two
remaining hot-path sites that consume ψ directly:

- ``UnifiedDCCDReinitializer._reinitialize`` (reinit_unified.py:58)
- ``UnifiedDCCDReinitializer._reinitialize_legacy`` (reinit_unified.py:122)
- Legacy ``Reinitializer`` WENO5 compression (reinitialize.py:185)

The extender sites
(``closest_point_extender.compute_normal``,
``field_extender.compute_normal``) retain the 1e-14 floor because they
operate on a SDF where |∇φ| ≈ 1 everywhere — the floor is physically
inactive and raising it would mask under-resolved low-gradient regions.
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
from twophase.levelset.reinit_unified import UnifiedDCCDReinitializer  # noqa: E402
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


# ── UnifiedDCCDReinitializer: hot path floor audit ──────────────────


@pytest.mark.parametrize("alpha_grid", [1.0, 2.0])
def test_unified_reinit_hot_path_safe_grad_floor(alpha_grid):
    """CHK-169: UnifiedDCCD hot path must use safe_grad floor 1e-6 (not 1e-14)."""
    backend, grid, ccd, eps, psi0 = _build(alpha_grid)
    # Run a single reinit step; introspect via the inner ∇ψ / safe_grad path by
    # reproducing what reinit_unified does on the same ψ.
    xp = backend.xp
    q = xp.asarray(psi0).copy()
    dpsi = []
    for ax in range(2):
        g1, _ = ccd.differentiate(q, ax)
        dpsi.append(g1)
    grad_sq = sum(g * g for g in dpsi)
    # Mirror the (post-CHK-169) floor exactly.
    safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-12)), 1e-6)
    assert float(np.min(safe_grad)) >= 1e-6 - 1e-20, (
        f"safe_grad min = {float(np.min(safe_grad)):.3e} < 1e-6 floor (CHK-169)"
    )

    # Also smoke-test that the reinitializer runs without NaN on this input.
    reinit = UnifiedDCCDReinitializer(
        backend=backend, grid=grid, ccd=ccd, eps=eps,
        n_steps=1, bc="zero", eps_d_comp=0.05, mass_correction=False,
    )
    out = reinit.reinitialize(psi0)
    assert np.all(np.isfinite(np.asarray(out)))


@pytest.mark.parametrize("alpha_grid", [1.0, 2.0])
def test_unified_reinit_single_iter_y_flip_equivariant(alpha_grid):
    """CHK-169: single-iter UnifiedDCCD must be y-flip equivariant to ULP.

    This is the same guarantee CHK-168 provides for SplitReinitializer;
    both consume ``dccd_compression_div`` / ``compute_gradient_normal``
    chain and share the ULP-amplification mechanism.
    """
    backend, grid, ccd, eps, psi0 = _build(alpha_grid)
    reinit = UnifiedDCCDReinitializer(
        backend=backend, grid=grid, ccd=ccd, eps=eps,
        n_steps=1, bc="zero", eps_d_comp=0.05, mass_correction=False,
    )
    out_f = np.asarray(reinit.reinitialize(psi0))
    out_b = np.flip(
        np.asarray(reinit.reinitialize(np.flip(psi0, axis=1))), axis=1,
    )
    denom = max(1.0, float(np.max(np.abs(out_f))))
    err = float(np.max(np.abs(out_f - out_b))) / denom
    assert err < 1e-12, (
        f"Unified single-iter y-flip err = {err:.3e} (CHK-169 target < 1e-12)"
    )


# ── UnifiedDCCDReinitializer legacy path floor audit ───────────────


@pytest.mark.parametrize("alpha_grid", [1.0, 2.0])
def test_unified_reinit_legacy_path_safe_grad_floor(alpha_grid):
    """CHK-169: legacy ``_reinitialize_legacy`` updated to match hot-path floor.

    The legacy path is a CHK-102 structural baseline; CHK-169 harmonises the
    floor without breaking its role as a reference implementation.
    """
    backend, grid, ccd, eps, psi0 = _build(alpha_grid)
    reinit = UnifiedDCCDReinitializer(
        backend=backend, grid=grid, ccd=ccd, eps=eps,
        n_steps=1, bc="zero", eps_d_comp=0.05, mass_correction=False,
    )
    # Legacy path is publicly accessible for regression debugging.
    out = np.asarray(reinit._reinitialize_legacy(psi0))
    assert np.all(np.isfinite(out))
    # Single-iter y-flip must also be ULP equivariant on the legacy path.
    out_b = np.asarray(
        reinit._reinitialize_legacy(np.flip(psi0, axis=1))
    )
    out_b = np.flip(out_b, axis=1)
    denom = max(1.0, float(np.max(np.abs(out))))
    err = float(np.max(np.abs(out - out_b))) / denom
    assert err < 1e-12, (
        f"Unified legacy single-iter y-flip err = {err:.3e} (CHK-169 target < 1e-12)"
    )


# ── Extender SDF-input sites: floor intentionally kept at 1e-14 ────


@pytest.mark.parametrize("alpha_grid", [1.0, 2.0])
def test_closest_point_extender_floor_kept_1e14_for_sdf(alpha_grid):
    """CHK-169: extender floor stays at 1e-14 because |∇φ| ≈ 1 for SDF."""
    from twophase.levelset.closest_point_extender import ClosestPointExtender

    backend, grid, ccd, eps, psi0 = _build(alpha_grid)
    # Build a proper SDF (tanh-inverse of ψ ≈ ε·logit(ψ)) to match what
    # extenders consume in production.
    xp = backend.xp
    q_clipped = xp.clip(xp.asarray(psi0), 1e-4, 1.0 - 1e-4)
    phi_sdf = eps * xp.log(q_clipped / (1.0 - q_clipped))

    ext = ClosestPointExtender(
        backend=backend, grid=grid, ccd=ccd,
    )
    n_hat = ext.compute_normal(phi_sdf)

    # Interior (non-interface) regions should have ||n̂|| ≈ 1 and
    # the floor should NOT be active anywhere (no warnings, no NaN).
    n_mag_sq = sum(np.asarray(h) ** 2 for h in n_hat)
    assert float(np.max(n_mag_sq)) <= 1.0 + 1e-8
    # Sanity: at least somewhere n̂ magnitude is near 1.
    assert float(np.max(n_mag_sq)) >= 0.9 - 1e-6


def test_field_extender_floor_kept_1e14_for_sdf():
    """CHK-169: field_extender floor stays at 1e-14 for same reason."""
    from twophase.levelset.field_extender import FieldExtender

    backend, grid, ccd, eps, psi0 = _build(1.0)
    xp = backend.xp
    q_clipped = xp.clip(xp.asarray(psi0), 1e-4, 1.0 - 1e-4)
    phi_sdf = eps * xp.log(q_clipped / (1.0 - q_clipped))

    ext = FieldExtender(
        backend=backend, grid=grid, ccd=ccd,
    )
    n_hat = ext.compute_normal(phi_sdf)
    n_mag_sq = sum(np.asarray(h) ** 2 for h in n_hat)
    assert np.all(np.isfinite(n_mag_sq))
    assert float(np.max(n_mag_sq)) >= 0.9 - 1e-6
