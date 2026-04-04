# META-WORKFLOW: Inter-Agent Coordination, Task Flow & Evolution
# VERSION: 3.0.0
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
# § T-L-E-A PIPELINE — Master Cross-Domain Flow

The primary execution order for all new work in this system.
Each arrow represents a mandatory Interface Contract gate (meta-domains.md §INTER-DOMAIN INTERFACES).

```
T-Domain (Theory & Analysis)
  │  Composite: Specialist derives equations; Theory Auditor independently re-derives.
  │  Atomic:    EquationDeriver → artifacts/T/derivation_{id}.md
  │             SpecWriter → artifacts/T/spec_{id}.md → docs/interface/AlgorithmSpecs.md
  │  OUTPUT: docs/interface/AlgorithmSpecs.md  [signed by Theory Auditor]
  ▼
L-Domain (Core Library)
  │  Composite: Specialist implements solver from AlgorithmSpecs; TestRunner verifies.
  │  Atomic:    CodeArchitectAtomic → artifacts/L/architecture_{id}.md
  │             LogicImplementer → artifacts/L/impl_{id}.py
  │             (On error: ErrorAnalyzer → artifacts/L/diagnosis_{id}.md
  │                        RefactorExpert → artifacts/L/fix_{id}.patch)
  │  OUTPUT: docs/interface/SolverAPI_vX.py    [signed by L-Domain Gatekeeper]
  ▼
E-Domain (Experiment)
  │  Composite: Specialist runs simulations; Validation Guard passes all 4 sanity checks.
  │  Atomic:    TestDesigner → artifacts/E/test_spec_{id}.md
  │             VerificationRunner → artifacts/E/run_{id}.log
  │  OUTPUT: docs/interface/ResultPackage/      [signed by Validation Guard]
  │          docs/interface/TechnicalReport.md  [jointly signed by T-Auditor + Validation Guard]
  ▼
A-Domain (Academic Writing)
  │  Specialist writes paper using ResultPackage + TechnicalReport; Logical Reviewer audits.
  │  OUTPUT: paper/sections/*.tex (merged to main via AU2 PASS)
  ▼
Q-Domain (QA & Audit) — cross-cuts all stages
  │  Composite: ConsistencyAuditor performs AU2 gate at each domain boundary.
  │  Atomic:    ResultAuditor → artifacts/Q/audit_{id}.md
  │  Contradictions found = high-value success (Falsification Loop).
  ▼
main (VALIDATED + merged by Root Admin)
```

**T-L-E-A ordering is mandatory.** No domain may begin work without the upstream Interface
Contract being signed. Exceptions require explicit user authorization and escalation to Root Admin.

**Continuous Paper (CI/CP) mode:** When a change propagates (e.g., T-Domain equation revision),
all downstream domains (L → E → A) must re-validate their Interface Contracts.
See §CI/CP PIPELINE below.

────────────────────────────────────────────────────────
# § PIPELINE MODE — TRIVIAL / FAST-TRACK / FULL-PIPELINE

Every incoming task is classified into one of three execution modes BEFORE routing.
ResearchArchitect performs this classification as part of GIT-01 Step 0.

## Classification Criterion

| Condition | Mode |
|-----------|------|
| Change touches `docs/memo/` (theory derivations), `docs/interface/*.md`, or `src/core/` (solver core) | **FULL-PIPELINE** |
| New domain branch required (cross-domain work) | **FULL-PIPELINE** |
| Change is whitespace-only, comment-only, typo fix, or docs-only (no logic change) | **TRIVIAL** |
| All other changes (bug fix, paper prose, experiment re-run, config) | **FAST-TRACK** |

When uncertain → classify one level higher (TRIVIAL→FAST-TRACK, FAST-TRACK→FULL-PIPELINE; φ1).

## Gatekeeper Intensity by Pipeline Mode

Every pipeline mode carries a fixed Gatekeeper protocol. Gatekeepers must not escalate intensity
beyond the assigned tier for low-risk modes (φ2 Minimal Footprint), and must not reduce intensity
below the assigned tier for high-risk modes (φ1 Conservative Classification).

| Pipeline Mode | Gatekeeper Protocol               | Independent Re-derivation |
|---------------|-----------------------------------|---------------------------|
| TRIVIAL       | Lint + DOM-02 scope-check only    | NONE                      |
| FAST-TRACK    | Standard P-E-V-A loop; GA-2/3/5  | SUMMARY only (not full)   |
| FULL-PIPELINE | Full AU2 gate + all GA conditions | MANDATORY (GA-4)          |

**Violation:** Applying FULL-PIPELINE intensity to a TRIVIAL task is a φ2 violation.
Applying TRIVIAL intensity to a FULL-PIPELINE task is a φ1 violation and an A5 (Algorithm Fidelity) risk.

────────────────────────────────────────────────────────
## TRIVIAL Mode (NEW — minimal overhead for non-logic changes)

Streamlined path for changes that cannot affect correctness. Designed to eliminate
protocol overhead that exceeds the actual work (φ2 Minimal Footprint).

