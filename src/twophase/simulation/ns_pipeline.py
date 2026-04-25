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

import numpy as np

from ..ccd.fccd import FCCDSolver
from ..levelset.reinitialize import Reinitializer
from .ns_step_state import NSStepInputs, NSStepRequest, NSStepState
from .ns_step_services import (
    compute_ns_predictor_stage,
    compute_ns_surface_tension_stage,
    correct_ns_velocity_stage,
    materialise_ns_step_fields,
    record_ns_step_diagnostics,
    solve_ns_pressure_stage,
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
    build_runtime_initial_velocity,
    compute_runtime_dt_max,
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
        eps_g_factor: float = 2.0,
        eps_g_cells: float | None = None,
        dx_min_floor: float = 1e-6,
        use_local_eps: bool = False,
        eps_xi_cells: float | None = None,
        grid_rebuild_freq: int = 1,
        reinit_every: int = 2,
        reinit_method: str = 'eikonal_xi',
        cn_viscous: bool = False,
        Re: float = 1.0,
        reproject_variable_density: bool = False,
        reproject_mode: str = "legacy",
        phi_primary_transport: bool = True,
        interface_tracking_enabled: bool = True,
        interface_tracking_method: str | None = None,
        phi_primary_redist_every: int = 4,
        phi_primary_clip_factor: float = 12.0,
        phi_primary_heaviside_eps_scale: float = 1.0,
        kappa_max: float | None = None,
        dgr_phi_smooth_C: float = 1e-4,
        reinit_eps_scale: float = 1.0,
        ridge_sigma_0: float = 3.0,
        advection_scheme: str = "dissipative_ccd",
        convection_scheme: str = "ccd",
        ppe_solver: str = "fvm_iterative",
        pressure_scheme: str | None = None,
        ppe_coefficient_scheme: str = "phase_density",
        ppe_interface_coupling_scheme: str = "none",
        ppe_iteration_method: str = "gmres",
        ppe_tolerance: float = 1.0e-8,
        ppe_max_iterations: int = 500,
        ppe_restart: int | None = 80,
        ppe_preconditioner: str = "line_pcr",
        ppe_pcr_stages: int | None = 4,
        ppe_c_tau: float = 2.0,
        ppe_defect_correction: bool = False,
        ppe_dc_max_iterations: int = 0,
        ppe_dc_tolerance: float = 0.0,
        ppe_dc_relaxation: float = 1.0,
        surface_tension_scheme: str = "csf",
        convection_time_scheme: str = "ab2",
        pressure_gradient_scheme: str | None = None,
        surface_tension_gradient_scheme: str | None = None,
        momentum_gradient_scheme: str = "projection_consistent",
        viscous_spatial_scheme: str = "ccd_bulk",
        viscous_time_scheme: str | None = None,
        cn_mode: str = "picard",
        cn_buoyancy_predictor_assembly_mode: str = "none",
        uccd6_sigma: float = 1.0e-3,
        face_flux_projection: bool = False,
        canonical_face_state: bool = False,
        face_native_predictor_state: bool = False,
        face_no_slip_boundary_state: bool = False,
        preserve_projected_faces: bool = False,
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
                eps_factor=eps_factor,
                eps_g_factor=eps_g_factor,
                eps_g_cells=eps_g_cells,
                dx_min_floor=dx_min_floor,
                use_local_eps=use_local_eps,
                eps_xi_cells=eps_xi_cells,
            ),
            interface=SolverInterfaceOptions(
                grid_rebuild_freq=grid_rebuild_freq,
                reinit_every=reinit_every,
                reinit_method=reinit_method,
                reproject_variable_density=reproject_variable_density,
                reproject_mode=reproject_mode,
                phi_primary_transport=phi_primary_transport,
                interface_tracking_enabled=interface_tracking_enabled,
                interface_tracking_method=interface_tracking_method,
                phi_primary_redist_every=phi_primary_redist_every,
                phi_primary_clip_factor=phi_primary_clip_factor,
                phi_primary_heaviside_eps_scale=phi_primary_heaviside_eps_scale,
                kappa_max=kappa_max,
                dgr_phi_smooth_C=dgr_phi_smooth_C,
                reinit_eps_scale=reinit_eps_scale,
                ridge_sigma_0=ridge_sigma_0,
            ),
            ppe=SolverPPEOptions(
                ppe_solver=ppe_solver,
                pressure_scheme=pressure_scheme,
                ppe_coefficient_scheme=ppe_coefficient_scheme,
                ppe_interface_coupling_scheme=ppe_interface_coupling_scheme,
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
            ),
            schemes=SolverSchemeOptions(
                hfe_C=hfe_C,
                reinit_steps=reinit_steps,
                cn_viscous=cn_viscous,
                Re=Re,
                surface_tension_scheme=surface_tension_scheme,
                convection_time_scheme=convection_time_scheme,
                advection_scheme=advection_scheme,
                convection_scheme=convection_scheme,
                pressure_gradient_scheme=pressure_gradient_scheme,
                surface_tension_gradient_scheme=surface_tension_gradient_scheme,
                momentum_gradient_scheme=momentum_gradient_scheme,
                viscous_spatial_scheme=viscous_spatial_scheme,
                viscous_time_scheme=(
                    viscous_time_scheme
                    or ("crank_nicolson" if cn_viscous else "forward_euler")
                ),
                cn_mode=cn_mode,
                cn_buoyancy_predictor_assembly_mode=cn_buoyancy_predictor_assembly_mode,
                uccd6_sigma=uccd6_sigma,
                face_flux_projection=face_flux_projection,
                canonical_face_state=canonical_face_state,
                face_native_predictor_state=face_native_predictor_state,
                face_no_slip_boundary_state=face_no_slip_boundary_state,
                preserve_projected_faces=preserve_projected_faces,
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
            reprojector=self._reprojector,
        )
        self.X, self.Y = result.X, result.Y
        self._p_prev = None
        self._p_prev_dev = None
        self._conv_prev = None
        self._conv_ab2_ready = False
        self._velocity_prev = None
        self._velocity_bdf2_ready = False
        reset_ns_runtime_contexts(self)
        return result.psi, result.u, result.v

    # ── initial condition / velocity builders ─────────────────────────────

    def psi_from_phi(self, phi: np.ndarray) -> np.ndarray:
        """Smooth Heaviside ψ = H_ε(φ)."""
        return runtime_psi_from_phi(self._runtime_setup_context(), phi)

    def build_ic(self, cfg: "ExperimentConfig") -> np.ndarray:
        """Build initial ψ field from config ``initial_condition`` section.

        Accepts three YAML formats:

        1. **Builder format** (explicit)::

               initial_condition:
                 background_phase: liquid
                 shapes: [{type: circle, ...}]

        2. **Single-shape shorthand**::

               initial_condition:
                 type: circle
                 center: [0.5, 0.5]
                 radius: 0.25
                 interior_phase: gas

        3. **Union shorthand** (multiple shapes, same background)::

               initial_condition:
                 type: union
                 shapes: [{type: circle, interior_phase: gas, ...}, ...]
        """
        return build_runtime_initial_condition(
            self._runtime_setup_context(),
            cfg.initial_condition,
        )

    def build_velocity(
        self, cfg: "ExperimentConfig", psi: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build initial (u, v) from config ``initial_velocity`` section.

        If ``initial_velocity`` is absent, returns zero fields.
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
    ) -> float:
        """CFL + viscous + capillary timestep limit."""
        return compute_runtime_dt_max(
            self._runtime_timestep_context(),
            u,
            v,
            physics,
            cfl=cfl,
        )

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
        if (
            (self._canonical_face_state or self._preserve_projected_faces)
            and self._projected_face_components is not None
            and hasattr(self._div_op, "reconstruct_nodes")
        ):
            state.face_velocity_components = self._projected_face_components
            state.projected_face_components = self._projected_face_components
            state.u, state.v = self._div_op.reconstruct_nodes(
                self._projected_face_components
            )
        return state

    def _advance_interface_stage(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Advance the interface transport and optional grid rebuild."""
        state.psi = self._transport.advance(
            state.psi, [state.u, state.v], state.dt, step_index=state.step_index
        )
        if (
            self._alpha_grid > 1.0
            and self._interface_runtime.rebuild_freq > 0
            and state.step_index > 0
            and (state.step_index % self._interface_runtime.rebuild_freq == 0)
        ):
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
            self._projected_face_components = None
        return state

    def _materialise_step_fields(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Build density and viscosity fields for the current step."""
        return materialise_ns_step_fields(state)

    def _surface_tension_stage(
        self,
        state: NSStepState,
    ) -> NSStepState:
        """Compute curvature and balanced-force surface tension terms."""
        return compute_ns_surface_tension_stage(
            state,
            backend=self._backend,
            curv=self._curv,
            hfe=self._hfe,
            interface_runtime=self._interface_runtime,
            step_diag=self._step_diag,
            st_force=self._st_force,
            ccd=self._ccd,
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
            surface_tension_scheme=self._surface_tension_scheme,
            face_native_predictor_state=self._face_native_predictor_state,
            bc_type=self.bc_type,
            face_no_slip_boundary_state=self._face_no_slip_boundary_state,
        )
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
            fccd_div_op=self._fccd_div_op,
            div_op=self._div_op,
            ppe_runtime=self._ppe_runtime,
            bc_type=self.bc_type,
            apply_velocity_bc=_apply_bc,
        )

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
        state = self._materialise_step_fields(state)
        state = self._surface_tension_stage(state)
        state = self._predict_velocity_stage(state)
        _apply_bc(state.u_star, state.v_star, state.bc_hook, self.bc_type)
        state = self._solve_pressure_stage(state)
        state = self._correct_velocity_stage(state)
        self._projected_face_components = state.projected_face_components
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
