#!/usr/bin/env python3
"""[U8] Time integration suite — Tier V.

Paper ref: Chapter 12 U8 (sec:U8_time_integration; paper/sections/12u8_time_integration.tex).

Sub-tests
---------
  (a) TVD-RK3 ODE 3rd-order convergence + stability region
      ODE  q' = -q,  q(0)=1,  q(1)=e^{-1}
      n = 4, 8, …, 512, expected slope 3.00
  (b) EXT2/AB2 ODE 2nd-order (forward-Euler start)
      n = 16, 32, …, 512, expected slope 2.00
  (c) implicit-BDF2 diffusion MMS 2nd-order
      2D periodic heat eq. u_t = ν ∇²u, ν=0.01,
      u_exact = exp(-8π²ν t) sin(2πx) sin(2πy), N=64,
      Δt = T/[10..320], expected slope 2.00 + A-stable damping
  (d) Viscous 3-layer Layer A/B/C accuracy (full variable operator)
      Layer A: μ_l/μ_g=1   implicit-BDF2 full operator → O(Δt²)
      Layer B: μ_l/μ_g≥10  implicit-BDF2 full operator → O(Δt²)
      Layer C: HFE-blend smoothed μ → O(Δt²)

Usage
-----
  python experiment/ch12/exp_U8_time_integration_suite.py
  python experiment/ch12/exp_U8_time_integration_suite.py --plot-only
"""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt

from twophase.time_integration.tvd_rk3 import tvd_rk3
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    convergence_loglog, compute_convergence_rates,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures" / "ch12_u8_time_integration_suite"


# ── U8-a: TVD-RK3 ODE 3rd-order (production integrator) ─────────────────────

def _ode_rk3_error(n_steps: int) -> float:
    """Drives production `twophase.time_integration.tvd_rk3` on scalar ODE
    q' = -q,  q(0) = 1,  expected order 3 for Shu-Osher TVD-RK3."""
    rhs = lambda q: -q
    dt = 1.0 / n_steps
    q = np.float64(1.0)
    for _ in range(n_steps):
        q = tvd_rk3(np, q, dt, rhs)
    return float(abs(q - np.exp(-1.0)))


def run_U8a():
    n_list = [4, 8, 16, 32, 64, 128, 256, 512]
    rows = [{"n": n, "dt": 1.0 / n, "err": _ode_rk3_error(n)} for n in n_list]
    return {"tvd_rk3": rows}


# ── U8-b: EXT2/AB2 ODE 2nd-order (ODE benchmark) ────────────────────────────
# NOTE: This is an ODE benchmark, NOT the production integrator.
# Production EXT2 lives inside the NS predictor history path,
# which is heavily NS-coupled (requires FlowState, ConvectionTerm, ViscousTerm,
# ...) and cannot be invoked on a scalar ODE. The inline EXT2/AB2 formula below
# exposes the same second-order extrapolation skeleton on a scalar RHS.

def _ode_ext2_error(n_steps: int) -> float:
    """EXT2/AB2 with forward-Euler startup (ODE benchmark)."""
    rhs = lambda q: -q
    dt = 1.0 / n_steps
    q_prev = 1.0
    f_prev = rhs(q_prev)
    # FE start
    q = q_prev + dt * f_prev
    f_curr = rhs(q)
    # AB2: q_{n+1} = q_n + dt * (3/2 f_n - 1/2 f_{n-1})
    for _ in range(n_steps - 1):
        q_new = q + dt * (1.5 * f_curr - 0.5 * f_prev)
        f_prev = f_curr
        q = q_new
        f_curr = rhs(q)
    return float(abs(q - np.exp(-1.0)))


def run_U8b():
    n_list = [16, 32, 64, 128, 256, 512]
    rows = [{"n": n, "dt": 1.0 / n, "err": _ode_ext2_error(n)} for n in n_list]
    return {"ext2": rows}


# ── U8-c: implicit-BDF2 diffusion 2D MMS ─────────────────────────────────────