**Applicable to:** typo fixes, whitespace normalization, comment additions/edits,
documentation-only changes, `.gitignore` updates, config formatting.

**NOT applicable to:** any change to `.py`, `.tex` (content), solver parameters,
test files, or interface contracts — even if the change appears trivial.

| Gate | Status |
|------|--------|
| HAND-03 Acceptance Check | **OMITTED** |
| GIT-SP branch isolation | **OMITTED** — commit directly on domain branch |
| DOM-02 Pre-Write Storage Check | **RETAINED** (contamination guard — always required) |
| HAND-02 RETURN token | **OMITTED** |
| Gatekeeper PR review | **OMITTED** — coordinator may self-commit |
| IF-Agreement (GIT-00) | **OMITTED** |
| AU2 PASS | **OMITTED** |

**Commit format:** `{branch}: trivial — {summary}`

**Guard — What Triggers Upgrade to FAST-TRACK:**
If, during TRIVIAL execution, any of the following is discovered:
- The change modifies logic (even one line of `.py` or `.tex` content)
- The change affects test behavior
- The diff is larger than 20 lines

→ STOP TRIVIAL immediately; reclassify as FAST-TRACK or FULL-PIPELINE.

## FULL-PIPELINE Mode

Full T-L-E-A ordering. All protocols apply:
- IF-Agreement (GIT-00) required before any Specialist starts
- All GA-1 through GA-6 Gatekeeper Approval conditions enforced
- AU2 PASS required for VALIDATED phase
- CI/CP propagation applies on upstream change

**Use for:** new theory derivations, solver algorithm changes, API contract changes,
cross-domain work, any change to `src/core/` or `docs/interface/`.

## FAST-TRACK Mode

Streamlined path for intra-domain, non-breaking changes. Reduced gate set:

| Omitted gate | Reason |
|-------------|--------|
| IF-Agreement (GIT-00) | Existing interface contract is reused; Specialist declares it in DISPATCH context |
| AU2 PASS | Gatekeeper PR review is sufficient for low-risk intra-domain work |
| Composite roles only | micro-agent decomposition not required |

**Retained gates:**
- GIT-SP (Specialist branch isolation — always required)
- DOM-02 Pre-Write Storage Check (contamination guard — always required)
- HAND-03 checks 0–7 (omit check 9 upstream-contract validation for FAST-TRACK)
- MERGE CRITERIA: TEST-PASS + LOG-ATTACHED (BUILD-SUCCESS optional for pure-prose changes)
- Gatekeeper PR review: GA-2, GA-3, GA-5 (independent verification, evidence, no territory violation)

**Use for:** bug fixes, paper prose corrections, adding documentation, experiment
re-runs with unchanged solver, config changes, refactors that don't touch `src/core/`.

## FAST-TRACK Guard — What Triggers Upgrade to FULL-PIPELINE

If, during FAST-TRACK execution, any of the following is discovered:
- The fix requires touching `src/core/` or `docs/interface/`
- A theory inconsistency is found (triggers T-Domain work)
- The Gatekeeper determines the change has downstream impact

→ STOP FAST-TRACK immediately; escalate to ResearchArchitect for FULL-PIPELINE re-routing.

────────────────────────────────────────────────────────
# § PARALLEL EXECUTION — TaskPlanner Staged Dispatch

When TaskPlanner decomposes a COMPOUND task into a multi-stage plan, the following
rules govern parallel and sequential execution within and across stages.

A task is COMPOUND when ANY of the C1–C5 criteria holds (see ResearchArchitect.md):
  C1: maps to 2+ distinct agents
  C2: spans 2+ domains
  C3: requires sequential handoffs with intermediate artifacts
  C4: user explicitly requests parallel execution
  C5: maps to 1 agent BUT decomposes into 2+ independent sub-problems
      (distinct target files/sections with no shared artifacts or write conflicts)
C5 ensures that single-agent tasks with parallelizable sub-problems are NOT
short-circuited as SIMPLE. In C5 plans, multiple tasks may share the same agent type.

## Parallel Eligibility (PE)

| Rule | Description |
|------|-------------|
| **PE-1** | Tasks with NO `depends_on` edges between them MAY run in parallel |
| **PE-2** | Tasks writing to the SAME file or directory MUST NOT run in parallel (resource conflict) |
| **PE-3** | Tasks in the SAME domain sharing the SAME Gatekeeper MAY run in parallel IF on separate `dev/` branches |
| **PE-4** | Cross-domain tasks MUST respect T-L-E-A ordering — a downstream domain task CANNOT be parallel with its upstream dependency |
| **PE-5** | TRIVIAL-mode tasks MAY run in parallel with any non-conflicting task regardless of domain |

## Barrier Sync Protocol (BS)

```
BS-1: Stage N+1 does NOT begin until ALL tasks in Stage N have issued HAND-02 RETURN.
BS-2: If a task in a parallel stage returns STOPPED or FAIL:
        - Other tasks in the same stage are allowed to complete (no premature kill).
        - The barrier is marked PARTIAL — next stage is BLOCKED.
        - TaskPlanner reports failure to user with partial results summary.
BS-3: User chooses recovery: (a) fix and retry failed task, (b) re-plan entire pipeline,
      (c) proceed with partial results (only if downstream tasks do not depend on failed task).
BS-4: Barrier timeout: if any task exceeds estimated duration by 3x, TaskPlanner issues
      a STATUS_CHECK — if the agent is still working, extend; if STOPPED, trigger BS-2.
```

