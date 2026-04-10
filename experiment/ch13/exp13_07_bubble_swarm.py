#!/usr/bin/env python3
"""[13-7] Multiple bubble swarm rising in periodic domain (N=9 bubbles).

Paper ref: §13.7 (sec:val_bubble_swarm)

Array of 9 bubbles in a doubly-periodic 3×3 domain.  Measures effective
swarm rise velocity U_swarm vs. the Tryggvason (2001) DNS reference.
Void fraction α ≈ 0.196.

Config : experiment/ch13/config/exp13_07_bubble_swarm.yaml
Output : experiment/ch13/results/exp13_07/

Usage
-----
  python experiment/ch13/exp13_07_bubble_swarm.py
  python experiment/ch13/exp13_07_bubble_swarm.py --plot-only
"""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np

from twophase.config_io import load_experiment_config
from twophase.ns_pipeline import run_simulation
from twophase.plot_factory import generate_figures
from twophase.experiment import (
    apply_style, experiment_argparser,
    save_results,
)

apply_style()

CONFIG  = pathlib.Path(__file__).parent / "config" / "exp13_07_bubble_swarm.yaml"
OUT_DIR = pathlib.Path(__file__).parent / "results" / "exp13_07"


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = OUT_DIR / "data.npz"

    cfg = load_experiment_config(CONFIG)
    ph = cfg.physics
    print(f"[exp13-7] σ={ph.sigma:.4f}  μ={ph.mu:.5f}"
          f"  ρ_l/ρ_g={ph.rho_l/ph.rho_g:.0f}")

    if args.plot_only:
        results = dict(np.load(npz_path, allow_pickle=True))
    else:
        print("[exp13-7] Running 9-bubble swarm simulation (T=20, long run)...")
        results = run_simulation(cfg)
        save_results(npz_path,
                     {k: v for k, v in results.items()
                      if isinstance(v, np.ndarray)})

    generate_figures(cfg, results, OUT_DIR)

    if "mean_rise_velocity" in results and len(results["mean_rise_velocity"]) > 0:
        u_swarm = float(np.mean(results["mean_rise_velocity"][-100:]))
        print(f"[exp13-7] U_swarm (mean last 100 steps) = {u_swarm:.4f}")

    print(f"[exp13-7] saved → {OUT_DIR}")


if __name__ == "__main__":
    main()
