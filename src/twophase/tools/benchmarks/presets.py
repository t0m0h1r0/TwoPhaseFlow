"""
Benchmark configuration presets (DRY).

Centralizes SimulationConfig construction for benchmark problems.
Each benchmark's _make_config() delegates here to eliminate duplication.
"""

from __future__ import annotations
from twophase.config import SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig

__all__ = [
    "rising_bubble_config",
    "stationary_droplet_config",
    "rayleigh_taylor_config",
]


def rising_bubble_config(
    N: int = 64,
    t_end: float = 3.0,
    Re: float = 35.0,
    We: float = 10.0,
    rho_ratio: float = 0.1,
) -> SimulationConfig:
    """Config for rising bubble benchmark (Hysing et al. 2009)."""
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, 2 * N), L=(1.0, 2.0)),
        fluid=FluidConfig(Re=Re, Fr=1.0, We=We, rho_ratio=rho_ratio, mu_ratio=rho_ratio),
        numerics=NumericsConfig(
            epsilon_factor=1.5, reinit_steps=4, cfl_number=0.25,
            t_end=t_end, bc_type="wall",
        ),
        solver=SolverConfig(ppe_solver_type="fvm_iterative"),
    )


def stationary_droplet_config(
    N: int = 64,
    t_end: float = 1.0,
    Re: float = 100.0,
    We: float = 1.0,
    Fr: float = 1e6,
    rho_ratio: float = 0.001,
    ppe_solver_type: str = "fvm_iterative",
    allow_kronecker_lu: bool = False,
    bc_type: str = "wall",
    cn_viscous: bool = True,
) -> SimulationConfig:
    """Config for stationary droplet benchmark (Laplace pressure test)."""
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(Re=Re, Fr=Fr, We=We, rho_ratio=rho_ratio, mu_ratio=rho_ratio),
        numerics=NumericsConfig(
            epsilon_factor=1.5, reinit_steps=4, cfl_number=0.25,
            t_end=t_end, bc_type=bc_type, cn_viscous=cn_viscous,
        ),
        solver=SolverConfig(
            ppe_solver_type=ppe_solver_type,
            allow_kronecker_lu=allow_kronecker_lu,
        ),
    )


def rayleigh_taylor_config(
    N: int = 64,
    t_end: float = 2.0,
    Re: float = 1000.0,
    rho_ratio: float = 0.2,
) -> SimulationConfig:
    """Config for Rayleigh-Taylor instability benchmark."""
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, 4 * N), L=(0.5, 2.0)),
        fluid=FluidConfig(Re=Re, Fr=1.0, We=1e6, rho_ratio=rho_ratio, mu_ratio=rho_ratio),
        numerics=NumericsConfig(
            epsilon_factor=1.5, reinit_steps=4, cfl_number=0.25,
            t_end=t_end, bc_type="wall",
        ),
        solver=SolverConfig(ppe_solver_type="fvm_iterative"),
    )
