#!/usr/bin/env python3
"""Rising bubble: per-step κ filter (Helmholtz) vs no filter.

Kim compact filter on φ is contraindicated for dynamic simulations:
repeated application dissolves the interface via cumulative diffusion.
The correct per-step filter is HelmholtzKappaFilter applied to κ before
the CSF force computation — it never touches φ, so balanced-force is
preserved.

Frequent reinitialization (every step) is essential for rising bubble
stability; without it σ_κ grows unboundedly.

Compares:
  (A) Baseline  — REINIT_EVERY=1, no κ filter
  (B) Helmholtz — REINIT_EVERY=1, HelmholtzKappaFilter applied to κ each step

Setup (Hysing-like 2D):
  Domain: [0,1]×[0,2], wall BC
  Bubble: center (0.5, 0.5), R=0.25, light fluid inside (ρ_g=1)
  ρ_l=2, σ=0.1, μ=0.01, g=1.0, T_final=1.5

Output:
  experiment/ch12/results/kim_rising_bubble/kim_rising_bubble.pdf
  experiment/ch12/results/kim_rising_bubble/kim_rising_bubble_data.npz

Usage:
  python experiment/ch12/exp12_kim_rising_bubble.py
  python experiment/ch12/exp12_kim_rising_bubble.py --plot-only
"""

import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside, invert_heaviside
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.compact_filters import HelmholtzKappaFilter
from twophase.pressure.ppe_builder import PPEBuilder

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "kim_rising_bubble"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NPZ_PATH = OUT_DIR / "kim_rising_bubble_data.npz"
FIG_PATH = OUT_DIR / "kim_rising_bubble.pdf"

# ── Physical parameters ───────────────────────────────────────────────────
NX, NY  = 64, 128
RHO_L   = 2.0        # liquid (outside, heavy)
RHO_G   = 1.0        # gas    (inside bubble, light)
RHO_REF = 1.5
MU      = 0.01
G_ACC   = 1.0
SIGMA   = 0.1
R       = 0.25
T_FINAL = 1.5
SNAP_TIMES = [0.0, 0.3, 0.6, 1.0, 1.5]

# Reinitialization: every step (essential for rising bubble)
REINIT_EVERY = 1

# Non-uniform grid: interface-fitted concentration (alpha_grid > 1)
ALPHA_GRID  = 2.0   # grid density peak (actual h_min ≈ h_uniform / 5 for this value)
EPS_G_FACTOR = 2.0  # ε_g = EPS_G_FACTOR × ε_scalar  (Gaussian width for grid density)

# Helmholtz κ filter strength (per-step, applied to κ only)
ALPHA_HELM = 1.0


# ── Core simulation ───────────────────────────────────────────────────────