def _bdf2_diffusion_2d_error(N: int, n_t: int, T: float, nu: float) -> float:
    """2D periodic heat eq via BDF1 startup + implicit-BDF2 spectral Laplacian.

    For periodic BC, ∇² is diagonal in Fourier basis. The first step uses
    backward Euler, then BDF2 applies:
        (3 u^{n+1} - 4 u^n + u^{n-1}) / (2 dt) = -ν K² u^{n+1}.
    """
    h = 1.0 / N
    dt = T / n_t
    x = np.arange(N) * h  # periodic nodes
    X, Y = np.meshgrid(x, x, indexing="ij")
    u0 = np.sin(2 * np.pi * X) * np.sin(2 * np.pi * Y)
    u_hat = np.fft.fft2(u0)

    kx = 2 * np.pi * np.fft.fftfreq(N, d=h)
    ky = 2 * np.pi * np.fft.fftfreq(N, d=h)
    KX, KY = np.meshgrid(kx, ky, indexing="ij")
    K2 = KX**2 + KY**2

    if n_t == 1:
        u_hat_T = u_hat / (1.0 + nu * dt * K2)
    else:
        u_prev = u_hat
        u_curr = u_hat / (1.0 + nu * dt * K2)
        denom = 3.0 + 2.0 * nu * dt * K2
        for _ in range(1, n_t):
            u_next = (4.0 * u_curr - u_prev) / denom
            u_prev, u_curr = u_curr, u_next
        u_hat_T = u_curr
    u_T = np.real(np.fft.ifft2(u_hat_T))

    decay = np.exp(-8 * np.pi**2 * nu * T)
    u_exact = decay * np.sin(2 * np.pi * X) * np.sin(2 * np.pi * Y)
    return float(np.max(np.abs(u_T - u_exact)))


def _bdf2_stability_max_growth(N: int, n_t: int, T: float, nu: float) -> float:
    """Return max |u| growth ratio over T to assess BDF2 A-stable damping."""
    h = 1.0 / N
    dt = T / n_t
    x = np.arange(N) * h
    X, Y = np.meshgrid(x, x, indexing="ij")
    u = np.sin(2 * np.pi * X) * np.sin(2 * np.pi * Y) + 0.1 * np.sin(8 * np.pi * X)
    u_hat = np.fft.fft2(u)
    kx = 2 * np.pi * np.fft.fftfreq(N, d=h)
    ky = 2 * np.pi * np.fft.fftfreq(N, d=h)
    KX, KY = np.meshgrid(kx, ky, indexing="ij")
    K2 = KX**2 + KY**2
    init_max = float(np.max(np.abs(np.real(np.fft.ifft2(u_hat)))))
    if n_t == 1:
        u_hat_T = u_hat / (1.0 + nu * dt * K2)
    else:
        u_prev = u_hat
        u_curr = u_hat / (1.0 + nu * dt * K2)
        denom = 3.0 + 2.0 * nu * dt * K2
        for _ in range(1, n_t):
            u_next = (4.0 * u_curr - u_prev) / denom
            u_prev, u_curr = u_curr, u_next
        u_hat_T = u_curr
    final_max = float(np.max(np.abs(np.real(np.fft.ifft2(u_hat_T)))))
    return final_max / max(init_max, 1e-300)


def _fe_growth_2d(N: int, n_t: int, T: float, nu: float) -> float:
    """Forward-Euler growth factor for comparison (CFL_nu = nu·dt/h² > 0.5 → unstable)."""
    h = 1.0 / N
    dt = T / n_t
    x = np.arange(N) * h
    X, Y = np.meshgrid(x, x, indexing="ij")
    u = np.sin(2 * np.pi * X) * np.sin(2 * np.pi * Y) + 0.1 * np.sin(8 * np.pi * X)
    u_hat = np.fft.fft2(u)
    kx = 2 * np.pi * np.fft.fftfreq(N, d=h)
    ky = 2 * np.pi * np.fft.fftfreq(N, d=h)
    KX, KY = np.meshgrid(kx, ky, indexing="ij")
    K2 = KX**2 + KY**2
    factor = 1.0 - nu * dt * K2
    init_max = float(np.max(np.abs(np.real(np.fft.ifft2(u_hat)))))
    u_hat_T = u_hat * (factor ** n_t)
    final = np.real(np.fft.ifft2(u_hat_T))
    final_max = float(np.max(np.abs(final))) if np.all(np.isfinite(final)) else float("inf")
    return final_max / max(init_max, 1e-300)


