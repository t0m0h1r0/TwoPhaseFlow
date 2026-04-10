#!/usr/bin/env python3
"""[13-2] Capillary wave oscillation decay — Prosperetti (1981) benchmark.

Paper ref: §13.2 (sec:val_capillary)

A circular liquid droplet with a small l=2 shape perturbation oscillates
and decays due to viscosity.  The natural frequency and damping rate are
given analytically by Prosperetti (1981).

For a droplet in gas with ρ_g << ρ_l, the inviscid natural frequency of
the l-th mode is:

    ω₀² = l(l−1)(l+2) σ / (ρ_l R₀³)

For l=2:  ω₀² = 8σ / (ρ_l R₀³)

The viscous damping rate (leading-order, ρ_g << ρ_l):

    β = (2l²+4l−1) ν_l / ((2l+1) R₀²)

For l=2:  β = 3 ν_l / (5 R₀²)  →  amplitude ∝ exp(−β t) cos(ω t)

Setup
-----
  Domain  : [0, 1] × [0, 1],  wall BC
  Droplet : R₀ = 0.25, perturbed by ε = 0.05, mode l = 2
            r(θ) = R₀ (1 + ε cos(2θ))
  ρ_l = 10,  ρ_g = 1,  μ = 0.05 (uniform),  σ = 1.0,  no gravity
  Grid    : 128 × 128
  T_final : 5.0  (≈ 5 oscillation periods)

Theoretical values (ρ_g/ρ_l = 0.1 correction included in formula):
  ω₀²  =  8σ / (ρ_l R₀³) × ρ_l/(ρ_l+ρ_g) = 8/(10 × 0.015625) × 10/11 ≈ 46.5
  ω₀   ≈ 6.82 rad / time   →   T₀ = 2π/ω₀ ≈ 0.92 time units
  ν_l  = μ/ρ_l = 0.005
  β    = 3 × 0.005 / (5 × 0.0625) = 0.048  (mild damping)

Metrics
-------
  - Measured oscillation period T_sim vs T₀: |T_sim − T₀|/T₀ < 10%
  - Measured decay rate β_sim vs β_theory: |β_sim − β|/β < 20%
  - Volume conservation: |ΔV|/V₀ < 0.5%

Reference
---------
  Prosperetti (1981) Phys. Fluids 24, 1217.

Output
------
  experiment/ch13/results/13_capillary_wave/
    capillary_wave.pdf   — amplitude D(t) with theoretical fit
    data.npz             — raw data

Usage
-----
  python experiment/ch13/exp13_02_capillary_wave.py
  python experiment/ch13/exp13_02_capillary_wave.py --plot-only
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
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__, "13_capillary_wave")

# ── Parameters ──────────────────────────────────────────────────────────────
NX, NY   = 128, 128
LX, LY   = 1.0, 1.0
XC, YC   = 0.5, 0.5
R0       = 0.25
EPS_PERT = 0.05     # perturbation amplitude
RHO_L    = 10.0
RHO_G    = 1.0
RHO_REF  = 0.5 * (RHO_L + RHO_G)
MU       = 0.05
SIGMA    = 1.0
T_FINAL  = 5.0


def _theoretical_params():
    """Inviscid frequency and viscous damping for l=2 mode."""
    l = 2
    # Include density of outer fluid: Lamb (1932) correction factor
    # ω₀² = l(l-1)(l+2) σ / R₀³ / (ρ_l + ρ_g/(2l+1))  — Prosperetti eq.(17)
    # Simplified: use (ρ_l + ρ_g) denominator for 2-fluid
    omega0_sq = l * (l - 1) * (l + 2) * SIGMA / (R0**3 * (RHO_L + RHO_G))
    omega0 = np.sqrt(omega0_sq)
    T0 = 2.0 * np.pi / omega0
    nu_l = MU / RHO_L
    beta = (2 * l**2 + 4 * l - 1) * nu_l / ((2 * l + 1) * R0**2)
    return omega0, T0, beta


def _solve_ppe(rhs, rho, ppb):
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppb._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _wall_bc(arr):
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


def _deformation(psi, X, Y):
    """D = (L−B)/(L+B) from second moments of psi > 0.5 region."""
    mask = psi > 0.5
    if not np.any(mask):
        return 0.0
    xs = X[mask]; ys = Y[mask]
    xc = xs.mean(); yc = ys.mean()
    dx = xs - xc; dy = ys - yc
    Ixx = float(np.mean(dx**2))
    Iyy = float(np.mean(dy**2))
    Ixy = float(np.mean(dx * dy))
    disc = max(0.0, 0.25 * (Ixx - Iyy)**2 + Ixy**2)
    eig1 = 0.5 * (Ixx + Iyy) + np.sqrt(disc)
    eig2 = 0.5 * (Ixx + Iyy) - np.sqrt(disc)
    L = np.sqrt(max(eig1, 1e-20))
    B = np.sqrt(max(eig2, 1e-20))
    return float((L - B) / (L + B)) if (L + B) > 1e-12 else 0.0


def run(T_final=T_FINAL, cfl=0.15, print_every=200):
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

    # Perturbed droplet: r(θ) = R₀(1 + ε cos(2θ))
    theta = np.arctan2(Y - YC, X - XC)
    r_pert = R0 * (1.0 + EPS_PERT * np.cos(2.0 * theta))
    r_grid = np.sqrt((X - XC)**2 + (Y - YC)**2)
    phi = r_pert - r_grid           # +1 inside droplet, −1 outside
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    dt_visc  = 0.25 * h**2 / (MU / RHO_G)
    dt_sigma = 0.25 * np.sqrt((RHO_L + RHO_G) * h**3 / (2.0 * np.pi * SIGMA))
    V0 = float(np.sum(psi) * h**2)

    omega0, T0, beta = _theoretical_params()
    D0 = _deformation(psi, X, Y)   # initial deformation

    print(f"  R₀={R0}  ε={EPS_PERT}  ρ_l/ρ_g={RHO_L/RHO_G:.0f}"
          f"  ω₀={omega0:.3f}  T₀={T0:.3f}  β={beta:.4f}  D₀={D0:.4f}")

    times = []; deform_hist = []; vol_err_hist = []
    t = 0.0; step = 0

    while t < T_final and step < 500000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt = min(cfl * h / u_max, dt_visc, dt_sigma, T_final - t)
        if dt < 1e-12:
            break

        # 1. Advect + reinitialize
        psi = np.asarray(adv.advance(psi, [u, v], dt))
        if step % 2 == 0:
            psi = np.asarray(reinit.reinitialize(psi))
        rho = RHO_G + (RHO_L - RHO_G) * psi

        # 2. Curvature + CSF
        xp = backend.xp
        kappa_raw = curv.compute(psi)
        kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_x = SIGMA * kappa * np.asarray(dpsi_dx)
        f_y = SIGMA * kappa * np.asarray(dpsi_dy)

        # 3. NS predictor
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

        u_star = u + dt * (conv_u + visc_u)
        v_star = v + dt * (conv_v + visc_v)
        _wall_bc(u_star); _wall_bc(v_star)

        # 4. PPE (balanced-force)
        du_s_dx, _ = ccd.differentiate(u_star, 0)
        dv_s_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_s_dx) + np.asarray(dv_s_dy)) / dt
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

        D = _deformation(psi, X, Y)
        V = float(np.sum(psi) * h**2)
        ke = 0.5 * float(np.sum(rho * (u**2 + v**2)) * h**2)

        times.append(t); deform_hist.append(D)
        vol_err_hist.append(abs(V - V0) / V0)

        if step % print_every == 0 or step <= 2:
            print(f"    step={step:5d}  t={t:.4f}  dt={dt:.5f}"
                  f"  D={D:.4f}  KE={ke:.3e}")
        if np.isnan(ke) or ke > 1e5:
            print(f"    BLOWUP at step={step}")
            break

    return {
        "times":    np.array(times),
        "deform":   np.array(deform_hist),
        "vol_err":  np.array(vol_err_hist),
        "D0":       D0,
        "omega0":   omega0, "T0": T0, "beta": beta,
    }


def plot(res):
    apply_style()
    times  = res["times"]
    deform = res["deform"]
    D0     = float(res["D0"])
    omega0 = float(res["omega0"])
    T0     = float(res["T0"])
    beta   = float(res["beta"])

    # Theoretical fit: D(t) = D₀ exp(−β t) cos(ω_d t)
    omega_d = np.sqrt(max(0.0, omega0**2 - beta**2))
    t_fit = np.linspace(0.0, times[-1], 400)
    D_fit = D0 * np.exp(-beta * t_fit) * np.cos(omega_d * t_fit)

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    ax = axes[0]
    ax.plot(times, deform, color=COLORS[0], lw=0.8, label="Simulation $D(t)$")
    ax.plot(t_fit, D_fit, color="r", ls="--", lw=1.2,
            label=f"Prosperetti: $D_0 e^{{-\\beta t}}\\cos(\\omega_d t)$")
    ax.plot(t_fit,  D0 * np.exp(-beta * t_fit), "k:", lw=0.8, alpha=0.6,
            label="Envelope $\\pm D_0 e^{-\\beta t}$")
    ax.plot(t_fit, -D0 * np.exp(-beta * t_fit), "k:", lw=0.8, alpha=0.6)
    ax.set_xlabel("$t$"); ax.set_ylabel("$D = (L-B)/(L+B)$")
    ax.set_title("Capillary wave oscillation")
    ax.legend(fontsize=7)

    # Volume conservation
    ax = axes[1]
    ax.semilogy(times, np.array(res["vol_err"]) + 1e-16,
                color=COLORS[1])
    ax.set_xlabel("$t$"); ax.set_ylabel("$|\\Delta V|/V_0$")
    ax.set_title("Volume conservation")

    fig.suptitle(
        f"Capillary wave  ($\\rho_l/\\rho_g = {int(RHO_L/RHO_G)}$,"
        f"  $T_0 = {T0:.3f}$,  $\\beta = {beta:.3f}$)",
        fontsize=11)
    fig.tight_layout()
    return fig


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()

    npz_path = OUT / "data.npz"

    if args.plot_only:
        res = load_results(npz_path)
    else:
        res = run()
        save_results(npz_path, {k: v for k, v in res.items()
                                if isinstance(v, (np.ndarray, float))})

    fig = plot(res)
    save_figure(fig, OUT / "capillary_wave.pdf")
    print(f"[exp13-2] saved → {OUT}")


if __name__ == "__main__":
    main()
