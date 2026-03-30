"""
Oscillating Droplet — Lamb-Formula Comparison (Phase 4.2)

Theoretical background
----------------------
For a slightly deformed droplet (mode n = 2), Lamb's inviscid formula gives:

    ω₂ = sqrt( n(n−1)(n+2) σ / ((ρ_l + ρ_g) R³) )
       = sqrt( 8 σ / ((ρ_l + ρ_g) R³) )

In our non-dimensional system (ρ_l = 1, σ = 1/We):

    ω₂ = sqrt( 8 / (We (1 + rho_ratio) R³) )
    T₂ = 2π / ω₂

Viscous damping rate (Lamb, n = 2):

    λ = (n−1)(2n+1) μ_l / (ρ_l R²) = 5 / (Re R²)

The amplitude decays as exp(−λ t).

Setup
-----
Domain        : [0,1]²   Wall BC
Initial shape : ellipse with semi-axes a = R(1+δ), b = R(1−δ), δ = 0.05
               Approximate SDF: φ(x,y) = r − R − δ R cos(2θ)
               ψ₀ = 1 / (1 + exp(φ/ε))
R = 0.25, δ = 0.05 (5 % deformation, linear regime)
Fluid: Re = 100, We = 1 (strong surface tension), Fr = ∞, rho_ratio = 0.01

Measured period and damping from simulation
-------------------------------------------
Track the y-extent of the droplet:  e(t) = max{y : ψ > 0.5} − min{y : ψ > 0.5}
The n=2 mode oscillates as e(t) ~ e₀ + A exp(−λ t) cos(ω₂ t)
Extract ω₂_num and λ_num by finding successive maxima.

Pass criteria
-------------
|T₂_num / T₂_Lamb − 1| < 0.05   (5 % period tolerance)
|λ_num  / λ_Lamb  − 1| < 0.20   (20 % decay-rate tolerance)

Usage::

    python3 experiments/oscillating_droplet.py
"""

from __future__ import annotations

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import find_peaks  # type: ignore

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from twophase.config import (
    SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig,
)
from twophase.simulation.builder import SimulationBuilder

# ── Parameters ────────────────────────────────────────────────────────────────

RADIUS    = 0.25
CENTER    = (0.5, 0.5)
DELTA     = 0.05     # fractional deformation amplitude

RE        = 100.0
FR        = 1.0e10   # no gravity
WE        = 1.0      # strong surface tension → fast oscillation
RHO_RATIO = 0.01

N         = 64       # grid resolution

SEP = "=" * 68


# ── Analytical Lamb values ────────────────────────────────────────────────────

def lamb_period(we: float, rho_ratio: float, R: float) -> float:
    """T₂ = 2π / sqrt(8 σ / ((ρ_l + ρ_g) R³))  [dimensionless, ρ_l = 1]."""
    sigma   = 1.0 / we          # σ = ρ_l U_ref² L_ref / We = 1/We
    omega2  = np.sqrt(8.0 * sigma / ((1.0 + rho_ratio) * R ** 3))
    return 2.0 * np.pi / omega2


def lamb_decay(re: float, R: float) -> float:
    """λ = 5 / (Re R²)  (n = 2 damping rate)."""
    return 5.0 / (re * R ** 2)


# ── Build initial ellipse IC ──────────────────────────────────────────────────

def build_ellipse_psi(grid, eps: float, cx: float, cy: float,
                      R: float, delta: float) -> np.ndarray:
    """CLS field for a slightly elliptical droplet.

    Uses the approximate SDF for small deformation:
        φ(x,y) = r − R − δ R cos(2θ)
    """
    X, Y = grid.meshgrid()
    r   = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    theta = np.arctan2(Y - cy, X - cx)
    phi = r - R - delta * R * np.cos(2.0 * theta)
    arg = np.clip(phi / eps, -500.0, 500.0)
    return 1.0 / (1.0 + np.exp(arg))


# ── Config ────────────────────────────────────────────────────────────────────

T_LAMB = lamb_period(WE, RHO_RATIO, RADIUS)
T_END  = 4.0 * T_LAMB   # run ~4 periods


