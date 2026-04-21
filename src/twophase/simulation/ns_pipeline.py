"""Two-phase NS pipeline: solver setup + one-step integration.

Provides ``TwoPhaseNSSolver`` — a reusable class that wraps the common
5-stage predictor-corrector used in all §13 experiments.
Also provides ``run_simulation()`` for fully config-driven execution.

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
from ..levelset.advection import DissipativeCCDAdvection
from ..levelset.fccd_advection import FCCDLevelSetAdvection
from ..levelset.curvature import CurvatureCalculator
from ..levelset.reinitialize import Reinitializer
from ..levelset.transport_strategy import ILevelSetTransport, PhiPrimaryTransport, PsiDirectTransport
from .step_diagnostics import IStepDiagnostics, NullStepDiagnostics, ActiveStepDiagnostics
from .velocity_reprojector import (
    IVelocityReprojector, LegacyReprojector, VariableDensityReprojector,
    ConsistentGFMReprojector, ConsistentIIMReprojector
)
from .viscous_predictor import IViscousPredictor, ExplicitViscousPredictor, CNViscousPredictor
from .surface_tension_strategy import INSSurfaceTensionStrategy, SurfaceTensionForce, NullSurfaceTensionForce
from .gradient_operator import (
    IGradientOperator, CCDGradientOperator, FVMGradientOperator,
    IDivergenceOperator, CCDDivergenceOperator, FVMDivergenceOperator,
)
from ..levelset.curvature_filter import InterfaceLimitedFilter
from ..ns_terms.fccd_convection import FCCDConvectionTerm
from ..ns_terms.context import NSComputeContext
from ..ppe.fvm_spsolve import PPESolverFVMSpsolve
from ..ppe.iim.stencil_corrector import IIMStencilCorrector
from .initial_conditions.builder import InitialConditionBuilder
from .initial_conditions.velocity_fields import velocity_field_from_dict


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
        phi_primary_redist_every: int = 4,
        phi_primary_clip_factor: float = 12.0,
        phi_primary_heaviside_eps_scale: float = 1.0,
        kappa_max: float | None = None,
        dgr_phi_smooth_C: float = 1e-4,
        reinit_eps_scale: float = 1.0,
        ridge_sigma_0: float = 3.0,
        advection_scheme: str = "dissipative_ccd",
        convection_scheme: str = "ccd",
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
        self._phi_primary_transport = bool(phi_primary_transport)
        self._phi_primary_redist_every = max(1, int(phi_primary_redist_every))
        self._phi_primary_clip_factor = max(2.0, float(phi_primary_clip_factor))
        self._phi_primary_heaviside_eps_scale = max(1.0, float(phi_primary_heaviside_eps_scale))
        self._kappa_max = float(kappa_max) if kappa_max is not None else None
        self._face_flux_projection = bool(face_flux_projection)
        self._reinit_eps_scale = float(reinit_eps_scale)
        self._reproject_mode = str(reproject_mode).strip().lower()
        if self._reproject_mode not in {
            "legacy", "variable_density_only", "consistent_iim", "consistent_gfm",
        }:
            raise ValueError(
                f"Unsupported reproject_mode='{reproject_mode}'. "
                "Use legacy|variable_density_only|consistent_iim|consistent_gfm."
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
        self._ppe_solver = PPESolverFVMSpsolve(self._backend, self._grid, bc_type=bc_type)
        self._reproj_iim = IIMStencilCorrector(self._grid, mode="hermite")

        # eps field: ξ空間セル数ベース or 従来のlocal eps or スカラー
        eps_curv = self._make_eps_field() if self._use_local_eps and alpha_grid > 1.0 else self._eps
        self._curv = CurvatureCalculator(self._backend, self._ccd, eps_curv)
        self._hfe = InterfaceLimitedFilter(self._backend, self._ccd, C=hfe_C)

        # Pressure gradient operator strategy (CCD vs FVM)
        if not self._grid.uniform and bc_type == "wall":
            self._grad_op: IGradientOperator = FVMGradientOperator(self._backend, self._grid)
            self._div_op: IDivergenceOperator = FVMDivergenceOperator(self._backend, self._grid)
        else:
            self._grad_op = CCDGradientOperator(self._backend, self._ccd, bc_type=bc_type)
            self._div_op = CCDDivergenceOperator(self._ccd)

        # Advection / convection scheme selection (CHK-160 bridge for FCCD).
        # One shared FCCDSolver reuses the CCD LU factorisation for both
        # ψ advection and momentum convection — mirrors builder.py §"one
        # factorisation, many calls".  All array ops stay on ``backend.xp``;
        # no host round-trip is added on the hot path.
        self._advection_scheme = str(advection_scheme)
        self._convection_scheme = str(convection_scheme)
        self._fccd_modes = {"fccd_nodal": "node", "fccd_flux": "flux"}
        needs_fccd = (
            self._advection_scheme in self._fccd_modes
            or self._convection_scheme in self._fccd_modes
        )
        self._fccd = (
            FCCDSolver(self._grid, self._backend, bc_type=bc_type, ccd_solver=self._ccd)
            if needs_fccd else None
        )
        if self._advection_scheme in self._fccd_modes:
            # mass_correction stays off: the outer step() already applies
            # w=4ψ(1-ψ) correction on ψ after psi_from_phi; enabling it here
            # would run the same formula on φ (SDF-valued) under
            # phi_primary_transport, where w goes negative in the liquid bulk
            # and scrambles φ.
            self._adv = FCCDLevelSetAdvection(
                self._backend, self._grid, self._fccd,
                mode=self._fccd_modes[self._advection_scheme],
                mass_correction=False,
            )
        else:
            self._adv = DissipativeCCDAdvection(self._backend, self._grid, self._ccd)
        self._fccd_conv = (
            FCCDConvectionTerm(
                self._backend, self._fccd,
                mode=self._fccd_modes[self._convection_scheme],
            )
            if self._convection_scheme in self._fccd_modes else None
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
        if phi_primary_transport:
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
        if self._reproject_mode == "legacy":
            self._reprojector: IVelocityReprojector = LegacyReprojector()
        elif self._reproject_mode == "variable_density_only":
            self._reprojector = VariableDensityReprojector()
        elif self._reproject_mode == "consistent_gfm":
            self._reprojector = VariableDensityReprojector()
        elif self._reproject_mode == "consistent_iim":
            self._reprojector = ConsistentIIMReprojector(
                self._reproj_iim,
                self._reconstruct_base,
            )
        else:
            raise ValueError(f"Unknown reproject_mode: {self._reproject_mode}")

        # Viscous predictor strategy (CN vs Explicit)
        self._cn_viscous = cn_viscous
        self._Re = Re
        if cn_viscous:
            from ..ns_terms.viscous import ViscousTerm
            viscous_term = ViscousTerm(self._backend, Re=Re, cn_viscous=True)
            self._viscous_predictor: IViscousPredictor = CNViscousPredictor(
                self._backend, viscous_term
            )
        else:
            self._viscous_predictor = ExplicitViscousPredictor(self._backend, Re=Re)

        # Surface tension strategy (always SurfaceTensionForce; checks σ > 0 internally)
        self._st_force: INSSurfaceTensionStrategy = SurfaceTensionForce(self._backend)

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
            reinit_method=getattr(getattr(cfg, "run", g), "reinit_method", 'eikonal_xi'),
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

        # 2. Compute old cell volumes for mass correction (host-side)
        dV_old = old_h[0].copy()
        for ax in range(1, self._grid.ndim):
            dV_old = np.expand_dims(dV_old, axis=ax) * old_h[ax]
        psi_host = np.asarray(self._backend.to_host(psi))
        M_before = float(np.sum(psi_host * dV_old))

        # 3. Rebuild grid from ψ (mutates coords, h, J, dJ_dxi in-place)
        self._grid.update_from_levelset(psi, self._eps, ccd=self._ccd)

        # 4. Remap psi, u, v from old grid to new grid.
        remapper = build_grid_remapper(self._backend, old_coords, self._grid.coords)
        psi = np.clip(np.asarray(self._backend.to_host(remapper.remap(psi))), 0.0, 1.0)
        u = np.asarray(self._backend.to_host(remapper.remap(u)))
        v = np.asarray(self._backend.to_host(remapper.remap(v)))

        # 5. Mass correction for psi
        dV_new = np.asarray(self._backend.to_host(self._grid.cell_volumes()))
        psi = np.asarray(apply_mass_correction(np, psi, dV_new, M_before))

        # 6. Update meshgrid cache.
        self.X, self.Y = self._grid.meshgrid()

        # 8. Update curvature eps_field for local-eps mode
        if self._use_local_eps:
            self._curv.eps = self._make_eps_field()

        # 8b. CHK-159: refresh reinitializer grid caches (Ridge-Eikonal h_min/eps_local/FMM).
        if hasattr(self._reinit, 'update_grid'):
            self._reinit.update_grid(self._grid)
        # 8c. CHK-160: invalidate PPE builder coord cache.
        if hasattr(self._ppe_solver, 'ppb') and hasattr(self._ppe_solver.ppb, 'invalidate_gpu_cache'):
            self._ppe_solver.ppb.invalidate_gpu_cache()

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
        xp = self._backend.xp
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
        ic = dict(cfg.initial_condition)
        ic_norm = _normalise_ic_dict(ic)
        builder = InitialConditionBuilder.from_dict(ic_norm)
        return np.asarray(builder.build(self._grid, self._eps))

    def build_velocity(
        self, cfg: "ExperimentConfig", psi: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build initial (u, v) from config ``initial_velocity`` section.

        If ``initial_velocity`` is absent, returns zero fields.
        """
        if cfg.initial_velocity is None:
            return np.zeros(self.X.shape), np.zeros(self.Y.shape)

        spec = dict(cfg.initial_velocity)
        vf = velocity_field_from_dict(spec)
        u, v = vf.compute(self.X, self.Y)
        return (np.asarray(self._backend.to_host(u)),
                np.asarray(self._backend.to_host(v)))

    # ── boundary-condition hook factory ──────────────────────────────────

    def make_bc_hook(self, cfg: "ExperimentConfig"):
        """Return a ``bc_hook(u, v)`` callable from config.

        * ``None`` → periodic (no-op)
        * default wall → zeros all 4 boundaries
        * ``boundary_condition.type == 'couette'`` → Couette shear
        """
        bc_cfg = cfg.boundary_condition

        if bc_cfg is None:
            if self.bc_type == "periodic":
                return None
            return _wall_bc_hook  # standard zero-wall

        bc_type = bc_cfg.get("type", "wall")
        if bc_type == "couette":
            gamma = float(bc_cfg.get("gamma_dot", 1.0))
            U = 0.5 * gamma * self.LY

            def _couette(u: np.ndarray, v: np.ndarray) -> None:
                u[:, 0] = -U
                u[:, -1] = +U
                v[:, 0] = 0.0
                v[:, -1] = 0.0
                u[0, :] = u[1, :]
                u[-1, :] = u[-2, :]

            return _couette

        return _wall_bc_hook

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
            # Grid rebuild is CPU-bound; round-trip through host.
            psi_h, u_h, v_h = _h(psi), _h(u), _h(v)
            try:
                psi_h, u_h, v_h = self._rebuild_grid(
                    psi_h, u_h, v_h, rho_l=rho_l, rho_g=rho_g,
                )
            except TypeError:
                # Backward compatibility for experiment monkey-patches that
                # replace _rebuild_grid(psi, u, v) with a 3-arg lambda.
                psi_h, u_h, v_h = self._rebuild_grid(psi_h, u_h, v_h)
            psi, u, v = xp.asarray(psi_h), xp.asarray(u_h), xp.asarray(v_h)

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
        _dbg_kappa_max = float(self._backend.to_host(xp.max(xp.abs(kappa))))
        self._step_diag.record_kappa(_dbg_kappa_max)

        # Strategy pattern: surface tension force encapsulates σ > 0 check
        f_x, f_y = self._st_force.compute(kappa, psi, sigma, ccd)

        # ── 3. NS predictor ────────────────────────────────────────────
        du_dx, du_xx = ccd.differentiate(u, 0)
        du_dy, du_yy = ccd.differentiate(u, 1)
        dv_dx, dv_xx = ccd.differentiate(v, 0)
        dv_dy, dv_yy = ccd.differentiate(v, 1)

        # Momentum convection: default centred CCD, or FCCD (SP-D §6/§7)
        # when the user opts in. Both return −(u·∇)u componentwise, so the
        # AB2 buffer shape and later viscous/buoyancy arithmetic are
        # unchanged (CHK-158 V9). No D2H is added by this dispatch.
        if self._fccd_conv is not None:
            ctx = NSComputeContext(velocity=[u, v], ccd=ccd, rho=rho, mu=mu_field)
            _conv = self._fccd_conv.compute(ctx)
            conv_u = _conv[0]
            conv_v = _conv[1]
        else:
            conv_u = -(u * du_dx + v * du_dy)
            conv_v = -(u * dv_dx + v * dv_dy)

        # Buoyancy (applied to explicit RHS before viscous step)
        buoy_v = xp.zeros_like(v)
        if g_acc != 0.0:
            buoy_v = -(rho - rho_ref) / rho * g_acc

        # Strategy pattern: viscous predictor encapsulates CN vs Explicit logic
        u_star, v_star = self._viscous_predictor.predict(
            u, v, conv_u, conv_v, mu_field, rho, dt, ccd, buoy_v=buoy_v
        )

        _apply_bc(u_star, v_star, bc_hook, self.bc_type)

        # ── 4. PPE (balanced-force) ─────────────────────────────────────
        rhs = self._div_op.divergence([u_star, v_star]) / dt
        # Add balanced-force CSF contribution if σ > 0 (zero forces when σ ≤ 0)
        rhs = rhs + self._div_op.divergence([f_x / rho, f_y / rho])
        _dbg_ppe_rhs_max = float(self._backend.to_host(xp.max(xp.abs(rhs))))
        self._step_diag.record_ppe_rhs(_dbg_ppe_rhs_max)
        p = self._ppe_solver.solve(rhs, rho)

        # ── 5. Corrector ───────────────────────────────────────────────
        # Strategy pattern: gradient operator encapsulates CCD vs FVM logic
        dp_dx = self._grad_op.gradient(p, 0)
        dp_dy = self._grad_op.gradient(p, 1)
        _dbg_bf_res_max = float(self._backend.to_host(
            xp.maximum(xp.max(xp.abs(dp_dx - f_x / rho)),
                       xp.max(xp.abs(dp_dy - f_y / rho)))
        ))
        self._step_diag.record_bf_residual(_dbg_bf_res_max)
        projected_on_faces = (
            self._face_flux_projection and hasattr(self._div_op, "project")
        )
        if projected_on_faces:
            u, v = self._div_op.project(
                [u_star, v_star],
                p,
                rho,
                dt,
                [f_x / rho, f_y / rho],
            )
        else:
            u = u_star - dt / rho * dp_dx + dt * f_x / rho
            v = v_star - dt / rho * dp_dy + dt * f_y / rho

        _apply_bc(u, v, bc_hook, self.bc_type)

        _dbg_div_u_max = float(self._backend.to_host(
            xp.max(xp.abs(self._div_op.divergence([u, v])))
        ))
        self._step_diag.record_div_u(_dbg_div_u_max)

        return psi, u, v, p

    # ── private ───────────────────────────────────────────────────────────
    # (PPE solve and matrix build delegated to self._ppe_solver —  see PPESolverFVMSpsolve)


