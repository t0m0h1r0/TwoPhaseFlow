"""GPU-resident AO-Fast runtime packets for geometric cell fractions.

This module is the production CUDA boundary for the first AO-Fast runtime
slice.  It deliberately bypasses the dense exact AO helpers guarded in
``twophase.geometry.gpu_runtime_guard``: all geometry, transport, Hodge, and
capillary packet arrays remain in the backend namespace and scalar diagnostics
are returned as backend scalars rather than Python control values.

The capillary Riesz source remains device-resident.  Non-static pressure
reaction is not represented by the Young-Laplace diagnostic multiplier here;
it is marked pending until the downstream pressure-adjoint split is built on
the projection face lattice.
"""

from __future__ import annotations

import math
from contextlib import nullcontext

import numpy as np

from ..backend import is_device_array
from ..geometry.active_kernels import refresh_active_geometry_2d
from ..geometry.bundle_capillary import (
    GeometricCapillaryRieszRepresentative,
    GeometricFaceMassHodge,
    GeometricPressureCapillaryHodge,
    GeometricSurfaceEnergyCovector,
    GeometricYoungLaplaceResidual,
)
from ..geometry.p1_cut_geometry import P1CutGeometry, _case_field
from ..geometry.p1_cut_jacobian import P1CutDerivatives, scatter_local_to_nodes
from ..geometry.phase_state import (
    GeometricCommonFluxTransportResult,
    GeometricPhaseState,
    GeometricPhaseStratum,
    GeometricPhaseTransportResult,
)
from ..geometry.swept_flux import (
    P1SweptFluxCertificate,
    P1SweptFluxResult,
    SweptFluxCertificate,
    SweptFluxTransportResult,
    _bottom_side_horizontal_strip_area,
    _left_side_vertical_strip_area,
    _right_side_vertical_strip_area,
    _top_side_horizontal_strip_area,
)
from .geometric_phase_runtime import (
    GeometricRuntimeCapillaryApplicationState,
    GeometricRuntimeCapillaryState,
    GeometricRuntimeCommonFluxState,
)


def build_geometric_phase_state_gpu(grid, phi, *, level: float = 0.0):
    """Build a GPU-resident geometric state without dense exact AO entry."""
    _require_gpu_array_namespace(grid.xp, "build_geometric_phase_state_gpu")
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    geometry, derivatives = _geometry_and_derivatives_full(grid, phi_dev, level=level)
    del derivatives
    cell_measures = _cell_measures_2d(grid, xp, phi_dev.dtype)
    theta = geometry.q / cell_measures
    zero = xp.asarray(0.0, dtype=phi_dev.dtype)
    return GeometricPhaseState(
        q=geometry.q,
        phi=phi_dev,
        theta=theta,
        geometry=geometry,
        stratum=_stratum_from_geometry(grid, phi_dev, geometry, level=level),
        compatibility_residual_linf=zero,
        compatibility_residual_l2=zero,
        ledger=None,
    )


def transport_geometric_phase_common_flux_2d_gpu(
    grid,
    state: GeometricPhaseState,
    face_velocity,
    *,
    dt: float,
    rho_l: float,
    rho_g: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
    project_every_steps: int = 0,
    step_index: int = 0,
) -> GeometricCommonFluxTransportResult:
    """Advance ``q`` and same-face common fluxes on the GPU.

    ``project_every_steps`` is accepted only as ``0``; the active fused
    projection route remains a separate admission gate.
    """
    del step_index
    _require_gpu_array_namespace(grid.xp, "transport_geometric_phase_common_flux_2d_gpu")
    if project_every_steps != 0:
        raise ValueError(
            "GPU geometric q transport requires project_every_steps=0 until "
            "the fused active compatibility projection is connected"
        )
    dt = _validate_positive_float(dt, "dt")
    tolerance = _validate_nonnegative_float(tolerance, "tolerance")
    rho_l, rho_g = _validate_densities(rho_l, rho_g)
    boundary = _normalize_boundary(boundary)

    swept_flux = _construct_p1_swept_flux_gpu(
        grid,
        state.phi,
        face_velocity,
        dt=dt,
        boundary=boundary,
        level=state.stratum.level,
        tolerance=tolerance,
    )
    transport = _apply_swept_flux_gpu(
        grid,
        state.q,
        swept_flux.phase_fluxes,
        dt=dt,
        boundary=boundary,
    )
    pre_projection = _phase_state_from_q_phi_gpu(
        grid,
        transport.q,
        state.phi,
        level=state.stratum.level,
    )
    phase_transport = GeometricPhaseTransportResult(
        state=pre_projection,
        pre_projection_state=pre_projection,
        swept_flux=swept_flux,
        transport=transport,
        projected=False,
    )
    volume_fluxes = _face_volume_fluxes_gpu(
        grid,
        face_velocity,
        boundary=boundary,
    )
    mass_fluxes = _common_mass_fluxes_gpu(
        grid.xp,
        swept_flux.phase_fluxes,
        volume_fluxes,
        rho_l=rho_l,
        rho_g=rho_g,
    )
    return GeometricCommonFluxTransportResult(
        phase_transport=phase_transport,
        volume_fluxes=volume_fluxes,
        mass_fluxes=mass_fluxes,
    )


