#!/usr/bin/env python3
"""[13-8] Droplet deformation in linear shear flow (Taylor deformation).

Paper ref: §13.8 (sec:val_taylor_deformation)

A neutrally buoyant droplet (ρ_l = ρ_g) in a background linear shear flow
u = γ̇ y (Couette configuration).  At small capillary number Ca the steady
deformation parameter

    D = (L − B) / (L + B)

is predicted analytically by Taylor (1932):

    D_theory = (19λ + 16) / (16λ + 16) × Ca

where λ = μ_l / μ_g is the viscosity ratio and Ca = μ_g γ̇ R / σ.

Setup
-----
  Domain  : [0, 4R] × [0, 4R],  R = 0.25  →  [0, 1] × [0, 1]
  BC      : Couette shear — u(y=0) = −U,  u(y=Ly) = +U  →  γ̇ = 2U/Ly
  Droplet : centred at (Lx/2, Ly/2),  ρ_l = ρ_g = 1 (neutrally buoyant)
  σ = μ_g γ̇ R / Ca  (derived from Ca definition)
  No gravity
  Ca sweep : {0.1, 0.2, 0.3, 0.4} at λ = 1 and λ = 5
  Grid : 128 × 128,  T_final = 5 (dimensionless time  t* = t γ̇)

Analytical target
-----------------
  D_theory = (19λ + 16) / (16λ + 16) × Ca   (valid for Ca < 0.5, λ finite)

Metrics
-------
  - Measured D vs. Ca: error |D_sim − D_theory| / D_theory < 10% for Ca ≤ 0.3
  - Volume conservation: |ΔV| / V₀ < 0.5%
  - Steady state: D converges (plateau in D(t) before t = 5)

Reference
---------
  Taylor, G.I. (1932) Proc. Roy. Soc. A 138, 41–48.
  Taylor, G.I. (1934) Proc. Roy. Soc. A 146, 501–523.
  Rallison, J.M. (1984) Ann. Rev. Fluid Mech. 16, 45–66.

Output
------
  experiment/ch13/results/13_taylor_deformation/
    taylor_deform.pdf      — D vs Ca for λ=1 and λ=5 with Taylor analytical
    deform_history.pdf     — D(t) for each (Ca, λ) case
    data.npz               — raw data

Usage
-----
  python experiment/ch13/exp13_08_taylor_deformation.py
  python experiment/ch13/exp13_08_taylor_deformation.py --plot-only
  python experiment/ch13/exp13_08_taylor_deformation.py --ca 0.2 --lam 1.0
"""

import sys, pathlib
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
    COLORS, MARKERS, LINESTYLES, FIGSIZE_2COL, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__, "13_taylor_deformation")

# ── Parameters ──────────────────────────────────────────────────────────────
NX, NY   = 128, 128
R        = 0.25
LX       = 4.0 * R    # = 1.0
LY       = 4.0 * R    # = 1.0
RHO      = 1.0        # ρ_l = ρ_g = 1 (neutrally buoyant)
MU_G     = 0.1        # outer (gas/matrix) viscosity
GAMMA    = 1.0        # shear rate γ̇ = 2U/Ly → U = γ̇ Ly/2
U_WALL   = 0.5 * GAMMA * LY   # top wall velocity (+U), bottom wall (-U)
T_FINAL  = 5.0        # dimensionless time t* = t γ̇  (≈ 5 shear-time units)

CA_CASES  = [0.1, 0.2, 0.3, 0.4]
LAM_CASES = [1.0, 5.0]   # viscosity ratio λ = μ_l / μ_g


def _sigma_from_ca(Ca):
    """σ = μ_g γ̇ R / Ca."""
    return MU_G * GAMMA * R / Ca


def _mu_l_from_lam(lam):
    return lam * MU_G


def _solve_ppe(rhs, rho, ppb):
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppb._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _couette_profile(Y, t=None):
    """Linear shear profile u = γ̇ (y − Ly/2) mapped to [−U, +U]."""
    return GAMMA * (Y - LY / 2.0)


