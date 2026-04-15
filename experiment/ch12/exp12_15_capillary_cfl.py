#!/usr/bin/env python3
"""[12-15] Capillary CFL scaling for a linear 1-D capillary wave.

This experiment intentionally isolates the capillary timestep restriction from
the full 2-D CSF/PPE/CLS pipeline.  The evolved model is the linear inviscid
capillary-wave equation in Fourier form,

    eta_tt = -(sigma / (rho_l + rho_g)) |D|^3 eta,

whose dispersion relation is omega(k)^2 = sigma |k|^3 / (rho_l + rho_g).
The stability limit is measured for explicit RK4 by binary searching dt.

Output
------
  experiment/ch12/results/15_capillary_cfl/data.npz
  experiment/ch12/results/15_capillary_cfl/capillary_cfl.pdf
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()

OUT = experiment_dir(__file__, "15_capillary_cfl")
NPZ = OUT / "data.npz"

RHO_L = 2.0
RHO_G = 1.0
SIGMA = 1.0
L = 1.0
GRIDS = [32, 64, 128, 256]
N_PROBE_STEPS = 400
BISECT_TOL = 0.005
GROW_LIMIT = 10.0


def _rhs(eta, vel, k_abs_3):
    """Return (eta_t, vel_t) for eta_tt = -c |D|^3 eta."""
    eta_hat = np.fft.fft(eta)
    acc = np.fft.ifft(-k_abs_3 * eta_hat).real
    return vel, acc


def _rk4_step(eta, vel, dt, k_abs_3):
    k1_e, k1_v = _rhs(eta, vel, k_abs_3)
    k2_e, k2_v = _rhs(eta + 0.5 * dt * k1_e, vel + 0.5 * dt * k1_v, k_abs_3)
    k3_e, k3_v = _rhs(eta + 0.5 * dt * k2_e, vel + 0.5 * dt * k2_v, k_abs_3)
    k4_e, k4_v = _rhs(eta + dt * k3_e, vel + dt * k3_v, k_abs_3)
    eta_new = eta + (dt / 6.0) * (k1_e + 2.0 * k2_e + 2.0 * k3_e + k4_e)
    vel_new = vel + (dt / 6.0) * (k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v)
    return eta_new, vel_new


def _is_stable(N, dt):
    h = L / N
    x = np.arange(N) * h
    eta0 = np.sin(np.pi * x / h) + 1.0e-3 * np.sin(2.0 * np.pi * x / L)
    # The first term is the Nyquist-scale stress test; for even N it is zero
    # at nodes, so the low-mode perturbation keeps the state nonzero.  Stability
    # is controlled by the operator's largest Fourier eigenfrequency.
    if np.max(np.abs(eta0)) < 1e-14:
        eta0 = np.cos(np.pi * x / h)
    eta = eta0.copy()
    vel = np.zeros_like(eta)
    amp0 = max(float(np.max(np.abs(eta))), 1e-30)

    k = 2.0 * np.pi * np.fft.fftfreq(N, d=h)
    k_abs_3 = (SIGMA / (RHO_L + RHO_G)) * np.abs(k) ** 3

    for _ in range(N_PROBE_STEPS):
        eta, vel = _rk4_step(eta, vel, dt, k_abs_3)
        amp = max(float(np.max(np.abs(eta))), float(np.max(np.abs(vel))))
        if not np.isfinite(amp) or amp > GROW_LIMIT * amp0:
            return False
    return True


def run_single(N):
    h = L / N
    dt_sigma = np.sqrt((RHO_L + RHO_G) * h ** 3 / (2.0 * np.pi * SIGMA))

    dt_lo = 0.05 * dt_sigma
    dt_hi = 4.0 * dt_sigma

    while not _is_stable(N, dt_lo):
        dt_lo *= 0.5
    while _is_stable(N, dt_hi):
        dt_hi *= 1.5

    for _ in range(80):
        dt_mid = 0.5 * (dt_lo + dt_hi)
        if _is_stable(N, dt_mid):
            dt_lo = dt_mid
        else:
            dt_hi = dt_mid
        if (dt_hi - dt_lo) / max(dt_lo, 1e-300) < BISECT_TOL:
            break

    return {
        "N": N,
        "h": h,
        "dt_max": dt_lo,
        "dt_sigma": dt_sigma,
        "ratio": dt_lo / dt_sigma,
    }


def make_figures(results):
    Ns = np.array([r["N"] for r in results])
    hs = np.array([r["h"] for r in results])
    dt_max = np.array([r["dt_max"] for r in results])
    dt_sigma = np.array([r["dt_sigma"] for r in results])
    ratios = np.array([r["ratio"] for r in results])

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    ax = axes[0]
    ax.loglog(hs, dt_max, marker=MARKERS[0], color=COLORS[0], lw=1.5,
              label=r"$\Delta t_{\max}$")
    ax.loglog(hs, dt_sigma, marker=MARKERS[1], color=COLORS[1], lw=1.5,
              ls="--", label=r"$\Delta t_\sigma$")
    ax.loglog(hs, dt_sigma[0] * (hs / hs[0]) ** 1.5,
              "k:", lw=1.0, alpha=0.7, label=r"$h^{3/2}$")
    ax.invert_xaxis()
    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$\Delta t$")
    ax.set_title("(a) Capillary CFL scaling")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.semilogx(Ns, ratios, marker=MARKERS[2], color=COLORS[2], lw=1.5)
    ax.set_xlabel("$N$")
    ax.set_ylabel(r"$\Delta t_{\max}/\Delta t_\sigma$")
    ax.set_title("(b) Ratio to capillary scale")
    ax.grid(True, alpha=0.3, which="both")

    fig.tight_layout()
    save_figure(fig, OUT / "capillary_cfl")


def _pack(results, exponent, mean_ratio):
    return {
        "Ns": np.array([r["N"] for r in results], dtype=int),
        "hs": np.array([r["h"] for r in results], dtype=float),
        "dt_maxs": np.array([r["dt_max"] for r in results], dtype=float),
        "dt_sigmas": np.array([r["dt_sigma"] for r in results], dtype=float),
        "ratios": np.array([r["ratio"] for r in results], dtype=float),
        "exponent": np.array(exponent),
        "mean_ratio": np.array(mean_ratio),
    }


def _unpack(d):
    key = "dt_sigmas" if "dt_sigmas" in d else "dt_theorys"
    return [
        {
            "N": int(d["Ns"][i]),
            "h": float(d["hs"][i]),
            "dt_max": float(d["dt_maxs"][i]),
            "dt_sigma": float(d[key][i]),
            "ratio": float(d["ratios"][i]),
        }
        for i in range(len(d["Ns"]))
    ]


def main():
    print("\n" + "=" * 72)
    print("  [12-15] Linear capillary CFL scaling")
    print("=" * 72 + "\n")
    print(f"  {'N':>5} | {'h':>10} | {'dt_max':>12} | {'dt_sigma':>12} | {'ratio':>8}")
    print("  " + "-" * 60)

    results = []
    for N in GRIDS:
        r = run_single(N)
        results.append(r)
        print(f"  {r['N']:>5} | {r['h']:>10.6f} | {r['dt_max']:>12.3e} | "
              f"{r['dt_sigma']:>12.3e} | {r['ratio']:>8.3f}")

    hs = np.array([r["h"] for r in results])
    dt_max = np.array([r["dt_max"] for r in results])
    exponent = float(np.polyfit(np.log(hs), np.log(dt_max), 1)[0])
    mean_ratio = float(np.mean([r["ratio"] for r in results]))

    print(f"\n  Scaling exponent: {exponent:.4f}  (target: 1.5)")
    print(f"  Mean ratio Δt_max/Δt_sigma: {mean_ratio:.4f}")
    print(f"\n  Exponent check : {'PASS' if abs(exponent - 1.5) < 0.03 else 'FAIL'}")
    print(f"  Ratio check    : {'PASS' if np.std([r['ratio'] for r in results]) / mean_ratio < 0.05 else 'FAIL'}")

    save_results(NPZ, _pack(results, exponent, mean_ratio))
    make_figures(results)


if __name__ == "__main__":
    args = experiment_argparser("Linear capillary CFL scaling").parse_args()
    if args.plot_only:
        make_figures(_unpack(load_results(NPZ)))
    else:
        main()
