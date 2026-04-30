"""Operator-stack assembly helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

from ..ccd.fccd import FCCDSolver
from ..levelset.interfaces import ILevelSetAdvection
from ..ns_terms.interfaces import IConvectionTerm
from .gradient_operator import FCCDDivergenceOperator, IGradientOperator
from .ns_operator_builders import (
    build_ns_divergence_operators,
    build_ns_fccd_solver_if_needed,
    build_ns_gradient_operators,
    build_ns_transport_operators,
)
from .ns_runtime_factories import NSPPEFactoryOptions, build_ns_ppe_solver


@dataclass(frozen=True)
class NSOperatorStackOptions:
    bc_type: str
    advection_scheme: str
    convection_scheme: str
    pressure_gradient_scheme: str
    surface_tension_gradient_scheme: str
    ppe_solver_name: str
    face_flux_projection: bool
    uccd6_sigma: float


@dataclass(frozen=True)
class NSOperatorStack:
    fccd: FCCDSolver | None
    fccd_div_op: FCCDDivergenceOperator | None
    div_op: object
    face_flux_projection: bool
    ppe_solver: object
    pressure_grad_op: IGradientOperator
    surface_tension_grad_op: IGradientOperator | None
    adv: ILevelSetAdvection
    conv_term: IConvectionTerm


def build_ns_operator_stack(
    *,
    backend,
    grid,
    ccd,
    options: NSOperatorStackOptions,
    ppe_options: NSPPEFactoryOptions,
) -> NSOperatorStack:
    fccd = build_ns_fccd_solver_if_needed(
        backend=backend,
        grid=grid,
        ccd=ccd,
        bc_type=options.bc_type,
        scheme_names={
            options.advection_scheme,
            options.convection_scheme,
            options.pressure_gradient_scheme,
            options.surface_tension_gradient_scheme,
            options.ppe_solver_name,
        },
    )
    fccd_div_op, div_op = build_ns_divergence_operators(
        backend=backend,
        grid=grid,
        ccd=ccd,
        bc_type=options.bc_type,
        ppe_solver_name=options.ppe_solver_name,
        fccd=fccd,
    )

    face_flux_projection = options.face_flux_projection or bool(fccd_div_op is not None)
    if (
        ppe_options.interface_coupling_scheme == "affine_jump"
        and not face_flux_projection
    ):
        raise ValueError(
            "ppe_interface_coupling_scheme='affine_jump' requires a "
            "face-flux projection path so the corrector can subtract the "
            "same interface jump used by the PPE"
        )
    ppe_solver = build_ns_ppe_solver(
        backend=backend,
        grid=grid,
        bc_type=options.bc_type,
        fccd=fccd,
        options=ppe_options,
    )

    pressure_grad_op, surface_tension_grad_op = build_ns_gradient_operators(
        backend=backend,
        ccd=ccd,
        bc_type=options.bc_type,
        pressure_gradient_scheme=options.pressure_gradient_scheme,
        surface_tension_gradient_scheme=options.surface_tension_gradient_scheme,
        fccd=fccd,
    )

    adv, conv_term = build_ns_transport_operators(
        backend=backend,
        grid=grid,
        ccd=ccd,
        bc_type=options.bc_type,
        advection_scheme=options.advection_scheme,
        convection_scheme=options.convection_scheme,
        fccd=fccd,
        uccd6_sigma=options.uccd6_sigma,
    )
    return NSOperatorStack(
        fccd=fccd,
        fccd_div_op=fccd_div_op,
        div_op=div_op,
        face_flux_projection=face_flux_projection,
        ppe_solver=ppe_solver,
        pressure_grad_op=pressure_grad_op,
        surface_tension_grad_op=surface_tension_grad_op,
        adv=adv,
        conv_term=conv_term,
    )
