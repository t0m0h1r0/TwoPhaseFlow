"""
Rising Bubble Benchmark — Hysing et al. (2009) Case 1 (Phase 4.3)

Reference
---------
Hysing, S., Turek, S., Kuzmin, D., Parolini, N., Burman, E., Ganesan, S.,
& Tobiska, L. (2009). Quantitative benchmark computations of two-dimensional
bubble dynamics. International Journal for Numerical Methods in Fluids,
60(11), 1259–1288.

Physical setup (Case 1)
-----------------------
  ρ_l = 1000,  ρ_g = 100,  μ_l = 10,   μ_g = 1
  σ   = 24.5,  g   = 0.98 (downward, y-direction)
  R   = 0.25   (bubble radius),  domain [0,1]×[0,2]
  initial centre (0.5, 0.5),  u₀ = 0

Non-dimensional system (L_ref = 1, U_ref = sqrt(g × D) = sqrt(0.98 × 0.5))
--------------------------------------------------------------------------
  Re        = ρ_l U_ref L_ref / μ_l        ≈ 70.00
  We        = ρ_l U_ref² L_ref / σ         ≈ 20.00
  Fr        = U_ref / sqrt(g L_ref)         ≈ 0.7071
  rho_ratio = ρ_g / ρ_l                    = 0.10
  mu_ratio  = μ_g / μ_l                    = 0.10

Hysing benchmark quantities (Case 1, Table 2 reference values)
--------------------------------------------------------------
  Terminal rise velocity  U_T / U_ref  ≈  0.2417
  Circularity at t = 3   c(3)          ≈  0.9013
  Centroid height at t = 3  y_c(3)     (varies by scheme; ~1.0–1.2)

Run time T = 3 × U_ref / L_ref ≈ 2.12 (dimensionless)

Measured quantities
-------------------
1. Rise velocity  v_c(t) = d(y_c)/dt,  where  y_c = ∫ y ψ dV / ∫ ψ dV
2. Circularity    c(t)   = 2 sqrt(π A) / P
   A = bubble area (cells with ψ > 0.5)
   P = perimeter (estimated from |∇ψ| integral)
3. Centroid height y_c(t)

Usage::

    python3 experiments/rising_bubble.py
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

# ── Physical → dimensionless conversion (Case 1) ──────────────────────────────

_RHO_L  = 1000.0
_RHO_G  = 100.0
_MU_L   = 10.0
_MU_G   = 1.0
_SIGMA  = 24.5
_G_PHYS = 0.98
_D      = 0.5          # bubble diameter (physical)
_L_REF  = 1.0          # domain width (physical)
_U_REF  = np.sqrt(_G_PHYS * _D)   # ≈ 0.7000

RE        = _RHO_L * _U_REF * _L_REF / _MU_L          # ≈ 70.00
WE        = _RHO_L * _U_REF ** 2 * _L_REF / _SIGMA    # ≈ 20.00
FR        = _U_REF / np.sqrt(_G_PHYS * _L_REF)         # ≈ 0.7071
RHO_RATIO = _RHO_G / _RHO_L                             # = 0.10
MU_RATIO  = _MU_G  / _MU_L                              # = 0.10

# Dimensionless bubble: R = 0.25 in [0,1]×[0,2] domain
RADIUS    = 0.25
CENTER    = (0.5, 0.5)
LX, LY    = 1.0, 2.0

# Run until t_phys = 3  →  t_dimless = t_phys × U_ref / L_ref
T_PHYS = 3.0
T_END  = T_PHYS * _U_REF / _L_REF   # ≈ 2.10

# Hysing reference (Case 1): terminal velocity in units of U_ref
U_T_REF    = 0.2417
C_REF      = 0.9013   # circularity at t_phys = 3

N = 64   # grid points along x (y uses 2N)

SEP = "=" * 68


# ── Config ────────────────────────────────────────────────────────────────────

def _make_config(N: int) -> SimulationConfig:
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, 2 * N), L=(LX, LY)),
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


# ── Diagnostic helpers ────────────────────────────────────────────────────────

def _centroid_and_area(psi: np.ndarray, grid) -> tuple[float, float]:
    """Return (y_centroid, area) using cells with ψ > 0.5."""
    X, Y = grid.meshgrid()
    h_x = float(grid.L[0] / grid.N[0])
    h_y = float(grid.L[1] / grid.N[1])
    cell_area = h_x * h_y
    inside = psi > 0.5
    A   = float(np.sum(inside)) * cell_area
    if A > 0:
        y_c = float(np.sum(Y[inside])) * cell_area / A
    else:
        y_c = float("nan")
    return y_c, A


def _circularity(psi: np.ndarray, grid) -> float:
    """c = 2 sqrt(π A) / P,  perimeter from |∇ψ| integral."""
    X, Y = grid.meshgrid()
    h_x = float(grid.L[0] / grid.N[0])
    h_y = float(grid.L[1] / grid.N[1])
    cell_area = h_x * h_y

    _, A = _centroid_and_area(psi, grid)
    if A <= 0:
        return float("nan")

    # Perimeter estimate: P = ∫ |∇ψ| dV  (uses central differences)
    dpsi_dx = (psi[2:, 1:-1] - psi[:-2, 1:-1]) / (2.0 * h_x)
    dpsi_dy = (psi[1:-1, 2:] - psi[1:-1, :-2]) / (2.0 * h_y)
    grad_mag = np.sqrt(dpsi_dx ** 2 + dpsi_dy ** 2)
    P = float(np.sum(grad_mag)) * cell_area

    if P > 0:
        return 2.0 * np.sqrt(np.pi * A) / P
    return float("nan")


# ── Run ───────────────────────────────────────────────────────────────────────

def run(N: int) -> dict:
    cfg = _make_config(N)
    sim = SimulationBuilder(cfg).build()

    psi_np = (
        InitialConditionBuilder(background_phase="liquid")
        .add(Circle(center=CENTER, radius=RADIUS, interior_phase="gas"))
        .build(sim.grid, sim.eps)
    )
    sim.psi.data = sim.backend.to_device(psi_np)

    times:         list[float] = []
    y_centroids:   list[float] = []
    circularities: list[float] = []

    def record(s):
        xp  = s.backend.xp
        psi = np.asarray(xp.asarray(s.psi.data))
        y_c, _A = _centroid_and_area(psi, s.grid)
        c       = _circularity(psi, s.grid)
        times.append(s.time)
        y_centroids.append(y_c)
        circularities.append(c)

    record(sim)
    # ~20 records per convective time unit
    dt_cfl  = 0.25 / N
    steps_per_unit = max(1, int(1.0 / dt_cfl))
    interval = max(1, steps_per_unit // 20)
    sim.run(t_end=T_END, output_interval=interval,
            verbose=True, callback=record)

    t_arr = np.array(times)
    yc_arr = np.array(y_centroids)
    c_arr  = np.array(circularities)

    # Rise velocity: finite difference of centroid
    v_c = np.gradient(yc_arr, t_arr)

    # Terminal velocity: mean of last 10 % of run
    n_tail = max(1, len(t_arr) // 10)
    U_T_num = float(np.mean(v_c[-n_tail:]))

    # Circularity at t_end (closest to T_END)
    c_final = float(c_arr[-1])

    return {
        "N": N,
        "times":         t_arr,
        "y_centroids":   yc_arr,
        "circularities": c_arr,
        "v_c":           v_c,
        "U_T_num":       U_T_num,
        "c_final":       c_final,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(SEP)
    print("Rising Bubble — Hysing et al. (2009) Case 1 Benchmark (Phase 4.3)")
    print(f"  ρ_l={_RHO_L}, ρ_g={_RHO_G}, μ_l={_MU_L}, μ_g={_MU_G}")
    print(f"  σ={_SIGMA}, g={_G_PHYS}")
    print(f"  U_ref={_U_REF:.4f},  Re={RE:.2f},  We={WE:.2f},  Fr={FR:.4f}")
    print(f"  rho_ratio={RHO_RATIO},  mu_ratio={MU_RATIO}")
    print(f"  R={RADIUS},  center={CENTER},  domain [{LX}×{LY}]")
    print(f"  N={N}×{2*N},  T_end={T_END:.4f}  (t_phys={T_PHYS})")
    print(f"  Hysing ref:  U_T={U_T_REF:.4f},  c(t=3)={C_REF:.4f}")
    print(SEP)

    print("  Running simulation ...", flush=True)
    r = run(N)

    U_T_err = abs(r["U_T_num"] / U_T_REF - 1.0)
    c_err   = abs(r["c_final"] / C_REF   - 1.0)

    # Pass: terminal velocity within 10 %, circularity within 5 %
    pass_U = U_T_err <= 0.10
    pass_c = c_err   <= 0.05

    print(f"\n  Quantity               Hysing ref    Simulation    Rel. error   Pass")
    print(f"  {'─' * 68}")
    print(f"  Terminal vel U_T       {U_T_REF:>10.4f}    {r['U_T_num']:>10.4f}    "
          f"{U_T_err:>8.4f}   {'✓' if pass_U else '✗'}")
    print(f"  Circularity c(t_end)   {C_REF:>10.4f}    {r['c_final']:>10.4f}    "
          f"{c_err:>8.4f}   {'✓' if pass_c else '✗'}")
    print(f"\n  Overall: {'PASS ✓' if pass_U and pass_c else 'FAIL ✗'}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    os.makedirs("results/rising_bubble", exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    fig.suptitle("Rising Bubble — Hysing et al. (2009) Case 1", fontsize=11)

    t  = r["times"]
    yc = r["y_centroids"]
    vc = r["v_c"]
    c  = r["circularities"]

    axes[0].plot(t, yc)
    axes[0].set_xlabel("t (dimensionless)")
    axes[0].set_ylabel("y-centroid")
    axes[0].set_title("Bubble centroid height")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(t, vc)
    axes[1].axhline(U_T_REF, color="red", linestyle="--",
                    label=f"Hysing U_T={U_T_REF:.4f}")
    axes[1].axhline(r["U_T_num"], color="blue", linestyle=":",
                    label=f"Num U_T={r['U_T_num']:.4f}")
    axes[1].set_xlabel("t")
    axes[1].set_ylabel("Rise velocity v_c")
    axes[1].set_title("Rise velocity")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(t, c)
    axes[2].axhline(C_REF, color="red", linestyle="--",
                    label=f"Hysing c(3)={C_REF:.4f}")
    axes[2].set_xlabel("t")
    axes[2].set_ylabel("Circularity")
    axes[2].set_title("Bubble circularity")
    axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    path = "results/rising_bubble/rising_bubble.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"\n  Plot saved: {path}")

    return r


if __name__ == "__main__":
    main()
