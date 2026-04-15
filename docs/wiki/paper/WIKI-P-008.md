---
ref_id: WIKI-P-008
title: "Ch11+Ch12 Review Corrections: 14 Findings Fixed (2026-04-16)"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - commit: "1254d71"
    description: "ch11 review round 1: 3 findings (1 Major, 1 Medium, 1 Minor)"
  - commit: "bf1c4f6"
    description: "ch11 review round 2: 5 findings (1 Critical, 2 Major, 2 Medium)"
  - commit: "a4bfec2"
    description: "ch12 review round 3: 6 findings (2 Critical, 3 Major, 1 Minor)"
depends_on:
  - "[[WIKI-P-007]]"
compiled_by: ResearchArchitect
compiled_at: 2026-04-16
---

# Ch11+Ch12 Review Corrections: 14 Findings Fixed

Three review rounds on 2026-04-16, continuing from [[WIKI-P-007]].

---

## Round 1 — Ch11 (commit 1254d71)

| Sev | File | Issue | Fix |
|-----|------|-------|-----|
| Major | 11_component_verification L44 | "Step 1, 5" in intro contradicts table L70 (Step 5 = §12) | Replaced with explicit scheme names + "ODE テスト" |
| Medium | 11g_summary L118 | "安定・質量保存" expectation vs 23% mass loss | Changed to "安定・質量影響評価" |
| Minor | ch11_gfm_recovery.png | Orphaned PNG, violates PDF-only rule | git rm |

## Round 2 — Ch11 (commit bf1c4f6)

| Sev | File | Issue | Fix |
|-----|------|-------|-----|
| Critical | 11c L24 / 11d L216 | "PPE を統合した" vs "PPE は解かない" | Removed PPE claim; added §12 forward ref |
| Major | 11c L123 | "L2 decreasing" but Zalesak L2 increases (8.62e-2→1.19e-1) | Split description: vortex decreasing, Zalesak ε-limited increase |
| Major | 11c L22 / 11d L176 | Intro promises upwind-HFE comparison; HFE section excludes (NaN) | Intro now states exclusion upfront |
| Medium | 11a L334 | "DCCD negligible impact" overgeneralized (smooth L2: 3 orders worse) | Added CLS wavelength condition (λ_min≈9.4h, H≈0.98) |
| Medium | 11c L105/L310 | Reinit counts "3-4" vs "2" without condition disambiguation | Added (N=128, ε/h=1.0) vs (N=128, ε/h=1.5) |

## Round 3 — Ch12 (commit a4bfec2)

| Sev | File | Issue | Fix |
|-----|------|-------|-----|
| Critical | 12g L24,73,83 | Grid-adaptation test confounded with reinit setting change | Weakened causal claims; noted control experiment needed |
| Critical | 12e L87,98 | ρ=5 stability + growth ratio 5.3 cited without in-text data | Expanded footnote with ρ=5 N=64 values + N=128 growth ratio |
| Major | 12c L183 | ε=3h contradicts L190 ε=2h and code (eps=2.0*h) | Fixed to ε=2h |
| Major | 12c L60,65 | Figure caption "order drops at small Δt" vs table (all 2.00) | Aligned caption with table |
| Major | 12_ L73 / 12e L81 | ∇·u < 1e-10 criterion vs two-phase 1e-2 results | Scoped to single-phase; added ‡ footnote for two-phase |
| Minor | 12d L32,46 | N=256 declared but absent from results table | Corrected to N=64,128 with cost footnote |

---

## Recurring Patterns Observed

1. **Scope mismatch**: Claims in section intros not matching actual test definitions (Young-Laplace PPE, HFE upwind, Step 5).
2. **Confounded comparisons**: Multiple variables changed simultaneously without control (12g reinit + grid type).
3. **Expectation overshoot**: Expectation column in summary tables using stronger language than results warrant (mass conservation, error trends).
4. **Transcription errors**: Numerical values in text not matching code or tables (ε=3h vs 2h, Zalesak trend).
5. **Missing evidence**: Conclusions referencing data not present in the text (ρ=5 growth ratio, N=256).
