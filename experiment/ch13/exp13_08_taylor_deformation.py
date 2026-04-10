#!/usr/bin/env python3
"""[13-8] Droplet deformation in linear shear flow (Taylor deformation).

Paper ref: §13.8 (sec:val_taylor_deformation)

Neutrally buoyant droplet (ρ_l = ρ_g) in Couette shear flow u = γ̇(y−Ly/2).
Small-deformation steady state D = (L−B)/(L+B) is predicted analytically
by Taylor (1932): D_theory = (19λ+16)/(16λ+16) × Ca.

Sweeps Ca ∈ {0.1, 0.2, 0.3, 0.4} at λ ∈ {1, 5} (8 cases total).

Config : experiment/ch13/config/exp13_08_taylor_deformation.yaml
Output : experiment/ch13/results/exp13_08/

Usage
-----
  python experiment/ch13/exp13_08_taylor_deformation.py
  python experiment/ch13/exp13_08_taylor_deformation.py --plot-only
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
from twophase.experiment import (
    apply_style, experiment_argparser,
    save_results,
    COLORS,
)

apply_style()

CONFIG   = pathlib.Path(__file__).parent / "config" / "exp13_08_taylor_deformation.yaml"
OUT_DIR  = pathlib.Path(__file__).parent / "results" / "exp13_08"

CA_SWEEP     = [0.1, 0.2, 0.3, 0.4]
LAMBDA_SWEEP = [1.0, 5.0]
GAMMA_DOT    = 2.0


def _d_theory(Ca, lam):
    return (19 * lam + 16) / (16 * lam + 16) * Ca


def run_sweep():
    cfg_base = load_experiment_config(CONFIG)
    results_all = {}

    for lam in LAMBDA_SWEEP:
        for Ca in CA_SWEEP:
            label = f"lam{lam:.0f}_Ca{Ca:.1f}"
            print(f"\n  === λ={lam:.0f}  Ca={Ca:.1f} ===")
            ph = cfg_base.physics
            sigma = ph.mu_g * GAMMA_DOT * 0.25 / Ca   # R_ref = 0.25
            cfg = cfg_base.override(**{
                "physics.sigma":     sigma,
                "physics.lambda_mu": lam,
            })
            results = run_simulation(cfg)
            D_final = float(results["deformation"][-1]) if "deformation" in results else float("nan")
            D_th = _d_theory(Ca, lam)
            err = abs(D_final - D_th) / D_th if D_th > 0 else float("nan")
            print(f"    D_sim={D_final:.4f}  D_th={D_th:.4f}  err={err:.3f}")
            results_all[label] = results

    return results_all


def plot_d_vs_ca(results_all):
    fig, axes = plt.subplots(1, len(LAMBDA_SWEEP),
                             figsize=(5 * len(LAMBDA_SWEEP), 4))
    if len(LAMBDA_SWEEP) == 1:
        axes = [axes]

    for ax, lam in zip(axes, LAMBDA_SWEEP):
        D_sim = []
        D_th  = []
        for Ca in CA_SWEEP:
            key = f"lam{lam:.0f}_Ca{Ca:.1f}"
            res = results_all.get(key, {})
            D_s = float(res["deformation"][-1]) if "deformation" in res and len(res["deformation"]) > 0 else float("nan")
            D_sim.append(D_s)
            D_th.append(_d_theory(Ca, lam))

        ax.plot(CA_SWEEP, D_th,  "k--", label="Taylor (1932)")
        ax.plot(CA_SWEEP, D_sim, "o-", color=COLORS[0], label="Simulation")
        ax.set_xlabel("Ca")
        ax.set_ylabel("D = (L−B)/(L+B)")
        ax.set_title(f"λ = {lam:.0f}")
        ax.legend()
        ax.grid(True, alpha=0.3)

    fig.suptitle("§13.8 Taylor droplet deformation")
    fig.tight_layout()
    return fig


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = OUT_DIR / "data_sweep.npz"

    if args.plot_only:
        raw = dict(np.load(npz_path, allow_pickle=True))
        results_all = {}
        for lam in LAMBDA_SWEEP:
            for Ca in CA_SWEEP:
                key = f"lam{lam:.0f}_Ca{Ca:.1f}"
                k_t = f"{key}_times"
                k_d = f"{key}_D"
                if k_t in raw:
                    results_all[key] = {
                        "times":       raw[k_t],
                        "deformation": raw.get(k_d, np.array([])),
                    }
    else:
        results_all = run_sweep()
        flat = {}
        for key, res in results_all.items():
            flat[f"{key}_times"] = res.get("times", np.array([]))
            flat[f"{key}_D"]     = res.get("deformation", np.array([]))
        save_results(npz_path, flat)

    fig = plot_d_vs_ca(results_all)
    fig.savefig(OUT_DIR / "taylor_D_vs_Ca.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"[exp13-8] saved → {OUT_DIR}")


if __name__ == "__main__":
    main()