def _apply_couette_bc(u, v, Y):
    """Enforce Couette velocity on top and bottom walls."""
    # u at y=0 → −U,  u at y=Ly → +U
    u[:, 0]  = -U_WALL
    u[:, -1] = +U_WALL
    # v = 0 at walls
    v[:, 0]  = 0.0
    v[:, -1] = 0.0
    # Left/right: periodic-like (zero normal flow, free slip in x)
    # For wall BC solver we also zero out normal velocity at x-walls
    u[0, :] = u[1, :]
    u[-1, :] = u[-2, :]


def _wall_bc_v(arr):
    """Zero normal velocity at all walls (for v-corrector)."""
    arr[:, 0]  = 0.0
    arr[:, -1] = 0.0
    arr[0, :]  = 0.0
    arr[-1, :] = 0.0


def _deformation_param(psi, X, Y):
    """D = (L−B)/(L+B) from principal axes of psi>0.5 region."""
    mask = psi > 0.5
    if not np.any(mask):
        return float("nan"), float("nan"), float("nan")
    xs = X[mask]; ys = Y[mask]
    # Bounding box axes (simple estimate; sufficient for small deformation)
    Lax = float(ys.max() - ys.min())   # extent in y (flow-gradient direction)
    Bax = float(xs.max() - xs.min())   # extent in x (flow direction)
    # For shear deformation the droplet tilts diagonally; use moments
    xc = float(xs.mean()); yc = float(ys.mean())
    dx = xs - xc; dy = ys - yc
    Ixx = float(np.mean(dx**2))
    Iyy = float(np.mean(dy**2))
    Ixy = float(np.mean(dx * dy))
    # Eigenvalues of inertia tensor → principal half-axes
    trace = Ixx + Iyy
    det   = Ixx * Iyy - Ixy**2
    disc  = max(0.0, 0.25 * (Ixx - Iyy)**2 + Ixy**2)
    eig1  = 0.5 * trace + np.sqrt(disc)
    eig2  = 0.5 * trace - np.sqrt(disc)
    L_ell = np.sqrt(max(eig1, 1e-20))
    B_ell = np.sqrt(max(eig2, 1e-20))
    D = (L_ell - B_ell) / (L_ell + B_ell) if (L_ell + B_ell) > 1e-12 else 0.0
    return float(D), Lax, Bax


