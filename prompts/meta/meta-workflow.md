# DEPRECATED — v7.0.0: Superseded by kernel-workflow.md. Do not edit. Retained for reference only.
# META-WORKFLOW: Inter-Agent Coordination, Task Flow & Evolution
# VERSION: 3.1.0
# ABSTRACT LAYER — workflow logic: P-E-V-A loop, domain pipelines, handoff rules, control protocols.
# FOUNDATION (φ1–φ7, A1–A11): prompts/meta/meta-core.md  ← READ FIRST
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

The primary execution order for all new work. Each arrow = mandatory Interface Contract gate.

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
  │  ConsistencyAuditor performs AU2 gate at each domain boundary.
  │  Atomic: ResultAuditor → artifacts/Q/audit_{id}.md
  ▼
main (VALIDATED + merged by Root Admin)

K-Domain (Knowledge/Wiki) — parallel, post-validation
  │  Triggered by: any domain artifact reaching VALIDATED phase
  │  KnowledgeArchitect compiles wiki entry; WikiAuditor verifies pointer integrity
  │  OUTPUT: docs/wiki/{category}/{REF-ID}.md [signed by WikiAuditor]
```

**T-L-E-A ordering is mandatory.** No domain begins work without the upstream Interface Contract signed.
Exceptions require explicit user authorization. Continuous Paper mode: → §CI/CP PIPELINE.

### Worked Example: Bug fix in Laplacian stencil (FULL-PIPELINE)

| Step | Agent | Task (HAND-01 `task` field) | HAND-02 `status` | STOP if violated |
|------|-------|----------------------------|------------------|-----------------|
| 1 | TheoryAuditor | Re-derive 6th-order CCD Laplacian stencil from governing PDE | SUCCESS + AlgorithmSpecs.md signed | STOP-02 if stencil contradicts existing derivation |
| 2 | CodeArchitect | Revise `src/twophase/ccd/laplacian.py` per new AlgorithmSpecs.md | SUCCESS + SolverAPI signed | STOP-03 if spec–code mismatch remains |
| 3 | ExperimentRunner | Run MMS test `experiment/ch11/test_ccd_laplacian.py`; attach log | SUCCESS + ResultPackage signed | STOP-05 if MMS order < 5.8 |
| 4 | ConsistencyAuditor | AU2 gate: theory ↔ code ↔ MMS cross-check | AU2 PASS | STOP-04 if any discrepancy unfixed |
| 5 | PaperWriter | Update §3.2 stencil description to match new derivation | SUCCESS + diff attached | STOP-06 if paper contradicts ResultPackage |
| 6 | Root Admin | Merge domain PR to `main` after GA-0–GA-6 all satisfied | (merge) | STOP-02 if any GA unsatisfied |

────────────────────────────────────────────────────────
# § PIPELINE MODE — TRIVIAL / FAST-TRACK / FULL-PIPELINE

ResearchArchitect classifies every incoming task before routing (part of GIT-01 Step 0).
When uncertain → classify one level higher (φ1).

## Classification Criterion

| Condition | Mode |
|-----------|------|
| Touches `docs/memo/`, `docs/interface/*.md`, or `src/core/`; new domain branch required | **FULL-PIPELINE** |
| Whitespace-only, comment-only, typo fix, docs-only | **TRIVIAL** |
| All other changes (bug fix, paper prose, experiment re-run, config) | **FAST-TRACK** |

## Gatekeeper Intensity

| Mode | Gatekeeper Protocol | Independent Re-derivation |
|------|---------------------|---------------------------|
| TRIVIAL | Lint + DOM-02 scope-check only | NONE |
| FAST-TRACK | Standard P-E-V-A; GA-2/3/5 | SUMMARY only |
| FULL-PIPELINE | Full AU2 gate + all GA conditions | MANDATORY (GA-4) |

## TRIVIAL Mode

**Applicable to:** typo, whitespace, comment, docs-only, `.gitignore`, config formatting.
**NOT applicable to:** any `.py`, `.tex` (content), solver params, test files, interface contracts.

| Gate | Status |
|------|--------|
| HAND-03 Acceptance Check | OMITTED |
| GIT-SP branch isolation | OMITTED — commit directly on domain branch |
| DOM-02 Pre-Write Storage Check | RETAINED |
| HAND-02 RETURN token | OMITTED |
| Gatekeeper PR review | OMITTED — coordinator may self-commit |
| IF-Agreement (GIT-00) | OMITTED |
| AU2 PASS | OMITTED |

**Commit format:** `{branch}: trivial — {summary}`
**Upgrade to FAST-TRACK if:** logic change found, test behavior affected, or diff > 20 lines.

## FULL-PIPELINE Mode

Full T-L-E-A ordering; all protocols apply. Use for: new theory derivations, solver algorithm changes,
API contract changes, cross-domain work, changes to `src/core/` or `docs/interface/`.

## FAST-TRACK Mode

| Omitted gate | Reason |
|-------------|--------|
| IF-Agreement (GIT-00) | Existing contract reused; declared in DISPATCH |
| AU2 PASS | Gatekeeper PR review sufficient for intra-domain low-risk |
| Micro-agent decomposition | Not required |

**Retained:** GIT-SP, DOM-02, HAND-03 checks 1–4 and 6 (omit check 5: upstream-contract for FAST-TRACK),
MERGE CRITERIA (TEST-PASS + LOG-ATTACHED), GA-2/3/5.

**Use for:** bug fixes, paper prose, docs, experiment re-runs, config, refactors not touching `src/core/`.
**Upgrade to FULL-PIPELINE if:** fix requires `src/core/` or `docs/interface/`; theory inconsistency found; downstream impact detected.

────────────────────────────────────────────────────────
# § PARALLEL EXECUTION — TaskPlanner Staged Dispatch

A task is COMPOUND when ANY C1–C5 criterion holds (see ResearchArchitect.md).

## Parallel Eligibility (PE)

| Rule | Description |
|------|-------------|
| PE-1 | Tasks with no `depends_on` edges MAY run in parallel |
| PE-2 | Tasks writing to the SAME file/directory MUST NOT run in parallel |
| PE-3 | Same-domain tasks sharing same Gatekeeper MAY run in parallel on separate `dev/` branches |
| PE-4 | Cross-domain tasks MUST respect T-L-E-A ordering |
| PE-5 | TRIVIAL-mode tasks MAY run in parallel with any non-conflicting task |

## Barrier Sync (BS) + Resource Conflict (RC)

- **BS-1:** Stage N+1 does NOT begin until ALL tasks in Stage N issue HAND-02 RETURN.
- **BS-2:** Any STOPPED/FAIL in a parallel stage → barrier PARTIAL; next stage BLOCKED.
- **BS-3:** User chooses: (a) fix + retry, (b) re-plan, (c) proceed with partial results.
- **BS-4:** Task exceeds 3× estimated duration → STATUS_CHECK; still working=extend, STOPPED=trigger BS-2. Under `concurrency_profile == "worktree"`: any task holding a branch lock >24 h past its `acquired_at` is a STATUS_CHECK candidate, and if stale → **STOP-10** (`meta-ops.md § STOP CONDITIONS`). Stale locks are NEVER silently reclaimed (see `docs/locks/README.md`).
- **RC-1/2/3:** Collect `writes_to` per task; non-empty intersection → make SEQUENTIAL.
- **RC-4:** DOM-02 rules still apply per-agent; RC is an additional pre-dispatch check.
- **RC-5 (v5.1):** Under `concurrency_profile == "worktree"`, `writes_to` conflict is additionally guarded by the BRANCH_LOCK_REGISTRY pre-check (`docs/02_ACTIVE_LEDGER.md §4`): a task whose branch already appears in §4 under another session MUST NOT be dispatched. RC-5 composes with RC-1/2/3 — both path-level AND branch-level must be collision-free.

> Under `concurrency_profile == "worktree"` (v5.1), each node also acquires/releases a
> branch lock — see **§ CONCURRENCY EXTENSIONS (v5.1 only)** below for full node semantics.

## Plan Approval Gate

TaskPlanner presents plan to user before Stage 1: stage DAG, per-task agent/inputs/outputs,
resource conflict resolutions, domain ordering constraints. User approves / modifies / rejects.

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

## Trigger conditions

| Event | Propagation chain | Contracts invalidated |
|-------|------------------|-----------------------|
| T-Domain equation changes | T → L → E → A | `AlgorithmSpecs.md`, `SolverAPI_vX.py`, `ResultPackage/`, `TechnicalReport.md` |
| L-Domain solver API changes | L → E → A | `SolverAPI_vX.py`, `ResultPackage/`, `TechnicalReport.md` |
| L-Domain `src/twophase/` hash changes | L → E → A | Same as above + paper/ figures tagged **[STALE]**; A-Gatekeeper PASS blocked until figures re-generated |
| E-Domain result changes | E → A | `ResultPackage/`, `TechnicalReport.md` |
| A-Domain paper revision (no upstream) | A only | none |

## CI/CP Protocol

```
CHANGE-PROPAGATION:
  1. Triggering domain Gatekeeper issues INVALIDATION notice for affected interface contracts.
  2. Each downstream Gatekeeper BLOCKS new dev/ work until upstream contract re-signed.
  2a. [src/twophase/ hash change] PaperWorkflowCoordinator tags paper/ figures [STALE];
      A-Domain Gatekeeper CANNOT issue PASS until ExperimentRunner re-generates via E-Domain.
  3. Upstream domain executes its pipeline → re-signs Interface Contract.
  4. Downstream Gatekeeper verifies new contract → unblocks Specialists.
  5. ConsistencyAuditor performs cross-domain AU2 gate after each re-signing.
```

**Hard rule:** Starting work on an invalidated contract = CONTAMINATION violation.
**Rolling validation:** ResearchArchitect may sequence propagation one domain at a time.

## [INTEGRITY_MANIFEST] — Hash Continuity

`docs/02_ACTIVE_LEDGER.md` maintains a `[INTEGRITY_MANIFEST]` section:

```
[INTEGRITY_MANIFEST]
  T_hash: {sha256 of docs/interface/AlgorithmSpecs.md at signing}
  L_hash: {sha256 of docs/interface/SolverAPI_vX.py at signing}
  E_hash: {sha256 of docs/interface/ResultPackage/ manifest at signing}
  A_hash: {sha256 of final paper/sections/ commit at VALIDATED}
```

T → L → E → A: each hash recorded only after upstream is locked.
Gatekeeper MUST verify hash continuity before issuing PASS. Mismatch = CONTAMINATION → CI/CP re-propagation.
Fresh deployment: all hashes `{pending}` — treat as missing contract; block downstream work.
Hash mismatch action: (1) issue CONTAMINATION notice, (2) STOP downstream dev/, (3) trigger CI/CP re-propagation.

────────────────────────────────────────────────────────
# § CONCURRENCY EXTENSIONS (v5.1 only — worktree profile)

> **Load condition:** applies ONLY when `_base.yaml :: concurrency_profile == "worktree"`.
> Under `legacy` profile this section is descriptive, not enforced.
> Standard agents do NOT need to read this section at session start.

Introduced by CHK-114. Promotes the T-L-E-A pipeline nodes (rule PE-4) to a **Node**
abstraction with mandatory lock bindings. Each node wraps the P-E-V-A loop with
concurrency semantics; P-E-V-A itself is unchanged.

**Node structure (all four T/L/E/A nodes share this pattern):**
- **Pre**: `LOCK-ACQUIRE {branch}` (`meta-ops.md §LOCK-ACQUIRE`). Collision with another `session_id` → STOP-10.
- **Body**: node-specific work; P-E-V-A loop runs inside.
- **Post**: `LOCK-RELEASE {branch}` after HAND-02 emitted; `GIT-ATOMIC-PUSH` runs BEFORE release, inside the lock.

### T-Node (Theory)
**Body:** derive → TheoryAuditor independent re-derivation. `verification_hash` covers derivation document. No code writes; `src/` and `experiment/` forbidden (DOM-02).
**Lock scope:** `dev/T/{agent_id}/{task_id}` branch in dedicated worktree.
**Success criterion:** TheoryAuditor re-derivation PASS + schema-valid HAND-02.

### L-Node (Library)
**Body:** implementation → Reflexion loop (P-E-V-A, max 5 iterations per φ5) → GIT-ATOMIC-PUSH → HAND-02. Test evidence (MMS / convergence / pytest) as structured output; `verification_hash` covers diff.
**Lock scope:** `dev/L/{agent_id}/{task_id}` branch in `../wt/{session_id}/dev-L-{agent_id}-{task_id}`.
**Success criterion:** pytest PASS + convergence order ≥ target + schema-valid HAND-02.

### E-Node (Experiment)
**Body:** simulation run → SC-1..SC-4 sanity checks → package results → HAND-02. Failed sanity check → STOP inside node; no forward push.
**Lock scope:** `dev/E/{agent_id}/{task_id}`; typically short-lived (hours not days).
**Success criterion:** all 4 sanity checks PASS + schema-valid HAND-02.

### A-Node (Academic Writing + Audit)
**Body:** classify finding → diff-only LaTeX patches → verdict table → HAND-02 (`verification_hash` covers patch). OR: cross-domain audit (independent re-derivation per HAND-03 check 6).
**Lock scope:** `dev/A/{agent_id}/{task_id}`; classify BEFORE acquiring lock to minimise held time.
**Success criterion:** BUILD-02 PASS (writing) OR all AU-2 items green (auditing) + schema-valid HAND-02.

### Inter-node synchronization
Nodes synchronize through two shared artifacts:
1. `docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY` — canonical lock state across all sessions.
2. `docs/locks/{branch_slug}.lock.json` — ephemeral O_EXCL guard.

Divergence between the two → STOP-10 CONTAMINATION_GUARD. T→L→E→A ordering (PE-4) is unchanged.

────────────────────────────────────────────────────────
# § GIT BRANCH GOVERNANCE → meta-domains.md

Authoritative definitions — branch ownership, storage territory, 3-phase lifecycle,
branch rules, domain lock protocol, contamination guard: **meta-domains.md**.

Quick reference:
- `code`, `paper`, `prompt`: Domain Integration Staging branches; owned by Gatekeepers
- `dev/{agent_role}`: Individual Workspaces; sovereign per Specialist; created via GIT-SP
- `docs/interface/`: Shared inter-domain agreements; writable by Gatekeepers only (→ GIT-00)
- `main`: protected — never committed directly (A8); merged via PR by Root Admin only
- 3-phase lifecycle: DRAFT → REVIEWED → VALIDATED
- Session start: GIT-00 → GIT-01 → DOM-01
- `git commit` on `main` = A8 violation → abort and re-run GIT-01

────────────────────────────────────────────────────────
# § P-E-V-A EXECUTION LOOP

Master execution frame for ALL domain work. No phase may be skipped.

| Phase | Responsibility | Agent | Output | git phase |
|-------|---------------|-------|--------|-----------|
| PLAN | Define scope, success criteria, stop conditions | Coordinator or ResearchArchitect | task scope (temp_work_log) | — |
| EXECUTE | Produce artifact; run CoVe self-check before HAND-02 | Specialist (CodeArchitect, PaperWriter, PromptArchitect…) | code / patch / paper / prompt | DRAFT commit |
| VERIFY | Confirm artifact meets spec (independent agent) | TestRunner / PaperCompiler+Reviewer / PromptAuditor | PASS or FAIL verdict | REVIEWED commit on PASS |
| AUDIT | Gate check; cross-system consistency | ConsistencyAuditor / PromptAuditor | AU2 gate verdict (10 items) | VALIDATED commit + merge on PASS |

Rules:
- FAIL at VERIFY → return to EXECUTE (not to PLAN unless scope changes)
- FAIL at AUDIT → return to EXECUTE
- Loop counter tracked per phase (P6); MAX_REVIEW_ROUNDS = 5
- AUDIT agent must be independent of EXECUTE agent (φ7)
- PLAN always starts with ResearchArchitect loading docs/02_ACTIVE_LEDGER.md

**CoVe (Chain-of-Verification) — Standard V-phase prerequisite (Pillar 2):**
CoVe is the Specialist's mandatory self-check inside EXECUTE, run immediately before issuing HAND-02.
Full spec: meta-roles.md §COVE MANDATE. Summary:
1. Generate 3 adversarial questions (logic, axiom compliance, scope/IF-Agreement fidelity).
2. Derive answers independently; correct the artifact for any flaw found.
3. Place ONLY the corrected artifact in HAND-02 payload; append `"CoVe: Q1=..., Q2=..., Q3=..."` to `detail`.

CoVe does NOT replace VERIFY. VERIFY remains an independent agent check (§B Broken Symmetry).
The Gatekeeper MUST reject any HAND-02 token where the `detail` field is absent or lacks the CoVe
summary — a missing summary signals incomplete EXECUTE. Action: return to EXECUTE, do not advance to VERIFY.

────────────────────────────────────────────────────────
# § LEDGER UPDATE CADENCE

Within a domain's EXECUTE phase, specialists append to `artifacts/temp_work_log.json`
(unstructured, append-only, session-local). The Gatekeeper performs a **batch-update** to
`docs/02_ACTIVE_LEDGER.md` at exactly two moments:

1. On `HAND-02` receipt (regardless of status), and
2. On AU2 `VALIDATED` verdict at AUDIT phase.

Between these moments, the ledger is **read-only**.
Any agent that writes to `02_ACTIVE_LEDGER.md` mid-EXECUTE commits a **Ledger-Thrash violation** (STOP-SOFT).

────────────────────────────────────────────────────────
# § DOMAIN PIPELINES

Each pipeline is a concrete instantiation of P-E-V-A. No phase may be skipped.

## Common Pipeline Structure

```
PRE-CHECK  Gatekeeper → GIT-01 (branch preflight) + DOM-01 (domain lock)
IF-AGREE   Gatekeeper → GIT-00 (interface contract) → Specialist creates dev/ branch
PLAN       Gatekeeper → identify gaps, dispatch Specialist
EXECUTE    Specialist → produce artifact on dev/ branch → open PR: dev/ → {domain} (LOG-ATTACHED)
VERIFY     Verifier   → run checks → PASS: Gatekeeper merges (GIT-03) + opens PR → main (GIT-04-A)
                                    → FAIL: loop back to EXECUTE (P6 bounded)
AUDIT      ConsistencyAuditor → AU2 gate → PASS: Root Admin merges → main (GIT-04-B)
                                          → FAIL: route error to responsible agent
```

## Domain Pipeline Agent Assignments

| Domain | Branch | Gatekeeper | EXECUTE agents | VERIFY agent(s) | AUDIT gate | Precondition |
|--------|--------|------------|----------------|-----------------|------------|--------------|
| **T** Theory | `theory` | TheoryAuditor | CodeArchitect, PaperWriter | TheoryAuditor (independent re-derivation) | ConsistencyAuditor | none |
| **L** Code | `code` | CodeWorkflowCoordinator | CodeArchitect, CodeCorrector, CodeReviewer | TestRunner (TEST-01/02) | ConsistencyAuditor | `docs/interface/AlgorithmSpecs.md` signed |
| **E** Experiment | `experiment` | CodeWorkflowCoordinator | ExperimentRunner (EXP-01/02) | CodeWorkflowCoordinator (Validation Guard) | ConsistencyAuditor | `docs/interface/SolverAPI_vX.py` signed |
| **A** Paper | `paper` | PaperWorkflowCoordinator | PaperWriter | PaperCompiler + PaperReviewer | ConsistencyAuditor | `docs/interface/ResultPackage/` signed |
| **P** Prompt | `prompt` | PromptArchitect | PromptArchitect (includes compression pass) | PromptAuditor (Q3 checklist) | PromptAuditor | none |
| **K** Knowledge | `wiki` | WikiAuditor | KnowledgeArchitect (K-COMPILE) | WikiAuditor (K-LINT + pointer check) | WikiAuditor | Any domain artifact at VALIDATED phase |

## Domain-Specific Notes

**T-Domain:** TheoryAuditor re-derives independently WITHOUT reading Specialist's work (Broken Symmetry).
DISAGREE → STOP; escalate to user. On AUDIT PASS → signs `docs/interface/AlgorithmSpecs.md`.

**L-Domain:** VERIFY FAIL routing: THEORY_ERR → CodeArchitect; IMPL_ERR → CodeCorrector.

**E-Domain:** Absent `SolverAPI_vX.py` → STOP (hard precondition). All SC-1–SC-4 must PASS.
On VERIFY PASS → signs `docs/interface/ResultPackage/`.

**A-Domain:** 0 FATAL + 0 MAJOR → PASS. AUDIT FAIL: PAPER_ERROR → PaperWriter; CODE_ERROR → CodeArchitect → TestRunner.

**P-Domain:** PromptArchitect is both Gatekeeper and EXECUTE agent (PromptAuditor = independent VERIFY).

**K-Domain:** K-COMPILE on any VALIDATED artifact; parallel / not blocking the main pipeline.
K-LINT mandatory pre-merge; broken pointer = STOP-HARD (K-A2). DEPRECATED entries trigger RE-VERIFY to consumers.

────────────────────────────────────────────────────────
## WARM_BOOT Fast-Path (SDP-01)

Triggered when a meta-file edit is detected that does NOT affect Axioms (A1–A11) or φ1–φ7.

```
[WARM_BOOT_TRIGGER]
  Condition: meta-file edit detected (non-Axiom change)
  =>
  Bootstrapper:       Structural Generate (Fast) — IDs + file paths + tag closure only
  ConsistencyAuditor: Audit Meta-Consistency (Heavy) — Axiom alignment + cross-ref integrity
  Gatekeeper:         Sign & Hot-Reload generated agents
```

**Rules:**
- WARM_BOOT requires: no φ1–φ7 / A1–A11 text diff (grep gate: count unchanged)
- If Axiom text IS modified → full COLD_START required (no fast-path)
- ConsistencyAuditor AUDIT-TASK token is emitted by Bootstrapper, not the user
- Hot-Reload = overwrite `prompts/agents-{env}/{AgentName}.md` for affected agents only

────────────────────────────────────────────────────────
## Bootstrap Pipeline (new feature only — run before Code Pipeline)

| Step | Agent | Output | Gate |
|------|-------|--------|------|
| 1: Formal Axiomatization | PaperWriter | docs/memo/ derivation entry | Logic self-consistent; no UI/framework mention |
| 2: Structural Contract | CodeArchitect | prompts/specs/ interface definition | Dependency unidirectional (A9) |
| 3: Headless Implementation | CodeArchitect | src/core/ module (stdlib only) | TestRunner PASS in CLI environment |
| 4: Shell Integration | CodeArchitect | src/system/ wrapper | ExperimentRunner sanity checks PASS |

Rules: Step 1 immutable once Step 2 begins; Step 3 must not reference Step 4 artifact;
CRITICAL_VIOLATION if Step 4 bypasses Step 2 contract to access Step 3 internals (A9).

────────────────────────────────────────────────────────
<meta_section id="STOP-RECOVER-MATRIX" version="5.1.0" axiom_refs="A8,phi4,phi4.1,phi5">
# § STOP-RECOVER MATRIX

<purpose>Workflow-level recovery pathway for every STOP condition. Answers WHO resolves and WHERE the pipeline resumes. Trigger definitions are SSoT in meta-ops.md §STOP CONDITIONS — this matrix does NOT redefine them.</purpose>
<authority>Consulted by the Coordinator that receives a STOPPED HAND-02. Specialist triggers the STOP; Coordinator consults this matrix; recovery agent dispatched.</authority>
<rules>
- MUST look up the STOP trigger here BEFORE issuing any recovery dispatch.
- MUST NOT redefine STOP-xx trigger semantics in this file — only the recovery recipe (who, action, resume point) lives here.
- For STOP-09/10/11 (v5.1 concurrency STOPs): trigger definitions and immediate response are in meta-ops.md §STOP CONDITIONS; this matrix only adds the workflow-level recovery recipe.
- MUST NOT auto-delete worktrees, locks, or files as part of recovery — human review required for all STOP-09/10 cases.
</rules>
<see_also>meta-ops.md §STOP CONDITIONS (trigger + immediate action SSoT), meta-ops.md §LOCK-ACQUIRE, meta-ops.md §LOCK-RELEASE, docs/locks/README.md</see_also>

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
| K-LINT broken pointer (K-A2) | STOP-HARD | WikiAuditor → TraceabilityManager | Fix or remove broken pointer; re-run K-LINT | VERIFY |
| SSoT violation (duplicate wiki entry) | STOP-SOFT | WikiAuditor → TraceabilityManager | K-REFACTOR to consolidate duplicates into pointers | EXECUTE |
| Source artifact invalidated after wiki compilation | STOP-HARD | WikiAuditor | K-DEPRECATE the wiki entry; trigger RE-VERIFY to consumers | PLAN |
| GPU/environment error | STOP-SOFT | User → DevOpsArchitect | Fix environment; re-run experiment | EXECUTE |

| HAND token malformed (missing required field) | STOP-SOFT | DiagnosticArchitect | Re-emit corrected HAND token (ERR-R3); Gatekeeper approves | PLAN |
| BUILD-FAIL — missing dependency or config error | STOP-SOFT | DiagnosticArchitect | Propose install/config fix (ERR-R2); Gatekeeper approves; retry | EXECUTE |
| Wrong write path caught before commit (pre-DOM-02) | STOP-SOFT | DiagnosticArchitect | Propose corrected path (ERR-R1); Gatekeeper approves; Specialist retries | EXECUTE |
| GIT conflict on non-logic file (.gitignore, config) | STOP-SOFT | DiagnosticArchitect | Propose merge resolution (ERR-R4); Gatekeeper approves | PRE-CHECK |
| STOP-09: base-directory destruction (v5.1) | STOP-HARD | User | Inspect the rogue worktree / write path; do NOT auto-delete (may contain real work). Verify `../wt/` convention violated. Manual worktree removal with rationale in `docs/02_ACTIVE_LEDGER.md §4`. | PRE-CHECK |
| STOP-10: foreign branch-lock force (v5.1) | STOP-HARD | User | Holding session_id vs. attempting session_id mismatch. Confirm lock ownership via `docs/02_ACTIVE_LEDGER.md §4` + `docs/locks/*.lock.json`. `LOCK-RELEASE --force` only after verifying holder session is actually crashed (see `docs/locks/README.md`). Never overwrite a live lock. | PRE-CHECK |
| STOP-11: atomic-push rebase conflict (v5.1) | STOP-SOFT | User (for conflict resolution) + Specialist (resumes) | `git rebase --abort` already run by the wrapper. Human resolves rebase against `origin/{base}` in the session's worktree. Specialist retains the branch lock during resolution (`lock_released: false` on HAND-02 FAIL). After user `git rebase --continue` + tests, Specialist re-runs GIT-ATOMIC-PUSH. | EXECUTE |

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
</meta_section>

────────────────────────────────────────────────────────
# § HANDOFF RULES

**Canonical handoff protocol:** meta-ops.md §HANDOFF PROTOCOL (HAND-01, HAND-02, HAND-03)

Every dispatch sends HAND-01; every completion returns HAND-02;
every receiver runs HAND-03 (Acceptance Check) before starting work.

**Definition of Done — Main-Merge Rule:**
A task is NOT considered finished until merged into `main` via GIT-04 Phase B.
Cross-domain handoffs only permitted after source domain's work is merged into `main`.

```
Cross-Domain Handoff Pre-check (receiving Gatekeeper):
  □ Verify source branch merged to main (GIT-04 Phase B commit in main history)
    Not found → REJECT; source domain not Done; return status: REJECT
  □ Run PRE-CHECK for new domain (GIT-01 + DOM-01)
  □ Run IF-AGREE for new task (GIT-00; write IF-AGREEMENT before dispatching Specialist)
```

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

**HAND-02-CL:** Appended to every HAND-02 RETURN. Agent declares: (1) all task-relevant state serialized to external files; (2) `produced` field is COMPLETE enumeration of artifacts left behind; (3) internal context LIQUIDATED.

**Fresh Context:** Every HAND-01 dispatch SHOULD start a new session loading ONLY: the DISPATCH token, artifacts in `inputs`, and the agent's SCOPE files.

**Hard rule:** Consuming upstream agent's conversation history instead of artifacts = Context Leakage Violation (CONTAMINATION); Gatekeeper must REJECT and re-dispatch.

────────────────────────────────────────────────────────
# § CONTROL PROTOCOLS

## Layer Integrity

**P1: LAYER_STASIS_PROTOCOL** — prevent cross-layer corruption (← φ7)
- Content edit → Tags READ-ONLY; Tag edit → Content READ-ONLY; Structure edit → no content rewrite
- Violation → immediate STOP

**P2: NON_INTERFERENCE_AUDIT** — protect solver purity (← φ3, A5)
- Infrastructure changes must not alter numerical results (verify bit-level or tolerance-bounded equality)
- Failure → block MERGE → route to CodeReviewer

**P5: SINGLE-ACTION DISCIPLINE** (← φ2) — one agent per step; one objective per prompt; minimal scope

## Error Handling

**P6: BOUNDED LOOP CONTROL** (← φ5) — MAX_REVIEW_ROUNDS = 5; threshold breach → escalate to user

**P9: THEORY_ERR / IMPL_ERR CLASSIFICATION** — mandatory before any fix (← φ1, φ7)
- THEORY_ERR: root cause in solver logic or paper equation → fix paper/ or docs/memo/ first
- IMPL_ERR: root cause in infrastructure → fix there only
- Uncertain → treat as THEORY_ERR; verify with ConsistencyAuditor

## Knowledge Management

**P3: ASSUMPTION_TO_CONSTRAINT_PROMOTION** (← φ1) — detect stable assumptions → promote to constraints
with ASM-ID; inject into future prompts and reviews

**P4: CONTEXT_COMPRESSION_GATE** — triggered before DONE, schema migration, prompt regeneration;
compress 02_ACTIVE_LEDGER.md §B LESSONS; promote stable rules to CORE AXIOMS

**P7: LEGACY MIGRATION** — detect old prompts/schemas → map to current; record migration notes

## Meta-Governance

**Meta-as-master rule → meta-core.md A10**: `prompts/meta/` is the single source of truth.

────────────────────────────────────────────────────────
# § AUDIT GATE → meta-ops.md AUDIT-01

AU2 gate (10-item release checklist, ConsistencyAuditor): **meta-ops.md AUDIT-01**.
AUDIT phase in each domain pipeline invokes AUDIT-01 before any merge to `main`.

────────────────────────────────────────────────────────
# § POST-EXECUTION FEEDBACK LOOP

Every agent issuing HAND-02 SHOULD append a lightweight **POST_EXECUTION_REPORT** block.

## POST_EXECUTION_REPORT Format

```yaml
POST_EXECUTION_REPORT:
  friction_points:         # [MANDATORY] steps that caused unnecessary overhead
    - "{rule/protocol ID}: {description}"
  uncovered_scenarios:     # [MANDATORY] situations no rule addressed
    - "{description}"
  rules_useful:            # rules that actively prevented an error
    - "{rule ID}: {how it helped}"
  anti_patterns_triggered: # AP-xx patterns detected and avoided
    - "{AP-xx}: {what would have happened}"
  isolation_level_used:    # actual level (L0/L1/L2/L3) + was it sufficient?
    level: "L1"
    sufficient: true
```

**Rules:** Token budget ≤ 150 tokens total. Report friction even when it reflects poorly on the system.
Do not propose meta-level fixes — report observations only.

## Aggregation

At session end, coordinators write a **SESSION_FEEDBACK** entry (queued in `artifacts/temp_work_log.json`
until batch-flushed to `docs/02_ACTIVE_LEDGER.md §FEEDBACK` at HAND-02 receipt):

```
SESSION_FEEDBACK:
  date: {ISO 8601}  domain: {T|L|E|A|P}  pipeline_mode: {TRIVIAL|FAST-TRACK|FULL-PIPELINE}
  agents_invoked: [...]  top_friction: "..."  uncovered_gaps: [...]  anti_patterns_caught: [...]
```

ResearchArchitect reads §FEEDBACK on session start. After every 10 SESSION_FEEDBACK entries,
a human operator or PromptArchitect evaluates whether meta-*.md updates are warranted.

────────────────────────────────────────────────────────
# § META-EVOLUTION POLICY

**Cycle:** Observe → Evaluate → Generalize → Promote → Validate → Compress

**M1: Knowledge Promotion** — On ConsistencyAuditor PASS: extract reusable patterns; stage in
`artifacts/temp_work_log.json` until batch-flush. Promote to meta-core.md §AXIOMS only if
system-wide, axiom-compatible, and brief (A1).

**M2: Self-Healing** — Apply P9 before any fix.
- THEORY_ERR → update docs/memo/ or paper first, then re-derive implementation
- IMPL_ERR → patch src/system/ only; never touch solver core (src/core/)
Stage findings in temp_work_log until batch-flush.

**M3: Knowledge Compilation** — On any domain reaching VALIDATED: KnowledgeArchitect evaluates
whether artifact introduces reusable knowledge; if yes, K-COMPILE produces wiki entry.
WikiAuditor verifies pointer integrity and SSoT compliance before publishing.
K-Domain does not block the main pipeline.

**Deprecate** if: obsolete, redundant, subsumed, conflicting, or over-specific.
**Promote** only if: repeated usefulness, structural generality, axiom-compatible, short formulation.
**Never promote** if: increases ambiguity, breaks solver purity, mixes layers, or weakens reproducibility.
If uncertain: stage in temp_work_log.

────────────────────────────────────────────────────────
## § META-EVOLUTION GUARDRAILS

Any self-evolution proposal modifying the **Immutable Zones** = **System Panic**:

**Immutable Zone 1:** φ1–φ7 (meta-core.md §DESIGN PHILOSOPHY) + A1–A11 (meta-core.md §AXIOMS)
**Immutable Zone 2:** HAND-03 Acceptance Check items (checks 1–6) in meta-ops.md §HANDOFF PROTOCOL
**Immutable Zone 3:** `main` branch protection — never committed by non-Root-Admin (A8)

**SYSTEM_PANIC format:** `triggered by: {agent}; reason: "Immutable Zone modification: {zone} — {element}"; action: STOP; required: escalate to user; resume: only after explicit authorization.`
Main Branch variant: add `evidence: git log --oneline -1 main` + revert confirmation before resume.

**Corollary:** "Refining" an axiom without removing it is still a modification. Route all Immutable Zone proposals to user before any edit.

**Permitted evolution paths (outside Immutable Zones):**
- Adding new axioms (A11+), control protocols (P-new), or operations (NEW-xx) — user-authorized
- Modifying Layer 3 (meta-workflow.md) within bounds of Layer 1+2
- Modifying Layer 2 (meta-roles.md, meta-ops.md) operations — not touching HAND-03 or AUTH_LEVEL

────────────────────────────────────────────────────────
# § COMMAND FORMAT → meta-ops.md §COMMAND FORMAT

Canonical command syntax and invocation rules: **meta-ops.md §COMMAND FORMAT**.
