"""Tests for PhaseRegion force-admission contract helpers."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.coupling.closed_interface_riesz import (
    face_measure_components,
    transport_increment_from_face_velocity,
)
from twophase.coupling.phase_region_force_admission import (
    attach_phase_region_force_diagnostics,
    build_phase_region_force_adapter_decision,
    build_phase_region_force_admission_candidate,
    build_phase_region_force_admission_report,
    phase_region_face_mass_metric,
    scale_face_velocity_to_fixed_stratum,
    two_phase_nodal_density,
)
from twophase.geometry import CellMeasurePhase
from twophase.simulation.divergence_ops import FCCDDivergenceOperator
from twophase.simulation.phase_region_work_gate import (
    build_phase_region_pressure_velocity_g0_report,
)


def _setup(nx: int = 4, ny: int = 5):
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(nx, ny), L=(1.2, 0.8)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    return grid, backend, fccd


def _nodal_psi(grid: Grid) -> np.ndarray:
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    X, Y = np.meshgrid(x / x[-1], y / y[-1], indexing="ij")
    return 0.52 + 0.18 * X + 0.08 * Y


def _ellipse_psi(grid: Grid) -> np.ndarray:
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    X, Y = np.meshgrid(x, y, indexing="ij")
    cx = 0.5 * x[-1]
    cy = 0.5 * y[-1]
    a = 0.275 * x[-1]
    b = 0.225 * y[-1]
    phi = np.sqrt(((X - cx) / a) ** 2 + ((Y - cy) / b) ** 2) - 1.0
    return 1.0 / (1.0 + np.exp(phi / (1.5 / grid.N[0] / 0.25)))


def _cell_area(grid: Grid) -> np.ndarray:
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    return dx[:, None] * dy[None, :]


def _valid_admission_and_report():
    grid, backend, fccd = _setup(12, 12)
    cell_area = _cell_area(grid)
    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
    )
    admission = attach_phase_region_force_diagnostics(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=FCCDDivergenceOperator(fccd),
        admission=admission,
        probe_face_velocity_components=admission.cochain.surface_acceleration,
    )
    report = build_phase_region_force_admission_report(
        admission=admission,
        grid=grid,
        compatibility_residual_linf=0.0,
        required_metric_keys=(
            "source_volume",
            "owner_volume",
            "diagnostics_valid",
            "self_fd_power_residual",
            "hodge_divergence_linf",
            "compat_linf",
            "grid_alpha",
            "min_dx",
        ),
    )
    assert report.valid, report.reason
    return grid, backend, fccd, admission, report


def _valid_nonuniform_admission_and_report():
    backend = Backend(use_gpu=False)
    grid = Grid(
        GridConfig(
            ndim=2,
            N=(12, 12),
            L=(1.2, 0.8),
            alpha_grid=2.0,
            eps_g_cells=4.0,
        ),
        backend,
    )
    grid.coords[0] = np.array(
        (
            0.0,
            0.07,
            0.15,
            0.25,
            0.38,
            0.52,
            0.66,
            0.78,
            0.89,
            0.99,
            1.08,
            1.15,
            1.2,
        ),
        dtype=float,
    )
    grid.coords[1] = np.array(
        (
            0.0,
            0.04,
            0.10,
            0.17,
            0.26,
            0.37,
            0.49,
            0.59,
            0.67,
            0.73,
            0.77,
            0.79,
            0.8,
        ),
        dtype=float,
    )
    grid._refresh_node_spacings()
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    grid._build_metrics(ccd=ccd)
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    cell_area = _cell_area(grid)
    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
    )
    admission = attach_phase_region_force_diagnostics(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=FCCDDivergenceOperator(fccd),
        admission=admission,
        probe_face_velocity_components=admission.cochain.surface_acceleration,
    )
    report = build_phase_region_force_admission_report(
        admission=admission,
        grid=grid,
        compatibility_residual_linf=0.0,
        required_metric_keys=("grid_alpha", "min_dx", "max_dx"),
    )
    assert report.valid, report.reason
    assert report.grid_alpha == pytest.approx(2.0)
    assert report.min_dx < report.max_dx
    return grid, backend, fccd, admission, report


def _runtime_pressure_velocity_faces(grid, backend, fccd, admission):
    div_op = FCCDDivergenceOperator(fccd)
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    X, Y = np.meshgrid(x / x[-1], y / y[-1], indexing="ij")
    velocity = [
        np.sin(2.0 * np.pi * X) * np.cos(np.pi * Y),
        -0.5 * np.cos(np.pi * X) * np.sin(2.0 * np.pi * Y),
    ]
    pressure = 0.3 * X + 0.2 * Y + 0.1 * np.sin(np.pi * X) * np.sin(np.pi * Y)
    runtime_faces = div_op.face_fluxes(velocity)
    pressure_faces = div_op.pressure_fluxes(
        pressure,
        admission.face_metric.rho_node,
        boundary_face_space="full_face",
    )
    return backend.xp, runtime_faces, pressure_faces


def test_two_phase_nodal_density_matches_runtime_indicator_formula():
    grid, backend, _ = _setup()
    psi = _nodal_psi(grid)

    rho = two_phase_nodal_density(
        xp=backend.xp,
        psi=psi,
        rho_l=10.0,
        rho_g=2.0,
    )

    np.testing.assert_allclose(rho, 2.0 + 8.0 * psi)
    assert float(np.min(rho)) == pytest.approx(2.0 + 8.0 * float(np.min(psi)))
    assert float(np.max(rho)) == pytest.approx(2.0 + 8.0 * float(np.max(psi)))


def test_phase_region_face_metric_uses_nodal_density_on_faces():
    grid, backend, _ = _setup()
    xp = backend.xp
    psi = _nodal_psi(grid)
    metric = phase_region_face_mass_metric(
        xp=xp,
        grid=grid,
        psi=psi,
        rho_l=10.0,
        rho_g=2.0,
    )

    rho = 2.0 + 8.0 * psi
    measures = face_measure_components(xp=xp, grid=grid)
    expected_x = 0.5 * (rho[:-1, :] + rho[1:, :]) * np.asarray(measures[0])
    expected_y = 0.5 * (rho[:, :-1] + rho[:, 1:]) * np.asarray(measures[1])

    np.testing.assert_allclose(metric.rho_node, rho)
    np.testing.assert_allclose(metric.face_weight_components[0], expected_x)
    np.testing.assert_allclose(metric.face_weight_components[1], expected_y)
    assert metric.rho_min == pytest.approx(float(np.min(rho)))
    assert metric.rho_max == pytest.approx(float(np.max(rho)))


def test_build_force_admission_candidate_is_zero_step_and_not_force_admissible():
    grid, backend, fccd = _setup(12, 12)
    cell_area = _cell_area(grid)
    q_l = 0.25 * cell_area

    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=q_l,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
    )

    assert admission.valid, admission.reason
    assert admission.reason == "ok"
    assert admission.runtime_steps == 0
    assert admission.force_admissible is False
    assert admission.owner_map.complement_used is True
    np.testing.assert_allclose(admission.owner_map.q_owner, cell_area - q_l)
    assert admission.face_metric.rho_min > 0.0
    assert admission.cochain is not None
    assert admission.metrics["force_admissible"] == 0.0
    assert admission.metrics["valid"] == 1.0


def test_build_force_admission_candidate_fails_closed_on_bad_runtime_step():
    grid, backend, fccd = _setup(12, 12)
    cell_area = _cell_area(grid)

    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
        runtime_steps=1,
    )

    assert not admission.valid
    assert admission.reason == "runtime_steps_must_be_zero"
    assert admission.force_admissible is False
    assert admission.metrics["force_admissible"] == 0.0


def test_build_force_admission_candidate_fails_closed_on_cell_shaped_psi():
    grid, backend, fccd = _setup(12, 12)
    cell_area = _cell_area(grid)

    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=np.full(tuple(grid.N), 0.6, dtype=float),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
    )

    assert not admission.valid
    assert "nodal grid shape" in admission.reason
    assert admission.force_admissible is False


def test_attach_force_diagnostics_keeps_candidate_unadmitted():
    grid, backend, fccd = _setup(12, 12)
    cell_area = _cell_area(grid)
    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
    )
    assert admission.valid, admission.reason

    with_diagnostics = attach_phase_region_force_diagnostics(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=FCCDDivergenceOperator(fccd),
        admission=admission,
        probe_face_velocity_components=admission.cochain.surface_acceleration,
        fd_eps=1.0e-7,
    )

    diagnostics = with_diagnostics.diagnostics
    assert with_diagnostics.valid
    assert with_diagnostics.force_admissible is False
    assert diagnostics is not None
    assert diagnostics.valid, diagnostics.reason
    assert diagnostics.reason == "ok"
    assert diagnostics.self_work.valid
    assert diagnostics.probe_work.valid
    assert diagnostics.hodge.hodge_divergence_linf < 1.0e-8
    assert diagnostics.reaction.residual_divergence_linf < 1.0e-8
    assert with_diagnostics.metrics["diagnostics_valid"] == 1.0
    assert with_diagnostics.metrics["force_admissible"] == 0.0
    assert "probe_fd_power_residual" in with_diagnostics.metrics


def test_attach_force_diagnostics_fails_closed_for_invalid_candidate():
    grid, backend, fccd = _setup(12, 12)
    cell_area = _cell_area(grid)
    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
        runtime_steps=1,
    )

    with_diagnostics = attach_phase_region_force_diagnostics(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=FCCDDivergenceOperator(fccd),
        admission=admission,
    )

    assert not with_diagnostics.valid
    assert with_diagnostics.force_admissible is False
    assert with_diagnostics.diagnostics is not None
    assert with_diagnostics.diagnostics.reason == "candidate_not_valid"
    assert with_diagnostics.metrics["diagnostics_valid"] == 0.0


def test_build_force_admission_report_exports_zero_step_contract_metrics():
    grid, backend, fccd = _setup(12, 12)
    cell_area = _cell_area(grid)
    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
    )
    admission = attach_phase_region_force_diagnostics(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=FCCDDivergenceOperator(fccd),
        admission=admission,
        probe_face_velocity_components=admission.cochain.surface_acceleration,
    )
    required = (
        "source_volume",
        "owner_volume",
        "diagnostics_valid",
        "self_fd_power_residual",
        "hodge_divergence_linf",
        "compat_linf",
        "grid_alpha",
        "min_dx",
    )

    report = build_phase_region_force_admission_report(
        admission=admission,
        grid=grid,
        compatibility_residual_linf=0.0,
        required_metric_keys=required,
    )

    assert report.valid, report.reason
    assert report.reason == "ok"
    assert report.force_admissible is False
    assert report.runtime_steps == 0
    assert report.diagnostics_valid is True
    assert report.complement_used is True
    assert report.bc_type == "periodic"
    assert report.face_component_shapes == ((12, 13), (13, 12))
    assert report.missing_metric_keys == ()
    assert report.metrics["compat_linf"] == 0.0
    assert report.metrics["grid_alpha"] == pytest.approx(1.0)
    assert report.metrics["min_dx"] == pytest.approx(min(grid.L[0] / 12, grid.L[1] / 12))
    assert report.metrics["force_admissible"] == 0.0


def test_build_force_admission_report_fails_closed_on_missing_required_metric():
    grid, backend, fccd = _setup(12, 12)
    cell_area = _cell_area(grid)
    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
    )
    admission = attach_phase_region_force_diagnostics(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=FCCDDivergenceOperator(fccd),
        admission=admission,
    )

    report = build_phase_region_force_admission_report(
        admission=admission,
        grid=grid,
        required_metric_keys=("not_a_metric",),
    )

    assert not report.valid
    assert report.reason == "missing_metrics:not_a_metric"
    assert report.force_admissible is False
    assert report.missing_metric_keys == ("not_a_metric",)


def test_build_force_admission_report_fails_closed_on_invalid_grid_spacing():
    grid, backend, fccd = _setup(12, 12)
    cell_area = _cell_area(grid)
    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
    )
    admission = attach_phase_region_force_diagnostics(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=FCCDDivergenceOperator(fccd),
        admission=admission,
    )
    grid.coords[0] = np.array(
        (0.0, 0.1, 0.2, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2),
        dtype=float,
    )

    report = build_phase_region_force_admission_report(
        admission=admission,
        grid=grid,
    )

    assert not report.valid
    assert report.reason == "grid_spacing_invalid"
    assert report.force_admissible is False


def test_build_force_admission_report_records_wall_nonuniform_grid_metadata():
    grid, backend, fccd = _setup(4, 5)
    grid.set_boundary_type("wall")
    grid.coords[0] = np.array((0.0, 0.1, 0.35, 0.9, 1.2), dtype=float)
    grid.coords[1] = np.array((0.0, 0.05, 0.2, 0.42, 0.65, 0.8), dtype=float)
    cell_area = _cell_area(grid)
    admission = build_phase_region_force_admission_candidate(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        psi=_ellipse_psi(grid),
        q_source=0.25 * cell_area,
        cell_area=cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        rho_l=10.0,
        rho_g=2.0,
        sigma=0.072,
        runtime_steps=1,
    )

    report = build_phase_region_force_admission_report(
        admission=admission,
        grid=grid,
    )

    assert not report.valid
    assert report.reason == "candidate:runtime_steps_must_be_zero"
    assert report.bc_type == "wall"
    assert report.min_dx == pytest.approx(0.05)
    assert report.max_dx == pytest.approx(0.55)
    assert report.face_component_shapes == ()
    assert report.complement_used is None


def test_build_force_adapter_decision_validates_report_but_withholds_force():
    _grid, _backend, _fccd, admission, report = _valid_admission_and_report()

    decision = build_phase_region_force_adapter_decision(
        admission=admission,
        report=report,
        required_metric_keys=("self_fd_power_residual", "compat_linf"),
    )

    assert decision.valid, decision.reason
    assert decision.reason == "ok"
    assert decision.force_admissible is False
    assert decision.force_components is None
    assert decision.withheld_force_reason == "pressure_velocity_work_gate_missing"
    assert decision.report is report
    assert "self_fd_power_residual" in decision.candidate_metric_keys
    assert decision.metrics["adapter_decision_valid"] == 1.0
    assert decision.metrics["force_admissible"] == 0.0
    assert decision.metrics["force_withheld"] == 1.0


def test_build_force_adapter_decision_fails_closed_on_invalid_report():
    _grid, _backend, _fccd, admission, report = _valid_admission_and_report()
    invalid_report = replace(report, valid=False, reason="diagnostics_missing")

    decision = build_phase_region_force_adapter_decision(
        admission=admission,
        report=invalid_report,
    )

    assert not decision.valid
    assert decision.reason == "report:diagnostics_missing"
    assert decision.force_admissible is False
    assert decision.force_components is None


def test_build_force_adapter_decision_fails_closed_on_face_shape_mismatch():
    _grid, _backend, _fccd, admission, report = _valid_admission_and_report()
    mismatched_report = replace(report, face_component_shapes=((1, 2), (3, 4)))

    decision = build_phase_region_force_adapter_decision(
        admission=admission,
        report=mismatched_report,
    )

    assert not decision.valid
    assert decision.reason == "face_component_shape_mismatch"
    assert decision.force_admissible is False
    assert decision.force_components is None


def test_build_force_adapter_decision_fails_closed_on_missing_required_metric():
    _grid, _backend, _fccd, admission, report = _valid_admission_and_report()

    decision = build_phase_region_force_adapter_decision(
        admission=admission,
        report=report,
        required_metric_keys=("not_a_metric",),
    )

    assert not decision.valid
    assert decision.reason == "missing_metrics:not_a_metric"
    assert decision.force_admissible is False
    assert decision.force_components is None
    assert decision.metrics["adapter_missing_metric_count"] == 1.0


def test_pressure_velocity_g0_report_accepts_matching_face_space_and_metric():
    grid, backend, fccd, admission, report = _valid_admission_and_report()
    decision = build_phase_region_force_adapter_decision(
        admission=admission,
        report=report,
    )
    xp, runtime_faces, pressure_faces = _runtime_pressure_velocity_faces(
        grid,
        backend,
        fccd,
        admission,
    )

    g0 = build_phase_region_pressure_velocity_g0_report(
        xp=xp,
        admission=admission,
        decision=decision,
        runtime_face_velocity_components=runtime_faces,
        pressure_face_components=pressure_faces,
        bc_type=fccd.bc_type,
        boundary_face_space="full_face",
    )

    expected_surface_work = sum(
        float(np.sum(np.asarray(w) * np.asarray(s) * np.asarray(u)))
        for w, s, u in zip(
            admission.face_metric.face_weight_components,
            admission.cochain.surface_acceleration,
            runtime_faces,
        )
    )

    assert g0.valid, g0.reason
    assert g0.reason == "ok"
    assert g0.force_admissible is False
    assert g0.surface_face_shapes == ((12, 13), (13, 12))
    assert g0.surface_face_shapes == g0.velocity_face_shapes
    assert g0.surface_face_shapes == g0.pressure_face_shapes
    assert g0.surface_face_shapes == g0.metric_face_shapes
    assert g0.boundary_residual_linf == 0.0
    assert g0.surface_velocity_work == pytest.approx(expected_surface_work)
    assert np.isfinite(g0.pressure_velocity_work)
    assert g0.metrics["g0_valid"] == 1.0
    assert g0.metrics["force_admissible"] == 0.0


def test_pressure_velocity_g0_report_accepts_nonuniform_metric_faces():
    grid, backend, fccd, admission, report = _valid_nonuniform_admission_and_report()
    decision = build_phase_region_force_adapter_decision(
        admission=admission,
        report=report,
    )
    xp, runtime_faces, pressure_faces = _runtime_pressure_velocity_faces(
        grid,
        backend,
        fccd,
        admission,
    )

    g0 = build_phase_region_pressure_velocity_g0_report(
        xp=xp,
        admission=admission,
        decision=decision,
        runtime_face_velocity_components=runtime_faces,
        pressure_face_components=pressure_faces,
        bc_type=fccd.bc_type,
        boundary_face_space="full_face",
    )

    assert g0.valid, g0.reason
    assert g0.force_admissible is False
    assert g0.surface_face_shapes == g0.metric_face_shapes
    assert report.min_dx < report.max_dx
    assert g0.metrics["metric_weight_min"] > 0.0
    assert np.isfinite(g0.surface_velocity_work)
    assert np.isfinite(g0.pressure_velocity_work)


def test_pressure_velocity_g0_report_rejects_nodal_force_component_route():
    grid, backend, _fccd, admission, report = _valid_admission_and_report()
    decision = build_phase_region_force_adapter_decision(
        admission=admission,
        report=report,
    )
    nodal_components = [
        np.zeros(tuple(grid.shape), dtype=float),
        np.zeros(tuple(grid.shape), dtype=float),
    ]
    pressure_faces = [
        np.zeros_like(component)
        for component in admission.cochain.surface_acceleration
    ]

    g0 = build_phase_region_pressure_velocity_g0_report(
        xp=backend.xp,
        admission=admission,
        decision=decision,
        runtime_face_velocity_components=nodal_components,
        pressure_face_components=pressure_faces,
    )

    assert not g0.valid
    assert g0.reason == "velocity_face_shape_mismatch"
    assert g0.force_admissible is False
    assert g0.surface_face_shapes != tuple(tuple(grid.shape) for _axis in range(grid.ndim))


def test_pressure_velocity_g0_report_rejects_boundary_space_mismatch():
    grid, backend, fccd, admission, report = _valid_admission_and_report()
    decision = build_phase_region_force_adapter_decision(
        admission=admission,
        report=report,
    )
    xp, runtime_faces, pressure_faces = _runtime_pressure_velocity_faces(
        grid,
        backend,
        fccd,
        admission,
    )
    bad_surface_faces = [
        np.array(component, copy=True)
        for component in admission.cochain.surface_acceleration
    ]
    bad_surface_faces[0][0, :] = 1.0
    bad_cochain = replace(
        admission.cochain,
        surface_acceleration=bad_surface_faces,
    )
    bad_admission = replace(admission, cochain=bad_cochain)

    g0 = build_phase_region_pressure_velocity_g0_report(
        xp=xp,
        admission=bad_admission,
        decision=decision,
        runtime_face_velocity_components=runtime_faces,
        pressure_face_components=pressure_faces,
        bc_type="wall",
        boundary_face_space="impermeable_face",
    )

    assert not g0.valid
    assert g0.reason == "surface_face_boundary_space_mismatch"
    assert g0.force_admissible is False
    assert g0.boundary_residual_linf > 0.0


def test_pressure_velocity_g0_report_fails_closed_on_pressure_shape_mismatch():
    grid, backend, fccd, admission, report = _valid_admission_and_report()
    decision = build_phase_region_force_adapter_decision(
        admission=admission,
        report=report,
    )
    xp, runtime_faces, pressure_faces = _runtime_pressure_velocity_faces(
        grid,
        backend,
        fccd,
        admission,
    )
    mismatched_pressure_faces = [
        pressure_faces[0][:-1, :],
        pressure_faces[1],
    ]

    g0 = build_phase_region_pressure_velocity_g0_report(
        xp=xp,
        admission=admission,
        decision=decision,
        runtime_face_velocity_components=runtime_faces,
        pressure_face_components=mismatched_pressure_faces,
    )

    assert not g0.valid
    assert g0.reason == "pressure_face_shape_mismatch"
    assert g0.force_admissible is False


def test_phase_region_face_metric_rejects_cell_density_shape():
    grid, backend, _ = _setup()
    cell_indicator = np.full(tuple(grid.N), 0.6, dtype=float)

    with pytest.raises(ValueError, match="nodal grid shape"):
        phase_region_face_mass_metric(
            xp=backend.xp,
            grid=grid,
            psi=cell_indicator,
            rho_l=10.0,
            rho_g=2.0,
        )


def test_scale_face_velocity_to_fixed_stratum_limits_transport_increment():
    grid, backend, fccd = _setup()
    xp = backend.xp
    psi = _nodal_psi(grid)
    faces = [
        10.0 * xp.ones((grid.N[0], grid.N[1] + 1)),
        -8.0 * xp.ones((grid.N[0] + 1, grid.N[1])),
    ]
    fd_eps = 1.0e-3
    sign_fraction = 2.0e-2

    scaled = scale_face_velocity_to_fixed_stratum(
        xp=xp,
        fccd=fccd,
        psi=psi,
        face_velocity_components=faces,
        fd_eps=fd_eps,
        sign_fraction=sign_fraction,
    )

    delta = transport_increment_from_face_velocity(
        xp=xp,
        fccd=fccd,
        psi=psi,
        face_velocity_components=scaled.face_velocity_components,
    )
    signed = psi - 0.5
    plus = psi + fd_eps * np.asarray(delta)
    minus = psi - fd_eps * np.asarray(delta)

    assert scaled.valid, scaled.reason
    assert 0.0 < scaled.scale < 1.0
    limit = sign_fraction * scaled.sign_margin
    assert fd_eps * float(np.max(np.abs(delta))) <= limit + 1.0e-12
    np.testing.assert_array_equal(np.sign(plus - 0.5), np.sign(signed))
    np.testing.assert_array_equal(np.sign(minus - 0.5), np.sign(signed))


def test_scale_face_velocity_to_fixed_stratum_fails_on_zero_sign_margin():
    grid, backend, fccd = _setup()
    xp = backend.xp
    psi = np.full(tuple(grid.shape), 0.5, dtype=float)
    faces = [
        xp.ones((grid.N[0], grid.N[1] + 1)),
        xp.ones((grid.N[0] + 1, grid.N[1])),
    ]

    scaled = scale_face_velocity_to_fixed_stratum(
        xp=xp,
        fccd=fccd,
        psi=psi,
        face_velocity_components=faces,
        fd_eps=1.0e-3,
    )

    assert not scaled.valid
    assert scaled.reason == "zero_sign_margin"
    assert scaled.scale == 0.0
