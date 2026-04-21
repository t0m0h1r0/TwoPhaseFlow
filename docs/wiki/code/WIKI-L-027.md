---
ref_id: WIKI-L-027
title: "Split-Reinit y-flip Invariance: safe_grad Floor in compute_gradient_normal"
domain: code
status: ACCEPTED
superseded_by: null
sources:
  - path: src/twophase/levelset/reinit_ops.py
    description: Shared reinit operators (compute_gradient_normal, dccd_compression_div)
  - path: src/twophase/levelset/reinit_split.py
    description: SplitReinitializer that consumes compute_gradient_normal
  - path: experiment/ch13/tools/split_reinit_yflip_probe.py
    description: Operator-isolation probe used to triangulate the bug
  - path: experiment/ch13/config/ch13_04_sym_B_alpha2_split.yaml
    description: Binary-search gate for α=2 stretched + split reinit
  - path: src/twophase/tests/test_reinit_split_yflip.py
    description: Regression suite guarding the fix
depends_on:
  - "[[WIKI-L-021]]: CLS Reinitialization Operator Split"
  - "[[WIKI-L-008]]: DCCD Compression (ψ(1-ψ) n̂ flux)"
tags: [levelset, reinit, split, symmetry, y_flip, floor, regularisation, accepted_change]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-21"
---

# Split-Reinit y-flip Invariance — `safe_grad` Floor Fix (CHK-168)

## Problem

`experiment/ch13/config/ch13_04_sym_B_alpha2_split.yaml` exercises an α=2
stretched grid with `reinit_method='split'` on a y-flip-symmetric initial
condition (mode=2 perturbed circle). `symmetry_error` diagnostic shows:

| step / t | sym_psi_y | sym_psi_x | y/x |
|---|---|---|---|
| 1–4 (t<0.003) | 1.3–1.4e-15 | 1.7–1.8e-15 | 0.8 (sub-ULP) |
| **5 (t≈0.004)** | **4.47e-6** | **3.23e-7** | **13.8 ×** |
| final | 3.02e-1 | 7.01e-2 | 4.31 × |

The 13.8× y/x ratio at the first reinit call (`reinit_every=2`) shows a
**y-flip-specific** asymmetry — the split-reinit operator itself is not
y-flip equivariant.

## Diagnosis

Operator-isolation probe
(`experiment/ch13/tools/split_reinit_yflip_probe.py`) measured
`||op(ψ) − flip_y(op(flip_y(ψ)))||_∞ / max|op(ψ)|` for each sub-operator
of a single `SplitReinitializer.reinitialize` call:

- `ccd.differentiate(ψ, axis=*)` → ULP (6e-17 … 7e-15) ✓ equivariant
- `filtered_divergence(flux, axis)` → 5e-13 (bulk-noise amplified)
- `compute_gradient_normal` `n̂_y` → **3.4e-5** ← culprit

Location diagnostic: `argmax |n̂_y − (−flip_y(n̂_y))|` = node **(32, 32)**,
the y-flip fixed row. At this node:
- `∂ψ/∂y = 8.5e-17` (ULP noise from the CCD tridiagonal solve)
- `|∇ψ|` falls below the `safe_grad` floor `1e-14`
- `n̂_y = 8.5e-17 / 1e-14 = 8.5e-3` — **ULP amplified by 10¹⁴×**

Every y-ODD ULP bit in `∂ψ/∂y` is amplified into O(1e-3) noise in `n̂_y`.
The compression flux `ψ(1−ψ) n̂` carries this into
`dccd_compression_div`, and after one full reinit inner iteration the
output asymmetry is O(1e-6).

## Fix

