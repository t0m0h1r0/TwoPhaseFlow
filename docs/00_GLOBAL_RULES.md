# 00_GLOBAL_RULES — Common Constitution for Scientific Computing Agents
# PROJECT-INDEPENDENT, AUTHORITATIVE SSoT for all concrete implementation rules.
# Agents read this as their primary rule reference. Edit directly — not derived.
# Axiom rationale + domain structure: prompts/meta/*.md
# Project-specific state (module map, CHK/ASM/KL registers): docs/01_PROJECT_MAP.md, docs/02_ACTIVE_LEDGER.md
# Last updated: 2026-03-28

────────────────────────────────────────────────────────
# § A — Core Axioms A1–A8

## A1: Token Economy
no redundancy; diff > rewrite; reference > duplication; compact over verbose

## A2: External Memory First
State only in: docs/02_ACTIVE_LEDGER.md, docs/01_PROJECT_MAP.md, git history.
Append-only; ID-based (CHK, ASM, KL); never rely on implicit memory.

## A3: 3-Layer Traceability
Equation → Discretization → Code mandatory for every scientific/numerical claim.

## A4: Separation
Never mix: logic/content/tags/style; solver/infrastructure/performance;
theory/discretization/implementation/verification.

## A5: Solver Purity
Infrastructure must not affect numerical results. Solver isolated from I/O, logging, config, refactoring.

## A6: Diff-First Output
No full file output unless explicitly required. Explain only what changed, why, and what is unchanged.

## A7: Backward Compatibility
Preserve semantics on migration. Never discard meaning without explicit deprecation.

## A8: Git Governance
branches: main (protected), paper, code, prompt.
merge path: domain branch → main only, after gate audit PASS.
Direct main edits forbidden unless explicitly authorized.

────────────────────────────────────────────────────────
# § C — Code Domain Rules

## C1 — SOLID Principles (MANDATORY)

All production code must comply. Report violations as `[SOLID-X] location — description` before fixing.

**S — Single Responsibility Principle**
Each class/module has exactly one reason to change.
- Solver class must not handle I/O, config parsing, or visualization.
- Violation signal: class with unrelated public methods; method name containing "and".

**O — Open/Closed Principle**
Open for extension via new class; closed for modification.
- New scheme variants → new classes implementing the shared interface; never modify existing.
- Violation signal: `if scheme == "A": ... elif scheme == "B": ...` inside a solver class.

**L — Liskov Substitution Principle**
Subclasses must be substitutable for their base class without breaking correctness.
- Every interface implementation must honour full contract (shape, dtype, BC semantics, return range).
- Violation signal: subclass that raises NotImplementedError or silently ignores BC flags.

**I — Interface Segregation Principle**
Interfaces are small and purpose-specific. Clients depend only on what they use.
- Violation signal: interface with > ~5 abstract methods; concrete class leaving stubs.

**D — Dependency Inversion Principle**
High-level modules depend on abstractions, not concretions. Constructor injection required.
- No service locators, no global singletons. Import the interface, not the concrete class.
- Violation signal: direct concrete class import in a high-level module.

**SOLID Audit Procedure:**
Before any code change:
1. State which SOLID rule(s) each new class/function affects.
2. If violation found: `[SOLID-X] Class Foo: description — fix required.`
3. Fix in same commit unless explicitly deferred.

## C2 — Preserve Once-Tested Implementations (MANDATORY)

Never delete code that has passed tests unless explicitly instructed.

When an algorithm is superseded:
1. Rename old class to descriptive legacy name (e.g., `LegacyReinitializerWENO5`).
2. Keep in same file as new implementation.
3. Add comment block:
   ```python
   # ── Legacy <AlgorithmName> implementation ─────────────────────────────────────
   # Superseded by <NewClassName>. DO NOT DELETE — used for cross-validation.
   ```
4. Ensure module compiles without error; run full test suite.

Current project legacy classes: see docs/01_PROJECT_MAP.md § C2 Legacy Register.

## C3 — Builder Pattern (Sole Construction Path)

The designated builder is the SOLE construction path for the main simulation object.
Direct `__init__` on the simulation class is forbidden.
Fixes must restore paper-exact behavior; deviation from paper = bug; improvement not in paper = out of scope (A3).

## C4 — Implicit Solver Policy

| System type | Primary | Fallback |
|---|---|---|
| Global sparse system (PPE) | Iterative solver (e.g., LGMRES) | Direct sparse LU on non-convergence |
| Banded / block-tridiagonal | Direct LU | — |

Departure from this policy requires explicit inline justification.

## C5 — General Code Quality

