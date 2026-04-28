#!/usr/bin/env python3
"""[V10] Zalesak slotted-disk on non-uniform grid (alpha=2) — Tier D.

Paper ref: §13.5 (sec:nonuniform_grid_ns contributor).

Verifies CLS-psi solid-body rotation accuracy on a non-uniform
interface-fitted grid (alpha_grid=2.0). The standard Zalesak slotted disk
in solid-body rotation through one full revolution stresses CLS advection,
periodic interface crossing, and the non-uniform Ridge-Eikonal
reinitialization simultaneously.

Setup
-----
  Domain [0,1]^2, periodic BC (rotation closes on itself).
  Slotted disk: center (0.5, 0.75), radius 0.15, slot width 0.05,
  slot length 0.25.
  Velocity (solid-body rotation about (0.5, 0.5)):
    u(x,y) = -(2*pi/T_rev) * (y - 0.5),
    v(x,y) =  (2*pi/T_rev) * (x - 0.5).
  T_rev = 1.0 (one full revolution).
  N in {64, 128}, alpha_grid = 2.0.
  CFL = 0.25 (limited by max |u|).
  Reinitialize every 10 advection steps (Ridge-Eikonal, non-uniform).

Diagnostics at t = T_rev:
  - Centroid L2 displacement error vs initial centroid.
  - Volume drift |V(T) - V(0)| / V(0).

Pass criterion
--------------
  - Centroid order >= 1.5 across N=64 -> 128.
  - Volume drift < 5e-3 at N=128.

Usage
-----
  python experiment/ch13/exp_V10_cls_advection_nonuniform.py
  python experiment/ch13/exp_V10_cls_advection_nonuniform.py --plot-only
"""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.advection_weno import LevelSetAdvection as WenoLS
from twophase.levelset.ridge_eikonal import RidgeEikonalReinitializer
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    compute_convergence_rates,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

T_REV = 1.0
DISK_R = 0.15
DISK_CENTER = (0.5, 0.75)
SLOT_WIDTH = 0.05
SLOT_LENGTH = 0.25
REINIT_EVERY = 10


def _slotted_disk_phi(X, Y) -> np.ndarray:
    """Signed-distance-like phi: phi > 0 inside disk minus slot."""
    cx, cy = DISK_CENTER
    rho = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    # Disk: inside = R - rho > 0
    in_disk = DISK_R - rho
    # Slot: rectangle x in [cx-w/2, cx+w/2], y in [cy-R, cy-R+slot_len]
    sx = np.abs(X - cx) - SLOT_WIDTH / 2.0  # >0 outside slot in x
    sy_lo = (cy - DISK_R) - Y               # >0 below slot
    sy_hi = Y - (cy - DISK_R + SLOT_LENGTH)  # >0 above slot
    # In-slot when sx<0 and sy_lo<0 and sy_hi<0
    in_slot = np.maximum(np.maximum(sx, sy_lo), sy_hi)  # >0 outside slot
    # phi = min(in_disk, in_slot) so >0 only when in_disk>0 AND in_slot>0
    return np.minimum(in_disk, in_slot)


def _ccd_grad(field, ccd, axis, backend):
    d1, _ = ccd.differentiate(field, axis)
    return np.asarray(backend.to_host(d1))


def _weno_advect(psi_h, u, v, ls_adv, backend, dt):
    """WENO5 + TVD-RK3 advection (high-order CLS update)."""
    psi_dev = backend.to_device(psi_h)
    u_dev = backend.to_device(u)
    v_dev = backend.to_device(v)
    out = ls_adv.advance(psi_dev, [u_dev, v_dev], dt, clip_bounds=(1e-12, 1.0 - 1e-12))
    return np.asarray(backend.to_host(out))


def _measure_centroid_volume(psi_h, X_h, Y_h, dV_h):
    """Compute volume and centroid of {psi > 0.5} (CLS H_eps level set)."""
    chi = (psi_h > 0.5).astype(float)
    V = float(np.sum(chi * dV_h))
    if V <= 0:
        return float("nan"), float("nan"), float("nan")
    cx = float(np.sum(X_h * chi * dV_h) / V)
    cy = float(np.sum(Y_h * chi * dV_h) / V)
    return V, cx, cy


