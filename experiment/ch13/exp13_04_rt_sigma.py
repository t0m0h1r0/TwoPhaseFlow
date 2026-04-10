#!/usr/bin/env python3
"""[13-4] Rayleigh--Taylor instability with surface tension (σ > 0).

Paper ref: §13.4 (sec:val_rt_sigma)

Surface tension stabilizes short-wavelength RT modes.  For a flat interface
in a gravitational field, the growth rate is:

    ω² = g k (ρ_l − ρ_g) / (ρ_l + ρ_g) − σ k³ / (ρ_l + ρ_g)

The cutoff wavenumber (neutral stability) is:

    k_c = sqrt(g (ρ_l − ρ_g) / σ)

Modes with k > k_c are stabilized by surface tension.

Setup
-----
  Domain  : [0, 1] × [0, 4],  wall BC (all sides)
  Initial interface: y = 2 + 0.05 sin(2π x)  (single-mode perturbation, k = 2π)
  ρ_l = 3 (heavy, y > 2),  ρ_g = 1 (light, y < 2),  g = 1,  μ = 0.01 (uniform)
  σ sweep : {0.0, 0.02, 0.05}  — progressive stabilization
  Grid    : 64 × 256
  T_final : 3.0

Theoretical cutoff wavenumber k_c (with ρ_l=3, ρ_g=1, g=1):
  σ=0.00 : k_c → ∞  (all modes grow)
  σ=0.02 : k_c = sqrt(2/0.02) = sqrt(100) ≈ 10.0
  σ=0.05 : k_c = sqrt(2/0.05) = sqrt(40)  ≈  6.32

Initial mode k = 2π ≈ 6.28:
  σ=0.00 : ω² ≈ 3.14  (grows freely)
  σ=0.02 : ω² ≈ 1.90  (slower growth)
  σ=0.05 : ω² ≈ 0.046 (marginally unstable, k ≈ k_c)

Metrics
-------
  - Interface shape snapshots at t = {0, 1, 2, 3}
  - Linear growth rate ω measured from ln(A(t)) vs t  (early phase only)
  - Comparison of ω_sim vs ω_theory for each σ: error < 20%
  - Volume conservation: |ΔV|/V₀ < 0.5%

Reference
---------
  Tryggvason (1988) J. Comput. Phys. 75, 253–282.
  He et al. (1999) J. Comput. Phys. 152, 642–663.

Output
------
  experiment/ch13/results/13_rt_sigma/
    rt_sigma_snapshots.pdf   — interface shapes for each σ
    rt_sigma_growth.pdf      — ln(A(t)) vs t with linear fits
    data.npz                 — raw data

Usage
-----
  python experiment/ch13/exp13_04_rt_sigma.py
  python experiment/ch13/exp13_04_rt_sigma.py --plot-only
  python experiment/ch13/exp13_04_rt_sigma.py --sigma 0.02
"""

import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.curvature_filter import InterfaceLimitedFilter
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__, "13_rt_sigma")

# ── Parameters ──────────────────────────────────────────────────────────────
NX, NY   = 64, 256
LX, LY   = 1.0, 4.0
RHO_L    = 3.0    # heavy (top half)
RHO_G    = 1.0    # light (bottom half)
RHO_REF  = 0.5 * (RHO_L + RHO_G)
MU       = 0.01
G_ACC    = 1.0
A0       = 0.05   # initial perturbation amplitude
T_FINAL  = 3.0
SIGMA_CASES = [0.0, 0.02, 0.05]


def _theory_omega(sigma):
    """Theoretical growth rate ω for k=2π mode."""
    k = 2.0 * np.pi
    rho_sum = RHO_L + RHO_G
    omega_sq = G_ACC * k * (RHO_L - RHO_G) / rho_sum - sigma * k**3 / rho_sum
    return float(np.sqrt(max(0.0, omega_sq)))


def _solve_ppe(rhs, rho, ppb):
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppb._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _wall_bc(arr):
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


def _interface_amplitude(psi, Y, h):
    """Interface position at x=0.5 (approximate) via psi=0.5 crossing."""
    # Use maximum y-position of interface (psi≈0.5) as amplitude proxy
    mid_col = NX // 2
    col = psi[mid_col, :]
    # Find approximate interface crossing
    for j in range(NY - 1):
        if (col[j] - 0.5) * (col[j + 1] - 0.5) < 0:
            y_int = Y[mid_col, j] + h * (0.5 - col[j]) / (col[j + 1] - col[j])
            return float(y_int)
    return float(LY / 2.0)


