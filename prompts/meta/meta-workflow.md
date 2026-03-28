# META-WORKFLOW: Inter-Agent Coordination, Task Flow & Evolution
# ABSTRACT LAYER — workflow logic: P-E-V-A loop, Git governance, state machine, handoff map.
# Concrete phase/commit format and lifecycle rules: docs/00_GLOBAL_RULES.md §GIT, §P-E-V-A
# Project state: docs/02_ACTIVE_LEDGER.md

────────────────────────────────────────────────────────
# § GIT BRANCH GOVERNANCE

## Branches
- `main` — protected integration branch; never edited directly
- `paper` — all paper work; pull from `main` before starting
- `code` — all code work; pull from `main` before starting
- `prompt` — all prompt system work; pull from `main` before starting
- `code/*` or `paper/*` — sub-branches for isolated tasks; branch from parent, never from `main`

## Branch Rules
- To switch domains (code ↔ paper ↔ prompt): merge current branch into `main` first
- Never mix paper, code, or prompt edits in one branch step unless explicitly authorized
- Sub-branches merge back to parent (`code`, `paper`, or `prompt`), not directly to `main`

## Commit & Merge Lifecycle (uniform across all domain branches)

Every domain branch passes through three phases. Each phase boundary triggers an automatic
commit; the final phase triggers an automatic merge to `main`.

| Phase | Trigger | Auto-action |
|-------|---------|-------------|
| DRAFT | Primary creation agent returns to coordinator | `git commit -m "{branch}: draft — {summary}"` |
| REVIEWED | Review loop exits with no blocking findings | `git commit -m "{branch}: reviewed — {summary}"` |
| VALIDATED | Gate auditor returns PASS | `git commit -m "{branch}: validated — {summary}"` then merge `{branch} → main` |

## Per-Domain Trigger Map

| Branch | Coordinator | DRAFT trigger | REVIEWED trigger | GATE (VALIDATED) |
|--------|-------------|---------------|-----------------|-----------------|
| `paper` | PaperWorkflowCoordinator | PaperWriter returns | PaperReviewer: no FATAL/MAJOR | ConsistencyAuditor PASS |
| `code` | CodeWorkflowCoordinator | CodeArchitect/Corrector cycle + TestRunner PASS | All components TestRunner PASS | ConsistencyAuditor PASS |
| `prompt` | PromptArchitect (direct) | PromptArchitect/Compressor returns | *(no intermediate review loop)* | PromptAuditor PASS |

**Merge message format:** `merge({branch} → main): {summary}`

## Branch Rules (additional)
- Never skip a phase commit — each is a recoverable checkpoint
- Never merge to `main` without reaching the VALIDATED phase
- Each domain merges to `main` independently — no cross-domain wait
- Merge decisions must be recorded in docs/02_ACTIVE_LEDGER.md
- Direct `main` edits are forbidden unless explicitly authorized
- Adding a new branch: define (1) branch name, (2) coordinator, (3) DRAFT trigger,
  (4) REVIEWED trigger, (5) gate auditor. Add one row to the per-domain trigger map.

────────────────────────────────────────────────────────
# § DOMAIN BOOTSTRAPPING SEQUENCE (new feature or component)

When introducing a new feature or component, execute these 4 phases in order.
No phase may be skipped. Gate = pass before proceeding.

| Phase | Agent | Output | Gate |
|-------|-------|--------|------|
| 1: Formal Axiomatization | PaperWriter | docs/theory/logic.tex entry — set theory, functions, zero UI/framework mention | Logic self-consistent without external variables |
| 2: Structural Contract | CodeArchitect | prompts/specs/architecture.md — map mathematical states to interfaces (State_t → schema) | Interface unidirectional: System depends on Core |
| 3: Headless Implementation | CodeArchitect | src/core/ module — standard libraries only, 100% portable | Pass tests/core/ in CLI environment (TestRunner) |
| 4: Shell Integration | CodeArchitect | src/system/ wrapper — visuals, I/O, user interactions | Integration + UI/UX validation by ExperimentRunner |

Rules:
- Phase 1 output is immutable once Phase 2 begins; change requires re-entering Phase 1
- Phase 2 defines the contract; Core and System agree on it independently
- Phase 3 implementation must not reference any Phase 4 artifact
- CRITICAL_VIOLATION if Phase 4 bypasses Phase 2 contract to access Phase 3 internals (A9)