def run(use_helm: bool, label: str):
    backend = Backend(use_gpu=False)

    gc     = GridConfig(ndim=2, N=(NX, NY), L=(1.0, 2.0),
                        alpha_grid=ALPHA_GRID, eps_g_factor=EPS_G_FACTOR)
    grid   = Grid(gc, backend)

    # Build initial non-uniform grid from a uniform-grid SDF estimate
    h_unif = 1.0 / NX
    X0, Y0 = grid.meshgrid()
    phi_init = R - np.sqrt((X0 - 0.5)**2 + (Y0 - 0.5)**2)
    ccd0 = CCDSolver(grid, backend, bc_type="wall")
    grid.update_from_levelset(phi_init, 1.5 * h_unif, ccd0)

    # ε = 1.5 × h_min: interface-band cell width is h_min, so ε/h_local = 1.5 ✓
    # Bulk cells (h_local >> h_min) have ε/h_local < 1.5, but ψ saturates there
    h_min = float(min(np.min(grid.h[ax]) for ax in range(2)))
    eps   = 1.5 * h_min

    ccd    = CCDSolver(grid, backend, bc_type="wall")
    ppb    = PPEBuilder(backend, grid, bc_type="wall")
    curv   = CurvatureCalculator(backend, ccd, eps)
    ls_adv = DissipativeCCDAdvection(backend, grid, ccd)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4)
    helm   = HelmholtzKappaFilter(backend, ccd, alpha=ALPHA_HELM) if use_helm else None

    X, Y = grid.meshgrid()
    phi0 = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi  = np.asarray(heaviside(np, phi0, eps))
    u    = np.zeros_like(X)
    v    = np.zeros_like(X)
    p    = np.zeros_like(X)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    dt_visc = 0.25 * h_min**2 / (MU / RHO_G)

    snapshots     = [{"t": 0.0, "psi": psi.copy(),
                      "vel_mag": np.zeros_like(X)}]
    snap_idx      = 1
    centroid_hist = []
    rise_vel_hist = []
    time_hist     = []
    ke_hist       = []
    kappa_std_hist = []
    t = 0.0; step = 0

    print(f"  [{label}] running …")

    while t < T_FINAL and step < 500000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt    = min(0.2 * h_min / u_max, dt_visc, T_FINAL - t)
        if dt < 1e-10:
            break

        # 1. Advect ψ
        psi = np.asarray(ls_adv.advance(psi, [u, v], dt))

        # 2. Reinitialize every step (restores ψ = H_ε(φ) with ε = 1.5×h_min)
        if step % REINIT_EVERY == 0:
            psi = np.asarray(reinit.reinitialize(psi))

        # 3. Update density from current ψ
        rho = RHO_L + (RHO_G - RHO_L) * psi

        # 4. Curvature; optional Helmholtz κ filter before CSF force
        kappa = curv.compute(psi)
        if use_helm:
            kappa = helm.apply(kappa, psi)

        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_csf_x   = SIGMA * kappa * np.asarray(dpsi_dx)
        f_csf_y   = SIGMA * kappa * np.asarray(dpsi_dy)

        # 5. Convection + viscous + buoyancy
        du_dx, du_xx = ccd.differentiate(u, 0)
        du_dy, du_yy = ccd.differentiate(u, 1)
        dv_dx, dv_xx = ccd.differentiate(v, 0)
        dv_dy, dv_yy = ccd.differentiate(v, 1)
        du_dx = np.asarray(du_dx); du_xx = np.asarray(du_xx)
        du_dy = np.asarray(du_dy); du_yy = np.asarray(du_yy)
        dv_dx = np.asarray(dv_dx); dv_xx = np.asarray(dv_xx)
        dv_dy = np.asarray(dv_dy); dv_yy = np.asarray(dv_yy)

        conv_u = -(u * du_dx + v * du_dy)
        conv_v = -(u * dv_dx + v * dv_dy)
        visc_u = (MU / rho) * (du_xx + du_yy)
        visc_v = (MU / rho) * (dv_xx + dv_yy)
        buoy_v = -(rho - RHO_REF) / rho * G_ACC

        u_star = u + dt * (conv_u + visc_u)
        v_star = v + dt * (conv_v + visc_v + buoy_v)
        wall_bc(u_star); wall_bc(v_star)

        # 6. PPE + implicit CSF divergence source
        triplet, A_shape = ppb.build(rho)
        A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
        du_star_dx, _ = ccd.differentiate(u_star, 0)
        dv_star_dy, _ = ccd.differentiate(v_star, 1)
        rhs  = (np.asarray(du_star_dx) + np.asarray(dv_star_dy)) / dt
        df_x, _ = ccd.differentiate(f_csf_x / rho, 0)
        df_y, _ = ccd.differentiate(f_csf_y / rho, 1)
        rhs += np.asarray(df_x) + np.asarray(df_y)
        rhs_vec = rhs.ravel().copy(); rhs_vec[ppb._pin_dof] = 0.0
        p = spsolve(A, rhs_vec).reshape(grid.shape)

        # 7. Corrector — CCD ∇p with wall-Neumann zeroing (consistent with VelocityCorrector)
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        ccd.enforce_wall_neumann(dp_dx, 0)
        ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * np.asarray(dp_dx) + dt * f_csf_x / rho
        v = v_star - dt / rho * np.asarray(dp_dy) + dt * f_csf_y / rho
        wall_bc(u); wall_bc(v)

        t += dt; step += 1

        # Diagnostics  (ψ=1 inside bubble)
        psi_sum = float(np.sum(psi))
        y_c    = float(np.sum(Y * psi)) / psi_sum if psi_sum > 1e-10 else 0.5
        v_rise = float(np.sum(v * psi)) / psi_sum if psi_sum > 1e-10 else 0.0
        ke     = float(np.sum(rho * (u**2 + v**2)) * h_min * (2.0 / NY)) / 2

        kappa_np  = np.asarray(kappa)
        near_mask = psi * (1 - psi) > 0.1
        ks = float(np.std(kappa_np[near_mask])) if np.any(near_mask) else float("nan")

        centroid_hist.append(y_c)
        rise_vel_hist.append(v_rise)
        time_hist.append(t)
        ke_hist.append(ke)
        kappa_std_hist.append(ks)

        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.3f}")
            break

        # Snapshots
        while snap_idx < len(SNAP_TIMES) and t >= SNAP_TIMES[snap_idx]:
            vm = np.sqrt(u**2 + v**2)
            snapshots.append({"t": float(SNAP_TIMES[snap_idx]),
                               "psi": psi.copy(), "vel_mag": vm.copy(),
                               "kappa": kappa_np.copy()})
            print(f"    t={SNAP_TIMES[snap_idx]:.1f}  y_c={y_c:.3f}  "
                  f"v_rise={v_rise:.4f}  σ_κ={ks:.3f}  KE={ke:.3e}")
            snap_idx += 1

        if step % 300 == 0:
            print(f"    step={step:5d}  t={t:.3f}  y_c={y_c:.3f}  "
                  f"v_rise={v_rise:.4f}  σ_κ={ks:.3f}")

    print(f"  [{label}] done: step={step}, t={t:.3f}")
    return {
        "label":          label,
        "snapshots":      snapshots,
        "time_hist":      np.array(time_hist),
        "centroid_hist":  np.array(centroid_hist),
        "rise_vel_hist":  np.array(rise_vel_hist),
        "ke_hist":        np.array(ke_hist),
        "kappa_std_hist": np.array(kappa_std_hist),
    }