# ── IC normalisation helper ───────────────────────────────────────────────────

def _normalise_ic_dict(ic: dict) -> dict:
    """Convert shorthand IC dicts to InitialConditionBuilder format.

    Returns a dict with ``background_phase`` and ``shapes`` keys suitable
    for :meth:`InitialConditionBuilder.from_dict`.
    """
    if "shapes" in ic and "type" not in ic:
        # Already in builder format (explicit background_phase + shapes)
        return ic

    ic_type = ic.get("type", "")

    if ic_type == "union":
        # {type: union, shapes: [...], background_phase: ...}
        shapes = ic.get("shapes", [])
        bg = ic.get("background_phase") or _infer_background(shapes)
        return {"background_phase": bg, "shapes": shapes}

    if ic_type:
        # Single-shape shorthand: strip meta keys, wrap in shapes list
        shape_dict = {k: v for k, v in ic.items()
                      if k not in ("background_phase",)}
        bg = ic.get("background_phase") or _infer_background([shape_dict])
        return {"background_phase": bg, "shapes": [shape_dict]}

    # Fallback: pass through as-is
    return ic


def _infer_background(shapes: list) -> str:
    """Infer background phase as the complement of shapes' interior_phase.

    * Any gas shape → background = liquid
    * All liquid shapes → background = gas
    """
    for s in shapes:
        if s.get("interior_phase", "liquid") == "gas":
            return "liquid"
    return "gas"


