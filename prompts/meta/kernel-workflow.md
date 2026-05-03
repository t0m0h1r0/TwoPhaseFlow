# kernel-workflow.md — Workflow Protocols v7.0.0
# Replaces: meta-workflow.md (42KB → ~22KB, -48%).
# P-E-V-A loop, T-L-E-A pipeline, STOP-RECOVER MATRIX, DYNAMIC-REPLANNING, CONTEXT-MANAGEMENT.
#
# Concrete phase/commit format: docs/00_GLOBAL_RULES.md §GIT, §P-E-V-A
# Operations SSoT: kernel-ops.md
# FOUNDATION: kernel-constitution.md §AXIOMS ← READ FIRST

<meta_section id="META-WORKFLOW" version="7.0.0" axiom_refs="A6,A8,phi4,phi5">
<purpose>Workflow logic: P-E-V-A loop, domain pipelines, handoff rules, v7.0.0 control protocols.</purpose>
<authority>PromptArchitect edits. ResearchArchitect consults when routing decisions needed.</authority>
</meta_section>

────────────────────────────────────────────────────────
# § P-E-V-A EXECUTION LOOP

Master execution frame for ALL domain work. No phase may be skipped.

| Phase | Responsibility | Agent | Output | Git phase |
|-------|---------------|-------|--------|-----------|
| PLAN | Define scope, success criteria, stop conditions | Coordinator | task scope | — |
| EXECUTE | Produce artifact + CoVe before HAND-02 | Specialist | code/patch/paper/prompt | DRAFT commit |
| VERIFY | Confirm artifact meets spec (independent) | TestRunner / PaperReviewer / PromptAuditor | PASS or FAIL | REVIEWED commit |
| AUDIT | Gate check; cross-system consistency | ConsistencyAuditor | AU2 gate verdict | VALIDATED commit + merge |

Rules:
- FAIL at VERIFY → return to EXECUTE (not to PLAN unless scope changes)
- FAIL at AUDIT → return to EXECUTE
- Loop counter per phase; MAX_REVIEW_ROUNDS = 5 (φ5)
- AUDIT agent MUST be independent of EXECUTE agent (φ7)
- PLAN always starts with ResearchArchitect loading docs/02_ACTIVE_LEDGER.md

**CoVe prerequisite:** Specialist runs CoVe IMMEDIATELY before HAND-02. See kernel-roles.md §COVE MANDATE.
Gatekeeper MUST reject HAND-02 where `detail` field is absent or lacks CoVe summary → return to EXECUTE.

────────────────────────────────────────────────────────
# § T-L-E-A PIPELINE — Master Cross-Domain Flow

Mandatory execution order. Each arrow = signed Interface Contract gate.

```
T (Theory) → L (Library) → E (Experiment) → A (Academic)
                                              ↕
                              K (Knowledge) — parallel, post-VALIDATED
```

**T→L→E→A ordering is mandatory.** No domain begins without upstream contract SIGNED.

### Domain Pipeline Table

| Domain | Branch | Gatekeeper | EXECUTE | VERIFY | Precondition |
|--------|--------|------------|---------|--------|--------------|
| T Theory | `theory` | TheoryAuditor | TheoryArchitect | TheoryAuditor (independent re-derivation) | none |
| L Code | `code` | CodeWorkflowCoordinator | CodeArchitect, CodeCorrector | TestRunner | AlgorithmSpecs.md signed |
| E Experiment | `experiment` | CodeWorkflowCoordinator | ExperimentRunner | Coordinator (Validation Guard SC-1..4) | SolverAPI_vX.py signed |
| A Paper | `paper` | PaperWorkflowCoordinator | PaperWriter | PaperCompiler + PaperReviewer | ResultPackage/ signed |
| P Prompt | `prompt` | PromptArchitect | PromptArchitect | PromptAuditor (Q3 checklist) | none |
| K Knowledge | `wiki` | WikiAuditor | KnowledgeArchitect | WikiAuditor (K-LINT + pointer) | any VALIDATED artifact |

