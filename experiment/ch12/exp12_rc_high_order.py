#!/usr/bin/env python3
"""Rhie-Chow Richardson correction — O(h²) → O(h⁴) bracket verification.

Two-part experiment:
  Part 1: Grid convergence of RC bracket norm (manufactured smooth p field)
          Standard bracket:   (∇p)_f − avg(∇p)_f             = O(h²)
          Corrected bracket:  standard + h²/12 · p̄'''_f      = O(h⁴)

  Part 2: Static droplet spurious current comparison
          Standard RC  vs  Richardson-corrected RC

Theory (docs/memo/rc_ccd_high_order_correction.md):
  (∇p)_f − avg(∇p)_f = −h²/12 p'''(x_f) + O(h⁴)
  CCD gives p'' → differentiate once more → p''' at cell centers
  Add h²/12 · (p'''_L + p'''_R)/2 to cancel leading error

A3 traceability
───────────────
  RC bracket Taylor expansion → appendix_numerics_solver_s4.tex eq:rc_detection_taylor
  Richardson correction        → docs/memo/rc_ccd_high_order_correction.md §2

Output:
  experiment/ch12/results/rc_high_order/
    rc_high_order.pdf
    rc_high_order_data.npz

Usage:
  python experiment/ch12/exp12_rc_high_order.py
  python experiment/ch12/exp12_rc_high_order.py --plot-only
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
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.levelset.curvature_filter import InterfaceLimitedFilter
from twophase.pressure.rhie_chow import RhieChowInterpolator
from twophase.pressure.velocity_corrector import ccd_pressure_gradient

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "rc_high_order"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NPZ_PATH = OUT_DIR / "rc_high_order_data.npz"
FIG_PATH = OUT_DIR / "rc_high_order.pdf"

# ── Physical parameters ──────────────────────────────────────────────────────
R       = 0.25
SIGMA   = 1.0
WE      = 10.0
RHO_G   = 1.0
RHO_L   = 2.0
N_STEPS = 400


# ══════════════════════════════════════════════════════════════════════════════
# Part 1: Grid convergence of RC bracket norm
# ══════════════════════════════════════════════════════════════════════════════

def rc_bracket_convergence():
    """Measure ‖bracket‖ for standard and corrected RC across grid sizes.

    Manufactured field: p(x,y) = cos(2πx) cos(2πy)
    Exact p'''_x = (2π)³ sin(2πx) cos(2πy)
    """
    N_LIST = [16, 32, 64, 128]
    results = {"N": [], "h": [],
               "bracket_std_Linf": [], "bracket_cor_Linf": [],
               "bracket_herm_Linf": [], "bracket_d2fd_Linf": [],
               "bracket_std_L2": [], "bracket_cor_L2": [],
               "bracket_herm_L2": [], "bracket_d2fd_L2": []}

    for N in N_LIST:
        backend = Backend(use_gpu=False)
        xp = backend.xp
        h = 1.0 / N

        gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd  = CCDSolver(grid, backend, bc_type="periodic")

        X, Y = grid.meshgrid()
        p = np.cos(2.0 * np.pi * X) * np.cos(2.0 * np.pi * Y)

        # Collect per-face bracket values across axes
        bracket_std_vals = []
        bracket_cor_vals = []
        bracket_herm_vals = []
        bracket_d2fd_vals = []

        for ax in range(2):
            # CCD cell-centre derivatives (d1=p', d2=p'' simultaneously)
            dp_cell, d2p_cell = ccd.differentiate(xp.asarray(p), ax)
            dp_cell  = np.asarray(dp_cell)
            d2p_cell = np.asarray(d2p_cell)

            # p''' = D^(1)_CCD(p'') — only needed for Richardson
            d3p_cell, _ = ccd.differentiate(xp.asarray(d2p_cell), ax)
            d3p_cell = np.asarray(d3p_cell)

            # Face quantities (face k between nodes k-1, k)
            def get_LR(arr, ax=ax):
                sl_L = [slice(None)] * 2; sl_L[ax] = slice(0, N)
                sl_R = [slice(None)] * 2; sl_R[ax] = slice(1, N + 1)
                return arr[tuple(sl_L)], arr[tuple(sl_R)]

            p_L, p_R       = get_LR(p)
            dp_L, dp_R     = get_LR(dp_cell)
            d2p_L, d2p_R   = get_LR(d2p_cell)
            d3p_L, d3p_R   = get_LR(d3p_cell)

            # Standard bracket: (∇p)_f − avg(∇p)_f  →  O(h²)
            dp_face = (p_R - p_L) / h
            dp_bar  = 0.5 * (dp_L + dp_R)
            bracket_std = dp_face - dp_bar

            # Richardson correction: + h²/12 · p̄'''_f  →  O(h⁴)
            d3p_bar = 0.5 * (d3p_L + d3p_R)
            bracket_cor = bracket_std + (h**2 / 12.0) * d3p_bar

            # Hermite bracket (zero extra CCD cost):
            #   face: 3(p_E-p_P)/(2h) - (p'_P+p'_E)/4       →  O(h⁴)
            #   avg:  (p'_P+p'_E)/2 + h/8*(p''_P-p''_E)      →  O(h⁴)
            dp_face_herm = 1.5 * (p_R - p_L) / h - 0.25 * (dp_L + dp_R)
            dp_bar_herm  = 0.5 * (dp_L + dp_R) + (h / 8.0) * (d2p_L - d2p_R)
            bracket_herm = dp_face_herm - dp_bar_herm

            # d2fd bracket: standard + h/12*(d2p_R - d2p_L)  →  O(h⁴)
            #   Uses FD of CCD d2 to estimate p''' at face.
            #   Preserves standard RC structure (same face grad, same avg).
            bracket_d2fd = bracket_std + (h / 12.0) * (d2p_R - d2p_L)

            bracket_std_vals.append(bracket_std.ravel())
            bracket_cor_vals.append(bracket_cor.ravel())
            bracket_herm_vals.append(bracket_herm.ravel())
            bracket_d2fd_vals.append(bracket_d2fd.ravel())

        all_std  = np.concatenate(bracket_std_vals)
        all_cor  = np.concatenate(bracket_cor_vals)
        all_herm = np.concatenate(bracket_herm_vals)
        all_d2fd = np.concatenate(bracket_d2fd_vals)
        bracket_std_Linf  = float(np.max(np.abs(all_std)))
        bracket_cor_Linf  = float(np.max(np.abs(all_cor)))
        bracket_herm_Linf = float(np.max(np.abs(all_herm)))
        bracket_d2fd_Linf = float(np.max(np.abs(all_d2fd)))
        bracket_std_L2    = float(np.sqrt(np.mean(all_std**2)))
        bracket_cor_L2    = float(np.sqrt(np.mean(all_cor**2)))
        bracket_herm_L2   = float(np.sqrt(np.mean(all_herm**2)))
        bracket_d2fd_L2   = float(np.sqrt(np.mean(all_d2fd**2)))

        results["N"].append(N)
        results["h"].append(h)
        results["bracket_std_Linf"].append(bracket_std_Linf)
        results["bracket_cor_Linf"].append(bracket_cor_Linf)
        results["bracket_herm_Linf"].append(bracket_herm_Linf)
        results["bracket_d2fd_Linf"].append(bracket_d2fd_Linf)
        results["bracket_std_L2"].append(bracket_std_L2)
        results["bracket_cor_L2"].append(bracket_cor_L2)
        results["bracket_herm_L2"].append(bracket_herm_L2)
        results["bracket_d2fd_L2"].append(bracket_d2fd_L2)

        print(f"  N={N:4d}  h={h:.4f}  "
              f"‖std‖∞={bracket_std_Linf:.4e}  ‖rich‖∞={bracket_cor_Linf:.4e}  "
              f"‖herm‖∞={bracket_herm_Linf:.4e}  ‖d2fd‖∞={bracket_d2fd_Linf:.4e}")

    # Convergence slopes
    for key in ("bracket_std_Linf", "bracket_cor_Linf", "bracket_herm_Linf",
                "bracket_d2fd_Linf",
                "bracket_std_L2",   "bracket_cor_L2",   "bracket_herm_L2",
                "bracket_d2fd_L2"):
        vals = np.array(results[key])
        hs   = np.array(results["h"])
        slopes = np.log(vals[1:] / vals[:-1]) / np.log(hs[1:] / hs[:-1])
        tag = key.replace("bracket_", "").replace("_", " ")
        print(f"  slopes ({tag}): {[f'{s:.2f}' for s in slopes]}")

    return results


