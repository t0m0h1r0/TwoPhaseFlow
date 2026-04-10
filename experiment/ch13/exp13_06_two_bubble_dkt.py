#!/usr/bin/env python3
"""[13-6] Two-bubble Drafting-Kissing-Tumbling (DKT) interaction.

Paper ref: §13.6 (sec:val_dkt)

Two identical gas bubbles aligned vertically.  The trailing bubble drafts
in the wake of the leading one, accelerates (kissing), then tumbles
laterally.  Qualitative DKT phases are observable in y-separation Δy(t).

Config : experiment/ch13/config/exp13_06_two_bubble_dkt.yaml
Output : experiment/ch13/results/exp13_06/

Usage
-----
  python experiment/ch13/exp13_06_two_bubble_dkt.py
  python experiment/ch13/exp13_06_two_bubble_dkt.py --plot-only
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

CONFIG  = pathlib.Path(__file__).parent / "config" / "exp13_06_two_bubble_dkt.yaml"
OUT_DIR = pathlib.Path(__file__).parent / "results" / "exp13_06"


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = OUT_DIR / "data.npz"

    cfg = load_experiment_config(CONFIG)
    ph = cfg.physics
    print(f"[exp13-6] σ={ph.sigma:.4f}  μ={ph.mu:.5f}"
          f"  ρ_l/ρ_g={ph.rho_l/ph.rho_g:.0f}")

    if args.plot_only:
        results = dict(np.load(npz_path, allow_pickle=True))
    else:
        print("[exp13-6] Running two-bubble DKT simulation...")
        results = run_simulation(cfg)
        save_results(npz_path,
                     {k: v for k, v in results.items()
                      if isinstance(v, np.ndarray)})

    generate_figures(cfg, results, OUT_DIR)
    print(f"[exp13-6] saved → {OUT_DIR}")


if __name__ == "__main__":
    main()
