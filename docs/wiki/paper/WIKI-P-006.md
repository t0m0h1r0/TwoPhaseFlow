---
ref_id: WIKI-P-006
title: "Paper Review §11–§13: Findings and Action Items (2026-04-11)"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/11_chapter.tex
  - path: paper/sections/11_spatial.tex
  - path: paper/sections/11_spatial_geometry.tex
  - path: paper/sections/11_interface.tex
  - path: paper/sections/11_interface_field.tex
  - path: paper/sections/11_solver.tex
  - path: paper/sections/11_time.tex
  - path: paper/sections/11_summary.tex
  - path: paper/sections/12_verification.tex
  - path: paper/sections/12_legacy_component_verification.tex
  - path: paper/sections/12a_force_balance.tex
  - path: paper/sections/12b_conservation.tex
  - path: paper/sections/12c_time_accuracy.tex
  - path: paper/sections/12c2_highre_dccd.tex
  - path: paper/sections/12d_coupling.tex
  - path: paper/sections/12e_interface_crossing.tex
  - path: paper/sections/12e2_nonuniform_grid.tex
  - path: paper/sections/12f_error_budget.tex
  - path: paper/sections/13_benchmarks.tex
depends_on:
  - WIKI-P-004  # CHK-096 §1–§11 review (precursor, §11 delta only)
  - WIKI-T-028  # CLS-DCCD conservation theorem (ground truth for §11.2 verification)
  - WIKI-E-009  # shape preservation study (ground truth for adaptive reinit θ=1.10)
tags: [review, paper, chapters-11-13, CHK-111]
---

# Paper Review §11–§13 — CHK-111

**Date**: 2026-04-11
**Scope**: §11 delta (since CHK-096) + §12 first-pass + §13 first-pass (18 .tex files)
**Outcome**: 0 Fatal / 4 Major / 7 Minor / 2 Style; 6 independent derivations PASS

## Context

CHK-096 (2026-04-08, WIKI-P-004) covered §1–§11 with 0F / 7M / 14m / 3S findings. Since then:
- §11 received 24 commits (CHK-105 CLS-DCCD proof + adaptive reinit θ=1.10, DGR thickness correction, 4 readability passes)
- §12 received 17 commits (split-PPE promotion, §12.3c DCCD high-Re test, §12.5c spatial-varying ε, error budget rewrite) — never dedicated-reviewed
- §13 received rebuild-frequency calibration + exp13_03 artifact refresh

## Findings summary

| Severity | §11 | §12 | §13 | Cross-ch | Total |
|---|---|---|---|---|---|
| Fatal | 0 | 0 | 0 | 0 | **0** |
| Major | 0 | 2 | 2 | 0 | **4** |
| Minor | 1 | 4 | 1 | 1 | **7** |
| Style | 0 | 1 | 0 | 1 | **2** |

## Major findings (all patched in CHK-111)

- **M-1** [12c_time_accuracy.tex:134](../../../paper/sections/12c_time_accuracy.tex) §12.3c CFL subsection lacked 目的/結論 structure. **Fix**: added explicit `\noindent\textbf{目的：}` + `手順：` + `結論：` markers.
- **M-2** [12e2_nonuniform_grid.tex:5](../../../paper/sections/12e2_nonuniform_grid.tex) §12.5b opened directly with 手順, no 目的. **Fix**: inserted 目的/評価対象 block before existing 手順.
- **M-3** [13_benchmarks.tex:157](../../../paper/sections/13_benchmarks.tex) capillary wave volume error 1.74% declared success while stated acceptance was `<0.5%`. **Fix**: reworded to PARTIAL verdict, attributed to global long-time accumulation (not non-uniform grid specific), noted uniform-grid baseline is comparable.
- **M-4** [13_benchmarks.tex:178](../../../paper/sections/13_benchmarks.tex) rising bubble v_rise 1/4 dissipation blamed on "interpolation diffusion" without mechanism. **Fix**: added 3-sentence explanation (grid rebuild linear interpolation smooths velocity gradient → effective numerical viscosity → reduced terminal velocity; cross-linked to §12.5b parasitic current observation).

