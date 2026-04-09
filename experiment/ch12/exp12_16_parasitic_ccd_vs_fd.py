#!/usr/bin/env python3
"""[12-16] CCD vs FD parasitic flow comparison (static droplet).

Paper ref: SS9 — CCD balanced-force gives O(10^-5) parasitic current
vs O(10^-2) for standard 2nd-order FD at N=64.

Compares parasitic flow magnitude between CCD-gradient and 2nd-order
FD-gradient balanced-force projection for a static circular droplet.
Both operators are used consistently for BOTH the surface tension
gradient (grad H) and the pressure gradient (grad p), so the
balanced-force cancellation quality depends on operator accuracy:
CCD gives O(h^6) cancellation, FD gives O(h^2).

Setup
-----
  Domain [0,1]^2, wall BC, R=0.25, center (0.5, 0.5)
  rho_l = rho_g = 1  (single-density, isolates parasitic flow)
  sigma = 1.0, We = 1
  Non-incremental projection, 200 time steps
  Grid: N = 32, 64, 128

Output
------
  experiment/ch12/results/parasitic_ccd_vs_fd_16/
    parasitic_ccd_vs_fd.pdf     -- convergence + N=64 velocity contours
    data.npz                    -- raw data

Usage
-----
  python experiment/ch12/exp12_16_parasitic_ccd_vs_fd.py
  python experiment/ch12/exp12_16_parasitic_ccd_vs_fd.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.levelset.curvature_filter import InterfaceLimitedFilter
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

# -- Physical parameters -------------------------------------------------------
RHO_L = 1.0
RHO_G = 1.0
SIGMA = 1.0
WE = 1.0
R = 0.25
DP_EXACT = SIGMA / (R * WE)   # = 4.0
N_STEPS = 200
GRIDS = [32, 64, 128]


# -- 2nd-order FD gradient ------------------------------------------------------

def fd_gradient(f, h):
    """2nd-order central FD gradient with 2nd-order one-sided boundaries."""
    dfdx = np.zeros_like(f)
    dfdy = np.zeros_like(f)
    # Central interior
    dfdx[1:-1, :] = (f[2:, :] - f[:-2, :]) / (2 * h)
    dfdy[:, 1:-1] = (f[:, 2:] - f[:, :-2]) / (2 * h)
    # One-sided at boundaries
    dfdx[0, :] = (-3 * f[0, :] + 4 * f[1, :] - f[2, :]) / (2 * h)
    dfdx[-1, :] = (3 * f[-1, :] - 4 * f[-2, :] + f[-3, :]) / (2 * h)
    dfdy[:, 0] = (-3 * f[:, 0] + 4 * f[:, 1] - f[:, 2]) / (2 * h)
    dfdy[:, -1] = (3 * f[:, -1] - 4 * f[:, -2] + f[:, -3]) / (2 * h)
    return dfdx, dfdy


# -- PPE solver ----------------------------------------------------------------

def _build_fd_laplacian(N, h):
    """Build 2nd-order FD Laplacian for N x N grid with Neumann BC (pin [0,0])."""
    n = N * N
    h2 = h * h
    rows, cols, vals = [], [], []
    for j in range(N):
        for i in range(N):
            idx = j * N + i
            diag = 0.0
            # x-direction
            if i > 0:
                rows.append(idx); cols.append(idx - 1); vals.append(1.0 / h2)
                diag -= 1.0 / h2
            if i < N - 1:
                rows.append(idx); cols.append(idx + 1); vals.append(1.0 / h2)
                diag -= 1.0 / h2
            # y-direction
            if j > 0:
                rows.append(idx); cols.append(idx - N); vals.append(1.0 / h2)
                diag -= 1.0 / h2
            if j < N - 1:
                rows.append(idx); cols.append(idx + N); vals.append(1.0 / h2)
                diag -= 1.0 / h2
            rows.append(idx); cols.append(idx); vals.append(diag)
    A = sp.csr_matrix((vals, (rows, cols)), shape=(n, n))
    # Pin pressure at (0, 0)
    pin = 0
    A[pin, :] = 0
    A[pin, pin] = 1.0
    A.eliminate_zeros()
    return A, pin


def _solve_ppe_ccd(rhs, rho, ppe_builder):
    """Solve PPE using the CCD-based PPE builder."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _solve_ppe_fd(rhs, N, h, pin):
    """Solve PPE using 2nd-order FD Laplacian (constant rho=1)."""
    A, _ = _build_fd_laplacian(N, h)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[pin] = 0.0
    return spsolve(A, rhs_vec).reshape((N, N))


