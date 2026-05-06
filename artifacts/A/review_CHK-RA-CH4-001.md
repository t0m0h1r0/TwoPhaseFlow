# Review CHK-RA-CH4-001 — Chapters 4--11 Strict Narrative Audit

Date: 2026-05-06
Branch: `ra-ch4-11-narrative-review-20260506`
Scope: `paper/sections/04*.tex` through `paper/sections/11*.tex`
Reviewer stance: severe paper reviewer; emphasis on narrative necessity, notation unity, and logical consistency.

## Round 1 Verdict: FAIL

### MAJOR-1: DCCD was still presented as a CLS/default stabilizer after the paper had moved the standard path to FCCD/UCCD6

Evidence before remediation:

- `paper/sections/04c_dccd_derivation.tex` header stated that DCCD was the CLS advection implementation default.
- `paper/sections/11_full_algorithm.tex` mapped checkerboard suppression to DCCD and listed DCCD parameters for CLS/PPE divergence/curvature.
- `paper/sections/06_scheme_per_variable.tex` and `paper/sections/06b_advection.tex` already stated the current standard path: CLS `\psi` uses FCCD face flux, bulk momentum uses UCCD6, and pressure/BF closure must not be smoothed by DCCD.

Why this is MAJOR:

The reader would enter §4 believing DCCD is the operative CLS default, then reach §6/§11 where FCCD/UCCD6 are standard. This is not a stylistic mismatch; it breaks the method hierarchy and obscures the pressure no-DCCD rule later verified in U9.

Remediation:

- Reframed DCCD in §4.4 as a node-centered CCD exterior post-filter with explicit application boundaries.
- Restated that standard CLS advection is FCCD face flux and bulk momentum is UCCD6.
- Removed the §11 global DCCD-stabilization narrative and replaced it with face-flux / same-locus projection closure.
- Rewrote §11 reinitialization from hard-coded DCCD/DGR frequencies to the §5 Stage B--F Ridge--Eikonal and mass-closure contract.

### MAJOR-2: §11 reintroduced research-log parameters as if they were the final one-step algorithm

Evidence before remediation:

- §11 used fixed `n_reinit = 4`, `theta_reinit = 1.10`, fixed-frequency DGR, and a DCCD reinitialization label inside the canonical seven-step update.

Why this is MAJOR:

The integrated algorithm chapter must state the mathematical update contract, not an experiment configuration. The old wording made the algorithm depend on tuning constants rather than on the Stage A--F responsibilities already established in §5.

Remediation:

- Replaced the fixed-parameter block with the invariant contract: physical transport, geometry projection, and `\phi`-space mass closure are separate discrete identities.
- Kept iterative Eikonal parameters only as comparison-path guidance, not as the standard path identity.

### MINOR-1: Notation and paper-register wording drift

Evidence before remediation:

- §5 used `production`, `gate`, `設定ファイル`, and `旧実装` language in theory chapters.
- §5b used bare `\kappa` where the paper convention requires `\kappa_{lg}`.
- §6d used `fallback` / `現行実装` wording where the claim was a discretization placement rule.

Remediation:

- Replaced implementation-history language with standard path / comparison path / closure condition wording.
- Unified §5b curvature wording to `\kappa_{lg}`.
- Reworded §6d to stress low-order interface-band closure and collocated stress placement, not implementation fallback.

## Round 2 Verdict: PASS

MAJOR+: 0
FATAL: 0
Residual MINOR: existing overfull hbox in `paper/sections/09f_pressure_summary.tex:71` remains outside this change.

Post-remediation checks:

- Targeted terminology scan: no remaining claim that DCCD is the standard CLS default.
- `git diff --check`: PASS.
- `make -C paper`: PASS; produced `paper/main.pdf` with 244 pages.

[SOLID-X] Paper/docs only; no solver code, experiment scripts, configs, or result files changed. No FD/WENO/PPE fallback or alternate pressure scheme introduced.
