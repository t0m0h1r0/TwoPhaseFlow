#!/usr/bin/env python3
"""[13-3] Single rising bubble — Hysing et al. (2009) benchmark (Case 1, modified).

Paper ref: §13.3 (sec:val_rising_bubble)

A gas bubble in a heavier liquid rises under gravity.  Re=35, Eo=10 with
ρ_l/ρ_g = 10 (modified from Hysing Case 1 ρ_l/ρ_g = 1000).  Physical
parameters σ and μ are derived from Re and Eo in the config file.

Config : experiment/ch13/config/exp13_03_rising_bubble.yaml
Output : experiment/ch13/results/exp13_03/

Usage
-----
  python experiment/ch13/exp13_03_rising_bubble.py
  python experiment/ch13/exp13_03_rising_bubble.py --plot-only
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

CONFIG  = pathlib.Path(__file__).parent / "config" / "exp13_03_rising_bubble.yaml"
OUT_DIR = pathlib.Path(__file__).parent / "results" / "exp13_03"


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = OUT_DIR / "data.npz"

    cfg = load_experiment_config(CONFIG)
    ph = cfg.physics
    print(f"[exp13-3] σ={ph.sigma:.5f}  μ={ph.mu:.5f}"
          f"  ρ_l/ρ_g={ph.rho_l/ph.rho_g:.0f}")

    if args.plot_only:
        results = dict(np.load(npz_path, allow_pickle=True))
    else:
        print("[exp13-3] Running rising bubble simulation...")
        results = run_simulation(cfg)
        save_results(npz_path,
                     {k: v for k, v in results.items()
                      if isinstance(v, np.ndarray)})

    generate_figures(cfg, results, OUT_DIR)
    print(f"[exp13-3] saved → {OUT_DIR}")


if __name__ == "__main__":
    main()