# -- Wall BC helper -------------------------------------------------------------

def wall_bc(arr):
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


# -- Single-grid run with specified gradient operator ---------------------------

def run(N, method="ccd"):
    """Run static droplet on N x N grid using given gradient method.

    Parameters
    ----------
    N : int
        Grid resolution.
    method : str
        ``"ccd"`` for CCD gradient, ``"fd"`` for 2nd-order FD.

    Returns
    -------
    dict
        Diagnostics including parasitic velocity and pressure error.
    """
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)

    # CCD-based PPE builder (needed for method="ccd")
    if method == "ccd":
        ppe_builder = PPEBuilder(backend, grid, bc_type="wall")

    X, Y = grid.meshgrid()
    rho = np.ones_like(X) * RHO_L   # single-density

    # Level-set and Heaviside
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))

    # HFE-filtered curvature (always CCD — curvature computation is separate)
    xp = backend.xp
    kappa_raw = curv_calc.compute(psi)
    kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))

    # CSF surface tension force: F_sigma = (sigma/We) * kappa * grad(psi)
    # Gradient of psi uses the SAME operator as pressure gradient (balanced-force)
    if method == "ccd":
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        dpsi_dx = np.asarray(dpsi_dx)
        dpsi_dy = np.asarray(dpsi_dy)
    else:
        dpsi_dx, dpsi_dy = fd_gradient(psi, h)

    f_csf_x = (SIGMA / WE) * kappa * dpsi_dx
    f_csf_y = (SIGMA / WE) * kappa * dpsi_dy

    # Time-stepping
    u = np.zeros_like(X)
    v = np.zeros_like(X)
    u_max_history = []

    for step in range(N_STEPS):
        # Predictor (non-incremental)
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # Divergence of predicted velocity
        if method == "ccd":
            du_dx, _ = ccd.differentiate(u_star, 0)
            dv_dy, _ = ccd.differentiate(v_star, 1)
            div_ustar = np.asarray(du_dx) + np.asarray(dv_dy)
        else:
            du_dx, _ = fd_gradient(u_star, h)
            _, dv_dy = fd_gradient(v_star, h)
            div_ustar = du_dx + dv_dy

        rhs = div_ustar / dt

        # PPE solve
        if method == "ccd":
            p = _solve_ppe_ccd(rhs, rho, ppe_builder)
        else:
            p = _solve_ppe_fd(rhs, N, h, pin=0)

        # Corrector — pressure gradient uses SAME operator
        if method == "ccd":
            dp_dx, _ = ccd.differentiate(p, 0)
            dp_dy, _ = ccd.differentiate(p, 1)
            dp_dx = np.asarray(dp_dx)
            dp_dy = np.asarray(dp_dy)
        else:
            dp_dx, dp_dy = fd_gradient(p, h)

        u = u_star - dt / rho * dp_dx
        v = v_star - dt / rho * dp_dy
        wall_bc(u); wall_bc(v)

        vel_mag = np.sqrt(u**2 + v**2)
        u_max_history.append(float(np.max(vel_mag)))

        if np.isnan(u_max_history[-1]) or u_max_history[-1] > 1e6:
            print(f"    [N={N}, {method}] BLOWUP at step {step + 1}")
            break

    # Laplace pressure
    inside = phi > 3 * h
    outside = phi < -3 * h
    if np.any(inside) and np.any(outside):
        dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
    else:
        dp_meas = float("nan")
    dp_rel_err = abs(dp_meas - DP_EXACT) / DP_EXACT

    # Parasitic velocity field at final step (for contour plot)
    vel_final = np.sqrt(u**2 + v**2)

    return {
        "N": N, "h": h, "method": method,
        "u_para_inf": max(u_max_history),
        "u_para_final": u_max_history[-1],
        "dp_meas": dp_meas, "dp_exact": DP_EXACT,
        "dp_rel_err": dp_rel_err,
        "u_max_history": np.array(u_max_history),
        "vel_field": vel_final,
    }


