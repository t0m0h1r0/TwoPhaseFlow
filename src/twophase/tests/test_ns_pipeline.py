"""
Unit tests for ns_pipeline.py — §12/§13 5-stage predictor-corrector.

Tests cover:
  1. TwoPhaseNSSolver construction (uniform and non-uniform)
  2. 5-stage step() stability on uniform grid (no NaN, KE bounded)
  3. Grid rebuild: coords change, mass conserved, fields remapped
  4. dt_max uses h_min on non-uniform grids
  5. config_io round-trip: alpha_grid flows from YAML dict → solver
"""

from types import SimpleNamespace

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
    """Capillary bound uses cfl as C_wave in the wave-resolution scale."""
    from twophase.simulation.config_io import PhysicsCfg

    s = _make_solver(alpha_grid=1.0)
    u = np.zeros(s._grid.shape)
    v = np.zeros(s._grid.shape)
    ph = PhysicsCfg(rho_l=1.0, rho_g=1.0, sigma=1.0, mu=1.0e-12)

    dt = s.dt_max(u, v, ph, cfl=0.2)
    expected = 0.2 * np.sqrt(
        (ph.rho_l + ph.rho_g) * s.h_min ** 3 / (2.0 * np.pi * ph.sigma)
    )
    assert dt == pytest.approx(expected)


def test_dt_max_accepts_separate_capillary_cfl():
    """Theory policy can lower the capillary constant without changing advective CFL."""
    from twophase.simulation.config_io import PhysicsCfg

    s = _make_solver(alpha_grid=1.0)
    u = np.zeros(s._grid.shape)
    v = np.zeros(s._grid.shape)
    ph = PhysicsCfg(rho_l=1.0, rho_g=1.0, sigma=1.0, mu=1.0e-12)

    dt = s.dt_max(u, v, ph, cfl=0.2, cfl_capillary=0.05)
    expected = 0.05 * np.sqrt(
        (ph.rho_l + ph.rho_g) * s.h_min ** 3 / (2.0 * np.pi * ph.sigma)
    )
    assert dt == pytest.approx(expected)


def test_dt_budget_reports_active_limiter_and_candidates():
    """Runner diagnostics need all timestep candidates, not only the minimum."""
    from twophase.simulation.config_io import PhysicsCfg

    s = _make_solver(alpha_grid=1.0)
    u = np.zeros(s._grid.shape)
    v = np.zeros(s._grid.shape)
    ph = PhysicsCfg(rho_l=1.0, rho_g=1.0, sigma=1.0, mu=1.0e-12)

    budget = s.dt_budget(u, v, ph, cfl=0.2, cfl_capillary=0.05)
    diagnostics = budget.diagnostics()

    assert budget.limiter == "capillary"
    assert budget.dt == pytest.approx(budget.dt_capillary)
    assert diagnostics["dt_limiter_code"] == pytest.approx(3.0)
    assert diagnostics["dt_capillary"] == pytest.approx(budget.dt)


def test_dt_budget_treats_zero_viscosity_as_no_viscous_limit():
    """Inviscid configurations must not fail while evaluating the CFL budget."""
    from twophase.simulation.config_io import PhysicsCfg

    s = _make_solver(alpha_grid=1.0)
    u = np.ones(s._grid.shape)
    v = np.zeros(s._grid.shape)
    ph = PhysicsCfg(rho_l=1.0, rho_g=1.0, sigma=0.0, mu=0.0, mu_l=0.0, mu_g=0.0)

    budget = s.dt_budget(u, v, ph, cfl=0.2)

    assert np.isinf(budget.dt_viscous)
    assert budget.limiter == "advective"


