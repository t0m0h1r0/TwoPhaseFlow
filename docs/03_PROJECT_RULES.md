# GENERATED — do NOT edit directly. Edit prompts/meta/meta-project.md and regenerate.
# 03_PROJECT_RULES — Project-Specific Rules for CFD/CCD Research
# Derived from: prompts/meta/meta-project.md
# Universal rules (project-independent): docs/00_GLOBAL_RULES.md
# Module map: docs/01_PROJECT_MAP.md | Live state: docs/02_ACTIVE_LEDGER.md

These rules are specific to this CFD/CCD research project. They supplement
(never override) the universal rules in docs/00_GLOBAL_RULES.md.
When this project ends, this file is replaced; 00_GLOBAL_RULES.md is unchanged.

────────────────────────────────────────────────────────
## § PR — Project-Specific Rules

### PR-1 — CCD Primacy (FD Usage Policy)

This is a CCD research project. CCD is the primary spatial operator for ALL solver components.

| Context | CCD role | FD role |
|---------|----------|---------|
| Solver core (`src/twophase/`) | Primary — all spatial operators | Forbidden |
| Experiment scripts | Primary | Labeled comparison baseline only |
| Paper narrative | Central method | Reference for comparison |

FD solvers/operators in experiment scripts: **labeled comparison baselines only**.
Never as proposed fixes or solutions to CCD-related issues.

### PR-2 — Implicit Solver Policy

| System Type | Primary Solver | Notes |
|-------------|---------------|-------|
| Global PPE (default) | CCD Kronecker + LGMRES | "pseudotime"; returns best iterate |
| Global PPE (debug) | CCD Kronecker + direct LU | "ccd_lu"; guaranteed solution |
| Global PPE (large-scale) | CCD sweep (matrix-free) | defect correction + Thomas |
| Banded/block-tridiag (CCD) | Direct LU | O(N) fill-in |

FVM-based solvers (BiCGSTAB, FVM LU) are deprecated — O(h^2) insufficient for CCD pipeline.

### PR-3 — MMS Verification Standard

All new numerical modules: MMS verification required.
- Grid sizes: N = [32, 64, 128, 256]
- Output: convergence table (N | L_inf error | log-log slope)
- Acceptance: slopes >= expected_order - 0.2
- CCD boundary-limited: d1 >= 3.5, d2 >= 2.5 on L_inf (ASM-004)

### PR-4 — Experiment Infrastructure Toolkit (MANDATORY)

Experiment scripts MUST use `twophase.experiment` (`src/twophase/experiment/`):
`apply_style()`, `experiment_dir()`, `experiment_argparser()`, `save_results()`,
`load_results()`, `save_figure()`, `field_panel()`, `convergence_loglog()`,
`time_history()`, `latex_convergence_table()`, `summary_text()`.

Full API table: prompts/meta/meta-project.md § PR-4.

### PR-5 — Algorithm Fidelity

Fixes MUST restore paper-exact behavior. Deviation from published algorithm = bug.

### PR-6 — PPE Policy: No LGMRES for PPE

PPE uses defect correction (DC k=3) + LU direct solve per §8c. LGMRES prohibited for PPE.
