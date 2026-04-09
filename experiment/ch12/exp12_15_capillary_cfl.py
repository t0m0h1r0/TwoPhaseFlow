#!/usr/bin/env python3
"""[12-15] Capillary CFL scaling verification.

Validates: Ch7b -- capillary wave CFL dt_sigma proportional to dx^{3/2}.

Test: Small-amplitude capillary wave on flat interface.
  Measure maximum stable dt at various grid resolutions.

Expected: dt_max scales as dx^{3/2} (not dx or dx^2).
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
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

# -- Physical parameters -------------------------------------------------------
SIGMA = 0.07         # surface tension coefficient
RHO_L = 1000.0       # liquid density
RHO_G = 1.0          # gas density
RHO_SUM = RHO_L + RHO_G
AMPLITUDE = 1e-3     # small perturbation
N_LIST = [32, 64, 128, 256]
N_TEST_STEPS = 100   # steps per stability probe
BISECT_ITERS = 40    # binary search iterations


# -- Theoretical capillary CFL -------------------------------------------------

def dt_sigma_theory(h):
    """Theoretical capillary CFL: dt = sqrt((rho_l+rho_g) * h^3 / (2*pi*sigma))."""
    return np.sqrt(RHO_SUM * h**3 / (2.0 * np.pi * SIGMA))


# -- Capillary wave PDE model ---------------------------------------------------
#
#  Linearised capillary wave on a flat interface (1-D surface):
#    eta_tt = -(sigma / (rho_l + rho_g)) * eta_xxx
#
#  Written as a first-order system:
#    eta_t = v
#    v_t   = -coeff * eta_xxx
#
#  where coeff = sigma / (rho_l + rho_g).
#
#  We discretise the spatial 3rd derivative with CCD (differentiate d2
#  then differentiate once more) and march with explicit RK4.
# -------------------------------------------------------------------------

def run_capillary_test(N, dt, n_steps):
    """Run capillary wave PDE for n_steps with RK4, return True if stable."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    coeff = SIGMA / RHO_SUM

    # Initial condition: eta(x,0) = A*sin(2*pi*x), uniform in y
    X, _ = grid.meshgrid()
    x1d = np.asarray(X[:, 0])
    eta_1d = AMPLITUDE * np.sin(2.0 * np.pi * x1d)

    # Embed into 2-D array (uniform in y) for CCD compatibility
    Ny = N + 1
    eta = np.tile(eta_1d[:, None], (1, Ny))
    vel = np.zeros_like(eta)

    def compute_eta_xxx(e):
        """3rd spatial derivative via CCD: d/dx(d2/dx2)."""
        _, d2 = ccd.differentiate(e, axis=0)
        d3, _ = ccd.differentiate(np.asarray(d2), axis=0)
        return np.asarray(d3)

    def rhs(e, v):
        """Return (d_eta/dt, d_v/dt)."""
        return v, -coeff * compute_eta_xxx(e)

    for _ in range(n_steps):
        # RK4
        de1, dv1 = rhs(eta, vel)
        de2, dv2 = rhs(eta + 0.5 * dt * de1, vel + 0.5 * dt * dv1)
        de3, dv3 = rhs(eta + 0.5 * dt * de2, vel + 0.5 * dt * dv2)
        de4, dv4 = rhs(eta + dt * de3, vel + dt * dv3)

        eta = eta + (dt / 6.0) * (de1 + 2.0 * de2 + 2.0 * de3 + de4)
        vel = vel + (dt / 6.0) * (dv1 + 2.0 * dv2 + 2.0 * dv3 + dv4)

        if np.any(np.isnan(eta)) or np.max(np.abs(eta)) > 100.0 * AMPLITUDE:
            return False

    return True


def find_max_stable_dt(N):
    """Binary search for maximum stable dt of capillary wave PDE."""
    h = 1.0 / N
    dt_low = 0.0
    dt_high = 10.0 * h   # generous upper bound

    for _ in range(BISECT_ITERS):
        dt_mid = 0.5 * (dt_low + dt_high)
        if run_capillary_test(N, dt_mid, N_TEST_STEPS):
            dt_low = dt_mid
        else:
            dt_high = dt_mid

    return dt_low


# -- Test A: Analytical CFL scaling --------------------------------------------

def analytical_scaling():
    """Compute theoretical dt_sigma for a range of h values."""
    h_arr = np.logspace(-1, -3, 50)
    dt_arr = dt_sigma_theory(h_arr)
    return h_arr, dt_arr


# -- Test B: Numerical stability search -----------------------------------------

