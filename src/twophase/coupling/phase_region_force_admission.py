"""Contract helpers for PhaseRegion force admission candidates.

Symbol mapping
--------------
``psi`` -> runtime phase chart/gauge evaluated on grid nodes.
``rho`` -> nodal two-phase density ``rho_g + (rho_l-rho_g) psi``.
``M_f`` -> face mass metric built from nodal density.
``T`` -> fixed-stratum transport map ``-D_f(psi_f u_f)``.

This module is a contract helper only.  It does not connect capillary force to
pressure projection, advance velocity, solve nonlinear admission, micro-step,
or run a T/8 path.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from twophase.geometry import AtlasValidationError
from twophase.geometry import CellMeasurePhase
from twophase.geometry import map_cell_measure_to_phase_owner

from .closed_interface_riesz import closed_interface_riesz_cochain
from .closed_interface_riesz import face_mass_components
from .closed_interface_riesz import transport_increment_from_face_velocity
from .closed_interface_stratum import array_to_numpy


@dataclass(frozen=True)
class PhaseRegionFaceMassMetric:
    """Nodal density and face weights for a PhaseRegion force candidate."""

    rho_node: object
    face_weight_components: list[object]
    rho_min: float
    rho_max: float


@dataclass(frozen=True)
class FixedStratumVelocityScale:
    """Scaled face velocity that keeps a finite-difference probe local."""

    face_velocity_components: list[object]
    scale: float
    sign_margin: float
    delta_linf: float
    valid: bool
    reason: str


@dataclass(frozen=True)
class PhaseRegionForceAdmission:
    """Zero-step PhaseRegion force candidate with explicit admission status."""

    valid: bool
    reason: str
    force_admissible: bool
    runtime_steps: int
    owner_map: object | None
    face_metric: PhaseRegionFaceMassMetric | None
    cochain: object | None
    metrics: dict[str, float]


def two_phase_nodal_density(
    *,
    xp,
    psi,
    rho_l: float,
    rho_g: float,
    indicator_tolerance: float = 1.0e-12,
):
    """Return nodal two-phase density from a runtime phase indicator."""
    psi_arr = xp.asarray(psi, dtype=float)
    if psi_arr.ndim != 2:
        raise ValueError("psi must be a 2D nodal array")
    psi_host = array_to_numpy(xp, psi_arr)
    if not np.all(np.isfinite(psi_host)):
        raise ValueError("psi must be finite")
    tol = float(indicator_tolerance)
    if not np.isfinite(tol) or tol < 0.0:
        raise ValueError("indicator_tolerance must be finite and nonnegative")
    if float(np.min(psi_host)) < -tol or float(np.max(psi_host)) > 1.0 + tol:
        raise ValueError("psi must stay within [0, 1] up to indicator_tolerance")
    rho_l_value = float(rho_l)
    rho_g_value = float(rho_g)
    if not np.isfinite(rho_l_value) or not np.isfinite(rho_g_value):
        raise ValueError("rho_l and rho_g must be finite")
    if rho_l_value <= 0.0 or rho_g_value <= 0.0:
        raise ValueError("rho_l and rho_g must be positive")
    return rho_g_value + (rho_l_value - rho_g_value) * psi_arr


def build_phase_region_force_admission_candidate(
    *,
    xp,
    grid,
    fccd,
    psi,
    q_source,
    cell_area,
    source_phase: CellMeasurePhase | int | str,
    owner_phase: CellMeasurePhase | int | str,
    rho_l: float,
    rho_g: float,
    sigma: float,
    capacity_tolerance: float = 1.0e-12,
    runtime_steps: int = 0,
    phase_threshold: float = 0.5,
) -> PhaseRegionForceAdmission:
    """Build a zero-step force candidate without admitting it to runtime use."""
    steps = int(runtime_steps)
    if steps != 0:
        return _invalid_admission("runtime_steps_must_be_zero", steps)
    try:
        owner_map = map_cell_measure_to_phase_owner(
            q_source,
            cell_area,
            source_phase=source_phase,
            owner_phase=owner_phase,
            capacity_tolerance=float(capacity_tolerance),
        )
        face_metric = phase_region_face_mass_metric(
            xp=xp,
            grid=grid,
            psi=psi,
            rho_l=float(rho_l),
            rho_g=float(rho_g),
        )
        cochain = closed_interface_riesz_cochain(
            xp=xp,
            grid=grid,
            psi=psi,
            fccd=fccd,
            sigma=float(sigma),
            face_weight_components=face_metric.face_weight_components,
            phase_threshold=float(phase_threshold),
        )
    except (AtlasValidationError, ValueError, np.linalg.LinAlgError) as exc:
        return _invalid_admission(str(exc), steps)
    metrics = _candidate_metrics(
        xp=xp,
        runtime_steps=steps,
        owner_map=owner_map,
        face_metric=face_metric,
        cochain=cochain,
    )
    return PhaseRegionForceAdmission(
        valid=True,
        reason="ok",
        force_admissible=False,
        runtime_steps=steps,
        owner_map=owner_map,
        face_metric=face_metric,
        cochain=cochain,
        metrics=metrics,
    )


def phase_region_face_mass_metric(
    *,
    xp,
    grid,
    psi,
    rho_l: float,
    rho_g: float,
    indicator_tolerance: float = 1.0e-12,
) -> PhaseRegionFaceMassMetric:
    """Build ``M_f`` from runtime nodal ``psi`` without accepting cell density."""
    psi_arr = xp.asarray(psi, dtype=float)
    if tuple(psi_arr.shape) != tuple(grid.shape):
        raise ValueError(
            "psi must have nodal grid shape; cell-density input is not allowed"
        )
    rho_node = two_phase_nodal_density(
        xp=xp,
        psi=psi_arr,
        rho_l=float(rho_l),
        rho_g=float(rho_g),
        indicator_tolerance=float(indicator_tolerance),
    )
    weights = face_mass_components(xp=xp, grid=grid, rho=rho_node)
    rho_host = array_to_numpy(xp, rho_node)
    return PhaseRegionFaceMassMetric(
        rho_node=rho_node,
        face_weight_components=weights,
        rho_min=float(np.min(rho_host)),
        rho_max=float(np.max(rho_host)),
    )


def scale_face_velocity_to_fixed_stratum(
    *,
    xp,
    fccd,
    psi,
    face_velocity_components,
    fd_eps: float,
    sign_fraction: float = 2.0e-2,
    phase_threshold: float = 0.5,
) -> FixedStratumVelocityScale:
    """Scale a virtual face velocity so ``psi +/- eps*T(u)`` remains local."""
    eps = float(fd_eps)
    fraction = float(sign_fraction)
    threshold = float(phase_threshold)
    if not np.isfinite(eps) or eps <= 0.0:
        raise ValueError("fd_eps must be finite and positive")
    if not np.isfinite(fraction) or fraction <= 0.0 or fraction > 1.0:
        raise ValueError("sign_fraction must be in (0, 1]")
    if not np.isfinite(threshold):
        raise ValueError("phase_threshold must be finite")

    psi_arr = xp.asarray(psi, dtype=float)
    psi_host = array_to_numpy(xp, psi_arr)
    sign_margin = float(np.min(np.abs(psi_host - threshold)))
    if sign_margin <= 0.0:
        return FixedStratumVelocityScale(
            face_velocity_components=[
                xp.asarray(component) for component in face_velocity_components
            ],
            scale=0.0,
            sign_margin=sign_margin,
            delta_linf=0.0,
            valid=False,
            reason="zero_sign_margin",
        )

    delta = transport_increment_from_face_velocity(
        xp=xp,
        fccd=fccd,
        psi=psi_arr,
        face_velocity_components=face_velocity_components,
    )
    delta_linf = float(np.max(np.abs(array_to_numpy(xp, delta))))
    if delta_linf <= 0.0:
        return FixedStratumVelocityScale(
            face_velocity_components=[
                xp.asarray(component) for component in face_velocity_components
            ],
            scale=1.0,
            sign_margin=sign_margin,
            delta_linf=0.0,
            valid=True,
            reason="zero_transport_increment",
        )
    scale = min(1.0, fraction * sign_margin / (eps * delta_linf))
    return FixedStratumVelocityScale(
        face_velocity_components=[
            float(scale) * xp.asarray(component) for component in face_velocity_components
        ],
        scale=float(scale),
        sign_margin=sign_margin,
        delta_linf=delta_linf,
        valid=True,
        reason="ok",
    )


def _invalid_admission(reason: str, runtime_steps: int) -> PhaseRegionForceAdmission:
    return PhaseRegionForceAdmission(
        valid=False,
        reason=str(reason),
        force_admissible=False,
        runtime_steps=int(runtime_steps),
        owner_map=None,
        face_metric=None,
        cochain=None,
        metrics={
            "runtime_steps": float(runtime_steps),
            "force_admissible": 0.0,
            "valid": 0.0,
        },
    )


def _candidate_metrics(
    *,
    xp,
    runtime_steps: int,
    owner_map,
    face_metric: PhaseRegionFaceMassMetric,
    cochain,
) -> dict[str, float]:
    weights = [
        array_to_numpy(xp, component)
        for component in face_metric.face_weight_components
    ]
    weight_min = min(float(np.min(component)) for component in weights)
    weight_max = max(float(np.max(component)) for component in weights)
    return {
        "runtime_steps": float(runtime_steps),
        "force_admissible": 0.0,
        "valid": 1.0,
        "complement_used": float(owner_map.complement_used),
        "source_volume": float(owner_map.source_volume),
        "owner_volume": float(owner_map.owner_volume),
        "rho_min": float(face_metric.rho_min),
        "rho_max": float(face_metric.rho_max),
        "face_weight_min": weight_min,
        "face_weight_max": weight_max,
        "phase_threshold": float(cochain.phase_threshold),
        "sigma": float(cochain.sigma),
    }
