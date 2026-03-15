"""
Simulation configuration dataclass.

All physical and numerical parameters live here so that every component
is fully specified by a single immutable object.

Dimensionless numbers follow the paper's (§2.4) non-dimensionalisation:

    Re = ρ_l U L / μ_l         (Reynolds)
    Fr = U / sqrt(g L)          (Froude)
    We = ρ_l U² L / σ           (Weber)
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class SimulationConfig:
    # ── Dimensionality ────────────────────────────────────────────────────
    ndim: int = 2

    # ── Grid ─────────────────────────────────────────────────────────────
    N: Tuple[int, ...] = (64, 64)
    L: Tuple[float, ...] = (1.0, 1.0)

    # ── Dimensionless numbers ─────────────────────────────────────────────
    Re: float = 100.0
    Fr: float = 1.0
    We: float = 10.0

    # ── Fluid properties (ratios gas/liquid) ─────────────────────────────
    rho_ratio: float = 0.001   # ρ_g / ρ_l
    mu_ratio: float = 0.01     # μ_g / μ_l

    # ── Interface parameters ──────────────────────────────────────────────
    # ε = epsilon_factor * min(Δx)  — interface thickness (§3.3)
    epsilon_factor: float = 1.5
    # α_grid controls interface-fitted grid stretching (§5); 1.0 = uniform
    alpha_grid: float = 1.0
    # Number of pseudo-time reinitialisation sub-steps per advection step
    reinit_steps: int = 4

    # ── Time integration ──────────────────────────────────────────────────
    cfl_number: float = 0.3
    t_end: float = 1.0
    # Use Crank-Nicolson (half-implicit) for the viscous term (§9)
    cn_viscous: bool = True

    # ── Pressure solver ───────────────────────────────────────────────────
    bicgstab_tol: float = 1e-10
    bicgstab_maxiter: int = 1000

    # ── Boundary conditions ───────────────────────────────────────────────
    # 'wall'     — no-slip / no-penetration on all boundaries
    # 'periodic' — periodic in all directions
    bc_type: str = "wall"

    # ── Hardware ─────────────────────────────────────────────────────────
    use_gpu: bool = False

    # ── dx_min floor to prevent near-zero cell widths (§5, Known Issues) ─
    dx_min_floor: float = 1e-6

    def __post_init__(self) -> None:
        assert self.ndim in (2, 3), f"ndim must be 2 or 3, got {self.ndim}"
        assert len(self.N) == self.ndim, (
            f"len(N)={len(self.N)} must equal ndim={self.ndim}"
        )
        assert len(self.L) == self.ndim, (
            f"len(L)={len(self.L)} must equal ndim={self.ndim}"
        )
        assert self.bc_type in ("wall", "periodic"), (
            f"bc_type must be 'wall' or 'periodic', got '{self.bc_type}'"
        )
