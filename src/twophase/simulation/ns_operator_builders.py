"""Focused operator builders for `TwoPhaseNSSolver` assembly."""

from __future__ import annotations

from ..ccd.fccd import FCCDSolver
from ..core.boundary import is_all_periodic
from ..levelset.interfaces import ILevelSetAdvection
from ..ns_terms.interfaces import IConvectionTerm
from .gradient_operator import (
    CCDGradientOperator,
    CCDDivergenceOperator,
    FCCDDivergenceOperator,
    FVMDivergenceOperator,
    IGradientOperator,
)
from .scheme_build_ctx import AdvectionBuildCtx, ConvectionBuildCtx, GradientBuildCtx


def build_ns_fccd_solver_if_needed(*, backend, grid, ccd, bc_type: str, scheme_names: set[str]):
    fccd_names = frozenset({"fccd_flux", "fccd_nodal", "fccd_iterative"})
    needs_fccd = bool(scheme_names & fccd_names)
    if not needs_fccd:
        return None
    return FCCDSolver(
        grid,
        backend,
        bc_type=bc_type,
        ccd_solver=ccd,
    )


def build_ns_divergence_operators(
    *,
    backend,
    grid,
    ccd,
    bc_type: str,
    ppe_solver_name: str,
    fccd,
):
    fccd_div_op = FCCDDivergenceOperator(fccd) if fccd is not None else None
    if ppe_solver_name == "fccd_iterative":
        if fccd_div_op is None:
            raise RuntimeError("FCCD PPE requires FCCDDivergenceOperator")
        div_op = fccd_div_op
    elif not grid.uniform and not is_all_periodic(bc_type, grid.ndim):
        div_op = FVMDivergenceOperator(backend, grid)
    else:
        div_op = CCDDivergenceOperator(ccd)
    return fccd_div_op, div_op


def build_ns_gradient_operators(
    *,
    backend,
    ccd,
    bc_type: str,
    pressure_gradient_scheme: str,
    surface_tension_gradient_scheme: str,
    fccd,
):
    ccd_grad_op: IGradientOperator = CCDGradientOperator(
        backend,
        ccd,
        bc_type=bc_type,
    )
    grad_ctx = GradientBuildCtx(ccd_op=ccd_grad_op, fccd=fccd)
    pressure_grad_op = IGradientOperator.from_scheme(
        pressure_gradient_scheme,
        grad_ctx,
    )
    surface_tension_grad_op = (
        None
        if surface_tension_gradient_scheme == "none"
        else IGradientOperator.from_scheme(surface_tension_gradient_scheme, grad_ctx)
    )
    return pressure_grad_op, surface_tension_grad_op


def build_ns_transport_operators(
    *,
    backend,
    grid,
    ccd,
    bc_type: str,
    advection_scheme: str,
    convection_scheme: str,
    fccd,
    uccd6_sigma: float,
):
    adv = ILevelSetAdvection.from_scheme(
        advection_scheme,
        AdvectionBuildCtx(
            backend=backend,
            grid=grid,
            ccd=ccd,
            bc_type=bc_type,
            fccd=fccd,
        ),
    )
    conv_term = IConvectionTerm.from_scheme(
        convection_scheme,
        ConvectionBuildCtx(
            backend=backend,
            ccd=ccd,
            grid=grid,
            fccd=fccd,
            uccd6_sigma=uccd6_sigma,
        ),
    )
    return adv, conv_term
