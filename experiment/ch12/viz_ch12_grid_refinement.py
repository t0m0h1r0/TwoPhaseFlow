#!/usr/bin/env python3
"""§12.2 Interface-adapted grid refinement: alpha=1,2,4 comparison.

Static droplet (R=0.25, rho_l/rho_g=2, We=10), N=64, T=0.5.
Compares parasitic currents with uniform (alpha=1) vs interface-fitted (alpha=2,4) grids.
PPE solved by defect correction (PPESolverSweep, section 8d) -- fully CCD-consistent.

Output: results/ch12_grid_refinement/ch12_grid_refinement.eps
        paper/figures/ch12_grid_refinement.eps
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

OUT_RES = pathlib.Path(__file__).resolve().parent / "results" / "grid_refinement"
OUT_FIG = pathlib.Path(__file__).resolve().parent / "results" / "grid_refinement"
OUT_RES.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

N = 64
RHO_L, RHO_G = 2.0, 1.0
WE = 10.0
R = 0.25
SIGMA = 1.0
T_FINAL = 0.5
ALPHA_LIST = [1, 2, 4]


def run(alpha):
    """Run static droplet with interface-fitted grid at concentration factor alpha.

    PPE: 2nd-order FD sparse matrix (spsolve).
    Gradients: CCD O(h^6).
    """
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=float(alpha))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    # Step 1: adapt grid to interface (using uniform phi as guide)
    X_uni, Y_uni = grid.meshgrid()
    phi_uni = R - np.sqrt((X_uni - 0.5)**2 + (Y_uni - 0.5)**2)
    grid.update_from_levelset(phi_uni, eps, ccd=ccd)   # no-op for alpha=1

    # Step 2: recompute ALL fields on the (possibly adapted) physical coordinates
    X, Y = grid.meshgrid()
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    # Build PPE sparse matrix (FD spsolve)
    ppb = PPEBuilder(backend, grid, bc_type='wall')
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)

    # dt must respect the minimum local spacing
    h_min = min(float(np.min(np.asarray(grid.coords[ax][1:]) -
                             np.asarray(grid.coords[ax][:-1])))
                for ax in range(2))
    dt = 0.25 * h_min
    print(f"    h_min={h_min:.4f} (h={h:.4f}), dt={dt:.5f}")

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    kappa = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u_max_hist = []
    t = 0.0
    step = 0

    while t < T_FINAL:
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt

        # FD PPE solve (spsolve)
        rhs_vec = rhs.ravel().copy()
        rhs_vec[ppb._pin_dof] = 0.0
        p = spsolve(A, rhs_vec).reshape(grid.shape)

        # CCD gradient for projection
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        u_max = float(np.max(np.sqrt(u**2 + v**2)))
        u_max_hist.append(u_max)
        t += dt
        step += 1
        if np.isnan(u_max) or u_max > 1e6:
            print(f"    alpha={alpha}: blowup at step {step}, t={t:.4f}")
            break

    print(f"    Completed {step} steps, t={t:.4f}")

    # Measure Laplace pressure error
    inside = phi > 3.0 / N
    outside = phi < -3.0 / N
    dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
    dp_exact = SIGMA / (R * WE)
    dp_err = abs(dp_meas - dp_exact) / dp_exact

    vel_mag = np.sqrt(u**2 + v**2)
    return {
        'alpha': alpha, 'phi': phi, 'p': p, 'vel_mag': vel_mag,
        'u_max_hist': u_max_hist, 'n_steps': step,
        'dp_meas': dp_meas, 'dp_exact': dp_exact, 'dp_err': dp_err,
    }


def make_figure(results):
    fig = plt.figure(figsize=(16, 12))

    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.1,
                          height_ratios=[1, 1, 0.7])

    axes_p  = [fig.add_subplot(gs[0, i]) for i in range(3)]
    axes_vm = [fig.add_subplot(gs[1, i]) for i in range(3)]
    ax_hist = fig.add_subplot(gs[2, :])

    all_p  = np.concatenate([r['p'].ravel() for r in results])
    all_vm = np.concatenate([r['vel_mag'].ravel() for r in results])
    vmax_p  = float(np.percentile(np.abs(all_p), 99)) * 1.05
    vmax_vm = float(np.percentile(all_vm, 99)) * 1.05

    im_p_last  = None
    im_vm_last = None

    for i, r in enumerate(results):
        alpha = r['alpha']
        phi = r['phi']
        p = r['p']
        vm = r['vel_mag']
        Ng_x, Ng_y = p.shape
        x1d = np.linspace(0, 1, Ng_x)
        y1d = np.linspace(0, 1, Ng_y)

        # Pressure field
        ax = axes_p[i]
        im_p = ax.pcolormesh(x1d, y1d, p.T, cmap='RdBu_r',
                             vmin=-vmax_p, vmax=vmax_p, shading='auto')
        ax.contour(x1d, y1d, phi.T, levels=[0.0], colors='k', linewidths=1.5)
        ax.set_title(fr'$\alpha={alpha}$' + f'\n$\\Delta p={r["dp_meas"]:.3f}$ '
                     f'(err {r["dp_err"]*100:.1f}%)', fontsize=10)
        ax.set_xlabel('$x$')
        ax.set_aspect('equal')
        if i > 0:
            ax.set_yticklabels([])
        im_p_last = im_p

        # Velocity magnitude
        ax = axes_vm[i]
        im_vm = ax.pcolormesh(x1d, y1d, vm.T, cmap='hot_r',
                              vmin=0, vmax=vmax_vm, shading='auto')
        ax.contour(x1d, y1d, phi.T, levels=[0.0], colors='w', linewidths=1.5)
        ax.set_title(fr'$\|\mathbf{{u}}\|_\infty={vm.max():.2e}$', fontsize=10)
        ax.set_xlabel('$x$')
        ax.set_aspect('equal')
        if i > 0:
            ax.set_yticklabels([])
        im_vm_last = im_vm

    axes_p[0].set_ylabel('Pressure $p(x,y)$', fontsize=11)
    axes_vm[0].set_ylabel(r'Parasitic velocity $\|\mathbf{u}(x,y)\|$', fontsize=11)

    fig.colorbar(im_p_last,  ax=axes_p,  label='$p$',             shrink=0.8)
    fig.colorbar(im_vm_last, ax=axes_vm, label=r'$\|\mathbf{u}\|$', shrink=0.8)

    # Time history
    colors = ['tab:blue', 'tab:orange', 'tab:green']
    for r, col in zip(results, colors):
        hist = r['u_max_hist']
        times = np.linspace(0, T_FINAL, len(hist) + 1)[1:]
        ax_hist.semilogy(times, hist, color=col, linewidth=1.5,
                         label=fr'$\alpha={r["alpha"]}$ ({r["n_steps"]} steps), peak={max(hist):.2e}')
    ax_hist.set_xlabel('Physical time $t$')
    ax_hist.set_ylabel(r'$\|\mathbf{u}\|_\infty$')
    ax_hist.set_title('Parasitic velocity history', fontsize=10)
    ax_hist.legend(fontsize=10)
    ax_hist.grid(True, which='both', ls='--', alpha=0.4)

    plt.suptitle(
        r'Interface-fitted grid: $\rho_l/\rho_g=2$, $N=64$, $We=10$, $T=0.5$'
        '\n(black line = interface $\\phi=0$)',
        fontsize=12
    )

    fname = "ch12_grid_refinement.eps"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")


def main():
    results = []
    for alpha in ALPHA_LIST:
        print(f"  Running alpha={alpha} ...")
        r = run(alpha)
        print(f"    ||u||_inf={r['vel_mag'].max():.3e}, "
              f"dp={r['dp_meas']:.4f} (exact={r['dp_exact']:.4f}, err={r['dp_err']*100:.1f}%)")
        results.append(r)

    make_figure(results)
    print("Done.")


if __name__ == "__main__":
    main()