def materialise_geometric_common_flux_state_gpu(
    grid,
    result: GeometricCommonFluxTransportResult,
    *,
    rho_l: float,
    rho_g: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
) -> GeometricRuntimeCommonFluxState:
    """Expose q-derived density and face Hodge without host scalar gates."""
    _require_gpu_array_namespace(grid.xp, "materialise_geometric_common_flux_state_gpu")
    del tolerance
    rho_l, rho_g = _validate_densities(rho_l, rho_g)
    boundary = _normalize_boundary(boundary)
    xp = grid.xp
    phase_state = result.phase_transport.state
    density = rho_g + (rho_l - rho_g) * xp.asarray(phase_state.theta)
    face_hodge = _face_mass_hodge_gpu(
        grid,
        phase_state,
        density,
        rho_l=rho_l,
        rho_g=rho_g,
        boundary=boundary,
    )
    residual = _mass_flux_formula_residual_gpu(
        xp,
        result.phase_transport.swept_flux.phase_fluxes,
        result.volume_fluxes,
        result.mass_fluxes,
        rho_l=rho_l,
        rho_g=rho_g,
    )
    return GeometricRuntimeCommonFluxState(
        phase_state=phase_state,
        density=density,
        volume_fluxes=tuple(xp.asarray(face) for face in result.volume_fluxes),
        mass_fluxes=tuple(xp.asarray(face) for face in result.mass_fluxes),
        face_hodge=face_hodge,
        min_density=xp.min(density),
        max_density=xp.max(density),
        mass_flux_formula_residual_linf=residual,
    )


def materialise_geometric_runtime_capillary_state_gpu(
    grid,
    material: GeometricRuntimeCommonFluxState,
    *,
    sigma: float,
    tolerance: float = 1.0e-11,
    max_pcg_iterations: int = 256,
) -> GeometricRuntimeCapillaryState:
    """Build the GPU AO capillary source packet.

    Accuracy contract: a fixed-iteration device-resident PCG solve constructs
    the bundle Riesz source ``r_sigma`` from the active Schur equations.
    It is not admitted as a pressure reaction.  The pressure-reaction fields
    are zero until the simulation-layer pressure-adjoint split constructs
    ``Pi^{M_f}_{R_p(q_T)} r_sigma`` on projection faces.
    """
    _require_gpu_array_namespace(grid.xp, "materialise_geometric_runtime_capillary_state_gpu")
    sigma = _validate_sigma(sigma)
    tolerance = _validate_positive_float(tolerance, "tolerance")
    xp = grid.xp
    phase_state = material.phase_state
    geometry, derivatives = _geometry_and_derivatives_full(
        grid,
        phase_state.phi,
        level=phase_state.stratum.level,
    )
    del geometry

    energy_local = sigma * derivatives.ds_local
    energy_nodal = scatter_local_to_nodes(grid, energy_local)
    capillary_nodal = -energy_nodal
    surface_energy = sigma * xp.sum(phase_state.geometry.cell_surface_lengths)
    surface = GeometricSurfaceEnergyCovector(
        state=phase_state,
        derivatives=derivatives,
        sigma=sigma,
        surface_energy=surface_energy,
        energy_nodal_covector=energy_nodal,
        capillary_nodal_covector=capillary_nodal,
        compatibility_residual_linf=phase_state.compatibility_residual_linf,
    )

    row_norm = xp.sum(derivatives.jq_local * derivatives.jq_local, axis=-1)
    active = row_norm > 0.0
    rhs = _apply_jq_full(xp, derivatives.jq_local, capillary_nodal)
    pressure_cell = _solve_schur_pcg_fixed_gpu(
        grid,
        xp,
        derivatives.jq_local,
        xp.where(active, rhs, xp.zeros_like(rhs)),
        row_norm,
        active,
        max_iterations=max_pcg_iterations,
    )
    pressure_nodal = _apply_jq_transpose_full(grid, derivatives.jq_local, pressure_cell)
    projected_rhs = _apply_jq_full(xp, derivatives.jq_local, pressure_nodal)
    schur_residual = xp.where(active, projected_rhs - rhs, xp.zeros_like(rhs))
    residual_nodal = energy_nodal + pressure_nodal
    normal_residual = xp.where(
        active,
        _apply_jq_full(xp, derivatives.jq_local, residual_nodal),
        xp.zeros_like(rhs),
    )

    capillary_face = _face_incidence_adjoint_gpu(
        grid,
        pressure_cell,
        boundary=material.face_hodge.boundary,
    )
    pressure_face = tuple(xp.zeros_like(face) for face in capillary_face)
    residual_face = tuple(
        cap - press for cap, press in zip(capillary_face, pressure_face, strict=True)
    )
    acceleration = tuple(
        covector / weight
        for covector, weight in zip(
            capillary_face,
            material.face_hodge.weights,
            strict=True,
        )
    )
    pressure_acceleration = tuple(
        covector / weight
        for covector, weight in zip(
            pressure_face,
            material.face_hodge.weights,
            strict=True,
        )
    )
    residual_acceleration = tuple(
        covector / weight
        for covector, weight in zip(
            residual_face,
            material.face_hodge.weights,
            strict=True,
        )
    )

    capillary_riesz = GeometricCapillaryRieszRepresentative(
        surface_covector=surface,
        face_hodge=material.face_hodge,
        face_covectors=capillary_face,
        acceleration=acceleration,
        schur_residual_linf=_linf(xp, schur_residual),
        weighted_acceleration_l2=_face_weighted_l2_gpu(
            xp,
            acceleration,
            material.face_hodge.weights,
        ),
        max_abs_face_covector=_max_abs_face_pair_gpu(xp, capillary_face),
    )
    young_laplace = GeometricYoungLaplaceResidual(
        surface_covector=surface,
        pressure=pressure_cell,
        pressure_nodal_covector=pressure_nodal,
        residual_nodal_covector=residual_nodal,
        residual_linf=_linf(xp, residual_nodal),
        residual_l2=_l2(xp, residual_nodal),
        normal_residual_linf=_linf(xp, normal_residual),
        active_cell_count=-1,
        pressure_was_solved=True,
    )
    hodge = GeometricPressureCapillaryHodge(
        capillary_riesz=capillary_riesz,
        young_laplace_residual=young_laplace,
        pressure_face_covectors=pressure_face,
        pressure_acceleration=pressure_acceleration,
        residual_face_covectors=residual_face,
        residual_acceleration=residual_acceleration,
        max_abs_pressure_face_covector=_max_abs_face_pair_gpu(xp, pressure_face),
        max_abs_residual_face_covector=_max_abs_face_pair_gpu(xp, residual_face),
        weighted_pressure_acceleration_l2=_face_weighted_l2_gpu(
            xp,
            pressure_acceleration,
            material.face_hodge.weights,
        ),
        weighted_residual_acceleration_l2=_face_weighted_l2_gpu(
            xp,
            residual_acceleration,
            material.face_hodge.weights,
        ),
    )
    component_reaction_accelerations = _single_cell_volume_reaction_accelerations_gpu(
        grid,
        phase_state,
        material.face_hodge.weights,
        boundary=material.face_hodge.boundary,
    )
    zero_surface_tension = sigma == 0.0
    return GeometricRuntimeCapillaryState(
        material=material,
        pressure_capillary_hodge=hodge,
        pressure_range_status=(
            "pressure_exact_static"
            if zero_surface_tension
            else "pressure_reaction_projection_pending"
        ),
        pressure_exact_static=zero_surface_tension,
        capillary_drive_present=not zero_surface_tension,
        pressure_range_tolerance=tolerance,
        capillary_force_face_covectors=capillary_face,
        capillary_force_acceleration=acceleration,
        pressure_reaction_face_covectors=pressure_face,
        pressure_reaction_acceleration=pressure_acceleration,
        capillary_force_weighted_acceleration_l2=(
            capillary_riesz.weighted_acceleration_l2
        ),
        pressure_reaction_weighted_acceleration_l2=(
            hodge.weighted_pressure_acceleration_l2
        ),
        max_abs_capillary_force_face_covector=(
            capillary_riesz.max_abs_face_covector
        ),
        max_abs_pressure_reaction_face_covector=(
            hodge.max_abs_pressure_face_covector
        ),
        surface_energy_nodal_covector=energy_nodal,
        pressure_reaction_nodal_covector=pressure_nodal,
        young_laplace_residual_nodal_covector=residual_nodal,
        young_laplace_residual_linf=young_laplace.residual_linf,
        young_laplace_residual_l2=young_laplace.residual_l2,
        young_laplace_normal_residual_linf=young_laplace.normal_residual_linf,
        weighted_residual_acceleration_l2=hodge.weighted_residual_acceleration_l2,
        max_abs_residual_face_covector=hodge.max_abs_residual_face_covector,
        component_reaction_accelerations=component_reaction_accelerations,
        pressure_reaction_projection_status=(
            "pressure_hodge_diagnostic"
            if zero_surface_tension
            else "pressure_reaction_projection_pending"
        ),
    )


