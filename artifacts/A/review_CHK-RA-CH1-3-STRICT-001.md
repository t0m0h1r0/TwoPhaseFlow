# CHK-RA-CH1-3-STRICT-001 — Chapters 1--3 Strict Narrative Review

Date: 2026-05-06
Worktree: `.claude/worktrees/codex-ra-ch1-3-strict-review-20260506`
Branch: `codex/ra-ch1-3-strict-review-20260506`
Scope: `paper/sections/01*.tex`, `paper/sections/02*.tex`, `paper/sections/03*.tex`, adjacent checks against Chapters 9, 11, 13, and 14.

Stop condition: repeat review/remediation until no MAJOR+ findings remain, or round > 20.

## Round 1 Verdict: FAIL

### MAJOR-1 — The latest range-projected pressure-jump closure is not first-class in Chapters 1--2.

Chapter 1 correctly says the pressure-jump path closes interface jump, correction, and face flux in the same $D_f A_f G_f$ value space, but it does not name the current capillary range projection. Chapter 2 then derives cut-face affine jump data as if the raw Young--Laplace face value directly feeds the PPE. Chapters 9, 11, and 13 make the current contract stricter: the capillary cochain must be projected into the $D_f A_f G_f$ range before the PPE/corrector sees it. Without this, the opening chapters understate the newest central result.

### MAJOR-2 — Chapter 1's "current verification range" is stale after the Chapter 14 benchmark rewrite.

The introduction lists V6/V7/V10 as the current verification range and immediately sends long-time fully coupled moving-interface behavior to future work. That is now incomplete: Chapter 14 records a successful physical benchmark layer (capillary wave, oscillating droplet, bubble rise, and Rayleigh--Taylor) on the production stack. The introduction must separate formal convergence/diagnostic gates from physical benchmark evidence, otherwise the paper reads as if the latest benchmark results are absent.

### MAJOR-3 — Chapter 3 frames Ridge--Eikonal as conditional repair, while the latest production algorithm schedules it as a standard geometry refresh.

Chapter 3 says Ridge--Eikonal is used when $\psi$ quality exceeds thresholds or topology changes occur, and that distance reconstruction is "needed when necessary." Chapter 11 lists Ridge--Eikonal reconstruction as Stage 2 of each production time step, and Chapter 14 uses it every step in the benchmark stack. The theory can still describe reduced/diagnostic triggered use, but the main narrative must identify the current production cadence.

### MINOR-1 — The Chapter 1 roadmap omits capillary range projection from the one-line method summary.

The roadmap lists CLS, Ridge--Eikonal, FCCD/UCCD6, HFE, split PPE, DC, and projection-native closure, but not capillary range projection. This makes the roadmap less precise than the later pressure chapters.

## Round 1 Remediation Plan

- Add capillary range projection to the Chapter 1 thesis, roadmap, Chapter 2 contract, and surface-tension closure hierarchy.
- Clarify that raw cut-face Young--Laplace data is geometric input, not the final PPE/corrector cochain; the production path uses the range-projected cochain.
- Rewrite the Chapter 1 verification paragraph into formal verification gates plus Chapter 14 physical benchmark coverage.
- Recast Chapter 3 Ridge--Eikonal wording: production stack performs it as the scheduled geometry refresh, while reduced runs may use threshold-triggered repair.

## Round 1 Response

- Updated the Chapter 1 thesis so the face-space contract explicitly includes capillary range projection and affine pressure-history face acceleration.
- Replaced the stale "current verification range" paragraph with a two-layer validation narrative: formal V6/V7/V10 gates plus the Chapter 14 physical benchmark set on the same production stack.
- Added capillary range projection to the Chapter 1 roadmap and Chapter 2 governing-equation contract.
- Rewrote the Chapter 2 surface-tension hierarchy so raw cut-face Young--Laplace data is separated from the range-projected capillary cochain used by the PPE/corrector.
- Reframed Chapter 3 Ridge--Eikonal as the production stack's standard geometry update, with threshold-triggered use reserved for reduced/diagnostic paths.

## Round 2 Verdict: PASS

MAJOR+ findings: 0.

One wording issue found during Round 2 was fixed immediately: mixed Japanese/English terms around capillary projection and Ridge--Eikonal cadence were normalized to the paper's existing technical vocabulary.

Targeted rescans found no remaining stale `現行の検証範囲`, `必要時のみ`, `fallback`, `フォールバック`, `RCA`, `TODO`, trial/version-change vocabulary, or missing capillary range projection hits in the touched Chapter 1--3 summaries.

Validation:

- `git diff --check`: PASS
- Targeted stale/current-stack scan: PASS
- `make -C paper`: PASS (`paper/main.pdf`, 245 pages)
- `paper/main.log` fatal/error/undefined-reference/undefined-citation/overfull/underfull scan: PASS

[SOLID-X] Paper/docs/review artifact only; no `src/twophase/`, experiment script, config, or result file changed. No tested implementation deleted. No FD/WENO/PPE fallback, damping/CFL workaround, curvature cap, smoothing, masked-output fallback, or alternate pressure scheme introduced.