def run_U8c():
    N = 64
    T = 0.5
    nu = 0.01
    nt_list = [10, 20, 40, 80, 160, 320]
    rows = [
        {"n_t": nt, "dt": T / nt, "err": _bdf2_diffusion_2d_error(N, nt, T, nu)}
        for nt in nt_list
    ]
    # Stability sweep at fixed N=64, T=0.5: vary dt to span CFL_nu ∈ {0.5, 1, 5, 10}
    h = 1.0 / N
    cfl_targets = [0.5, 1.0, 5.0, 10.0]
    stab = []
    for cfl in cfl_targets:
        dt = cfl * h * h / nu
        nt = max(int(np.ceil(T / dt)), 1)
        bdf2_growth = _bdf2_stability_max_growth(N, nt, T, nu)
        fe_growth = _fe_growth_2d(N, nt, T, nu)
        stab.append({
            "CFL_nu": cfl, "dt": dt, "n_t": nt,
            "bdf2_growth": bdf2_growth, "fe_growth": fe_growth,
        })
    return {"bdf2_diffusion": rows, "N": N, "T": T, "nu": nu, "stability": stab}


# ── U8-d: viscous 3-layer (μ-jump full-operator BDF2 1D MMS) ────────────────

def _build_mu_field_1d(N: int, mu_ratio: float, eps_band: float):
    """Smoothed μ profile: μ(x) = 1 + (μ_l/μ_g − 1) · ½(1 + tanh((x−½)/ε)).

    Returns (x, μ, μ_x) on the (N+1)-node grid.
    """
    x = np.linspace(0.0, 1.0, N + 1)
    phi = x - 0.5
    psi = 0.5 * (1.0 + np.tanh(phi / eps_band))
    dpsi_dx = 0.5 / eps_band / np.cosh(phi / eps_band) ** 2
    mu = 1.0 + (mu_ratio - 1.0) * psi
    mu_x = (mu_ratio - 1.0) * dpsi_dx
    return x, mu, mu_x


