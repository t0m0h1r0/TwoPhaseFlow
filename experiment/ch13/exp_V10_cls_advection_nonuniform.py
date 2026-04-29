#!/usr/bin/env python3
"""[V10] FCCD CLS advection visuals on uniform / non-uniform grids — Tier D.

Paper ref: §13.5 (sec:nonuniform_grid_ns contributor).

Verifies the ch14 production interface-transport choice,
FCCD flux-form ψ advection + TVD-RK3, on two visually diagnostic CLS tests:
Zalesak slotted-disk rigid rotation and a reversible single-vortex
deformation cycle.

Setup
-----
  Domain [0,1]^2, periodic BC (rotation closes on itself).
  Slotted disk: center (0.5, 0.75), radius 0.15, slot width 0.05,
  slot length 0.25.
  Velocity (solid-body rotation about (0.5, 0.5)):
    u(x,y) = -(2*pi/T_rev) * (y - 0.5),
    v(x,y) =  (2*pi/T_rev) * (x - 0.5).
  T_rev = 1.0 (one full revolution).
  Zalesak: N in {64, 128}, alpha_grid in {1.0, 2.0}.
  Single vortex: N = 96, alpha_grid = 2.0, T = 8.0.
  CFL = 0.25 (limited by max |u|).
  Spatial transport: FCCD flux form (same production family as ch14).

Diagnostics at t = T_rev:
  - Centroid L2 displacement error vs initial centroid.
  - Conservative CLS mass drift |∫ψ(T)dV - ∫ψ(0)dV| / ∫ψ(0)dV.
  - Thresholded area drift for the visible {ψ > 0.5} shape.

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
from twophase.ccd.fccd import FCCDSolver
from twophase.levelset.fccd_advection import FCCDLevelSetAdvection
from twophase.levelset.reinitialize import Reinitializer
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIGURES = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"

T_REV = 1.0
DISK_R = 0.15
DISK_CENTER = (0.5, 0.75)
SLOT_WIDTH = 0.05
SLOT_LENGTH = 0.25
SINGLE_VORTEX_N = 96
SINGLE_VORTEX_ALPHA = 2.0
SINGLE_VORTEX_T = 8.0
SINGLE_VORTEX_PHASE_DIVISIONS = 32
SINGLE_VORTEX_REINIT_EVERY = 10
SINGLE_VORTEX_REINIT_METHOD = "ridge_eikonal"


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


def _circle_phi(X, Y, center=(0.5, 0.75), radius=0.15) -> np.ndarray:
    """Signed-distance-like phi for the single-vortex reversible disk."""
    return radius - np.sqrt((X - center[0]) ** 2 + (Y - center[1]) ** 2)


def _single_vortex_velocity(X, Y, t: float, T: float) -> tuple[np.ndarray, np.ndarray]:
    """LeVeque/Enright single-vortex deformation field with reversal at t=T."""
    amp = np.cos(np.pi * t / T)
    u = np.sin(np.pi * X) ** 2 * np.sin(2.0 * np.pi * Y) * amp
    v = -np.sin(np.pi * Y) ** 2 * np.sin(2.0 * np.pi * X) * amp
    return u, v


def _fccd_advect(psi_h, u, v, ls_adv, backend, dt):
    """FCCD flux-form + TVD-RK3 ψ advection."""
    psi_dev = backend.to_device(psi_h)
    u_dev = backend.to_device(u)
    v_dev = backend.to_device(v)
    out = ls_adv.advance(psi_dev, [u_dev, v_dev], dt, clip_bounds=(1e-12, 1.0 - 1e-12))
    return np.asarray(backend.to_host(out))


def _measure_centroid_area(psi_h, X_h, Y_h, dV_h):
    """Compute thresholded area and centroid of {psi > 0.5}."""
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
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)

    h_min = float(min(np.min(np.asarray(grid.h[ax])) for ax in range(2)))
    eps = 1.5 * h_min
    omega = 2.0 * np.pi / T_REV
    u_max = omega * 0.5 * np.sqrt(2.0)  # max |u| at corners
    dt_est = 0.25 * h_min / max(u_max, 1e-3)
    n_steps = int(np.ceil(T_REV / dt_est))
    dt = T_REV / n_steps

    X, Y = grid.meshgrid()
    X_h = np.asarray(backend.to_host(X))
    Y_h = np.asarray(backend.to_host(Y))
    dV_h = np.asarray(backend.to_host(grid.cell_volumes()))

    phi_h = _slotted_disk_phi(X_h, Y_h)
    psi_h = 1.0 / (1.0 + np.exp(-phi_h / eps))  # H_eps for transport mass
    psi0_active = psi_h.copy()
    mass0 = float(np.sum(psi0_active * dV_h))
    area0, cx0, cy0 = _measure_centroid_area(psi_h, X_h, Y_h, dV_h)

    u = -omega * (Y_h - 0.5)
    v = omega * (X_h - 0.5)

    ls_adv = FCCDLevelSetAdvection(backend, grid, fccd, mode="flux")

    for step in range(n_steps):
        psi_h = _fccd_advect(psi_h, u, v, ls_adv, backend, dt)

    mass_T = float(np.sum(psi_h * dV_h))
    area_T, cx_T, cy_T = _measure_centroid_area(psi_h, X_h, Y_h, dV_h)
    cent_err = float(np.sqrt((cx_T - cx0) ** 2 + (cy_T - cy0) ** 2))
    vol_drift = float(abs(mass_T - mass0) / max(mass0, 1e-12))
    area_drift = float(abs(area_T - area0) / max(area0, 1e-12))

    return {
        "N": N, "alpha": alpha, "h_min": h_min, "dt": dt, "n_steps": n_steps,
        "V0": mass0, "V_T": mass_T, "area0": area0, "area_T": area_T,
        "cx0": cx0, "cy0": cy0, "cx_T": cx_T, "cy_T": cy_T,
        "centroid_err": cent_err, "volume_drift": vol_drift, "area_drift": area_drift,
        "X": X_h, "Y": Y_h, "psi0": psi0_active, "psi_T": psi_h,
    }


def _run_single_vortex(N: int = SINGLE_VORTEX_N, alpha: float = SINGLE_VORTEX_ALPHA) -> dict:
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0),
                                            alpha_grid=alpha))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    h_uniform = 1.0 / N
    eps_init = 1.5 * h_uniform
    X0, Y0 = grid.meshgrid()
    X0_h = np.asarray(backend.to_host(X0))
    Y0_h = np.asarray(backend.to_host(Y0))
    psi_seed = 1.0 / (1.0 + np.exp(-_circle_phi(X0_h, Y0_h) / eps_init))
    if alpha > 1.0:
        grid.update_from_levelset(backend.to_device(psi_seed), eps_init, ccd=ccd)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    fccd = FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd)

    h_min = float(min(np.min(np.asarray(grid.h[ax])) for ax in range(2)))
    eps = 1.5 * h_min
    X, Y = grid.meshgrid()
    X_h = np.asarray(backend.to_host(X))
    Y_h = np.asarray(backend.to_host(Y))
    dV_h = np.asarray(backend.to_host(grid.cell_volumes()))
    psi0_h = 1.0 / (1.0 + np.exp(-_circle_phi(X_h, Y_h) / eps))
    psi_h = psi0_h.copy()
    V0 = float(np.sum(psi0_h * dV_h))
    area0 = float(np.sum((psi0_h > 0.5) * dV_h))

    u0, v0 = _single_vortex_velocity(X_h, Y_h, 0.0, SINGLE_VORTEX_T)
    max_speed = float(np.max(np.sqrt(u0 * u0 + v0 * v0)))
    dt_est = 0.25 * h_min / max(max_speed, 1e-3)
    n_steps = int(np.ceil(SINGLE_VORTEX_T / dt_est))
    n_steps = int(
        np.ceil(n_steps / SINGLE_VORTEX_PHASE_DIVISIONS) * SINGLE_VORTEX_PHASE_DIVISIONS
    )
    dt = SINGLE_VORTEX_T / n_steps
    steps_per_snapshot = n_steps // SINGLE_VORTEX_PHASE_DIVISIONS
    phase_fractions = np.linspace(0.0, 1.0, SINGLE_VORTEX_PHASE_DIVISIONS + 1)
    phase_times = SINGLE_VORTEX_T * phase_fractions
    phase_psi = [psi_h.copy()]

    ls_adv = FCCDLevelSetAdvection(backend, grid, fccd, mode="flux")
    reinit = Reinitializer(
        backend, grid, ccd, eps,
        n_steps=4,
        method=SINGLE_VORTEX_REINIT_METHOD,
        mass_correction=True,
    )
    t = 0.0
    reinit_count = 0
    for step in range(n_steps):
        t_mid = t + 0.5 * dt
        u, v = _single_vortex_velocity(X_h, Y_h, t_mid, SINGLE_VORTEX_T)
        psi_h = _fccd_advect(psi_h, u, v, ls_adv, backend, dt)
        if (step + 1) % SINGLE_VORTEX_REINIT_EVERY == 0:
            psi_h = np.asarray(backend.to_host(reinit.reinitialize(backend.to_device(psi_h))))
            reinit_count += 1
        t += dt
        if (step + 1) % steps_per_snapshot == 0:
            phase_psi.append(psi_h.copy())
    phase_psi_h = np.stack(phase_psi, axis=0)
    psi_half = phase_psi_h[SINGLE_VORTEX_PHASE_DIVISIONS // 2]

    V_T = float(np.sum(psi_h * dV_h))
    area_T = float(np.sum((psi_h > 0.5) * dV_h))
    volume_drift = float(abs(V_T - V0) / max(V0, 1e-12))
    area_drift = float(abs(area_T - area0) / max(area0, 1e-12))
    reversal_l1 = float(np.sum(np.abs(psi_h - psi0_h) * dV_h) / max(np.sum(dV_h), 1e-12))

    return {
        "N": N, "alpha": alpha, "h_min": h_min, "dt": dt, "n_steps": n_steps,
        "reinit_every": SINGLE_VORTEX_REINIT_EVERY,
        "reinit_count": reinit_count,
        "reinit_method": SINGLE_VORTEX_REINIT_METHOD,
        "V0": V0, "V_T": V_T, "area0": area0, "area_T": area_T,
        "volume_drift": volume_drift, "area_drift": area_drift, "reversal_l1": reversal_l1,
        "X": X_h, "Y": Y_h, "psi0": psi0_h, "psi_half": psi_half, "psi_T": psi_h,
        "phase_divisions": SINGLE_VORTEX_PHASE_DIVISIONS,
        "phase_fractions": phase_fractions, "phase_times": phase_times, "phase_psi": phase_psi_h,
    }


def run_all() -> dict:
    rows_a2 = [_run(N, alpha=2.0) for N in (64, 128)]
    rows_a1 = [_run(N, alpha=1.0) for N in (64, 128)]
    single_vortex = _run_single_vortex()
    return {"runs": rows_a2, "runs_a1": rows_a1, "single_vortex": single_vortex}


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

    save_figure(fig, OUT / "V10_zalesak_nonuniform",
                also_to=PAPER_FIGURES / "ch13_v10_zalesak")

    row_a1_128 = next(r for r in rows_a1 if r["N"] == 128)
    row_a2_128 = next(r for r in rows_a2 if r["N"] == 128)
    fig_snap, axes_snap = plt.subplots(1, 3, figsize=(12, 4))
    panels = (
        (row_a1_128, row_a1_128["psi0"], "initial"),
        (row_a1_128, row_a1_128["psi_T"], "α=1 final"),
        (row_a2_128, row_a2_128["psi_T"], "α=2 final"),
    )
    for ax, (row, psi, title) in zip(axes_snap, panels):
        im = ax.pcolormesh(row["X"], row["Y"], psi, cmap="viridis",
                           vmin=0.0, vmax=1.0, shading="auto")
        ax.contour(row["X"], row["Y"], psi, levels=[0.5], colors="white", linewidths=1.0)
        ax.set_aspect("equal"); ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_title(title)
    fig_snap.colorbar(im, ax=axes_snap.ravel().tolist(), shrink=0.82, label="$\\psi$")
    fig_snap.suptitle("V10: Zalesak slotted disk snapshots (N=128)")
    save_figure(fig_snap, OUT / "V10_zalesak_snapshots",
                also_to=PAPER_FIGURES / "ch13_v10_zalesak_snapshot")

    sv = results["single_vortex"]
    fig_sv, axes_sv = plt.subplots(1, 3, figsize=(12, 4))
    for ax, psi, title in zip(
        axes_sv,
        (sv["psi0"], sv["psi_half"], sv["psi_T"]),
        ("initial", "max deformation", "reversed final"),
    ):
        im = ax.pcolormesh(sv["X"], sv["Y"], psi, cmap="magma",
                           vmin=0.0, vmax=1.0, shading="auto")
        ax.contour(sv["X"], sv["Y"], psi, levels=[0.5], colors="white", linewidths=1.0)
        ax.set_aspect("equal"); ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_title(title)
    fig_sv.colorbar(im, ax=axes_sv.ravel().tolist(), shrink=0.82, label="$\\psi$")
    fig_sv.suptitle(
        f"V10: single-vortex deformation (N={sv['N']}, α={sv['alpha']:.0f}, "
        f"{sv.get('reinit_method', 'no-reinit')}, L1={sv['reversal_l1']:.2e})"
    )
    save_figure(fig_sv, OUT / "V10_single_vortex_snapshots",
                also_to=PAPER_FIGURES / "ch13_v10_single_vortex")

    if "phase_psi" in sv:
        phase_psi = np.asarray(sv["phase_psi"])
        phase_fractions = np.asarray(sv["phase_fractions"])
        phase_divisions = int(sv.get("phase_divisions", SINGLE_VORTEX_PHASE_DIVISIONS))
        ncols = 9
        nrows = int(np.ceil(len(phase_fractions) / ncols))
        fig_phase, axes_phase = plt.subplots(nrows, ncols, figsize=(2.0 * ncols, 1.85 * nrows),
                                             sharex=True, sharey=True)
        axes_flat = np.asarray(axes_phase).ravel()
        for idx, ax in enumerate(axes_flat):
            if idx >= len(phase_fractions):
                ax.axis("off")
                continue
            im = ax.pcolormesh(sv["X"], sv["Y"], phase_psi[idx], cmap="magma",
                               vmin=0.0, vmax=1.0, shading="auto")
            ax.contour(sv["X"], sv["Y"], phase_psi[idx], levels=[0.5],
                       colors="white", linewidths=0.7)
            numerator = int(round(float(phase_fractions[idx]) * phase_divisions))
            ax.set_title(f"t/T={numerator}/{phase_divisions}", fontsize=8)
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
        fig_phase.colorbar(im, ax=axes_flat.tolist(), shrink=0.82, label="$\\psi$")
        fig_phase.suptitle(
            f"V10: single-vortex deformation over one cycle "
            f"(N={sv['N']}, alpha={sv['alpha']:.0f}, "
            f"{sv.get('reinit_method', 'no-reinit')} every {int(sv.get('reinit_every', 0))})"
        )
        save_figure(fig_phase, OUT / "V10_single_vortex_phase32",
                    also_to=PAPER_FIGURES / "ch13_v10_single_vortex_phase32")


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
    sv = results["single_vortex"]
    print("V10 (single-vortex deformation reversal, FCCD/TVD-RK3):")
    print(f"  N={sv['N']:>3}  α={sv['alpha']:.0f}  L1_reverse={sv['reversal_l1']:.3e}  "
          f"vol_drift={sv['volume_drift']:.3e}  V_T/V0={sv['V_T']/max(sv['V0'],1e-12):.4f}")
    print(f"  reinit={sv.get('reinit_method', 'none')} every {int(sv.get('reinit_every', 0))} "
          f"steps ({int(sv.get('reinit_count', 0))} calls)")


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