# ══════════════════════════════════════════════════════════════════════════════
# Part 2: Static droplet — standard RC vs Richardson-corrected RC
# ══════════════════════════════════════════════════════════════════════════════

def run_droplet(N: int, mode: str = "std"):
    """Run static droplet with standard, Richardson, or Hermite RC.

    Parameters
    ----------
    N    : grid resolution
    mode : 'std' | 'rich' | 'herm'
    """
    backend = Backend(use_gpu=False)
    xp = backend.xp

    h   = 1.0 / N
    eps = 1.5 * h
    dt  = 0.25 * h

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")

    X, Y    = grid.meshgrid()
    phi_raw = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi     = np.asarray(heaviside(np, phi_raw, eps))
    rho     = RHO_G + (RHO_L - RHO_G) * psi

    rhie_chow = RhieChowInterpolator(backend, grid, ccd, bc_type="wall")
    ppb       = PPEBuilder(backend, grid, bc_type="wall")
    triplet, A_shape = ppb.build(rho)
    A_fd = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    pin  = ppb._pin_dof

    curv_calc = CurvatureCalculator(backend, ccd, eps)
    hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)
    kappa_raw = curv_calc.compute(psi)
    kappa     = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))

    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u = np.zeros_like(X); v = np.zeros_like(X); p = np.zeros_like(X)
    u_max_hist = []
    bracket_hist = []   # track RC bracket norm

    for step in range(N_STEPS):
        # Predictor
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # PPE: standard RC + BF for RHS
        div_rc = rhie_chow.face_velocity_divergence(
            [u_star, v_star], p, rho, dt,
            kappa=xp.asarray(kappa), psi=xp.asarray(psi), we=WE,
        )

        # High-order RC correction to divergence
        if mode == "rich":
            rc_corr = _rc_richardson_correction(ccd, xp, p, grid, dt, rho)
            div_rc = div_rc + xp.asarray(rc_corr)
        elif mode == "herm":
            rc_corr = _rc_hermite_correction(ccd, xp, p, grid, dt, rho)
            div_rc = div_rc + xp.asarray(rc_corr)
        elif mode == "d2fd":
            rc_corr = _rc_d2fd_correction(ccd, xp, p, grid, dt, rho)
            div_rc = div_rc + xp.asarray(rc_corr)

        rhs_vec = np.asarray(div_rc).ravel() / dt
        rhs_vec[pin] = 0.0
        p = spsolve(A_fd, rhs_vec).reshape(grid.shape)

        # Corrector: CCD ∇p
        grad_p = ccd_pressure_gradient(ccd, xp.asarray(p), grid.ndim)
        u = u_star - dt / rho * np.asarray(grad_p[0])
        v = v_star - dt / rho * np.asarray(grad_p[1])
        wall_bc(u); wall_bc(v)

        u_mag = np.sqrt(u**2 + v**2)
        u_max_hist.append(float(np.max(u_mag)))

        # Measure bracket norm every 50 steps
        if step % 50 == 0:
            bn = _measure_bracket_norm(ccd, xp, p, grid, mode)
            bracket_hist.append((step, bn))

        if np.isnan(u_max_hist[-1]) or u_max_hist[-1] > 1e6:
            print(f"    BLOWUP at step={len(u_max_hist)}")
            break

    inside  = phi_raw >  3.0 / N
    outside = phi_raw < -3.0 / N
    dp_exact = SIGMA / (R * WE)
    dp_meas  = float(np.mean(p[inside]) - np.mean(p[outside]))
    dp_err   = abs(dp_meas - dp_exact) / dp_exact

    return {
        "N": N,
        "mode": mode,
        "u_max": float(np.max(np.sqrt(u**2 + v**2))),
        "u_max_hist": np.array(u_max_hist),
        "dp_meas": dp_meas,
        "dp_exact": dp_exact,
        "dp_err": dp_err,
        "bracket_hist": np.array(bracket_hist),
        "p": p,
        "vel_mag": np.sqrt(u**2 + v**2),
        "phi_raw": phi_raw,
    }


