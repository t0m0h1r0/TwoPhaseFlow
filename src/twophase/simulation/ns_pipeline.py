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
import warnings

from ..backend import Backend
from ..config import GridConfig
from ..core.grid import Grid
from ..ccd.ccd_solver import CCDSolver
from ..ccd.fccd import FCCDSolver
from ..levelset.reconstruction import ReconstructionConfig, HeavisideInterfaceReconstructor
from ..levelset.advection import LevelSetAdvection, DissipativeCCDAdvection  # registration
from ..levelset.fccd_advection import FCCDLevelSetAdvection                  # registration
from ..levelset.curvature import CurvatureCalculator
from ..levelset.reinitialize import Reinitializer
from ..levelset.transport_strategy import (
    ILevelSetTransport, PhiPrimaryTransport, PsiDirectTransport,
    StaticInterfaceTransport,
)
from .step_diagnostics import IStepDiagnostics, NullStepDiagnostics, ActiveStepDiagnostics
from .velocity_reprojector import (
    IVelocityReprojector,
    LegacyReprojector, VariableDensityReprojector,      # registration
    ConsistentGFMReprojector, ConsistentIIMReprojector,  # registration
)
from .viscous_predictor import (
    IViscousPredictor,
    ExplicitViscousPredictor, CNViscousPredictor,  # registration
)
from .surface_tension_strategy import (
    INSSurfaceTensionStrategy,
    SurfaceTensionForce, NullSurfaceTensionForce, PressureJumpSurfaceTension,  # registration
)
from .gradient_operator import (
    CCDGradientOperator, FCCDGradientOperator, FVMGradientOperator,  # registration
    CCDDivergenceOperator, FVMDivergenceOperator, FCCDDivergenceOperator,
)
from .ns_operator_stack import NSOperatorStackOptions, build_ns_operator_stack
from .ns_grid_rebuild import rebuild_ns_grid
from .scheme_build_ctx import ReprojectorBuildCtx, SurfaceTensionBuildCtx, ViscousBuildCtx
from ..levelset.curvature_filter import InterfaceLimitedFilter
from ..ns_terms.convection import ConvectionTerm                      # registration
from ..ns_terms.fccd_convection import FCCDConvectionTerm             # registration
from ..ns_terms.uccd6_convection import UCCD6ConvectionTerm           # registration
from ..ns_terms.context import NSComputeContext
from ..ppe.interfaces import IPPESolver
from ..ppe.fccd_matrixfree import PPESolverFCCDMatrixFree              # registration
from ..ppe.fvm_matrixfree import PPESolverFVMMatrixFree                # registration
from ..ppe.fvm_spsolve import PPESolverFVMSpsolve                      # registration
from ..ppe.iim.stencil_corrector import IIMStencilCorrector
from .ns_runtime_factories import (
    NSPPEFactoryOptions,
    build_ns_ppe_cfg_shim,
    build_ns_ppe_solver,
    build_ns_plain_ppe_solver,
    build_ns_reinitializer,
)
from .runtime_setup import (
    apply_velocity_bc as _apply_bc,
    build_initial_condition,
    build_initial_velocity,
    infer_background as _infer_background,
    make_boundary_condition_hook,
    normalise_ic_dict as _normalise_ic_dict,
    wall_bc_hook as _wall_bc_hook,
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
        uccd6_sigma: float = 1.0e-3,
        face_flux_projection: bool = False,
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
                uccd6_sigma=uccd6_sigma,
                face_flux_projection=face_flux_projection,
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
        self._initialise_geometry(options.grid)
        self._initialise_interface_runtime(options.interface)
        self._initialise_ppe_runtime(
            options.ppe,
            surface_tension_scheme=options.schemes.surface_tension_scheme,
        )
        self._p_prev = None
        self._p_prev_dev = None
        self._reproj_iim = IIMStencilCorrector(self._grid, mode="hermite")
        self._initialise_scheme_runtime(options.schemes)
        self._initialise_operator_stack(options.grid, options.schemes)
        self._reconstruct_base = HeavisideInterfaceReconstructor(
            self._backend,
            ReconstructionConfig(
                eps=self._eps,
                eps_scale=1.0,
                clip_factor=self._phi_primary_clip_factor,
            ),
        )
        self._reconstruct_phi_primary = HeavisideInterfaceReconstructor(
            self._backend,
            ReconstructionConfig(
                eps=self._eps,
                eps_scale=self._phi_primary_heaviside_eps_scale,
                clip_factor=self._phi_primary_clip_factor,
            ),
        )
        self._reinit = self._build_reinitializer(options.interface, options.schemes)

        # Level-set transport strategy (advection + reinit + redistancing)
        if not self._interface_tracking_enabled:
            self._transport = StaticInterfaceTransport(self._backend)
        elif self._phi_primary_transport:
            self._transport = PhiPrimaryTransport(
                self._backend,
                {
                    "redist_every": self._phi_primary_redist_every,
                    "clip_factor": self._phi_primary_clip_factor,
                    "eps_scale": self._phi_primary_heaviside_eps_scale,
                },
                self._reconstruct_phi_primary,
                self._adv,
                self._reinit,
                self._grid,
            )
        else:
            self._transport = PsiDirectTransport(
                self._backend,
                self._adv,
                self._reinit,
                reinit_every=options.interface.reinit_every,
            )

        self.X, self.Y = self._grid.meshgrid()

        # Step diagnostics strategy (Null Object pattern)
        self._step_diag = (
            ActiveStepDiagnostics() if options.schemes.debug_diagnostics else NullStepDiagnostics()
        )

        # Velocity reprojection strategy (after grid rebuild)
        reproj_ctx = ReprojectorBuildCtx(
            iim_stencil_corrector=self._reproj_iim,
            reconstruct_base=self._reconstruct_base,
        )
        self._reprojector: IVelocityReprojector = IVelocityReprojector.from_scheme(
            self._reproject_mode, reproj_ctx
        )

        # Viscous predictor strategy (CN vs Explicit)
        self._cn_viscous = options.schemes.cn_viscous
        self._Re = options.schemes.Re
        self._viscous_spatial_scheme = str(options.schemes.viscous_spatial_scheme)
        from ..ns_terms.viscous import ViscousTerm
        _viscous_term = ViscousTerm(
            self._backend,
            Re=options.schemes.Re,
            cn_viscous=True,
            spatial_scheme=self._viscous_spatial_scheme,
        )
        _viscous_scheme = "crank_nicolson" if options.schemes.cn_viscous else "explicit"
        viscous_ctx = ViscousBuildCtx(
            backend=self._backend,
            re=options.schemes.Re,
            spatial_scheme=self._viscous_spatial_scheme,
            viscous_term=_viscous_term,
        )
        self._viscous_predictor: IViscousPredictor = IViscousPredictor.from_scheme(
            _viscous_scheme, viscous_ctx
        )

        # Surface tension strategy — scheme class decides its own construction.
        self._surface_tension_scheme = str(options.schemes.surface_tension_scheme)
        st_ctx = SurfaceTensionBuildCtx(backend=self._backend)
        self._st_force: INSSurfaceTensionStrategy = INSSurfaceTensionStrategy.from_scheme(
            self._surface_tension_scheme, st_ctx
        )

    def _initialise_geometry(self, options: SolverGridOptions) -> None:
        """Initialise grid geometry and backend state."""
        self.NX, self.NY = options.NX, options.NY
        self.LX, self.LY = options.LX, options.LY
        self.bc_type = options.bc_type
        self._alpha_grid = float(options.alpha_grid)
        self._eps_factor = float(options.eps_factor)
        self._eps_xi_cells = options.eps_xi_cells
        self._use_local_eps = bool(options.use_local_eps) or (options.eps_xi_cells is not None)
        self._h = options.LX / options.NX
        self._eps = self._eps_factor * self._h

        self._backend = Backend(use_gpu=options.use_gpu)
        gc = GridConfig(
            ndim=2,
            N=(options.NX, options.NY),
            L=(options.LX, options.LY),
            alpha_grid=options.alpha_grid,
            eps_g_factor=options.eps_g_factor,
            eps_g_cells=options.eps_g_cells,
            dx_min_floor=options.dx_min_floor,
        )
        self._grid = Grid(gc, self._backend)
        self._ccd = CCDSolver(self._grid, self._backend, bc_type=options.bc_type)

    def _initialise_interface_runtime(self, options: SolverInterfaceOptions) -> None:
        """Normalise interface-tracking and remap controls."""
        self._rebuild_freq = max(0, int(options.grid_rebuild_freq))
        self._reinit_every = int(options.reinit_every)
        self._reproject_variable_density = bool(options.reproject_variable_density)
        self._face_flux_projection = False
        self._reinit_eps_scale = float(options.reinit_eps_scale)
        self._kappa_max = float(options.kappa_max) if options.kappa_max is not None else None

        self._interface_tracking_enabled = bool(options.interface_tracking_enabled)
        tracking_method = options.interface_tracking_method
        if not self._interface_tracking_enabled:
            self._interface_tracking_method = "none"
        else:
            if tracking_method is None:
                tracking_method = (
                    "phi_primary" if bool(options.phi_primary_transport) else "psi_direct"
                )
            self._interface_tracking_method = str(tracking_method).strip().lower()
            if self._interface_tracking_method == "phi":
                self._interface_tracking_method = "phi_primary"
            elif self._interface_tracking_method == "psi":
                self._interface_tracking_method = "psi_direct"
            elif self._interface_tracking_method == "none":
                self._interface_tracking_enabled = False
        if self._interface_tracking_method not in {"phi_primary", "psi_direct", "none"}:
            raise ValueError(
                "Unsupported interface_tracking_method="
                f"'{tracking_method}'. Use phi_primary|psi_direct|none."
            )
        self._phi_primary_transport = (
            bool(options.phi_primary_transport)
            if self._interface_tracking_method not in {"phi_primary", "psi_direct"}
            else self._interface_tracking_method == "phi_primary"
        )
        self._phi_primary_redist_every = max(1, int(options.phi_primary_redist_every))
        self._phi_primary_clip_factor = max(2.0, float(options.phi_primary_clip_factor))
        self._phi_primary_heaviside_eps_scale = max(
            1.0, float(options.phi_primary_heaviside_eps_scale)
        )

        self._reproject_mode = str(options.reproject_mode).strip().lower()
        if self._reproject_mode not in {
            "legacy", "variable_density_only", "iim", "gfm",
            "consistent_iim", "consistent_gfm",
        }:
            raise ValueError(
                f"Unsupported reproject_mode='{options.reproject_mode}'. "
                "Use legacy|variable_density_only|gfm|iim."
            )
        if self._reproject_variable_density and self._reproject_mode == "legacy":
            self._reproject_mode = "variable_density_only"

    def _initialise_ppe_runtime(
        self,
        options: SolverPPEOptions,
        *,
        surface_tension_scheme: str,
    ) -> None:
        """Normalise PPE configuration and validate coupled options."""
        raw_ppe = str(
            options.pressure_scheme if options.pressure_scheme is not None else options.ppe_solver
        ).strip().lower()
        self._ppe_solver_name = IPPESolver._aliases.get(raw_ppe, raw_ppe)
        if self._ppe_solver_name not in IPPESolver._registry:
            raise ValueError(
                f"Unsupported ppe_solver={raw_ppe!r}. "
                "Use fvm_iterative|fvm_direct|fccd_iterative."
            )
        self._ppe_iteration_method = str(options.ppe_iteration_method).strip().lower()
        self._ppe_coefficient_scheme = str(options.ppe_coefficient_scheme).strip().lower()
        self._ppe_interface_coupling_scheme = str(
            options.ppe_interface_coupling_scheme
        ).strip().lower()
        if str(surface_tension_scheme).strip().lower() == "pressure_jump":
            if self._ppe_coefficient_scheme != "phase_separated":
                raise ValueError(
                    "surface_tension_scheme='pressure_jump' requires "
                    "ppe_coefficient_scheme='phase_separated'"
                )
            if self._ppe_interface_coupling_scheme != "jump_decomposition":
                raise ValueError(
                    "surface_tension_scheme='pressure_jump' requires "
                    "ppe_interface_coupling_scheme='jump_decomposition'"
                )

        self._ppe_tolerance = float(options.ppe_tolerance)
        self._ppe_max_iterations = int(options.ppe_max_iterations)
        self._ppe_restart = options.ppe_restart
        self._ppe_preconditioner = str(options.ppe_preconditioner).strip().lower()
        self._ppe_pcr_stages = options.ppe_pcr_stages
        self._ppe_c_tau = float(options.ppe_c_tau)
        self._ppe_defect_correction = bool(options.ppe_defect_correction)
        self._ppe_dc_max_iterations = int(options.ppe_dc_max_iterations)
        self._ppe_dc_tolerance = float(options.ppe_dc_tolerance)
        self._ppe_dc_relaxation = float(options.ppe_dc_relaxation)
        self._pressure_scheme = (
            "fvm_matrixfree" if self._ppe_solver_name == "fvm_iterative"
            else "fvm_spsolve" if self._ppe_solver_name == "fvm_direct"
            else "fccd_matrixfree"
        )

    def _initialise_scheme_runtime(self, options: SolverSchemeOptions) -> None:
        """Normalise scheme selections and stateful time-integration flags."""
        eps_curv = self._make_eps_field() if self._use_local_eps and self._alpha_grid > 1.0 else self._eps
        self._curv = CurvatureCalculator(self._backend, self._ccd, eps_curv)
        self._hfe = InterfaceLimitedFilter(self._backend, self._ccd, C=options.hfe_C)

        conv_time_aliases = {
            "adams_bashforth_2": "ab2",
            "adams_bashforth": "ab2",
            "ab_2": "ab2",
            "explicit": "ab2",
            "forward_euler": "forward_euler",
            "euler": "forward_euler",
        }
        raw_time_scheme = str(options.convection_time_scheme).strip().lower()
        self._convection_time_scheme = conv_time_aliases.get(raw_time_scheme, raw_time_scheme)
        if self._convection_time_scheme not in {"ab2", "forward_euler"}:
            raise ValueError(
                "Unsupported convection_time_scheme="
                f"{self._convection_time_scheme!r}; use ab2|forward_euler."
            )

        self._conv_prev = None
        self._conv_ab2_ready = False
        self._momentum_gradient_scheme = str(options.momentum_gradient_scheme).strip().lower()
        self._pressure_gradient_scheme = str(
            options.pressure_gradient_scheme or self._momentum_gradient_scheme
        ).strip().lower()
        raw_st_scheme = str(options.surface_tension_scheme).strip().lower()
        if raw_st_scheme == "pressure_jump":
            if options.surface_tension_gradient_scheme not in {None, "none"}:
                raise ValueError(
                    "surface_tension_gradient_scheme must be omitted or 'none' "
                    "when surface_tension_scheme='pressure_jump'"
                )
            self._surface_tension_gradient_scheme = "none"
        else:
            self._surface_tension_gradient_scheme = str(
                options.surface_tension_gradient_scheme or self._momentum_gradient_scheme
            ).strip().lower()
        self._advection_scheme = str(options.advection_scheme)
        self._convection_scheme = str(options.convection_scheme)

    def _initialise_operator_stack(
        self,
        grid_options: SolverGridOptions,
        scheme_options: SolverSchemeOptions,
    ) -> None:
        """Build spatial operators and solver strategies."""
        stack = build_ns_operator_stack(
            backend=self._backend,
            grid=self._grid,
            ccd=self._ccd,
            options=NSOperatorStackOptions(
                bc_type=grid_options.bc_type,
                advection_scheme=self._advection_scheme,
                convection_scheme=self._convection_scheme,
                pressure_gradient_scheme=self._pressure_gradient_scheme,
                surface_tension_gradient_scheme=self._surface_tension_gradient_scheme,
                ppe_solver_name=self._ppe_solver_name,
                face_flux_projection=bool(scheme_options.face_flux_projection)
                or bool(self._face_flux_projection),
                uccd6_sigma=float(scheme_options.uccd6_sigma),
            ),
            ppe_options=self._make_ppe_factory_options(self._ppe_solver_name),
        )
        self._fccd = stack.fccd
        self._fccd_div_op = stack.fccd_div_op
        self._div_op = stack.div_op
        self._face_flux_projection = stack.face_flux_projection
        self._ppe_solver = stack.ppe_solver
        self._pressure_grad_op = stack.pressure_grad_op
        self._surface_tension_grad_op = stack.surface_tension_grad_op
        self._grad_op = self._pressure_grad_op
        self._adv = stack.adv
        self._conv_term = stack.conv_term

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
            reinit_steps=scheme_options.reinit_steps,
            reinit_method=interface_options.reinit_method,
            dgr_phi_smooth_C=interface_options.dgr_phi_smooth_C,
            reinit_eps_scale=self._reinit_eps_scale,
            ridge_sigma_0=float(interface_options.ridge_sigma_0),
        )

    # ── PPE solver dispatch (pressure_scheme) ─────────────────────────────

    def _make_ppe_factory_options(self, solver_name: str) -> NSPPEFactoryOptions:
        return NSPPEFactoryOptions(
            solver_name=solver_name,
            tolerance=self._ppe_tolerance,
            max_iterations=self._ppe_max_iterations,
            restart=self._ppe_restart,
            preconditioner=self._ppe_preconditioner,
            pcr_stages=self._ppe_pcr_stages,
            c_tau=self._ppe_c_tau,
            iteration_method=self._ppe_iteration_method,
            coefficient_scheme=self._ppe_coefficient_scheme,
            interface_coupling_scheme=self._ppe_interface_coupling_scheme,
            defect_correction=self._ppe_defect_correction,
            dc_max_iterations=self._ppe_dc_max_iterations,
            dc_tolerance=self._ppe_dc_tolerance,
            dc_relaxation=self._ppe_dc_relaxation,
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
        return build_ns_ppe_solver(
            backend=self._backend,
            grid=self._grid,
            bc_type=self.bc_type,
            fccd=self._fccd,
            options=self._make_ppe_factory_options(pressure_scheme),
        )

    def _build_plain_ppe_solver(self, ppe_scheme: str):
        """Instantiate an unwrapped PPE solver via registry."""
        return build_ns_plain_ppe_solver(
            backend=self._backend,
            grid=self._grid,
            bc_type=self.bc_type,
            fccd=self._fccd,
            options=self._make_ppe_factory_options(ppe_scheme),
        )

    def _build_ppe_cfg_shim(
        self,
        *,
        preconditioner: str | None = None,
        pcr_stages: int | None = None,
    ):
        """Build the SimpleNamespace config shim for PPESolverFVMMatrixFree."""
        return build_ns_ppe_cfg_shim(
            self._make_ppe_factory_options(self._ppe_solver_name),
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
        return result.psi, result.u, result.v

    # ── initial condition / velocity builders ─────────────────────────────

    def psi_from_phi(self, phi: np.ndarray) -> np.ndarray:
        """Smooth Heaviside ψ = H_ε(φ)."""
        return np.asarray(self._backend.to_host(self._reconstruct_base.psi_from_phi(phi)))

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
        return build_initial_condition(self._grid, self._eps, cfg.initial_condition)

    def build_velocity(
        self, cfg: "ExperimentConfig", psi: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build initial (u, v) from config ``initial_velocity`` section.

        If ``initial_velocity`` is absent, returns zero fields.
        """
        return build_initial_velocity(
            self.X,
            self.Y,
            cfg.initial_velocity,
            self._backend.to_host,
        )

    # ── boundary-condition hook factory ──────────────────────────────────

    def make_bc_hook(self, cfg: "ExperimentConfig"):
        """Return a ``bc_hook(u, v)`` callable from config.

        * ``None`` → periodic (no-op)
        * default wall → zeros all 4 boundaries
        * ``boundary_condition.type == 'couette'`` → Couette shear
        """
        return make_boundary_condition_hook(
            cfg.boundary_condition,
            self.bc_type,
            self.LY,
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
        h = self.h_min if self._alpha_grid > 1.0 else self._h
        mu_max = max(
            filter(None, [physics.mu, physics.mu_l, physics.mu_g])
        )
        rho_min = physics.rho_g

        xp = self._backend.xp
        _uv_max = np.asarray(self._backend.to_host(
            xp.stack([xp.max(xp.abs(xp.asarray(u))), xp.max(xp.abs(xp.asarray(v)))])
        ))
        u_max = max(float(_uv_max[0]), float(_uv_max[1]), 1e-10)
        dt_cfl = cfl * h / u_max
        # CN (Heun trapezoid) relaxes viscous CFL by ~2× vs forward Euler
        visc_safety = 0.5 if self._cn_viscous else 0.25
        dt_visc = visc_safety * h ** 2 / (mu_max / rho_min)

        if physics.sigma > 0.0:
            rho_sum = physics.rho_l + physics.rho_g
            dt_cap = 0.25 * np.sqrt(
                rho_sum * h ** 3 / (2.0 * np.pi * physics.sigma)
            )
            return min(dt_cfl, dt_visc, dt_cap)
        return min(dt_cfl, dt_visc)

    def _prepare_step_inputs(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        rho_l: float,
        rho_g: float,
        rho_ref: float | None,
    ) -> tuple["array", "array", "array", float]:
        """Promote step inputs to the active backend and normalise ``rho_ref``."""
        xp = self._backend.xp
        rho_ref = 0.5 * (rho_l + rho_g) if rho_ref is None else rho_ref
        return xp.asarray(psi), xp.asarray(u), xp.asarray(v), float(rho_ref)

    def _advance_interface_stage(
        self,
        psi: "array",
        u: "array",
        v: "array",
        dt: float,
        rho_l: float,
        rho_g: float,
        step_index: int,
    ) -> tuple["array", "array", "array"]:
        """Advance the interface transport and optional grid rebuild."""
        psi = self._transport.advance(psi, [u, v], dt, step_index=step_index)
        if (
            self._alpha_grid > 1.0
            and self._rebuild_freq > 0
            and step_index > 0
            and (step_index % self._rebuild_freq == 0)
        ):
            try:
                psi, u, v = self._rebuild_grid(psi, u, v, rho_l=rho_l, rho_g=rho_g)
            except TypeError:
                psi, u, v = self._rebuild_grid(psi, u, v)
        return psi, u, v

    def _materialise_step_fields(
        self,
        psi: "array",
        rho_l: float,
        rho_g: float,
        mu: float | np.ndarray,
        mu_l: float | None,
        mu_g: float | None,
    ) -> tuple["array", float | np.ndarray]:
        """Build density and viscosity fields for the current step."""
        rho = rho_g + (rho_l - rho_g) * psi
        if mu_l is not None and mu_g is not None:
            mu_field = mu_g + (mu_l - mu_g) * psi
        else:
            mu_field = mu
        return rho, mu_field

    def _surface_tension_stage(
        self,
        psi: "array",
        rho: "array",
        sigma: float,
    ) -> tuple["array", "array", "array", list["array"] | None]:
        """Compute curvature and balanced-force surface tension terms."""
        xp = self._backend.xp
        kappa_raw = self._curv.compute(psi)
        kappa = self._hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi))
        if self._kappa_max is not None:
            kappa = xp.clip(kappa, -self._kappa_max, self._kappa_max)
        debug_scalars = None
        if isinstance(self._step_diag, ActiveStepDiagnostics):
            debug_scalars = [xp.max(xp.abs(kappa))]

        f_x, f_y = self._st_force.compute(
            kappa, psi, sigma, self._ccd, grad_op=self._surface_tension_grad_op
        )
        return kappa, f_x, f_y, debug_scalars

    def _predict_velocity_stage(
        self,
        psi: "array",
        u: "array",
        v: "array",
        rho: "array",
        mu_field: float | np.ndarray,
        dt: float,
        g_acc: float,
        rho_ref: float,
    ) -> tuple["array", "array"]:
        """Advance the momentum predictor stage."""
        xp = self._backend.xp
        conv_ctx = NSComputeContext(velocity=[u, v], ccd=self._ccd, rho=rho, mu=mu_field)
        conv_u, conv_v = self._conv_term.compute(conv_ctx)

        buoy_v = xp.zeros_like(v)
        if g_acc != 0.0:
            buoy_v = -(rho - rho_ref) / rho * g_acc

        if self._convection_time_scheme == "ab2":
            if self._conv_ab2_ready and self._conv_prev is not None:
                conv_step_u = 1.5 * conv_u - 0.5 * self._conv_prev[0]
                conv_step_v = 1.5 * conv_v - 0.5 * self._conv_prev[1]
            else:
                conv_step_u = conv_u
                conv_step_v = conv_v
            self._conv_prev = (xp.copy(conv_u), xp.copy(conv_v))
            self._conv_ab2_ready = True
        else:
            conv_step_u = conv_u
            conv_step_v = conv_v

        return self._viscous_predictor.predict(
            u,
            v,
            conv_step_u,
            conv_step_v,
            mu_field,
            rho,
            dt,
            self._ccd,
            buoy_v=buoy_v,
            psi=psi,
        )

    def _solve_pressure_stage(
        self,
        psi: "array",
        u_star: "array",
        v_star: "array",
        rho: "array",
        dt: float,
        sigma: float,
        kappa: "array",
        f_x: "array",
        f_y: "array",
        debug_scalars: list["array"] | None,
    ) -> tuple["array", "array", list["array"] | None]:
        """Solve PPE and prepare the corrector pressure field."""
        xp = self._backend.xp
        rhs = self._div_op.divergence([u_star, v_star]) / dt
        rhs = rhs + self._div_op.divergence([f_x / rho, f_y / rho])
        if debug_scalars is not None:
            debug_scalars.append(xp.max(xp.abs(rhs)))
        if hasattr(self._ppe_solver, "set_interface_jump_context"):
            jump_sigma = sigma if self._surface_tension_scheme == "pressure_jump" else 0.0
            self._ppe_solver.set_interface_jump_context(psi=psi, kappa=kappa, sigma=jump_sigma)

        p = self._ppe_solver.solve(rhs, rho, dt=dt, p_init=self._p_prev_dev)
        self._p_prev_dev = getattr(self._ppe_solver, "last_base_pressure", p)
        self._p_prev = np.asarray(self._backend.to_host(self._p_prev_dev))
        p_corrector = self._p_prev_dev if self._surface_tension_scheme == "pressure_jump" else p
        return p, p_corrector, debug_scalars

    def _correct_velocity_stage(
        self,
        u_star: "array",
        v_star: "array",
        p_corrector: "array",
        rho: "array",
        dt: float,
        f_x: "array",
        f_y: "array",
        bc_hook,
        debug_scalars: list["array"] | None,
    ) -> tuple["array", "array"]:
        """Apply pressure correction and optional face-flux projection."""
        xp = self._backend.xp
        dp_dx = self._pressure_grad_op.gradient(p_corrector, 0)
        dp_dy = self._pressure_grad_op.gradient(p_corrector, 1)
        if debug_scalars is not None:
            debug_scalars.append(
                xp.maximum(
                    xp.max(xp.abs(dp_dx - f_x / rho)),
                    xp.max(xp.abs(dp_dy - f_y / rho)),
                )
            )
        if self._face_flux_projection:
            proj_op = self._fccd_div_op if self._fccd_div_op is not None else self._div_op
            project_kwargs = {}
            if proj_op is self._fccd_div_op:
                project_kwargs["pressure_gradient"] = (
                    "fccd" if self._ppe_solver_name == "fccd_iterative" else "fvm"
                )
            u, v = proj_op.project(
                [u_star, v_star],
                p_corrector,
                rho,
                dt,
                [f_x / rho, f_y / rho],
                **project_kwargs,
            )
        else:
            u = u_star - dt / rho * dp_dx + dt * f_x / rho
            v = v_star - dt / rho * dp_dy + dt * f_y / rho
        _apply_bc(u, v, bc_hook, self.bc_type)
        return u, v

    def _record_step_diagnostics(
        self,
        debug_scalars: list["array"] | None,
        u: "array",
        v: "array",
    ) -> None:
        """Flush step diagnostics to the active recorder."""
        if debug_scalars is None:
            return
        xp = self._backend.xp
        debug_scalars.append(xp.max(xp.abs(self._div_op.divergence([u, v]))))
        dbg = np.asarray(self._backend.to_host(xp.stack(debug_scalars)))
        self._step_diag.record_kappa(float(dbg[0]))
        self._step_diag.record_ppe_rhs(float(dbg[1]))
        self._step_diag.record_bf_residual(float(dbg[2]))
        self._step_diag.record_div_u(float(dbg[3]))
        self._step_diag.record_ppe_stats(
            getattr(self._ppe_solver, "last_diagnostics", {})
        )

    # ── one NS timestep ───────────────────────────────────────────────────

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
        psi, u, v, rho_ref = self._prepare_step_inputs(psi, u, v, rho_l, rho_g, rho_ref)
        psi, u, v = self._advance_interface_stage(psi, u, v, dt, rho_l, rho_g, step_index)
        rho, mu_field = self._materialise_step_fields(psi, rho_l, rho_g, mu, mu_l, mu_g)
        kappa, f_x, f_y, debug_scalars = self._surface_tension_stage(psi, rho, sigma)
        u_star, v_star = self._predict_velocity_stage(
            psi, u, v, rho, mu_field, dt, g_acc, rho_ref
        )
        _apply_bc(u_star, v_star, bc_hook, self.bc_type)
        p, p_corrector, debug_scalars = self._solve_pressure_stage(
            psi, u_star, v_star, rho, dt, sigma, kappa, f_x, f_y, debug_scalars
        )
        u, v = self._correct_velocity_stage(
            u_star, v_star, p_corrector, rho, dt, f_x, f_y, bc_hook, debug_scalars
        )
        self._record_step_diagnostics(debug_scalars, u, v)

        p_out = np.asarray(self._backend.to_host(p)) if self._backend.is_gpu() else p
        return psi, u, v, p_out

    # ── private ───────────────────────────────────────────────────────────
    # (PPE solve and matrix build delegated to self._ppe_solver —  see PPESolverFVMSpsolve)


from .runner import run_simulation
