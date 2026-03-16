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

- `docs/02_CODEGEN.md`        → algorithm implementation
- `docs/03_TESTGEN.md`        → numerical tests
- `docs/07_VERIFY.md`         → paper-to-code verification
- `docs/08_CLEANUP.md`        → dead code elimination
- `docs/09_REFACTORING.md`    → safe refactoring (SOLID)
- `docs/10_EVALUATE.md`       → component correctness evaluation
- `docs/11_WRITING.md`        → paper writing (Japanese LaTeX)
- `docs/12_REVIEW.md`         → paper review (CFD professor role)
- `docs/13_UPDATE.md`         → paper pedagogical expansion
- `docs/14_STRUCTUAL_REVIEW.md` → manuscript structural review
- `docs/15_STRUCTUAL_UPDATE.md` → manuscript structural rewrite