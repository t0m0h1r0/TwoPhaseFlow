#!/usr/bin/env python3
"""§12.2 Static droplet benchmark — zero-base re-experiment.

Based on §11 conclusions:
  - PPE: FD spsolve (exact, zero residual)
  - Gradients: CCD O(h^6) (balanced force)
  - No HFE (harmful for smoothed Heaviside pressure)
  - Non-incremental projection

Experiments:
  1. Grid convergence: N=32,48,64,96,128, rho_l/rho_g=2, We=10, 200 steps
  2. Density sweep: rho_l/rho_g=2,3,5,10, N=64, 200 steps
  3. 2D field visualization at N=64

Output:
  results/ch12_static_droplet/
  paper/figures/ch12_static_droplet_convergence.png
  paper/figures/ch12_droplet_fields.png
  paper/figures/ch12_density_fields.png
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
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder

OUT_RES = pathlib.Path(__file__).resolve().parent / "results" / "static_droplet"
OUT_FIG = pathlib.Path(__file__).resolve().parent / "results" / "static_droplet"
OUT_RES.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

R = 0.25
SIGMA = 1.0
WE = 10.0
RHO_G = 1.0
N_STEPS = 200


def run_droplet(N, rho_l, n_steps=N_STEPS):
    """Run static droplet: FD PPE + CCD gradients, no HFE."""
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppb = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (rho_l - RHO_G) * psi

    # Build FD PPE matrix (static density)
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    # CSF force (computed once, static interface)
    kappa = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u_max_hist = []
    p = np.zeros_like(X)

    for step in range(n_steps):
        # Predictor
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # Divergence (CCD)
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt

        # PPE solve (FD spsolve — exact, zero residual)
        rhs_vec = rhs.ravel().copy()
        rhs_vec[ppb._pin_dof] = 0.0
        p = spsolve(A, rhs_vec).reshape(grid.shape)

        # Corrector (CCD gradient — balanced force O(h^6))
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        u_max = float(np.max(np.sqrt(u**2 + v**2)))
        u_max_hist.append(u_max)
        if np.isnan(u_max) or u_max > 1e6:
            print(f"    BLOWUP at step={step+1}")
            break

    # Laplace pressure
    vel_mag = np.sqrt(u**2 + v**2)
    inside = phi > 3.0 / N
    outside = phi < -3.0 / N
    dp_exact = SIGMA / (R * WE)
    dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
    dp_err = abs(dp_meas - dp_exact) / dp_exact

    # Divergence
    du_final, _ = ccd.differentiate(u, 0)
    dv_final, _ = ccd.differentiate(v, 1)
    div_u = np.asarray(du_final) + np.asarray(dv_final)
    div_max = float(np.max(np.abs(div_u)))

    return {
        'N': N, 'rho_l': rho_l, 'n_steps': len(u_max_hist),
        'u_max': float(vel_mag.max()), 'u_max_hist': u_max_hist,
        'dp_meas': dp_meas, 'dp_exact': dp_exact, 'dp_err': dp_err,
        'div_max': div_max,
        'phi': phi, 'p': p, 'vel_mag': vel_mag, 'psi': psi,
    }


# ── Experiment 1: Grid convergence ──────────────────────────────────────

def exp1_grid_convergence():
    print("=" * 60)
    print("Exp 1: Grid convergence (rho_l/rho_g=2, We=10, 200 steps)")
    print("=" * 60)
    Ns = [32, 48, 64, 96, 128]
    results = []
    for N in Ns:
        print(f"  N={N} ...")
        r = run_droplet(N, rho_l=2.0)
        print(f"    ||u||={r['u_max']:.3e}, dp_err={r['dp_err']*100:.2f}%, "
              f"div_max={r['div_max']:.3e}")
        results.append(r)

    # Table
    print("\n  Grid convergence table:")
    print(f"  {'N':>5} {'||u||_inf':>12} {'dp_err%':>10} {'div_max':>12}")
    for r in results:
        print(f"  {r['N']:5d} {r['u_max']:12.3e} {r['dp_err']*100:10.2f} "
              f"{r['div_max']:12.3e}")

    # Figure: convergence plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    Ns_arr = np.array([r['N'] for r in results])
    hs = 1.0 / Ns_arr

    ax1.loglog(hs, [r['u_max'] for r in results], 'bo-', label=r'$\|\mathbf{u}\|_\infty$')
    ax1.loglog(hs, 0.5 * hs**2, 'k--', alpha=0.5, label=r'$O(h^2)$ ref')
    ax1.set_xlabel('$h = 1/N$'); ax1.set_ylabel(r'$\|\mathbf{u}_\mathrm{para}\|_\infty$')
    ax1.set_title('Parasitic velocity'); ax1.legend(); ax1.grid(True, which='both', ls='--', alpha=0.4)

    ax2.semilogx(hs, [r['dp_err']*100 for r in results], 'rs-')
    ax2.set_xlabel('$h = 1/N$'); ax2.set_ylabel(r'$\Delta p$ relative error (%)')
    ax2.set_title('Laplace pressure error'); ax2.grid(True, which='both', ls='--', alpha=0.4)

    plt.suptitle(r'Static droplet grid convergence: $\rho_l/\rho_g=2$, $We=10$, 200 steps'
                 '\n(FD PPE + CCD gradient, no HFE)', fontsize=11)
    plt.tight_layout()
    fname = "ch12_static_droplet_convergence.png"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")
    return results


# ── Experiment 2: Density sweep ─────────────────────────────────────────

def exp2_density_sweep():
    print("\n" + "=" * 60)
    print("Exp 2: Density sweep (N=64, We=10, 200 steps)")
    print("=" * 60)
    rho_ratios = [2, 3, 5, 10]
    results = []
    for rho_l in rho_ratios:
        print(f"  rho_l={rho_l} ...")
        r = run_droplet(64, rho_l=float(rho_l))
        print(f"    ||u||={r['u_max']:.3e}, dp_err={r['dp_err']*100:.2f}%, "
              f"div_max={r['div_max']:.3e}")
        results.append(r)

    # Figure: 2x4 panels
    fig, axes = plt.subplots(2, 4, figsize=(18, 9))
    all_p = np.concatenate([r['p'].ravel() for r in results])
    vmax_p = float(np.percentile(np.abs(all_p), 99)) * 1.05
    vmax_u = float(max(r['vel_mag'].max() for r in results))

    for i, r in enumerate(results):
        Ng = r['p'].shape[0]
        x1d = np.linspace(0, 1, Ng)

        ax = axes[0, i]
        im_p = ax.pcolormesh(x1d, x1d, r['p'].T, cmap='RdBu_r',
                             vmin=-vmax_p, vmax=vmax_p, shading='auto')
        ax.contour(x1d, x1d, r['phi'].T, levels=[0.0], colors='k', linewidths=1.5)
        ax.set_title(fr'$\rho_l/\rho_g={int(r["rho_l"])}$' + '\n'
                     fr'$\Delta p={r["dp_meas"]:.3f}$', fontsize=10)
        ax.set_aspect('equal')
        if i > 0: ax.set_yticklabels([])

        ax = axes[1, i]
        im_u = ax.pcolormesh(x1d, x1d, r['vel_mag'].T, cmap='hot_r',
                             vmin=0, vmax=vmax_u, shading='auto')
        ax.contour(x1d, x1d, r['phi'].T, levels=[0.0], colors='w', linewidths=1.5)
        ax.set_title(fr'$\|\mathbf{{u}}\|_\infty={r["u_max"]:.2e}$', fontsize=10)
        ax.set_aspect('equal')
        if i > 0: ax.set_yticklabels([])

    axes[0, 0].set_ylabel('Pressure $p(x,y)$', fontsize=11)
    axes[1, 0].set_ylabel(r'Parasitic velocity $\|\mathbf{u}(x,y)\|$', fontsize=11)
    fig.colorbar(im_p, ax=axes[0, :].tolist(), label='$p$', shrink=0.8)
    fig.colorbar(im_u, ax=axes[1, :].tolist(), label=r'$\|\mathbf{u}\|$', shrink=0.8)
    plt.suptitle(r'Density sweep: $N=64$, $We=10$, 200 steps (FD PPE + CCD grad)', fontsize=12)
    plt.tight_layout()
    fname = "ch12_density_fields.png"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")
    return results


# ── Experiment 3: 2D field visualization at N=64 ────────────────────────

def exp3_field_viz(conv_results):
    # Use N=64 result from grid convergence
    r = [x for x in conv_results if x['N'] == 64][0]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    Ng = r['p'].shape[0]
    x1d = np.linspace(0, 1, Ng)

    # Pressure
    ax = axes[0]
    vmax_p = max(abs(r['p'].min()), abs(r['p'].max()))
    im_p = ax.pcolormesh(x1d, x1d, r['p'].T, cmap='RdBu_r',
                         vmin=-vmax_p, vmax=vmax_p, shading='auto')
    ax.contour(x1d, x1d, r['phi'].T, levels=[0.0], colors='k', linewidths=1.5)
    ax.set_title(f'Pressure $p(x,y)$\n$\\Delta p={r["dp_meas"]:.3f}$ '
                 f'(err {r["dp_err"]*100:.1f}%)', fontsize=10)
    ax.set_aspect('equal')
    fig.colorbar(im_p, ax=ax, shrink=0.7)

    # Velocity magnitude
    ax = axes[1]
    im_u = ax.pcolormesh(x1d, x1d, r['vel_mag'].T, cmap='hot_r',
                         vmin=0, shading='auto')
    ax.contour(x1d, x1d, r['phi'].T, levels=[0.0], colors='w', linewidths=1.5)
    ax.set_title(fr'Parasitic velocity $\|\mathbf{{u}}\|$' + '\n'
                 fr'peak $= {r["u_max"]:.2e}$', fontsize=10)
    ax.set_aspect('equal')
    fig.colorbar(im_u, ax=ax, shrink=0.7)

    # Time history
    ax = axes[2]
    steps = np.arange(1, len(r['u_max_hist']) + 1)
    ax.semilogy(steps, r['u_max_hist'], 'b-', linewidth=1.5)
    ax.set_xlabel('Step'); ax.set_ylabel(r'$\|\mathbf{u}\|_\infty$')
    ax.set_title('Parasitic velocity history', fontsize=10)
    ax.grid(True, which='both', ls='--', alpha=0.4)

    plt.suptitle(r'Static droplet: $N=64$, $\rho_l/\rho_g=2$, $We=10$'
                 '\n(FD PPE + CCD gradient, no HFE)', fontsize=11)
    plt.tight_layout()
    fname = "ch12_droplet_fields.png"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")


def main():
    conv = exp1_grid_convergence()
    density = exp2_density_sweep()
    exp3_field_viz(conv)

    # Save data for --plot-only
    _scalar_keys = ('N', 'rho_l', 'n_steps', 'u_max', 'dp_meas', 'dp_exact', 'dp_err', 'div_max')
    np.savez(OUT_RES / "run_static_droplet_data.npz",
             n_conv=len(conv), n_density=len(density),
             **{f"conv_{i}_{k}": np.array(r[k]) for i, r in enumerate(conv)
                for k in list(_scalar_keys) + ['u_max_hist', 'phi', 'p', 'vel_mag']},
             **{f"density_{i}_{k}": np.array(r[k]) for i, r in enumerate(density)
                for k in list(_scalar_keys) + ['phi', 'p', 'vel_mag']})
    print("\nAll experiments complete.")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT_RES / "run_static_droplet_data.npz", allow_pickle=True)
        _scalar_keys = ('N', 'rho_l', 'n_steps', 'u_max', 'dp_meas', 'dp_exact', 'dp_err', 'div_max')
        _n_conv = int(_d["n_conv"])
        _n_density = int(_d["n_density"])
        _conv = []
        for _i in range(_n_conv):
            _r = {k: _d[f"conv_{_i}_{k}"].item() if _d[f"conv_{_i}_{k}"].ndim == 0
                  else _d[f"conv_{_i}_{k}"] for k in list(_scalar_keys) + ['u_max_hist', 'phi', 'p', 'vel_mag']}
            _r['N'] = int(_r['N']); _r['n_steps'] = int(_r['n_steps'])
            _conv.append(_r)
        _density = []
        for _i in range(_n_density):
            _r = {k: _d[f"density_{_i}_{k}"].item() if _d[f"density_{_i}_{k}"].ndim == 0
                  else _d[f"density_{_i}_{k}"] for k in list(_scalar_keys) + ['phi', 'p', 'vel_mag']}
            _r['N'] = int(_r['N']); _r['n_steps'] = int(_r['n_steps'])
            _density.append(_r)
        exp3_field_viz(_conv)
        # Re-generate convergence and density figures
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        # convergence plot
        Ns_arr = np.array([r['N'] for r in _conv])
        hs = 1.0 / Ns_arr
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        ax1.loglog(hs, [r['u_max'] for r in _conv], 'bo-', label=r'$\|\mathbf{u}\|_\infty$')
        ax1.loglog(hs, 0.5 * hs**2, 'k--', alpha=0.5, label=r'$O(h^2)$ ref')
        ax1.set_xlabel('$h = 1/N$'); ax1.set_ylabel(r'$\|\mathbf{u}_\mathrm{para}\|_\infty$')
        ax1.set_title('Parasitic velocity'); ax1.legend(); ax1.grid(True, which='both', ls='--', alpha=0.4)
        ax2.semilogx(hs, [r['dp_err']*100 for r in _conv], 'rs-')
        ax2.set_xlabel('$h = 1/N$'); ax2.set_ylabel(r'$\Delta p$ relative error (%)')
        ax2.set_title('Laplace pressure error'); ax2.grid(True, which='both', ls='--', alpha=0.4)
        plt.tight_layout()
        fname = "ch12_static_droplet_convergence.png"
        fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: {OUT_RES / fname}")
    else:
        main()
