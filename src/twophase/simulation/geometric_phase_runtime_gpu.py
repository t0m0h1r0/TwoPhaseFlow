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
from ..geometry.active_kernels import (
    refresh_active_geometry_2d,
    refresh_active_volume_geometry_candidates_2d,
)
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


_SCHUR_RAW_KERNELS = {}
_PCG_BLOCK_RAW_KERNELS = {}


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


def project_geometric_phase_state_gpu(
    grid,
    q,
    phi,
    *,
    level: float = 0.0,
    tolerance: float = 1.0e-11,
    relative_tolerance: float = 0.0,
    max_newton_iterations: int = 8,
    solver_scheme: str = "pcg",
    pcg_tolerance: float = 1.0e-12,
    pcg_max_iterations: int = 256,
    pcg_roundoff_floor: float | None = 1.0e-14,
    dc_tolerance: float = 1.0e-11,
    dc_max_iterations: int = 8,
    dc_relaxation: float = 1.0,
) -> GeometricPhaseState:
    """Build and project a GPU geometric state from explicit ``q`` and ``phi``.

    A3 mapping:
      Equation: SP-AO requires the hard cell-volume constraint
      ``Q_h(phi)=q`` before surface-energy variation.
      Discretization: callers may supply a topology-moving gauge seed; this
      wrapper closes it with the active-set Schur/Newton compatibility
      projection without relaxing the residual tolerance.
      Code: arrays stay in the CuPy namespace and the returned state records
      the exact recomputed compatibility residual.
    """
    _require_gpu_array_namespace(grid.xp, "project_geometric_phase_state_gpu")
    state = _phase_state_from_q_phi_gpu(grid, q, phi, level=level)
    return _project_q_phi_compatibility_fixed_gpu(
        grid,
        state,
        tolerance=tolerance,
        relative_tolerance=relative_tolerance,
        max_newton_iterations=max_newton_iterations,
        solver_scheme=solver_scheme,
        pcg_tolerance=pcg_tolerance,
        pcg_max_iterations=pcg_max_iterations,
        pcg_roundoff_floor=pcg_roundoff_floor,
        dc_tolerance=dc_tolerance,
        dc_max_iterations=dc_max_iterations,
        dc_relaxation=dc_relaxation,
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
    max_newton_iterations: int = 8,
    relative_tolerance: float = 0.0,
    solver_scheme: str = "pcg",
    pcg_tolerance: float = 1.0e-12,
    pcg_max_iterations: int = 256,
    pcg_roundoff_floor: float | None = 1.0e-14,
    dc_tolerance: float = 1.0e-11,
    dc_max_iterations: int = 8,
    dc_relaxation: float = 1.0,
) -> GeometricCommonFluxTransportResult:
    """Advance ``q`` and same-face common fluxes on the GPU.

    When ``project_every_steps`` selects the current step, the transported
    physical cell volume is projected back onto the P1 gauge manifold
    ``Q_h(phi)=q`` before capillarity can consume the state.
    """
    _require_gpu_array_namespace(grid.xp, "transport_geometric_phase_common_flux_2d_gpu")
    dt = _validate_positive_float(dt, "dt")
    tolerance = _validate_nonnegative_float(tolerance, "tolerance")
    project_every_steps = _validate_nonnegative_int(
        project_every_steps,
        "project_every_steps",
    )
    step_index = _validate_nonnegative_int(step_index, "step_index")
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
        tolerance=tolerance,
    )
    pre_projection = _phase_state_from_q_phi_gpu(
        grid,
        transport.q,
        state.phi,
        level=state.stratum.level,
    )
    should_project = (
        project_every_steps > 0 and step_index % project_every_steps == 0
    )
    final_state = (
        _project_q_phi_compatibility_fixed_gpu(
            grid,
            pre_projection,
            tolerance=tolerance,
            relative_tolerance=relative_tolerance,
            max_newton_iterations=max_newton_iterations,
            solver_scheme=solver_scheme,
            pcg_tolerance=pcg_tolerance,
            pcg_max_iterations=pcg_max_iterations,
            pcg_roundoff_floor=pcg_roundoff_floor,
            dc_tolerance=dc_tolerance,
            dc_max_iterations=dc_max_iterations,
            dc_relaxation=dc_relaxation,
        )
        if should_project
        else pre_projection
    )
    phase_transport = GeometricPhaseTransportResult(
        state=final_state,
        pre_projection_state=pre_projection,
        swept_flux=swept_flux,
        transport=transport,
        projected=should_project,
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
    solver_scheme: str = "pcg",
    pcg_tolerance: float = 1.0e-12,
    max_pcg_iterations: int = 256,
    pcg_roundoff_floor: float | None = 1.0e-14,
    dc_tolerance: float = 1.0e-11,
    dc_max_iterations: int = 8,
    dc_relaxation: float = 1.0,
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
    solver_scheme = str(solver_scheme).strip().lower()
    pcg_tolerance = _validate_positive_float(pcg_tolerance, "pcg_tolerance")
    if pcg_roundoff_floor is not None:
        pcg_roundoff_floor = _validate_positive_float(
            pcg_roundoff_floor,
            "pcg_roundoff_floor",
        )
        if pcg_roundoff_floor > pcg_tolerance:
            raise ValueError("pcg_roundoff_floor must not exceed pcg_tolerance")
    dc_tolerance = _validate_positive_float(dc_tolerance, "dc_tolerance")
    dc_max_iterations = _validate_positive_int(dc_max_iterations, "dc_max_iterations")
    dc_relaxation = _validate_positive_float(dc_relaxation, "dc_relaxation")
    if dc_relaxation > 1.0:
        raise ValueError("dc_relaxation must not exceed 1.0")
    xp = grid.xp
    phase_state = material.phase_state
    geometry, derivatives = _geometry_and_derivatives_full(
        grid,
        phase_state.phi,
        level=phase_state.stratum.level,
    )
    del geometry

    row_norm = xp.sum(derivatives.jq_local * derivatives.jq_local, axis=-1)
    active = _active_cut_rows_from_norm_gpu(xp, row_norm)
    schur_support = _masked_schur_support_from_active(
        grid,
        xp,
        derivatives.jq_local,
        row_norm,
        active,
    )
    energy_local_A = sigma * schur_support.gather_local(derivatives.ds_local)
    energy_nodal = schur_support.scatter_local_to_nodes(energy_local_A)
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

    rhs_A = schur_support.apply_j(capillary_nodal)
    rhs = schur_support.scatter_cells(rhs_A)
    pressure_cell = _solve_schur_for_active_policy_gpu(
        grid,
        xp,
        derivatives.jq_local,
        xp.where(active, rhs, xp.zeros_like(rhs)),
        row_norm,
        active,
        solver_scheme=solver_scheme,
        pcg_tolerance=pcg_tolerance,
        pcg_max_iterations=max_pcg_iterations,
        pcg_roundoff_floor=pcg_roundoff_floor,
        dc_tolerance=dc_tolerance,
        dc_max_iterations=dc_max_iterations,
        dc_relaxation=dc_relaxation,
        support=schur_support,
    )
    pressure_A = schur_support.gather_cells(pressure_cell)
    pressure_nodal = schur_support.apply_j_transpose(pressure_A)
    projected_rhs_A = schur_support.apply_schur(pressure_A)
    schur_residual = schur_support.scatter_cells(projected_rhs_A - rhs_A)
    residual_nodal = energy_nodal + pressure_nodal
    normal_residual = schur_support.scatter_cells(
        schur_support.apply_j(residual_nodal)
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


def materialise_geometric_graph_capillary_state_gpu(
    grid,
    material: GeometricRuntimeCommonFluxState,
    *,
    sigma: float,
    tolerance: float = 1.0e-11,
) -> GeometricRuntimeCapillaryState:
    """Build the graph-endpoint AO capillary source on the GPU.

    A3 mapping:
      Equation: for an x-periodic/y-wall single graph, the state owner is the
      column volume ``H_i(q)=y_min + sum_j q_ij / dx_i`` and the surface energy
      is ``E_G=sigma sum_i sqrt(ds_i^2 + (H_{i+1}-H_i)^2)``.
      Discretization: differentiate this graph energy in the column heights,
      pull the variation back only to the cut cell carrying ``dH_i/dq_ij``,
      then use the same finite-volume incidence adjoint and face Hodge as
      swept-volume q transport.  This avoids the singular P1 cut-cell surface
      derivative at graph cell-boundary crossings.
      Code: all height, cut-cell, incidence, and Hodge operations are
      backend-native; scalar host transfer remains limited to the existing
      fail-close boundary.
    """
    _require_gpu_array_namespace(
        grid.xp,
        "materialise_geometric_graph_capillary_state_gpu",
    )
    sigma = _validate_sigma(sigma)
    tolerance = _validate_positive_float(tolerance, "tolerance")
    xp = grid.xp
    phase_state = material.phase_state
    q = xp.asarray(phase_state.q)
    dtype = q.dtype
    x = _grid_coord_device(grid, xp, 0, dtype)
    y = _grid_coord_device(grid, xp, 1, dtype)
    dx = x[1:] - x[:-1]
    column_volume = xp.sum(q, axis=1)
    height = y[0] + column_volume / dx
    lower = y[0]
    upper = y[-1]
    height_bounds = _host_scalar_packet_float(
        grid.backend,
        [
            ("graph height min", xp.min(height)),
            ("graph height max", xp.max(height)),
        ],
    )
    if height_bounds["graph height min"] < float(lower) - float(tolerance):
        raise ValueError("graph capillary height fell below the y-wall domain")
    if height_bounds["graph height max"] > float(upper) + float(tolerance):
        raise ValueError("graph capillary height rose above the y-wall domain")

    dx_next = xp.roll(dx, -1)
    segment_dx = 0.5 * (dx + dx_next)
    dh = xp.roll(height, -1) - height
    segment_length = xp.sqrt(segment_dx * segment_dx + dh * dh)
    surface_energy = sigma * xp.sum(segment_length)
    slope_right = dh / segment_length
    slope_left = xp.roll(slope_right, 1)
    height_gradient = sigma * (slope_left - slope_right)

    y_lower = y[:-1].reshape((1, -1))
    y_upper = y[1:].reshape((1, -1))
    height_col = height.reshape((-1, 1))
    cut_mask = (height_col >= y_lower) & (height_col < y_upper)
    top_cell = height_col >= y[-2]
    cut_mask = xp.where(top_cell, y_upper == y[-1], cut_mask)
    cut_count = xp.sum(cut_mask.astype(dtype), axis=1)
    cut_violation = xp.max(xp.abs(cut_count - xp.ones_like(cut_count)))
    if _host_scalar_packet_float(
        grid.backend,
        [("graph cut count violation", cut_violation)],
    )["graph cut count violation"] > 0.5:
        raise ValueError("graph capillary endpoint must have one cut cell per column")
    cell_covector = xp.where(
        cut_mask,
        height_gradient.reshape((-1, 1)) / dx.reshape((-1, 1)),
        xp.zeros_like(q),
    )
    incidence_covectors = _face_incidence_adjoint_gpu(
        grid,
        cell_covector,
        boundary=material.face_hodge.boundary,
    )
    face_covectors = tuple(-xp.asarray(face) for face in incidence_covectors)
    acceleration = tuple(
        covector / weight
        for covector, weight in zip(
            face_covectors,
            material.face_hodge.weights,
            strict=True,
        )
    )

    geometry, derivatives = _geometry_and_derivatives_full(
        grid,
        phase_state.phi,
        level=phase_state.stratum.level,
    )
    del geometry
    zero_nodes = xp.zeros_like(phase_state.phi)
    zero_cells = xp.zeros_like(q)
    zero_faces = tuple(xp.zeros_like(face) for face in face_covectors)
    surface = GeometricSurfaceEnergyCovector(
        state=phase_state,
        derivatives=derivatives,
        sigma=sigma,
        surface_energy=surface_energy,
        energy_nodal_covector=zero_nodes,
        capillary_nodal_covector=zero_nodes,
        compatibility_residual_linf=phase_state.compatibility_residual_linf,
    )
    capillary_riesz = GeometricCapillaryRieszRepresentative(
        surface_covector=surface,
        face_hodge=material.face_hodge,
        face_covectors=face_covectors,
        acceleration=acceleration,
        schur_residual_linf=xp.asarray(0.0, dtype=dtype),
        weighted_acceleration_l2=_face_weighted_l2_gpu(
            xp,
            acceleration,
            material.face_hodge.weights,
        ),
        max_abs_face_covector=_max_abs_face_pair_gpu(xp, face_covectors),
    )
    young_laplace = GeometricYoungLaplaceResidual(
        surface_covector=surface,
        pressure=zero_cells,
        pressure_nodal_covector=zero_nodes,
        residual_nodal_covector=zero_nodes,
        residual_linf=xp.asarray(0.0, dtype=dtype),
        residual_l2=xp.asarray(0.0, dtype=dtype),
        normal_residual_linf=xp.asarray(0.0, dtype=dtype),
        active_cell_count=-1,
        pressure_was_solved=False,
    )
    hodge = GeometricPressureCapillaryHodge(
        capillary_riesz=capillary_riesz,
        young_laplace_residual=young_laplace,
        pressure_face_covectors=zero_faces,
        pressure_acceleration=zero_faces,
        residual_face_covectors=face_covectors,
        residual_acceleration=acceleration,
        max_abs_pressure_face_covector=xp.asarray(0.0, dtype=dtype),
        max_abs_residual_face_covector=capillary_riesz.max_abs_face_covector,
        weighted_pressure_acceleration_l2=xp.asarray(0.0, dtype=dtype),
        weighted_residual_acceleration_l2=(
            capillary_riesz.weighted_acceleration_l2
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
        capillary_force_face_covectors=face_covectors,
        capillary_force_acceleration=acceleration,
        pressure_reaction_face_covectors=zero_faces,
        pressure_reaction_acceleration=zero_faces,
        capillary_force_weighted_acceleration_l2=(
            capillary_riesz.weighted_acceleration_l2
        ),
        pressure_reaction_weighted_acceleration_l2=xp.asarray(0.0, dtype=dtype),
        max_abs_capillary_force_face_covector=(
            capillary_riesz.max_abs_face_covector
        ),
        max_abs_pressure_reaction_face_covector=xp.asarray(0.0, dtype=dtype),
        surface_energy_nodal_covector=zero_nodes,
        pressure_reaction_nodal_covector=zero_nodes,
        young_laplace_residual_nodal_covector=zero_nodes,
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
        -xp.asarray(face) for face in capillary.capillary_force_acceleration
    )
    pressure_acceleration = tuple(
        -xp.asarray(face) for face in capillary.pressure_reaction_acceleration
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
            "active q/phi compatibility residual",
            _active_interface_compatibility_residual_linf_gpu(
                backend.xp,
                capillary,
            ),
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
    compatibility = scalars["active q/phi compatibility residual"]
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


def _active_interface_compatibility_residual_linf_gpu(
    xp,
    capillary: GeometricRuntimeCapillaryState,
):
    """Return compatibility residual on rows that carry capillary geometry."""
    phase_state = capillary.material.phase_state
    derivatives = (
        capillary.pressure_capillary_hodge
        .capillary_riesz
        .surface_covector
        .derivatives
    )
    row_norm = xp.sum(derivatives.jq_local * derivatives.jq_local, axis=-1)
    active = _active_cut_rows_from_norm_gpu(xp, row_norm)
    residual = xp.asarray(phase_state.q) - xp.asarray(phase_state.geometry.q)
    return xp.max(xp.where(active, xp.abs(residual), xp.zeros_like(residual)))


def _active_cut_rows_from_norm_gpu(xp, row_norm):
    """Return the numerically meaningful fixed-stratum Schur support."""
    row_norm = xp.asarray(row_norm)
    row_norm_floor = xp.asarray(1.0e-12, dtype=row_norm.dtype) * xp.max(row_norm)
    return row_norm > row_norm_floor


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


def _geometry_q_candidates_full(grid, phi_candidates, *, level: float):
    xp = grid.xp
    phi_dev = xp.asarray(phi_candidates)
    cell_ids = _full_cell_ids(grid, xp)
    active = refresh_active_volume_geometry_candidates_2d(
        grid,
        phi_dev,
        cell_ids,
        level=level,
    )
    return active.q_A.reshape((phi_dev.shape[0],) + tuple(grid.N))


def _phase_state_from_q_phi_gpu(grid, q, phi, *, level: float):
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    q_dev = xp.asarray(q, dtype=phi_dev.dtype)
    geometry, derivatives = _geometry_and_derivatives_full(grid, phi_dev, level=level)
    del derivatives
    residual = q_dev - geometry.q
    return _phase_state_from_current_geometry_gpu(
        grid,
        q_dev,
        phi_dev,
        geometry,
        residual,
        level=level,
    )


def _phase_state_from_current_geometry_gpu(
    grid,
    q,
    phi,
    geometry,
    residual,
    *,
    level: float,
):
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    q_dev = xp.asarray(q, dtype=phi_dev.dtype)
    cell_measures = _cell_measures_2d(grid, xp, phi_dev.dtype)
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


def _project_q_phi_compatibility_fixed_gpu(
    grid,
    state: GeometricPhaseState,
    *,
    tolerance: float,
    relative_tolerance: float,
    max_newton_iterations: int,
    solver_scheme: str,
    pcg_tolerance: float,
    pcg_max_iterations: int,
    pcg_roundoff_floor: float | None,
    dc_tolerance: float,
    dc_max_iterations: int,
    dc_relaxation: float,
) -> GeometricPhaseState:
    """Restore the SP-AO hard constraint ``Q_h(phi)=q`` on the GPU.

    A3 mapping:
      Equation: after swept-volume transport, SP-AO requires
      ``Q_h(phi^{n+1}) = q^{n+1}`` before the surface-energy variation is
      evaluated.
      Discretization: safeguarded active-set Newton solves
      ``J_q J_q^T lambda = q - Q_h(phi)`` and updates
      ``delta phi = J_q^T lambda``.  Candidate gauges are accepted only after
      exact ``Q_h`` recomputation, so near-node topology changes are handled by
      residual-monotone active-set refresh instead of freezing the old sign
      stratum or applying a coordinate offset.
      Code: this routine keeps the Schur solve and line-search candidates in
      the backend namespace; each Newton sweep starts with a batched scalar
      fail-close check and skips the Schur/line-search work once the exact
      active-interface ``q/phi`` residual has already met the contract.
    """
    _require_gpu_array_namespace(grid.xp, "_project_q_phi_compatibility_fixed_gpu")
    tolerance = _validate_positive_float(tolerance, "tolerance")
    relative_tolerance = _validate_nonnegative_float(
        relative_tolerance,
        "relative_tolerance",
    )
    max_newton_iterations = _validate_positive_int(
        max_newton_iterations,
        "max_newton_iterations",
    )
    xp = grid.xp
    level = state.stratum.level
    phi = xp.asarray(state.phi)
    q_target = xp.asarray(state.q, dtype=phi.dtype)
    geometry, derivatives = _geometry_and_derivatives_full(grid, phi, level=level)
    residual = q_target - geometry.q
    row_norm = xp.sum(derivatives.jq_local * derivatives.jq_local, axis=-1)
    row_norm_floor = xp.asarray(1.0e-12, dtype=phi.dtype) * xp.max(row_norm)
    active_rows = row_norm > row_norm_floor
    initial_linf = xp.max(
        xp.where(active_rows, xp.abs(residual), xp.zeros_like(residual))
    )
    residual_tolerance = xp.maximum(
        xp.asarray(tolerance, dtype=phi.dtype),
        xp.asarray(relative_tolerance, dtype=phi.dtype) * initial_linf,
    )

    for _ in range(max_newton_iterations):
        row_norm = xp.sum(derivatives.jq_local * derivatives.jq_local, axis=-1)
        row_norm_floor = xp.asarray(1.0e-12, dtype=phi.dtype) * xp.max(row_norm)
        active_rows = row_norm > row_norm_floor
        residual_linf = xp.max(
            xp.where(active_rows, xp.abs(residual), xp.zeros_like(residual))
        )
        active_newton = residual_linf > residual_tolerance
        convergence = _host_scalar_packet_float(
            grid.backend,
            [
                ("active projection residual_linf", residual_linf),
                ("active projection residual_tolerance", residual_tolerance),
            ],
        )
        if (
            convergence["active projection residual_linf"]
            <= convergence["active projection residual_tolerance"]
        ):
            break
        rhs = xp.where(active_rows, residual, xp.zeros_like(residual))
        schur_support = _masked_schur_support_from_active(
            grid,
            xp,
            derivatives.jq_local,
            row_norm,
            active_rows,
        )
        lagrange = _solve_schur_for_active_policy_gpu(
            grid,
            xp,
            derivatives.jq_local,
            rhs,
            row_norm,
            active_rows,
            solver_scheme=solver_scheme,
            pcg_tolerance=pcg_tolerance,
            pcg_max_iterations=pcg_max_iterations,
            pcg_roundoff_floor=pcg_roundoff_floor,
            dc_tolerance=dc_tolerance,
            dc_max_iterations=dc_max_iterations,
            dc_relaxation=dc_relaxation,
            support=schur_support,
        )
        delta_phi = schur_support.apply_j_transpose(
            schur_support.gather_cells(lagrange)
        )
        step = _residual_reducing_step_gpu(
            grid,
            xp,
            phi,
            delta_phi,
            q_target,
            level=level,
            current_residual_linf=residual_linf,
            step_cap=xp.asarray(1.0, dtype=phi.dtype),
            active_newton=active_newton,
            active_rows=active_rows,
        )
        phi = xp.where(active_newton, phi + step * delta_phi, phi)
        geometry, derivatives = _geometry_and_derivatives_full(grid, phi, level=level)
        residual = q_target - geometry.q

    return _phase_state_from_current_geometry_gpu(
        grid,
        q_target,
        phi,
        geometry,
        residual,
        level=level,
    )


def _sign_margin_step_fraction_gpu(xp, phi_rel, delta_phi, *, sign_safety: float):
    """Return a device scalar limiting Newton updates to the fixed sign stratum."""
    safety = xp.asarray(sign_safety, dtype=delta_phi.dtype)
    crossing = phi_rel * delta_phi < 0.0
    safe_delta = xp.where(crossing, xp.abs(delta_phi), xp.ones_like(delta_phi))
    ratios = xp.where(crossing, xp.abs(phi_rel) / safe_delta, xp.inf)
    cap = xp.min(ratios)
    one = xp.asarray(1.0, dtype=delta_phi.dtype)
    return xp.minimum(one, safety * cap)


def _residual_reducing_step_gpu(
    grid,
    xp,
    phi,
    delta_phi,
    q_target,
    *,
    level: float,
    current_residual_linf,
    step_cap,
    active_newton,
    active_rows,
):
    """Pick the first fixed backtracking step that reduces exact ``Q_h`` error."""
    step = xp.minimum(xp.asarray(1.0, dtype=phi.dtype), step_cap)
    min_step = xp.asarray(1.0e-8, dtype=phi.dtype)
    factors = xp.asarray(
        (
            1.0,
            0.5,
            0.25,
            0.125,
            0.0625,
            0.03125,
            0.015625,
            0.0078125,
            0.00390625,
            0.001953125,
            0.0009765625,
            0.00048828125,
            0.000244140625,
            0.0001220703125,
        ),
        dtype=phi.dtype,
    )
    steps = step * factors
    candidate_phi = phi[None, ...] + steps[:, None, None] * delta_phi[None, ...]
    candidate_q = _geometry_q_candidates_full(grid, candidate_phi, level=level)
    candidate_residual = xp.abs(q_target[None, ...] - candidate_q)
    candidate_linf = xp.max(
        xp.where(
            active_rows[None, ...],
            candidate_residual,
            xp.zeros_like(candidate_residual),
        ),
        axis=(1, 2),
    )
    candidate_index = xp.arange(steps.shape[0], dtype=xp.int64)
    sentinel = xp.asarray(steps.shape[0], dtype=xp.int64)
    accept = (
        active_newton
        & (steps >= min_step)
        & (candidate_linf < current_residual_linf)
    )
    improved_linf = xp.where(accept, candidate_linf, xp.inf)
    best = xp.argmin(improved_linf)
    any_accepted = xp.any(accept)
    first = xp.where(any_accepted, best, sentinel)
    first_mask = candidate_index == first
    selected = xp.sum(xp.where(first_mask, steps, xp.zeros_like(steps)))
    return selected


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
    x = _grid_coord_device(grid, xp, 0, phi_dev.dtype)
    y = _grid_coord_device(grid, xp, 1, phi_dev.dtype)
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


def _apply_swept_flux_gpu(
    grid,
    q,
    phase_fluxes,
    *,
    dt: float,
    boundary,
    tolerance: float,
):
    xp = grid.xp
    q_dev = xp.asarray(q)
    flux_x, flux_y = tuple(xp.asarray(face, dtype=q_dev.dtype) for face in phase_fluxes)
    swept_x = dt * flux_x
    swept_y = dt * flux_y
    cell_measures = _cell_measures_2d(grid, xp, q_dev.dtype)
    min_input_margin = xp.min(xp.minimum(q_dev, cell_measures - q_dev))
    closure_residual = _closure_residual_linf_gpu(
        xp,
        flux_x,
        flux_y,
        boundary,
    )
    min_donor_margin, min_receiver_margin = _directional_capacity_margins_2d_gpu(
        xp,
        q_dev,
        cell_measures,
        swept_x,
        swept_y,
        boundary,
    )
    divergence = (swept_x[1:, :] - swept_x[:-1, :]) + (
        swept_y[:, 1:] - swept_y[:, :-1]
    )
    q_next = q_dev - divergence
    min_margin = xp.min(xp.minimum(q_next, cell_measures - q_next))
    volume_drift = xp.sum(q_next) - xp.sum(q_dev)
    scalars = _host_scalar_packet_float(
        grid.backend,
        [
            ("swept flux input q bound margin", min_input_margin),
            ("swept flux closure residual", closure_residual),
            ("swept flux donor margin", min_donor_margin),
            ("swept flux receiver margin", min_receiver_margin),
            ("swept flux transported q bound margin", min_margin),
            ("swept flux global volume drift", volume_drift),
        ],
    )
    violations: list[str] = []
    if scalars["swept flux input q bound margin"] < -tolerance:
        violations.append("input q lies outside physical cell-volume bounds")
    if scalars["swept flux closure residual"] > tolerance:
        violations.append("swept phase flux violates declared boundary closure")
    if scalars["swept flux donor margin"] < -tolerance:
        violations.append("swept phase flux exceeds donor liquid capacity")
    if scalars["swept flux receiver margin"] < -tolerance:
        violations.append("swept phase flux exceeds receiver gas capacity")
    if scalars["swept flux transported q bound margin"] < -tolerance:
        violations.append("swept phase flux violates q boundedness certificate")
    if abs(scalars["swept flux global volume drift"]) > tolerance:
        violations.append("swept phase flux violates global q conservation")
    if violations:
        raise ValueError(
            "GPU AO swept-flux fail-close: " + "; ".join(violations)
        )
    return SweptFluxTransportResult(
        q=q_next,
        certificate=SweptFluxCertificate(
            dt=dt,
            boundary=boundary,
            initial_volume=xp.sum(q_dev),
            final_volume=xp.sum(q_next),
            volume_drift=volume_drift,
            closure_residual_linf=closure_residual,
            min_q=xp.min(q_next),
            max_q=xp.max(q_next),
            min_bound_margin=min_margin,
            min_donor_margin=min_donor_margin,
            min_receiver_margin=min_receiver_margin,
        ),
    )


def _face_volume_fluxes_gpu(grid, face_velocity, *, boundary):
    del boundary
    xp = grid.xp
    velocity_x, velocity_y = _face_arrays(grid, face_velocity, dtype=float)
    dx = _grid_cell_width_device(grid, xp, 0, velocity_x.dtype)
    dy = _grid_cell_width_device(grid, xp, 1, velocity_x.dtype)
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


def _directional_capacity_margins_2d_gpu(
    xp,
    q,
    cell_measures,
    swept_x,
    swept_y,
    boundary,
):
    outgoing = xp.zeros_like(q)
    incoming = xp.zeros_like(q)

    x_internal = swept_x[1:-1, :]
    x_forward = xp.maximum(x_internal, 0.0)
    x_backward = xp.maximum(-x_internal, 0.0)
    outgoing[:-1, :] = outgoing[:-1, :] + x_forward
    incoming[1:, :] = incoming[1:, :] + x_forward
    outgoing[1:, :] = outgoing[1:, :] + x_backward
    incoming[:-1, :] = incoming[:-1, :] + x_backward

    y_internal = swept_y[:, 1:-1]
    y_forward = xp.maximum(y_internal, 0.0)
    y_backward = xp.maximum(-y_internal, 0.0)
    outgoing[:, :-1] = outgoing[:, :-1] + y_forward
    incoming[:, 1:] = incoming[:, 1:] + y_forward
    outgoing[:, 1:] = outgoing[:, 1:] + y_backward
    incoming[:, :-1] = incoming[:, :-1] + y_backward

    if boundary[0] == "periodic":
        x_periodic = swept_x[0, :]
        x_forward = xp.maximum(x_periodic, 0.0)
        x_backward = xp.maximum(-x_periodic, 0.0)
        outgoing[-1, :] = outgoing[-1, :] + x_forward
        incoming[0, :] = incoming[0, :] + x_forward
        outgoing[0, :] = outgoing[0, :] + x_backward
        incoming[-1, :] = incoming[-1, :] + x_backward

    if boundary[1] == "periodic":
        y_periodic = swept_y[:, 0]
        y_forward = xp.maximum(y_periodic, 0.0)
        y_backward = xp.maximum(-y_periodic, 0.0)
        outgoing[:, -1] = outgoing[:, -1] + y_forward
        incoming[:, 0] = incoming[:, 0] + y_forward
        outgoing[:, 0] = outgoing[:, 0] + y_backward
        incoming[:, -1] = incoming[:, -1] + y_backward

    donor_margin = xp.min(q - outgoing)
    receiver_margin = xp.min(cell_measures - q + outgoing - incoming)
    return donor_margin, receiver_margin


def estimate_geometric_swept_capacity_dt_gpu(
    grid,
    state: GeometricPhaseState,
    face_velocity,
    *,
    dt_upper: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
    bisection_iterations: int = 20,
) -> float:
    """Return the largest tested timestep preserving swept-volume bounds.

    The bound is the invariant-domain condition for the explicit finite-volume
    update of the geometric liquid cell volume ``q``.  At each candidate
    timestep the same P1 swept phase flux used by production transport is
    constructed, then the donor liquid capacity, receiver gas capacity, and
    transported cell-volume bounds are checked.  If ``dt_upper`` is already
    admissible it is returned unchanged; otherwise a monotone bisection returns
    the last candidate that satisfied the exact swept-geometry certificate.
    """
    dt_upper = _validate_positive_float(dt_upper, "dt_upper")
    tolerance = _validate_nonnegative_float(tolerance, "tolerance")
    bisection_iterations = _validate_nonnegative_int(
        bisection_iterations,
        "bisection_iterations",
    )
    boundary = _normalize_boundary(boundary)
    xp = grid.xp
    q_dev = xp.asarray(state.q)
    cell_measures = _cell_measures_2d(grid, xp, q_dev.dtype)
    input_margin = xp.min(xp.minimum(q_dev, cell_measures - q_dev))
    input_scalars = _host_scalar_packet_float(
        grid.backend,
        [("geometric capacity input q bound margin", input_margin)],
    )
    if input_scalars["geometric capacity input q bound margin"] < -tolerance:
        raise ValueError(
            "GPU AO geometric-capacity timestep fail-close: input q lies "
            "outside physical cell-volume bounds"
        )

    def capacity_scalars(dt_value: float) -> dict[str, float]:
        swept_flux = _construct_p1_swept_flux_gpu(
            grid,
            state.phi,
            face_velocity,
            dt=dt_value,
            boundary=boundary,
            level=state.stratum.level,
            tolerance=tolerance,
        )
        flux_x, flux_y = tuple(
            xp.asarray(face, dtype=q_dev.dtype)
            for face in swept_flux.phase_fluxes
        )
        swept_x = dt_value * flux_x
        swept_y = dt_value * flux_y
        donor_margin, receiver_margin = _directional_capacity_margins_2d_gpu(
            xp,
            q_dev,
            cell_measures,
            swept_x,
            swept_y,
            boundary,
        )
        divergence = (swept_x[1:, :] - swept_x[:-1, :]) + (
            swept_y[:, 1:] - swept_y[:, :-1]
        )
        q_next = q_dev - divergence
        transported_margin = xp.min(xp.minimum(q_next, cell_measures - q_next))
        return _host_scalar_packet_float(
            grid.backend,
            [
                ("geometric capacity donor margin", donor_margin),
                ("geometric capacity receiver margin", receiver_margin),
                ("geometric capacity transported q bound margin", transported_margin),
            ],
        )

    def admissible(scalars: dict[str, float]) -> bool:
        return (
            scalars["geometric capacity donor margin"] >= -tolerance
            and scalars["geometric capacity receiver margin"] >= -tolerance
            and scalars["geometric capacity transported q bound margin"] >= -tolerance
        )

    upper_scalars = capacity_scalars(dt_upper)
    if admissible(upper_scalars):
        return dt_upper

    lower = 0.0
    upper = dt_upper
    for _ in range(int(bisection_iterations)):
        candidate = 0.5 * (lower + upper)
        if candidate <= 0.0:
            break
        if admissible(capacity_scalars(candidate)):
            lower = candidate
        else:
            upper = candidate
    return lower


def _face_mass_hodge_gpu(grid, state, density, *, rho_l, rho_g, boundary):
    xp = grid.xp
    dx = _grid_cell_width_device(grid, xp, 0, density.dtype)
    dy = _grid_cell_width_device(grid, xp, 1, density.dtype)

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
    dx = _grid_cell_width_device(grid, xp, 0, dtype)
    dy = _grid_cell_width_device(grid, xp, 1, dtype)
    return dx[:, None] * dy[None, :]


def _grid_coord_device(grid, xp, axis: int, dtype):
    getter = getattr(grid, "device_coords", None)
    if callable(getter):
        return getter(axis, dtype=dtype)
    return xp.asarray(grid.coords[axis], dtype=dtype)


def _grid_cell_width_device(grid, xp, axis: int, dtype):
    getter = getattr(grid, "device_cell_widths", None)
    if callable(getter):
        return getter(axis, dtype=dtype)
    coords = _grid_coord_device(grid, xp, axis, dtype)
    return coords[1:] - coords[:-1]


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


class _MaskedSchurSupport2D:
    """Fixed-shape coordinates for the active Schur operator ``J_A J_A^T``.

    A3 mapping:
      Equation: AO-Fast solves the active normal equations
      ``J_A J_A^T lambda_A = b_A`` on the fixed P1 cut stratum.
      Discretization: inactive rows are represented by a backend mask rather
      than discovered through ``argwhere``/``unique`` so the row space has fixed
      shape and no dynamic support-count synchronization.
      Code: masked ``J``/``J^T`` preserve the dense operator coefficients and
      keep every Krylov recurrence on device-resident arrays.
    """

    def __init__(self, grid, xp, jq_local, row_norm, active):
        if grid.ndim != 2:
            raise ValueError("masked Schur support currently supports 2D grids")
        self.grid = grid
        self.xp = xp
        self.cell_shape = tuple(grid.N)
        self.node_shape = (int(grid.N[0]) + 1, int(grid.N[1]) + 1)
        self.n_cells = int(grid.N[0]) * int(grid.N[1])
        self.n_nodes = self.node_shape[0] * self.node_shape[1]
        self.jq_local = xp.asarray(jq_local)
        self.row_norm_A = xp.asarray(row_norm)
        self.active = xp.asarray(active, dtype=bool)
        self.dtype = self.jq_local.dtype
        self.n_active = self.n_cells

    def gather_cells(self, cell_values):
        """Return fixed-shape active cell values with inactive rows zeroed."""
        values = self.xp.asarray(cell_values).reshape(self.cell_shape)
        return self.xp.where(self.active, values, self.xp.zeros_like(values))

    def scatter_cells(self, active_values):
        """Return dense cell values with inactive rows zeroed."""
        xp = self.xp
        values = xp.asarray(active_values).reshape(self.cell_shape)
        return xp.where(self.active, values, xp.zeros_like(values))

    def gather_local(self, local_values):
        """Return fixed-shape local corner values with inactive rows zeroed."""
        xp = self.xp
        local = xp.asarray(local_values).reshape(self.cell_shape + (4,))
        return xp.where(self.active[..., None], local, xp.zeros_like(local))

    def scatter_local_to_nodes(self, local_values):
        """Scatter active cell-local corner covectors to dense nodal values."""
        return scatter_local_to_nodes(self.grid, self.gather_local(local_values))

    def apply_j(self, nodal_values):
        """Apply active ``J`` to a dense nodal vector."""
        xp = self.xp
        applied = _apply_jq_full(xp, self.jq_local, nodal_values)
        return xp.where(self.active, applied, xp.zeros_like(applied))

    def apply_j_transpose(self, cell_values):
        """Apply active ``J^T`` and scatter to the dense nodal shape."""
        return _apply_jq_transpose_full(
            self.grid,
            self.jq_local,
            self.gather_cells(cell_values),
        )

    def apply_schur(self, cell_values):
        """Apply masked ``J_A J_A^T`` to fixed-shape cell values."""
        return _apply_schur_masked_2d(
            self.xp,
            self.jq_local,
            self.active,
            cell_values,
            self.cell_shape,
            self.node_shape,
        )


def _masked_schur_support_from_active(grid, xp, jq_local, row_norm, active):
    return _MaskedSchurSupport2D(grid, xp, jq_local, row_norm, active)


def _apply_schur_masked_2d(
    xp,
    jq_local,
    active,
    cell_values,
    cell_shape,
    node_shape,
):
    """Apply ``J_A J_A^T`` using the P1 cell-node incidence formula.

    Algebraically this is identical to scatter-local-to-nodes followed by a
    local gather, but it avoids constructing the intermediate local and stacked
    nodal gather arrays in the Krylov hot loop.
    """
    values = xp.asarray(cell_values).reshape(cell_shape)
    raw_result = _apply_schur_masked_2d_raw_if_available(
        xp,
        jq_local,
        active,
        values,
        cell_shape,
    )
    if raw_result is not None:
        return raw_result
    return _apply_schur_masked_2d_vector(
        xp,
        jq_local,
        active,
        values,
        cell_shape,
        node_shape,
    )


def _apply_schur_masked_2d_vector(
    xp,
    jq_local,
    active,
    cell_values,
    cell_shape,
    node_shape,
):
    values = xp.asarray(cell_values).reshape(cell_shape)
    active_values = xp.where(active, values, xp.zeros_like(values))
    local = jq_local * active_values[..., None]
    nodal = xp.zeros(node_shape, dtype=local.dtype)
    nodal[:-1, :-1] = nodal[:-1, :-1] + local[..., 0]
    nodal[1:, :-1] = nodal[1:, :-1] + local[..., 1]
    nodal[1:, 1:] = nodal[1:, 1:] + local[..., 2]
    nodal[:-1, 1:] = nodal[:-1, 1:] + local[..., 3]
    applied = (
        jq_local[..., 0] * nodal[:-1, :-1]
        + jq_local[..., 1] * nodal[1:, :-1]
        + jq_local[..., 2] * nodal[1:, 1:]
        + jq_local[..., 3] * nodal[:-1, 1:]
    )
    return xp.where(active, applied, xp.zeros_like(applied))


def _apply_schur_masked_2d_raw_if_available(
    xp,
    jq_local,
    active,
    values,
    cell_shape,
):
    return None
    raw_kernel_type = getattr(xp, "RawKernel", None)
    if raw_kernel_type is None:
        return None
    dtype = np.dtype(values.dtype)
    if dtype not in (np.dtype("float32"), np.dtype("float64")):
        return None
    jq = xp.ascontiguousarray(jq_local)
    mask = xp.ascontiguousarray(active)
    cells = xp.ascontiguousarray(values)
    out = xp.empty(cell_shape, dtype=values.dtype)
    kernel = _schur_raw_kernel(xp, dtype)
    n_cells = int(cell_shape[0]) * int(cell_shape[1])
    threads = 128
    blocks = (n_cells + threads - 1) // threads
    kernel(
        (blocks,),
        (threads,),
        (
            jq,
            mask,
            cells,
            out,
            np.int32(cell_shape[0]),
            np.int32(cell_shape[1]),
            np.int32(n_cells),
        ),
    )
    return out


def _schur_raw_kernel(xp, dtype):
    key = (id(xp), np.dtype(dtype).name)
    cached = _SCHUR_RAW_KERNELS.get(key)
    if cached is not None:
        return cached
    scalar = "float" if np.dtype(dtype) == np.dtype("float32") else "double"
    code = f"""
extern "C" __global__
void apply_schur_masked_2d(
    const {scalar}* __restrict__ jq,
    const bool* __restrict__ active,
    const {scalar}* __restrict__ values,
    {scalar}* __restrict__ out,
    const int nx,
    const int ny,
    const int n_cells
) {{
    int idx = blockDim.x * blockIdx.x + threadIdx.x;
    if (idx >= n_cells) {{
        return;
    }}
    if (!active[idx]) {{
        out[idx] = ({scalar})0;
        return;
    }}
    int i = idx / ny;
    int j = idx - i * ny;
    {scalar} result = ({scalar})0;
    for (int corner = 0; corner < 4; ++corner) {{
        int ni = i + ((corner == 1 || corner == 2) ? 1 : 0);
        int nj = j + ((corner == 2 || corner == 3) ? 1 : 0);
        {scalar} nodal = ({scalar})0;
        int cidx;
        cidx = ni * ny + nj;
        if (ni >= 0 && ni < nx && nj >= 0 && nj < ny && active[cidx]) {{
            nodal += jq[4 * cidx + 0] * values[cidx];
        }}
        cidx = (ni - 1) * ny + nj;
        if (ni - 1 >= 0 && ni - 1 < nx && nj >= 0 && nj < ny && active[cidx]) {{
            nodal += jq[4 * cidx + 1] * values[cidx];
        }}
        cidx = (ni - 1) * ny + (nj - 1);
        if (ni - 1 >= 0 && ni - 1 < nx && nj - 1 >= 0 && nj - 1 < ny
                && active[cidx]) {{
            nodal += jq[4 * cidx + 2] * values[cidx];
        }}
        cidx = ni * ny + (nj - 1);
        if (ni >= 0 && ni < nx && nj - 1 >= 0 && nj - 1 < ny && active[cidx]) {{
            nodal += jq[4 * cidx + 3] * values[cidx];
        }}
        result += jq[4 * idx + corner] * nodal;
    }}
    out[idx] = result;
}}
"""
    kernel = xp.RawKernel(code, "apply_schur_masked_2d")
    _SCHUR_RAW_KERNELS[key] = kernel
    return kernel


def _solve_schur_for_active_policy_gpu(
    grid,
    xp,
    jq_local,
    rhs,
    row_norm,
    active,
    *,
    solver_scheme: str,
    pcg_tolerance: float,
    pcg_max_iterations: int,
    pcg_roundoff_floor: float | None,
    dc_tolerance: float,
    dc_max_iterations: int,
    dc_relaxation: float,
    support=None,
):
    """Dispatch the AO-Fast active Schur solve without hidden fallbacks."""
    scheme = str(solver_scheme).strip().lower()
    if scheme == "pcg":
        return _solve_schur_pcg_fixed_gpu(
            grid,
            xp,
            jq_local,
            rhs,
            row_norm,
            active,
            max_iterations=pcg_max_iterations,
            tolerance=pcg_tolerance,
            roundoff_floor=pcg_roundoff_floor,
            support=support,
        )
    if scheme == "dc":
        return _solve_schur_dc_fixed_gpu(
            grid,
            xp,
            jq_local,
            rhs,
            row_norm,
            active,
            max_iterations=dc_max_iterations,
            tolerance=dc_tolerance,
            relaxation=dc_relaxation,
            support=support,
        )
    if scheme == "dc_then_pcg":
        dc_guess = _solve_schur_dc_fixed_gpu(
            grid,
            xp,
            jq_local,
            rhs,
            row_norm,
            active,
            max_iterations=dc_max_iterations,
            tolerance=dc_tolerance,
            relaxation=dc_relaxation,
            support=support,
        )
        return _solve_schur_pcg_fixed_gpu(
            grid,
            xp,
            jq_local,
            rhs,
            row_norm,
            active,
            initial_guess=dc_guess,
            max_iterations=pcg_max_iterations,
            tolerance=pcg_tolerance,
            roundoff_floor=pcg_roundoff_floor,
            support=support,
        )
    raise ValueError(
        "solver_scheme must be 'pcg', 'dc', or 'dc_then_pcg'"
    )


def _solve_schur_pcg_fixed_gpu(
    grid,
    xp,
    jq_local,
    rhs,
    row_norm,
    active,
    *,
    max_iterations: int,
    tolerance: float,
    roundoff_floor: float | None = None,
    initial_guess=None,
    support=None,
):
    """Solve ``J J^T x = rhs`` with a fixed device-resident PCG loop.

    The loop count is fixed by the caller so no residual-dependent host
    synchronization occurs inside the GPU capillary source construction.
    Once the device residual reaches the requested tolerance, scalar masks
    freeze the recurrence so later fixed iterations cannot drift away from
    the accepted pressure-adjoint solve.
    """
    iterations = int(max_iterations)
    if iterations < 1:
        raise ValueError("max_pcg_iterations must be positive")
    tolerance = _validate_positive_float(tolerance, "tolerance")
    if roundoff_floor is not None:
        roundoff_floor = _validate_positive_float(roundoff_floor, "roundoff_floor")
        if roundoff_floor > tolerance:
            raise ValueError("roundoff_floor must not exceed tolerance")
    support = support or _masked_schur_support_from_active(
        grid,
        xp,
        jq_local,
        row_norm,
        active,
    )
    if support.n_active == 0:
        return xp.zeros_like(rhs)
    raw_solution = _solve_schur_pcg_block_raw_if_available(
        xp,
        support.jq_local,
        rhs,
        support.row_norm_A,
        support.active,
        initial_guess,
        support.cell_shape,
        iterations=iterations,
        tolerance=tolerance,
        roundoff_floor=roundoff_floor,
    )
    if raw_solution is not None:
        return raw_solution
    return _solve_schur_pcg_fixed_gpu_vector(
        xp,
        rhs,
        initial_guess,
        support,
        iterations=iterations,
        tolerance=tolerance,
        roundoff_floor=roundoff_floor,
    )


def _solve_schur_pcg_fixed_gpu_vector(
    xp,
    rhs,
    initial_guess,
    support,
    *,
    iterations: int,
    tolerance: float,
    roundoff_floor: float | None,
):
    b = support.gather_cells(rhs)
    diagonal = xp.where(
        support.row_norm_A > 0.0,
        support.row_norm_A,
        xp.ones_like(support.row_norm_A),
    )
    x = (
        xp.zeros_like(b)
        if initial_guess is None
        else support.gather_cells(initial_guess)
    )
    r = b - support.apply_schur(x)
    z = r / diagonal
    p = z
    rz_old = xp.sum(r * z)
    algebra_floor = 1.0e-30 if roundoff_floor is None else max(
        float(roundoff_floor) ** 2,
        1.0e-30,
    )
    eps = xp.asarray(algebra_floor, dtype=b.dtype)
    residual_tolerance = xp.asarray(tolerance, dtype=b.dtype)
    for _ in range(iterations):
        ap = support.apply_schur(p)
        denom = xp.sum(p * ap)
        residual_linf = xp.max(xp.abs(r))
        active_iteration = (
            (residual_linf > residual_tolerance)
            & (xp.abs(denom) > eps)
            & (xp.abs(rz_old) > eps)
        )
        safe_denom = xp.where(active_iteration, denom, xp.ones_like(denom))
        alpha = xp.where(active_iteration, rz_old / safe_denom, xp.zeros_like(denom))
        x_next = x + alpha * p
        r_next = r - alpha * ap
        x = xp.where(active_iteration, x_next, x)
        r = xp.where(active_iteration, r_next, r)
        z = r / diagonal
        rz_new = xp.sum(r * z)
        safe_rz_old = xp.where(active_iteration, rz_old, xp.ones_like(rz_old))
        beta = xp.where(active_iteration, rz_new / safe_rz_old, xp.zeros_like(rz_old))
        p = xp.where(active_iteration, z + beta * p, p)
        rz_old = xp.where(active_iteration, rz_new, rz_old)
    return support.scatter_cells(x)


def _solve_schur_pcg_block_raw_if_available(
    xp,
    jq_local,
    rhs,
    row_norm,
    active,
    initial_guess,
    cell_shape,
    *,
    iterations: int,
    tolerance: float,
    roundoff_floor: float | None,
):
    raw_kernel_type = getattr(xp, "RawKernel", None)
    if raw_kernel_type is None:
        return None
    n_cells = int(cell_shape[0]) * int(cell_shape[1])
    if n_cells < 1 or n_cells > 1024:
        return None
    rhs_values = xp.asarray(rhs).reshape(cell_shape)
    dtype = np.dtype(rhs_values.dtype)
    if dtype not in (np.dtype("float32"), np.dtype("float64")):
        return None
    jq = xp.ascontiguousarray(jq_local)
    mask = xp.ascontiguousarray(active)
    b = xp.ascontiguousarray(rhs_values)
    row = xp.ascontiguousarray(row_norm)
    if initial_guess is None:
        initial = b
        has_initial = np.int32(0)
    else:
        initial = xp.ascontiguousarray(xp.asarray(initial_guess).reshape(cell_shape))
        has_initial = np.int32(1)
    out = xp.empty(cell_shape, dtype=rhs_values.dtype)
    threads = 1 << (n_cells - 1).bit_length()
    algebra_floor = 1.0e-30 if roundoff_floor is None else max(
        float(roundoff_floor) ** 2,
        1.0e-30,
    )
    kernel = _pcg_block_raw_kernel(xp, dtype)
    kernel(
        (1,),
        (threads,),
        (
            jq,
            mask,
            b,
            row,
            initial,
            out,
            np.int32(cell_shape[0]),
            np.int32(cell_shape[1]),
            np.int32(n_cells),
            np.int32(iterations),
            np.asarray(tolerance, dtype=dtype),
            np.asarray(algebra_floor, dtype=dtype),
            has_initial,
        ),
        shared_mem=6 * threads * dtype.itemsize,
    )
    return out


def _pcg_block_raw_kernel(xp, dtype):
    key = (id(xp), np.dtype(dtype).name, "pcg_block")
    cached = _PCG_BLOCK_RAW_KERNELS.get(key)
    if cached is not None:
        return cached
    scalar = "float" if np.dtype(dtype) == np.dtype("float32") else "double"
    code = f"""
__device__ __forceinline__ {scalar} abs_scalar({scalar} value) {{
    return value < ({scalar})0 ? -value : value;
}}

__device__ __forceinline__ {scalar} schur_at(
    const {scalar}* __restrict__ jq,
    const bool* __restrict__ active,
    const {scalar}* __restrict__ values,
    const int idx,
    const int nx,
    const int ny
) {{
    int i = idx / ny;
    int j = idx - i * ny;
    {scalar} result = ({scalar})0;
    for (int corner = 0; corner < 4; ++corner) {{
        int ni = i + ((corner == 1 || corner == 2) ? 1 : 0);
        int nj = j + ((corner == 2 || corner == 3) ? 1 : 0);
        {scalar} nodal = ({scalar})0;
        int cidx;
        cidx = ni * ny + nj;
        if (ni >= 0 && ni < nx && nj >= 0 && nj < ny && active[cidx]) {{
            nodal += jq[4 * cidx + 0] * values[cidx];
        }}
        cidx = (ni - 1) * ny + nj;
        if (ni - 1 >= 0 && ni - 1 < nx && nj >= 0 && nj < ny && active[cidx]) {{
            nodal += jq[4 * cidx + 1] * values[cidx];
        }}
        cidx = (ni - 1) * ny + (nj - 1);
        if (ni - 1 >= 0 && ni - 1 < nx && nj - 1 >= 0 && nj - 1 < ny
                && active[cidx]) {{
            nodal += jq[4 * cidx + 2] * values[cidx];
        }}
        cidx = ni * ny + (nj - 1);
        if (ni >= 0 && ni < nx && nj - 1 >= 0 && nj - 1 < ny && active[cidx]) {{
            nodal += jq[4 * cidx + 3] * values[cidx];
        }}
        result += jq[4 * idx + corner] * nodal;
    }}
    return result;
}}

__device__ __forceinline__ void reduce_sum({scalar}* values) {{
    int tid = threadIdx.x;
    __syncthreads();
    for (int stride = blockDim.x >> 1; stride > 0; stride >>= 1) {{
        if (tid < stride) {{
            values[tid] += values[tid + stride];
        }}
        __syncthreads();
    }}
}}

__device__ __forceinline__ void reduce_max({scalar}* values) {{
    int tid = threadIdx.x;
    __syncthreads();
    for (int stride = blockDim.x >> 1; stride > 0; stride >>= 1) {{
        if (tid < stride && values[tid + stride] > values[tid]) {{
            values[tid] = values[tid + stride];
        }}
        __syncthreads();
    }}
}}

extern "C" __global__
void solve_schur_pcg_block_2d(
    const {scalar}* __restrict__ jq,
    const bool* __restrict__ active,
    const {scalar}* __restrict__ rhs,
    const {scalar}* __restrict__ row_norm,
    const {scalar}* __restrict__ initial,
    {scalar}* __restrict__ out,
    const int nx,
    const int ny,
    const int n_cells,
    const int iterations,
    const {scalar} tolerance,
    const {scalar} eps,
    const int has_initial
) {{
    extern __shared__ unsigned char shared_raw[];
    {scalar}* x = reinterpret_cast<{scalar}*>(shared_raw);
    {scalar}* r = x + blockDim.x;
    {scalar}* z = r + blockDim.x;
    {scalar}* p = z + blockDim.x;
    {scalar}* ap = p + blockDim.x;
    {scalar}* reduction = ap + blockDim.x;

    int tid = threadIdx.x;
    bool inside = tid < n_cells;
    bool is_active = inside && active[tid];
    {scalar} diag = (
        is_active && row_norm[tid] > ({scalar})0
        ? row_norm[tid]
        : ({scalar})1
    );
    x[tid] = (
        is_active && has_initial
        ? initial[tid]
        : ({scalar})0
    );
    __syncthreads();

    ap[tid] = (
        is_active
        ? schur_at(jq, active, x, tid, nx, ny)
        : ({scalar})0
    );
    __syncthreads();
    r[tid] = is_active ? rhs[tid] - ap[tid] : ({scalar})0;
    z[tid] = r[tid] / diag;
    p[tid] = z[tid];
    reduction[tid] = inside ? r[tid] * z[tid] : ({scalar})0;
    reduce_sum(reduction);
    {scalar} rz_old = reduction[0];

    for (int iter = 0; iter < iterations; ++iter) {{
        ap[tid] = (
            is_active
            ? schur_at(jq, active, p, tid, nx, ny)
            : ({scalar})0
        );
        __syncthreads();
        reduction[tid] = inside ? p[tid] * ap[tid] : ({scalar})0;
        reduce_sum(reduction);
        {scalar} denom = reduction[0];
        reduction[tid] = inside ? abs_scalar(r[tid]) : ({scalar})0;
        reduce_max(reduction);
        {scalar} residual_linf = reduction[0];
        bool active_iteration = (
            residual_linf > tolerance
            && abs_scalar(denom) > eps
            && abs_scalar(rz_old) > eps
        );
        if (!active_iteration) {{
            break;
        }}
        {scalar} alpha = rz_old / denom;
        if (is_active) {{
            x[tid] += alpha * p[tid];
            r[tid] -= alpha * ap[tid];
            z[tid] = r[tid] / diag;
        }} else {{
            x[tid] = ({scalar})0;
            r[tid] = ({scalar})0;
            z[tid] = ({scalar})0;
        }}
        __syncthreads();
        reduction[tid] = inside ? r[tid] * z[tid] : ({scalar})0;
        reduce_sum(reduction);
        {scalar} rz_new = reduction[0];
        {scalar} beta = rz_new / rz_old;
        if (is_active) {{
            p[tid] = z[tid] + beta * p[tid];
        }} else {{
            p[tid] = ({scalar})0;
        }}
        rz_old = rz_new;
        __syncthreads();
    }}
    if (inside) {{
        out[tid] = is_active ? x[tid] : ({scalar})0;
    }}
}}
"""
    kernel = xp.RawKernel(code, "solve_schur_pcg_block_2d")
    _PCG_BLOCK_RAW_KERNELS[key] = kernel
    return kernel


def _solve_schur_dc_fixed_gpu(
    grid,
    xp,
    jq_local,
    rhs,
    row_norm,
    active,
    *,
    max_iterations: int,
    tolerance: float,
    relaxation: float,
    initial_guess=None,
    support=None,
):
    """Residual-monotone Jacobi defect correction for active Schur rows."""
    iterations = _validate_positive_int(max_iterations, "max_iterations")
    tolerance = _validate_positive_float(tolerance, "tolerance")
    relaxation = _validate_positive_float(relaxation, "relaxation")
    if relaxation > 1.0:
        raise ValueError("relaxation must not exceed 1.0")
    support = support or _masked_schur_support_from_active(
        grid,
        xp,
        jq_local,
        row_norm,
        active,
    )
    if support.n_active == 0:
        return xp.zeros_like(rhs)
    b = support.gather_cells(rhs)
    diagonal = xp.where(
        support.row_norm_A > 0.0,
        support.row_norm_A,
        xp.ones_like(support.row_norm_A),
    )
    x = (
        xp.zeros_like(b)
        if initial_guess is None
        else support.gather_cells(initial_guess)
    )
    residual = b - support.apply_schur(x)
    residual_linf = xp.max(xp.abs(residual))
    residual_tolerance = xp.asarray(tolerance, dtype=b.dtype)
    for _ in range(iterations):
        active_iteration = residual_linf > residual_tolerance
        candidate = x + relaxation * residual / diagonal
        candidate_residual = b - support.apply_schur(candidate)
        candidate_linf = xp.max(xp.abs(candidate_residual))
        accept = active_iteration & (candidate_linf <= residual_linf)
        x = xp.where(accept, candidate, x)
        residual = xp.where(accept, candidate_residual, residual)
        residual_linf = xp.where(accept, candidate_linf, residual_linf)
    return support.scatter_cells(x)


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


def _validate_positive_int(value, name):
    converted = int(value)
    if converted < 1 or converted != value:
        raise ValueError(f"{name} must be a positive integer")
    return converted


def _validate_nonnegative_int(value, name):
    converted = int(value)
    if converted < 0 or converted != value:
        raise ValueError(f"{name} must be a non-negative integer")
    return converted


def _host_scalar_float(backend, value, name: str) -> float:
    del backend, value, name
    raise RuntimeError(
        "single-scalar GPU host transfer is forbidden; use "
        "_host_scalar_packet_float at an explicit fail-close/reporting boundary"
    )


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