## Resource Conflict Detection (RC)

Before dispatching a parallel stage, TaskPlanner MUST verify no write-territory overlap:

```
RC-1: Collect `writes_to` from all tasks in the stage.
RC-2: For each pair of tasks, compute set intersection of `writes_to`.
RC-3: Non-empty intersection → mark the pair as SEQUENTIAL (move one to next stage).
RC-4: DOM-02 storage territory rules still apply per-agent — RC is an additional check.
```

## Plan Approval Gate

TaskPlanner MUST present the plan to the user BEFORE dispatching Stage 1.
The plan presentation includes:
- Stage diagram (text DAG)
- Per-task agent, inputs, outputs, estimated complexity
- Resource conflict resolutions applied
- Domain ordering constraints applied

User may: (a) approve as-is, (b) request modifications, (c) reject and provide new instructions.

## Integration with P-E-V-A

Each atomic task within a TaskPlanner stage follows the standard P-E-V-A loop.
TaskPlanner operates at the PLAN phase — it does not replace or bypass any gate.
The per-task P-E-V-A is managed by the assigned Coordinator or Specialist as usual.

```
TaskPlanner (PLAN — compound decomposition)
  └── Stage 1: [Task A (P-E-V-A), Task B (P-E-V-A)]  ← parallel
       └── Barrier Sync
            └── Stage 2: [Task C (P-E-V-A)]           ← sequential
                 └── Barrier Sync
                      └── HAND-02 RETURN to ResearchArchitect
```

────────────────────────────────────────────────────────
# § CI/CP PIPELINE — Continuous Integration / Continuous Paper

CI/CP defines how changes propagate through the T-L-E-A chain without breaking downstream domains.

## Trigger conditions

| Event | Propagation chain | Interface Contracts invalidated | Additional effect |
|-------|------------------|---------------------------------|------------------|
| T-Domain equation changes | T → L → E → A | `AlgorithmSpecs.md`, `SolverAPI_vX.py`, `ResultPackage/`, `TechnicalReport.md` | — |
| L-Domain solver API changes | L → E → A | `SolverAPI_vX.py`, `ResultPackage/`, `TechnicalReport.md` | — |
| L-Domain `src/twophase/` hash changes (any commit to solver code) | L → E → A | `SolverAPI_vX.py`, `ResultPackage/`, `TechnicalReport.md` | All `paper/` figures tagged **[STALE]**; A-Gatekeeper PASS blocked until figures re-generated via E-Domain |
| E-Domain result changes | E → A | `ResultPackage/`, `TechnicalReport.md` | — |
| A-Domain paper revision (no upstream impact) | A only | none upstream | — |

## CI/CP Protocol

```
CHANGE-PROPAGATION:
  1. Triggering domain Gatekeeper issues INVALIDATION notice for affected interface contracts.
  2. Each downstream domain Gatekeeper receives notice and BLOCKS any new dev/ work
     until the upstream Interface Contract is re-signed.
  2a. [src/twophase/ hash change only] PaperWorkflowCoordinator tags all paper/ figures as [STALE]
      in docs/02_ACTIVE_LEDGER.md. A-Domain Gatekeeper (PaperWorkflowCoordinator +
      PaperReviewer) CANNOT issue PASS on any A-Domain PR until [STALE] figures are
      re-generated by ExperimentRunner (E-Domain) and the new ResultPackage/ is signed.
  3. Upstream domain executes its pipeline (T/L/E) → re-signs its Interface Contract.
  4. Downstream Gatekeeper verifies new contract → unblocks Specialists.
  5. ConsistencyAuditor (Q-Domain) performs cross-domain AU2 gate after each re-signing.
```

**[STALE] figure rule:** A paper/ figure tagged [STALE] must not appear in any VALIDATED-phase
commit. The [STALE] tag is cleared ONLY when ExperimentRunner completes EXP-01 + EXP-02
against the new `src/twophase/` and the new `ResultPackage/` is signed by the E-Domain Gatekeeper.

**Hard rule:** A Specialist may not begin work on a domain whose upstream Interface Contract
has been invalidated. Starting work on an invalid contract is a CONTAMINATION violation.

**Rolling validation:** For large changes, ResearchArchitect may sequence the propagation
one domain at a time (T → L gate, then L → E gate, etc.) rather than all-at-once.

## [INTEGRITY_MANIFEST] — Hash Continuity Protocol

Maintain an `[INTEGRITY_MANIFEST]` section within `docs/02_ACTIVE_LEDGER.md` that records
the artifact hash of each domain's signed Interface Contract in the dependency chain:

