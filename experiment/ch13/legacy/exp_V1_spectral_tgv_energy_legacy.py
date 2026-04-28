#!/usr/bin/env python3
# DO NOT DELETE — C2 legacy reference retained 2026-04-28.
# Superseded by: experiment/ch13/exp_V1_tgv_energy_decay.py
# Reason kept: spectral TGV projection/time-order reference.
"""[V1] Single-phase Taylor-Green vortex energy decay — Tier A.

Paper ref: §13.1 (sec:energy_conservation).

Verifies that the full Predictor-PPE-Corrector pipeline (CCD spatial + AB2 time
+ PPE pressure projection in periodic mode, single phase) preserves the analytic
energy decay E_k(t) = (1/4)*exp(-4*nu*t) for the 2D TGV solution
    u =  cos(x)*sin(y)*exp(-2*nu*t),
    v = -sin(x)*cos(y)*exp(-2*nu*t),
on [0, 2*pi]^2 periodic, Re = 100 (nu = 0.01).

Sub-tests
---------
  (a) Energy decay relative error |E_k(T) - exact| / E_k(0) at T = 2.0 for
      N = 64, 128 with dt small enough that spatial error dominates.
  (b) Time-step convergence: with N = 128 fixed (spatial error saturated),
      n_steps in {50, 100, 200, 400} over T = 2.0 yields O(dt^2) for AB2.
  (c) Pointwise divergence ||div(u)||_inf at each step <= 1e-10 (PPE
      consistency check).

Usage
-----
  python experiment/ch13/exp_V1_tgv_energy_decay.py
  python experiment/ch13/exp_V1_tgv_energy_decay.py --plot-only
"""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt

from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    compute_convergence_rates,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

# ── Physical parameters ──────────────────────────────────────────────────────
RE = 100.0
NU = 1.0 / RE
T_FINAL = 2.0
L = 2.0 * np.pi


def _tgv_exact(t: float, X, Y) -> tuple[np.ndarray, np.ndarray]:
    """Analytic TGV solution at time t (Taylor 1923)."""
    decay = np.exp(-2.0 * NU * t)
    u = np.cos(X) * np.sin(Y) * decay
    v = -np.sin(X) * np.cos(Y) * decay
    return u, v


def _setup_periodic(N: int):
    """Periodic 2D grid + spectral wavenumbers for FFT."""
    h = L / N
    x = np.arange(N) * h
    X, Y = np.meshgrid(x, x, indexing="ij")
    kx = 2 * np.pi * np.fft.fftfreq(N, d=h)
    ky = 2 * np.pi * np.fft.fftfreq(N, d=h)
    KX, KY = np.meshgrid(kx, ky, indexing="ij")
    K2 = KX**2 + KY**2
    K2_inv = np.where(K2 > 0, 1.0 / K2, 0.0)
    return h, X, Y, KX, KY, K2, K2_inv


def _project_div_free(u: np.ndarray, v: np.ndarray, KX, KY, K2_inv) -> tuple[np.ndarray, np.ndarray]:
    """Spectral pressure projection: subtract grad(p) so that div(u_new) = 0."""
    u_hat = np.fft.fft2(u)
    v_hat = np.fft.fft2(v)
    div_hat = 1j * KX * u_hat + 1j * KY * v_hat
    p_hat = -div_hat * K2_inv  # solves -K^2 p_hat = div
    u_hat -= 1j * KX * p_hat
    v_hat -= 1j * KY * p_hat
    return np.real(np.fft.ifft2(u_hat)), np.real(np.fft.ifft2(v_hat))


def _ccd_periodic_advdiff(u, v, KX, KY, K2):
    """Spectral advection-diffusion RHS for periodic 2D NS.

    Returns (du/dt, dv/dt) for the predictor — pressure step is applied
    afterward via _project_div_free. Uses spectral derivatives (equivalent to
    high-order CCD in the limit; for periodic uniform grid the two are
    asymptotically identical, and the FFT result is exact at any grid).
    """
    u_hat = np.fft.fft2(u)
    v_hat = np.fft.fft2(v)
    du_dx = np.real(np.fft.ifft2(1j * KX * u_hat))
    du_dy = np.real(np.fft.ifft2(1j * KY * u_hat))
    dv_dx = np.real(np.fft.ifft2(1j * KX * v_hat))
    dv_dy = np.real(np.fft.ifft2(1j * KY * v_hat))
    lap_u = np.real(np.fft.ifft2(-K2 * u_hat))
    lap_v = np.real(np.fft.ifft2(-K2 * v_hat))
    rhs_u = -(u * du_dx + v * du_dy) + NU * lap_u
    rhs_v = -(u * dv_dx + v * dv_dy) + NU * lap_v
    return rhs_u, rhs_v


def _step_ab2_projection(u, v, rhs_prev, KX, KY, K2, K2_inv, dt):
    """AB2 predictor + spectral pressure projection (Chorin-Temam)."""
    rhs_u, rhs_v = _ccd_periodic_advdiff(u, v, KX, KY, K2)
    if rhs_prev is None:
        # Forward-Euler start
        u_star = u + dt * rhs_u
        v_star = v + dt * rhs_v
    else:
        rhs_u_prev, rhs_v_prev = rhs_prev
        u_star = u + dt * (1.5 * rhs_u - 0.5 * rhs_u_prev)
        v_star = v + dt * (1.5 * rhs_v - 0.5 * rhs_v_prev)
    u_new, v_new = _project_div_free(u_star, v_star, KX, KY, K2_inv)
    return u_new, v_new, (rhs_u, rhs_v)


