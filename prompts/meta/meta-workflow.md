# META-WORKFLOW: Inter-Agent Coordination, Task Flow & Evolution

This file defines how agents interact, how tasks are handed off, what order tasks execute in,
and how the system evolves over time.

────────────────────────────────────────────────────────
# WORKFLOW STATE MACHINE

```
INTAKE
  → RESEARCH

── PAPER DOMAIN (branch: paper) ──────────────────────────
  → PAPER_WRITE
  → PAPER_COMMIT_DRAFT       (auto-commit after PaperWriter completes)
  → PAPER_COMPILE
  → PAPER_REVIEW
  → PAPER_CORRECT            (if FATAL/MAJOR found)
  → [loop: PAPER_COMPILE → PAPER_REVIEW → PAPER_CORRECT until no FATAL/MAJOR]
  → PAPER_COMMIT             (auto-commit when review loop clears)
  → PAPER_CONSISTENCY        (ConsistencyAuditor gate — paper domain)
  → PAPER_MERGE_MAIN         (merge paper → main independently)

── CODE DOMAIN (branch: code) ────────────────────────────
  → CODE_DERIVE
  → SOLVER_REVIEW
  → SOLVER_FIX
  → INFRA_REVIEW
  → INFRA_FIX
  → TEST_UNIT
  → TEST_INTEGRATION
  → EXPERIMENT
  → CODE_CONSISTENCY         (ConsistencyAuditor gate — code domain)
  → CODE_MERGE_MAIN          (merge code → main independently)

── PROMPT DOMAIN (branch: prompt) ────────────────────────
  → PROMPT_EDIT
  → PROMPT_AUDIT
  → PROMPT_CORRECT           (if FAIL found)
  → [loop: PROMPT_AUDIT → PROMPT_CORRECT until PASS]
  → PROMPT_COMMIT            (auto-commit prompt branch)
  → PROMPT_MERGE_MAIN        (merge prompt → main independently)

── CROSS-DOMAIN ──────────────────────────────────────────
  → CONSISTENCY_AUDIT        (full cross-domain validation, if needed)
  → DONE
```

**Branch mapping:**

| State | Branch |
|-------|--------|
| INTAKE, RESEARCH | neutral (pending branch assignment) |
| PAPER_WRITE, PAPER_COMMIT_DRAFT, PAPER_COMPILE, PAPER_REVIEW, PAPER_CORRECT, PAPER_COMMIT, PAPER_CONSISTENCY | `paper` |
| CODE_DERIVE, SOLVER_REVIEW, SOLVER_FIX, INFRA_REVIEW, INFRA_FIX, TEST_UNIT, TEST_INTEGRATION, EXPERIMENT, CODE_CONSISTENCY | `code` |
| PROMPT_EDIT, PROMPT_AUDIT, PROMPT_CORRECT, PROMPT_COMMIT | `prompt` |
| PAPER_MERGE_MAIN, CODE_MERGE_MAIN, PROMPT_MERGE_MAIN | `main` after domain-specific validation |
| CONSISTENCY_AUDIT | cross-domain release gate (optional) |
| DONE | after all required merges and state recording |

**Rules:**
- do not skip states unless explicitly authorized
- each state has a distinct responsibility
- transition only when current state's deliverable is complete
- record state progress in ACTIVE_STATE.md
- record current branch in ACTIVE_STATE.md
- commit `paper` and `code` at coherent checkpoints automatically
- merge to `main` only after audit passes

────────────────────────────────────────────────────────
# GIT BRANCH GOVERNANCE

**Branches:**
- `main` — protected integration branch; never edited directly
- `paper` — all paper work; pull from `main` before starting
- `code` — all code work; pull from `main` before starting
- `prompt` — all prompt system work; pull from `main` before starting
- `code/*` or `paper/*` — sub-branches for isolated tasks; branch from parent, never from `main`

**Branch rules:**
- to switch domains (code ↔ paper ↔ prompt): merge current branch into `main` first
- never mix paper, code, or prompt edits in one branch step unless explicitly authorized
- sub-branches merge back to parent (`code`, `paper`, or `prompt`), not directly to `main`