def run(Ca, lam, T_final=T_FINAL, cfl=0.15, print_every=200):
    """Run Taylor deformation at given Ca and viscosity ratio λ."""
    sigma  = _sigma_from_ca(Ca)
    mu_l   = _mu_l_from_lam(lam)

    backend = Backend(use_gpu=False)
    h   = LX / NX
    eps = 1.5 * h

    gc   = GridConfig(ndim=2, N=(NX, NY), L=(LX, LY))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")
    ppb  = PPEBuilder(backend, grid, bc_type="wall")
    curv = CurvatureCalculator(backend, ccd, eps)
    hfe  = InterfaceLimitedFilter(backend, ccd, C=0.05)
    adv  = DissipativeCCDAdvection(backend, grid, ccd)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4)

    X, Y = grid.meshgrid()

    # Droplet centered at domain center: psi=1 inside, 0 outside
    phi = R - np.sqrt((X - LX / 2.0)**2 + (Y - LY / 2.0)**2)
    psi = np.asarray(heaviside(np, phi, eps))

    # Initial velocity: background Couette flow
    u = _couette_profile(Y)
    v = np.zeros_like(X)
    _apply_couette_bc(u, v, Y)

    # Viscosity field (variable μ)
    mu = MU_G + (mu_l - MU_G) * psi
    rho = np.full_like(X, RHO)          # ρ = 1 everywhere (neutrally buoyant)

    dt_visc = 0.25 * h**2 / (max(mu_l, MU_G) / RHO)
    V0 = float(np.sum(psi) * h**2)

    times = []; deform_hist = []; vol_err_hist = []
    snap_times = [0.0, 1.0, 2.0, T_final]
    snapshots  = []
    snap_idx   = 0
    t = 0.0; step = 0

    D_theory = (19.0 * lam + 16.0) / (16.0 * lam + 16.0) * Ca

    print(f"  Ca={Ca:.2f}  λ={lam:.1f}  σ={sigma:.4f}  μ_l={mu_l:.4f}"
          f"  D_theory={D_theory:.4f}")

    while t < T_final and step < 400000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt = min(cfl * h / u_max, dt_visc, T_final - t)
        if dt < 1e-12:
            break

        # 1. Advect + reinitialize psi
        psi = np.asarray(adv.advance(psi, [u, v], dt))
        if step % 2 == 0:
            psi = np.asarray(reinit.reinitialize(psi))
        mu = MU_G + (mu_l - MU_G) * psi
        # rho stays uniform = 1

        # 2. Curvature (HFE-filtered) + CSF force
        xp = backend.xp
        kappa_raw = curv.compute(psi)
        kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_x = sigma * kappa * np.asarray(dpsi_dx)
        f_y = sigma * kappa * np.asarray(dpsi_dy)

        # 3. NS predictor (convection + viscous; no buoyancy; variable μ)
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
        visc_u = (mu / rho) * (du_xx + du_yy)
        visc_v = (mu / rho) * (dv_xx + dv_yy)

        u_star = u + dt * (conv_u + visc_u)
        v_star = v + dt * (conv_v + visc_v)
        _apply_couette_bc(u_star, v_star, Y)

        # 4. PPE with CSF divergence source (balanced-force)
        du_s_dx, _ = ccd.differentiate(u_star, 0)
        dv_s_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_s_dx) + np.asarray(dv_s_dy)) / dt
        df_x, _ = ccd.differentiate(f_x / rho, 0)
        df_y, _ = ccd.differentiate(f_y / rho, 1)
        rhs += np.asarray(df_x) + np.asarray(df_y)
        p = _solve_ppe(rhs, rho, ppb)

        # 5. Velocity corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        ccd.enforce_wall_neumann(dp_dx, 0)
        ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * np.asarray(dp_dx) + dt * f_x / rho
        v = v_star - dt / rho * np.asarray(dp_dy) + dt * f_y / rho
        _apply_couette_bc(u, v, Y)

        t += dt; step += 1

        # Diagnostics
        D, _, _ = _deformation_param(psi, X, Y)
        V = float(np.sum(psi) * h**2)
        dV = abs(V - V0) / V0
        ke = 0.5 * float(np.sum(rho * (u**2 + v**2)) * h**2)

        times.append(t); deform_hist.append(D); vol_err_hist.append(dV)

        if step % print_every == 0 or step <= 2:
            print(f"    step={step:5d}  t={t:.4f}  dt={dt:.5f}"
                  f"  D={D:.4f}  |ΔV|/V₀={dV:.2e}  KE={ke:.3e}")
        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.4f}")
            break

        if snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
            snapshots.append({"t": float(t), "psi": psi.copy(),
                               "u": u.copy(), "v": v.copy()})
            snap_idx += 1

    # Steady-state D: mean over last 20% of run
    if len(deform_hist) > 20:
        D_ss = float(np.mean(deform_hist[int(0.8 * len(deform_hist)):]))
    else:
        D_ss = float(deform_hist[-1]) if deform_hist else float("nan")

    return {
        "Ca": Ca, "lam": lam,
        "times":     np.array(times),
        "deform":    np.array(deform_hist),
        "vol_err":   np.array(vol_err_hist),
        "D_ss":      D_ss,
        "D_theory":  (19.0 * lam + 16.0) / (16.0 * lam + 16.0) * Ca,
        "snapshots": snapshots,
        "V0": V0,
    }


