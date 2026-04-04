#!/usr/bin/env python3
"""Static droplet experiment: FVM vs CCD-LU + IIM pressure diagnostic.

Compares FVM (2nd-order) and CCD-LU (6th-order) PPE solvers on the
static droplet benchmark. After time-stepping, uses IIM jump decomposition
to reconstruct the sharp pressure jump for diagnostics.

Metrics:
  - Parasitic current ||u||∞
  - Laplace pressure error
  - Pressure cross-section

Setup: R=0.25, center=(0.5,0.5), wall BC, no gravity, 200 steps.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig, SimulationConfig, SolverConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.pressure.ppe_solver_ccd_lu import PPESolverCCDLU

OUT = pathlib.Path(__file__).resolve().parent.parent / "results" / "static_droplet_iim"
OUT.mkdir(parents=True, exist_ok=True)

RHO_L, RHO_G = 2.0, 1.0
WE, R, SIGMA = 10.0, 0.25, 1.0
N_STEPS = 200


def run(N, solver_type="fvm"):
    """Run static droplet. solver_type: 'fvm' or 'ccd_lu'."""
    be = Backend(use_gpu=False)
    xp = be.xp
    h = 1.0 / N; eps = 1.5 * h; dt = 0.25 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, be)
    ccd = CCDSolver(grid, be, bc_type='wall')
    curv = CurvatureCalculator(be, ccd, eps)
    ppe_builder = PPEBuilder(be, grid, bc_type='wall')

    ccd_lu_solver = None
    if solver_type == "ccd_lu":
        cfg = SimulationConfig(grid=gc, solver=SolverConfig(
            ppe_solver_type="ccd_lu", pseudo_tol=1e-10, pseudo_maxiter=500))
        ccd_lu_solver = PPESolverCCDLU(be, cfg, grid, ccd=ccd)

    X, Y = grid.meshgrid()
    dp_exact = SIGMA / (R * WE)

    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    u = np.zeros_like(X); v = np.zeros_like(X); p = np.zeros_like(X)

    kappa = np.asarray(curv.compute(psi))
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(a):
        a[0, :] = 0; a[-1, :] = 0; a[:, 0] = 0; a[:, -1] = 0

    u_hist = []
    for step in range(N_STEPS):
        u_s = u + dt / rho * f_x; v_s = v + dt / rho * f_y
        wall_bc(u_s); wall_bc(v_s)

        du, _ = ccd.differentiate(u_s, 0)
        dv, _ = ccd.differentiate(v_s, 1)
        rhs = (np.asarray(du) + np.asarray(dv)) / dt

        if solver_type == "ccd_lu":
            p = np.asarray(be.to_host(ccd_lu_solver.solve(
                xp.asarray(rhs), xp.asarray(rho), dt=dt)))
        else:
            triplet, shape_A = ppe_builder.build(rho)
            A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=shape_A)
            rv = rhs.ravel().copy(); rv[ppe_builder._pin_dof] = 0.0
            p = spsolve(A, rv).reshape(rho.shape)

        gx, _ = ccd.differentiate(p, 0); gy, _ = ccd.differentiate(p, 1)
        u = u_s - dt / rho * np.asarray(gx)
        v = v_s - dt / rho * np.asarray(gy)
        wall_bc(u); wall_bc(v)

        mag = float(np.max(np.sqrt(u**2 + v**2)))
        u_hist.append(mag)
        if np.isnan(mag) or mag > 1e6:
            print(f"    [{solver_type} N={N}] BLOWUP step {step+1}"); break

    ins = phi > 3*h; out = phi < -3*h
    dp_m = float(np.mean(p[ins]) - np.mean(p[out])) if ins.any() and out.any() else np.nan
    dp_e = abs(dp_m - dp_exact) / dp_exact

    near = np.abs(phi) < 2*h
    osc = float(np.max(p[near]) - np.min(p[near])) if near.any() else 0

    return dict(solver=solver_type, N=N, h=h, dp_exact=dp_exact,
                u_peak=max(u_hist), u_final=u_hist[-1],
                dp_meas=dp_m, dp_err=dp_e, p_osc=osc,
                u_hist=np.array(u_hist), p=p, phi=phi, X=X, Y=Y,
                kappa=kappa, rho=rho, psi=psi, n_steps=len(u_hist))


def make_figures(results):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fvm = sorted([r for r in results if r["solver"]=="fvm"], key=lambda r:r["N"])
    clu = sorted([r for r in results if r["solver"]=="ccd_lu"], key=lambda r:r["N"])

    # ── Fig 1: Convergence ───────────────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    for data, lbl, mk, c in [(fvm,"FVM (2nd)","o","C0"), (clu,"CCD-LU (6th)","^","C1")]:
        hs = [r["h"] for r in data]
        ax1.loglog(hs, [r["u_final"] for r in data], f'{mk}-', color=c, ms=8, lw=1.5, label=lbl)
        ax2.loglog(hs, [r["dp_err"] for r in data], f'{mk}-', color=c, ms=8, lw=1.5, label=lbl)

    h_ref = np.array([r["h"] for r in fvm])
    for ax, vals in [(ax1, [r["u_final"] for r in fvm]), (ax2, [r["dp_err"] for r in fvm])]:
        v0 = vals[0] if vals[0] > 0 else 1e-6
        ax.loglog(h_ref, v0*(h_ref/h_ref[0])**1, 'k--', alpha=0.4, label="$O(h)$")
        ax.loglog(h_ref, v0*(h_ref/h_ref[0])**2, 'k:', alpha=0.4, label="$O(h^2)$")
        ax.legend(fontsize=10); ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    ax1.set_xlabel("$h$"); ax1.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax1.set_title("Parasitic Current (final step)")
    ax2.set_xlabel("$h$"); ax2.set_ylabel(r"$|\Delta p|$ relative error")
    ax2.set_title("Laplace Pressure Error")
    plt.tight_layout()
    fig.savefig(OUT/"convergence.png", dpi=150, bbox_inches="tight")
    plt.close(fig); print(f"  Saved: {OUT/'convergence.png'}")

    # ── Fig 2: Parasitic current time history ────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    for ax, data, title in [(ax1, fvm, "FVM"), (ax2, clu, "CCD-LU")]:
        for r in data:
            ax.semilogy(range(1, r["n_steps"]+1), r["u_hist"], lw=1.2,
                        label=f"$N={r['N']}$")
        ax.set_xlabel("Step"); ax.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
        ax.set_title(f"{title}: Parasitic Current History"); ax.legend(); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUT/"parasitic_history.png", dpi=150, bbox_inches="tight")
    plt.close(fig); print(f"  Saved: {OUT/'parasitic_history.png'}")

    # ── Fig 3: Pressure field + cross-section (N=64) ─────────────────────
    for solver_label, data in [("FVM", fvm), ("CCD-LU", clu)]:
        r64 = [r for r in data if r["N"] == 64]
        if not r64: continue
        r = r64[0]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        vmax = max(abs(np.nanmin(r["p"])), abs(np.nanmax(r["p"])))
        if vmax < 1e-15: vmax = 1
        cf = ax1.contourf(r["X"], r["Y"], r["p"], levels=40, cmap='RdBu_r',
                          vmin=-vmax, vmax=vmax)
        plt.colorbar(cf, ax=ax1, label="$p$")
        ax1.contour(r["X"], r["Y"], r["phi"], levels=[0], colors='k', linewidths=2)
        ax1.set_aspect('equal'); ax1.set_title(f"{solver_label}: Pressure ($N=64$)")
        ax1.set_xlabel("$x$"); ax1.set_ylabel("$y$")

        j = r["X"].shape[1] // 2
        ax2.plot(r["X"][:, j], r["p"][:, j], 'b-', lw=1.5, label="$p(x, y=0.5)$")
        ax2.axhline(r["dp_exact"], color='g', ls='--', alpha=0.6,
                     label=f"$\\sigma/(R\\cdot We)={r['dp_exact']:.3f}$")
        ax2.axhline(0, color='gray', alpha=0.3)
        for ci in np.where(np.diff(np.sign(r["phi"][:, j])))[0]:
            ax2.axvline(r["X"][ci, j], color='r', ls=':', alpha=0.5)
        ax2.set_xlabel("$x$"); ax2.set_ylabel("$p$")
        ax2.set_title(f"{solver_label}: Pressure Cross-section ($y=0.5$)")
        ax2.legend(); ax2.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(OUT/f"pressure_{solver_label.lower().replace('-','')}_N64.png",
                    dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: pressure_{solver_label.lower().replace('-','')}_N64.png")

    # ── Fig 4: Oscillation comparison ────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 5))
    for data, lbl, mk, c in [(fvm,"FVM","o","C0"), (clu,"CCD-LU","^","C1")]:
        ax.semilogy([r["h"] for r in data], [r["p_osc"] for r in data],
                    f'{mk}-', color=c, ms=8, lw=1.5, label=lbl)
    ax.set_xlabel("$h$"); ax.set_ylabel("Pressure oscillation near $\\Gamma$")
    ax.set_title("Interface Pressure Oscillation"); ax.legend(); ax.grid(True, alpha=0.3)
    ax.invert_xaxis()
    fig.savefig(OUT/"oscillation.png", dpi=150, bbox_inches="tight")
    plt.close(fig); print(f"  Saved: {OUT/'oscillation.png'}")


def main():
    print("\n" + "="*80)
    print("  Static Droplet: FVM vs CCD-LU (§12.2)")
    print(f"  R={R}, We={WE}, ρ_l/ρ_g={RHO_L/RHO_G:.0f}, {N_STEPS} steps")
    print("="*80)

    Ns = [32, 64, 128]
    results = []

    print(f"\n  {'solver':<8} {'N':>4} {'||u||_peak':>12} {'||u||_fin':>12} "
          f"{'Δp_err':>10} {'p_osc':>10}")
    print("  "+"-"*66)

    for st in ("fvm", "ccd_lu"):
        for N in Ns:
            r = run(N, st)
            results.append(r)
            print(f"  {st:<8} {N:>4} {r['u_peak']:>12.4e} {r['u_final']:>12.4e} "
                  f"{r['dp_err']:>9.2%} {r['p_osc']:>10.2e}")

    print("\n  Convergence rates (||u||∞ final):")
    for st in ("fvm", "ccd_lu"):
        runs = sorted([r for r in results if r["solver"]==st], key=lambda r:r["N"])
        for i in range(1, len(runs)):
            r0, r1 = runs[i-1], runs[i]
            if r0["u_final"]>0 and r1["u_final"]>0:
                rate = np.log(r0["u_final"]/r1["u_final"]) / np.log(r0["h"]/r1["h"])
            else: rate = float('nan')
            print(f"    {st}: N={r0['N']}→{r1['N']}: rate={rate:+.2f}")

    make_figures(results)
    print(f"\n  All saved to {OUT}")


if __name__ == "__main__":
    main()