```
[INTEGRITY_MANIFEST]
  T_hash: {sha256 of docs/interface/AlgorithmSpecs.md at time of signing}
  L_hash: {sha256 of docs/interface/SolverAPI_vX.py at time of signing}
  E_hash: {sha256 of docs/interface/ResultPackage/ manifest at time of signing}
  A_hash: {sha256 of final paper/sections/ commit at time of VALIDATED}
```

**Dependency chain rule:** T(hash) → L(hash) → E(hash) → A(hash).
Each downstream hash is recorded only after the upstream hash is locked.

**Gatekeeper mandate:** Before issuing a PASS verdict at any domain boundary, the Gatekeeper
MUST verify hash continuity — confirm that the upstream hash recorded in [INTEGRITY_MANIFEST]
matches the current state of the upstream Interface Contract. A hash mismatch means the
downstream domain was built on an invalidated contract (CONTAMINATION violation → CI/CP
re-propagation required).

**Update rule:** When a domain re-signs its Interface Contract (after CI/CP propagation),
the corresponding hash and all downstream hashes MUST be updated before new dev/ work begins.

**Initialization rule (first-run):** On fresh deployment, `[INTEGRITY_MANIFEST]` does not yet exist.
EnvMetaBootstrapper creates the section with all hashes set to `{pending}`. A `{pending}` hash means
the corresponding domain's Interface Contract has not yet been signed. Downstream domains must treat
`{pending}` upstream hashes the same as a missing contract — BLOCK new dev/ work until the upstream
domain executes its pipeline and replaces `{pending}` with a real hash.

**Hash mismatch circuit breaker:** If a Gatekeeper performing hash continuity verification finds that
the current `sha256` of an upstream Interface Contract does NOT match the hash recorded in
`[INTEGRITY_MANIFEST]`, the Gatekeeper MUST:
1. Issue a CONTAMINATION notice in `docs/02_ACTIVE_LEDGER.md`
2. STOP all downstream dev/ work immediately
3. Trigger CI/CP re-propagation from the domain where the mismatch was detected
4. Do NOT issue PASS until the hash is reconciled and the manifest is updated

────────────────────────────────────────────────────────
# § GIT BRANCH GOVERNANCE → meta-domains.md

Authoritative definitions — branch ownership, storage territory, 3-phase lifecycle,
branch rules, domain lock protocol, contamination guard: **meta-domains.md**.

Quick reference only:
- `code`, `paper`, `prompt`: Domain Integration Staging branches; owned by Gatekeepers
- `dev/{agent_role}`: Individual Workspaces; sovereign per Specialist; created via GIT-SP
- `docs/interface/`: Shared inter-domain agreements; writable by Gatekeepers only (→ GIT-00)
- `main`: protected — never committed directly (A8); merged via PR by Root Admin only
- 3-phase lifecycle: DRAFT (GIT-02 on dev/) → REVIEWED (dev/ PR merged to domain by Gatekeeper, GIT-03) → VALIDATED (domain PR merged to main by Root Admin, GIT-04)
- Session start: GIT-00 (IF-Agreement) → GIT-01 (Branch Preflight) → DOM-01 (Domain Lock)
- `git commit` on `main` = A8 violation → abort and re-run GIT-01
- Branch Isolation: Specialists MUST NOT access other agents' `dev/` branches (→ meta-domains.md §BRANCH ISOLATION)
- Selective Sync: pull from main ONLY when docs/interface/ updated OR merge conflict detected (→ meta-domains.md §SELECTIVE SYNC)

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

Each pipeline is a concrete instantiation of P-E-V-A (§ above).
All pipelines share a common structure — domain-specific details are in the table and notes below.

## Common Pipeline Structure (all domains)

```
PRE-CHECK  Gatekeeper → GIT-01 (branch preflight) + DOM-01 (domain lock)
IF-AGREE   Gatekeeper → GIT-00 (interface contract) → Specialist reads contract → creates dev/ branch
PLAN       Gatekeeper → identify gaps, record in 02_ACTIVE_LEDGER.md, dispatch Specialist
EXECUTE    Specialist → produce artifact on dev/ branch → open PR: dev/ → {domain} (LOG-ATTACHED)
VERIFY     Verifier   → run checks → PASS: Gatekeeper merges (GIT-03) + opens PR → main (GIT-04-A)
                                    → FAIL: loop back to EXECUTE (P6 bounded)
AUDIT      ConsistencyAuditor → AU2 gate → PASS: Root Admin merges → main (GIT-04-B)
                                          → FAIL: route error to responsible agent
```

## Domain Pipeline Agent Assignments

| Domain | Branch | Gatekeeper | EXECUTE agents | VERIFY agent(s) | AUDIT gate | Precondition |
|--------|--------|------------|----------------|-----------------|------------|--------------|
| **T** Theory | `theory` | TheoryAuditor | CodeArchitect, PaperWriter | TheoryAuditor (independent re-derivation) | ConsistencyAuditor | none (upstream) |
| **L** Code | `code` | CodeWorkflowCoordinator | CodeArchitect, CodeCorrector, CodeReviewer | TestRunner (TEST-01/02) | ConsistencyAuditor | `docs/interface/AlgorithmSpecs.md` signed |
| **E** Experiment | `experiment` | CodeWorkflowCoordinator | ExperimentRunner (EXP-01/02) | CodeWorkflowCoordinator (Validation Guard) | ConsistencyAuditor | `docs/interface/SolverAPI_vX.py` signed |
| **A** Paper | `paper` | PaperWorkflowCoordinator | PaperWriter | PaperCompiler + PaperReviewer | ConsistencyAuditor | `docs/interface/ResultPackage/` signed |
| **P** Prompt | `prompt` | PromptArchitect | PromptArchitect (includes compression pass) | PromptAuditor (Q3 checklist) | PromptAuditor | none |

