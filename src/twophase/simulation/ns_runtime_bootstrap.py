"""Bootstrap helpers for `TwoPhaseNSSolver` runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..ppe.iim.stencil_corrector import IIMStencilCorrector
from .ns_option_canonicalizer import canonicalize_viscous_time_scheme
from .ns_runtime_components import (
    NSRuntimeComponentOptions,
    NSRuntimeComponents,
    build_ns_runtime_components,
)


@dataclass(frozen=True)
class NSRuntimeBootstrapArtifacts:
    reproj_iim: object
    reinit: object
    cn_viscous: bool
    reynolds_number: float
    viscous_spatial_scheme: str
    viscous_time_scheme: str
    cn_mode: str
    surface_tension_scheme: str
    components: NSRuntimeComponents


def build_ns_runtime_bootstrap(
    *,
    backend,
    grid,
    adv,
    eps,
    interface_runtime,
    scheme_options,
    build_reinitializer: Callable[[], object],
) -> NSRuntimeBootstrapArtifacts:
    """Build runtime artifacts after geometry/runtime normalization."""
    reproj_iim = IIMStencilCorrector(grid, mode="hermite")
    reinit = build_reinitializer()
    viscous_time_scheme = canonicalize_viscous_time_scheme(
        getattr(
            scheme_options,
            "viscous_time_scheme",
            "crank_nicolson" if bool(scheme_options.cn_viscous) else "forward_euler",
        )
    )
    cn_viscous = viscous_time_scheme in {"crank_nicolson", "implicit_bdf2"}
    reynolds_number = float(scheme_options.Re)
    viscous_spatial_scheme = str(scheme_options.viscous_spatial_scheme)
    cn_mode = str(getattr(scheme_options, "cn_mode", "picard"))
    surface_tension_scheme = str(scheme_options.surface_tension_scheme)
    components = build_ns_runtime_components(
        backend=backend,
        grid=grid,
        adv=adv,
        reinit=reinit,
        eps=eps,
        options=NSRuntimeComponentOptions(
            phi_primary_clip_factor=interface_runtime.phi_primary_clip_factor,
            phi_primary_heaviside_eps_scale=interface_runtime.phi_primary_heaviside_eps_scale,
            interface_tracking_enabled=interface_runtime.interface_tracking_enabled,
            phi_primary_transport=interface_runtime.phi_primary_transport,
            phi_primary_redist_every=interface_runtime.phi_primary_redist_every,
            reinit_every=interface_runtime.reinit_every,
            debug_diagnostics=scheme_options.debug_diagnostics,
            reproject_mode=interface_runtime.reproject_mode,
            cn_viscous=cn_viscous,
            reynolds_number=reynolds_number,
            viscous_spatial_scheme=viscous_spatial_scheme,
            viscous_time_scheme=viscous_time_scheme,
            viscous_solver=str(getattr(scheme_options, "viscous_solver", "defect_correction")),
            viscous_solver_tolerance=float(
                getattr(scheme_options, "viscous_solver_tolerance", 1.0e-8)
            ),
            viscous_solver_max_iterations=int(
                getattr(scheme_options, "viscous_solver_max_iterations", 80)
            ),
            viscous_solver_restart=int(
                getattr(scheme_options, "viscous_solver_restart", 40)
            ),
            viscous_dc_max_iterations=int(
                getattr(scheme_options, "viscous_dc_max_iterations", 3)
            ),
            viscous_dc_relaxation=float(
                getattr(scheme_options, "viscous_dc_relaxation", 0.8)
            ),
            viscous_dc_low_operator=str(
                getattr(scheme_options, "viscous_dc_low_operator", "component")
            ),
            cn_mode=cn_mode,
            surface_tension_scheme=surface_tension_scheme,
        ),
        reproj_iim=reproj_iim,
    )
    return NSRuntimeBootstrapArtifacts(
        reproj_iim=reproj_iim,
        reinit=reinit,
        cn_viscous=cn_viscous,
        reynolds_number=reynolds_number,
        viscous_spatial_scheme=viscous_spatial_scheme,
        viscous_time_scheme=viscous_time_scheme,
        cn_mode=cn_mode,
        surface_tension_scheme=surface_tension_scheme,
        components=components,
    )


def bind_ns_runtime_bootstrap(solver, artifacts: NSRuntimeBootstrapArtifacts) -> None:
    """Bind runtime bootstrap artifacts onto the solver compatibility surface."""
    solver._p_prev = None
    solver._p_prev_dev = None
    solver._reproj_iim = artifacts.reproj_iim
    solver._reinit = artifacts.reinit
    solver._cn_viscous = artifacts.cn_viscous
    solver._Re = artifacts.reynolds_number
    solver._viscous_spatial_scheme = artifacts.viscous_spatial_scheme
    solver._viscous_time_scheme = artifacts.viscous_time_scheme
    solver._cn_mode = artifacts.cn_mode
    solver._surface_tension_scheme = artifacts.surface_tension_scheme
    solver._reconstruct_base = artifacts.components.reconstruct_base
    solver._reconstruct_phi_primary = artifacts.components.reconstruct_phi_primary
    solver._transport = artifacts.components.transport
    solver.X, solver.Y = artifacts.components.X, artifacts.components.Y
    solver._step_diag = artifacts.components.step_diag
    solver._reprojector = artifacts.components.reprojector
    solver._viscous_predictor = artifacts.components.viscous_predictor
    solver._st_force = artifacts.components.st_force
