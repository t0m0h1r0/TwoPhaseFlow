"""Strategy assembly helpers for `TwoPhaseNSSolver` runtime components."""

from __future__ import annotations

from .step_diagnostics import ActiveStepDiagnostics, NullStepDiagnostics
from .surface_tension_strategy import INSSurfaceTensionStrategy
from .velocity_reprojector import IVelocityReprojector
from .viscous_predictor import IViscousPredictor
from .scheme_build_ctx import ReprojectorBuildCtx, SurfaceTensionBuildCtx, ViscousBuildCtx


def build_ns_step_diagnostics(*, debug_enabled: bool):
    return ActiveStepDiagnostics() if debug_enabled else NullStepDiagnostics()


def build_ns_reprojector(*, reproject_mode: str, reproj_iim, reconstruct_base):
    return IVelocityReprojector.from_scheme(
        reproject_mode,
        ReprojectorBuildCtx(
            iim_stencil_corrector=reproj_iim,
            reconstruct_base=reconstruct_base,
        ),
    )


def build_ns_viscous_predictor(
    *,
    backend,
    cn_viscous: bool,
    viscous_time_scheme: str | None = None,
    reynolds_number: float,
    viscous_spatial_scheme: str,
    cn_mode: str = "picard",
    viscous_solver: str = "defect_correction",
    viscous_solver_tolerance: float = 1.0e-8,
    viscous_solver_max_iterations: int = 80,
    viscous_solver_restart: int = 40,
    viscous_dc_max_iterations: int = 3,
    viscous_dc_relaxation: float = 0.8,
):
    from .ns_option_canonicalizer import canonicalize_viscous_time_scheme
    from ..ns_terms.viscous import ViscousTerm
    from ..time_integration.cn_advance import make_cn_advance

    selected_scheme = canonicalize_viscous_time_scheme(
        viscous_time_scheme
        or ("crank_nicolson" if cn_viscous else "forward_euler")
    )
    viscous_term = ViscousTerm(
        backend,
        Re=reynolds_number,
        cn_viscous=True,
        spatial_scheme=viscous_spatial_scheme,
        cn_advance=make_cn_advance(backend, cn_mode),
    )
    return IViscousPredictor.from_scheme(
        selected_scheme,
        ViscousBuildCtx(
            backend=backend,
            re=reynolds_number,
            spatial_scheme=viscous_spatial_scheme,
            viscous_term=viscous_term,
            cn_mode=cn_mode,
            solver=viscous_solver,
            solver_tolerance=viscous_solver_tolerance,
            solver_max_iterations=viscous_solver_max_iterations,
            solver_restart=viscous_solver_restart,
            dc_max_iterations=viscous_dc_max_iterations,
            dc_relaxation=viscous_dc_relaxation,
        ),
    )


def build_ns_surface_tension_force(*, backend, surface_tension_scheme: str):
    return INSSurfaceTensionStrategy.from_scheme(
        surface_tension_scheme,
        SurfaceTensionBuildCtx(backend=backend),
    )