def _rc_richardson_correction(ccd, xp, p, grid, dt, rho):
    """Compute the Richardson correction to the RC divergence.

    The standard RC bracket adds (∇p)_f − avg(∇p)_f = −h²/12 p''' + O(h⁴)
    to each face velocity. This correction adds +h²/12 p̄'''_f to cancel
    the leading O(h²) error, leaving O(h⁴).

    The correction enters the divergence as:
        Δ(div) = Σ_ax  [(h²/12 · p̄'''_f)_{i+½} − (h²/12 · p̄'''_f)_{i−½}] / h
               × (−dt · (1/ρ)_f^harm)

    Returns correction array to add to div_rc.
    """
    ndim = grid.ndim
    correction = np.zeros(grid.shape)

    for ax in range(ndim):
        N_ax = grid.N[ax]
        h = float(grid.L[ax] / N_ax)

        # p''' from CCD: differentiate p'' once more
        _, d2p = ccd.differentiate(xp.asarray(p), ax)
        d3p, _ = ccd.differentiate(d2p, ax)
        d3p = np.asarray(d3p)

        def sl(idx):
            s = [slice(None)] * ndim
            s[ax] = idx
            return tuple(s)

        # Face quantities between nodes k-1, k  (faces 1..N_ax)
        d3p_L = d3p[sl(slice(0, N_ax))]
        d3p_R = d3p[sl(slice(1, N_ax + 1))]
        rho_L = rho[sl(slice(0, N_ax))]
        rho_R = rho[sl(slice(1, N_ax + 1))]

        d3p_face = 0.5 * (d3p_L + d3p_R)
        inv_rho_harm = 2.0 / (rho_L + rho_R)

        # RC correction to face velocity: −dt · (1/ρ)_f · (h²/12 · p̄'''_f)
        corr_face = -dt * inv_rho_harm * (h**2 / 12.0) * d3p_face

        # Internal faces array (N_ax+1 faces, 0 = wall, rest = internal)
        flux_shape = list(grid.shape)
        flux_shape[ax] = N_ax + 1
        flux = np.zeros(flux_shape)
        flux[sl(slice(1, N_ax + 1))] = corr_face

        # FVM divergence: (flux[k+1] − flux[k]) / h
        sl_hi = [slice(None)] * ndim; sl_hi[ax] = slice(1, None)
        sl_lo = [slice(None)] * ndim; sl_lo[ax] = slice(0, -1)
        div_int = (flux[tuple(sl_hi)] - flux[tuple(sl_lo)]) / h

        # Wall node N_ax: (0 − flux[N_ax]) / h
        sl_last = [slice(None)] * ndim; sl_last[ax] = slice(-1, None)
        div_Nax = -flux[tuple(sl_last)] / h
        div_ax = np.concatenate([div_int, div_Nax], axis=ax)

        correction += div_ax

    return correction


