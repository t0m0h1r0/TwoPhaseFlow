"""Run-loop helpers for the legacy `TwoPhaseSimulation` core."""

from __future__ import annotations

from typing import Callable, Optional

from .legacy_simulation_state import (
    restore_legacy_simulation,
    snapshot_legacy_simulation,
)


def run_legacy_simulation(
    sim,
    *,
    t_end: Optional[float],
    output_interval: int,
    verbose: bool,
    callback: Optional[Callable],
) -> None:
    if t_end is None:
        t_end = sim.config.numerics.t_end

    sim._update_properties()
    sim._update_curvature()

    while sim.time < t_end:
        dt_nominal = sim.cfl_calc.compute(
            [sim.velocity[ax] for ax in range(sim.config.grid.ndim)],
            sim.mu.data,
            sim.rho.data,
        )
        dt_nominal = min(dt_nominal, t_end - sim.time)
        dt = advance_legacy_step_with_retry(sim, dt_nominal, verbose=verbose)

        if verbose and sim.step % output_interval == 0:
            sim._diagnostics.report(sim, dt)
        if callback is not None and sim.step % output_interval == 0:
            callback(sim)

    if verbose:
        print(f"シミュレーション終了 t={sim.time:.6f}, step={sim.step}")


def advance_legacy_step_with_retry(sim, dt_nominal: float, verbose: bool = False) -> float:
    max_retries = 12
    dt_try = float(dt_nominal)
    snapshot = snapshot_legacy_simulation(sim)

    for retry in range(max_retries + 1):
        try:
            sim.step_forward(dt_try)
            if has_nonfinite_legacy_state(sim):
                raise FloatingPointError("non-finite state after step")
            return dt_try
        except Exception:
            restore_legacy_simulation(sim, snapshot)
            if retry >= max_retries:
                raise
            dt_try *= 0.5
            if verbose:
                print(
                    f"[run] step retry {retry + 1}/{max_retries}: "
                    f"reducing dt to {dt_try:.3e}"
                )

    return dt_try


def has_nonfinite_legacy_state(sim) -> bool:
    xp = sim.backend.xp
    fields = [
        sim.psi.data,
        sim.rho.data,
        sim.mu.data,
        sim.kappa.data,
        sim.phi.data,
        sim.pressure.data,
    ]
    fields.extend(sim.velocity[ax] for ax in range(sim.config.grid.ndim))
    fields.extend(sim.vel_star[ax] for ax in range(sim.config.grid.ndim))
    return any(bool(xp.any(~xp.isfinite(arr))) for arr in fields)
