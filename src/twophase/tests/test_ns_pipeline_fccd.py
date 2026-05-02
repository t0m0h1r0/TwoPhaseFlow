"""
CHK-160 integration coverage: FCCD + Ridge-Eikonal + α=2 + GFM-style
reproject + InterfaceLimitedFilter HFE, end-to-end through
``TwoPhaseNSSolver``.

Covers the minimum stack the user requested for
``experiment/ch13/config/ch13_04_capwave_fullstack_alpha2.yaml`` at
``N=16`` so the test stays fast, 2 steps, sigma>0.  No NaN, finite KE,
non-trivial ψ advection after the stack swap.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ppe.defect_correction import PPESolverDefectCorrection
from twophase.ppe.fccd_matrixfree import PPESolverFCCDMatrixFree
from twophase.simulation.divergence_ops import FCCDDivergenceOperator
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.simulation.ns_step_services import _interface_supported_curvature
from twophase.levelset.curvature_psi import CurvatureCalculatorPsi
from twophase.levelset.fccd_advection import FCCDLevelSetAdvection
from twophase.simulation.config_io import ExperimentConfig
from twophase.simulation.face_projection import reconstruct_nodes_from_faces
from twophase.levelset.transport_strategy import PsiDirectTransport
from twophase.simulation.velocity_reprojector import (
    ConsistentIIMReprojector,
    VariableDensityReprojector,
)
from twophase.ppe.interfaces import IPPESolver


N = 16
L = 1.0


def _make_nonuniform_fccd_wall_stack():
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(8, 7), L=(1.0, 1.4), alpha_grid=2.0),
    )
    grid = Grid(cfg.grid, backend)
    for axis, power in enumerate((1.25, 1.4)):
        length = grid.L[axis]
        xi = np.linspace(0.0, 1.0, grid.N[axis] + 1)
        coords = length * xi ** power
        coords[-1] = length
        grid.coords[axis] = coords
        cell_width = np.diff(coords)
        node_width = np.empty(grid.N[axis] + 1)
        node_width[0] = cell_width[0]
        node_width[-1] = cell_width[-1]
        node_width[1:-1] = 0.5 * (cell_width[:-1] + cell_width[1:])
        grid.h[axis] = node_width
    ccd = CCDSolver(grid, backend, bc_type="wall")
    grid._build_metrics(ccd=ccd)
    fccd = FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd)
    return backend, grid, fccd


def test_fccd_projection_divergence_matches_ppe_operator_nonuniform_wall():
    """Projection and FCCD PPE must share the same metric and face space."""
    backend, grid, fccd = _make_nonuniform_fccd_wall_stack()
    div_op = FCCDDivergenceOperator(fccd)
    ppe = PPESolverFCCDMatrixFree(backend, SimulationConfig(), grid, fccd)
    rng = np.random.default_rng(314)
    pressure = rng.standard_normal(grid.shape)
    rho = 1.0 + rng.uniform(0.0, 0.5, grid.shape)

    ppe.prepare_operator(rho)
    ppe_apply = np.asarray(ppe._apply_operator_core(np.asarray(pressure))).ravel()
    projection_apply = np.asarray(
        div_op.divergence_from_faces(
            div_op.pressure_fluxes(pressure, rho, pressure_gradient="fccd")
        )
    ).ravel()
    projection_apply_public_name = np.asarray(
        div_op.divergence_from_faces(
            div_op.pressure_fluxes(pressure, rho, pressure_gradient="fccd_flux")
        )
    ).ravel()

    mask = np.ones_like(ppe_apply, dtype=bool)
    mask[ppe._pin_dof] = False
    np.testing.assert_allclose(
        projection_apply[mask],
        ppe_apply[mask],
        rtol=1.0e-12,
        atol=1.0e-12,
    )
    np.testing.assert_allclose(
        projection_apply_public_name[mask],
        ppe_apply[mask],
        rtol=1.0e-12,
        atol=1.0e-12,
    )


def test_fccd_projection_rejects_unknown_face_options():
    """Chapter 8 face subsystem must fail closed instead of changing locus."""
    backend, grid, fccd = _make_nonuniform_fccd_wall_stack()
    div_op = FCCDDivergenceOperator(fccd)
    pressure = np.zeros(grid.shape)
    rho = np.ones(grid.shape)

    with pytest.raises(ValueError, match="pressure_gradient"):
        div_op.pressure_fluxes(pressure, rho, pressure_gradient="central")
    with pytest.raises(ValueError, match="coefficient_scheme"):
        div_op.pressure_fluxes(pressure, rho, coefficient_scheme="arithmetic")
    with pytest.raises(ValueError, match="interface_coupling_scheme"):
        div_op.pressure_fluxes(
            pressure,
            rho,
            coefficient_scheme="phase_separated",
            interface_coupling_scheme="smoothed_jump",
        )


def test_fccd_matrixfree_enforces_mixed_periodic_image_rows():
    """Mixed periodic-wall PPE must constrain duplicate pressure image nodes."""
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(8, 8), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic_wall")
    fccd = FCCDSolver(grid, backend, bc_type="periodic_wall", ccd_solver=ccd)
    ppe = PPESolverFCCDMatrixFree(backend, SimulationConfig(), grid, fccd)
    rho = np.ones(grid.shape)
    pressure = np.zeros(grid.shape)
    pressure[-1, :] = np.linspace(1.0, 2.0, grid.shape[1])

    ppe.prepare_operator(rho)
    applied = np.asarray(ppe.apply(pressure))
    np.testing.assert_allclose(applied[-1, :], pressure[-1, :] - pressure[0, :])

    rhs = np.zeros(grid.shape)
    rhs[-1, :] = 1.0
    solved = np.asarray(ppe.solve(rhs, rho))
    np.testing.assert_allclose(solved[-1, :], solved[0, :], atol=1.0e-14)


def test_defect_correction_preserves_mixed_periodic_pressure_space():
    """DC wrapper must not reintroduce duplicate periodic image DOFs."""
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(8, 8), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic_wall")
    fccd = FCCDSolver(grid, backend, bc_type="periodic_wall", ccd_solver=ccd)
    operator = PPESolverFCCDMatrixFree(backend, SimulationConfig(), grid, fccd)
    dc = PPESolverDefectCorrection(backend, grid, operator, operator)

    pressure = np.zeros(grid.shape)
    pressure[-1, :] = np.linspace(1.0, 2.0, grid.shape[1])
    pressure_synced = np.asarray(dc._enforce_pressure_gauge(pressure))
    np.testing.assert_allclose(pressure_synced[-1, :], pressure_synced[0, :])

    rhs = np.ones(grid.shape)
    rhs_projected = np.asarray(dc._enforce_rhs_compatibility(rhs))
    np.testing.assert_allclose(rhs_projected[-1, :], 0.0)


def test_phase_separated_fccd_projection_matches_ppe_operator_nonuniform_wall():
    """Projection must cut the same cross-phase faces as phase-separated PPE."""
    backend, grid, fccd = _make_nonuniform_fccd_wall_stack()
    div_op = FCCDDivergenceOperator(fccd)
    cfg = type(
        "Cfg",
        (),
        {
            "ppe_coefficient_scheme": "phase_separated",
            "ppe_interface_coupling_scheme": "jump_decomposition",
        },
    )()
    ppe = PPESolverFCCDMatrixFree(backend, cfg, grid, fccd)
    rng = np.random.default_rng(2718)
    pressure = rng.standard_normal(grid.shape)
    rho = np.ones(grid.shape)
    rho[: grid.N[0] // 2 + 1, :] = 1000.0

    ppe.prepare_operator(rho)
    ppe_apply = np.asarray(ppe._apply_operator_core(np.asarray(pressure))).ravel()
    projection_apply = np.asarray(
        div_op.divergence_from_faces(
            div_op.pressure_fluxes(
                pressure,
                rho,
                pressure_gradient="fccd",
                coefficient_scheme="phase_separated",
            )
        )
    ).ravel()

    np.testing.assert_allclose(
        projection_apply,
        ppe_apply,
        rtol=1.0e-12,
        atol=1.0e-12,
    )


def test_phase_separated_corrector_forwards_projection_coefficient_scheme():
    """NS corrector must use the same face coefficient scheme as the PPE."""
    from twophase.simulation.ns_step_services import correct_ns_velocity_stage
    from twophase.simulation.ns_step_state import NSStepState

    class GradientStub:
        def gradient(self, pressure, axis):
            return np.zeros_like(pressure)

    class ProjectionRecorder:
        def __init__(self):
            self.kwargs = None

        def project_faces(self, components, p, rho, dt, force_components=None, **kwargs):
            self.kwargs = kwargs
            return [np.array(component, copy=True) for component in components]

        def reconstruct_nodes(self, face_components):
            return face_components

    arr = np.zeros((3, 3))
    state = NSStepState(
        psi=arr,
        u=arr,
        v=arr,
        dt=1.0e-3,
        rho_l=1000.0,
        rho_g=1.0,
        sigma=0.0,
        mu=0.0,
        g_acc=0.0,
        rho_ref=500.5,
        mu_l=None,
        mu_g=None,
        bc_hook=None,
        step_index=0,
        rho=np.ones_like(arr),
        f_x=np.zeros_like(arr),
        f_y=np.zeros_like(arr),
        u_star=np.zeros_like(arr),
        v_star=np.zeros_like(arr),
        p_corrector=np.zeros_like(arr),
    )
    backend = type("BackendStub", (), {"xp": np})()
    ppe_runtime = type(
        "PPERuntime",
        (),
        {
            "ppe_solver_name": "fccd_iterative",
            "ppe_coefficient_scheme": "phase_separated",
        },
    )()
    projection = ProjectionRecorder()

    correct_ns_velocity_stage(
        state,
        backend=backend,
        pressure_grad_op=GradientStub(),
        face_flux_projection=True,
        preserve_projected_faces=True,
        fccd_div_op=projection,
        div_op=projection,
        ppe_runtime=ppe_runtime,
        bc_type="wall",
        apply_velocity_bc=lambda *_args: None,
    )

    assert projection.kwargs == {
        "pressure_gradient": "fccd",
        "coefficient_scheme": "phase_separated",
    }


def _mode2_ic(solver: TwoPhaseNSSolver) -> np.ndarray:
    """Prolate-perturbed disc: ψ=1 inside, ψ=0 outside, ε-widening applied."""
    X, Y = solver.X, solver.Y
    Xh = np.asarray(solver._backend.to_host(X))
    Yh = np.asarray(solver._backend.to_host(Y))
    r = np.sqrt((Xh - 0.5) ** 2 + (Yh - 0.5) ** 2)
    theta = np.arctan2(Yh - 0.5, Xh - 0.5)
    R_iface = 0.25 * (1.0 + 0.05 * np.cos(2.0 * theta))
    phi = R_iface - r
    return solver.psi_from_phi(phi)


def test_psi_direct_transport_reinitializes_after_initial_step_only():
    class IdentityAdvection:
        def advance(self, psi, velocity, dt):
            return psi

    class ShiftReinitializer:
        def reinitialize(self, psi):
            return psi + 1.0

    transport = PsiDirectTransport(
        Backend(use_gpu=False),
        IdentityAdvection(),
        ShiftReinitializer(),
        reinit_every=2,
    )
    psi = np.zeros((3, 3))
    velocity = [np.zeros_like(psi), np.zeros_like(psi)]

    assert np.allclose(transport.advance(psi, velocity, 0.1, step_index=0), psi)
    assert np.allclose(transport.advance(psi, velocity, 0.1, step_index=2), psi + 1.0)


def test_psi_direct_transport_applies_ch6_mass_correction():
    class LossyAdvection:
        def advance(self, psi, velocity, dt):
            return 0.9 * psi

    class IdentityReinitializer:
        def reinitialize(self, psi):
            return psi

    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(4, 4), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    X, Y = grid.meshgrid()
    psi = 0.5 + 0.1 * np.sin(2.0 * np.pi * X) * np.sin(2.0 * np.pi * Y)
    velocity = [np.zeros_like(psi), np.zeros_like(psi)]
    transport = PsiDirectTransport(
        backend,
        LossyAdvection(),
        IdentityReinitializer(),
        reinit_every=0,
        grid=grid,
        mass_correction=True,
    )

    mass_before = np.sum(psi * grid.cell_volumes())
    psi_new = transport.advance(psi, velocity, 0.1, step_index=1)
    mass_after = np.sum(psi_new * grid.cell_volumes())

    assert mass_after == pytest.approx(mass_before, rel=1.0e-12, abs=1.0e-12)


@pytest.mark.parametrize(
    "advection_scheme,convection_scheme",
    [("fccd_flux", "fccd_flux"), ("fccd_nodal", "fccd_nodal")],
)
def test_fullstack_two_steps_no_nan(advection_scheme: str, convection_scheme: str):
    """FCCD × Ridge-Eikonal × α=2 × consistent_gfm × HFE — 2 steps stable."""
    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        alpha_grid=2.0,
        use_local_eps=True,
        eps_factor=1.5,
        grid_rebuild_freq=0,         # static α=2 grid
        reinit_method="ridge_eikonal",
        reinit_every=2,
        reinit_eps_scale=1.4,
        ridge_sigma_0=3.0,
        reproject_mode="consistent_gfm",
        phi_primary_transport=True,
        advection_scheme=advection_scheme,
        convection_scheme=convection_scheme,
    )
    psi = _mode2_ic(solver)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)
    # Mimic run_simulation()'s one-shot rebuild for static α>1 configs, so
    # _fvm_pressure_grad finds its precomputed spacing (grid_rebuild_freq=0).
    psi, u, v = solver._rebuild_grid(psi, u, v, rho_l=833.0, rho_g=1.0)
    for i in range(2):
        psi, u, v, p = solver.step(
            psi, u, v, dt=5e-4,
            rho_l=833.0, rho_g=1.0, sigma=1.0, mu=0.05, step_index=i,
        )
    for name, arr in [("psi", psi), ("u", u), ("v", v), ("p", p)]:
        assert np.all(np.isfinite(arr)), f"{name} not finite"
    # ψ bounded in [0, 1] to within tiny drift (CLS invariant)
    assert float(np.min(psi)) >= -1e-10
    assert float(np.max(psi)) <= 1.0 + 1e-10


def test_fccd_solver_is_shared():
    """Sanity: convection + advection share one FCCDSolver instance."""
    from twophase.ns_terms.fccd_convection import FCCDConvectionTerm

    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        alpha_grid=2.0,
        advection_scheme="fccd_flux",
        convection_scheme="fccd_flux",
    )
    assert solver._fccd is not None
    assert isinstance(solver._conv_term, FCCDConvectionTerm)
    assert solver._conv_term._fccd is solver._fccd
    assert solver._adv._fccd is solver._fccd


def test_ch13_fccd_hfe_uccd_yaml_builds_solver():
    """Checked-in ch13 YAML is executable: FCCD/HFE stack + UCCD convection."""
    from twophase.ppe.defect_correction import PPESolverDefectCorrection
    from twophase.ppe.fccd_matrixfree import PPESolverFCCDMatrixFree

    path = (
        Path(__file__).resolve().parents[3]
        / "experiment/ch13/config/ch13_capillary_water_air_alpha2_n128.yaml"
    )
    cfg = ExperimentConfig.from_yaml(path)
    solver = TwoPhaseNSSolver.from_config(cfg)

    assert solver._fccd is not None
    assert solver._advection_scheme == "fccd_flux"
    assert solver._convection_scheme == "uccd6"
    assert solver._pressure_gradient_scheme == "fccd_flux"
    assert solver._surface_tension_gradient_scheme == "none"
    assert solver._surface_tension_scheme == "pressure_jump"
    assert solver._ppe_coefficient_scheme == "phase_separated"
    assert solver._ppe_interface_coupling_scheme == "jump_decomposition"
    assert solver._hfe is not None
    assert isinstance(solver._transport, PsiDirectTransport)
    assert solver._interface_runtime.rebuild_freq == 0
    assert solver._interface_runtime.reinit_every == 20
    assert isinstance(solver._ppe_solver, PPESolverDefectCorrection)
    assert isinstance(solver._ppe_solver.base_solver, PPESolverFCCDMatrixFree)
    assert solver._div_op is solver._fccd_div_op
    assert solver._viscous_spatial_scheme == "ccd_bulk"


def test_ch13_capillary_wave_yaml_builds_initial_field():
    """Capillary-wave YAML should build a sinusoidal two-phase initial field."""
    path = (
        Path(__file__).resolve().parents[3]
        / "experiment/ch13/config/ch13_capillary_water_air_alpha2_n128.yaml"
    )
    cfg = ExperimentConfig.from_yaml(path)
    solver = TwoPhaseNSSolver.from_config(cfg)

    psi = solver.build_ic(cfg)
    assert psi.shape == solver._grid.shape

    x0 = int(np.argmin(np.abs(np.asarray(solver._grid.coords[0]) - 0.0)))
    y_low = int(np.argmin(np.abs(np.asarray(solver._grid.coords[1]) - 0.25)))
    y_high = int(np.argmin(np.abs(np.asarray(solver._grid.coords[1]) - 0.75)))
    assert psi[x0, y_low] > 0.5
    assert psi[x0, y_high] < 0.5


def test_ch13_capillary_curvature_is_supported_on_interface_band():
    """HFE must not reintroduce pressure-jump curvature in saturation tails."""
    path = (
        Path(__file__).resolve().parents[3]
        / "experiment/ch13/config/ch13_capillary_water_air_alpha2_n128.yaml"
    )
    cfg = ExperimentConfig.from_yaml(path)
    solver = TwoPhaseNSSolver.from_config(cfg)
    psi = solver.build_ic(cfg)
    u, v = solver.build_velocity(cfg, psi)
    psi, _, _ = solver._rebuild_grid(psi, u, v, cfg.physics.rho_l, cfg.physics.rho_g)

    kappa_raw = solver._curv.compute(psi)
    kappa = solver._hfe.apply(
        solver._backend.xp.asarray(kappa_raw),
        solver._backend.xp.asarray(psi),
    )
    kappa = _interface_supported_curvature(
        kappa,
        psi,
        xp=solver._backend.xp,
        psi_min=getattr(solver._curv, "psi_min", 0.01),
    )
    kappa_h = np.asarray(solver._backend.to_host(kappa))
    psi_h = np.asarray(solver._backend.to_host(psi))

    psi_min = getattr(solver._curv, "psi_min", 0.01)
    tail = (psi_h <= psi_min) | (psi_h >= 1.0 - psi_min)
    assert np.all(kappa_h[tail] == 0.0)
    assert float(np.max(np.abs(kappa_h * (1.0 - psi_h)))) < 20.0


def test_ch13_rising_bubble_water_air_yaml_builds_solver():
    from twophase.ppe.defect_correction import PPESolverDefectCorrection
    from twophase.ppe.fccd_matrixfree import PPESolverFCCDMatrixFree

    path = (
        Path(__file__).resolve().parents[3]
        / "experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml"
    )
    cfg = ExperimentConfig.from_yaml(path)
    solver = TwoPhaseNSSolver.from_config(cfg)

    assert solver._grid.N[0] == 128
    assert solver._grid.N[1] == 256
    assert solver.LX == pytest.approx(1.0)
    assert solver.LY == pytest.approx(2.0)
    assert isinstance(solver._transport, PsiDirectTransport)
    assert solver._interface_runtime.rebuild_freq == 0
    assert solver._interface_runtime.reinit_every == 4
    assert solver._advection_scheme == "fccd_flux"
    assert solver._convection_scheme == "uccd6"
    assert solver._convection_time_scheme == "imex_bdf2"
    assert solver._viscous_time_scheme == "implicit_bdf2"
    assert solver._viscous_solver == "defect_correction"
    assert solver._cn_buoyancy_predictor_assembly_mode == "balanced_buoyancy"
    assert solver._face_flux_projection is True
    assert solver._canonical_face_state is True
    assert solver._face_native_predictor_state is True
    assert isinstance(solver._ppe_solver, PPESolverDefectCorrection)
    assert isinstance(solver._ppe_solver.base_solver, PPESolverFCCDMatrixFree)


def test_phase_separated_fccd_ppe_cuts_cross_phase_faces():
    """SP-M Phase 1: FCCD PPE does not couple pressure across phase jumps."""
    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_defect_correction=False,
        ppe_preconditioner="none",
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="jump_decomposition",
    )
    ppe = solver._ppe_solver
    rho = np.ones(solver._grid.shape)
    rho[: N // 2 + 1, :] = 1000.0

    ppe.prepare_operator(rho)
    coeff_x = np.asarray(ppe._face_inverse_density(ppe._rho, axis=0))

    assert ppe.coefficient_scheme == "phase_separated"
    assert ppe.interface_coupling_scheme == "jump_decomposition"
    assert ppe._uses_phase_mean_gauge()
    assert np.all(coeff_x[N // 2, :] == 0.0)
    assert np.all(coeff_x[: N // 2, :] > 0.0)
    assert np.all(coeff_x[N // 2 + 1 :, :] > 0.0)


def test_phase_separated_fallback_pin_candidates_are_bulk_not_interface_edge():
    """Fallback point-gauge candidates must avoid diffuse contact-line rows."""
    from twophase.ppe.fccd_matrixfree_helpers import compute_fccd_phase_gauges

    rho = np.ones((16, 16))
    rho[:, :8] = 1000.0
    rho[:, 8] = 450.0

    state = compute_fccd_phase_gauges(
        rho_host=rho,
        coefficient_scheme="phase_separated",
        default_pin_dof=0,
    )
    coords = [np.unravel_index(dof, rho.shape) for dof in state.pin_dofs]

    assert len(coords) == 2
    for i, j in coords:
        assert 0 < i < rho.shape[0] - 1
        assert 0 < j < rho.shape[1] - 1
        assert j != 8


def test_phase_separated_fccd_ppe_projects_rhs_per_phase():
    """Each decoupled Neumann phase block must receive zero-mean RHS."""
    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_defect_correction=False,
        ppe_preconditioner="none",
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="jump_decomposition",
    )
    ppe = solver._ppe_solver
    rho = np.ones(solver._grid.shape)
    rho[: N // 2 + 1, :] = 1000.0
    rhs = np.ones_like(rho)
    rhs[: N // 2 + 1, :] = 7.0
    rhs[N // 2 + 1 :, :] = -3.0

    ppe.prepare_operator(rho)
    projected = np.asarray(ppe._project_rhs_compatibility(rhs))
    liquid = np.asarray(ppe._rho) >= ppe._phase_threshold
    gas = np.asarray(ppe._rho) < ppe._phase_threshold

    assert abs(float(np.mean(projected[liquid]))) < 1.0e-14
    assert abs(float(np.mean(projected[gas]))) < 1.0e-14


def test_phase_separated_fccd_ppe_projects_rhs_by_control_volume():
    """Nonuniform Neumann compatibility is a zero control-volume integral."""
    backend, grid, fccd = _make_nonuniform_fccd_wall_stack()
    cfg = type(
        "Cfg",
        (),
        {
            "ppe_coefficient_scheme": "phase_separated",
            "ppe_interface_coupling_scheme": "jump_decomposition",
        },
    )()
    ppe = PPESolverFCCDMatrixFree(backend, cfg, grid, fccd)
    rho = np.ones(grid.shape)
    rho[: grid.N[0] // 2 + 1, :] = 1000.0
    rng = np.random.default_rng(1618)
    rhs = rng.standard_normal(grid.shape)

    ppe.prepare_operator(rho)
    projected = np.asarray(ppe._project_rhs_compatibility(rhs))
    weights = np.asarray(grid.cell_volumes())

    phase_masks = (
        np.asarray(ppe._rho) >= ppe._phase_threshold,
        np.asarray(ppe._rho) < ppe._phase_threshold,
    )
    for mask in phase_masks:
        assert abs(float(np.sum(weights[mask] * projected[mask]))) < 1.0e-13


def test_phase_separated_mean_gauge_removes_phase_constant_modes():
    """Phase-separated PPE uses mean gauges, not point Dirichlet pins."""
    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_defect_correction=False,
        ppe_preconditioner="none",
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="jump_decomposition",
    )
    ppe = solver._ppe_solver
    rho = np.ones(solver._grid.shape)
    rho[: N // 2 + 1, :] = 1000.0
    ppe.prepare_operator(rho)

    field = np.zeros_like(rho)
    field[rho < ppe._phase_threshold] = 3.0
    field[rho >= ppe._phase_threshold] = -2.0
    applied = np.asarray(ppe.apply(field))

    assert np.allclose(applied, field)


def test_phase_separated_mean_gauge_preserves_mirror_symmetry():
    """The nullspace gauge must not introduce a one-point symmetry defect."""
    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_defect_correction=False,
        ppe_preconditioner="none",
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="jump_decomposition",
    )
    ppe = solver._ppe_solver
    y = np.linspace(-1.0, 1.0, N + 1)
    x = np.linspace(-1.0, 1.0, N + 1)
    yy, xx = np.meshgrid(y, x, indexing="ij")
    rho = np.where(yy < 0.0, 1000.0, 1.0)
    pressure = xx * xx + 0.3 * yy

    ppe.prepare_operator(rho)
    applied = np.asarray(ppe.apply(pressure))

    np.testing.assert_allclose(applied, applied[:, ::-1], rtol=1.0e-12, atol=1.0e-12)


def test_phase_separated_defect_correction_preserves_mirror_symmetry():
    """Outer residual correction must use the same mean gauge as the base PPE."""
    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_preconditioner="none",
        ppe_tolerance=1.0e-12,
        ppe_max_iterations=200,
        ppe_restart=80,
        ppe_defect_correction=True,
        ppe_dc_max_iterations=2,
        ppe_dc_tolerance=1.0e-10,
        ppe_dc_relaxation=0.7,
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="jump_decomposition",
        surface_tension_scheme="pressure_jump",
    )
    ppe = solver._ppe_solver
    from twophase.ppe.fd_direct import PPESolverFDDirect
    assert isinstance(ppe.base_solver, PPESolverFDDirect)
    y = np.linspace(-1.0, 1.0, N + 1)
    x = np.linspace(-1.0, 1.0, N + 1)
    yy, xx = np.meshgrid(y, x, indexing="ij")
    rho = np.where(yy < 0.0, 1000.0, 1.0)
    psi = np.where(yy < 0.0, 1.0, 0.0)
    kappa = 2.0 + 0.1 * xx * xx
    rhs = np.zeros_like(rho)

    ppe.set_interface_jump_context(psi=psi, kappa=kappa, sigma=0.072)
    pressure = np.asarray(solver._backend.to_host(ppe.solve(rhs, rho)))

    np.testing.assert_allclose(
        pressure,
        pressure[:, ::-1],
        rtol=1.0e-6,
        atol=1.0e-6,
    )


def test_ch14_capillary_yaml_uses_true_low_order_defect_base():
    from twophase.ppe.defect_correction import PPESolverDefectCorrection
    from twophase.ppe.fccd_matrixfree import PPESolverFCCDMatrixFree
    from twophase.ppe.fd_direct import PPESolverFDDirect

    path = (
        Path(__file__).resolve().parents[3]
        / "experiment/ch14/config/ch14_capillary.yaml"
    )
    cfg = ExperimentConfig.from_yaml(path)
    solver = TwoPhaseNSSolver.from_config(cfg)

    assert cfg.run.ppe_solver == "fccd_iterative"
    assert cfg.run.ppe_dc_base_solver == "fd_direct"
    assert cfg.grid.bc_type == "periodic_wall"
    assert cfg.grid.grid_rebuild_freq == 1
    assert cfg.grid.fitting_axes == (False, True)
    assert cfg.grid.fitting_alpha_grid == (1.0, 2.0)
    assert cfg.grid.wall_refinement_axes == (False, True)
    assert cfg.grid.wall_alpha_grid == (1.0, 1.3)
    assert cfg.grid.wall_eps_g_cells == (None, 4.0)
    assert solver.bc_type == "periodic_wall"
    assert solver._ppe_dc_relaxation == pytest.approx(0.7)
    assert isinstance(solver._ppe_solver, PPESolverDefectCorrection)
    assert isinstance(solver._ppe_solver.operator, PPESolverFCCDMatrixFree)
    assert isinstance(solver._ppe_solver.base_solver, PPESolverFDDirect)


def test_mixed_periodic_wall_velocity_hook_zeroes_wall_and_syncs_periodic_axis():
    from twophase.simulation.runtime_setup import wall_bc_hook

    u = np.ones((4, 5))
    v = np.ones((4, 5))
    u[0, 2] = 7.0
    v[-1, 2] = 9.0

    wall_bc_hook(u, v, bc_type="periodic_wall")

    assert u[-1, 2] == pytest.approx(u[0, 2])
    assert v[-1, 2] == pytest.approx(v[0, 2])
    np.testing.assert_allclose(u[:, 0], 0.0)
    np.testing.assert_allclose(u[:, -1], 0.0)
    np.testing.assert_allclose(v[:, 0], 0.0)
    np.testing.assert_allclose(v[:, -1], 0.0)


def test_mixed_periodic_wall_face_reconstruction_uses_cyclic_axis():
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(4, 3), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    fx = np.arange(16.0).reshape(4, 4)
    fy = np.arange(15.0).reshape(5, 3)
    fy[-1, :] += 100.0

    u, v = reconstruct_nodes_from_faces(
        np,
        grid,
        [fx, fy],
        bc_type="periodic_wall",
    )

    np.testing.assert_allclose(u[0, :], 0.5 * (fx[0, :] + fx[-1, :]))
    np.testing.assert_allclose(u[-1, :], u[0, :])
    np.testing.assert_allclose(v[-1, :], v[0, :])


def test_fccd_advection_syncs_mixed_periodic_scalar_image():
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(4, 4), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic_wall")
    fccd = FCCDSolver(grid, backend, bc_type="periodic_wall", ccd_solver=ccd)
    advection = FCCDLevelSetAdvection(backend, grid, fccd, mode="flux")
    psi = np.zeros(grid.shape)
    psi[0, 2] = 0.25
    psi[-1, 2] = 0.75
    velocity = [np.zeros(grid.shape), np.zeros(grid.shape)]

    psi_new = advection.advance(psi, velocity, dt=1.0e-3)

    np.testing.assert_allclose(psi_new[-1, :], psi_new[0, :])
    assert psi_new[-1, 2] == pytest.approx(0.25)


def test_defect_correction_can_build_fd_iterative_cg_base_solver():
    from twophase.ppe.defect_correction import PPESolverDefectCorrection
    from twophase.ppe.fd_matrixfree import PPESolverFDMatrixFree

    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_defect_correction=True,
        ppe_dc_base_solver="fd_iterative",
        ppe_dc_max_iterations=2,
        ppe_dc_tolerance=1.0e-8,
        ppe_iteration_method="cg",
        ppe_preconditioner="jacobi",
        ppe_tolerance=1.0e-6,
        ppe_max_iterations=40,
    )

    assert isinstance(solver._ppe_solver, PPESolverDefectCorrection)
    assert isinstance(solver._ppe_solver.base_solver, PPESolverFDMatrixFree)
    assert solver._ppe_solver.base_solver.iteration_method == "cg"
    assert solver._ppe_solver.base_solver.preconditioner == "jacobi"
    assert solver._ppe_solver.base_solver.allow_direct_fallback is False


def test_phase_separated_fccd_ppe_applies_pressure_jump_context():
    """SP-M Phase 2: pressure_jump adds j_gl=-σκ on the gas side."""
    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_defect_correction=False,
        ppe_preconditioner="none",
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="jump_decomposition",
        surface_tension_scheme="pressure_jump",
        debug_diagnostics=True,
    )
    ppe = solver._ppe_solver
    pressure = np.zeros(solver._grid.shape)
    psi = np.zeros_like(pressure)
    psi[: N // 2 + 1, :] = 1.0
    kappa = np.full_like(pressure, 3.0)

    ppe.set_interface_jump_context(psi=psi, kappa=kappa, sigma=2.0)
    jumped = np.asarray(ppe.apply_interface_jump(pressure))

    assert np.allclose(jumped[: N // 2 + 1, :], 0.0)
    assert np.allclose(jumped[N // 2 + 1 :, :], -6.0)
    assert np.allclose(pressure, 0.0)
    ppe.invalidate_cache()
    assert np.allclose(np.asarray(ppe.apply_interface_jump(pressure)), pressure)


def test_pressure_jump_constructor_rejects_force_gradient():
    with pytest.raises(ValueError, match="surface_tension_gradient_scheme"):
        TwoPhaseNSSolver(
            N, N, L, L,
            bc_type="wall",
            ppe_coefficient_scheme="phase_separated",
            ppe_interface_coupling_scheme="jump_decomposition",
            surface_tension_scheme="pressure_jump",
            surface_tension_gradient_scheme="fccd_flux",
        )


def test_pressure_jump_constructor_requires_jump_coupling():
    with pytest.raises(ValueError, match="ppe_interface_coupling_scheme"):
        TwoPhaseNSSolver(
            N, N, L, L,
            bc_type="wall",
            ppe_coefficient_scheme="phase_separated",
            ppe_interface_coupling_scheme="none",
            surface_tension_scheme="pressure_jump",
        )


def test_local_epsilon_constructor_rejects_nonuniform_csf_surface_tension():
    with pytest.raises(ValueError, match="local interface width"):
        TwoPhaseNSSolver(
            N, N, L, L,
            bc_type="wall",
            alpha_grid=2.0,
            use_local_eps=True,
            surface_tension_scheme="csf",
        )


def test_affine_jump_constructor_requires_face_flux_projection_path():
    with pytest.raises(ValueError, match="face-flux projection"):
        TwoPhaseNSSolver(
            N, N, L, L,
            bc_type="wall",
            ppe_solver="fvm_iterative",
            ppe_coefficient_scheme="phase_separated",
            ppe_interface_coupling_scheme="affine_jump",
            surface_tension_scheme="pressure_jump",
            pressure_gradient_scheme="ccd",
            surface_tension_gradient_scheme="none",
        )


def test_pressure_jump_constructor_accepts_affine_jump():
    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_preconditioner="none",
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="affine_jump",
        surface_tension_scheme="pressure_jump",
        debug_diagnostics=True,
    )

    assert solver._ppe_interface_coupling_scheme == "affine_jump"
    assert solver._ppe_solver.operator.interface_coupling_scheme == "affine_jump"


def test_affine_jump_corrector_forwards_interface_context():
    """Velocity correction must use the same affine jump context as the PPE."""
    from twophase.simulation.ns_step_services import correct_ns_velocity_stage
    from twophase.simulation.ns_step_state import NSStepState

    class GradientStub:
        def gradient(self, pressure, axis):
            return np.zeros_like(pressure)

    class ProjectionRecorder:
        def __init__(self):
            self.kwargs = None

        def project_faces(self, components, p, rho, dt, force_components=None, **kwargs):
            self.kwargs = kwargs
            return [np.array(component, copy=True) for component in components]

        def reconstruct_nodes(self, face_components):
            return face_components

    arr = np.zeros((3, 3))
    state = NSStepState(
        psi=np.array([[1.0, 1.0, 1.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
        u=arr,
        v=arr,
        dt=1.0e-3,
        rho_l=1000.0,
        rho_g=1.0,
        sigma=2.0,
        mu=0.0,
        g_acc=0.0,
        rho_ref=500.5,
        mu_l=None,
        mu_g=None,
        bc_hook=None,
        step_index=0,
        rho=np.ones_like(arr),
        kappa=np.full_like(arr, 3.0),
        f_x=np.zeros_like(arr),
        f_y=np.zeros_like(arr),
        u_star=np.zeros_like(arr),
        v_star=np.zeros_like(arr),
        p_corrector=np.zeros_like(arr),
    )
    backend = type("BackendStub", (), {"xp": np})()
    ppe_runtime = type(
        "PPERuntime",
        (),
        {
            "ppe_solver_name": "fccd_iterative",
            "ppe_coefficient_scheme": "phase_separated",
            "ppe_interface_coupling_scheme": "affine_jump",
        },
    )()
    projection = ProjectionRecorder()

    correct_ns_velocity_stage(
        state,
        backend=backend,
        pressure_grad_op=GradientStub(),
        face_flux_projection=True,
        preserve_projected_faces=True,
        fccd_div_op=projection,
        div_op=projection,
        ppe_runtime=ppe_runtime,
        bc_type="wall",
        apply_velocity_bc=lambda *_args: None,
    )

    assert projection.kwargs["pressure_gradient"] == "fccd"
    assert projection.kwargs["coefficient_scheme"] == "phase_separated"
    assert projection.kwargs["interface_coupling_scheme"] == "affine_jump"
    context = projection.kwargs["interface_stress_context"]
    assert context.sigma == pytest.approx(2.0)
    np.testing.assert_allclose(context.pressure_jump_gas_minus_liquid, -6.0)


def test_phase_separated_pressure_jump_stack_one_step_no_nan():
    """Executable SP-M smoke: phase-separated FCCD PPE + pressure_jump."""
    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        advection_scheme="fccd_flux",
        convection_scheme="uccd6",
        pressure_gradient_scheme="fccd_flux",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_preconditioner="none",
        ppe_max_iterations=500,
        ppe_tolerance=1.0e-6,
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="jump_decomposition",
        surface_tension_scheme="pressure_jump",
        debug_diagnostics=True,
    )
    psi = _mode2_ic(solver)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    psi, u, v, p = solver.step(
        psi, u, v, dt=2.0e-4,
        rho_l=1000.0, rho_g=1.0, sigma=0.1,
        mu=0.01, step_index=0,
    )

    for name, arr in [("psi", psi), ("u", u), ("v", v), ("p", p)]:
        assert np.all(np.isfinite(arr)), f"{name} not finite"

    speed_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))))
    assert speed_max > 1.0e-12
    previous_pressure = solver._p_prev
    if previous_pressure is None:
        assert solver._p_prev_dev is not None
        previous_pressure = solver._backend.to_host(solver._p_prev_dev)
    assert not np.allclose(np.asarray(previous_pressure), np.asarray(p))
    diag = solver._step_diag.last
    assert diag["ppe_phase_count"] == 2.0
    assert diag["ppe_pin_count"] == 0.0
    assert diag["ppe_mean_gauge"] == 1.0
    assert diag["ppe_interface_coupling_jump"] == 1.0
    assert diag["ppe_rhs_phase_mean_after_max"] < 1.0e-10


def test_affine_jump_pressure_stack_one_step_no_nan():
    """Executable affine interface-stress smoke: no regular pressure ``J``."""
    solver = TwoPhaseNSSolver(
        N, N, L, L,
        bc_type="wall",
        advection_scheme="fccd_flux",
        convection_scheme="uccd6",
        pressure_gradient_scheme="fccd_flux",
        ppe_solver="fccd_iterative",
        pressure_scheme="fccd_iterative",
        ppe_preconditioner="none",
        ppe_max_iterations=500,
        ppe_tolerance=1.0e-6,
        ppe_coefficient_scheme="phase_separated",
        ppe_interface_coupling_scheme="affine_jump",
        surface_tension_scheme="pressure_jump",
        debug_diagnostics=True,
    )
    psi = _mode2_ic(solver)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    psi, u, v, p = solver.step(
        psi, u, v, dt=2.0e-4,
        rho_l=1000.0, rho_g=1.0, sigma=0.1,
        mu=0.01, step_index=0,
    )

    for name, arr in [("psi", psi), ("u", u), ("v", v), ("p", p)]:
        assert np.all(np.isfinite(arr)), f"{name} not finite"

    speed_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))))
    assert speed_max > 1.0e-12
    diag = solver._step_diag.last
    assert diag["ppe_interface_coupling_jump"] == 0.0
    assert diag["ppe_interface_coupling_affine_jump"] == 1.0


def test_fccd_not_constructed_when_unused():
    """Baseline path: no FCCDSolver allocated when both schemes are legacy."""
    from twophase.ns_terms.convection import ConvectionTerm

    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        advection_scheme="dissipative_ccd",
        convection_scheme="ccd",
        ppe_solver="fvm_iterative",
        ppe_defect_correction=False,
        ppe_coefficient_scheme="phase_density",
        ppe_interface_coupling_scheme="none",
        pressure_gradient_scheme="ccd",
        surface_tension_scheme="none",
    )
    assert solver._fccd is None
    assert isinstance(solver._conv_term, ConvectionTerm)


def test_pipeline_uses_matrixfree_fvm_ppe():
    """Stage 4 PPE uses the shared NumPy/CuPy matrix-free FVM solver."""
    from twophase.ppe.fvm_matrixfree import PPESolverFVMMatrixFree

    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        ppe_solver="fvm_iterative",
        ppe_defect_correction=False,
        ppe_coefficient_scheme="phase_density",
        ppe_interface_coupling_scheme="none",
        pressure_gradient_scheme="ccd",
        surface_tension_scheme="none",
    )
    assert isinstance(solver._ppe_solver, PPESolverFVMMatrixFree)


def test_pipeline_uses_psi_direct_curvature_runtime():
    """Runtime curvature must match the production ``psi_direct_filtered`` path."""
    solver = TwoPhaseNSSolver(N, N, L, L, bc_type="wall")
    assert isinstance(solver._curv, CurvatureCalculatorPsi)


def test_pipeline_can_select_direct_fvm_ppe():
    """Stage 4 PPE direct sparse solve remains selectable for comparisons."""
    from twophase.ppe.fvm_spsolve import PPESolverFVMSpsolve

    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        ppe_solver="fvm_direct",
        ppe_defect_correction=False,
        ppe_coefficient_scheme="phase_density",
        ppe_interface_coupling_scheme="none",
        pressure_gradient_scheme="ccd",
        surface_tension_scheme="none",
    )
    assert isinstance(solver._ppe_solver, PPESolverFVMSpsolve)


def test_pipeline_can_solve_fccd_ppe_smoke():
    """FCCD PPE operator is usable as a pressure solve, not just configurable."""
    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        ppe_solver="fccd_iterative",
        ppe_defect_correction=False,
        pressure_gradient_scheme="fccd_flux",
        surface_tension_gradient_scheme="none",
        ppe_preconditioner="none",
        ppe_max_iterations=100,
        ppe_tolerance=1.0e-8,
    )
    rho = np.ones(solver._grid.shape)
    rhs = np.zeros(solver._grid.shape)
    rhs[2, 3] = 1.0
    rhs[3, 3] = -1.0
    rhs.ravel()[solver._ppe_solver._pin_dof] = 0.0

    pressure = solver._ppe_solver.solve(rhs, rho, dt=1.0)
    residual = solver._backend.to_host(solver._ppe_solver.apply(pressure) - rhs)

    assert np.isfinite(solver._backend.to_host(pressure)).all()
    assert np.linalg.norm(residual) < 1.0e-6


def test_surface_tension_uses_configured_gradient_operator():
    """CSF ∇ψ uses the surface-tension term's configured operator."""
    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        alpha_grid=2.0,
        grid_rebuild_freq=0,
        surface_tension_scheme="csf",
        pressure_gradient_scheme="projection_consistent",
        surface_tension_gradient_scheme="fccd_flux",
    )
    psi = _mode2_ic(solver)
    velocity = np.zeros_like(psi)
    psi, _u, _v = solver._rebuild_grid(psi, velocity, velocity)
    kappa = np.ones_like(psi)

    force_x, force_y = solver._st_force.compute(
        kappa, psi, 2.0, solver._ccd, solver._surface_tension_grad_op,
    )

    np.testing.assert_allclose(
        solver._backend.to_host(force_x),
        solver._backend.to_host(2.0 * solver._surface_tension_grad_op.gradient(psi, 0)),
    )
    np.testing.assert_allclose(
        solver._backend.to_host(force_y),
        solver._backend.to_host(2.0 * solver._surface_tension_grad_op.gradient(psi, 1)),
    )
    assert solver._pressure_grad_op is solver._grad_op
    assert solver._surface_tension_grad_op is not solver._pressure_grad_op