def test_dt_max_crank_nicolson_omits_viscous_stability_limit():
    """Implicit CN viscosity should not be governed by the CFL multiplier."""
    from twophase.simulation.config_io import PhysicsCfg

    s = _make_solver(alpha_grid=1.0, viscous_time_scheme="crank_nicolson")
    u = np.ones(s._grid.shape)
    v = np.ones(s._grid.shape)
    ph = PhysicsCfg(rho_l=1.0, rho_g=1.0, sigma=0.0, mu=1.0e6)

    dt = s.dt_max(u, v, ph, cfl=0.2)
    expected = 0.2 / (1.0 / s.h_min + 1.0 / s.h_min)
    assert dt == pytest.approx(expected)


def test_dt_max_implicit_bdf2_omits_viscous_stability_limit():
    """True implicit BDF2 viscosity should not impose the explicit ν/h² bound."""
    from twophase.simulation.config_io import PhysicsCfg

    s = _make_solver(
        alpha_grid=1.0,
        convection_time_scheme="imex_bdf2",
        viscous_time_scheme="implicit_bdf2",
    )
    u = np.ones(s._grid.shape)
    v = np.ones(s._grid.shape)
    ph = PhysicsCfg(rho_l=1.0, rho_g=1.0, sigma=0.0, mu=1.0e6)

    dt = s.dt_max(u, v, ph, cfl=0.2)
    expected = 0.2 / (1.0 / s.h_min + 1.0 / s.h_min)
    assert dt == pytest.approx(expected)


def test_imex_bdf2_predictor_uses_ext2_and_projection_dt():
    """Second BDF2 step must use EXT2 convection and γΔt projection scaling."""
    from twophase.backend import Backend
    from twophase.simulation.ns_step_services import compute_ns_predictor_stage
    from twophase.simulation.ns_step_state import NSStepInputs, NSStepState

    backend = Backend(use_gpu=False)
    xp = backend.xp
    shape = (2, 2)

    class ConstantConvection:
        def compute(self, ctx):
            return xp.full_like(ctx.velocity[0], 3.0), xp.full_like(ctx.velocity[1], -4.0)

    class RecordingPredictor:
        def predict_bdf2(
            self,
            u,
            v,
            u_prev,
            v_prev,
            conv_u,
            conv_v,
            mu,
            rho,
            dt,
            ccd,
            buoy_v=None,
            psi=None,
        ):
            self.u_prev = xp.copy(u_prev)
            self.v_prev = xp.copy(v_prev)
            self.conv_u = xp.copy(conv_u)
            self.conv_v = xp.copy(conv_v)
            self.dt = dt
            return xp.copy(u), xp.copy(v)

    predictor = RecordingPredictor()
    inputs = NSStepInputs(
        psi=xp.ones(shape),
        u=xp.full(shape, 2.0),
        v=xp.full(shape, -1.0),
        dt=0.3,
        rho_l=1.0,
        rho_g=1.0,
        sigma=0.0,
        mu=1.0,
    )
    state = NSStepState.from_inputs(inputs, backend=backend)
    state.rho = xp.ones(shape)
    state.mu_field = xp.ones(shape)
    conv_prev = (xp.full(shape, 1.0), xp.full(shape, 2.0))
    velocity_prev = (xp.full(shape, 0.5), xp.full(shape, -0.25))

    state, conv_ready, next_conv, velocity_ready, next_velocity = compute_ns_predictor_stage(
        state,
        backend=backend,
        ccd=None,
        conv_term=ConstantConvection(),
        viscous_predictor=predictor,
        scheme_runtime=SimpleNamespace(convection_time_scheme="imex_bdf2"),
        conv_ab2_ready=True,
        conv_prev=conv_prev,
        velocity_bdf2_ready=True,
        velocity_prev=velocity_prev,
        projection_consistent_buoyancy=True,
    )

    assert state.projection_dt == pytest.approx(0.2)
    assert predictor.dt == pytest.approx(0.3)
    np.testing.assert_allclose(predictor.conv_u, xp.full(shape, 5.0))
    np.testing.assert_allclose(predictor.conv_v, xp.full(shape, -10.0))
    np.testing.assert_allclose(predictor.u_prev, velocity_prev[0])
    np.testing.assert_allclose(predictor.v_prev, velocity_prev[1])
    assert conv_ready is True
    assert velocity_ready is True
    np.testing.assert_allclose(next_conv[0], xp.full(shape, 3.0))
    np.testing.assert_allclose(next_velocity[0], state.u)


