# Docs Bundle — Ready-to-deploy documentation files

**Purpose:** This single document contains ready-to-save markdown content for the `docs/` directory. Each section below is the full content for one file. Copy each section to `docs/<filename>.md` (or use the provided shell snippet at the end to create them automatically).

---

## --- FILE: docs/PROJECT_CONTEXT.md ---

# Project Context

Project: Two-Phase Flow Solver
Language: Python
Specification: paper/ (Japanese)
Implementation: src/ (English)
Testing: pytest src/twophase/tests

Key rules:

* `paper/` is the authoritative specification and must be written in Japanese.
* `src/` is the implementation; use English for code, comments, docs.
* Deleted directories (e.g. `base/`) must never be referenced.

Minimal context for fast LLM priming (keep this section short):

* High-order CCD finite differences, level-set interface tracking, projection method.
* Backend abstraction: `xp = backend.xp` (numpy/cupy switch).

---

## --- FILE: docs/HANDOVER.md ---

# HANDOVER

Last update: 2026-03-15
Status: Implementation complete — 25 tests passing

## Current State

* Two-phase flow solver implemented from scratch.
* All unit/numerical tests: `pytest src/twophase/tests` → 25 passed.
* Python requirement: ≥ 3.9

## Repo layout (short)

* `paper/` — numerical spec (Japanese)
* `src/` — implementation (English)
* `docs/` — operational docs and LLM prompts

## Immediate TODO (short)

* GPU optimizations (CuPy custom kernels)
* Non-uniform grid tests
* 3D verification tests
* Periodic boundary support
* Output writers (VTK/HDF5)

## Quick start

```bash
pip install -e src/
pytest src/twophase/tests
```

---

## --- FILE: docs/ARCHITECTURE.md ---

# Architecture

Repository structure (short):

```
src/
  pyproject.toml
  README.md
  twophase/
    backend.py
    config.py
    simulation.py
    core/
    ccd/
    levelset/
    ns_terms/
    pressure/
    time_integration/
    tests/
paper/
docs/
```

Module responsibilities (one-line each):

* `backend`: numpy/CuPy switch (provide `xp`).
* `config`: `SimulationConfig` dataclass (all parameters).
* `simulation`: main time integration loop and CLI entry points.
* `core`: grid metrics and field wrappers.
* `ccd`: compact finite difference operators and block tridiagonal solver.
* `levelset`: heaviside/delta, curvature, advection, reinitialization.
* `ns_terms`: convection, viscous, gravity, surface tension, predictor.
* `pressure`: PPE assembly and solver, Rhie-Chow interpolation, velocity correction.
* `time_integration`: CFL, TVD-RK3 integrator.

Solver workflow (short):

1. Compute predictor (NS explicit terms)
2. Assemble and solve pressure Poisson equation
3. Velocity correction
4. Advect level set
5. Reinitialize level set

---

## --- FILE: docs/DEVELOPMENT_RULES.md ---

# Development Rules

High-level constraints:

* Numerical specification lives in `paper/` (Japanese).
* Implementation lives in `src/` (English).
* Avoid global mutable state; inject dependencies through constructors.
* Use `xp = backend.xp` for array ops; never directly import CuPy in modules.
* All new features must include tests and a short validation plan.

Coding style & commit conventions:

* Python ≥ 3.9; vectorized numpy-style code preferred.
* Commit messages: `type(scope): short` e.g. `feat(levelset): vectorized WENO5`.
* Tests in `src/twophase/tests/`.

Review and change rules for LLMs:

* LLM-proposed changes must include: 1) short summary, 2) full patch, 3) test plan or test code.
* Preface each LLM change with a one-line changelog entry appended to the doc.

---

## --- FILE: docs/CLAUDE.md ---

# Claude Instructions

Primary workflow:

1. Read `docs/PROJECT_CONTEXT.md` first.
2. Then read `docs/HANDOVER.md`, `docs/ARCHITECTURE.md`, and `docs/DEVELOPMENT_RULES.md`.
3. Summarize the current project state and wait for user instruction.

Language policy:

* Use **English** for: code, code comments, docs (under `docs/`), commit messages, and in-chat development explanations.
* Use **Japanese** for: `paper/` LaTeX manuscript and any generated paper sections.

