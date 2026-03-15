# Claude Instructions

You are assisting development of a CFD research code.

Before doing any task:

1. Read

- docs/PROJECT_CONTEXT.md
- docs/HANDOVER.md
- docs/ARCHITECTURE.md
- docs/DEVELOPMENT_RULES.md

2. Summarize the current project state.

3. Wait for user instructions.

---

# Language Policy (Important)

Use **English** for:

- code
- comments
- documentation
- commit messages
- development explanations

Use **Japanese** only for:

- research papers
- paper sections
- LaTeX manuscript generation

Paper files are located in:


paper/


All LaTeX content generated for the paper must be written in **Japanese**.

---

# Implementation Rules

- `paper/` is the numerical specification
- `src/` contains the implementation
- never reference deleted directories
- avoid global mutable state
- backend must use `xp = backend.xp`

---

# Workflow

When modifying code:

1. Explain reasoning briefly
2. Show the patch
3. Ensure tests pass

Prefer minimal changes.

---

# Modes

If instructed, follow the appropriate protocol:

- `docs/02_CODEGEN.md` → algorithm implementation
- `docs/03_TESTGEN.md` → numerical tests
- `docs/04_REFACTOR.md` → safe refactoring
- `docs/05_RESEARCH.md` → research assistance