# DOC_INDEX

Last update: 2026-03-17 — rebuilt as clean navigation index; added 16_FIX_REF, fixed STRUCTURAL typos

Navigation map for all docs/ files.

---

## Core context (read first in this order)

| # | File | Purpose |
|---|------|---------|
| 1 | `PROJECT_CONTEXT.md` | Project overview — quick LLM priming context |
| 2 | `HANDOVER.md` | Current status, recent changes, known TODOs |
| 3 | `ARCHITECTURE.md` | Code layout, module responsibilities, solver workflow |
| 4 | `DEVELOPMENT_RULES.md` | Coding standards, commit conventions, LLM change rules |
| 5 | `CLAUDE.md` | Claude operation instructions and mode dispatch |

---

## Workflow mode protocols

### Code workflows

| File | Mode | Purpose |
|------|------|---------|
| `02_CODEGEN.md`        | CODEGEN   | Implement algorithms from paper into src/ |
| `03_TESTGEN.md`        | TESTGEN   | Generate numerical and unit tests |
| `07_VERIFY.md`         | VERIFY    | Paper-to-code fidelity verification (7-step) |
| `08_CLEANUP.md`        | CLEANUP   | Dead code and legacy code elimination (8-step) |
| `09_REFACTORING.md`    | REFACTOR  | SOLID architecture refactoring (6-step) |
| `10_EVALUATE.md`       | EVALUATE  | Component correctness via MMS/convergence (8-step) |

### Paper workflows

| File | Mode | Purpose |
|------|------|---------|
| `11_WRITING.md`          | WRITING        | Write Japanese LaTeX sections |
| `12_REVIEW.md`           | REVIEW         | CFD professor manuscript review |
| `13_UPDATE.md`           | UPDATE         | Pedagogical expansion of .tex files |
| `14_STRUCTURAL_REVIEW.md`| STRUCT-REVIEW  | Manuscript structural review (TOC/order/figures) |
| `15_STRUCTURAL_UPDATE.md`| STRUCT-UPDATE  | Implement revised manuscript structure |
| `16_FIX_REF.md`          | FIX-REF        | Enforce `\ref{}`/`\eqref{}` semantic labels |

---

## Meta files

| File | Purpose |
|------|---------|
| `MD_MANAGER.md` | Rules for creating and updating docs/ files |
| `prompt_catalog.md` | Full catalog of all workflow prompts |

---

Usage: Prime Claude with `docs/PROJECT_CONTEXT.md` then `docs/CLAUDE.md`.