def plot(results_by_lam):
    """Two-panel summary: D vs Ca (comparison) + D(t) histories."""
    apply_style()

    # ── Fig 1: D vs Ca for each λ ──────────────────────────────────────────
    fig1, ax = plt.subplots(figsize=FIGSIZE_2COL)
    ca_arr = np.linspace(0.0, 0.45, 80)

    for li, (lam, results) in enumerate(results_by_lam.items()):
        D_theory_line = (19.0 * lam + 16.0) / (16.0 * lam + 16.0) * ca_arr
        ax.plot(ca_arr, D_theory_line, color=COLORS[li], ls="--", lw=1.2,
                label=f"Taylor $\\lambda={lam:.0f}$")

        cas  = [r["Ca"]     for r in results]
        Dss  = [r["D_ss"]   for r in results]
        ax.scatter(cas, Dss, color=COLORS[li], marker=MARKERS[li], s=50, zorder=5,
                   label=f"Sim $\\lambda={lam:.0f}$")

    ax.set_xlabel("$Ca$")
    ax.set_ylabel("$D = (L-B)/(L+B)$")
    ax.set_title("Taylor deformation: simulation vs. analytical")
    ax.legend(fontsize=8)
    fig1.tight_layout()

    # ── Fig 2: D(t) histories ──────────────────────────────────────────────
    all_results = [r for res_list in results_by_lam.values() for r in res_list]
    n = len(all_results)
    ncols = min(4, n)
    nrows = (n + ncols - 1) // ncols
    fig2, axes = plt.subplots(nrows, ncols, figsize=(3.8 * ncols, 3.5 * nrows),
                               squeeze=False)

    for idx, res in enumerate(all_results):
        ax2 = axes[idx // ncols][idx % ncols]
        ax2.plot(res["times"], res["deform"], color=COLORS[idx % len(COLORS)])
        ax2.axhline(res["D_theory"], color="r", ls="--", lw=0.8,
                    label=f"Taylor: {res['D_theory']:.3f}")
        ax2.axhline(res["D_ss"], color="k", ls=":", lw=0.8,
                    label=f"Sim SS: {res['D_ss']:.3f}")
        ax2.set_xlabel("$t$"); ax2.set_ylabel("$D$")
        ax2.set_title(f"$Ca={res['Ca']:.2f},\\ \\lambda={res['lam']:.0f}$",
                      fontsize=9)
        ax2.legend(fontsize=7)

    # hide unused axes
    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].axis("off")

    fig2.suptitle("Taylor deformation — D(t) histories", fontsize=11)
    fig2.tight_layout()

    return fig1, fig2


def main():
    parser = experiment_argparser(description=__doc__)
    parser.add_argument("--ca",  type=float, default=None,
                        help="Single Ca case (default: all CA_CASES)")
    parser.add_argument("--lam", type=float, default=None,
                        help="Viscosity ratio λ (default: all LAM_CASES)")
    args = parser.parse_args()

    npz_path = OUT / "data.npz"

    if args.plot_only:
        data = load_results(npz_path)
        results_by_lam = {}
        for lam in LAM_CASES:
            results_by_lam[lam] = []
            for Ca in CA_CASES:
                key = f"Ca{int(Ca*100):03d}_lam{int(lam*10):02d}"
                if key in data:
                    results_by_lam[lam].append(
                        {"Ca": Ca, "lam": lam, **data[key]})
    else:
        ca_list  = [args.ca]  if args.ca  is not None else CA_CASES
        lam_list = [args.lam] if args.lam is not None else LAM_CASES

        results_by_lam = {lam: [] for lam in lam_list}
        save_dict = {}
        for lam in lam_list:
            for Ca in ca_list:
                res = run(Ca, lam)
                results_by_lam[lam].append(res)
                key = f"Ca{int(Ca*100):03d}_lam{int(lam*10):02d}"
                save_dict[key] = {k: v for k, v in res.items()
                                  if isinstance(v, (np.ndarray, float, int))}
        save_results(npz_path, save_dict)

    fig1, fig2 = plot(results_by_lam)
    save_figure(fig1, OUT / "taylor_deform.pdf")
    save_figure(fig2, OUT / "deform_history.pdf")
    print(f"[exp13-8] saved → {OUT}")


if __name__ == "__main__":
    main()