def materialise_geometric_runtime_capillary_application_state_gpu(
    grid,
    capillary: GeometricRuntimeCapillaryState,
    *,
    dt: float,
) -> GeometricRuntimeCapillaryApplicationState:
    """Build AO predictor/reaction increments without scalar host control."""
    _require_gpu_array_namespace(
        grid.xp,
        "materialise_geometric_runtime_capillary_application_state_gpu",
    )
    dt = _validate_positive_float(dt, "dt")
    xp = grid.xp
    predictor_acceleration = tuple(
        xp.asarray(face) for face in capillary.capillary_force_acceleration
    )
    pressure_acceleration = tuple(
        xp.asarray(face) for face in capillary.pressure_reaction_acceleration
    )
    predictor_increment = tuple(dt * face for face in predictor_acceleration)
    pressure_increment = tuple(dt * face for face in pressure_acceleration)
    balanced_increment = tuple(
        pred - react
        for pred, react in zip(predictor_increment, pressure_increment, strict=True)
    )
    weights = capillary.material.face_hodge.weights
    return GeometricRuntimeCapillaryApplicationState(
        capillary=capillary,
        dt=dt,
        predictor_face_acceleration=predictor_acceleration,
        pressure_reaction_face_acceleration=pressure_acceleration,
        predictor_face_increment=predictor_increment,
        pressure_reaction_face_increment=pressure_increment,
        pressure_balanced_face_increment=balanced_increment,
        predictor_increment_weighted_l2=_face_weighted_l2_gpu(
            xp,
            predictor_increment,
            weights,
        ),
        pressure_reaction_increment_weighted_l2=_face_weighted_l2_gpu(
            xp,
            pressure_increment,
            weights,
        ),
        pressure_balanced_increment_weighted_l2=_face_weighted_l2_gpu(
            xp,
            balanced_increment,
            weights,
        ),
        max_abs_pressure_balanced_face_increment=_max_abs_face_pair_gpu(
            xp,
            balanced_increment,
        ),
        pressure_exact_static=capillary.pressure_exact_static,
        capillary_drive_present=capillary.capillary_drive_present,
        face_hodge_weights=weights,
        pressure_reaction_projection_status=(
            capillary.pressure_reaction_projection_status
        ),
    )


