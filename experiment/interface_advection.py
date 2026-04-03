"""
Interface Advection Benchmark: Zalesak Disk + Single Vortex
============================================================
Two standard interface-tracking benchmark tests.  Both use only the
CLS/DCCD advection module — no NS pressure or velocity coupling.

Test A — Zalesak Slotted Disk (solid-body rotation)
    Slotted disk rotated one full revolution (T=1) in a prescribed
    rigid-body rotation field.  Shape and volume conservation measured.

Test B — Single Vortex (LeVeque 1996 / Rider–Kothe 1995)
    Circular patch stretched by a time-reversing vortex field.
    Interface returns to initial position at T=1; shape and volume
    errors quantify the method's ability to preserve interface integrity.

Both tests use DissipativeCCDAdvection (DCCD) with TVD-RK3.
Reference: Rider & Kothe (1998), Zalesak (1979), LeVeque (1996).
"""

from __future__ import annotations

import os
import sys
import numpy as np
from scipy.ndimage import distance_transform_edt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.heaviside import heaviside

# ── Parameters ────────────────────────────────────────────────────────────────

N_TEST   = 128       # primary grid resolution for figures
N_CONV   = [64, 128] # grid sizes for convergence table (64 is slow for 256 but ok)
T_END    = 1.0
CFL          = 0.45

# Zalesak disk (standard setup, Rider & Kothe 1998)
ZAL_CX, ZAL_CY = 0.5, 0.75
ZAL_R          = 0.15
ZAL_SLOT_W     = 0.05   # slot width
ZAL_SLOT_H     = 0.25   # slot height (from y = cy − R upward)

# Single Vortex circle
SV_CX, SV_CY  = 0.5, 0.75
SV_R           = 0.15

SNAP_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "ch10_cls_advection")


def _save_snapshot(name, N, X, Y, psi0, psi_T):
    """Save ψ fields for plot-only regeneration."""
    os.makedirs(SNAP_DIR, exist_ok=True)
    np.savez(os.path.join(SNAP_DIR, f"{name}_N{N}_snapshot.npz"),
             X=X, Y=Y, psi0=psi0, psi_T=psi_T, N=N)
    print(f"  Snapshot: {SNAP_DIR}/{name}_N{N}_snapshot.npz")


# ── Grid / solver factory ─────────────────────────────────────────────────────

def _make_grid_ccd_adv(N: int):
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="periodic")
    return grid, ccd, adv, backend


# ── Initial conditions ────────────────────────────────────────────────────────

def _eps(N: int) -> float:
    return 3.0 / N   # interface thickness ε = 3h


def _circle_psi(X, Y, cx, cy, R, eps: float) -> np.ndarray:
    """CLS ψ for a filled circle."""
    phi = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - R   # +outside, −inside
    return heaviside(np, -phi, eps)    # ψ=1 inside, ψ=0 outside


def _zalesak_psi(X, Y, N: int) -> np.ndarray:
    """CLS ψ for the Zalesak slotted disk via distance-transform SDF."""
    eps = _eps(N)
    h = 1.0 / N

    # Binary mask: 1 inside disk, 0 outside; subtract slot
    r = np.sqrt((X - ZAL_CX) ** 2 + (Y - ZAL_CY) ** 2)
    in_disk = r < ZAL_R
    in_slot = (
        (np.abs(X - ZAL_CX) < ZAL_SLOT_W / 2)
        & (Y > ZAL_CY - ZAL_R)
        & (Y < ZAL_CY - ZAL_R + ZAL_SLOT_H)
    )
    mask = (in_disk & ~in_slot).astype(float)

    # Unsigned distance transform (in pixels → physical)
    dist_in  = distance_transform_edt(mask > 0.5) * h
    dist_out = distance_transform_edt(mask <= 0.5) * h
    phi = dist_out - dist_in    # negative inside Zalesak, positive outside
    return heaviside(np, -phi, eps)


