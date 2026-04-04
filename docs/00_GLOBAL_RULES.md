# GENERATED — do NOT edit directly. Edit prompts/meta/*.md and regenerate.
# 00_GLOBAL_RULES — Common Constitution for Scientific Computing Agents
# PROJECT-INDEPENDENT, AUTHORITATIVE SSoT for all concrete implementation rules.
# Derived from: prompts/meta/meta-core.md, meta-persona.md, meta-roles.md, meta-workflow.md, meta-ops.md
# Project state (module map, ASM-IDs): docs/01_PROJECT_MAP.md
# Live state (phase, CHK/KL registers): docs/02_ACTIVE_LEDGER.md

All axioms and domain constraints defined here apply unconditionally to every agent in the system.
No agent may override, weaken, or bypass these rules without explicit user escalation.

────────────────────────────────────────────────────────
## § A — Core Axioms A1–A10

These axioms are the immutable foundation of all agent behavior. They are compression-exempt (Q4):
no prompt compression may weaken or remove them.

| ID | Name | Rule |
|----|------|------|
| A1 | Token Economy | No redundancy; diff > rewrite; reference > duplication. Prefer compact, compositional rules over verbose explanations. |
| A2 | External Memory First | State only in: docs/02_ACTIVE_LEDGER.md, docs/01_PROJECT_MAP.md, git history. Append-only; short entries; ID-based (CHK, ASM, KL); never rely on implicit memory. |
| A3 | 3-Layer Traceability | Equation → Discretization → Code is mandatory. Every scientific or numerical claim must preserve this chain. |
| A4 | Separation | Never mix: logic/content/tags/style; solver/infrastructure/performance; theory/discretization/implementation/verification. |
| A5 | Solver Purity | Solver isolated from infrastructure; infrastructure must not affect numerical results. Numerical meaning invariant under logging, I/O, visualization, config, or refactoring. |
| A6 | Diff-First Output | No full file output unless explicitly required. Prefer patch-like edits; preserve locality; explain only what changed and why. |
| A7 | Backward Compatibility | Preserve semantics when migrating; upgrade by mapping and compressing. Never discard meaning without explicit deprecation. |
| A8 | Git Governance | Branches: `main` (protected); `code`, `paper`, `prompt` (domain integration staging); direct main edits forbidden. `dev/{agent_role}`: individual workspaces — sovereign per agent; no cross-agent access. Merge path: dev/{agent_role} → {domain} (Gatekeeper PR) → main (Root Admin PR) after VALIDATED phase. |
| A9 | Core/System Sovereignty | "The solver core is the master; the infrastructure is the servant." `src/core/` has zero dependency on `src/system/`. Infrastructure may import solver core; solver core must never import infrastructure. Direct access to solver core internals from infrastructure = CRITICAL_VIOLATION — escalate immediately. |
| A10 | Meta-Governance | `prompts/meta/` is the SINGLE SOURCE OF TRUTH for all system rules and axioms. `docs/` files are DERIVED outputs — never edit docs/ directly to change a rule. Reconstruction of docs/ from prompts/meta/ alone must always be possible. |

**Immutable Zones (meta-workflow.md §META-EVOLUTION GUARDRAILS):**
- φ-Principles (φ1–φ7) and Axioms A1–A10 are immutable — no modification or weakening permitted.
- HAND-03 Acceptance Check items (checks 0–8) are immutable.
- Any proposal to modify an Immutable Zone triggers SYSTEM_PANIC: STOP all pipeline activity; escalate to user.

**English-First rule:** All agents reason and output in English. Japanese output only on explicit user request.

────────────────────────────────────────────────────────
## § C — Code Domain Rules

Applies to all L-Domain agents: CodeWorkflowCoordinator, CodeArchitect, CodeCorrector, CodeReviewer, TestRunner, ExperimentRunner.

### C1 — SOLID Principles (MANDATORY)

All code must comply with SOLID principles. Audit procedure: before writing or modifying any class/function, verify compliance.

