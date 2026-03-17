# Prompt Catalog

Last update: 2026-03-18 — complete rewrite for consolidated 7-prompt system

Navigation map for all workflow prompt files in `docs/`.
See `DOC_INDEX.md` for canonical reading order.

---

## Naming Convention

Workflow prompts follow: `NN_DOMAIN_ROLE.md`

- `NN` — two-digit sequence (01–09 = code, 10–19 = paper, 99 = meta)
- `DOMAIN` — `CODE` or `PAPER`
- `ROLE` — uppercase noun describing the agent role

---

## Code Workflow Prompts

### [01_CODE_MASTER.md](01_CODE_MASTER.md)

**Role:** Master Orchestrator & Lead Scientist

**Purpose:** Drive the overall paper↔code verification loop. Parse the paper, build a Component Inventory, identify unverified components, and dispatch the appropriate sub-agent.

**When to use:** At the start of a session to get an up-to-date project status, or when you need to decide which sub-agent to invoke next.

**Output:** Project summary, Component Inventory table (paper ref → file → status), Top-3 next actions with sub-agent targets.

**Dispatches to:** `02_CODE_DEVELOP`, `03_CODE_VERIFY`, `04_CODE_REFACTOR`

---

### [02_CODE_DEVELOP.md](02_CODE_DEVELOP.md)

**Role:** Elite Scientific Software Engineer & Test Architect

**Purpose:** Translate mathematical equations from the paper into production-ready Python modules with rigorous MMS (Method of Manufactured Solutions) tests.

**When to use:** Implementing a new algorithm, discretization scheme, or numerical component from a paper section or equation.

**Key constraints:**
- Follow equations exactly; never alter discretization
- Use injected `xp` backend for all array ops
- Cite equation numbers in docstrings
- MMS test must assert convergence order (observed ≥ expected − 0.2)

**Output:** Variable mapping → architecture → source code → test code → CLI run instructions.

---

### [03_CODE_VERIFY.md](03_CODE_VERIFY.md)

**Role:** Senior Numerical Verifier & Project Lead

**Purpose:** Interpret test outputs, diagnose numerical failures, determine root cause (code bug vs. paper error), and propose the authoritative fix.

**When to use:** After running tests, when convergence is wrong, or when a component behaves unexpectedly.

**Key constraints:**
- Rank root-cause hypotheses with confidence scores
- Every decision must be evidence-based
- Paper corrections must be in Japanese LaTeX

**Output:** Diagnostic thinking → diagnosis summary → resolution (diff or Japanese LaTeX fix) → JSON decision log.

---

### [04_CODE_REFACTOR.md](04_CODE_REFACTOR.md)

**Role:** Senior Software Architect & Code Auditor

**Purpose:** Eliminate dead code, reduce duplication, and improve architecture without altering numerical behavior or external APIs.

**When to use:** Architecture has grown complex, backward-compat code is stale, or a cleanup pass is needed after refactoring.

**Risk levels:** `SAFE_REMOVE` / `LOW_RISK` / `HIGH_RISK`

**Key constraint:** External behavior and numerical results must remain identical (bitwise where possible).

**Output:** Analysis → findings inventory table → migration plan → diff patch → verification commands.

---

## Paper Workflow Prompts

### [10_PAPER_EDITOR.md](10_PAPER_EDITOR.md)

**Role:** Distinguished Professor & Academic Editor (CFD)

**Purpose:** Write and expand LaTeX manuscript sections with textbook-quality pedagogical depth. Covers initial drafting, pedagogical expansion of terse sections, and structural rewriting.

**When to use:**
- Adding new sections to `paper/`
- Expanding terse derivations into step-by-step textbook content
- Rewriting manuscript structure after a structural review

**Key constraints:**
- Manuscript text in Academic Japanese (である/だ style)
- Zero information loss — expand, never condense
- Follow complex equations with physical meaning + algorithmic implications
- Use `tcolorbox`, `algorithm2e`, `align` environments

**Output:** Structural intent (English) → complete ready-to-compile LaTeX block (Japanese).

---

### [11_PAPER_CRITIC.md](11_PAPER_CRITIC.md)

**Role:** No-punches-pulled Peer Reviewer & Senior Research Scientist

**Purpose:** Rigorous audit of the LaTeX manuscript — logical consistency, mathematical validity, pedagogical clarity, and structural flow.

**When to use:** After a writing pass to catch logical gaps, circular logic, dimension mismatches, or weak derivations.

**Key constraints:** Entire output in Japanese. Authorized to recommend complete removal of invalid/redundant content.

**Output (Japanese):**
- 【致命的な矛盾と改修案】Fatal contradictions with fixes
- 【論理の飛躍と「行間」の指摘】Logical leaps and missing steps
- 【実装容易性の評価】Implementation readiness critique
- 【構成・レイアウトへの辛口評価】Structure and layout critique

---

### [12_LATEX_ENGINE.md](12_LATEX_ENGINE.md)

**Role:** LaTeX Compliance & Repair Engine

**Purpose:** Enforce strict authoring rules — replace all hard-coded section/figure/equation numbers with `\ref{}`/`\eqref{}`, and fix any compilation errors with minimal intervention.

**When to use:**
- After structural rewrites where numbering may have shifted
- When `latexmk` reports errors (fontspec, missing packages, syntax)
- Before final submission to ensure cross-reference integrity

**Key constraints:**
- Anti-hardcoding: no manual "Section 3", "Eq. (5)" allowed
- Minimal intervention — fix errors without rewriting prose
- Consistent label naming: `sec:`, `eq:`, `fig:`

**Output:** Refactor report (replaced refs, added labels, diagnosed errors) → unified diff / updated files → compliance status.

---

## Prompt Relationships

```
Code development workflow:
  01_CODE_MASTER → dispatches to:
    02_CODE_DEVELOP  (implement + test)
    03_CODE_VERIFY   (diagnose failures)
    04_CODE_REFACTOR (cleanup + SOLID)

Paper writing workflow:
  10_PAPER_EDITOR   (write / expand / restructure)
    → 11_PAPER_CRITIC (critical review)
    → 10_PAPER_EDITOR (address critique)
    → 12_LATEX_ENGINE (fix refs + compile)

Typical full cycle:
  02_CODE_DEVELOP → 03_CODE_VERIFY → 01_CODE_MASTER (re-assess)
  10_PAPER_EDITOR → 11_PAPER_CRITIC → 10_PAPER_EDITOR → 12_LATEX_ENGINE
```

---

## Meta Prompts

### [99_PROMPT.md](99_PROMPT.md)

**Purpose:** Evolve and maintain the prompt system itself.

**When to use:** When prompts become stale, redundant, or the project has changed significantly.

**Process:** Repository analysis → prompt inventory → quality evaluation → optimization → naming → architecture → updates → catalog.