def test_implicit_bdf2_viscous_predictor_zero_operator_matches_formula():
    """With V=0, the matrix-free solve reduces exactly to the BDF2 affine RHS."""
    from twophase.backend import Backend
    from twophase.simulation.viscous_predictors import ImplicitBDF2ViscousPredictor

    backend = Backend(use_gpu=False)
    xp = backend.xp

    class ZeroViscous:
        Re = 1.0

        def _evaluate(self, velocity_components, mu, rho, ccd, psi=None):
            return [xp.zeros_like(component) for component in velocity_components]

    predictor = ImplicitBDF2ViscousPredictor(
        backend,
        ZeroViscous(),
        tolerance=1.0e-12,
        max_iterations=5,
        restart=5,
        solver="gmres",
    )
    u = xp.array([[1.0, 2.0], [3.0, 4.0]])
    v = xp.array([[0.5, 0.25], [-0.25, -0.5]])
    u_prev = xp.zeros_like(u)
    v_prev = xp.ones_like(v)
    conv_u = xp.full_like(u, 0.75)
    conv_v = xp.full_like(v, -0.5)
    dt = 0.12

    u_star, v_star = predictor.predict_bdf2(
        u,
        v,
        u_prev,
        v_prev,
        conv_u,
        conv_v,
        xp.ones_like(u),
        xp.ones_like(u),
        dt,
        ccd=None,
    )

    expected_u = (4.0 / 3.0) * u - (1.0 / 3.0) * u_prev + (2.0 / 3.0) * dt * conv_u
    expected_v = (4.0 / 3.0) * v - (1.0 / 3.0) * v_prev + (2.0 / 3.0) * dt * conv_v
    np.testing.assert_allclose(
        backend.asnumpy(u_star),
        backend.asnumpy(expected_u),
        rtol=1.0e-12,
        atol=1.0e-12,
    )
    np.testing.assert_allclose(
        backend.asnumpy(v_star),
        backend.asnumpy(expected_v),
        rtol=1.0e-12,
        atol=1.0e-12,
    )


def test_implicit_bdf2_viscous_dc_zero_operator_matches_formula():
    """With V=0, the DC low Helmholtz solve reduces to the BDF2 affine RHS."""
    from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
    from twophase.simulation.viscous_predictors import ImplicitBDF2ViscousPredictor

    solver_runtime = TwoPhaseNSSolver(4, 4, 1.0, 1.0)
    backend = solver_runtime._backend
    xp = backend.xp

    class ZeroViscous:
        Re = 1.0

        def _evaluate(self, velocity_components, mu, rho, ccd, psi=None):
            return [xp.zeros_like(component) for component in velocity_components]

    predictor = ImplicitBDF2ViscousPredictor(
        backend,
        ZeroViscous(),
        tolerance=1.0e-12,
        dc_corrections=2,
        dc_relaxation=0.8,
    )
    shape = solver_runtime._grid.shape
    u = xp.arange(np.prod(shape), dtype=float).reshape(shape) / 10.0
    v = xp.flip(u, axis=0)
    u_prev = xp.zeros_like(u)
    v_prev = xp.ones_like(v)
    conv_u = xp.full_like(u, 0.25)
    conv_v = xp.full_like(v, -0.125)
    dt = 0.09

    u_star, v_star = predictor.predict_bdf2(
        u,
        v,
        u_prev,
        v_prev,
        conv_u,
        conv_v,
        xp.zeros_like(u),
        xp.ones_like(u),
        dt,
        solver_runtime._ccd,
    )

    expected_u = (4.0 / 3.0) * u - (1.0 / 3.0) * u_prev + (2.0 / 3.0) * dt * conv_u
    expected_v = (4.0 / 3.0) * v - (1.0 / 3.0) * v_prev + (2.0 / 3.0) * dt * conv_v
    np.testing.assert_allclose(
        backend.asnumpy(u_star),
        backend.asnumpy(expected_u),
        rtol=1.0e-12,
        atol=1.0e-12,
    )
    np.testing.assert_allclose(
        backend.asnumpy(v_star),
        backend.asnumpy(expected_v),
        rtol=1.0e-12,
        atol=1.0e-12,
    )
    assert predictor.last_diagnostics["viscous_dc_low_factor_reuse"] == pytest.approx(1.0)


