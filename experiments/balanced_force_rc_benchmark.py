"""
Balanced-Force Rhie-Chow Extension — Parasitic Current Benchmark.

Implements the verification procedure described in §7.4 (sec:balanced_force_verification)
and §7.3.2 (sec:rc_balanced_force) of the paper.

Experiment design
-----------------
Static droplet: circular liquid drop of radius R=0.25 centred in a unit
square, ρ_l/ρ_g = 1000, We = 1, no gravity.  Initial velocity u = 0.

Two solver configurations are compared:

  (A) Standard RC  — eq:rc-face (pressure correction only, current default)
  (B) BF-RC        — eq:rc-face-balanced (adds surface-tension correction to
                     the RC bracket; implemented in rhie_chow.py §7.3.2)

Measured quantities
-------------------
1. ||u||_∞ vs time — parasitic current growth/saturation.
2. Laplace pressure jump Δp vs theoretical σ/R = 4.0.
3. Grid-convergence of ||u||_∞ at t=t_end: expect O(h²) for both configs
   (CSF-model-error limited), but BF-RC should have a substantially smaller
   prefactor.

Expected results (§7.4 algbox)
-------------------------------
  Standard RC, N=64 : ||u||_∞ ~ O(10⁻²) (operator mismatch drives parasitic flow)
  BF-RC,       N=64 : ||u||_∞ ~ O(10⁻³)–O(10⁻⁴) (mismatch cancelled)
  Convergence order  : q ≈ 2 for both (CSF O(ε²) ~ O(h²) floor)

Usage::

    python experiments/balanced_force_rc_benchmark.py

Outputs::

    results/balanced_force_rc/  (PNG figures + console table)
"""

from __future__ import annotations
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

# Ensure src/ is on the path when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from twophase.config import (
    SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig,
)
from twophase.simulation.builder import SimulationBuilder
from twophase.initial_conditions import InitialConditionBuilder, Circle


# ── Benchmark parameters ────────────────────────────────────────────────────

RADIUS   = 0.25
CENTER   = (0.5, 0.5)
WE       = 1.0
RHO_RATIO = 0.001   # ρ_g / ρ_l = 1/1000
RE       = 100.0
T_END    = 0.05     # short run — enough to see parasitic current saturation
N_SINGLE = 64       # resolution for time-series comparison
N_LIST   = [32, 64, 128]   # grid-convergence resolutions

LAPLACE_REF = 1.0 / (WE * RADIUS)   # = 4.0

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "balanced_force_rc")


# ── Simulation helpers ───────────────────────────────────────────────────────

def _make_config(N: int) -> SimulationConfig:
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(
            Re=RE, Fr=1.0e10, We=WE,
            rho_ratio=RHO_RATIO, mu_ratio=RHO_RATIO,
        ),
        numerics=NumericsConfig(
            epsilon_factor=1.5,
            reinit_steps=4,
            cfl_number=0.25,
            t_end=T_END,
            cn_viscous=True,
            bc_type="wall",
        ),
        solver=SolverConfig(ppe_solver_type="lu"),
    )