def _viscous_layer_1d(layer: str, mu_ratio: float, n_t: int,
                       T: float = 0.02, N: int = 64, alpha: float = 1.0):
    """1D MMS for implicit-BDF2 full-variable-viscosity study (Chapter 12 U8-d).

    PDE         u_t = ∂_x[μ(x) ∂_x u] + s(x,t)        on [0,1], Dirichlet u=0
    Manuf. soln u(x,t) = exp(−α t) sin(πx)
    MMS source  s = u_t,exact − L_full(u_exact)        ← computed via DISCRETE
                                                          face-averaged FD so
                                                          spatial error cancels.

    All layers solve the full conservative variable-coefficient operator
    implicitly. This is the component-level time skeleton of the current
    implicit-BDF2 + DC viscous contract: the DC fixed point has no explicit
    cross-term time lag, so the measured time order should remain second order.

      Layer A (μ=const, μ_l/μ_g = 1) : implicit-BDF2 full operator
      Layer B (μ ∈ {10, 100}, ε=1.5h): implicit-BDF2 full operator
      Layer C (μ ∈ {10, 100}, ε=5h)  : implicit-BDF2 full operator
    """
    h = 1.0 / N
    dt = T / n_t

    if layer == "A":
        x = np.linspace(0.0, 1.0, N + 1)
        mu = np.ones_like(x) * mu_ratio
        mu_x = np.zeros_like(x)
    elif layer == "B":
        x, mu, mu_x = _build_mu_field_1d(N, mu_ratio, eps_band=1.5 * h)
    elif layer == "C":
        x, mu, mu_x = _build_mu_field_1d(N, mu_ratio, eps_band=5.0 * h)
    else:
        raise ValueError(layer)

    sx = np.sin(np.pi * x)
    u = sx.copy()  # IC; u(0)=u(1)=0 by sin

    # Face-averaged μ on staggered points i+1/2 (length N)
    mu_face = 0.5 * (mu[1:] + mu[:-1])
    mu_avg = float(np.mean(mu))

    # Discrete L_full (face-averaged conservative FD): full ∂_x[μ ∂_x u]
    def L_full_apply(u_full):
        out = np.zeros_like(u_full)
        out[1:-1] = (mu_face[1:] * (u_full[2:] - u_full[1:-1])
                     - mu_face[:-1] * (u_full[1:-1] - u_full[:-2])) / h**2
        return out

    # MMS source via DISCRETE operator → spatial error cancels exactly.
    def src_full_disc(t):
        E = np.exp(-alpha * t)
        u_ex = E * sx
        return -alpha * u_ex - L_full_apply(u_ex)

    Ndof = N - 1
    a_l = mu_face[0:N-1] / h**2  # μ_{i-1/2} for i=1..N-1
    a_r = mu_face[1:N] / h**2    # μ_{i+1/2}
    main_L = -(a_l + a_r)
    sub_L = a_l[1:]
    sup_L = a_r[:-1]

    def thomas(a_sub, a_main, a_sup, rhs):
        n = len(a_main)
        c_p = np.zeros(n - 1)
        d_p = np.zeros(n)
        c_p[0] = a_sup[0] / a_main[0]
        d_p[0] = rhs[0] / a_main[0]
        for i in range(1, n):
            denom = a_main[i] - a_sub[i - 1] * c_p[i - 1]
            if i < n - 1:
                c_p[i] = a_sup[i] / denom
            d_p[i] = (rhs[i] - a_sub[i - 1] * d_p[i - 1]) / denom
        out = np.zeros(n)
        out[-1] = d_p[-1]
        for i in range(n - 2, -1, -1):
            out[i] = d_p[i] - c_p[i] * out[i + 1]
        return out

    be_main = np.ones(Ndof) / dt - main_L
    be_sub = -sub_L
    be_sup = -sup_L

    t1 = dt
    rhs_full = u / dt + src_full_disc(t1)
    u_prev = u.copy()
    u_curr = u.copy()
    u_curr[1:-1] = thomas(be_sub, be_main, be_sup, rhs_full[1:-1])

    bdf2_main = 1.5 * np.ones(Ndof) / dt - main_L
    bdf2_sub = -sub_L
    bdf2_sup = -sup_L

    for n_step in range(1, n_t):
        t_np1 = (n_step + 1) * dt
        rhs_full = (2.0 * u_curr - 0.5 * u_prev) / dt + src_full_disc(t_np1)
        u_next = u_curr.copy()
        u_next[1:-1] = thomas(bdf2_sub, bdf2_main, bdf2_sup, rhs_full[1:-1])
        u_prev, u_curr = u_curr, u_next
    u = u_curr

    u_exact_T = np.exp(-alpha * T) * sx
    return float(np.max(np.abs(u - u_exact_T))), float(np.max(np.abs(mu_x))), float(np.mean(mu))


def run_U8d():
    nt_list = [16, 32, 64, 128, 256]
    T = 0.02
    N = 64
    # Layer A is constant-μ (μ_x≡0). Layer B/C carry the ratio sweep.
    cases = [
        ("A", 1.0),
        ("B", 10.0),
        ("B", 100.0),
        ("C", 10.0),
        ("C", 100.0),
    ]
    rows = []
    for layer, mu_r in cases:
        for n_t in nt_list:
            err, mu_x_max, mu_mean = _viscous_layer_1d(layer, mu_r, n_t, T=T, N=N)
            rows.append({
                "layer": layer, "mu_ratio": mu_r,
                "n_t": n_t, "dt": T / n_t,
                "err": err,
                "mu_x_max": mu_x_max, "mu_mean": mu_mean,
            })
    return {"layers": rows, "T": T, "N": N, "cases": cases}


# ── Aggregator + plotting ────────────────────────────────────────────────────

def run_all() -> dict:
    return {
        "U8a": run_U8a(),
        "U8b": run_U8b(),
        "U8c": run_U8c(),
        "U8d": run_U8d(),
    }