## Domain-Specific Notes

**T-Domain (Theory):**
- TheoryAuditor re-derives independently WITHOUT reading Specialist's work first (→ §B Broken Symmetry)
- DISAGREE → STOP; surface conflict; do not average; escalate to user
- On AUDIT PASS → TheoryAuditor signs `docs/interface/AlgorithmSpecs.md`

**L-Domain (Code):**
- VERIFY FAIL routing: THEORY_ERR → CodeArchitect; IMPL_ERR → CodeCorrector
- Optional: ExperimentRunner after VERIFY and before AUDIT (sanity + reproducibility checks)

**E-Domain (Experiment):**
- Precondition is hard: absent `docs/interface/SolverAPI_vX.py` → STOP; run L-Domain first
- VERIFY: all 4 sanity checks (SC-1–SC-4) must PASS; partial results → STOP
- On VERIFY PASS → Gatekeeper signs `docs/interface/ResultPackage/`

**A-Domain (Paper):**
- VERIFY exit: 0 FATAL + 0 MAJOR → PASS. FATAL or MAJOR → PaperWriter (correction mode) → PaperCompiler loop
- AUDIT FAIL routing: PAPER_ERROR → PaperWriter; CODE_ERROR → CodeArchitect → TestRunner

**P-Domain (Prompt):**
- PromptArchitect is both Gatekeeper and EXECUTE agent (Broken Symmetry preserved: PromptAuditor is the independent VERIFY agent)
- AUDIT gate = PromptAuditor (doubles as domain gate for prompt domain)

────────────────────────────────────────────────────────
## Bootstrap Pipeline (new feature only — run before Code Pipeline)

Use when introducing a component that does not yet exist in any form.
Not the default pipeline.

| Step | Agent | Output | Gate |
|------|-------|--------|------|
| 1: Formal Axiomatization | PaperWriter | docs/memo/ derivation entry | Logic self-consistent; no UI/framework mention |
| 2: Structural Contract | CodeArchitect | prompts/specs/ interface definition | Dependency unidirectional (A9) |
| 3: Headless Implementation | CodeArchitect | src/core/ module (stdlib only) | TestRunner PASS in CLI environment |
| 4: Shell Integration | CodeArchitect | src/system/ wrapper | ExperimentRunner sanity checks PASS |

Rules:
- Step 1 is immutable once Step 2 begins; changes require re-entering Step 1
- Step 3 must not reference any Step 4 artifact
- CRITICAL_VIOLATION if Step 4 bypasses Step 2 contract to access Step 3 internals (A9)

────────────────────────────────────────────────────────
# § STOP-RECOVER MATRIX

When an agent triggers a STOP condition, this matrix defines the recovery pathway.
Every STOP is recoverable — the question is WHO resolves it and WHERE the pipeline resumes.

## Recovery Table

| STOP Trigger | Severity | Recovery Agent | Recovery Action | Resume Point |
|-------------|----------|---------------|----------------|-------------|
| Paper/equation ambiguity | STOP-HARD | User → PaperWriter or CodeArchitect | User clarifies ambiguity; Specialist re-derives | EXECUTE |
| TestRunner FAIL | STOP-HARD | Coordinator → CodeCorrector | Classify THEORY_ERR/IMPL_ERR (P9); dispatch targeted fix | EXECUTE |
| AU2 FAIL — PAPER_ERROR | STOP-HARD | ConsistencyAuditor → PaperWriter | Cite specific AU2 item; PaperWriter fixes | EXECUTE |
| AU2 FAIL — CODE_ERROR | STOP-HARD | ConsistencyAuditor → CodeArchitect | Cite specific AU2 item; re-implement from spec | EXECUTE |
| AU2 FAIL — THEORY_ERROR | STOP-HARD | ConsistencyAuditor → TheoryArchitect | Re-derive from first principles; TheoryAuditor re-verifies | EXECUTE (T-Domain) |
| Authority conflict (paper vs code vs theory) | STOP-HARD | User | User ruling + rationale recorded in LEDGER; φ3 hierarchy applied | PLAN |
| Merge conflict (GIT) | STOP-HARD | User | Manual conflict resolution; re-run GIT-01 | PRE-CHECK |
| MAX_REJECT_ROUNDS exceeded (Gatekeeper) | STOP-HARD | User → Root Admin | Review both Specialist + Gatekeeper artifacts; binding ruling | VERIFY |
| Loop > MAX_REVIEW_ROUNDS (Coordinator) | STOP-HARD | User | Review full loop history; scope change decision | PLAN |
| Branch contamination (DOM-02 violation) | STOP-HARD | User | Revert contaminated commit; re-run GIT-SP from clean state | PRE-CHECK |
| Upstream contract invalidated (CI/CP) | STOP-HARD | CI/CP propagation | Re-sign upstream contract; cascade INVALIDATED signals downstream | PLAN |
| Broken Symmetry detected (Auditor saw CoT) | STOP-HARD | Coordinator | Re-dispatch Auditor in fresh session (L3 isolation) with sanitized inputs | VERIFY |
| Token budget exceeded | STOP-SOFT | Coordinator | Compress context or split task; re-dispatch with smaller scope | EXECUTE |
| Missing input file | STOP-SOFT | Coordinator | Identify which upstream agent should produce it; dispatch | PLAN |
| PaperCompiler BUILD-FAIL | STOP-SOFT | PaperWorkflowCoordinator → PaperCompiler | Parse log; apply surgical fix; re-compile | VERIFY |
| GPU/environment error | STOP-SOFT | User → DevOpsArchitect | Fix environment; re-run experiment | EXECUTE |

