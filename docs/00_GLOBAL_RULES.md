# 00_GLOBAL_RULES — Common Constitution for Scientific Computing Agents
# PROJECT-INDEPENDENT, AUTHORITATIVE SSoT for all concrete implementation rules.
# Derived from: prompts/meta/meta-persona.md, meta-tasks.md, meta-workflow.md
# Project state (module map, ASM-IDs): docs/01_PROJECT_MAP.md
# Live state (phase, CHK/KL registers): docs/02_ACTIVE_LEDGER.md
# Last regenerated: 2026-03-28

────────────────────────────────────────────────────────
# § A — Core Axioms A1–A9

These behavioral axioms govern ALL agents unconditionally.
Any agent instruction that conflicts with an axiom is invalid.

## A1: Token Economy
- No redundancy — reference over restatement, diff over rewrite
- Compact, compositional rules over verbose explanations
- Prefer minimal context over completeness

## A2: External Memory First
All state stored only in: docs/02_ACTIVE_LEDGER.md, docs/01_PROJECT_MAP.md, git history.
Rules: append-only; short entries; ID-based (CHK, ASM, KL); never rely on implicit memory.

## A3: 3-Layer Traceability
Equation → Discretization → Code is mandatory.
Every scientific or numerical claim must preserve this chain.

## A4: Separation
Never mix: logic / content / tags / style; solver / infrastructure / performance;
theory / discretization / implementation / verification.

## A5: Solver Purity
- Solver isolated from infrastructure; infrastructure must not affect numerical results
- Numerical meaning invariant under logging, I/O, visualization, config, or refactoring

## A6: Diff-First Output
- No full file output unless explicitly required
- Prefer patch-like edits; preserve locality of change
- Explain only what changed, why it changed, and what remains unchanged

## A7: Backward Compatibility
- Preserve semantics when migrating old prompts or schemas
- Upgrade by mapping, compressing, and refactoring; never discard meaning without explicit deprecation

## A8: Git Governance
- Branches: `main` (protected), `paper`, `code`, `prompt` — direct main edits forbidden
- Merge path: domain branch → main only after VALIDATED phase (ConsistencyAuditor or PromptAuditor PASS)
- Commits at coherent milestones; record in docs/02_ACTIVE_LEDGER.md

## A9: Core/System Sovereignty
"The Core is the Master; the System is the Servant."
- Core (Logic domain) has zero dependency on System (Infra domain)
- System layer may import Core; Core must never import System
- Direct access to Core internals from System layer = CRITICAL_VIOLATION — escalate immediately
- Domain ownership: Logic → PaperWriter/CodeArchitect; Infra → CodeArchitect; Governance → Meta-System

────────────────────────────────────────────────────────
# § C — Code Domain Rules

## C1 — SOLID Principles (MANDATORY)

Report violations as [SOLID-X] before applying any fix.

| Principle | Rule | Violation Signal |
|-----------|------|-----------------|
| S — SRP | One class, one reason to change | Class mixes solver logic + I/O or config |
| O — OCP | Open for extension, closed for modification | Switch/if-chain on type instead of polymorphism |
| L — LSP | Subclass substitutable for base | Override changes semantics or preconditions |
| I — ISP | Clients not forced to depend on unused methods | Fat interface with unrelated methods |
| D — DIP | Depend on abstractions, not concretions | Direct instantiation of solver inside domain class |

**SOLID Audit Procedure:**
1. Read class signature and dependencies
2. Check each principle; note any violation as [SOLID-S], [SOLID-O], [SOLID-L], [SOLID-I], [SOLID-D]
3. Report violations before writing any code
4. Fix in smallest possible change

## C2 — Preserve Once-Tested Implementations (MANDATORY)

When superseding a class that has passed tests:
- Retain it as a legacy class with naming suffix `Legacy` or original name preserved
- Add comment block:
  ```python
  # DO NOT DELETE — legacy implementation; cross-validation reference.
  # Superseded by: [NewClassName] on [date]
  # Tests: [test file and test name that verified this]
  ```