# ── Velocity fields ───────────────────────────────────────────────────────────

def _solid_body_vel(X, Y, T=1.0):
    """Rigid-body rotation: one full revolution in time T."""
    omega = 2.0 * np.pi / T
    u = -omega * (Y - 0.5)
    v =  omega * (X - 0.5)
    return u, v


def _single_vortex_vel(X, Y, t: float, T=1.0):
    """Rider–Kothe single vortex, time-modulated to reverse at T/2."""
    cos_t = np.cos(np.pi * t / T)
    u =  np.sin(np.pi * X) ** 2 * np.sin(2.0 * np.pi * Y) * cos_t
    v = -np.sin(np.pi * Y) ** 2 * np.sin(2.0 * np.pi * X) * cos_t
    return u, v


# ── Advection loop ────────────────────────────────────────────────────────────

def _run(psi0: np.ndarray, vel_fn, T: float, N: int,
         adv: DissipativeCCDAdvection,
         snapshots: list | None = None) -> tuple:
    """Advance ψ from 0 to T; return (ψ_final, volume_history).

    Parameters
    ----------
    psi0       : initial ψ field (N+1, N+1)
    vel_fn     : callable(t) → (u, v) arrays
    T          : final time
    N          : grid size (for CFL)
    adv        : DissipativeCCDAdvection instance
    snapshots  : list of times at which to store ψ (approximate)
    """
    h = 1.0 / N
    psi = psi0.copy()
    t = 0.0
    vol_hist = [float(psi.sum() * h * h)]
    snap_fields = {}
    snap_times = set(snapshots or [])

    while t < T - 1e-14:
        u, v = vel_fn(t)
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-14)
        dt = min(CFL * h / u_max, T - t)
        psi = np.asarray(adv.advance(psi, [u, v], dt))
        t += dt
        vol_hist.append(float(psi.sum() * h * h))
        # Record snapshot at nearest time
        for st in list(snap_times):
            if abs(t - st) < 1.5 * dt:
                snap_fields[st] = psi.copy()
                snap_times.discard(st)

    return psi, np.array(vol_hist)


# ── Test A: Zalesak Disk ──────────────────────────────────────────────────────

def test_zalesak(N: int, make_figure: bool = False):
    grid, ccd, adv, backend = _make_grid_ccd_adv(N)
    X, Y = grid.meshgrid()

    psi0 = _zalesak_psi(X, Y, N)
    V0 = float(psi0.sum() * (1.0 / N) ** 2)

    vel_fn = lambda t: _solid_body_vel(X, Y)   # time-independent
    psi_T, vol_hist = _run(psi0, vel_fn, T_END, N, adv)

    VT = float(psi_T.sum() * (1.0 / N) ** 2)
    vol_err = abs(VT - V0) / V0

    # Shape error: area of ψ≥0.5 symmetric difference with initial mask
    mask0  = (psi0  >= 0.5)
    mask_T = (psi_T >= 0.5)
    h2 = (1.0 / N) ** 2
    area_union = float(np.sum(mask0 | mask_T)) * h2
    area_inter = float(np.sum(mask0 & mask_T)) * h2
    shape_err = (area_union - area_inter) / (float(np.sum(mask0)) * h2)

    if make_figure:
        _fig_zalesak(X, Y, psi0, psi_T, N)
        _save_snapshot("zalesak", N, X, Y, psi0, psi_T)

    return vol_err, shape_err


