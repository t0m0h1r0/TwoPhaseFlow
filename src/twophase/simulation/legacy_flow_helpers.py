"""Step-level helper functions for the legacy `TwoPhaseSimulation` core."""

from __future__ import annotations

from typing import List

from ..core.flow_state import FlowState
from ..levelset.heaviside import invert_heaviside, update_properties


def build_legacy_flow_state(sim, pressure) -> FlowState:
    ndim = sim.config.grid.ndim
    return FlowState(
        velocity=[sim.velocity[axis] for axis in range(ndim)],
        psi=sim.psi.data,
        rho=sim.rho.data,
        mu=sim.mu.data,
        kappa=sim.kappa.data,
        pressure=pressure,
    )


def advance_legacy_levelset(sim, dt: float) -> None:
    ndim = sim.config.grid.ndim
    vel_components = [sim.velocity[axis] for axis in range(ndim)]
    psi_adv = sim.ls_advect.advance(sim.psi.data, vel_components, dt)
    sim.psi.data = sim.ls_reinit.reinitialize(psi_adv)


def predict_legacy_velocity(sim, state: FlowState, dt: float) -> List:
    ndim = sim.config.grid.ndim
    vel_star_list = sim.predictor.compute(state, dt)
    for axis in range(ndim):
        sim.vel_star[axis] = vel_star_list[axis]
    return [sim.vel_star[axis] for axis in range(ndim)]


def solve_legacy_ppe(sim, vel_star: List, dt: float):
    if sim._ppe_rhs_gfm is not None:
        rhs = sim._ppe_rhs_gfm.build_rhs(
            vel_star,
            sim.phi.data,
            sim.kappa.data,
            sim.rho.data,
            dt,
        )
    else:
        div_rc = sim.rhie_chow.face_velocity_divergence(
            vel_star,
            sim.pressure.data,
            sim.rho.data,
            dt,
        )
        rhs = div_rc / dt

    delta_p = sim.ppe_solver.solve(rhs, sim.rho.data, dt, p_init=None)
    sim.pressure.data = sim.pressure.data + delta_p
    return delta_p


def correct_legacy_velocity(sim, vel_star: List, delta_p, dt: float) -> None:
    ndim = sim.config.grid.ndim
    n_hat = sim._field_ext.compute_normal(sim.phi.data)
    delta_p_ext = sim._field_ext.extend(delta_p, sim.phi.data, n_hat)
    vel_new = sim.vel_corrector.correct(vel_star, delta_p_ext, sim.rho.data, dt)
    for axis in range(ndim):
        sim.velocity[axis] = vel_new[axis]


def update_legacy_properties(sim) -> None:
    rho, mu = update_properties(
        sim.backend.xp,
        sim.psi.data,
        sim._rho_l,
        sim._rho_g,
        sim._mu_l,
        sim._mu_g,
    )
    sim.rho.data = rho
    sim.mu.data = mu


def update_legacy_curvature(sim) -> None:
    sim.kappa.data = sim.curvature_calc.compute(sim.psi.data)
    if sim._needs_phi:
        sim.phi.data = invert_heaviside(sim.backend.xp, sim.psi.data, sim.eps)
