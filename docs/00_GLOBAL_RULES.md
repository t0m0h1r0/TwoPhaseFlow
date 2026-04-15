# 00_GLOBAL_RULES — Universal Rules for Scientific Computing
# Project-specific rules: docs/03_PROJECT_RULES.md
# Module map + ASM-IDs: docs/01_PROJECT_MAP.md
# Live state (phase, CHK/KL): docs/02_ACTIVE_LEDGER.md
# Meta-sources: prompts/meta/*.md (A10: single source of truth)

────────────────────────────────────────────────────────
## § A — Core Axioms A1–A11

| ID | Name | Rule |
|----|------|------|
| A1 | Token Economy | diff > rewrite; reference > duplication |
| A2 | External Memory First | State in docs/*.md + git only; append-only; ID-based (CHK, ASM, KL) |
| A3 | 3-Layer Traceability | Equation → Discretization → Code chain mandatory |
| A4 | Separation | Never mix: solver/infrastructure; theory/discretization/implementation/verification |
| A5 | Solver Purity | `src/twophase/` has zero I/O, logging, config dependency; numerical invariant |
| A6 | Diff-First Output | No full file output unless explicitly required |
| A7 | Backward Compatibility | Never discard meaning without explicit deprecation |
| A8 | Git Governance | `main` protected; worktrees for isolated work |
| A9 | Core/System Sovereignty | `src/core/` never imports from `src/system/` |
| A10 | Meta-Governance | `prompts/meta/` is SSoT; `docs/` are derived |
| A11 | Knowledge-First | Prefer `docs/wiki/` over re-derivation |

**Key principles:** φ1 evidence before action; φ2 minimal footprint; φ6 change the source, not the derived artifact; φ7 classify before acting.

────────────────────────────────────────────────────────
## § C — Code Domain Rules

### C1 — SOLID Principles
Report violations as `[SOLID-X]` and fix before proceeding. Key checks:
- **S**: class doing I/O + computation → split
- **D**: high-level imports concrete class → inject interface

### C2 — Preserve Once-Tested Implementations
Never delete code that passed tests. Superseded → `{Name}Legacy` with `# DO NOT DELETE` comment.
Registry: `docs/01_PROJECT_MAP.md §8`.

### C3 — Builder Pattern
`SimulationBuilder` is the sole construction path (ASM-001).

### C4 — General Code Quality
- Google-style docstrings with equation number citations for numerical methods
- No UI/framework imports in `src/core/` (A9)
- Symbol mapping table (paper notation → Python variable) for new modules

Project-specific rules (PR-1–PR-6): `docs/03_PROJECT_RULES.md`.

────────────────────────────────────────────────────────
## § P — Paper Domain Rules

### P1 — LaTeX Authoring
- Cross-references: `\ref`, `\eqref`, `\autoref` — never hardcode numbers
- Label prefixes: `sec:`, `eq:`, `fig:`, `tab:`, `alg:`, `app:`
- tcolorbox: 6 types (mybox/defbox/resultbox/algbox/warnbox/remarkbox) — **never nest**
- Figures/tables: `[htbp]`; captions below figures, above tables

### KL-12 — texorpdfstring (xelatex infinite-loop trap)
Math in section/subsection titles or captions MUST use `\texorpdfstring`.
Pre-compile scan: `grep -n "\\section\|\\subsection\|\\caption" paper/sections/*.tex | grep "\$" | grep -v "texorpdfstring"` → zero matches required.

### P3 — Whole-Paper Consistency
- P3-A: symbol consistency; P3-B: equation↔code (A3); P3-C: cross-ref integrity
- P3-D: multi-site parameters (register: `docs/01_PROJECT_MAP.md §10`)
- P3-E: narrative coherence; P3-F: tcolorbox type↔content

### P4 — Reviewer Skepticism
Independently verify before applying any reviewer finding. "Reviewer says so" is never sufficient.

────────────────────────────────────────────────────────
## § AU — Verification Authority Chain

When sources disagree, authority descends:
1. First principles (independent derivation)
2. MMS-passing code (`src/twophase/`)
3. Paper equations (`paper/sections/*.tex`)

Error taxonomy: **THEORY_ERR** (solver/equation) vs **IMPL_ERR** (adapter/infrastructure).

────────────────────────────────────────────────────────
## § Reference (agent prompt system, git lifecycle, prompt rules)

Full details in `prompts/meta/*.md`. Key points:
- Agent prompts: `prompts/agents-claude/*.md` (read as domain reference)
- Prompt template: PURPOSE / INPUTS / RULES / PROCEDURE / OUTPUT / STOP
- Git lifecycle: DRAFT → REVIEWED → VALIDATED → merge to main
- Merge criteria: tests pass + compile success + logs attached
- Execution loop: PLAN → EXECUTE → VERIFY → AUDIT (no phase skipped)
