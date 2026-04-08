#!/usr/bin/env python3
"""§12 Local-eps experiment: interface-fitted non-uniform grid + ε = 1.5·h_local.

Compare three configurations for rising bubble (rho_l=2, rho_g=1, sigma=0.1):
  A: uniform grid,  scalar eps = 1.5·h_unif
  B: non-uniform (alpha=2), scalar eps = 1.5·h_min  (old, mismatch)
  C: non-uniform (alpha=2), eps_field = 1.5·h_local  (new, matched)

Output: results/ch12_local_eps/
        paper/figures/ch12_local_eps.png
"""

import sys, pathlib
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
from twophase.levelset.heaviside import heaviside
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.reinitialize import Reinitializer
from twophase.pressure.ppe_builder import PPEBuilder

OUT_RES = pathlib.Path(__file__).resolve().parent / "results" / "local_eps"
OUT_FIG = pathlib.Path(__file__).resolve().parent / "results" / "local_eps"
OUT_RES.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

NX, NY = 64, 128
RHO_L, RHO_G, RHO_REF = 2.0, 1.0, 1.5
MU, G_ACC, SIGMA, R = 0.01, 1.0, 0.1, 0.25
T_FINAL = 3.0
EPS_FACTOR = 1.5   # ε = EPS_FACTOR · h_local


def make_eps_field(grid):
    """2-D field: eps[i,j] = EPS_FACTOR * max(h_x[i], h_y[j])."""
    hx = grid.h[0][:, np.newaxis]   # (NX+1, 1)
    hy = grid.h[1][np.newaxis, :]   # (1, NY+1)
    return EPS_FACTOR * np.maximum(hx, hy)


def run(label, alpha_grid, use_local_eps):
    """Run rising bubble with given grid type and eps strategy.

    Parameters
    ----------
    label         : str  — identifier for printout
    alpha_grid    : float — 1.0 = uniform; >1 = interface-fitted
    use_local_eps : bool  — True → eps_field = 1.5·h_local per step
                            False → scalar eps = 1.5·h_min (global)
    """
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(NX, NY), L=(1.0, 2.0), alpha_grid=alpha_grid)
    grid = Grid(gc, backend)

    # --- initial uniform build ---
    h_unif = float(grid.h[0][0])  # uniform spacing before any fitting
    eps_scalar = EPS_FACTOR * h_unif

    X, Y = grid.meshgrid()
    phi0 = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)

    # --- Apply interface-fitted grid for non-uniform cases (both B and C) ---
    if alpha_grid > 1.0:
        ccd_tmp = CCDSolver(grid, backend, bc_type='wall')
        grid.update_from_levelset(phi0, eps_scalar, ccd_tmp)
        X, Y = grid.meshgrid()

    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppb = PPEBuilder(backend, grid, bc_type='wall')
    ls_adv = DissipativeCCDAdvection(backend, grid, ccd)

    # h_min and dt_cap from ACTUAL grid (after fitting for non-uniform)
    h_min = float(min(grid.h[0].min(), grid.h[1].min()))
    eps_scalar_local = EPS_FACTOR * h_min  # conservative scalar eps for reinit/dtau
    reinit = Reinitializer(backend, grid, ccd, eps_scalar_local, n_steps=4)

    # eps field: local for C, global scalar for A/B
    if use_local_eps:
        eps_now = make_eps_field(grid)
    else:
        eps_now = eps_scalar_local

    curv_calc = CurvatureCalculator(backend, ccd, eps_now)

    # Recompute phi0 on updated grid coords
    phi0 = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)

    psi = np.asarray(heaviside(np, phi0, eps_now))
    rho = RHO_L + (RHO_G - RHO_L) * psi
    u = np.zeros_like(X); v = np.zeros_like(X); p = np.zeros_like(X)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    dt_visc = 0.25 * h_min**2 / (MU / RHO_G)
    dt_cap  = np.sqrt(min(RHO_G, RHO_L) * h_min**3 / (8 * np.pi * SIGMA))

    t, step = 0.0, 0
    yc_hist, vr_hist, ke_hist, t_hist = [], [], [], []
    blowup = False

    print(f"\n  [{label}] alpha={alpha_grid}, local_eps={use_local_eps}, "
          f"h_min={h_min:.4f}, dt_cap={dt_cap:.5f}")

    while t < T_FINAL and step < 5000000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt = min(0.2 * h_unif / u_max, dt_visc, dt_cap, T_FINAL - t)
        if dt < 1e-12:
            break

        # 1. Advect + reinitialize
        psi = np.asarray(ls_adv.advance(psi, [u, v], dt))
        if step % 5 == 0:
            psi = np.asarray(reinit.reinitialize(psi))

        # Non-uniform grid is kept FIXED (built once from initial phi).
        # Dynamic grid update is intentionally omitted here to isolate
        # the effect of local-eps from coordinate remapping complexity.

        rho = RHO_L + (RHO_G - RHO_L) * psi

        # 3. Curvature + CSF
        kappa = curv_calc.compute(psi)
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_csf_x = SIGMA * kappa * np.asarray(dpsi_dx)
        f_csf_y = SIGMA * kappa * np.asarray(dpsi_dy)

        # 4. Momentum predictor
        du_dx, du_xx = ccd.differentiate(u, 0)
        du_dy, du_yy = ccd.differentiate(u, 1)
        dv_dx, dv_xx = ccd.differentiate(v, 0)
        dv_dy, dv_yy = ccd.differentiate(v, 1)
        du_dx=np.asarray(du_dx); du_xx=np.asarray(du_xx)
        du_dy=np.asarray(du_dy); du_yy=np.asarray(du_yy)
        dv_dx=np.asarray(dv_dx); dv_xx=np.asarray(dv_xx)
        dv_dy=np.asarray(dv_dy); dv_yy=np.asarray(dv_yy)

        u_star = u + dt * (-(u*du_dx + v*du_dy)
                           + MU/rho*(du_xx + du_yy) + f_csf_x/rho)
        v_star = v + dt * (-(u*dv_dx + v*dv_dy)
                           + MU/rho*(dv_xx + dv_yy)
                           - (rho - RHO_REF)/rho*G_ACC + f_csf_y/rho)
        wall_bc(u_star); wall_bc(v_star)

        # 5. PPE
        triplet, A_shape = ppb.build(rho)
        A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
        du_s, _ = ccd.differentiate(u_star, 0)
        dv_s, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_s) + np.asarray(dv_s)) / dt
        rhs_v = rhs.ravel().copy(); rhs_v[ppb._pin_dof] = 0.0
        p = spsolve(A, rhs_v).reshape(grid.shape)

        # 6. Corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt/rho * np.asarray(dp_dx)
        v = v_star - dt/rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        t += dt; step += 1

        psi_sum = float(np.sum(psi))
        y_c   = float(np.sum(Y * psi)) / psi_sum if psi_sum > 1e-10 else 0.5
        v_rise = float(np.sum(v * psi)) / psi_sum if psi_sum > 1e-10 else 0.0
        ke = float(np.sum(rho * (u**2 + v**2)) * h_unif * (2.0/NY)) / 2

        yc_hist.append(y_c); vr_hist.append(v_rise)
        ke_hist.append(ke); t_hist.append(t)

        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.3f}")
            blowup = True; break

        if step % 600 == 0:
            print(f"    step={step:5d}, t={t:.3f}, y_c={y_c:.4f}, "
                  f"v_rise={v_rise:.4f}, KE={ke:.3e}")

    print(f"  [{label}] Done: step={step}, t={t:.3f}, blowup={blowup}")
    return {
        'label': label, 'alpha': alpha_grid, 'local_eps': use_local_eps,
        't': np.array(t_hist), 'yc': np.array(yc_hist),
        'vr': np.array(vr_hist), 'ke': np.array(ke_hist),
        'blowup': blowup, 'final_t': t,
    }


