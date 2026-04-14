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

**CCD PPE indefiniteness (2026-04-15):** CCD 1D D2 matrix has 2 wrong-sign
eigenvalues (modes k=N-1, N) per axis. The Kronecker-product PPE operator is
therefore indefinite. CCD-LU blows up for general RHS; DC+FD-LU stalls at
O(h²). See memory `project_ccd_ppe_indefinite.md` for derivation.

| System Type | Primary Solver | Notes |
|-------------|---------------|-------|
| Global PPE (ch11 component tests) | CCD Kronecker + direct LU | "ccd_lu"; smooth-RHS only; **NOT for integration tests** |
| Global PPE (ch12/ch13 integration) | FD 5-point Laplacian + spsolve | negative-definite; stable for arbitrary RHS |
| Global PPE (production, via Builder) | DC sweep or FD spsolve | per SolverConfig; never CCD Kronecker+LU |
| Banded/block-tridiag (CCD) | Direct LU | O(N) fill-in; efficient |

**Policy:** CCD Kronecker+LU (`PPESolverCCDLU`) is restricted to ch11
component-level unit tests with smooth manufactured RHS. For ch12+ integration
simulations (droplet, RT, etc.), use FD PPE (`PPEBuilder` + `spsolve`) or
DC sweep. FVM-based iterative solvers (BiCGSTAB) remain deprecated.

### PR-3 — MMS Verification Standard

All new numerical modules: MMS verification required.
- Grid sizes: N = [32, 64, 128, 256]
- Output: convergence table (N | L_inf error | log-log slope)
- Acceptance: slopes >= expected_order - 0.2
- CCD boundary-limited: d1 >= 3.5, d2 >= 2.5 on L_inf (ASM-004)

### PR-4 — Experiment Data Output (MANDATORY)

Every experiment script MUST:
1. **Save raw data** (NPZ/CSV) before plotting — results must be reproducible without re-running the simulation.
2. **Support `--plot-only`** — regenerate PDF graphs from saved data without computation.
3. **Output PDF graphs** to `experiment/ch{N}/results/{experiment_name}/` (colocated with data).
4. **Never present results without saved data** — if asked for results, the data file must already exist.

Violation = data loss risk. Re-running expensive simulations (CCD-LU, N=64+) wastes hours.

When available, use `twophase.experiment` (`src/twophase/experiment/`):
`apply_style()`, `experiment_dir()`, `experiment_argparser()`, `save_results()`,
`load_results()`, `save_figure()`, `field_panel()`, `convergence_loglog()`,
`time_history()`, `latex_convergence_table()`, `summary_text()`.

Full API table: prompts/meta/meta-project.md § PR-4.

### PR-5 — Algorithm Fidelity

Fixes MUST restore paper-exact behavior. Deviation from published algorithm = bug.

### PR-6 — PPE Policy: No LGMRES for PPE

PPE uses defect correction (DC k=3) + LU direct solve per §8c. LGMRES prohibited for PPE.

**Chapter scope (2026-04-15):**
- ch11 (component tests): CCD Kronecker+LU allowed for smooth manufactured RHS
- ch12+ (integration tests): FD PPE (`PPEBuilder`+`spsolve`) or DC sweep only
- `PPESolverCCDLU` must NOT appear in ch12+ integration scripts
