# META-PROJECT: Project-Specific Profile
# VERSION: 1.0.0
# ABSTRACT LAYER — PROJECT: rules, conventions, and constraints specific to THIS research project.
# This file is the SINGLE SOURCE OF TRUTH for project-specific rules that do NOT belong in the
# universal system (meta-core.md, meta-domains.md, etc.).
#
# Separation principle:
#   - meta-core.md    → Universal axioms (A1–A11, φ1–φ7) — valid for ANY project
#   - meta-domains.md → Domain framework (T/L/E/A structure) — valid for ANY multi-domain project
#   - meta-project.md → THIS file: project-type + project-instance rules — swap this file to change project
#
# Derived output: docs/03_PROJECT_RULES.md (generated, not manually edited)
# FOUNDATION: meta-core.md §AXIOMS  ← READ FIRST

<meta_section id="META-PROJECT" version="5.1.0" axiom_refs="phi6,A7,A10">
<purpose>Project-specific profile (PR-1…PR-6). Swappable by design — replacing this file and regenerating `docs/03_PROJECT_RULES.md` retargets the entire ecosystem at a new research project without touching universal files.</purpose>
<authority>The Root Admin (ResearchArchitect) edits this file only when onboarding a new project type or instance. All other agents consult `docs/03_PROJECT_RULES.md` (generated from this file).</authority>
<rules>
- MUST NOT reference project-specific rules from meta-core.md / meta-domains.md / meta-ops.md (separation principle — keep universal files project-agnostic).
- MUST regenerate `docs/03_PROJECT_RULES.md` after any PR-{N} edit.
- PR-IDs are LOCAL to this file — do not clash with A-{N} (axioms), C-{N} (code), P-{N} (paper), Q-{N} (prompt), AU-{N} (audit).
</rules>
<see_also>docs/03_PROJECT_RULES.md (generated), meta-core.md §A, meta-deploy.md §Stage 2</see_also>

────────────────────────────────────────────────────────
# § PROJECT IDENTITY

| Field | Value |
|-------|-------|
| Project type | Computational Fluid Dynamics (CFD) research |
| Research focus | Two-phase incompressible flow with CCD (Combined Compact Difference) |
| Primary method | CCD 6th-order compact scheme for spatial discretisation |
| Solver architecture | Projection method (IPC) + CCD-based PPE |
| Target output | Doctoral thesis (LaTeX) + reproducible experiment suite |

────────────────────────────────────────────────────────
# § PR — Project-Specific Rules

These rules apply to all agents working within this project. They are NOT universal —
they derive from the research methodology, solver architecture, and tooling decisions
specific to this CFD project. When this project ends or a new project begins, this file
is replaced; the universal system (meta-core.md, meta-domains.md) remains unchanged.

## PR-1 — CCD Primacy (FD Usage Policy)

This is a CCD research project. CCD is the primary spatial operator for ALL solver components.

| Context | CCD role | FD role |
|---------|----------|---------|
| Solver core (`src/twophase/`) | Primary — all spatial operators | Forbidden |
| Experiment scripts | Primary | Labeled comparison baseline only |
| Paper narrative | Central method | Reference for comparison |

FD (finite difference) solvers/operators may appear in experiment scripts **only as labeled
comparison baselines**, never as proposed fixes or solutions to CCD-related issues.

## PR-2 — Implicit Solver Policy

| System Type | Primary Solver | Notes |
|-------------|---------------|-------|
| Global PPE (default) | CCD Kronecker + LGMRES | "pseudotime"; returns best iterate on non-convergence |
| Global PPE (debug) | CCD Kronecker + direct LU | "ccd_lu"; guaranteed solution, O(n^1.5) memory |
| Global PPE (large-scale) | CCD sweep (matrix-free) | defect correction + Thomas (O(N) per iter) |
| Banded/block-tridiag (CCD) | Direct LU | O(N) fill-in; efficient |

FVM-based solvers (BiCGSTAB, FVM LU) are deprecated — O(h^2) accuracy insufficient for CCD pipeline.

## PR-3 — MMS Verification Standard

All new numerical modules must be verified by Method of Manufactured Solutions (MMS):

| Parameter | Value |
|-----------|-------|
| Grid sizes | N = [32, 64, 128, 256] |
| Required output | Convergence table (N \| L_inf error \| log-log slope) |
| Acceptance criterion | All slopes >= expected_order - 0.2 |
| CCD boundary-limited orders | d1 >= 3.5, d2 >= 2.5 on L_inf (ASM-004) |

## PR-4 — Experiment Infrastructure Toolkit

Experiment scripts (`experiment/ch{N}/*.py`) MUST use `twophase.experiment`
(`src/twophase/experiment/`) for all non-numerical infrastructure.

| Concern | Toolkit API | Replaces |
|---------|------------|----------|
| Matplotlib setup | `apply_style()` | `matplotlib.use("Agg")` + inline fontsize/dpi |
| Output directory | `experiment_dir(__file__)` | pathlib / mkdir boilerplate |
| `--plot-only` argparse | `experiment_argparser(desc)` | manual ArgumentParser |
| NPZ save | `save_results(path, dict)` | manual flatten + np.savez |
| NPZ load | `load_results(path)` | manual np.load + scalar restore |
| PDF figure save | `save_figure(fig, path)` | fig.savefig(dpi=150, bbox_inches="tight") |
| 2D field panel | `field_panel(ax, X, Y, field, ...)` | pcolormesh + contour + colorbar |
| Convergence plot | `convergence_loglog(ax, hs, errors)` | loglog + reference slopes |
| Time series | `time_history(ax, series)` | semilogy + grid + legend |
| LaTeX table | `latex_convergence_table(path, results, cols)` | manual tabular formatting |
| Summary box | `summary_text(fig, rows)` | fig.text(family="monospace") |
| Colors/markers | `COLORS`, `MARKERS`, `LINESTYLES` | ad-hoc hex codes |
| Figure sizing | `figsize_grid(nrows, ncols)` | magic-number tuples |

Custom matplotlib calls remain allowed for domain-specific plot logic.
Direct reimplementation of toolkit concerns = A1 (Token Economy) violation.

## PR-5 — Algorithm Fidelity

Fixes MUST restore paper-exact behavior. Any deviation from the published/derived algorithm
is classified as a bug, not a design choice. The paper equation is the specification;
the code is the implementation.

**A3 chain (project-specific instance):**
```
Paper equation (paper/sections/*.tex)
  → Discretisation memo (docs/memo/*.md)
  → Code implementation (src/twophase/)
  → Experiment verification (experiment/ch{N}/)
```

## PR-6 — PPE Policy: No LGMRES for PPE

PPE must use defect correction (DC k=3) + LU direct solve per §8c.
LGMRES is prohibited for PPE due to convergence instability with CCD operators.

───────────────────────────────────────────────���────────
# § PORTABILITY NOTES

To adapt this system for a different project:

1. Replace this file (meta-project.md) with project-appropriate PR-rules
2. Regenerate docs/03_PROJECT_RULES.md from the new meta-project.md
3. Update _base.yaml `project_rules` reference if PR-IDs change
4. Universal files (meta-core.md, meta-domains.md, meta-ops.md, etc.) require NO changes

The PR-{N} numbering is local to this file. Universal rules use A-{N} (axioms),
C-{N} (code, universal), P-{N} (paper), Q-{N} (prompt), AU-{N} (audit).
</meta_section>