AUDIT at all domains: ConsistencyAuditor AU2 gate.

### Common Pipeline Structure

```
PRE-CHECK  Gatekeeper → GIT-01 + DOM-01
IF-AGREE   Gatekeeper → GIT-00 (interface contract)
PLAN       Gatekeeper → dispatch Specialist
EXECUTE    Specialist → artifact on dev/ branch → PR: dev/ → {domain}
VERIFY     Verifier → PASS: Gatekeeper merges + opens PR → main
                    → FAIL: loop back to EXECUTE (bounded by MAX_REVIEW_ROUNDS)
AUDIT      ConsistencyAuditor → AU2 gate → PASS: Root Admin merges → main
                                          → FAIL: route to responsible agent
```

### Domain Notes

**T-Domain:** TheoryAuditor re-derives WITHOUT reading Specialist's work (Broken Symmetry). DISAGREE → STOP; escalate to user.

**L-Domain:** VERIFY FAIL routing: THEORY_ERR → CodeArchitect; IMPL_ERR → CodeCorrector.

**E-Domain:** Missing SolverAPI_vX.py → STOP (hard precondition). All SC-1–SC-4 must PASS.

**A-Domain:** 0 FATAL + 0 MAJOR → PASS. AUDIT FAIL: PAPER_ERROR → PaperWriter; CODE_ERROR → CodeArchitect.

**K-Domain:** K-COMPILE on any VALIDATED artifact (parallel, non-blocking). K-LINT pre-merge mandatory; broken pointer = STOP-HARD (K-A2).

────────────────────────────────────────────────────────
# § PIPELINE MODE

ResearchArchitect classifies every task before routing. When uncertain → one level higher (φ1).

| Condition | Mode |
|-----------|------|
| Touches `docs/memo/`, `docs/interface/`, or `src/core/`; new domain branch | FULL-PIPELINE |
| Whitespace, comment, typo, docs-only | TRIVIAL |
| All other (bug fix, paper prose, experiment re-run, config) | FAST-TRACK |

| Mode | Gatekeeper Protocol | Independent Re-derivation |
|------|---------------------|--------------------------|
| TRIVIAL | Lint + DOM-02 scope-check only | NONE |
| FAST-TRACK | Standard P-E-V-A; GA-2/3/5 | SUMMARY only |
| FULL-PIPELINE | Full AU2 gate + all GA | MANDATORY (GA-4) |

**TRIVIAL omits:** HAND-03, GIT-SP isolation, HAND-02, Gatekeeper PR review, IF-Agreement, AU2.
Commit format: `{branch}: trivial — {summary}`. Upgrade to FAST-TRACK if diff > 20 lines or logic change found.

**FAST-TRACK omits:** IF-Agreement (reuses existing), AU2, micro-agent decomposition.
Retains: GIT-SP, DOM-02, HAND-03 checks 1–4 and 6, TEST-PASS + LOG-ATTACHED.
Upgrade to FULL-PIPELINE if: fix requires `src/core/` or `docs/interface/`; theory inconsistency found.

## Agent Effort Policy (v8.0.0-candidate)

ResearchArchitect and TaskPlanner scale agent count to task complexity and independence, not to perceived importance.

```yaml
AGENT_EFFORT_POLICY:
  TRIVIAL:
    agents: 1
    max_tool_calls: 3
    no_subagents: true
  FAST_TRACK:
    agents: executor + verifier
    max_replan_cycles: 1
    audit: summary
  FULL_PIPELINE:
    agents: coordinator + specialist + independent auditor
    multi_agent_allowed_if:
      - independent_search_branches >= 2
      - write_territory_conflict == false
      - shared_context_dependency == low
  RESEARCH_BREADTH:
    agents: orchestrator + N subagents
    N_rule: scale by source breadth and uncertainty
    artifact_output_required: true
```

Coding, proof, and audit tasks with tight shared context prefer one executor plus an independent verifier.
Breadth-heavy research may use multiple agents only when outputs can be artifact-separated.