def _rc_hermite_correction(ccd, xp, p, grid, dt, rho):
    """Compute the Hermite RC correction to divergence (zero extra CCD cost).

    Replaces the standard bracket with Hermite-interpolated versions:
      face: 3(p_E-p_P)/(2h) - (p'_P+p'_E)/4            O(h⁴)
      avg:  (p'_P+p'_E)/2 + h/8*(p''_P-p''_E)           O(h⁴)

    The correction is the DIFFERENCE between Hermite and standard brackets,
    added to the existing RC divergence computed by RhieChowInterpolator.
    """
    ndim = grid.ndim
    correction = np.zeros(grid.shape)

    for ax in range(ndim):
        N_ax = grid.N[ax]
        h = float(grid.L[ax] / N_ax)

        dp_cell, d2p_cell = ccd.differentiate(xp.asarray(p), ax)
        dp_cell  = np.asarray(dp_cell)
        d2p_cell = np.asarray(d2p_cell)

        def sl(idx):
            s = [slice(None)] * ndim
            s[ax] = idx
            return tuple(s)

        # Wall fix for dp_cell (same as rhie_chow.py)
        dp_fix = dp_cell.copy()
        dp_fix[sl(0)]    = (p[sl(1)] - p[sl(0)]) / h
        dp_fix[sl(N_ax)] = (p[sl(N_ax)] - p[sl(N_ax - 1)]) / h

        # Face quantities between nodes k-1, k  (faces 1..N_ax)
        p_L    = p[sl(slice(0, N_ax))]
        p_R    = p[sl(slice(1, N_ax + 1))]
        dp_L   = dp_fix[sl(slice(0, N_ax))]
        dp_R   = dp_fix[sl(slice(1, N_ax + 1))]
        d2p_L  = d2p_cell[sl(slice(0, N_ax))]
        d2p_R  = d2p_cell[sl(slice(1, N_ax + 1))]
        rho_L  = rho[sl(slice(0, N_ax))]
        rho_R  = rho[sl(slice(1, N_ax + 1))]

        # Standard bracket (what RhieChowInterpolator already computes)
        dp_face_std = (p_R - p_L) / h
        dp_bar_std  = 0.5 * (dp_L + dp_R)

        # Hermite bracket
        dp_face_herm = 1.5 * (p_R - p_L) / h - 0.25 * (dp_L + dp_R)
        dp_bar_herm  = 0.5 * (dp_L + dp_R) + (h / 8.0) * (d2p_L - d2p_R)

        # Delta: Hermite bracket minus standard bracket
        delta_bracket = (dp_face_herm - dp_bar_herm) - (dp_face_std - dp_bar_std)

        inv_rho_harm = 2.0 / (rho_L + rho_R)
        corr_face = -dt * inv_rho_harm * delta_bracket

        # Internal faces array
        flux_shape = list(grid.shape)
        flux_shape[ax] = N_ax + 1
        flux = np.zeros(flux_shape)
        flux[sl(slice(1, N_ax + 1))] = corr_face

        # FVM divergence
        sl_hi = [slice(None)] * ndim; sl_hi[ax] = slice(1, None)
        sl_lo = [slice(None)] * ndim; sl_lo[ax] = slice(0, -1)
        div_int = (flux[tuple(sl_hi)] - flux[tuple(sl_lo)]) / h
        sl_last = [slice(None)] * ndim; sl_last[ax] = slice(-1, None)
        div_Nax = -flux[tuple(sl_last)] / h
        div_ax = np.concatenate([div_int, div_Nax], axis=ax)

        correction += div_ax

    return correction