def _slope_summary(rows: list[dict], dt_key: str, err_key: str) -> str:
    dts = [r[dt_key] for r in rows]
    errs = [r[err_key] for r in rows]
    rates = compute_convergence_rates(errs, dts)
    finite = [r for r in rates if np.isfinite(r) and r > -10]
    return f"mean={np.mean(finite):.2f}" if finite else "n/a"


def _u8d_cases(rows: list[dict]) -> list[tuple[str, float]]:
    return sorted(
        {(str(r["layer"]), float(r["mu_ratio"])) for r in rows},
        key=lambda item: (item[0], item[1]),
    )


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    ax_a, ax_b = axes[0]
    ax_c, ax_d = axes[1]

    rows_a = results["U8a"]["tvd_rk3"]
    dts_a = [r["dt"] for r in rows_a]
    convergence_loglog(
        ax_a, dts_a,
        {"$|q - e^{-1}|$": [r["err"] for r in rows_a]},
        ref_orders=[3], xlabel="$\\Delta t$", ylabel="abs error",
        title="(a) TVD-RK3 ODE")

    rows_b = results["U8b"]["ext2"]
    dts_b = [r["dt"] for r in rows_b]
    convergence_loglog(
        ax_b, dts_b,
        {"$|q - e^{-1}|$": [r["err"] for r in rows_b]},
        ref_orders=[2], xlabel="$\\Delta t$", ylabel="abs error",
        title="(b) EXT2/AB2 ODE (FE start)")

    rows_c = results["U8c"]["bdf2_diffusion"]
    dts_c = [r["dt"] for r in rows_c]
    convergence_loglog(
        ax_c, dts_c,
        {"$L_\\infty$ ($N=64$)": [r["err"] for r in rows_c]},
        ref_orders=[2], xlabel="$\\Delta t$", ylabel="$L_\\infty$ error",
        title="(c) implicit-BDF2 diffusion MMS")

    rows_d = results["U8d"]["layers"]
    dts_d = sorted({r["dt"] for r in rows_d}, reverse=True)
    cases = _u8d_cases(rows_d)
    series = {}
    for layer, mu_r in cases:
        label = f"L{layer} $\\mu_r={int(mu_r)}$"
        errs = []
        for dt in dts_d:
            hits = [r for r in rows_d if r["layer"] == layer
                    and r["mu_ratio"] == mu_r and abs(r["dt"] - dt) < 1e-12]
            if hits:
                errs.append(hits[0]["err"])
        if errs:
            series[label] = errs
    convergence_loglog(
        ax_d, dts_d, series,
        ref_orders=[1, 2], xlabel="$\\Delta t$", ylabel="$L_\\infty$ error",
        title="(d) Viscous full-operator BDF2")
    ax_d.legend(fontsize=7, ncol=2)

    save_figure(fig, OUT / "U8_time_integration_suite", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    print("U8-a TVD-RK3 ODE       slope:", _slope_summary(results["U8a"]["tvd_rk3"], "dt", "err"))
    print("U8-b EXT2/AB2 ODE      slope:", _slope_summary(results["U8b"]["ext2"], "dt", "err"))
    print("U8-c BDF2 diffusion 2D slope:", _slope_summary(results["U8c"]["bdf2_diffusion"], "dt", "err"))
    print("U8-c BDF2 stability sweep:")
    for s in results["U8c"]["stability"]:
        print(f"  CFL_nu={s['CFL_nu']:>4} dt={s['dt']:.3e} n_t={s['n_t']}"
              f"  BDF2 growth={s['bdf2_growth']:.3e}  FE growth={s['fe_growth']:.3e}")
    print("U8-d viscous full-operator BDF2 (slope by layer × mu_ratio):")
    cases = _u8d_cases(results["U8d"]["layers"])
    for layer, mu_r in cases:
        sub = [r for r in results["U8d"]["layers"]
               if r["layer"] == layer and r["mu_ratio"] == mu_r]
        if sub:
            print(f"  Layer {layer}  mu_ratio={mu_r:>5}  slope:",
                  _slope_summary(sub, "dt", "err"))


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> U8 outputs in {OUT}")


if __name__ == "__main__":
    main()