def validate_geometric_runtime_capillary_fail_close_gpu(
    backend,
    capillary: GeometricRuntimeCapillaryState,
    application: GeometricRuntimeCapillaryApplicationState,
    *,
    ppe_runtime=None,
) -> None:
    """Fail-close the GPU AO capillary source packet at the solver boundary.

    A3 mapping:
      Equation: the raw bundle Riesz source must satisfy the active Schur
      normal equations; the pressure reaction itself is admitted later by
      ``r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma`` on projection faces.
      Discretization: the GPU source packet may be pending pressure-reaction
      projection, but it must not be a zero-drive packet created by reusing the
      same pressure face as both source and reaction.
      Code: one outer boundary synchronization converts scalar diagnostics to
      host values and raises before invalid packets reach momentum/PPE slots.
    """
    if not backend.is_gpu():
        return
    _require_gpu_array_namespace(
        backend.xp,
        "validate_geometric_runtime_capillary_fail_close_gpu",
    )
    tolerance = float(capillary.pressure_range_tolerance)
    if not (math.isfinite(tolerance) and tolerance > 0.0):
        raise ValueError("GPU AO capillary fail-close tolerance must be positive")

    declared_drive = bool(
        application.capillary_drive_present and not application.pressure_exact_static
    )
    scalar_packet = [
        (
            "q/phi compatibility residual",
            capillary.material.phase_state.compatibility_residual_linf,
        ),
        (
            "Young-Laplace normal residual",
            capillary.young_laplace_normal_residual_linf,
        ),
    ]
    if declared_drive:
        scalar_packet.extend([
            (
                "AO predictor increment weighted l2",
                application.predictor_increment_weighted_l2,
            ),
            (
                "AO pressure-balanced increment weighted l2",
                application.pressure_balanced_increment_weighted_l2,
            ),
            (
                "AO pressure-balanced increment max",
                application.max_abs_pressure_balanced_face_increment,
            ),
        ])
    scalars = _host_scalar_packet_float(backend, scalar_packet)

    violations: list[str] = []
    compatibility = scalars["q/phi compatibility residual"]
    normal_residual = scalars["Young-Laplace normal residual"]
    if compatibility > tolerance:
        violations.append(
            "q/phi compatibility residual "
            f"{compatibility:.6e} exceeds tolerance {tolerance:.6e}; "
            "restore q=Q_h(phi) before capillarity"
        )
    if normal_residual > tolerance:
        violations.append(
            "AO capillary source solve violates Young-Laplace normal equations "
            f"({normal_residual:.6e} > {tolerance:.6e}); a certified active "
            "PCG/Newton/DC solve is required before advancing"
        )

    predictor_l2 = 0.0
    if declared_drive:
        predictor_l2 = scalars["AO predictor increment weighted l2"]
    nonstatic = declared_drive and predictor_l2 > tolerance
    if nonstatic:
        balanced_l2 = scalars["AO pressure-balanced increment weighted l2"]
        balanced_max = scalars["AO pressure-balanced increment max"]
        pending_projection = (
            str(
                getattr(capillary, "pressure_reaction_projection_status", "")
            ).strip().lower()
            == "pressure_reaction_projection_pending"
        )
        if (
            not pending_projection
            and balanced_l2 <= tolerance
            and balanced_max <= tolerance
        ):
            violations.append(
                "non-static packet has zero pressure-balanced drive "
                f"(weighted_l2={balanced_l2:.6e}, max={balanced_max:.6e}); "
                "the current approximation cancels the capillary force by "
                "construction"
            )

    if violations:
        raise ValueError("GPU AO capillary fail-close: " + "; ".join(violations))


def _geometry_and_derivatives_full(grid, phi, *, level: float):
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    cell_ids = _full_cell_ids(grid, xp)
    active = refresh_active_geometry_2d(
        grid,
        phi_dev,
        cell_ids,
        level=level,
    )
    cell_shape = tuple(grid.N)
    q = active.q_A.reshape(cell_shape)
    cell_measure = active.cell_measure_A.reshape(cell_shape)
    surface = active.s_A.reshape(cell_shape)
    sign_margin = xp.min(xp.abs(phi_dev - float(level)))
    geometry = P1CutGeometry(
        q=q,
        theta=q / cell_measure,
        surface_length=xp.sum(surface),
        cell_surface_lengths=surface,
        sign_margin=sign_margin,
    )
    derivatives = P1CutDerivatives(
        jq_local=active.jq_local_A.reshape(cell_shape + (4,)),
        ds_local=active.ds_local_A.reshape(cell_shape + (4,)),
    )
    return geometry, derivatives


def _phase_state_from_q_phi_gpu(grid, q, phi, *, level: float):
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    q_dev = xp.asarray(q, dtype=phi_dev.dtype)
    geometry, derivatives = _geometry_and_derivatives_full(grid, phi_dev, level=level)
    del derivatives
    cell_measures = _cell_measures_2d(grid, xp, phi_dev.dtype)
    residual = q_dev - geometry.q
    return GeometricPhaseState(
        q=q_dev,
        phi=phi_dev,
        theta=q_dev / cell_measures,
        geometry=geometry,
        stratum=_stratum_from_geometry(grid, phi_dev, geometry, level=level),
        compatibility_residual_linf=_linf(xp, residual),
        compatibility_residual_l2=_l2(xp, residual),
        ledger=None,
    )


def _stratum_from_geometry(grid, phi, geometry: P1CutGeometry, *, level: float):
    xp = grid.xp
    phi_rel = xp.asarray(phi) - float(level)
    values = (
        phi_rel[:-1, :-1],
        phi_rel[1:, :-1],
        phi_rel[1:, 1:],
        phi_rel[:-1, 1:],
    )
    return GeometricPhaseStratum(
        node_signs=xp.where(phi_rel < 0.0, -1, 1).astype(xp.int8),
        cell_cases=_case_field(xp, values),
        sign_margin=geometry.sign_margin,
        level=level,
    )