**Commit & merge lifecycle (applies uniformly to every branch)**

Every domain branch passes through three phases. Each phase boundary triggers an automatic commit; the final phase triggers an automatic merge to `main`.

| Phase | Trigger | Auto-action |
|-------|---------|-------------|
| DRAFT | Primary creation agent returns to coordinator | `git commit -m "{branch}: draft — {summary}"` |
| REVIEWED | Review loop exits with no blocking findings | `git commit -m "{branch}: reviewed — {summary}"` |
| VALIDATED | Gate auditor returns PASS | `git commit -m "{branch}: validated — {summary}"` then merge `{branch} → main` |

**Per-domain trigger map:**

| Branch | Coordinator | DRAFT trigger | REVIEWED trigger | GATE (VALIDATED) |
|--------|-------------|---------------|-----------------|-----------------|
| `paper` | PaperWorkflowCoordinator | PaperWriter returns to coordinator | PaperReviewer: no FATAL/MAJOR remaining | ConsistencyAuditor PASS |
| `code` | CodeWorkflowCoordinator | Each CodeArchitect/Corrector cycle when TestRunner PASS | All components TestRunner PASS | ConsistencyAuditor PASS |
| `prompt` | PromptArchitect (direct) | PromptArchitect/Compressor returns | *(no intermediate review loop)* | PromptAuditor PASS |

**Merge message format:** `merge({branch} → main): {summary}`

**Rules:**
- never skip a phase commit — each is a recoverable checkpoint
- never merge to `main` without reaching the VALIDATED phase
- each domain merges to `main` independently — no cross-domain wait
- merge decisions must be recorded in ACTIVE_STATE.md
- direct `main` edits are forbidden unless explicitly authorized

**Adding a new branch:** define (1) branch name, (2) coordinator, (3) DRAFT trigger, (4) REVIEWED trigger, (5) gate auditor. Add one row to the per-domain trigger map above.

────────────────────────────────────────────────────────
# AGENT HANDOFF MAP

This table defines which agent receives work from which, and under what condition.

| From | Condition | To |
|------|-----------|----|
| ResearchArchitect | user intent mapped to agent | any target agent |
| CodeWorkflowCoordinator | gap identified in code | CodeArchitect / TestRunner / CodeReviewer / CodeCorrector |
| CodeWorkflowCoordinator | all components verified | ConsistencyAuditor (code domain gate) |
| CodeWorkflowCoordinator | ConsistencyAuditor gate PASS | auto-merge code → main |
| CodeArchitect | implementation complete | TestRunner |
| TestRunner | PASS | CodeWorkflowCoordinator (VERIFIED verdict) |
| TestRunner | FAIL | STOP → user direction → CodeCorrector or CodeArchitect |
| CodeCorrector | fix applied | TestRunner (for formal convergence verdict) |
| CodeReviewer | migration plan ready | CodeArchitect (for implementation) or STOP |
| ExperimentRunner | sanity checks pass | PaperWorkflowCoordinator or PaperWriter (verified result data) |
| PaperWorkflowCoordinator | dispatch for writing | PaperWriter |
| PaperWorkflowCoordinator | PaperWriter result received | auto-commit paper branch (`paper: writing pass complete`) |
| PaperWorkflowCoordinator | dispatch for compiling/reviewing/fixing | PaperCompiler / PaperReviewer / PaperCorrector |
| PaperWorkflowCoordinator | no FATAL/MAJOR findings remain | auto-commit paper branch → ConsistencyAuditor (paper domain gate) |
| PaperWorkflowCoordinator | ConsistencyAuditor gate PASS | auto-merge paper → main |
| PaperWorkflowCoordinator | FATAL/MAJOR findings remain | PaperCorrector → PaperCompiler → PaperReviewer (loop) |
| PaperWorkflowCoordinator | review loop threshold exceeded | STOP → user direction |
| PaperWriter | writing complete (normal) | PaperWorkflowCoordinator (return result — do NOT stop) |
| PaperWriter | ambiguous derivation | STOP → ConsistencyAuditor |
| PaperReviewer | findings report | PaperWorkflowCoordinator (classification: FATAL/MAJOR/MINOR) |
| PaperCorrector | fixes applied | PaperWorkflowCoordinator (report result) |
| PaperCompiler | compile error unresolvable | PaperWriter |
| ConsistencyAuditor | PAPER_ERROR found | PaperWriter |
| ConsistencyAuditor | CODE_ERROR found | CodeArchitect → TestRunner |
| ConsistencyAuditor | authority conflict | CodeWorkflowCoordinator |
| ConsistencyAuditor | gate PASS (paper domain) | PaperWorkflowCoordinator → merge paper → main |
| ConsistencyAuditor | gate PASS (code domain) | CodeWorkflowCoordinator → merge code → main |
| PromptAuditor | FAIL found | PromptArchitect |
| PromptAuditor | PASS | auto-commit prompt branch → auto-merge prompt → main |
| PromptArchitect | prompt generated | PromptAuditor (validation) |
| PromptCompressor | compressed prompt | PromptAuditor (validation) |
| any agent | STOP condition triggered | user (for direction) |

