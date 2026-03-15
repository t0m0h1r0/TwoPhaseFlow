"""
twophase — Two-phase flow solver.

Conservative Level Set + CCD (6th-order) + Chorin Projection.

Paper: see paper/sections/ for the full mathematical specification.

Quick start::

    from twophase import SimulationConfig, TwoPhaseSimulation
    import numpy as np

    cfg = SimulationConfig(ndim=2, N=(64, 64), L=(1.0, 1.0),
                           Re=50.0, Fr=1.0, We=10.0,
                           rho_ratio=0.1, mu_ratio=0.1, t_end=0.5)
    sim = TwoPhaseSimulation(cfg)

    X, Y = sim.grid.meshgrid()
    sim.psi.data[:] = 1.0 / (1.0 + np.exp(
        -(np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.2) / (1.5 / 64)
    ))
    sim.run(output_interval=20, verbose=True)
"""

from .backend import Backend
from .config import SimulationConfig
from .simulation import TwoPhaseSimulation

__all__ = ["Backend", "SimulationConfig", "TwoPhaseSimulation"]