────────────────────────────────────────────────────────
# § PLAN → EXECUTE → VERIFY → AUDIT LOOP (P-E-V-A)

This is the master execution loop for ALL domain work. Every significant task runs through
all four phases in order. No phase may be skipped.

```
PLAN        Define scope, expected outputs, success criteria, and stop conditions.
            Agent: domain coordinator or ResearchArchitect (routing).
            Output: task specification in 02_ACTIVE_LEDGER.md.

EXECUTE     Carry out the task. One agent, one objective, one step (P5).
            Agent: specialist (CodeArchitect, PaperWriter, etc.)
            Output: artifact (code, patch, data, prompt).

VERIFY      Confirm the artifact meets its specification.
            Agent: TestRunner (code), PaperCompiler + PaperReviewer (paper),
                   PromptAuditor (prompts), ConsistencyAuditor (cross-domain).
            Output: PASS or FAIL verdict.

AUDIT       Gate check before merge. Cross-system consistency validation.
            Agent: ConsistencyAuditor (for code and paper), PromptAuditor (for prompts).
            Output: AU2 gate verdict (all 10 items). On PASS: auto-merge.
```

Rules:
- FAIL at VERIFY → return to EXECUTE; do not skip to AUDIT
- FAIL at AUDIT → return to EXECUTE (never to PLAN unless scope changes)
- Loop counter tracked per phase (P6: BOUNDED LOOP CONTROL)
- MAX_REVIEW_ROUNDS = 5 for paper domain

────────────────────────────────────────────────────────
# § WORKFLOW STATE MACHINE

```
INTAKE
  → RESEARCH

── PAPER DOMAIN (branch: paper) ──────────────────────────
  → PAPER_WRITE           [EXECUTE]
  → PAPER_COMMIT_DRAFT    (auto-commit after PaperWriter completes)
  → PAPER_COMPILE         [VERIFY — stage 1]
  → PAPER_REVIEW          [VERIFY — stage 2]
  → PAPER_CORRECT         (if FATAL/MAJOR found)
  → [loop: PAPER_COMPILE → PAPER_REVIEW → PAPER_CORRECT until no FATAL/MAJOR]
  → PAPER_COMMIT          (auto-commit when review loop clears)
  → PAPER_CONSISTENCY     [AUDIT — ConsistencyAuditor gate]
  → PAPER_MERGE_MAIN      (merge paper → main independently)

── CODE DOMAIN (branch: code) ────────────────────────────
  → CODE_DERIVE           [EXECUTE]
  → SOLVER_REVIEW         [VERIFY]
  → SOLVER_FIX            (if failure found)
  → INFRA_REVIEW          [VERIFY]
  → INFRA_FIX             (if failure found)
  → TEST_UNIT             [VERIFY]
  → TEST_INTEGRATION      [VERIFY]
  → EXPERIMENT            [EXECUTE]
  → CODE_CONSISTENCY      [AUDIT — ConsistencyAuditor gate]
  → CODE_MERGE_MAIN       (merge code → main independently)

── PROMPT DOMAIN (branch: prompt) ────────────────────────
  → PROMPT_EDIT           [EXECUTE]
  → PROMPT_AUDIT          [VERIFY + AUDIT]
  → PROMPT_CORRECT        (if FAIL found)
  → [loop: PROMPT_AUDIT → PROMPT_CORRECT until PASS]
  → PROMPT_COMMIT         (auto-commit prompt branch)
  → PROMPT_MERGE_MAIN     (merge prompt → main independently)

── CROSS-DOMAIN ──────────────────────────────────────────
  → CONSISTENCY_AUDIT     (full cross-domain validation, if needed)
  → DONE
```

## Branch Mapping

| State | Branch |
|-------|--------|
| INTAKE, RESEARCH | neutral (pending branch assignment) |
| PAPER_WRITE, PAPER_COMMIT_DRAFT, PAPER_COMPILE, PAPER_REVIEW, PAPER_CORRECT, PAPER_COMMIT, PAPER_CONSISTENCY | `paper` |
| CODE_DERIVE, SOLVER_REVIEW, SOLVER_FIX, INFRA_REVIEW, INFRA_FIX, TEST_UNIT, TEST_INTEGRATION, EXPERIMENT, CODE_CONSISTENCY | `code` |
| PROMPT_EDIT, PROMPT_AUDIT, PROMPT_CORRECT, PROMPT_COMMIT | `prompt` |
| PAPER_MERGE_MAIN, CODE_MERGE_MAIN, PROMPT_MERGE_MAIN | `main` after domain validation |
| CONSISTENCY_AUDIT | cross-domain release gate (optional) |
| DONE | after all required merges and state recording |

