"""
Unit tests for ns_pipeline.py — §12/§13 5-stage predictor-corrector.

Tests cover:
  1. TwoPhaseNSSolver construction (uniform and non-uniform)
  2. 5-stage step() stability on uniform grid (no NaN, KE bounded)
  3. Grid rebuild: coords change, mass conserved, fields remapped
  4. dt_max uses h_min on non-uniform grids
  5. config_io round-trip: alpha_grid flows from YAML dict → solver
"""

import numpy as np
import pytest

from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.simulation.config_io import GridCfg, _parse_grid


# ── helpers ──────────────────────────────────────────────────────────────────

N = 32
LX = LY = 1.0


def _make_solver(alpha_grid: float = 1.0, **kw):
    return TwoPhaseNSSolver(N, N, LX, LY, alpha_grid=alpha_grid, **kw)


def _droplet_ic(solver):
    """Circle droplet at centre: gas inside, liquid outside."""
    X, Y = solver.X, solver.Y
    R = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    return solver.psi_from_phi(0.25 - R)


# ── Test 1: Construction ─────────────────────────────────────────────────────

def test_construction_uniform():
    s = _make_solver(alpha_grid=1.0)
    assert s._alpha_grid == 1.0
    assert s.h_min == pytest.approx(LX / N)


def test_construction_nonuniform():
    s = _make_solver(alpha_grid=2.0)
    assert s._alpha_grid == 2.0
    # Before any rebuild, grid is still uniform
    assert s.h_min == pytest.approx(LX / N)


# ── Test 2: step() stability (uniform) ───────────────────────────────────────

def test_step_uniform_no_nan():
    """5-stage step on uniform grid: no NaN, KE finite after 4 steps."""
    s = _make_solver()
    psi = _droplet_ic(s)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    for i in range(4):
        psi, u, v, p = s.step(
            psi, u, v, dt=1e-3,
            rho_l=10.0, rho_g=1.0, sigma=1.0, mu=0.05, step_index=i,
        )

    for name, arr in [("psi", psi), ("u", u), ("v", v), ("p", p)]:
        assert np.all(np.isfinite(arr)), f"{name} not finite after 4 steps"


# ── Test 3: grid rebuild ─────────────────────────────────────────────────────

def test_rebuild_grid_coords_change():
    """After rebuild, grid coordinates differ from uniform."""
    s = _make_solver(alpha_grid=2.0)
    psi = _droplet_ic(s)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    uniform_coords = s._grid.coords[0].copy()
    psi, u, v = s._rebuild_grid(psi, u, v)

    assert not np.allclose(s._grid.coords[0], uniform_coords), \
        "Grid coordinates should change after rebuild"
    assert s.h_min < LX / N, \
        "h_min should decrease (nodes concentrate near interface)"


def test_rebuild_grid_mass_conservation():
    """Remap must preserve psi mass (integral over dV) to high accuracy."""
    s = _make_solver(alpha_grid=2.0)
    psi = _droplet_ic(s)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    h_uniform = LX / N
    M_before = float(np.sum(psi)) * h_uniform ** 2

    psi, u, v = s._rebuild_grid(psi, u, v)

    dV = s._grid.cell_volumes()
    M_after = float(np.sum(psi * dV))

    assert abs(M_after - M_before) / max(abs(M_before), 1e-30) < 1e-6, \
        f"Mass not conserved: {M_before:.6e} -> {M_after:.6e}"


def test_rebuild_grid_noop_uniform():
    """_rebuild_grid is a no-op when alpha_grid=1.0."""
    s = _make_solver(alpha_grid=1.0)
    psi = _droplet_ic(s)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    psi_orig = psi.copy()
    psi2, u2, v2 = s._rebuild_grid(psi, u, v)
    assert np.array_equal(psi2, psi_orig)


# ── Test 4: step with grid rebuild ───────────────────────────────────────────