[src/twophase/levelset/reinit_ops.py:47-68](../../../src/twophase/levelset/reinit_ops.py#L47-L68)

```python
def compute_gradient_normal(xp, psi, ccd):
    # ...
    grad_sq = sum(g * g for g in dpsi)
    safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-12)), 1e-6)
    n_hat = [g / safe_grad for g in dpsi]
    return dpsi, n_hat, safe_grad
```

**Rationale**: the floor marks the scale below which `|∇ψ|` is
indistinguishable from round-off and `n̂` direction is physically
undefined (bulk regions where `ψ(1−ψ) → 0`). Interface nodes carry
`|∇ψ| ≈ 1/(2ε) ≈ 30`, so the floor is inactive at the interface and
bit-exactness is preserved on any grid (PR-5).

Prior floor values `(grad_sq ≥ 1e-28, safe_grad ≥ 1e-14)` were chosen
only to avoid divide-by-zero and did not account for the ULP
amplification on y-flip ODD modes.

## Verification

Probe after fix (α=2 stretched grid, same config):

| stage | y-flip err | x-flip err | y/x |
|---|---|---|---|
| `n_hat_y` | 6.4e-11 | 1.0e-14 | — |
| `dccd_compression_div` | 3.9e-13 | 2.1e-13 | **1.9×** |
| 1-iter reinit (no mass corr) | 3.3e-16 | 4.4e-16 | **0.75× ULP** |
| 4-iter reinit + mass corr | 1.27e-7 | 1.32e-7 | **0.96×** |

- **Core bug resolved**: y/x ratio 13.8× → 1.9× at operator level, 0.96×
  at per-call output level.
- **Single-iter is ULP equivariant** on α=1 uniform *and* α=2 stretched.
- **4-iter residual 1.27e-7** is Lyapunov amplification intrinsic to
  split-reinit's backward-parabolic compression term (ASM-122-A). Per-iter
  multiplier ≈ 700×; same on α=1 uniform and α=2 stretched — therefore
  *not* a grid-stretching bug.

Regression tests ([src/twophase/tests/test_reinit_split_yflip.py](../../../src/twophase/tests/test_reinit_split_yflip.py)):

- `test_compute_gradient_normal_floor_is_1e6` — direct fix assertion
- `test_dccd_compression_div_y_flip_equivariant` — operator equivariance
- `test_split_reinit_single_iteration_y_flip_equivariant` — ULP after 1 iter
- `test_split_reinit_y_flip_magnitude` — output < 2e-6 (pre-fix ≥ 4.47e-6)

Full test suite: **293 passed / 15 skipped / 2 xfailed** — zero regression.

## Out of scope / follow-up

- **ASM-122-A Lyapunov chaos**: the residual 1.27e-7 per reinit call
  accumulates under `reinit_every=2` iteration. On the sym_B config
  (σ=1, T_final=8) the final `sym_psi_y` is expected to remain orders
  of magnitude below the pre-fix 3e-1 level, but precise alignment with
  the Ridge-Eikonal gate (`< 1e-10`) is *not* achievable for split
  reinit without redesigning the compression term to dampen rather
  than sharpen grid-scale y-ODD modes. This is a known limitation
  (ASM-122-A) — not a bug.

- **CHK-169 follow-up (DONE)**: The floor-raise was applied consistently
  across all ψ-consuming sites:
    - `src/twophase/levelset/reinit_unified.py:58` (hot path) → **1e-6**
    - `src/twophase/levelset/reinit_unified.py:122` (legacy baseline) → **1e-6**
    - `src/twophase/levelset/reinitialize.py:185` (legacy WENO5 facade) → **1e-6**

  The remaining two sites were intentionally kept at `1e-14`:
    - `src/twophase/levelset/closest_point_extender.py:107`
    - `src/twophase/levelset/field_extender.py:90`

  These consume **SDF φ** (not ψ), and |∇φ| ≈ 1 everywhere — the floor
  is physically inactive. Raising would mask legitimate
  low-gradient regions where HFE extension is most sensitive.
  See `src/twophase/tests/test_reinit_floor_audit.py` for the
  regression suite covering all 5 sites.

- **CHK-169 also marks** `ch13_04_capwave_ridge_alpha2.yaml`
  (non-FCCD Ridge-Eikonal on α=2) as deprecated for σ>0 + α>1
  configurations due to the pre-existing H-01 KE blowup at t≈2.85
  (WIKI-E-030). Production reference for α=2 + σ>0 is
  `ch13_04_capwave_fullstack_alpha2.yaml` (FCCD, PASS T=8).

- **Lyapunov chaos (ASM-122-A)**: The 4-iter composition drift is
  structural — any attempt to dampen (reduce `n_steps`, add hybrid
  projection) compromises the interface-sharpening physics that
  motivates split-reinit. For y-flip-critical long-time runs, prefer
  `method='ridge_eikonal'` (ULP post-CHK-167, no backward-parabolic
  term).  See the updated
  `SplitReinitializer` / `Reinitializer` docstrings for guidance.
