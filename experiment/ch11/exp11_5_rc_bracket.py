#!/usr/bin/env python3
"""[11-5] Rhie-Chow correction bracket convergence: standard vs C/RC.

Validates: Ch8 -- C/RC bracket improves convergence from O(h^2) to O(h^4).

Test:
  p = cos(2*pi*x)*cos(2*pi*y), periodic BC, N=[16,32,64,128].
  Standard RC bracket: (dp/dx)_{i+1/2} ≈ (p_{i+1} - p_i)/h
  C/RC bracket: uses CCD p' and p'' for higher-order face interpolation.

Expected: Standard O(h^2); C/RC O(h^4).
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_1COL,
)

apply_style()
OUT = experiment_dir(__file__)


def rc_bracket_test(Ns):
    """Compare standard and C/RC bracket accuracy."""
    backend = Backend(use_gpu=False)
    xp = backend.xp
    k = 2 * np.pi
    res_std, res_crc = [], []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        h = 1.0 / N

        X, Y = grid.meshgrid()
        p = np.cos(k * X) * np.cos(k * Y)

        # CCD derivatives
        dp_dx, d2p_dx2 = ccd.differentiate(xp.asarray(p), axis=0)
        dp_dx = np.asarray(backend.to_host(dp_dx))
        d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))

        # Exact face gradient at x_{i+1/2}
        x_face = X[:-1, :] + h / 2
        dp_dx_exact = -k * np.sin(k * x_face) * np.cos(k * Y[:-1, :])

        # Standard RC bracket: (p_{i+1} - p_i) / h
        dp_std = (p[1:, :] - p[:-1, :]) / h

        # C/RC bracket: use CCD p' and p'' for Hermite interpolation to face
        # dp/dx|_{i+1/2} = (p_{i+1} - p_i)/h - h/24 * (p''_{i+1} - p''_i)
        # This is the Richardson-corrected form
        dp_crc = (p[1:, :] - p[:-1, :]) / h - h / 24.0 * (d2p_dx2[1:, :] - d2p_dx2[:-1, :])

        err_std = float(np.max(np.abs(dp_std - dp_dx_exact)))
        err_crc = float(np.max(np.abs(dp_crc - dp_dx_exact)))

        res_std.append({"N": N, "h": h, "Li": err_std})
        res_crc.append({"N": N, "h": h, "Li": err_crc})

        ratio = err_std / err_crc if err_crc > 0 else float("inf")
        print(f"  N={N:>4}: Std={err_std:.3e}, C/RC={err_crc:.3e}, ratio={ratio:.1f}x")

    for res in [res_std, res_crc]:
        for i in range(1, len(res)):
            r0, r1 = res[i-1], res[i]
            if r0["Li"] > 0 and r1["Li"] > 0:
                r1["Li_slope"] = np.log(r1["Li"] / r0["Li"]) / np.log(r1["h"] / r0["h"])

    return res_std, res_crc


def plot_all(res_std, res_crc):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE_1COL)

    hs = [r["h"] for r in res_std]
    ax.loglog(hs, [r["Li"] for r in res_std], "s--", label=r"Standard RC ($O(h^2)$)", markersize=7)
    ax.loglog(hs, [r["Li"] for r in res_crc], "o-", label=r"C/RC ($O(h^4)$)", markersize=7)

    h_ref = np.array([hs[0], hs[-1]])
    for order, ls in [(2, ":"), (4, "-.")]:
        ax.loglog(h_ref, res_std[0]["Li"]*(h_ref/h_ref[0])**order,
                  ls, color="gray", alpha=0.5, label=f"$O(h^{order})$")

    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title("Rhie--Chow bracket: standard vs corrected")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, OUT / "rc_bracket")


def main():
    args = experiment_argparser("[11-5] RC Bracket").parse_args()
    Ns = [16, 32, 64, 128]

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["standard"], d["corrected"])
        return

    print("\n--- RC bracket convergence ---")
    res_std, res_crc = rc_bracket_test(Ns)

    save_results(OUT / "data.npz", {"standard": res_std, "corrected": res_crc})
    plot_all(res_std, res_crc)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