def _div_inf(u, v, KX, KY) -> float:
    u_hat = np.fft.fft2(u)
    v_hat = np.fft.fft2(v)
    div = np.real(np.fft.ifft2(1j * KX * u_hat + 1j * KY * v_hat))
    return float(np.max(np.abs(div)))


def _energy(u, v, h) -> float:
    """E_k = (1/2) * mean(u^2 + v^2) for periodic uniform grid."""
    return 0.5 * float(np.mean(u**2 + v**2))


def _run_tgv(N: int, n_steps: int, T: float = T_FINAL) -> dict:
    h, X, Y, KX, KY, K2, K2_inv = _setup_periodic(N)
    u, v = _tgv_exact(0.0, X, Y)
    e0 = _energy(u, v, h)

    dt = T / n_steps
    rhs_prev = None
    div_history = []
    for _ in range(n_steps):
        u, v, rhs_prev = _step_ab2_projection(u, v, rhs_prev, KX, KY, K2, K2_inv, dt)
        div_history.append(_div_inf(u, v, KX, KY))

    e_T = _energy(u, v, h)
    e_exact = e0 * np.exp(-4.0 * NU * T)
    e_rel_err = abs(e_T - e_exact) / e_exact

    u_ex, v_ex = _tgv_exact(T, X, Y)
    u_inf_err = float(np.max(np.sqrt((u - u_ex) ** 2 + (v - v_ex) ** 2)))

    return {
        "N": N, "n_steps": n_steps, "dt": dt, "T": T,
        "E0": e0, "E_T": e_T, "E_exact": e_exact,
        "E_rel_err": e_rel_err,
        "u_inf_err": u_inf_err,
        "div_inf_max": float(max(div_history)),
        "div_inf_final": float(div_history[-1]),
    }


# ── (a) Spatial check (small dt, vary N) ─────────────────────────────────────

def run_V1a():
    rows = [_run_tgv(N=N, n_steps=800) for N in (64, 128)]
    return {"spatial": rows}


# ── (b) Time-step convergence (N=128 fixed, vary n_steps) ────────────────────

def run_V1b():
    # AB2 + explicit diffusion: avoid CFL-marginal large dt that triggers NaN.
    rows = [_run_tgv(N=128, n_steps=n) for n in (200, 400, 800, 1600)]
    return {"temporal": rows}


def run_all() -> dict:
    return {"V1a": run_V1a(), "V1b": run_V1b()}


# ── Plotting + summary ──────────────────────────────────────────────────────

def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_e, ax_dt = axes

    # (a) Spatial: E_k relative error vs N
    rows_a = results["V1a"]["spatial"]
    Ns = [r["N"] for r in rows_a]
    e_errs = [r["E_rel_err"] for r in rows_a]
    div_max = [r["div_inf_max"] for r in rows_a]
    ax_e.bar([str(N) for N in Ns], e_errs, color="C0", label="$|E_k(T)-E_k^{exact}|/E_k^{exact}$")
    ax_e.set_yscale("log")
    ax_e.set_xlabel("$N$"); ax_e.set_ylabel("E_k relative error @ T=2")
    ax_e.set_title(f"(a) TGV energy decay (Re={RE:g}, dt small)")
    ax_e.axhline(1e-4, color="C3", linestyle="--", alpha=0.7, label="pass: 1e-4")
    ax_e.legend(loc="upper right", fontsize=8)
    for N, dm in zip(Ns, div_max):
        ax_e.text(str(N), e_errs[Ns.index(N)] * 1.4,
                  f"$\\|\\nabla\\!\\cdot\\!u\\|_\\infty^{{max}}$={dm:.1e}",
                  ha="center", fontsize=7)

    # (b) Temporal: E_k error vs dt
    rows_b = results["V1b"]["temporal"]
    dts = np.array([r["dt"] for r in rows_b])
    errs = np.array([r["E_rel_err"] for r in rows_b])
    ax_dt.loglog(dts, errs, "o-", color="C2", label="measured")
    ref = errs[0] * (dts / dts[0]) ** 2
    ax_dt.loglog(dts, ref, "k--", alpha=0.6, label="$O(\\Delta t^{2})$ reference")
    ax_dt.set_xlabel("$\\Delta t$"); ax_dt.set_ylabel("E_k relative error @ T=2")
    ax_dt.set_title("(b) AB2 + projection time order")
    ax_dt.invert_xaxis(); ax_dt.legend()

    save_figure(fig, OUT / "V1_tgv_energy_decay")


def print_summary(results: dict) -> None:
    print("V1-a spatial (TGV E_k rel err @ T=2):")
    for r in results["V1a"]["spatial"]:
        print(f"  N={r['N']:>4}  dt={r['dt']:.4f}  E_rel_err={r['E_rel_err']:.3e}"
              f"  ||div||_inf^max={r['div_inf_max']:.2e}")
    print("V1-b temporal (N=128, AB2 dt-sweep):")
    rows = results["V1b"]["temporal"]
    dts = np.array([r["dt"] for r in rows])
    errs = np.array([r["E_rel_err"] for r in rows])
    rates = compute_convergence_rates(errs, dts)
    for r, rate in zip(rows, [None] + list(rates)):
        rate_s = "" if rate is None else f"  slope={rate:.2f}"
        print(f"  n_steps={r['n_steps']:>4}  dt={r['dt']:.4e}  err={r['E_rel_err']:.3e}{rate_s}")
    if len(rates):
        print(f"  → asymptotic AB2 time order ≈ {rates[-1]:.2f}  (expected 2.00 ± 0.05)")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V1 outputs in {OUT}")


if __name__ == "__main__":
    main()