When modifying code or docs:

* Provide a 1–3 line rationale.
* Provide the exact patch or full new file content.
* Provide tests or a validation checklist and run instructions.
* Do not reference deleted directories.

Operation modes (explicit):

* `CODEGEN` → follow `docs/02_CODEGEN.md`.
* `TESTGEN` → follow `docs/03_TESTGEN.md`.
* `REFACTOR` → follow `docs/04_REFACTOR.md`.
* `RESEARCH` → follow `docs/05_RESEARCH.md`.
* `PAPER` → follow `docs/06_PAPER_WRITING.md` (Japanese output only).

Example seed prompt to start session:

```
Read docs/CLAUDE.md and initialize the development context.
```

---

## --- FILE: docs/02_CODEGEN.md ---

# CODE GENERATION PROTOCOL

Purpose: Implement numerical algorithms from `paper/` into `src/`.

Requirements:

1. Follow the paper’s equations exactly unless the user instructs otherwise.
2. Explain the numerical method briefly (1–3 sentences) before code.
3. Output code in English, with references to paper sections (Japanese) if needed.
4. Include tests or instructions to validate correctness.

Implementation constraints:

* Support `ndim` = 2 or 3 where applicable.
* Use `xp = backend.xp` for numerical arrays.
* Keep changes minimal and well-tested.

Output format for LLMs:

* Short summary
* Code block with file path and patch
* Test or validation instructions

---

## --- FILE: docs/03_TESTGEN.md ---

# TEST GENERATION PROTOCOL

Purpose: Generate numerical and unit tests for `src/` modules.

Test types:

* Convergence/order tests (use analytic functions)
* Conservation/property tests (mass, divergence-free)
* Regression tests (numerical stability for fixed seeds)

Placement: `src/twophase/tests/`

When generating a test, the LLM must provide:

* short purpose statement
* pytest code
* run instructions and expected outcome

---

## --- FILE: docs/04_REFACTOR.md ---

# SAFE REFACTOR PROTOCOL

Goal: Improve code quality without changing numerical results.

Allowed changes:

* rename/internal restructuring for readability
* remove duplication
* modularization

Forbidden changes:

* algorithmic changes that alter numerical methods
* boundary condition modifications
* changes to discretization orders without approval

Procedure:

1. Propose a refactor and list modified files.
2. Run full test suite and report results.
3. Provide before/after code snippets.

---

## --- FILE: docs/05_RESEARCH.md ---

# RESEARCH ASSISTANT MODE

Goal: Assist research activities (benchmarks, experiments, analysis).

Outputs the LLM may produce:

* Suggested experiments with parameters
* Benchmark descriptions and validation metrics
* Short analyses of simulation output (error metrics, plots)

When writing research text for the paper, switch to `PAPER` mode (Japanese LaTeX output) by following `docs/06_PAPER_WRITING.md`.

---

## --- FILE: docs/06_PAPER_WRITING.md ---

# PAPER WRITING MODE

Purpose: Produce LaTeX manuscript sections in Japanese.

Rules:

* Output LaTeX only; do not include extraneous commentary.
* Use academic Japanese, consistent notation, and include equation references.
* Ensure every variable is defined before use.

Prompt template for the LLM:

```
Read paper/ and docs/PROJECT_CONTEXT.md.
Task: Generate a LaTeX section in Japanese on <topic>.
Requirements: valid LaTeX, define variables, reference equations in paper.
Output: LaTeX only.
```

---

## --- FILE: docs/DOC_INDEX.md ---

# DOC_INDEX

This file lists the canonical order for reading docs and which file to prime Claude with.

1. `PROJECT_CONTEXT.md` — LLM quick context (short)
2. `HANDOVER.md` — current status
3. `ARCHITECTURE.md` — code layout and responsibilities
4. `DEVELOPMENT_RULES.md` — coding & LLM rules
5. `CLAUDE.md` — operation instructions
6. `02_CODEGEN.md`, `03_TESTGEN.md`, `04_REFACTOR.md`, `05_RESEARCH.md`, `06_PAPER_WRITING.md` — mode protocols

Usage: Always prime Claude with `docs/PROJECT_CONTEXT.md` then `docs/CLAUDE.md`.

---

## --- FILE: docs/07_BENCHMARKS.md ---

