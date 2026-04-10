#!/usr/bin/env python3
"""[13-5] Two-droplet head-on collision — coalescence and bouncing regimes.

Paper ref: §13.5 (sec:val_droplet_collision)

Two identical liquid droplets (R=0.25) move toward each other in quiescent
gas.  The Weber number controls the outcome: low We → coalescence, high We
→ reflexive separation.  Sweeps We ∈ {0.5, 2.0, 5.0}.

Config : experiment/ch13/config/exp13_05_droplet_collision.yaml
Output : experiment/ch13/results/exp13_05/

Usage
-----
  python experiment/ch13/exp13_05_droplet_collision.py
  python experiment/ch13/exp13_05_droplet_collision.py --plot-only
"""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.config_io import load_experiment_config
from twophase.ns_pipeline import run_simulation
from twophase.plot_factory import generate_figures
from twophase.experiment import (
    apply_style, experiment_argparser,
    save_results,
    COLORS,
)

apply_style()

CONFIG   = pathlib.Path(__file__).parent / "config" / "exp13_05_droplet_collision.yaml"
OUT_DIR  = pathlib.Path(__file__).parent / "results" / "exp13_05"
WE_SWEEP = [0.5, 2.0, 5.0]
U0       = 0.1      # approach speed
D_DROP   = 0.5      # droplet diameter


def run_sweep():
    cfg_base = load_experiment_config(CONFIG)
    ph = cfg_base.physics
    all_results = {}

    for We in WE_SWEEP:
        print(f"\n  === We={We:.1f} ===")
        # σ = ρ_l v₀² d / We
        sigma = ph.rho_l * U0 ** 2 * D_DROP / We
        cfg = cfg_base.override(**{"physics.sigma": sigma})
        results = run_simulation(cfg)
        all_results[f"We_{We:.1f}"] = results
        vol_err_final = float(results["volume_conservation"][-1]) if "volume_conservation" in results else float("nan")
        print(f"    σ={sigma:.4f}  |ΔV|/V₀={vol_err_final:.2e}")

    return all_results


def plot_summary(all_results):
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, (key, res) in enumerate(all_results.items()):
        t = res.get("times", np.array([]))
        vol = res.get("volume_conservation", np.array([]))
        ax.semilogy(t, vol + 1e-16, color=COLORS[i % len(COLORS)],
                    label=key.replace("We_", "We="))
    ax.set_xlabel("t")
    ax.set_ylabel("|ΔV|/V₀")
    ax.set_title("§13.5 Droplet collision — volume conservation")
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
        all_results = {}
        for We in WE_SWEEP:
            key = f"We_{We:.1f}"
            k_t = f"{key}_times"
            k_v = f"{key}_vol"
            if k_t in raw:
                all_results[key] = {
                    "times":               raw[k_t],
                    "volume_conservation": raw.get(k_v, np.array([])),
                }
    else:
        all_results = run_sweep()
        flat = {}
        for key, res in all_results.items():
            flat[f"{key}_times"] = res.get("times", np.array([]))
            flat[f"{key}_vol"]   = res.get("volume_conservation", np.array([]))
        save_results(npz_path, flat)

        # YAML figures for base case (We=2.0)
        if "We_2.0" in all_results:
            cfg = load_experiment_config(CONFIG)
            generate_figures(cfg, all_results["We_2.0"], OUT_DIR)

    fig = plot_summary(all_results)
    fig.savefig(OUT_DIR / "we_sweep_volume.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"[exp13-5] saved → {OUT_DIR}")


if __name__ == "__main__":
    main()