def numerical_stability():
    """Find maximum stable dt for each grid resolution."""
    results = []
    for N in N_LIST:
        h = 1.0 / N
        dt_theory = float(dt_sigma_theory(h))
        print(f"  N={N:>4}, h={h:.4e}: searching for dt_max ...")
        dt_max = find_max_stable_dt(N)
        ratio = dt_max / dt_theory if dt_theory > 0 else float("nan")
        results.append({
            "N": N, "h": h,
            "dt_max": dt_max, "dt_theory": dt_theory,
            "ratio": ratio,
        })
        print(f"    dt_max={dt_max:.4e}, dt_theory={dt_theory:.4e}, "
              f"ratio={ratio:.3f}")
    return results


# -- Plotting -------------------------------------------------------------------

def plot_all(results):
    """2-panel figure: (a) dt_max vs h, (b) ratio vs N."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    h_arr = np.array([r["h"] for r in results])
    dt_max = np.array([r["dt_max"] for r in results])
    dt_thy = np.array([r["dt_theory"] for r in results])
    N_arr = np.array([r["N"] for r in results])
    ratio = np.array([r["ratio"] for r in results])

    # (a) Log-log: dt_max vs h
    ax = axes[0]
    ax.loglog(h_arr, dt_max, "o-", color=COLORS[0], markersize=7,
              label=r"Measured $\Delta t_{\max}$")
    ax.loglog(h_arr, dt_thy, "s--", color=COLORS[1], markersize=6,
              label=r"Theory $\sqrt{(\rho_l+\rho_g)\,h^3/(2\pi\sigma)}$")

    # Reference slopes
    h_ref = np.array([h_arr[0], h_arr[-1]])
    for exp, ls, lbl in [(1.0, ":", r"$O(h)$"),
                          (1.5, "-.", r"$O(h^{3/2})$"),
                          (2.0, "--", r"$O(h^2)$")]:
        scale = dt_max[0] * (h_ref / h_ref[0])**exp
        ax.loglog(h_ref, scale, ls=ls, color="gray", alpha=0.4, label=lbl)

    ax.set_xlabel("$h = 1/N$")
    ax.set_ylabel(r"$\Delta t$")
    ax.set_title(r"(a) Capillary CFL: $\Delta t_\sigma$ vs $h$")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which="both")

    # Compute measured slope
    if len(h_arr) >= 2:
        slope_meas = np.polyfit(np.log(h_arr), np.log(dt_max), 1)[0]
        slope_thy = np.polyfit(np.log(h_arr), np.log(dt_thy), 1)[0]
        ax.text(0.05, 0.05,
                f"measured slope: {slope_meas:.2f}\ntheory slope: {slope_thy:.2f}",
                transform=ax.transAxes, fontsize=7, va="bottom",
                bbox=dict(boxstyle="round", fc="white", alpha=0.8))

    # (b) Ratio dt_max / dt_theory vs N
    ax = axes[1]
    ax.plot(N_arr, ratio, "o-", color=COLORS[0], markersize=7)
    ax.axhline(np.mean(ratio), color="gray", ls="--", alpha=0.5,
               label=f"mean = {np.mean(ratio):.2f}")
    ax.set_xlabel("$N$")
    ax.set_ylabel(r"$\Delta t_{\max} / \Delta t_{\sigma,\mathrm{theory}}$")
    ax.set_title(r"(b) Ratio (should $\to$ constant)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_xscale("log", base=2)
    ax.set_xticks(N_arr)
    ax.set_xticklabels([str(n) for n in N_arr])

    fig.tight_layout()
    save_figure(fig, OUT / "capillary_cfl")


# -- Main -----------------------------------------------------------------------

def main():
    args = experiment_argparser(
        "[12-15] Capillary CFL scaling"
    ).parse_args()

    if args.plot_only:
        d = load_results(NPZ)
        plot_all(d["results"])
        return

    print("\n=== [12-15] Capillary CFL scaling verification ===")

    print("\n--- (A) Analytical scaling ---")
    h_ana, dt_ana = analytical_scaling()
    slope = np.polyfit(np.log(h_ana), np.log(dt_ana), 1)[0]
    print(f"  Theoretical slope of log(dt_sigma) vs log(h): {slope:.4f} "
          f"(expect 1.5)")

    print("\n--- (B) Numerical stability search ---")
    results = numerical_stability()

    # Print table
    print(f"\n{'N':>6} {'h':>10} {'dt_max':>12} {'dt_theory':>12} {'ratio':>8}")
    print("-" * 52)
    for r in results:
        print(f"{r['N']:>6} {r['h']:>10.4e} {r['dt_max']:>12.4e} "
              f"{r['dt_theory']:>12.4e} {r['ratio']:>8.3f}")

    # Convergence slope
    h_arr = np.array([r["h"] for r in results])
    dt_arr = np.array([r["dt_max"] for r in results])
    if len(h_arr) >= 2:
        slope_meas = np.polyfit(np.log(h_arr), np.log(dt_arr), 1)[0]
        print(f"\n  Measured scaling exponent: {slope_meas:.3f} (expect 1.5)")

    save_results(NPZ, {"results": results})
    plot_all(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
