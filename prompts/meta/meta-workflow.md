# META-WORKFLOW: Inter-Agent Coordination, Task Flow & Evolution

This file defines how agents interact, how tasks are handed off, what order tasks execute in,
and how the system evolves over time.

────────────────────────────────────────────────────────
# WORKFLOW STATE MACHINE

```
INTAKE
  → RESEARCH
  → PAPER_WRITE
  → PAPER_COMPILE
  → PAPER_REVIEW
  → PAPER_CORRECT
  → CODE_DERIVE
  → SOLVER_REVIEW
  → SOLVER_FIX
  → INFRA_REVIEW
  → INFRA_FIX
  → TEST_UNIT
  → TEST_INTEGRATION
  → EXPERIMENT
  → CONSISTENCY_AUDIT
  → MERGE
  → DONE
```

**Branch mapping:**

| State | Branch |
|-------|--------|
| INTAKE, RESEARCH | neutral (pending branch assignment) |
| PAPER_WRITE, PAPER_COMPILE, PAPER_REVIEW, PAPER_CORRECT | `paper` |
| CODE_DERIVE, SOLVER_REVIEW, SOLVER_FIX, INFRA_REVIEW, INFRA_FIX, TEST_UNIT, TEST_INTEGRATION, EXPERIMENT | `code` |
| CONSISTENCY_AUDIT | prepares release state |
| MERGE | `main` only, after validation and authorization |
| DONE | after merge completion and state recording |

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
- `code/*` or `paper/*` — sub-branches for isolated tasks; branch from parent, never from `main`

**Branch rules:**
- before starting any code task: `git pull origin main` into `code`
- before starting any paper task: `git pull origin main` into `paper`
- to switch domains (code ↔ paper): merge current branch into `main` first
- never mix paper and code edits in one branch step unless explicitly authorized
- sub-branches merge back to parent (`code` or `paper`), not directly to `main`

**Commit rules:**
- commits to `paper` and `code` are made automatically at coherent milestones
- commit messages must be short, specific, and traceable
- never wait for a perfect end state if a stable checkpoint exists

**Merge rules:**
- merge to `main` requires all tests, reviews, and audits to pass
- merge decisions must be recorded in ACTIVE_STATE.md
- non-authorized agents may prepare diffs, but may not finalize merges into `main`
- `main` merges require explicit permission from authorized maintainer or merge agent

────────────────────────────────────────────────────────
# AGENT HANDOFF MAP

This table defines which agent receives work from which, and under what condition.

| From | Condition | To |
|------|-----------|----|
| ResearchArchitect | user intent mapped to agent | any target agent |
| WorkflowCoordinator | gap identified in code/paper | CodeArchitect / TestRunner / CodeReviewer / CodeCorrector |
| CodeArchitect | implementation complete | TestRunner |
| TestRunner | PASS | WorkflowCoordinator (VERIFIED verdict) |
| TestRunner | FAIL | STOP → user direction → CodeCorrector or CodeArchitect |
| CodeCorrector | fix applied | TestRunner (for formal convergence verdict) |
| CodeReviewer | migration plan ready | CodeArchitect (for implementation) or STOP |
| ExperimentRunner | sanity checks pass | PaperWriter (verified result data) |
| PaperReviewer | findings classified | PaperCorrector (VERIFIED/LOGICAL_GAP) or discard (REVIEWER_ERROR) |
| PaperCorrector | fixes applied | PaperCompiler (compilation check) |
| PaperCompiler | compile error unresolvable | PaperWriter |
| ConsistencyAuditor | PAPER_ERROR found | PaperWriter |
| ConsistencyAuditor | CODE_ERROR found | CodeArchitect → TestRunner |
| ConsistencyAuditor | authority conflict | WorkflowCoordinator |
| PromptAuditor | FAIL found | PromptArchitect |
| PromptArchitect | prompt generated | PromptAuditor (validation) |
| PromptCompressor | compressed prompt | PromptAuditor (validation) |
| any agent | STOP condition triggered | user (for direction) |
| WorkflowCoordinator | all components verified | ConsistencyAuditor → MERGE |

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

## P8: BRANCH-SCOPED EXECUTION
- before starting code task: `git pull origin main` into `code`
- before starting paper task: `git pull origin main` into `paper`
- never mix paper and code edits in one branch step unless explicitly authorized
- sub-branches merge to parent (`code` or `paper`), never directly to `main`
- `main` is kept clean — only receives merges from `code` or `paper` when work is complete and verified

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

Purpose: make the system improve without becoming noisy or unstable.

## Observe
- failures
- repeated exceptions
- drift
- redundancy
- unnecessary rewrites
- schema friction
- layer violations

## Evaluate
- Is the issue incidental or structural?
- Does it recur across tasks?
- Does it affect correctness, traceability, or reproducibility?

## Generalize
- abstract reusable patterns
- rewrite into short, general rules
- keep only stable patterns

## Promote
- LESSON → candidate rule
- stable ASSUMPTION → constraint
- repeated workaround → protocol
- recurring schema pattern → architecture rule

## Validate (before promoting)
- no conflict with core axioms
- no solver-purity violation
- no layer interference
- no loss of backward compatibility

## Compress
- remove redundant lower-level rules
- merge overlapping rules
- preserve semantics via migration notes

## Deprecate
Deprecate a rule if it is: obsolete, redundant, subsumed, conflicting, or too specific.

Never promote a rule that:
- increases ambiguity
- breaks solver purity
- mixes layers
- increases token load without added generality
- weakens reproducibility

────────────────────────────────────────────────────────
# PROMOTION CRITERIA

A rule may be promoted only if it satisfies most of the following:
- repeated usefulness across multiple tasks
- structural generality
- non-interference with existing axioms
- short and stable formulation
- explicit reuse value
- compression benefit
- backward compatibility

If uncertain, keep it in LESSONS or ASSUMPTION_LEDGER. Do not over-promote.

────────────────────────────────────────────────────────
# FINAL INSTRUCTION

Build a system that:
- never corrupts structure
- never breaks solver purity
- evolves its own rules only through validated promotion
- minimizes tokens without losing meaning
- preserves traceability across theory, discretization, and code
- remains stable under long execution
- maintains backward compatibility while improving itself
- uses `paper`, `code`, and `main` as the only persistent branches
- commits automatically to `paper` and `code` at coherent milestones
- blocks any merge into `main` unless validation passes and authorization is present