def test_weno5_advection_constructed_from_scheme():
    """YAML-advertised WENO5 path must not silently fall back to DCCD."""
    from twophase.levelset.advection import LevelSetAdvection

    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        advection_scheme="weno5",
        convection_scheme="ccd",
        ppe_solver="fvm_iterative",
        ppe_defect_correction=False,
        ppe_coefficient_scheme="phase_density",
        ppe_interface_coupling_scheme="none",
        pressure_gradient_scheme="ccd",
        surface_tension_scheme="none",
    )
    assert isinstance(solver._adv, LevelSetAdvection)
    assert solver._fccd is None


def test_fccd_psi_bimodal_preserved():
    """Regression: ψ bimodal structure must survive FCCD + phi_primary transport.

    Prior bug: ns_pipeline constructed ``FCCDLevelSetAdvection(
    mass_correction=True)``.  Under ``phi_primary_transport=True`` the
    ``advance`` call is on **φ (SDF)**, and the ψ-CLS correction formula
    ``w = 4q(1-q)`` goes negative in the liquid bulk (φ < 0), scrambling
    φ every step.  After psi_from_phi the interface smeared to the domain
    mean V_liq/V_tot ≈ 0.2 within ~6 steps.  Mass integral was preserved
    by the outer ψ correction, so ``volume_conservation`` passed while
    the interface was visually gone.

    This test locks in the fix (mass_correction=False in ns_pipeline) with
    a stronger gate: the bimodal [0, 1] structure of ψ must survive.
    """
    solver = TwoPhaseNSSolver(
        32, 32, L, L, bc_type="wall",
        alpha_grid=2.0,
        use_local_eps=True,
        eps_factor=1.5,
        grid_rebuild_freq=0,
        reinit_method="ridge_eikonal",
        reinit_every=2,
        reinit_eps_scale=1.4,
        ridge_sigma_0=3.0,
        reproject_mode="consistent_gfm",
        phi_primary_transport=True,
        advection_scheme="fccd_flux",
        convection_scheme="fccd_flux",
    )
    psi = _mode2_ic(solver)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)
    psi, u, v = solver._rebuild_grid(psi, u, v, rho_l=833.0, rho_g=1.0)
    for i in range(6):
        psi, u, v, p = solver.step(
            psi, u, v, dt=5e-4,
            rho_l=833.0, rho_g=1.0, sigma=1.0, mu=0.05, step_index=i,
        )
    psi_host = np.asarray(solver._backend.to_host(psi))
    assert float(np.max(psi_host)) > 0.9, (
        f"ψ max collapsed to {float(np.max(psi_host))!r} — interface vanished"
    )
    assert float(np.min(psi_host)) < 0.1, (
        f"ψ min rose to {float(np.min(psi_host))!r} — interface vanished"
    )