def make_figure(results):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    colors = ['b', 'r', 'g']
    styles = ['-', '--', '-']

    for r, c, ls in zip(results, colors, styles):
        lbl = r['label']
        axes[0].plot(r['t'], r['yc'], color=c, ls=ls, lw=1.5, label=lbl)
        axes[1].plot(r['t'], r['vr'], color=c, ls=ls, lw=1.5, label=lbl)
        axes[2].plot(r['t'], r['ke'], color=c, ls=ls, lw=1.5, label=lbl)

    for ax, ylabel, title in zip(axes,
        ['Centroid $y_c$', 'Rise velocity $v_{rise}$', 'Kinetic energy'],
        ['Bubble centroid', 'Rise velocity', 'Kinetic energy']):
        ax.set_xlabel('$t$'); ax.set_ylabel(ylabel)
        ax.set_title(title); ax.legend(fontsize=9)
        ax.grid(True, ls='--', alpha=0.4)

    plt.suptitle(
        'Rising bubble: uniform vs non-uniform grid (α=2) with/without local ε\n'
        fr'$N={NX}\times{NY}$, $\rho_l/\rho_g=2$, $\sigma=0.1$, $T={T_FINAL}$',
        fontsize=11)
    plt.tight_layout()
    fname = "ch12_local_eps.png"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Saved: {OUT_FIG / fname}")


def main():
    results = []

    # A: uniform, scalar eps
    results.append(run("A: uniform, scalar-ε", alpha_grid=1.0, use_local_eps=False))

    # B: non-uniform alpha=2, scalar eps (mismatch — previous negative result)
    results.append(run("B: non-unif α=2, scalar-ε", alpha_grid=2.0, use_local_eps=False))

    # C: non-uniform alpha=2, local eps (fix)
    results.append(run("C: non-unif α=2, local-ε", alpha_grid=2.0, use_local_eps=True))

    print("\n  Summary:")
    print(f"  {'Label':<30} {'final_t':>8} {'blowup':>7}")
    for r in results:
        print(f"  {r['label']:<30} {r['final_t']:8.3f} {str(r['blowup']):>7}")

    make_figure(results)

    # Save data for --plot-only
    np.savez(OUT_RES / "local_eps_data.npz",
             n_results=len(results),
             **{f"label_{i}": r['label'] for i, r in enumerate(results)},
             **{f"t_{i}": r['t'] for i, r in enumerate(results)},
             **{f"yc_{i}": r['yc'] for i, r in enumerate(results)},
             **{f"vr_{i}": r['vr'] for i, r in enumerate(results)},
             **{f"ke_{i}": r['ke'] for i, r in enumerate(results)},
             **{f"blowup_{i}": r['blowup'] for i, r in enumerate(results)})
    print("Done.")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT_RES / "local_eps_data.npz", allow_pickle=True)
        _n = int(_d["n_results"])
        _results = []
        for _i in range(_n):
            _results.append({
                'label': str(_d[f"label_{_i}"]),
                't': _d[f"t_{_i}"],
                'yc': _d[f"yc_{_i}"],
                'vr': _d[f"vr_{_i}"],
                'ke': _d[f"ke_{_i}"],
                'blowup': bool(_d[f"blowup_{_i}"]),
            })
        make_figure(_results)
    else:
        main()