def _construct_p1_swept_flux_gpu(
    grid,
    phi,
    face_velocity,
    *,
    dt: float,
    boundary: tuple[str, str],
    level: float,
    tolerance: float,
):
    del tolerance
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    phi_rel = phi_dev - float(level)
    velocity_x, velocity_y = _face_arrays(grid, face_velocity, dtype=phi_dev.dtype)
    x = xp.asarray(grid.coords[0], dtype=phi_dev.dtype)
    y = xp.asarray(grid.coords[1], dtype=phi_dev.dtype)
    dx = x[1:] - x[:-1]
    dy = y[1:] - y[:-1]
    flux_x = xp.zeros_like(velocity_x)
    flux_y = xp.zeros_like(velocity_y)
    max_courant_x = xp.asarray(0.0, dtype=phi_dev.dtype)
    max_courant_y = xp.asarray(0.0, dtype=phi_dev.dtype)

    internal_x = velocity_x[1:-1, :]
    if internal_x.size:
        displacement = dt * xp.abs(internal_x)
        positive = xp.where(internal_x >= 0.0, displacement, 0.0)
        negative = xp.where(internal_x < 0.0, displacement, 0.0)
        donor_width = xp.where(
            internal_x >= 0.0,
            dx[:-1].reshape((-1, 1)),
            dx[1:].reshape((-1, 1)),
        )
        max_courant_x = xp.maximum(
            max_courant_x,
            xp.max(displacement / donor_width),
        )
        positive_area = _right_side_vertical_strip_area(
            xp,
            y,
            x[1:-1].reshape((-1, 1)),
            positive,
            dx[:-1].reshape((-1, 1)),
            phi_rel[:-2, :-1],
            phi_rel[1:-1, :-1],
            phi_rel[:-2, 1:],
            phi_rel[1:-1, 1:],
        )
        negative_area = _left_side_vertical_strip_area(
            xp,
            y,
            x[1:-1].reshape((-1, 1)),
            negative,
            dx[1:].reshape((-1, 1)),
            phi_rel[1:-1, :-1],
            phi_rel[2:, :-1],
            phi_rel[1:-1, 1:],
            phi_rel[2:, 1:],
        )
        flux_x[1:-1, :] = xp.where(
            internal_x >= 0.0,
            positive_area / dt,
            -negative_area / dt,
        )

    if boundary[0] == "periodic":
        boundary_velocity = velocity_x[0:1, :]
        displacement = dt * xp.abs(boundary_velocity)
        positive = xp.where(boundary_velocity >= 0.0, displacement, 0.0)
        negative = xp.where(boundary_velocity < 0.0, displacement, 0.0)
        donor_width = xp.where(boundary_velocity >= 0.0, dx[-1], dx[0])
        max_courant_x = xp.maximum(
            max_courant_x,
            xp.max(displacement / donor_width),
        )
        positive_area = _right_side_vertical_strip_area(
            xp,
            y,
            x[-1:].reshape((1, 1)),
            positive,
            dx[-1],
            phi_rel[-2:-1, :-1],
            phi_rel[-1:, :-1],
            phi_rel[-2:-1, 1:],
            phi_rel[-1:, 1:],
        )
        negative_area = _left_side_vertical_strip_area(
            xp,
            y,
            x[0:1].reshape((1, 1)),
            negative,
            dx[0],
            phi_rel[0:1, :-1],
            phi_rel[1:2, :-1],
            phi_rel[0:1, 1:],
            phi_rel[1:2, 1:],
        )
        boundary_flux = xp.where(
            boundary_velocity >= 0.0,
            positive_area / dt,
            -negative_area / dt,
        )
        flux_x[0, :] = boundary_flux[0, :]
        flux_x[-1, :] = boundary_flux[0, :]

    internal_y = velocity_y[:, 1:-1]
    if internal_y.size:
        displacement = dt * xp.abs(internal_y)
        positive = xp.where(internal_y >= 0.0, displacement, 0.0)
        negative = xp.where(internal_y < 0.0, displacement, 0.0)
        donor_width = xp.where(
            internal_y >= 0.0,
            dy[:-1].reshape((1, -1)),
            dy[1:].reshape((1, -1)),
        )
        max_courant_y = xp.maximum(
            max_courant_y,
            xp.max(displacement / donor_width),
        )
        positive_area = _top_side_horizontal_strip_area(
            xp,
            x,
            y[1:-1].reshape((1, -1)),
            positive,
            dy[:-1].reshape((1, -1)),
            phi_rel[:-1, :-2],
            phi_rel[1:, :-2],
            phi_rel[:-1, 1:-1],
            phi_rel[1:, 1:-1],
        )
        negative_area = _bottom_side_horizontal_strip_area(
            xp,
            x,
            y[1:-1].reshape((1, -1)),
            negative,
            dy[1:].reshape((1, -1)),
            phi_rel[:-1, 1:-1],
            phi_rel[1:, 1:-1],
            phi_rel[:-1, 2:],
            phi_rel[1:, 2:],
        )
        flux_y[:, 1:-1] = xp.where(
            internal_y >= 0.0,
            positive_area / dt,
            -negative_area / dt,
        )

    if boundary[1] == "periodic":
        boundary_velocity = velocity_y[:, 0:1]
        displacement = dt * xp.abs(boundary_velocity)
        positive = xp.where(boundary_velocity >= 0.0, displacement, 0.0)
        negative = xp.where(boundary_velocity < 0.0, displacement, 0.0)
        donor_width = xp.where(boundary_velocity >= 0.0, dy[-1], dy[0])
        max_courant_y = xp.maximum(
            max_courant_y,
            xp.max(displacement / donor_width),
        )
        positive_area = _top_side_horizontal_strip_area(
            xp,
            x,
            y[-1:].reshape((1, 1)),
            positive,
            dy[-1],
            phi_rel[:-1, -2:-1],
            phi_rel[1:, -2:-1],
            phi_rel[:-1, -1:],
            phi_rel[1:, -1:],
        )
        negative_area = _bottom_side_horizontal_strip_area(
            xp,
            x,
            y[0:1].reshape((1, 1)),
            negative,
            dy[0],
            phi_rel[:-1, 0:1],
            phi_rel[1:, 0:1],
            phi_rel[:-1, 1:2],
            phi_rel[1:, 1:2],
        )
        boundary_flux = xp.where(
            boundary_velocity >= 0.0,
            positive_area / dt,
            -negative_area / dt,
        )
        flux_y[:, 0] = boundary_flux[:, 0]
        flux_y[:, -1] = boundary_flux[:, 0]

    return P1SweptFluxResult(
        phase_fluxes=(flux_x, flux_y),
        certificate=P1SweptFluxCertificate(
            dt=dt,
            boundary=boundary,
            max_courant_linf=xp.maximum(max_courant_x, max_courant_y),
            max_abs_phase_flux=_max_abs_face_pair_gpu(xp, (flux_x, flux_y)),
            closure_residual_linf=_closure_residual_linf_gpu(
                xp,
                flux_x,
                flux_y,
                boundary,
            ),
        ),
    )


