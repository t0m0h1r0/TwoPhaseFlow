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
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from .backend import Backend
from .config import GridConfig
from .core.grid import Grid
from .ccd.ccd_solver import CCDSolver
from .levelset.heaviside import heaviside
from .levelset.advection import DissipativeCCDAdvection
from .levelset.curvature import CurvatureCalculator
from .levelset.reinitialize import Reinitializer
from .levelset.curvature_filter import InterfaceLimitedFilter
from .pressure.ppe_builder import PPEBuilder
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
    ) -> None:
        self.NX, self.NY = NX, NY
        self.LX, self.LY = LX, LY
        self.bc_type = bc_type

        self._h = LX / NX
        self._eps = eps_factor * self._h

        self._backend = Backend(use_gpu=use_gpu)
        gc = GridConfig(ndim=2, N=(NX, NY), L=(LX, LY))
        self._grid = Grid(gc, self._backend)
        self._ccd = CCDSolver(self._grid, self._backend, bc_type=bc_type)
        self._ppb = PPEBuilder(self._backend, self._grid, bc_type=bc_type)
        self._curv = CurvatureCalculator(self._backend, self._ccd, self._eps)
        self._hfe = InterfaceLimitedFilter(self._backend, self._ccd, C=hfe_C)
        self._adv = DissipativeCCDAdvection(self._backend, self._grid, self._ccd)
        self._reinit = Reinitializer(
            self._backend, self._grid, self._ccd, self._eps, n_steps=reinit_steps
        )
        self.X, self.Y = self._grid.meshgrid()

    # ── class-method constructors ─────────────────────────────────────────

    @classmethod
    def from_config(cls, cfg: "ExperimentConfig") -> "TwoPhaseNSSolver":
        """Construct from an :class:`ExperimentConfig`."""
        g = cfg.grid
        return cls(g.NX, g.NY, g.LX, g.LY, bc_type=g.bc_type)

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

    # ── initial condition / velocity builders ─────────────────────────────

    def psi_from_phi(self, phi: np.ndarray) -> np.ndarray:
        """Smooth Heaviside ψ = H_ε(φ)."""
        return np.asarray(heaviside(np, phi, self._eps))

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
        h = self._h
        mu_max = max(
            filter(None, [physics.mu, physics.mu_l, physics.mu_g])
        )
        rho_min = physics.rho_g

        u_max = max(
            float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10
        )
        dt_cfl = cfl * h / u_max
        dt_visc = 0.25 * h ** 2 / (mu_max / rho_min)

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

        # ── 1. Advect ψ + reinitialize ─────────────────────────────────
        psi = np.asarray(self._adv.advance(psi, [u, v], dt))
        if step_index % 2 == 0:
            psi = np.asarray(self._reinit.reinitialize(psi))
        rho = rho_g + (rho_l - rho_g) * psi

        # Variable viscosity (recomputed after advection so μ tracks ψ)
        if mu_l is not None and mu_g is not None:
            mu_field: float | np.ndarray = mu_g + (mu_l - mu_g) * psi
        else:
            mu_field = mu  # scalar or pre-computed array

        # ── 2. Curvature + balanced-force CSF ──────────────────────────
        if sigma > 0.0:
            kappa_raw = self._curv.compute(psi)
            kappa = np.asarray(
                self._hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi))
            )
            dpsi_dx, _ = ccd.differentiate(psi, 0)
            dpsi_dy, _ = ccd.differentiate(psi, 1)
            f_x = sigma * kappa * np.asarray(dpsi_dx)
            f_y = sigma * kappa * np.asarray(dpsi_dy)
        else:
            f_x = f_y = np.zeros_like(psi)

        # ── 3. NS predictor ────────────────────────────────────────────
        du_dx, du_xx = ccd.differentiate(u, 0)
        du_dy, du_yy = ccd.differentiate(u, 1)
        dv_dx, dv_xx = ccd.differentiate(v, 0)
        dv_dy, dv_yy = ccd.differentiate(v, 1)
        du_dx = np.asarray(du_dx); du_xx = np.asarray(du_xx)
        du_dy = np.asarray(du_dy); du_yy = np.asarray(du_yy)
        dv_dx = np.asarray(dv_dx); dv_xx = np.asarray(dv_xx)
        dv_dy = np.asarray(dv_dy); dv_yy = np.asarray(dv_yy)

        conv_u = -(u * du_dx + v * du_dy)
        conv_v = -(u * dv_dx + v * dv_dy)
        visc_u = (mu_field / rho) * (du_xx + du_yy)
        visc_v = (mu_field / rho) * (dv_xx + dv_yy)

        u_star = u + dt * (conv_u + visc_u)
        v_star = v + dt * (conv_v + visc_v)
        if g_acc != 0.0:
            v_star = v_star + dt * (-(rho - rho_ref) / rho * g_acc)

        _apply_bc(u_star, v_star, bc_hook, self.bc_type)

        # ── 4. PPE (balanced-force) ─────────────────────────────────────
        du_s_dx, _ = ccd.differentiate(u_star, 0)
        dv_s_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_s_dx) + np.asarray(dv_s_dy)) / dt
        if sigma > 0.0:
            df_x, _ = ccd.differentiate(f_x / rho, 0)
            df_y, _ = ccd.differentiate(f_y / rho, 1)
            rhs += np.asarray(df_x) + np.asarray(df_y)
        p = self._solve_ppe(rhs, rho)

        # ── 5. Corrector ───────────────────────────────────────────────
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        if self.bc_type == "wall":
            ccd.enforce_wall_neumann(dp_dx, 0)
            ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * np.asarray(dp_dx) + dt * f_x / rho
        v = v_star - dt / rho * np.asarray(dp_dy) + dt * f_y / rho

        _apply_bc(u, v, bc_hook, self.bc_type)
        return psi, u, v, p

    # ── private ───────────────────────────────────────────────────────────

    def _solve_ppe(self, rhs: np.ndarray, rho: np.ndarray) -> np.ndarray:
        triplet, A_shape = self._ppb.build(rho)
        A = sp.csr_matrix(
            (triplet[0], (triplet[1], triplet[2])), shape=A_shape
        )
        rhs_vec = rhs.ravel().copy()
        rhs_vec[self._ppb._pin_dof] = 0.0
        return spsolve(A, rhs_vec).reshape(rho.shape)


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
    from .diagnostics import DiagnosticCollector

    solver = TwoPhaseNSSolver.from_config(cfg)
    psi = solver.build_ic(cfg)
    u, v = solver.build_velocity(cfg, psi)
    bc_hook = solver.make_bc_hook(cfg)
    ph = cfg.physics

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

        diag.collect(t, psi, u, v, p)

        while snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
            snaps.append({"t": float(t), "psi": psi.copy()})
            snap_idx += 1

        if step % cfg.run.print_every == 0 or step <= 2:
            ke = diag.last("kinetic_energy", 0.0)
            print(f"  step={step:5d}  t={t:.4f}  dt={dt:.5f}  KE={ke:.3e}")

        ke = diag.last("kinetic_energy", 0.0)
        if np.isnan(ke) or ke > 1e6:
            print(f"  BLOWUP at step={step}, t={t:.4f}")
            break

    return {**diag.to_arrays(), "snapshots": snaps}