────────────────────────────────────────────────────────
# CONTROL PROTOCOLS

## P1: LAYER_STASIS_PROTOCOL
Purpose: prevent cross-layer corruption.

Rules:
- when editing Content → Tags are READ-ONLY
- when editing Tags → Content is READ-ONLY
- when editing Structure → no content rewrite
- when editing Style → no semantic rewrite
- all cross-layer edits are forbidden unless explicitly authorized

Violation → immediate STOP

## P2: NON_INTERFERENCE_AUDIT
Purpose: protect solver purity.

Rules:
- infrastructure changes must not alter numerical results
- verify either: bit-level equality, or tolerance-bounded equality with explicit rationale
- any deviation must be classified and explained

Failure:
→ block MERGE
→ route to CodeReviewer

## P3: ASSUMPTION_TO_CONSTRAINT_PROMOTION
Purpose: evolve knowledge.

Rules:
- detect stable assumptions
- promote stable assumptions to constraints
- write promoted items to ASSUMPTION_LEDGER with ASM-ID
- inject promoted constraints into future prompts and reviews

## P4: CONTEXT_COMPRESSION_GATE
Purpose: long-term token efficiency.

Triggered: before DONE, before schema migration, before prompt regeneration.

Actions:
- compress LESSONS.md
- extract reusable rules
- promote stable rules to CORE AXIOMS when justified
- remove redundancy
- preserve backward compatibility through mapping notes

## P5: SINGLE-ACTION DISCIPLINE
- exactly one agent per step
- exactly one primary objective per prompt
- no multi-task execution inside a single action
- keep input scope minimal

## P6: BOUNDED LOOP CONTROL
- maintain retry counter per phase
- define maximum retry threshold
- on threshold breach, escalate instead of looping
- never conceal failure by silent repetition

## P7: LEGACY MIGRATION
- detect old prompts, old schemas, old conventions
- map them to the current schema
- compress and upgrade
- preserve semantics
- record migration notes in ARCHITECTURE or LESSONS

────────────────────────────────────────────────────────
# COMMAND FORMAT

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

────────────────────────────────────────────────────────
# CONSISTENCY AUDITOR CHECKLIST (release gate)

Before any merge to `main`, all of the following must pass:

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
# META-EVOLUTION POLICY

Cycle: **Observe** (failures, drift, redundancy, layer violations) → **Evaluate** (structural vs. incidental; recurrence; impact on correctness/traceability/reproducibility) → **Generalize** (abstract to short, stable, reusable rule) → **Promote** (LESSON → rule; stable ASSUMPTION → constraint; workaround → protocol) → **Validate** (no axiom conflict; no solver-purity violation; no layer interference; backward-compatible) → **Compress** (merge overlapping rules; remove subsumed rules; preserve semantics).

**Deprecate** if: obsolete, redundant, subsumed, conflicting, or over-specific.

**Never promote** a rule that: increases ambiguity, breaks solver purity, mixes layers, adds token load without generality, or weakens reproducibility.

**Promotion requires:** repeated usefulness, structural generality, axiom-compatible, short formulation, compression benefit. If uncertain, keep in LESSONS or ASSUMPTION_LEDGER.
