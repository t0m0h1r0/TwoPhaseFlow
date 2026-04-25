"""Runtime component assembly helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

from ..levelset.reconstruction import ReconstructionConfig, HeavisideInterfaceReconstructor
from ..levelset.transport_strategy import PhiPrimaryTransport, PsiDirectTransport, StaticInterfaceTransport
from .surface_tension_strategy import INSSurfaceTensionStrategy
from .velocity_reprojector import IVelocityReprojector
from .viscous_predictor import IViscousPredictor
from .ns_runtime_strategy_builders import (
    build_ns_reprojector,
    build_ns_step_diagnostics,
    build_ns_surface_tension_force,
    build_ns_viscous_predictor,
)


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


@dataclass(frozen=True)
class NSRuntimeComponentOptions:
    phi_primary_clip_factor: float
    phi_primary_heaviside_eps_scale: float
    interface_tracking_enabled: bool
    phi_primary_transport: bool
    phi_primary_redist_every: int
    reinit_every: int
    debug_diagnostics: bool
    reproject_mode: str
    cn_viscous: bool
    reynolds_number: float
    viscous_spatial_scheme: str
    viscous_time_scheme: str
    surface_tension_scheme: str


def build_ns_runtime_components(
    *,
    backend,
    grid,
    adv,
    reinit,
    eps,
    options: NSRuntimeComponentOptions,
    reproj_iim,
) -> NSRuntimeComponents:
    reconstruct_base = HeavisideInterfaceReconstructor(
        backend,
        ReconstructionConfig(
            eps=eps,
            eps_scale=1.0,
            clip_factor=options.phi_primary_clip_factor,
        ),
    )
    reconstruct_phi_primary = HeavisideInterfaceReconstructor(
        backend,
        ReconstructionConfig(
            eps=eps,
            eps_scale=options.phi_primary_heaviside_eps_scale,
            clip_factor=options.phi_primary_clip_factor,
        ),
    )

    if not options.interface_tracking_enabled:
        transport = StaticInterfaceTransport(backend)
    elif options.phi_primary_transport:
        transport = PhiPrimaryTransport(
            backend,
            {
                "redist_every": options.phi_primary_redist_every,
                "clip_factor": options.phi_primary_clip_factor,
                "eps_scale": options.phi_primary_heaviside_eps_scale,
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
            reinit_every=options.reinit_every,
        )

    step_diag = build_ns_step_diagnostics(
        debug_enabled=options.debug_diagnostics,
    )
    reprojector = build_ns_reprojector(
        reproject_mode=options.reproject_mode,
        reproj_iim=reproj_iim,
        reconstruct_base=reconstruct_base,
    )
    viscous_predictor = build_ns_viscous_predictor(
        backend=backend,
        cn_viscous=options.cn_viscous,
        viscous_time_scheme=options.viscous_time_scheme,
        reynolds_number=options.reynolds_number,
        viscous_spatial_scheme=options.viscous_spatial_scheme,
    )
    st_force = build_ns_surface_tension_force(
        backend=backend,
        surface_tension_scheme=options.surface_tension_scheme,
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
