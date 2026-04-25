"""Predictor-assembly callbacks for pressure-robust buoyancy handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List


@dataclass(frozen=True)
class PredictorAssemblySelection:
    """Normalized predictor-assembly selection."""

    predictor_state_assembly: Callable[..., List] | None = None
    cn_intermediate_state_repair_mode: str | None = None


def predictor_extra_rhs(
    explicit_rhs: list,
    convective_rhs: list | None,
    buoyancy_rhs: list | None,
) -> list:
    """Return explicit RHS after removing the buoyancy part."""
    if convective_rhs is not None and buoyancy_rhs is not None:
        return convective_rhs
    if buoyancy_rhs is None:
        return explicit_rhs
    return [
        explicit_rhs[component_index] - buoyancy_rhs[component_index]
        for component_index in range(len(explicit_rhs))
    ]


def select_gravity_aligned_axis(
    force_components: list | None,
    xp,
    preferred_axis: int | None = None,
) -> int | None:
    """Return the component axis carrying the largest buoyancy magnitude."""
    if not force_components:
        return None
    if preferred_axis is not None and 0 <= preferred_axis < len(force_components):
        return preferred_axis
    magnitudes = []
    for component in force_components:
        if component is None:
            magnitudes.append(0.0)
            continue
        component_array = xp.asarray(component)
        if component_array.size == 0:
            magnitudes.append(0.0)
            continue
        magnitudes.append(float(xp.max(xp.abs(component_array))))
    if not magnitudes:
        return None
    axis = max(range(len(magnitudes)), key=lambda index: magnitudes[index])
    return axis if magnitudes[axis] > 0.0 else None


def select_transverse_axis(
    force_components: list | None,
    xp,
    preferred_axis: int | None = None,
) -> int | None:
    """Return an axis transverse to the gravity-aligned force component."""
    gravity_axis = select_gravity_aligned_axis(
        force_components,
        xp,
        preferred_axis=preferred_axis,
    )
    if gravity_axis is None:
        return None
    for axis in range(len(force_components)):
        if axis != gravity_axis:
            return axis
    return None


def make_buoyancy_force_split_predictor_state_assembly(
    *,
    interface_state_transform: Callable[[list], None],
    residual_force_builder: Callable[[list, object, object], list],
) -> Callable[..., List]:
    """Build a predictor from the non-hydrostatic buoyancy residual.

    A3 mapping:
      Equation: ``rho' g = -grad(rho' Phi_g) + Phi_g grad(rho')``.
      Discretization: advance only ``f_h^res`` in the explicit predictor
      substate and keep the hydrostatic gradient in pressure space.
      Code: ``residual_force_builder`` produces ``f_h^res``; the face-space
      transform stores the result in projection-native variables.
    """

    def _assembly(
        *,
        u_old: list,
        explicit_rhs: list,
        convective_rhs: list | None,
        buoyancy_rhs: list | None,
        visc_n: list,
        rho,
        dt: float,
        xp,
    ) -> list:
        if buoyancy_rhs is None:
            return [
                u_old[component_index]
                + dt * (explicit_rhs[component_index] / rho + visc_n[component_index])
                for component_index in range(len(u_old))
            ]
        residual_force = residual_force_builder(buoyancy_rhs, rho, xp)
        buoyancy_predictor = [
            u_old[component_index] + dt * (residual_force[component_index] / rho)
            for component_index in range(len(u_old))
        ]
        interface_state_transform(buoyancy_predictor)
        extra_rhs = predictor_extra_rhs(explicit_rhs, convective_rhs, buoyancy_rhs)
        return [
            buoyancy_predictor[component_index]
            + dt * (extra_rhs[component_index] / rho + visc_n[component_index])
            for component_index in range(len(u_old))
        ]

    return _assembly


def select_buoyancy_predictor_state_assembly(
    *,
    mode: str,
    fullband_state_transform: Callable[[list], None] | None = None,
    residual_buoyancy_force_builder: Callable[[list, object, object], list] | None = None,
) -> PredictorAssemblySelection:
    """Select the supported buoyancy predictor assembly."""
    normalized = str(mode or "none").strip().lower()
    if normalized in {"", "none"}:
        return PredictorAssemblySelection()
    if normalized in {
        "balanced_buoyancy",
        "buoyancy_faceresidual_stagesplit_transversefullband",
    }:
        if fullband_state_transform is None or residual_buoyancy_force_builder is None:
            return PredictorAssemblySelection()
        return PredictorAssemblySelection(
            predictor_state_assembly=make_buoyancy_force_split_predictor_state_assembly(
                interface_state_transform=fullband_state_transform,
                residual_force_builder=residual_buoyancy_force_builder,
            ),
            cn_intermediate_state_repair_mode="transverse_fullband_local",
        )
    raise ValueError(f"Unsupported predictor_assembly={mode!r}")