def run_case(N: int, use_bf_rc: bool, verbose: bool = True) -> dict:
    """Run one static-droplet case and return diagnostics.

    Parameters
    ----------
    N          : grid points per side
    use_bf_rc  : True → Balanced-Force RC (eq:rc-face-balanced)
                 False → standard RC (eq:rc-face)
    """
    cfg = _make_config(N)
    sim = SimulationBuilder(cfg).build()

    psi_np = (
        InitialConditionBuilder(background_phase="gas")
        .add(Circle(center=CENTER, radius=RADIUS))
        .build(sim.grid, sim.eps)
    )
    sim.psi.data = sim.backend.to_device(psi_np)

    # Monkey-patch the _solve_pressure step to inject kappa/psi/we into RC when
    # Balanced-Force mode is requested.
    if use_bf_rc:
        _patch_bf_rc(sim)

    times: list[float] = []
    max_vel: list[float] = []

    def record(s):
        xp = s.backend.xp
        u_max = max(float(xp.max(xp.abs(v))) for v in s.velocity)
        times.append(s.time)
        max_vel.append(u_max)

    record(sim)

    output_interval = max(1, int(T_END / 0.01 / 5))
    sim.run(
        t_end=T_END,
        output_interval=output_interval,
        verbose=verbose,
        callback=record,
    )

    # Laplace pressure
    xp = sim.backend.xp
    psi = sim.psi.data
    p   = sim.pressure.data
    inside  = psi > 0.5
    outside = psi < 0.5
    n_in  = int(xp.sum(inside))
    n_out = int(xp.sum(outside))
    dp = 0.0
    dp_err = 1.0
    if n_in > 0 and n_out > 0:
        p_in  = float(xp.sum(p[inside]))  / n_in
        p_out = float(xp.sum(p[outside])) / n_out
        dp = p_in - p_out
        dp_err = abs(dp - LAPLACE_REF) / abs(LAPLACE_REF)

    sigma_over_mu = RE / WE
    parasitic_norm = max_vel[-1] / max(sigma_over_mu, 1e-14)

    return {
        "times":            np.array(times),
        "max_velocity":     np.array(max_vel),
        "laplace_pressure": dp,
        "laplace_error":    dp_err,
        "parasitic_norm":   parasitic_norm,
        "N": N,
        "use_bf_rc": use_bf_rc,
    }


def _patch_bf_rc(sim) -> None:
    """Replace sim._solve_pressure with a version that passes kappa/psi/we to RC.

    This is the minimal change to exercise eq:rc-face-balanced without
    modifying the TwoPhaseSimulation orchestration code.  In a future
    integration this logic would live inside _core.py with a config flag.
    """
    original_solve = sim._solve_pressure
    we = sim.config.fluid.We

    def _solve_pressure_bf(vel_star, dt):
        div_rc = sim.rhie_chow.face_velocity_divergence(
            vel_star,
            sim.pressure.data,
            sim.rho.data,
            dt,
            kappa=sim.kappa.data,
            psi=sim.psi.data,
            we=we,
        )
        delta_p = sim.ppe_solver.solve(
            div_rc / dt, sim.rho.data, dt, p_init=None,
        )
        sim.pressure.data = sim.pressure.data + delta_p
        return delta_p

    sim._solve_pressure = _solve_pressure_bf


# ── Analysis helpers ─────────────────────────────────────────────────────────