| Letter | Principle | Violation Signal | Required Fix |
|--------|-----------|-----------------|-------------|
| S | Single Responsibility | Class doing I/O + computation + storage | Split into separate classes |
| O | Open/Closed | Adding feature requires modifying existing class | Add subclass or strategy |
| L | Liskov Substitution | Subclass changes method contract | Fix signature or redesign |
| I | Interface Segregation | Forcing agent to implement unused methods | Split interface |
| D | Dependency Inversion | High-level module imports concrete class | Inject interface |

**SOLID Audit Procedure:** Report violations in `[SOLID-X]` format (e.g., `[SOLID-D]`). Fix before proceeding.

### C2 — Preserve Once-Tested Implementations (MANDATORY)

Never delete code that passed tests. Superseded implementations must be retained as legacy classes.

**Legacy naming rule:** `{OriginalName}Legacy` or `{OriginalName}WENO5` etc. with comment block:
```python
# DO NOT DELETE — passed tests {YYYY-MM-DD}
# Superseded by: {NewClassName} in {filename}
# Retained for: cross-validation and regression baseline
```

**Reference:** docs/01_PROJECT_MAP.md § C2 Legacy Register — mandatory registry for all legacy classes.

### C3 — Builder Pattern (Sole Construction Path)

`SimulationBuilder` is the sole construction path (ASM-001). Direct `__init__` construction of `TwoPhaseSimulation` is forbidden.
Every new major component must follow this pattern to maintain dependency injection and testability.

### C4 — Implicit Solver Policy

| System Type | Primary Solver | Fallback | Notes |
|-------------|---------------|---------|-------|
| Global PPE (default) | CCD Kronecker + LGMRES | *(none)* | "pseudotime"; returns best iterate on non-convergence |
| Global PPE (debug) | CCD Kronecker + direct LU | — | "ccd_lu"; guaranteed solution, O(n^1.5) memory |
| Global PPE (large-scale) | CCD sweep (matrix-free) | — | "sweep"; defect correction + Thomas (O(N) per iter) |
| Banded/block-tridiag (CCD) | Direct LU | — | O(N) fill-in; efficient |

FVM-based solvers (BiCGSTAB, FVM LU) are deprecated — O(h²) accuracy insufficient for CCD pipeline.

### C5 — General Code Quality

- Google-style docstrings with equation number citations mandatory for all numerical methods
- Import auditing: no UI/framework imports in `src/core/` (A9 enforcement)
- Symbol mapping table (paper notation → Python variable) required for every new module
- Backward compatibility adapters required when superseding existing code

### C6 — MMS Test Standard

All new numerical modules must be verified by Method of Manufactured Solutions (MMS):
- Grid sizes N=[32, 64, 128, 256]
- Required output: convergence table (N | L∞ error | log-log slope)
- Acceptance: all slopes ≥ expected_order − 0.2
- CCD boundary-limited orders: d1 ≥ 3.5, d2 ≥ 2.5 on L∞ (ASM-004)

────────────────────────────────────────────────────────
## § P — Paper Domain Rules

Applies to all A-Domain agents: PaperWorkflowCoordinator, PaperWriter, PaperReviewer, PaperCompiler, PaperCorrector.

### P1 — LaTeX Authoring (MANDATORY)

**Cross-references:** Always use `\ref`, `\eqref`, `\autoref` — never hardcode numbers.

**Label prefixes (mandatory):**
| Prefix | Use |
|--------|-----|
| `sec:` | Section |
| `eq:` | Equation |
| `fig:` | Figure |
| `tab:` | Table |
| `alg:` | Algorithm |
| `app:` | Appendix |

**tcolorbox environments (6 types; no nesting rule):**

| Environment | Use |
|-------------|-----|
| `mybox` | General information/note |
| `defbox` | Definitions |
| `resultbox` | Key results |
| `algbox` | Algorithm descriptions |
| `warnbox` | Warnings |
| `remarkbox` | Remarks |

