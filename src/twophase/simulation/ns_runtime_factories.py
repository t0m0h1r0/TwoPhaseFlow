"""Factory helpers for `TwoPhaseNSSolver` runtime components."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace

from ..levelset.reinitialize import Reinitializer
from ..ppe.defect_correction import PPESolverDefectCorrection
from ..ppe.interfaces import IPPESolver
from .scheme_build_ctx import PPEBuildCtx


@dataclass(frozen=True)
class NSPPEFactoryOptions:
    solver_name: str
    dc_base_solver_name: str | None
    tolerance: float
    max_iterations: int
    restart: int | None
    preconditioner: str
    pcr_stages: int | None
    c_tau: float
    iteration_method: str
    coefficient_scheme: str
    interface_coupling_scheme: str
    defect_correction: bool
    dc_max_iterations: int
    dc_tolerance: float
    dc_relaxation: float


@dataclass(frozen=True)
class NSReinitializerFactoryOptions:
    reinit_steps: int
    reinit_method: str
    dgr_phi_smooth_C: float
    reinit_eps_scale: float
    ridge_sigma_0: float


def build_ns_reinitializer(
    *,
    backend,
    grid,
    ccd,
    eps,
    options: NSReinitializerFactoryOptions,
) -> Reinitializer:
    return Reinitializer(
        backend,
        grid,
        ccd,
        eps,
        n_steps=options.reinit_steps,
        method=options.reinit_method,
        phi_smooth_C=options.dgr_phi_smooth_C,
        eps_scale=options.reinit_eps_scale,
        sigma_0=options.ridge_sigma_0,
    )


def build_ns_ppe_cfg_shim(
    options: NSPPEFactoryOptions,
    *,
    preconditioner: str | None = None,
    pcr_stages: int | None = None,
):
    return SimpleNamespace(
        solver=SimpleNamespace(
            pseudo_tol=options.tolerance,
            pseudo_maxiter=options.max_iterations,
            pseudo_c_tau=options.c_tau,
            ppe_iteration_method=options.iteration_method,
            ppe_restart=options.restart,
            ppe_preconditioner=preconditioner or "none",
            ppe_pcr_stages=pcr_stages,
            ppe_coefficient_scheme=options.coefficient_scheme,
            ppe_interface_coupling_scheme=options.interface_coupling_scheme,
        )
    )


def build_ns_plain_ppe_solver(
    *,
    backend,
    grid,
    bc_type: str,
    fccd,
    options: NSPPEFactoryOptions,
):
    from ..core.boundary import BoundarySpec

    bc_spec = BoundarySpec(
        bc_type=bc_type,
        shape=tuple(n + 1 for n in grid.N),
        N=grid.N,
    )
    cfg_shim = (
        build_ns_ppe_cfg_shim(
            options,
            preconditioner=options.preconditioner,
            pcr_stages=options.pcr_stages,
        )
        if options.solver_name in {"fvm_iterative", "fccd_iterative"} else None
    )
    ppe_ctx = PPEBuildCtx(
        backend=backend,
        grid=grid,
        bc_type=bc_type,
        bc_spec=bc_spec,
        config=cfg_shim,
        fccd=fccd,
    )
    return IPPESolver.from_scheme(options.solver_name, ppe_ctx)


def build_ns_ppe_solver(
    *,
    backend,
    grid,
    bc_type: str,
    fccd,
    options: NSPPEFactoryOptions,
):
    if options.defect_correction:
        from ..core.boundary import BoundarySpec

        base_options = replace(
            options,
            solver_name=options.dc_base_solver_name or options.solver_name,
            defect_correction=False,
        )
        base_solver = build_ns_plain_ppe_solver(
            backend=backend,
            grid=grid,
            bc_type=bc_type,
            fccd=fccd,
            options=base_options,
        )
        operator_ctx = PPEBuildCtx(
            backend=backend,
            grid=grid,
            bc_type=bc_type,
            bc_spec=BoundarySpec(
                bc_type=bc_type,
                shape=tuple(n + 1 for n in grid.N),
                N=grid.N,
            ),
            config=build_ns_ppe_cfg_shim(options, preconditioner="none"),
            fccd=fccd,
        )
        operator = IPPESolver.from_scheme(options.solver_name, operator_ctx)
        return PPESolverDefectCorrection(
            backend,
            grid,
            base_solver,
            operator,
            max_corrections=options.dc_max_iterations,
            tolerance=options.dc_tolerance,
            relaxation=options.dc_relaxation,
        )
    return build_ns_plain_ppe_solver(
        backend=backend,
        grid=grid,
        bc_type=bc_type,
        fccd=fccd,
        options=options,
    )