# ── I/O ───────────────────────────────────────────────────────────────────

def save_npz(baseline, helm_run):
    flat = {}
    for run_key, r in [("baseline", baseline), ("helm", helm_run)]:
        for k in ("time_hist", "centroid_hist", "rise_vel_hist",
                  "ke_hist", "kappa_std_hist"):
            flat[f"{run_key}__{k}"] = r[k]
        for i, snap in enumerate(r["snapshots"]):
            for field in ("psi", "vel_mag"):
                flat[f"{run_key}__snap_{i}_{field}"] = snap[field]
            flat[f"{run_key}__snap_{i}_t"] = np.array(snap["t"])
        flat[f"{run_key}__n_snaps"] = np.array(len(r["snapshots"]))
    np.savez(NPZ_PATH, **flat)
    print(f"Saved data → {NPZ_PATH}")


def load_npz():
    data   = np.load(NPZ_PATH, allow_pickle=False)
    result = {}
    for run_key in ("baseline", "helm"):
        n = int(data[f"{run_key}__n_snaps"])
        snaps = []
        for i in range(n):
            snaps.append({
                "t":       float(data[f"{run_key}__snap_{i}_t"]),
                "psi":     data[f"{run_key}__snap_{i}_psi"],
                "vel_mag": data[f"{run_key}__snap_{i}_vel_mag"],
            })
        result[run_key] = {
            "snapshots":      snaps,
            "time_hist":      data[f"{run_key}__time_hist"],
            "centroid_hist":  data[f"{run_key}__centroid_hist"],
            "rise_vel_hist":  data[f"{run_key}__rise_vel_hist"],
            "ke_hist":        data[f"{run_key}__ke_hist"],
            "kappa_std_hist": data[f"{run_key}__kappa_std_hist"],
        }
    return result


# ── Plotting ──────────────────────────────────────────────────────────────

