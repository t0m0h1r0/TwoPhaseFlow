"""Operator-stack assembly helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

from ..ccd.fccd import FCCDSolver
from ..levelset.interfaces import ILevelSetAdvection
from ..ns_terms.interfaces import IConvectionTerm
from .gradient_operator import (
    CCDGradientOperator,
    CCDDivergenceOperator,
    FCCDDivergenceOperator,
    FVMDivergenceOperator,
    IGradientOperator,
)
from .ns_runtime_factories import NSPPEFactoryOptions, build_ns_ppe_solver
from .scheme_build_ctx import AdvectionBuildCtx, ConvectionBuildCtx, GradientBuildCtx


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
    fccd_names = frozenset({"fccd_flux", "fccd_nodal", "fccd_iterative"})
    needs_fccd = bool(
        {
            options.advection_scheme,
            options.convection_scheme,
            options.pressure_gradient_scheme,
            options.surface_tension_gradient_scheme,
            options.ppe_solver_name,
        }
        & fccd_names
    )
    fccd = (
        FCCDSolver(
            grid,
            backend,
            bc_type=options.bc_type,
            ccd_solver=ccd,
        )
        if needs_fccd
        else None
    )

    ccd_grad_op: IGradientOperator = CCDGradientOperator(
        backend,
        ccd,
        bc_type=options.bc_type,
    )
    fccd_div_op = FCCDDivergenceOperator(fccd) if fccd is not None else None
    if options.ppe_solver_name == "fccd_iterative":
        if fccd_div_op is None:
            raise RuntimeError("FCCD PPE requires FCCDDivergenceOperator")
        div_op = fccd_div_op
    elif not grid.uniform and options.bc_type == "wall":
        div_op = FVMDivergenceOperator(backend, grid)
    else:
        div_op = CCDDivergenceOperator(ccd)

    face_flux_projection = options.face_flux_projection or bool(fccd_div_op is not None)
    ppe_solver = build_ns_ppe_solver(
        backend=backend,
        grid=grid,
        bc_type=options.bc_type,
        fccd=fccd,
        options=ppe_options,
    )

    grad_ctx = GradientBuildCtx(ccd_op=ccd_grad_op, fccd=fccd)
    pressure_grad_op = IGradientOperator.from_scheme(
        options.pressure_gradient_scheme,
        grad_ctx,
    )
    surface_tension_grad_op = (
        None
        if options.surface_tension_gradient_scheme == "none"
        else IGradientOperator.from_scheme(options.surface_tension_gradient_scheme, grad_ctx)
    )

    adv = ILevelSetAdvection.from_scheme(
        options.advection_scheme,
        AdvectionBuildCtx(
            backend=backend,
            grid=grid,
            ccd=ccd,
            bc_type=options.bc_type,
            fccd=fccd,
        ),
    )
    conv_term = IConvectionTerm.from_scheme(
        options.convection_scheme,
        ConvectionBuildCtx(
            backend=backend,
            ccd=ccd,
            grid=grid,
            fccd=fccd,
            uccd6_sigma=options.uccd6_sigma,
        ),
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
