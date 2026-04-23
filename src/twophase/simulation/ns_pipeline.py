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
from ..core.grid_remap import build_grid_remapper
from ..ccd.ccd_solver import CCDSolver
from ..ccd.fccd import FCCDSolver
from ..levelset.heaviside import apply_mass_correction
from ..levelset.reconstruction import ReconstructionConfig, HeavisideInterfaceReconstructor
from ..levelset.interfaces import ILevelSetAdvection
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
    IGradientOperator,
    CCDGradientOperator, FCCDGradientOperator, FVMGradientOperator,  # registration
    IDivergenceOperator, CCDDivergenceOperator, FVMDivergenceOperator,
    FCCDDivergenceOperator,
)
from .scheme_build_ctx import (
    GradientBuildCtx, AdvectionBuildCtx, ConvectionBuildCtx,
    ReprojectorBuildCtx, SurfaceTensionBuildCtx, ViscousBuildCtx, PPEBuildCtx,
)
from ..levelset.curvature_filter import InterfaceLimitedFilter
from ..ns_terms.interfaces import IConvectionTerm
from ..ns_terms.convection import ConvectionTerm                      # registration
from ..ns_terms.fccd_convection import FCCDConvectionTerm             # registration
from ..ns_terms.uccd6_convection import UCCD6ConvectionTerm           # registration
from ..ns_terms.context import NSComputeContext
from ..ppe.interfaces import IPPESolver
from ..ppe.defect_correction import PPESolverDefectCorrection
from ..ppe.fccd_matrixfree import PPESolverFCCDMatrixFree              # registration
from ..ppe.fvm_matrixfree import PPESolverFVMMatrixFree                # registration
from ..ppe.fvm_spsolve import PPESolverFVMSpsolve                      # registration
from ..ppe.iim.stencil_corrector import IIMStencilCorrector
from .runtime_setup import (
    apply_velocity_bc as _apply_bc,
    build_initial_condition,
    build_initial_velocity,
    infer_background as _infer_background,
    make_boundary_condition_hook,
    normalise_ic_dict as _normalise_ic_dict,
    wall_bc_hook as _wall_bc_hook,
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
        self.NX, self.NY = NX, NY
        self.LX, self.LY = LX, LY
        self.bc_type = bc_type
        self._alpha_grid = alpha_grid
        self._eps_factor = eps_factor
        self._eps_xi_cells = eps_xi_cells
        self._use_local_eps = use_local_eps or (eps_xi_cells is not None)
        # grid_rebuild_freq == 0 → static non-uniform grid (build once from IC,
        # never rebuild). This avoids rebuild-driven metric discontinuity
        # (WIKI-X-012 Mode 1) entirely.
        self._rebuild_freq = int(grid_rebuild_freq)
        if self._rebuild_freq < 0:
            self._rebuild_freq = 0
        self._reinit_every = int(reinit_every)
        self._reproject_variable_density = bool(reproject_variable_density)
        self._interface_tracking_enabled = bool(interface_tracking_enabled)
        if not self._interface_tracking_enabled:
            self._interface_tracking_method = "none"
        else:
            if interface_tracking_method is None:
                interface_tracking_method = (
                    "phi_primary" if bool(phi_primary_transport) else "psi_direct"
                )
            self._interface_tracking_method = str(interface_tracking_method).strip().lower()
            if self._interface_tracking_method == "phi":
                self._interface_tracking_method = "phi_primary"
            elif self._interface_tracking_method == "psi":
                self._interface_tracking_method = "psi_direct"
            elif self._interface_tracking_method == "none":
                self._interface_tracking_enabled = False
        if self._interface_tracking_method not in {"phi_primary", "psi_direct", "none"}:
            raise ValueError(
                "Unsupported interface_tracking_method="
                f"'{interface_tracking_method}'. Use phi_primary|psi_direct|none."
            )
        self._phi_primary_transport = (
            bool(phi_primary_transport)
            if self._interface_tracking_method not in {"phi_primary", "psi_direct"}
            else self._interface_tracking_method == "phi_primary"
        )
        self._phi_primary_redist_every = max(1, int(phi_primary_redist_every))
        self._phi_primary_clip_factor = max(2.0, float(phi_primary_clip_factor))
        self._phi_primary_heaviside_eps_scale = max(1.0, float(phi_primary_heaviside_eps_scale))
        self._kappa_max = float(kappa_max) if kappa_max is not None else None
        self._face_flux_projection = bool(face_flux_projection)
        self._reinit_eps_scale = float(reinit_eps_scale)
        self._reproject_mode = str(reproject_mode).strip().lower()
        if self._reproject_mode not in {
            "legacy", "variable_density_only", "iim", "gfm",
            "consistent_iim", "consistent_gfm",
        }:
            raise ValueError(
                f"Unsupported reproject_mode='{reproject_mode}'. "
                "Use legacy|variable_density_only|gfm|iim."
            )
        # Backward compatibility: old flag maps to variable-density-only mode.
        if self._reproject_variable_density and self._reproject_mode == "legacy":
            self._reproject_mode = "variable_density_only"

        self._h = LX / NX
        self._eps = eps_factor * self._h

        self._backend = Backend(use_gpu=use_gpu)
        gc = GridConfig(
            ndim=2, N=(NX, NY), L=(LX, LY),
            alpha_grid=alpha_grid,
            eps_g_factor=eps_g_factor,
            eps_g_cells=eps_g_cells,
            dx_min_floor=dx_min_floor,
        )
        self._grid = Grid(gc, self._backend)
        self._ccd = CCDSolver(self._grid, self._backend, bc_type=bc_type)
        _raw_ppe = str(pressure_scheme if pressure_scheme is not None else ppe_solver).strip().lower()
        self._ppe_solver_name = IPPESolver._aliases.get(_raw_ppe, _raw_ppe)
        if self._ppe_solver_name not in IPPESolver._registry:
            raise ValueError(
                f"Unsupported ppe_solver={_raw_ppe!r}. "
                "Use fvm_iterative|fvm_direct|fccd_iterative."
            )
        self._ppe_iteration_method = str(ppe_iteration_method).strip().lower()
        self._ppe_coefficient_scheme = str(ppe_coefficient_scheme).strip().lower()
        self._ppe_interface_coupling_scheme = str(
            ppe_interface_coupling_scheme
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
        self._ppe_tolerance = float(ppe_tolerance)
        self._ppe_max_iterations = int(ppe_max_iterations)
        self._ppe_restart = ppe_restart
        self._ppe_preconditioner = str(ppe_preconditioner).strip().lower()
        self._ppe_pcr_stages = ppe_pcr_stages
        self._ppe_c_tau = float(ppe_c_tau)
        self._ppe_defect_correction = bool(ppe_defect_correction)
        self._ppe_dc_max_iterations = int(ppe_dc_max_iterations)
        self._ppe_dc_tolerance = float(ppe_dc_tolerance)
        self._ppe_dc_relaxation = float(ppe_dc_relaxation)
        self._pressure_scheme = (
            "fvm_matrixfree" if self._ppe_solver_name == "fvm_iterative"
            else "fvm_spsolve" if self._ppe_solver_name == "fvm_direct"
            else "fccd_matrixfree"
        )
        self._p_prev = None
        self._p_prev_dev = None
        self._reproj_iim = IIMStencilCorrector(self._grid, mode="hermite")

        # eps field: ξ空間セル数ベース or 従来のlocal eps or スカラー
        eps_curv = self._make_eps_field() if self._use_local_eps and alpha_grid > 1.0 else self._eps
        self._curv = CurvatureCalculator(self._backend, self._ccd, eps_curv)
        self._hfe = InterfaceLimitedFilter(self._backend, self._ccd, C=hfe_C)

        _CONV_TIME_ALIASES = {
            "adams_bashforth_2": "ab2", "adams_bashforth": "ab2", "ab_2": "ab2",
            "explicit": "ab2", "forward_euler": "forward_euler",
            "euler": "forward_euler",
        }
        _raw_cts = str(convection_time_scheme).strip().lower()
        self._convection_time_scheme = _CONV_TIME_ALIASES.get(_raw_cts, _raw_cts)
        if self._convection_time_scheme not in {"ab2", "forward_euler"}:
            raise ValueError(
                "Unsupported convection_time_scheme="
                f"{self._convection_time_scheme!r}; use ab2|forward_euler."
            )
        self._conv_prev = None
        self._conv_ab2_ready = False
        self._momentum_gradient_scheme = str(momentum_gradient_scheme).strip().lower()
        self._pressure_gradient_scheme = str(
            pressure_gradient_scheme or self._momentum_gradient_scheme
        ).strip().lower()
        _raw_st_scheme = str(surface_tension_scheme).strip().lower()
        if _raw_st_scheme == "pressure_jump":
            if surface_tension_gradient_scheme not in {None, "none"}:
                raise ValueError(
                    "surface_tension_gradient_scheme must be omitted or 'none' "
                    "when surface_tension_scheme='pressure_jump'"
                )
            self._surface_tension_gradient_scheme = "none"
        else:
            self._surface_tension_gradient_scheme = str(
                surface_tension_gradient_scheme or self._momentum_gradient_scheme
            ).strip().lower()

        # FCCDSolver: created first so FCCDDivergenceOperator can use it below.
        # One shared instance reuses the CCD LU factorisation — mirrors builder.py
        # §"one factorisation, many calls".
        _FCCD_NAMES = frozenset({"fccd_flux", "fccd_nodal", "fccd_iterative"})
        needs_fccd = bool(
            {
                str(advection_scheme), str(convection_scheme),
                self._pressure_gradient_scheme, self._surface_tension_gradient_scheme,
                self._ppe_solver_name,
            }
            & _FCCD_NAMES
        )
        self._fccd = (
            FCCDSolver(self._grid, self._backend, bc_type=bc_type, ccd_solver=self._ccd)
            if needs_fccd else None
        )

        # Momentum gradient / divergence operators.
        # _div_op: PPE RHS divergence.  FCCD PPE uses FCCD face-flux divergence;
        # legacy non-uniform wall runs retain the FVM divergence from WIKI-T-068.
        # _fccd_div_op: face-flux projector with O(h⁴) FCCD face values.
        ccd_grad_op: IGradientOperator = CCDGradientOperator(self._backend, self._ccd, bc_type=bc_type)
        self._fccd_div_op: FCCDDivergenceOperator | None = (
            FCCDDivergenceOperator(self._fccd)
            if self._fccd is not None
            else None
        )
        if self._ppe_solver_name == "fccd_iterative":
            if self._fccd_div_op is None:
                raise RuntimeError("FCCD PPE requires FCCDDivergenceOperator")
            self._div_op = self._fccd_div_op
        elif not self._grid.uniform and bc_type == "wall":
            self._div_op: IDivergenceOperator = FVMDivergenceOperator(self._backend, self._grid)
        else:
            self._div_op = CCDDivergenceOperator(self._ccd)

        if self._fccd_div_op is not None:
            self._face_flux_projection = True
        self._ppe_solver = self._build_ppe_solver(self._ppe_solver_name)

        # Gradient operators — each scheme class decides its own construction.
        grad_ctx = GradientBuildCtx(ccd_op=ccd_grad_op, fccd=self._fccd)
        self._pressure_grad_op = IGradientOperator.from_scheme(
            self._pressure_gradient_scheme, grad_ctx
        )
        self._surface_tension_grad_op = (
            None if self._surface_tension_gradient_scheme == "none"
            else IGradientOperator.from_scheme(self._surface_tension_gradient_scheme, grad_ctx)
        )
        self._grad_op = self._pressure_grad_op

        # Advection scheme — scheme class decides its own construction.
        adv_ctx = AdvectionBuildCtx(
            backend=self._backend, grid=self._grid,
            ccd=self._ccd, bc_type=bc_type, fccd=self._fccd,
        )
        self._advection_scheme = str(advection_scheme)
        self._adv = ILevelSetAdvection.from_scheme(self._advection_scheme, adv_ctx)

        # Convection term — single slot; CCD, FCCD, and UCCD6 all return IConvectionTerm.
        self._convection_scheme = str(convection_scheme)
        conv_ctx = ConvectionBuildCtx(
            backend=self._backend, ccd=self._ccd, grid=self._grid,
            fccd=self._fccd, uccd6_sigma=float(uccd6_sigma),
        )
        self._conv_term: IConvectionTerm = IConvectionTerm.from_scheme(
            self._convection_scheme, conv_ctx
        )
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
        # Reinit uses conservative scalar eps (Option C: memo §4.2)
        # DGR is grid-agnostic (cell_volumes() based mass correction, logit inversion).
        # SplitReinitializer's CN diffusion assumes uniform h = L/N — causes accumulated
        # diffusion even on uniform grids (transition width grows to ~1.0 vs ε≈0.023).
        self._reinit = Reinitializer(
            self._backend, self._grid, self._ccd, self._eps,
            n_steps=reinit_steps, method=reinit_method,
            phi_smooth_C=dgr_phi_smooth_C,
            eps_scale=self._reinit_eps_scale,
            sigma_0=float(ridge_sigma_0),
        )

        # Level-set transport strategy (advection + reinit + redistancing)
        if not self._interface_tracking_enabled:
            self._transport = StaticInterfaceTransport(self._backend)
        elif self._phi_primary_transport:
            self._transport = PhiPrimaryTransport(
                self._backend,
                {
                    "redist_every": phi_primary_redist_every,
                    "clip_factor": phi_primary_clip_factor,
                    "eps_scale": phi_primary_heaviside_eps_scale,
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
                reinit_every=reinit_every,
            )

        self.X, self.Y = self._grid.meshgrid()

        # Step diagnostics strategy (Null Object pattern)
        self._step_diag = (
            ActiveStepDiagnostics() if debug_diagnostics else NullStepDiagnostics()
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
        self._cn_viscous = cn_viscous
        self._Re = Re
        self._viscous_spatial_scheme = str(viscous_spatial_scheme)
        from ..ns_terms.viscous import ViscousTerm
        _viscous_term = ViscousTerm(
            self._backend,
            Re=Re,
            cn_viscous=True,
            spatial_scheme=self._viscous_spatial_scheme,
        )
        _viscous_scheme = "crank_nicolson" if cn_viscous else "explicit"
        viscous_ctx = ViscousBuildCtx(
            backend=self._backend,
            re=Re,
            spatial_scheme=self._viscous_spatial_scheme,
            viscous_term=_viscous_term,
        )
        self._viscous_predictor: IViscousPredictor = IViscousPredictor.from_scheme(
            _viscous_scheme, viscous_ctx
        )

        # Surface tension strategy — scheme class decides its own construction.
        self._surface_tension_scheme = str(surface_tension_scheme)
        st_ctx = SurfaceTensionBuildCtx(backend=self._backend)
        self._st_force: INSSurfaceTensionStrategy = INSSurfaceTensionStrategy.from_scheme(
            self._surface_tension_scheme, st_ctx
        )

    # ── PPE solver dispatch (pressure_scheme) ─────────────────────────────

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
        ppe_solver = pressure_scheme
        if self._ppe_defect_correction:
            base_solver = self._build_plain_ppe_solver(ppe_solver)
            # DC outer operator: matrix-free without preconditioner (used for residual)
            from ..core.boundary import BoundarySpec
            _op_bc_spec = BoundarySpec(
                bc_type=self.bc_type,
                shape=tuple(n + 1 for n in self._grid.N),
                N=self._grid.N,
            )
            _op_ctx = PPEBuildCtx(
                backend=self._backend, grid=self._grid,
                bc_type=self.bc_type, bc_spec=_op_bc_spec,
                config=self._build_ppe_cfg_shim(preconditioner="none"),
                fccd=self._fccd,
            )
            operator = IPPESolver.from_scheme(ppe_solver, _op_ctx)
            return PPESolverDefectCorrection(
                self._backend,
                self._grid,
                base_solver,
                operator,
                max_corrections=self._ppe_dc_max_iterations,
                tolerance=self._ppe_dc_tolerance,
                relaxation=self._ppe_dc_relaxation,
            )
        return self._build_plain_ppe_solver(ppe_solver)

    def _build_plain_ppe_solver(self, ppe_scheme: str):
        """Instantiate an unwrapped PPE solver via registry."""
        from ..core.boundary import BoundarySpec

        bc_spec = BoundarySpec(
            bc_type=self.bc_type,
            shape=tuple(n + 1 for n in self._grid.N),
            N=self._grid.N,
        )
        cfg_shim = (
            self._build_ppe_cfg_shim(
                preconditioner=self._ppe_preconditioner,
                pcr_stages=self._ppe_pcr_stages,
            )
            if ppe_scheme in {"fvm_iterative", "fccd_iterative"} else None
        )
        ppe_ctx = PPEBuildCtx(
            backend=self._backend, grid=self._grid,
            bc_type=self.bc_type, bc_spec=bc_spec, config=cfg_shim,
            fccd=self._fccd,
        )
        return IPPESolver.from_scheme(ppe_scheme, ppe_ctx)

    def _build_ppe_cfg_shim(
        self,
        *,
        preconditioner: str | None = None,
        pcr_stages: int | None = None,
    ):
        """Build the SimpleNamespace config shim for PPESolverFVMMatrixFree."""
        from types import SimpleNamespace

        return SimpleNamespace(
            solver=SimpleNamespace(
                pseudo_tol=self._ppe_tolerance,
                pseudo_maxiter=self._ppe_max_iterations,
                pseudo_c_tau=self._ppe_c_tau,
                ppe_iteration_method=self._ppe_iteration_method,
                ppe_restart=self._ppe_restart,
                ppe_preconditioner=preconditioner or "none",
                ppe_pcr_stages=pcr_stages,
                ppe_coefficient_scheme=self._ppe_coefficient_scheme,
                ppe_interface_coupling_scheme=self._ppe_interface_coupling_scheme,
            )
        )

    # ── class-method constructors ─────────────────────────────────────────

    @classmethod
    def from_config(cls, cfg: "ExperimentConfig") -> "TwoPhaseNSSolver":
        """Construct from an :class:`ExperimentConfig`."""
        g = cfg.grid
        return cls(
            g.NX, g.NY, g.LX, g.LY,
            bc_type=g.bc_type,
            alpha_grid=getattr(g, "alpha_grid", 1.0),
            eps_factor=getattr(g, "eps_factor", 1.5),
            eps_g_factor=getattr(g, "eps_g_factor", 2.0),
            eps_g_cells=getattr(g, "eps_g_cells", None),
            dx_min_floor=getattr(g, "dx_min_floor", 1e-6),
            use_local_eps=getattr(g, "use_local_eps", False),
            eps_xi_cells=getattr(g, "eps_xi_cells", None),
            grid_rebuild_freq=getattr(g, "grid_rebuild_freq", 1),
            reinit_every=getattr(getattr(cfg, "run", g), "reinit_every", 2),
            reinit_method=(
                getattr(getattr(cfg, "run", g), "reinit_method", None) or "eikonal_xi"
            ),
            cn_viscous=getattr(getattr(cfg, "run", g), "cn_viscous", False),
            Re=getattr(getattr(cfg, "physics", g), "Re", 1.0),
            reproject_variable_density=getattr(
                getattr(cfg, "run", g), "reproject_variable_density", False,
            ),
            reproject_mode=getattr(
                getattr(cfg, "run", g), "reproject_mode", "legacy",
            ),
            phi_primary_transport=bool(
                getattr(getattr(cfg, "run", g), "phi_primary_transport", True)
            ),
            interface_tracking_enabled=bool(
                getattr(getattr(cfg, "run", g), "interface_tracking_enabled", True)
            ),
            interface_tracking_method=str(
                getattr(getattr(cfg, "run", g), "interface_tracking_method", "phi_primary")
            ),
            phi_primary_redist_every=int(
                getattr(getattr(cfg, "run", g), "phi_primary_redist_every", 4)
            ),
            phi_primary_clip_factor=float(
                getattr(getattr(cfg, "run", g), "phi_primary_clip_factor", 12.0)
            ),
            phi_primary_heaviside_eps_scale=float(
                getattr(getattr(cfg, "run", g), "phi_primary_heaviside_eps_scale", 1.0)
            ),
            kappa_max=getattr(getattr(cfg, "run", g), "kappa_max", None),
            dgr_phi_smooth_C=float(
                getattr(getattr(cfg, "run", g), "dgr_phi_smooth_C", 1e-4)
            ),
            reinit_eps_scale=float(cfg.run.reinit_eps_scale),
            ridge_sigma_0=float(
                getattr(getattr(cfg, "run", g), "ridge_sigma_0", 3.0)
            ),
            advection_scheme=str(
                getattr(getattr(cfg, "run", g), "advection_scheme", "dissipative_ccd")
            ),
            convection_scheme=str(
                getattr(getattr(cfg, "run", g), "convection_scheme", "ccd")
            ),
            ppe_solver=str(
                getattr(getattr(cfg, "run", g), "ppe_solver", "fvm_iterative")
            ),
            pressure_scheme=str(
                getattr(getattr(cfg, "run", g), "pressure_scheme", "fvm_matrixfree")
            ),
            ppe_coefficient_scheme=str(
                getattr(getattr(cfg, "run", g), "ppe_coefficient_scheme", "phase_density")
            ),
            ppe_interface_coupling_scheme=str(
                getattr(getattr(cfg, "run", g), "ppe_interface_coupling_scheme", "none")
            ),
            ppe_iteration_method=str(
                getattr(getattr(cfg, "run", g), "ppe_iteration_method", "gmres")
            ),
            ppe_tolerance=float(
                getattr(getattr(cfg, "run", g), "ppe_tolerance", 1.0e-8)
            ),
            ppe_max_iterations=int(
                getattr(getattr(cfg, "run", g), "ppe_max_iterations", 500)
            ),
            ppe_restart=getattr(getattr(cfg, "run", g), "ppe_restart", 80),
            ppe_preconditioner=str(
                getattr(getattr(cfg, "run", g), "ppe_preconditioner", "line_pcr")
            ),
            ppe_pcr_stages=getattr(getattr(cfg, "run", g), "ppe_pcr_stages", 4),
            ppe_c_tau=float(getattr(getattr(cfg, "run", g), "ppe_c_tau", 2.0)),
            ppe_defect_correction=bool(
                getattr(getattr(cfg, "run", g), "ppe_defect_correction", False)
            ),
            ppe_dc_max_iterations=int(
                getattr(getattr(cfg, "run", g), "ppe_dc_max_iterations", 0)
            ),
            ppe_dc_tolerance=float(
                getattr(getattr(cfg, "run", g), "ppe_dc_tolerance", 0.0)
            ),
            ppe_dc_relaxation=float(
                getattr(getattr(cfg, "run", g), "ppe_dc_relaxation", 1.0)
            ),
            surface_tension_scheme=str(
                getattr(getattr(cfg, "run", g), "surface_tension_scheme", "csf")
            ),
            convection_time_scheme=str(
                getattr(getattr(cfg, "run", g), "convection_time_scheme", "ab2")
            ),
            viscous_spatial_scheme=str(
                getattr(getattr(cfg, "run", g), "viscous_spatial_scheme", "ccd_bulk")
            ),
            pressure_gradient_scheme=str(
                getattr(
                    getattr(cfg, "run", g),
                    "pressure_gradient_scheme",
                    "projection_consistent",
                )
            ),
            surface_tension_gradient_scheme=str(
                getattr(getattr(cfg, "run", g), "surface_tension_gradient_scheme")
            ),
            momentum_gradient_scheme=str(
                getattr(getattr(cfg, "run", g), "momentum_gradient_scheme", "projection_consistent")
            ),
            uccd6_sigma=float(
                getattr(getattr(cfg, "run", g), "uccd6_sigma", 1.0e-3)
            ),
            face_flux_projection=bool(
                getattr(getattr(cfg, "run", g), "face_flux_projection", False)
            ),
            debug_diagnostics=bool(getattr(getattr(cfg, "run", g), "debug_diagnostics", False)),
        )

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
        if self._alpha_grid <= 1.0:
            return psi, u, v

        # 1. Save old grid state for interpolation
        old_coords = [c.copy() for c in self._grid.coords]
        old_h = [h.copy() for h in self._grid.h]

        # 2. Compute old cell volumes / mass on the active device to avoid
        #    per-rebuild D2H round-trips on the GPU path.
        xp = self._backend.xp
        dV_old = xp.asarray(old_h[0])
        for ax in range(1, self._grid.ndim):
            dV_old = xp.expand_dims(dV_old, axis=ax) * xp.asarray(old_h[ax])
        psi_dev = xp.asarray(psi)
        M_before = xp.sum(psi_dev * dV_old)

        # 3. Rebuild grid from ψ (mutates coords, h, J, dJ_dxi in-place)
        self._grid.update_from_levelset(psi, self._eps, ccd=self._ccd)

        # 4. Remap psi, u, v from old grid to new grid.
        remapper = build_grid_remapper(self._backend, old_coords, self._grid.coords)
        psi = xp.clip(xp.asarray(remapper.remap(psi)), 0.0, 1.0)
        u = xp.asarray(remapper.remap(u))
        v = xp.asarray(remapper.remap(v))

        # 5. Mass correction for psi
        dV_new = self._grid.cell_volumes()
        psi = apply_mass_correction(xp, psi, dV_new, M_before)

        # 6. Update meshgrid cache.
        self.X, self.Y = self._grid.meshgrid()

        # 8. Update curvature eps_field for local-eps mode
        if self._use_local_eps:
            self._curv.eps = self._make_eps_field()

        # 8b. CHK-159/160/175: refresh grid-dependent caches via interfaces.
        self._reinit.update_grid(self._grid)
        self._ppe_solver.update_grid(self._grid)
        self._ppe_solver.invalidate_cache()
        if self._fccd_div_op is not None:
            self._fccd_div_op.update_weights()
        self._p_prev = None
        self._p_prev_dev = None
        self._conv_prev = None
        self._conv_ab2_ready = False

        # 9. Velocity re-projection: linear interpolation of (u, v) does not
        #    preserve ∇·u = 0. Solve a PPE to remove the spurious divergence
        #    introduced by the remap.  Without this step the remapped velocity
        #    has O(h) divergence which drives exponential KE growth.
        # Strategy pattern: reprojector encapsulates legacy/variable-density/IIM logic.
        u, v = self._reprojector.reproject(
            psi, u, v, self._ppe_solver, self._ccd, self._backend,
            rho_l=rho_l, rho_g=rho_g,
        )

        # Return device arrays — callers expect the same device type as input.
        return xp.asarray(psi), xp.asarray(u), xp.asarray(v)

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
        ccd = self._ccd
        xp = self._backend.xp

        if rho_ref is None:
            rho_ref = 0.5 * (rho_l + rho_g)

        # Helper: device→host, safe for both numpy and cupy arrays.
        # Used ONLY for stage-1 (phi-primary transport) and grid rebuild
        # which are CPU-bound algorithms.  Stages 2-5 stay device-resident.
        def _h(arr): return np.asarray(self._backend.to_host(arr))

        # Promote inputs to device — no-op on CPU backend.
        psi = xp.asarray(psi)
        u = xp.asarray(u)
        v = xp.asarray(v)

        # ── 1. Advect + reinitialize ───────────────────────────────────
        # Strategy pattern: transport encapsulates phi-primary vs psi-direct logic
        psi = self._transport.advance(psi, [u, v], dt, step_index=step_index)

        # ── 1b. Grid rebuild (interface-fitted, every rebuild_freq steps)
        # rebuild_freq == 0 → static grid, never rebuild during time-stepping.
        if (
            self._alpha_grid > 1.0
            and self._rebuild_freq > 0
            and step_index > 0
            and (step_index % self._rebuild_freq == 0)
        ):
            # Keep the rebuild/remap path on the active backend as far as
            # possible; Grid.update_from_levelset() still hostifies internally,
            # but remap/mass-correction/reprojection can remain device-resident.
            try:
                psi, u, v = self._rebuild_grid(
                    psi, u, v, rho_l=rho_l, rho_g=rho_g,
                )
            except TypeError:
                # Backward compatibility for experiment monkey-patches that
                # replace _rebuild_grid(psi, u, v) with a 3-arg lambda.
                psi, u, v = self._rebuild_grid(psi, u, v)

        # All arrays below are device-resident (xp namespace).
        rho = rho_g + (rho_l - rho_g) * psi

        # Variable viscosity (recomputed after advection so μ tracks ψ)
        if mu_l is not None and mu_g is not None:
            mu_field = mu_g + (mu_l - mu_g) * psi
        else:
            mu_field = mu  # scalar or pre-computed array

        # ── 2. Curvature + balanced-force CSF ──────────────────────────
        # Compute curvature (used for diagnostics + surface tension force)
        kappa_raw = self._curv.compute(psi)
        kappa = self._hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi))
        if self._kappa_max is not None:
            kappa = xp.clip(kappa, -self._kappa_max, self._kappa_max)
        debug_scalars = None
        if isinstance(self._step_diag, ActiveStepDiagnostics):
            debug_scalars = [xp.max(xp.abs(kappa))]

        # Strategy pattern: surface tension force encapsulates σ > 0 check.
        # R-1.5: Pass the configured ∇ψ operator for non-uniform grids.
        f_x, f_y = self._st_force.compute(
            kappa, psi, sigma, ccd, grad_op=self._surface_tension_grad_op
        )

        # ── 3. NS predictor ────────────────────────────────────────────

        # Momentum convection: CCD, FCCD (SP-D §6/§7), or UCCD6 (WIKI-X-023).
        # All return −(u·∇)u componentwise via the registered IConvectionTerm.
        _conv_ctx = NSComputeContext(velocity=[u, v], ccd=ccd, rho=rho, mu=mu_field)
        _conv = self._conv_term.compute(_conv_ctx)
        conv_u = _conv[0]
        conv_v = _conv[1]

        # Buoyancy (applied to explicit RHS before viscous step)
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

        # Strategy pattern: viscous predictor encapsulates CN vs Explicit logic
        u_star, v_star = self._viscous_predictor.predict(
            u, v, conv_step_u, conv_step_v, mu_field, rho, dt, ccd,
            buoy_v=buoy_v, psi=psi,
        )

        _apply_bc(u_star, v_star, bc_hook, self.bc_type)

        # ── 4. PPE (balanced-force) ─────────────────────────────────────
        rhs = self._div_op.divergence([u_star, v_star]) / dt
        # Add balanced-force CSF contribution if σ > 0 (zero forces when σ ≤ 0)
        rhs = rhs + self._div_op.divergence([f_x / rho, f_y / rho])
        if debug_scalars is not None:
            debug_scalars.append(xp.max(xp.abs(rhs)))
        if hasattr(self._ppe_solver, "set_interface_jump_context"):
            jump_sigma = sigma if self._surface_tension_scheme == "pressure_jump" else 0.0
            self._ppe_solver.set_interface_jump_context(
                psi=psi, kappa=kappa, sigma=jump_sigma
            )
        p = self._ppe_solver.solve(rhs, rho, dt=dt, p_init=self._p_prev_dev)
        self._p_prev_dev = getattr(self._ppe_solver, "last_base_pressure", p)
        self._p_prev = np.asarray(self._backend.to_host(self._p_prev_dev))
        p_corrector = (
            self._p_prev_dev if self._surface_tension_scheme == "pressure_jump" else p
        )

        # ── 5. Corrector ───────────────────────────────────────────────
        # Strategy pattern: pressure gradient operator encapsulates CCD vs FVM logic
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
                [u_star, v_star], p_corrector, rho, dt, [f_x / rho, f_y / rho],
                **project_kwargs,
            )
        else:
            u = u_star - dt / rho * dp_dx + dt * f_x / rho
            v = v_star - dt / rho * dp_dy + dt * f_y / rho

        _apply_bc(u, v, bc_hook, self.bc_type)

        if debug_scalars is not None:
            debug_scalars.append(xp.max(xp.abs(self._div_op.divergence([u, v]))))
            dbg = np.asarray(self._backend.to_host(xp.stack(debug_scalars)))
            self._step_diag.record_kappa(float(dbg[0]))
            self._step_diag.record_ppe_rhs(float(dbg[1]))
            self._step_diag.record_bf_residual(float(dbg[2]))
            self._step_diag.record_div_u(float(dbg[3]))
            self._step_diag.record_ppe_stats(
                getattr(self._ppe_solver, "last_diagnostics", {})
            )

        p_out = np.asarray(self._backend.to_host(p)) if self._backend.is_gpu() else p
        return psi, u, v, p_out

    # ── private ───────────────────────────────────────────────────────────
    # (PPE solve and matrix build delegated to self._ppe_solver —  see PPESolverFVMSpsolve)


from .runner import run_simulation
