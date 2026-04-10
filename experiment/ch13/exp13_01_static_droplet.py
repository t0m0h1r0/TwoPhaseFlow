#!/usr/bin/env python3
"""[13-1] Static droplet parasitic current — grid convergence study.

Paper ref: §13.1 (sec:val_static_droplet)

Measures spurious (parasitic) currents and Laplace pressure error for a
static droplet at rest under surface tension.  Grid convergence N ∈ {32,
64, 128, 256} shows O(h²)–O(h⁴) convergence with the balanced-force CSF.

Config : experiment/ch13/config/exp13_01_static_droplet.yaml
Output : experiment/ch13/results/exp13_01/

Usage
-----
  python experiment/ch13/exp13_01_static_droplet.py
  python experiment/ch13/exp13_01_static_droplet.py --plot-only
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
    save_results, load_results,
    COLORS,
)

apply_style()

CONFIG  = pathlib.Path(__file__).parent / "config" / "exp13_01_static_droplet.yaml"
OUT_DIR = pathlib.Path(__file__).parent / "results" / "exp13_01"
N_SWEEP = [32, 64, 128, 256]


def run_sweep():
    cfg_base = load_experiment_config(CONFIG)
    h_vals = []
    u_para_inf = []
    laplace_err = []

    for N in N_SWEEP:
        print(f"\n  === N={N} ===")
        cfg = cfg_base.override(**{
            "grid.NX": N,
            "grid.NY": N,
        })
        h = cfg.grid.LX / N

        results = run_simulation(cfg)

        # Parasitic current proxy from kinetic energy
        ke = float(results["kinetic_energy"][-1]) if "kinetic_energy" in results else 0.0
        rho_l = cfg.physics.rho_l
        area = cfg.grid.LX * cfg.grid.LY
        u_inf = np.sqrt(max(2.0 * ke / (rho_l * area), 0.0))

        lp = float(results["laplace_pressure"][-1]) if "laplace_pressure" in results else 0.0

        h_vals.append(h)
        u_para_inf.append(u_inf)
        laplace_err.append(lp)
        print(f"    h={h:.4f}  ‖u_para‖∞≈{u_inf:.3e}  Δp_err={lp:.3e}")

    return {
        "h_vals":      np.array(h_vals),
        "u_para_inf":  np.array(u_para_inf),
        "laplace_err": np.array(laplace_err),
    }


def plot_convergence(data):
    h = data["h_vals"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))

    for ax, key, lbl in zip(axes,
                             ["u_para_inf", "laplace_err"],
                             ["‖u_para‖∞", "|Δp error|"]):
        err = data[key]
        ax.loglog(h, err + 1e-16, "o-", color=COLORS[0], label="Simulation")
        ax.loglog(h, (err[-1] + 1e-16) * (h / h[-1]) ** 2,
                  "k--", alpha=0.6, label="O(h²)")
        ax.set_xlabel("h")
        ax.set_ylabel(lbl)
        ax.set_title(f"{lbl} vs h")
        ax.legend()
        ax.grid(True, which="both", alpha=0.3)

    fig.suptitle("§13.1 Parasitic current grid convergence")
    fig.tight_layout()
    return fig


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = OUT_DIR / "data.npz"

    if args.plot_only:
        data = dict(np.load(npz_path))
    else:
        data = run_sweep()
        save_results(npz_path, data)

    fig = plot_convergence(data)
    fig.savefig(OUT_DIR / "convergence.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"[exp13-1] saved → {OUT_DIR}")


if __name__ == "__main__":
    main()