def plot(baseline, helm_run):
    n_snaps = min(len(baseline["snapshots"]), len(helm_run["snapshots"]))
    n_snaps = min(n_snaps, len(SNAP_TIMES))

    x1d = np.linspace(0, 1,  NX + 1)
    y1d = np.linspace(0, 2,  NY + 1)

    all_vm = np.concatenate([
        s["vel_mag"].ravel()
        for r in (baseline, helm_run)
        for s in r["snapshots"][1:]
    ])
    vmax_vm = float(np.nanpercentile(all_vm, 99)) * 1.05 if len(all_vm) > 0 else 1.0

    # Layout: 4 rows × n_snaps cols + history panels
    fig = plt.figure(figsize=(3.5 * n_snaps, 16))
    gs  = fig.add_gridspec(5, n_snaps, hspace=0.3, wspace=0.08,
                           height_ratios=[1.5, 1.5, 1.5, 1.5, 1.0])

    colors = {"No filter": "#2166ac", "Helmholtz κ": "#d6604d"}

    for i in range(n_snaps):
        t_s = SNAP_TIMES[i]

        for row_offset, (run_key, run) in enumerate(
            [("No filter", baseline), ("Helmholtz κ", helm_run)]
        ):
            snap = run["snapshots"][i]

            ax_rho = fig.add_subplot(gs[row_offset * 2, i])
            ax_rho.pcolormesh(x1d, y1d, snap["psi"].T,
                              cmap="Blues", vmin=0, vmax=1, shading="auto")
            ax_rho.contour(x1d, y1d, snap["psi"].T,
                           levels=[0.5], colors="r", linewidths=1.2)
            if i == 0:
                ax_rho.set_ylabel(f"{run_key}\n$\\psi$", fontsize=9)
            ax_rho.set_title(f"$t={t_s:.1f}$" if row_offset == 0 else "",
                             fontsize=10)
            ax_rho.set_xlim(0, 1); ax_rho.set_ylim(0, 2)
            ax_rho.set_aspect("equal")
            if i > 0: ax_rho.set_yticks([])

            ax_vel = fig.add_subplot(gs[row_offset * 2 + 1, i])
            ax_vel.pcolormesh(x1d, y1d, snap["vel_mag"].T,
                              cmap="hot_r", vmin=0, vmax=vmax_vm, shading="auto")
            ax_vel.contour(x1d, y1d, snap["psi"].T,
                           levels=[0.5], colors="w", linewidths=1.0)
            if i == 0:
                ax_vel.set_ylabel(f"{run_key}\n$|\\mathbf{{u}}|$", fontsize=9)
            ax_vel.set_xlim(0, 1); ax_vel.set_ylim(0, 2)
            ax_vel.set_aspect("equal")
            if i > 0: ax_vel.set_yticks([])

    # Bottom row: history plots
    gs_bot = gs[4, :].subgridspec(1, 3, wspace=0.35)
    ax_yc  = fig.add_subplot(gs_bot[0])
    ax_vr  = fig.add_subplot(gs_bot[1])
    ax_ks  = fig.add_subplot(gs_bot[2])

    for run_key, run, ls in [
        ("No filter",  baseline,  "-"),
        ("Helmholtz κ", helm_run, "--"),
    ]:
        c  = colors[run_key]
        t  = run["time_hist"]
        ax_yc.plot(t, run["centroid_hist"],  ls=ls, color=c, lw=1.5, label=run_key)
        ax_vr.plot(t, run["rise_vel_hist"],  ls=ls, color=c, lw=1.5, label=run_key)
        ax_ks.semilogy(t, run["kappa_std_hist"], ls=ls, color=c, lw=1.5, label=run_key)

    for ax, ylabel, title in [
        (ax_yc, "Centroid $y_c$",                 "Bubble centroid"),
        (ax_vr, "Rise velocity $v_r$",             "Rise velocity"),
        (ax_ks, "$\\sigma_\\kappa$ (near interface)", "Curvature noise"),
    ]:
        ax.set_xlabel("$t$", fontsize=9)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_title(title, fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, which="both", ls="--", alpha=0.4)

    fig.suptitle(
        f"Rising bubble — Helmholtz $\\kappa$ filter (per-step, on $\\kappa$ only)\n"
        f"$N_x\\times N_y={NX}\\times{NY}$,  "
        f"$\\rho_l/\\rho_g={int(RHO_L/RHO_G)}$,  $\\sigma={SIGMA}$,  "
        f"$\\mu={MU}$,  $g={G_ACC}$\n"
        f"Reinit every step | Helmholtz $\\alpha={ALPHA_HELM}$ (applied to $\\kappa$ only; $\\phi$ untouched)",
        fontsize=10, y=1.002,
    )

    fig.savefig(FIG_PATH, format="pdf", bbox_inches="tight")
    print(f"Saved figure → {FIG_PATH}")
    plt.close(fig)


# ── Entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()

    if args.plot_only:
        d        = load_npz()
        baseline = d["baseline"]
        helm_run = d["helm"]
    else:
        baseline = run(use_helm=False, label="No filter")
        helm_run = run(use_helm=True,  label="Helmholtz κ")
        save_npz(baseline, helm_run)

    plot(baseline, helm_run)


if __name__ == "__main__":
    main()
