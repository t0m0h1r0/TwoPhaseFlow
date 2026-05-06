"""Fixed-stratum Riesz diagnostics for closed-interface capillarity.

Symbol mapping
--------------
``T`` -> conservative face transport ``-D_f(psi_f u_f)``
``dE`` -> :func:`trace_surface_length_gradient_2d`
``dV`` -> :func:`liquid_area_gradient_2d`
``M_f`` -> face kinetic-energy/mass weights
``s`` -> acceleration cochain ``-M_f^{-1} T^T dE``
``B`` -> component-volume reaction cochain ``M_f^{-1} T^T dV``

The routines in this file are diagnostic proof tools.  They do not change the
production pressure-jump force.  Their purpose is to test the A3 chain

    surface-energy virtual work -> face-space Riesz representative -> Hodge gate

on one fixed marching-squares stratum.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .closed_interface_geometry import liquid_area_gradient_2d
from .closed_interface_geometry import trace_surface_length_2d
from .closed_interface_geometry import trace_surface_length_gradient_2d
from .closed_interface_stratum import ClosedInterfaceStratum
from .closed_interface_stratum import array_to_numpy
from .closed_interface_stratum import build_closed_interface_stratum
from .transport_variational_capillary import _negative_face_divergence_adjoint


@dataclass(frozen=True)
class ClosedInterfaceRieszCochain:
    """Surface and component-reaction cochains on one fixed stratum."""

    stratum: ClosedInterfaceStratum
    psi: Any
    surface_nodal_covector: Any
    volume_nodal_covector: Any
    surface_acceleration: list[Any]
    volume_reaction_acceleration: list[Any]
    surface_force_covector: list[Any]
    volume_reaction_force_covector: list[Any]
    face_weight_components: list[Any]
    phase_threshold: float
    sigma: float


@dataclass(frozen=True)
class VirtualWorkCheck:
    """Finite-difference and Riesz-work residuals for one face velocity."""

    valid: bool
    finite_difference: float
    gradient_action: float
    capillary_power: float
    finite_difference_gradient_residual: float
    finite_difference_power_residual: float
    riesz_residual: float
    reason: str


@dataclass(frozen=True)
class WeightedHodgeDecomposition:
    """Weighted projection into ``range(M_f^{-1} D_f^T)``."""

    range_components: list[Any]
    hodge_components: list[Any]
    component_weighted_l2: float
    range_weighted_l2: float
    hodge_weighted_l2: float
    hodge_divergence_linf: float


@dataclass(frozen=True)
class ComponentReactionHodgeGate:
    """Hodge residual after adding the area/component reaction direction."""

    surface_hodge_weighted_l2: float
    volume_hodge_weighted_l2: float
    beta: float
    residual_components: list[Any]
    residual_weighted_l2: float
    residual_ratio: float
    residual_divergence_linf: float


def face_measure_components(*, xp, grid) -> list[Any]:
    """Return face-control measures for a 2-D node-centred grid."""
    if grid.ndim != 2:
        raise ValueError("closed-interface Riesz diagnostics currently support 2D")
    measures = []
    for axis in range(grid.ndim):
        d_face = xp.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
        d_shape = [1] * grid.ndim
        d_shape[axis] = -1
        transverse_axis = 1 - axis
        face_area = xp.asarray(grid.h[transverse_axis])
        area_shape = [1] * grid.ndim
        area_shape[transverse_axis] = -1
        measures.append(d_face.reshape(d_shape) * face_area.reshape(area_shape))
    return measures


def face_mass_components(*, xp, grid, rho=None) -> list[Any]:
    """Return ``M_f`` weights, using arithmetic face density when supplied."""
    measures = face_measure_components(xp=xp, grid=grid)
    if rho is None:
        return measures
    rho_arr = xp.asarray(rho)
    weights = []
    for axis, measure in enumerate(measures):
        n_cells = grid.N[axis]
        low = _axis_slice(axis, 0, n_cells, grid.ndim)
        high = _axis_slice(axis, 1, n_cells + 1, grid.ndim)
        rho_face = 0.5 * (rho_arr[low] + rho_arr[high])
        weights.append(rho_face * measure)
    return weights


def closed_interface_riesz_cochain(
    *,
    xp,
    grid,
    psi,
    fccd,
    sigma: float,
    rho=None,
    phase_threshold: float = 0.5,
    threshold_tol: float = 0.0,
) -> ClosedInterfaceRieszCochain:
    """Build ``s=-M_f^{-1}T^Td(sigma S_h)`` and ``B=M_f^{-1}T^TdV_h``.

    The transport map is the conservative face map already used by the current
    transport-variational capillary diagnostics:

    ``T(u) = -D_f(psi_f u_f)``.
    """
    stratum = build_closed_interface_stratum(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=float(phase_threshold),
        threshold_tol=float(threshold_tol),
    )
    if not stratum.regular:
        raise ValueError("closed-interface Riesz cochain requires a regular stratum")
    psi_arr = xp.asarray(psi)
    surface_nodal = trace_surface_length_gradient_2d(
        xp=xp,
        grid=grid,
        psi=psi_arr,
        sigma=float(sigma),
        phase_threshold=float(phase_threshold),
    )
    volume_nodal = liquid_area_gradient_2d(
        xp=xp,
        grid=grid,
        psi=psi_arr,
        phase_threshold=float(phase_threshold),
    )
    weights = face_mass_components(xp=xp, grid=grid, rho=rho)
    surface_force = _negative_transport_adjoint_force_covector(
        xp=xp,
        fccd=fccd,
        psi=psi_arr,
        nodal_covector=surface_nodal,
    )
    negative_volume_force = _negative_transport_adjoint_force_covector(
        xp=xp,
        fccd=fccd,
        psi=psi_arr,
        nodal_covector=volume_nodal,
    )
    volume_force = [-component for component in negative_volume_force]
    return ClosedInterfaceRieszCochain(
        stratum=stratum,
        psi=psi_arr,
        surface_nodal_covector=surface_nodal,
        volume_nodal_covector=volume_nodal,
        surface_acceleration=_divide_face_components(xp, surface_force, weights),
        volume_reaction_acceleration=_divide_face_components(xp, volume_force, weights),
        surface_force_covector=surface_force,
        volume_reaction_force_covector=volume_force,
        face_weight_components=weights,
        phase_threshold=float(phase_threshold),
        sigma=float(sigma),
    )


def transport_increment_from_face_velocity(
    *,
    xp,
    fccd,
    psi,
    face_velocity_components,
) -> Any:
    """Return ``T(u)=-D_f(psi_f u_f)`` for face velocity components."""
    delta = None
    psi_arr = xp.asarray(psi)
    for axis, velocity in enumerate(face_velocity_components):
        transported_flux = fccd.face_value(psi_arr, axis) * xp.asarray(velocity)
        axis_delta = -fccd.face_divergence(transported_flux, axis)
        delta = axis_delta if delta is None else delta + axis_delta
    return delta


def fixed_stratum_virtual_work_check(
    *,
    xp,
    grid,
    fccd,
    cochain: ClosedInterfaceRieszCochain,
    face_velocity_components,
    epsilon: float = 1.0e-7,
    threshold_tol: float = 0.0,
) -> VirtualWorkCheck:
    """Check ``dE[T(u)] + <s,u>_M = 0`` on the current stratum."""
    delta = transport_increment_from_face_velocity(
        xp=xp,
        fccd=fccd,
        psi=cochain.psi,
        face_velocity_components=face_velocity_components,
    )
    plus = cochain.psi + float(epsilon) * delta
    minus = cochain.psi - float(epsilon) * delta
    if not cochain.stratum.matches(
        xp=xp,
        grid=grid,
        psi=plus,
        threshold_tol=float(threshold_tol),
    ):
        return _invalid_virtual_work_check("plus_stratum_changed")
    if not cochain.stratum.matches(
        xp=xp,
        grid=grid,
        psi=minus,
        threshold_tol=float(threshold_tol),
    ):
        return _invalid_virtual_work_check("minus_stratum_changed")

    value_plus = trace_surface_length_2d(
        xp=xp,
        grid=grid,
        psi=plus,
        sigma=cochain.sigma,
        phase_threshold=cochain.phase_threshold,
    )
    value_minus = trace_surface_length_2d(
        xp=xp,
        grid=grid,
        psi=minus,
        sigma=cochain.sigma,
        phase_threshold=cochain.phase_threshold,
    )
    finite_difference = _to_float(
        xp,
        (value_plus - value_minus) / (2.0 * float(epsilon)),
    )
    gradient_action = _to_float(
        xp,
        xp.sum(xp.asarray(cochain.surface_nodal_covector) * delta),
    )
    capillary_power = face_weighted_dot(
        xp=xp,
        left_components=cochain.surface_acceleration,
        right_components=face_velocity_components,
        face_weight_components=cochain.face_weight_components,
    )
    fd_grad_residual = _relative_residual(finite_difference, gradient_action)
    fd_power_residual = _relative_residual(finite_difference, -capillary_power)
    riesz_residual = _relative_residual(gradient_action, -capillary_power)
    return VirtualWorkCheck(
        True,
        float(finite_difference),
        float(gradient_action),
        float(capillary_power),
        float(fd_grad_residual),
        float(fd_power_residual),
        float(riesz_residual),
        "ok",
    )


def weighted_hodge_decomposition(
    *,
    xp,
    div_op,
    face_components,
    face_weight_components,
    rcond: float = 1.0e-12,
) -> WeightedHodgeDecomposition:
    """Project a face cochain with the exact dense ``D_f`` diagnostic matrix."""
    D, shapes, sizes = _dense_divergence_matrix(
        xp=xp,
        div_op=div_op,
        face_templates=face_components,
    )
    component_flat = _flatten_face_components(face_components)
    weight_flat = _flatten_face_components(face_weight_components)
    if np.any(weight_flat <= 0.0):
        raise ValueError("weighted Hodge decomposition requires positive face weights")
    inv_weight = 1.0 / weight_flat
    normal_matrix = D @ (inv_weight[:, None] * D.T)
    source = D @ component_flat
    potential = np.linalg.lstsq(normal_matrix, source, rcond=float(rcond))[0]
    range_flat = inv_weight * (D.T @ potential)
    hodge_flat = component_flat - range_flat
    range_components = _unflatten_face_components(xp, range_flat, shapes, sizes)
    hodge_components = _unflatten_face_components(xp, hodge_flat, shapes, sizes)
    return WeightedHodgeDecomposition(
        range_components=range_components,
        hodge_components=hodge_components,
        component_weighted_l2=_weighted_norm_from_flat(component_flat, weight_flat),
        range_weighted_l2=_weighted_norm_from_flat(range_flat, weight_flat),
        hodge_weighted_l2=_weighted_norm_from_flat(hodge_flat, weight_flat),
        hodge_divergence_linf=float(np.max(np.abs(D @ hodge_flat))),
    )


def component_reaction_hodge_gate(
    *,
    xp,
    div_op,
    cochain: ClosedInterfaceRieszCochain,
    rcond: float = 1.0e-12,
) -> ComponentReactionHodgeGate:
    """Remove the best area-reaction Hodge direction from surface capillarity."""
    surface = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=cochain.surface_acceleration,
        face_weight_components=cochain.face_weight_components,
        rcond=float(rcond),
    )
    volume = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=cochain.volume_reaction_acceleration,
        face_weight_components=cochain.face_weight_components,
        rcond=float(rcond),
    )
    denominator = face_weighted_dot(
        xp=xp,
        left_components=volume.hodge_components,
        right_components=volume.hodge_components,
        face_weight_components=cochain.face_weight_components,
    )
    numerator = face_weighted_dot(
        xp=xp,
        left_components=surface.hodge_components,
        right_components=volume.hodge_components,
        face_weight_components=cochain.face_weight_components,
    )
    beta = numerator / denominator if denominator > 0.0 else 0.0
    residual = [
        surface_component - beta * volume_component
        for surface_component, volume_component in zip(
            surface.hodge_components,
            volume.hodge_components,
            strict=True,
        )
    ]
    residual_norm = face_weighted_norm(
        xp=xp,
        face_components=residual,
        face_weight_components=cochain.face_weight_components,
    )
    residual_ratio = residual_norm / max(surface.hodge_weighted_l2, 1.0e-30)
    D, _, _ = _dense_divergence_matrix(
        xp=xp,
        div_op=div_op,
        face_templates=residual,
    )
    residual_div = float(np.max(np.abs(D @ _flatten_face_components(residual))))
    return ComponentReactionHodgeGate(
        surface_hodge_weighted_l2=surface.hodge_weighted_l2,
        volume_hodge_weighted_l2=volume.hodge_weighted_l2,
        beta=float(beta),
        residual_components=residual,
        residual_weighted_l2=float(residual_norm),
        residual_ratio=float(residual_ratio),
        residual_divergence_linf=residual_div,
    )


def face_weighted_dot(
    *,
    xp,
    left_components,
    right_components,
    face_weight_components,
) -> float:
    """Return ``sum_f M_f left_f right_f`` as a host float."""
    terms = []
    for left, right, weight in zip(
        left_components,
        right_components,
        face_weight_components,
        strict=True,
    ):
        terms.append(xp.sum(xp.asarray(left) * xp.asarray(right) * xp.asarray(weight)))
    if not terms:
        return 0.0
    return _to_float(xp, xp.sum(xp.stack(terms)))


def face_weighted_norm(*, xp, face_components, face_weight_components) -> float:
    """Return the ``M_f`` weighted norm of face components."""
    squared = face_weighted_dot(
        xp=xp,
        left_components=face_components,
        right_components=face_components,
        face_weight_components=face_weight_components,
    )
    return float(np.sqrt(max(squared, 0.0)))


def _negative_transport_adjoint_force_covector(*, xp, fccd, psi, nodal_covector):
    force = []
    for axis in range(fccd.grid.ndim):
        adjoint = _negative_face_divergence_adjoint(
            xp=xp,
            fccd=fccd,
            nodal_covector=nodal_covector,
            axis=axis,
        )
        force.append(-fccd.face_value(psi, axis) * adjoint)
    return force


def _divide_face_components(xp, numerator_components, denominator_components):
    return [
        xp.asarray(numerator) / xp.asarray(denominator)
        for numerator, denominator in zip(
            numerator_components,
            denominator_components,
            strict=True,
        )
    ]


def _dense_divergence_matrix(*, xp, div_op, face_templates):
    templates = [xp.asarray(component) for component in face_templates]
    shapes = [tuple(component.shape) for component in templates]
    sizes = [int(np.prod(shape)) for shape in shapes]
    total_size = sum(sizes)
    zero_faces = [xp.zeros_like(component) for component in templates]
    sample = div_op.divergence_from_faces(zero_faces)
    row_count = int(np.prod(sample.shape))
    matrix = np.zeros((row_count, total_size), dtype=float)
    offset = 0
    for axis, (shape, size) in enumerate(zip(shapes, sizes, strict=True)):
        for local_index in range(size):
            faces = [xp.zeros_like(component) for component in templates]
            face_host = np.zeros(shape, dtype=float)
            face_host.flat[local_index] = 1.0
            faces[axis] = xp.asarray(face_host, dtype=templates[axis].dtype)
            matrix[:, offset + local_index] = array_to_numpy(
                xp,
                div_op.divergence_from_faces(faces),
            ).ravel()
        offset += size
    return matrix, shapes, sizes


def _flatten_face_components(face_components) -> np.ndarray:
    return np.concatenate(
        [np.asarray(component, dtype=float).ravel() for component in face_components]
    )


def _unflatten_face_components(xp, flat, shapes, sizes):
    components = []
    offset = 0
    for shape, size in zip(shapes, sizes, strict=True):
        components.append(xp.asarray(flat[offset : offset + size].reshape(shape)))
        offset += size
    return components


def _weighted_norm_from_flat(component_flat, weight_flat) -> float:
    return float(np.sqrt(np.sum(component_flat * component_flat * weight_flat)))


def _axis_slice(axis: int, start: int, stop: int, ndim: int):
    slices = [slice(None)] * ndim
    slices[axis] = slice(start, stop)
    return tuple(slices)


def _invalid_virtual_work_check(reason: str) -> VirtualWorkCheck:
    return VirtualWorkCheck(False, 0.0, 0.0, 0.0, np.inf, np.inf, np.inf, reason)


def _relative_residual(left: float, right: float) -> float:
    denominator = abs(left) + abs(right) + 1.0e-30
    return abs(left - right) / denominator


def _to_float(xp, value) -> float:
    return float(np.asarray(array_to_numpy(xp, value)))
