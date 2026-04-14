#!/usr/bin/env python3
"""[11-31] CLS reinitialization interface position shift measurement.

Validates: Ch7b -- reinit-induced zero-level shift scales as O(h^3*dtau).

Tests:
  (a) Measure zero-level position shift after 1 reinit call at N=32,64,128,256
      using a heaviside(SDF) initial condition (O(h) from tanh equilibrium).
  (b) Verify spatial convergence rate of the zero-level shift vs h.
  (c) Measure accumulated shift over 10 reinit calls (should scale ~10x single).

Expected per §7b: |delta_x0| = O(h^3*dtau) per reinit step when ψ is already
near the tanh equilibrium.  Starting from heaviside(SDF), the leading O(h^2)
transient dominates; convergence rate is measured and compared to both O(h^2)
and O(h^3) reference lines.

Grid convention: Grid returns (N+1)×(N+1) node-based arrays; zero-level search
is performed along the column j=N//2 (fixed y≈0.5, x varies with row index).
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.heaviside import heaviside
from twophase.levelset.reinit_ops import compute_dtau
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)

# ── Parameters ────────────────────────────────────────────────────────────────
_R = 0.25           # circle radius
_CX, _CY = 0.5, 0.5  # circle centre
_EPS_COEFF = 1.5    # ε = 1.5 * h
_N_STEPS = 5        # pseudo-time steps per reinit call
_N_CALLS_ACCUM = 10  # number of reinit calls for accumulation test


# ── Interface position measurement ───────────────────────────────────────────

def zero_crossing_col(psi, X, N):
    """Find the first ψ=0.5 crossing along column j=N//2 (fixed y, x varies).

    Grid layout: X has shape (N+1, N+1) with X[:, j] = x-coordinates and
    Y[i, :] = y-coordinates.  Column j=N//2 sits near y=0.5.

    Uses linear interpolation; handles the case where a node lands exactly
    on ψ=0.5 (returns the node x directly).

    Returns
    -------
    float
        x-coordinate of the ψ=0.5 crossing, or NaN if not found.
    """
    j = N // 2
    col = np.array(psi[:, j])
    xcol = np.array(X[:, j])
    for i in range(len(col) - 1):
        a = float(col[i])
        b = float(col[i + 1])
        if a == 0.5:
            return float(xcol[i])
        if (a - 0.5) * (b - 0.5) < 0:
            t = (0.5 - a) / (b - a)
            return float(xcol[i]) + t * (float(xcol[i + 1]) - float(xcol[i]))
    return float("nan")


def centroid_2d(psi, X, Y, xp):
    """Volume-weighted centroid: (∫ψ x dV / ∫ψ dV, ∫ψ y dV / ∫ψ dV)."""
    total = float(xp.sum(psi))
    if total < 1e-15:
        return 0.0, 0.0
    xc = float(xp.sum(psi * X)) / total
    yc = float(xp.sum(psi * Y)) / total
    return xc, yc


# ── Single-N measurement ──────────────────────────────────────────────────────

def measure_shift(N, n_reinit_calls, backend):
    """Measure zero-level and centroid shift after n_reinit_calls.

    Initial condition: heaviside(signed-distance-function) — O(h) from the
    tanh equilibrium of the operator-split reinit scheme.

    Returns
    -------
    dict with keys: N, h, dtau, zero_shift_1, zero_shift_n, centroid_shift_1,
    centroid_shift_n, z0_before.
    """
    xp = backend.xp
    h = 1.0 / N
    eps = _EPS_COEFF * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    # No mass correction: measure raw geometric shift
    reinit = Reinitializer(
        backend, grid, ccd, eps,
        n_steps=_N_STEPS,
        bc="zero",
        unified_dccd=False,
        mass_correction=False,
        method="split",
    )
    dtau = float(compute_dtau(grid, eps))

    X, Y = grid.meshgrid()
    # heaviside(SDF): O(h) perturbation away from tanh equilibrium
    phi = xp.sqrt((X - _CX) ** 2 + (Y - _CY) ** 2) - _R
    psi0 = heaviside(xp, phi, eps)

    z0 = zero_crossing_col(psi0, X, N)
    xc0, yc0 = centroid_2d(psi0, X, Y, xp)

    # 1-call measurement
    psi1 = reinit.reinitialize(xp.copy(psi0))
    z1 = zero_crossing_col(psi1, X, N)
    xc1, yc1 = centroid_2d(psi1, X, Y, xp)
    zero_shift_1 = abs(z1 - z0) if not (np.isnan(z0) or np.isnan(z1)) else float("nan")
    centroid_shift_1 = float(np.sqrt((xc1 - xc0) ** 2 + (yc1 - yc0) ** 2))

    # n_reinit_calls measurement
    psi_n = xp.copy(psi0)
    for _ in range(n_reinit_calls):
        psi_n = reinit.reinitialize(psi_n)
    zn = zero_crossing_col(psi_n, X, N)
    xcn, ycn = centroid_2d(psi_n, X, Y, xp)
    zero_shift_n = abs(zn - z0) if not (np.isnan(z0) or np.isnan(zn)) else float("nan")
    centroid_shift_n = float(np.sqrt((xcn - xc0) ** 2 + (ycn - yc0) ** 2))

    return {
        "N": N,
        "h": h,
        "dtau": dtau,
        "z0_before": z0,
        "zero_shift_1": zero_shift_1,
        "zero_shift_n": zero_shift_n,
        "centroid_shift_1": centroid_shift_1,
        "centroid_shift_n": centroid_shift_n,
    }


# ── Convergence study ─────────────────────────────────────────────────────────

def run_convergence(Ns=(32, 64, 128, 256)):
    """Measure shift at multiple resolutions and print convergence summary."""
    backend = Backend()
    results = []
    print(
        f"\n=== [11-31] Reinit interface shift: N={list(Ns)}, "
        f"{_N_CALLS_ACCUM}-call accumulation ==="
    )
    print(f"  IC: heaviside(SDF), R={_R}, centre=({_CX},{_CY}), ε=1.5h, n_steps={_N_STEPS}")

    for N in Ns:
        r = measure_shift(N, n_reinit_calls=_N_CALLS_ACCUM, backend=backend)
        results.append(r)
        ratio = (r["zero_shift_n"] / r["zero_shift_1"]
                 if r["zero_shift_1"] > 1e-20 else float("nan"))
        print(
            f"  N={N:>4}: h={r['h']:.4f}  dtau={r['dtau']:.3e}"
            f"  z0={r['z0_before']:.4f}"
            f"  |Δx_0|(1)={r['zero_shift_1']:.3e}"
            f"  |Δx_0|({_N_CALLS_ACCUM})={r['zero_shift_n']:.3e}"
            f"  ratio={ratio:.1f}"
        )

    # Convergence rates (zero_shift_1)
    hs = [r["h"] for r in results]
    zs1 = [r["zero_shift_1"] for r in results]
    valid = [
        (i, zs1[i], zs1[i - 1])
        for i in range(1, len(zs1))
        if not (np.isnan(zs1[i]) or np.isnan(zs1[i - 1]))
        and zs1[i] > 1e-15 and zs1[i - 1] > 1e-15
    ]
    rates = [
        np.log(v[1] / v[2]) / np.log(hs[v[0]] / hs[v[0] - 1])
        for v in valid
    ]
    mean_rate = float(np.mean(rates)) if rates else float("nan")
    print(f"\n  Zero-level shift convergence rates (1-call): {[f'{r:.2f}' for r in rates]}")
    print(f"  Mean rate = {mean_rate:.2f}  (§7b predicts ~3 when near equilibrium)")

    # Accumulation linearity at finest resolved N
    for r in reversed(results):
        if not np.isnan(r["zero_shift_1"]) and r["zero_shift_1"] > 1e-15:
            ratio = r["zero_shift_n"] / r["zero_shift_1"]
            print(f"  Accumulation ratio at N={r['N']}: {ratio:.2f}  (ideal ~{_N_CALLS_ACCUM})")
            break

    return results


# ── Plotting ──────────────────────────────────────────────────────────────────

def plot_all(results):
    """Log-log plot of h vs zero-level shift for 1-call and N-call reinit."""
    import matplotlib.pyplot as plt

    hs = [r["h"] for r in results]
    zs1 = [r["zero_shift_1"] for r in results]
    zsn = [r["zero_shift_n"] for r in results]
    cs1 = [r["centroid_shift_1"] for r in results]
    csn = [r["centroid_shift_n"] for r in results]

    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE_2COL)

    h_arr = np.asarray(hs, dtype=float)

    # Data series
    ax.loglog(h_arr, zs1, marker=MARKERS[0], color=COLORS[0],
              label=r"Zero-level $|\Delta x_0|$, 1 reinit call")
    ax.loglog(h_arr, zsn, marker=MARKERS[1], color=COLORS[1],
              ls="--", label=rf"Zero-level $|\Delta x_0|$, {_N_CALLS_ACCUM} reinit calls")
    ax.loglog(h_arr, cs1, marker=MARKERS[2], color=COLORS[2],
              label=r"Centroid $|\Delta x_c|$, 1 reinit call")
    ax.loglog(h_arr, csn, marker=MARKERS[3], color=COLORS[3],
              ls="--", label=rf"Centroid $|\Delta x_c|$, {_N_CALLS_ACCUM} reinit calls")

    # Reference slopes O(h), O(h^2), O(h^3) — anchored at first data point
    h_ref = np.array([h_arr[0], h_arr[-1]])
    e0 = float(zs1[0])
    ref_specs = [
        (1, ":", 0.45, "$O(h^1)$"),
        (2, "-.", 0.50, "$O(h^2)$"),
        (3, "--", 0.60, "$O(h^3)$"),
    ]
    for order, ls, alpha, label in ref_specs:
        e_ref = e0 * (h_ref / h_ref[0]) ** order
        ax.loglog(h_ref, e_ref, color="gray", ls=ls, alpha=alpha, label=label)

    ax.set_xlabel("$h$")
    ax.set_ylabel(r"Interface shift $|\Delta x|$")
    ax.set_title(
        r"[11-31] Reinit-induced interface shift (heaviside IC, §7b)",
        fontsize=10,
    )
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "reinit_interface_shift")


# ── Main ──────────────────────────────────────────────────────────────────────

def _pack_arrays(results, keys):
    """Convert list-of-dicts → dict of 1-D numpy arrays (for npz storage)."""
    return {k: np.array([float(r[k]) for r in results]) for k in keys}


_KEYS = ("N", "h", "dtau", "z0_before",
         "zero_shift_1", "zero_shift_n",
         "centroid_shift_1", "centroid_shift_n")

_NS = (32, 64, 128, 256)


def main():
    args = experiment_argparser("[11-31] Reinit Interface Shift").parse_args()

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        # save_results flattens {"results": {k: arr}} → d["results"][k]
        packed = d["results"]  # dict of 1-D arrays keyed by _KEYS
        results = [
            {k: float(packed[k][i]) for k in _KEYS}
            for i in range(len(_NS))
        ]
        plot_all(results)
        return

    results = run_convergence(Ns=_NS)

    save_results(OUT / "data.npz", {"results": _pack_arrays(results, _KEYS)})

    plot_all(results)

    # PASS/FAIL summary
    hs = [r["h"] for r in results]
    zs1 = [r["zero_shift_1"] for r in results]
    valid = [
        (i, zs1[i], zs1[i - 1])
        for i in range(1, len(zs1))
        if not (np.isnan(zs1[i]) or np.isnan(zs1[i - 1]))
        and zs1[i] > 1e-15 and zs1[i - 1] > 1e-15
    ]
    rates = [np.log(v[1] / v[2]) / np.log(hs[v[0]] / hs[v[0] - 1]) for v in valid]
    mean_rate = float(np.mean(rates)) if rates else float("nan")
    passed = mean_rate >= 1.5
    print(f"\n[RESULT] Mean zero-level shift rate = {mean_rate:.2f}")
    print(f"[RESULT] PASS: {passed}  (rate >= 1.5 confirms algebraic decay; §7b target ~3)")


if __name__ == "__main__":
    main()
