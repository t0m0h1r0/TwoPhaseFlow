# DOC_INDEX

Last update: 2026-03-18 — updated workflow table to reflect new 7-prompt consolidation (01-04 code, 10-12 paper)

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
| `01_CODE_MASTER.md`   | MASTER   | Orchestrate paper↔code sync; dispatch sub-agents |
| `02_CODE_DEVELOP.md`  | DEVELOP  | Implement algorithms from paper; generate MMS tests |
| `03_CODE_VERIFY.md`   | VERIFY   | Diagnose test failures; root-cause analysis; decision log |
| `04_CODE_REFACTOR.md` | REFACTOR | Dead code elimination + SOLID architecture refactoring |

### Paper workflows

| File | Mode | Purpose |
|------|------|---------|
| `10_PAPER_EDITOR.md`  | EDITOR   | Write/expand Japanese LaTeX sections (Distinguished Professor) |
| `11_PAPER_CRITIC.md`  | CRITIC   | Critical peer review of manuscript (CFD professor, Japanese) |
| `12_LATEX_ENGINE.md`  | LATEX    | Enforce `\ref{}`/`\eqref{}` labels; fix compilation errors |

---

## Meta files

| File | Purpose |
|------|---------|
| `MD_MANAGER.md` | Rules for creating and updating docs/ files |
| `prompt_catalog.md` | Full catalog of all workflow prompts |

---

Usage: Prime Claude with `docs/PROJECT_CONTEXT.md` then `docs/CLAUDE.md`.
