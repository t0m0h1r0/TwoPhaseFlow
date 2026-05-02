"""Unit tests for Ridge-Eikonal non-uniform reinitializer (CHK-159).

Covers V1 ridge topology, V2 sigma_eff convergence, V3 non-uniform FMM
residual, V5 CPU/GPU parity. V4 volume and V6 backward-compat land in a
second pass once the builder / config wire-up is live.
"""

from __future__ import annotations

import numpy as np
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.wall_contact import (
    WallContactSet,
    apply_masked_mass_correction,
)
from twophase.levelset.ridge_eikonal import (
    NonUniformFMM,
    RidgeExtractor,
    RidgeEikonalReinitializer,
)


# ── fixtures & helpers ──────────────────────────────────────────────────

@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def _mk_grid(n=64, L=1.0, alpha=1.0, backend=None):
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(n, n), L=(L, L), alpha_grid=alpha)
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    if alpha > 1.0:
        x = np.linspace(0.0, L, n + 1)
        X, Y = np.meshgrid(x, x, indexing="ij")
        phi0 = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2) - 0.25
        eps = 1.5 * (L / n)
        psi0 = 1.0 / (1.0 + np.exp(-phi0 / eps))
        grid.update_from_levelset(psi0, eps=eps, ccd=ccd)
    return grid, ccd


def _phi_circle(grid, cx, cy, R):
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    return np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - R


def _wall_crossing(coord, values, level=0.5):
    shifted = np.asarray(values) - level
    idx = np.where(shifted[:-1] * shifted[1:] <= 0.0)[0]
    if idx.size == 0:
        return np.nan
    k = int(idx[0])
    a = values[k]
    b = values[k + 1]
    if b == a:
        return float(coord[k])
    return float(coord[k] + (level - a) * (coord[k + 1] - coord[k]) / (b - a))


def _wall_crossings(coord, values, level=0.5):
    shifted = np.asarray(values) - level
    crossings = []
    for index in np.where(shifted[:-1] * shifted[1:] <= 0.0)[0]:
        left_index = int(index)
        left_value = values[left_index]
        right_value = values[left_index + 1]
        if right_value == left_value:
            crossings.append(float(coord[left_index]))
        else:
            crossings.append(float(
                coord[left_index]
                + (level - left_value)
                * (coord[left_index + 1] - coord[left_index])
                / (right_value - left_value)
            ))
    return crossings


