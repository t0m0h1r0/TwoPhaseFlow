"""
Top-level time-step loop.

Implements the full 7-step algorithm described in §9.1 (Eq. 85–94).

Per-timestep flow:

  Step 1 — CLS advection (WENO5 + TVD-RK3)
  Step 2 — Reinitialization (pseudo-time PDE)
  Step 3 — Update material properties (ρ̃, μ̃)
  Step 4 — Curvature (φ ← H_ε^{-1}(ψ), κ ← CCD)
  Step 5 — Predictor u* (convection + viscous + gravity + surface tension)
  Step 6 — PPE solve (Rhie-Chow div + BiCGSTAB)
  Step 7 — Corrector u^{n+1} = u* − (Δt/ρ̃) ∇p^{n+1}

Usage::

    from twophase import SimulationConfig, TwoPhaseSimulation
    import numpy as np

    cfg = SimulationConfig(ndim=2, N=(64, 64), L=(1.0, 1.0),
                           Re=100., Fr=1., We=10.,
                           rho_ratio=0.1, mu_ratio=0.1, t_end=1.0)
    sim = TwoPhaseSimulation(cfg)

    X, Y = sim.grid.meshgrid()
    sim.psi.data[:] = 1.0 / (1.0 + np.exp(
        -(np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.2) / (1.5 / 64)
    ))
    sim.run(output_interval=20, verbose=True)
"""

from __future__ import annotations
import numpy as np
from typing import Optional, Callable, TYPE_CHECKING

from .backend import Backend
from .config import SimulationConfig
from .core.grid import Grid
from .core.field import ScalarField, VectorField
from .ccd.ccd_solver import CCDSolver
from .levelset.heaviside import heaviside, update_properties, invert_heaviside
from .levelset.curvature import CurvatureCalculator
from .levelset.advection import LevelSetAdvection
from .levelset.reinitialize import Reinitializer
from .ns_terms.predictor import Predictor
from .pressure.rhie_chow import RhieChowInterpolator
from .pressure.ppe_builder import PPEBuilder
from .pressure.ppe_solver import PPESolver
from .pressure.ppe_solver_pseudotime import PPESolverPseudoTime
from .pressure.velocity_corrector import VelocityCorrector
from .time_integration.cfl import CFLCalculator


