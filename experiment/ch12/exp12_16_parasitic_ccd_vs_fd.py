#!/usr/bin/env python3
"""[12-16] Parasitic currents: CCD vs FD balanced-force discretization.

Paper ref: WIKI-E-014

Compares CCD (compact cubic) and 2nd-order FD (central difference)
spatial derivatives for the surface-tension projection.  CCD's
higher-order balanced force suppresses parasitic currents significantly.

Setup
-----
  Static droplet: R=0.25, center (0.5, 0.5), ρ_l=ρ_g=1, We=1, σ=1
  Wall BC, N_STEPS=200, dt=0.25*h, eps=1.5*h
  N ∈ {32, 64, 128}

Expected results
----------------
  N=32 : CCD ‖u‖∞ ≈ 1.71e-1,  FD ‖u‖∞ ≈ 2.32e-1,  FD/CCD ≈  1.4×
  N=64 : CCD ‖u‖∞ ≈ 4.45e-3,  FD ‖u‖∞ ≈ 4.97e-2,  FD/CCD ≈ 11×
  N=128: CCD ‖u‖∞ ≈ 6.27e-3,  FD ‖u‖∞ ≈ 2.62e-2,  FD/CCD ≈  4.2×

Pass criteria
-------------
  FD/CCD ratio ≥ 10× at N=64
  CCD convergence slope ≥ 5.0

Output
------
  experiment/ch12/results/16_parasitic_ccd_vs_fd/data.npz
  experiment/ch12/results/16_parasitic_ccd_vs_fd/parasitic_ccd_vs_fd.pdf

Usage
-----
  python experiment/ch12/exp12_16_parasitic_ccd_vs_fd.py
  python experiment/ch12/exp12_16_parasitic_ccd_vs_fd.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()

OUT = experiment_dir(__file__, "16_parasitic_ccd_vs_fd")
NPZ = OUT / "data.npz"

# ── Physical parameters ──────────────────────────────────────────────────────
RHO_L   = 1.0
RHO_G   = 1.0
SIGMA   = 1.0
WE      = 1.0
R       = 0.25
N_STEPS = 200
GRIDS   = [32, 64, 128]


# ── FD derivative helpers ────────────────────────────────────────────────────

def fd_differentiate(f, axis, h):
    """2nd-order central difference with periodic extension (then wall-zero BC)."""
    df = (np.roll(f, -1, axis=axis) - np.roll(f, 1, axis=axis)) / (2.0 * h)
    # Apply wall (Dirichlet zero) BC by zeroing boundary rows/cols
    if axis == 0:
        df[0, :] = 0.0; df[-1, :] = 0.0
    else:
        df[:, 0] = 0.0; df[:, -1] = 0.0
    return df


def fd_differentiate2(f, axis, h):
    """2nd-order central 2nd derivative with periodic extension (then wall-zero BC)."""
    d2f = (np.roll(f, -1, axis=axis) - 2.0 * f + np.roll(f, 1, axis=axis)) / h**2
    if axis == 0:
        d2f[0, :] = 0.0; d2f[-1, :] = 0.0
    else:
        d2f[:, 0] = 0.0; d2f[:, -1] = 0.0
    return d2f


# ── Curvature via FD (divergence of normal) ──────────────────────────────────

def fd_curvature(psi, h):
    """Compute κ = -div(n) via 2nd-order FD on the Heaviside gradient.

    n = ∇ψ / |∇ψ|,  κ = -div(n)
    """
    dpsi_dx = fd_differentiate(psi, 0, h)
    dpsi_dy = fd_differentiate(psi, 1, h)
    grad_mag = np.sqrt(dpsi_dx**2 + dpsi_dy**2) + 1e-14

    nx = dpsi_dx / grad_mag
    ny = dpsi_dy / grad_mag

    dnx_dx = fd_differentiate(nx, 0, h)
    dny_dy = fd_differentiate(ny, 1, h)

    return -(dnx_dx + dny_dy)


# ── PPE helper ───────────────────────────────────────────────────────────────

def _solve_ppe(rhs, rho, ppe_builder):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


# ── Single simulation (CCD or FD) ────────────────────────────────────────────

def run_single(N, use_fd=False):
    """Run static droplet. If use_fd, replace CCD derivatives with FD.

    Parameters
    ----------
    N : int
        Grid size (N×N).
    use_fd : bool
        If True, use 2nd-order central FD; otherwise use CCD.

    Returns
    -------
    dict with keys N, h, u_max_peak, u_max_final, u_max_history.
    """
    backend = Backend(use_gpu=False)
    h   = 1.0 / N
    eps = 1.5 * h
    dt  = 0.25 * h

    gc          = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid        = Grid(gc, backend)
    ccd         = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')

    X, Y = grid.meshgrid()

    # Level-set / density
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi   # uniform when ρ_l = ρ_g = 1

    # ── CSF body force ────────────────────────────────────────────────────────
    if use_fd:
        kappa     = fd_curvature(psi, h)
        dpsi_dx   = fd_differentiate(psi, 0, h)
        dpsi_dy   = fd_differentiate(psi, 1, h)
    else:
        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa     = np.asarray(curv_calc.compute(psi))
        _dpsi_dx, _ = ccd.differentiate(psi, 0)
        _dpsi_dy, _ = ccd.differentiate(psi, 1)
        dpsi_dx   = np.asarray(_dpsi_dx)
        dpsi_dy   = np.asarray(_dpsi_dy)

    f_csf_x = (SIGMA / WE) * kappa * dpsi_dx
    f_csf_y = (SIGMA / WE) * kappa * dpsi_dy

    # ── Time loop ─────────────────────────────────────────────────────────────
    u = np.zeros((N, N))
    v = np.zeros((N, N))

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u_max_history = []

    for step in range(N_STEPS):
        # Predictor (non-incremental: no grad p^n)
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # PPE divergence: use same derivative type for consistency
        if use_fd:
            du_dx = fd_differentiate(u_star, 0, h)
            dv_dy = fd_differentiate(v_star, 1, h)
        else:
            _du_dx, _ = ccd.differentiate(u_star, 0)
            _dv_dy, _ = ccd.differentiate(v_star, 1)
            du_dx = np.asarray(_du_dx)
            dv_dy = np.asarray(_dv_dy)

        rhs = (du_dx + dv_dy) / dt
        p   = _solve_ppe(rhs, rho, ppe_builder)

        # Corrector
        if use_fd:
            dp_dx = fd_differentiate(p, 0, h)
            dp_dy = fd_differentiate(p, 1, h)
        else:
            _dp_dx, _ = ccd.differentiate(p, 0)
            _dp_dy, _ = ccd.differentiate(p, 1)
            dp_dx = np.asarray(_dp_dx)
            dp_dy = np.asarray(_dp_dy)

        u = u_star - dt / rho * dp_dx
        v = v_star - dt / rho * dp_dy
        wall_bc(u); wall_bc(v)

        vel_mag = float(np.max(np.sqrt(u**2 + v**2)))
        u_max_history.append(vel_mag)

        if np.isnan(vel_mag) or vel_mag > 1e6:
            print(f"    [N={N}, fd={use_fd}] BLOWUP at step {step + 1}")
            break

    return {
        "N":            N,
        "h":            h,
        "u_max_peak":   max(u_max_history),
        "u_max_final":  u_max_history[-1],
        "u_max_history": np.array(u_max_history),
        "n_steps":      len(u_max_history),
    }


# ── Plotting ─────────────────────────────────────────────────────────────────

def make_figures(ccd_results, fd_results):
    Ns       = np.array([r["N"]          for r in ccd_results])
    hs       = np.array([r["h"]          for r in ccd_results])
    u_ccd    = np.array([r["u_max_peak"] for r in ccd_results])
    u_fd     = np.array([r["u_max_peak"] for r in fd_results])
    ratios   = u_fd / (u_ccd + 1e-300)

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # Panel (a): ‖u_para‖∞ vs h, reference slopes
    ax = axes[0]
    ax.loglog(hs, u_ccd, color=COLORS[0], marker=MARKERS[0], lw=1.5, ms=6,
              label="CCD")
    ax.loglog(hs, u_fd,  color=COLORS[1], marker=MARKERS[1], lw=1.5, ms=6,
              label="FD (2nd order)")

    # Reference slopes anchored at coarsest CCD point
    h_ref = hs
    ax.loglog(h_ref, u_ccd[0] * (h_ref / hs[0])**2,  'k--', alpha=0.5,
              lw=1.0, label=r"$O(h^2)$")
    ax.loglog(h_ref, u_ccd[0] * (h_ref / hs[0])**5,  'k:',  alpha=0.5,
              lw=1.0, label=r"$O(h^5)$")

    ax.invert_xaxis()
    ax.set_xlabel(r"Grid spacing $h$")
    ax.set_ylabel(r"$\|\mathbf{u}_{\mathrm{para}}\|_\infty$")
    ax.set_title(r"(a) Parasitic current magnitude")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which="both")

    # Panel (b): FD/CCD ratio vs N
    ax = axes[1]
    ax.semilogx(Ns, ratios, color=COLORS[2], marker=MARKERS[2], lw=1.5, ms=6,
                label="FD / CCD")
    ax.axhline(10.0, color='k', ls='--', lw=1.0, alpha=0.7, label="10× threshold")
    ax.set_xlabel(r"$N$")
    ax.set_ylabel("FD / CCD ratio")
    ax.set_title(r"(b) FD / CCD ratio")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which="both")

    plt.tight_layout()
    save_figure(fig, OUT / "parasitic_ccd_vs_fd")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 72)
    print("  [12-16] Parasitic Currents: CCD vs FD")
    print("=" * 72 + "\n")

    ccd_results = []
    fd_results  = []

    print(f"  {'N':>5} | {'CCD ||u||inf':>13} | {'FD ||u||inf':>13} | {'FD/CCD':>8}")
    print("  " + "-" * 52)

    for N in GRIDS:
        print(f"  Running N={N} CCD ...", flush=True)
        r_ccd = run_single(N, use_fd=False)
        print(f"  Running N={N} FD  ...", flush=True)
        r_fd  = run_single(N, use_fd=True)

        ccd_results.append(r_ccd)
        fd_results.append(r_fd)

        ratio = r_fd["u_max_peak"] / (r_ccd["u_max_peak"] + 1e-300)
        print(f"  {N:>5} | {r_ccd['u_max_peak']:>13.3e} | "
              f"{r_fd['u_max_peak']:>13.3e} | {ratio:>8.2f}x")

    # Convergence slope for CCD (log-log)
    hs    = np.array([r["h"]          for r in ccd_results])
    u_ccd = np.array([r["u_max_peak"] for r in ccd_results])
    u_fd  = np.array([r["u_max_peak"] for r in fd_results])

    if len(hs) >= 2:
        ccd_slope = np.polyfit(np.log(hs), np.log(u_ccd), 1)[0]
    else:
        ccd_slope = float('nan')

    idx64 = [r["N"] for r in ccd_results].index(64) if 64 in [r["N"] for r in ccd_results] else None
    ratio_at_64 = (u_fd[idx64] / (u_ccd[idx64] + 1e-300)) if idx64 is not None else float('nan')

    print(f"\n  CCD convergence slope: {ccd_slope:.3f}  (pass if >= 5.0)")
    print(f"  FD/CCD ratio at N=64 : {ratio_at_64:.2f}x  (pass if >= 10)")

    slope_ok = ccd_slope >= 5.0 if not np.isnan(ccd_slope) else False
    ratio_ok = ratio_at_64 >= 10.0 if not np.isnan(ratio_at_64) else False
    print(f"\n  CCD slope check      : {'PASS' if slope_ok else 'FAIL'}")
    print(f"  FD/CCD@N=64 check    : {'PASS' if ratio_ok else 'FAIL'}")

    make_figures(ccd_results, fd_results)

    # Save data
    save_data = {
        "Ns":    np.array([r["N"] for r in ccd_results]),
        "hs":    np.array([r["h"] for r in ccd_results]),
        "u_ccd": u_ccd,
        "u_fd":  u_fd,
        "ccd_slope":   np.array(ccd_slope),
        "ratio_at_64": np.array(ratio_at_64),
    }
    for i, (r_ccd, r_fd) in enumerate(zip(ccd_results, fd_results)):
        save_data[f"u_max_hist_ccd_{i}"] = r_ccd["u_max_history"]
        save_data[f"u_max_hist_fd_{i}"]  = r_fd["u_max_history"]
    save_results(NPZ, save_data)

    print("\n  [RESULT] CCD convergence slope:", ccd_slope)
    print("  [RESULT] FD/CCD ratio at N=64:", ratio_at_64)
    for r_ccd, r_fd in zip(ccd_results, fd_results):
        ratio = r_fd["u_max_peak"] / (r_ccd["u_max_peak"] + 1e-300)
        print(f"  [RESULT] N={r_ccd['N']:>3}: CCD={r_ccd['u_max_peak']:.3e}, "
              f"FD={r_fd['u_max_peak']:.3e}, ratio={ratio:.2f}x")


if __name__ == "__main__":
    args = experiment_argparser(
        "Parasitic currents: CCD vs FD balanced-force discretization"
    ).parse_args()

    if args.plot_only:
        d = load_results(NPZ)
        Ns    = d["Ns"]
        hs    = d["hs"]
        u_ccd = d["u_ccd"]
        u_fd  = d["u_fd"]
        n     = len(Ns)
        _ccd_results = [
            {"N": int(Ns[i]), "h": float(hs[i]), "u_max_peak": float(u_ccd[i]),
             "u_max_history": d.get(f"u_max_hist_ccd_{i}", np.array([]))}
            for i in range(n)
        ]
        _fd_results = [
            {"N": int(Ns[i]), "h": float(hs[i]), "u_max_peak": float(u_fd[i]),
             "u_max_history": d.get(f"u_max_hist_fd_{i}", np.array([]))}
            for i in range(n)
        ]
        make_figures(_ccd_results, _fd_results)
    else:
        main()