────────────────────────────────────────────────────────
# § PARALLEL EXECUTION — TaskPlanner Staged Dispatch

## Parallel Eligibility (PE)

| Rule | Description |
|------|-------------|
| PE-1 | Tasks with no `depends_on` edges MAY run in parallel |
| PE-2 | Tasks writing to SAME file/directory MUST NOT run in parallel |
| PE-3 | Same-domain tasks sharing same Gatekeeper MAY run in parallel on separate dev/ branches |
| PE-4 | Cross-domain tasks MUST respect T-L-E-A ordering |
| PE-5 | TRIVIAL-mode tasks MAY run in parallel with non-conflicting tasks |

## Barrier Sync (BS)

- **BS-1:** Stage N+1 does NOT begin until ALL Stage N tasks issue HAND-02 RETURN.
- **BS-2:** Any STOPPED/FAIL in a parallel stage → barrier PARTIAL; next stage BLOCKED.
- **BS-3:** User chooses: (a) fix + retry, (b) re-plan, (c) proceed with partial results.
- **BS-4:** Task >24h holding branch lock → STATUS_CHECK; stale → STOP-10.

## Resource Conflict (RC)

- RC-1/2/3: Collect `writes_to` per task; non-empty intersection → make SEQUENTIAL.
- RC-5: Under `concurrency_profile == "worktree"`: task whose branch appears in ACTIVE_LEDGER §4 under another session MUST NOT be dispatched.

**Plan Approval Gate:** TaskPlanner presents stage DAG to user before Stage 1. User approves before dispatch.

────────────────────────────────────────────────────────
# § CONCURRENCY EXTENSIONS (worktree profile only)

Applies when `_base.yaml :: concurrency_profile == "worktree"`. Under `legacy` profile: descriptive only.

**Node structure** (T/L/E/A nodes share this pattern):
- Pre: `LOCK(branch)` — collision with another session_id → STOP-10
- Body: node-specific work; P-E-V-A loop inside
- Post: `GIT-ATOMIC-PUSH` (inside lock) → `UNLOCK(branch)` after HAND-02 emitted

| Node | Forbidden writes | Success criterion |
|------|-----------------|-------------------|
| T | `src/`, `experiment/` (DOM-02) | TheoryAuditor re-derivation PASS + schema-valid HAND-02 |
| L | (standard DOM-02) | pytest PASS + convergence order ≥ target |
| E | (standard DOM-02) | SC-1..SC-4 all PASS |
| A | (standard DOM-02) | BUILD-02 PASS (writing) OR all AU2 items green (auditing) |

Nodes synchronize via `docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY` + `docs/locks/{branch_slug}.lock.json`.
Divergence between the two → STOP-10.

────────────────────────────────────────────────────────
# § CI/CP PIPELINE — Continuous Integration / Continuous Paper

| Change | Contracts invalidated |
|--------|----------------------|
| T-Domain equation | AlgorithmSpecs.md, SolverAPI_vX.py, ResultPackage/, TechnicalReport.md |
| L-Domain solver API | SolverAPI_vX.py, ResultPackage/, TechnicalReport.md |
| src/twophase/ hash | Same as above + paper/ figures tagged [STALE] |
| E-Domain results | ResultPackage/, TechnicalReport.md |
| A-Domain revision (no upstream) | none |

```
CHANGE-PROPAGATION:
  1. Triggering Gatekeeper issues INVALIDATION for affected interface contracts.
  2. Each downstream Gatekeeper BLOCKS new dev/ work until upstream contract re-signed.
  3. Upstream executes pipeline → re-signs Interface Contract.
  4. Downstream Gatekeeper verifies new contract → unblocks Specialists.
  5. ConsistencyAuditor AU2 gate after each re-signing.
```

Hard rule: Starting work on an invalidated contract = CONTAMINATION violation.