def _run(N: int, alpha: float, n_steps: int = 200) -> dict:
    backend = Backend(use_gpu=False)
    xp = backend.xp
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0),
                                            alpha_grid=alpha))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    h_uniform = 1.0 / N
    eps_init = 1.5 * h_uniform
    X0, Y0 = grid.meshgrid()
    X0_h = np.asarray(backend.to_host(X0))
    Y0_h = np.asarray(backend.to_host(Y0))
    phi0_h = _slotted_disk_phi(X0_h, Y0_h)
    psi0_h = 1.0 / (1.0 + np.exp(-phi0_h / eps_init))
    if alpha > 1.0:
        grid.update_from_levelset(backend.to_device(psi0_h), eps_init, ccd=ccd)

    h_min = float(min(np.min(np.asarray(grid.h[ax])) for ax in range(2)))
    eps = 1.5 * h_min
    omega = 2.0 * np.pi / T_REV
    u_max = omega * 0.5 * np.sqrt(2.0)  # max |u| at corners
    dt = 0.25 * h_min / max(u_max, 1e-3)
    n_steps = int(np.ceil(T_REV / dt)) + 1

    X, Y = grid.meshgrid()
    X_h = np.asarray(backend.to_host(X))
    Y_h = np.asarray(backend.to_host(Y))
    dV_h = np.asarray(backend.to_host(grid.cell_volumes()))

    phi_h = _slotted_disk_phi(X_h, Y_h)
    psi_h = 1.0 / (1.0 + np.exp(-phi_h / eps))  # H_eps for transport mass
    V0, cx0, cy0 = _measure_centroid_volume(psi_h, X_h, Y_h, dV_h)

    u = -omega * (Y_h - 0.5)
    v = omega * (X_h - 0.5)

    ls_adv = WenoLS(backend, grid, bc="periodic")

    for step in range(n_steps):
        psi_h = _weno_advect(psi_h, u, v, ls_adv, backend, dt)

    V_T, cx_T, cy_T = _measure_centroid_volume(psi_h, X_h, Y_h, dV_h)
    cent_err = float(np.sqrt((cx_T - cx0) ** 2 + (cy_T - cy0) ** 2))
    vol_drift = float(abs(V_T - V0) / max(V0, 1e-12))

    return {
        "N": N, "alpha": alpha, "h_min": h_min, "dt": dt, "n_steps": n_steps,
        "V0": V0, "V_T": V_T, "cx0": cx0, "cy0": cy0, "cx_T": cx_T, "cy_T": cy_T,
        "centroid_err": cent_err, "volume_drift": vol_drift,
    }


def run_all() -> dict:
    rows_a2 = [_run(N, alpha=2.0) for N in (64, 128)]
    rows_a1 = [_run(N, alpha=1.0) for N in (64, 128)]
    return {"runs": rows_a2, "runs_a1": rows_a1}


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_c, ax_v = axes
    rows_a2 = results["runs"]
    rows_a1 = results.get("runs_a1", [])

    for rows, color, lbl in ((rows_a1, "C0", "α=1 (uniform)"),
                              (rows_a2, "C3", "α=2 (non-uniform)")):
        if rows is None or len(rows) == 0: continue
        Ns = np.array([r["N"] for r in rows])
        cents = np.array([r["centroid_err"] for r in rows])
        ax_c.loglog(1.0 / Ns, cents, "o-", color=color, label=lbl)

    Ns_ref = np.array([64, 128])
    if len(rows_a1):
        c0 = rows_a1[0]["centroid_err"]
        ax_c.loglog(1.0 / Ns_ref, c0 * (Ns_ref[0] / Ns_ref) ** 1.5,
                    "k--", alpha=0.5, label="O(h^{1.5})")
    ax_c.invert_xaxis(); ax_c.set_xlabel("h ~ 1/N"); ax_c.set_ylabel("centroid L2 error")
    ax_c.set_title("V10: Zalesak rotation centroid"); ax_c.legend(fontsize=8)

    cats = []; vals = []; bar_colors = []
    for rows, color, prefix in ((rows_a1, "C0", "α1"), (rows_a2, "C3", "α2")):
        for r in rows:
            cats.append(f"{prefix}\nN{r['N']}")
            vals.append(r["volume_drift"])
            bar_colors.append(color)
    ax_v.bar(cats, vals, color=bar_colors)
    ax_v.set_ylabel("|ΔV|/V0")
    ax_v.set_yscale("log"); ax_v.axhline(5e-3, color="k", linestyle="--", alpha=0.6,
                                          label="pass: 5e-3")
    ax_v.set_title("V10: volume drift after 1 rev"); ax_v.legend(fontsize=8)

    save_figure(fig, OUT / "V10_zalesak_nonuniform")


def print_summary(results: dict) -> None:
    for tag, key in (("α=2", "runs"), ("α=1", "runs_a1")):
        rows = results.get(key, [])
        if rows is None or len(rows) == 0: continue
        print(f"V10 (Zalesak slotted disk, {tag}, 1 revolution):")
        for r in rows:
            print(f"  N={r['N']:>3}  cent_err={r['centroid_err']:.3e}  "
                  f"vol_drift={r['volume_drift']:.3e}  V_T/V0={r['V_T']/max(r['V0'],1e-12):.4f}")
        if len(rows) >= 2:
            Ns = np.array([r["N"] for r in rows])
            cents = np.array([r["centroid_err"] for r in rows])
            if all(cents > 0):
                slope = np.log(cents[1] / cents[0]) / np.log(Ns[0] / Ns[1])
                print(f"  → centroid order ≈ {slope:.2f}  (target ≥ 1.5)")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V10 outputs in {OUT}")


if __name__ == "__main__":
    main()
