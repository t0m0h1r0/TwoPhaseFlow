"""Builder adapter for ``TwoPhaseNSSolver`` construction from configs."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .ns_solver_options import (
    NSSolverInitOptions,
    SolverGridOptions,
    SolverInterfaceOptions,
    SolverPPEOptions,
    SolverSchemeOptions,
)

if TYPE_CHECKING:
    from .config_io import ExperimentConfig
    from .ns_pipeline import TwoPhaseNSSolver


def build_solver_init_options(cfg: "ExperimentConfig") -> NSSolverInitOptions:
    """Translate ``ExperimentConfig`` into grouped solver options."""
    g = cfg.grid
    run = getattr(cfg, "run", g)
    physics = getattr(cfg, "physics", g)
    fitting_axes = getattr(g, "fitting_axes", (True, True))
    alpha_grid = getattr(g, "alpha_grid", 1.0)
    return NSSolverInitOptions(
        grid=SolverGridOptions(
            NX=g.NX,
            NY=g.NY,
            LX=g.LX,
            LY=g.LY,
            bc_type=g.bc_type,
            alpha_grid=alpha_grid,
            fitting_axes=fitting_axes,
            fitting_alpha_grid=(
                getattr(g, "fitting_alpha_grid", None)
                or tuple(alpha_grid if axis else 1.0 for axis in fitting_axes)
            ),
            eps_factor=getattr(g, "eps_factor", 1.5),
            eps_g_factor=getattr(g, "eps_g_factor", 2.0),
            fitting_eps_g_factor=(
                getattr(g, "fitting_eps_g_factor", None)
                or (getattr(g, "eps_g_factor", 2.0),) * 2
            ),
            eps_g_cells=getattr(g, "eps_g_cells", None),
            fitting_eps_g_cells=(
                getattr(g, "fitting_eps_g_cells", None)
                or (getattr(g, "eps_g_cells", None),) * 2
            ),
            wall_refinement_axes=getattr(g, "wall_refinement_axes", (False, False)),
            wall_alpha_grid=getattr(g, "wall_alpha_grid", (1.0, 1.0)),
            wall_eps_g_factor=getattr(g, "wall_eps_g_factor", 2.0),
            wall_eps_g_factor_axes=(
                getattr(g, "wall_eps_g_factor_axes", None)
                or (getattr(g, "wall_eps_g_factor", 2.0),) * 2
            ),
            wall_eps_g_cells=getattr(g, "wall_eps_g_cells", (None, None)),
            wall_sides=getattr(
                g,
                "wall_sides",
                (("lower", "upper"), ("lower", "upper")),
            ),
            dx_min_floor=getattr(g, "dx_min_floor", 1e-6),
            fitting_dx_min_floor=(
                getattr(g, "fitting_dx_min_floor", None)
                or (getattr(g, "dx_min_floor", 1e-6),) * 2
            ),
            use_local_eps=getattr(g, "use_local_eps", False),
            eps_xi_cells=getattr(g, "eps_xi_cells", None),
        ),
        interface=SolverInterfaceOptions(
            grid_rebuild_freq=getattr(g, "grid_rebuild_freq", 0),
            reinit_every=getattr(run, "reinit_every", 2),
            reinit_method=(getattr(run, "reinit_method", None) or "ridge_eikonal"),
            reproject_variable_density=getattr(run, "reproject_variable_density", False),
            reproject_mode=getattr(run, "reproject_mode", "legacy"),
            phi_primary_transport=bool(getattr(run, "phi_primary_transport", True)),
            interface_tracking_enabled=bool(getattr(run, "interface_tracking_enabled", True)),
            interface_tracking_method=str(
                getattr(run, "interface_tracking_method", "phi_primary")
            ),
            phi_primary_redist_every=int(getattr(run, "phi_primary_redist_every", 4)),
            phi_primary_clip_factor=float(getattr(run, "phi_primary_clip_factor", 12.0)),
            phi_primary_heaviside_eps_scale=float(
                getattr(run, "phi_primary_heaviside_eps_scale", 1.0)
            ),
            kappa_max=getattr(run, "kappa_max", None),
            dgr_phi_smooth_C=float(getattr(run, "dgr_phi_smooth_C", 0.0)),
            reinit_eps_scale=float(getattr(run, "reinit_eps_scale", 1.0)),
            ridge_sigma_0=float(getattr(run, "ridge_sigma_0", 3.0)),
        ),
        ppe=SolverPPEOptions(
            ppe_solver=str(getattr(run, "ppe_solver", "fccd_iterative")),
            ppe_dc_base_solver=getattr(run, "ppe_dc_base_solver", "fd_direct"),
            pressure_scheme=str(getattr(run, "pressure_scheme", "fccd_matrixfree")),
            ppe_coefficient_scheme=str(
                getattr(run, "ppe_coefficient_scheme", "phase_separated")
            ),
            ppe_interface_coupling_scheme=str(
                getattr(run, "ppe_interface_coupling_scheme", "affine_jump")
            ),
            ppe_iteration_method=str(getattr(run, "ppe_iteration_method", "gmres")),
            ppe_tolerance=float(getattr(run, "ppe_tolerance", 1.0e-8)),
            ppe_max_iterations=int(getattr(run, "ppe_max_iterations", 500)),
            ppe_restart=getattr(run, "ppe_restart", 80),
            ppe_preconditioner=str(getattr(run, "ppe_preconditioner", "none")),
            ppe_pcr_stages=getattr(run, "ppe_pcr_stages", 4),
            ppe_c_tau=float(getattr(run, "ppe_c_tau", 2.0)),
            ppe_defect_correction=bool(getattr(run, "ppe_defect_correction", True)),
            ppe_dc_max_iterations=int(getattr(run, "ppe_dc_max_iterations", 3)),
            ppe_dc_tolerance=float(getattr(run, "ppe_dc_tolerance", 1.0e-8)),
            ppe_dc_relaxation=float(getattr(run, "ppe_dc_relaxation", 0.8)),
        ),
        schemes=SolverSchemeOptions(
            cn_viscous=getattr(run, "cn_viscous", False),
            Re=getattr(physics, "Re", 1.0),
            reinit_steps=4,
            hfe_C=0.05,
            advection_scheme=str(getattr(run, "advection_scheme", "fccd_flux")),
            convection_scheme=str(getattr(run, "convection_scheme", "uccd6")),
            surface_tension_scheme=str(getattr(run, "surface_tension_scheme", "pressure_jump")),
            convection_time_scheme=str(getattr(run, "convection_time_scheme", "imex_bdf2")),
            viscous_spatial_scheme=str(getattr(run, "viscous_spatial_scheme", "ccd_bulk")),
            viscous_time_scheme=str(getattr(run, "viscous_time_scheme", "implicit_bdf2")),
            viscous_solver=str(getattr(run, "viscous_solver", "defect_correction")),
            viscous_solver_tolerance=float(
                getattr(run, "viscous_solver_tolerance", 1.0e-8)
            ),
            viscous_solver_max_iterations=int(
                getattr(run, "viscous_solver_max_iterations", 80)
            ),
            viscous_solver_restart=int(getattr(run, "viscous_solver_restart", 40)),
            viscous_dc_max_iterations=int(getattr(run, "viscous_dc_max_iterations", 3)),
            viscous_dc_relaxation=float(getattr(run, "viscous_dc_relaxation", 0.8)),
            viscous_dc_low_operator=str(
                getattr(run, "viscous_dc_low_operator", "component")
            ),
            cn_mode=str(getattr(run, "cn_mode", "picard")),
            cn_buoyancy_predictor_assembly_mode=str(
                getattr(run, "cn_buoyancy_predictor_assembly_mode", "none")
            ),
            pressure_gradient_scheme=str(
                getattr(run, "pressure_gradient_scheme", "fccd_flux")
            ),
            surface_tension_gradient_scheme=str(
                getattr(run, "surface_tension_gradient_scheme", "none")
            ),
            momentum_gradient_scheme=str(
                getattr(run, "momentum_gradient_scheme", "fccd_flux")
            ),
            uccd6_sigma=float(getattr(run, "uccd6_sigma", 1.0e-3)),
            face_flux_projection=bool(getattr(run, "face_flux_projection", False)),
            canonical_face_state=bool(getattr(run, "canonical_face_state", False)),
            face_native_predictor_state=bool(
                getattr(run, "face_native_predictor_state", False)
            ),
            face_no_slip_boundary_state=bool(
                getattr(run, "face_no_slip_boundary_state", False)
            ),
            preserve_projected_faces=bool(
                getattr(run, "preserve_projected_faces", False)
            ),
            projection_consistent_buoyancy=bool(
                getattr(run, "projection_consistent_buoyancy", False)
            ),
            debug_diagnostics=bool(getattr(run, "debug_diagnostics", False)),
        ),
    )


class NSSolverBuilder:
    """Builder adapter for the modern ``TwoPhaseNSSolver`` pipeline."""

    def __init__(self, cfg: "ExperimentConfig") -> None:
        self._options = build_solver_init_options(cfg)

    def with_debug_diagnostics(self, enabled: bool) -> "NSSolverBuilder":
        """Override debug diagnostics for ad-hoc builds."""
        self._options = replace(
            self._options,
            schemes=replace(self._options.schemes, debug_diagnostics=bool(enabled)),
        )
        return self

    def build_options(self) -> NSSolverInitOptions:
        """Return the current grouped options."""
        return self._options

    def build(self) -> "TwoPhaseNSSolver":
        """Construct a solver from the accumulated options."""
        from .ns_pipeline import TwoPhaseNSSolver

        return TwoPhaseNSSolver.from_options(self._options)