**[INTEGRITY_MANIFEST]** in `docs/02_ACTIVE_LEDGER.md`:
```
T_hash: {sha256 of AlgorithmSpecs.md at signing}
L_hash: {sha256 of SolverAPI_vX.py at signing}
E_hash: {sha256 of ResultPackage/ manifest at signing}
A_hash: {sha256 of final paper/sections/ commit at VALIDATED}
```
Hash mismatch → CONTAMINATION notice → STOP downstream → trigger CI/CP re-propagation.

────────────────────────────────────────────────────────
# § DYNAMIC-REPLANNING (v7.0.0)

Trigger: any agent returns `status: BLOCKED_REPLAN_REQUIRED` in HAND-02.

```
BLOCKED_REPLAN_REQUIRED → {coordinator}
  replan_context: {one-sentence: which assumption is invalid}
  stop_code:      STOP-06 (or other relevant code)
```

**Coordinator procedure:**
1. Read `replan_context` from HAND-02.
2. Identify invalidated plan steps or IF-AGREEMENT fields.
3a. IF recoverable within domain: issue revised HAND-01 with corrected task/constraints.
3b. IF fundamental (theory wrong, interface contract invalid): escalate to user + log in ACTIVE_LEDGER §REPLAN_LOG.
4. Log: `docs/02_ACTIVE_LEDGER.md §REPLAN_LOG` entry: `{date}: {task_id} replanned — {reason}`.

Limits: max 2 replan cycles per task. On 3rd trigger: mandatory user escalation (kernel-antipatterns.md §AP-12).

────────────────────────────────────────────────────────
# § PROTO-DEBATE (HAND-04, v7.0.0)

When two agents reach conflicting verdicts on a falsifiable hypothesis, Coordinator invokes HAND-04.

Procedure:
1. Coordinator identifies contested hypothesis (falsifiable, one sentence).
2. Instantiate two Specialist instances A and B with L2 isolation minimum.
3. Emit HAND-04 to both; set `round_limit` (default 3, max 5).
4. Each round: A asserts, B rebuts; arbiter (Coordinator) evaluates.
5. After `round_limit` rounds or early consensus:

| DebateResult.verdict | Action |
|---------------------|--------|
| CONSENSUS | Proceed with consensus result; log in ACTIVE_LEDGER |
| SPLIT | Escalate to ResearchArchitect via HAND-02 `stop_code: STOP-08` |
| ESCALATE | Pause pipeline; ResearchArchitect decides |

Schema SSoT: kernel-roles.md §SCHEMA-IN-CODE Hand04Payload, DebateResult.

────────────────────────────────────────────────────────
# § CONTEXT-MANAGEMENT (v7.0.0)

See kernel-ops.md §OP-CONDENSE for v7-compatible condensation and v8 adaptive fields.

**Condensation triggers:**
- Context utilization ≥ 60%
- Turn count ≥ 30

**Resumption after CONDENSE:**
1. Load CONDENSE-CHECKPOINT as sole context.
2. Run HAND-03() on any pending DISPATCH.
3. Resume from `next_action`.

**Long session protocol:** At each HAND-02 emission, agent appends artifact paths + sha256 prefix to checkpoint buffer. Coordinator requests CONDENSE when either trigger is breached.

**Adaptive compression (v8.0.0-candidate):**
- Prefer `CONDENSE-CHECKPOINT-V2` when long sessions include unresolved STOP/AP flags, multiple artifacts, or handoff chains.
- Include `immutable_constraints`, `state_delta`, `risk_flags`, and `lost_context_test`.
- If resumed work fails because condensation omitted required context, record `compression_failure_log` and update the next checkpoint guideline.
- Compression quality is evaluated by whether the resumed agent can answer `lost_context_test` without reopening the full transcript.

────────────────────────────────────────────────────────
# § WARM_BOOT Fast-Path (SDP-01)

Triggered when meta-file edit detected that does NOT affect A1–A11 or φ1–φ7 text.

```
[WARM_BOOT_TRIGGER]
  Condition: meta-file edit detected (non-Axiom change)
  =>
  Bootstrapper:       Structural Generate (Fast) — IDs + file paths + tag closure only
  ConsistencyAuditor: Audit Meta-Consistency (Heavy) — Axiom alignment + cross-ref integrity
  Gatekeeper:         Sign & Hot-Reload generated agents
```