def _fig_zalesak(X, Y, psi0, psi_T, N):
    fig, axes = plt.subplots(1, 2, figsize=(9, 4),
                             gridspec_kw={"width_ratios": [1, 1], "wspace": 0.25})
    levels = [0.5]
    for ax, psi, title in [(axes[0], psi0, "Initial (t=0)"),
                            (axes[1], psi_T, "After 1 rev (t=T)")]:
        c = ax.contourf(X, Y, psi, levels=50, cmap="RdBu_r", vmin=0, vmax=1)
        ax.contour(X, Y, psi0, levels=levels, colors="k", linewidths=0.8,
                   linestyles="--")
        ax.contour(X, Y, psi, levels=levels, colors="r", linewidths=1.2)
        ax.set_aspect("equal")
        ax.set_title(f"{title}\n$N={N}$")
        ax.set_xlabel("$x$"); ax.set_ylabel("$y$")
    fig.subplots_adjust(right=0.88)
    cax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
    fig.colorbar(c, cax=cax, label=r"$\psi$")
    out = os.path.join(os.path.dirname(__file__), "..", "paper", "figures",
                       f"zalesak_N{N}.pdf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figure: {out}")


# ── Test B: Single Vortex ─────────────────────────────────────────────────────

def test_single_vortex(N: int, make_figure: bool = False):
    grid, ccd, adv, backend = _make_grid_ccd_adv(N)
    X, Y = grid.meshgrid()
    eps = _eps(N)

    psi0 = _circle_psi(X, Y, SV_CX, SV_CY, SV_R, eps)
    V0 = float(psi0.sum() * (1.0 / N) ** 2)

    vel_fn = lambda t: _single_vortex_vel(X, Y, t, T_END)
    snap_times = [T_END / 2]
    psi_T, vol_hist = _run(psi0, vel_fn, T_END, N, adv, snapshots=snap_times)

    VT = float(psi_T.sum() * (1.0 / N) ** 2)
    vol_err = abs(VT - V0) / V0

    # Shape error: symmetric difference of ψ≥0.5 regions (same metric as Zalesak)
    h2 = (1.0 / N) ** 2
    mask0  = (psi0  >= 0.5)
    mask_T = (psi_T >= 0.5)
    area_union = float(np.sum(mask0 | mask_T)) * h2
    area_inter = float(np.sum(mask0 & mask_T)) * h2
    shape_err = (area_union - area_inter) / (float(np.sum(mask0)) * h2)

    if make_figure:
        _fig_single_vortex(X, Y, psi0, psi_T, N)
        _save_snapshot("single_vortex", N, X, Y, psi0, psi_T)

    return vol_err, shape_err


def _fig_single_vortex(X, Y, psi0, psi_T, N):
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    for ax, psi, title in [(axes[0], psi0, "Initial (t=0)"),
                            (axes[1], psi_T, "After reversal (t=T)")]:
        ax.contourf(X, Y, psi, levels=50, cmap="RdBu_r", vmin=0, vmax=1)
        ax.contour(X, Y, psi0, levels=[0.5], colors="k", linewidths=0.8,
                   linestyles="--")
        ax.contour(X, Y, psi, levels=[0.5], colors="r", linewidths=1.2)
        ax.set_aspect("equal")
        ax.set_title(f"{title}\n$N={N}$")
        ax.set_xlabel("$x$"); ax.set_ylabel("$y$")
    out = os.path.join(os.path.dirname(__file__), "..", "paper", "figures",
                       f"single_vortex_N{N}.pdf")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figure: {out}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 62)
    print("Interface Advection Benchmarks")
    print("=" * 62)

    # ── Test A: Zalesak
    print("\nTest A: Zalesak Slotted Disk  (solid-body rotation, T=1)")
    print(f"  {'N':>5}  {'vol_err':>14}  {'shape_err':>14}")
    for N in N_CONV:
        ve, se = test_zalesak(N, make_figure=(N == N_TEST))
        print(f"  {N:>5}  {ve:>14.4e}  {se:>14.4e}")

    # ── Test B: Single Vortex
    print("\nTest B: Single Vortex  (time-reversing, T=1)")
    print(f"  {'N':>5}  {'vol_err':>14}  {'sym_diff_err':>14}")
    for N in N_CONV:
        ve, se = test_single_vortex(N, make_figure=(N == N_TEST))
        print(f"  {N:>5}  {ve:>14.4e}  {se:>14.4e}")

    print("\nDone.")