- No magic numbers — define named constants at module top.
- No silent BC fallback — raise `ValueError` for unknown BC strings.
- No mutable default arguments in function signatures.
- Array shapes documented in every public method: e.g., `shape (N_x, N_y)`.
- Constructor injection only — no module-level singletons, no `global` state.

## C6 — MMS Test Standard

- Grid sizes: N = [32, 64, 128, 256]
- Norms: L1, L2, L∞
- Convergence: linear regression on log-log; assert `observed_order ≥ expected_order − 0.2`
- Test determinism: reproducible from config alone

────────────────────────────────────────────────────────
# § P — Paper Domain Rules

## P1 — LaTeX Authoring (MANDATORY)

**Cross-references:**
No hardcoded references. Never write "Section 3", "Eq. (5)", "下図", "次章".
Always use `\ref{sec:...}`, `\eqref{eq:...}`, `\ref{fig:...}`, `\ref{tab:...}`.

**Page Layout:**
- Every `\part{}` and `\section{}` MUST begin on a new page (`\clearpage` or `\cleardoublepage`).
- All `\clearpage`/`\cleardoublepage` live exclusively in `main.tex` — never in section files.
- If a Part and its first Section start consecutively: ONE page break only (no double break).

**tcolorbox Environments:**
| Environment | Purpose |
|---|---|
| `defbox` | Formal definitions (numbered) |
| `warnbox` | Implementation warnings / pitfalls |
| `algbox` | Step-by-step algorithms |
| `mybox` | Supplementary notes / derivation asides |
| `resultbox` | Key numerical results / summary tables |
| `derivbox` | Mathematical derivations |

Usage rules:
- **No nesting (MANDATORY):** Never place a tcolorbox inside another tcolorbox.
  Nested breakable boxes break internal height calculation.
- Sparse and purposeful — boxes are for content readers must *find again quickly*.
- When NOT to use: physical intuition, inline derivation steps, one-time comparison tables,
  section introductions, short 1–3 line notes, summaries of what was just derived.

**Japanese Font:** No `\emph` on Japanese text — use `\textbf{和文}`.

**Label Consistency:**
- Every `\section`, `\subsection`, equation, figure, and table must have a `\label{}`.
- Allowed prefixes only: `sec:`, `eq:`, `fig:`, `tab:`, `alg:`.

**Content Rules:**
- Tangential detail → `appendix_proofs.tex`. Do not detour readers in main text.
- Every complex equation must be followed by its physical meaning and implementation implications.

## KL-12 — `\texorpdfstring` in Numbered Headings (MANDATORY — infinite-loop trap)

Any numbered `\section`, `\subsection`, or `\subsubsection` with math (`$...$`) in the title
**must** wrap the math in `\texorpdfstring{<latex>}{<plain-text>}`.
Starred variants (`\section*`) are exempt.

**Failure mode:** hyperref tries to expand math into PDF bookmark strings → infinite loop at 100% CPU.

```latex
% Correct
\section{CCD 精度：\texorpdfstring{$O(h^6)$}{O(h\textasciicircum 6)} の導出}
% Wrong — will hang xelatex
\section{CCD $O(h^6)$ 精度}
```

**Pre-compile scan (MANDATORY before every compile):**
```bash
grep -rn '\\section\b\|\\subsection\b\|\\subsubsection\b' paper/sections/ \
  | grep '\$' | grep -v 'texorpdfstring\|\*'
```
Any hit = violation. Fix before compiling.

## P3 — Whole-Paper Consistency (apply every review pass)

**P3-A: Scheme-Change Propagation**
Any scheme description change must propagate to: abstract, introduction, chapter body,
accuracy summary tables, conclusion, and all appendix sections citing the scheme.
Trigger: any edit that changes an O(Δtⁿ) order, replaces a named scheme, or renames a method.

**P3-B: Paired `\ref` / `\label` Audit**
Every `\ref{X}` must have exactly one `\label{X}`. Zero hits → add label. Two hits → remove duplicate.

**P3-C: Intermediate-Step Accuracy**
Every intermediate derivation step must be individually correct.
Only claim O(hⁿ) after verifying the leading error coefficient independently.

**P3-D: Multi-Site Parameter Consistency**
Parameters appearing in multiple sections must be non-contradictory.
Project-specific parameter/location map: docs/01_PROJECT_MAP.md § P3-D Register.

**P3-E: Bootstrap Requirement**
Algorithms with circular dependencies must explicitly describe the initialization sequence.

**P3-F: Selection Guide Completeness**
Multi-variant sections must conclude with a selection guide (table: Situation | Choice | Notes).

## P4 — Reviewer Skepticism Protocol (MANDATORY)

