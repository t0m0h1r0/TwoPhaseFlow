#!/usr/bin/env python3
"""[11-15] AB2 time integration accuracy (with Euler startup).

Validates: Ch6 -- Adams-Bashforth 2nd order with forward Euler at n=0.

Test:
  ODE dq/dt = -q, q(0)=1, exact q(T=1)=e^{-1}.
  n = 16, 32, 64, 128, 256, 512 steps.

Expected: O(dt^2); parasitic root |rho_2|=0.5 decays negligibly.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    FIGSIZE_1COL,
)

apply_style()
OUT = experiment_dir(__file__)


def ab2_ode_test():
    # Scalar ODE dq/dt = -q with Backend() for opt-in symmetry — the inner
    # loop is Python-float arithmetic (no arrays), so CPU and GPU backends
    # are bit-identical; Backend() presence just aligns this script with the
    # rest of ch11 for GPU opt-in tracking.
    backend = Backend()
    xp = backend.xp
    T = 1.0
    q_exact = float(xp.exp(xp.asarray(-T)))
    n_list = [16, 32, 64, 128, 256, 512]
    results = []

    for n in n_list:
        dt = T / n; q = 1.0; f_prev = None
        for step in range(n):
            f_n = -q
            if step == 0:
                q = q + dt * f_n
            else:
                q = q + dt * (1.5 * f_n - 0.5 * f_prev)
            f_prev = f_n

        err = abs(q - q_exact)
        results.append({"n": n, "dt": dt, "err": err})

    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        if r0["err"] > 1e-15 and r1["err"] > 1e-15:
            r1["slope"] = np.log(r1["err"]/r0["err"]) / np.log(r1["dt"]/r0["dt"])

    return results


def plot_all(results):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE_1COL)
    dt = [r["dt"] for r in results]
    ax.loglog(dt, [r["err"] for r in results], "o-", label="AB2 (Euler startup)", markersize=7)
    d_ref = np.array([dt[0], dt[-1]])
    for order, ls in [(1, ":"), (2, "--")]:
        ax.loglog(d_ref, results[0]["err"]*(d_ref/d_ref[0])**order,
                  ls, color="gray", alpha=0.5, label=f"$O(\\Delta t^{order})$")
    ax.set_xlabel(r"$\Delta t$"); ax.set_ylabel(r"$|q-e^{-1}|$")
    ax.set_title("AB2 ODE convergence: $dq/dt=-q$")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, OUT / "ab2_time")


def main():
    args = experiment_argparser("[11-15] AB2 Time").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["results"])
        return

    results = ab2_ode_test()
    for r in results:
        s = r.get("slope", float("nan"))
        print(f"  n={r['n']:>4}: err={r['err']:.3e}, slope={s:.2f}")

    save_results(OUT / "data.npz", {"results": results})
    plot_all(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