def _rc_d2fd_correction(ccd, xp, p, grid, dt, rho):
    """RC correction using FD of CCD d2 — zero extra CCD cost, O(h⁴).

    Adds h/12*(d2p_R - d2p_L) to the standard bracket at each face.
    This estimates p''' via FD of CCD p'' and performs Richardson correction.

    Preserves standard RC structure: same face gradient, same average.
    Only adds a small additive correction. O(h⁴) coefficient = h⁴/720 p⁵.
    """
    ndim = grid.ndim
    correction = np.zeros(grid.shape)

    for ax in range(ndim):
        N_ax = grid.N[ax]
        h = float(grid.L[ax] / N_ax)

        _, d2p = ccd.differentiate(xp.asarray(p), ax)
        d2p = np.asarray(d2p)

        def sl(idx):
            s = [slice(None)] * ndim
            s[ax] = idx
            return tuple(s)

        d2p_L = d2p[sl(slice(0, N_ax))]
        d2p_R = d2p[sl(slice(1, N_ax + 1))]
        rho_L = rho[sl(slice(0, N_ax))]
        rho_R = rho[sl(slice(1, N_ax + 1))]
        inv_rho_harm = 2.0 / (rho_L + rho_R)

        # Correction to face velocity: -dt*(1/ρ)_f * h/12*(d2p_R - d2p_L)
        corr_face = -dt * inv_rho_harm * (h / 12.0) * (d2p_R - d2p_L)

        flux_shape = list(grid.shape)
        flux_shape[ax] = N_ax + 1
        flux = np.zeros(flux_shape)
        flux[sl(slice(1, N_ax + 1))] = corr_face

        sl_hi = [slice(None)] * ndim; sl_hi[ax] = slice(1, None)
        sl_lo = [slice(None)] * ndim; sl_lo[ax] = slice(0, -1)
        div_int = (flux[tuple(sl_hi)] - flux[tuple(sl_lo)]) / h
        sl_last = [slice(None)] * ndim; sl_last[ax] = slice(-1, None)
        div_Nax = -flux[tuple(sl_last)] / h
        div_ax = np.concatenate([div_int, div_Nax], axis=ax)

        correction += div_ax

    return correction