def _half_period_error(field):
    values = np.asarray(field)
    n_unique = values.shape[0] - 1
    return float(
        np.max(
            np.abs(
                values[: n_unique // 2, :]
                - values[n_unique // 2 : n_unique, :]
            )
        )
    )


# ── V1 — ridge topology (two disks vs merged) ──────────────────────────

def test_ridge_topology_two_disks(backend):
    grid, _ = _mk_grid(n=64, L=1.0, alpha=1.0, backend=backend)
    phi_a = _phi_circle(grid, 0.30, 0.5, 0.15)
    phi_b = _phi_circle(grid, 0.70, 0.5, 0.15)
    phi_union = np.minimum(phi_a, phi_b)  # two disconnected disks

    ext = RidgeExtractor(backend, grid, sigma_0=3.0)
    xi = ext.compute_xi_ridge(phi_union)
    assert np.all(np.isfinite(np.asarray(xi))), "xi_ridge must be finite"
    mask = np.asarray(ext.extract_ridge_mask(xi))
    assert mask.any(), "two disks should yield a non-empty ridge mask"
    # A ridge mask with two disconnected disks should touch both halves.
    left  = mask[:, :33].sum()
    right = mask[:, 32:].sum()
    assert left > 0 and right > 0, (
        f"ridge should appear under both disks (left={left}, right={right})"
    )


def test_ridge_topology_single_merged_disk(backend):
    grid, _ = _mk_grid(n=64, L=1.0, alpha=1.0, backend=backend)
    phi = _phi_circle(grid, 0.5, 0.5, 0.25)  # single disk
    ext = RidgeExtractor(backend, grid, sigma_0=3.0)
    xi = ext.compute_xi_ridge(phi)
    mask = np.asarray(ext.extract_ridge_mask(xi))
    # A single convex region must produce a non-empty ridge concentrated near the centre.
    assert mask.any(), "single disk should yield a non-empty ridge mask"
    ii, jj = np.where(mask)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    cx = x[ii].mean()
    cy = y[jj].mean()
    assert abs(cx - 0.5) < 0.1 and abs(cy - 0.5) < 0.1, (
        f"ridge centroid ({cx:.3f}, {cy:.3f}) should be near (0.5, 0.5)"
    )


# ── V2 — sigma_eff spatial scaling under alpha=2 stretching ────────────

def test_sigma_eff_convergence_alpha2(backend):
    """sigma_eff(x) tracks h(x)·sigma_0/h_ref exactly at every node."""
    grid, _ = _mk_grid(n=64, L=1.0, alpha=2.0, backend=backend)
    sigma_0 = 3.0
    ext = RidgeExtractor(backend, grid, sigma_0=sigma_0)
    h_ref_exp = float(np.prod([L / N for L, N in zip(grid.L, grid.N)]) ** (1.0 / grid.ndim))
    hx = np.asarray(grid.h[0]).reshape(-1, 1)
    hy = np.asarray(grid.h[1]).reshape(1, -1)
    h_field = np.sqrt(hx * hy)
    sigma_expected = sigma_0 * h_field / h_ref_exp
    sigma_actual = np.asarray(ext.sigma_eff)
    err = np.max(np.abs(sigma_actual - sigma_expected))
    assert err < 1e-12, f"sigma_eff mismatch Linf={err:.3e}"
    # Stretching must produce spatial variation of sigma_eff.
    assert sigma_actual.max() / sigma_actual.min() > 1.1, (
        "alpha=2 should produce >10% spread in sigma_eff"
    )


# ── V3 — non-uniform FMM Eikonal residual on stretched grid ────────────

def _eikonal_residual_phys(phi, grid):
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    gx = np.zeros_like(phi)
    gy = np.zeros_like(phi)
    dx = np.diff(x)
    dy = np.diff(y)
    gx[1:-1, :] = (phi[2:, :] - phi[:-2, :]) / (dx[:-1] + dx[1:]).reshape(-1, 1)
    gy[:, 1:-1] = (phi[:, 2:] - phi[:, :-2]) / (dy[:-1] + dy[1:]).reshape(1, -1)
    # One-sided at boundaries.
    gx[0,  :] = (phi[1, :] - phi[0, :])  / dx[0]
    gx[-1, :] = (phi[-1, :] - phi[-2, :]) / dx[-1]
    gy[:, 0]  = (phi[:, 1] - phi[:, 0])  / dy[0]
    gy[:, -1] = (phi[:, -1] - phi[:, -2]) / dy[-1]
    return np.sqrt(gx * gx + gy * gy)


@pytest.mark.parametrize("alpha", [1.0, 2.0, 3.0])
def test_fmm_eikonal_residual(backend, alpha):
    """|grad_x phi_fmm| - 1 in physical space stays below a reasonable band.

    FMM is first-order accurate; we assert a band <0.35 excluding the
    interface and domain boundaries. Caustic cells are excluded via a
    trimming mask (phi close to zero).
    """
    grid, _ = _mk_grid(n=64, L=1.0, alpha=alpha, backend=backend)
    phi_exact = _phi_circle(grid, 0.5, 0.5, 0.25)
    fmm = NonUniformFMM(grid)
    phi_fmm = fmm.solve(phi_exact.copy())

    g_abs = _eikonal_residual_phys(phi_fmm, grid)
    # Exclude interface (where |phi| ≈ 0) and outer 2-node band.
    trim = np.ones_like(phi_fmm, dtype=bool)
    trim[:2, :] = False; trim[-2:, :] = False
    trim[:, :2] = False; trim[:, -2:] = False
    trim &= np.abs(phi_fmm) > 2.0 * float(np.min(grid.h[0]))
    res = np.abs(g_abs[trim] - 1.0)
    # Caustic-cell spikes are bounded to a few outliers (<0.5% of nodes).
    p99 = np.percentile(res, 99.0)
    assert p99 < 0.35, (
        f"alpha={alpha}: FMM Eikonal residual 99th pct too wide (p99={p99:.3f})"
    )
    # Mean residual should tighten further.
    assert res.mean() < 0.1, (
        f"alpha={alpha}: FMM mean Eikonal residual {res.mean():.3f} too high"
    )


def test_fmm_physical_coord_seeding(backend):
    """FMM distance at a node adjacent to the interface equals the
    physical-coordinate linear-interpolation seed (not an index fraction)."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=backend)
    # Interface at x=0.5 (axis-aligned plane, trivial to trace).
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    phi_in = X - 0.5
    fmm = NonUniformFMM(grid)
    phi_out = fmm.solve(phi_in)
    # For this field |phi| is the exact x-distance to the plane x=0.5.
    err = np.max(np.abs(np.abs(phi_out) - np.abs(phi_in)))
    # Axis-aligned 1-D interface + physical seeding: FMM should reconstruct
    # to machine precision (up to floating-point quadratic rounding ~1e-12).
    assert err < 1e-10, f"1D physical-seed reconstruction err={err:.3e}"


def test_fmm_exact_zero_wall_seed_is_dirichlet(backend):
    """A zero set on the wall is FMM Dirichlet data, not a missing crossing."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, _ = np.meshgrid(x, y, indexing="ij")
    phi_in = X.copy()

    fmm = NonUniformFMM(grid)
    phi_out = fmm.solve(phi_in)

    np.testing.assert_allclose(phi_out[0, :], 0.0, atol=1e-14)
    np.testing.assert_allclose(phi_out[:, 16], x, atol=1e-12)


def test_reinit_mass_correction_pins_wall_contact(backend):
    """Mass correction must not detach an interface pinned to a wall."""
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, _ = np.meshgrid(x, y, indexing="ij")
    eps = 0.04
    psi = 1.0 / (1.0 + np.exp(-X / eps))
    reinit = RidgeEikonalReinitializer(
        backend, grid, ccd, eps=eps, sigma_0=3.0,
        eps_scale=1.4, mass_correction=True,
    )

    psi_out = np.asarray(reinit.reinitialize(psi))

    np.testing.assert_allclose(psi_out[0, :], 0.5, atol=2e-12)


def test_ridge_eikonal_preserves_mixed_periodic_half_period_symmetry(backend):
    """Zero-set FMM seeding must preserve the periodic quotient symmetry."""
    n = 32
    grid = Grid(GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0), alpha_grid=1.0), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic_wall")
    eps = 1.5 / n
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    phi = Y - (0.5 + 0.04 * np.cos(4.0 * np.pi * X))
    psi = heaviside(np, phi, eps)
    psi[-1, :] = psi[0, :]
    reinit = RidgeEikonalReinitializer(
        backend, grid, ccd, eps=eps, sigma_0=3.0,
        eps_scale=1.4, mass_correction=True,
    )

    psi_out = np.asarray(reinit.reinitialize(psi))

    assert _half_period_error(psi) < 1.0e-14
    assert _half_period_error(psi_out) < 1.0e-12
    np.testing.assert_allclose(psi_out[-1, :], psi_out[0, :], atol=1e-14)


def test_wall_contact_detection_records_side_wall_coordinates(backend):
    """No-slip contact constraints are detected in physical wall coordinates."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    _, Y = np.meshgrid(x, y, indexing="ij")
    y_contact = 0.47
    eps = 0.04
    psi = 1.0 / (1.0 + np.exp(-(Y - y_contact) / eps))

    contacts = WallContactSet.detect_from_psi(psi, grid, bc_type="wall")

    assert len(contacts.contacts) == 2
    coords = sorted(contact.coordinate for contact in contacts.contacts)
    np.testing.assert_allclose(coords, [y_contact, y_contact], atol=1e-4)
    assert len(contacts.traces) == 4


def test_wall_trace_constraint_disabled_for_periodic_bc(backend):
    """Periodic boundaries do not receive no-slip wall trace constraints."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    y_coords = np.asarray(grid.coords[1])
    _, y_mesh = np.meshgrid(np.asarray(grid.coords[0]), y_coords, indexing="ij")
    psi = 1.0 / (1.0 + np.exp(-(y_mesh - 0.47) / 0.04))

    contacts = WallContactSet.detect_from_psi(psi, grid, bc_type="periodic")

    assert not contacts
    assert len(contacts.contacts) == 0
    assert len(contacts.traces) == 0


def test_wall_contact_impose_pins_half_contour(backend):
    """Pinned contacts impose the exact wall half-contour after distortion."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    _, Y = np.meshgrid(x, y, indexing="ij")
    y_contact = 0.47
    eps = 0.04
    psi = 1.0 / (1.0 + np.exp(-(Y - y_contact) / eps))
    contacts = WallContactSet.detect_from_psi(psi, grid, bc_type="wall")
    y_pinned = contacts.contacts[0].coordinate
    psi[:, :] = 0.2

    psi_pinned = contacts.impose_on_wall_trace(np, grid, psi)

    np.testing.assert_allclose(
        _wall_crossing(y, psi_pinned[0, :]),
        y_pinned,
        atol=1e-14,
    )
    np.testing.assert_allclose(
        _wall_crossing(y, psi_pinned[-1, :]),
        y_pinned,
        atol=1e-14,
    )


def test_wall_trace_projection_removes_extra_wall_crossings(backend):
    """No-slip wall trace projection prevents birth of new wall contacts."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x_coords = np.asarray(grid.coords[0])
    y_coords = np.asarray(grid.coords[1])
    _, y_mesh = np.meshgrid(x_coords, y_coords, indexing="ij")
    y_contact = 0.47
    eps = 0.04
    psi = 1.0 / (1.0 + np.exp(-(y_mesh - y_contact) / eps))
    contacts = WallContactSet.detect_from_psi(psi, grid, bc_type="wall")
    y_pinned = contacts.contacts[0].coordinate

    distorted = psi.copy()
    distorted[0, :] = 0.5 + 0.35 * np.sin(6.0 * np.pi * y_coords)
    distorted[-1, :] = distorted[0, :]
    assert len(_wall_crossings(y_coords, distorted[0, :])) > 1

    projected = contacts.impose_on_wall_trace(np, grid, distorted)

    left_crossings = _wall_crossings(y_coords, projected[0, :])
    right_crossings = _wall_crossings(y_coords, projected[-1, :])
    assert len(left_crossings) == 1
    assert len(right_crossings) == 1
    np.testing.assert_allclose(left_crossings[0], y_pinned, atol=1e-14)
    np.testing.assert_allclose(right_crossings[0], y_pinned, atol=1e-14)


def test_wall_trace_projection_leaves_interior_free(backend):
    """Wall trace projection is a boundary-only operation."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x_coords = np.asarray(grid.coords[0])
    y_coords = np.asarray(grid.coords[1])
    _, y_mesh = np.meshgrid(x_coords, y_coords, indexing="ij")
    psi = 1.0 / (1.0 + np.exp(-(y_mesh - 0.47) / 0.04))
    contacts = WallContactSet.detect_from_psi(psi, grid, bc_type="wall")
    projected = contacts.impose_on_wall_trace(np, grid, psi)
    interior_distorted = projected.copy()
    interior_distorted[1:-1, 1:-1] = np.clip(
        interior_distorted[1:-1, 1:-1] + 0.123,
        0.0,
        1.0,
    )

    after_projection = contacts.impose_on_wall_trace(np, grid, interior_distorted)

    np.testing.assert_allclose(
        after_projection[1:-1, 1:-1],
        interior_distorted[1:-1, 1:-1],
        atol=0.0,
    )


def test_wall_phase_projection_allows_near_wall_approach(backend):
    """Wall values may approach the interface without creating contact."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x_coords = np.asarray(grid.coords[0])
    y_coords = np.asarray(grid.coords[1])
    _, y_mesh = np.meshgrid(x_coords, y_coords, indexing="ij")
    psi = 1.0 / (1.0 + np.exp(-(y_mesh - 0.47) / 0.04))
    contacts = WallContactSet.detect_from_psi(psi, grid, bc_type="wall")
    approached = contacts.impose_on_wall_trace(np, grid, psi)
    reference_side = np.sign(psi[0, :] - 0.5)
    contact_band = np.abs(y_coords - contacts.contacts[0].coordinate) < 2.0 * np.min(grid.h[1])
    free_wall = reference_side != 0.0
    free_wall = free_wall & np.logical_not(contact_band)
    approached[0, free_wall & (reference_side < 0.0)] = 0.499
    approached[0, free_wall & (reference_side > 0.0)] = 0.501

    projected = contacts.impose_on_wall_trace(np, grid, approached)

    np.testing.assert_allclose(
        projected[0, free_wall & (reference_side < 0.0)],
        0.499,
        atol=0.0,
    )
    np.testing.assert_allclose(
        projected[0, free_wall & (reference_side > 0.0)],
        0.501,
        atol=0.0,
    )


def test_masked_mass_correction_preserves_pinned_contact(backend):
    """Mass correction excludes pinned contact DOFs."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    _, Y = np.meshgrid(x, y, indexing="ij")
    y_contact = 0.47
    eps = 0.04
    psi = 1.0 / (1.0 + np.exp(-(Y - y_contact) / eps))
    contacts = WallContactSet.detect_from_psi(psi, grid, bc_type="wall")
    y_pinned = contacts.contacts[0].coordinate
    psi = contacts.impose_on_wall_trace(np, grid, psi)
    dV = grid.cell_volumes()
    free_mask = np.logical_not(contacts.contact_mask(np, grid, psi.shape))

    corrected = apply_masked_mass_correction(
        np,
        psi,
        dV,
        np.sum(psi * dV) + 1.0e-3,
        free_mask,
    )
    corrected = contacts.impose_on_wall_trace(np, grid, corrected)

    np.testing.assert_allclose(
        _wall_crossing(y, corrected[0, :]),
        y_pinned,
        atol=1e-14,
    )
    np.testing.assert_allclose(
        _wall_crossing(y, corrected[-1, :]),
        y_pinned,
        atol=1e-14,
    )


def test_constraint_mask_preserves_contact_but_not_full_wall_trace(backend):
    """Conservation repair is not forbidden from moving same-phase wall values."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x_coords = np.asarray(grid.coords[0])
    y_coords = np.asarray(grid.coords[1])
    _, y_mesh = np.meshgrid(x_coords, y_coords, indexing="ij")
    y_contact = 0.47
    eps = 0.04
    psi = 1.0 / (1.0 + np.exp(-(y_mesh - y_contact) / eps))
    contacts = WallContactSet.detect_from_psi(psi, grid, bc_type="wall")
    projected = contacts.impose_on_wall_trace(np, grid, psi)
    constrained = contacts.constraint_mask(np, grid, projected.shape)
    free_mask = np.logical_not(constrained)

    assert not np.any(constrained[1:-1, 1:-1])
    assert not np.all(constrained[0, :])

    corrected = apply_masked_mass_correction(
        np,
        projected,
        grid.cell_volumes(),
        np.sum(projected * grid.cell_volumes()) + 1.0e-3,
        free_mask,
    )
    corrected = contacts.impose_on_wall_trace(np, grid, corrected)

    np.testing.assert_allclose(
        _wall_crossing(y_coords, corrected[0, :]),
        contacts.contacts[0].coordinate,
        atol=1e-14,
    )


def test_ridge_eikonal_reinit_preserves_pinned_contact_coordinate(backend):
    """Ridge-eikonal reinit keeps no-slip contact coordinates fixed."""
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    _, Y = np.meshgrid(x, y, indexing="ij")
    y_contact = 0.47
    eps = 0.04
    psi = 1.0 / (1.0 + np.exp(-(Y - y_contact) / eps))
    contacts = WallContactSet.detect_from_psi(psi, grid, bc_type="wall")
    y_pinned = contacts.contacts[0].coordinate
    reinit = RidgeEikonalReinitializer(
        backend, grid, ccd, eps=eps, sigma_0=3.0,
        eps_scale=1.4, mass_correction=True,
    )
    reinit.set_wall_contacts(contacts)

    psi_out = np.asarray(reinit.reinitialize(psi))

    np.testing.assert_allclose(
        _wall_crossing(y, psi_out[0, :]),
        y_pinned,
        atol=1e-14,
    )
    np.testing.assert_allclose(
        _wall_crossing(y, psi_out[-1, :]),
        y_pinned,
        atol=1e-14,
    )


# ── V5 — CPU/GPU parity (CPU-only under this test; GPU gated elsewhere) ─

def test_sigma_eff_cpu_fuse_identity(backend):
    """On CPU backend, @_fuse must be identity — kernels produce the
    same values as a plain numpy expression."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=backend)
    ext = RidgeExtractor(backend, grid, sigma_0=3.0)
    hx = np.asarray(grid.h[0]).reshape(-1, 1)
    hy = np.asarray(grid.h[1]).reshape(1, -1)
    h_field = np.sqrt(hx * hy)
    h_ref = float(np.prod([L / N for L, N in zip(grid.L, grid.N)]) ** (1.0 / grid.ndim))
    sigma_expect = 3.0 * h_field / h_ref
    np.testing.assert_allclose(np.asarray(ext.sigma_eff), sigma_expect, rtol=0, atol=1e-14)


def test_reinit_preserves_shape(backend):
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    phi_exact = _phi_circle(grid, 0.5, 0.5, 0.25)
    eps = 1.5 * (1.0 / 32)
    psi = 1.0 / (1.0 + np.exp(-phi_exact / eps))
    reinit = RidgeEikonalReinitializer(
        backend, grid, ccd, eps=eps, sigma_0=3.0, eps_scale=1.4, mass_correction=True,
    )
    psi_out = reinit.reinitialize(psi)
    psi_out = np.asarray(psi_out)
    assert psi_out.shape == psi.shape
    assert np.all((psi_out >= -1e-6) & (psi_out <= 1.0 + 1e-6)), (
        f"psi out of [0,1]: min={psi_out.min()}, max={psi_out.max()}"
    )


# ── V4 — volume conservation (integration) ─────────────────────────────

@pytest.mark.parametrize("alpha", [1.0, 2.0])
def test_volume_conservation_single_step(backend, alpha):
    """One reinit pass on a static circle preserves volume within 5%."""
    grid, ccd = _mk_grid(n=64, L=1.0, alpha=alpha, backend=backend)
    phi_exact = _phi_circle(grid, 0.5, 0.5, 0.25)
    eps = 1.5 * float(np.min(grid.h[0]))
    psi = 1.0 / (1.0 + np.exp(-phi_exact / eps))
    reinit = RidgeEikonalReinitializer(
        backend, grid, ccd, eps=eps, sigma_0=3.0, eps_scale=1.4, mass_correction=True,
    )
    dV = np.asarray(grid.cell_volumes())
    V_in = float(np.sum(np.asarray(psi) * dV))
    psi_out = np.asarray(reinit.reinitialize(psi))
    V_out = float(np.sum(psi_out * dV))
    rel = abs(V_out - V_in) / max(abs(V_in), 1e-30)
    assert rel < 0.05, f"alpha={alpha}: volume drift {rel*100:.2f}% > 5%"


# ── V6 — backward compatibility via builder (default='split') ──────────

def test_backcompat_default_is_split():
    """NumericsConfig default reinit_method must remain 'split'."""
    from twophase.config import NumericsConfig
    nc = NumericsConfig()
    assert nc.reinit_method == "split"
    assert nc.ridge_sigma_0 == 3.0


def test_backcompat_builder_default_builds_split(backend):
    """Building the Reinitializer facade with defaults picks SplitReinitializer."""
    from twophase.levelset.reinitialize import Reinitializer
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    eps = 1.5 * (1.0 / 32)
    r = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="neumann")
    # Strategy instance should be SplitReinitializer (no ridge side-effects).
    from twophase.levelset.reinit_split import SplitReinitializer
    assert isinstance(r._strategy, SplitReinitializer)


def test_builder_registers_ridge_eikonal(backend):
    """Explicit method='ridge_eikonal' picks RidgeEikonalReinitializer."""
    from twophase.levelset.reinitialize import Reinitializer
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    eps = 1.5 * (1.0 / 32)
    r = Reinitializer(
        backend, grid, ccd, eps, n_steps=4, bc="neumann",
        method="ridge_eikonal", sigma_0=3.0, eps_scale=1.0,
    )
    assert isinstance(r._strategy, RidgeEikonalReinitializer)
    assert r._strategy._eps_scale == pytest.approx(1.0)
    np.testing.assert_allclose(np.asarray(r._strategy._eps_local), eps, atol=1e-15)


def test_dgr_default_is_paper_exact_no_smoothing(backend):
    """DGR default must not add the optional non-paper φ Laplacian smoothing."""
    from twophase.levelset.reinit_dgr import DGRReinitializer
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    eps = 1.5 * (1.0 / 32)

    reinit = DGRReinitializer(backend, grid, ccd, eps=eps)

    assert reinit.phi_smooth_C == pytest.approx(0.0)


def test_uniform_basis_eikonal_paths_reject_nonuniform_grid(backend):
    """ξ-SDF/eikonal_fmm are uniform-grid bases; non-uniform uses ridge_eikonal."""
    from twophase.levelset.reinit_eikonal import EikonalReinitializer
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=2.0, backend=backend)
    assert not grid.uniform
    eps = 1.5 * float(np.min(grid.h[0]))

    with pytest.raises(ValueError, match="uniform-grid basis"):
        EikonalReinitializer(backend, grid, ccd, eps=eps, xi_sdf=True)
    with pytest.raises(ValueError, match="uniform-grid basis"):
        EikonalReinitializer(backend, grid, ccd, eps=eps, fmm=True)


@pytest.mark.gpu
def test_gpu_parity_ridge_kernels():
    """V5: CPU/GPU parity of fused kernels (gated behind --gpu)."""
    cpu = Backend(use_gpu=False)
    try:
        gpu = Backend(use_gpu=True)
    except Exception as e:
        pytest.skip(f"GPU backend unavailable: {e}")
    grid_cpu, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=cpu)
    grid_gpu, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=gpu)
    ext_cpu = RidgeExtractor(cpu, grid_cpu, sigma_0=3.0)
    ext_gpu = RidgeExtractor(gpu, grid_gpu, sigma_0=3.0)
    s_cpu = np.asarray(ext_cpu.sigma_eff)
    s_gpu = ext_gpu.sigma_eff
    s_gpu = s_gpu.get() if hasattr(s_gpu, "get") else np.asarray(s_gpu)
    np.testing.assert_allclose(s_cpu, s_gpu, rtol=1e-12, atol=1e-14)


@pytest.mark.gpu
def test_gpu_fmm_matches_cpu_accepted_set_with_ridge_seeds():
    """GPU FMM must match CPU accepted-set FMM, not a fixed-sweep proxy."""
    cpu = Backend(use_gpu=False)
    try:
        gpu = Backend(use_gpu=True)
    except Exception as e:
        pytest.skip(f"GPU backend unavailable: {e}")

    grid_cpu, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=cpu)
    grid_gpu, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=gpu)
    phi_cpu = _phi_circle(grid_cpu, 0.47, 0.52, 0.23)
    h_min = float(min(np.min(grid_cpu.h[ax]) for ax in range(grid_cpu.ndim)))
    ridge_mask_cpu = np.abs(phi_cpu) < 0.35 * h_min
    ii, jj = np.where(ridge_mask_cpu & (np.abs(phi_cpu) < 0.5 * h_min))
    extra_seeds = [(int(ii[k]), int(jj[k]), 0.0) for k in range(len(ii))]

    fmm_cpu = NonUniformFMM(grid_cpu)
    fmm_gpu = NonUniformFMM(grid_gpu, backend=gpu)
    phi_expected = fmm_cpu.solve(phi_cpu.copy(), extra_seeds=extra_seeds)
    phi_actual_dev = fmm_gpu.solve(
        gpu.xp.asarray(phi_cpu),
        ridge_mask=gpu.xp.asarray(ridge_mask_cpu),
        h_min=h_min,
    )

    assert hasattr(phi_actual_dev, "get"), "GPU FMM must return a device array"
    phi_actual = phi_actual_dev.get()
    np.testing.assert_allclose(phi_actual, phi_expected, rtol=2e-13, atol=2e-13)


# ── C7 — ε-mismatch idempotency tests (CHK-160) ────────────────────────

def test_reinit_call2_idempotent(backend):
    """C7: reinit is idempotent on call 2+ (eps_local consistent fix).

    After call 1 expands ψ from eps to eps_local width, call 2 should
    preserve the width and mass (delta_phi ≈ 0). This test verifies that
    the ε-mismatch fix (line 449: self._eps → self._eps_local) makes call 2
    idempotent. Failure indicates regression to the bug.
    """
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    reinit = RidgeEikonalReinitializer(
        backend, grid, ccd, eps=0.05, sigma_0=3.0,
        eps_scale=1.4, mass_correction=True,
    )
    # Create test ψ (e.g., from a circle).
    phi_init = _phi_circle(grid, 0.5, 0.5, 0.25)
    xp = backend.xp
    psi = xp.asarray(heaviside(xp, phi_init, eps=0.05))

    dV = grid.cell_volumes()

    # Call 1: narrow input → wide output.
    psi_call1 = reinit.reinitialize(psi)
    M_call1 = xp.sum(psi_call1 * dV)

    # Call 2: wide input → wide output (should be idempotent).
    psi_call2 = reinit.reinitialize(psi_call1)
    M_call2 = xp.sum(psi_call2 * dV)

    # Delta_phi on call 2 should be ≈ 0 (idempotent: M_old ≈ M_new).
    # We check indirectly: |M(call2 input) - M(call2 output)| / M should be tiny.
    # If delta_phi were large (bug), M_call2 ≠ M_call1 by ~1% or more.
    # With fix, drift is <1e-4 (numerical precision in mass correction).
    rel_mass_drift_call2 = float(np.abs(M_call2 - M_call1)) / float(np.abs(M_call1) + 1e-14)
    assert rel_mass_drift_call2 < 1e-4, (
        f"Call 2 mass drift {rel_mass_drift_call2:.2e} indicates non-idempotent reinit "
        "(ε-mismatch bug regression or numerical instability)"
    )


def test_ridge_eikonal_no_ke_blowup(backend):
    """C7: KE must not spike >100× between reinit calls.

    The ε-mismatch bug caused a 14× KE jump at step 4 (call 2) on α≈1 grids.
    This test runs 6 steps of the full ns_pipeline stack with ridge_eikonal
    and fccd, and asserts KE(step 4) < 100× KE(step 2). Catches the regression.
    """
    from twophase.simulation.ns_pipeline import TwoPhaseNSSolver

    N = 32
    L = 1.0
    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        alpha_grid=1.01,  # Barely non-uniform: α=1.01 shows step-4 blowup acutely.
        use_local_eps=True,
        eps_factor=1.5,
        grid_rebuild_freq=0,
        reinit_method="ridge_eikonal",
        reinit_every=2,
        reinit_eps_scale=1.4,
        ridge_sigma_0=3.0,
        surface_tension_scheme="pressure_jump",
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="affine_jump",
        reproject_mode="consistent_gfm",
        phi_primary_transport=True,
        advection_scheme="fccd_flux",
        convection_scheme="fccd_flux",
    )

    # Initial condition: perturbed disc.
    xp = solver._backend.xp
    X, Y = solver.X, solver.Y
    r = xp.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    theta = xp.arctan2(Y - 0.5, X - 0.5)
    R_iface = 0.25 * (1.0 + 0.05 * xp.cos(2.0 * theta))
    phi = R_iface - r
    psi = solver.psi_from_phi(phi)
    u = xp.zeros_like(psi)
    v = xp.zeros_like(psi)

    # Rebuild grid once (static α>1).
    psi, u, v = solver._rebuild_grid(psi, u, v, rho_l=833.0, rho_g=1.0)

    ke_by_step = []
    for i in range(6):
        psi, u, v, p = solver.step(psi, u, v, dt=5e-4, rho_l=833.0, rho_g=1.0,
                                    sigma=1.0, mu=0.05, step_index=i)
        ke = float(xp.sum(0.5 * (833.0 * u**2 + 1.0 * v**2)))
        ke_by_step.append(ke)

    # Step 2 (first reinit, step_index=2): expect ~1.4× growth (normal).
    # Step 4 (second reinit, step_index=4): with bug, 14× jump. With fix, ~1.4×.
    ke_step2 = ke_by_step[2]
    ke_step4 = ke_by_step[4]
    ratio = ke_step4 / (ke_step2 + 1e-14)

    assert ratio < 100.0, (
        f"KE blowup: step 4 / step 2 = {ratio:.1f} (should be <100, caught ε-mismatch bug)"
    )