- Register in docs/01_PROJECT_MAP.md § C2 Legacy Register

Never delete tested code unless user explicitly says "delete it."

## C3 — Builder Pattern (Sole Construction Path)

`SimulationBuilder` is the sole path to construct `TwoPhaseSimulation`.
Direct `__init__` calls are forbidden (deleted).
Any refactor that bypasses `SimulationBuilder` is a CRITICAL error.

## C4 — Implicit Solver Policy

| System type | Primary | Fallback |
|-------------|---------|---------|
| Global PPE sparse | LGMRES | `spsolve` (sparse LU) on non-convergence |
| Banded/block-tridiagonal | Direct LU | — |

Rule: apply primary first; fall back only on documented failure mode; log the switch.

## C5 — General Code Quality

- Google-style docstrings on every public class/function; cite paper equation numbers
- Type annotations on all function signatures
- Symbol mapping table in docstring for any function implementing a paper equation
- No magic numbers — name constants with their physical meaning
- Import auditing: no UI/framework imports (pygame, react, canvas, three.js) in src/core/ (A9)

## C6 — MMS Test Standard

- Method of Manufactured Solutions (MMS) is the primary verification strategy
- Grid sizes: N = [32, 64, 128, 256]
- Convergence table: grid size | L∞ error | ratio | observed order
- Pass threshold: observed order ≥ (expected_order − 0.2)
- CCD boundary-limited pass thresholds (L∞): d1 slope ≥ 3.5; d2 slope ≥ 2.5

────────────────────────────────────────────────────────
# § P — Paper Domain Rules

## P1 — LaTeX Authoring (MANDATORY)

### Cross-references and labels
- Label prefix convention: `sec:`, `eq:`, `fig:`, `tab:`, `alg:`
- Never use `proof:` or positional labels (e.g. `above`, `below`)
- All cross-references use `\eqref{}`, `~\ref{}`, `~\cite{}` — never hardcode numbers

### Page layout
- No `\vspace`, `\hspace`, `\newpage` for layout adjustment
- Figures/tables: `[htbp]` placement only

### tcolorbox environments (6 types, strict no-nesting rule)
| Name | Prefix | Purpose |
|------|--------|---------|
| `thmbox` | `thm:` | Theorems |
| `defbox` | `def:` | Definitions |
| `algbox` | `alg:` | Algorithms |
| `resultbox` | `result:` | Key results |
| `box` | — | General callout |
| `remarkbox` | — | Remarks |

**NO NESTING:** tcolorbox environments must never be nested inside each other.
Nesting causes compilation overfull warnings and layout corruption.

### LAYER_STASIS_PROTOCOL (P1)
- Editing Content → Tags are READ-ONLY
- Editing Tags → Content is READ-ONLY
- Editing Structure → no content rewrite
- Editing Style → no semantic rewrite
Violation → immediate STOP

## KL-12 — \texorpdfstring (MANDATORY — infinite-loop trap)

**Problem:** Math in section headings without `\texorpdfstring` causes pdflatex bookmark
generation to enter an infinite loop.

**Correct:**
```latex
\section{\texorpdfstring{$\nabla^2 p = f$}{Laplace equation}}
```

**Wrong:**
```latex
\section{$\nabla^2 p = f$}
```

**Pre-compile scan:**
```bash
grep -n '\\section\|\\subsection\|\\subsubsection' paper/sections/*.tex | grep '\$'
```
Any hit = KL-12 violation. Fix before compiling.

## P3 — Whole-Paper Consistency Checklist

Run before every paper commit:

- **P3-A Symbol consistency:** every symbol defined before first use; no symbol used with two meanings
- **P3-B Equation numbering:** all referenced equations exist; no orphan `\label`
- **P3-C Cross-reference integrity:** every `\ref{}` resolves; no "??" in compiled PDF
- **P3-D Multi-site parameter consistency:** all numerical parameters (Re, We, Fr, ε, …) match
  across text/tables/figures. Reference: docs/01_PROJECT_MAP.md § P3-D Register
