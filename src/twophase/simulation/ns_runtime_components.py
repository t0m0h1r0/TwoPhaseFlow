"""Runtime component assembly helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

from ..levelset.reconstruction import ReconstructionConfig, HeavisideInterfaceReconstructor
from ..levelset.transport_strategy import PhiPrimaryTransport, PsiDirectTransport, StaticInterfaceTransport
from .step_diagnostics import ActiveStepDiagnostics, NullStepDiagnostics
from .surface_tension_strategy import INSSurfaceTensionStrategy
from .velocity_reprojector import IVelocityReprojector
from .viscous_predictor import IViscousPredictor
from .scheme_build_ctx import ReprojectorBuildCtx, SurfaceTensionBuildCtx, ViscousBuildCtx


@dataclass(frozen=True)
class NSRuntimeComponents:
    reconstruct_base: HeavisideInterfaceReconstructor
    reconstruct_phi_primary: HeavisideInterfaceReconstructor
    transport: object
    step_diag: object
    reprojector: IVelocityReprojector
    viscous_predictor: IViscousPredictor
    st_force: INSSurfaceTensionStrategy
    X: object
    Y: object


def build_ns_runtime_components(
    *,
    backend,
    grid,
    adv,
    reinit,
    eps,
    phi_primary_clip_factor: float,
    phi_primary_heaviside_eps_scale: float,
    interface_tracking_enabled: bool,
    phi_primary_transport: bool,
    phi_primary_redist_every: int,
    reinit_every: int,
    debug_diagnostics: bool,
    reproject_mode: str,
    reproj_iim,
    cn_viscous: bool,
    reynolds_number: float,
    viscous_spatial_scheme: str,
    surface_tension_scheme: str,
) -> NSRuntimeComponents:
    reconstruct_base = HeavisideInterfaceReconstructor(
        backend,
        ReconstructionConfig(
            eps=eps,
            eps_scale=1.0,
            clip_factor=phi_primary_clip_factor,
        ),
    )
    reconstruct_phi_primary = HeavisideInterfaceReconstructor(
        backend,
        ReconstructionConfig(
            eps=eps,
            eps_scale=phi_primary_heaviside_eps_scale,
            clip_factor=phi_primary_clip_factor,
        ),
    )

    if not interface_tracking_enabled:
        transport = StaticInterfaceTransport(backend)
    elif phi_primary_transport:
        transport = PhiPrimaryTransport(
            backend,
            {
                "redist_every": phi_primary_redist_every,
                "clip_factor": phi_primary_clip_factor,
                "eps_scale": phi_primary_heaviside_eps_scale,
            },
            reconstruct_phi_primary,
            adv,
            reinit,
            grid,
        )
    else:
        transport = PsiDirectTransport(
            backend,
            adv,
            reinit,
            reinit_every=reinit_every,
        )

    step_diag = ActiveStepDiagnostics() if debug_diagnostics else NullStepDiagnostics()
    reprojector = IVelocityReprojector.from_scheme(
        reproject_mode,
        ReprojectorBuildCtx(
            iim_stencil_corrector=reproj_iim,
            reconstruct_base=reconstruct_base,
        ),
    )

    from ..ns_terms.viscous import ViscousTerm

    viscous_term = ViscousTerm(
        backend,
        Re=reynolds_number,
        cn_viscous=True,
        spatial_scheme=viscous_spatial_scheme,
    )
    viscous_predictor = IViscousPredictor.from_scheme(
        "crank_nicolson" if cn_viscous else "explicit",
        ViscousBuildCtx(
            backend=backend,
            re=reynolds_number,
            spatial_scheme=viscous_spatial_scheme,
            viscous_term=viscous_term,
        ),
    )

    st_force = INSSurfaceTensionStrategy.from_scheme(
        surface_tension_scheme,
        SurfaceTensionBuildCtx(backend=backend),
    )
    X, Y = grid.meshgrid()
    return NSRuntimeComponents(
        reconstruct_base=reconstruct_base,
        reconstruct_phi_primary=reconstruct_phi_primary,
        transport=transport,
        step_diag=step_diag,
        reprojector=reprojector,
        viscous_predictor=viscous_predictor,
        st_force=st_force,
        X=X,
        Y=Y,
    )