def _measure_bracket_norm(ccd, xp, p, grid, mode):
    """Measure L∞ norm of RC bracket (std, rich, herm, or d2fd)."""
    bracket_sq = np.zeros(grid.shape)

    for ax in range(grid.ndim):
        N_ax = grid.N[ax]
        h = float(grid.L[ax] / N_ax)

        dp_cell, d2p = ccd.differentiate(xp.asarray(p), ax)
        dp_cell = np.asarray(dp_cell)
        d2p = np.asarray(d2p)

        def sl(idx):
            s = [slice(None)] * grid.ndim
            s[ax] = idx
            return tuple(s)

        dp_fix = dp_cell.copy()
        dp_fix[sl(0)]    = (p[sl(1)] - p[sl(0)]) / h
        dp_fix[sl(N_ax)] = (p[sl(N_ax)] - p[sl(N_ax - 1)]) / h

        p_L  = p[sl(slice(0, N_ax))]
        p_R  = p[sl(slice(1, N_ax + 1))]
        dp_L = dp_fix[sl(slice(0, N_ax))]
        dp_R = dp_fix[sl(slice(1, N_ax + 1))]

        if mode == "herm":
            d2p_np = np.asarray(d2p)
            d2p_L = d2p_np[sl(slice(0, N_ax))]
            d2p_R = d2p_np[sl(slice(1, N_ax + 1))]
            dp_face = 1.5 * (p_R - p_L) / h - 0.25 * (dp_L + dp_R)
            dp_bar  = 0.5 * (dp_L + dp_R) + (h / 8.0) * (d2p_L - d2p_R)
        else:
            dp_face = (p_R - p_L) / h
            dp_bar  = 0.5 * (dp_L + dp_R)

        bracket = dp_face - dp_bar

        if mode == "rich":
            d3p, _ = ccd.differentiate(xp.asarray(d2p), ax)
            d3p = np.asarray(d3p)
            d3p_L = d3p[sl(slice(0, N_ax))]
            d3p_R = d3p[sl(slice(1, N_ax + 1))]
            bracket = bracket + (h**2 / 12.0) * 0.5 * (d3p_L + d3p_R)
        elif mode == "d2fd":
            d2p_np = np.asarray(d2p)
            d2p_L = d2p_np[sl(slice(0, N_ax))]
            d2p_R = d2p_np[sl(slice(1, N_ax + 1))]
            bracket = bracket + (h / 12.0) * (d2p_R - d2p_L)

        pad_shape = list(bracket.shape)
        pad_shape[ax] = 1
        bracket_padded = np.concatenate(
            [np.zeros(pad_shape), bracket], axis=ax
        )
        bracket_sq += bracket_padded**2

    return float(np.sqrt(bracket_sq).max())


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def compute_all():
    print("═══ Part 1: RC bracket convergence (periodic, cos·cos) ═══")
    conv = rc_bracket_convergence()

    print("\n═══ Part 2: Static droplet — std vs Richardson vs Hermite vs d2fd ═══")
    droplet = {}
    for N in [32, 64]:
        for mode in ["std", "rich", "herm", "d2fd"]:
            tag = f"N{N}_{mode}"
            print(f"  [{tag}] ...")
            r = run_droplet(N, mode)
            print(f"    ‖u‖∞={r['u_max']:.3e}  Δp err={r['dp_err']*100:.2f}%")
            droplet[tag] = r

    return {"conv": conv, "droplet": droplet}


def save_npz(results):
    flat = {}
    # Part 1
    for k, v in results["conv"].items():
        flat[f"conv__{k}"] = np.asarray(v)
    # Part 2
    for tag, r in results["droplet"].items():
        for k, v in r.items():
            if isinstance(v, str):
                v = np.array(v)  # store string as numpy object
            flat[f"drop_{tag}__{k}"] = np.asarray(v)
    np.savez(NPZ_PATH, **flat)
    print(f"Saved data → {NPZ_PATH}")