def test_from_config_threads_fccd_keys():
    """YAML → RunCfg → TwoPhaseNSSolver dispatch end-to-end."""
    raw = {
        "grid": {
            "cells": [N, N],
            "domain": {"size": [L, L], "boundary": "wall"},
            "distribution": {
                "schedule": "static",
                "axes": {
                    "x": {
                        "type": "nonuniform",
                        "monitors": {"interface": {"alpha": 2.0}},
                    },
                    "y": {
                        "type": "nonuniform",
                        "monitors": {"interface": {"alpha": 2.0}},
                    },
                },
            },
        },
        "interface": {
            "thickness": {"mode": "nominal", "base_factor": 1.5},
            "reinitialization": {
                "algorithm": "ridge_eikonal",
                "schedule": {"every_steps": 2},
                "profile": {"eps_scale": 1.4, "ridge_sigma_0": 3.0},
            },
        },
        "physics": {
            "phases": {
                "liquid": {"rho": 833.0, "mu": 0.05},
                "gas": {"rho": 1.0, "mu": 0.05},
            },
            "surface_tension": 1.0,
        },
        "run": {
            "time": {"final": 1.0, "cfl": 0.1},
        },
        "numerics": {
            "physical_time": {
                "interface_advection": {
                    "spatial": "fccd",
                    "time": "explicit",
                    "tracking": {"enabled": True, "primary": "phi"},
                },
                "momentum": {
                    "form": "primitive_velocity",
                    "convection": {"spatial": "fccd", "time": "explicit"},
                    "viscosity": {"spatial": "ccd", "time": "crank_nicolson"},
                    "capillary_force": {
                        "formulation": "csf",
                        "time": "explicit",
                        "curvature": "psi_direct_filtered",
                        "force_gradient": "projection_consistent",
                    },
                },
            },
            "elliptic": {
                "pressure_projection": {
                    "mode": "consistent_gfm",
                        "poisson": {
                            "discretization": "fvm",
                            "coefficient": "phase_density",
                            "solver": {"kind": "direct"},
                        },
                },
            },
        },
    }
    cfg = ExperimentConfig.from_dict(raw)
    solver = TwoPhaseNSSolver.from_config(cfg)
    assert solver._advection_scheme == "fccd_flux"
    assert solver._convection_scheme == "fccd_flux"
    assert solver._ppe_solver_name == "fvm_direct"
    assert solver._cn_viscous is True
    assert solver._interface_tracking_method == "phi_primary"
    assert solver._interface_tracking_enabled is True
    assert solver._fccd is not None
    assert solver._conv_term is not None


