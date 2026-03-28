# META-WORKFLOW: Inter-Agent Coordination, Task Flow & Evolution
# ABSTRACT LAYER — workflow logic: P-E-V-A loop, domain pipelines, handoff rules, control protocols.
# FOUNDATION (φ1–φ7, A1–A10): prompts/meta/meta-core.md  ← READ FIRST
# Domain registry, branch rules, storage sovereignty: prompts/meta/meta-domains.md
# Canonical operations (GIT/DOM/BUILD/TEST/EXP/HAND/AUDIT): prompts/meta/meta-ops.md
# Concrete phase/commit format and lifecycle rules: docs/00_GLOBAL_RULES.md §GIT, §P-E-V-A
# Project state: docs/02_ACTIVE_LEDGER.md

────────────────────────────────────────────────────────
# § WORKFLOW PHILOSOPHY

This file defines the HOW. The WHY is in meta-core.md §DESIGN PHILOSOPHY.
Read the φ-principles before interpreting any rule in this file.

────────────────────────────────────────────────────────
# § GIT BRANCH GOVERNANCE → meta-domains.md

Authoritative definitions — branch ownership, storage territory, 3-phase lifecycle,
branch rules, domain lock protocol, contamination guard: **meta-domains.md**.

Quick reference only:
- `code` branch: CodeWorkflowCoordinator; `paper`: PaperWorkflowCoordinator; `prompt`: PromptArchitect
- `main`: protected — never committed directly (A8)
- 3-phase lifecycle: DRAFT (GIT-02) → REVIEWED (GIT-03) → VALIDATED (GIT-04 + merge to main)
- First action every session: Branch Preflight GIT-01, then Domain Lock DOM-01 (→ meta-ops.md)
- `git commit` on `main` = A8 violation → abort and re-run GIT-01

────────────────────────────────────────────────────────
# § P-E-V-A EXECUTION LOOP

Master execution frame for ALL domain work. No phase may be skipped.

| Phase | Responsibility | Agent | Output | git phase |
|-------|---------------|-------|--------|-----------|
| PLAN | Define scope, success criteria, stop conditions | Coordinator or ResearchArchitect | task spec in 02_ACTIVE_LEDGER.md | — |
| EXECUTE | Produce the artifact | Specialist (CodeArchitect, PaperWriter, PromptArchitect…) | code / patch / paper / prompt | DRAFT commit |
| VERIFY | Confirm artifact meets spec | TestRunner / PaperCompiler+Reviewer / PromptAuditor | PASS or FAIL verdict | REVIEWED commit on PASS |
| AUDIT | Gate check; cross-system consistency | ConsistencyAuditor / PromptAuditor | AU2 gate verdict (10 items) | VALIDATED commit + merge on PASS |

Rules:
- FAIL at VERIFY → return to EXECUTE (not to PLAN unless scope changes)
- FAIL at AUDIT → return to EXECUTE
- Loop counter tracked per phase (P6); MAX_REVIEW_ROUNDS = 5
- AUDIT agent must be independent of EXECUTE agent (φ7)
- PLAN always starts with ResearchArchitect loading docs/02_ACTIVE_LEDGER.md

────────────────────────────────────────────────────────
# § DOMAIN PIPELINES

Each pipeline is a concrete instantiation of P-E-V-A.
The abstract frame (above) governs; domain detail (below) specializes it.

────────────────────────────────────────────────────────
## Code Pipeline (branch: `code`)

```
PRE-CHECK  CodeWorkflowCoordinator  [MANDATORY before PLAN]
           → Run GIT-01 (auto-switch to `code` + origin/main sync → meta-ops.md GIT-01)
           → Run DOM-01: establish DOMAIN-LOCK for this session

PLAN     CodeWorkflowCoordinator
           → Branch preflight (already done in PRE-CHECK)
           → Parse paper; inventory src/ gaps; record in 02_ACTIVE_LEDGER.md
           → Dispatch specialist (one gap per step, P5)

EXECUTE  CodeArchitect     — new module or equation implementation
         CodeCorrector     — targeted fix after TestRunner FAIL
         CodeReviewer      — refactor plan (execution handed back to CodeArchitect)
           → Artifact: Python module + pytest file
           → git: draft commit

VERIFY   TestRunner
           PASS → CodeWorkflowCoordinator (component VERIFIED; continue inventory)
           FAIL → STOP → user → CodeCorrector or CodeArchitect
         [repeat EXECUTE → VERIFY until all gaps closed]
           → git: reviewed commit

AUDIT    ConsistencyAuditor (AU2 gate — all 10 items)
           PASS → CodeWorkflowCoordinator → git: validated + merge code → main
           THEORY_ERR → CodeArchitect → TestRunner
           IMPL_ERR   → CodeCorrector  → TestRunner
           Authority conflict → CodeWorkflowCoordinator → STOP → user
```

Optional: ExperimentRunner after VERIFY and before AUDIT (sanity + reproducibility checks).