def _make_config() -> SimulationConfig:
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(
            Re=RE, Fr=FR, We=WE,
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


# ── Run simulation ────────────────────────────────────────────────────────────

def run() -> dict:
    cfg = _make_config()
    sim = SimulationBuilder(cfg).build()

    psi_np = build_ellipse_psi(
        sim.grid, sim.eps, CENTER[0], CENTER[1], RADIUS, DELTA
    )
    sim.psi.data = sim.backend.to_device(psi_np)

    times:   list[float] = []
    extents: list[float] = []   # y-extent of ψ > 0.5

    def record(s):
        xp  = s.backend.xp
        psi = xp.asarray(s.psi.data)
        # node coordinates along y-axis
        y_coords = s.grid.coords[1]   # shape (N+1,)
        mask = psi > 0.5              # shape (N+1, N+1)
        # rows (y-indices) that have at least one ψ > 0.5
        y_present = xp.where(xp.any(mask, axis=0))[0]
        if len(y_present) > 0:
            y_min = float(y_coords[int(y_present.min())])
            y_max = float(y_coords[int(y_present.max())])
            ext = y_max - y_min
        else:
            ext = 0.0
        times.append(s.time)
        extents.append(ext)

    record(sim)
    # Record ~40 samples per period
    steps_per_period = max(1, int(T_LAMB / (0.25 / N)))
    interval = max(1, steps_per_period // 40)
    sim.run(t_end=T_END, output_interval=interval,
            verbose=False, callback=record)

    return {
        "times":   np.array(times),
        "extents": np.array(extents),
    }


# ── Analyse oscillation ───────────────────────────────────────────────────────

def analyse(times: np.ndarray, extents: np.ndarray) -> dict:
    """Extract period and decay rate from y-extent oscillation."""
    # Remove DC offset (mean extent after first oscillation)
    e_mean  = np.mean(extents)
    e_fluct = extents - e_mean

    # Find peaks of the oscillation
    peaks, _ = find_peaks(e_fluct, height=0.1 * np.max(np.abs(e_fluct)),
                          distance=3)
    troughs, _ = find_peaks(-e_fluct, height=0.1 * np.max(np.abs(e_fluct)),
                            distance=3)

    period_num = float("nan")
    decay_num  = float("nan")

    if len(peaks) >= 2:
        # Period from spacing between peaks
        peak_times = times[peaks]
        dt_peaks   = np.diff(peak_times)
        period_num = float(np.median(dt_peaks))

    if len(peaks) >= 2:
        # Decay rate from log of successive peak amplitudes
        amps  = np.abs(e_fluct[peaks])
        if np.all(amps > 0):
            log_amps = np.log(amps)
            slope, _ = np.polyfit(times[peaks], log_amps, 1)
            decay_num = float(-slope)

    return {"period_num": period_num, "decay_num": decay_num, "n_peaks": len(peaks)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    T_lamb = lamb_period(WE, RHO_RATIO, RADIUS)
    lam    = lamb_decay(RE, RADIUS)

    print(SEP)
    print("Oscillating Droplet — Lamb Formula Comparison (Phase 4.2)")
    print(f"  R={RADIUS}, δ={DELTA}, N={N}, Re={RE}, We={WE}, Fr=∞")
    print(f"  rho_ratio={RHO_RATIO}")
    print(f"  Lamb period  T₂   = {T_lamb:.5f}")
    print(f"  Lamb decay   λ    = {lam:.5f}")
    print(f"  Run until    T    = {T_END:.4f}  (~{T_END/T_lamb:.1f} periods)")
    print(SEP)

    print("  Running simulation ...", flush=True)
    data    = run()
    results = analyse(data["times"], data["extents"])

    period_num = results["period_num"]
    decay_num  = results["decay_num"]

    period_err = abs(period_num / T_lamb - 1.0) if not np.isnan(period_num) else float("nan")
    decay_err  = abs(decay_num  / lam    - 1.0) if not np.isnan(decay_num)  else float("nan")

    pass_T = period_err <= 0.05
    pass_L = decay_err  <= 0.20

    print(f"\n  Quantity        Lamb (theory)   Numerical       Rel. error   Pass")
    print(f"  {'─'*65}")
    print(f"  Period  T₂     {T_lamb:>13.5f}   "
          f"{period_num:>13.5f}   {period_err:>9.4f}   {'✓' if pass_T else '✗'}")
    print(f"  Decay   λ      {lam:>13.5f}   "
          f"{decay_num:>13.5f}   {decay_err:>9.4f}   {'✓' if pass_L else '✗'}")
    print(f"\n  Overall: {'PASS ✓' if pass_T and pass_L else 'FAIL ✗'}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    os.makedirs("results/oscillating_droplet", exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.suptitle("Oscillating Droplet — Lamb Formula Comparison", fontsize=11)

    t = data["times"]
    e = data["extents"]

    ax = axes[0]
    ax.plot(t, e, label="Simulation  y-extent")
    # Lamb envelope
    e0    = RADIUS * 2.0
    A_est = DELTA * RADIUS * 2.0
    env   = e0 + A_est * np.exp(-lam * t) * np.cos(2 * np.pi * t / T_lamb)
    ax.plot(t, env, "--", label=f"Lamb T₂={T_lamb:.4f}", alpha=0.8)
    ax.set_xlabel("t")
    ax.set_ylabel("y-extent of ψ > 0.5")
    ax.set_title("y-extent oscillation")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    e_fluct = e - np.mean(e)
    ax.plot(t, e_fluct, label="fluctuation e(t)−ē")
    ax.axhline(0, color="k", linewidth=0.5)
    if not np.isnan(period_num):
        ax.set_title(f"Fluctuation  T_num={period_num:.4f}  (Lamb={T_lamb:.4f})")
    else:
        ax.set_title("Fluctuation (period extraction failed)")
    ax.set_xlabel("t")
    ax.set_ylabel("e − ē")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = "results/oscillating_droplet/oscillating_droplet.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"\n  Plot saved: {path}")

    return {
        "T_lamb": T_lamb, "lambda_lamb": lam,
        "T_num": period_num, "lambda_num": decay_num,
        "T_err": period_err, "lambda_err": decay_err,
        "pass_T": pass_T, "pass_L": pass_L,
    }


if __name__ == "__main__":
    main()
