#!/usr/bin/env python3
"""exp12_10  Variable-density monolithic DC breakdown.

This script matches paper §12.5: it does *not* perform an A@p round trip.
Instead it solves a manufactured variable-density PPE by defect correction,
using a high-order CCD residual and a low-order FD variable-coefficient
preconditioner:

    L_H(p) = (1/rho) Lap(p) - (grad rho · grad p) / rho^2
    p_{k+1} = p_k + L_L^{-1}(rhs - L_H(p_k)).

The reported residuals are ||rhs - L_H(p_k)||_inf for k=0 and k=3.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.tools.experiment.gpu import sparse_solve_2d
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.levelset.curvature import CurvatureCalculator
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure, COLORS, MARKERS,
)

try:
    from twophase.simulation.visualization.plot_fields import (
        field_with_contour, symmetric_range,
    )
    _HAS_PLOT_FIELDS = True
except Exception:
    _HAS_PLOT_FIELDS = False

apply_style()
OUT = experiment_dir(__file__, "10_density_sweep")
NPZ = OUT / "density_sweep.npz"

R = 0.25
K_DC = 3


def _zero_boundary(a):
    a[0, :] = 0.0
    a[-1, :] = 0.0
    a[:, 0] = 0.0
    a[:, -1] = 0.0


def _smoothed_density(phi, eps, rho_ratio):
    H = 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))
    rho_g = 1.0 / rho_ratio
    return 1.0 + (rho_g - 1.0) * (1.0 - H)


def _eval_lh_varrho(p, rho, ccd, backend):
    xp = backend.xp
    p_dev = xp.asarray(p)
    rho_dev = xp.asarray(rho)
    out = xp.zeros_like(p_dev)
    for ax in range(2):
        dp, d2p = ccd.differentiate(p_dev, ax)
        drho, _ = ccd.differentiate(rho_dev, ax)
        out += d2p / rho_dev - (drho / rho_dev ** 2) * dp
    return np.asarray(backend.to_host(out))


def _build_fd_varrho_dirichlet(N, h, rho):
    import scipy.sparse as sp
    nx = ny = N + 1
    rows, cols, vals = [], [], []
    drho_dx = np.zeros_like(rho)
    drho_dy = np.zeros_like(rho)
    drho_dx[1:N, :] = (rho[2:N + 1, :] - rho[0:N - 1, :]) / (2.0 * h)
    drho_dy[:, 1:N] = (rho[:, 2:N + 1] - rho[:, 0:N - 1]) / (2.0 * h)

    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if i == 0 or i == N or j == 0 or j == N:
                rows.append(k); cols.append(k); vals.append(1.0)
                continue
            inv_rho = 1.0 / rho[i, j]
            cx = drho_dx[i, j] / rho[i, j] ** 2
            cy = drho_dy[i, j] / rho[i, j] ** 2
            coeff = 1.0 / h ** 2
            rows.append(k); cols.append((i + 1) * ny + j); vals.append(inv_rho * coeff - cx / (2.0 * h))
            rows.append(k); cols.append((i - 1) * ny + j); vals.append(inv_rho * coeff + cx / (2.0 * h))
            rows.append(k); cols.append(i * ny + (j + 1)); vals.append(inv_rho * coeff - cy / (2.0 * h))
            rows.append(k); cols.append(i * ny + (j - 1)); vals.append(inv_rho * coeff + cy / (2.0 * h))
            rows.append(k); cols.append(k); vals.append(-4.0 * inv_rho * coeff)
    return sp.csr_matrix((vals, (rows, cols)), shape=(nx * ny, nx * ny))


def run_dc_case(N, rho_ratio, k_dc=K_DC):
    backend = Backend()
    h = 1.0 / N
    eps = 1.5 * h
    grid = Grid(GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    X, Y = grid.meshgrid()
    # DC loop is CPU-based (FD matrix + spsolve); convert meshgrid to host
    X, Y = backend.to_host(X), backend.to_host(Y)

    p_star = np.sin(np.pi * X) * np.sin(np.pi * Y)
    phi = R - np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    rho = _smoothed_density(phi, eps, rho_ratio)
    liquid = phi > 3.0 * h

    rhs = _eval_lh_varrho(p_star, rho, ccd, backend)
    _zero_boundary(rhs)
    A = _build_fd_varrho_dirichlet(N, h, rho)

    from scipy.sparse.linalg import spsolve as _spsolve
    p = np.zeros_like(p_star)
    residuals = []
    for k in range(k_dc + 1):
        res = rhs - _eval_lh_varrho(p, rho, ccd, backend)
        _zero_boundary(res)
        residuals.append(float(np.max(np.abs(res))))
        if k == k_dc:
            break
        dp = _spsolve(A, res.ravel()).reshape(p.shape)
        _zero_boundary(dp)
        p = p + dp
        _zero_boundary(p)

    err = float(np.max(np.abs(p - p_star)))
    err_liq = float(np.max(np.abs((p - p_star)[liquid]))) if np.any(liquid) else err
    return {
        "N": N,
        "h": h,
        "rho_ratio": float(rho_ratio),
        "err_linf": err,
        "err_liq": err_liq,
        "r0": residuals[0],
        "r3": residuals[3],
        "residuals": np.array(residuals),
        "status": "conv" if residuals[3] < residuals[0] else "divg",
    }


def run_density_sweep():
    return [run_dc_case(64, rr) for rr in [2, 5, 10, 20, 50, 100]]


def run_grid_convergence(rho_ratio):
    return [run_dc_case(N, rho_ratio) for N in [16, 32, 64, 128]]


def _rate(r0, r1, key):
    if r0[key] <= 0 or r1[key] <= 0:
        return float("nan")
    return float(np.log(r0[key] / r1[key]) / np.log(r0["h"] / r1["h"]))


def make_figures(sweep, conv_2, conv_5):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    rr = [r["rho_ratio"] for r in sweep]
    ax.semilogy(rr, [r["err_liq"] for r in sweep], "o-", color=COLORS[0],
                label=r"$L^\infty$ error")
    ax.semilogy(rr, [r["r3"] / r["r0"] for r in sweep], "s--", color=COLORS[1],
                label=r"$\|r_3\|_\infty/\|r_0\|_\infty$")
    ax.axhline(1.0, color="k", lw=1.0, ls=":", alpha=0.7)
    ax.set_xscale("log")
    ax.set_xlabel(r"$\rho_l/\rho_g$")
    ax.set_ylabel("Error / residual ratio")
    ax.set_title("(a) Monolithic DC density-ratio limit")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(fontsize=8)

    ax = axes[1]
    for label, conv, color, marker in [
        (r"$\rho_l/\rho_g=2$", conv_2, COLORS[0], MARKERS[0]),
        (r"$\rho_l/\rho_g=5$", conv_5, COLORS[1], MARKERS[1]),
    ]:
        ax.loglog([r["h"] for r in conv], [r["err_liq"] for r in conv],
                  f"{marker}-", color=color, label=label)
    h_ref = np.array([conv_2[0]["h"], conv_2[-1]["h"]])
    ax.loglog(h_ref, conv_2[0]["err_liq"] * (h_ref / h_ref[0]) ** 2,
              "k:", alpha=0.5, label=r"$O(h^2)$")
    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$L^\infty$ error (liquid interior)")
    ax.set_title("(b) Grid convergence")
    ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()
    ax.legend(fontsize=8)

    fig.tight_layout()
    save_figure(fig, OUT / "density_sweep")


def _solve_ppe(rhs, rho, ppe_builder, backend):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = [backend.to_device(a) for a in triplet]
    A = backend.sparse.csr_matrix((data, (rows, cols)), shape=A_shape)
    xp = backend.xp
    rhs_flat = xp.asarray(rhs).ravel().copy()
    rhs_flat[ppe_builder._pin_dof] = 0.0
    return sparse_solve_2d(backend, A, rhs_flat).reshape(rho.shape)


def _run_droplet_snapshot(rho_l, rho_g=1.0, N=64, n_steps=50):
    backend = Backend()
    xp = backend.xp
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h
    grid = Grid(GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = R - xp.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    psi = heaviside(xp, phi, eps)
    rho = rho_g + (rho_l - rho_g) * psi
    u = xp.zeros_like(psi)
    v = xp.zeros_like(psi)

    kappa = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_x = 0.1 * kappa * dpsi_dx
    f_y = 0.1 * kappa * dpsi_dy

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    p = xp.zeros_like(psi)
    for _ in range(n_steps):
        u_star = u + dt / rho * f_x
        v_star = v + dt / rho * f_y
        wall_bc(u_star); wall_bc(v_star)
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (du_dx + dv_dy) / dt
        p = _solve_ppe(rhs, rho, ppe_builder, backend)
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * dp_dx
        v = v_star - dt / rho * dp_dy
        wall_bc(u); wall_bc(v)

    return {
        "rho_ratio": rho_l / rho_g,
        "p": backend.to_host(p), "u": backend.to_host(u),
        "v": backend.to_host(v), "psi": backend.to_host(psi),
        "x1d": np.linspace(0, 1, N + 1),
        "y1d": np.linspace(0, 1, N + 1),
    }


def run_field_snapshots():
    return [_run_droplet_snapshot(float(rr), 1.0) for rr in [2, 3, 5, 10]]


def make_field_figure(snapshots):
    if not _HAS_PLOT_FIELDS:
        return
    n = len(snapshots)
    fig, axes = plt.subplots(2, n, figsize=(3.5 * n, 7))
    p_vmax = max(symmetric_range(s["p"]) for s in snapshots)
    speed_vmax = max(float(np.max(np.sqrt(s["u"] ** 2 + s["v"] ** 2)))
                     for s in snapshots)
    im_p = im_v = None
    for col, snap in enumerate(snapshots):
        speed = np.sqrt(snap["u"] ** 2 + snap["v"] ** 2)
        im_p = field_with_contour(
            axes[0, col], snap["x1d"], snap["y1d"], snap["p"],
            cmap="RdBu_r", vmin=-p_vmax, vmax=p_vmax,
            contour_field=snap["psi"], contour_level=0.5,
            title=rf"$\rho_l/\rho_g={int(snap['rho_ratio'])}$",
            xlabel="$x$", ylabel="$y$" if col == 0 else "",
        )
        im_v = field_with_contour(
            axes[1, col], snap["x1d"], snap["y1d"], speed,
            cmap="viridis", vmin=0.0, vmax=speed_vmax,
            contour_field=snap["psi"], contour_level=0.5,
            title="", xlabel="$x$", ylabel="$y$" if col == 0 else "",
        )
        axes[0, col].set_aspect("equal")
        axes[1, col].set_aspect("equal")
    if im_p is not None:
        fig.colorbar(im_p, ax=axes[0, :].tolist(), shrink=0.8, label="$p$")
    if im_v is not None:
        fig.colorbar(im_v, ax=axes[1, :].tolist(), shrink=0.8, label=r"$|\mathbf{u}|$")
    fig.tight_layout()
    save_figure(fig, OUT / "density_fields",
                also_to="paper/figures/ch12_density_fields.pdf")


def _flatten(results, prefix):
    flat = {f"n_{prefix}": len(results)}
    keys = ["N", "h", "rho_ratio", "err_linf", "err_liq", "r0", "r3", "status"]
    for i, r in enumerate(results):
        for k in keys:
            flat[f"{prefix}__r{i}_{k}"] = r[k]
        flat[f"{prefix}__r{i}_residuals"] = r["residuals"]
    return flat


def _rebuild(d, prefix):
    out = []
    for i in range(int(d[f"n_{prefix}"])):
        out.append({
            "N": int(d[f"{prefix}__r{i}_N"]),
            "h": float(d[f"{prefix}__r{i}_h"]),
            "rho_ratio": float(d[f"{prefix}__r{i}_rho_ratio"]),
            "err_linf": float(d[f"{prefix}__r{i}_err_linf"]),
            "err_liq": float(d[f"{prefix}__r{i}_err_liq"]),
            "r0": float(d[f"{prefix}__r{i}_r0"]),
            "r3": float(d[f"{prefix}__r{i}_r3"]),
            "status": str(d[f"{prefix}__r{i}_status"]),
            "residuals": np.asarray(d[f"{prefix}__r{i}_residuals"]),
        })
    return out


def main():
    args = experiment_argparser("Variable-density DC breakdown").parse_args()
    if args.plot_only:
        d = load_results(NPZ)
        make_figures(_rebuild(d, "sweep"), _rebuild(d, "conv_2"), _rebuild(d, "conv_5"))
        return

    print("\n" + "=" * 72)
    print("  exp12_10  Variable-density monolithic DC breakdown")
    print("=" * 72)

    sweep = run_density_sweep()
    print(f"\n  {'rho':>6} | {'err_liq':>11} | {'r0':>11} | {'r3':>11} | status")
    print("  " + "-" * 60)
    for r in sweep:
        print(f"  {r['rho_ratio']:>6.0f} | {r['err_liq']:>11.3e} | "
              f"{r['r0']:>11.3e} | {r['r3']:>11.3e} | {r['status']}")

    conv_2 = run_grid_convergence(2)
    conv_5 = run_grid_convergence(5)
    for label, conv in [(2, conv_2), (5, conv_5)]:
        print(f"\n  Grid convergence rho={label}:")
        for i, r in enumerate(conv):
            rate = "" if i == 0 else f" rate={_rate(conv[i-1], r, 'err_liq'):.2f}"
            print(f"    N={r['N']:>3}: err_liq={r['err_liq']:.3e}{rate}")

    snapshots = run_field_snapshots()
    make_field_figure(snapshots)

    flat = {}
    flat.update(_flatten(sweep, "sweep"))
    flat.update(_flatten(conv_2, "conv_2"))
    flat.update(_flatten(conv_5, "conv_5"))
    save_results(NPZ, flat)
    make_figures(sweep, conv_2, conv_5)
    print(f"\n  Results saved to {OUT}")


if __name__ == "__main__":
    main()