## Minor findings (queued for batch patch)

- **m-1** [11_summary.tex:70](../../../paper/sections/11_summary.tex) 判定 column header lacks legend for ✓/△ symbols
- **m-2** [12_legacy_component_verification.tex](../../../paper/sections/12_legacy_component_verification.tex) pure label stub with **0** `\ref{sec:component_verification}` sites in paper/ — safe to delete
- **m-3** [12_verification.tex:12](../../../paper/sections/12_verification.tex) `\label{sec:grid_convergence}` is referenced from [04_ccd.tex:100](../../../paper/sections/04_ccd.tex) but semantic target (curvature convergence) lives in §10.1 — retarget 04_ccd.tex ref or rename label
- **m-4** split-PPE notation drift: §12 uses `$\Ord{h^{7.0}}$`, §11/§9 use `$\Ord{h^7}$` — standardize to `$\Ord{h^7}$` (8 sites)
- **m-5** [12f_error_budget.tex:134](../../../paper/sections/12f_error_budget.tex) §12→§13 bridge needs one sentence explicitly stating §13 benchmarks operate within proven range
- **m-6** [13_benchmarks.tex:15](../../../paper/sections/13_benchmarks.tex) monolithic PPE choice not justified — add sentence explaining σ=0/low-ρ conditions make split-PPE unnecessary
- **m-7** (§13 from Phase C agent) — subsumed by m-6 above

## Style findings

- **S-1** [12d_coupling.tex:13](../../../paper/sections/12d_coupling.tex) 「先行告知」→「発見概要」 rewording
- **S-2** notation drift (tracked under m-4)

## Independent derivations performed

1. **DCCD periodic zero-sum** (§11.2, `eq:dccd_zero_sum`) — CCD block-circulant row sum = 0 (constant-mode argument) + filter telescoping identity → `Σf̃' = 0` ✓ matches paper
2. **θ = 1.10 traceability** (§11.2 adaptive reinit) — WIKI-E-009 P3 table: adaptive-1.10 is optimum (+21.4% vs 1.05/1.20 bracketing) ✓
3. **Mass error wording update** (O(10⁻⁵) → O(10⁻¹⁵)) — 0 residual O(10⁻⁵) sites in §11 ✓
4. **Interface temporal degradation** (§12.3d) — φ-transport vs ρ-projection time-splitting mismatch produces O(Δt) term; paper derivation matches independent sketch ✓
5. **Split-PPE O(h^7) cross-chapter consistency** — §9.3 → §11.3.3 (`sec:verify_split_ppe_dc` in 11_solver.tex:205) → §12.5a → §12.6 all resolve and agree on claim ✓
6. **Prosperetti formula** (§13.1) — ω₀=6.822, T₀=0.921 for l=2, σ=1, ρ_l=10, ρ_g=1, R₀=0.25 ✓ matches paper "≈6.82"
7. **Two independent failure modes PR-5** (§12.4) — IPC ∇pⁿ jump crossing + variable-density PPE conditioning both documented, HFE-alone failure test present ✓

## PR-5 Algorithm Fidelity verdict

**PASS**. "Moving interface + σ>0 diverges at step 2" claim is consistent across 4 sites in §12 (12_verification:29, 12d_coupling:15/170/225) and both independent root causes are explicitly distinguished.

## Dead-weight recommendations

- **12_legacy_component_verification.tex** — 15 lines, 0 references, safe to delete. Comment in file claims "referenced from §12, §13" but grep confirms no such references exist.

## Superseded items

This entry extends [WIKI-P-004](WIKI-P-004.md) (CHK-096) for the §11–§13 scope. WIKI-P-004 remains authoritative for §1–§10.

## Next actions

1. Batch-apply Minor m-1 through m-6 in a follow-up PaperWriter session
2. Delete 12_legacy_component_verification.tex and remove its include from main.tex
3. Retarget 04_ccd.tex:100 forward-ref (m-3)