class TwoPhaseSimulation:
    """Two-phase flow solver.

    Parameters
    ----------
    config : SimulationConfig
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.backend = Backend(use_gpu=config.use_gpu)
        xp = self.backend.xp

        # ── Grid ──────────────────────────────────────────────────────────
        self.grid = Grid(config, self.backend)

        # ── Interface thickness ε ─────────────────────────────────────────
        dx_min = min(config.L[ax] / config.N[ax] for ax in range(config.ndim))
        self.eps = config.epsilon_factor * dx_min

        # ── CCD solver ────────────────────────────────────────────────────
        self.ccd = CCDSolver(self.grid, self.backend)

        # ── Fields ────────────────────────────────────────────────────────
        shape = self.grid.shape

        # Level set: ψ (Conservative Level Set, ψ ∈ [0,1])
        self.psi = ScalarField(self.grid, self.backend)

        # Derived fields
        self.rho = ScalarField(self.grid, self.backend)
        self.mu  = ScalarField(self.grid, self.backend)
        self.kappa = ScalarField(self.grid, self.backend)
        self.pressure = ScalarField(self.grid, self.backend)

        # Velocity: stored as a VectorField
        self.velocity = VectorField(self.grid, self.backend)
        self.vel_star = VectorField(self.grid, self.backend)

        # ── Sub-module instances ──────────────────────────────────────────
        self.ls_advect = LevelSetAdvection(self.backend)
        self.ls_advect.set_grid(self.grid)

        self.ls_reinit = Reinitializer(
            self.backend, self.grid, self.eps, config.reinit_steps
        )

        self.curvature_calc = CurvatureCalculator(self.backend, self.eps)
        self.predictor = Predictor(self.backend, config)
        self.rhie_chow = RhieChowInterpolator(self.backend, self.grid)
        self.ppe_builder = PPEBuilder(self.backend, self.grid)
        if config.ppe_solver_type == "pseudotime":
            self.ppe_solver = PPESolverPseudoTime(self.backend, config, self.grid)
        else:
            self.ppe_solver = PPESolver(self.backend, config)
        self.vel_corrector = VelocityCorrector(self.backend)
        self.cfl_calc = CFLCalculator(self.backend, self.grid, config.cfl_number)

        # ── Simulation time ───────────────────────────────────────────────
        self.time: float = 0.0
        self.step: int = 0

        # ── Dimensionless fluid properties ────────────────────────────────
        # In paper's scaling: ρ_l = 1, ρ_g = rho_ratio
        self._rho_l: float = 1.0
        self._rho_g: float = config.rho_ratio
        self._mu_l: float = 1.0
        self._mu_g: float = config.mu_ratio

    # ── Public API ────────────────────────────────────────────────────────

    def run(
        self,
        t_end: Optional[float] = None,
        output_interval: int = 10,
        verbose: bool = True,
        callback: Optional[Callable] = None,
    ) -> None:
        """Integrate from ``self.time`` to ``t_end``.

        Parameters
        ----------
        t_end           : stop time (default: config.t_end)
        output_interval : print diagnostics every N steps
        verbose         : if True, print per-step info
        callback        : optional ``f(sim)`` called every output_interval steps
        """
        if t_end is None:
            t_end = self.config.t_end

        # Initialise properties from initial ψ
        self._update_properties()
        self._update_curvature()

        while self.time < t_end:
            dt = self.cfl_calc.compute(
                [self.velocity[ax] for ax in range(self.config.ndim)],
                self.mu.data,
                self.rho.data,
            )
            dt = min(dt, t_end - self.time)

            self.step_forward(dt)

            if verbose and self.step % output_interval == 0:
                self._print_diagnostics(dt)
            if callback is not None and self.step % output_interval == 0:
                callback(self)

        if verbose:
            print(f"Simulation finished at t={self.time:.6f}, step={self.step}")

    def step_forward(self, dt: float) -> None:
        """Advance the simulation by one time step of size ``dt``."""
        xp = self.backend.xp

        # Step 1: CLS advection ────────────────────────────────────────────
        vel_components = [self.velocity[ax] for ax in range(self.config.ndim)]
        psi_adv = self.ls_advect.advance(self.psi.data, vel_components, dt)

        # Step 2: Reinitialization ─────────────────────────────────────────
        psi_new = self.ls_reinit.reinitialize(psi_adv, self.ccd)
        self.psi.data = psi_new

        # Step 3: Material properties ──────────────────────────────────────
        self._update_properties()

        # Step 4: Curvature ────────────────────────────────────────────────
        self._update_curvature()

        # Step 5: Predictor ────────────────────────────────────────────────
        vel_n = [self.velocity[ax] for ax in range(self.config.ndim)]
        vel_star_list = self.predictor.compute(
            vel_n,
            self.rho.data,
            self.mu.data,
            self.kappa.data,
            self.psi.data,
            self.ccd,
            dt,
        )
        for ax in range(self.config.ndim):
            self.vel_star[ax] = vel_star_list[ax]

        # Step 6: PPE solve ────────────────────────────────────────────────
        div_rc = self.rhie_chow.face_velocity_divergence(
            [self.vel_star[ax] for ax in range(self.config.ndim)],
            self.pressure.data,
            self.rho.data,
            self.ccd,
            dt,
        )
        rhs_ppe = div_rc / dt

        if isinstance(self.ppe_solver, PPESolverPseudoTime):
            p_new = self.ppe_solver.solve(
                self.pressure.data, rhs_ppe, self.rho.data, self.ccd
            )
        else:
            triplet, A_shape = self.ppe_builder.build(self.rho.data)
            p_new = self.ppe_solver.solve(
                triplet, A_shape, rhs_ppe, self.ppe_builder.n_dof,
                self.grid.shape,
                p_init=self.pressure.data,   # warm-start from p^n
            )
        self.pressure.data = p_new

        # Step 7: Corrector ────────────────────────────────────────────────
        vel_new = self.vel_corrector.correct(
            [self.vel_star[ax] for ax in range(self.config.ndim)],
            self.pressure.data,
            self.rho.data,
            self.ccd,
            dt,
        )
        for ax in range(self.config.ndim):
            self.velocity[ax] = vel_new[ax]

        # Apply wall boundary conditions
        self._apply_wall_bc()

        self.time += dt
        self.step += 1

    # ── Private helpers ───────────────────────────────────────────────────

    def _update_properties(self) -> None:
        rho, mu = update_properties(
            self.backend.xp,
            self.psi.data,
            self._rho_l, self._rho_g,
            self._mu_l, self._mu_g,
        )
        self.rho.data = rho
        self.mu.data  = mu

    def _update_curvature(self) -> None:
        self.kappa.data = self.curvature_calc.compute(self.psi.data, self.ccd)

    def _apply_wall_bc(self) -> None:
        """Enforce no-slip / no-penetration on all boundaries."""
        if self.config.bc_type != "wall":
            return
        for ax in range(self.config.ndim):
            u = self.velocity[ax]
            # Zero velocity on all boundary faces (no-slip)
            sl_lo = [slice(None)] * self.config.ndim
            sl_hi = [slice(None)] * self.config.ndim
            sl_lo[ax] = 0
            sl_hi[ax] = -1
            u[tuple(sl_lo)] = 0.0
            u[tuple(sl_hi)] = 0.0

    def _print_diagnostics(self, dt: float) -> None:
        xp = self.backend.xp
        # Divergence of velocity
        div = xp.zeros(self.grid.shape)
        for ax in range(self.config.ndim):
            d1, _ = self.ccd.differentiate(self.velocity[ax], ax)
            div += d1
        div_max = float(xp.max(xp.abs(div)))

        # Volume (integral of ψ)
        dV = self.grid.cell_volume()
        vol = float(xp.sum(self.psi.data)) * dV

        print(
            f"  t={self.time:.5f}  dt={dt:.3e}  "
            f"|∇·u|_∞={div_max:.3e}  vol(ψ)={vol:.6f}"
        )