Rules:
- Do not skip states unless explicitly authorized
- Each state has a distinct responsibility
- Transition only when current state's deliverable is complete
- Record state progress in docs/02_ACTIVE_LEDGER.md
- Commit at coherent checkpoints automatically
- Merge to `main` only after audit passes

────────────────────────────────────────────────────────
# § AGENT HANDOFF MAP

| From | Condition | To |
|------|-----------|----|
| ResearchArchitect | user intent mapped | any target agent |
| CodeWorkflowCoordinator | gap identified | CodeArchitect / TestRunner / CodeReviewer / CodeCorrector |
| CodeWorkflowCoordinator | all components verified | ConsistencyAuditor (code domain gate) |
| CodeWorkflowCoordinator | ConsistencyAuditor PASS | auto-merge code → main |
| CodeArchitect | implementation complete | TestRunner |
| TestRunner | PASS | CodeWorkflowCoordinator (VERIFIED verdict) |
| TestRunner | FAIL | STOP → user → CodeCorrector or CodeArchitect |
| CodeCorrector | fix applied | TestRunner (formal convergence verdict) |
| CodeReviewer | migration plan ready | CodeArchitect (implementation) or STOP |
| ExperimentRunner | sanity checks pass | PaperWorkflowCoordinator or PaperWriter |
| PaperWorkflowCoordinator | dispatch writing | PaperWriter |
| PaperWorkflowCoordinator | PaperWriter result received | auto-commit paper branch |
| PaperWorkflowCoordinator | dispatch compile/review/fix | PaperCompiler / PaperReviewer / PaperCorrector |
| PaperWorkflowCoordinator | no FATAL/MAJOR | auto-commit → ConsistencyAuditor |
| PaperWorkflowCoordinator | ConsistencyAuditor PASS | auto-merge paper → main |
| PaperWorkflowCoordinator | FATAL/MAJOR remain | PaperCorrector → PaperCompiler → PaperReviewer (loop) |
| PaperWorkflowCoordinator | loop > MAX_REVIEW_ROUNDS | STOP → user |
| PaperWriter | normal completion | PaperWorkflowCoordinator (return — do NOT stop) |
| PaperWriter | ambiguous derivation | STOP → ConsistencyAuditor |
| PaperReviewer | findings report | PaperWorkflowCoordinator (FATAL/MAJOR/MINOR) |
| PaperCorrector | fixes applied | PaperWorkflowCoordinator |
| PaperCompiler | unresolvable error | PaperWriter |
| ConsistencyAuditor | PAPER_ERROR | PaperWriter |
| ConsistencyAuditor | CODE_ERROR | CodeArchitect → TestRunner |
| ConsistencyAuditor | authority conflict | CodeWorkflowCoordinator |
| ConsistencyAuditor | PASS (paper domain) | PaperWorkflowCoordinator → merge paper → main |
| ConsistencyAuditor | PASS (code domain) | CodeWorkflowCoordinator → merge code → main |
| PromptAuditor | FAIL | PromptArchitect |
| PromptAuditor | PASS | auto-commit → auto-merge prompt → main |
| PromptArchitect | prompt generated | PromptAuditor |
| PromptCompressor | compressed prompt | PromptAuditor |
| any agent | STOP condition triggered | user (for direction) |

────────────────────────────────────────────────────────
# § CONTROL PROTOCOLS

## P1: LAYER_STASIS_PROTOCOL
Purpose: prevent cross-layer corruption.
- when editing Content → Tags are READ-ONLY
- when editing Tags → Content is READ-ONLY
- when editing Structure → no content rewrite
- when editing Style → no semantic rewrite
- all cross-layer edits are forbidden unless explicitly authorized
Violation → immediate STOP

## P2: NON_INTERFERENCE_AUDIT
Purpose: protect solver purity.
- infrastructure changes must not alter numerical results
- verify either: bit-level equality, or tolerance-bounded equality with explicit rationale
Failure → block MERGE → route to CodeReviewer