def test_implicit_bdf2_viscous_dc_reduces_high_residual():
    """DC iterations reduce the high-order viscous Helmholtz residual."""
    from twophase.ns_terms.viscous import ViscousTerm
    from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
    from twophase.simulation.viscous_predictors import ImplicitBDF2ViscousPredictor

    solver_runtime = TwoPhaseNSSolver(
        8,
        8,
        1.0,
        1.0,
        use_gpu=False,
        convection_time_scheme="imex_bdf2",
        viscous_time_scheme="implicit_bdf2",
    )
    X, Y = solver_runtime.X, solver_runtime.Y
    u = np.sin(np.pi * X) * np.sin(np.pi * Y)
    v = np.zeros_like(u)
    zeros = np.zeros_like(u)
    mu = np.full_like(u, 0.05)
    rho = np.ones_like(u)
    viscous = ViscousTerm(
        solver_runtime._backend,
        Re=1.0,
        cn_viscous=True,
        spatial_scheme="ccd_bulk",
    )
    predictor = ImplicitBDF2ViscousPredictor(
        solver_runtime._backend,
        viscous,
        tolerance=1.0e-10,
        dc_corrections=4,
        dc_relaxation=0.8,
    )

    predictor.predict_bdf2(
        u,
        v,
        u,
        v,
        zeros,
        zeros,
        mu,
        rho,
        0.01,
        solver_runtime._ccd,
    )

    history = predictor.last_residual_history
    assert len(history) == 4
    assert all(after < before for before, after in zip(history, history[1:]))
    assert history[-1] < 0.05 * history[0]


def test_implicit_bdf2_viscous_dc_scalar_low_reduces_high_residual():
    """Scalar low Helmholtz remains a valid DC contraction operator."""
    from twophase.ns_terms.viscous import ViscousTerm
    from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
    from twophase.simulation.viscous_predictors import ImplicitBDF2ViscousPredictor

    solver_runtime = TwoPhaseNSSolver(
        8,
        8,
        1.0,
        1.0,
        use_gpu=False,
        convection_time_scheme="imex_bdf2",
        viscous_time_scheme="implicit_bdf2",
    )
    X, Y = solver_runtime.X, solver_runtime.Y
    u = np.sin(np.pi * X) * np.sin(np.pi * Y)
    v = 0.2 * np.cos(np.pi * X) * np.sin(np.pi * Y)
    zeros = np.zeros_like(u)
    mu = 0.02 + 0.01 * (X + Y)
    rho = 1.0 + 0.2 * np.sin(np.pi * X) ** 2
    viscous = ViscousTerm(
        solver_runtime._backend,
        Re=1.0,
        cn_viscous=True,
        spatial_scheme="ccd_bulk",
    )
    predictor = ImplicitBDF2ViscousPredictor(
        solver_runtime._backend,
        viscous,
        tolerance=1.0e-10,
        dc_corrections=4,
        dc_relaxation=0.8,
        dc_low_operator="scalar",
    )

    predictor.predict_bdf2(
        u,
        v,
        u,
        v,
        zeros,
        zeros,
        mu,
        rho,
        0.01,
        solver_runtime._ccd,
    )

    history = predictor.last_residual_history
    assert predictor.last_diagnostics["viscous_dc_low_operator_scalar"] == pytest.approx(1.0)
    assert len(history) == 4
    assert all(after < before for before, after in zip(history, history[1:]))
    assert history[-1] < 0.25 * history[0]