────────────────────────────────────────────────────────
## Paper Pipeline (branch: `paper`)

```
PRE-CHECK  PaperWorkflowCoordinator  [MANDATORY before PLAN]
           → Run GIT-01 (auto-switch to `paper` + origin/main sync → meta-ops.md GIT-01)
           → Run DOM-01: establish DOMAIN-LOCK for this session

PLAN     PaperWorkflowCoordinator
           → Branch preflight (already done in PRE-CHECK)
           → Identify section gaps or review targets; record in 02_ACTIVE_LEDGER.md

EXECUTE  PaperWriter
           → Artifact: LaTeX patch (diff only)
           → git: draft commit

VERIFY   PaperCompiler   — zero compilation errors (pre-condition for review)
         PaperReviewer   — classify findings: FATAL / MAJOR / MINOR
           0 FATAL, 0 MAJOR → proceed
           FATAL or MAJOR  → PaperCorrector → back to PaperCompiler
           [loop; counter > MAX_REVIEW_ROUNDS → STOP → user with full history]
           → git: reviewed commit

AUDIT    ConsistencyAuditor (AU2 gate — all 10 items)
           PASS       → PaperWorkflowCoordinator → git: validated + merge paper → main
           PAPER_ERROR → PaperWriter
           CODE_ERROR  → CodeArchitect → TestRunner (code branch)
```

────────────────────────────────────────────────────────
## Prompt Pipeline (branch: `prompt`)

```
PRE-CHECK  PromptArchitect  [MANDATORY before PLAN]
           → Run GIT-01 (auto-switch to `prompt` + origin/main sync → meta-ops.md GIT-01)
           → Run DOM-01: establish DOMAIN-LOCK for this session

PLAN     PromptArchitect
           → Branch preflight (already done in PRE-CHECK)
           → Parse target agent + environment; identify gaps vs. meta files

EXECUTE  PromptArchitect   — generate or refactor prompt
         PromptCompressor  — compress existing prompt (alternative EXECUTE path)
           → Artifact: prompts/agents/{AgentName}.md
           → git: draft commit

VERIFY   PromptAuditor (Q3 checklist — 9 items)
           FAIL → PromptArchitect (targeted correction)
           [loop; counter > MAX_REVIEW_ROUNDS → STOP → user]
           → git: reviewed commit on PASS

AUDIT    PromptAuditor (doubles as gate for prompt domain)
           PASS → git: validated commit + merge prompt → main
```

────────────────────────────────────────────────────────
## Bootstrap Pipeline (new feature only — run before Code Pipeline)

Use when introducing a component that does not yet exist in any form.
Not the default pipeline.

| Step | Agent | Output | Gate |
|------|-------|--------|------|
| 1: Formal Axiomatization | PaperWriter | docs/theory/logic.tex entry | Logic self-consistent; no UI/framework mention |
| 2: Structural Contract | CodeArchitect | prompts/specs/ interface definition | Dependency unidirectional (A9) |
| 3: Headless Implementation | CodeArchitect | src/core/ module (stdlib only) | TestRunner PASS in CLI environment |
| 4: Shell Integration | CodeArchitect | src/system/ wrapper | ExperimentRunner sanity checks PASS |

Rules:
- Step 1 is immutable once Step 2 begins; changes require re-entering Step 1
- Step 3 must not reference any Step 4 artifact
- CRITICAL_VIOLATION if Step 4 bypasses Step 2 contract to access Step 3 internals (A9)

────────────────────────────────────────────────────────
# § HANDOFF RULES

**Canonical handoff protocol:** meta-ops.md §HANDOFF PROTOCOL (HAND-01, HAND-02, HAND-03)

All agent-to-agent transfers use the structured token format defined there.
Every dispatch sends HAND-01; every completion returns HAND-02;
every receiver runs HAND-03 (Acceptance Check) before starting work.

**Definition of Done — Main-Merge Rule:**
A task is NOT considered finished until all work is merged into `main` via GIT-04 (VALIDATED
commit + merge). Cross-domain handoffs (e.g., Code → Paper) are only permitted after the
source domain's work is merged into `main`. The receiving coordinator MUST verify this:

```
Cross-Domain Handoff Pre-check (run by receiving coordinator before accepting):
  □ Verify source branch merged to main: confirm GIT-04 merge commit present in main history
    (→ meta-ops.md GIT-04 for merge commit format)
    Not found → REJECT handoff; source domain is not "Done" yet; return BLOCKED
  □ Run PRE-CHECK for the new domain (→ GIT-01 auto-switch + origin/main sync + DOM-01)
```

The table below covers only non-obvious routing decisions — errors, stops,
and cross-domain transitions. Normal coordinator ↔ specialist handoffs are
fully described by the domain pipelines combined with the protocol.

