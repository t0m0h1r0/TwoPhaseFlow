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
from ..levelset.heaviside import apply_mass_correction
from ..levelset.reconstruction import ReconstructionConfig, HeavisideInterfaceReconstructor
from ..levelset.advection import DissipativeCCDAdvection
from ..levelset.curvature import CurvatureCalculator
from ..levelset.reinitialize import Reinitializer
from ..levelset.curvature_filter import InterfaceLimitedFilter
from ..ppe.ppe_builder import PPEBuilder
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
    use_gpu : bool
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
        use_gpu: bool = False,
        alpha_grid: float = 1.0,
        eps_g_factor: float = 2.0,
        dx_min_floor: float = 1e-6,
        use_local_eps: bool = False,
        grid_rebuild_freq: int = 1,
        reinit_every: int = 2,
        reinit_method: str | None = None,
        cn_viscous: bool = False,
        Re: float = 1.0,
        reproject_variable_density: bool = False,
        reproject_mode: str = "legacy",
        phi_primary_transport: bool = False,
        phi_primary_redist_every: int = 4,
        phi_primary_clip_factor: float = 12.0,
        phi_primary_heaviside_eps_scale: float = 1.0,
        kappa_max: float | None = None,
        dgr_phi_smooth_C: float = 1e-4,
    ) -> None:
        self.NX, self.NY = NX, NY
        self.LX, self.LY = LX, LY
        self.bc_type = bc_type
        self._alpha_grid = alpha_grid
        self._eps_factor = eps_factor
        self._use_local_eps = use_local_eps
        # grid_rebuild_freq == 0 → static non-uniform grid (build once from IC,
        # never rebuild). This avoids rebuild-driven metric discontinuity
        # (WIKI-X-012 Mode 1) entirely.
        self._rebuild_freq = int(grid_rebuild_freq)
        if self._rebuild_freq < 0:
            self._rebuild_freq = 0
        # Safety fallback for non-uniform dynamic runs:
        # per-step rebuild (freq=1) is prone to remap/reprojection-driven
        # instability. Use a conservative default cadence unless caller sets
        # a value >1 explicitly.
        if self._alpha_grid > 1.0 and self._rebuild_freq == 1:
            self._rebuild_freq = 10
        self._reinit_every = int(reinit_every)
        self._reproject_variable_density = bool(reproject_variable_density)
        self._phi_primary_transport = bool(phi_primary_transport)
        self._phi_primary_redist_every = max(1, int(phi_primary_redist_every))
        self._phi_primary_clip_factor = max(2.0, float(phi_primary_clip_factor))
        self._phi_primary_heaviside_eps_scale = max(1.0, float(phi_primary_heaviside_eps_scale))
        self._kappa_max = float(kappa_max) if kappa_max is not None else None
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
        self._reproject_warned_fallback = False
        self._reproject_warned_iim_fail = False
        self._reproject_warned_iim_reject = False
        self._reproject_stats = {
            "calls": 0,
            "iim_attempts": 0,
            "iim_accepts": 0,
            "iim_rejects": 0,
            "iim_fails": 0,
            "iim_reject_nonfinite": 0,
            "iim_reject_divergence": 0,
            "iim_crossings_total": 0,
            "iim_crossings_accept": 0,
            "iim_crossings_reject": 0,
            "iim_div_base_sum": 0.0,
            "iim_div_iim_sum": 0.0,
            "iim_div_iim_accept_sum": 0.0,
            "iim_div_iim_reject_sum": 0.0,
            "iim_backtrack_accepts": 0,
        }

        self._h = LX / NX
        self._eps = eps_factor * self._h

        self._backend = Backend(use_gpu=use_gpu)
        gc = GridConfig(
            ndim=2, N=(NX, NY), L=(LX, LY),
            alpha_grid=alpha_grid,
            eps_g_factor=eps_g_factor,
            dx_min_floor=dx_min_floor,
        )
        self._grid = Grid(gc, self._backend)
        self._ccd = CCDSolver(self._grid, self._backend, bc_type=bc_type)
        self._ppb = PPEBuilder(self._backend, self._grid, bc_type=bc_type)
        self._reproj_iim = IIMStencilCorrector(self._grid, mode="hermite")

        # Curvature uses local eps_field when use_local_eps=True on non-uniform grids
        eps_curv = self._make_eps_field() if use_local_eps and alpha_grid > 1.0 else self._eps
        self._curv = CurvatureCalculator(self._backend, self._ccd, eps_curv)
        self._hfe = InterfaceLimitedFilter(self._backend, self._ccd, C=hfe_C)
        self._adv = DissipativeCCDAdvection(self._backend, self._grid, self._ccd)
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
        if reinit_method is None:
            reinit_method = 'dgr'  # DGR: all-grid default; use YAML reinit_method: split to override
        self._reinit = Reinitializer(
            self._backend, self._grid, self._ccd, self._eps,
            n_steps=reinit_steps, method=reinit_method,
            phi_smooth_C=dgr_phi_smooth_C,
        )
        self.X, self.Y = self._grid.meshgrid()

        # Viscous term: CN (Heun predictor-corrector, O(Δt²)) or explicit FE
        self._cn_viscous = cn_viscous
        self._Re = Re
        if cn_viscous:
            from ..ns_terms.viscous import ViscousTerm
            self._viscous = ViscousTerm(self._backend, Re=Re, cn_viscous=True)

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
            dx_min_floor=getattr(g, "dx_min_floor", 1e-6),
            use_local_eps=getattr(g, "use_local_eps", False),
            grid_rebuild_freq=getattr(g, "grid_rebuild_freq", 1),
            reinit_every=getattr(getattr(cfg, "run", g), "reinit_every", 2),
            reinit_method=getattr(getattr(cfg, "run", g), "reinit_method", None),
            cn_viscous=getattr(getattr(cfg, "run", g), "cn_viscous", False),
            Re=getattr(getattr(cfg, "physics", g), "Re", 1.0),
            reproject_variable_density=getattr(
                getattr(cfg, "run", g), "reproject_variable_density", False,
            ),
            reproject_mode=getattr(
                getattr(cfg, "run", g), "reproject_mode", "legacy",
            ),
            phi_primary_transport=bool(
                getattr(getattr(cfg, "run", g), "phi_primary_transport", False)
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
        return dict(self._reproject_stats)

    def _make_eps_field(self):
        """ε(x) = eps_factor · max(h_x(i), h_y(j)) at each node.

        Returns a device-native array in ``backend.xp`` so it can be
        multiplied against device fields in the hot loop without any
        host↔device traffic.
        """
        xp = self._backend.xp
        hx = xp.asarray(self._grid.h[0])[:, None]
        hy = xp.asarray(self._grid.h[1])[None, :]
        return self._eps_factor * xp.maximum(hx, hy)

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

        # 2. Compute old cell volumes for mass correction
        dV_old = old_h[0].copy()
        for ax in range(1, self._grid.ndim):
            dV_old = np.expand_dims(dV_old, axis=ax) * old_h[ax]
        M_before = float(np.sum(psi * dV_old))

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

        # 9. Velocity re-projection: linear interpolation of (u, v) does not
        #    preserve ∇·u = 0. Solve a PPE to remove the spurious divergence
        #    introduced by the remap.  Without this step the remapped velocity
        #    has O(h) divergence which drives exponential KE growth.
        try:
            u, v = self._reproject_velocity(
                psi, u, v, rho_l=rho_l, rho_g=rho_g,
            )
        except TypeError:
            # Backward compatibility for experiment monkey-patches that
            # replace _reproject_velocity(psi, u, v) with a 3-arg lambda.
            u, v = self._reproject_velocity(psi, u, v)

        return psi, u, v

    def _reproject_velocity(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        rho_l: float | None = None,
        rho_g: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Remove divergence from (u, v) via a pressure-Poisson correction."""
        ccd = self._ccd
        def _h(arr):
            return np.asarray(self._backend.to_host(arr))
        self._reproject_stats["calls"] += 1

        use_varrho = self._reproject_mode in {"variable_density_only"}
        if self._reproject_mode in {"consistent_gfm"}:
            if not self._reproject_warned_fallback:
                warnings.warn(
                    f"reproject_mode='{self._reproject_mode}' currently uses "
                    "legacy projection fallback (skeleton mode).",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self._reproject_warned_fallback = True

        if use_varrho and rho_l is not None and rho_g is not None:
            rho = rho_g + (rho_l - rho_g) * psi
        else:
            rho = np.ones_like(psi)
        du_dx, _ = ccd.differentiate(u, 0)
        dv_dy, _ = ccd.differentiate(v, 1)
        div = _h(du_dx) + _h(dv_dy)

        # Base projection (acceptance baseline).
        phi_base = self._solve_ppe(div, rho)

        def _apply_phi(phi_sol: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            dpx, _ = ccd.differentiate(phi_sol, 0)
            dpy, _ = ccd.differentiate(phi_sol, 1)
            if self.bc_type == "wall":
                ccd.enforce_wall_neumann(dpx, 0)
                ccd.enforce_wall_neumann(dpy, 1)
            if use_varrho and rho_l is not None and rho_g is not None:
                uu = u - _h(dpx) / rho
                vv = v - _h(dpy) / rho
            else:
                uu = u - _h(dpx)
                vv = v - _h(dpy)
            return uu, vv

        def _div_l2(uu: np.ndarray, vv: np.ndarray) -> float:
            duu, _ = ccd.differentiate(uu, 0)
            dvv, _ = ccd.differentiate(vv, 1)
            dd = _h(duu) + _h(dvv)
            return float(np.sqrt(np.mean(dd * dd)))

        u_base, v_base = _apply_phi(phi_base)
        div_base = _div_l2(u_base, v_base)

        if self._reproject_mode == "consistent_iim" and rho_l is not None and rho_g is not None:
            self._reproject_stats["iim_attempts"] += 1
            try:
                # Reprojection-specific IIM: enforce interface consistency by
                # adding jump-aware RHS correction (sigma=0, flux-jump driven).
                phi_iface = np.asarray(self._backend.to_host(self._reconstruct_base.phi_from_psi(psi)))
                n_cross = len(self._reproj_iim.find_interface_crossings(phi_iface))
                self._reproject_stats["iim_crossings_total"] += int(n_cross)
                kappa0 = np.zeros_like(psi)
                A_host = self._build_ppe_matrix(rho)
                dp0_x, _ = ccd.differentiate(phi_base, 0)
                dp0_y, _ = ccd.differentiate(phi_base, 1)
                delta_q = self._reproj_iim.compute_correction(
                    A_host,
                    phi_iface,
                    kappa0,
                    0.0,   # no Young-Laplace jump for reprojection potential
                    rho,
                    div,
                    dp_dx=_h(dp0_x),
                    dp_dy=_h(dp0_y),
                ).reshape(psi.shape)
                phi_iim = self._solve_ppe(div + delta_q, rho)
                u_iim, v_iim = _apply_phi(phi_iim)
                div_iim = _div_l2(u_iim, v_iim)
                self._reproject_stats["iim_div_base_sum"] += float(div_base)
                self._reproject_stats["iim_div_iim_sum"] += float(div_iim)
                finite_ok = np.isfinite(u_iim).all() and np.isfinite(v_iim).all()
                if finite_ok and div_iim <= 1.05 * max(div_base, 1e-30):
                    self._reproject_stats["iim_accepts"] += 1
                    self._reproject_stats["iim_crossings_accept"] += int(n_cross)
                    self._reproject_stats["iim_div_iim_accept_sum"] += float(div_iim)
                    return u_iim, v_iim
                # Backtracking on jump correction strength (line-search style).
                accepted_bt = False
                for scale in (0.5, 0.25, 0.125):
                    phi_bt = self._solve_ppe(div + scale * delta_q, rho)
                    u_bt, v_bt = _apply_phi(phi_bt)
                    div_bt = _div_l2(u_bt, v_bt)
                    finite_bt = np.isfinite(u_bt).all() and np.isfinite(v_bt).all()
                    if finite_bt and div_bt <= 1.05 * max(div_base, 1e-30):
                        self._reproject_stats["iim_accepts"] += 1
                        self._reproject_stats["iim_crossings_accept"] += int(n_cross)
                        self._reproject_stats["iim_div_iim_accept_sum"] += float(div_bt)
                        self._reproject_stats["iim_backtrack_accepts"] += 1
                        return u_bt, v_bt
                    # Keep the best diagnostic value for rejected candidates.
                    if np.isfinite(div_bt):
                        div_iim = min(div_iim, div_bt)
                    finite_ok = finite_ok or finite_bt
                    accepted_bt = accepted_bt or (finite_bt and div_bt <= 1.05 * max(div_base, 1e-30))
                if accepted_bt:
                    return u_iim, v_iim
                self._reproject_stats["iim_rejects"] += 1
                self._reproject_stats["iim_crossings_reject"] += int(n_cross)
                self._reproject_stats["iim_div_iim_reject_sum"] += float(div_iim)
                if not finite_ok:
                    self._reproject_stats["iim_reject_nonfinite"] += 1
                else:
                    self._reproject_stats["iim_reject_divergence"] += 1
                if not self._reproject_warned_iim_reject:
                    warnings.warn(
                        "consistent_iim candidate rejected by acceptance gate; "
                        f"div_base={div_base:.3e}, div_iim={div_iim:.3e}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    self._reproject_warned_iim_reject = True
                return u_base, v_base
            except Exception as e:
                self._reproject_stats["iim_fails"] += 1
                if not self._reproject_warned_iim_fail:
                    warnings.warn(
                        "consistent_iim reprojection failed; fallback to base "
                        f"variable-density projection. cause={e}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    self._reproject_warned_iim_fail = True
                return u_base, v_base

        return u_base, v_base

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
            return np.zeros_like(self.X), np.zeros_like(self.Y)

        spec = dict(cfg.initial_velocity)
        vf = velocity_field_from_dict(spec)
        u, v = vf.compute(self.X, self.Y)
        return np.asarray(u), np.asarray(v)

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

        u_max = max(
            float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10
        )
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
        def _h(arr): return np.asarray(self._backend.to_host(arr))

        # ── 1. Advect + reinitialize ───────────────────────────────────
        if self._phi_primary_transport:
            # Experimental path: transport phi as the primary variable and
            # reconstruct psi via H_eps(phi) each step.
            dV_pre = np.asarray(self._backend.to_host(self._grid.cell_volumes()))
            M_pre = float(np.sum(psi * dV_pre))
            phi = np.asarray(self._backend.to_host(self._reconstruct_phi_primary.phi_from_psi(psi)))
            phi = _h(self._adv.advance(phi, [u, v], dt, clip_bounds=None))
            # Prevent over-saturation of logit reconstruction.
            phi = np.asarray(self._backend.to_host(self._reconstruct_phi_primary.clip_phi(phi)))
            psi = np.asarray(self._backend.to_host(self._reconstruct_phi_primary.psi_from_phi(phi)))
            # Re-distance/thickness correction on a controlled cadence to
            # avoid over-sharpening into near-binary fields.
            if step_index > 0 and (step_index % self._phi_primary_redist_every == 0):
                psi = _h(self._reinit.reinitialize(psi))
                phi = np.asarray(self._backend.to_host(self._reconstruct_phi_primary.phi_from_psi(psi)))
                psi = np.asarray(self._backend.to_host(self._reconstruct_phi_primary.psi_from_phi(phi)))
            psi = np.asarray(apply_mass_correction(np, psi, dV_pre, M_pre))
        else:
            psi = _h(self._adv.advance(psi, [u, v], dt))
        if (not self._phi_primary_transport) and self._reinit_every > 0 and step_index % self._reinit_every == 0:
            psi = _h(self._reinit.reinitialize(psi))

        # ── 1b. Grid rebuild (interface-fitted, every rebuild_freq steps)
        # rebuild_freq == 0 → static grid, never rebuild during time-stepping.
        if self._alpha_grid > 1.0 and self._rebuild_freq > 0 and (step_index % self._rebuild_freq == 0):
            try:
                psi, u, v = self._rebuild_grid(
                    psi, u, v, rho_l=rho_l, rho_g=rho_g,
                )
            except TypeError:
                # Backward compatibility for experiment monkey-patches that
                # replace _rebuild_grid(psi, u, v) with a 3-arg lambda.
                psi, u, v = self._rebuild_grid(psi, u, v)

        rho = rho_g + (rho_l - rho_g) * psi

        # Variable viscosity (recomputed after advection so μ tracks ψ)
        if mu_l is not None and mu_g is not None:
            mu_field: float | np.ndarray = mu_g + (mu_l - mu_g) * psi
        else:
            mu_field = mu  # scalar or pre-computed array

        # ── 2. Curvature + balanced-force CSF ──────────────────────────
        if sigma > 0.0:
            kappa_raw = self._curv.compute(psi)
            kappa = _h(self._hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
            if self._kappa_max is not None:
                kappa = np.clip(kappa, -self._kappa_max, self._kappa_max)
            dpsi_dx, _ = ccd.differentiate(psi, 0)
            dpsi_dy, _ = ccd.differentiate(psi, 1)
            f_x = sigma * kappa * _h(dpsi_dx)
            f_y = sigma * kappa * _h(dpsi_dy)
        else:
            f_x = f_y = np.zeros_like(psi)

        # ── 3. NS predictor ────────────────────────────────────────────
        du_dx, du_xx = ccd.differentiate(u, 0)
        du_dy, du_yy = ccd.differentiate(u, 1)
        dv_dx, dv_xx = ccd.differentiate(v, 0)
        dv_dy, dv_yy = ccd.differentiate(v, 1)
        du_dx = _h(du_dx); du_xx = _h(du_xx)
        du_dy = _h(du_dy); du_yy = _h(du_yy)
        dv_dx = _h(dv_dx); dv_xx = _h(dv_xx)
        dv_dy = _h(dv_dy); dv_yy = _h(dv_yy)

        conv_u = -(u * du_dx + v * du_dy)
        conv_v = -(u * dv_dx + v * dv_dy)

        # Buoyancy (applied to explicit RHS before viscous step)
        buoy_v = np.zeros_like(v)
        if g_acc != 0.0:
            buoy_v = -(rho - rho_ref) / rho * g_acc

        if self._cn_viscous:
            # CN viscous (Heun predictor-corrector, O(Δt²), explicit but
            # trapezoid-averaged → relaxed CFL vs forward Euler).
            # explicit_rhs = rho * (convection + buoyancy) per component
            explicit_rhs = [rho * conv_u, rho * (conv_v + buoy_v)]
            vel_star = self._viscous.apply_cn_predictor(
                [u, v], explicit_rhs, mu_field, rho, ccd, dt,
            )
            u_star, v_star = vel_star[0], vel_star[1]
            # Ensure host arrays
            u_star = _h(u_star) if hasattr(u_star, '__cuda_array_interface__') else np.asarray(u_star)
            v_star = _h(v_star) if hasattr(v_star, '__cuda_array_interface__') else np.asarray(v_star)
        else:
            # Original explicit forward-Euler viscous
            visc_u = (mu_field / rho) * (du_xx + du_yy)
            visc_v = (mu_field / rho) * (dv_xx + dv_yy)
            u_star = u + dt * (conv_u + visc_u)
            v_star = v + dt * (conv_v + visc_v + buoy_v)

        _apply_bc(u_star, v_star, bc_hook, self.bc_type)

        # ── 4. PPE (balanced-force) ─────────────────────────────────────
        du_s_dx, _ = ccd.differentiate(u_star, 0)
        dv_s_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (_h(du_s_dx) + _h(dv_s_dy)) / dt
        if sigma > 0.0:
            df_x, _ = ccd.differentiate(f_x / rho, 0)
            df_y, _ = ccd.differentiate(f_y / rho, 1)
            rhs += _h(df_x) + _h(df_y)
        p = self._solve_ppe(rhs, rho)

        # ── 5. Corrector ───────────────────────────────────────────────
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        if self.bc_type == "wall":
            ccd.enforce_wall_neumann(dp_dx, 0)
            ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * _h(dp_dx) + dt * f_x / rho
        v = v_star - dt / rho * _h(dp_dy) + dt * f_y / rho

        _apply_bc(u, v, bc_hook, self.bc_type)
        return psi, u, v, p

    # ── private ───────────────────────────────────────────────────────────

    def _solve_ppe(self, rhs: np.ndarray, rho: np.ndarray) -> np.ndarray:
        A_host = self._build_ppe_matrix(rho)
        rhs_vec = rhs.ravel().copy()
        rhs_vec[self._ppb._pin_dof] = 0.0
        if self._backend.is_gpu():
            A_dev = self._backend.sparse.csr_matrix(A_host)
            rhs_dev = self._backend.xp.asarray(rhs_vec)
            p_dev = self._backend.sparse_linalg.spsolve(A_dev, rhs_dev)
            return np.asarray(self._backend.to_host(p_dev)).reshape(rho.shape)
        return self._backend.sparse_linalg.spsolve(A_host, rhs_vec).reshape(rho.shape)

    def _build_ppe_matrix(self, rho: np.ndarray):
        import scipy.sparse as sp
        triplet, A_shape = self._ppb.build(rho)
        return sp.csr_matrix(
            (triplet[0], (triplet[1], triplet[2])), shape=A_shape
        )


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

    # Static non-uniform grid: build once from IC, then freeze.
    # rebuild_freq==0 means the grid is never rebuilt during time-stepping,
    # avoiding Mode-1 metric discontinuity (WIKI-X-012).
    if solver._alpha_grid > 1.0 and solver._rebuild_freq == 0:
        psi, u, v = solver._rebuild_grid(psi, u, v, ph.rho_l, ph.rho_g)
        print(f"  [static non-uniform] grid built from IC, h_min={solver.h_min:.4e}")

    # Initial radius estimate from IC (used only by laplace_pressure metric)
    ic = cfg.initial_condition
    R_ic = float(ic.get("radius", 0.25)) if isinstance(ic, dict) else 0.25

    diag = DiagnosticCollector(
        cfg.diagnostics, solver.X, solver.Y, solver.h,
        rho_l=ph.rho_l, rho_g=ph.rho_g,
        sigma=ph.sigma, R=R_ic,
    )
    snaps: list[dict] = []
    snap_times = list(cfg.run.snap_times)
    snap_idx = 0

    T = cfg.run.T_final if cfg.run.T_final is not None else float("inf")
    max_steps = cfg.run.max_steps

    t = 0.0
    step = 0

    while t < T and step < max_steps:
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

        # Update diagnostic references for dynamic grids
        if solver._alpha_grid > 1.0:
            diag.X = solver.X
            diag.Y = solver.Y
            dV = solver._grid.cell_volumes()
        else:
            dV = None

        diag.collect(t, psi, u, v, p, dV=dV)

        while snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
            snap_entry = {
                "t": float(t),
                "psi": psi.copy(),
                "u": u.copy(),
                "v": v.copy(),
                "p": p.copy(),
            }
            if solver._alpha_grid > 1.0:
                snap_entry["grid_coords"] = [c.copy() for c in solver._grid.coords]
            snaps.append(snap_entry)
            snap_idx += 1

        if step % cfg.run.print_every == 0 or step <= 2:
            ke = diag.last("kinetic_energy", 0.0)
            print(f"  step={step:5d}  t={t:.4f}  dt={dt:.5f}  KE={ke:.3e}")

        ke = diag.last("kinetic_energy", 0.0)
        if np.isnan(ke) or ke > 1e6:
            print(f"  BLOWUP at step={step}, t={t:.4f}")
            break

    return {**diag.to_arrays(), "snapshots": snaps}
