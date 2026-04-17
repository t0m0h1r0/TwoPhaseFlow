#!/usr/bin/env python3
"""Trace first DGR call — compare old and new implementations at IC.

Shows scale distribution, phi_sdf stats, and curvature difference
between old (global eps_eff) and new (pointwise eps_local) approaches.
"""

import sys
import pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from twophase.simulation.config_io import load_experiment_config
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.levelset.heaviside import invert_heaviside, heaviside

CONFIG = ROOT / "experiment/ch13/config/exp13_01_a1.0_dgr.yaml"
_SCALE_MAX = 15.0
_SCALE_MIN = 0.1


def run():
    cfg = load_experiment_config(CONFIG)
    solver = TwoPhaseNSSolver.from_config(cfg)
    xp = solver._backend.xp
    grid = solver._grid
    ccd = solver._ccd
    eps = solver._eps

    psi = xp.asarray(solver.build_ic(cfg))
    print(f"ε = {eps:.5f}  Grid: {grid.N}")

    # Shared: |∇ψ|
    grad_sq = xp.zeros_like(psi)
    for ax in range(grid.ndim):
        g1, _ = ccd.differentiate(psi, ax)
        grad_sq += g1 * g1
    grad_psi = xp.sqrt(xp.maximum(grad_sq, 1e-28))

    psi_1mpsi = psi * (1.0 - psi)
    eps_local = psi_1mpsi / xp.maximum(grad_psi, 1e-14)
    phi_raw = invert_heaviside(xp, psi, eps)

    band = (psi > 0.05) & (psi < 0.95)
    eps_local_np = np.array(eps_local)
    band_np = np.array(band)
    psi_np = np.array(psi)
    phi_raw_np = np.array(phi_raw)
    grad_psi_np = np.array(grad_psi)

    # ── OLD: global eps_eff scale ────────────────────────────────────────────
    eps_eff_global = float(xp.median(eps_local[band]))
    scale_old = eps_eff_global / eps
    phi_sdf_old = phi_raw_np * scale_old

    # ── NEW: pointwise eps_local scale (band only) ────────────────────────────
    scale_band_np = np.clip(eps_local_np / eps, _SCALE_MIN, _SCALE_MAX)
    scale_new_np = np.where(band_np, scale_band_np, np.ones_like(psi_np))
    phi_sdf_new = phi_raw_np * scale_new_np

    # ── Analyze ──────────────────────────────────────────────────────────────
    def ccd_lap(f):
        fx = xp.asarray(f)
        lap = xp.zeros_like(fx)
        for ax in range(grid.ndim):
            _, d2 = ccd.differentiate(fx, ax)
            lap += d2
        return np.array(lap)

    kappa_old = ccd_lap(phi_sdf_old)
    kappa_new = ccd_lap(phi_sdf_new)

    print("\n── Scale distribution ────────────────────────────────────────────")
    print(f"  OLD scale (global): {scale_old:.5f}")
    print(f"  NEW scale (band):   mean={scale_new_np[band_np].mean():.5f}  "
          f"std={scale_new_np[band_np].std():.5f}  "
          f"min={scale_new_np[band_np].min():.5f}  max={scale_new_np[band_np].max():.5f}")
    print(f"  NEW scale (all):    min={scale_new_np.min():.5f}  max={scale_new_np.max():.5f}")

    print("\n── phi_sdf stats ─────────────────────────────────────────────────")
    print(f"  phi_sdf_old:  max={phi_sdf_old.max():.4f}  min={phi_sdf_old.min():.4f}"
          f"  band max={phi_sdf_old[band_np].max():.4f}")
    print(f"  phi_sdf_new:  max={phi_sdf_new.max():.4f}  min={phi_sdf_new.min():.4f}"
          f"  band max={phi_sdf_new[band_np].max():.4f}")

    print("\n── Curvature (∇²φ_sdf) in band ────────────────────────────────────")
    print(f"  κ_old band: mean={kappa_old[band_np].mean():.4f}  max|κ|={np.abs(kappa_old[band_np]).max():.4f}")
    print(f"  κ_new band: mean={kappa_new[band_np].mean():.4f}  max|κ|={np.abs(kappa_new[band_np]).max():.4f}")
    print(f"  max |Δκ| band = {np.abs(kappa_new - kappa_old)[band_np].max():.4f}")

    print("\n── psi_new comparison ──────────────────────────────────────────────")
    psi_new_old = 1.0 / (1.0 + np.exp(-phi_sdf_old / eps))
    psi_new_new = 1.0 / (1.0 + np.exp(-phi_sdf_new / eps))
    diff_psi = np.abs(psi_new_new - psi_new_old)
    print(f"  max |psi_new_new - psi_new_old| = {diff_psi.max():.6f}")
    print(f"  max |psi_new_new - psi_new_old| in band = {diff_psi[band_np].max():.6f}")

    # ── Identify problematic cells ────────────────────────────────────────────
    print("\n── Cells where scale_new differs significantly from 1 ─────────────")
    sig = band_np & (np.abs(scale_new_np - 1.0) > 0.1)
    if sig.any():
        print(f"  N cells with |scale-1|>0.1 in band: {sig.sum()}")
        print(f"  psi at these cells: {psi_np[sig][:5]}")
        print(f"  eps_local at these cells: {eps_local_np[sig][:5]}")
        print(f"  scale at these cells: {scale_new_np[sig][:5]}")
        print(f"  grad_psi at these cells: {grad_psi_np[sig][:5]}")
    else:
        print("  No significant deviations from scale=1 in band at IC.")


if __name__ == "__main__":
    run()
