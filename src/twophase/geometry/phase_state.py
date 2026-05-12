"""Typed SP-AO geometric phase state.

Symbol mapping
--------------
``q_C`` -> :attr:`GeometricPhaseState.q`, physical liquid cell volume owner.
``phi`` -> :attr:`GeometricPhaseState.phi`, continuous nodal gauge.
``theta_C`` -> :attr:`GeometricPhaseState.theta`, normalized q-view.
``rho_C(q)`` -> :meth:`GeometricPhaseState.density_view`.
``Q_h(phi)`` -> :attr:`GeometricPhaseState.geometry.q`.

The state owns material volume through ``q``.  ``phi`` is only the compatible
geometry gauge, and the residual ``q-Q_h(phi)`` is recorded explicitly so later
runtime layers cannot silently mix the diffuse ``psi`` route with the geometric
``q`` route.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .cell_complex import MetricCellComplex
from .compatibility_projection import (
    CompatibilityProjectionLedger,
    project_cell_volume_compatibility_2d,
)
from .p1_cut_geometry import (
    P1CutGeometry,
    _case_field,
    _cell_corner_fields,
    cut_geometry_2d,
)
from .swept_flux import (
    P1SweptFluxResult,
    SweptFluxTransportResult,
    apply_certified_swept_flux_2d,
    common_mass_fluxes_2d,
    construct_p1_swept_flux_2d,
    face_volume_fluxes_2d,
)


@dataclass(frozen=True)
class GeometricPhaseStratum:
    """Fixed-stratum sign and marching-square case data for one gauge."""

    node_signs: object
    cell_cases: object
    sign_margin: float
    level: float


@dataclass(frozen=True)
class GeometricPhaseState:
    """SP-AO state bundle tying physical ``q`` to a compatible gauge ``phi``."""

    q: object
    phi: object
    theta: object
    geometry: P1CutGeometry
    stratum: GeometricPhaseStratum
    compatibility_residual_linf: float
    compatibility_residual_l2: float
    ledger: CompatibilityProjectionLedger | None = None

    @property
    def phase_kind(self) -> str:
        """Return the explicit state-space tag used by parser/runtime gates."""
        return "geometric_cell_fraction"

    @classmethod
    def from_phi(
        cls,
        grid,
        phi,
        *,
        level: float = 0.0,
    ) -> "GeometricPhaseState":
        """Build a compatible geometric state with ``q=Q_h(phi)``."""
        phi_dev = _validate_phi(grid, phi)
        geometry = cut_geometry_2d(grid, phi_dev, level=level)
        return _build_state(
            cls,
            grid=grid,
            q=geometry.q,
            phi=phi_dev,
            geometry=geometry,
            level=level,
            tolerance=0.0,
            require_compatible=False,
            ledger=None,
        )

    @classmethod
    def from_q_phi(
        cls,
        grid,
        q,
        phi,
        *,
        level: float = 0.0,
        tolerance: float = 1.0e-11,
        require_compatible: bool = True,
        ledger: CompatibilityProjectionLedger | None = None,
    ) -> "GeometricPhaseState":
        """Build a state from explicit ``q`` and ``phi``.

        Set ``require_compatible=False`` for the pre-projection state produced
        by a future geometric transport step.  The returned object still keeps
        density and theta views tied to ``q``, not to ``Q_h(phi)``.
        """
        _validate_tolerance(tolerance)
        phi_dev = _validate_phi(grid, phi)
        complex_h = MetricCellComplex.from_grid(grid)
        q_dev = grid.xp.asarray(q, dtype=phi_dev.dtype)
        if tuple(q_dev.shape) != complex_h.shape:
            raise ValueError("q shape must match the grid cell shape")
        _validate_q_bounds(grid.xp, q_dev, complex_h.cell_measures, tolerance)
        geometry = cut_geometry_2d(grid, phi_dev, level=level)
        return _build_state(
            cls,
            grid=grid,
            q=q_dev,
            phi=phi_dev,
            geometry=geometry,
            level=level,
            tolerance=tolerance,
            require_compatible=require_compatible,
            ledger=ledger,
        )

    def density_view(self, *, rho_l: float, rho_g: float):
        """Return ``rho_C(q)=rho_g+(rho_l-rho_g)theta_C``."""
        rho_l = float(rho_l)
        rho_g = float(rho_g)
        if not (math.isfinite(rho_l) and math.isfinite(rho_g)):
            raise ValueError("rho_l and rho_g must be finite")
        density = rho_g + (rho_l - rho_g) * self.theta
        xp = _array_namespace(density)
        if _scalar_bool(xp, xp.any(~xp.isfinite(density))):
            raise ValueError("density view must be finite")
        return density

    def is_compatible(self, *, tolerance: float = 1.0e-11) -> bool:
        """Return whether the recorded residual satisfies the q-unit tolerance."""
        _validate_tolerance(tolerance)
        return self.compatibility_residual_linf <= tolerance

    def project_compatibility(
        self,
        grid,
        *,
        tolerance: float = 1.0e-11,
        max_newton_iterations: int = 8,
        max_cg_iterations: int | None = None,
        sign_safety: float = 0.95,
        min_step_fraction: float = 1.0e-8,
    ) -> "GeometricPhaseState":
        """Return a state with ``phi`` projected so ``Q_h(phi)=q``."""
        projection = project_cell_volume_compatibility_2d(
            grid,
            self.phi,
            self.q,
            level=self.stratum.level,
            tolerance=tolerance,
            max_newton_iterations=max_newton_iterations,
            max_cg_iterations=max_cg_iterations,
            sign_safety=sign_safety,
            min_step_fraction=min_step_fraction,
        )
        return type(self).from_q_phi(
            grid,
            self.q,
            projection.phi,
            level=self.stratum.level,
            tolerance=tolerance,
            require_compatible=True,
            ledger=projection.ledger,
        )


@dataclass(frozen=True)
class GeometricPhaseTransportResult:
    """One geometric transport step with optional compatibility projection."""

    state: GeometricPhaseState
    pre_projection_state: GeometricPhaseState
    swept_flux: P1SweptFluxResult
    transport: SweptFluxTransportResult
    projected: bool


@dataclass(frozen=True)
class GeometricCommonFluxTransportResult:
    """Geometric q transport plus same-face volume and mass fluxes."""

    phase_transport: GeometricPhaseTransportResult
    volume_fluxes: tuple[object, object]
    mass_fluxes: tuple[object, object]


def transport_geometric_phase_state_2d(
    grid,
    state: GeometricPhaseState,
    face_velocity,
    *,
    dt: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-11,
    project_every_steps: int = 0,
    step_index: int = 0,
    max_newton_iterations: int = 8,
    max_cg_iterations: int | None = None,
    sign_safety: float = 0.95,
    min_step_fraction: float = 1.0e-8,
) -> GeometricPhaseTransportResult:
    """Advance owned ``q`` by geometric swept flux and optionally project ``phi``.

    ``project_every_steps=0`` preserves the transported but incompatible
    pre-projection state.  Positive values project when ``step_index`` is a
    multiple of the cadence, so ``project_every_steps=1`` performs the AO
    compatibility projection on every transport call.
    """
    if not isinstance(state, GeometricPhaseState):
        raise TypeError("state must be a GeometricPhaseState")
    _validate_tolerance(tolerance)
    try:
        state = type(state).from_q_phi(
            grid,
            state.q,
            state.phi,
            level=state.stratum.level,
            tolerance=tolerance,
            require_compatible=True,
            ledger=state.ledger,
        )
    except ValueError as exc:
        raise ValueError(
            "geometric phase transport requires a compatible q/phi state; "
            "project compatibility before constructing swept fluxes"
        ) from exc
    project_every_steps = _validate_nonnegative_int(
        project_every_steps,
        name="project_every_steps",
    )
    step_index = _validate_nonnegative_int(step_index, name="step_index")

    swept_flux = construct_p1_swept_flux_2d(
        grid,
        state.phi,
        face_velocity,
        dt=dt,
        boundary=boundary,
        level=state.stratum.level,
        tolerance=tolerance,
    )
    transport = apply_certified_swept_flux_2d(
        grid,
        state.q,
        swept_flux.phase_fluxes,
        dt=dt,
        boundary=boundary,
        tolerance=tolerance,
    )
    pre_projection = type(state).from_q_phi(
        grid,
        transport.q,
        state.phi,
        level=state.stratum.level,
        tolerance=tolerance,
        require_compatible=False,
    )
    should_project = (
        project_every_steps > 0 and step_index % project_every_steps == 0
    )
    final_state = (
        pre_projection.project_compatibility(
            grid,
            tolerance=tolerance,
            max_newton_iterations=max_newton_iterations,
            max_cg_iterations=max_cg_iterations,
            sign_safety=sign_safety,
            min_step_fraction=min_step_fraction,
        )
        if should_project
        else pre_projection
    )
    return GeometricPhaseTransportResult(
        state=final_state,
        pre_projection_state=pre_projection,
        swept_flux=swept_flux,
        transport=transport,
        projected=should_project,
    )


def transport_geometric_phase_common_flux_2d(
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
    max_cg_iterations: int | None = None,
    sign_safety: float = 0.95,
    min_step_fraction: float = 1.0e-8,
) -> GeometricCommonFluxTransportResult:
    """Advance geometric phase and form ``Phi_m`` from the same ``Phi_l``."""
    phase_transport = transport_geometric_phase_state_2d(
        grid,
        state,
        face_velocity,
        dt=dt,
        boundary=boundary,
        tolerance=tolerance,
        project_every_steps=project_every_steps,
        step_index=step_index,
        max_newton_iterations=max_newton_iterations,
        max_cg_iterations=max_cg_iterations,
        sign_safety=sign_safety,
        min_step_fraction=min_step_fraction,
    )
    volume_fluxes = face_volume_fluxes_2d(
        grid,
        face_velocity,
        boundary=boundary,
        tolerance=tolerance,
    )
    mass_fluxes = common_mass_fluxes_2d(
        grid,
        phase_transport.swept_flux.phase_fluxes,
        volume_fluxes,
        rho_l=rho_l,
        rho_g=rho_g,
    )
    return GeometricCommonFluxTransportResult(
        phase_transport=phase_transport,
        volume_fluxes=volume_fluxes,
        mass_fluxes=mass_fluxes,
    )


def _build_state(
    cls,
    *,
    grid,
    q,
    phi,
    geometry: P1CutGeometry,
    level: float,
    tolerance: float,
    require_compatible: bool,
    ledger: CompatibilityProjectionLedger | None,
):
    xp = grid.xp
    complex_h = MetricCellComplex.from_grid(grid)
    residual = xp.asarray(q) - geometry.q
    residual_linf = _norm_linf(xp, residual)
    if require_compatible and residual_linf > tolerance:
        raise ValueError(
            "geometric phase state is not compatible: "
            f"||q-Q_h(phi)||_inf={residual_linf:.3e}"
        )
    return cls(
        q=xp.asarray(q),
        phi=phi,
        theta=complex_h.theta_view(q),
        geometry=geometry,
        stratum=_build_stratum(grid, phi, geometry=geometry, level=level),
        compatibility_residual_linf=residual_linf,
        compatibility_residual_l2=_norm_l2(xp, residual),
        ledger=ledger,
    )


def _build_stratum(
    grid,
    phi,
    *,
    geometry: P1CutGeometry,
    level: float,
) -> GeometricPhaseStratum:
    xp = grid.xp
    values, _points = _cell_corner_fields(xp, grid, phi - float(level))
    return GeometricPhaseStratum(
        node_signs=phi < float(level),
        cell_cases=_case_field(xp, values),
        sign_margin=geometry.sign_margin,
        level=float(level),
    )


def _validate_phi(grid, phi):
    if grid.ndim != 2:
        raise ValueError("GeometricPhaseState currently supports 2D grids")
    phi_dev = grid.xp.asarray(phi)
    if tuple(phi_dev.shape) != (grid.N[0] + 1, grid.N[1] + 1):
        raise ValueError("phi shape must match the grid nodal shape")
    if _scalar_bool(grid.xp, grid.xp.any(~grid.xp.isfinite(phi_dev))):
        raise ValueError("phi must be finite")
    return phi_dev


def _validate_q_bounds(xp, q, cell_measures, tolerance: float) -> None:
    if _scalar_bool(xp, xp.any(~xp.isfinite(q))):
        raise ValueError("q must be finite")
    below = q < -tolerance
    above = q > cell_measures + tolerance
    if _scalar_bool(xp, xp.any(below | above)):
        raise ValueError("q must lie within physical cell-volume bounds")


def _validate_tolerance(tolerance: float) -> None:
    if not (math.isfinite(float(tolerance)) and float(tolerance) >= 0.0):
        raise ValueError("tolerance must be finite and non-negative")


def _validate_nonnegative_int(value, *, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a non-negative integer")
    try:
        converted = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if converted != value or converted < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return converted


def _norm_linf(xp, value) -> float:
    return _scalar_float(xp, xp.max(xp.abs(value)))


def _norm_l2(xp, value) -> float:
    return _scalar_float(xp, xp.sqrt(xp.sum(value * value)))


def _scalar_bool(xp, value) -> bool:
    if hasattr(value, "get"):
        value = value.get()
    return bool(value)


def _scalar_float(xp, value) -> float:
    if hasattr(value, "get"):
        value = value.get()
    return float(value)


def _array_namespace(value):
    module = getattr(type(value), "__module__", "")
    if module.startswith("cupy"):
        import cupy  # type: ignore[import-not-found]

        return cupy
    import numpy

    return numpy
