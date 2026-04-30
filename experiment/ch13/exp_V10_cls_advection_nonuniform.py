#!/usr/bin/env python3
"""[V10] FCCD CLS advection visuals on the uniform grid — Type-B (mass) / Type-D (shape).

Paper ref: §13.5 (sec:zalesak_cls_advection).

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
  Zalesak: N in {64, 128}, alpha_grid = 1.0.
  Single vortex: N = 128, alpha_grid = 1.0, T = 8.0, with no interface
  tracking and fixed uniform-grid Ridge-Eikonal + mass correction every
  10 steps.
  CFL = 0.25 (limited by max |u|).
  Spatial transport: FCCD flux form (same production family as ch14).

Diagnostics at t = T_rev:
  - Centroid L2 displacement error vs initial centroid.
  - Conservative CLS mass drift |∫ψ(T)dV - ∫ψ(0)dV| / ∫ψ(0)dV.
  - Thresholded area drift for the visible {ψ > 0.5} shape.

Pass criteria (FORMAL)
----------------------
  V10-a (Zalesak rotation, alpha=1, N in {64, 128}):
    - mass drift (post Olsson--Kreiss correction) < 0.5%.
      Both N=64 and N=128 satisfy with > 3 orders of margin.
  V10-b (single-vortex reversal, alpha=1, N=128, T=8):
    - mass drift < 0.5% (post Ridge--Eikonal + mass correction).

Reported diagnostics (NO formal threshold; Type-D theoretical limits)
---------------------------------------------------------------------
  V10-a:
    - centroid L2 displacement; centroid order across N=64 -> 128.
      O(h^1.5) reference line is a diagnostic plot guideline ONLY.
      slot/h = 6.4 sharp-corner under-resolution prevents asymptotic
      convergence; classified Type-D hard limit
      (Zalesak 1979; Olsson--Kreiss 2005).
    - shape L1 area drift.
  V10-b:
    - L1 reversal error. T=8 filament-thickness < h sub-grid structure
      cannot be tracked on a fixed Eulerian grid
      (Enright et al. 2002); classified Type-D hard limit.
      Informational only.

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
from twophase.core.grid_remap import build_grid_remapper
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.levelset.fccd_advection import FCCDLevelSetAdvection
from twophase.levelset.heaviside import apply_mass_correction
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
ZALESAK_MASS_CORRECTION_EVERY = 10
SINGLE_VORTEX_N = 128
SINGLE_VORTEX_ALPHA = 1.0
SINGLE_VORTEX_T = 8.0
SINGLE_VORTEX_PHASE_DIVISIONS = 32
SINGLE_VORTEX_REINIT_EVERY = 10
SINGLE_VORTEX_GRID_REBUILD_EVERY = 0
SINGLE_VORTEX_REINIT_METHOD = "ridge_eikonal"
SINGLE_VORTEX_MASS_CORRECTION = True


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


def _mass_reinitialize(psi_h, backend, dV, mass_target: float):
    """Apply CLS mass correction only, without geometric reinitialization."""
    psi_dev = backend.to_device(psi_h)
    out = apply_mass_correction(backend.xp, psi_dev, dV, mass_target)
    return np.asarray(backend.to_host(out))


def _grid_h_min(grid) -> float:
    """Return the minimum nodal spacing over all tensor-product axes."""
    return float(min(np.min(np.asarray(grid.h[axis_index])) for axis_index in range(grid.ndim)))


def _host_mesh(backend, grid) -> tuple[np.ndarray, np.ndarray]:
    """Materialize the active grid mesh on host memory."""
    mesh_x, mesh_y = grid.meshgrid()
    return np.asarray(backend.to_host(mesh_x)), np.asarray(backend.to_host(mesh_y))


def _make_single_vortex_operators(backend, grid, eps: float):
    """Build advection and Ridge-Eikonal operators for the active grid."""
    ccd_solver = CCDSolver(grid, backend, bc_type="wall")
    fccd_solver = FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd_solver)
    levelset_advection = FCCDLevelSetAdvection(
        backend, grid, fccd_solver, mode="flux"
    )
    reinitializer = Reinitializer(
        backend, grid, ccd_solver, eps,
        n_steps=4,
        method=SINGLE_VORTEX_REINIT_METHOD,
        mass_correction=SINGLE_VORTEX_MASS_CORRECTION,
    )
    return ccd_solver, levelset_advection, reinitializer


def _rebuild_single_vortex_grid(psi_h, backend, grid, ccd, eps: float, mass_target: float):
    """Rebuild the interface-fitted grid and remap ψ onto the new coordinates."""
    old_coords = [coords.copy() for coords in grid.coords]
    psi_dev = backend.to_device(psi_h)
    grid.update_from_levelset(psi_dev, eps, ccd=ccd)
    remapper = build_grid_remapper(backend, old_coords, grid.coords)
    psi_remapped = backend.xp.clip(remapper.remap(psi_dev), 0.0, 1.0)
    psi_remapped = apply_mass_correction(
        backend.xp,
        psi_remapped,
        grid.cell_volumes(),
        mass_target,
    )
    return np.asarray(backend.to_host(psi_remapped))


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

    h_min = _grid_h_min(grid)
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

    mass_correction_count = 0
    for step in range(n_steps):
        psi_h = _fccd_advect(psi_h, u, v, ls_adv, backend, dt)
        if (step + 1) % ZALESAK_MASS_CORRECTION_EVERY == 0:
            psi_h = _mass_reinitialize(psi_h, backend, dV_h, mass0)
            mass_correction_count += 1

    mass_T = float(np.sum(psi_h * dV_h))
    area_T, cx_T, cy_T = _measure_centroid_area(psi_h, X_h, Y_h, dV_h)
    cent_err = float(np.sqrt((cx_T - cx0) ** 2 + (cy_T - cy0) ** 2))
    vol_drift = float(abs(mass_T - mass0) / max(mass0, 1e-12))
    area_drift = float(abs(area_T - area0) / max(area0, 1e-12))
    shape_l1 = float(np.sum(np.abs(psi_h - psi0_active) * dV_h)
                     / max(np.sum(dV_h), 1e-12))

    return {
        "N": N, "alpha": alpha, "h_min": h_min, "dt": dt, "n_steps": n_steps,
        "mass_correction_every": ZALESAK_MASS_CORRECTION_EVERY,
        "mass_correction_count": mass_correction_count,
        "V0": mass0, "V_T": mass_T, "area0": area0, "area_T": area_T,
        "cx0": cx0, "cy0": cy0, "cx_T": cx_T, "cy_T": cy_T,
        "centroid_err": cent_err, "volume_drift": vol_drift, "area_drift": area_drift,
        "shape_l1": shape_l1,
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

    h_min = _grid_h_min(grid)
    eps = 1.5 * h_min
    X_h, Y_h = _host_mesh(backend, grid)
    dV_h = np.asarray(backend.to_host(grid.cell_volumes()))
    psi0_h = 1.0 / (1.0 + np.exp(-_circle_phi(X_h, Y_h) / eps))
    psi_h = psi0_h.copy()
    initial_coords = [coords.copy() for coords in grid.coords]
    initial_dV_h = dV_h.copy()
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
    phase_X = [X_h.copy()]
    phase_Y = [Y_h.copy()]

    ccd, ls_adv, reinit = _make_single_vortex_operators(backend, grid, eps)
    t = 0.0
    reinit_count = 0
    grid_rebuild_count = 0
    grid_rebuild_every = SINGLE_VORTEX_GRID_REBUILD_EVERY if alpha > 1.0 else 0
    grid_rebuild_steps = []
    h_min_history = [h_min]
    for step in range(n_steps):
        t_mid = t + 0.5 * dt
        u, v = _single_vortex_velocity(X_h, Y_h, t_mid, SINGLE_VORTEX_T)
        psi_h = _fccd_advect(psi_h, u, v, ls_adv, backend, dt)
        if (step + 1) % SINGLE_VORTEX_REINIT_EVERY == 0:
            psi_h = np.asarray(
                backend.to_host(reinit.reinitialize(backend.to_device(psi_h)))
            )
            reinit_count += 1
        if (
            grid_rebuild_every > 0
            and (step + 1) % grid_rebuild_every == 0
        ):
            psi_h = _rebuild_single_vortex_grid(psi_h, backend, grid, ccd, eps, V0)
            ccd, ls_adv, reinit = _make_single_vortex_operators(backend, grid, eps)
            X_h, Y_h = _host_mesh(backend, grid)
            dV_h = np.asarray(backend.to_host(grid.cell_volumes()))
            grid_rebuild_count += 1
            grid_rebuild_steps.append(step + 1)
            h_min_history.append(_grid_h_min(grid))
        t += dt
        if (step + 1) % steps_per_snapshot == 0:
            phase_psi.append(psi_h.copy())
            phase_X.append(X_h.copy())
            phase_Y.append(Y_h.copy())
    phase_psi_h = np.stack(phase_psi, axis=0)
    phase_X_h = np.stack(phase_X, axis=0)
    phase_Y_h = np.stack(phase_Y, axis=0)
    psi_half = phase_psi_h[SINGLE_VORTEX_PHASE_DIVISIONS // 2]

    if grid_rebuild_count > 0:
        to_initial = build_grid_remapper(
            backend,
            [coords.copy() for coords in grid.coords],
            initial_coords,
        )
        psi_T_on_initial = np.asarray(
            backend.to_host(
                backend.xp.clip(to_initial.remap(backend.to_device(psi_h)), 0.0, 1.0)
            )
        )
    else:
        psi_T_on_initial = psi_h.copy()

    V_T = float(np.sum(psi_h * dV_h))
    area_T = float(np.sum((psi_h > 0.5) * dV_h))
    volume_drift = float(abs(V_T - V0) / max(V0, 1e-12))
    area_drift = float(abs(area_T - area0) / max(area0, 1e-12))
    reversal_l1 = float(
        np.sum(np.abs(psi_T_on_initial - psi0_h) * initial_dV_h)
        / max(np.sum(initial_dV_h), 1e-12)
    )

    return {
        "N": N, "alpha": alpha, "h_min": h_min, "dt": dt, "n_steps": n_steps,
        "reinit_every": SINGLE_VORTEX_REINIT_EVERY,
        "reinit_count": reinit_count,
        "reinit_method": SINGLE_VORTEX_REINIT_METHOD,
        "mass_correction": SINGLE_VORTEX_MASS_CORRECTION,
        "grid_rebuild_every": grid_rebuild_every,
        "grid_rebuild_count": grid_rebuild_count,
        "grid_rebuild_steps": np.asarray(grid_rebuild_steps, dtype=int),
        "grid_h_min_history": np.asarray(h_min_history, dtype=float),
        "V0": V0, "V_T": V_T, "area0": area0, "area_T": area_T,
        "volume_drift": volume_drift, "area_drift": area_drift, "reversal_l1": reversal_l1,
        "X": X_h, "Y": Y_h, "psi0": psi0_h, "psi_half": psi_half, "psi_T": psi_h,
        "phase_divisions": SINGLE_VORTEX_PHASE_DIVISIONS,
        "phase_fractions": phase_fractions, "phase_times": phase_times,
        "phase_psi": phase_psi_h, "phase_X": phase_X_h, "phase_Y": phase_Y_h,
    }


def run_all() -> dict:
    zalesak = [_run(N, alpha=1.0) for N in (64, 128)]
    single_vortex = _run_single_vortex()
    return {"zalesak": zalesak, "runs": zalesak, "single_vortex": single_vortex}


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_c, ax_v = axes
    rows_a1 = results.get("zalesak")
    if rows_a1 is None:
        rows_a1 = results.get("runs_a1", results.get("runs", []))

    if rows_a1 is not None and len(rows_a1):
        Ns = np.array([r["N"] for r in rows_a1])
        cents = np.array([r["centroid_err"] for r in rows_a1])
        ax_c.loglog(1.0 / Ns, cents, "o-", color="C0", label="α=1 (uniform)")

    Ns_ref = np.array([64, 128])
    if len(rows_a1):
        c0 = rows_a1[0]["centroid_err"]
        ax_c.loglog(1.0 / Ns_ref, c0 * (Ns_ref[0] / Ns_ref) ** 1.5,
                    "k--", alpha=0.5, label="O(h^{1.5})")
    ax_c.invert_xaxis(); ax_c.set_xlabel("h ~ 1/N"); ax_c.set_ylabel("centroid L2 error")
    ax_c.set_title("V10: Zalesak rotation centroid"); ax_c.legend(fontsize=8)

    cats = []; vals = []; bar_colors = []
    for r in rows_a1:
        cats.append(f"N={r['N']}")
        vals.append(r["volume_drift"])
        bar_colors.append("C0")
    ax_v.bar(cats, vals, color=bar_colors)
    ax_v.set_ylabel("mass drift  |ΔV|/V0")
    ax_v.set_yscale("log"); ax_v.axhline(5e-3, color="k", linestyle="--", alpha=0.6,
                                          label="pass: 0.5% mass drift")
    ax_v.set_title("V10-a: mass drift (Olsson--Kreiss corr.)"); ax_v.legend(fontsize=8)

    save_figure(fig, OUT / "V10_zalesak_uniform",
                also_to=PAPER_FIGURES / "ch13_v10_zalesak")

    row_a1_128 = next(r for r in rows_a1 if r["N"] == 128)
    fig_snap, axes_snap = plt.subplots(1, 3, figsize=(12, 4))
    panels = (
        (row_a1_128["psi0"], "initial", "viridis"),
        (row_a1_128["psi_T"], "α=1 final", "viridis"),
        (np.abs(row_a1_128["psi_T"] - row_a1_128["psi0"]), "|final - initial|", "magma"),
    )
    for ax, (psi, title, cmap) in zip(axes_snap, panels):
        im = ax.pcolormesh(row_a1_128["X"], row_a1_128["Y"], psi, cmap=cmap,
                           vmin=0.0, vmax=1.0, shading="auto")
        if title != "|final - initial|":
            ax.contour(row_a1_128["X"], row_a1_128["Y"], psi, levels=[0.5],
                       colors="white", linewidths=1.0)
        ax.set_aspect("equal"); ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_title(title)
    fig_snap.colorbar(im, ax=axes_snap.ravel().tolist(), shrink=0.82, label="value")
    fig_snap.suptitle("V10: Zalesak slotted disk snapshots (N=128)")
    save_figure(fig_snap, OUT / "V10_zalesak_snapshots",
                also_to=PAPER_FIGURES / "ch13_v10_zalesak_snapshot")

    sv = results["single_vortex"]
    phase_divisions = int(sv.get("phase_divisions", SINGLE_VORTEX_PHASE_DIVISIONS))
    phase_X = np.asarray(sv.get("phase_X", []))
    phase_Y = np.asarray(sv.get("phase_Y", []))
    fig_sv, axes_sv = plt.subplots(1, 3, figsize=(12, 4))
    snapshot_indices = (0, phase_divisions // 2, phase_divisions)
    for ax, psi, title, snap_idx in zip(
        axes_sv,
        (sv["psi0"], sv["psi_half"], sv["psi_T"]),
        ("initial", "max deformation", "reversed final"),
        snapshot_indices,
    ):
        mesh_x, mesh_y = sv["X"], sv["Y"]
        if phase_X.ndim == 3 and phase_Y.ndim == 3:
            mesh_x, mesh_y = phase_X[snap_idx], phase_Y[snap_idx]
        im = ax.pcolormesh(mesh_x, mesh_y, psi, cmap="magma",
                           vmin=0.0, vmax=1.0, shading="auto")
        ax.contour(mesh_x, mesh_y, psi, levels=[0.5], colors="white", linewidths=1.0)
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
        ncols = 9
        nrows = int(np.ceil(len(phase_fractions) / ncols))
        fig_phase, axes_phase = plt.subplots(nrows, ncols, figsize=(2.0 * ncols, 1.85 * nrows),
                                             sharex=True, sharey=True)
        axes_flat = np.asarray(axes_phase).ravel()
        for idx, ax in enumerate(axes_flat):
            if idx >= len(phase_fractions):
                ax.axis("off")
                continue
            mesh_x, mesh_y = sv["X"], sv["Y"]
            if phase_X.ndim == 3 and phase_Y.ndim == 3:
                mesh_x, mesh_y = phase_X[idx], phase_Y[idx]
            im = ax.pcolormesh(mesh_x, mesh_y, phase_psi[idx], cmap="magma",
                               vmin=0.0, vmax=1.0, shading="auto")
            ax.contour(mesh_x, mesh_y, phase_psi[idx], levels=[0.5],
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
    rows = results.get("zalesak")
    if rows is None:
        rows = results.get("runs_a1", results.get("runs", []))
    if rows is not None and len(rows):
        print("V10 (Zalesak slotted disk, α=1 uniform, 1 revolution):")
        for r in rows:
            print(f"  N={r['N']:>3}  cent_err={r['centroid_err']:.3e}  "
                  f"vol_drift={r['volume_drift']:.3e}  V_T/V0={r['V_T']/max(r['V0'],1e-12):.4f}")
        if len(rows) >= 2:
            Ns = np.array([r["N"] for r in rows])
            cents = np.array([r["centroid_err"] for r in rows])
            if all(cents > 0):
                slope = np.log(cents[1] / cents[0]) / np.log(Ns[0] / Ns[1])
                print(f"  → centroid order ≈ {slope:.2f}  (sharp-slot diagnostic)")
    sv = results["single_vortex"]
    print("V10 (single-vortex deformation reversal, FCCD/TVD-RK3):")
    print(f"  N={sv['N']:>3}  α={sv['alpha']:.0f}  L1_reverse={sv['reversal_l1']:.3e}  "
          f"vol_drift={sv['volume_drift']:.3e}  V_T/V0={sv['V_T']/max(sv['V0'],1e-12):.4f}")
    print(f"  reinit={sv.get('reinit_method', 'none')} every {int(sv.get('reinit_every', 0))} "
          f"steps ({int(sv.get('reinit_count', 0))} calls)")
    print(f"  mass_correction={bool(sv.get('mass_correction', False))} every "
          f"{int(sv.get('reinit_every', 0))} steps")
    print(f"  grid_rebuild every {int(sv.get('grid_rebuild_every', 0))} "
          f"steps ({int(sv.get('grid_rebuild_count', 0))} calls)")


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
