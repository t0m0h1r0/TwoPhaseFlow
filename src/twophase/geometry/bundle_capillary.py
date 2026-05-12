"""Bundle-capillary covector gates for SP-AO geometric phase states.

Symbol mapping
--------------
``E_sigma(phi)`` -> :attr:`GeometricSurfaceEnergyCovector.surface_energy`.
``d_phi E_sigma`` -> :attr:`GeometricSurfaceEnergyCovector.energy_nodal_covector`.
``-d_phi E_sigma`` -> :attr:`GeometricSurfaceEnergyCovector.capillary_nodal_covector`.
``T_q w`` -> :attr:`GeometricFaceVolumeVariation.delta_q`.
``L_B(w)`` -> :attr:`GeometricBundleLift.delta_phi`.
``r_sigma(w)`` -> :attr:`GeometricCapillaryBundleWork.capillary_virtual_work`.
``M_f`` -> :attr:`GeometricFaceMassHodge.weights`.
``a_sigma=M_f^{-1}r_sigma`` ->
            :attr:`GeometricCapillaryRieszRepresentative.acceleration`.
``d_phi E_sigma + J_q^T pi`` ->
            :attr:`GeometricYoungLaplaceResidual.residual_nodal_covector`.
``T_q^T pi`` ->
            :attr:`GeometricPressureCapillaryHodge.pressure_face_covectors`.
``chi_m`` -> :attr:`GeometricComponentVolumeReactionHodge.component_masks`.
``T_q^T chi_m`` ->
            :attr:`GeometricComponentVolumeReactionHodge.component_reaction_face_covectors`.
``dS_h`` -> local surface-length derivative from
            :func:`twophase.geometry.cut_geometry_derivatives_2d`.

This module implements the first Stage 4 geometry-layer primitive from SP-AO
Section 8:

``E_sigma(phi) = sigma S_h(phi)``,
``delta q = T_q(Gamma_h) w``,
``r_sigma(w) = -sigma dS_h(phi)[L_B(w)]``,
``a_sigma = M_f^{-1} r_sigma``.

The returned nodal/face objects are geometry-layer gates, not standalone
runtime capillary forces.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .compatibility_projection import (
    _apply_jq,
    _apply_jq_transpose,
    _norm_l2,
    _norm_linf,
    _solve_schur_cg,
)
from .cell_complex import MetricCellComplex
from .gpu_runtime_guard import reject_device_value, reject_gpu_namespace
from .p1_cut_jacobian import (
    P1CutDerivatives,
    cut_geometry_derivatives_2d,
    scatter_local_to_nodes,
)
from .phase_state import GeometricPhaseState
from .swept_flux import _closure_residual_linf, _errstate, _normalize_boundary


@dataclass(frozen=True)
class GeometricSurfaceEnergyCovector:
    """Surface-energy covector on a compatible SP-AO ``q/phi`` state."""

    state: GeometricPhaseState
    derivatives: P1CutDerivatives
    sigma: float
    surface_energy: float
    energy_nodal_covector: object
    capillary_nodal_covector: object
    compatibility_residual_linf: float


@dataclass(frozen=True)
class GeometricFaceVolumeVariation:
    """Closed face-volume cochain and its induced ``delta q = T_q w``."""

    face_variations: tuple[object, object]
    delta_q: object
    boundary: tuple[str, str]
    closure_residual_linf: float
    total_delta_q: float
    max_abs_delta_q: float


@dataclass(frozen=True)
class GeometricBundleLift:
    """Identity-metric compatible gauge lift ``L_B(w)``."""

    state: GeometricPhaseState
    variation: GeometricFaceVolumeVariation
    derivatives: P1CutDerivatives
    delta_phi: object
    predicted_delta_phi: object
    lifted_delta_q: object
    residual_linf: float
    residual_l2: float
    active_cell_count: int


@dataclass(frozen=True)
class GeometricCapillaryBundleWork:
    """Scalar virtual work ``r_sigma(w)`` before face-Hodge Riesz assembly."""

    surface_covector: GeometricSurfaceEnergyCovector
    lift: GeometricBundleLift
    capillary_virtual_work: float
    energy_virtual_work: float


@dataclass(frozen=True)
class GeometricFaceMassHodge:
    """Positive face Hodge ``M_f`` for integrated face-volume cochains."""

    state: GeometricPhaseState
    weights: tuple[object, object]
    rho_l: float
    rho_g: float
    boundary: tuple[str, str]
    min_weight: float
    max_weight: float


@dataclass(frozen=True)
class GeometricCapillaryRieszRepresentative:
    """Face-space representative ``a_sigma=M_f^{-1}r_sigma``."""

    surface_covector: GeometricSurfaceEnergyCovector
    face_hodge: GeometricFaceMassHodge
    face_covectors: tuple[object, object]
    acceleration: tuple[object, object]
    schur_residual_linf: float
    weighted_acceleration_l2: float
    max_abs_face_covector: float


@dataclass(frozen=True)
class GeometricYoungLaplaceResidual:
    """Pressure-range residual for static Young-Laplace balance."""

    surface_covector: GeometricSurfaceEnergyCovector
    pressure: object
    pressure_nodal_covector: object
    residual_nodal_covector: object
    residual_linf: float
    residual_l2: float
    normal_residual_linf: float
    active_cell_count: int
    pressure_was_solved: bool


@dataclass(frozen=True)
class GeometricPressureCapillaryHodge:
    """Face-Hodge representative of capillary work minus pressure reaction."""

    capillary_riesz: GeometricCapillaryRieszRepresentative
    young_laplace_residual: GeometricYoungLaplaceResidual
    pressure_face_covectors: tuple[object, object]
    pressure_acceleration: tuple[object, object]
    residual_face_covectors: tuple[object, object]
    residual_acceleration: tuple[object, object]
    max_abs_pressure_face_covector: float
    max_abs_residual_face_covector: float
    weighted_pressure_acceleration_l2: float
    weighted_residual_acceleration_l2: float


@dataclass(frozen=True)
class GeometricComponentVolumeReactionHodge:
    """Face-Hodge projection onto component-volume reaction directions."""

    capillary_riesz: GeometricCapillaryRieszRepresentative
    component_masks: tuple[object, ...]
    component_volumes: tuple[float, ...]
    component_reaction_face_covectors: tuple[tuple[object, object], ...]
    component_reaction_accelerations: tuple[tuple[object, object], ...]
    source_face_covectors: tuple[object, object]
    source_acceleration: tuple[object, object]
    component_coefficients: object
    gram_matrix: object
    rhs: object
    represented_face_covectors: tuple[object, object]
    represented_acceleration: tuple[object, object]
    residual_face_covectors: tuple[object, object]
    residual_acceleration: tuple[object, object]
    source_weighted_l2: float
    represented_weighted_l2: float
    residual_weighted_l2: float
    residual_ratio: float
    max_abs_residual_face_covector: float
    max_component_orthogonality: float


def geometric_surface_energy_covector_2d(
    grid,
    state: GeometricPhaseState,
    *,
    sigma: float,
    tolerance: float = 1.0e-11,
) -> GeometricSurfaceEnergyCovector:
    """Return the backend-native ``d_phi E_sigma`` covector.

    Implements the SP-AO Section 8 surface-energy differential
    ``E_sigma(phi)=sigma S_h(phi)`` on the compatible gauge
    ``q=Q_h(phi)``.  The output maps the symbols
    ``dS_h`` -> ``derivatives.ds_local``,
    ``d_phi E_sigma`` -> ``energy_nodal_covector``, and the pre-lift
    ``-sigma dS_h`` factor in ``r_sigma(w)`` ->
    ``capillary_nodal_covector``.  It does not assemble ``T_q``, ``L_B``, or
    the face Hodge ``M_f``.
    """
    if grid.ndim != 2:
        raise ValueError("geometric_surface_energy_covector_2d supports 2D grids")
    if not isinstance(state, GeometricPhaseState):
        raise TypeError("state must be a GeometricPhaseState")
    sigma = _validate_sigma(sigma)
    tolerance = _validate_tolerance(tolerance)

    compatible_state = _compatible_state(
        grid,
        state,
        tolerance=tolerance,
        context="surface-energy covector",
    )

    derivatives = cut_geometry_derivatives_2d(
        grid,
        compatible_state.phi,
        level=compatible_state.stratum.level,
    )
    xp = grid.xp
    energy_local = sigma * derivatives.ds_local
    energy_nodal = scatter_local_to_nodes(grid, energy_local)
    capillary_nodal = -energy_nodal
    _validate_finite_array(xp, energy_nodal, name="energy_nodal_covector")
    _validate_finite_array(xp, capillary_nodal, name="capillary_nodal_covector")

    return GeometricSurfaceEnergyCovector(
        state=compatible_state,
        derivatives=derivatives,
        sigma=sigma,
        surface_energy=float(sigma * compatible_state.geometry.surface_length),
        energy_nodal_covector=energy_nodal,
        capillary_nodal_covector=capillary_nodal,
        compatibility_residual_linf=compatible_state.compatibility_residual_linf,
    )


def geometric_face_volume_variation_2d(
    grid,
    face_variations,
    *,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-12,
) -> GeometricFaceVolumeVariation:
    """Return ``delta q = T_q w`` for a closed liquid face-volume cochain.

    This is the Stage 4 incidence gate for supplied integrated face-volume
    variations ``w``.  With the same orientation as swept ``Phi_l``,
    ``delta q_C = -[(w_x)_{i+1/2}-(w_x)_{i-1/2}
                  +(w_y)_{j+1/2}-(w_y)_{j-1/2}]``.
    It does not construct ``w`` from interface traces; it only certifies and
    applies the closed face cochain used by the future ``T_q(Gamma_h)`` path.
    """
    if grid.ndim != 2:
        raise ValueError("geometric_face_volume_variation_2d supports 2D grids")
    reject_gpu_namespace(grid.xp, context="geometric_face_volume_variation_2d")
    tolerance = _validate_tolerance(tolerance)
    boundary = _normalize_boundary(boundary)
    complex_h = MetricCellComplex.from_grid(grid)
    xp = grid.xp
    variation_x, variation_y = _validate_face_variations(
        grid,
        face_variations,
        dtype=complex_h.cell_measures.dtype,
    )
    closure_residual = _closure_residual_linf(
        xp,
        variation_x,
        variation_y,
        boundary,
    )
    if closure_residual > tolerance:
        raise ValueError("face-volume variation violates declared boundary closure")

    with _errstate(xp):
        delta_q = -(
            (variation_x[1:, :] - variation_x[:-1, :])
            + (variation_y[:, 1:] - variation_y[:, :-1])
        )
    _validate_finite_array(xp, delta_q, name="delta_q")
    total_delta_q = _scalar_float(xp, xp.sum(delta_q))
    if abs(total_delta_q) > tolerance:
        raise ValueError("face-volume variation violates global q conservation")

    return GeometricFaceVolumeVariation(
        face_variations=(variation_x, variation_y),
        delta_q=delta_q,
        boundary=boundary,
        closure_residual_linf=closure_residual,
        total_delta_q=total_delta_q,
        max_abs_delta_q=_scalar_float(xp, xp.max(xp.abs(delta_q))),
    )


def geometric_bundle_lift_2d(
    grid,
    state: GeometricPhaseState,
    face_variations,
    *,
    boundary: tuple[str, str] = ("wall", "wall"),
    delta_phi_pred=None,
    tolerance: float = 1.0e-11,
    max_cg_iterations: int | None = None,
) -> GeometricBundleLift:
    """Lift ``T_q w`` to a compatible gauge variation ``L_B(w)``.

    Implements the identity-gauge-metric slice of the SP-AO bundle lift:

    ``L_B(w)=argmin ||delta_phi-delta_phi_pred||^2``
    subject to ``J_q delta_phi = T_q w``.

    The lift is linear and fixed-stratum.  It is a geometry-layer primitive and
    does not apply ``delta_phi`` to the state.
    """
    if grid.ndim != 2:
        raise ValueError("geometric_bundle_lift_2d supports 2D grids")
    if not isinstance(state, GeometricPhaseState):
        raise TypeError("state must be a GeometricPhaseState")
    tolerance = _validate_tolerance(tolerance)
    boundary = _normalize_boundary(boundary)
    compatible_state = _compatible_state(
        grid,
        state,
        tolerance=tolerance,
        context="bundle lift",
    )
    _validate_periodic_phi_closure(
        grid,
        compatible_state,
        boundary=boundary,
        tolerance=tolerance,
        context="bundle lift",
    )
    variation = geometric_face_volume_variation_2d(
        grid,
        face_variations,
        boundary=boundary,
        tolerance=tolerance,
    )
    xp = grid.xp
    derivatives = cut_geometry_derivatives_2d(
        grid,
        compatible_state.phi,
        level=compatible_state.stratum.level,
    )
    predicted = _validate_delta_phi_pred(
        grid,
        delta_phi_pred,
        dtype=compatible_state.phi.dtype,
    )
    rhs = variation.delta_q - _apply_jq(xp, derivatives.jq_local, predicted)
    row_norm = xp.sum(derivatives.jq_local * derivatives.jq_local, axis=-1)
    active = row_norm > 0.0
    inactive_residual = xp.where(active, xp.zeros_like(rhs), xp.abs(rhs))
    if _scalar_bool(xp.any(inactive_residual > tolerance)):
        raise ValueError("T_q w changes a cell outside the active cut stratum")

    max_cg_iterations = (
        4 * (grid.N[0] + 1) * (grid.N[1] + 1)
        if max_cg_iterations is None
        else int(max_cg_iterations)
    )
    if max_cg_iterations < 1:
        raise ValueError("max_cg_iterations must be positive")
    lagrange = _solve_schur_cg(
        grid=grid,
        jq_local=derivatives.jq_local,
        rhs=xp.where(active, rhs, xp.zeros_like(rhs)),
        row_norm=row_norm,
        active=active,
        tolerance=max(tolerance * 0.1, 1.0e-14),
        max_iterations=max_cg_iterations,
    )
    delta_phi = predicted + _apply_jq_transpose(grid, derivatives.jq_local, lagrange)
    _validate_finite_array(xp, delta_phi, name="delta_phi")
    lifted_delta_q = _apply_jq(xp, derivatives.jq_local, delta_phi)
    residual = lifted_delta_q - variation.delta_q
    residual_linf = _norm_linf(xp, residual)
    if residual_linf > tolerance:
        raise ValueError(
            "bundle lift failed to satisfy J_q delta_phi = T_q w; "
            f"residual={residual_linf:.3e}"
        )
    return GeometricBundleLift(
        state=compatible_state,
        variation=variation,
        derivatives=derivatives,
        delta_phi=delta_phi,
        predicted_delta_phi=predicted,
        lifted_delta_q=lifted_delta_q,
        residual_linf=residual_linf,
        residual_l2=_norm_l2(xp, residual),
        active_cell_count=int(_scalar_float(xp, xp.sum(active))),
    )


def geometric_capillary_bundle_work_2d(
    grid,
    state: GeometricPhaseState,
    face_variations,
    *,
    sigma: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    delta_phi_pred=None,
    tolerance: float = 1.0e-11,
    max_cg_iterations: int | None = None,
) -> GeometricCapillaryBundleWork:
    """Evaluate the scalar pre-Riesz capillary work ``r_sigma(w)``.

    The returned scalar is
    ``r_sigma(w) = -sigma dS_h(phi)[L_B(w)]``.  It is not yet the face
    acceleration ``M_f^{-1} r_sigma``.
    """
    sigma = _validate_sigma(sigma)
    lift = geometric_bundle_lift_2d(
        grid,
        state,
        face_variations,
        boundary=boundary,
        delta_phi_pred=delta_phi_pred,
        tolerance=tolerance,
        max_cg_iterations=max_cg_iterations,
    )
    surface = geometric_surface_energy_covector_2d(
        grid,
        lift.state,
        sigma=sigma,
        tolerance=tolerance,
    )
    xp = grid.xp
    energy_virtual_work = _nodal_dot(
        xp,
        surface.energy_nodal_covector,
        lift.delta_phi,
    )
    capillary_virtual_work = _nodal_dot(
        xp,
        surface.capillary_nodal_covector,
        lift.delta_phi,
    )
    return GeometricCapillaryBundleWork(
        surface_covector=surface,
        lift=lift,
        capillary_virtual_work=capillary_virtual_work,
        energy_virtual_work=energy_virtual_work,
    )


def geometric_face_mass_hodge_2d(
    grid,
    state: GeometricPhaseState,
    *,
    rho_l: float,
    rho_g: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
) -> GeometricFaceMassHodge:
    """Return the positive face Hodge for AO face-volume cochains.

    The face variable in this module is the integrated face-volume cochain
    used by ``T_q``.  Thus the diagonal Hodge uses
    ``rho_f * dual_length / face_length`` in 2D, the cochain version of the
    kinetic face mass.  This is a geometry-layer metric gate; it does not apply
    the resulting acceleration to a runtime velocity field.
    """
    if grid.ndim != 2:
        raise ValueError("geometric_face_mass_hodge_2d supports 2D grids")
    rho_l, rho_g = _validate_densities(rho_l, rho_g)
    tolerance = _validate_tolerance(tolerance)
    boundary = _normalize_boundary(boundary)
    compatible_state = _compatible_state(
        grid,
        state,
        tolerance=tolerance,
        context="face mass Hodge",
    )
    _validate_periodic_phi_closure(
        grid,
        compatible_state,
        boundary=boundary,
        tolerance=tolerance,
        context="face mass Hodge",
    )
    xp = grid.xp
    density = compatible_state.density_view(rho_l=rho_l, rho_g=rho_g)
    weight_x, weight_y = _face_volume_hodge_weights_2d(
        grid,
        density,
        boundary=boundary,
    )
    _validate_positive_face_weights(xp, (weight_x, weight_y))
    return GeometricFaceMassHodge(
        state=compatible_state,
        weights=(weight_x, weight_y),
        rho_l=rho_l,
        rho_g=rho_g,
        boundary=boundary,
        min_weight=min(
            _scalar_float(xp, xp.min(weight_x)),
            _scalar_float(xp, xp.min(weight_y)),
        ),
        max_weight=max(
            _scalar_float(xp, xp.max(weight_x)),
            _scalar_float(xp, xp.max(weight_y)),
        ),
    )


def geometric_capillary_riesz_2d(
    grid,
    state: GeometricPhaseState,
    *,
    sigma: float,
    rho_l: float,
    rho_g: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
    max_cg_iterations: int | None = None,
) -> GeometricCapillaryRieszRepresentative:
    """Assemble ``a_sigma=M_f^{-1}r_sigma`` on the AO face-volume space.

    The covector is built by the adjoint of the already implemented bundle
    lift.  With ``c=-sigma dS_h`` and ``S_q=J_q J_q^T``, solve
    ``S_q lambda = J_q c`` and return ``r_sigma=T_q^T lambda``.  For every
    closed admissible face-volume cochain ``w``,
    ``sum_f r_sigma_f w_f`` equals
    ``-sigma dS_h(phi)[L_B(w)]``.
    """
    sigma = _validate_sigma(sigma)
    tolerance = _validate_tolerance(tolerance)
    boundary = _normalize_boundary(boundary)
    surface = geometric_surface_energy_covector_2d(
        grid,
        state,
        sigma=sigma,
        tolerance=tolerance,
    )
    face_hodge = geometric_face_mass_hodge_2d(
        grid,
        surface.state,
        rho_l=rho_l,
        rho_g=rho_g,
        boundary=boundary,
        tolerance=tolerance,
    )
    xp = grid.xp
    derivatives = surface.derivatives
    rhs = _apply_jq(xp, derivatives.jq_local, surface.capillary_nodal_covector)
    row_norm = xp.sum(derivatives.jq_local * derivatives.jq_local, axis=-1)
    active = row_norm > 0.0
    max_cg_iterations = (
        4 * (grid.N[0] + 1) * (grid.N[1] + 1)
        if max_cg_iterations is None
        else int(max_cg_iterations)
    )
    if max_cg_iterations < 1:
        raise ValueError("max_cg_iterations must be positive")
    lagrange = _solve_schur_cg(
        grid=grid,
        jq_local=derivatives.jq_local,
        rhs=xp.where(active, rhs, xp.zeros_like(rhs)),
        row_norm=row_norm,
        active=active,
        tolerance=max(tolerance * 0.1, 1.0e-14),
        max_iterations=max_cg_iterations,
    )
    projected_rhs = _apply_jq(
        xp,
        derivatives.jq_local,
        _apply_jq_transpose(grid, derivatives.jq_local, lagrange),
    )
    schur_residual = xp.where(active, projected_rhs - rhs, xp.zeros_like(rhs))
    schur_residual_linf = _norm_linf(xp, schur_residual)
    if schur_residual_linf > tolerance:
        raise ValueError(
            "capillary Riesz adjoint solve failed; "
            f"residual={schur_residual_linf:.3e}"
        )
    face_covectors = _face_incidence_adjoint_2d(
        grid,
        lagrange,
        boundary=boundary,
    )
    acceleration = tuple(
        covector / weight
        for covector, weight in zip(face_covectors, face_hodge.weights, strict=True)
    )
    for axis, component in enumerate(acceleration):
        _validate_finite_array(xp, component, name=f"axis-{axis} capillary acceleration")
    return GeometricCapillaryRieszRepresentative(
        surface_covector=surface,
        face_hodge=face_hodge,
        face_covectors=face_covectors,
        acceleration=acceleration,
        schur_residual_linf=schur_residual_linf,
        weighted_acceleration_l2=_face_weighted_l2(
            xp,
            acceleration,
            face_hodge.weights,
        ),
        max_abs_face_covector=max(
            _scalar_float(xp, xp.max(xp.abs(face_covectors[0]))),
            _scalar_float(xp, xp.max(xp.abs(face_covectors[1]))),
        ),
    )


def geometric_young_laplace_residual_2d(
    grid,
    state: GeometricPhaseState,
    *,
    sigma: float,
    pressure=None,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
    max_cg_iterations: int | None = None,
) -> GeometricYoungLaplaceResidual:
    """Evaluate the pressure-range residual for static capillary balance.

    The SP-AO static range condition is
    ``d_phi E_sigma + J_q^T pi = 0`` on the fixed cut stratum.  When
    ``pressure`` is supplied this routine evaluates that residual directly.
    When it is omitted, the least-squares pressure multiplier is found from
    ``J_q J_q^T pi = -J_q d_phi E_sigma``.  A small
    ``residual_linf`` certifies that the capillary covector is pressure
    representable; a large residual is the geometry-layer nonzero-drive gate.
    """
    if grid.ndim != 2:
        raise ValueError("geometric_young_laplace_residual_2d supports 2D grids")
    sigma = _validate_sigma(sigma)
    tolerance = _validate_tolerance(tolerance)
    boundary = _normalize_boundary(boundary)
    surface = geometric_surface_energy_covector_2d(
        grid,
        state,
        sigma=sigma,
        tolerance=tolerance,
    )
    _validate_periodic_phi_closure(
        grid,
        surface.state,
        boundary=boundary,
        tolerance=tolerance,
        context="Young-Laplace residual",
    )
    xp = grid.xp
    derivatives = surface.derivatives
    row_norm = xp.sum(derivatives.jq_local * derivatives.jq_local, axis=-1)
    active = row_norm > 0.0
    pressure_was_solved = pressure is None
    if pressure is None:
        rhs = -_apply_jq(xp, derivatives.jq_local, surface.energy_nodal_covector)
        max_cg_iterations = (
            4 * (grid.N[0] + 1) * (grid.N[1] + 1)
            if max_cg_iterations is None
            else int(max_cg_iterations)
        )
        if max_cg_iterations < 1:
            raise ValueError("max_cg_iterations must be positive")
        pressure_cell = _solve_schur_cg(
            grid=grid,
            jq_local=derivatives.jq_local,
            rhs=xp.where(active, rhs, xp.zeros_like(rhs)),
            row_norm=row_norm,
            active=active,
            tolerance=max(tolerance * 0.1, 1.0e-14),
            max_iterations=max_cg_iterations,
        )
    else:
        pressure_cell = _validate_cell_pressure(
            grid,
            pressure,
            dtype=surface.state.q.dtype,
        )

    pressure_nodal = _apply_jq_transpose(grid, derivatives.jq_local, pressure_cell)
    residual_nodal = surface.energy_nodal_covector + pressure_nodal
    _validate_finite_array(xp, pressure_nodal, name="pressure_nodal_covector")
    _validate_finite_array(xp, residual_nodal, name="Young-Laplace residual")
    normal_residual = xp.where(
        active,
        _apply_jq(xp, derivatives.jq_local, residual_nodal),
        xp.zeros_like(row_norm),
    )
    normal_residual_linf = _norm_linf(xp, normal_residual)
    if pressure_was_solved and normal_residual_linf > tolerance:
        raise ValueError(
            "Young-Laplace pressure solve failed; "
            f"residual={normal_residual_linf:.3e}"
        )
    return GeometricYoungLaplaceResidual(
        surface_covector=surface,
        pressure=pressure_cell,
        pressure_nodal_covector=pressure_nodal,
        residual_nodal_covector=residual_nodal,
        residual_linf=_norm_linf(xp, residual_nodal),
        residual_l2=_norm_l2(xp, residual_nodal),
        normal_residual_linf=normal_residual_linf,
        active_cell_count=int(_scalar_float(xp, xp.sum(active))),
        pressure_was_solved=pressure_was_solved,
    )


def geometric_pressure_capillary_hodge_2d(
    grid,
    state: GeometricPhaseState,
    *,
    sigma: float,
    rho_l: float,
    rho_g: float,
    pressure=None,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
    max_cg_iterations: int | None = None,
) -> GeometricPressureCapillaryHodge:
    """Assemble the pressure/capillary face-Hodge adjoint gate.

    With ``pi`` a cell pressure multiplier, ``T_q^T pi`` is the face covector
    whose work on a closed face-volume cochain ``w`` equals
    ``pi^T T_q w`` and ``(J_q^T pi)^T L_B(w)``.  The returned residual face
    covector is

    ``r_sigma - T_q^T pi``,

    so its work equals
    ``-(d_phi E_sigma + J_q^T pi)^T L_B(w)`` for the same bundle lift and
    face Hodge.  This is a geometry-layer identity gate, not a runtime pressure
    subtraction route.
    """
    sigma = _validate_sigma(sigma)
    rho_l, rho_g = _validate_densities(rho_l, rho_g)
    tolerance = _validate_tolerance(tolerance)
    boundary = _normalize_boundary(boundary)
    capillary = geometric_capillary_riesz_2d(
        grid,
        state,
        sigma=sigma,
        rho_l=rho_l,
        rho_g=rho_g,
        boundary=boundary,
        tolerance=tolerance,
        max_cg_iterations=max_cg_iterations,
    )
    young_laplace = geometric_young_laplace_residual_2d(
        grid,
        capillary.surface_covector.state,
        sigma=sigma,
        pressure=pressure,
        boundary=boundary,
        tolerance=tolerance,
        max_cg_iterations=max_cg_iterations,
    )
    xp = grid.xp
    pressure_face = _face_incidence_adjoint_2d(
        grid,
        young_laplace.pressure,
        boundary=boundary,
    )
    residual_face = tuple(
        capillary_covector - pressure_covector
        for capillary_covector, pressure_covector in zip(
            capillary.face_covectors,
            pressure_face,
            strict=True,
        )
    )
    pressure_acceleration = tuple(
        covector / weight
        for covector, weight in zip(
            pressure_face,
            capillary.face_hodge.weights,
            strict=True,
        )
    )
    residual_acceleration = tuple(
        covector / weight
        for covector, weight in zip(
            residual_face,
            capillary.face_hodge.weights,
            strict=True,
        )
    )
    for axis, component in enumerate(pressure_acceleration):
        _validate_finite_array(
            xp,
            component,
            name=f"axis-{axis} pressure acceleration",
        )
    for axis, component in enumerate(residual_acceleration):
        _validate_finite_array(
            xp,
            component,
            name=f"axis-{axis} pressure-capillary residual acceleration",
        )
    return GeometricPressureCapillaryHodge(
        capillary_riesz=capillary,
        young_laplace_residual=young_laplace,
        pressure_face_covectors=pressure_face,
        pressure_acceleration=pressure_acceleration,
        residual_face_covectors=residual_face,
        residual_acceleration=residual_acceleration,
        max_abs_pressure_face_covector=max(
            _scalar_float(xp, xp.max(xp.abs(pressure_face[0]))),
            _scalar_float(xp, xp.max(xp.abs(pressure_face[1]))),
        ),
        max_abs_residual_face_covector=max(
            _scalar_float(xp, xp.max(xp.abs(residual_face[0]))),
            _scalar_float(xp, xp.max(xp.abs(residual_face[1]))),
        ),
        weighted_pressure_acceleration_l2=_face_weighted_l2(
            xp,
            pressure_acceleration,
            capillary.face_hodge.weights,
        ),
        weighted_residual_acceleration_l2=_face_weighted_l2(
            xp,
            residual_acceleration,
            capillary.face_hodge.weights,
        ),
    )


def geometric_component_volume_reaction_hodge_2d(
    grid,
    state: GeometricPhaseState,
    *,
    sigma: float,
    rho_l: float,
    rho_g: float,
    component_masks=None,
    source_face_covectors=None,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
    max_cg_iterations: int | None = None,
    component_theta_threshold: float = 1.0e-12,
    rcond: float = 1.0e-12,
) -> GeometricComponentVolumeReactionHodge:
    """Remove component-volume reaction directions in the face Hodge metric.

    For component indicator cochains ``chi_m``, the reaction face covector is
    ``T_q^T chi_m``.  Its work on a closed face-volume cochain ``w`` is
    ``chi_m^T T_q w``, the component-volume variation.  This gate projects a
    supplied face covector, or the capillary covector ``r_sigma`` by default,
    away from the span of those component reactions in the same ``M_f`` metric
    used by pressure/capillary Hodge diagnostics.
    """
    sigma = _validate_sigma(sigma)
    rho_l, rho_g = _validate_densities(rho_l, rho_g)
    tolerance = _validate_tolerance(tolerance)
    boundary = _normalize_boundary(boundary)
    component_theta_threshold = _validate_component_theta_threshold(
        component_theta_threshold
    )
    rcond = _validate_rcond(rcond)
    capillary = geometric_capillary_riesz_2d(
        grid,
        state,
        sigma=sigma,
        rho_l=rho_l,
        rho_g=rho_g,
        boundary=boundary,
        tolerance=tolerance,
        max_cg_iterations=max_cg_iterations,
    )
    xp = grid.xp
    if source_face_covectors is None:
        source_face = capillary.face_covectors
    else:
        source_face = _validate_face_covectors(
            grid,
            source_face_covectors,
            dtype=capillary.surface_covector.state.q.dtype,
            x_name="x-face source covector",
            y_name="y-face source covector",
        )
    source_acceleration = tuple(
        covector / weight
        for covector, weight in zip(
            source_face,
            capillary.face_hodge.weights,
            strict=True,
        )
    )
    for axis, component in enumerate(source_acceleration):
        _validate_finite_array(xp, component, name=f"axis-{axis} source acceleration")

    masks = (
        _component_volume_masks_2d(
            grid,
            capillary.surface_covector.state,
            boundary=boundary,
            component_theta_threshold=component_theta_threshold,
        )
        if component_masks is None
        else _validate_component_masks(
            grid,
            component_masks,
            dtype=capillary.surface_covector.state.q.dtype,
        )
    )
    if not masks:
        raise ValueError("component-volume reaction requires at least one component")
    component_volumes = tuple(
        _scalar_float(xp, xp.sum(mask * capillary.surface_covector.state.q))
        for mask in masks
    )
    if any(volume <= 0.0 for volume in component_volumes):
        raise ValueError("component masks must select positive liquid volume")
    reaction_face = tuple(
        _face_incidence_adjoint_2d(grid, mask, boundary=boundary)
        for mask in masks
    )
    reaction_acceleration = tuple(
        tuple(
            covector / weight
            for covector, weight in zip(
                covectors,
                capillary.face_hodge.weights,
                strict=True,
            )
        )
        for covectors in reaction_face
    )
    for component_index, acceleration in enumerate(reaction_acceleration):
        for axis, component in enumerate(acceleration):
            _validate_finite_array(
                xp,
                component,
                name=(
                    f"component-{component_index} axis-{axis} "
                    "volume-reaction acceleration"
                ),
            )

    gram_host = np.zeros((len(masks), len(masks)), dtype=float)
    rhs_host = np.zeros(len(masks), dtype=float)
    for row, left in enumerate(reaction_acceleration):
        rhs_host[row] = _face_weighted_dot(
            xp,
            source_acceleration,
            left,
            capillary.face_hodge.weights,
        )
        for col, right in enumerate(reaction_acceleration):
            gram_host[row, col] = _face_weighted_dot(
                xp,
                left,
                right,
                capillary.face_hodge.weights,
            )
    coefficients_host = np.linalg.lstsq(gram_host, rhs_host, rcond=rcond)[0]
    coefficients = xp.asarray(coefficients_host, dtype=source_face[0].dtype)
    gram = xp.asarray(gram_host, dtype=source_face[0].dtype)
    rhs = xp.asarray(rhs_host, dtype=source_face[0].dtype)
    _validate_finite_array(xp, coefficients, name="component coefficients")
    _validate_finite_array(xp, gram, name="component reaction Gram matrix")
    _validate_finite_array(xp, rhs, name="component reaction rhs")

    represented_face = tuple(xp.zeros_like(component) for component in source_face)
    for coefficient, covectors in zip(coefficients_host, reaction_face, strict=True):
        represented_face = tuple(
            represented + float(coefficient) * covector
            for represented, covector in zip(
                represented_face,
                covectors,
                strict=True,
            )
        )
    residual_face = tuple(
        source - represented
        for source, represented in zip(source_face, represented_face, strict=True)
    )
    represented_acceleration = tuple(
        covector / weight
        for covector, weight in zip(
            represented_face,
            capillary.face_hodge.weights,
            strict=True,
        )
    )
    residual_acceleration = tuple(
        covector / weight
        for covector, weight in zip(
            residual_face,
            capillary.face_hodge.weights,
            strict=True,
        )
    )
    for axis, component in enumerate(residual_acceleration):
        _validate_finite_array(
            xp,
            component,
            name=f"axis-{axis} component-volume residual acceleration",
        )
    for axis, component in enumerate(represented_acceleration):
        _validate_finite_array(
            xp,
            component,
            name=f"axis-{axis} component-volume represented acceleration",
        )
    max_orthogonality = (
        max(
            abs(
                _face_weighted_dot(
                    xp,
                    residual_acceleration,
                    reaction,
                    capillary.face_hodge.weights,
                )
            )
            for reaction in reaction_acceleration
        )
        if reaction_acceleration
        else 0.0
    )
    source_norm = _face_weighted_l2(
        xp,
        source_acceleration,
        capillary.face_hodge.weights,
    )
    residual_norm = _face_weighted_l2(
        xp,
        residual_acceleration,
        capillary.face_hodge.weights,
    )
    return GeometricComponentVolumeReactionHodge(
        capillary_riesz=capillary,
        component_masks=masks,
        component_volumes=component_volumes,
        component_reaction_face_covectors=reaction_face,
        component_reaction_accelerations=reaction_acceleration,
        source_face_covectors=source_face,
        source_acceleration=source_acceleration,
        component_coefficients=coefficients,
        gram_matrix=gram,
        rhs=rhs,
        represented_face_covectors=represented_face,
        represented_acceleration=represented_acceleration,
        residual_face_covectors=residual_face,
        residual_acceleration=residual_acceleration,
        source_weighted_l2=source_norm,
        represented_weighted_l2=_face_weighted_l2(
            xp,
            represented_acceleration,
            capillary.face_hodge.weights,
        ),
        residual_weighted_l2=residual_norm,
        residual_ratio=residual_norm / max(source_norm, 1.0e-30),
        max_abs_residual_face_covector=max(
            _scalar_float(xp, xp.max(xp.abs(residual_face[0]))),
            _scalar_float(xp, xp.max(xp.abs(residual_face[1]))),
        ),
        max_component_orthogonality=max_orthogonality,
    )


def _validate_sigma(sigma: float) -> float:
    converted = float(sigma)
    if not (math.isfinite(converted) and converted >= 0.0):
        raise ValueError("sigma must be finite and non-negative")
    return converted


def _validate_densities(rho_l: float, rho_g: float) -> tuple[float, float]:
    converted_l = float(rho_l)
    converted_g = float(rho_g)
    if not (math.isfinite(converted_l) and converted_l > 0.0):
        raise ValueError("rho_l must be finite and positive")
    if not (math.isfinite(converted_g) and converted_g > 0.0):
        raise ValueError("rho_g must be finite and positive")
    return converted_l, converted_g


def _validate_tolerance(tolerance: float) -> float:
    converted = float(tolerance)
    if not (math.isfinite(converted) and converted >= 0.0):
        raise ValueError("tolerance must be finite and non-negative")
    return converted


def _validate_component_theta_threshold(component_theta_threshold: float) -> float:
    converted = float(component_theta_threshold)
    if not (math.isfinite(converted) and 0.0 <= converted <= 1.0):
        raise ValueError("component_theta_threshold must be finite and in [0, 1]")
    return converted


def _validate_rcond(rcond: float) -> float:
    converted = float(rcond)
    if not (math.isfinite(converted) and converted >= 0.0):
        raise ValueError("rcond must be finite and non-negative")
    return converted


def _validate_finite_array(xp, value, *, name: str) -> None:
    if _scalar_bool(xp.any(~xp.isfinite(value))):
        raise ValueError(f"{name} must be finite")


def _compatible_state(
    grid,
    state: GeometricPhaseState,
    *,
    tolerance: float,
    context: str,
) -> GeometricPhaseState:
    reject_gpu_namespace(grid.xp, context=f"{context} dense exact AO runtime")
    try:
        return type(state).from_q_phi(
            grid,
            state.q,
            state.phi,
            level=state.stratum.level,
            tolerance=tolerance,
            require_compatible=True,
            ledger=state.ledger,
        )
    except ValueError as exc:
        raise ValueError(f"{context} requires a compatible q/phi state") from exc


def _validate_face_variations(grid, face_variations, *, dtype):
    if len(face_variations) != 2:
        raise ValueError("2D face variations must contain x- and y-face arrays")
    xp = grid.xp
    variation_x = xp.asarray(face_variations[0], dtype=dtype)
    variation_y = xp.asarray(face_variations[1], dtype=dtype)
    expected_x = (grid.N[0] + 1, grid.N[1])
    expected_y = (grid.N[0], grid.N[1] + 1)
    if tuple(variation_x.shape) != expected_x:
        raise ValueError(f"x-face volume variation shape must be {expected_x}")
    if tuple(variation_y.shape) != expected_y:
        raise ValueError(f"y-face volume variation shape must be {expected_y}")
    _validate_finite_array(grid.xp, variation_x, name="x-face volume variation")
    _validate_finite_array(grid.xp, variation_y, name="y-face volume variation")
    return variation_x, variation_y


def _validate_face_covectors(
    grid,
    face_covectors,
    *,
    dtype,
    x_name: str,
    y_name: str,
):
    if len(face_covectors) != 2:
        raise ValueError("2D face covectors must contain x- and y-face arrays")
    xp = grid.xp
    covector_x = xp.asarray(face_covectors[0], dtype=dtype)
    covector_y = xp.asarray(face_covectors[1], dtype=dtype)
    expected_x = (grid.N[0] + 1, grid.N[1])
    expected_y = (grid.N[0], grid.N[1] + 1)
    if tuple(covector_x.shape) != expected_x:
        raise ValueError(f"{x_name} shape must be {expected_x}")
    if tuple(covector_y.shape) != expected_y:
        raise ValueError(f"{y_name} shape must be {expected_y}")
    _validate_finite_array(xp, covector_x, name=x_name)
    _validate_finite_array(xp, covector_y, name=y_name)
    return covector_x, covector_y


def _validate_component_masks(grid, component_masks, *, dtype) -> tuple[object, ...]:
    if component_masks is None:
        return ()
    xp = grid.xp
    expected_shape = (grid.N[0], grid.N[1])
    masks = []
    for index, mask in enumerate(component_masks):
        mask_dev = xp.asarray(mask, dtype=dtype)
        if tuple(mask_dev.shape) != expected_shape:
            raise ValueError(f"component mask shape must be {expected_shape}")
        _validate_finite_array(xp, mask_dev, name=f"component-{index} mask")
        if _scalar_bool(xp.any(mask_dev < 0.0)):
            raise ValueError("component masks must be non-negative")
        if _scalar_bool(xp.any(mask_dev > 1.0)):
            raise ValueError("component masks must not exceed one")
        if _scalar_float(xp, xp.max(mask_dev)) <= 0.0:
            raise ValueError("component masks must be nonzero")
        masks.append(mask_dev)
    return tuple(masks)


def _component_volume_masks_2d(
    grid,
    state: GeometricPhaseState,
    *,
    boundary: tuple[str, str],
    component_theta_threshold: float,
) -> tuple[object, ...]:
    if _scalar_bool(grid.xp.any(state.stratum.cell_cases == 10)):
        raise ValueError(
            "default component masks require cell-connected liquid support; "
            "split-cell component topology needs explicit component_masks"
        )
    theta = _host_numpy(state.theta)
    support = np.asarray(theta > component_theta_threshold, dtype=bool)
    visited = np.zeros_like(support, dtype=bool)
    masks = []
    nx, ny = support.shape
    for seed_i in range(nx):
        for seed_j in range(ny):
            if visited[seed_i, seed_j] or not support[seed_i, seed_j]:
                continue
            mask = np.zeros_like(support, dtype=bool)
            stack = [(seed_i, seed_j)]
            visited[seed_i, seed_j] = True
            while stack:
                cell_i, cell_j = stack.pop()
                mask[cell_i, cell_j] = True
                for next_i, next_j in _component_neighbor_indices(
                    cell_i,
                    cell_j,
                    shape=(nx, ny),
                    boundary=boundary,
                ):
                    if visited[next_i, next_j] or not support[next_i, next_j]:
                        continue
                    visited[next_i, next_j] = True
                    stack.append((next_i, next_j))
            masks.append(grid.xp.asarray(mask, dtype=state.q.dtype))
    return tuple(masks)


def _component_neighbor_indices(
    cell_i: int,
    cell_j: int,
    *,
    shape: tuple[int, int],
    boundary: tuple[str, str],
):
    nx, ny = shape
    for axis_i, axis_j, axis in ((-1, 0, 0), (1, 0, 0), (0, -1, 1), (0, 1, 1)):
        next_i = cell_i + axis_i
        next_j = cell_j + axis_j
        if next_i < 0 or next_i >= nx:
            if boundary[axis] != "periodic":
                continue
            next_i %= nx
        if next_j < 0 or next_j >= ny:
            if boundary[axis] != "periodic":
                continue
            next_j %= ny
        yield next_i, next_j


def _validate_delta_phi_pred(grid, delta_phi_pred, *, dtype):
    xp = grid.xp
    if delta_phi_pred is None:
        return xp.zeros((grid.N[0] + 1, grid.N[1] + 1), dtype=dtype)
    predicted = xp.asarray(delta_phi_pred, dtype=dtype)
    expected_shape = (grid.N[0] + 1, grid.N[1] + 1)
    if tuple(predicted.shape) != expected_shape:
        raise ValueError(f"delta_phi_pred shape must be {expected_shape}")
    _validate_finite_array(xp, predicted, name="delta_phi_pred")
    return predicted


def _validate_cell_pressure(grid, pressure, *, dtype):
    xp = grid.xp
    pressure_cell = xp.asarray(pressure, dtype=dtype)
    expected_shape = (grid.N[0], grid.N[1])
    if tuple(pressure_cell.shape) != expected_shape:
        raise ValueError(f"pressure shape must be {expected_shape}")
    _validate_finite_array(xp, pressure_cell, name="pressure")
    return pressure_cell


def _face_volume_hodge_weights_2d(grid, density, *, boundary: tuple[str, str]):
    xp = grid.xp
    dtype = density.dtype
    complex_h = MetricCellComplex.from_grid(grid)
    x = _astype_like(complex_h.x_edges, density)
    y = _astype_like(complex_h.y_edges, density)
    dx = x[1:] - x[:-1]
    dy = y[1:] - y[:-1]

    rho_x = xp.zeros((grid.N[0] + 1, grid.N[1]), dtype=dtype)
    if grid.N[0] > 1:
        rho_x[1:-1, :] = 0.5 * (density[:-1, :] + density[1:, :])
    if boundary[0] == "periodic":
        periodic_rho = 0.5 * (density[-1, :] + density[0, :])
        rho_x[0, :] = periodic_rho
        rho_x[-1, :] = periodic_rho
    else:
        rho_x[0, :] = density[0, :]
        rho_x[-1, :] = density[-1, :]

    dual_x = xp.zeros((grid.N[0] + 1, 1), dtype=dtype)
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

    rho_y = xp.zeros((grid.N[0], grid.N[1] + 1), dtype=dtype)
    if grid.N[1] > 1:
        rho_y[:, 1:-1] = 0.5 * (density[:, :-1] + density[:, 1:])
    if boundary[1] == "periodic":
        periodic_rho = 0.5 * (density[:, -1] + density[:, 0])
        rho_y[:, 0] = periodic_rho
        rho_y[:, -1] = periodic_rho
    else:
        rho_y[:, 0] = density[:, 0]
        rho_y[:, -1] = density[:, -1]

    dual_y = xp.zeros((1, grid.N[1] + 1), dtype=dtype)
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
    return weight_x, weight_y


def _validate_positive_face_weights(xp, weights) -> None:
    for axis, weight in enumerate(weights):
        _validate_finite_array(xp, weight, name=f"axis-{axis} face Hodge weight")
        if _scalar_bool(xp.any(weight <= 0.0)):
            raise ValueError("face Hodge weights must be positive")


def _astype_like(value, reference):
    if getattr(value, "dtype", None) == getattr(reference, "dtype", None):
        return value
    return value.astype(reference.dtype, copy=False)


def _validate_periodic_phi_closure(
    grid,
    state: GeometricPhaseState,
    *,
    boundary: tuple[str, str],
    tolerance: float,
    context: str,
) -> None:
    xp = grid.xp
    residuals = []
    if boundary[0] == "periodic":
        residuals.append(xp.max(xp.abs(state.phi[0, :] - state.phi[-1, :])))
    if boundary[1] == "periodic":
        residuals.append(xp.max(xp.abs(state.phi[:, 0] - state.phi[:, -1])))
    if not residuals:
        return
    residual = max(_scalar_float(xp, value) for value in residuals)
    if residual > tolerance:
        raise ValueError(f"{context} requires periodic phi closure")


def _face_incidence_adjoint_2d(
    grid,
    cell_values,
    *,
    boundary: tuple[str, str],
):
    xp = grid.xp
    values = xp.asarray(cell_values)
    covector_x = xp.zeros((grid.N[0] + 1, grid.N[1]), dtype=values.dtype)
    covector_y = xp.zeros((grid.N[0], grid.N[1] + 1), dtype=values.dtype)

    covector_x[0, :] = values[0, :]
    if grid.N[0] > 1:
        covector_x[1:-1, :] = values[1:, :] - values[:-1, :]
    covector_x[-1, :] = -values[-1, :]
    if boundary[0] == "periodic":
        seam_covector = 0.5 * (values[0, :] - values[-1, :])
        covector_x[0, :] = seam_covector
        covector_x[-1, :] = seam_covector
    else:
        covector_x[0, :] = 0.0
        covector_x[-1, :] = 0.0

    covector_y[:, 0] = values[:, 0]
    if grid.N[1] > 1:
        covector_y[:, 1:-1] = values[:, 1:] - values[:, :-1]
    covector_y[:, -1] = -values[:, -1]
    if boundary[1] == "periodic":
        seam_covector = 0.5 * (values[:, 0] - values[:, -1])
        covector_y[:, 0] = seam_covector
        covector_y[:, -1] = seam_covector
    else:
        covector_y[:, 0] = 0.0
        covector_y[:, -1] = 0.0

    _validate_finite_array(xp, covector_x, name="x-face capillary covector")
    _validate_finite_array(xp, covector_y, name="y-face capillary covector")
    return covector_x, covector_y


def _face_weighted_l2(xp, components, weights) -> float:
    total = None
    for component, weight in zip(components, weights, strict=True):
        contribution = xp.sum(weight * component * component)
        total = contribution if total is None else total + contribution
    return math.sqrt(max(_scalar_float(xp, total), 0.0))


def _face_weighted_dot(xp, left_components, right_components, weights) -> float:
    total = None
    for left, right, weight in zip(
        left_components,
        right_components,
        weights,
        strict=True,
    ):
        contribution = xp.sum(weight * left * right)
        total = contribution if total is None else total + contribution
    return _scalar_float(xp, total)


def _nodal_dot(xp, left, right) -> float:
    return _scalar_float(xp, xp.sum(left * right))


def _host_numpy(value):
    reject_device_value(value, context="component-volume mask host boundary")
    return np.asarray(value)


def _scalar_bool(value) -> bool:
    reject_device_value(value, context="bundle capillary scalar reduction")
    return bool(value)


def _scalar_float(xp, value) -> float:
    reject_device_value(value, context="bundle capillary scalar reduction")
    return float(value)
