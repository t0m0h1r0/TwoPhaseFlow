"""Scheme/runtime bootstrap helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..levelset.curvature_psi import CurvatureCalculatorPsi
from ..levelset.curvature_filter import InterfaceLimitedFilter
from .ns_option_canonicalizer import (
    validate_local_epsilon_surface_tension_compatibility,
)
from .ns_operator_stack import NSOperatorStack, NSOperatorStackOptions, build_ns_operator_stack
from .ns_ppe_runtime import make_ns_ppe_factory_options
from .ns_runtime_binding import bind_ns_scheme_runtime
from .ns_runtime_config import NSSchemeRuntimeState, normalise_ns_scheme_runtime


@dataclass(frozen=True)
class NSSchemeRuntimeArtifacts:
    curv: object
    curvature_filter: object
    state: NSSchemeRuntimeState


def build_ns_scheme_runtime_artifacts(
    *,
    backend,
    ccd,
    eps,
    use_local_eps: bool,
    alpha_grid: float,
    make_eps_field: Callable[[], object],
    options,
) -> NSSchemeRuntimeArtifacts:
    """Build normalized scheme runtime state and curvature helpers."""
    validate_local_epsilon_surface_tension_compatibility(
        use_local_eps=use_local_eps,
        alpha_grid=alpha_grid,
        surface_tension_scheme=getattr(options, "surface_tension_scheme", "csf"),
    )
    curv = CurvatureCalculatorPsi(backend, ccd)
    curvature_filter = InterfaceLimitedFilter(backend, ccd, C=options.hfe_C)
    state = normalise_ns_scheme_runtime(options)
    return NSSchemeRuntimeArtifacts(
        curv=curv,
        curvature_filter=curvature_filter,
        state=state,
    )


def bind_ns_scheme_runtime_artifacts(solver, artifacts: NSSchemeRuntimeArtifacts) -> None:
    """Bind normalized scheme runtime artifacts onto the solver."""
    solver._curv = artifacts.curv
    solver._curvature_filter = artifacts.curvature_filter
    solver._hfe = artifacts.curvature_filter  # Backward-compatible alias.
    bind_ns_scheme_runtime(solver, artifacts.state)
    solver._conv_prev = None
    solver._conv_ab2_ready = False
    solver._velocity_prev = None
    solver._velocity_bdf2_ready = False


def build_ns_scheme_operator_stack(
    *,
    backend,
    grid,
    ccd,
    grid_options,
    scheme_options,
    interface_runtime,
    ppe_runtime,
    scheme_runtime,
) -> NSOperatorStack:
    """Build the operator stack from normalized runtime state."""
    return build_ns_operator_stack(
        backend=backend,
        grid=grid,
        ccd=ccd,
        options=NSOperatorStackOptions(
            bc_type=grid_options.bc_type,
            advection_scheme=scheme_runtime.advection_scheme,
            convection_scheme=scheme_runtime.convection_scheme,
            pressure_gradient_scheme=scheme_runtime.pressure_gradient_scheme,
            surface_tension_gradient_scheme=scheme_runtime.surface_tension_gradient_scheme,
            ppe_solver_name=ppe_runtime.ppe_solver_name,
            face_flux_projection=bool(scheme_options.face_flux_projection)
            or bool(interface_runtime.face_flux_projection),
            uccd6_sigma=float(scheme_options.uccd6_sigma),
        ),
        ppe_options=make_ns_ppe_factory_options(
            ppe_runtime,
            solver_name=ppe_runtime.ppe_solver_name,
        ),
    )


def bind_ns_operator_stack(solver, stack: NSOperatorStack) -> None:
    """Bind the assembled operator stack onto the solver."""
    solver._fccd = stack.fccd
    solver._fccd_div_op = stack.fccd_div_op
    solver._div_op = stack.div_op
    solver._face_flux_projection = stack.face_flux_projection
    solver._ppe_solver = stack.ppe_solver
    solver._pressure_grad_op = stack.pressure_grad_op
    solver._surface_tension_grad_op = stack.surface_tension_grad_op
    solver._grad_op = stack.pressure_grad_op
    solver._adv = stack.adv
    solver._conv_term = stack.conv_term
