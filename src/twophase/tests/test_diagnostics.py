"""
Unit tests for diagnostics/collector.py — §11/§12 metric accumulation.

Tests cover:
  1. volume_conservation metric (uniform & non-uniform dV)
  2. kinetic_energy metric (volume-weighted)
  3. deformation metric (second-moment D = (L-B)/(L+B))
  4. interface_amplitude metric
  5. collect() with dV=None fallback (backward compat)
  6. bubble_centroid metric (volume-weighted)
"""

import numpy as np
import pytest

from twophase.tools.diagnostics.collector import DiagnosticCollector
from twophase.tools.diagnostics.interface_diagnostics import (
    midband_fraction,
    relative_mass_error,
)


# ── helpers ──────────────────────────────────────────────────────────────────

N = 32
L = 1.0
H = L / N


def _make_grid():
    x = np.linspace(0, L, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    return X, Y


def _circle_psi(X, Y, cx=0.5, cy=0.5, R=0.25, eps=None):
    """Smoothed Heaviside for a circular interface."""
    if eps is None:
        eps = 1.5 * H
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    phi = R - dist  # positive inside
    psi = np.where(
        phi < -eps, 0.0,
        np.where(phi > eps, 1.0,
                 0.5 * (1 + phi / eps + np.sin(np.pi * phi / eps) / np.pi)),
    )
    return psi


# ── Test 1: volume conservation ──────────────────────────────────────────────

def test_volume_conservation_uniform():
    """Volume conservation relative error = 0 when psi unchanged."""
    X, Y = _make_grid()
    psi = _circle_psi(X, Y)
    u = v = p = np.zeros_like(psi)

    diag = DiagnosticCollector(["volume_conservation"], X, Y, H)
    diag.collect(0.0, psi, u, v, p)
    diag.collect(0.1, psi, u, v, p)  # identical psi

    vc = diag.to_arrays()["volume_conservation"]
    assert vc[1] == pytest.approx(0.0, abs=1e-14)


def test_volume_conservation_with_dV():
    """Volume conservation uses dV array when provided."""
    X, Y = _make_grid()
    psi = _circle_psi(X, Y)
    u = v = p = np.zeros_like(psi)

    # Non-uniform dV (random perturbation, same total area)
    rng = np.random.default_rng(42)
    dV = H ** 2 * (1.0 + 0.1 * rng.standard_normal(psi.shape))
    dV = dV * (L ** 2 / np.sum(dV))  # normalize total area

    diag = DiagnosticCollector(["volume_conservation"], X, Y, H)
    diag.collect(0.0, psi, u, v, p, dV=dV)
    diag.collect(0.1, psi, u, v, p, dV=dV)

    vc = diag.to_arrays()["volume_conservation"]
    assert vc[1] == pytest.approx(0.0, abs=1e-14)


# ── Test 2: kinetic energy ───────────────────────────────────────────────────

def test_kinetic_energy_uniform():
    """KE = 0.5 * sum(rho * |u|^2 * dV)."""
    X, Y = _make_grid()
    psi = np.ones_like(X)  # all liquid
    rho_l, rho_g = 10.0, 1.0
    u = np.ones_like(X) * 2.0
    v = np.zeros_like(X)
    p = np.zeros_like(X)

    diag = DiagnosticCollector(
        ["kinetic_energy"], X, Y, H, rho_l=rho_l, rho_g=rho_g,
    )
    diag.collect(0.0, psi, u, v, p)
    ke = diag.last("kinetic_energy")

    # Expected: 0.5 * rho_l * u^2 * L^2 = 0.5 * 10 * 4 * 1 = 20
    # Discrete sum with (N+1)^2 nodes * h^2 exceeds L^2 → allow ~10% tolerance
    expected = 0.5 * rho_l * 4.0 * L ** 2
    assert ke == pytest.approx(expected, rel=0.1)


def test_kinetic_energy_with_dV():
    """KE uses dV when provided."""
    X, Y = _make_grid()
    psi = np.ones_like(X)
    u = np.ones_like(X)
    v = np.zeros_like(X)
    p = np.zeros_like(X)

    dV = np.full_like(X, H ** 2)

    diag = DiagnosticCollector(
        ["kinetic_energy"], X, Y, H, rho_l=1.0, rho_g=1.0,
    )
    diag.collect(0.0, psi, u, v, p, dV=dV)
    ke = diag.last("kinetic_energy")
    # 0.5 * 1.0 * 1.0 * 1.0^2 = 0.5 (continuous); discrete (N+1)^2 * h^2 > L^2
    assert ke == pytest.approx(0.5, rel=0.1)


# ── Test 3: deformation ─────────────────────────────────────────────────────

def test_deformation_circle():
    """Circular droplet: D = 0 (symmetric)."""
    X, Y = _make_grid()
    psi = _circle_psi(X, Y)
    u = v = p = np.zeros_like(psi)

    diag = DiagnosticCollector(["deformation"], X, Y, H)
    diag.collect(0.0, psi, u, v, p)
    D = diag.last("deformation")
    assert abs(D) < 0.05, f"Circle deformation should be ~0, got {D}"


def test_deformation_ellipse():
    """Elliptical region: D > 0 (non-symmetric)."""
    X, Y = _make_grid()
    # Ellipse: semi-axes 0.3 in x, 0.15 in y
    dist = np.sqrt(((X - 0.5) / 0.3) ** 2 + ((Y - 0.5) / 0.15) ** 2)
    psi = np.where(dist < 1.0, 1.0, 0.0)
    u = v = p = np.zeros_like(psi)

    diag = DiagnosticCollector(["deformation"], X, Y, H)
    diag.collect(0.0, psi, u, v, p)
    D = diag.last("deformation")
    assert D > 0.1, f"Ellipse deformation should be > 0.1, got {D}"


def test_signed_deformation_tracks_axis_orientation():
    """Signed deformation is positive for x-long and negative for y-long drops."""
    X, Y = _make_grid()
    u = v = p = np.zeros_like(X)

    dist_x = np.sqrt(((X - 0.5) / 0.3) ** 2 + ((Y - 0.5) / 0.15) ** 2)
    psi_x = np.where(dist_x < 1.0, 1.0, 0.0)
    diag_x = DiagnosticCollector(["signed_deformation"], X, Y, H)
    diag_x.collect(0.0, psi_x, u, v, p)

    dist_y = np.sqrt(((X - 0.5) / 0.15) ** 2 + ((Y - 0.5) / 0.3) ** 2)
    psi_y = np.where(dist_y < 1.0, 1.0, 0.0)
    diag_y = DiagnosticCollector(["signed_deformation"], X, Y, H)
    diag_y.collect(0.0, psi_y, u, v, p)

    assert diag_x.last("signed_deformation") > 0.1
    assert diag_y.last("signed_deformation") < -0.1


# ── Test 4: interface amplitude ──────────────────────────────────────────────

def test_interface_amplitude_flat():
    """Flat interface at mid-height: amplitude = 0."""
    X, Y = _make_grid()
    psi = np.where(Y > 0.5, 1.0, 0.0)
    u = v = p = np.zeros_like(psi)

    diag = DiagnosticCollector(["interface_amplitude"], X, Y, H)
    diag.collect(0.0, psi, u, v, p)
    amp = diag.last("interface_amplitude")
    assert amp < 0.05


# ── Test 5: backward compatibility (dV=None) ────────────────────────────────

def test_collect_dV_none_backward_compat():
    """collect() with no dV argument uses h^2 (uniform)."""
    X, Y = _make_grid()
    psi = _circle_psi(X, Y)
    u = v = p = np.zeros_like(psi)

    diag = DiagnosticCollector(
        ["volume_conservation", "kinetic_energy"], X, Y, H,
    )
    # Should not raise
    diag.collect(0.0, psi, u, v, p)
    diag.collect(0.1, psi, u, v, p)

    assert len(diag.times) == 2


# ── Test 6: bubble centroid ──────────────────────────────────────────────────

def test_bubble_centroid_centered():
    """Gas bubble at centre: centroid should be ~(0.5, 0.5)."""
    X, Y = _make_grid()
    # Gas bubble: psi < 0.5 inside → invert the liquid circle
    psi = 1.0 - _circle_psi(X, Y)
    u = v = p = np.zeros_like(psi)

    diag = DiagnosticCollector(
        ["bubble_centroid"], X, Y, H,
    )
    diag.collect(0.0, psi, u, v, p)
    xc = diag.last("xc")
    yc = diag.last("yc")

    assert abs(xc - 0.5) < 0.05, f"xc should be ~0.5, got {xc}"
    assert abs(yc - 0.5) < 0.05, f"yc should be ~0.5, got {yc}"


# ── Test 7: symmetry_error (CHK-161) ──────────────────────────────────────────

def test_symmetry_error_centered_circle():
    """A centred circle is 4-fold symmetric → both flip errors ≈ 0."""
    X, Y = _make_grid()
    psi = _circle_psi(X, Y)
    u = v = p = np.zeros_like(psi)

    diag = DiagnosticCollector(["symmetry_error"], X, Y, H)
    diag.collect(0.0, psi, u, v, p)
    assert diag.last("sym_psi_y") < 1e-14
    assert diag.last("sym_psi_x") < 1e-14


def test_symmetry_error_detects_shift():
    """A y-shifted circle has y-flip error > 0 but x-flip error ≈ 0."""
    X, Y = _make_grid()
    psi = _circle_psi(X, Y, cy=0.55)  # shift up
    u = v = p = np.zeros_like(psi)

    diag = DiagnosticCollector(["symmetry_error"], X, Y, H)
    diag.collect(0.0, psi, u, v, p)
    assert diag.last("sym_psi_y") > 0.1    # y-flip broken
    assert diag.last("sym_psi_x") < 1e-14  # x-flip preserved


def test_symmetry_error_velocity_parity():
    """A stagnation-like flow (u odd in x, v odd in y) → zero parity-aware error."""
    X, Y = _make_grid()
    psi = _circle_psi(X, Y)
    # u(x,y) = x - 0.5 is odd about x=0.5, even in y; v is the mirror.
    u = (X - 0.5).copy()
    v = (Y - 0.5).copy()
    p = np.zeros_like(psi)

    diag = DiagnosticCollector(["symmetry_error"], X, Y, H)
    diag.collect(0.0, psi, u, v, p)
    # All six sub-keys must be ≈ 0 for a 4-fold symmetric stagnation flow.
    for k in ("sym_psi_y", "sym_psi_x",
              "sym_u_y", "sym_u_x", "sym_v_y", "sym_v_x"):
        assert diag.last(k) < 1e-13, f"{k} = {diag.last(k)}"


def test_midband_fraction_basic():
    psi = np.array([[0.0, 0.2], [0.85, 1.0]], dtype=float)
    frac = midband_fraction(psi, lo=0.1, hi=0.9)
    assert frac == pytest.approx(0.5, abs=1e-15)


def test_relative_mass_error_zero():
    psi = np.array([[0.2, 0.4], [0.6, 0.8]], dtype=float)
    dV = np.ones_like(psi)
    m0 = float(np.sum(psi * dV))
    err = relative_mass_error(psi, dV, m0)
    assert err == pytest.approx(0.0, abs=1e-15)