| HAND token malformed (missing required field) | STOP-SOFT | DiagnosticArchitect | Re-emit corrected HAND token (ERR-R3); Gatekeeper approves | PLAN |
| BUILD-FAIL — missing dependency or config error | STOP-SOFT | DiagnosticArchitect | Propose install/config fix (ERR-R2); Gatekeeper approves; retry | EXECUTE |
| Wrong write path caught before commit (pre-DOM-02) | STOP-SOFT | DiagnosticArchitect | Propose corrected path (ERR-R1); Gatekeeper approves; Specialist retries | EXECUTE |
| GIT conflict on non-logic file (.gitignore, config) | STOP-SOFT | DiagnosticArchitect | Propose merge resolution (ERR-R4); Gatekeeper approves | PRE-CHECK |

## Recovery Protocol

1. **Agent triggers STOP:** Issue RETURN token with `status: STOPPED` and `issues` field citing the specific trigger.
2. **Coordinator receives RETURN:** Look up trigger in this matrix → identify Recovery Agent and Resume Point.
3. **Coordinator dispatches recovery:** Issue HAND-01 to Recovery Agent with context block including:
   - Original task scope
   - STOP trigger description
   - Resume Point (which P-E-V-A phase to re-enter)
4. **Recovery Agent completes fix:** Issues HAND-02 RETURN → pipeline resumes at Resume Point.
5. **If Recovery Agent is "User":** Coordinator issues RETURN STOPPED to user with full context; awaits user input.

**Hard rule:** A coordinator that encounters a STOP trigger NOT listed in this matrix must escalate to User — do not improvise recovery paths.

## DiagnosticArchitect Self-Healing Flow

When the Recovery Agent column is **DiagnosticArchitect**, the coordinator uses the following sub-protocol instead of the standard Recovery Protocol above:

```
Coordinator
  │── HAND-01 → DiagnosticArchitect (STOP trigger + error class ERR-R?)
  │
  DiagnosticArchitect
  │── Classify: RECOVERABLE or NON-RECOVERABLE
  │   If NON-RECOVERABLE → HAND-02 STOPPED to coordinator → escalate to User
  │── Write artifacts/M/diagnosis_{id}.md
  │── HAND-01 → Gatekeeper (fix proposal)
  │
  Gatekeeper
  │── Review fix proposal (DOM-02 + scope check only)
  │── HAND-02 PASS → DiagnosticArchitect     OR    HAND-02 FAIL → DiagnosticArchitect
  │                                                  (increment repair round counter)
  DiagnosticArchitect
  │── On PASS: HAND-01 → originally blocked agent (fix applied; resume at Resume Point)
  │── On FAIL (round < 3): propose revised fix → back to Gatekeeper
  │── On FAIL (round = 3): HAND-02 STOPPED → coordinator → User
  │
  Coordinator
  └── Pipeline resumes at Resume Point OR escalates to User
```

**Gatekeeper scope in DiagnosticArchitect flow:** Gatekeeper reviews fix proposals for
DOM-02 compliance and safety only — NOT for scientific correctness. Scientific correctness
checks (GA-4, GA-6) do not apply to diagnostic fix proposals.

────────────────────────────────────────────────────────
# § HANDOFF RULES

**Canonical handoff protocol:** meta-ops.md §HANDOFF PROTOCOL (HAND-01, HAND-02, HAND-03)

All agent-to-agent transfers use the structured token format defined there.
Every dispatch sends HAND-01; every completion returns HAND-02;
every receiver runs HAND-03 (Acceptance Check) before starting work.

**Definition of Done — Main-Merge Rule:**
A task is NOT considered finished until all work is merged into `main` via GIT-04 Phase B
(Root Admin final merge). Cross-domain handoffs (e.g., Code → Paper) are only permitted
after the source domain's work is merged into `main`. The receiving Gatekeeper MUST verify:

