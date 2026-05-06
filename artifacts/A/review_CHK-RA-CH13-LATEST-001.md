# CHK-RA-CH13-LATEST-001 — Chapter 13 Strict Reviewer Loop

## Scope

- Branch/worktree: `codex/ra-ch13-latest-narrative-review-20260506` / `.claude/worktrees/codex-ra-ch13-latest-narrative-review-20260506`
- Target: paper Chapter 13 and directly referenced cross-paper summaries/appendix.
- Review emphasis: latest research content, convincing narrative, notation consistency, section structure, and logical coherence.
- Stop rule: repeat until no MAJOR+ findings, or round count exceeds 20.

## Round 1 Findings

### MAJOR-1 — The chapter headline still let reduced CSF/BF tests compete with the latest stack

Evidence: `paper/sections/13_verification.tex:53`--`84` defined a broad `reference operator stack` and then called V6/V7/V9 a subset. This made the latest range-projected pressure-jump closure read as one subset among many, while V3/V5/V8 CSF/BF reductions occupy much of the early narrative.

Root fix: rewrote the chapter stack paragraph so the latest two-phase standard is named first as `range-projected pressure-jump stack`, then classified V1/V2, V3/V4/V5/V8, V6/V7/V9, and V10 as purpose-specific reductions or direct tests.

### MAJOR-2 — HFE was expanded incorrectly

Evidence: `paper/sections/13_verification.tex:61` wrote `HFE（Heaviside-Flux-Embedded）`, contradicting §9.4 and U6 where HFE is `Hermite Field Extension`.

Root fix: corrected the expansion and rewrote the stack item as Hermite Field Extension supplying one-sided Hermite extension and curvature data. Synchronized the V6 wording that had `HFE-filtered curvature`.

### MAJOR-3 — V4's title overstated the test as Galilean

Evidence: `paper/sections/13c_galilean_offset.tex:5` and summary rows called V4 a `Galilean offset` residual even though the body correctly states fixed no-slip walls and pinned PPE make exact Galilean invariance impossible.

Root fix: renamed the paper-facing test to `fixed-wall uniform-offset residual` throughout Chapter 13 summaries, captions, and the section title, while preserving the explanation that this is not a zero-residual Galilean-invariance proof.

### MAJOR-4 — Latest V7 value was stale outside Chapter 13

Evidence: `paper/sections/00_abstract.tex:25` and `:62` still reported V7 slope `1.48`, while Chapter 13 now reports the range-projected stack result `1.59`.

Root fix: updated the title-page summary and abstract to `1.59`, and rewrote the appendix V7 support text to present the current range-projected result without narrating old value changes as paper content.

### MAJOR-5 — Pressure visualization text contained research-log/output-file details

Evidence: `paper/sections/13b_twophase_static.tex:127`--`132` discussed `production snapshot`, `plot-only`, and exact generated PDF counts. That reads like workflow history, not manuscript evidence.

Root fix: replaced it with the pressure-output contract: pressure-jump paths use `pressure_hodge` as the pressure-figure representative and do not use `pressure_bulk` band-masked plots.

### MINOR-1 — Projection terminology drifted between `face-flux projection` and `projection-native face closure`

Evidence: `paper/sections/13d_density_ratio.tex:17`, `13e_nonuniform_ns.tex:98`, and `13f_error_budget.tex:90` used `face-flux projection`, while §11/§13 otherwise use projection-native face closure.

Root fix: normalized those occurrences to `projection-native face closure`.

## Round 2 Findings

Pending after Round 1 remediation.