Rules:
- WARM_BOOT requires: no φ1–φ7 / A1–A11 text diff (grep gate: count unchanged).
- If Axiom text IS modified → full COLD_START required.
- Hot-Reload = overwrite `prompts/agents-{env}/{AgentName}.md` for affected agents only.

────────────────────────────────────────────────────────
# § LEDGER UPDATE CADENCE

Specialists append to `artifacts/temp_work_log.json` (unstructured, append-only, session-local).
Gatekeeper batch-updates `docs/02_ACTIVE_LEDGER.md` at exactly two moments:
1. On HAND-02 receipt (any status)
2. On AU2 VALIDATED verdict at AUDIT phase

Between these: ledger is read-only. Any agent writing to ACTIVE_LEDGER mid-EXECUTE = Ledger-Thrash violation (STOP-SOFT).

────────────────────────────────────────────────────────
# § GATEKEEPER APPROVAL CONDITIONS (GA)

| Condition | Required for | Mode |
|-----------|-------------|------|
| GA-0: DOM-01 gate passed | all | FAST+FULL |
| GA-1: IF-AGREEMENT signed (GIT-00) | cross-domain dispatch | FULL |
| GA-2: TEST-PASS + LOG-ATTACHED | any code change | FAST+FULL |
| GA-3: Convergence table present | CCD operator changed | FAST+FULL |
| GA-4: Independent re-derivation PASS | theory/algo change | FULL |
| GA-5: No open STOP codes | any | FAST+FULL |
| GA-6: All upstream contracts SIGNED | merge to main | FULL |

All GA conditions MUST pass before Gatekeeper issues PASS on a PR.

────────────────────────────────────────────────────────
<meta_section id="STOP-RECOVER-MATRIX" version="7.0.0" axiom_refs="A8,phi4,phi4.1,phi5">
# § STOP-RECOVER MATRIX

<purpose>Workflow-level recovery for every STOP condition. WHO resolves and WHERE pipeline resumes.</purpose>
<rules>
- MUST look up trigger here BEFORE issuing recovery dispatch.
- MUST NOT redefine STOP-xx triggers (SSoT: kernel-ops.md §STOP CONDITIONS).
- MUST NOT auto-delete worktrees, locks, or files — human review required for STOP-09/10.
</rules>