def test_from_config_can_disable_interface_tracking():
    raw = {
        "grid": {
            "cells": [N, N],
            "domain": {"size": [L, L], "boundary": "wall"},
            "distribution": {
                "type": "uniform",
                "method": "none",
                "alpha": 1.0,
                "schedule": "static",
            },
        },
        "interface": {
            "thickness": {"mode": "nominal", "base_factor": 1.5},
            "reinitialization": {
                "algorithm": "ridge_eikonal",
                "schedule": {"every_steps": 2},
            },
        },
        "physics": {
            "phases": {
                "liquid": {"rho": 1.0, "mu": 0.01},
                "gas": {"rho": 1.0, "mu": 0.01},
            },
            "surface_tension": 0.0,
        },
        "run": {
            "time": {"final": 0.1, "cfl": 0.1},
        },
        "numerics": {
            "physical_time": {
                "interface_advection": {
                    "spatial": "dissipative_ccd",
                    "time": "explicit",
                    "tracking": {"enabled": False, "primary": "none"},
                },
                "momentum": {
                    "form": "primitive_velocity",
                    "convection": {"spatial": "ccd", "time": "explicit"},
                    "viscosity": {"spatial": "ccd", "time": "explicit"},
                    "capillary_force": {
                        "formulation": "csf",
                        "time": "explicit",
                        "curvature": "psi_direct_filtered",
                        "force_gradient": "projection_consistent",
                    },
                },
            },
            "elliptic": {
                "pressure_projection": {
                    "mode": "standard",
                        "poisson": {
                            "discretization": "fvm",
                            "coefficient": "phase_density",
                            "solver": {"kind": "iterative", "method": "gmres"},
                        },
                },
            },
        },
    }
    cfg = ExperimentConfig.from_dict(raw)
    solver = TwoPhaseNSSolver.from_config(cfg)
    assert solver._interface_tracking_enabled is False
    assert solver._interface_tracking_method == "none"


