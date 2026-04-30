#!/usr/bin/env python3
"""[V7] Two-phase time-order diagnostic on the §14 stack.

Paper ref: §13.4 (sec:imex_bdf2_twophase_time).

V7 now runs through ``TwoPhaseNSSolver`` with the same production-family
operators as §14:

  - FCCD interface transport + TVD-RK3,
  - UCCD6 momentum convection + IMEX-BDF2,
  - direct-ψ filtered curvature and ridge-eikonal reinitialization,
  - pressure-jump phase-separated FCCD PPE with defect correction.

The finest step count is used as the Richardson reference.  This is a
diagnostic of the coupled stack, not a pure BDF2 unit test.

Usage
-----
  make run EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py
  make plot EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np

from ch14_stack_common import ch14_circle_config, run_ch14_case, to_host
from twophase.tools.experiment import (
    apply_style,
    compute_convergence_rates,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIGURES = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"

R = 0.25
CENTER = (0.5, 0.5)
SIGMA = 1.0
RHO_L = 10.0
RHO_G = 1.0
MU_L = 1.0e-3
MU_G = 1.0e-4
N_GRID = 24
T_FINAL = 0.02
U_AMP = 0.02
N_STEPS_LIST = (8, 16, 32, 64)


def _wall_bc(arr: np.ndarray) -> None:
    arr[0, :] = 0.0
    arr[-1, :] = 0.0
    arr[:, 0] = 0.0
    arr[:, -1] = 0.0


def _perturbed_velocity(solver, psi) -> tuple[np.ndarray, np.ndarray]:
    X = to_host(solver, solver.X)
    Y = to_host(solver, solver.Y)
    psi_h = to_host(solver, psi)
    u = U_AMP * np.cos(2.0 * np.pi * Y) * psi_h
    v = -U_AMP * np.cos(2.0 * np.pi * X) * psi_h
    _wall_bc(u)
    _wall_bc(v)
    return u, v


def _case_config(n_steps: int):
    return ch14_circle_config(
        N=N_GRID,
        out_dir=OUT,
        radius=R,
        center=CENTER,
        rho_l=RHO_L,
        rho_g=RHO_G,
        mu_l=MU_L,
        mu_g=MU_G,
        sigma=SIGMA,
        max_steps=n_steps,
        final_time=T_FINAL,
        dt=T_FINAL / n_steps,
        reinit_every=1,
    )


def _run(n_steps: int) -> dict:
    out = run_ch14_case(
        cfg=_case_config(n_steps),
        label=f"V7 n={n_steps}",
        radius=R,
        center=CENTER,
        velocity_builder=_perturbed_velocity,
    )
    out.update({"n_steps": n_steps, "dt": T_FINAL / n_steps})
    return out


def run_all() -> dict:
    runs = []
    for n_steps in N_STEPS_LIST:
        print(f"[V7] n_steps={n_steps}, dt={T_FINAL / n_steps:.3e}")
        runs.append(_run(n_steps))
    u_ref = runs[-1]["u"]
    v_ref = runs[-1]["v"]
    rows = []
    for run in runs[:-1]:
        err = float(np.max(np.sqrt((run["u"] - u_ref) ** 2 + (run["v"] - v_ref) ** 2)))
        rows.append(
            {
                "n_steps": run["n_steps"],
                "dt": run["dt"],
                "Linf_err": err,
                "u_inf_final": run["u_inf_final"],
                "volume_drift_final": run["volume_drift_final"],
            }
        )
    return {
        "reference_n_steps": runs[-1]["n_steps"],
        "rows": rows,
        "runs": runs,
        "meta": {
            "N": N_GRID,
            "T_final": T_FINAL,
            "rho_ratio": RHO_L / RHO_G,
            "reinit_every": 1,
        },
    }


def make_figures(results: dict) -> None:
    rows = results["rows"]
    dts = np.array([r["dt"] for r in rows])
    errs = np.array([r["Linf_err"] for r in rows])
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    ax.loglog(dts, errs, "o-", color="C0", label="§14 coupled stack")
    if len(errs):
        ax.loglog(dts, errs[0] * (dts / dts[0]) ** 2, "k--", alpha=0.6, label="O(dt²)")
        ax.loglog(dts, errs[0] * (dts / dts[0]), "k:", alpha=0.5, label="O(dt)")
    ax.invert_xaxis()
    ax.set_xlabel("dt")
    ax.set_ylabel(r"$\|u-u_{\rm ref}\|_\infty$")
    ax.set_title(f"V7: §14 stack time-order diagnostic (N={N_GRID})")
    ax.legend()
    save_figure(
        fig,
        OUT / "V7_imex_bdf2_twophase_time",
        also_to=PAPER_FIGURES / "ch13_v7_imex_bdf2_time",
    )


def print_summary(results: dict) -> None:
    rows = results["rows"]
    dts = np.array([r["dt"] for r in rows])
    errs = np.array([r["Linf_err"] for r in rows])
    rates = compute_convergence_rates(errs, dts)
    print(f"V7 (§14 stack time diagnostic, N={N_GRID}, ref={results['reference_n_steps']}):")
    for row, rate in zip(rows, [None] + list(rates)):
        rate_s = "" if rate is None else f"  slope={rate:.2f}"
        print(
            f"  n={row['n_steps']:>3}  dt={row['dt']:.3e}  "
            f"Linf_err={row['Linf_err']:.3e}{rate_s}"
        )
    if len(rates):
        print(f"  → finest observed slope ≈ {rates[-1]:.2f}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V7 outputs in {OUT}")


if __name__ == "__main__":
    main()
