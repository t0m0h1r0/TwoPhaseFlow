#!/usr/bin/env python3
"""[13-2] Capillary wave decay — Prosperetti (1981) benchmark.

Paper ref: §13.2 (sec:val_capillary_wave)

A perturbed circular droplet (l=2 mode, ε=0.05) oscillates under surface
tension.  The deformation D(t) decays as D ∝ exp(−β t) cos(ω₀ t + φ₀).
Compare oscillation frequency ω₀ and decay rate β to Prosperetti (1981).

Config : experiment/ch13/config/exp13_02_capillary_wave.yaml
Output : experiment/ch13/results/exp13_02/

Usage
-----
  python experiment/ch13/exp13_02_capillary_wave.py
  python experiment/ch13/exp13_02_capillary_wave.py --plot-only
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
from twophase.plot_factory import generate_figures
from twophase.experiment import (
    apply_style, experiment_argparser,
    save_results,
    COLORS,
)

apply_style()

CONFIG  = pathlib.Path(__file__).parent / "config" / "exp13_02_capillary_wave.yaml"
OUT_DIR = pathlib.Path(__file__).parent / "results" / "exp13_02"


def _theoretical_params(rho_l, rho_g, sigma, R0, l=2, mu=0.05):
    """Prosperetti (1981): inviscid frequency + leading-order decay rate."""
    rho_sum = rho_l + rho_g
    omega0_sq = l * (l - 1) * (l + 2) * sigma / (rho_sum * R0 ** 3)
    omega0 = math.sqrt(max(omega0_sq, 0.0))
    beta = (2 * l + 1) * (2 * l - 1) * mu / (rho_sum * R0 ** 2)
    return omega0, beta


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = OUT_DIR / "data.npz"

    cfg = load_experiment_config(CONFIG)

    if args.plot_only:
        results = dict(np.load(npz_path, allow_pickle=True))
    else:
        print("[exp13-2] Running capillary wave simulation...")
        results = run_simulation(cfg)
        save_results(npz_path,
                     {k: v for k, v in results.items()
                      if isinstance(v, np.ndarray)})

    generate_figures(cfg, results, OUT_DIR)

    ph = cfg.physics
    omega0, beta = _theoretical_params(ph.rho_l, ph.rho_g, ph.sigma, 0.25,
                                       l=2, mu=ph.mu)
    T_osc = 2.0 * math.pi / omega0 if omega0 > 0 else float("inf")
    print(f"[exp13-2] Theory: ω₀={omega0:.4f}  T={T_osc:.4f}  β={beta:.5f}")
    print(f"[exp13-2] saved → {OUT_DIR}")


if __name__ == "__main__":
    main()