def test_step_nonuniform_no_nan():
    """5-stage step with per-step grid rebuild: no NaN after 2 steps."""
    s = _make_solver(alpha_grid=2.0)
    psi = _droplet_ic(s)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    for i in range(2):
        psi, u, v, p = s.step(
            psi, u, v, dt=1e-3,
            rho_l=10.0, rho_g=1.0, sigma=1.0, mu=0.05, step_index=i,
        )

    for name, arr in [("psi", psi), ("u", u), ("v", v), ("p", p)]:
        assert np.all(np.isfinite(arr)), f"{name} not finite with grid rebuild"


# ── Test 5: dt_max uses h_min ────────────────────────────────────────────────

def test_dt_max_nonuniform():
    """dt_max must be smaller on non-uniform grid (h_min < h_uniform)."""
    from twophase.simulation.config_io import PhysicsCfg

    s_uniform = _make_solver(alpha_grid=1.0)
    s_nonunif = _make_solver(alpha_grid=2.0)

    # Trigger a rebuild so h_min < h_uniform
    psi = _droplet_ic(s_nonunif)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)
    s_nonunif._rebuild_grid(psi, u, v)

    ph = PhysicsCfg(rho_l=10.0, rho_g=1.0, sigma=1.0, mu=0.05)
    dt_u = s_uniform.dt_max(u, u, ph)
    dt_n = s_nonunif.dt_max(u, u, ph)
    assert dt_n < dt_u, "dt_max should be smaller with non-uniform grid"


def test_dt_max_uses_directional_courant_sum():
    """2-D advection CFL must use Σ_i |u_i|/h_i, not max_i |u_i|/h_min."""
    from twophase.simulation.config_io import PhysicsCfg

    s = _make_solver(alpha_grid=1.0)
    u = np.ones(s._grid.shape)
    v = np.ones(s._grid.shape)
    ph = PhysicsCfg(rho_l=1.0, rho_g=1.0, sigma=0.0, mu=1.0e-12)

    dt = s.dt_max(u, v, ph, cfl=0.2)
    expected = 0.2 / (1.0 / s.h_min + 1.0 / s.h_min)
    assert dt == pytest.approx(expected)


def test_dt_max_capillary_wave_bound_uses_h_min():
    """Capillary bound follows C_wave sqrt((rho_l+rho_g) h_min^3/(2πσ))."""
    from twophase.simulation.config_io import PhysicsCfg

    s = _make_solver(alpha_grid=1.0)
    u = np.zeros(s._grid.shape)
    v = np.zeros(s._grid.shape)
    ph = PhysicsCfg(rho_l=1.0, rho_g=1.0, sigma=1.0, mu=1.0e-12)

    dt = s.dt_max(u, v, ph, cfl=0.2)
    expected = 0.25 * np.sqrt(
        (ph.rho_l + ph.rho_g) * s.h_min ** 3 / (2.0 * np.pi * ph.sigma)
    )
    assert dt == pytest.approx(expected)


# ── Test 6: config_io round-trip ─────────────────────────────────────────────

def test_gridcfg_parse_alpha_grid():
    """_parse_grid reads canonical interface-fitting settings."""
    grid = {
        "cells": [64, 64],
        "domain": {"size": [1.0, 1.0], "boundary": "wall"},
        "distribution": {
            "type": "interface_fitted",
            "method": "gaussian_levelset",
            "alpha": 3.0,
            "eps_g_factor": 4.0,
            "schedule": "static",
        },
    }
    interface = {
        "thickness": {"mode": "nominal", "base_factor": 1.5},
    }
    g = _parse_grid(grid, interface)
    assert g.alpha_grid == 3.0
    assert g.eps_g_factor == 4.0
    assert g.dx_min_floor == 1e-6  # default


def test_gridcfg_default_uniform():
    """Disabled interface fitting forces uniform grid."""
    grid = {
        "cells": [32, 32],
        "domain": {"size": [1.0, 1.0], "boundary": "wall"},
        "distribution": {
            "type": "uniform",
            "method": "none",
            "alpha": 2.0,
            "schedule": "static",
        },
    }
    interface = {
        "thickness": {"mode": "nominal", "base_factor": 1.5},
    }
    g = _parse_grid(grid, interface)
    assert g.alpha_grid == 1.0
