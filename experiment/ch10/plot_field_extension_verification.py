#!/usr/bin/env python3
"""Generate field_extension_verification.eps (§10.2 Figure 9).

Reads hermite_data.npz produced by exp10_ext_pde_hermite.py.
Two-panel figure:
  (a) Field extension convergence — Upwind O(h¹) vs Hermite O(h⁶)
  (b) Young–Laplace Δp = κ/We     — Upwind vs Hermite (identical at t=0)
"""

import pathlib
import numpy as np
import matplotlib.pyplot as plt

DATA = pathlib.Path(__file__).resolve().parent / "results" / "ext_pde_hermite" / "hermite_data.npz"
FIGDIR = pathlib.Path(__file__).resolve().parent / "results" / "ext_pde_hermite"

d = np.load(DATA)

fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(10, 4.2))

# ── (a) Extension convergence ────────────────────────────────────────────────
Ns_up = d["upwind_N"]
err_up = d["upwind_err"]
Ns_hm = d["hermite_N"]
err_hm = d["hermite_err"]

ax_a.loglog(Ns_up, err_up, "o-", color="tab:red", ms=7, lw=1.8, label="Upwind (Aslam 2004)")
ax_a.loglog(Ns_hm, err_hm, "s-", color="tab:blue", ms=7, lw=1.8, label="Hermite (proposed)")

# Reference slopes
N_ref = np.array([Ns_up[0], Ns_up[-1]], dtype=float)
h_ref = 1.0 / N_ref
ax_a.loglog(N_ref, 0.5 * h_ref**1, "--", color="tab:red", alpha=0.5, lw=1, label=r"$O(h^1)$")
ax_a.loglog(N_ref, 3e4 * h_ref**6, "--", color="tab:blue", alpha=0.5, lw=1, label=r"$O(h^6)$")

ax_a.set_xlabel(r"$N$")
ax_a.set_ylabel(r"$L^\infty$ error (extension band)")
ax_a.set_title("(a) Field extension convergence")
ax_a.legend(loc="lower left", fontsize=8.5)
ax_a.grid(True, which="both", ls=":", alpha=0.4)

# ── (b) Young–Laplace Δp ─────────────────────────────────────────────────────
Ns_lp = d["laplace_N"]
dp_up = d["laplace_dp_upwind"]
dp_hm = d["laplace_dp_hermite"]
dp_exact = 4.0

# Skip N=32 (negative Δp, off-scale)
mask = Ns_lp >= 64
Ns_plot = Ns_lp[mask]
dp_up_plot = dp_up[mask]
dp_hm_plot = dp_hm[mask]

ax_b.plot(Ns_plot, dp_up_plot, "o-", color="tab:red", ms=7, lw=1.8, label="Upwind")
ax_b.plot(Ns_plot, dp_hm_plot, "s--", color="tab:blue", ms=7, lw=1.8, label="Hermite")
ax_b.axhline(dp_exact, color="gray", ls="--", lw=1, alpha=0.7, label=r"Exact $\Delta p = 4.0$")

# Annotate relative errors
for N_val, dp_val, rel_err in zip(Ns_plot, dp_up_plot, d["laplace_rel_err_upwind"][mask]):
    pct = f"{rel_err * 100:.1f}%"
    y_off = -0.12 if N_val == 64 else 0.06
    ax_b.annotate(pct, (N_val, dp_val), textcoords="offset points",
                  xytext=(8, -12 if N_val == 64 else 8), fontsize=8.5,
                  color="tab:red")

ax_b.set_xlabel(r"$N$")
ax_b.set_ylabel(r"$\Delta p$")
ax_b.set_title(r"(b) Young–Laplace $\Delta p = \kappa/\mathit{We}$")
ax_b.legend(loc="lower right", fontsize=8.5)
ax_b.set_ylim(3.2, 4.25)
ax_b.set_xlim(55, 140)
ax_b.grid(True, which="both", ls=":", alpha=0.4)

fig.tight_layout()
out = FIGDIR / "field_extension_verification.eps"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved: {out}")
plt.close(fig)