# -- Plotting ------------------------------------------------------------------

def make_figures(results_ccd, results_fd):
    """Generate comparison figures."""
    hs_ccd = [r["h"] for r in results_ccd]
    hs_fd = [r["h"] for r in results_fd]
    u_ccd = [r["u_para_inf"] for r in results_ccd]
    u_fd = [r["u_para_inf"] for r in results_fd]
    dp_ccd = [r["dp_rel_err"] for r in results_ccd]
    dp_fd = [r["dp_rel_err"] for r in results_fd]
    h_ref = np.array(hs_ccd)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # (a) Parasitic current vs h — CCD and FD
    ax = axes[0]
    ax.loglog(hs_ccd, u_ccd, "o-", color=COLORS[0], linewidth=1.5, markersize=7,
              label="CCD (balanced-force)")
    ax.loglog(hs_fd, u_fd, "s-", color=COLORS[1], linewidth=1.5, markersize=7,
              label="FD$_2$ (balanced-force)")
    # Reference slopes
    ax.loglog(h_ref, u_ccd[0] * (h_ref / hs_ccd[0])**2, "k--", alpha=0.4,
              label=r"$O(h^2)$")
    ax.loglog(h_ref, u_ccd[0] * (h_ref / hs_ccd[0])**4, "k:", alpha=0.4,
              label=r"$O(h^4)$")
    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$\|\mathbf{u}_{\mathrm{para}}\|_\infty$")
    ax.set_title("(a) Parasitic current")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    # (b) Laplace pressure error vs h
    ax = axes[1]
    ax.loglog(hs_ccd, dp_ccd, "o-", color=COLORS[0], linewidth=1.5, markersize=7,
              label="CCD")
    ax.loglog(hs_fd, dp_fd, "s-", color=COLORS[1], linewidth=1.5, markersize=7,
              label="FD$_2$")
    ax.loglog(h_ref, dp_ccd[0] * (h_ref / hs_ccd[0])**1, "k--", alpha=0.4,
              label=r"$O(h^1)$")
    ax.loglog(h_ref, dp_ccd[0] * (h_ref / hs_ccd[0])**2, "k:", alpha=0.4,
              label=r"$O(h^2)$")
    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$\Delta p$ relative error")
    ax.set_title(r"(b) Laplace pressure error")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    # (c) Velocity contour at N=64, side-by-side CCD vs FD
    ax = axes[2]
    # Find N=64 results
    r_ccd_64 = next((r for r in results_ccd if r["N"] == 64), results_ccd[-1])
    r_fd_64 = next((r for r in results_fd if r["N"] == 64), results_fd[-1])
    N64 = r_ccd_64["N"]
    h64 = r_ccd_64["h"]
    x1d = np.linspace(0.5 * h64, 1.0 - 0.5 * h64, N64)
    Xm, Ym = np.meshgrid(x1d, x1d, indexing="ij")

    # Plot FD field as background, CCD contour overlay
    vmax = float(np.max(r_fd_64["vel_field"]))
    if vmax < 1e-20:
        vmax = 1.0
    im = ax.pcolormesh(Xm, Ym, r_fd_64["vel_field"],
                       shading="auto", cmap="hot_r", vmin=0, vmax=vmax)
    # CCD contours on top
    levels_ccd = np.linspace(0, float(np.max(r_ccd_64["vel_field"])) * 0.8, 6)
    if levels_ccd[-1] > 0:
        ax.contour(Xm, Ym, r_ccd_64["vel_field"], levels=levels_ccd,
                   colors="cyan", linewidths=0.8, alpha=0.7)
    # Droplet outline
    theta = np.linspace(0, 2 * np.pi, 200)
    ax.plot(0.5 + R * np.cos(theta), 0.5 + R * np.sin(theta),
            "w--", linewidth=1.0, alpha=0.8)
    ax.set_xlabel("$x$"); ax.set_ylabel("$y$")
    ax.set_title(f"(c) $|\\mathbf{{u}}|$ at $N={N64}$\n"
                 f"color: FD ({r_fd_64['u_para_inf']:.1e}), "
                 f"contour: CCD ({r_ccd_64['u_para_inf']:.1e})")
    ax.set_aspect("equal")
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    cb.set_label(r"$|\mathbf{u}|$ (FD)")

    fig.tight_layout()
    save_figure(fig, OUT / "parasitic_ccd_vs_fd")