def _apply_swept_flux_gpu(grid, q, phase_fluxes, *, dt: float, boundary):
    xp = grid.xp
    q_dev = xp.asarray(q)
    flux_x, flux_y = tuple(xp.asarray(face, dtype=q_dev.dtype) for face in phase_fluxes)
    swept_x = dt * flux_x
    swept_y = dt * flux_y
    divergence = (swept_x[1:, :] - swept_x[:-1, :]) + (
        swept_y[:, 1:] - swept_y[:, :-1]
    )
    q_next = q_dev - divergence
    cell_measures = _cell_measures_2d(grid, xp, q_dev.dtype)
    min_margin = xp.min(xp.minimum(q_next, cell_measures - q_next))
    return SweptFluxTransportResult(
        q=q_next,
        certificate=SweptFluxCertificate(
            dt=dt,
            boundary=boundary,
            initial_volume=xp.sum(q_dev),
            final_volume=xp.sum(q_next),
            volume_drift=xp.sum(q_next) - xp.sum(q_dev),
            closure_residual_linf=_closure_residual_linf_gpu(
                xp,
                flux_x,
                flux_y,
                boundary,
            ),
            min_q=xp.min(q_next),
            max_q=xp.max(q_next),
            min_bound_margin=min_margin,
            min_donor_margin=min_margin,
            min_receiver_margin=min_margin,
        ),
    )


def _face_volume_fluxes_gpu(grid, face_velocity, *, boundary):
    del boundary
    xp = grid.xp
    velocity_x, velocity_y = _face_arrays(grid, face_velocity, dtype=float)
    x = xp.asarray(grid.coords[0], dtype=velocity_x.dtype)
    y = xp.asarray(grid.coords[1], dtype=velocity_x.dtype)
    dx = x[1:] - x[:-1]
    dy = y[1:] - y[:-1]
    return (
        velocity_x * dy.reshape((1, -1)),
        velocity_y * dx.reshape((-1, 1)),
    )


def _common_mass_fluxes_gpu(xp, phase_fluxes, volume_fluxes, *, rho_l, rho_g):
    drho = rho_l - rho_g
    return tuple(
        rho_g * volume + drho * phase
        for phase, volume in zip(phase_fluxes, volume_fluxes, strict=True)
    )


def _face_mass_hodge_gpu(grid, state, density, *, rho_l, rho_g, boundary):
    xp = grid.xp
    x = xp.asarray(grid.coords[0], dtype=density.dtype)
    y = xp.asarray(grid.coords[1], dtype=density.dtype)
    dx = x[1:] - x[:-1]
    dy = y[1:] - y[:-1]

    rho_x = xp.zeros((grid.N[0] + 1, grid.N[1]), dtype=density.dtype)
    if grid.N[0] > 1:
        rho_x[1:-1, :] = 0.5 * (density[:-1, :] + density[1:, :])
    if boundary[0] == "periodic":
        periodic_rho = 0.5 * (density[-1, :] + density[0, :])
        rho_x[0, :] = periodic_rho
        rho_x[-1, :] = periodic_rho
    else:
        rho_x[0, :] = density[0, :]
        rho_x[-1, :] = density[-1, :]
    dual_x = xp.zeros((grid.N[0] + 1, 1), dtype=density.dtype)
    if grid.N[0] > 1:
        dual_x[1:-1, 0] = 0.5 * (dx[:-1] + dx[1:])
    if boundary[0] == "periodic":
        dual = 0.5 * (dx[-1] + dx[0])
        dual_x[0, 0] = 0.5 * dual
        dual_x[-1, 0] = 0.5 * dual
    else:
        dual_x[0, 0] = 0.5 * dx[0]
        dual_x[-1, 0] = 0.5 * dx[-1]
    weight_x = rho_x * dual_x / dy.reshape((1, -1))

    rho_y = xp.zeros((grid.N[0], grid.N[1] + 1), dtype=density.dtype)
    if grid.N[1] > 1:
        rho_y[:, 1:-1] = 0.5 * (density[:, :-1] + density[:, 1:])
    if boundary[1] == "periodic":
        periodic_rho = 0.5 * (density[:, -1] + density[:, 0])
        rho_y[:, 0] = periodic_rho
        rho_y[:, -1] = periodic_rho
    else:
        rho_y[:, 0] = density[:, 0]
        rho_y[:, -1] = density[:, -1]
    dual_y = xp.zeros((1, grid.N[1] + 1), dtype=density.dtype)
    if grid.N[1] > 1:
        dual_y[0, 1:-1] = 0.5 * (dy[:-1] + dy[1:])
    if boundary[1] == "periodic":
        dual = 0.5 * (dy[-1] + dy[0])
        dual_y[0, 0] = 0.5 * dual
        dual_y[0, -1] = 0.5 * dual
    else:
        dual_y[0, 0] = 0.5 * dy[0]
        dual_y[0, -1] = 0.5 * dy[-1]
    weight_y = rho_y * dual_y / dx.reshape((-1, 1))
    weights = (weight_x, weight_y)
    return GeometricFaceMassHodge(
        state=state,
        weights=weights,
        rho_l=rho_l,
        rho_g=rho_g,
        boundary=boundary,
        min_weight=xp.minimum(xp.min(weight_x), xp.min(weight_y)),
        max_weight=xp.maximum(xp.max(weight_x), xp.max(weight_y)),
    )


