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

**Code workflows**

- `docs/01_CODE_MASTER.md`   → master orchestrator — paper↔code sync, sub-agent dispatch
- `docs/02_CODE_DEVELOP.md`  → algorithm implementation + MMS test generation
- `docs/03_CODE_VERIFY.md`   → test diagnosis, root-cause analysis, decision log
- `docs/04_CODE_REFACTOR.md` → dead code elimination + SOLID refactoring

**Paper workflows**

- `docs/10_PAPER_EDITOR.md`  → paper writing, pedagogical expansion, structural rewrite (Japanese LaTeX)
- `docs/11_PAPER_CRITIC.md`  → critical peer review (CFD professor role, Japanese output)
- `docs/12_LATEX_ENGINE.md`  → LaTeX compliance: `\ref{}`/`\eqref{}` + compilation repair