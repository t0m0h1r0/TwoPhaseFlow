# CHK-RA-CH12-13-STRICT-001 — §12--§13 Strict Reviewer Loop

## Scope

- Branch/worktree: `ra-ch12-13-update-20260506` / `.claude/worktrees/ra-ch12-13-update-20260506`
- Target: paper chapters 12--13, with emphasis on narrative coherence, notation consistency, and logical consistency.
- Stop rule: repeat until no MAJOR+ findings, or round count exceeds 20.
- Evidence baseline: `CHK-RA-CH12-13-UPDATE-001` reran V6/V7/V9 with `capillary_range_projection: range_projected`; this review checks whether the manuscript now reads as one coherent verification chapter.

## Round 1 Findings

### MAJOR-1 — The chapter-level stack definition omitted capillary range projection

The updated V6/V7/V9 evidence is generated on the range-projected pressure-jump stack, but §13 still defined the V6/V7/V9 subset as `reference-stack subset` without naming capillary range projection as a stack component. This made the tables appear updated while the chapter contract still described the older stack. Root fix: define `range-projected pressure-jump stack` once in §13 and use it as the canonical reading for V6/V7/V9.

Status: fixed in `paper/sections/13_verification.tex`, `13d_density_ratio.tex`, `13e_nonuniform_ns.tex`, `13f_error_budget.tex`, and the §12 bridge.

### MAJOR-2 — Pressure-output semantics did not cover all pressure-jump paths

The pressure-output paragraph named only V6/V9, while V3 has an auxiliary pressure-jump face-balance gate and V7 uses the same pressure-jump path for its coupled-stack time test. A reviewer could therefore read V7's pressure path as outside the diagnostic contract. Root fix: extend the pressure-jump PPE paragraph to V3 auxiliary gate and V6/V7/V9, while explicitly separating V7's velocity-error slope from pressure diagnostics.

Status: fixed in `paper/sections/13_verification.tex`.

### MAJOR-3 — V3/V5 Weber-number narrative had the sign of capillary scale reversed

The V3 verdict said We=1 has one order smaller capillary force than V5 at We=10. Under the paper's nondimensional reading this is reversed: the We=1 capillary pressure scale is larger. The same paragraph also risked comparing V3 peak values and V5 final-time values as one convergence sequence. Root fix: state that V3 has the larger capillary scale and that V3 peak vs V5 final-time diagnostics must not be compared as a single convergence column.

Status: fixed in `paper/sections/13b_twophase_static.tex`.

### MAJOR-4 — §12 bridge and §13 error budget retained pre-range-projection wording

The bridge table and summary table still used `projection-native / affine-history stack` or generic `reference stack` wording, which hid the decisive Hodge closure in V9 and the V6/V7 evidence. Root fix: synchronize the bridge, overview, V9 table, and final V6/V7/V9 mapping to `range-projected pressure-jump stack`.

Status: fixed in `paper/sections/12h_summary.tex`, `13e_nonuniform_ns.tex`, and `13f_error_budget.tex`.

## Round 2 Findings

Targeted scans after the Round 1 fixes found no remaining MAJOR+ issues.

- Stale range-projection values/old V7 slope scan: no matches for old `1.48`, old V6 pressure ratio `2.006`, old V9 volume floor `3.79e-8`, or old V6 speed narrative.
- Stack-name scan: only the intentional definition sentence remains, explaining that `reference stack` is the upper-set name and V6/V7/V9 are read as `range-projected pressure-jump stack`.
- Logic scan: the V3/V5 Weber-number reversal is removed.
- Paper validation: `make -C paper` passed and regenerated `paper/main.pdf` (244 pages). Fatal/error/undefined-reference scan passed. The only overfull hit remains the pre-existing `paper/sections/09f_pressure_summary.tex:71`, outside this task scope.

Stop condition met at Round 2: no MAJOR+ findings remain.