# -- Table ---------------------------------------------------------------------

def print_table(results_ccd, results_fd):
    print(f"\n{'='*78}")
    print("  [12-16] Parasitic Current: CCD vs FD Balanced-Force")
    print(f"{'='*78}")
    print(f"  {'Method':<6} {'N':>5} | {'h':>10} | {'||u_para||_inf':>14} | "
          f"{'Dp_err%':>10}")
    print("  " + "-" * 60)
    for label, results in [("CCD", results_ccd), ("FD", results_fd)]:
        for r in results:
            print(f"  {label:<6} {r['N']:>5} | {r['h']:>10.5f} | "
                  f"{r['u_para_inf']:>14.4e} | {r['dp_rel_err']:>9.2%}")
        print("  " + "-" * 60)

    # Convergence rates
    print("\n  Convergence rates (parasitic current):")
    for label, results in [("CCD", results_ccd), ("FD", results_fd)]:
        for i in range(1, len(results)):
            r0, r1 = results[i - 1], results[i]
            log_h = np.log(r0["h"] / r1["h"])
            if r0["u_para_inf"] > 0 and r1["u_para_inf"] > 0:
                rate = np.log(r0["u_para_inf"] / r1["u_para_inf"]) / log_h
            else:
                rate = float("nan")
            print(f"    {label}: N={r0['N']:>3}->{r1['N']:>3}:  "
                  f"||u||_inf rate = {rate:+.2f}")

    # Ratio at N=64
    r_ccd_64 = next((r for r in results_ccd if r["N"] == 64), None)
    r_fd_64 = next((r for r in results_fd if r["N"] == 64), None)
    if r_ccd_64 and r_fd_64 and r_ccd_64["u_para_inf"] > 0:
        ratio = r_fd_64["u_para_inf"] / r_ccd_64["u_para_inf"]
        print(f"\n  At N=64:  FD/CCD parasitic ratio = {ratio:.0f}x")
        print(f"    CCD: {r_ccd_64['u_para_inf']:.2e}")
        print(f"    FD:  {r_fd_64['u_para_inf']:.2e}")


# -- Main ----------------------------------------------------------------------

def main():
    args = experiment_argparser("[12-16] Parasitic CCD vs FD").parse_args()

    if args.plot_only:
        data = load_results(NPZ)
        make_figures(data["results_ccd"], data["results_fd"])
        return

    results_ccd = []
    results_fd = []

    for N in GRIDS:
        print(f"  Running N={N}, CCD ...")
        r = run(N, method="ccd")
        results_ccd.append(r)

        print(f"  Running N={N}, FD ...")
        r = run(N, method="fd")
        results_fd.append(r)

    print_table(results_ccd, results_fd)

    # Save (strip large arrays for portability; keep vel_field for N=64)
    def _strip(r, keep_vel=False):
        d = {k: v for k, v in r.items()
             if k not in ("u_max_history", "vel_field")}
        return d

    save_data = {
        "results_ccd": [_strip(r) for r in results_ccd],
        "results_fd": [_strip(r) for r in results_fd],
    }
    # Save velocity fields and histories separately
    for i, r in enumerate(results_ccd):
        save_data[f"vel_ccd_{i}"] = r["vel_field"]
        save_data[f"hist_ccd_{i}"] = r["u_max_history"]
    for i, r in enumerate(results_fd):
        save_data[f"vel_fd_{i}"] = r["vel_field"]
        save_data[f"hist_fd_{i}"] = r["u_max_history"]
    save_results(NPZ, save_data)

    # Reconstruct full dicts for plotting
    for i, r in enumerate(results_ccd):
        r.pop("u_max_history", None)
    for i, r in enumerate(results_fd):
        r.pop("u_max_history", None)

    make_figures(results_ccd, results_fd)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    main()
