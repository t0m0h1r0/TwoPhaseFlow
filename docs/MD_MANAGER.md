# MD Manager — Documentation Orchestrator

**Last update:** 2026-03-16
**Purpose:** Central manager for the project's documentation markdown files. Provides templates, update/creation rules, Claude prompts, and automation snippets so that docs in `docs/` and `paper/` stay consistent and are easy for an LLM to update.

---

## 1. When to use this file

Use `MD_MANAGER.md` whenever you need to:

* Create a new project doc (`docs/*.md`) or `paper/*.tex` helper files.
* Update an existing doc to reflect current implementation/state.
* Ask Claude (or another LLM) to generate, translate, or compress documentation.
* Standardize language & formatting across docs.

## 2. High level rules (always apply)

1. `paper/` content (LaTeX and manuscript text) **must be written in Japanese**.
2. All other code-related docs (`docs/*.md`, README, commit messages, in-code comments) **must be in English**.
3. Never reference deleted directories (e.g. `base/`).
4. Keep each doc focused: 1 file = 1 purpose (context, handover, architecture, rules, prompt templates, benchmarks, etc.).
5. When an LLM edits docs, require: short summary, the exact patch, and a test/validation checklist.

---

## 3. Document templates (copy & paste to create new files)

### PROJECT_CONTEXT.md (very short, LLM-first)

```markdown
# Project Context

Project: Two-Phase Flow Solver
Language: Python
Specification: paper/
Implementation: src/
Testing: pytest src/twophase/tests
Key rules:
- paper/ is authoritative spec (Japanese)
- src/ is implementation (English)
- deleted directories must never be referenced
```

### HANDOVER.md (concise operational state)

```markdown
# HANDOVER

Last update: YYYY-MM-DD
Status: <short status>

## Current State
- short bullets: tests, CI, noteworthy issues

## Repo structure (short)
- src/
- paper/
- docs/

## Immediate TODO
- list (1..n)

## Quick start
- install
- test
```

### ARCHITECTURE.md (reference for LLMs)

```markdown
# Architecture

Repo structure: (short tree)

Module responsibilities:
- backend: numpy/cupy switch (xp)
- levelset: interface tracking
- ccd: compact finite difference
- pressure: PPE assembly

Solver workflow:
1. predictor
2. pressure
3. correction
4. levelset
5. reinit
```

### DEVELOPMENT_RULES.md (safety + style)

```markdown
# Development Rules

- paper/ is authoritative
- no global mutable state
- backend via constructor; use xp = backend.xp
- tests required for new features
- changes must be minimal and test-first

Commit message convention:
- type(scope): brief
- e.g. feat(levelset): vectorized WENO5 advection
```

### CLAUDE.md (how to prime Claude)

```markdown
# Claude Instructions

1. Read PROJECT_CONTEXT.md first.
2. Use English for code/docs and Japanese for paper/LaTeX.
3. When asked to change code: provide summary, patch, and test results.
4. Do not reference deleted dirs.
```

---

## 4. Automation snippets

Use these bash snippets in your terminal to create a new doc from the templates above.

Create PROJECT_CONTEXT.md if missing:

```bash
mkdir -p docs
cat > docs/PROJECT_CONTEXT.md <<'MD'
# Project Context

Project: Two-Phase Flow Solver
Language: Python
Specification: paper/
Implementation: src/
Testing: pytest src/twophase/tests
Key rules:
- paper/ is authoritative spec (Japanese)
- src/ is implementation (English)
- deleted directories must never be referenced
MD

git add docs/PROJECT_CONTEXT.md && git commit -m "docs(project): add PROJECT_CONTEXT.md"
```

Create a new doc from a named template (example: HANDOVER):

```bash
TEMPLATE_NAME=HANDOVER
case $TEMPLATE_NAME in
  HANDOVER)
    cat > docs/HANDOVER.md <<'MD'
# HANDOVER

Last update: $(date +%F)
Status:

## Current State
-

## Repo structure
- src/
- paper/
- docs/

## Immediate TODO
-

## Quick start
- pip install -e src/
- pytest src/twophase/tests
MD
    ;;
  *) echo "unknown template";;
esac

git add docs/HANDOVER.md && git commit -m "docs: add HANDOVER.md"
```

---

## 5. Claude prompts (ready-to-send)

Below are short, exact prompts to give Claude. Each prompt expects Claude to read `docs/*` first.

### A. Create or update a docs file (English)

```
Read docs/PROJECT_CONTEXT.md and docs/CLAUDE.md.

Task: Create or update `docs/ARCHITECTURE.md` to reflect current code in `src/`.

Requirements:
- Keep it under 400 tokens
- Provide a 1-paragraph summary + file content
- If updating, include a short changelog at top with date

Output: full content for docs/ARCHITECTURE.md only.
```

### B. Compress HANDOVER for token reduction

```
Read docs/HANDOVER.md.
Task: Produce a condensed English HANDOVER.md (≤ 400 tokens) that preserves tests, status, and TODOs.
Output: full content only.
```

### C. Generate a new test (pytest) for a module

```
Read docs/PROJECT_CONTEXT.md and src/twophase/<module you will test>.
Task: Propose a pytest verifying one numerical property (e.g. mass conservation) and output the test code and a short explanation.
```

### D. Create/Update paper section (Japanese)

```
Read paper/current.tex (or paper/ directory) and docs/PROJECT_CONTEXT.md.
Task: Write a LaTeX section in Japanese describing the level set reinitialization method. Keep it rigorous and include any equations. Output only valid LaTeX to be pasted into paper/.
```

---

## 6. Naming & versioning conventions

* Files under `docs/` must be kebab-case or upper snake: `PROJECT_CONTEXT.md`, `HANDOVER.md`, `ARCHITECTURE.md`, etc.
* When updating a doc via LLM, prepend a one-line changelog at the top: `Last update: YYYY-MM-DD — summary`.
* Commit messages for doc changes: `docs(<file>): brief` e.g. `docs(hand-over): condense handover`.

---

## 7. When to create a new doc (decision rules)

Create a new `docs/*.md` when:

* The topic cannot be summarized in ≤ 400 tokens in an existing doc.
* You need to pin configuration for a benchmark or experiment.
* You add a new major component (GPU backend, new solver, major refactor).

Preferred filename pattern: `NN_feature.md` where `NN` is optional two-digit ordering if you want sequence (e.g. `02_CODEGEN.md`).

---

## 8. Quick check-list for LLM-driven edits

When an LLM proposes a doc change, ensure it includes:

* [ ] A one-line summary
* [ ] The proposed file content (full)
* [ ] A short test or validation plan (how to confirm accuracy)
* [ ] A suggested commit message

If any item is missing, ask the LLM to provide it before applying the change.

---

## 9. Example: adding a benchmark doc

Use this prompt to ask Claude to create `docs/07_benchmarks.md`:

```
Read docs/PROJECT_CONTEXT.md.
Task: Create docs/07_benchmarks.md describing 4 benchmark problems (rising bubble, Zalesak disk, Rayleigh–Taylor, droplet deformation). For each include: short physics description, suggested numerical parameters, and expected diagnostics. Keep the whole file < 800 tokens and in English.
Output: full file content.
```

---

## 10. Final notes

* Keep `MD_MANAGER.md` as the single source of process truth for how docs must be created and updated.
* When in doubt, prefer smaller docs and more explicit prompts to Claude.
* I can generate any of the template files or run the Claude prompts for you — tell me which file to create or update and I will produce the exact markdown content ready to paste or commit.

---

*End of MD_MANAGER.md — edit this file whenever your doc-process rules change.*