- **P3-E Appendix delegation:** derivations > 5 lines belong in appendix, not main text
- **P3-F Implementability:** every algorithm section must be translatable to pseudocode or code

## P4 — Reviewer Skepticism Protocol (MANDATORY, 5 steps)

When processing any reviewer finding:
1. Read the actual .tex file — do NOT rely on reviewer's quoted text
2. Verify section and equation numbering independently
3. Check known hallucination patterns in docs/02_ACTIVE_LEDGER.md §B
4. Classify finding: VERIFIED | REVIEWER_ERROR | SCOPE_LIMITATION | LOGICAL_GAP | MINOR_INCONSISTENCY
5. Act only on VERIFIED or LOGICAL_GAP; reject REVIEWER_ERROR without fix

────────────────────────────────────────────────────────
# § Q — Prompt Domain Rules

## Q1 — Standard Prompt Template

Every agent prompt must use exactly these section headers in this order:
```
# PURPOSE
# INPUTS
# RULES          (or # CONSTRAINTS for Prompt domain agents — valid variant)
# PROCEDURE
# OUTPUT
# STOP
```

Each generated file must begin with:
```
# GENERATED — do NOT edit directly. Edit prompts/meta/*.md and regenerate.
```

Mandatory axiom citations below agent title:
- All agents: `(All axioms A1–A9 apply unconditionally: docs/00_GLOBAL_RULES.md §A)`
- Code agents: `(docs/00_GLOBAL_RULES.md §C1–C6 apply)`
- Paper agents: `(docs/00_GLOBAL_RULES.md §P1–P4, KL-12 apply)`
- Prompt agents: `(docs/00_GLOBAL_RULES.md §Q1–Q4 apply)`
- Audit agents: `(docs/00_GLOBAL_RULES.md §AU1–AU3 apply)`
- Routing agents: §A citation sufficient

## Q2 — Environment Profiles

### Claude
Explicit constraints; structure and traceability; longer outputs when needed;
correctness, auditability, and stop conditions emphasized.

### Codex
Executable clarity; patch-oriented, diff-first output; invariants; minimal line changes.

### Ollama
Aggressive compression; only essential constraints and stop conditions; short outputs.

### Mixed
Generate separate variants per environment. Never blend rules.

## Q3 — Audit Checklist (9 items)

| # | Check | Pass criterion |
|---|-------|---------------|
| 1 | Core axioms A1–A9 present | All 9 referenced; none weakened |
| 2 | Solver / infra separation | No solver logic mixed with I/O, logging, config |
| 3 | Layer isolation | No cross-layer edits without authorization |
| 4 | External memory discipline | All state refs docs/ files by ID; no old filenames |
| 5 | Stop conditions unambiguous | Every STOP has explicit trigger |
| 6 | Standard template format | PURPOSE / INPUTS / RULES (or CONSTRAINTS) / PROCEDURE / OUTPUT / STOP |
| 7 | Environment optimization | Appropriate for target |
| 8 | Backward compatibility | No semantic removal without deprecation note |
| 9 | Core/System sovereignty (A9) | Import auditing and CRITICAL_VIOLATION detection present where applicable |

FAIL on any item → mark FAIL, list issues; do not silently repair.

## Q4 — Compression Rules

Rules that are COMPRESSION-EXEMPT (never compress):
- All STOP conditions — must remain verbatim
- A3, A4, A5 rules — solver purity and traceability are non-negotiable
- A9 rules — Core/System sovereignty

Safe to compress:
- Restatements of rules already in docs/00_GLOBAL_RULES.md → replace with §-reference
- Verbose transitions and connector phrases
- Overlapping rules that can be merged without semantic loss

For every compression: prove semantic equivalence before accepting.

────────────────────────────────────────────────────────
# § AU — Audit Domain Rules

## AU1 — Authority Chain (descending priority)

