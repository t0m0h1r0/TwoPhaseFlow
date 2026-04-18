---
ref_id: WIKI-P-010
title: "07b_reinitialization: Eikonal Unified Method Section (CHK-136)"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/07b_reinitialization.tex
    description: "New subsubsection: 統一再初期化 Eikonal 法 added before 安定性制約"
depends_on:
  - "[[WIKI-P-009]]"
  - "[[WIKI-T-042]]"
compiled_by: ResearchArchitect
compiled_at: 2026-04-18
---

# 07b_reinitialization: Eikonal Unified Method Section (CHK-136)

One addition to `paper/sections/07b_reinitialization.tex` arising from CHK-136:

---

## Added Section — \subsubsection{統一再初期化：Eikonal 法}

Added after the DGR limitations paragraph (after 適用制限（2）),
before the \subsection{安定性制約} section.

### Content

New \subsubsection{統一再初期化：Eikonal 法（WIKI-T-042）} containing:

1. **Algorithm box** (algbox environment):
   - Step 1: ロジット反転 (logit inversion)
   - Step 2: Eikonal PDE 反復 (Godunov upwind, n_iter=20)
   - Step 3: セル局所 ε による再構成 (local-ε reconstruction)
   - Step 4: φ 空間質量補正 (φ-space mass correction)

2. **3 theoretical guarantees**:
   - 零点集合保存（正確）— Eikonal PDE preserves zero-set exactly
   - 勾配収束 — |∇φ|→1 guarantees thickness ε(i,j)
   - 質量保存（前クリッピング）— φ-space correction, same as DGR Thm 2

3. **Comparison table** (4 methods × 4 criteria):
   - 分裂法のみ: shape ✓, width ✗, σ>0 ✓
   - DGR のみ: shape ✗, width ✓, σ>0 ✗ (blowup)
   - ハイブリッド: shape ✓, width ✓, σ>0 ✗ (wrong D(t))
   - Eikonal (本法): shape ✓, width ✓, σ>0 検証中

4. **Closing paragraph**: explains how Eikonal avoids CHK-135 failure mode
   (no global-median scale, cell-local ε, no cross-cell shape contamination)

### Insertion Point

After line 262 (end of DGR 適用制限 paragraph), before line 264 (安定性制約 subsection).

---

## Files Modified

- `paper/sections/07b_reinitialization.tex`: +68 lines (new subsubsection)

---

## CHK-136 Result (T=2 Prosperetti, α=1.0)

| Metric | Result | Status |
|--------|--------|--------|
| VolCons max | 0.15% | ✓ |
| D(T=2) | 0.245 | ✗ (should be ~0.021) |
| Blowup | None | ✓ |

**Eikonal has the same failure mode as hybrid+φ-space on σ>0.**
The comparison table in the paper was updated to show ✗ for σ>0 (CHK-136).
Root cause: discrete Godunov zero-set drift (see WIKI-T-042 §CHK-136 Results).
The closing paragraph was revised to document the failure and note zero-set protection
as a future fix direction. See WIKI-T-042 for full technical analysis.
