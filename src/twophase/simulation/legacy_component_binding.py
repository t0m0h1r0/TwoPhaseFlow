"""Component binding helpers for the legacy `TwoPhaseSimulation` core."""

from __future__ import annotations

from ..core.field import ScalarField, VectorField


def bind_legacy_simulation_components(sim, components) -> None:
    sim.config = components.config
    sim.backend = components.backend
    sim.grid = components.grid
    sim.eps = components.eps
    sim.ccd = components.ccd

    sim.psi = ScalarField(components.grid, components.backend)
    sim.rho = ScalarField(components.grid, components.backend)
    sim.mu = ScalarField(components.grid, components.backend)
    sim.kappa = ScalarField(components.grid, components.backend)
    sim.phi = ScalarField(components.grid, components.backend)
    sim.pressure = ScalarField(components.grid, components.backend)
    sim.velocity = VectorField(components.grid, components.backend)
    sim.vel_star = VectorField(components.grid, components.backend)

    sim.ls_advect = components.ls_advect
    sim.ls_reinit = components.ls_reinit
    sim.curvature_calc = components.curvature_calc
    sim.predictor = components.predictor
    sim.ppe_solver = components.ppe_solver
    sim.rhie_chow = components.rhie_chow
    sim.vel_corrector = components.vel_corrector
    sim.cfl_calc = components.cfl_calc
    sim._bc_handler = components.bc_handler
    sim._diagnostics = components.diagnostics
    sim._ppe_rhs_gfm = components.ppe_rhs_gfm
    sim._field_ext = components.field_extender
    sim._needs_phi = (
        (components.field_extender is not None and not components.field_extender.is_null_extender)
        or (components.ppe_rhs_gfm is not None)
    )

    sim.time = 0.0
    sim.step = 0
    sim._rho_l = 1.0
    sim._rho_g = components.config.fluid.rho_ratio
    sim._mu_l = 1.0
    sim._mu_g = components.config.fluid.mu_ratio
