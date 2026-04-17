#!/usr/bin/env python3
"""Set C diagnostic: compare old (global eps_eff) vs new (pointwise) DGR phi_sdf.

Confirms H1: global scale introduces O(1) errors in phi_sdf for curved interfaces.

Usage: .venv/bin/python3 experiment/ch13/diag/exp13_diag_dgr_sdf_comparison.py
"""

import sys
import pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from twophase.simulation.config_io import load_experiment_config
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.levelset.heaviside import invert_heaviside

CONFIG = ROOT / "experiment/ch13/config/exp13_01_a1.0_dgr.yaml"


def run():
    cfg = load_experiment_config(CONFIG)
    solver = TwoPhaseNSSolver.from_config(cfg)
    xp = solver._backend.xp
    grid = solver._grid
    ccd = solver._ccd
    eps = solver._eps

    # Build initial ψ (capillary wave IC, perturbed circle)
    psi = xp.asarray(solver.build_ic(cfg))

    print(f"Grid: {grid.N}, ε = {eps:.5f}")
    print(f"ψ range: [{float(xp.min(psi)):.4f}, {float(xp.max(psi)):.4f}]")

    # ── Shared step 1: compute |∇ψ| via CCD ──────────────────────────────────
    grad_sq_psi = xp.zeros_like(psi)
    for ax in range(grid.ndim):
        g1, _ = ccd.differentiate(psi, ax)
        grad_sq_psi += g1 * g1
    grad_psi = xp.sqrt(xp.maximum(grad_sq_psi, 1e-28))

    # ── OLD: global eps_eff scale ────────────────────────────────────────────
    band = (psi > 0.05) & (psi < 0.95)
    eps_local = (psi * (1.0 - psi))[band] / xp.maximum(grad_psi[band], 1e-14)
    eps_eff = float(xp.median(eps_local))
    eps_local_np = np.array(eps_local)

    phi_raw = invert_heaviside(xp, psi, eps)
    scale_old = eps_eff / eps
    phi_sdf_old = phi_raw * scale_old

    # ── NEW: pointwise |∇φ_raw| normalization (WIKI-T-030 Step 2) ───────────
    grad_sq_phi = xp.zeros_like(phi_raw)
    for ax in range(grid.ndim):
        g1, _ = ccd.differentiate(phi_raw, ax)
        grad_sq_phi += g1 * g1
    g_min = 0.1
    grad_phi_norm = xp.sqrt(xp.maximum(grad_sq_phi, g_min**2))
    phi_sdf_new = phi_raw / grad_phi_norm

    # ── Compare ──────────────────────────────────────────────────────────────
    diff = np.array(phi_sdf_new - phi_sdf_old)
    phi_old_np = np.array(phi_sdf_old)
    phi_new_np = np.array(phi_sdf_new)
    psi_np = np.array(psi)
    band_np = np.array(band)

    print("\n── OLD (global ε_eff scale) ──────────────────────────────────────")
    print(f"  ε_eff (median) = {eps_eff:.6f}  (ε = {eps:.6f})")
    print(f"  scale          = {scale_old:.4f}  (ε_eff/ε)")
    print(f"  eps_local std  = {eps_local_np.std():.6f}")
    print(f"  eps_local CV   = {eps_local_np.std()/eps_local_np.mean():.4f}  (coeff of variation)")
    print(f"  phi_sdf_old:   max={phi_old_np.max():.4f}  min={phi_old_np.min():.4f}")

    print("\n── NEW (pointwise |∇φ_raw| normalization) ────────────────────────")
    grad_phi_np = np.array(grad_phi_norm)
    print(f"  |∇φ_raw| band: mean={grad_phi_np[band_np].mean():.4f}  "
          f"std={grad_phi_np[band_np].std():.4f}  "
          f"min={grad_phi_np[band_np].min():.4f}  max={grad_phi_np[band_np].max():.4f}")
    print(f"  phi_sdf_new:   max={phi_new_np.max():.4f}  min={phi_new_np.min():.4f}")

    print("\n── Difference φ_sdf_new − φ_sdf_old ─────────────────────────────")
    print(f"  max |diff|       = {np.abs(diff).max():.6f}")
    print(f"  mean |diff|      = {np.abs(diff).mean():.6f}")
    print(f"  mean |diff| band = {np.abs(diff[band_np]).mean():.6f}")
    print(f"  L_inf diff / ε   = {np.abs(diff).max() / eps:.4f}  (relative to ε)")

    # ── Curvature via φ_sdf difference ───────────────────────────────────────
    # CCD Laplacian of both phi_sdf → approximate κ
    def ccd_laplacian(f):
        lap = xp.zeros_like(f)
        for ax in range(grid.ndim):
            _, d2 = ccd.differentiate(f, ax)
            lap += d2
        return np.array(lap)

    kappa_old = ccd_laplacian(phi_sdf_old)
    kappa_new = ccd_laplacian(phi_sdf_new)
    kappa_diff = kappa_new - kappa_old

    print("\n── Curvature (∇²φ_sdf) ────────────────────────────────────────────")
    print(f"  κ_old band: mean={kappa_old[band_np].mean():.4f}  max|κ|={np.abs(kappa_old[band_np]).max():.4f}")
    print(f"  κ_new band: mean={kappa_new[band_np].mean():.4f}  max|κ|={np.abs(kappa_new[band_np]).max():.4f}")
    print(f"  max |Δκ| band = {np.abs(kappa_diff[band_np]).max():.4f}")

    print("\n── Conclusion ──────────────────────────────────────────────────────")
    cv = eps_local_np.std() / eps_local_np.mean()
    l_inf_rel = np.abs(diff).max() / eps
    if cv > 0.1:
        print(f"  H1 CONFIRMED: local ε_eff CV={cv:.3f} >> 0.1 → global scale is inaccurate")
    else:
        print(f"  H1 WEAK: local ε_eff CV={cv:.3f} ≤ 0.1 → interface nearly uniform")
    if l_inf_rel > 0.1:
        print(f"  φ_sdf error = {l_inf_rel:.3f}ε >> 0 → curvature corruption confirmed")
    else:
        print(f"  φ_sdf error = {l_inf_rel:.3f}ε ≈ 0 → negligible difference")


if __name__ == "__main__":
    run()