**No-nesting rule (MANDATORY):** tcolorbox environments must NEVER be nested inside another tcolorbox. Root cause of overfull warnings. Flatten all nested boxes before compiling.

**Page layout:** Figures/tables placed with `[htbp]`; captions below figures, above tables.

### KL-12 — \\texorpdfstring (MANDATORY — infinite-loop trap)

Math expressions in section titles, subsection titles, or figure/table captions MUST be wrapped:

```latex
% CORRECT:
\section{\texorpdfstring{$O(h^4)$}{O(h\textasciicircum 4)} Convergence}

% WRONG (causes xelatex 100% CPU hang):
\section{$O(h^4)$ Convergence}
```

**Pre-compile scan (mandatory before every BUILD-02):**
```sh
grep -n "\\\\section\|\\\\subsection\|\\\\caption" paper/sections/*.tex \
  | grep "\$" | grep -v "texorpdfstring"
```
Zero matches required. Any match is a KL-12 violation — fix before compiling.

### P3 — Whole-Paper Consistency (P3-A through P3-F)

- **P3-A:** Symbol consistency — same symbol must mean the same thing everywhere
- **P3-B:** Equation consistency — paper equations must match code implementations (A3)
- **P3-C:** Cross-reference integrity — all `\ref`, `\eqref` must resolve
- **P3-D:** Multi-site parameter discipline — Reference: docs/01_PROJECT_MAP.md § P3-D Register
- **P3-E:** Narrative consistency — chapter ordering and forward references must be coherent
- **P3-F:** tcolorbox type consistency — box type must match content semantics

### P4 — Reviewer Skepticism Protocol (5-step, MANDATORY)

When processing reviewer findings, PaperWriter MUST follow this sequence:

