"""Simulation adapters for SP-AO geometric phase transport.

Symbol mapping:
    ``q_C`` -> physical cell-volume carrier in ``GeometricPhaseState``.
    ``rho_C(q)`` -> affine q-derived cell density.
    ``Phi_V`` -> face total-volume flux.
    ``Phi_m`` -> common mass flux ``rho_g Phi_V + (rho_l-rho_g) Phi_l``.

This module is the runtime boundary between geometry-owned AO state and the
Navier--Stokes pipeline.  It validates typed q/common-flux data without
reinterpreting legacy nodal ``psi`` as material volume.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..backend import is_device_array
from ..geometry import (
    GeometricCommonFluxTransportResult,
    GeometricFaceMassHodge,
    GeometricPhaseState,
    GeometricPressureCapillaryHodge,
    geometric_face_mass_hodge_2d,
    geometric_pressure_capillary_hodge_2d,
)


@dataclass(frozen=True)
class GeometricRuntimeCommonFluxState:
    """Material snapshot derived from one compatible AO q/common-flux result."""

    phase_state: GeometricPhaseState
    density: Any
    volume_fluxes: tuple[Any, Any]
    mass_fluxes: tuple[Any, Any]
    face_hodge: GeometricFaceMassHodge
    min_density: Any
    max_density: Any
    mass_flux_formula_residual_linf: float


@dataclass(frozen=True)
class GeometricRuntimeCapillaryState:
    """Pressure/capillary Hodge snapshot for one AO material state."""

    material: GeometricRuntimeCommonFluxState
    pressure_capillary_hodge: GeometricPressureCapillaryHodge
    pressure_range_status: str
    pressure_exact_static: bool
    capillary_drive_present: bool
    pressure_range_tolerance: float
    capillary_force_face_covectors: tuple[Any, Any]
    capillary_force_acceleration: tuple[Any, Any]
    pressure_reaction_face_covectors: tuple[Any, Any]
    pressure_reaction_acceleration: tuple[Any, Any]
    capillary_force_weighted_acceleration_l2: float
    pressure_reaction_weighted_acceleration_l2: float
    max_abs_capillary_force_face_covector: float
    max_abs_pressure_reaction_face_covector: float
    surface_energy_nodal_covector: Any
    pressure_reaction_nodal_covector: Any
    young_laplace_residual_nodal_covector: Any
    young_laplace_residual_linf: float
    young_laplace_residual_l2: float
    young_laplace_normal_residual_linf: float
    weighted_residual_acceleration_l2: float
    max_abs_residual_face_covector: float


@dataclass(frozen=True)
class GeometricRuntimeCapillaryApplicationState:
    """Face-native AO capillary predictor/reaction increments for one step."""

    capillary: GeometricRuntimeCapillaryState
    dt: float
    predictor_face_acceleration: tuple[Any, Any]
    pressure_reaction_face_acceleration: tuple[Any, Any]
    predictor_face_increment: tuple[Any, Any]
    pressure_reaction_face_increment: tuple[Any, Any]
    pressure_balanced_face_increment: tuple[Any, Any]
    predictor_increment_weighted_l2: float
    pressure_reaction_increment_weighted_l2: float
    pressure_balanced_increment_weighted_l2: float
    max_abs_pressure_balanced_face_increment: float
    pressure_exact_static: bool
    capillary_drive_present: bool


def materialise_geometric_common_flux_state(
    grid,
    result: GeometricCommonFluxTransportResult,
    *,
    rho_l: float,
    rho_g: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
) -> GeometricRuntimeCommonFluxState:
    """Validate and expose q-derived density plus AO common mass fluxes."""
    if getattr(grid.xp, "__name__", "").split(".", 1)[0] == "cupy":
        raise ValueError(
            "geometric runtime GPU execution requires active fused AO-Fast "
            "kernels; dense exact AO materialisation is CPU-only"
        )
    if not isinstance(result, GeometricCommonFluxTransportResult):
        raise TypeError("result must be a GeometricCommonFluxTransportResult")
    tolerance = _validate_tolerance(tolerance)
    rho_l, rho_g = _validate_phase_densities(rho_l, rho_g)
    xp = grid.xp
    phase_state = result.phase_transport.state
    if not phase_state.is_compatible(tolerance=tolerance):
        raise ValueError(
            "geometric runtime material state requires compatible q/phi; "
            "use every-step compatibility projection before downstream coupling"
        )

    density = xp.asarray(phase_state.density_view(rho_l=rho_l, rho_g=rho_g))
    _validate_shape(density, tuple(grid.N), "geometric density")
    _validate_finite(xp, density, "geometric density")
    min_density = xp.min(density)
    max_density = xp.max(density)
    if _scalar_bool(min_density <= 0.0):
        raise ValueError("geometric density must be positive")
    volume_fluxes = _validate_face_pair(
        grid,
        result.volume_fluxes,
        name="volume flux",
    )
    mass_fluxes = _validate_face_pair(
        grid,
        result.mass_fluxes,
        name="mass flux",
    )
    phase_fluxes = _validate_face_pair(
        grid,
        result.phase_transport.swept_flux.phase_fluxes,
        name="phase flux",
    )
    residual = _mass_flux_formula_residual(
        xp,
        phase_fluxes,
        volume_fluxes,
        mass_fluxes,
        rho_l=rho_l,
        rho_g=rho_g,
    )
    scale = _mass_flux_scale(
        xp,
        phase_fluxes,
        volume_fluxes,
        mass_fluxes,
        rho_l,
        rho_g,
    )
    if _scalar_bool(residual > tolerance * scale):
        raise ValueError("geometric common mass flux violates Phi_m formula")
    face_hodge = geometric_face_mass_hodge_2d(
        grid,
        phase_state,
        rho_l=rho_l,
        rho_g=rho_g,
        boundary=boundary,
        tolerance=tolerance,
    )
    return GeometricRuntimeCommonFluxState(
        phase_state=phase_state,
        density=density,
        volume_fluxes=volume_fluxes,
        mass_fluxes=mass_fluxes,
        face_hodge=face_hodge,
        min_density=min_density,
        max_density=max_density,
        mass_flux_formula_residual_linf=_scalar_float(residual),
    )


def materialise_geometric_runtime_capillary_state(
    grid,
    material: GeometricRuntimeCommonFluxState,
    *,
    sigma: float,
    tolerance: float = 1.0e-11,
    max_cg_iterations: int | None = None,
) -> GeometricRuntimeCapillaryState:
    """Validate pressure/capillary Hodge diagnostics for an AO material state."""
    if getattr(grid.xp, "__name__", "").split(".", 1)[0] == "cupy":
        raise ValueError(
            "geometric runtime GPU execution requires active fused AO-Fast "
            "kernels; dense exact AO capillary materialisation is CPU-only"
        )
    if not isinstance(material, GeometricRuntimeCommonFluxState):
        raise TypeError("material must be a GeometricRuntimeCommonFluxState")
    tolerance = _validate_tolerance(tolerance)
    hodge = geometric_pressure_capillary_hodge_2d(
        grid,
        material.phase_state,
        sigma=sigma,
        rho_l=material.face_hodge.rho_l,
        rho_g=material.face_hodge.rho_g,
        boundary=material.face_hodge.boundary,
        tolerance=tolerance,
        max_cg_iterations=max_cg_iterations,
    )
    _validate_matching_face_hodge(grid.xp, material, hodge)
    pressure_range_status, pressure_exact_static, capillary_drive_present = (
        _classify_capillary_pressure_range(hodge, tolerance=tolerance)
    )
    capillary_force_face_covectors = _validate_face_pair(
        grid,
        hodge.capillary_riesz.face_covectors,
        name="runtime capillary force face covector",
    )
    capillary_force_acceleration = _validate_face_pair(
        grid,
        hodge.capillary_riesz.acceleration,
        name="runtime capillary force acceleration",
    )
    pressure_reaction_face_covectors = _validate_face_pair(
        grid,
        hodge.pressure_face_covectors,
        name="runtime pressure reaction face covector",
    )
    pressure_reaction_acceleration = _validate_face_pair(
        grid,
        hodge.pressure_acceleration,
        name="runtime pressure reaction acceleration",
    )
    surface_energy_nodal_covector = _validate_node_field(
        grid,
        hodge.young_laplace_residual.surface_covector.energy_nodal_covector,
        name="runtime surface-energy nodal covector",
    )
    pressure_reaction_nodal_covector = _validate_node_field(
        grid,
        hodge.young_laplace_residual.pressure_nodal_covector,
        name="runtime pressure-reaction nodal covector",
    )
    young_laplace_residual_nodal_covector = _validate_node_field(
        grid,
        hodge.young_laplace_residual.residual_nodal_covector,
        name="runtime Young-Laplace residual nodal covector",
    )
    return GeometricRuntimeCapillaryState(
        material=material,
        pressure_capillary_hodge=hodge,
        pressure_range_status=pressure_range_status,
        pressure_exact_static=pressure_exact_static,
        capillary_drive_present=capillary_drive_present,
        pressure_range_tolerance=tolerance,
        capillary_force_face_covectors=capillary_force_face_covectors,
        capillary_force_acceleration=capillary_force_acceleration,
        pressure_reaction_face_covectors=pressure_reaction_face_covectors,
        pressure_reaction_acceleration=pressure_reaction_acceleration,
        capillary_force_weighted_acceleration_l2=(
            hodge.capillary_riesz.weighted_acceleration_l2
        ),
        pressure_reaction_weighted_acceleration_l2=(
            hodge.weighted_pressure_acceleration_l2
        ),
        max_abs_capillary_force_face_covector=(
            hodge.capillary_riesz.max_abs_face_covector
        ),
        max_abs_pressure_reaction_face_covector=(
            hodge.max_abs_pressure_face_covector
        ),
        surface_energy_nodal_covector=surface_energy_nodal_covector,
        pressure_reaction_nodal_covector=pressure_reaction_nodal_covector,
        young_laplace_residual_nodal_covector=young_laplace_residual_nodal_covector,
        young_laplace_residual_linf=hodge.young_laplace_residual.residual_linf,
        young_laplace_residual_l2=hodge.young_laplace_residual.residual_l2,
        young_laplace_normal_residual_linf=(
            hodge.young_laplace_residual.normal_residual_linf
        ),
        weighted_residual_acceleration_l2=hodge.weighted_residual_acceleration_l2,
        max_abs_residual_face_covector=hodge.max_abs_residual_face_covector,
    )


def materialise_geometric_runtime_capillary_application_state(
    grid,
    capillary: GeometricRuntimeCapillaryState,
    *,
    dt: float,
) -> GeometricRuntimeCapillaryApplicationState:
    """Build the face-native capillary predictor/reaction increment pair."""
    if not isinstance(capillary, GeometricRuntimeCapillaryState):
        raise TypeError("capillary must be a GeometricRuntimeCapillaryState")
    dt = _validate_dt(dt)
    xp = grid.xp
    predictor_face_acceleration = _validate_face_pair(
        grid,
        capillary.capillary_force_acceleration,
        name="runtime AO capillary predictor acceleration",
    )
    pressure_reaction_face_acceleration = _validate_face_pair(
        grid,
        capillary.pressure_reaction_acceleration,
        name="runtime AO pressure reaction acceleration",
    )
    predictor_face_increment = _validate_face_pair(
        grid,
        _scale_face_pair(
            predictor_face_acceleration,
            dt=dt,
        ),
        name="runtime AO capillary predictor face increment",
    )
    pressure_reaction_face_increment = _validate_face_pair(
        grid,
        _scale_face_pair(
            pressure_reaction_face_acceleration,
            dt=dt,
        ),
        name="runtime AO pressure reaction face increment",
    )
    pressure_balanced_face_increment = _validate_face_pair(
        grid,
        _subtract_face_pairs(
            predictor_face_increment,
            pressure_reaction_face_increment,
        ),
        name="runtime AO pressure-balanced face increment",
    )
    weights = capillary.material.face_hodge.weights
    return GeometricRuntimeCapillaryApplicationState(
        capillary=capillary,
        dt=dt,
        predictor_face_acceleration=predictor_face_acceleration,
        pressure_reaction_face_acceleration=pressure_reaction_face_acceleration,
        predictor_face_increment=predictor_face_increment,
        pressure_reaction_face_increment=pressure_reaction_face_increment,
        pressure_balanced_face_increment=pressure_balanced_face_increment,
        predictor_increment_weighted_l2=_face_weighted_l2(
            xp,
            predictor_face_increment,
            weights,
            name="runtime AO capillary predictor increment weighted L2",
        ),
        pressure_reaction_increment_weighted_l2=_face_weighted_l2(
            xp,
            pressure_reaction_face_increment,
            weights,
            name="runtime AO pressure reaction increment weighted L2",
        ),
        pressure_balanced_increment_weighted_l2=_face_weighted_l2(
            xp,
            pressure_balanced_face_increment,
            weights,
            name="runtime AO pressure-balanced increment weighted L2",
        ),
        max_abs_pressure_balanced_face_increment=_max_abs_face_pair(
            xp,
            pressure_balanced_face_increment,
        ),
        pressure_exact_static=capillary.pressure_exact_static,
        capillary_drive_present=capillary.capillary_drive_present,
    )


def _classify_capillary_pressure_range(
    hodge: GeometricPressureCapillaryHodge,
    *,
    tolerance: float,
) -> tuple[str, bool, bool]:
    residual = hodge.young_laplace_residual
    if residual.normal_residual_linf > tolerance:
        raise ValueError(
            "runtime capillary pressure solve violates Young-Laplace normal "
            "equations"
        )
    if residual.residual_linf <= tolerance:
        return "pressure_exact_static", True, False
    return "nonzero_capillary_drive", False, True


def _validate_dt(dt: float) -> float:
    converted = float(dt)
    if not (math.isfinite(converted) and converted > 0.0):
        raise ValueError("dt must be finite and positive")
    return converted


def _validate_tolerance(tolerance: float) -> float:
    converted = float(tolerance)
    if not converted > 0.0:
        raise ValueError("tolerance must be positive")
    return converted


def _validate_phase_densities(rho_l: float, rho_g: float) -> tuple[float, float]:
    converted_l = float(rho_l)
    converted_g = float(rho_g)
    if not (math.isfinite(converted_l) and math.isfinite(converted_g)):
        raise ValueError("rho_l and rho_g must be finite and positive")
    if converted_l <= 0.0 or converted_g <= 0.0:
        raise ValueError("rho_l and rho_g must be finite and positive")
    return converted_l, converted_g


def _validate_shape(array, expected: tuple[int, ...], name: str) -> None:
    if tuple(array.shape) != expected:
        raise ValueError(f"{name} shape must be {expected}, got {tuple(array.shape)}")


def _validate_face_pair(grid, values, *, name: str):
    if len(values) != 2:
        raise ValueError(f"{name} must provide x and y face arrays")
    xp = grid.xp
    x_face = xp.asarray(values[0])
    y_face = xp.asarray(values[1])
    _validate_shape(x_face, (grid.N[0] + 1, grid.N[1]), f"x-face {name}")
    _validate_shape(y_face, (grid.N[0], grid.N[1] + 1), f"y-face {name}")
    _validate_finite(xp, x_face, f"x-face {name}")
    _validate_finite(xp, y_face, f"y-face {name}")
    return (x_face, y_face)


def _validate_node_field(grid, value, *, name: str):
    xp = grid.xp
    array = xp.asarray(value)
    _validate_shape(array, (grid.N[0] + 1, grid.N[1] + 1), name)
    _validate_finite(xp, array, name)
    return array


def _scale_face_pair(values, *, dt: float):
    return tuple(dt * component for component in values)


def _subtract_face_pairs(left, right):
    return tuple(
        left_component - right_component
        for left_component, right_component in zip(left, right, strict=True)
    )


def _face_weighted_l2(xp, values, weights, *, name: str) -> float:
    total = xp.asarray(0.0, dtype=values[0].dtype)
    with _errstate(xp, over="ignore", invalid="ignore"):
        for value, weight in zip(values, weights, strict=True):
            total = total + xp.sum(xp.asarray(weight) * xp.asarray(value) ** 2)
        norm = xp.sqrt(total)
    if _scalar_bool(~xp.isfinite(norm)):
        raise ValueError(f"{name} must be finite")
    return _scalar_float(norm)


def _max_abs_face_pair(xp, values) -> float:
    return max(
        _scalar_float(xp.max(xp.abs(values[0]))),
        _scalar_float(xp.max(xp.abs(values[1]))),
    )


def _errstate(xp, **kwargs):
    return getattr(xp, "errstate", np.errstate)(**kwargs)


def _validate_finite(xp, array, name: str) -> None:
    if _scalar_bool(xp.any(~xp.isfinite(array))):
        raise ValueError(f"{name} must be finite")


def _validate_matching_face_hodge(
    xp,
    material: GeometricRuntimeCommonFluxState,
    pressure_hodge: GeometricPressureCapillaryHodge,
) -> None:
    material_hodge = material.face_hodge
    capillary_hodge = pressure_hodge.capillary_riesz.face_hodge
    _validate_matching_phase_state(
        xp,
        material_hodge.state,
        material.phase_state,
        context="runtime material face Hodge",
    )
    _validate_matching_phase_state(
        xp,
        capillary_hodge.state,
        material.phase_state,
        context="runtime capillary Hodge",
    )
    if capillary_hodge.boundary != material_hodge.boundary:
        raise ValueError("runtime capillary Hodge boundary must match material Hodge")
    if capillary_hodge.rho_l != material_hodge.rho_l:
        raise ValueError("runtime capillary Hodge rho_l must match material Hodge")
    if capillary_hodge.rho_g != material_hodge.rho_g:
        raise ValueError("runtime capillary Hodge rho_g must match material Hodge")
    for axis, (left, right) in enumerate(
        zip(capillary_hodge.weights, material_hodge.weights, strict=True)
    ):
        mismatch = xp.max(xp.abs(xp.asarray(left) - xp.asarray(right)))
        if _scalar_bool(mismatch > 0.0):
            raise ValueError(
                f"axis-{axis} runtime capillary Hodge weights must match material Hodge"
            )


def _validate_matching_phase_state(
    xp,
    left: GeometricPhaseState,
    right: GeometricPhaseState,
    *,
    context: str,
) -> None:
    for name in ("q", "phi"):
        left_array = xp.asarray(getattr(left, name))
        right_array = xp.asarray(getattr(right, name))
        if tuple(left_array.shape) != tuple(right_array.shape):
            raise ValueError(f"{context} {name} shape must match material state")
        mismatch = xp.max(xp.abs(left_array - right_array))
        if _scalar_bool(mismatch > 0.0):
            raise ValueError(f"{context} {name} must match material state")


def _mass_flux_formula_residual(
    xp,
    phase_fluxes,
    volume_fluxes,
    mass_fluxes,
    *,
    rho_l: float,
    rho_g: float,
):
    drho = rho_l - rho_g
    residual = xp.asarray(0.0, dtype=mass_fluxes[0].dtype)
    for phase_flux, volume_flux, mass_flux in zip(
        phase_fluxes,
        volume_fluxes,
        mass_fluxes,
        strict=True,
    ):
        expected = rho_g * volume_flux + drho * phase_flux
        residual = xp.maximum(residual, xp.max(xp.abs(mass_flux - expected)))
    return residual


def _mass_flux_scale(
    xp,
    phase_fluxes,
    volume_fluxes,
    mass_fluxes,
    rho_l: float,
    rho_g: float,
):
    dtype = mass_fluxes[0].dtype
    scale = xp.asarray(max(abs(rho_l), abs(rho_g), 1.0), dtype=dtype)
    for values in (*phase_fluxes, *volume_fluxes, *mass_fluxes):
        scale = xp.maximum(scale, xp.max(xp.abs(values)))
    return scale


def _scalar_bool(value) -> bool:
    if is_device_array(value):
        raise ValueError(
            "geometric runtime scalar reduction would synchronize a CUDA "
            "value; active fused AO-Fast GPU kernels are required"
        )
    if hasattr(value, "item"):
        value = value.item()
    return bool(value)


def _scalar_float(value) -> float:
    if is_device_array(value):
        raise ValueError(
            "geometric runtime scalar reduction would synchronize a CUDA "
            "value; active fused AO-Fast GPU kernels are required"
        )
    if hasattr(value, "item"):
        value = value.item()
    return float(value)