def run(sigma, T_final=T_FINAL, cfl=0.15, print_every=200):
    backend = Backend(use_gpu=False)
    h   = LX / NX
    eps = 1.5 * h

    gc   = GridConfig(ndim=2, N=(NX, NY), L=(LX, LY))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")
    ppb  = PPEBuilder(backend, grid, bc_type="wall")
    curv = CurvatureCalculator(backend, ccd, eps) if sigma > 0.0 else None
    hfe  = InterfaceLimitedFilter(backend, ccd, C=0.05) if sigma > 0.0 else None
    adv  = DissipativeCCDAdvection(backend, grid, ccd)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4)

    X, Y = grid.meshgrid()

    # Initial level set: heavy (ρ_l) above, light (ρ_g) below
    # psi = 1 in heavy liquid (y > interface), psi = 0 in light gas (y < interface)
    y_iface = LY / 2.0 + A0 * np.sin(2.0 * np.pi * X / LX)
    phi = Y - y_iface     # +1 in heavy region (above), -1 in light (below)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    dt_visc  = 0.25 * h**2 / (MU / min(RHO_G, 1.0))
    if sigma > 0.0:
        dt_sigma = 0.25 * np.sqrt((RHO_L + RHO_G) * h**3 / (2.0 * np.pi * sigma))
    else:
        dt_sigma = np.inf
    V0 = float(np.sum(psi) * h**2)

    omega_theory = _theory_omega(sigma)
    print(f"  σ={sigma:.3f}  ω_theory={omega_theory:.4f}")

    times = []; amp_hist = []; vol_err_hist = []
    snap_times = [0.0, 1.0, 2.0, T_final]
    snapshots  = []
    snap_idx   = 0
    t = 0.0; step = 0

    while t < T_final and step < 400000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt = min(cfl * h / u_max, dt_visc, dt_sigma, T_final - t)
        if dt < 1e-12:
            break

        # 1. Advect + reinitialize
        psi = np.asarray(adv.advance(psi, [u, v], dt))
        if step % 2 == 0:
            psi = np.asarray(reinit.reinitialize(psi))
        rho = RHO_G + (RHO_L - RHO_G) * psi

        # 2. CSF (only if σ > 0)
        if sigma > 0.0:
            xp = backend.xp
            kappa_raw = curv.compute(psi)
            kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
            dpsi_dx, _ = ccd.differentiate(psi, 0)
            dpsi_dy, _ = ccd.differentiate(psi, 1)
            f_x = sigma * kappa * np.asarray(dpsi_dx)
            f_y = sigma * kappa * np.asarray(dpsi_dy)
        else:
            f_x = np.zeros_like(X)
            f_y = np.zeros_like(X)

        # 3. NS predictor with buoyancy
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
        _wall_bc(u_star); _wall_bc(v_star)

        # 4. PPE
        du_s_dx, _ = ccd.differentiate(u_star, 0)
        dv_s_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_s_dx) + np.asarray(dv_s_dy)) / dt
        if sigma > 0.0:
            df_x, _ = ccd.differentiate(f_x / rho, 0)
            df_y, _ = ccd.differentiate(f_y / rho, 1)
            rhs += np.asarray(df_x) + np.asarray(df_y)
        p = _solve_ppe(rhs, rho, ppb)

        # 5. Corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        ccd.enforce_wall_neumann(dp_dx, 0)
        ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * np.asarray(dp_dx) + dt * f_x / rho
        v = v_star - dt / rho * np.asarray(dp_dy) + dt * f_y / rho
        _wall_bc(u); _wall_bc(v)

        t += dt; step += 1

        y_int = _interface_amplitude(psi, Y, h)
        amp   = abs(y_int - LY / 2.0)
        V     = float(np.sum(psi) * h**2)
        ke    = 0.5 * float(np.sum(rho * (u**2 + v**2)) * h**2)

        times.append(t); amp_hist.append(amp)
        vol_err_hist.append(abs(V - V0) / V0)

        if step % print_every == 0 or step <= 2:
            print(f"    step={step:5d}  t={t:.4f}  dt={dt:.5f}"
                  f"  amp={amp:.4f}  KE={ke:.3e}")
        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.4f}")
            break

        if snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
            snapshots.append({"t": float(t), "psi": psi.copy()})
            snap_idx += 1

    # Measure growth rate from linear phase (t < 1.0)
    t_arr = np.array(times)
    a_arr = np.array(amp_hist)
    lin_mask = (t_arr > 0.1) & (t_arr < 1.0) & (a_arr > 1e-5)
    if np.sum(lin_mask) > 3:
        log_a = np.log(a_arr[lin_mask])
        t_lin = t_arr[lin_mask]
        omega_sim = float(np.polyfit(t_lin, log_a, 1)[0])
    else:
        omega_sim = float("nan")

    print(f"  σ={sigma:.3f}  ω_sim={omega_sim:.4f}  ω_theory={omega_theory:.4f}")

    return {
        "sigma":      sigma,
        "times":      np.array(times),
        "amp":        np.array(amp_hist),
        "vol_err":    np.array(vol_err_hist),
        "omega_sim":  omega_sim,
        "omega_theory": omega_theory,
        "snapshots":  snapshots,
    }


