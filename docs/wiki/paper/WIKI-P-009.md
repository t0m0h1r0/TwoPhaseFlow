---
ref_id: WIKI-P-009
title: "07b_reinitialization: DGR Mass Correction and σ>0 Limitation (CHK-135)"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/07b_reinitialization.tex
    description: "DGR algorithm step 5 and 適用制限 section updated"
depends_on:
  - "[[WIKI-P-008]]"
  - "[[WIKI-T-030]]"
  - "[[WIKI-E-027]]"
compiled_by: ResearchArchitect
compiled_at: 2026-04-18
---

# 07b_reinitialization: DGR Mass Correction and σ>0 Limitation (CHK-135)

Two corrections to `paper/sections/07b_reinitialization.tex` arising from CHK-135
investigation (worktree-ch13-capillary-physics, 2026-04-18).

---

## Correction 1 — DGR Algorithm Step 5: ψ-space → φ-space Mass Correction

### Old (incorrect for curved interfaces)

```latex
\item 質量補正：$\psi \leftarrow \psi_{\mathrm{new}} + \dfrac{\delta M}{\sum w}\,w$，
    $w = 4\psi_{\mathrm{new}}(1-\psi_{\mathrm{new}})$
```

Claim: "質量補正は界面の一様シフト Δφ = 4λε に相当し，プロファイル幅 ε を変化させない"

### Problem

The ψ-space correction shifts the interface by `δx ∝ w/|∇ψ|`. At high-curvature regions,
`|∇ψ|` is smaller → larger shift. For mode-2 capillary oscillation (Prosperetti benchmark),
each DGR call systematically elongates the droplet → D(t) saturates at 0.226 (should decay
to ~0). Confirmed by frequency sensitivity experiments (Set D, CHK-135): no stable frequency
exists — too infrequent → blowup; too frequent → wrong D(t).

### New (correct for curved interfaces)

```latex
\item φ空間質量補正：
  φ_sdf ← φ_sdf + δφ，ψ_new = H_ε(φ_sdf)，
  δφ = δM / ∫H'_ε dV，H'_ε = ψ_new(1-ψ_new)/ε
```

Since DGR produces `|∇φ_sdf| ≈ 1`, the interface displacement `δx = δφ/|∇φ| ≈ δφ` is
curvature-independent → uniform shift → no shape change.

Also added a note explaining why the old ψ-space correction fails and directing to
§verify_capillary_wave for experimental evidence.

---

## Correction 2 — 適用制限: Added σ>0 Capillary Wave Limitation

### Added Section

New 適用制限（2）describing the interface fold cascade mechanism:

- σ>0 capillary advection creates `|∇ψ|→0` folds in the interface band
- DGR's median ε_eff is robust to outliers → fold cells invisible → scale≈1 → no repair
- CCD Laplacian over fold cell → unphysical κ spike → CSF blowup (KE > 1e6, t < 0.2)

Experimental evidence table (Prosperetti 1981 benchmark, 64×64 grid):

| Method | Result |
|---|---|
| DGR alone | BLOWUP t<0.2 (CHK-133) |
| Hybrid (split+DGR) | Stable but wrong D(t)=0.226 (CHK-135) |
| Split-only | Correct D_final≈0, stable T=10 ✓ |

Recommendation: for σ>0 capillary wave benchmarks, use split-only reinit (not hybrid, not DGR alone).

---

## Files Modified

- `paper/sections/07b_reinitialization.tex`: Algorithm step 5, mass correction proof, 適用制限（2）
