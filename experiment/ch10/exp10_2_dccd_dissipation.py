#!/usr/bin/env python3
"""【10-2】DCCD numerical dissipation characteristics.

Evaluates high-wavenumber damping of the dissipative CCD filter via:
(a) Transfer function H(ξ; ε_d) analysis (analytical + numerical)
(b) Checkerboard mode attenuation test on actual grids
(c) Comparison: CCD vs DCCD on advection of sharp profile

Paper ref: §4d, §5 eq:eps_adv
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver

OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "results" / "ch10_dccd_dissipation"
OUT.mkdir(parents=True, exist_ok=True)


def transfer_function_analysis():
    """Compute and plot the DCCD transfer function H(ξ; ε_d)."""
    xi = np.linspace(0, np.pi, 500)
    eps_d_values = [0.0, 0.05, 0.10, 0.25, 0.50]

    results = {}
    for eps_d in eps_d_values:
        # H(ξ; ε_d) = 1 - 4 ε_d sin²(ξ/2)
        H = 1.0 - 4.0 * eps_d * np.sin(xi / 2)**2
        results[eps_d] = H

    # Key values at Nyquist (ξ=π)
    print("\n  Transfer function at Nyquist (ξ=π):")
    print(f"  {'ε_d':>6} | H(π)")
    print(f"  {'-'*6}-+-{'-'*8}")
    for eps_d in eps_d_values:
        H_pi = 1.0 - 4.0 * eps_d
        print(f"  {eps_d:>6.2f} | {H_pi:.4f}")

    return xi, results


def numerical_damping_test(N=128):
    """Measure actual damping of wavenumber modes by CCD + filter."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    h = 1.0 / N
    x = np.linspace(0, 1, N + 1)
    wavenumbers = [2, 4, 8, 16, 32, N // 2, N]  # in units of 2π/L

    eps_d_values = [0.0, 0.05, 0.25]
    results = {}

    for eps_d in eps_d_values:
        damping = []
        for k in wavenumbers:
            xi = 2 * np.pi * k  # physical wavenumber
            xi_norm = xi * h    # normalized wavenumber ξ = k·h

            # Create 2D sinusoidal field
            X, Y = grid.meshgrid()
            f = np.sin(xi * X) * np.ones_like(Y)

            # CCD differentiate
            d1, d2 = ccd.differentiate(f, axis=0)

            # Apply DCCD filter to d1 along axis 0
            if eps_d > 0:
                d1_filtered = d1.copy()
                d1_filtered[1:-1, :] = d1[1:-1, :] + eps_d * (
                    d1[2:, :] - 2 * d1[1:-1, :] + d1[:-2, :])
                # Periodic wrap
                d1_filtered[0, :] = d1[0, :] + eps_d * (
                    d1[1, :] - 2 * d1[0, :] + d1[-1, :])
                d1_filtered[-1, :] = d1_filtered[0, :]
            else:
                d1_filtered = d1

            # Exact d1 = k cos(kx)
            d1_exact = xi * np.cos(xi * X) * np.ones_like(Y)

            # Measure amplitude ratio (effective transfer function)
            # Compare RMS of filtered vs exact
            rms_filtered = np.sqrt(np.mean(d1_filtered[:, N//2]**2))
            rms_exact = np.sqrt(np.mean(d1_exact[:, N//2]**2))
            ratio = rms_filtered / rms_exact if rms_exact > 1e-15 else 0.0

            damping.append({
                "k": k, "xi_norm": xi_norm,
                "ratio": ratio,
                "H_theory": 1.0 - 4.0 * eps_d * np.sin(xi_norm / 2)**2
            })
        results[eps_d] = damping

    return results


def checkerboard_test():
    """Test checkerboard (2Δx) mode suppression on collocated grid."""
    backend = Backend(use_gpu=False)
    results = []

    for N in [32, 64, 128]:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")

        X, Y = grid.meshgrid()
        # Pure checkerboard: (-1)^(i+j)
        checker = (-1.0) ** (np.round(X * N).astype(int) + np.round(Y * N).astype(int))

        # CCD derivative of checkerboard
        d1_ccd, _ = ccd.differentiate(checker, axis=0)

        # DCCD filter with ε_d=0.25 (PPE mode: full checkerboard kill)
        d1_filtered = d1_ccd.copy()
        d1_filtered[1:-1, :] = d1_ccd[1:-1, :] + 0.25 * (
            d1_ccd[2:, :] - 2 * d1_ccd[1:-1, :] + d1_ccd[:-2, :])
        d1_filtered[0, :] = d1_ccd[0, :] + 0.25 * (
            d1_ccd[1, :] - 2 * d1_ccd[0, :] + d1_ccd[-1, :])
        d1_filtered[-1, :] = d1_filtered[0, :]

        rms_before = float(np.sqrt(np.mean(d1_ccd**2)))
        rms_after = float(np.sqrt(np.mean(d1_filtered**2)))
        reduction = rms_after / rms_before if rms_before > 0 else 0

        results.append({"N": N, "rms_ccd": rms_before, "rms_dccd": rms_after,
                         "reduction": reduction})
        print(f"  N={N:>4}: CCD RMS={rms_before:.3e}, DCCD RMS={rms_after:.3e}, "
              f"ratio={reduction:.4f}")

    return results


def advection_comparison():
    """Compare CCD vs DCCD advection of a step function (1D-like)."""
    from twophase.levelset.advection import LevelSetAdvection, DissipativeCCDAdvection

    backend = Backend(use_gpu=False)
    N = 256
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    X, Y = grid.meshgrid()
    eps = 1.5 / N

    # Initial: smooth step (tanh profile along x)
    psi0 = 0.5 * (1.0 + np.tanh((X - 0.3) / (2 * eps)))
    psi0 = np.clip(psi0, 0, 1)

    # Uniform velocity u=(1,0)
    u = np.ones_like(X)
    v = np.zeros_like(Y)
    vel = [u, v]

    dt = 0.4 / N  # CFL ~ 0.4
    n_steps = N  # advect one domain length

    # WENO5 advection
    adv_weno = LevelSetAdvection(backend, grid, bc="periodic")
    psi_weno = psi0.copy()
    for _ in range(n_steps):
        psi_weno = adv_weno.advance(psi_weno, vel, dt)

    # DCCD advection (eps_d=0.05)
    adv_dccd = DissipativeCCDAdvection(backend, grid, ccd, bc="periodic", eps_d=0.05)
    psi_dccd = psi0.copy()
    for _ in range(n_steps):
        psi_dccd = adv_dccd.advance(psi_dccd, vel, dt)

    # Exact: shifted by u*T = 1.0 (periodic → same as initial)
    psi_exact = psi0.copy()

    err_weno = float(np.sqrt(np.mean((psi_weno - psi_exact)**2)))
    err_dccd = float(np.sqrt(np.mean((psi_dccd - psi_exact)**2)))

    # TV (total variation)
    tv_exact = float(np.sum(np.abs(np.diff(psi_exact[:, N//2]))))
    tv_weno = float(np.sum(np.abs(np.diff(psi_weno[:, N//2]))))
    tv_dccd = float(np.sum(np.abs(np.diff(psi_dccd[:, N//2]))))

    print(f"\n  Advection comparison (N={N}, CFL=0.4, T=1.0):")
    print(f"  {'Scheme':>10} | {'L2 error':>10} | {'TV/TV_exact':>12}")
    print(f"  {'-'*10}-+-{'-'*10}-+-{'-'*12}")
    print(f"  {'WENO5':>10} | {err_weno:>10.3e} | {tv_weno/tv_exact:>12.4f}")
    print(f"  {'DCCD':>10} | {err_dccd:>10.3e} | {tv_dccd/tv_exact:>12.4f}")

    return {
        "psi0": psi0[:, N//2], "psi_weno": psi_weno[:, N//2],
        "psi_dccd": psi_dccd[:, N//2], "x": X[:, 0],
        "err_weno": err_weno, "err_dccd": err_dccd,
        "tv_weno": tv_weno / tv_exact, "tv_dccd": tv_dccd / tv_exact,
    }


def plot_all(xi, H_results, checker_results, adv_results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # (a) Transfer function
    ax = axes[0]
    for eps_d, H in H_results.items():
        ax.plot(xi / np.pi, H, label=f"$\\varepsilon_d={eps_d}$")
    ax.set_xlabel(r"$\xi / \pi$")
    ax.set_ylabel(r"$H(\xi; \varepsilon_d)$")
    ax.set_title("(a) Transfer function")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-0.1, 1.1)

    # (b) Checkerboard suppression
    ax = axes[1]
    Ns_cb = [r["N"] for r in checker_results]
    ratios = [r["reduction"] for r in checker_results]
    ax.bar([str(n) for n in Ns_cb], ratios)
    ax.set_xlabel("$N$")
    ax.set_ylabel("RMS ratio (DCCD/CCD)")
    ax.set_title(r"(b) Checkerboard kill ($\varepsilon_d=0.25$)")
    ax.set_ylim(0, 0.5)
    ax.grid(True, alpha=0.3, axis="y")

    # (c) Advection profiles
    ax = axes[2]
    ax.plot(adv_results["x"], adv_results["psi0"], "k--", label="Exact", lw=1)
    ax.plot(adv_results["x"], adv_results["psi_weno"], "b-", label="WENO5", lw=0.8)
    ax.plot(adv_results["x"], adv_results["psi_dccd"], "r-", label="DCCD", lw=0.8)
    ax.set_xlabel("$x$")
    ax.set_ylabel(r"$\psi$")
    ax.set_title("(c) Advection of tanh profile")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT / "dccd_dissipation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'dccd_dissipation.png'}")


def main():
    print("\n" + "="*80)
    print("  【10-2】DCCD Dissipation Characteristics")
    print("="*80)

    # (a) Transfer function
    print("\n--- (a) Transfer function H(ξ; ε_d) ---")
    xi, H_results = transfer_function_analysis()

    # (b) Numerical damping
    print("\n--- (b) Numerical wavenumber damping (N=128) ---")
    num_results = numerical_damping_test(N=128)

    # (c) Checkerboard suppression
    print("\n--- (c) Checkerboard mode suppression ---")
    checker_results = checkerboard_test()

    # (d) Advection comparison
    print("\n--- (d) CCD vs DCCD advection ---")
    adv_results = advection_comparison()

    # Plot
    plot_all(xi, H_results, checker_results, adv_results)

    # Save LaTeX table
    with open(OUT / "table_transfer.tex", "w") as fp:
        fp.write("% DCCD transfer function at Nyquist\n")
        fp.write("\\begin{tabular}{rr}\n\\toprule\n")
        fp.write("$\\varepsilon_d$ & $H(\\pi)$ \\\\\n\\midrule\n")
        for eps_d, H in H_results.items():
            fp.write(f"{eps_d:.2f} & {H[-1]:.4f} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")

    np.savez(OUT / "dissipation_data.npz",
             xi=xi, checker=checker_results, advection=adv_results)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    main()