## P3: ASSUMPTION_TO_CONSTRAINT_PROMOTION
Purpose: evolve knowledge.
- detect stable assumptions
- promote stable assumptions to constraints
- write promoted items to 02_ACTIVE_LEDGER.md with ASM-ID
- inject promoted constraints into future prompts and reviews

## P4: CONTEXT_COMPRESSION_GATE
Triggered: before DONE, before schema migration, before prompt regeneration.
Actions:
- compress 02_ACTIVE_LEDGER.md §B LESSONS
- extract reusable rules
- promote stable rules to CORE AXIOMS when justified
- remove redundancy; preserve backward compatibility through mapping notes

## P5: SINGLE-ACTION DISCIPLINE
- exactly one agent per step
- exactly one primary objective per prompt
- no multi-task execution inside a single action
- keep input scope minimal

## P6: BOUNDED LOOP CONTROL
- maintain retry counter per phase
- define maximum retry threshold (default: MAX_REVIEW_ROUNDS = 5)
- on threshold breach, escalate instead of looping
- never conceal failure by silent repetition

## P7: LEGACY MIGRATION
- detect old prompts, old schemas, old conventions
- map them to the current schema
- compress and upgrade; preserve semantics
- record migration notes in 01_PROJECT_MAP.md or 02_ACTIVE_LEDGER.md

## P8: META-AS-MASTER GOVERNANCE
- prompts/meta/ is the SINGLE SOURCE OF TRUTH for all rules
- docs/ files are DERIVED outputs — never edit docs/ directly for rule changes
- reconstruction of docs/ from prompts/meta/ alone must always be possible
- any rule change: edit prompts/meta/ first, then regenerate docs/ via EnvMetaBootstrapper

## P9: THEORY_ERR / IMPL_ERR CLASSIFICATION
When a bug or inconsistency is detected, classify before fixing:
- THEORY_ERR: root cause is in Logic domain (wrong equation, missing derivation step, bad
  mathematical assumption) → fix source in docs/theory/ or paper/sections/*.tex first
- IMPL_ERR: root cause is in Infra/Shell domain (wrong discretization application, import
  pollution, adapter mismatch) → fix in src/system/ or adapter layer
Rule: Never patch a symptom. If uncertain, treat as THEORY_ERR and verify with ConsistencyAuditor.

────────────────────────────────────────────────────────
# § CONSISTENCY AUDITOR CHECKLIST (release gate — AU2)

Before any merge to `main`, all 10 items must pass:

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

If any item fails: do not merge. Prefer explicit escalation over silent repair.

────────────────────────────────────────────────────────
# § META-EVOLUTION POLICY

**Cycle:**
Observe (failures, drift, redundancy, layer violations)
→ Evaluate (structural vs. incidental; recurrence; impact on correctness/traceability)
→ Generalize (abstract to short, stable, reusable rule)
→ Promote (LESSON → rule; stable ASSUMPTION → constraint; workaround → protocol)
→ Validate (no axiom conflict; no solver-purity violation; no layer interference;
            backward-compatible)
→ Compress (merge overlapping rules; remove subsumed; preserve semantics)

**M1: Knowledge Promotion**
Upon project success or milestone completion, extract reusable Logic (algorithms, derivations,
proofs) into prompts/meta/library/. These become project-independent canonical references.
Trigger: ConsistencyAuditor PASS on a full domain cycle.

**M2: Self-Healing**
When a bug occurs, apply P9 (THEORY_ERR / IMPL_ERR) before any fix attempt.
- THEORY_ERR → update docs/theory/ or paper; then re-derive implementation
- IMPL_ERR → patch Shell/Infra; never touch Logic domain artifacts
Fix the source, not the symptom. Record in 02_ACTIVE_LEDGER.md §LESSONS.

**Deprecate** if: obsolete, redundant, subsumed, conflicting, or over-specific.

**Never promote** a rule that: increases ambiguity, breaks solver purity, mixes layers,
adds token load without generality, or weakens reproducibility.

**Promotion requires:** repeated usefulness, structural generality, axiom-compatible,
short formulation, compression benefit. If uncertain: keep in 02_ACTIVE_LEDGER.md §LESSONS.

────────────────────────────────────────────────────────
# § COMMAND FORMAT

```
Initialize
Execute [AgentName]
Execute [filename]
```

Rules:
- one command sequence per step
- no hidden branching
- no multi-goal execution
- no unbounded continuation