# Benchmarks

This file describes reference validation problems and suggested parameters.

1. Rising bubble (2D)

* Description: buoyant bubble rising in quiescent heavy fluid
* Suggested params: Re=100, Fr=1, We=10, rho_ratio=0.001
* Diagnostics: center of mass, rise velocity, bubble shape

2. Zalesak disk (advection)

* Description: slotted disk rotational advection test
* Params: N=(128,128), 10 rotations
* Diagnostics: area conservation error

3. Rayleigh–Taylor instability

* Description: heavy fluid above light fluid
* Params: Atwood number, domain, perturbation
* Diagnostics: mixing layer growth, energy spectra

4. Droplet deformation under shear

* Description: single droplet in linear shear
* Params: Ca, Re, viscosity ratio
* Diagnostics: deformation parameter, breakup threshold

Each benchmark entry should include: input cfg, run instructions, and expected diagnostics.

---

# Auto-create script (bash)

Below is a shell snippet you can run at the repo root to create `docs/` and write each file from this bundle. It overwrites existing files with the same name.

```bash
mkdir -p docs

# The following heredoc blocks write each file. Run in a POSIX shell.
cat > docs/PROJECT_CONTEXT.md <<'MD'
$(sed -n '/^## --- FILE: docs\/PROJECT_CONTEXT.md ---$/,/^## --- FILE: docs\/HANDOVER.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/HANDOVER.md <<'MD'
$(sed -n '/^## --- FILE: docs\/HANDOVER.md ---$/,/^## --- FILE: docs\/ARCHITECTURE.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/ARCHITECTURE.md <<'MD'
$(sed -n '/^## --- FILE: docs\/ARCHITECTURE.md ---$/,/^## --- FILE: docs\/DEVELOPMENT_RULES.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/DEVELOPMENT_RULES.md <<'MD'
$(sed -n '/^## --- FILE: docs\/DEVELOPMENT_RULES.md ---$/,/^## --- FILE: docs\/CLAUDE.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/CLAUDE.md <<'MD'
$(sed -n '/^## --- FILE: docs\/CLAUDE.md ---$/,/^## --- FILE: docs\/02_CODEGEN.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/02_CODEGEN.md <<'MD'
$(sed -n '/^## --- FILE: docs\/02_CODEGEN.md ---$/,/^## --- FILE: docs\/03_TESTGEN.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/03_TESTGEN.md <<'MD'
$(sed -n '/^## --- FILE: docs\/03_TESTGEN.md ---$/,/^## --- FILE: docs\/04_REFACTOR.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/04_REFACTOR.md <<'MD'
$(sed -n '/^## --- FILE: docs\/04_REFACTOR.md ---$/,/^## --- FILE: docs\/05_RESEARCH.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/05_RESEARCH.md <<'MD'
$(sed -n '/^## --- FILE: docs\/05_RESEARCH.md ---$/,/^## --- FILE: docs\/06_PAPER_WRITING.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/06_PAPER_WRITING.md <<'MD'
$(sed -n '/^## --- FILE: docs\/06_PAPER_WRITING.md ---$/,/^## --- FILE: docs\/DOC_INDEX.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/DOC_INDEX.md <<'MD'
$(sed -n '/^## --- FILE: docs\/DOC_INDEX.md ---$/,/^## --- FILE: docs\/07_BENCHMARKS.md ---$/p' docs_bundle.md | sed '1d;$d')
MD

cat > docs/07_BENCHMARKS.md <<'MD'
$(sed -n '/^## --- FILE: docs\/07_BENCHMARKS.md ---$/,/^# Auto-create script (bash)$/p' docs_bundle.md | sed '1d;$d')
MD


echo "docs/ created. Review files and commit:"

echo "git add docs/ && git commit -m 'docs: add standardized docs bundle'"
```

---

# Notes

* This bundle is written for immediate deployment. Files are intentionally concise for token efficiency when priming LLMs.
* Paper content (LaTeX) is not included here — `paper/` remains the canonical spec and must be edited in Japanese using `docs/06_PAPER_WRITING.md` prompts.

If you want, I can:

* Create each `docs/*.md` file in the repo for you (generate patches or full-file contents),
* Or produce git-format patches for direct `git apply`.

Tell me which you prefer.