def load_npz():
    data = np.load(NPZ_PATH, allow_pickle=False)
    conv = {}
    droplet = {}
    for fullkey, val in data.items():
        if fullkey.startswith("conv__"):
            conv[fullkey[6:]] = val
        elif fullkey.startswith("drop_"):
            rest = fullkey[5:]
            tag, subkey = rest.split("__", 1)
            droplet.setdefault(tag, {})[subkey] = val
    for r in droplet.values():
        for k in ("u_max", "dp_meas", "dp_exact", "dp_err", "N"):
            if k in r:
                r[k] = float(r[k])
        if "mode" in r:
            r["mode"] = str(r["mode"])
    return {"conv": conv, "droplet": droplet}


# ── Plotting ─────────────────────────────────────────────────────────────────

def plot(results):
    conv = results["conv"]
    droplet = results["droplet"]

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.4, wspace=0.35)

    # ── Panel (0,0): Bracket convergence L∞ ──
    ax00 = fig.add_subplot(gs[0, 0])
    hs = np.asarray(conv["h"], dtype=float)
    std_Linf  = np.asarray(conv["bracket_std_Linf"], dtype=float)
    cor_Linf  = np.asarray(conv["bracket_cor_Linf"], dtype=float)
    herm_Linf = np.asarray(conv["bracket_herm_Linf"], dtype=float)

    d2fd_Linf = np.asarray(conv["bracket_d2fd_Linf"], dtype=float)

    ax00.loglog(hs, std_Linf,  "o-",  color="C0", lw=2, ms=7, label="Standard $O(h^2)$")
    ax00.loglog(hs, cor_Linf,  "s--", color="C3", lw=1.5, ms=6, label="Richardson $O(h^4)$")
    ax00.loglog(hs, herm_Linf, "D:",  color="C2", lw=1.5, ms=6, label="Hermite $O(h^4)$")
    ax00.loglog(hs, d2fd_Linf, "^-",  color="C4", lw=2, ms=7, label="C/RC $O(h^4)$")

    # Reference slopes
    h_ref = np.array([hs[0], hs[-1]])
    ax00.loglog(h_ref, std_Linf[0] * (h_ref / h_ref[0])**2,
                ":", color="C0", alpha=0.4, label="$h^2$ ref")
    ax00.loglog(h_ref, cor_Linf[0] * (h_ref / h_ref[0])**4,
                ":", color="C3", alpha=0.4, label="$h^4$ ref")
    ax00.set_xlabel("$h$"); ax00.set_ylabel(r"$\|\mathrm{bracket}\|_\infty$")
    ax00.set_title("Part 1: RC bracket convergence ($L^\\infty$)")
    ax00.legend(fontsize=7); ax00.grid(True, which="both", ls="--", alpha=0.3)

    # Convergence slope annotations
    for i in range(len(hs) - 1):
        slope_std  = np.log(std_Linf[i+1]/std_Linf[i])   / np.log(hs[i+1]/hs[i])
        slope_cor  = np.log(cor_Linf[i+1]/cor_Linf[i])   / np.log(hs[i+1]/hs[i])
        slope_herm = np.log(herm_Linf[i+1]/herm_Linf[i]) / np.log(hs[i+1]/hs[i])
        xm = np.sqrt(hs[i] * hs[i+1])
        ax00.annotate(f"{slope_std:.1f}",  (xm, np.sqrt(std_Linf[i]*std_Linf[i+1])),
                      fontsize=7, color="C0", ha="center")
        ax00.annotate(f"{slope_cor:.1f}",  (xm, np.sqrt(cor_Linf[i]*cor_Linf[i+1])),
                      fontsize=7, color="C3", ha="center")
        ax00.annotate(f"{slope_herm:.1f}", (xm, np.sqrt(herm_Linf[i]*herm_Linf[i+1]) * 0.5),
                      fontsize=7, color="C2", ha="center")

    # ── Panel (0,1): Bracket convergence L2 ──
    ax01 = fig.add_subplot(gs[0, 1])
    std_L2  = np.asarray(conv["bracket_std_L2"], dtype=float)
    cor_L2  = np.asarray(conv["bracket_cor_L2"], dtype=float)
    herm_L2 = np.asarray(conv["bracket_herm_L2"], dtype=float)

    d2fd_L2 = np.asarray(conv["bracket_d2fd_L2"], dtype=float)

    ax01.loglog(hs, std_L2,  "o-",  color="C0", lw=2, ms=7, label="Standard $O(h^2)$")
    ax01.loglog(hs, cor_L2,  "s--", color="C3", lw=1.5, ms=6, label="Richardson $O(h^4)$")
    ax01.loglog(hs, herm_L2, "D:",  color="C2", lw=1.5, ms=6, label="Hermite $O(h^4)$")
    ax01.loglog(hs, d2fd_L2, "^-",  color="C4", lw=2, ms=7, label="C/RC $O(h^4)$")
    ax01.loglog(h_ref, std_L2[0] * (h_ref / h_ref[0])**2,
                ":", color="C0", alpha=0.4, label="$h^2$ ref")
    ax01.loglog(h_ref, cor_L2[0] * (h_ref / h_ref[0])**4,
                ":", color="C3", alpha=0.4, label="$h^4$ ref")
    ax01.set_xlabel("$h$"); ax01.set_ylabel(r"$\|\mathrm{bracket}\|_2$")
    ax01.set_title("Part 1: RC bracket convergence ($L^2$)")
    ax01.legend(fontsize=7); ax01.grid(True, which="both", ls="--", alpha=0.3)

    # ── Panel (1,0): Droplet ‖u‖∞ history ──
    ax10 = fig.add_subplot(gs[1, 0])
    mode_colors = {"std": "C0", "rich": "C3", "herm": "C2", "d2fd": "C4"}
    mode_styles = {"std": "-", "rich": "--", "herm": ":", "d2fd": "-."}
    mode_labels = {"std": "standard", "rich": "Richardson", "herm": "Hermite",
                   "d2fd": "C/RC"}
    for tag in sorted(droplet.keys()):
        r = droplet[tag]
        N_val = int(r["N"])
        mode = tag.split("_")[-1]
        hist = np.asarray(r["u_max_hist"])
        h_val = 1.0 / N_val
        t_ax = np.arange(1, len(hist) + 1) * 0.25 * h_val
        ax10.semilogy(t_ax, hist, mode_styles.get(mode, "-"),
                      color=mode_colors.get(mode, "gray"),
                      lw=1.5 + (0.5 if N_val == 64 else 0),
                      alpha=0.6 if N_val == 32 else 1.0,
                      label=f"N={N_val} {mode_labels.get(mode, mode)}")
    ax10.set_xlabel("Physical time $t$")
    ax10.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax10.set_title("Part 2: Spurious current history")
    ax10.legend(fontsize=7, ncol=2); ax10.grid(True, which="both", ls="--", alpha=0.3)

    # ── Panel (1,1): Summary table ──
    ax11 = fig.add_subplot(gs[1, 1])
    ax11.axis("off")
    rows = [["Config", r"$\|u\|_\infty$", r"$\Delta p$ err"]]
    for tag in sorted(droplet.keys()):
        r = droplet[tag]
        N_val = int(r["N"])
        mode = tag.split("_")[-1]
        rows.append([f"N={N_val} {mode_labels.get(mode, mode)}",
                     f"{r['u_max']:.3e}",
                     f"{r['dp_err']*100:.2f}%"])
    table = ax11.table(cellText=rows[1:], colLabels=rows[0],
                       loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.4)
    ax11.set_title("Part 2: Static droplet results", fontsize=10, pad=20)

    fig.suptitle(
        "Rhie-Chow high-order correction: Standard vs Richardson vs Hermite vs C/RC\n"
        "C/RC: $O(h^2) \\to O(h^4)$, zero extra CCD cost, stable",
        fontsize=10, y=1.01,
    )
    fig.savefig(FIG_PATH, format="pdf", bbox_inches="tight")
    print(f"Saved figure → {FIG_PATH}")
    plt.close(fig)


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()

    if args.plot_only:
        results = load_npz()
    else:
        results = compute_all()
        save_npz(results)

    plot(results)


if __name__ == "__main__":
    main()
