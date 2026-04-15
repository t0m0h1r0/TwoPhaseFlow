#!/usr/bin/env python3
"""[11-2] DCCD filter transfer function and checkerboard suppression.

Validates: Ch4d -- DCCD dissipative filter design.

Tests:
  (a) Transfer function H(xi; eps_d) at eps_d = [0.00, 0.05, 0.10, 0.25, 0.50]
  (b) Checkerboard mode (-1)^{i+j} suppression with eps_d=0.25 on N=32,64,128

Expected: H(pi) = 0 for eps_d=0.25; complete Nyquist suppression.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def transfer_function_analysis():
    xi = np.linspace(0, np.pi, 500)
    eps_d_values = [0.00, 0.05, 0.10, 0.25, 0.50]
    results = {}
    print("\n  Transfer function at Nyquist (xi=pi):")
    print(f"  {'eps_d':>6} | H(pi)")
    print(f"  {'-'*6}-+-{'-'*8}")
    for eps_d in eps_d_values:
        H = 1.0 - 4.0 * eps_d * np.sin(xi / 2)**2
        results[str(eps_d)] = H
        print(f"  {eps_d:>6.2f} | {1.0 - 4.0 * eps_d:.4f}")
    return xi, results


def checkerboard_test():
    backend = Backend()
    xp = backend.xp
    results = []
    for N in [32, 64, 128]:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()
        checker = (-1.0) ** (xp.round(X * N).astype(int) + xp.round(Y * N).astype(int))

        d1_ccd, _ = ccd.differentiate(checker, axis=0)

        # DCCD filter eps_d=0.25 (full checkerboard kill)
        d1_f = d1_ccd.copy()
        d1_f[1:-1, :] = d1_ccd[1:-1, :] + 0.25 * (
            d1_ccd[2:, :] - 2 * d1_ccd[1:-1, :] + d1_ccd[:-2, :])
        d1_f[0, :] = d1_ccd[0, :] + 0.25 * (
            d1_ccd[1, :] - 2 * d1_ccd[0, :] + d1_ccd[-1, :])
        d1_f[-1, :] = d1_f[0, :]

        rms_before = float(xp.sqrt(xp.mean(d1_ccd**2)))
        rms_after = float(xp.sqrt(xp.mean(d1_f**2)))
        ratio = rms_after / rms_before if rms_before > 0 else 0
        results.append({"N": N, "rms_ccd": rms_before, "rms_dccd": rms_after,
                         "reduction": ratio})
        print(f"  N={N:>4}: CCD RMS={rms_before:.3e}, DCCD RMS={rms_after:.3e}, "
              f"ratio={ratio:.6f}")
    return results


def plot_all(xi, H_results, checker_results):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # (a) Transfer function
    ax = axes[0]
    for ci, (eps_d_str, H) in enumerate(H_results.items()):
        ax.plot(xi / np.pi, H, color=COLORS[ci % len(COLORS)],
                label=rf"$\varepsilon_d={eps_d_str}$")
    ax.set_xlabel(r"$\xi / \pi$"); ax.set_ylabel(r"$H(\xi; \varepsilon_d)$")
    ax.set_title("(a) DCCD transfer function")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3); ax.set_ylim(-0.1, 1.1)

    # (b) Checkerboard suppression
    ax = axes[1]
    Ns_cb = [r["N"] for r in checker_results]
    ratios = [r["reduction"] for r in checker_results]
    ax.bar([str(n) for n in Ns_cb], ratios, color=COLORS[0])
    ax.set_xlabel("$N$"); ax.set_ylabel("RMS ratio (DCCD/CCD)")
    ax.set_title(r"(b) Checkerboard kill ($\varepsilon_d=0.25$)")
    ax.set_ylim(0, max(0.1, max(ratios) * 1.5)); ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    save_figure(fig, OUT / "dccd_filter")


def main():
    args = experiment_argparser("[11-2] DCCD Filter").parse_args()

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        plot_all(data["xi"], data["H_results"], data["checker"])
        return

    print("\n--- (a) Transfer function ---")
    xi, H_results = transfer_function_analysis()

    print("\n--- (b) Checkerboard suppression ---")
    checker = checkerboard_test()

    save_results(OUT / "data.npz", {"xi": xi, "H_results": H_results, "checker": checker})
    plot_all(xi, H_results, checker)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