| STOP trigger | Severity | Recovery agent | Action | Resume |
|-------------|----------|---------------|--------|--------|
| Axiom A1–A11 violated | HARD | User | Revert; cite axiom | PLAN |
| HAND-03 Immutable Zone bypassed | HARD | User → ResearchArchitect | Report + revert | PLAN |
| Branch lock not acquired before write | HARD | Coordinator | Acquire LOCK; retry | PLAN |
| Paper/equation ambiguity | HARD | User → PaperWriter/CodeArchitect | User clarifies; re-derive | EXECUTE |
| TestRunner FAIL | HARD | Coordinator → CodeCorrector | THEORY_ERR or IMPL_ERR fix | EXECUTE |
| AU2 FAIL — PAPER_ERROR | HARD | ConsistencyAuditor → PaperWriter | Cite item; fix | EXECUTE |
| AU2 FAIL — CODE_ERROR | HARD | ConsistencyAuditor → CodeArchitect | Re-implement from spec | EXECUTE |
| AU2 FAIL — THEORY_ERROR | HARD | ConsistencyAuditor → TheoryArchitect | Re-derive; TheoryAuditor re-verifies | EXECUTE (T) |
| Authority conflict (paper/code/theory) | HARD | User | Ruling + rationale in LEDGER; φ3 | PLAN |
| Merge conflict (GIT) | HARD | User | Manual resolution; re-run GIT-01 | PRE-CHECK |
| MAX_REVIEW_ROUNDS exceeded | HARD | User → Root Admin | Review loop history; scope decision | PLAN |
| Branch contamination (DOM-02) | HARD | User | Revert contaminated commit; clean GIT-SP | PRE-CHECK |
| Upstream contract invalidated (CI/CP) | HARD | CI/CP propagation | Re-sign upstream; cascade INVALIDATED | PLAN |
| Broken Symmetry (Auditor saw CoT) | HARD | Coordinator | Re-dispatch Auditor fresh session (L3) | VERIFY |
| BLOCKED_REPLAN_REQUIRED | — | Coordinator | §DYNAMIC-REPLANNING procedure | PLAN |
| DEBATE SPLIT (HAND-04) | SOFT | ResearchArchitect | Arbiter ruling; log in LEDGER | PLAN |
| Token budget exceeded | SOFT | Coordinator | §OP-CONDENSE or split task | EXECUTE |
| Missing input file | SOFT | Coordinator | Dispatch upstream agent to produce it | PLAN |
| PaperCompiler BUILD-FAIL | SOFT | PaperWorkflowCoordinator → PaperCompiler | Parse log; surgical fix | VERIFY |
| K-LINT broken pointer (K-A2) | HARD | WikiAuditor → TraceabilityManager | Fix pointer; re-run K-LINT | VERIFY |
| SSoT violation (duplicate wiki entry) | SOFT | WikiAuditor → TraceabilityManager | K-REFACTOR; consolidate | EXECUTE |
| GPU/environment error | SOFT | User → DevOpsArchitect | Fix env; re-run | EXECUTE |
| HAND token malformed | SOFT | DiagnosticArchitect | Re-emit corrected token (ERR-R3) | PLAN |
| BUILD-FAIL — missing dep/config | SOFT | DiagnosticArchitect | Install/config fix (ERR-R2); retry | EXECUTE |
| Wrong write path (pre-DOM-02) | SOFT | DiagnosticArchitect | Corrected path (ERR-R1); retry | EXECUTE |
| STOP-09: base-dir destruction | HARD | User | Inspect rogue worktree; manual removal with rationale in LEDGER §4 | PRE-CHECK |
| STOP-10: foreign lock force | HARD | User | Confirm ownership via LEDGER §4 + locks/*.lock.json; LOCK-RELEASE --force only after verifying holder crashed | PRE-CHECK |
| STOP-11: atomic-push rebase conflict | SOFT | User + Specialist | `git rebase --abort` already run; human resolves; Specialist retains lock; re-run GIT-ATOMIC-PUSH | EXECUTE |
| STOP-12: dual HAND emission | HARD | Coordinator | Fix to single emission mode; re-emit | PLAN |

**Recovery Protocol:** HARD stops require explicit user acknowledgment before resuming.
SOFT stops may resume autonomously after correction with Coordinator log entry.

────────────────────────────────────────────────────────
# § INTERFACE DRAFTING — Speculative Parallel Execution

TheoryArchitect MAY publish `docs/interface/{id}.draft` once core algorithm structure is known.
CodeArchitect MAY read `.draft` to build scaffolding in `artifacts/L/scaffold_{id}.py.draft` only.

Promotion gate: TheoryAuditor HAND-02 `interface_contracts_checked: [{id}.draft → SIGNED]` → Gatekeeper removes `.draft` suffix.
TheoryAuditor FAIL → all scaffold files MUST be deleted.

────────────────────────────────────────────────────────
# § BOOTSTRAP PIPELINE (new feature only, runs before Code Pipeline)

| Step | Agent | Output | Gate |
|------|-------|--------|------|
| 1: Formal Axiomatization | TheoryArchitect | docs/memo/ derivation entry | Logic self-consistent |
| 2: Structural Contract | CodeArchitect | docs/interface/ spec | Dependency unidirectional (A9) |
| 3: Headless Implementation | CodeArchitect | src/core/ module | TestRunner PASS in CLI |
| 4: Shell Integration | CodeArchitect | src/system/ wrapper | EXP-01 sanity checks PASS |

Step 1 immutable once Step 2 begins. Step 4 MUST NOT bypass Step 2 contract to access Step 3 internals (A9 violation).
