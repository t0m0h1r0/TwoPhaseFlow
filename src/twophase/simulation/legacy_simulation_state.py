"""State snapshot helpers for the legacy `TwoPhaseSimulation` loop."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LegacySimulationSnapshot:
    psi: object
    rho: object
    mu: object
    kappa: object
    phi: object
    pressure: object
    velocity: list
    vel_star: list
    time: float
    step: int


def snapshot_legacy_simulation(sim) -> LegacySimulationSnapshot:
    xp = sim.backend.xp
    return LegacySimulationSnapshot(
        psi=xp.copy(sim.psi.data),
        rho=xp.copy(sim.rho.data),
        mu=xp.copy(sim.mu.data),
        kappa=xp.copy(sim.kappa.data),
        phi=xp.copy(sim.phi.data),
        pressure=xp.copy(sim.pressure.data),
        velocity=[xp.copy(sim.velocity[axis]) for axis in range(sim.config.grid.ndim)],
        vel_star=[xp.copy(sim.vel_star[axis]) for axis in range(sim.config.grid.ndim)],
        time=float(sim.time),
        step=int(sim.step),
    )


def restore_legacy_simulation(sim, snapshot: LegacySimulationSnapshot) -> None:
    xp = sim.backend.xp
    sim.psi.data = xp.copy(snapshot.psi)
    sim.rho.data = xp.copy(snapshot.rho)
    sim.mu.data = xp.copy(snapshot.mu)
    sim.kappa.data = xp.copy(snapshot.kappa)
    sim.phi.data = xp.copy(snapshot.phi)
    sim.pressure.data = xp.copy(snapshot.pressure)
    for axis in range(sim.config.grid.ndim):
        sim.velocity[axis] = xp.copy(snapshot.velocity[axis])
        sim.vel_star[axis] = xp.copy(snapshot.vel_star[axis])
    sim.time = snapshot.time
    sim.step = snapshot.step