| Situation | RETURN status | From | Routed to |
|-----------|--------------|------|-----------|
| Ambiguous user intent | STOPPED | ResearchArchitect | user |
| TestRunner FAIL | FAIL | TestRunner | coordinator → user |
| PaperCompiler unresolvable error | BLOCKED | PaperCompiler | PaperWriter (via coordinator) |
| PaperWriter ambiguous derivation | STOPPED | PaperWriter | ConsistencyAuditor (via coordinator) |
| ConsistencyAuditor PAPER_ERROR | FAIL | ConsistencyAuditor | PaperWriter |
| ConsistencyAuditor CODE_ERROR | FAIL | ConsistencyAuditor | CodeArchitect → TestRunner |
| ConsistencyAuditor authority conflict | STOPPED | ConsistencyAuditor | user via coordinator |
| Loop > MAX_REVIEW_ROUNDS | STOPPED | any coordinator | user |
| Any STOP condition triggered | STOPPED | any agent | user |

────────────────────────────────────────────────────────
# § CONTROL PROTOCOLS

Grouped by concern. All protocols apply unconditionally unless labeled.

## Layer Integrity

**P1: LAYER_STASIS_PROTOCOL** — prevent cross-layer corruption (← φ7)
- Content edit → Tags READ-ONLY
- Tag edit → Content READ-ONLY
- Structure edit → no content rewrite
- Style edit → no semantic rewrite
Violation → immediate STOP

**P2: NON_INTERFERENCE_AUDIT** — protect solver purity (← φ3, A5)
- Infrastructure changes must not alter numerical results
- Verify: bit-level equality, or tolerance-bounded equality with explicit rationale
Failure → block MERGE → route to CodeReviewer

**P5: SINGLE-ACTION DISCIPLINE** (← φ2)
- One agent per step; one objective per prompt; minimal input scope

## Error Handling

**P6: BOUNDED LOOP CONTROL** (← φ5)
- Maintain retry counter per phase; default MAX_REVIEW_ROUNDS = 5
- Threshold breach → escalate to user; never conceal failure by repetition

**P9: THEORY_ERR / IMPL_ERR CLASSIFICATION** — mandatory before any fix (← φ1, φ7)
- THEORY_ERR: root cause in solver logic or paper equation → fix in paper/ or docs/theory/ first
- IMPL_ERR: root cause in infrastructure (src/system/ or adapter layer) → fix there only
- Uncertain → treat as THEORY_ERR; verify with ConsistencyAuditor

## Knowledge Management

**P3: ASSUMPTION_TO_CONSTRAINT_PROMOTION** (← φ1)
- Detect stable assumptions → promote to constraints with ASM-ID in 02_ACTIVE_LEDGER.md
- Inject promoted constraints into future prompts and reviews

**P4: CONTEXT_COMPRESSION_GATE** — triggered before DONE, schema migration, prompt regeneration
- Compress 02_ACTIVE_LEDGER.md §B LESSONS; promote stable rules to CORE AXIOMS

**P7: LEGACY MIGRATION**
- Detect old prompts, schemas, conventions → map to current schema; preserve semantics
- Record migration notes in 01_PROJECT_MAP.md or 02_ACTIVE_LEDGER.md

## Meta-Governance

**Meta-as-master rule → meta-core.md A10** (← φ6)
prompts/meta/ is the single source of truth for all rules. See meta-core.md A10.

────────────────────────────────────────────────────────
# § AUDIT GATE → meta-ops.md AUDIT-01

AU2 gate (10-item release checklist, ConsistencyAuditor): **meta-ops.md AUDIT-01**.
AUDIT phase in each domain pipeline invokes AUDIT-01 before any merge to `main`.

────────────────────────────────────────────────────────
# § META-EVOLUTION POLICY

**Cycle:** Observe → Evaluate (structural vs. incidental) → Generalize → Promote → Validate → Compress

**M1: Knowledge Promotion** — On ConsistencyAuditor PASS (full domain cycle): extract reusable
patterns and record in docs/02_ACTIVE_LEDGER.md §LESSONS. Promote to meta-core.md §AXIOMS only if
the pattern is system-wide, axiom-compatible, and brief (A1).

**M2: Self-Healing** — Apply P9 before any fix.
- THEORY_ERR → update docs/theory/ or paper first, then re-derive implementation
- IMPL_ERR → patch src/system/ (infrastructure) only; never touch solver core (src/core/)
Record in 02_ACTIVE_LEDGER.md §LESSONS.

**Deprecate** if: obsolete, redundant, subsumed, conflicting, or over-specific.
**Promote** only if: repeated usefulness, structural generality, axiom-compatible, short formulation.
**Never promote** if: increases ambiguity, breaks solver purity, mixes layers, or weakens reproducibility.
If uncertain: keep in 02_ACTIVE_LEDGER.md §LESSONS.

────────────────────────────────────────────────────────
# § COMMAND FORMAT → meta-ops.md §COMMAND FORMAT

Canonical command syntax and invocation rules: **meta-ops.md §COMMAND FORMAT**.
