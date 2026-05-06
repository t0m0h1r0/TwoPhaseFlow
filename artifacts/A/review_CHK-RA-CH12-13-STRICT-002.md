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