1. Read the actual .tex file at the cited location independently
2. Derive the claim from first principles (do not read reviewer's reasoning first)
3. Classify: VERIFIED / REVIEWER_ERROR / SCOPE_LIMITATION / LOGICAL_GAP / MINOR_INCONSISTENCY
4. Act only on VERIFIED or LOGICAL_GAP findings
5. For REVIEWER_ERROR: reject with documented rationale; do not apply any fix

"The reviewer says so" is never a valid reason to make a change. Independent verification is mandatory.

────────────────────────────────────────────────────────
## § Q — Prompt Domain Rules

Applies to all P-Domain agents: PromptArchitect, PromptAuditor, PromptCompressor.

### Q1 — Standard Prompt Template

All agent prompts must use exactly this structure:
```
# PURPOSE
# INPUTS
# RULES         (or # CONSTRAINTS for prompt-domain agents — internal variant, not a defect)
# PROCEDURE
# OUTPUT
# STOP
```

Every generated prompt must include BOTH citation lines below the title heading:
- `(All axioms A1–A10 apply unconditionally: docs/00_GLOBAL_RULES.md §A)`
- Domain citation (Code: `§C1–C6`; Paper: `§P1–P4, KL-12`; Prompt: `§Q1–Q4`; Audit: `§AU1–AU3`)

### Q2 — Environment Profiles

| Environment | Optimization |
|-------------|-------------|
| Claude | Explicit constraints; structure and traceability; longer outputs when needed; correctness, auditability, and stop conditions emphasized |
| Codex | Executable clarity; patch-oriented, diff-first; invariants; minimal line changes |
| Ollama | Aggressive compression; only essential constraints and stop conditions; short outputs |
| Mixed | Generate separate variants per environment; do not blend rules |

### Q3 — Audit Checklist (9 items)

| # | Check | Pass Criterion |
|---|-------|---------------|
| 1 | Core axioms A1–A10 present | All 10 referenced; none weakened |
| 2 | Solver / infra separation | No solver logic mixed with I/O, logging, config |
| 3 | Layer isolation | No cross-layer edits without authorization |
| 4 | External memory discipline | All state refs docs/ files by ID; no old filenames |
| 5 | Stop conditions unambiguous | Every STOP has explicit trigger; STOP section ends with: `Recovery: look up trigger in meta-workflow.md §STOP-RECOVER MATRIX.` (Generation Rule 13) |
| 6 | Standard template format | PURPOSE / INPUTS / RULES (or CONSTRAINTS) / PROCEDURE / OUTPUT / STOP |
| 7 | Environment optimization | Appropriate for target |
| 8 | Backward compatibility | No semantic removal without deprecation note |
| 9 | Core/System sovereignty (A9) | CodeArchitect includes import auditing mandate; ConsistencyAuditor includes CRITICAL_VIOLATION detection + THEORY_ERR/IMPL_ERR taxonomy |

**Note — per-agent prompt audit:** PromptAuditor.md §q3_checklist contains the 9-item
per-agent compliance checklist (Q3-1 through Q3-9). This table is the system-level
deployment validation checklist. Both must pass before any agent prompt is accepted.
Key per-agent items: Q3-7 (JIT line in PROCEDURE), Q3-8 (no cross-layer leakage),
Q3-9 (BS-1 note for auditor agents). Behavioral Action Table (formerly Q3-4) is
**OMITTED** in all generated prompts per Generation Rule 9.

### Q4 — Compression Rules

Compression-exempt (must never be reduced or softened):
- All STOP conditions (verbatim preservation mandatory)
- A3 (3-Layer Traceability)
- A4 (Separation)
- A5 (Solver Purity)
- A9 (Core/System Sovereignty)

Compression permitted only when semantic equivalence is independently verified.

────────────────────────────────────────────────────────
## § AU — Audit Domain Rules

Applies to ConsistencyAuditor (Q-Domain).

### AU1 — Authority Chain (3 levels, descending)

When sources disagree, this chain determines which artifact is wrong:

1. First principles (independent derivation) — HIGHEST authority
2. MMS-passing code (`src/core/`) > docs/01_PROJECT_MAP.md §6 (numerical algorithm reference)
3. Paper equations (paper/sections/*.tex) — LOWEST authority

Infrastructure (`src/system/`) never overrides solver core. Fixing a lower-layer symptom when the
cause is in a higher layer is always wrong (φ3).

### AU2 — Gate Conditions (→ meta-ops.md AUDIT-01: 10-item release gate)

All 10 items must pass before issuing PASS verdict. A single FAIL blocks merge to main.
Consult prompts/meta/meta-ops.md AUDIT-01 for canonical item list and failure routing.

| Item | Category |
|------|----------|
| 1 | Equation = discretization = solver (A3 traceability) |
| 2 | LaTeX tag integrity (KL-12 compliance) |
| 3 | Infrastructure non-interference (A5) |
| 4 | Experiment reproducibility (EXP-02 SC-1–4) |
| 5 | Assumption validity (ASM-IDs active) |
| 6 | Traceability from claim to implementation |
| 7 | Backward compatibility (A7) |
| 8 | No redundant memory growth in ACTIVE_LEDGER |
| 9 | Branch policy compliance (A8) |
| 10 | Merge authorization compliance (VALIDATED phase + all MERGE CRITERIA) |

**Deadlock prevention:** Gatekeeper may reject ONLY with specific citation (checklist item #N, Interface Contract clause, or Core Axiom by number). If all formal checks pass but doubt remains → CONDITIONAL PASS; escalate to user.

### AU3 — Verification Procedures (→ meta-ops.md AUDIT-02: Procedures A–E)

ConsistencyAuditor must apply Procedures A–E in sequence when verifying mathematical claims.
"I couldn't find a problem" is valid only after at least Procedures A–D were applied.

| Procedure | Description |
|-----------|-------------|
| A | Independent derivation from first principles |
| B | Code–paper line-by-line comparison |
| C | MMS test result interpretation |
| D | Boundary scheme derivation |
| E | Authority chain conflict resolution (invoked only when A–D produce conflicting evidence) |

**Error taxonomy (mandatory classification before routing):**
- **THEORY_ERR:** Root cause in solver logic or paper equation → route to PaperWriter or CodeArchitect
- **IMPL_ERR:** Root cause in src/system/ or adapter layer → route to CodeCorrector
- **Authority conflict:** escalate to domain WorkflowCoordinator → user

**CRITICAL_VIOLATION detection:** Direct access to solver core (`src/core/`) from infrastructure (`src/system/`) = CRITICAL_VIOLATION. Escalate immediately, bypassing all queues. No other agent may issue AU2 verdicts.

**Phantom Reasoning Guard:** ConsistencyAuditor evaluates ONLY the final Artifact and signed Interface Contract. Specialist chain-of-thought, intermediate derivations, and scratch work are INVISIBLE to the Auditor. DISPATCH inputs for Auditor roles must list only final artifacts — never intermediate reasoning.

────────────────────────────────────────────────────────
## § GIT — 3-Phase Domain Lifecycle

All git operation syntax defined canonically in prompts/meta/meta-ops.md. This section provides lifecycle phase definitions.

| Phase | Trigger | Auto-action (commit message pattern) |
|-------|---------|--------------------------------------|
| DRAFT | Specialist completes implementation on dev/ branch | `{branch}: draft — {summary}` |
| REVIEWED | Gatekeeper merges dev/ PR after MERGE CRITERIA satisfied | `{branch}: reviewed — {summary}` |
| VALIDATED | ConsistencyAuditor/PromptAuditor AU2 PASS; merge to main | `merge({branch} → main): {summary}` |

**MERGE CRITERIA (all three required):**
- TEST-PASS: 100% unit/validation test success
- BUILD-SUCCESS: successful compilation/static analysis
- LOG-ATTACHED: execution logs in PR comment (tests/last_run.log or equivalent)

**Branch governance:**
- `main` — protected; never committed directly (A8); Root Admin merge only
- `code`, `paper`, `prompt` — domain integration staging; Gatekeeper-owned
- `dev/{agent_role}` — Specialist workspace; sovereign per agent; no cross-agent access
- `interface/` — cross-domain contracts; Gatekeeper write only (IF-COMMIT token required)

**Contamination rule:** Any write outside active DOMAIN-LOCK.write_territory = CONTAMINATION violation → STOP immediately; issue RETURN STOPPED.

**GIT-01 (Root Admin Step 0):** ResearchArchitect auto-switches to target domain branch before every routing decision. No commit authority.

────────────────────────────────────────────────────────
## § P-E-V-A — Execution Loop

Master execution frame for ALL domain work. No phase may be skipped.

| Phase | Responsibility | Agent | Output | Git Phase |
|-------|---------------|-------|--------|-----------|
| PLAN | Define scope, success criteria, stop conditions | Coordinator or ResearchArchitect | Task spec in docs/02_ACTIVE_LEDGER.md | — |
| EXECUTE | Produce the artifact | Specialist (CodeArchitect, PaperWriter, PromptArchitect…) | Code / patch / paper / prompt | DRAFT commit |
| VERIFY | Confirm artifact meets spec | TestRunner / PaperCompiler+Reviewer / PromptAuditor | PASS or FAIL verdict | REVIEWED commit on PASS |
| AUDIT | Gate check; cross-system consistency | ConsistencyAuditor / PromptAuditor | AU2 gate verdict (10 items) | VALIDATED commit + merge on PASS |

**Loop rules:**
- FAIL at VERIFY → return to EXECUTE (not to PLAN unless scope changes)
- FAIL at AUDIT → return to EXECUTE
- Loop counter tracked per phase (P6); MAX_REVIEW_ROUNDS = 5
- Exceeding MAX_REVIEW_ROUNDS without escalation = concealed failure (φ5)
- AUDIT agent must be independent of EXECUTE agent (φ7 — Broken Symmetry)
- PLAN always starts with ResearchArchitect loading docs/02_ACTIVE_LEDGER.md

**STOP is Progress (MH-1):** A STOP triggered by detecting a contradiction is more valuable than
proceeding with flawed reasoning. A STOP returned with a clear trigger is a successful agent action.
