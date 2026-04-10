#!/usr/bin/env python3
"""[13-4] Rayleigh-Taylor instability with surface tension (σ sweep).

Paper ref: §13.4 (sec:val_rt_sigma)

Shows stabilization of the RT instability by surface tension.  Sweeps
σ ∈ {0.0, 0.02, 0.05}.  At σ=0.05, the k=2π mode is near the cutoff
k_c = sqrt(g(ρ_l−ρ_g)/σ) and growth is strongly suppressed.

Config : experiment/ch13/config/exp13_04_rt_sigma.yaml
Output : experiment/ch13/results/exp13_04/

Usage
-----
  python experiment/ch13/exp13_04_rt_sigma.py
  python experiment/ch13/exp13_04_rt_sigma.py --plot-only
"""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.config_io import load_experiment_config
from twophase.ns_pipeline import run_simulation
from twophase.experiment import (
    apply_style, experiment_argparser,
    save_results,
    COLORS,
)

apply_style()

CONFIG   = pathlib.Path(__file__).parent / "config" / "exp13_04_rt_sigma.yaml"
OUT_DIR  = pathlib.Path(__file__).parent / "results" / "exp13_04"
SIGMA_SWEEP = [0.0, 0.02, 0.05]


def _rt_growth_rate(g, rho_l, rho_g, sigma, k):
    """Linear RT growth rate ω² = gk(ρ_l−ρ_g)/(ρ_l+ρ_g) − σk³/(ρ_l+ρ_g)."""
    rho_sum = rho_l + rho_g
    w2 = g * k * (rho_l - rho_g) / rho_sum - sigma * k ** 3 / rho_sum
    return math.sqrt(max(w2, 0.0))


def run_sweep():
    cfg_base = load_experiment_config(CONFIG)
    ph = cfg_base.physics
    k = 2.0 * math.pi  # k = 2π for wavelength = 1

    all_results = {}
    for sigma in SIGMA_SWEEP:
        print(f"\n  === σ={sigma:.3f} ===")
        cfg = cfg_base.override(**{"physics.sigma": sigma})
        results = run_simulation(cfg)
        all_results[f"sigma_{sigma:.3f}"] = results

        omega = _rt_growth_rate(ph.g_acc, ph.rho_l, ph.rho_g, sigma, k)
        if sigma > 0.0:
            k_c = math.sqrt(ph.g_acc * (ph.rho_l - ph.rho_g) / sigma)
        else:
            k_c = float("inf")
        print(f"    ω={omega:.4f}  k_c={k_c:.3f}  (k={k:.3f})")

    return all_results


def plot_summary(all_results):
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, (key, res) in enumerate(all_results.items()):
        t = res.get("times", np.array([]))
        eta = res.get("interface_amplitude", np.array([]))
        sigma_label = key.replace("sigma_", "σ=")
        ax.semilogy(t, eta + 1e-16, color=COLORS[i % len(COLORS)],
                    label=sigma_label)
    ax.set_xlabel("t")
    ax.set_ylabel("Interface amplitude η")
    ax.set_title("§13.4 RT instability — σ sweep")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = OUT_DIR / "data_sweep.npz"

    if args.plot_only:
        raw = dict(np.load(npz_path, allow_pickle=True))
        # Reconstruct dict of dicts from flat npz
        all_results = {}
        for sigma in SIGMA_SWEEP:
            key = f"sigma_{sigma:.3f}"
            times_key = f"{key}_times"
            amp_key   = f"{key}_amplitude"
            if times_key in raw:
                all_results[key] = {
                    "times":               raw[times_key],
                    "interface_amplitude": raw.get(amp_key, np.array([])),
                }
    else:
        all_results = run_sweep()
        flat = {}
        for key, res in all_results.items():
            flat[f"{key}_times"]     = res.get("times", np.array([]))
            flat[f"{key}_amplitude"] = res.get("interface_amplitude", np.array([]))
        save_results(npz_path, flat)

    fig = plot_summary(all_results)
    fig.savefig(OUT_DIR / "rt_sigma_sweep.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"[exp13-4] saved → {OUT_DIR}")


if __name__ == "__main__":
    main()
