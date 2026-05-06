# CHK-RA-CH12-13-STRICT-002 — §12--§13 Strict Reviewer Loop

## Scope

- Branch/worktree: `codex/ra-ch12-13-strict-review-20260506` / `.claude/worktrees/codex-ra-ch12-13-strict-review-20260506`
- Lock: `docs/locks/ra-ch12-13-strict-review-002-20260506.lock.json`
- Target: paper chapters 12--13, with emphasis on narrative coherence, notation consistency, section structure, and logical consistency.
- Stop rule: repeat until no MAJOR+ findings remain, or round count exceeds 20.
- Review stance: latest research content belongs in the manuscript; process history, version-change narration, and broad trial logs do not.

## Round 1 Findings

### MAJOR-1 — V1 mixed the quantitative convergence horizon with an unrelated long-time visualization horizon

§13a states V1 uses `T=0.05` for the convergence tests, but the vorticity snapshot caption and verdict discuss `t=0,25,50` and the decay factors `0.61/0.37`. As written, the figure appears to be part of the same quantitative run, which makes the settings internally inconsistent. Root fix: split V1 into a quantitative convergence contract (`T=0.05`) and a separate qualitative long-time visualization (`T_vis=50`) that is not used for the tabulated slopes.

Status: fixed in `paper/sections/13a_single_phase_ns.tex`.

### MAJOR-2 — V7/V10 still read like RCA/trial logs instead of final paper narrative

The chapter overview, V7 verdict, V10-a shape verdict, and V10-b shape verdict include detailed control-run inventory (`fixed_reinit_count`, no-reinit, CFL halving, per-T width proxy sequences, etc.). These details are useful research audit data, but in the paper they obscure the final mechanism: V7 is capillary pressure-jump/projection interface-band limited; V10 shape is fixed-grid CLS geometry limited, while mass is Type-B corrected. Root fix: keep only the decisive mechanism and cite the appendix/diagnostic evidence as supporting material without narrating the full trial history in the main §13 flow.

Status: fixed in `paper/sections/13_verification.tex`, `paper/sections/13d_density_ratio.tex`, `paper/sections/13e_nonuniform_ns.tex`, and `paper/sections/13f_error_budget.tex`.

### MAJOR-3 — Duplicate subtest IDs in the §12 summary weaken A3 traceability

The §12 summary table repeats `U6-b` for HFE 1D and 2D, and repeats `U7-a` for BF match and mismatch. A reader cannot cite one row unambiguously even though the paper stresses equation/discretization/code traceability. Root fix: retain the parent U-test names but give table rows unique subtest IDs (`U6-b1`, `U6-b2`, `U7-a1`, `U7-a2`) and update the explanatory note.

Status: fixed in `paper/sections/12h_summary.tex`.

## Round 2 Findings

### MAJOR-4 — §12 still abbreviated the V6/V7/V9 stack as pre-range-projection pressure-jump PPE

After Round 1, §13 defines V6/V7/V9 as the `range-projected pressure-jump stack`, but §12 design-map and U6/U7 bridge text still says only `pressure-jump 分相 PPE+HFE stack` or `pressure-jump stack`. That abbreviation drops the decisive latest closure terms: capillary range projection, projection-native face closure, and affine pressure-history faces. A reader entering through §12 could therefore think §13 is merely the older phase-separated PPE+HFE path. Root fix: make §12 exit wording and adjacent §13 summary wording name the same stack components as §13's canonical definition.

Status: fixed in `paper/sections/12_component_verification.tex`, `12h_summary.tex`, `12u2_ccd_poisson_ppe_bc.tex`, `12u6_split_ppe_dc_hfe.tex`, `12u7_bf_static_droplet.tex`, `13_verification.tex`, `13b_twophase_static.tex`, and `13f_error_budget.tex`.

### MINOR-1 — V10 prose referenced a non-existent heading name

V10-a/V10-b cite `各 V test の判定再分類`, while §13's actual heading is `各 V test の判定整理`. Root fix: use the actual heading name consistently.

Status: fixed in `paper/sections/13e_nonuniform_ns.tex`.

## Round 3 Findings

### MAJOR-5 — Manuscript-facing guidance still used process-history language

Round 3 scans found manuscript text saying tables contain `再生成した数値`, that `過去表` values are not reused, and that V5 uses a `Type-A revised criterion` with a `判定キー変更`. These are internal research/workflow statements, not final-paper claims. Root fix: rewrite them as final evidence policy and final criteria: tables contain the adopted verification values, and V5 is judged by the CCD absolute spurious-current scale.

Status: fixed in `paper/sections/12_component_verification.tex`, `13_verification.tex`, `13b_twophase_static.tex`, and `13e_nonuniform_ns.tex`.

## Round 4 Findings

Targeted scans after the Round 3 fixes found no remaining MAJOR+ issues.

- Stale values / old-stack wording: no matches for old V7 slope `1.48`, old V6 pressure ratio `2.006`, old V9 volume floor `3.79e-8`, pre-range-projection `pressure-jump 分相 PPE+HFE stack`, or `V6/V7/V9 pressure-jump stack`.
- Process-history wording: no matches for `過去表`, `変更点`, `全バージョン`, `試行錯誤`, `fixed_reinit_count`, `no-reinit`, `CFL 半減`, `追加診断`, `再実行`, `再生成`, `当初`, `revised criterion`, or `判定キー変更`. The only remaining scan hit is `格子再生成`, used as a technical moving-grid term in V8/V9 coverage limits.
- Traceability: §12 summary rows now use unique row IDs `U6-b1`, `U6-b2`, `U7-a1`, and `U7-a2`.
- Validation: `git diff --check` passed; `make -B -C paper` passed and generated `paper/main.pdf` (246 pages). Fatal/error/undefined/overfull scans passed. The only log warning is `Text page 147 contains only floats`, a non-fatal layout warning outside the review findings.

Stop condition met at Round 4: no MAJOR+ findings remain.
