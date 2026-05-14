"""Two-phase NS pipeline: solver setup + one-step integration.

Provides ``TwoPhaseNSSolver`` — a reusable class that wraps the common
5-stage predictor-corrector used in all §13 experiments.

Conventions
-----------
* ψ = 1 in liquid, ψ = 0 in gas  (CLS conservative level set)
* Buoyancy:  buoy_v = −(ρ − ρ_ref) / ρ × g
* Balanced-force CSF:  f = σ κ ∇ψ  added to both PPE RHS and corrector
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ..ccd.fccd import FCCDSolver
from ..core.boundary import boundary_axes
from ..core.grid_remap import build_grid_remapper
from ..coupling.transport_variational_capillary import p2_trace_surface_energy_2d
from ..levelset.reinitialize import Reinitializer
from ..levelset.wall_contact import WallContactSet
from .ns_step_state import NSStepInputs, NSStepRequest, NSStepState
from .ns_step_services import (
    compute_ns_geometric_surface_tension_stage,
    compute_ns_predictor_stage,
    compute_ns_surface_tension_stage,
    correct_ns_velocity_stage,
    materialise_ns_step_fields,
    record_ns_step_diagnostics,
    solve_ns_pressure_stage,
)
from .conservative_transport import ConservativeCommonFluxTransport
from .interface_projection_diagnostics import (
    reinit_projection_diagnostics,
    zero_reinit_projection_diagnostics,
)
from .geometric_phase_runtime import (
    materialise_geometric_common_flux_state,
    materialise_geometric_runtime_capillary_application_state,
    materialise_geometric_runtime_capillary_state,
    validate_geometric_runtime_capillary_application_admitted,
)
from .geometric_phase_runtime_gpu import (
    build_geometric_phase_state_gpu,
    estimate_geometric_swept_capacity_dt_gpu,
    materialise_geometric_common_flux_state_gpu,
    materialise_geometric_graph_capillary_state_gpu,
    materialise_geometric_runtime_capillary_application_state_gpu,
    materialise_geometric_runtime_capillary_state_gpu,
    project_geometric_phase_state_gpu,
    transport_geometric_phase_common_flux_2d_gpu,
    validate_geometric_runtime_capillary_fail_close_gpu,
)
from .geometric_volume_hodge import (
    GeometricVolumeHodgePolicy,
    build_geometric_volume_metrics,
    close_geometric_volume_flux_boundary,
    geometric_cell_face_shapes,
    geometric_volume_flux_divergence,
    geometric_volume_flux_gradient,
    geometric_volume_flux_projection_diagonal,
    project_geometric_cell_face_velocity,
    project_geometric_volume_flux_pair,
    projection_native_face_shapes,
    solve_geometric_volume_flux_projection_pcg,
)
from . import ns_pipeline_registrations as _ns_pipeline_registrations  # noqa: F401
from .ns_geometry_runtime import build_ns_geometry_runtime
from .ns_grid_rebuild import rebuild_ns_grid
from .ns_ppe_runtime import (
    build_ns_runtime_ppe_cfg_shim,
    build_ns_runtime_ppe_solver,
    build_ns_runtime_plain_ppe_solver,
)
from ..ppe.interfaces import IPPESolver
from .ns_runtime_factories import (
    NSReinitializerFactoryOptions,
    build_ns_reinitializer,
)
from .ns_runtime_config import (
    normalise_ns_interface_runtime,
    normalise_ns_ppe_runtime,
)
from .ns_runtime_binding import (
    bind_ns_interface_runtime,
    bind_ns_ppe_runtime,
)
from .ns_solver_runtime_lifecycle import (
    initialise_ns_solver_from_options,
    reset_ns_runtime_contexts,
)
from .ns_scheme_bootstrap import (
    bind_ns_operator_stack,
    bind_ns_scheme_runtime_artifacts,
    build_ns_scheme_operator_stack,
    build_ns_scheme_runtime_artifacts,
)
from .ns_runtime_services import (
    NSRuntimeSetupContext,
    NSTimestepEstimateContext,
    build_runtime_initial_condition,
    build_runtime_initial_phi,
    build_runtime_initial_velocity,
    compute_runtime_dt_max,
    compute_runtime_timestep_budget,
    make_runtime_boundary_condition_hook,
    psi_from_phi as runtime_psi_from_phi,
)
from .runtime_setup import (
    apply_velocity_bc as _apply_bc,
)
from .ns_solver_options import (
    NSSolverInitOptions,
    SolverGridOptions,
    SolverInterfaceOptions,
    SolverPPEOptions,
    SolverSchemeOptions,
)
from ..geometry import GeometricPhaseState, transport_geometric_phase_common_flux_2d


class TwoPhaseNSSolver:
    """Reusable two-phase NS solver.

    Implements the 5-stage predictor-corrector common to all §13 experiments:

    1. Advect ψ + reinitialize (every ``reinit_every`` steps)
    2. Curvature κ + balanced-force CSF force  (skipped when σ = 0)
    3. NS predictor  (convection + viscous + optional buoyancy)
    4. PPE  (variable-density, balanced-force source)
    5. Velocity corrector

    Parameters
    ----------
    NX, NY : int
    LX, LY : float
    bc_type : {'wall', 'periodic'}
    eps_factor : float   interface thickness  ε = eps_factor × h
    hfe_C : float        InterfaceLimitedFilter coefficient
    reinit_steps : int   inner steps of Reinitializer
    use_gpu : bool | None
    """

    def __init__(
        self,
        NX: int,
        NY: int,
        LX: float,
        LY: float,
        bc_type: str = "wall",
        eps_factor: float = 1.5,
        hfe_C: float = 0.05,
        reinit_steps: int = 4,
        use_gpu: bool | None = None,
        alpha_grid: float = 1.0,
        fitting_axes: tuple[bool, bool] = (True, True),
        fitting_alpha_grid: tuple[float, float] | None = None,
        eps_g_factor: float = 2.0,
        fitting_eps_g_factor: tuple[float, float] | None = None,
        eps_g_cells: float | None = None,
        fitting_eps_g_cells: tuple[float | None, float | None] | None = None,
        dx_min_floor: float = 1e-6,
        fitting_dx_min_floor: tuple[float, float] | None = None,
        use_local_eps: bool = False,
        eps_xi_cells: float | None = None,
        grid_rebuild_freq: int = 1,
        reinit_every: int = 0,
        reinit_trigger_mode: str = "adaptive",
        reinit_threshold: float = 1.10,
        reinit_method: str = "ridge_eikonal",
        cn_viscous: bool = False,
        Re: float = 1.0,
        reproject_variable_density: bool = False,
        reproject_mode: str = "legacy",
        phi_primary_transport: bool = True,
        interface_tracking_enabled: bool = True,
        interface_tracking_method: str | None = None,
        interface_gauge_reconstruction: str = "fixed_stratum",
        phi_primary_redist_every: int = 4,
        phi_primary_clip_factor: float = 12.0,
        phi_primary_heaviside_eps_scale: float = 1.0,
        kappa_max: float | None = None,
        dgr_phi_smooth_C: float = 0.0,
        reinit_eps_scale: float = 1.0,
        ridge_sigma_0: float = 3.0,
        reinit_volume_constraint: str = "diffuse_mass",
        advection_scheme: str = "fccd_flux",
        convection_scheme: str = "uccd6",
        ppe_solver: str = "fccd_iterative",
        ppe_dc_base_solver: str | None = "fd_direct",
        pressure_scheme: str | None = None,
        ppe_coefficient_scheme: str = "phase_separated",
        ppe_interface_coupling_scheme: str = "affine_jump",
        capillary_range_projection: str = "auto",
        capillary_reaction_projection: str = "none",
        pressure_force_contract: str = "raw_compact_gradient",
        scalar_operator_pairing: str = "legacy",
        pressure_history_mode: str = "face_acceleration",
        pressure_history_extrapolation: str = "constant",
        ppe_iteration_method: str = "gmres",
        ppe_tolerance: float = 1.0e-8,
        ppe_max_iterations: int = 500,
        ppe_restart: int | None = 80,
        ppe_preconditioner: str = "none",
        ppe_pcr_stages: int | None = 4,
        ppe_c_tau: float = 2.0,
        ppe_defect_correction: bool = True,
        ppe_dc_max_iterations: int = 3,
        ppe_dc_tolerance: float = 1.0e-8,
        ppe_dc_relaxation: float = 0.8,
        ppe_dc_fail_close: bool = False,
        surface_tension_scheme: str = "pressure_jump",
        capillary_force_source: str = "curvature_jump",
        capillary_closed_interface_endpoint: str = "conservative_psi",
        curvature_method: str = "psi_direct_filtered",
        momentum_form: str = "primitive_velocity",
        convection_time_scheme: str = "imex_bdf2",
        pressure_gradient_scheme: str | None = "fccd_flux",
        surface_tension_gradient_scheme: str | None = "none",
        momentum_gradient_scheme: str = "fccd_flux",
        viscous_spatial_scheme: str = "ccd_bulk",
        viscous_time_scheme: str | None = "implicit_bdf2",
        viscous_solver: str = "defect_correction",
        viscous_solver_tolerance: float = 1.0e-8,
        viscous_solver_max_iterations: int = 80,
        viscous_solver_restart: int = 40,
        viscous_dc_max_iterations: int = 3,
        viscous_dc_relaxation: float = 0.8,
        viscous_dc_low_operator: str = "component",
        cn_mode: str = "picard",
        cn_buoyancy_predictor_assembly_mode: str = "none",
        gravity_formulation: str = "body_acceleration",
        gravity_transport_adjoint: str = "legacy",
        gravity_metric: str = "legacy",
        gravity_hodge_gate: str = "off",
        gravity_work_gate: str = "off",
        uccd6_sigma: float = 1.0e-3,
        face_flux_projection: bool = False,
        canonical_face_state: bool = False,
        face_native_predictor_state: bool = False,
        face_no_slip_boundary_state: bool = False,
        preserve_projected_faces: bool = False,
        boundary_hodge_mode: str = "off",
        boundary_hodge_state_space: str = "full_face",
        boundary_hodge_wall_trace: str = "reconstruct_nodes",
        boundary_hodge_wall_retraction: str = "metric_projection",
        boundary_hodge_metric: str = "transported_face_mass",
        boundary_hodge_pressure_pairing: str = "active_variational_adjoint",
        boundary_hodge_solver: str = "matrix_free_cg",
        boundary_hodge_tolerance: float = 1.0e-10,
        boundary_hodge_max_iterations: int = 80,
        boundary_hodge_gate: str = "diagnostic",
        projection_consistent_buoyancy: bool = False,
        debug_diagnostics: bool = False,
    ) -> None:
        options = NSSolverInitOptions(
            grid=SolverGridOptions(
                NX=NX,
                NY=NY,
                LX=LX,
                LY=LY,
                bc_type=bc_type,
                use_gpu=use_gpu,
                alpha_grid=alpha_grid,
                fitting_axes=fitting_axes,
                fitting_alpha_grid=(
                    fitting_alpha_grid
                    if fitting_alpha_grid is not None
                    else tuple(alpha_grid if axis else 1.0 for axis in fitting_axes)
                ),
                eps_factor=eps_factor,
                eps_g_factor=eps_g_factor,
                fitting_eps_g_factor=(
                    fitting_eps_g_factor
                    if fitting_eps_g_factor is not None
                    else (eps_g_factor, eps_g_factor)
                ),
                eps_g_cells=eps_g_cells,
                fitting_eps_g_cells=(
                    fitting_eps_g_cells
                    if fitting_eps_g_cells is not None
                    else (eps_g_cells, eps_g_cells)
                ),
                dx_min_floor=dx_min_floor,
                fitting_dx_min_floor=(
                    fitting_dx_min_floor
                    if fitting_dx_min_floor is not None
                    else (dx_min_floor, dx_min_floor)
                ),
                use_local_eps=use_local_eps,
                eps_xi_cells=eps_xi_cells,
            ),
            interface=SolverInterfaceOptions(
                grid_rebuild_freq=grid_rebuild_freq,
                reinit_every=reinit_every,
                reinit_trigger_mode=reinit_trigger_mode,
                reinit_threshold=reinit_threshold,
                reinit_method=reinit_method,
                reproject_variable_density=reproject_variable_density,
                reproject_mode=reproject_mode,
                phi_primary_transport=phi_primary_transport,
                interface_tracking_enabled=interface_tracking_enabled,
                interface_tracking_method=interface_tracking_method,
                interface_gauge_reconstruction=interface_gauge_reconstruction,
                phi_primary_redist_every=phi_primary_redist_every,
                phi_primary_clip_factor=phi_primary_clip_factor,
                phi_primary_heaviside_eps_scale=phi_primary_heaviside_eps_scale,
                kappa_max=kappa_max,
                dgr_phi_smooth_C=dgr_phi_smooth_C,
                reinit_eps_scale=reinit_eps_scale,
                ridge_sigma_0=ridge_sigma_0,
                reinit_volume_constraint=reinit_volume_constraint,
            ),
            ppe=SolverPPEOptions(
                ppe_solver=ppe_solver,
                ppe_dc_base_solver=ppe_dc_base_solver,
                pressure_scheme=pressure_scheme,
                ppe_coefficient_scheme=ppe_coefficient_scheme,
                ppe_interface_coupling_scheme=ppe_interface_coupling_scheme,
                capillary_range_projection=capillary_range_projection,
                capillary_reaction_projection=capillary_reaction_projection,
                pressure_force_contract=pressure_force_contract,
                scalar_operator_pairing=scalar_operator_pairing,
                pressure_history_mode=pressure_history_mode,
                pressure_history_extrapolation=pressure_history_extrapolation,
                ppe_iteration_method=ppe_iteration_method,
                ppe_tolerance=ppe_tolerance,
                ppe_max_iterations=ppe_max_iterations,
                ppe_restart=ppe_restart,
                ppe_preconditioner=ppe_preconditioner,
                ppe_pcr_stages=ppe_pcr_stages,
                ppe_c_tau=ppe_c_tau,
                ppe_defect_correction=ppe_defect_correction,
                ppe_dc_max_iterations=ppe_dc_max_iterations,
                ppe_dc_tolerance=ppe_dc_tolerance,
                ppe_dc_relaxation=ppe_dc_relaxation,
                ppe_dc_fail_close=ppe_dc_fail_close,
            ),
            schemes=SolverSchemeOptions(
                hfe_C=hfe_C,
                reinit_steps=reinit_steps,
                cn_viscous=cn_viscous,
                Re=Re,
                surface_tension_scheme=surface_tension_scheme,
                capillary_force_source=capillary_force_source,
                capillary_closed_interface_endpoint=capillary_closed_interface_endpoint,
                curvature_method=curvature_method,
                momentum_form=momentum_form,
                convection_time_scheme=convection_time_scheme,
                advection_scheme=advection_scheme,
                convection_scheme=convection_scheme,
                pressure_gradient_scheme=pressure_gradient_scheme,
                surface_tension_gradient_scheme=surface_tension_gradient_scheme,
                momentum_gradient_scheme=momentum_gradient_scheme,
                viscous_spatial_scheme=viscous_spatial_scheme,
                viscous_time_scheme=(
                    viscous_time_scheme
                    or ("crank_nicolson" if cn_viscous else "implicit_bdf2")
                ),
                viscous_solver=viscous_solver,
                viscous_solver_tolerance=viscous_solver_tolerance,
                viscous_solver_max_iterations=viscous_solver_max_iterations,
                viscous_solver_restart=viscous_solver_restart,
                viscous_dc_max_iterations=viscous_dc_max_iterations,
                viscous_dc_relaxation=viscous_dc_relaxation,
                viscous_dc_low_operator=viscous_dc_low_operator,
                cn_mode=cn_mode,
                cn_buoyancy_predictor_assembly_mode=cn_buoyancy_predictor_assembly_mode,
                gravity_formulation=gravity_formulation,
                gravity_transport_adjoint=gravity_transport_adjoint,
                gravity_metric=gravity_metric,
                gravity_hodge_gate=gravity_hodge_gate,
                gravity_work_gate=gravity_work_gate,
                uccd6_sigma=uccd6_sigma,
                face_flux_projection=face_flux_projection,
                canonical_face_state=canonical_face_state,
                face_native_predictor_state=face_native_predictor_state,
                face_no_slip_boundary_state=face_no_slip_boundary_state,
                preserve_projected_faces=preserve_projected_faces,
                boundary_hodge_mode=boundary_hodge_mode,
                boundary_hodge_state_space=boundary_hodge_state_space,
                boundary_hodge_wall_trace=boundary_hodge_wall_trace,
                boundary_hodge_wall_retraction=boundary_hodge_wall_retraction,
                boundary_hodge_metric=boundary_hodge_metric,
                boundary_hodge_pressure_pairing=boundary_hodge_pressure_pairing,
                boundary_hodge_solver=boundary_hodge_solver,
                boundary_hodge_tolerance=boundary_hodge_tolerance,
                boundary_hodge_max_iterations=boundary_hodge_max_iterations,
                boundary_hodge_gate=boundary_hodge_gate,
                projection_consistent_buoyancy=projection_consistent_buoyancy,
                debug_diagnostics=debug_diagnostics,
            ),
        )
        self._initialise_from_options(options)

    @classmethod
    def from_options(cls, options: NSSolverInitOptions) -> "TwoPhaseNSSolver":
        """Construct a solver from grouped init options."""
        solver = cls.__new__(cls)
        solver._initialise_from_options(options)
        return solver

    def _initialise_from_options(self, options: NSSolverInitOptions) -> None:
        """Initialise the solver from grouped options."""
        initialise_ns_solver_from_options(self, options)

    def _initialise_geometry(self, options: SolverGridOptions) -> None:
        """Initialise grid geometry and backend state."""
        state = build_ns_geometry_runtime(options)
        self.NX, self.NY = state.NX, state.NY
        self.LX, self.LY = state.LX, state.LY
        self.bc_type = state.bc_type
        self._alpha_grid = state.alpha_grid
        self._eps_factor = state.eps_factor
        self._eps_xi_cells = state.eps_xi_cells
        self._use_local_eps = state.use_local_eps
        self._h = state.h
        self._eps = state.eps
        self._backend = state.backend
        self._grid = state.grid
        self._ccd = state.ccd
        self._wall_contacts = WallContactSet.empty()
        reset_ns_runtime_contexts(self)

    def _initialise_interface_runtime(self, options: SolverInterfaceOptions) -> None:
        """Normalise interface-tracking and remap controls."""
        state = normalise_ns_interface_runtime(options)
        bind_ns_interface_runtime(self, state)

    def _initialise_ppe_runtime(
        self,
        options: SolverPPEOptions,
        *,
        surface_tension_scheme: str,
    ) -> None:
        """Normalise PPE configuration and validate coupled options."""
        state = normalise_ns_ppe_runtime(
            options,
            surface_tension_scheme=surface_tension_scheme,
            ppe_aliases=IPPESolver._aliases,
            ppe_registry=IPPESolver._registry,
        )
        bind_ns_ppe_runtime(self, state)

    def _initialise_scheme_runtime(self, options: SolverSchemeOptions) -> None:
        """Normalise scheme selections and stateful time-integration flags."""
        artifacts = build_ns_scheme_runtime_artifacts(
            backend=self._backend,
            ccd=self._ccd,
            eps=self._eps,
            use_local_eps=self._use_local_eps,
            alpha_grid=self._alpha_grid,
            make_eps_field=self._make_eps_field,
            options=options,
        )
        bind_ns_scheme_runtime_artifacts(self, artifacts)

    def _initialise_operator_stack(
        self,
        grid_options: SolverGridOptions,
        scheme_options: SolverSchemeOptions,
    ) -> None:
        """Build spatial operators and solver strategies."""
        stack = build_ns_scheme_operator_stack(
            backend=self._backend,
            grid=self._grid,
            ccd=self._ccd,
            grid_options=grid_options,
            scheme_options=scheme_options,
            interface_runtime=self._interface_runtime,
            ppe_runtime=self._ppe_runtime,
            scheme_runtime=self._scheme_runtime,
        )
        bind_ns_operator_stack(self, stack)

    def _build_reinitializer(
        self,
        interface_options: SolverInterfaceOptions,
        scheme_options: SolverSchemeOptions,
    ) -> Reinitializer:
        """Build the level-set reinitializer."""
        return build_ns_reinitializer(
            backend=self._backend,
            grid=self._grid,
            ccd=self._ccd,
            eps=self._eps,
            options=NSReinitializerFactoryOptions(
                reinit_steps=scheme_options.reinit_steps,
                reinit_method=interface_options.reinit_method,
                dgr_phi_smooth_C=interface_options.dgr_phi_smooth_C,
                reinit_eps_scale=self._interface_runtime.reinit_eps_scale,
                ridge_sigma_0=float(interface_options.ridge_sigma_0),
                reinit_volume_constraint=interface_options.reinit_volume_constraint,
            ),
        )

    def _build_ppe_solver(self, pressure_scheme: str):
        """Instantiate the PPE solver selected by ``pressure_scheme``.

        ch13 pipeline supports:
          * 'fvm_spsolve'    : sparse FVM direct solve (production default)
          * 'fvm_matrixfree' : matrix-free FVM + line-preconditioned GMRES
                               (needs SimulationConfig; synthesised below)
          * 'fccd_matrixfree': matrix-free FCCD face-flux GMRES

        CCD-based PPE solvers ('ccd_lu', 'iim') hit the rank-deficient
        Neumann nullspace documented in WIKI-X-004 / WIKI-T-016; they are
        available via the SimulationBuilder pipeline (builder.py) but are
        disabled here to prevent silent divergence in two-phase runs.
        """
        return build_ns_runtime_ppe_solver(
            backend=self._backend,
            grid=self._grid,
            bc_type=self.bc_type,
            fccd=self._fccd,
            state=self._ppe_runtime,
            pressure_scheme=pressure_scheme,
        )

    def _build_plain_ppe_solver(self, ppe_scheme: str):
        """Instantiate an unwrapped PPE solver via registry."""
        return build_ns_runtime_plain_ppe_solver(
            backend=self._backend,
            grid=self._grid,
            bc_type=self.bc_type,
            fccd=self._fccd,
            state=self._ppe_runtime,
            ppe_scheme=ppe_scheme,
        )

    def _build_ppe_cfg_shim(
        self,
        *,
        preconditioner: str | None = None,
        pcr_stages: int | None = None,
    ):
        """Build the SimpleNamespace config shim for PPESolverFVMMatrixFree."""
        return build_ns_runtime_ppe_cfg_shim(
            self._ppe_runtime,
            preconditioner=preconditioner,
            pcr_stages=pcr_stages,
        )

    # ── class-method constructors ─────────────────────────────────────────

    @classmethod
    def from_config(cls, cfg: "ExperimentConfig") -> "TwoPhaseNSSolver":
        """Construct from an :class:`ExperimentConfig` via builder adapter."""
        from .ns_solver_builder import NSSolverBuilder

        return NSSolverBuilder(cfg).build()

    # ── properties ────────────────────────────────────────────────────────

    @property
    def h(self) -> float:
        return self._h

    @property
    def eps(self) -> float:
        return self._eps

    @property
    def backend(self):
        return self._backend

    @property
    def h_min(self) -> float:
        """Minimum local grid spacing (accounts for non-uniform refinement)."""
        return float(min(
            self._grid.h[ax].min() for ax in range(self._grid.ndim)
        ))

    @property
    def reproject_stats(self) -> dict:
        """Return counters for reprojection mode diagnostics."""
        return self._reprojector.stats

    def _make_eps_field(self):
        """ε(x) at each node — ξ空間で一定セル数の平滑化幅.

        eps_xi_cells モード: ε(i,j) = eps_xi_cells · max(h_x(i), h_y(j))
        従来モード:          ε(i,j) = eps_factor  · max(h_x(i), h_y(j))

        Returns a device-native array in ``backend.xp`` so it can be
        multiplied against device fields in the hot loop without any
        host↔device traffic.
        """
        xp = self._backend.xp
        hx = xp.asarray(self._grid.h[0])[:, None]
        hy = xp.asarray(self._grid.h[1])[None, :]
        factor = self._eps_xi_cells if self._eps_xi_cells is not None else self._eps_factor
        return factor * xp.maximum(hx, hy)

    # ── grid rebuild ─────────────────────────────────────────────────────

    def _rebuild_grid(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        rho_l: float | None = None,
        rho_g: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Rebuild interface-fitted grid and remap fields.

        No-op when ``alpha_grid <= 1.0``.

        Returns remapped (psi, u, v).
        """
        result = rebuild_ns_grid(
            backend=self._backend,
            grid=self._grid,
            ccd=self._ccd,
            eps=self._eps,
            alpha_grid=self._alpha_grid,
            psi=psi,
            u=u,
            v=v,
            rho_l=rho_l,
            rho_g=rho_g,
            use_local_eps=self._use_local_eps,
            curvature_operator=self._curv,
            make_eps_field=self._make_eps_field,
            reinitializer=self._reinit,
            ppe_solver=self._ppe_solver,
            fccd_div_op=self._fccd_div_op,
            div_op=self._div_op,
            ppe_runtime=self._ppe_runtime,
            reprojector=self._reprojector,
            wall_contacts=self._wall_contacts,
            projected_face_components=self._projected_face_components,
            bc_type=self.bc_type,
            face_no_slip_boundary_state=self._face_no_slip_boundary_state,
        )
        self._finalize_grid_rebuild(result)
        return result.psi, result.u, result.v

    def _rebuild_grid_conservative(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Rebuild grid while remapping conservative ``q`` and ``rho u``."""
        result = rebuild_ns_grid(
            backend=self._backend,
            grid=self._grid,
            ccd=self._ccd,
            eps=self._eps,
            alpha_grid=self._alpha_grid,
            psi=state.psi,
            u=state.u,
            v=state.v,
            rho_l=state.rho_l,
            rho_g=state.rho_g,
            use_local_eps=self._use_local_eps,
            curvature_operator=self._curv,
            make_eps_field=self._make_eps_field,
            reinitializer=self._reinit,
            ppe_solver=self._ppe_solver,
            fccd_div_op=self._fccd_div_op,
            div_op=self._div_op,
            ppe_runtime=self._ppe_runtime,
            reprojector=self._reprojector,
            wall_contacts=self._wall_contacts,
            conservative_momentum_components=state.conservative_momentum_components,
            projected_face_components=state.projected_face_components,
            bc_type=self.bc_type,
            face_no_slip_boundary_state=self._face_no_slip_boundary_state,
        )
        self._finalize_grid_rebuild(result)
        state.psi = result.psi
        state.u = result.u
        state.v = result.v
        state.rho = result.density
        state.conservative_density = result.density
        state.conservative_momentum_components = list(result.momentum_components or ())
        self._conservative_density = result.density
        self._conservative_momentum_components = state.conservative_momentum_components
        return state

    def _finalize_grid_rebuild(self, result) -> None:
        """Refresh grid-dependent solver history after any grid rebuild."""
        self.X, self.Y = result.X, result.Y
        self._p_prev = None
        self._p_prev_dev = None
        self._p_base_prev_dev = None
        self._p_prev_accel_face_components = None
        self._projected_face_components = result.projected_face_components
        self._conv_prev = None
        self._conv_ab2_ready = False
        self._velocity_prev = None
        self._velocity_bdf2_ready = False
        reset_ns_runtime_contexts(self)
        self._refresh_geometric_phase_state_after_grid_rebuild(result.psi)

    def _build_geometric_phase_state_for_current_grid(
        self,
        phi,
        *,
        boundary: tuple[str, str] | None = None,
    ):
        """Build AO state on the current grid and restore its configured gauge."""
        base = (
            build_geometric_phase_state_gpu(self._grid, phi)
            if self._backend.is_gpu()
            else GeometricPhaseState.from_phi(self._grid, phi)
        )
        active_boundary = (
            boundary
            if boundary is not None
            else boundary_axes(self.bc_type, self._grid.ndim)
        )
        if not self._geometric_graph_gauge_reconstruction_enabled(active_boundary):
            return base
        graph_phi = self._graph_phi_from_column_volume(base.q)
        return self._project_geometric_state_from_q_phi(
            base.q,
            graph_phi,
            level=base.stratum.level,
        )

    def _refresh_geometric_phase_state_after_grid_rebuild(self, psi) -> None:
        """Keep AO cell-volume geometry tied to the rebuilt grid metric."""
        if (
            getattr(self, "_geometric_phase_state", None) is None
            or self._alpha_grid <= 1.0
        ):
            return
        context = self._runtime_setup_context()
        phi = -context.reconstruct_base.phi_from_psi(psi)
        self._geometric_phase_state = (
            self._build_geometric_phase_state_for_current_grid(phi)
        )

    # ── initial condition / velocity builders ─────────────────────────────

    def psi_from_phi(self, phi: np.ndarray) -> np.ndarray:
        """Smooth Heaviside ψ = H_ε(φ)."""
        return runtime_psi_from_phi(self._runtime_setup_context(), phi)

    def set_wall_contacts(self, wall_contacts) -> None:
        """Attach no-slip wall-contact constraints to geometry services."""
        self._wall_contacts = wall_contacts or WallContactSet.empty()
        if hasattr(self._reinit, "set_wall_contacts"):
            self._reinit.set_wall_contacts(self._wall_contacts)

    def build_ic(self, cfg: "ExperimentConfig") -> np.ndarray:
        """Build initial ψ field from config ``initial_condition`` section.

        Accepts three YAML formats:

        1. **Builder format** (explicit primitives)::

               initial_condition:
                 background_phase: liquid
                 shapes: [{type: circle, ...}]

        2. **Object format** (experiment-facing)::

               initial_condition:
                 background_phase: liquid
                 objects: [{type: bubble, center: [0.5, 0.5], radius: 0.25}]

        3. **Single-shape shorthand**::

               initial_condition:
                 type: circle
                 center: [0.5, 0.5]
                 radius: 0.25
                 interior_phase: gas

        4. **Union shorthand** (multiple shapes, same background)::

               initial_condition:
                 type: union
                 shapes: [{type: circle, interior_phase: gas, ...}, ...]
        """
        self._last_geometric_common_flux_transport = None
        self._last_geometric_runtime_material = None
        self._last_geometric_runtime_capillary = None
        self._last_geometric_runtime_capillary_application = None
        context = self._runtime_setup_context()
        psi = build_runtime_initial_condition(
            context,
            cfg.initial_condition,
        )
        state_space = getattr(cfg, "interface_state_space", None)
        if getattr(state_space, "kind", "diffuse_cls") == "geometric_cell_fraction":
            phi = build_runtime_initial_phi(context, cfg.initial_condition)
            self._geometric_phase_state = (
                build_geometric_phase_state_gpu(self._grid, phi)
                if self._backend.is_gpu()
                else GeometricPhaseState.from_phi(
                    self._grid,
                    phi,
                )
            )
        else:
            self._geometric_phase_state = None
        return psi

    def build_velocity(
        self, cfg: "ExperimentConfig", psi: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build initial (u, v) from config ``initial_velocity`` section.

        If ``initial_velocity`` is absent, returns zero fields.  The section may
        name one velocity primitive or a ``base`` plus ``perturbations`` list.
        """
        return build_runtime_initial_velocity(
            self._runtime_setup_context(),
            cfg.initial_velocity,
        )

    # ── boundary-condition hook factory ──────────────────────────────────

    def make_bc_hook(self, cfg: "ExperimentConfig"):
        """Return a ``bc_hook(u, v)`` callable from config.

        * ``None`` → periodic (no-op)
        * default wall → zeros all 4 boundaries
        * ``boundary_condition.type == 'couette'`` → Couette shear
        """
        return make_runtime_boundary_condition_hook(
            self._runtime_setup_context(),
            cfg.boundary_condition,
        )

    # ── stable-timestep estimate ──────────────────────────────────────────

    def dt_max(
        self,
        u: np.ndarray,
        v: np.ndarray,
        physics: "PhysicsCfg",
        cfl: float = 0.15,
        *,
        cfl_advective: float | None = None,
        cfl_capillary: float | None = None,
        cfl_viscous: float = 1.0,
    ) -> float:
        """CFL + viscous + capillary timestep limit."""
        return compute_runtime_dt_max(
            self._runtime_timestep_context(),
            u,
            v,
            physics,
            cfl=cfl,
            cfl_advective=cfl_advective,
            cfl_capillary=cfl_capillary,
            cfl_viscous=cfl_viscous,
        )

    def dt_budget(
        self,
        u: np.ndarray,
        v: np.ndarray,
        physics: "PhysicsCfg",
        cfl: float = 0.15,
        *,
        cfl_advective: float | None = None,
        cfl_capillary: float | None = None,
        cfl_viscous: float = 1.0,
    ):
        """Return per-operator timestep candidates and active limiter."""
        budget = compute_runtime_timestep_budget(
            self._runtime_timestep_context(),
            u,
            v,
            physics,
            cfl=cfl,
            cfl_advective=cfl_advective,
            cfl_capillary=cfl_capillary,
            cfl_viscous=cfl_viscous,
        )
        return self._with_geometric_capacity_dt_budget(
            budget,
            u,
            v,
        )

    def _with_geometric_capacity_dt_budget(self, budget, u, v):
        """Admit the AO swept-volume invariant-domain timestep when active."""
        phase_state = getattr(self, "_geometric_phase_state", None)
        if (
            not self._geometric_phase_runtime_enabled()
            or phase_state is None
            or not self._backend.is_gpu()
            or not np.isfinite(budget.dt)
            or budget.dt <= 0.0
        ):
            return budget
        xp = self._backend.xp
        boundary = boundary_axes(self.bc_type, self._grid.ndim)
        face_velocity = self._nodal_velocity_to_geometric_cell_faces(
            xp.asarray(u),
            xp.asarray(v),
            boundary=boundary,
        )
        capacity_dt = estimate_geometric_swept_capacity_dt_gpu(
            self._grid,
            phase_state,
            face_velocity,
            dt_upper=budget.dt,
            boundary=boundary,
            tolerance=self._active_projection_absolute_tolerance,
        )
        if capacity_dt <= 0.0:
            raise ValueError(
                "GPU AO geometric-capacity timestep fail-close: no positive "
                "timestep preserves donor/receiver cell-volume bounds"
            )
        if capacity_dt < budget.dt:
            return replace(
                budget,
                dt=capacity_dt,
                limiter="geometric_capacity",
                dt_geometric_capacity=capacity_dt,
            )
        return replace(budget, dt_geometric_capacity=capacity_dt)

    def _runtime_setup_context(self) -> NSRuntimeSetupContext:
        """Build the convenience-service context for setup-facing helpers."""
        if self._runtime_setup_ctx is None:
            self._runtime_setup_ctx = NSRuntimeSetupContext(
                backend=self._backend,
                grid=self._grid,
                eps=self._eps,
                X=self.X,
                Y=self.Y,
                LY=self.LY,
                bc_type=self.bc_type,
                reconstruct_base=self._reconstruct_base,
            )
        return self._runtime_setup_ctx

    def _runtime_timestep_context(self) -> NSTimestepEstimateContext:
        """Build the timestep-estimation context for runtime services."""
        if self._runtime_timestep_ctx is None:
            h_axes = tuple(
                float(self._grid.h[ax].min())
                for ax in range(self._grid.ndim)
            )
            self._runtime_timestep_ctx = NSTimestepEstimateContext(
                backend=self._backend,
                h=self._h,
                h_min=self.h_min,
                alpha_grid=self._alpha_grid,
                cn_viscous=self._cn_viscous,
                viscous_time_scheme=self._viscous_time_scheme,
                h_axes=h_axes,
            )
        return self._runtime_timestep_ctx

    def _prepare_step_inputs(
        self,
        inputs: NSStepInputs | NSStepRequest,
    ) -> NSStepState:
        """Promote step inputs to the active backend and normalise ``rho_ref``."""
        state = NSStepState.from_inputs(inputs, backend=self._backend)
        if self._p_prev_dev is not None:
            state.previous_pressure = self._backend.xp.asarray(self._p_prev_dev)
        if self._p_base_prev_dev is not None:
            state.previous_base_pressure = self._backend.xp.asarray(
                self._p_base_prev_dev
            )
        if getattr(self, "_p_base_prev2_dev", None) is not None:
            state.previous_previous_base_pressure = self._backend.xp.asarray(
                self._p_base_prev2_dev
            )
        if self._p_prev_accel_face_components is not None:
            state.previous_pressure_accel_face_components = [
                self._backend.xp.asarray(component)
                for component in self._p_prev_accel_face_components
            ]
        if (
            (self._canonical_face_state or self._preserve_projected_faces)
            and self._projected_face_components is not None
            and hasattr(self._div_op, "reconstruct_nodes")
        ):
            projected_faces = [
                self._backend.xp.asarray(component)
                for component in self._projected_face_components
            ]
            if not self._geometric_phase_runtime_enabled():
                state.face_velocity_components = projected_faces
            state.projected_face_components = projected_faces
            state.u, state.v = self._div_op.reconstruct_nodes(
                projected_faces
            )
            _apply_bc(state.u, state.v, state.bc_hook, self.bc_type)
        if (
            self._conservative_common_flux_enabled()
            and not self._geometric_phase_runtime_enabled()
        ):
            density = getattr(self, "_conservative_density", None)
            momentum = getattr(self, "_conservative_momentum_components", None)
            if density is not None:
                state.conservative_density = self._backend.xp.asarray(density)
            if momentum is not None:
                state.conservative_momentum_components = [
                    self._backend.xp.asarray(component) for component in momentum
                ]
        return state

    def _conservative_common_flux_enabled(self) -> bool:
        return getattr(self, "_momentum_form", "primitive_velocity") == (
            "conservative_common_flux"
        )

    def _geometric_phase_runtime_enabled(self) -> bool:
        return getattr(self, "_advection_scheme", "") == "geometric_swept_volume"

    def _geometric_phase_grid_rebuild_due(self, step_index: int) -> bool:
        """Return whether AO-owned geometry should refresh the fitted grid."""
        return (
            self._geometric_phase_runtime_enabled()
            and self._alpha_grid > 1.0
            and self._interface_runtime.rebuild_freq > 0
            and int(step_index) > 0
            and int(step_index) % self._interface_runtime.rebuild_freq == 0
        )

    def _pressure_coordinate_history_enabled(self) -> bool:
        """Return whether pressure history can be regenerated on a new grid."""
        return str(
            getattr(self._ppe_runtime, "pressure_history_mode", "face_acceleration")
        ).strip().lower() == "pressure_coordinate"

    def prepare_geometric_grid_for_timestep(
        self,
        psi,
        u,
        v,
        *,
        dt: float,
        rho_l: float,
        rho_g: float,
        sigma: float,
        mu: float,
        g_acc: float,
        rho_ref: float,
        mu_l: float,
        mu_g: float,
        bc_hook,
        step_index: int,
    ):
        """Apply beginning-of-step AO grid rebuild before timestep selection."""
        if not self._geometric_phase_grid_rebuild_due(step_index):
            return psi, u, v, False
        if not self._pressure_coordinate_history_enabled():
            raise ValueError(
                "geometric_cell_fraction interface-following grid rebuild "
                "requires pressure_history.form='pressure_coordinate'; "
                "face-acceleration pressure history is a metric-complex "
                "cochain and cannot be reused after grid rebuild"
            )
        state = NSStepState.from_inputs(
            NSStepInputs(
                psi=psi,
                u=u,
                v=v,
                dt=dt,
                rho_l=rho_l,
                rho_g=rho_g,
                sigma=sigma,
                mu=mu,
                g_acc=g_acc,
                rho_ref=rho_ref,
                mu_l=mu_l,
                mu_g=mu_g,
                bc_hook=bc_hook,
                step_index=step_index,
            ),
            backend=self._backend,
        )
        if (
            (self._canonical_face_state or self._preserve_projected_faces)
            and self._projected_face_components is not None
        ):
            state.projected_face_components = [
                self._backend.xp.asarray(component)
                for component in self._projected_face_components
            ]
        rebuilt = self._rebuild_grid_from_geometric_phase_state(state)
        self._prepared_geometric_grid_rebuild_step = int(step_index)
        return rebuilt.psi, rebuilt.u, rebuilt.v, True

    def _rebuild_grid_from_geometric_phase_state(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Fit the tensor grid to AO geometry without replacing q by ψ data."""
        phase_state = getattr(self, "_geometric_phase_state", None)
        if phase_state is None:
            return state
        xp = self._backend.xp
        old_coords = [coords.copy() for coords in self._grid.coords]
        old_phi = xp.asarray(phase_state.phi)
        remap_pressure_coordinate_history = self._pressure_coordinate_history_enabled()
        old_p_prev = self._p_prev_dev if remap_pressure_coordinate_history else None
        old_p_base_prev = (
            self._p_base_prev_dev if remap_pressure_coordinate_history else None
        )
        old_p_base_prev2 = (
            getattr(self, "_p_base_prev2_dev", None)
            if remap_pressure_coordinate_history
            else None
        )
        context = self._runtime_setup_context()
        state.psi = context.reconstruct_base.psi_from_phi(-old_phi)
        state.rho = xp.asarray(
            state.rho_g
            + (state.rho_l - state.rho_g)
            * self._geometric_cell_to_node_view(phase_state.theta)
        )
        state.conservative_density = state.rho
        state.conservative_momentum_components = [
            state.rho * xp.asarray(state.u),
            state.rho * xp.asarray(state.v),
        ]
        state = self._rebuild_grid_conservative(state)
        # Face cochains are metric-complex objects.  The rebuild path may only
        # keep them after explicitly remapping them on face coordinates and
        # reprojecting them in the new Hodge metric.
        state.face_velocity_components = None
        remapper = build_grid_remapper(self._backend, old_coords, self._grid.coords)
        if remap_pressure_coordinate_history:
            # Physical affine-jump pressure is discontinuous and cannot be
            # remapped across a rebuilt interface-fitted grid.  The base
            # history below is stored in the reduced smooth HFE coordinate.
            self._p_prev_dev = None
            self._p_prev = None
            self._p_base_prev_dev = (
                None
                if old_p_base_prev is None
                else xp.asarray(remapper.remap(old_p_base_prev))
            )
            self._p_base_prev2_dev = (
                None
                if old_p_base_prev2 is None
                else xp.asarray(remapper.remap(old_p_base_prev2))
            )
        phi = remapper.remap(old_phi)
        self._geometric_phase_state = (
            self._build_geometric_phase_state_for_current_grid(
                phi,
                boundary=boundary_axes(self.bc_type, self._grid.ndim),
            )
        )
        state.projected_face_components = self._projected_face_components
        state.psi = self._geometric_cell_to_node_view(
            self._geometric_phase_state.theta
        )
        state.rho = xp.asarray(
            state.rho_g + (state.rho_l - state.rho_g) * state.psi
        )
        state.conservative_density = state.rho
        state.conservative_momentum_components = [
            state.rho * xp.asarray(state.u),
            state.rho * xp.asarray(state.v),
        ]
        return state

    def _face_velocity_for_common_flux(self, state: NSStepState):
        """Return projection-native face velocities for common-flux transport."""
        xp = self._backend.xp
        if state.face_velocity_components is not None:
            return [xp.asarray(component) for component in state.face_velocity_components]
        if hasattr(self._div_op, "face_fluxes"):
            return [
                xp.asarray(component)
                for component in self._div_op.face_fluxes([state.u, state.v])
            ]
        raise RuntimeError(
            "conservative_common_flux requires projection-native face velocities"
        )

    def _geometric_face_velocity_for_common_flux(self, state: NSStepState):
        """Return geometric cell-face normal velocities for AO swept transport."""
        xp = self._backend.xp
        nx, ny = int(self._grid.N[0]), int(self._grid.N[1])
        boundary = boundary_axes(self.bc_type, self._grid.ndim)
        geometric_shapes = geometric_cell_face_shapes((nx, ny))
        projection_shapes = projection_native_face_shapes((nx, ny))
        if state.face_velocity_components is not None:
            supplied = [
                xp.asarray(component) for component in state.face_velocity_components
            ]
            supplied_shapes = tuple(tuple(component.shape) for component in supplied)
            if supplied_shapes == geometric_shapes:
                return self._project_geometric_cell_face_velocity(
                    supplied,
                    dt=state.dt,
                    boundary=boundary,
                )
            if supplied_shapes == projection_shapes:
                return self._project_projection_faces_to_geometric_cell_faces(
                    supplied,
                    dt=state.dt,
                    boundary=boundary,
                )
            raise RuntimeError(
                "geometric_cell_fraction runtime transport requires either "
                f"geometric cell-face velocity shapes {geometric_shapes!r} or "
                f"projection-native face shapes {projection_shapes!r}; "
                f"got {supplied_shapes!r}"
            )
        if state.projected_face_components is not None:
            projected = [
                xp.asarray(component) for component in state.projected_face_components
            ]
            projected_shapes = tuple(tuple(component.shape) for component in projected)
            if projected_shapes != projection_shapes:
                raise RuntimeError(
                    "geometric_cell_fraction projected face state must have "
                    f"projection-native shapes {projection_shapes!r}; "
                    f"got {projected_shapes!r}"
                )
            return self._project_projection_faces_to_geometric_cell_faces(
                projected,
                dt=state.dt,
                boundary=boundary,
            )
        u = xp.asarray(state.u)
        v = xp.asarray(state.v)
        nodal_shape = (nx + 1, ny + 1)
        if tuple(u.shape) != nodal_shape or tuple(v.shape) != nodal_shape:
            raise RuntimeError(
                "geometric_cell_fraction runtime transport requires nodal "
                "velocities or geometric cell-face velocities"
            )
        x_faces, y_faces = self._nodal_velocity_to_geometric_cell_faces(
            u,
            v,
            boundary=boundary,
        )
        return self._project_geometric_cell_face_velocity(
            [x_faces, y_faces],
            dt=state.dt,
            boundary=boundary,
        )

    def _project_projection_faces_to_geometric_cell_faces(
        self,
        projection_faces,
        *,
        dt: float,
        boundary: tuple[str, str],
    ):
        """Explicitly pull projection-native faces back to AO cell faces."""
        if not hasattr(self._div_op, "reconstruct_nodes"):
            raise RuntimeError(
                "geometric_cell_fraction projection-face pullback requires "
                "a divergence operator with reconstruct_nodes"
            )
        u, v = self._div_op.reconstruct_nodes(projection_faces)
        _apply_bc(u, v, None, self.bc_type)
        x_faces, y_faces = self._nodal_velocity_to_geometric_cell_faces(
            u,
            v,
            boundary=boundary,
        )
        # Projection-native incompressibility is not a commuting certificate on
        # the moving geometric cell-face complex.  Transfer through the
        # finite-volume Hodge projector so q transport consumes a closed volume
        # cochain on its own nonuniform grid.
        return self._project_geometric_cell_face_velocity(
            [x_faces, y_faces],
            dt=dt,
            boundary=boundary,
        )

    def _nodal_velocity_to_geometric_cell_faces(
        self,
        u,
        v,
        *,
        boundary: tuple[str, str],
    ):
        """Map nodal vector components to AO geometric cell-face velocities."""
        xp = self._backend.xp
        x_faces = 0.5 * (u[:, :-1] + u[:, 1:])
        y_faces = 0.5 * (v[:-1, :] + v[1:, :])
        if boundary[0] != "periodic":
            x_faces = xp.array(x_faces, copy=True)
            x_faces[0, :] = 0.0
            x_faces[-1, :] = 0.0
        if boundary[1] != "periodic":
            y_faces = xp.array(y_faces, copy=True)
            y_faces[:, 0] = 0.0
            y_faces[:, -1] = 0.0
        return x_faces, y_faces

    def _project_geometric_cell_face_velocity(
        self,
        face_velocity,
        *,
        dt: float,
        boundary: tuple[str, str],
    ):
        """Project AO cell-face volume fluxes onto ``B_g Phi_V=0``.

        A3 mapping:
          Equation: a fully liquid cell has ``Phi_l=Phi_V``; preserving
          ``q_C=|C|`` therefore requires the AO finite-volume incidence
          ``B_g Phi_V=0`` on the geometric cell-face lattice.
          Discretization: build integrated cell-face volume fluxes, solve the
          Neumann/periodic finite-volume Hodge projection
          ``F=F0-grad_g pi`` with ``B_g F=0`` on the current nonuniform grid,
          and divide by physical face measures for swept-strip transport.
          Code: all vector algebra stays backend-native; one scalar packet at
          the end fail-closes if the projected divergence would move q beyond
          the active compatibility volume tolerance in one step.
        """
        projection = project_geometric_cell_face_velocity(
            self._backend,
            self._grid.coords,
            tuple(self._grid.N),
            face_velocity,
            dt=dt,
            boundary=boundary,
            policy=self._geometric_volume_hodge_policy(),
        )
        return projection.face_velocity_components

    def _geometric_volume_hodge_policy(self) -> GeometricVolumeHodgePolicy:
        """Return the YAML-owned AO volume Hodge PCG policy."""
        return GeometricVolumeHodgePolicy(
            absolute_tolerance=float(
                getattr(self, "_active_projection_absolute_tolerance", 1.0e-11)
            ),
            pcg_tolerance=float(
                getattr(self, "_active_projection_pcg_tolerance", 1.0e-12)
            ),
            pcg_max_iterations=int(
                getattr(self, "_active_projection_pcg_max_iterations", 256)
            ),
            pcg_roundoff_floor=getattr(
                self,
                "_active_projection_pcg_roundoff_floor",
                1.0e-14,
            ),
        )

    def _close_geometric_volume_flux_boundary(
        self,
        flux_x,
        flux_y,
        *,
        boundary: tuple[str, str],
    ):
        """Materialise the declared wall/periodic closure on cell-face fluxes."""
        return close_geometric_volume_flux_boundary(
            self._backend.xp,
            flux_x,
            flux_y,
            boundary=boundary,
        )

    def _project_geometric_volume_flux_pair(
        self,
        flux_x,
        flux_y,
        *,
        dt: float,
        boundary: tuple[str, str],
    ):
        """Return the finite-volume Hodge projection of cell-face fluxes."""
        projected, _raw_residual, _projected_residual = (
            project_geometric_volume_flux_pair(
                self._backend,
                self._grid.coords,
                tuple(self._grid.N),
                (flux_x, flux_y),
                dt=dt,
                boundary=boundary,
                policy=self._geometric_volume_hodge_policy(),
            )
        )
        return projected

    def _geometric_volume_flux_gradient(
        self,
        potential,
        *,
        dtype,
        boundary: tuple[str, str],
    ):
        """Return integrated cell-face flux ``grad_g potential``."""
        xp = self._backend.xp
        metrics = build_geometric_volume_metrics(
            xp,
            self._grid.coords,
            tuple(self._grid.N),
            dtype=dtype,
            boundary=boundary,
        )
        return geometric_volume_flux_gradient(
            xp,
            metrics,
            potential,
            dtype=dtype,
        )

    def _geometric_volume_flux_divergence(self, flux_x, flux_y):
        return geometric_volume_flux_divergence(flux_x, flux_y)

    def _geometric_volume_flux_projection_diagonal(
        self,
        *,
        dtype,
        boundary: tuple[str, str],
    ):
        xp = self._backend.xp
        metrics = build_geometric_volume_metrics(
            xp,
            self._grid.coords,
            tuple(self._grid.N),
            dtype=dtype,
            boundary=boundary,
        )
        return geometric_volume_flux_projection_diagonal(
            xp,
            metrics,
            dtype=dtype,
        )

    def _solve_geometric_volume_flux_projection_pcg(
        self,
        rhs,
        diag,
        *,
        boundary: tuple[str, str],
    ):
        """Device-resident fixed-loop PCG for the geometric flux Hodge solve."""
        xp = self._backend.xp
        metrics = build_geometric_volume_metrics(
            xp,
            self._grid.coords,
            tuple(self._grid.N),
            dtype=rhs.dtype,
            boundary=boundary,
        )
        policy = self._geometric_volume_hodge_policy().validated()
        return solve_geometric_volume_flux_projection_pcg(
            xp,
            metrics,
            rhs,
            diag,
            pcg_tolerance=policy.pcg_tolerance,
            max_iterations=policy.pcg_max_iterations,
            roundoff_floor=policy.pcg_roundoff_floor,
        )

    def _publish_conservative_state(self, state: NSStepState) -> NSStepState:
        """Persist conservative density/momentum as backend-native arrays."""
        xp = self._backend.xp
        density = state.conservative_density
        if density is None:
            density = state.rho
        if density is None:
            density = state.rho_g + (state.rho_l - state.rho_g) * state.psi
        density = xp.asarray(density)
        momentum = [
            density * xp.asarray(state.u),
            density * xp.asarray(state.v),
        ]
        state.conservative_density = density
        state.conservative_momentum_components = momentum
        self._conservative_density = density
        self._conservative_momentum_components = momentum
        return state

    def _geometric_projection_cadence(self) -> int:
        """Return the AO compatibility-projection cadence for q transport."""
        if getattr(self, "_reinit_method", "") != "compatibility_projection":
            return 0
        return int(getattr(self, "_reinit_every", 0))

    def _geometric_transport_projection_cadence(
        self,
        boundary: tuple[str, str],
    ) -> int:
        """Return the in-transport projection cadence for the current gauge.

        With q-primary graph tracking the mathematical owner is the transported
        cell volume.  The projection must therefore close the graph gauge
        reconstructed from q, not first force q into the old phi stratum.
        """
        cadence = self._geometric_projection_cadence()
        if self._geometric_graph_gauge_reconstruction_enabled(boundary):
            if cadence <= 0:
                raise ValueError(
                    "column_height_graph gauge reconstruction requires "
                    "compatibility_projection with a positive schedule"
                )
            return 0
        return cadence

    def _geometric_graph_gauge_reconstruction_enabled(
        self,
        boundary: tuple[str, str],
    ) -> bool:
        """Return whether q-primary AO should seed phi from a graph topology."""
        mode = getattr(self, "_interface_gauge_reconstruction", "fixed_stratum")
        if mode == "fixed_stratum":
            return False
        if mode != "column_height_graph":
            raise ValueError(
                "interface_gauge_reconstruction must be 'fixed_stratum' or "
                f"'column_height_graph', got {mode!r}"
            )
        if self._grid.ndim != 2 or tuple(boundary) != ("periodic", "wall"):
            raise ValueError(
                "column_height_graph gauge reconstruction requires a 2-D "
                "x-periodic/y-wall graph interface"
            )
        return True

    def _graph_phi_from_column_volume(self, q):
        """Build the liquid-below graph gauge predictor from AO column volumes.

        A3 mapping:
          Equation: for a single graph ``Gamma={y=h(x)}`` with liquid below,
          ``sum_j q_{ij} = dx_i (h_i - y_min)`` is the finite-volume column
          integral of the liquid indicator.
          Discretization: recover cell-center heights from the conserved
          column volume and interpolate them to P1 x-nodes with the same
          nonuniform-grid metric weights used by projection-facing cell views.
          Code: the returned gauge is only a topology-moving seed; the
          conserved cell volumes are not changed, and AO compatibility is
          closed by the hard ``Q_h(phi)=q`` projection before use.
        """
        xp = self._backend.xp
        q_dev = xp.asarray(q)
        expected = tuple(self._grid.N)
        if tuple(q_dev.shape) != expected:
            raise ValueError(f"graph q field shape must be {expected}")
        x_edges = xp.asarray(self._grid.coords[0], dtype=q_dev.dtype)
        y_edges = xp.asarray(self._grid.coords[1], dtype=q_dev.dtype)
        dx = x_edges[1:] - x_edges[:-1]
        column_volume = xp.sum(q_dev, axis=1)
        height_cells = y_edges[0] + column_volume / dx

        height_tol = max(
            float(getattr(self, "_active_projection_absolute_tolerance", 1.0e-11)),
            1.0e-12 * float(self._grid.L[1]),
        )
        min_height = float(self._backend.to_host(xp.min(height_cells)))
        max_height = float(self._backend.to_host(xp.max(height_cells)))
        lower = float(self._backend.to_host(y_edges[0]))
        upper = float(self._backend.to_host(y_edges[-1]))
        if min_height < lower - height_tol or max_height > upper + height_tol:
            raise ValueError(
                "column_height_graph gauge reconstruction requires all "
                "liquid-column heights to stay inside the y-wall domain"
            )

        nx = int(self._grid.N[0])
        column_rhs = 2.0 * column_volume / dx
        modes = xp.arange(nx, dtype=q_dev.dtype)
        angles = (
            2.0
            * xp.asarray(np.pi, dtype=q_dev.dtype)
            * modes
            / xp.asarray(nx, dtype=q_dev.dtype)
        )
        eigenvalues = 1.0 + xp.exp(1j * angles)
        denom = xp.real(eigenvalues * xp.conj(eigenvalues))
        denom_floor = (
            xp.asarray(100.0 * np.finfo(np.dtype(q_dev.dtype)).eps, dtype=q_dev.dtype)
            * xp.max(denom)
        )
        rhs_hat = xp.fft.fft(column_rhs)
        height_hat = xp.where(
            denom > denom_floor,
            xp.conj(eigenvalues) * rhs_hat / denom,
            xp.zeros_like(rhs_hat),
        )
        height_nodes_periodic = y_edges[0] + xp.real(xp.fft.ifft(height_hat))
        graph_total = xp.sum(
            dx
            * (
                0.5
                * (
                    height_nodes_periodic
                    + xp.roll(height_nodes_periodic, -1)
                )
                - y_edges[0]
            )
        )
        height_nodes_periodic = height_nodes_periodic + (
            xp.sum(column_volume) - graph_total
        ) / (x_edges[-1] - x_edges[0])
        height_nodes = xp.empty((nx + 1,), dtype=q_dev.dtype)
        height_nodes[:-1] = height_nodes_periodic
        height_nodes[-1] = height_nodes_periodic[0]

        min_height = float(self._backend.to_host(xp.min(height_nodes)))
        max_height = float(self._backend.to_host(xp.max(height_nodes)))
        if min_height < lower - height_tol or max_height > upper + height_tol:
            raise ValueError(
                "column_height_graph gauge reconstruction requires the realised "
                "P1 graph to stay inside the y-wall domain"
            )
        return y_edges.reshape((1, -1)) - height_nodes.reshape((-1, 1))

    def _project_geometric_state_from_q_phi(self, q, phi, *, level: float):
        """Close a topology-aware gauge seed with the AO hard constraint."""
        if self._backend.is_gpu():
            return project_geometric_phase_state_gpu(
                self._grid,
                q,
                phi,
                level=level,
                tolerance=self._active_projection_absolute_tolerance,
                relative_tolerance=self._active_projection_relative_tolerance,
                max_newton_iterations=self._active_projection_max_iterations,
                solver_scheme=self._active_projection_solver_scheme,
                pcg_tolerance=self._active_projection_pcg_tolerance,
                pcg_max_iterations=self._active_projection_pcg_max_iterations,
                pcg_roundoff_floor=self._active_projection_pcg_roundoff_floor,
                dc_tolerance=self._active_projection_dc_tolerance,
                dc_max_iterations=self._active_projection_dc_max_iterations,
                dc_relaxation=self._active_projection_dc_relaxation,
            )
        state = GeometricPhaseState.from_q_phi(
            self._grid,
            q,
            phi,
            level=level,
            tolerance=self._active_projection_absolute_tolerance,
            require_compatible=False,
        )
        return state.project_compatibility(
            self._grid,
            tolerance=self._active_projection_absolute_tolerance,
            max_newton_iterations=self._active_projection_max_iterations,
            max_cg_iterations=self._active_projection_pcg_max_iterations,
        )

    def _reconstruct_geometric_graph_gauge(
        self,
        result,
        *,
        boundary: tuple[str, str],
    ):
        """Replace transported fixed-stratum phi by a q-owned graph gauge."""
        if not self._geometric_graph_gauge_reconstruction_enabled(boundary):
            return result
        transported = result.phase_transport.state
        phi = self._graph_phi_from_column_volume(transported.q)
        projected = (
            build_geometric_phase_state_gpu(
                self._grid,
                phi,
                level=transported.stratum.level,
            )
            if self._backend.is_gpu()
            else self._project_geometric_state_from_q_phi(
                transported.q,
                phi,
                level=transported.stratum.level,
            )
        )
        phase_transport = replace(
            result.phase_transport,
            state=projected,
            pre_projection_state=transported,
            projected=True,
        )
        return replace(result, phase_transport=phase_transport)

    def _advance_geometric_phase_stage(self, state: NSStepState) -> NSStepState:
        """Advance typed AO q transport, then fail closed before NS coupling."""
        self._last_geometric_common_flux_transport = None
        self._last_geometric_runtime_material = None
        self._last_geometric_runtime_capillary = None
        self._last_geometric_runtime_capillary_application = None
        if self._geometric_phase_grid_rebuild_due(state.step_index):
            prepared_step = getattr(
                self,
                "_prepared_geometric_grid_rebuild_step",
                None,
            )
            if prepared_step == int(state.step_index):
                self._prepared_geometric_grid_rebuild_step = None
            else:
                state = self._rebuild_grid_from_geometric_phase_state(state)
        phase_state = getattr(self, "_geometric_phase_state", None)
        if phase_state is None:
            raise ValueError(
                "geometric_cell_fraction runtime transport requires "
                "build_ic(...) to attach GeometricPhaseState before advancing "
                "the NS step"
            )
        try:
            face_velocity = self._geometric_face_velocity_for_common_flux(state)
        except RuntimeError as exc:
            raise ValueError(
                "geometric_cell_fraction runtime transport requires "
                "geometric cell-face velocities"
            ) from exc
        boundary = boundary_axes(self.bc_type, self._grid.ndim)
        if self._backend.is_gpu():
            result = transport_geometric_phase_common_flux_2d_gpu(
                self._grid,
                phase_state,
                face_velocity,
                dt=state.dt,
                rho_l=state.rho_l,
                rho_g=state.rho_g,
                boundary=boundary,
                tolerance=self._active_projection_absolute_tolerance,
                project_every_steps=(
                    self._geometric_transport_projection_cadence(boundary)
                ),
                step_index=state.step_index,
                max_newton_iterations=self._active_projection_max_iterations,
                relative_tolerance=self._active_projection_relative_tolerance,
                solver_scheme=self._active_projection_solver_scheme,
                pcg_tolerance=self._active_projection_pcg_tolerance,
                pcg_max_iterations=self._active_projection_pcg_max_iterations,
                pcg_roundoff_floor=self._active_projection_pcg_roundoff_floor,
                dc_tolerance=self._active_projection_dc_tolerance,
                dc_max_iterations=self._active_projection_dc_max_iterations,
                dc_relaxation=self._active_projection_dc_relaxation,
            )
        else:
            result = transport_geometric_phase_common_flux_2d(
                self._grid,
                phase_state,
                face_velocity,
                dt=state.dt,
                rho_l=state.rho_l,
                rho_g=state.rho_g,
                boundary=boundary,
                tolerance=1.0e-11,
                project_every_steps=(
                    self._geometric_transport_projection_cadence(boundary)
                ),
                step_index=state.step_index,
            )
        result = self._reconstruct_geometric_graph_gauge(result, boundary=boundary)
        state.geometric_common_flux_transport = result
        self._last_geometric_common_flux_transport = result
        material = (
            materialise_geometric_common_flux_state_gpu(
                self._grid,
                result,
                rho_l=state.rho_l,
                rho_g=state.rho_g,
                boundary=boundary,
                tolerance=1.0e-11,
            )
            if self._backend.is_gpu()
            else materialise_geometric_common_flux_state(
                self._grid,
                result,
                rho_l=state.rho_l,
                rho_g=state.rho_g,
                boundary=boundary,
                tolerance=1.0e-11,
            )
        )
        state.geometric_runtime_material = material
        state.psi = self._geometric_cell_to_node_view(material.phase_state.theta)
        state.rho = self._geometric_cell_to_node_view(material.density)
        state.conservative_density = state.rho
        self._last_geometric_runtime_material = material
        capillary_endpoint = getattr(
            self,
            "_capillary_closed_interface_endpoint",
            "geometric_cell_fraction",
        )
        graph_gauge = self._geometric_graph_gauge_reconstruction_enabled(boundary)
        if graph_gauge and capillary_endpoint != "column_height_graph":
            raise ValueError(
                "column_height_graph gauge reconstruction requires "
                "closed_interface.endpoint='column_height_graph'"
            )
        if (not graph_gauge) and capillary_endpoint == "column_height_graph":
            raise ValueError(
                "closed_interface.endpoint='column_height_graph' requires "
                "gauge_reconstruction='column_height_graph'"
            )
        if self._backend.is_gpu():
            if graph_gauge:
                capillary = materialise_geometric_graph_capillary_state_gpu(
                    self._grid,
                    material,
                    sigma=state.sigma,
                    tolerance=self._active_projection_absolute_tolerance,
                )
            else:
                capillary = materialise_geometric_runtime_capillary_state_gpu(
                    self._grid,
                    material,
                    sigma=state.sigma,
                    tolerance=self._active_projection_absolute_tolerance,
                    solver_scheme=self._active_projection_solver_scheme,
                    pcg_tolerance=self._active_projection_pcg_tolerance,
                    max_pcg_iterations=self._active_projection_pcg_max_iterations,
                    pcg_roundoff_floor=self._active_projection_pcg_roundoff_floor,
                    dc_tolerance=self._active_projection_dc_tolerance,
                    dc_max_iterations=self._active_projection_dc_max_iterations,
                    dc_relaxation=self._active_projection_dc_relaxation,
                )
        else:
            capillary = materialise_geometric_runtime_capillary_state(
                self._grid,
                material,
                sigma=state.sigma,
                tolerance=1.0e-11,
            )
        state.geometric_runtime_capillary = capillary
        self._last_geometric_runtime_capillary = capillary
        application = (
            materialise_geometric_runtime_capillary_application_state_gpu(
                self._grid,
                capillary,
                dt=state.dt,
            )
            if self._backend.is_gpu()
            else materialise_geometric_runtime_capillary_application_state(
                self._grid,
                capillary,
                dt=state.dt,
            )
        )
        state.geometric_runtime_capillary_application = application
        self._last_geometric_runtime_capillary_application = application
        if self._backend.is_gpu():
            validate_geometric_runtime_capillary_fail_close_gpu(
                self._backend,
                capillary,
                application,
                ppe_runtime=self._ppe_runtime,
            )
        validate_geometric_runtime_capillary_application_admitted(
            application,
            allow_pending_reaction_projection=True,
        )
        state.conservative_transport_certificate = {
            "status": "geometric_phase_transport_ready",
            "projected": result.phase_transport.projected,
            "initial_volume": (
                result.phase_transport.transport.certificate.initial_volume
            ),
            "final_volume": result.phase_transport.transport.certificate.final_volume,
            "volume_drift": result.phase_transport.transport.certificate.volume_drift,
            "closure_residual_linf": (
                result.phase_transport.transport.certificate.closure_residual_linf
            ),
            "min_density": material.min_density,
            "max_density": material.max_density,
            "mass_flux_formula_residual_linf": (
                material.mass_flux_formula_residual_linf
            ),
            "face_hodge_min_weight": material.face_hodge.min_weight,
            "face_hodge_max_weight": material.face_hodge.max_weight,
            "capillary_pressure_range_status": capillary.pressure_range_status,
            "capillary_pressure_exact_static": capillary.pressure_exact_static,
            "capillary_drive_present": capillary.capillary_drive_present,
            "capillary_pressure_range_tolerance": (
                capillary.pressure_range_tolerance
            ),
            "capillary_source_discretization": (
                "column_height_graph"
                if self._backend.is_gpu() and graph_gauge
                else "p1_cut_bundle"
            ),
            "capillary_force_weighted_acceleration_l2": (
                capillary.capillary_force_weighted_acceleration_l2
            ),
            "capillary_pressure_reaction_weighted_acceleration_l2": (
                capillary.pressure_reaction_weighted_acceleration_l2
            ),
            "capillary_force_max_abs_face_covector": (
                capillary.max_abs_capillary_force_face_covector
            ),
            "capillary_pressure_reaction_max_abs_face_covector": (
                capillary.max_abs_pressure_reaction_face_covector
            ),
            "young_laplace_residual_linf": (
                capillary.young_laplace_residual_linf
            ),
            "young_laplace_residual_l2": (
                capillary.young_laplace_residual_l2
            ),
            "young_laplace_normal_residual_linf": (
                capillary.young_laplace_normal_residual_linf
            ),
            "capillary_weighted_residual_acceleration_l2": (
                capillary.weighted_residual_acceleration_l2
            ),
            "capillary_max_abs_residual_face_covector": (
                capillary.max_abs_residual_face_covector
            ),
            "ao_capillary_predictor_increment_weighted_l2": (
                application.predictor_increment_weighted_l2
            ),
            "ao_capillary_pressure_reaction_increment_weighted_l2": (
                application.pressure_reaction_increment_weighted_l2
            ),
            "ao_capillary_pressure_balanced_increment_weighted_l2": (
                application.pressure_balanced_increment_weighted_l2
            ),
            "ao_capillary_pressure_balanced_max_abs_face_increment": (
                application.max_abs_pressure_balanced_face_increment
            ),
        }
        if (
            application.pressure_exact_static
            and application.pressure_balanced_increment_weighted_l2
            <= capillary.pressure_range_tolerance
            and application.max_abs_pressure_balanced_face_increment
            <= capillary.pressure_range_tolerance
        ):
            self._geometric_phase_state = result.phase_transport.state
            state.conservative_transport_certificate[
                "ao_static_downstream_unblocked"
            ] = True
            return state
        if application.capillary_drive_present:
            state.conservative_transport_certificate[
                "ao_nonstatic_predictor_stage_unblocked"
            ] = True
            return state
        raise ValueError(
            "geometric_cell_fraction runtime transport produced typed "
            "q/density/common-flux/capillary-Hodge/application state, but "
            "non-static downstream AO momentum and PPE integration remain blocked"
        )

    def _geometric_cell_to_node_view(self, cell_values):
        """Average geometric cell cochains to the nodal NS material lattice."""
        xp = self._backend.xp
        values = xp.asarray(cell_values)
        expected = tuple(self._grid.N)
        if tuple(values.shape) != expected:
            raise ValueError(f"geometric cell field shape must be {expected}")
        nodes = xp.zeros((self._grid.N[0] + 1, self._grid.N[1] + 1), dtype=values.dtype)
        counts = xp.zeros_like(nodes)
        nodes[:-1, :-1] = nodes[:-1, :-1] + values
        counts[:-1, :-1] = counts[:-1, :-1] + 1.0
        nodes[1:, :-1] = nodes[1:, :-1] + values
        counts[1:, :-1] = counts[1:, :-1] + 1.0
        nodes[1:, 1:] = nodes[1:, 1:] + values
        counts[1:, 1:] = counts[1:, 1:] + 1.0
        nodes[:-1, 1:] = nodes[:-1, 1:] + values
        counts[:-1, 1:] = counts[:-1, 1:] + 1.0
        errstate = (
            xp.errstate(invalid="ignore")
            if hasattr(xp, "errstate")
            else np.errstate(invalid="ignore")
        )
        with errstate:
            nodal = nodes / counts
        boundary = boundary_axes(self.bc_type, self._grid.ndim)
        if boundary[0] == "periodic":
            seam = 0.5 * (nodal[0, :] + nodal[-1, :])
            nodal[0, :] = seam
            nodal[-1, :] = seam
        if boundary[1] == "periodic":
            seam = 0.5 * (nodal[:, 0] + nodal[:, -1])
            nodal[:, 0] = seam
            nodal[:, -1] = seam
        return nodal

    def _advance_conservative_common_flux_stage(
        self,
        state: NSStepState,
        *,
        psi_previous,
        will_rebuild: bool,
        rebuild_old_coords,
        step_diag_enabled: bool,
        record_projection_fields: bool,
        capillary_needs_transport_endpoint: bool,
    ) -> NSStepState:
        """Transport ``q, rho, rho u`` with the same FCCD stage ledger."""
        if getattr(self, "_interface_tracking_method", "psi_direct") != "psi_direct":
            raise NotImplementedError(
                "conservative_common_flux currently requires psi_direct transport"
            )
        if getattr(self._transport, "mass_correction", False):
            raise NotImplementedError(
                "conservative_common_flux requires mass correction to be expressed "
                "as a conservative q/momentum remap"
            )
        advance_face = getattr(self._transport, "advance_with_face_velocity", None)
        if not callable(advance_face):
            raise RuntimeError(
                "conservative_common_flux requires transport.advance_with_face_velocity"
            )

        xp = self._backend.xp
        if hasattr(self._transport, "record_reinit_projection"):
            must_record_reinit = (
                getattr(self._interface_runtime, "reinit_every", 0) > 0
                or getattr(self._interface_runtime, "reinit_trigger_mode", "fixed")
                == "adaptive"
            )
            self._transport.record_reinit_projection = (
                step_diag_enabled
                or record_projection_fields
                or capillary_needs_transport_endpoint
                or must_record_reinit
            )
        face_velocity = self._face_velocity_for_common_flux(state)
        advanced = advance_face(
            state.psi,
            face_velocity,
            state.dt,
            step_index=state.step_index,
            clip_bounds=None,
            bound_preserving=True,
            face_divergence_operator=self._div_op,
            return_ledger=True,
        )
        psi_after_retraction, ledger = advanced
        psi_after_retraction = xp.asarray(psi_after_retraction)
        state.conservative_transport_ledger = ledger
        reinit_projection = getattr(self._transport, "last_reinit_projection", None)
        reinit_triggered = bool(
            reinit_projection and reinit_projection.get("triggered", False)
        )
        state.psi_transport_endpoint = xp.asarray(
            getattr(ledger, "psi_after_transport", psi_after_retraction)
        )
        if record_projection_fields and reinit_projection:
            state.interface_projection_fields = dict(reinit_projection)
        state.interface_projection_diagnostics = zero_reinit_projection_diagnostics()
        state.psi_previous = psi_previous

        density0 = state.conservative_density
        if density0 is None:
            density0 = state.rho_g + (state.rho_l - state.rho_g) * ledger.psi_before
        density0 = xp.asarray(density0)
        momentum0 = state.conservative_momentum_components
        if momentum0 is None:
            momentum0 = [density0 * xp.asarray(state.u), density0 * xp.asarray(state.v)]
        transport = ConservativeCommonFluxTransport(
            self._backend,
            self._grid,
            self._fccd,
            divergence_operator=self._div_op,
        )
        result = transport.advance(
            density0,
            tuple(momentum0),
            ledger,
            rho_l=state.rho_l,
            rho_g=state.rho_g,
        )
        if reinit_triggered:
            density_final = state.rho_g + (state.rho_l - state.rho_g) * psi_after_retraction
            momentum_final = [
                density_final * velocity for velocity in result.velocity_components
            ]
            reinit_kinetic = transport._kinetic_energy(
                density_final,
                tuple(momentum_final),
            )
            reinit_kinetic_delta = reinit_kinetic - result.kinetic_energy_after
            state.psi = psi_after_retraction
            state.conservative_density = density_final
            state.rho = density_final
            state.conservative_momentum_components = momentum_final
            state.u, state.v = result.velocity_components
        else:
            state.psi = state.psi_transport_endpoint
            state.conservative_density = result.density
            state.rho = result.density
            state.conservative_momentum_components = list(result.momentum_components)
            reinit_kinetic_delta = xp.asarray(0.0, dtype=xp.asarray(result.density).dtype)
        state.conservative_transport_certificate = {
            "kinetic_energy_before": result.kinetic_energy_before,
            "kinetic_energy_after": result.kinetic_energy_after,
            "kinetic_energy_delta": result.kinetic_energy_delta,
            "reinit_kinetic_delta": reinit_kinetic_delta,
            "min_density": result.min_density,
            "max_density": result.max_density,
            "status": result.certificate_status,
        }
        if reinit_triggered:
            state.u = state.conservative_momentum_components[0] / state.rho
            state.v = state.conservative_momentum_components[1] / state.rho
        self._conservative_density = state.conservative_density
        self._conservative_momentum_components = list(
            state.conservative_momentum_components
        )
        if will_rebuild:
            state = self._rebuild_grid_conservative(state)
            if rebuild_old_coords is not None:
                remapper = build_grid_remapper(
                    self._backend,
                    rebuild_old_coords,
                    self._grid.coords,
                )
                state.psi_previous = xp.clip(
                    xp.asarray(remapper.remap(psi_previous)),
                    xp.asarray(0.0, dtype=state.psi.dtype),
                    xp.asarray(1.0, dtype=state.psi.dtype),
                )
                if state.psi_transport_endpoint is not None:
                    state.psi_transport_endpoint = xp.clip(
                        xp.asarray(remapper.remap(state.psi_transport_endpoint)),
                        xp.asarray(0.0, dtype=state.psi.dtype),
                        xp.asarray(1.0, dtype=state.psi.dtype),
                    )
            state.interface_projection_fields = None
        self._projected_face_components = None
        return state

    def _advance_interface_stage(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Advance the interface transport and optional grid rebuild."""
        backend = getattr(self, "_backend", None)
        xp = getattr(backend, "xp", None)
        if xp is None:
            xp = np
        if self._geometric_phase_runtime_enabled():
            return self._advance_geometric_phase_stage(state)
        if getattr(self, "_geometric_phase_state", None) is not None:
            raise ValueError(
                "geometric_cell_fraction runtime transport activation remains "
                "blocked after the initial-state gate; connect the AO "
                "q-transport/common-flux path before advancing the NS step"
            )
        psi_previous = xp.array(state.psi, copy=True)
        curvature_method = getattr(self, "_curvature_method", "")
        if curvature_method == "transport_variational_p2_ale_discrete_gradient":
            state.transport_variational_previous_surface_energy = None
        rebuild_old_coords = None
        will_rebuild = (
            self._alpha_grid > 1.0
            and self._interface_runtime.rebuild_freq > 0
            and state.step_index > 0
            and (state.step_index % self._interface_runtime.rebuild_freq == 0)
        )
        if will_rebuild:
            rebuild_old_coords = [coords.copy() for coords in self._grid.coords]
            if (
                curvature_method == "transport_variational_p2_ale_discrete_gradient"
            ):
                state.transport_variational_previous_surface_energy = (
                    p2_trace_surface_energy_2d(
                        xp=xp,
                        grid=self._grid,
                        psi=psi_previous,
                        sigma=state.sigma,
                    )
                )
        advance_face = getattr(self._transport, "advance_with_face_velocity", None)
        step_diag_enabled = bool(getattr(getattr(self, "_step_diag", None), "enabled", False))
        record_projection_fields = bool(
            getattr(self, "_record_interface_projection_fields", False)
        )
        capillary_needs_transport_endpoint = (
            getattr(self, "_capillary_force_source", "curvature_jump")
            == "closed_interface_riesz"
        )
        if self._conservative_common_flux_enabled():
            return self._advance_conservative_common_flux_stage(
                state,
                psi_previous=psi_previous,
                will_rebuild=will_rebuild,
                rebuild_old_coords=rebuild_old_coords,
                step_diag_enabled=step_diag_enabled,
                record_projection_fields=record_projection_fields,
                capillary_needs_transport_endpoint=capillary_needs_transport_endpoint,
            )
        if hasattr(self._transport, "record_reinit_projection"):
            self._transport.record_reinit_projection = (
                step_diag_enabled
                or record_projection_fields
                or capillary_needs_transport_endpoint
            )
        if state.face_velocity_components is not None and callable(advance_face):
            state.psi = advance_face(
                state.psi,
                state.face_velocity_components,
                state.dt,
                step_index=state.step_index,
            )
        else:
            state.psi = self._transport.advance(
                state.psi, [state.u, state.v], state.dt, step_index=state.step_index
            )
        state.interface_projection_diagnostics = zero_reinit_projection_diagnostics()
        reinit_projection = getattr(self._transport, "last_reinit_projection", None)
        state.psi_transport_endpoint = state.psi
        if reinit_projection and "psi_after_transport_before_reinit" in reinit_projection:
            state.psi_transport_endpoint = reinit_projection[
                "psi_after_transport_before_reinit"
            ]
        if record_projection_fields and reinit_projection:
            state.interface_projection_fields = dict(reinit_projection)
        if (
            step_diag_enabled
            and reinit_projection
            and reinit_projection.get("triggered", False)
        ):
            state.interface_projection_diagnostics = reinit_projection_diagnostics(
                xp=xp,
                backend=backend,
                grid=self._grid,
                psi_before=reinit_projection["psi_before"],
                psi_after=reinit_projection["psi_after"],
                sigma=state.sigma,
            )
        state.psi_previous = psi_previous
        if will_rebuild:
            try:
                state.psi, state.u, state.v = self._rebuild_grid(
                    state.psi,
                    state.u,
                    state.v,
                    rho_l=state.rho_l,
                    rho_g=state.rho_g,
                )
            except TypeError:
                state.psi, state.u, state.v = self._rebuild_grid(
                    state.psi,
                    state.u,
                    state.v,
                )
            if rebuild_old_coords is not None:
                remapper = build_grid_remapper(
                    backend,
                    rebuild_old_coords,
                    self._grid.coords,
                )
                state.psi_previous = xp.clip(
                    xp.asarray(remapper.remap(psi_previous)),
                    xp.asarray(0.0, dtype=state.psi.dtype),
                    xp.asarray(1.0, dtype=state.psi.dtype),
                )
                if state.psi_transport_endpoint is not None:
                    state.psi_transport_endpoint = xp.clip(
                        xp.asarray(remapper.remap(state.psi_transport_endpoint)),
                        xp.asarray(0.0, dtype=state.psi.dtype),
                        xp.asarray(1.0, dtype=state.psi.dtype),
                    )
            else:
                state.psi_transport_endpoint = state.psi
            self._projected_face_components = None
            state.interface_projection_fields = None
        return state

    def _materialise_step_fields(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Build density and viscosity fields for the current step."""
        if not self._interface_tracking_enabled:
            self._enable_static_ppe_operator_cache()
            cache_key = self._static_material_cache_key(state)
            cache = getattr(self, "_static_material_cache", None)
            if cache is not None and cache["key"] == cache_key:
                state.rho = cache["rho"]
                state.mu_field = cache["mu_field"]
                return state
            state = materialise_ns_step_fields(state)
            self._static_material_cache = {
                "key": cache_key,
                "rho": state.rho,
                "mu_field": state.mu_field,
            }
            return state
        return materialise_ns_step_fields(state)

    def _enable_static_ppe_operator_cache(self) -> None:
        """Enable coefficient reuse for frozen-interface static diagnostics."""
        if getattr(self, "_static_ppe_operator_cache_enabled", False):
            return
        setter = getattr(self._ppe_solver, "set_static_operator_cache", None)
        if callable(setter):
            setter(True)
        self._static_ppe_operator_cache_enabled = True

    @staticmethod
    def _static_material_cache_key(state: NSStepState) -> tuple:
        """Return an identity key for fields frozen by StaticInterfaceTransport."""
        mu_value = state.mu
        mu_pointer = getattr(getattr(mu_value, "data", None), "ptr", None)
        mu_dtype = getattr(
            getattr(mu_value, "dtype", None),
            "str",
            str(getattr(mu_value, "dtype", "")),
        )
        mu_shape = tuple(getattr(mu_value, "shape", ()))
        return (
            id(state.psi),
            tuple(getattr(state.psi, "shape", ())),
            float(state.rho_l),
            float(state.rho_g),
            state.mu_l,
            state.mu_g,
            id(mu_value),
            mu_pointer,
            mu_shape,
            mu_dtype,
        )

    def _surface_tension_stage(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Compute curvature and balanced-force surface tension terms."""
        if state.geometric_runtime_capillary_application is not None:
            return compute_ns_geometric_surface_tension_stage(
                state,
                backend=self._backend,
                step_diag=self._step_diag,
                projection_consistent_buoyancy=(
                    self._projection_consistent_buoyancy
                ),
            )
        return compute_ns_surface_tension_stage(
            state,
            backend=self._backend,
            curv=self._curv,
            curvature_filter=self._curvature_filter,
            interface_runtime=self._interface_runtime,
            step_diag=self._step_diag,
            st_force=self._st_force,
            ccd=self._ccd,
            grid=self._grid,
            bc_type=self.bc_type,
            surface_tension_grad_op=self._surface_tension_grad_op,
            projection_consistent_buoyancy=self._projection_consistent_buoyancy,
        )

    def _predict_velocity_stage(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Advance the momentum predictor stage."""
        (
            state,
            self._conv_ab2_ready,
            self._conv_prev,
            self._velocity_bdf2_ready,
            self._velocity_prev,
        ) = compute_ns_predictor_stage(
            state,
            backend=self._backend,
            ccd=self._ccd,
            conv_term=self._conv_term,
            viscous_predictor=self._viscous_predictor,
            scheme_runtime=self._scheme_runtime,
            conv_ab2_ready=self._conv_ab2_ready,
            conv_prev=self._conv_prev,
            velocity_bdf2_ready=self._velocity_bdf2_ready,
            velocity_prev=self._velocity_prev,
            projection_consistent_buoyancy=self._projection_consistent_buoyancy,
            face_native_predictor_state=self._face_native_predictor_state,
            face_no_slip_boundary_state=self._face_no_slip_boundary_state,
            div_op=self._div_op,
            bc_type=self.bc_type,
            cn_buoyancy_predictor_assembly_mode=self._cn_buoyancy_predictor_assembly_mode,
            pressure_grad_op=self._pressure_grad_op,
            Y=self.Y,
            coords=(self.X, self.Y),
            ppe_coefficient_scheme=self._ppe_coefficient_scheme,
            conservative_momentum_transport=self._conservative_common_flux_enabled(),
            ppe_runtime=self._ppe_runtime,
            ppe_solver=self._ppe_solver,
            curvature_method=self._curvature_method,
            capillary_force_source=self._capillary_force_source,
            grid=self._grid,
        )
        self._last_geometric_runtime_capillary_application = (
            state.geometric_runtime_capillary_application
        )
        return state

    def _solve_pressure_stage(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Solve PPE and prepare the corrector pressure field."""
        state, self._p_prev_dev, self._p_prev = solve_ns_pressure_stage(
            state,
            backend=self._backend,
            div_op=self._div_op,
            ppe_solver=self._ppe_solver,
            p_prev_dev=self._p_prev_dev,
            p_base_prev_dev=self._p_base_prev_dev,
            surface_tension_scheme=self._surface_tension_scheme,
            face_native_predictor_state=self._face_native_predictor_state,
            bc_type=self.bc_type,
            face_no_slip_boundary_state=self._face_no_slip_boundary_state,
            ppe_runtime=self._ppe_runtime,
            curvature_method=self._curvature_method,
            capillary_force_source=self._capillary_force_source,
        )
        self._p_base_prev2_dev = self._p_base_prev_dev
        self._p_base_prev_dev = (
            state.pressure_history_storage_base
            if state.pressure_history_storage_base is not None
            else state.pressure_base
        )
        self._p_prev_accel_face_components = state.pressure_accel_face_components
        return state

    def _correct_velocity_stage(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Apply pressure correction and optional face-flux projection."""
        return correct_ns_velocity_stage(
            state,
            backend=self._backend,
            pressure_grad_op=self._pressure_grad_op,
            face_flux_projection=self._face_flux_projection,
            canonical_face_state=self._canonical_face_state,
            face_native_predictor_state=self._face_native_predictor_state,
            face_no_slip_boundary_state=self._face_no_slip_boundary_state,
            preserve_projected_faces=self._preserve_projected_faces,
            boundary_hodge_mode=self._boundary_hodge_mode,
            boundary_hodge_wall_trace=self._boundary_hodge_wall_trace,
            boundary_hodge_metric=self._boundary_hodge_metric,
            boundary_hodge_solver=self._boundary_hodge_solver,
            boundary_hodge_tolerance=self._boundary_hodge_tolerance,
            boundary_hodge_max_iterations=self._boundary_hodge_max_iterations,
            boundary_hodge_gate=self._boundary_hodge_gate,
            fccd_div_op=self._fccd_div_op,
            div_op=self._div_op,
            ppe_runtime=self._ppe_runtime,
            bc_type=self.bc_type,
            apply_velocity_bc=_apply_bc,
            curvature_method=self._curvature_method,
            capillary_force_source=self._capillary_force_source,
        )

    def _commit_geometric_phase_state_after_downstream(
        self,
        state: NSStepState,
    ) -> None:
        """Commit transported AO q only after downstream NS stages succeed."""
        certificate = state.conservative_transport_certificate or {}
        if (
            state.geometric_common_flux_transport is None
            or (
                certificate.get("ao_nonstatic_velocity_corrector_applied") is not True
                and certificate.get("ao_static_split_downstream_unblocked") is not True
            )
        ):
            return
        self._geometric_phase_state = (
            state.geometric_common_flux_transport.phase_transport.state
        )
        certificate = dict(certificate)
        certificate["ao_nonstatic_downstream_unblocked"] = True
        state.conservative_transport_certificate = certificate

    def _record_step_diagnostics(
        self,
        state: NSStepState,
    ) -> None:
        """Flush step diagnostics to the active recorder."""
        record_ns_step_diagnostics(
            state,
            backend=self._backend,
            div_op=self._div_op,
            step_diag=self._step_diag,
            ppe_solver=self._ppe_solver,
        )

    # ── one NS timestep ───────────────────────────────────────────────────

    def step_request(
        self,
        request: NSStepInputs | NSStepRequest,
        *,
        return_host_pressure: bool = True,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Advance one timestep from a grouped request object."""
        state = self._prepare_step_inputs(request)
        state = self._advance_interface_stage(state)
        self._last_interface_projection_fields = state.interface_projection_fields
        state = self._materialise_step_fields(state)
        state = self._surface_tension_stage(state)
        state = self._predict_velocity_stage(state)
        _apply_bc(state.u_star, state.v_star, state.bc_hook, self.bc_type)
        state = self._solve_pressure_stage(state)
        state = self._correct_velocity_stage(state)
        self._commit_geometric_phase_state_after_downstream(state)
        if self._conservative_common_flux_enabled():
            if state.geometric_runtime_material is not None:
                state.conservative_transport_certificate[
                    "ao_static_legacy_conservative_publish_skipped"
                ] = True
                self._conservative_density = None
                self._conservative_momentum_components = None
            else:
                state = self._publish_conservative_state(state)
        self._projected_face_components = state.projected_face_components
        self._last_conservative_transport_certificate = dict(
            state.conservative_transport_certificate or {}
        )
        self._record_step_diagnostics(state)

        p_out = (
            np.asarray(self._backend.to_host(state.pressure))
            if self._backend.is_gpu() and return_host_pressure
            else state.pressure
        )
        return state.psi, state.u, state.v, p_out

    def step(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        dt: float,
        rho_l: float,
        rho_g: float,
        sigma: float,
        mu: float | np.ndarray,
        g_acc: float = 0.0,
        rho_ref: float | None = None,
        mu_l: float | None = None,
        mu_g: float | None = None,
        bc_hook=None,
        step_index: int = 0,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Advance one timestep (5-stage predictor-corrector).

        Parameters
        ----------
        psi : ndarray  CLS field  (1 = liquid, 0 = gas)
        u, v : ndarray velocity
        dt : float
        rho_l, rho_g : float  densities
        sigma : float  surface tension coefficient  (0 → skip CSF)
        mu : float or ndarray  viscosity  (scalar = uniform)
        g_acc : float  gravity  (0 → skip buoyancy)
        rho_ref : float or None  buoyancy reference (default: arithmetic mean)
        mu_l, mu_g : float or None  if provided, variable viscosity
                     μ = μ_g + (μ_l − μ_g) ψ  (recomputed after advection)
        bc_hook : callable(u, v) → None or None
                  Overrides built-in wall / periodic BC.
        step_index : int  used for reinitialization frequency

        Returns
        -------
        psi, u, v, p : ndarray
        """
        return self.step_request(
            NSStepRequest(
                psi=psi,
                u=u,
                v=v,
                dt=dt,
                rho_l=rho_l,
                rho_g=rho_g,
                sigma=sigma,
                mu=mu,
                g_acc=g_acc,
                rho_ref=rho_ref,
                mu_l=mu_l,
                mu_g=mu_g,
                bc_hook=bc_hook,
                step_index=step_index,
            )
        )

    # ── private ───────────────────────────────────────────────────────────
    # (PPE solve and matrix build delegated to self._ppe_solver —  see PPESolverFVMSpsolve)


from .runner import run_simulation