# ── module-level helpers ──────────────────────────────────────────────────────

def _wall_bc_hook(u: np.ndarray, v: np.ndarray) -> None:
    """Zero-velocity boundary condition (no-slip / no-penetration)."""
    for arr in (u, v):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0


def _apply_bc(u, v, bc_hook, bc_type: str) -> None:
    if bc_hook is not None:
        bc_hook(u, v)
    elif bc_type == "wall":
        _wall_bc_hook(u, v)
    # periodic: nothing to do


# ── top-level config-driven runner ───────────────────────────────────────────

def run_simulation(cfg: "ExperimentConfig") -> dict:
    """Run a complete simulation from an :class:`ExperimentConfig`.

    Parameters
    ----------
    cfg : ExperimentConfig

    Returns
    -------
    dict with keys:
        ``times`` (ndarray), ``snapshots`` (list of dicts),
        and one ndarray per active diagnostic metric.
    """
    from ..tools.diagnostics import DiagnosticCollector

    solver = TwoPhaseNSSolver.from_config(cfg)
    psi = solver.build_ic(cfg)
    u, v = solver.build_velocity(cfg, psi)
    bc_hook = solver.make_bc_hook(cfg)
    ph = cfg.physics

    # Non-uniform grid: always fit once to the IC before time-stepping.
    # rebuild_freq==0 freezes this IC-fitted grid; rebuild_freq>0 then
    # refreshes it periodically from the transported interface.
    if solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v, ph.rho_l, ph.rho_g)
        mode = "static" if solver._rebuild_freq == 0 else f"dynamic/{solver._rebuild_freq}"
        print(f"  [{mode} non-uniform] grid built from IC, h_min={solver.h_min:.4e}")

    # Initial radius estimate from IC (used only by laplace_pressure metric)
    ic = cfg.initial_condition
    R_ic = float(ic.get("radius", 0.25)) if isinstance(ic, dict) else 0.25

    _bk0 = solver._backend
    diag = DiagnosticCollector(
        cfg.diagnostics,
        np.asarray(_bk0.to_host(solver.X)),
        np.asarray(_bk0.to_host(solver.Y)),
        solver.h,
        rho_l=ph.rho_l, rho_g=ph.rho_g,
        sigma=ph.sigma, R=R_ic,
    )
    snaps: list[dict] = []
    if cfg.run.snap_interval is not None and cfg.run.T_final is not None:
        iv = cfg.run.snap_interval
        n = int(cfg.run.T_final / iv)
        auto = [i * iv for i in range(n + 1)]
        snap_times = sorted(set(list(cfg.run.snap_times) + auto))
    else:
        snap_times = list(cfg.run.snap_times)
    snap_idx = 0

    T = cfg.run.T_final if cfg.run.T_final is not None else float("inf")
    max_steps = cfg.run.max_steps

    t = 0.0
    step = 0
    dbg_history: list = []

    while t < T and (max_steps is None or step < max_steps):
        if cfg.run.dt_fixed is not None:
            dt = min(cfg.run.dt_fixed, T - t)
        else:
            dt = min(solver.dt_max(u, v, ph, cfg.run.cfl), T - t)
        if dt < 1e-12:
            break

        psi, u, v, p = solver.step(
            psi, u, v, dt,
            rho_l=ph.rho_l,
            rho_g=ph.rho_g,
            sigma=ph.sigma,
            mu=ph.mu,
            g_acc=ph.g_acc,
            rho_ref=ph.rho_ref,
            mu_l=ph.mu_l,
            mu_g=ph.mu_g,
            bc_hook=bc_hook,
            step_index=step,
        )
        t += dt
        step += 1

        # Diagnostics: pass device arrays — collector uses xp for on-device reductions.
        _bk = solver._backend
        dV_dev = solver._grid.cell_volumes() if solver._alpha_grid > 1.0 else None
        if solver._alpha_grid > 1.0:
            diag.X = np.asarray(_bk.to_host(solver.X))
            diag.Y = np.asarray(_bk.to_host(solver.Y))
        diag.collect(t, psi, u, v, p, dV=dV_dev)
        dbg_entry = solver._step_diag.last
        if dbg_entry:
            dbg_history.append({"t": t, "step": step, **dbg_entry})

        while snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
            _to_h = lambda a: np.asarray(_bk.to_host(a))
            psi_h, u_h, v_h, p_h = _to_h(psi), _to_h(u), _to_h(v), _to_h(p)
            snap_entry = {
                "t": float(t),
                "psi": psi_h.copy(),
                "u": u_h.copy(),
                "v": v_h.copy(),
                "p": p_h.copy(),
                "rho": (ph.rho_l * psi_h + ph.rho_g * (1.0 - psi_h)).copy(),
            }
            if solver._alpha_grid > 1.0:
                snap_entry["grid_coords"] = [c.copy() for c in solver._grid.coords]
            snaps.append(snap_entry)
            snap_idx += 1

        if step % cfg.run.print_every == 0 or step <= 2:
            ke = diag.last("kinetic_energy", 0.0)
            print(f"  step={step:5d}  t={t:.4f}  dt={dt:.5f}  KE={ke:.3e}")
            d = solver._step_diag.last
            if d:
                print(f"          kappa_max={d['kappa_max']:.3e}  ppe_rhs={d['ppe_rhs_max']:.3e}"
                      f"  bf_res={d['bf_residual_max']:.3e}  div_u={d['div_u_max']:.3e}")

        ke = diag.last("kinetic_energy", 0.0)
        if np.isnan(ke) or ke > 1e6:
            print(f"  BLOWUP at step={step}, t={t:.4f}")
            break

    results = {**diag.to_arrays(), "snapshots": snaps}
    if dbg_history:
        results["debug_diagnostics"] = {
            k: np.array([d[k] for d in dbg_history]) for k in dbg_history[0]
        }
    return results