def convergence_order(norms: list[float], h_list: list[float]) -> list[float]:
    orders = []
    for i in range(1, len(norms)):
        if norms[i] > 0 and norms[i - 1] > 0:
            q = np.log2(norms[i - 1] / norms[i]) / np.log2(h_list[i - 1] / h_list[i])
        else:
            q = float("nan")
        orders.append(q)
    return orders


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── 1. Time-series comparison at N=N_SINGLE ──────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Static Droplet — Parasitic Current Comparison (N={N_SINGLE})")
    print(f"{'='*60}")
    print("  Running standard RC …")
    res_std = run_case(N_SINGLE, use_bf_rc=False, verbose=False)
    print("  Running Balanced-Force RC …")
    res_bf  = run_case(N_SINGLE, use_bf_rc=True, verbose=False)

    print(f"\n  Standard RC  : ||u||_∞(t_end) = {res_std['max_velocity'][-1]:.3e}"
          f"  Δp = {res_std['laplace_pressure']:.4f}"
          f"  (err {res_std['laplace_error']:.2e})")
    print(f"  BF-RC        : ||u||_∞(t_end) = {res_bf['max_velocity'][-1]:.3e}"
          f"  Δp = {res_bf['laplace_pressure']:.4f}"
          f"  (err {res_bf['laplace_error']:.2e})")

    improvement = (res_std['max_velocity'][-1] / max(res_bf['max_velocity'][-1], 1e-20))
    print(f"\n  BF-RC parasitic reduction factor: {improvement:.1f}×")

    # Time-series plot
    fig, ax = plt.subplots(figsize=(7, 4), dpi=100)
    ax.semilogy(res_std["times"], res_std["max_velocity"] + 1e-20,
                "b-o", markersize=3, label="Standard RC (eq:rc-face)")
    ax.semilogy(res_bf["times"],  res_bf["max_velocity"]  + 1e-20,
                "r-s", markersize=3, label="BF-RC (eq:rc-face-balanced)")
    sigma_over_mu = RE / WE
    ax.axhline(1e-4 * sigma_over_mu, color="gray", linestyle="--",
               label=r"threshold $10^{-4}(\sigma/\mu)$")
    ax.set_xlabel("time $t$")
    ax.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax.set_title(f"Stationary Droplet N={N_SINGLE}: Parasitic Currents")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.4)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "timeseries_comparison.png")
    fig.savefig(path, bbox_inches="tight")
    print(f"\n  Saved: {path}")
    plt.close(fig)

    # ── 2. Grid convergence ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  Grid Convergence (parasitic current vs h)")
    print(f"{'='*60}")
    h_list = [1.0 / N for N in N_LIST]
    norms_std: list[float] = []
    norms_bf:  list[float] = []

    for N in N_LIST:
        print(f"  N={N} std …", end="", flush=True)
        r = run_case(N, use_bf_rc=False, verbose=False)
        norms_std.append(r["parasitic_norm"])
        print(f" {r['parasitic_norm']:.3e}   bf …", end="", flush=True)
        r = run_case(N, use_bf_rc=True, verbose=False)
        norms_bf.append(r["parasitic_norm"])
        print(f" {r['parasitic_norm']:.3e}")

    orders_std = convergence_order(norms_std, h_list)
    orders_bf  = convergence_order(norms_bf,  h_list)

    print(f"\n  {'N':>6}  {'h':>8}  {'Std RC norm':>12}  {'order':>6}  "
          f"{'BF-RC norm':>12}  {'order':>6}")
    print("  " + "-" * 68)
    for i, (N, h) in enumerate(zip(N_LIST, h_list)):
        o_std = f"{orders_std[i-1]:.2f}" if i > 0 else "—"
        o_bf  = f"{orders_bf[i-1]:.2f}"  if i > 0 else "—"
        print(f"  {N:>6}  {h:>8.5f}  {norms_std[i]:>12.3e}  {o_std:>6}  "
              f"{norms_bf[i]:>12.3e}  {o_bf:>6}")

    # Convergence plot
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    ax.loglog(h_list, norms_std, "b-o", label="Standard RC")
    ax.loglog(h_list, norms_bf,  "r-s", label="BF-RC")
    # O(h²) reference
    h_ref = np.array(h_list)
    scale = norms_std[0] / h_ref[0] ** 2
    ax.loglog(h_ref, scale * h_ref ** 2, "k--", alpha=0.5, label=r"$O(h^2)$ ref")
    ax.set_xlabel(r"$h = 1/N$")
    ax.set_ylabel(r"$\|\mathbf{u}\|_\infty / (\sigma/\mu)$")
    ax.set_title("Parasitic Current Grid Convergence")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.4, which="both")
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "convergence.png")
    fig.savefig(path, bbox_inches="tight")
    print(f"\n  Saved: {path}")
    plt.close(fig)

    # ── 3. Summary verdict ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  VERDICT (§7.4 acceptance criteria)")
    print(f"{'='*60}")
    laplace_ok  = abs(res_bf["laplace_pressure"] - LAPLACE_REF) / LAPLACE_REF < 0.05
    parasitic_ok = res_bf["parasitic_norm"] <= 1e-3
    print(f"  Laplace Δp = {res_bf['laplace_pressure']:.4f} "
          f"(theory {LAPLACE_REF:.4f}) → {'PASS' if laplace_ok else 'FAIL'}")
    print(f"  BF-RC ||u_para||/(σ/μ) = {res_bf['parasitic_norm']:.3e} "
          f"≤ 1e-3 → {'PASS' if parasitic_ok else 'FAIL'}")
    print(f"  Reduction vs std RC: {improvement:.1f}× → "
          f"{'PASS' if improvement >= 5.0 else 'MARGINAL'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