```
Cross-Domain Handoff Pre-check (run by receiving Gatekeeper before accepting):
  □ Verify source branch merged to main: confirm GIT-04 Phase B merge commit present in main history
    (→ meta-ops.md GIT-04 for merge commit format)
    Not found → REJECT handoff; source domain is not "Done" yet; return BLOCKED
  □ Run PRE-CHECK for the new domain (→ GIT-01 Selective Sync + DOM-01)
  □ Run IF-AGREE for the new task (→ GIT-00; write new IF-AGREEMENT before dispatching Specialist)
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
# § SESSION TERMINATION PROTOCOL — Context Liquidation

When an agent completes its task and issues a HAND-02 (RETURN token), the following
context liquidation rules apply to prevent token accumulation and context drift.

## HAND-02 Context Liquidation Rules

**HAND-02-CL (Context Liquidation):**
Upon issuing a RETURN token, the returning agent MUST declare that it **no longer
relies on its internal memory (conversation history)**. Only the serialized state
written to external files (domain storage or `artifacts/` when micro-agents are active)
is the source of truth for the next agent.

```
HAND-02-CL (Context Liquidation — appended to every HAND-02 RETURN):
  □ 1. All task-relevant state is serialized to external files (domain storage territory)
  □ 2. Agent declares: "Internal context is LIQUIDATED — external files are the sole
       source of truth for downstream agents"
  □ 3. No downstream agent may request or rely on the returning agent's
       conversation history, chain-of-thought, or intermediate reasoning
  □ 4. The RETURN token's `produced` field is the COMPLETE enumeration of
       what the agent leaves behind — anything not listed does not exist
```

**Fresh Context Recommendation:**
Whenever an agent handoff occurs (HAND-01 dispatch to a new agent), the receiving
agent SHOULD start in a **Fresh Context** (new session) to minimize token accumulation.
The receiving agent loads ONLY:
1. The DISPATCH token (HAND-01)
2. The referenced artifacts in `inputs` and `if_agreement`
3. Its own SCOPE files (meta-experimental.md §ATOMIC ROLE TAXONOMY)

**Rationale:** Long-running sessions accumulate stale context that increases token
cost per inference and introduces context drift. Fresh contexts force agents to
operate solely on serialized artifacts, reinforcing the Interface-First principle (IF-01).

**Hard rule:** A downstream agent that requests or consumes the upstream agent's
conversation history (rather than artifacts) commits a **Context Leakage Violation**.
This is equivalent to a CONTAMINATION violation — the receiving Gatekeeper must REJECT
the deliverable and re-dispatch with a fresh context.

## Sequence: GIT-00 → HAND-02-CL Flow

```
GIT-00 Pre-work (branch creation + PROJECT_MAP update)
    │
    ▼
EXECUTE phase (agent works on isolation branch)
    │
    ▼
GIT-SP commit (work + evidence committed to dev/{domain}/{agent_id}/{task_id})
    │
    ▼
GIT-SP PR (dev/ → {domain} with LOG-ATTACHED)
    │
    ▼
HAND-02 RETURN + HAND-02-CL (context liquidated; artifacts/ is sole truth)
    │
    ▼
[Gatekeeper HAND-03 Acceptance Check — loads only artifacts, never agent history]
    │
    ▼
[Fresh Context recommended for next agent dispatch]
```

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
- THEORY_ERR: root cause in solver logic or paper equation → fix in paper/ or docs/memo/ first
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
# § POST-EXECUTION FEEDBACK LOOP

Every agent that issues a HAND-02 RETURN token SHOULD append a lightweight
**POST-EXECUTION REPORT** block. This report feeds the self-evolution mechanism
(§META-EVOLUTION POLICY below) with empirical data from actual agent execution.

## POST-EXECUTION REPORT Format

Appended to HAND-02 RETURN token (after standard fields):

```yaml
POST_EXECUTION_REPORT:
  friction_points:         # protocol steps that caused unnecessary overhead
    - "{description of friction — cite specific rule/protocol ID}"
  rules_useful:            # rules that actively prevented an error or guided a decision
    - "{rule ID}: {how it helped}"
  rules_irrelevant:        # rules loaded but never consulted for this task
    - "{rule ID}"
  anti_patterns_triggered: # AP-xx patterns that were detected and avoided
    - "{AP-xx}: {what would have happened without the check}"
  uncovered_scenarios:     # situations encountered that no rule addressed
    - "{description of gap}"
  isolation_level_used:    # actual isolation level applied (L0/L1/L2/L3)
    level: "L1"
    sufficient: true       # was this level adequate for the task?
  tier_used: "TIER-2"      # which prompt tier was active
  tier_adequate: true       # was the tier sufficient, or was information missing?
