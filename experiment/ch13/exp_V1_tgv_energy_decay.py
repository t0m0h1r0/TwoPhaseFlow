#!/usr/bin/env python3
"""[V1] Taylor--Green vortex with CCD spatial operators and PPE projection.

Paper ref: §13.1 (sec:energy_conservation).

Solves the periodic 2-D Taylor--Green vortex using project CCD derivatives for
advection/diffusion and a pressure-projection step built from ``PPEBuilder``.
The previous FFT/spectral proxy is retained as a C2 legacy reference under
``experiment/ch13/legacy/``.

Usage
-----
  make run EXP=experiment/ch13/exp_V1_tgv_energy_decay.py
  make plot EXP=experiment/ch13/exp_V1_tgv_energy_decay.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.simulation.visualization.plot_fields import (
    field_with_contour,
    symmetric_range,
)
from twophase.simulation.visualization.plot_vector import compute_vorticity_2d
from twophase.tools.experiment import (
    apply_style,
    compute_convergence_rates,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)
from twophase.tools.experiment.gpu import sparse_solve_2d

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIGURES = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"

L = 2.0 * np.pi
NU = 0.01
T_FINAL = 0.05
SPATIAL_N = (32, 48, 64)
TIME_N = 64
SPATIAL_DT = 1.0e-3
TIME_DT_TARGETS = (4.0e-3, 2.0e-3, 1.0e-3)

# Snapshot run uses a much longer horizon so viscous decay (exp(-2 nu t))
# is visually meaningful: at t=50 with NU=0.01 the amplitude is ~0.37.
SNAPSHOT_T_FINAL = 50.0
SNAPSHOT_DT = 1.0e-2


def _setup(N: int, backend: Backend):
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(L, L)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    ppe = PPEBuilder(backend, grid, bc_type="periodic")
    X, Y = grid.meshgrid()
    return (
        grid,
        ccd,
        ppe,
        L / N,
        np.asarray(backend.to_host(X)),
        np.asarray(backend.to_host(Y)),
    )


def _exact_velocity(t: float, X: np.ndarray, Y: np.ndarray):
    decay = np.exp(-2.0 * NU * t)
    u = np.sin(X) * np.cos(Y) * decay
    v = -np.cos(X) * np.sin(Y) * decay
    return u, v


def _sync_periodic(arr: np.ndarray) -> np.ndarray:
    arr[-1, :] = arr[0, :]
    arr[:, -1] = arr[:, 0]
    return arr


def _grad(field, ccd, axis: int, backend: Backend) -> np.ndarray:
    d1, _ = ccd.differentiate(field, axis)
    return np.asarray(backend.to_host(d1))


def _lap(field, ccd, backend: Backend) -> np.ndarray:
    _, d2x = ccd.differentiate(field, 0)
    _, d2y = ccd.differentiate(field, 1)
    return np.asarray(backend.to_host(d2x)) + np.asarray(backend.to_host(d2y))


def _solve_ppe(rhs, ppe_builder, backend):
    triplet, shape = ppe_builder.build(np.ones_like(rhs))
    data, rows, cols = [backend.to_device(a) for a in triplet]
    A = backend.sparse.csr_matrix((data, (rows, cols)), shape=shape)
    rhs_flat = backend.xp.asarray(rhs).ravel().copy()
    rhs_flat[ppe_builder._pin_dof] = 0.0
    return np.asarray(sparse_solve_2d(backend, A, rhs_flat).reshape(rhs.shape))


def _rhs(u, v, ccd, backend):
    du_dx = _grad(u, ccd, 0, backend)
    du_dy = _grad(u, ccd, 1, backend)
    dv_dx = _grad(v, ccd, 0, backend)
    dv_dy = _grad(v, ccd, 1, backend)
    rhs_u = -(u * du_dx + v * du_dy) + NU * _lap(u, ccd, backend)
    rhs_v = -(u * dv_dx + v * dv_dy) + NU * _lap(v, ccd, backend)
    return _sync_periodic(rhs_u), _sync_periodic(rhs_v)


def _project(u_star, v_star, dt, ccd, ppe, backend):
    div = (_grad(u_star, ccd, 0, backend) + _grad(v_star, ccd, 1, backend)) / dt
    p = _solve_ppe(div, ppe, backend)
    u = u_star - dt * _grad(p, ccd, 0, backend)
    v = v_star - dt * _grad(p, ccd, 1, backend)
    return _sync_periodic(u), _sync_periodic(v)


def _energy(u: np.ndarray, v: np.ndarray, h: float) -> float:
    return float(0.5 * np.sum((u[:-1, :-1] ** 2 + v[:-1, :-1] ** 2) * h * h))


def _div_inf(u, v, ccd, backend) -> float:
    div = _grad(u, ccd, 0, backend) + _grad(v, ccd, 1, backend)
    return float(np.max(np.abs(div[:-1, :-1])))


def _run(N: int, dt_target: float) -> dict:
    backend = Backend(use_gpu=False)
    _, ccd, ppe, h, X, Y = _setup(N, backend)
    n_steps = max(1, int(np.ceil(T_FINAL / dt_target)))
    dt = T_FINAL / n_steps
    u, v = _exact_velocity(0.0, X, Y)
    u = _sync_periodic(u.copy())
    v = _sync_periodic(v.copy())
    rhs_prev = None
    div_max = _div_inf(u, v, ccd, backend)
    for _ in range(n_steps):
        rhs_u, rhs_v = _rhs(u, v, ccd, backend)
        if rhs_prev is None:
            u_star = u + dt * rhs_u
            v_star = v + dt * rhs_v
        else:
            rhs_u_prev, rhs_v_prev = rhs_prev
            u_star = u + dt * (1.5 * rhs_u - 0.5 * rhs_u_prev)
            v_star = v + dt * (1.5 * rhs_v - 0.5 * rhs_v_prev)
        u_star = _sync_periodic(u_star)
        v_star = _sync_periodic(v_star)
        u, v = _project(u_star, v_star, dt, ccd, ppe, backend)
        rhs_prev = (rhs_u, rhs_v)
        div_max = max(div_max, _div_inf(u, v, ccd, backend))
    u_ex, v_ex = _exact_velocity(T_FINAL, X, Y)
    e_num = _energy(u, v, h)
    e_ex = _energy(u_ex, v_ex, h)
    err = np.sqrt((u - u_ex) ** 2 + (v - v_ex) ** 2)
    return {
        "N": N,
        "h": h,
        "dt": dt,
        "n_steps": n_steps,
        "E_rel": abs(e_num - e_ex) / max(abs(e_ex), 1.0e-30),
        "u_Linf": float(np.max(err[:-1, :-1])),
        "div_inf_max": div_max,
    }


def run_V1_snapshots() -> dict:
    """Capture (u, v) and vorticity ω at t=0, T/2, T_final on N=TIME_N grid.

    Used for the 1×3 vorticity snapshot figure (V1_tgv_vorticity.pdf).
    Independent of `_run` to avoid contaminating the convergence sweeps.
    Uses a long horizon (SNAPSHOT_T_FINAL) so viscous decay is visible.
    """
    backend = Backend(use_gpu=False)
    N = TIME_N
    _, ccd, ppe, h, X, Y = _setup(N, backend)
    n_steps = max(1, int(np.ceil(SNAPSHOT_T_FINAL / SNAPSHOT_DT)))
    dt = SNAPSHOT_T_FINAL / n_steps
    half_step = n_steps // 2

    u, v = _exact_velocity(0.0, X, Y)
    u = _sync_periodic(u.copy())
    v = _sync_periodic(v.copy())

    omega_t0 = np.asarray(compute_vorticity_2d(u, v, ccd))
    omega_thalf = None
    rhs_prev = None
    for k in range(n_steps):
        rhs_u, rhs_v = _rhs(u, v, ccd, backend)
        if rhs_prev is None:
            u_star = u + dt * rhs_u
            v_star = v + dt * rhs_v
        else:
            rhs_u_prev, rhs_v_prev = rhs_prev
            u_star = u + dt * (1.5 * rhs_u - 0.5 * rhs_u_prev)
            v_star = v + dt * (1.5 * rhs_v - 0.5 * rhs_v_prev)
        u_star = _sync_periodic(u_star)
        v_star = _sync_periodic(v_star)
        u, v = _project(u_star, v_star, dt, ccd, ppe, backend)
        rhs_prev = (rhs_u, rhs_v)
        if k + 1 == half_step:
            omega_thalf = np.asarray(compute_vorticity_2d(u, v, ccd))
    omega_tfinal = np.asarray(compute_vorticity_2d(u, v, ccd))
    if omega_thalf is None:
        omega_thalf = omega_tfinal

    return {
        "x1d": X[:, 0],
        "y1d": Y[0, :],
        "omega_t0": omega_t0,
        "omega_thalf": omega_thalf,
        "omega_tfinal": omega_tfinal,
        "t_half": SNAPSHOT_T_FINAL * (half_step / n_steps),
        "t_final": SNAPSHOT_T_FINAL,
    }


def run_all() -> dict:
    spatial = [_run(N, SPATIAL_DT) for N in SPATIAL_N]
    temporal = [_run(TIME_N, dt) for dt in TIME_DT_TARGETS]
    snapshots = run_V1_snapshots()
    return {
        "spatial": spatial,
        "temporal": temporal,
        "snapshots": snapshots,
        "meta": {"T_final": T_FINAL, "nu": NU, "L": L},
    }


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_s, ax_t = axes
    spatial = results["spatial"]
    temporal = results["temporal"]
    hs = np.array([r["h"] for r in spatial])
    e_sp = np.array([r["u_Linf"] for r in spatial])
    dts = np.array([r["dt"] for r in temporal])
    e_tm = np.array([r["u_Linf"] for r in temporal])
    ax_s.loglog(hs, e_sp, "o-", color="C0", label="CCD/PPE")
    ax_s.invert_xaxis()
    ax_s.set_xlabel("h")
    ax_s.set_ylabel(r"$\|u-u_{\rm exact}\|_\infty$")
    ax_s.set_title("V1: spatial trend")
    ax_s.legend()
    ax_t.loglog(dts, e_tm, "s-", color="C3", label="AB2 + PPE")
    if len(e_tm):
        ax_t.loglog(dts, e_tm[0] * (dts / dts[0]) ** 2, "k--", alpha=0.5, label="O(dt²)")
    ax_t.invert_xaxis()
    ax_t.set_xlabel("dt")
    ax_t.set_ylabel(r"$\|u-u_{\rm exact}\|_\infty$")
    ax_t.set_title("V1: temporal trend")
    ax_t.legend()
    save_figure(
        fig,
        OUT / "V1_tgv_energy",
        also_to=PAPER_FIGURES / "ch13_v1_tgv_energy",
    )


def make_vorticity_figure(results: dict) -> None:
    """1×3 渦度スナップショット (t=0 / T/2 / T_final) — TGV 4 渦対の粘性減衰。"""
    snap = results.get("snapshots")
    if snap is None:
        return
    x1d = np.asarray(snap["x1d"])
    y1d = np.asarray(snap["y1d"])
    omegas = [
        np.asarray(snap["omega_t0"]),
        np.asarray(snap["omega_thalf"]),
        np.asarray(snap["omega_tfinal"]),
    ]
    t_half = float(snap.get("t_half", SNAPSHOT_T_FINAL / 2))
    t_final = float(snap.get("t_final", SNAPSHOT_T_FINAL))
    titles = [
        r"$t = 0$",
        rf"$t = {t_half:.1f}$ ($e^{{-2\nu t}} = {np.exp(-2.0 * NU * t_half):.2f}$)",
        rf"$t = {t_final:.1f}$ ($e^{{-2\nu t}} = {np.exp(-2.0 * NU * t_final):.2f}$)",
    ]
    vmax = symmetric_range(omegas, percentile=99)

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4))
    im = None
    for ax, omega, title in zip(axes, omegas, titles):
        im = field_with_contour(
            ax, x1d, y1d, omega,
            cmap="seismic", vmin=-vmax, vmax=vmax,
            title=title, xlabel="$x$", ylabel="$y$",
        )
    fig.suptitle(r"V1: Taylor--Green vortex — vorticity $\omega = \partial_x v - \partial_y u$", fontsize=12)
    fig.tight_layout(rect=(0, 0, 0.92, 0.95))
    cbar_ax = fig.add_axes([0.93, 0.18, 0.015, 0.66])
    fig.colorbar(im, cax=cbar_ax, label=r"$\omega$")
    save_figure(
        fig,
        OUT / "V1_tgv_vorticity",
        also_to=PAPER_FIGURES / "ch13_v1_tgv_vorticity",
    )


def print_summary(results: dict) -> None:
    print("V1 (TGV with CCD spatial operators + PPE projection):")
    print("  spatial:")
    for row in results["spatial"]:
        print(
            f"    N={row['N']:>3}  h={row['h']:.3e}  "
            f"u_err={row['u_Linf']:.3e}  E_rel={row['E_rel']:.3e}  "
            f"div={row['div_inf_max']:.3e}"
        )
    print("  temporal:")
    dts = np.array([r["dt"] for r in results["temporal"]])
    errs = np.array([r["u_Linf"] for r in results["temporal"]])
    rates = compute_convergence_rates(errs, dts)
    for row, rate in zip(results["temporal"], [None] + list(rates)):
        rate_s = "" if rate is None else f"  slope={rate:.2f}"
        print(
            f"    dt={row['dt']:.3e}  n={row['n_steps']:>3}  "
            f"u_err={row['u_Linf']:.3e}{rate_s}"
        )


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    make_vorticity_figure(results)
    print_summary(results)
    print(f"==> V1 outputs in {OUT}")


if __name__ == "__main__":
    main()
