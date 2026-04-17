# GENERATED — do NOT edit directly. Edit prompts/meta/kernel-project.md and regenerate.
# 03_PROJECT_RULES — CFD/CCD project-specific rules (supplement 00_GLOBAL_RULES.md)
# Universal rules: docs/00_GLOBAL_RULES.md | Map: docs/01_PROJECT_MAP.md | State: docs/02_ACTIVE_LEDGER.md

────────────────────────────────────────────────────────
## § PROJECT IDENTITY

| Field | Value |
|-------|-------|
| Project type | Computational Fluid Dynamics (CFD) research |
| Research focus | Two-phase incompressible flow with CCD (Combined Compact Difference) |
| Primary method | CCD 6th-order compact scheme for spatial discretisation |
| Solver architecture | Projection method (IPC) + CCD-based PPE |
| Target output | Doctoral thesis (LaTeX) + reproducible experiment suite |

────────────────────────────────────────────────────────
## § PR — Project-Specific Rules

## PR-1 — CCD Primacy (FD Usage Policy)

| Context | CCD role | FD role |
|---------|----------|---------|
| Solver core (`src/twophase/`) | Primary — all spatial operators | Forbidden |
| Experiment scripts | Primary | Labeled comparison baseline only |
| Paper narrative | Central method | Reference for comparison |

## PR-2 — Implicit Solver Policy

**CCD PPE indefiniteness (2026-04-15):** CCD 1D D2 has 2 wrong-sign eigenvalues (k=N-1,N) per axis → Kronecker PPE indefinite; CCD-LU blows up for general RHS. See `project_ccd_ppe_indefinite.md`.

| System Type | Primary Solver | Notes |
|-------------|---------------|-------|
| Global PPE (ch11 component tests) | CCD Kronecker + direct LU | "ccd_lu"; smooth-RHS only; **NOT for integration tests** |
| Global PPE (ch12/ch13 integration) | FD 5-point Laplacian + spsolve | negative-definite; stable for arbitrary RHS |
| Global PPE (production, via Builder) | DC sweep or FD spsolve | per SolverConfig; never CCD Kronecker+LU |
| Banded/block-tridiag (CCD) | Direct LU | O(N) fill-in; efficient |

**Policy:** `PPESolverCCDLU` restricted to ch11 component tests (smooth manufactured RHS only). ch12+ → FD PPE (`PPEBuilder`+`spsolve`) or DC sweep. BiCGSTAB deprecated.

## PR-3 — MMS Verification Standard

All new numerical modules: MMS verification required.
- Grid sizes: N = [32, 64, 128, 256]
- Output: convergence table (N | L_inf error | log-log slope)
- Acceptance: slopes >= expected_order - 0.2
- CCD boundary-limited: d1 >= 3.5, d2 >= 2.5 on L_inf (ASM-004)

## PR-4 — Experiment Infrastructure Toolkit

Every experiment script (`experiment/ch{N}/*.py`) MUST use `twophase.experiment` (`src/twophase/experiment/`) for all non-numerical infrastructure:

| Concern | Toolkit API |
|---------|------------|
| Matplotlib setup | `apply_style()` |
| Output directory | `experiment_dir(__file__)` |
| `--plot-only` argparse | `experiment_argparser(desc)` |
| NPZ save/load | `save_results()` / `load_results()` |
| PDF figure save | `save_figure(fig, path)` |
| 2D field panel | `field_panel(ax, X, Y, field, ...)` |
| Convergence plot | `convergence_loglog(ax, hs, errors)` |
| Time series | `time_history(ax, series)` |
| LaTeX table | `latex_convergence_table(path, results, cols)` |
| Summary box | `summary_text(fig, rows)` |
| Colors/markers | `COLORS`, `MARKERS`, `LINESTYLES` |
| Figure sizing | `figsize_grid(nrows, ncols)` |

Full API: `prompts/meta/kernel-project.md § PR-4`. Direct reimplementation = A1 violation.

## PR-5 — Algorithm Fidelity

Fixes MUST restore paper-exact behavior. Deviation from published algorithm = bug.

**A3 chain:**
```
Paper equation (paper/sections/*.tex)
  → Discretisation memo (docs/memo/*.md)
  → Code implementation (src/twophase/)
  → Experiment verification (experiment/ch{N}/)
```

## PR-6 — PPE Policy: No LGMRES for PPE

PPE uses defect correction (DC k=3) + LU direct solve per §8c. LGMRES prohibited for PPE.

**Chapter scope (2026-04-15):**
- ch11 (component tests): CCD Kronecker+LU allowed for smooth manufactured RHS
- ch12+ (integration tests): FD PPE (`PPEBuilder`+`spsolve`) or DC sweep only
- `PPESolverCCDLU` must NOT appear in ch12+ integration scripts