```

## Collection Rules

1. **Mandatory fields:** `friction_points` and `uncovered_scenarios` (even if empty `[]`)
2. **Optional fields:** all others (omit if nothing to report)
3. **Token budget:** report must not exceed 150 tokens total
4. **Honesty principle:** agents must report friction even when it reflects poorly on the system
5. **No self-diagnosis:** report observations only — do not propose meta-level fixes
   (that is the META-EVOLUTION POLICY's job)

## Aggregation and Consumption

1. Coordinators (CodeWorkflowCoordinator, PaperWorkflowCoordinator) collect POST_EXECUTION_REPORTs
   from all specialists in their session
2. At session end, coordinator writes an aggregated **SESSION_FEEDBACK** entry to
   `docs/02_ACTIVE_LEDGER.md §FEEDBACK` (append-only):
   ```
   SESSION_FEEDBACK:
     date: {ISO 8601}
     domain: {T|L|E|A|P}
     pipeline_mode: {TRIVIAL|FAST-TRACK|FULL-PIPELINE}
     agents_invoked: [{agent1}, {agent2}, ...]
     top_friction: "{most frequently cited friction point}"
     uncovered_gaps: [{gap1}, {gap2}]
     anti_patterns_caught: [{AP-xx}, ...]
   ```
3. ResearchArchitect reads §FEEDBACK on session start (alongside §ACTIVE STATE)
   to inform pipeline mode classification and routing decisions
4. Periodic review: after every 10 SESSION_FEEDBACK entries, a human operator or
   PromptArchitect evaluates whether meta-*.md updates are warranted

────────────────────────────────────────────────────────
# § META-EVOLUTION POLICY

**Cycle:** Observe → Evaluate (structural vs. incidental) → Generalize → Promote → Validate → Compress

**M1: Knowledge Promotion** — On ConsistencyAuditor PASS (full domain cycle): extract reusable
patterns and record in docs/02_ACTIVE_LEDGER.md §LESSONS. Promote to meta-core.md §AXIOMS only if
the pattern is system-wide, axiom-compatible, and brief (A1).

**M2: Self-Healing** — Apply P9 before any fix.
- THEORY_ERR → update docs/memo/ or paper first, then re-derive implementation
- IMPL_ERR → patch src/system/ (infrastructure) only; never touch solver core (src/core/)
Record in 02_ACTIVE_LEDGER.md §LESSONS.

**Deprecate** if: obsolete, redundant, subsumed, conflicting, or over-specific.
**Promote** only if: repeated usefulness, structural generality, axiom-compatible, short formulation.
**Never promote** if: increases ambiguity, breaks solver purity, mixes layers, or weakens reproducibility.
If uncertain: keep in 02_ACTIVE_LEDGER.md §LESSONS.

────────────────────────────────────────────────────────
## § META-EVOLUTION GUARDRAILS

Any self-evolution proposal — whether from a human operator, an agent, or a bootstrapper run —
that modifies or weakens the following **Immutable Zones** must be treated as a **System Panic**:

**Immutable Zone 1: Foundational Principles**
- All φ-Principles (φ1–φ7) in meta-core.md §DESIGN PHILOSOPHY
- All Axioms (A1–A10) in meta-core.md §AXIOMS

**Immutable Zone 2: Acceptance Check Logic**
- HAND-03 Acceptance Check items (checks 0–10) in meta-ops.md §HANDOFF PROTOCOL

**Immutable Zone 3: Main Branch Protection**
- The `main` branch is NEVER directly committed to by any agent except Root Admin (A8)
- Any file change detected on `main` by a non-Root-Admin agent triggers SYSTEM_PANIC

**System Panic protocol:**
```
SYSTEM_PANIC triggered by: {proposing agent or operation}
  reason:   "Immutable Zone modification attempted: {zone name} — {specific element}"
  proposal: {verbatim text of the proposed change}
  action:   STOP all pipeline activity immediately
  required: escalate to user; do not apply any part of the proposal
  resume:   only after explicit user authorization with documented rationale
```

**Main Branch Contamination SYSTEM_PANIC:**
```
SYSTEM_PANIC triggered by: {agent_id}
  reason:   "Forbidden write to main branch detected — Immutable Zone 3 violation"
  evidence: git log --oneline -1 main  (shows unauthorized commit)
  action:   STOP all pipeline activity immediately
  required: escalate to user; revert unauthorized commit on main
  resume:   only after explicit user authorization + revert confirmed
```

**Corollary:** A proposal that "refines" or "tightens" an axiom without removing it is still
a modification. Intent does not override the rule — structure does. Route all Immutable Zone
proposals to the user before any edit is made to prompts/meta/*.md.

**Permitted evolution paths (outside Immutable Zones):**
- Adding new axioms (A11+) — permitted if axiom-compatible and user-authorized
- Adding new control protocols (P-new) — permitted in meta-workflow.md §CONTROL PROTOCOLS
- Adding new operations (NEW-xx) — permitted in meta-ops.md with correct AUTH_LEVEL tag
- Modifying Layer 3 (meta-workflow.md, meta-deploy.md) — permitted within bounds of Layer 1+2
- Modifying Layer 2 (meta-domains.md, meta-roles.md, meta-ops.md) operations — permitted
  if not touching HAND-03 acceptance logic or AUTH_LEVEL definitions in Immutable Zone 2

────────────────────────────────────────────────────────
# § COMMAND FORMAT → meta-ops.md §COMMAND FORMAT

Canonical command syntax and invocation rules: **meta-ops.md §COMMAND FORMAT**.