0. Verify section/chapter numbering independently — never trust reviewer's references.
1. Read actual .tex file in full before processing any claim.
2. Independent mathematical derivation for each finding.
3. Classify verdict: VERIFIED / REVIEWER_ERROR / SCOPE_LIMITATION / LOGICAL_GAP / MINOR_INCONSISTENCY.
4. Check docs/02_ACTIVE_LEDGER.md §B for known hallucination patterns (KL-04 through KL-12).
5. Edit only after verification — never accept reviewer claim at face value.

────────────────────────────────────────────────────────
# § Q — Prompt Domain Rules

## Q1 — Standard Prompt Template
Every agent prompt: `# PURPOSE / # INPUTS / # RULES / # PROCEDURE / # OUTPUT / # STOP`

## Q2 — Environment Profiles

**Claude:** explicit constraints, structure and traceability, longer outputs when needed,
correctness, auditability, and stop conditions emphasized.
**Codex:** executable clarity, patch-oriented, diff-first, invariants, minimal line changes.
**Ollama:** aggressive compression, only essential constraints and stop conditions, short outputs.
**Mixed:** generate separate variants per environment; do not blend rules.

## Q3 — Audit Checklist (8 items — MANDATORY)

| # | Check | Pass criterion |
|---|-------|---------------|
| 1 | Core axioms A1–A8 present | All 8 referenced; none weakened |
| 2 | Solver / infra separation | No solver logic mixed with I/O, logging, config |
| 3 | Layer isolation | No cross-layer edits without authorization |
| 4 | External memory discipline | No implicit state; all state refs docs/ files by ID |
| 5 | Stop conditions unambiguous | Every STOP item has explicit trigger condition |
| 6 | Standard template format | PURPOSE / INPUTS / RULES / PROCEDURE / OUTPUT / STOP |
| 7 | Environment optimization | Appropriate for target (Claude/Codex/Ollama) |
| 8 | Backward compatibility | No semantic removal without deprecation note |

## Q4 — Compression Rules

- Stop conditions: compression-exempt — removal is never safe.
- A3, A4, A5: compression-exempt.
- Remove only demonstrably redundant content.
- Output diff only — no full file rewrite.

────────────────────────────────────────────────────────
# § AU — Audit Domain Rules

## AU1 — Authority Chain (descending)

1. `src/` passing MMS tests
2. `docs/01_PROJECT_MAP.md §6` (Numerical Algorithm Reference)
3. `paper/sections/*.tex`

When conflicts arise: the lower-numbered authority is correct; the higher-numbered is wrong.

## AU2 — Gate Conditions (all 10 must pass for merge to main)

1. equation = discretization = solver (3-layer traceability)
2. LaTeX tag integrity
3. infra non-interference
4. experiment reproducibility
5. assumption validity
6. traceability from claim to implementation
7. backward compatibility of schema changes
8. no redundant memory growth
9. branch policy compliance
10. merge authorization compliance

If any item fails: do not merge. Explicit escalation over silent repair.

## AU3 — Verification Procedures

A — Taylor-Expansion Coefficient Verification: re-derive O(hⁿ) accuracy from scratch.
B — Block Matrix Sign Verification: verify all matrix entries independently.
C — Boundary Scheme Verification: re-derive one-sided difference formulas.
D — Code–Paper Consistency: compare implementation line-by-line against paper equations.
E — Full-Section Sequential Audit: execute A–D in order for every equation in section.

────────────────────────────────────────────────────────
# § GIT — 3-Phase Domain Lifecycle

| Phase | Trigger | Commit message |
|-------|---------|----------------|
| DRAFT | creation agent returns | `{branch}: draft — {summary}` |
| REVIEWED | review exits with no blocking findings | `{branch}: reviewed — {summary}` |
| VALIDATED | gate auditor returns PASS | `{branch}: validated — {summary}` → merge to main |

Merge message format: `merge({branch} → main): {summary}`

Per-domain coordinators: paper → PaperWorkflowCoordinator; code → CodeWorkflowCoordinator;
prompt → PromptArchitect (direct).

────────────────────────────────────────────────────────
# § P-E-V-A — Execution Loop

```
PLAN     Define scope, success criteria, stop conditions → record in docs/02_ACTIVE_LEDGER.md
EXECUTE  Specialist agent; one objective; one step
VERIFY   TestRunner (code) / PaperCompiler+PaperReviewer (paper) / PromptAuditor (prompts)
AUDIT    ConsistencyAuditor gate (AU2: all 10 items) → PASS: auto-merge
```

Rules: FAIL at VERIFY → return to EXECUTE; FAIL at AUDIT → return to EXECUTE (not PLAN unless
scope changes); MAX_REVIEW_ROUNDS = 5 for paper domain.