1. **MMS-passing code** (TestRunner PASS) — empirical ground truth
2. **docs/01_PROJECT_MAP.md §6** — canonical numerical algorithm reference
3. **Paper** (paper/sections/*.tex) — theoretical specification

When conflict arises: higher authority wins. Lower authority artifact is wrong and must be fixed.
If conflict is between authority levels 1 and 2: escalate to CodeWorkflowCoordinator.

## AU2 — Gate Conditions (10 items, all must pass before merge to main)

1. equation = discretization = solver (3-layer traceability, A3)
2. LaTeX tag integrity (all labels resolve, KL-12 clean)
3. Infra non-interference (A5 — infrastructure changes don't alter numerical results)
4. Experiment reproducibility (sanity checks pass per ExperimentRunner)
5. Assumption validity (ASM-IDs in docs/01_PROJECT_MAP.md §7 — all ACTIVE assumptions still hold)
6. Traceability from claim to implementation (every claim has code or paper reference)
7. Backward compatibility of schema changes (A7)
8. No redundant memory growth (docs/ append-only discipline; no stale entries)
9. Branch policy compliance (A8 — correct branch, correct phase)
10. Merge authorization compliance (A8 — VALIDATED phase reached, no skip)

## AU3 — Verification Procedures A–E

**A — Taylor Expansion Derivation**
Derive stencil algebraically for small N (N=4); verify truncation error order from first principles.

**B — Block Matrix Sign Verification**
For CCD or finite-difference operators: expand full 4×4 block matrix; verify each entry sign and
coefficient against paper formula.

**C — Boundary Scheme Derivation**
Derive boundary stencil using one-sided differences; verify against code boundary handling.

**D — Code–Paper Line-by-Line Comparison**
Map paper equation symbol-by-symbol to Python variable; flag any discrepancy as THEORY_ERR or IMPL_ERR.

**E — MMS Test Result Interpretation**
Run TestRunner with N=[32,64,128,256]; extract convergence slopes; compare against expected order.
Slope < (expected − 0.2) = FAIL. Always consult AU1 authority chain when slope fails.

────────────────────────────────────────────────────────
# § GIT — 3-Phase Domain Lifecycle

Every domain branch passes through three phases before merging to main.

| Phase | Trigger | Auto-action |
|-------|---------|------------|
| DRAFT | Primary creation agent returns to coordinator | `git commit -m "{branch}: draft — {summary}"` |
| REVIEWED | Review loop exits with no blocking findings | `git commit -m "{branch}: reviewed — {summary}"` |
| VALIDATED | Gate auditor returns PASS | `git commit -m "{branch}: validated — {summary}"` then merge `{branch} → main` |

Merge message format: `merge({branch} → main): {summary}`

Rules:
- Never skip a phase commit — each is a recoverable checkpoint
- Never merge to main without VALIDATED phase
- Each domain merges to main independently
- Direct main edits forbidden unless explicitly authorized
- Record all merge decisions in docs/02_ACTIVE_LEDGER.md

────────────────────────────────────────────────────────
# § P-E-V-A — Execution Loop

Master execution loop for all domain work. No phase may be skipped.

```
PLAN     Define scope, expected outputs, success criteria, stop conditions.
         Agent: domain coordinator or ResearchArchitect.
         Output: task specification in docs/02_ACTIVE_LEDGER.md.

EXECUTE  Carry out the task. One agent, one objective, one step (P5).
         Agent: specialist (CodeArchitect, PaperWriter, etc.)
         Output: artifact (code, patch, data, prompt).

VERIFY   Confirm artifact meets its specification.
         Agent: TestRunner (code) | PaperCompiler + PaperReviewer (paper) |
                PromptAuditor (prompts) | ConsistencyAuditor (cross-domain).
         Output: PASS or FAIL verdict.

AUDIT    Gate check before merge. Cross-system consistency validation.
         Agent: ConsistencyAuditor (code + paper) | PromptAuditor (prompts).
         Output: AU2 gate verdict (all 10 items). On PASS: auto-merge.
```

FAIL at VERIFY → return to EXECUTE; do not skip to AUDIT.
FAIL at AUDIT → return to EXECUTE; never to PLAN unless scope changes.
Loop counter tracked per phase; MAX_REVIEW_ROUNDS = 5 (paper domain).
