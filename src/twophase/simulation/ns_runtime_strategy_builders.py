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
    reynolds_number: float,
    viscous_spatial_scheme: str,
):
    from ..ns_terms.viscous import ViscousTerm

    viscous_term = ViscousTerm(
        backend,
        Re=reynolds_number,
        cn_viscous=True,
        spatial_scheme=viscous_spatial_scheme,
    )
    return IViscousPredictor.from_scheme(
        "crank_nicolson" if cn_viscous else "explicit",
        ViscousBuildCtx(
            backend=backend,
            re=reynolds_number,
            spatial_scheme=viscous_spatial_scheme,
            viscous_term=viscous_term,
        ),
    )


def build_ns_surface_tension_force(*, backend, surface_tension_scheme: str):
    return INSSurfaceTensionStrategy.from_scheme(
        surface_tension_scheme,
        SurfaceTensionBuildCtx(backend=backend),
    )