def test_pressure_projection_uses_projection_dt():
    """PPE RHS and fallback corrector must share γΔt, not the raw Δt."""
    from twophase.backend import Backend
    from twophase.simulation.ns_step_services import (
        correct_ns_velocity_stage,
        solve_ns_pressure_stage,
    )
    from twophase.simulation.ns_step_state import NSStepInputs, NSStepState

    backend = Backend(use_gpu=False)
    xp = backend.xp
    shape = (2, 2)
    state = NSStepState.from_inputs(
        NSStepInputs(
            psi=xp.ones(shape),
            u=xp.zeros(shape),
            v=xp.zeros(shape),
            dt=0.3,
            rho_l=1.0,
            rho_g=1.0,
            sigma=0.0,
            mu=1.0,
        ),
        backend=backend,
    )
    state.projection_dt = 0.2
    state.rho = xp.ones(shape)
    state.f_x = xp.zeros(shape)
    state.f_y = xp.zeros(shape)
    state.u_star = xp.ones(shape)
    state.v_star = xp.ones(shape)

    class ConstantDivergence:
        def divergence(self, components):
            if np.allclose(components[0], 0.0) and np.allclose(components[1], 0.0):
                return xp.zeros(shape)
            return xp.full(shape, 6.0)

    class CapturingPPE:
        def solve(self, rhs, rho, dt=0.0, p_init=None):
            self.rhs = xp.copy(rhs)
            self.dt = dt
            return xp.zeros_like(rhs)

    ppe_solver = CapturingPPE()
    state, _, _ = solve_ns_pressure_stage(
        state,
        backend=backend,
        div_op=ConstantDivergence(),
        ppe_solver=ppe_solver,
        p_prev_dev=None,
        surface_tension_scheme="none",
    )
    assert ppe_solver.dt == pytest.approx(0.2)
    np.testing.assert_allclose(ppe_solver.rhs, xp.full(shape, 30.0))

    class ConstantGradient:
        def gradient(self, pressure, axis):
            return xp.full(shape, 2.0 + axis)

    state = correct_ns_velocity_stage(
        state,
        backend=backend,
        pressure_grad_op=ConstantGradient(),
        face_flux_projection=False,
        preserve_projected_faces=False,
        fccd_div_op=None,
        div_op=ConstantDivergence(),
        ppe_runtime=SimpleNamespace(
            ppe_solver_name="fvm_iterative",
            ppe_coefficient_scheme="phase_density",
        ),
        bc_type="periodic",
        apply_velocity_bc=lambda u, v, bc_hook, bc_type: None,
    )
    np.testing.assert_allclose(state.u, xp.full(shape, 1.0 - 0.2 * 2.0))
    np.testing.assert_allclose(state.v, xp.full(shape, 1.0 - 0.2 * 3.0))


# ── Test 6: config_io round-trip ─────────────────────────────────────────────

def test_gridcfg_parse_alpha_grid():
    """_parse_grid reads canonical interface-fitting settings."""
    grid = {
        "cells": [64, 64],
        "domain": {"size": [1.0, 1.0], "boundary": "wall"},
        "distribution": {
            "schedule": 0,
            "axes": {
                "x": {"type": "uniform"},
                "y": {
                    "type": "nonuniform",
                    "monitors": {
                        "interface": {
                            "alpha": 3.0,
                            "eps_g_factor": 4.0,
                        },
                    },
                },
            },
        },
    }
    interface = {
        "thickness": {"mode": "nominal", "base_factor": 1.5},
    }
    g = _parse_grid(grid, interface)
    assert g.alpha_grid == 3.0
    assert g.fitting_axes == (False, True)
    assert g.fitting_alpha_grid == (1.0, 3.0)
    assert g.eps_g_factor == 2.0
    assert g.fitting_eps_g_factor == (2.0, 4.0)
    assert g.dx_min_floor == 1e-6  # default
    assert g.grid_rebuild_freq == 0


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
