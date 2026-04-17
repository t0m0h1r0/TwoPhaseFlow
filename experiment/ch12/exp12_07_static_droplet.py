#!/usr/bin/env python3
"""【12-7】Static droplet — standard projection convergence test.

Paper ref: §12.7 (sec:val_static_drop_standard)

Grid convergence of parasitic currents and Laplace pressure error
using the standard non-incremental projection with CCD pressure gradient.

Setup
-----
  Static droplet: R=0.25, center (0.5, 0.5), wall BC, gravity=0
  rho_l/rho_g = 2,  We = 10
  Non-incremental projection (200 steps per grid)
  Grid: N = 32, 48, 64, 96, 128

Output
------
  experiment/ch12/results/static_droplet_07/
    convergence.pdf          — parasitic current + Laplace error vs h
    parasitic_history.pdf    — ||u||_inf time history per grid
    convergence_data.npz     — raw data
    table_convergence.tex    — LaTeX table

Usage
-----
  python experiment/ch12/exp12_07_static_droplet.py
  python experiment/ch12/exp12_07_static_droplet.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np

from twophase.backend import Backend
from twophase.tools.experiment.gpu import sparse_solve_2d
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.levelset.curvature_filter import InterfaceLimitedFilter
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
)
from twophase.simulation.visualization.plot_fields import (
    field_with_contour, streamlines_colored, velocity_arrows, symmetric_range,
)

OUT = experiment_dir(__file__, "static_droplet_07")
NPZ_PATH = OUT / "convergence_data.npz"

# ── Physical parameters ─────────────────────────────────────────────────────
RHO_L   = 2.0
RHO_G   = 1.0
WE      = 10.0
R       = 0.25
SIGMA   = 1.0
N_STEPS = 200
GRIDS   = [32, 48, 64, 96, 128]


# ── PPE solver ───────────────────────────────────────────────────────────────

def _solve_ppe(rhs, rho, ppe_builder, backend):
    triplet, A_shape = ppe_builder.build(rho)  # always host (numpy) arrays
    data, rows, cols = [backend.to_device(a) for a in triplet]
    A = backend.sparse.csr_matrix((data, (rows, cols)), shape=A_shape)
    xp = backend.xp
    rhs_flat = xp.asarray(rhs).ravel().copy()
    rhs_flat[ppe_builder._pin_dof] = 0.0
    return sparse_solve_2d(backend, A, rhs_flat).reshape(rho.shape)


# ── Single-grid simulation ──────────────────────────────────────────────────

def run_single(N):
    """Run static droplet on N x N grid. Return diagnostics dict."""
    backend = Backend()
    xp = backend.xp
    h   = 1.0 / N
    eps = 1.5 * h
    dt  = 0.25 * h

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc   = CurvatureCalculator(backend, ccd, eps)
    hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)

    X, Y = grid.meshgrid()
    dp_exact = SIGMA / (R * WE)

    # Initial conditions
    phi = R - xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = heaviside(xp, phi, eps)
    rho = RHO_G + (RHO_L - RHO_G) * psi

    u = xp.zeros_like(X)
    v = xp.zeros_like(X)

    # Precompute CSF with HFE-filtered curvature
    kappa_raw = curv_calc.compute(psi)
    kappa = hfe.apply(kappa_raw, psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * dpsi_dx
    f_csf_y = (SIGMA / WE) * kappa * dpsi_dy

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u_max_history = []

    for step in range(N_STEPS):
        # Predictor (non-incremental: no grad p^n)
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # PPE
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (du_dx + dv_dy) / dt
        p = _solve_ppe(rhs, rho, ppe_builder, backend)

        # Corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * dp_dx
        v = v_star - dt / rho * dp_dy
        wall_bc(u); wall_bc(v)

        vel_mag = xp.sqrt(u**2 + v**2)
        u_max_history.append(float(xp.max(vel_mag)))

        if np.isnan(u_max_history[-1]) or u_max_history[-1] > 1e6:
            print(f"    [N={N}] BLOWUP at step {step + 1}")
            break

    # Laplace pressure
    inside  = phi >  3 * h
    outside = phi < -3 * h
    if bool(xp.any(inside)) and bool(xp.any(outside)):
        dp_meas = float(xp.mean(p[inside]) - xp.mean(p[outside]))
    else:
        dp_meas = float('nan')
    dp_err = abs(dp_meas - dp_exact) / dp_exact

    out = {
        "N": N, "h": h,
        "u_max_peak": max(u_max_history),
        "u_max_final": u_max_history[-1],
        "dp_meas": dp_meas,
        "dp_exact": dp_exact,
        "dp_rel_err": dp_err,
        "u_max_history": np.array(u_max_history),
        "n_steps": len(u_max_history),
    }
    if N == 64:
        out["p_field"]   = backend.to_host(p)
        out["u_field"]   = backend.to_host(u)
        out["v_field"]   = backend.to_host(v)
        out["psi_field"] = backend.to_host(psi)
        out["X"]         = backend.to_host(X)
        out["Y"]         = backend.to_host(Y)
    return out


# ── Plotting ─────────────────────────────────────────────────────────────────

def make_figures(results):
    """Generate convergence and time-history plots."""
    apply_style()
    import matplotlib.pyplot as plt

    Ns       = [r["N"] for r in results]
    hs       = [r["h"] for r in results]
    u_peaks  = [r["u_max_peak"] for r in results]
    dp_errs  = [r["dp_rel_err"] for r in results]
    h_ref    = np.array(hs)

    # ── Convergence plot ──
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    ax.loglog(hs, u_peaks, 'bo-', lw=1.5, ms=8,
              label=r"$\|\mathbf{u}_{\mathrm{para}}\|_\infty$")
    ax.loglog(h_ref, u_peaks[0] * (h_ref / hs[0])**1, 'k--', alpha=0.5,
              label=r"$O(h^1)$")
    ax.loglog(h_ref, u_peaks[0] * (h_ref / hs[0])**2, 'k:', alpha=0.5,
              label=r"$O(h^2)$")
    ax.set_xlabel("Grid spacing $h$")
    ax.set_ylabel(r"$\|\mathbf{u}_{\mathrm{para}}\|_\infty$")
    ax.set_title("Parasitic Current Convergence")
    ax.legend(); ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    ax = axes[1]
    ax.loglog(hs, dp_errs, 'rs-', lw=1.5, ms=8,
              label=r"$|\Delta p - \sigma/R| / (\sigma/R)$")
    ax.loglog(h_ref, dp_errs[0] * (h_ref / hs[0])**1, 'k--', alpha=0.5,
              label=r"$O(h^1)$")
    ax.loglog(h_ref, dp_errs[0] * (h_ref / hs[0])**2, 'k:', alpha=0.5,
              label=r"$O(h^2)$")
    ax.set_xlabel("Grid spacing $h$")
    ax.set_ylabel(r"$\Delta p$ relative error")
    ax.set_title("Laplace Pressure Convergence")
    ax.legend(); ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    plt.tight_layout()
    save_figure(fig, OUT / "convergence")

    # ── Time history ──
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    for r in results:
        ax2.semilogy(np.arange(1, r["n_steps"] + 1), r["u_max_history"],
                     lw=1.2, label=f"$N={r['N']}$")
    ax2.set_xlabel("Time step")
    ax2.set_ylabel(r"$\|\mathbf{u}_{\mathrm{para}}\|_\infty$")
    ax2.set_title("Parasitic Current Time History")
    ax2.legend(); ax2.grid(True, alpha=0.3)
    save_figure(fig2, OUT / "parasitic_history")


# ── Field visualization (N=64 only) ─────────────────────────────────────────

def make_field_figure(r64):
    """Generate 5-panel field figure for N=64 and save as ch12_droplet_fields.pdf."""
    apply_style()
    import matplotlib.pyplot as plt

    p   = r64["p_field"]
    u   = r64["u_field"]
    v   = r64["v_field"]
    psi = r64["psi_field"]
    X   = r64["X"]
    Y   = r64["Y"]
    h   = r64["h"]

    x1d = X[:, 0]
    y1d = Y[0, :]

    speed = np.sqrt(u**2 + v**2)

    # Vorticity via np.gradient (post-processing, not CCD)
    dv_dx = np.gradient(v, h, axis=0)
    du_dy = np.gradient(u, h, axis=1)
    omega = dv_dx - du_dy

    p_vmax    = symmetric_range([p])
    spd_vmax  = float(speed.max()) or 1e-10
    omg_vmax  = symmetric_range([omega])

    fig, axes = plt.subplots(1, 5, figsize=(20, 4))
    fig.suptitle(r"Static droplet fields ($N=64$, $t=200\Delta t$)", fontsize=12)

    # (a) Pressure
    im_p = field_with_contour(
        axes[0], x1d, y1d, p,
        cmap="RdBu_r", vmin=-p_vmax, vmax=p_vmax,
        contour_field=psi, contour_level=0.5,
        title="(a) Pressure $p$", ylabel="$y$",
    )
    fig.colorbar(im_p, ax=axes[0], fraction=0.046, pad=0.04)

    # (b) Parasitic velocity magnitude
    im_spd = field_with_contour(
        axes[1], x1d, y1d, speed,
        cmap="viridis", vmin=0, vmax=spd_vmax,
        contour_field=psi, contour_level=0.5,
        title=r"(b) Speed $|\mathbf{u}|$",
    )
    fig.colorbar(im_spd, ax=axes[1], fraction=0.046, pad=0.04)

    # (c) Vorticity
    im_omg = field_with_contour(
        axes[2], x1d, y1d, omega,
        cmap="RdBu_r", vmin=-omg_vmax, vmax=omg_vmax,
        contour_field=psi, contour_level=0.5,
        title=r"(c) Vorticity $\omega$",
    )
    fig.colorbar(im_omg, ax=axes[2], fraction=0.046, pad=0.04)

    # (d) Streamlines colored by speed
    streamlines_colored(
        axes[3], x1d, y1d, u, v,
        cmap="viridis", density=1.5,
        contour_field=psi, contour_level=0.5, contour_color="r",
    )
    axes[3].set_title("(d) Streamlines")
    axes[3].set_xlabel("$x$")

    # (e) Velocity vectors with speed background
    velocity_arrows(
        axes[4], X, Y, u, v, x1d, y1d,
        stride=4, speed_cmap="YlOrRd", speed_vmax=spd_vmax,
        contour_field=psi, contour_level=0.5, contour_color="b",
    )
    axes[4].set_title("(e) Velocity vectors")
    axes[4].set_xlabel("$x$")

    plt.tight_layout()
    save_figure(fig, OUT / "droplet_fields",
                also_to="paper/figures/ch12_droplet_fields.pdf")
    print(f"  Field figure saved: {OUT / 'droplet_fields.pdf'}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 80)
    print("  [12-7] Static Droplet Grid Convergence (standard projection)")
    print("=" * 80 + "\n")

    results = []

    print(f"  {'N':>5} | {'h':>10} | {'||u||inf_peak':>14} | "
          f"{'dp_err':>10} | {'steps':>6}")
    print("  " + "-" * 62)

    for N in GRIDS:
        r = run_single(N)
        results.append(r)
        print(f"  {N:>5} | {r['h']:>10.5f} | {r['u_max_peak']:>14.4e} | "
              f"{r['dp_rel_err']:>9.2%} | {r['n_steps']:>6}")

    # Convergence rates
    print("\n  Convergence rates (successive pairs):")
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        rate_u = (np.log(r0["u_max_peak"] / r1["u_max_peak"])
                  / np.log(r0["h"] / r1["h"])
                  if r0["u_max_peak"] > 0 and r1["u_max_peak"] > 0
                  else float('nan'))
        rate_dp = (np.log(r0["dp_rel_err"] / r1["dp_rel_err"])
                   / np.log(r0["h"] / r1["h"])
                   if r0["dp_rel_err"] > 0 and r1["dp_rel_err"] > 0
                   else float('nan'))
        print(f"    N={r0['N']:>3} -> {r1['N']:>3}: "
              f"||u||inf rate={rate_u:+.2f},  dp rate={rate_dp:+.2f}")

    make_figures(results)

    r64_list = [r for r in results if r["N"] == 64]
    if r64_list:
        make_field_figure(r64_list[0])

    # Save LaTeX table
    with open(OUT / "table_convergence.tex", "w") as fp:
        fp.write("% Auto-generated by exp12_07_static_droplet.py\n")
        fp.write("\\begin{tabular}{rcccc}\n\\toprule\n")
        fp.write("$N$ & $h$ & $\\|\\bu_{\\mathrm{para}}\\|_\\infty$ & "
                 "$\\Delta p$ rel.\\ error & conv.\\ rate \\\\\n")
        fp.write("\\midrule\n")
        for i, r in enumerate(results):
            if i > 0:
                r0 = results[i - 1]
                rate = np.log(r0["dp_rel_err"] / r["dp_rel_err"]) / \
                       np.log(r0["h"] / r["h"])
                rate_str = f"${rate:.2f}$"
            else:
                rate_str = "---"
            fp.write(f"{r['N']} & ${r['h']:.4f}$ & "
                     f"${r['u_max_peak']:.2e}$ & "
                     f"${r['dp_rel_err']:.2e}$ & {rate_str} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Table saved: {OUT / 'table_convergence.tex'}")

    # Save raw data
    FIELD_KEYS = {"p_field", "u_field", "v_field", "psi_field", "X", "Y"}
    save_data = {}
    for i, r in enumerate(results):
        save_data[f"u_max_hist_{i}"] = r["u_max_history"]
        if r["N"] == 64:
            for k in FIELD_KEYS:
                if k in r:
                    save_data[f"f64_{k}"] = r[k]
    save_data["results"] = [{k: v for k, v in r.items()
                             if k != "u_max_history" and k not in FIELD_KEYS}
                            for r in results]
    save_results(NPZ_PATH, save_data)


if __name__ == "__main__":
    args = experiment_argparser("Static droplet grid convergence").parse_args()

    if args.plot_only:
        d = load_results(NPZ_PATH)
        _results = [dict(r.item()) if hasattr(r, 'item') else dict(r)
                    for r in d["results"]]
        for _i in range(len(_results)):
            _results[_i]["u_max_history"] = list(d[f"u_max_hist_{_i}"])
        make_figures(_results)
        _FIELD_KEYS = {"p_field", "u_field", "v_field", "psi_field", "X", "Y"}
        _r64 = next((r for r in _results if r["N"] == 64), None)
        if _r64 is not None and all(f"f64_{k}" in d for k in _FIELD_KEYS):
            for k in _FIELD_KEYS:
                _r64[k] = d[f"f64_{k}"]
            make_field_figure(_r64)
    else:
        main()
