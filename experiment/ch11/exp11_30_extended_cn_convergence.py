#!/usr/bin/env python3
"""[11-30] Extended CN temporal convergence.

Validates: Extended CN Phase 2 (docs/memo/extended_cn_impl_design.md §5.2).

Measures the temporal convergence order of the CN viscous advance
strategies on pure diffusion u_t = ν Δu with constant μ, ρ and zero
explicit_rhs:
  (a) PicardCNAdvance                  — baseline, expected O(Δt^2)
  (b) RichardsonCNAdvance(Picard)      — expected O(Δt^3), NOT O(Δt^4),
                                          because Picard (= Heun) is a
                                          non-symmetric RK base so
                                          Richardson extrapolation gains
                                          only +1 order, not +2.

Methodology: self-similarity refinement ratio. At fixed grid h, the
spatial discretization error is identical across every Δt run and cancels
in differences; the remaining signal

    d_i = max |u(Δt_i) − u(Δt_{i+1})|_∞

satisfies d_{i-1} / d_i ≈ 2^p for a method of temporal order p, so the
empirical order is p ≈ log2(d_{i-1}/d_i). This is the same approach used
in src/twophase/tests/test_ns_terms.py::test_richardson_cn_lifts_order_on_
pure_diffusion, generalized to multiple N.

Expected headline:
  Picard     order ≈ 2.0
  Richardson order ≈ 3.0  (not 4 — see §5.2 of the design memo)

Richardson(Implicit CN) and Richardson(Padé-(2,2)) from Phase 3/4/6 will
deliver the symmetric-base path to O(Δt^4) and O(Δt^6) respectively; they
will reuse this experiment harness by adding further strategy columns.
"""

import math
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig, FluidConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ns_terms.viscous import ViscousTerm
from twophase.ns_terms.cn_advance import PicardCNAdvance, RichardsonCNAdvance
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__)


# ── Physics: pure diffusion u_t = ν Δu on [0,1]² with wall BC ────────────
NU = 0.05       # kinematic viscosity (Re = 1/ν)
L  = 1.0
T_END = 0.02    # short horizon — stay well below viscous CFL


def _make_backend_grid_ccd(N: int):
    backend = Backend()
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend)     # default wall BC
    return backend, xp, grid, ccd


def _initial_field(xp, grid):
    X, Y = grid.meshgrid()
    X = xp.asarray(X); Y = xp.asarray(Y)
    # Lowest wall-compatible mode; zero at the domain boundary.
    u0 = xp.sin(np.pi * X) * xp.sin(np.pi * Y)
    v0 = xp.zeros_like(u0)
    return u0, v0


def _run(strategy, u_old, visc, ccd, dt, t_end, backend):
    xp = backend.xp
    u = [u_old[0].copy(), u_old[1].copy()]
    mu  = xp.ones_like(u_old[0])
    rho = xp.ones_like(u_old[0])
    rhs = [xp.zeros_like(u_old[0]), xp.zeros_like(u_old[0])]
    nsteps = int(round(t_end / dt))
    for _ in range(nsteps):
        u = strategy.advance(u, rhs, mu, rho, visc, ccd, dt)
    return u[0]


def self_similarity_order(N: int, dts):
    """Run both strategies at N and return self-similarity diffs + orders."""
    backend, xp, grid, ccd = _make_backend_grid_ccd(N)
    visc = ViscousTerm(backend, Re=1.0 / NU, cn_viscous=True)
    u0, v0 = _initial_field(xp, grid)

    picard = PicardCNAdvance(backend)
    richardson = RichardsonCNAdvance(picard)

    sols_p, sols_r = [], []
    for dt in dts:
        sols_p.append(_run(picard,     [u0, v0], visc, ccd, dt, T_END, backend))
        sols_r.append(_run(richardson, [u0, v0], visc, ccd, dt, T_END, backend))

    sl = (slice(2, -2), slice(2, -2))
    diffs_p = [float(xp.max(xp.abs(sols_p[i][sl] - sols_p[i+1][sl])))
               for i in range(len(dts) - 1)]
    diffs_r = [float(xp.max(xp.abs(sols_r[i][sl] - sols_r[i+1][sl])))
               for i in range(len(dts) - 1)]

    order_p = [math.log2(diffs_p[i] / diffs_p[i+1])
               for i in range(len(diffs_p) - 1) if diffs_p[i+1] > 1e-18]
    order_r = [math.log2(diffs_r[i] / diffs_r[i+1])
               for i in range(len(diffs_r) - 1) if diffs_r[i+1] > 1e-18]

    return {
        "N": N,
        "dts": list(dts),
        "diffs_picard": diffs_p,
        "diffs_richardson": diffs_r,
        "order_picard": order_p,
        "order_richardson": order_r,
    }


def plot(results):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

    # Diffs vs dt (dt_{i+1} on the x-axis — finer is to the left)
    ax = axes[0]
    for rec in results:
        dts = rec["dts"][1:]  # align with diffs length
        ax.loglog(dts, rec["diffs_picard"], "o-", label=f"Picard, N={rec['N']}")
        ax.loglog(dts, rec["diffs_richardson"], "s--", label=f"Richardson(Picard), N={rec['N']}")

    # Reference slopes
    rec = results[-1]
    dts = np.array(rec["dts"][1:])
    d0 = rec["diffs_picard"][0]
    for order, ls, label in [(2, ":", r"$\propto \Delta t^2$"),
                              (3, "-.", r"$\propto \Delta t^3$"),
                              (4, "--", r"$\propto \Delta t^4$")]:
        ax.loglog(dts, d0 * (dts / dts[0])**order, ls, color="gray", alpha=0.5, label=label)

    ax.set_xlabel(r"$\Delta t$")
    ax.set_ylabel(r"$\max_{\Omega}|u^{\Delta t_i}-u^{\Delta t_{i+1}}|$")
    ax.set_title("(a) Self-similarity differences")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which="both")

    # Order vs dt
    ax = axes[1]
    for rec in results:
        dts = rec["dts"][2:]  # align with order length
        ax.semilogx(dts, rec["order_picard"], "o-", label=f"Picard, N={rec['N']}")
        ax.semilogx(dts, rec["order_richardson"], "s--", label=f"Richardson(Picard), N={rec['N']}")
    ax.axhline(2.0, color="gray", ls=":", alpha=0.5)
    ax.axhline(3.0, color="gray", ls="-.", alpha=0.5)
    ax.axhline(4.0, color="gray", ls="--", alpha=0.5)
    ax.set_xlabel(r"$\Delta t$")
    ax.set_ylabel("Empirical order (self-similarity)")
    ax.set_title("(b) Measured temporal order")
    ax.set_ylim(0.5, 5.0)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "extended_cn_convergence")


def main():
    args = experiment_argparser("[11-30] Extended CN temporal convergence").parse_args()

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        plot(list(data["results"]))
        return

    dts = [T_END / n for n in (4, 8, 16, 32, 64)]
    results = []
    for N in (16, 32):
        print(f"\n--- N={N} ---")
        rec = self_similarity_order(N, dts)
        results.append(rec)
        print("  Picard     diffs:", [f"{d:.2e}" for d in rec["diffs_picard"]])
        print("  Picard     order:", [f"{o:.2f}" for o in rec["order_picard"]])
        print("  Richardson diffs:", [f"{d:.2e}" for d in rec["diffs_richardson"]])
        print("  Richardson order:", [f"{o:.2f}" for o in rec["order_richardson"]])

    save_results(OUT / "data.npz", {"results": results})
    plot(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
