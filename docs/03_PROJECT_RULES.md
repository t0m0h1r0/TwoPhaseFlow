# GENERATED — do NOT edit directly. Edit prompts/meta/meta-project.md and regenerate.
# 03_PROJECT_RULES — CFD/CCD project-specific rules (supplement 00_GLOBAL_RULES.md)
# Universal rules: docs/00_GLOBAL_RULES.md | Map: docs/01_PROJECT_MAP.md | State: docs/02_ACTIVE_LEDGER.md

────────────────────────────────────────────────────────
## § PR — Project-Specific Rules

### PR-1 — CCD Primacy (FD Usage Policy)

| Context | CCD role | FD role |
|---------|----------|---------|
| Solver core (`src/twophase/`) | Primary — all spatial operators | Forbidden |
| Experiment scripts | Primary | Labeled comparison baseline only |
| Paper narrative | Central method | Reference for comparison |

### PR-2 — Implicit Solver Policy

**CCD PPE indefiniteness (2026-04-15):** CCD 1D D2 has 2 wrong-sign eigenvalues (k=N-1,N) per axis → Kronecker PPE indefinite; CCD-LU blows up for general RHS. See `project_ccd_ppe_indefinite.md`.

| System Type | Primary Solver | Notes |
|-------------|---------------|-------|
| Global PPE (ch11 component tests) | CCD Kronecker + direct LU | "ccd_lu"; smooth-RHS only; **NOT for integration tests** |
| Global PPE (ch12/ch13 integration) | FD 5-point Laplacian + spsolve | negative-definite; stable for arbitrary RHS |
| Global PPE (production, via Builder) | DC sweep or FD spsolve | per SolverConfig; never CCD Kronecker+LU |
| Banded/block-tridiag (CCD) | Direct LU | O(N) fill-in; efficient |

**Policy:** `PPESolverCCDLU` restricted to ch11 component tests (smooth manufactured RHS only). ch12+ → FD PPE (`PPEBuilder`+`spsolve`) or DC sweep. BiCGSTAB deprecated.

### PR-3 — MMS Verification Standard

All new numerical modules: MMS verification required.
- Grid sizes: N = [32, 64, 128, 256]
- Output: convergence table (N | L_inf error | log-log slope)
- Acceptance: slopes >= expected_order - 0.2
- CCD boundary-limited: d1 >= 3.5, d2 >= 2.5 on L_inf (ASM-004)

### PR-4 — Experiment Data Output (MANDATORY)

Every experiment script MUST:
1. **Save raw data** (NPZ/CSV) before plotting — reproducible without re-running.
2. **Support `--plot-only`** — regenerate PDF graphs from saved data.
3. **Output PDF graphs** to `experiment/ch{N}/results/{experiment_name}/` (colocated with data).
4. **Never present results without saved data** — data file must exist first.

Use `twophase.experiment` (`src/twophase/experiment/`):
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