def plot(results_list):
    apply_style()

    # ── Snapshots grid ─────────────────────────────────────────────────────
    n_cases = len(results_list)
    n_snaps = 4
    fig1, axes = plt.subplots(n_snaps, n_cases,
                              figsize=(3.5 * n_cases, 3.5 * n_snaps))
    if n_cases == 1:
        axes = axes[:, None]

    for col, res in enumerate(results_list):
        for row, snap in enumerate(res["snapshots"][:n_snaps]):
            ax = axes[row, col]
            ax.contourf(snap["psi"].T, levels=[0.45, 0.55], colors=[COLORS[col]])
            ax.contour(snap["psi"].T, levels=[0.5], colors=["k"], linewidths=0.8)
            ax.set_title(f"σ={res['sigma']:.3f},  t={snap['t']:.1f}", fontsize=8)
            ax.set_aspect("equal"); ax.axis("off")

    fig1.suptitle("RT instability  (snapshots)", fontsize=11)
    fig1.tight_layout()

    # ── Growth rate comparison ──────────────────────────────────────────────
    fig2, axes2 = plt.subplots(1, 2, figsize=(9, 4))

    ax = axes2[0]
    for li, res in enumerate(results_list):
        t = res["times"]; a = res["amp"]
        mask = a > 1e-6
        ax.semilogy(t[mask], a[mask], color=COLORS[li],
                    label=f"σ={res['sigma']:.3f}  (ω_sim={res['omega_sim']:.3f})")
        # Theoretical line in linear phase
        t_fit = np.linspace(0.1, min(1.0, t[-1]), 50)
        A_fit = A0 * np.exp(res["omega_theory"] * t_fit)
        ax.semilogy(t_fit, A_fit, color=COLORS[li], ls="--", lw=0.8)
    ax.set_xlabel("$t$"); ax.set_ylabel("Interface amplitude $A$")
    ax.set_title("Growth (solid=sim, dashed=theory)")
    ax.legend(fontsize=8)

    # ω_sim vs ω_theory bar comparison
    ax = axes2[1]
    sigmas = [r["sigma"] for r in results_list]
    omegas_theory = [r["omega_theory"] for r in results_list]
    omegas_sim    = [r["omega_sim"] for r in results_list
                     if not np.isnan(r["omega_sim"])]
    x = np.arange(n_cases)
    w = 0.35
    ax.bar(x - w/2, omegas_theory, w, color=COLORS[0], alpha=0.7, label="Theory")
    if len(omegas_sim) == n_cases:
        ax.bar(x + w/2, omegas_sim, w, color=COLORS[1], alpha=0.7, label="Sim")
    ax.set_xticks(x)
    ax.set_xticklabels([f"σ={s:.3f}" for s in sigmas])
    ax.set_ylabel("Growth rate $\\omega$")
    ax.set_title("Growth rate comparison")
    ax.legend(fontsize=8)

    fig2.tight_layout()
    return fig1, fig2


def main():
    parser = experiment_argparser(description=__doc__)
    parser.add_argument("--sigma", type=float, default=None,
                        help="Single σ case (default: all SIGMA_CASES)")
    args = parser.parse_args()

    npz_path = OUT / "data.npz"

    if args.plot_only:
        data = load_results(npz_path)
        results = []
        for sigma in SIGMA_CASES:
            key = f"s{int(sigma * 1000):04d}"
            if key in data:
                results.append({"sigma": sigma, **data[key]})
    else:
        cases = [args.sigma] if args.sigma is not None else SIGMA_CASES
        results = [run(sigma) for sigma in cases]

        save_dict = {}
        for res in results:
            key = f"s{int(res['sigma'] * 1000):04d}"
            save_dict[key] = {k: v for k, v in res.items()
                              if isinstance(v, (np.ndarray, float))}
        save_results(npz_path, save_dict)

    fig1, fig2 = plot(results)
    save_figure(fig1, OUT / "rt_sigma_snapshots.pdf")
    save_figure(fig2, OUT / "rt_sigma_growth.pdf")
    print(f"[exp13-4] saved → {OUT}")


if __name__ == "__main__":
    main()