def _face_incidence_adjoint_gpu(grid, cell_values, *, boundary):
    xp = grid.xp
    values = xp.asarray(cell_values)
    covector_x = xp.zeros((grid.N[0] + 1, grid.N[1]), dtype=values.dtype)
    covector_y = xp.zeros((grid.N[0], grid.N[1] + 1), dtype=values.dtype)
    if grid.N[0] > 1:
        covector_x[1:-1, :] = values[1:, :] - values[:-1, :]
    if boundary[0] == "periodic":
        seam = 0.5 * (values[0, :] - values[-1, :])
        covector_x[0, :] = seam
        covector_x[-1, :] = seam
    if grid.N[1] > 1:
        covector_y[:, 1:-1] = values[:, 1:] - values[:, :-1]
    if boundary[1] == "periodic":
        seam = 0.5 * (values[:, 0] - values[:, -1])
        covector_y[:, 0] = seam
        covector_y[:, -1] = seam
    return covector_x, covector_y


def _single_cell_volume_reaction_accelerations_gpu(
    grid,
    state: GeometricPhaseState,
    face_weights,
    *,
    boundary,
    threshold: float = 1.0e-12,
):
    """Return the global liquid-cell-volume reaction direction on GPU faces.

    For the geometric-cell-fraction endpoint the YAML contract exposes the
    cell-volume constraint.  Its face covector is ``T_q^T chi`` with ``chi``
    the liquid-support cell indicator, and the runtime acceleration is
    ``M_f^{-1}T_q^T chi`` in the same AO face Hodge used by the raw source.
    """
    xp = grid.xp
    mask = xp.where(
        xp.asarray(state.theta) > xp.asarray(threshold, dtype=state.q.dtype),
        xp.asarray(1.0, dtype=state.q.dtype),
        xp.asarray(0.0, dtype=state.q.dtype),
    )
    covectors = _face_incidence_adjoint_gpu(grid, mask, boundary=boundary)
    acceleration = tuple(
        covector / weight
        for covector, weight in zip(covectors, face_weights, strict=True)
    )
    return (acceleration,)


def _full_cell_ids(grid, xp):
    i = xp.arange(grid.N[0], dtype=xp.int64).reshape((-1, 1))
    j = xp.arange(grid.N[1], dtype=xp.int64).reshape((1, -1))
    return xp.stack(
        (
            xp.broadcast_to(i, tuple(grid.N)).reshape((-1,)),
            xp.broadcast_to(j, tuple(grid.N)).reshape((-1,)),
        ),
        axis=-1,
    )


def _cell_measures_2d(grid, xp, dtype):
    x = xp.asarray(grid.coords[0], dtype=dtype)
    y = xp.asarray(grid.coords[1], dtype=dtype)
    dx = x[1:] - x[:-1]
    dy = y[1:] - y[:-1]
    return dx[:, None] * dy[None, :]


def _face_arrays(grid, arrays, *, dtype):
    if len(arrays) != 2:
        raise ValueError("2D face arrays must provide x and y components")
    xp = grid.xp
    x_face = xp.asarray(arrays[0], dtype=dtype)
    y_face = xp.asarray(arrays[1], dtype=dtype)
    expected_x = (grid.N[0] + 1, grid.N[1])
    expected_y = (grid.N[0], grid.N[1] + 1)
    if tuple(x_face.shape) != expected_x:
        raise ValueError(f"x-face array shape must be {expected_x}")
    if tuple(y_face.shape) != expected_y:
        raise ValueError(f"y-face array shape must be {expected_y}")
    return x_face, y_face


def _apply_jq_full(xp, jq_local, nodal_values):
    local = xp.stack(
        (
            nodal_values[:-1, :-1],
            nodal_values[1:, :-1],
            nodal_values[1:, 1:],
            nodal_values[:-1, 1:],
        ),
        axis=-1,
    )
    return xp.sum(jq_local * local, axis=-1)


def _solve_schur_pcg_fixed_gpu(
    grid,
    xp,
    jq_local,
    rhs,
    row_norm,
    active,
    *,
    max_iterations: int,
):
    """Solve ``J J^T x = rhs`` with a fixed device-resident PCG loop.

    The loop count is fixed by the caller so no residual-dependent host
    synchronization occurs inside the GPU capillary source construction.
    """
    iterations = int(max_iterations)
    if iterations < 1:
        raise ValueError("max_pcg_iterations must be positive")
    b = xp.where(active, xp.asarray(rhs), xp.zeros_like(rhs))
    diagonal = xp.where(active & (row_norm > 0.0), row_norm, xp.ones_like(row_norm))
    x = xp.zeros_like(b)
    r = b - _apply_schur_full_gpu(grid, xp, jq_local, x)
    z = r / diagonal
    p = z
    rz_old = xp.sum(r * z)
    eps = xp.asarray(1.0e-30, dtype=b.dtype)
    for _ in range(iterations):
        ap = _apply_schur_full_gpu(grid, xp, jq_local, p)
        denom = xp.sum(p * ap)
        safe_denom = xp.where(xp.abs(denom) > eps, denom, xp.ones_like(denom))
        alpha = rz_old / safe_denom
        x = x + alpha * p
        r = r - alpha * ap
        z = r / diagonal
        rz_new = xp.sum(r * z)
        safe_rz_old = xp.where(xp.abs(rz_old) > eps, rz_old, xp.ones_like(rz_old))
        beta = rz_new / safe_rz_old
        p = z + beta * p
        rz_old = rz_new
    return xp.where(active, x, xp.zeros_like(x))