class _NoMatrixPPESolver(IPPESolver):
    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        return np.zeros_like(rhs)


class _ArrayBackend:
    xp = np

    def to_device(self, arr):
        return np.asarray(arr)

    def to_host(self, arr):
        return np.asarray(arr)


class _RecordingReprojector:
    def __init__(self):
        self.calls = 0

    def reproject(self, psi, u, v, ppe_solver, ccd, backend, rho_l=None, rho_g=None):
        self.calls += 1
        return u + 1.0, v + 1.0


def test_consistent_iim_reprojector_uses_ppe_matrix_contract():
    """Matrix-free PPE fallback is driven by IPPESolver.get_matrix contract."""
    reprojector = ConsistentIIMReprojector(
        reproj_iim=object(),
        reconstruct_base=object(),
    )
    delegate = _RecordingReprojector()
    reprojector._delegate = delegate

    psi = np.zeros((4, 4))
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)
    u_out, v_out = reprojector.reproject(
        psi,
        u,
        v,
        _NoMatrixPPESolver(),
        ccd=None,
        backend=_ArrayBackend(),
        rho_l=2.0,
        rho_g=1.0,
    )

    assert delegate.calls == 1
    assert np.all(u_out == 1.0)
    assert np.all(v_out == 1.0)


class _ContextRecordingPPESolver(IPPESolver):
    def __init__(self):
        self.events = []

    def clear_interface_jump_context(self) -> None:
        self.events.append("clear")

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        self.events.append("solve")
        return np.zeros_like(rhs)


class _DerivativeOnlyCCD:
    def first_derivative(self, field, axis):
        return np.zeros_like(field)


def test_reprojector_clears_interface_jump_context_before_ppe_solve():
    reprojector = VariableDensityReprojector()
    ppe = _ContextRecordingPPESolver()
    psi = np.zeros((4, 4))
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    reprojector.reproject(
        psi,
        u,
        v,
        ppe,
        ccd=_DerivativeOnlyCCD(),
        backend=_ArrayBackend(),
        rho_l=2.0,
        rho_g=1.0,
    )

    assert ppe.events == ["clear", "solve"]
