"""
Static Droplet — Balanced-Force Ultimate Verification (Phase 4.1)

Setup
-----
Circular liquid droplet, R = 0.25, centred in a unit square [0,1]².
No gravity (Fr → ∞).  Initial velocity u = 0.  Wall BC.

Theoretical result
------------------
For a perfectly balanced discretisation (Balanced-Force property):
    ||u||_∞(t) = 0  ∀ t > 0

For a CSF-based scheme with O(h²) interface smearing, the practical floor is
    ||u||_∞ ~ C_parasitic × (σ/μ_l) × h²

Pass criteria (from §4.1 of development spec)
----------------------------------------------
- Laplace pressure jump  Δp = p_in − p_out  close to  σ/R  (Weber-number formula)
- ||u||_∞ at t = T_END  ≤  Ca_tol × (σ/μ_l)
  where  Ca_tol = 1e-3  (capillary tolerance; O(h²) CSF floor at N=64)

Usage::

    python3 experiments/static_droplet.py
"""

from __future__ import annotations

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from twophase.config import (
    SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig,
)
from twophase.simulation.builder import SimulationBuilder
from twophase.initial_conditions import InitialConditionBuilder, Circle

# ── Parameters ────────────────────────────────────────────────────────────────

RADIUS  = 0.25
CENTER  = (0.5, 0.5)

# Fluid: ρ_ratio = 0.1, μ_ratio = 0.1
# Surface tension We = 10 → σ = ρ U² L / We = 1/10 (non-dim)
# Re = 100 → μ_l = 1/Re = 0.01 (non-dim)
# Fr → ∞ (no gravity)
RE        = 100.0
FR        = 1.0e10
WE        = 10.0
RHO_RATIO = 0.1
MU_RATIO  = 0.1

T_END     = 0.5          # run for half a convective time unit
N_LIST    = [32, 64, 128]

# Laplace reference: Δp_ref = σ / R = (1/We) / R
LAPLACE_REF = 1.0 / (WE * RADIUS)   # = 0.4  (non-dimensional)

# Parasitic current tolerance: Ca_tol × σ / μ_l = 1e-3 × (1/We) / (1/Re)
CA_TOL = 1e-3
SIGMA_OVER_MU = RE / WE              # = 10.0

SEP = "=" * 68


# ── Config factory ────────────────────────────────────────────────────────────

