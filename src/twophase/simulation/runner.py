"""Config-driven simulation runner.

Keeps experiment orchestration separate from ``TwoPhaseNSSolver`` so the solver
class only owns scheme composition and one-step advancement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .config_io import ExperimentConfig


def run_simulation(cfg: "ExperimentConfig") -> dict:
    """Run a complete simulation from an :class:`ExperimentConfig`."""
    from .ns_pipeline import TwoPhaseNSSolver
    from ..tools.diagnostics import DiagnosticCollector

    solver = TwoPhaseNSSolver.from_config(cfg)
    psi = solver.build_ic(cfg)
    u, v = solver.build_velocity(cfg, psi)
    bc_hook = solver.make_bc_hook(cfg)
    ph = cfg.physics

    if solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v, ph.rho_l, ph.rho_g)
        mode = "static" if solver._rebuild_freq == 0 else f"dynamic/{solver._rebuild_freq}"
        print(f"  [{mode} non-uniform] grid built from IC, h_min={solver.h_min:.4e}")

    ic = cfg.initial_condition
    R_ic = float(ic.get("radius", 0.25)) if isinstance(ic, dict) else 0.25

    _bk0 = solver._backend
    diag = DiagnosticCollector(
        cfg.diagnostics,
        np.asarray(_bk0.to_host(solver.X)),
        np.asarray(_bk0.to_host(solver.Y)),
        solver.h,
        rho_l=ph.rho_l,
        rho_g=ph.rho_g,
        sigma=ph.sigma,
        R=R_ic,
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

        step_index = step
        grid_will_rebuild = (
            solver._alpha_grid > 1.0
            and solver._rebuild_freq > 0
            and step_index > 0
            and (step_index % solver._rebuild_freq == 0)
        )
        psi, u, v, p = solver.step(
            psi,
            u,
            v,
            dt,
            rho_l=ph.rho_l,
            rho_g=ph.rho_g,
            sigma=ph.sigma,
            mu=ph.mu,
            g_acc=ph.g_acc,
            rho_ref=ph.rho_ref,
            mu_l=ph.mu_l,
            mu_g=ph.mu_g,
            bc_hook=bc_hook,
            step_index=step_index,
        )
        t += dt
        step += 1

        _bk = solver._backend
        dV_dev = solver._grid.cell_volumes() if solver._alpha_grid > 1.0 else None
        if grid_will_rebuild:
            diag.X = np.asarray(_bk.to_host(solver.X))
            diag.Y = np.asarray(_bk.to_host(solver.Y))
        diag.collect(t, psi, u, v, _bk.xp.asarray(p), dV=dV_dev)
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
                print(
                    f"          kappa_max={d['kappa_max']:.3e}  "
                    f"ppe_rhs={d['ppe_rhs_max']:.3e}  "
                    f"bf_res={d['bf_residual_max']:.3e}  "
                    f"div_u={d['div_u_max']:.3e}"
                )

        ke = diag.last("kinetic_energy", 0.0)
        if np.isnan(ke) or ke > 1e6:
            print(f"  BLOWUP at step={step}, t={t:.4f}")
            break

    results = {**diag.to_arrays(), "snapshots": snaps}
    if dbg_history:
        results["debug_diagnostics"] = {
            key: np.array([entry[key] for entry in dbg_history]) for key in dbg_history[0]
        }
    return results