def _apply_schur_full_gpu(grid, xp, jq_local, cell_values):
    return _apply_jq_full(
        xp,
        jq_local,
        _apply_jq_transpose_full(grid, jq_local, cell_values),
    )


def _apply_jq_transpose_full(grid, jq_local, cell_values):
    return scatter_local_to_nodes(grid, jq_local * cell_values[..., None])


def _closure_residual_linf_gpu(xp, flux_x, flux_y, boundary):
    residual = xp.asarray(0.0, dtype=flux_x.dtype)
    if boundary[0] == "wall":
        residual = xp.maximum(residual, xp.max(xp.abs(flux_x[0, :])))
        residual = xp.maximum(residual, xp.max(xp.abs(flux_x[-1, :])))
    else:
        residual = xp.maximum(residual, xp.max(xp.abs(flux_x[0, :] - flux_x[-1, :])))
    if boundary[1] == "wall":
        residual = xp.maximum(residual, xp.max(xp.abs(flux_y[:, 0])))
        residual = xp.maximum(residual, xp.max(xp.abs(flux_y[:, -1])))
    else:
        residual = xp.maximum(residual, xp.max(xp.abs(flux_y[:, 0] - flux_y[:, -1])))
    return residual


def _mass_flux_formula_residual_gpu(
    xp,
    phase_fluxes,
    volume_fluxes,
    mass_fluxes,
    *,
    rho_l,
    rho_g,
):
    residual = xp.asarray(0.0, dtype=mass_fluxes[0].dtype)
    for phase, volume, mass in zip(phase_fluxes, volume_fluxes, mass_fluxes, strict=True):
        expected = rho_g * volume + (rho_l - rho_g) * phase
        residual = xp.maximum(residual, xp.max(xp.abs(mass - expected)))
    return residual


def _face_weighted_l2_gpu(xp, values, weights):
    total = xp.asarray(0.0, dtype=values[0].dtype)
    with _errstate(xp):
        for value, weight in zip(values, weights, strict=True):
            total = total + xp.sum(weight * value * value)
        return xp.sqrt(total)


def _max_abs_face_pair_gpu(xp, values):
    return xp.maximum(xp.max(xp.abs(values[0])), xp.max(xp.abs(values[1])))


def _linf(xp, value):
    return xp.max(xp.abs(value))


def _l2(xp, value):
    with _errstate(xp):
        return xp.sqrt(xp.sum(value * value))


def _errstate(xp):
    if hasattr(xp, "errstate"):
        return xp.errstate(over="ignore", invalid="ignore", divide="ignore")
    return nullcontext()


def _normalize_boundary(boundary):
    if isinstance(boundary, str):
        boundary = (boundary, boundary)
    if len(boundary) != 2:
        raise ValueError("boundary must provide one kind per axis")
    normalized = tuple(str(kind) for kind in boundary)
    if any(kind not in {"wall", "periodic"} for kind in normalized):
        raise ValueError("boundary entries must be 'wall' or 'periodic'")
    return normalized


def _validate_densities(rho_l, rho_g):
    rho_l = _validate_positive_float(rho_l, "rho_l")
    rho_g = _validate_positive_float(rho_g, "rho_g")
    return rho_l, rho_g


def _validate_sigma(sigma):
    value = float(sigma)
    if not (math.isfinite(value) and value >= 0.0):
        raise ValueError("sigma must be finite and non-negative")
    return value


def _validate_positive_float(value, name):
    converted = float(value)
    if not (math.isfinite(converted) and converted > 0.0):
        raise ValueError(f"{name} must be finite and positive")
    return converted


def _validate_nonnegative_float(value, name):
    converted = float(value)
    if not (math.isfinite(converted) and converted >= 0.0):
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


def _host_scalar_float(backend, value, name: str) -> float:
    converted = float(np.asarray(backend.to_host(value)))
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    return converted


def _host_scalar_packet_float(backend, entries) -> dict[str, float]:
    xp = backend.xp
    if not entries:
        return {}
    names = [name for name, _ in entries]
    packet = xp.stack([xp.asarray(value) for _, value in entries])
    host_values = np.asarray(backend.to_host(packet), dtype=float).reshape(-1)
    if host_values.size != len(names):
        raise ValueError("GPU scalar packet transfer changed scalar count")
    converted: dict[str, float] = {}
    for name, value in zip(names, host_values, strict=True):
        scalar = float(value)
        if not math.isfinite(scalar):
            raise ValueError(f"{name} must be finite")
        converted[name] = scalar
    return converted


def _pressure_history_mode(ppe_runtime) -> str:
    return str(
        getattr(ppe_runtime, "pressure_history_mode", "face_acceleration")
    ).strip().lower()


def _require_gpu_array_namespace(xp, context):
    module = getattr(xp, "__name__", type(xp).__module__)
    if str(module).split(".", 1)[0] != "cupy":
        raise ValueError(f"{context} requires the CuPy backend")


def uses_device_scalars(value) -> bool:
    """Small test helper for verifying the GPU packet keeps diagnostics device-side."""
    return is_device_array(value)