def _make_config(N: int) -> SimulationConfig:
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(
            Re=RE, Fr=FR, We=WE,
            rho_ratio=RHO_RATIO, mu_ratio=MU_RATIO,
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


# ── Single run ────────────────────────────────────────────────────────────────

def run_one(N: int) -> dict:
    cfg = _make_config(N)
    sim = SimulationBuilder(cfg).build()

    psi_np = (
        InitialConditionBuilder(background_phase="gas")
        .add(Circle(center=CENTER, radius=RADIUS))
        .build(sim.grid, sim.eps)
    )
    sim.psi.data = sim.backend.to_device(psi_np)

    times: list[float] = []
    max_vel: list[float] = []

    def record(s):
        xp = s.backend.xp
        u_max = max(float(xp.max(xp.abs(v))) for v in s.velocity)
        times.append(s.time)
        max_vel.append(u_max)

    record(sim)
    output_interval = max(1, int(T_END / 0.02 / 5))
    sim.run(t_end=T_END, output_interval=output_interval,
            verbose=False, callback=record)

    xp  = sim.backend.xp
    psi = sim.psi.data
    p   = sim.pressure.data
    inside  = psi > 0.5
    outside = psi < 0.5
    n_in  = int(xp.sum(inside))
    n_out = int(xp.sum(outside))
    dp = float("nan")
    dp_err = float("nan")
    if n_in > 0 and n_out > 0:
        p_in  = float(xp.sum(p[inside]))  / n_in
        p_out = float(xp.sum(p[outside])) / n_out
        dp    = p_in - p_out
        dp_err = abs(dp - LAPLACE_REF) / abs(LAPLACE_REF)

    u_final = max_vel[-1]
    pass_u  = u_final <= CA_TOL * SIGMA_OVER_MU
    pass_dp = dp_err <= 0.05 if not np.isnan(dp_err) else False

    return {
        "N": N, "h": 1.0 / N,
        "times": np.array(times),
        "max_vel": np.array(max_vel),
        "u_final": u_final,
        "laplace_dp": dp,
        "laplace_err": dp_err,
        "pass_u":  pass_u,
        "pass_dp": pass_dp,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(SEP)
    print("Static Droplet — Balanced-Force Verification (Phase 4.1)")
    print(f"  R={RADIUS}, center={CENTER}, Re={RE}, We={WE}, Fr=∞")
    print(f"  rho_ratio={RHO_RATIO}, T_end={T_END}")
    print(f"  Laplace ref  Δp_ref = σ/R = {LAPLACE_REF:.4f}")
    print(f"  Pass: ||u||_∞ ≤ Ca_tol×σ/μ = {CA_TOL}×{SIGMA_OVER_MU} = {CA_TOL * SIGMA_OVER_MU:.3e}")
    print(SEP)

    results = []
    header = f"  {'N':>5}  {'h':>7}  {'u_final':>10}  {'Δp':>8}  {'Δp_err':>8}  {'pass_u':>7}  {'pass_Δp':>8}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for N in N_LIST:
        print(f"  Running N={N} ...", end="", flush=True)
        r = run_one(N)
        results.append(r)
        mark_u  = "✓" if r["pass_u"]  else "✗"
        mark_dp = "✓" if r["pass_dp"] else "✗"
        print(f"\r  {N:>5}  {r['h']:>7.4f}  {r['u_final']:>10.3e}  "
              f"{r['laplace_dp']:>8.4f}  {r['laplace_err']:>8.3e}  "
              f"{mark_u:>7}  {mark_dp:>8}")

    # Convergence slope for ||u||_∞
    hs  = [r["h"]       for r in results]
    us  = [r["u_final"] for r in results]
    ok  = [u > 0 for u in us]
    if sum(ok) >= 2:
        slope = float(np.polyfit(np.log([hs[i] for i, o in enumerate(ok) if o]),
                                 np.log([us[i] for i, o in enumerate(ok) if o]), 1)[0])
        print(f"\n  ||u||_∞ convergence slope vs h: {slope:.2f}")
        print(f"  (Expected: ≈ 2.0 for CSF O(h²) parasitic-current floor)")

    overall = all(r["pass_u"] and r["pass_dp"] for r in results)
    print(f"\n  Overall: {'PASS ✓' if overall else 'FAIL ✗'}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    os.makedirs("results/static_droplet", exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    fig.suptitle("Static Droplet — Balanced-Force Verification", fontsize=11)

    # left: ||u||_∞ vs time
    ax = axes[0]
    for r in results:
        ax.semilogy(r["times"], r["max_vel"] + 1e-20, label=f"N={r['N']}")
    ax.axhline(CA_TOL * SIGMA_OVER_MU, color="red", linestyle="--",
               label=f"Ca_tol = {CA_TOL:.0e}")
    ax.set_xlabel("t")
    ax.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax.set_title(r"Parasitic current $\|\mathbf{u}\|_\infty(t)$")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    # right: ||u||_∞ vs h (grid convergence)
    ax = axes[1]
    ax.loglog(hs, us, "o-", label=r"$\|\mathbf{u}\|_\infty$ at $t=T$")
    h_arr = np.array(hs)
    ax.loglog(h_arr, us[0] * (h_arr / hs[0]) ** 2,
              "--", color="gray", label="O(h²)")
    ax.set_xlabel("h = 1/N")
    ax.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax.set_title("Grid convergence of parasitic current")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    plt.tight_layout()
    path = "results/static_droplet/static_droplet.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"\n  Plot saved: {path}")

    return results


if __name__ == "__main__":
    main()
