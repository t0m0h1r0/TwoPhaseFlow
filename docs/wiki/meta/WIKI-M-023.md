# WIKI-M-023: Meta-System v6.0.0 Design Specification (Adaptive/Consensus-Aware)
**Category:** Meta | **Created:** 2026-04-18 | **Status:** DESIGN — not yet applied to prompts/meta/
**Source:** MetaEvolutionArchitect evolution directive (v5.1.0 → v6.0.0)

This entry captures the complete design specification for v6.0.0. It is knowledge-only:
no `prompts/meta/` files have been modified yet. Application requires a CHK-tracked
MetaEvolutionArchitect session (Stage 1b immutable body-diff gate will trigger on SCHEMA-IN-CODE changes).

---

## Gap Analysis: v5.1.0 Limitations vs. Latest Research

| ID | Gap | Current State | Research Reference |
|----|-----|--------------|-------------------|
| G-1 | Gate Paralysis (AP-04 + over-escalation) | Gatekeeper REJECT → immediate STOP-HARD → human escalation | Multi-Agent Debate, Reflexion self-repair |
| G-2 | Rigid Planning | TaskPlanner creates static DAG at session start; no mid-execution revision | Dynamic Replanning / Plan-and-Solve-with-Replanning |
| G-3 | Passive AP-09 mitigation | 5-turn rule-reload recommendation only | MemGPT working-memory self-summarization (Context Condensation) |
| G-4 | Binary gate dependence | AU2 = static Yes/No checklist | LLM-as-a-Judge / Evaluator-Optimizer Loop, rubric scoring |

---

## Design Rationale: Coexistence with the Immutable Zone

The Immutable Zone contains: φ1–φ7, A1–A11, HAND-03 7-check logic, SCHEMA-IN-CODE TypeScript interfaces.

The 4 new mechanisms are compatible with the Immutable Zone as follows:

| Mechanism | Immutable Zone interaction | Compatibility |
|-----------|--------------------------|---------------|
| PROTO-DEBATE (HAND-04) | Extends `hand_type` union in SCHEMA-IN-CODE; does NOT touch HAND-03 logic | Additive extension; requires constitutional PR (CHK-tracked); HAND-03 acceptance check still runs first |
| DYNAMIC-REPLANNING | Adds `BLOCKED_REPLAN_REQUIRED` to `Hand02Payload.status` enum | Additive extension to SCHEMA-IN-CODE; non-breaking for receivers that pattern-match on known values |
| CONTEXT-CONDENSATION (OP-CONDENSE) | New operation in meta-ops.md §KNOWLEDGE OPERATIONS tier; touches no immutable sections | Fully additive; aligns with φ4 (Stateless Agents) and LA-3 (State Tracking Limitation) |
| EVALUATOR-OPTIMIZER LOOP (Rubric) | Adds `rubric_scores` to optional `detail` field of HAND-02; AU2 checklist preserved | Backward-compatible: HAND-02 `detail` is already optional; binary gate is augmented, not replaced |

**φ-principle alignment check:**

- φ1 Truth Before Action: PROTO-DEBATE requires evidence (`evidence[]` paths) — not assertions.
- φ2 Minimal Footprint: DYNAMIC-REPLANNING triggers ONLY on Specialist-signaled `BLOCKED_REPLAN_REQUIRED` — not on every step.
- φ5 Bounded Autonomy: PROTO-DEBATE max 2 rounds; EVALUATOR-OPTIMIZER max 3 improvement loops — hard limits.
- φ7 Classification Precedes Action: Gatekeeper RETAINS final verdict in PROTO-DEBATE; Evaluator SCORES before acting — both are classification before action.
- φ4 Stateless Agents: OP-CONDENSE externalizes the compressed state snapshot — strengthens, not weakens, φ4.
- φ6 Single Source: all new rules live in prompts/meta/ source files; agent files are regenerated.

**A8.1 / concurrency impact:** All 4 mechanisms are compatible with the worktree concurrency model. HAND-04 DEBATE tokens carry `session_id` and `branch_lock_acquired` like all other envelopes.

---

## Mechanism 1: PROTO-DEBATE Protocol

**Target files:** `meta-workflow.md`, `meta-ops.md`
**New elements:** HAND-04 DEBATE token, `DEBATE-RESULT` verdict, debate loop rules
**Immutable Zone delta:** Extend `HandoffEnvelope.hand_type` union + add `Hand04Payload` interface to SCHEMA-IN-CODE

### Design

When a Gatekeeper issues HAND-02 `status: REJECT`, the Specialist MAY (not MUST) issue one HAND-04 DEBATE token with evidence-based counter-argument. The Gatekeeper issues a binding `DEBATE-RESULT` verdict (SUSTAIN / OVERRULE). Maximum 2 debate rounds. Final verdict authority always remains with the Gatekeeper or ConsistencyAuditor (Broken Symmetry preserved).

```
Normal flow:                     With PROTO-DEBATE:
Specialist → HAND-02 REJECT      Specialist → HAND-02 REJECT
   ↓                                ↓
Coordinator → STOP/escalate      Specialist → HAND-04 DEBATE (round 1, evidence[])
                                     ↓
                                  Gatekeeper → DEBATE-RESULT SUSTAIN or OVERRULE
                                     ↓ (if SUSTAIN AND round < 2)
                                  Specialist → HAND-04 DEBATE (round 2, NEW evidence[])
                                     ↓
                                  Gatekeeper → DEBATE-RESULT final (binding)
                                     ↓ (if SUSTAIN after 2 rounds)
                                  Coordinator → escalate to ConsistencyAuditor or user
```

### Patch: `meta-ops.md` — HAND-04 token spec

```xml
<meta_section id="HAND-04" version="6.0.0" axiom_refs="A4,A6,phi5,phi7">
## HAND-04: DEBATE Token (v6.0.0)

<purpose>PROTO-DEBATE — Specialist challenges a REJECT verdict with evidence before human escalation.
Preserves Broken Symmetry: Gatekeeper retains final DEBATE-RESULT authority. Max 2 rounds.</purpose>
<authority>Sender: Specialist who received HAND-02 status:REJECT. Receiver: the Gatekeeper that issued the REJECT.
ONLY valid after HAND-02 status:REJECT. NOT a substitute for CoVe or HAND-03.</authority>

Sent by: Specialist (max 2 times per REJECT chain)
Received by: the Gatekeeper that issued the REJECT

```
DEBATE → {gatekeeper}
  debate_id:             {uuid v4 — new per debate chain}
  round:                 {1 | 2}
  original_reject_hash:  {verification_hash of the triggering HAND-02}
  rebuttal:              {one-paragraph evidence-based counter-argument}
  evidence:              [{file_paths proving the counter-argument}]
  session_id:            {UUID v4}
  branch_lock_acquired:  {true|false}
  verification_hash:     {sha256 hex}
  timestamp:             {ISO 8601 UTC}
```

DEBATE-RESULT format (Gatekeeper's response — emitted as HAND-02 RETURN with extended debate_result field):
```
RETURN → {specialist}
  status:          REJECT (SUSTAIN) | SUCCESS (OVERRULE)
  debate_result:   SUSTAIN | OVERRULE
  debate_rationale: {one paragraph — must cite specific evidence evaluated}
  produced:        [{file_paths}] | none
  issues:          [{remaining blockers}] | none
  round_closed:    {1 | 2}
  session_id:      {UUID v4}
  ...
```

<rules>
- MUST provide non-empty `evidence[]` (at minimum 1 file path). Evidence-free rebuttal = auto-SUSTAIN (AP-12).
- MUST NOT introduce new evidence that was not in the agent's write_territory (DOM-02 still applies).
- MUST NOT be used as a delay tactic: `evidence[]` in round 2 MUST differ from round 1 (new paths).
- MUST limit debate chain to 2 rounds maximum. After round 2 SUSTAIN → mandatory ConsistencyAuditor or user escalation.
- Gatekeeper MUST issue DEBATE-RESULT within the same session. No deferral.
- MUST NOT bypass HAND-03 acceptance check — HAND-03 still runs on HAND-04 receipt.
- Gatekeeper DEBATE-RESULT is binding. Specialist MUST NOT issue further HAND-04 after SUSTAIN on round 2.
</rules>
<stop_conditions>STOP-07 (round > 2), STOP-02 (debate about immutable zone content)</stop_conditions>
<see_also>§HAND-02, §HAND-03, meta-workflow.md §PROTO-DEBATE RULES, meta-antipatterns.md §AP-12</see_also>
</meta_section>
```

### Patch: `meta-workflow.md` — PROTO-DEBATE rules in P-E-V-A

```xml
<meta_section id="PROTO-DEBATE" version="6.0.0" axiom_refs="phi5,phi7,A4,A6">
## § PROTO-DEBATE RULES (v6.0.0 addition to P-E-V-A)

<purpose>Reduce STOP-HARD escalations when a REJECT stems from evidence gap, not from an
actual error. Max 2 rounds preserve φ5 Bounded Autonomy. Gatekeeper retains final authority (φ7).</purpose>

### When PROTO-DEBATE MAY be initiated

A Specialist MAY initiate PROTO-DEBATE ONLY when:
1. HAND-02 status = REJECT was received
2. The rejection cites a verifiable factual claim (not a policy violation, not an Immutable Zone issue)
3. The Specialist has file-path evidence NOT included in the original DISPATCH inputs (new evidence)

A Specialist MUST NOT initiate PROTO-DEBATE when:
- REJECT is based on HAND-03 failure (structural/schema problem — fix and resubmit)
- REJECT is based on STOP-02 Immutable Zone violation
- REJECT is based on DOM-02 territory violation
- The Specialist has no new evidence beyond what was in the original DISPATCH

### Debate Loop Anti-deadlock Rules

| Rule | Description |
|------|-------------|
| DB-1 | Max 2 rounds per REJECT chain. Round counter resets on a new DISPATCH. |
| DB-2 | Round 2 `evidence[]` MUST contain at least 1 new path not in round 1. |
| DB-3 | After 2× SUSTAIN: Coordinator escalates to ConsistencyAuditor (not user directly). ConsistencyAuditor issues binding ruling; no further HAND-04 in this chain. |
| DB-4 | After ConsistencyAuditor SUSTAIN: Coordinator escalates to user. Final. |
| DB-5 | DEBATE-RESULT OVERRULE by Gatekeeper requires a rationale explaining why the new evidence changes the verdict. Generic "evidence accepted" is invalid. |
| DB-6 | HAND-04 DEBATE tokens are logged in ACTIVE_LEDGER §DEBATE_LOG (append-only) for auditability. |

### DEBATE-RESULT → STOP-RECOVER integration

| Outcome | Coordinator action |
|---------|-------------------|
| OVERRULE (SUCCESS) | Pipeline continues at VERIFY phase. Original REJECT is superseded. |
| SUSTAIN (round 1) | Specialist may issue HAND-04 round 2 with NEW evidence, or abandon. |
| SUSTAIN (round 2) | MANDATORY ConsistencyAuditor escalation. No further HAND-04. |
| ConsistencyAuditor SUSTAIN | MANDATORY user escalation. FINAL. |
</meta_section>
```

### Schema extension: `meta-roles.md §SCHEMA-IN-CODE`

```typescript
// Extend hand_type union (constitutional change — requires CHK-tracked session):
interface HandoffEnvelope {
  hand_type: "HAND-01" | "HAND-02" | "HAND-03" | "HAND-04";  // v6.0.0: added HAND-04
  // ... existing fields unchanged
}

// New payload type for HAND-04:
interface Hand04Payload {
  debate_id:             string;    // UUID v4 — new per debate chain
  round:                 1 | 2;     // never exceeds 2 (DB-1)
  original_reject_hash:  string;    // verification_hash of triggering HAND-02 REJECT
  rebuttal:              string;    // one-paragraph evidence-based counter-argument
  evidence:              string[];  // file paths; must be non-empty (AP-12 guard)
}

// Extend Hand02Payload for DEBATE-RESULT:
interface Hand02Payload {
  status: "SUCCESS" | "FAIL" | "REJECT" | "BLOCKED_REPLAN_REQUIRED";  // v6.0.0: added BLOCKED_REPLAN_REQUIRED
  debate_result?:    "SUSTAIN" | "OVERRULE";  // present when this is a DEBATE-RESULT response
  debate_rationale?: string;  // required when debate_result is present
  round_closed?:     1 | 2;   // which debate round this closes
  replan_scope?:     string;  // present when status == BLOCKED_REPLAN_REQUIRED
  // ... existing fields unchanged
}
```

---

## Mechanism 2: DYNAMIC-REPLANNING

**Target files:** `meta-roles.md`, `meta-workflow.md`
**New elements:** `BLOCKED_REPLAN_REQUIRED` status, TaskPlanner replan authority, REPLAN-TASK token
**Immutable Zone delta:** Add `BLOCKED_REPLAN_REQUIRED` to `Hand02Payload.status` enum in SCHEMA-IN-CODE

### Design

When a Specialist hits an insurmountable mid-execution blocker (not an error — a dependency or scope change that makes the original plan invalid), they return `HAND-02 status: BLOCKED_REPLAN_REQUIRED` instead of FAIL. The Coordinator routes this to TaskPlanner, who revises the `02_ACTIVE_LEDGER.md` plan and reissues HAND-01 with the revised scope.

```
Normal FAIL flow:               DYNAMIC-REPLANNING flow:
Specialist → HAND-02 FAIL      Specialist → HAND-02 BLOCKED_REPLAN_REQUIRED
  ↓                                replan_scope: "upstream contract changed"
Review + retry                     ↓
                                Coordinator → routes to TaskPlanner (REPLAN-TASK)
                                   ↓
                                TaskPlanner → revises ACTIVE_LEDGER plan
                                → new HAND-01 to Specialist (revised task)
                                   ↓
                                Specialist → resumes at EXECUTE
```

### Patch: `meta-workflow.md` — DYNAMIC-REPLANNING section

```xml
<meta_section id="DYNAMIC-REPLANNING" version="6.0.0" axiom_refs="phi2,phi4,phi5,A2,A8">
## § DYNAMIC-REPLANNING (v6.0.0)

<purpose>Allow mid-execution plan revision when a Specialist hits a structural blocker
that makes the original plan invalid — not an error, but a dependency change or scope shift.
Preserves φ2 (Minimal Footprint): triggered only on explicit Specialist signal, not on every FAIL.</purpose>

### Trigger Conditions

`BLOCKED_REPLAN_REQUIRED` is appropriate ONLY when:
1. The Specialist's `dev/` branch task is still valid, but the PLAN is now incorrect due to:
   - An upstream Interface Contract changed mid-execution
   - A PATCH-IF was applied that alters the Specialist's inputs
   - A dependency task was cancelled or its output format changed
2. The Specialist has no path to SUCCESS without a revised plan
3. The issue is NOT within the Specialist's authority to fix directly

`BLOCKED_REPLAN_REQUIRED` is NOT appropriate for:
- Normal FAIL (fixable with a code or paper change) → use HAND-02 `status: FAIL`
- Scope creep opportunity → reject per φ2 (Minimal Footprint)
- Ambiguous requirements → use STOP with clarification request

### REPLAN-TASK Flow

1. **Specialist** → HAND-02 `status: BLOCKED_REPLAN_REQUIRED, replan_scope: "{why plan is invalid}"`
2. **Coordinator** → identifies replan scope; issues REPLAN-TASK to TaskPlanner:
   ```
   REPLAN-TASK:
     original_chk:     {CHK-id of the blocked plan}
     blocked_agent:    {agent name}
     blocked_branch:   {dev/ branch}
     replan_reason:    {copied from HAND-02 replan_scope}
     ledger_section:   {ACTIVE_LEDGER section to revise}
   ```
3. **TaskPlanner** → reads ACTIVE_LEDGER, revises plan, writes updated task spec to ACTIVE_LEDGER (append-only: adds REPLAN entry with rationale + timestamp)
4. **TaskPlanner** → HAND-02 SUCCESS with `produced: ["docs/02_ACTIVE_LEDGER.md §{section}"]`
5. **Coordinator** → issues new HAND-01 to Specialist with revised task scope

### Anti-runaway Rules

| Rule | Description |
|------|-------------|
| RP-1 | Max 2 REPLAN cycles per CHK. Third BLOCKED_REPLAN_REQUIRED → STOP; escalate to user. |
| RP-2 | Each REPLAN requires a written rationale in ACTIVE_LEDGER (A2 External Memory). |
| RP-3 | TaskPlanner MUST NOT expand scope during REPLAN — revision is strictly narrowing or re-routing. |
| RP-4 | Lock status during REPLAN: Specialist retains branch lock (`lock_released: false` on BLOCKED_REPLAN_REQUIRED). |
| RP-5 | REPLAN does NOT restart the git lifecycle (branch remains; DRAFT commits preserved). |
</meta_section>
```

### Patch: `meta-roles.md` — TaskPlanner REPLAN authority

```xml
<meta_section id="TASKPLANNER-REPLAN" version="6.0.0" axiom_refs="phi2,phi4,A2,A8">
## TaskPlanner: Dynamic Replan Authority (v6.0.0 extension)

<purpose>Extends TaskPlanner's authority to revise ACTIVE_LEDGER plans in response to
BLOCKED_REPLAN_REQUIRED signals. Original static planning authority is unchanged.</purpose>

**Additional authority (v6.0.0):**
- MAY write to `docs/02_ACTIVE_LEDGER.md §ACTIVE_PLAN` on receipt of REPLAN-TASK token
- MUST append a `REPLAN-{N}` entry with rationale, timestamp, and diff from original plan
- MUST NOT: expand scope, change Gatekeeper assignments, alter branch ownership

**REPLAN output format (appended to ACTIVE_LEDGER):**
```
REPLAN-{N}:
  chk_id:       {original CHK-id}
  triggered_by: {HAND-02 verification_hash of the BLOCKED_REPLAN_REQUIRED}
  reason:       {copied from replan_scope}
  plan_delta:   {describe what changed: removed task X, rerouted Y, narrowed scope of Z}
  timestamp:    {ISO 8601 UTC}
  signed_by:    TaskPlanner
```
</meta_section>
```

---

## Mechanism 3: CONTEXT-CONDENSATION (OP-CONDENSE)

**Target files:** `meta-ops.md`, `meta-antipatterns.md`
**New elements:** OP-CONDENSE operation, `artifacts/temp_work_log.json` condensation format
**Immutable Zone delta:** None — fully additive new operation

### Design

Long-running sessions accumulate context that degrades LLM performance (AP-09). OP-CONDENSE allows an agent to create a compressed snapshot of its working state, then restart with the condensed state as the new context (L1 or L3 isolation restart). This aligns with φ4 (Stateless Agents) and LA-3 (State Tracking Limitation).

### Patch: `meta-ops.md` — OP-CONDENSE operation

```xml
<meta_section id="OP-CONDENSE" version="6.0.0" axiom_refs="phi4,phi4.1,A2,LA-3,LA-5">
## OP-CONDENSE: Context Condensation Protocol (v6.0.0)

<purpose>Active mitigation of AP-09 Context Collapse. Agent creates a compressed working-state
snapshot and optionally restarts session context with the snapshot as the new input.
Aligns with φ4 (Stateless Agents): compressed state is externalized, not in-context.</purpose>
<authority>Any agent experiencing context saturation (LA-2 threshold approaching) OR on Coordinator request.
No Gatekeeper approval needed — agent self-executes. Coordinator is notified but does not gate.</authority>

**Trigger conditions:**
- Agent estimates own context window is approaching 60% threshold (LA-2)
- Session exceeds 30 agent turns since last condensation or session start
- Coordinator issues `CONDENSE_REQUEST` in HAND-01 `constraints[]`

**OP-CONDENSE procedure:**

```
STEP 1 — Snapshot current working state to artifacts/temp_work_log.json:

{
  "condense_timestamp": "{ISO 8601 UTC}",
  "session_id": "{UUID v4}",
  "branch": "{current branch}",
  "chk_id": "{current CHK-id}",
  "goal": "{one-sentence objective from current HAND-01}",
  "completed_steps": ["{step 1 result}", "{step 2 result}", ...],
  "pending_decisions": ["{unresolved question}"],
  "key_findings": ["{critical finding that must survive context restart}"],
  "artifacts_produced": ["{file_path}"],
  "stop_conditions_active": ["{any triggered STOP-SOFT or pending actions}"]
}

STEP 2 — Signal condensation in HAND-02 detail or inline note:
  "OP-CONDENSE executed: {N} steps condensed → artifacts/temp_work_log.json"

STEP 3 (Optional — if L1/L3 restart needed):
  L1 restart: new prompt injection with snapshot as initial context, same session
  L3 restart: new Claude Code session invocation (Agent tool, isolation: worktree),
              snapshot path passed as first input in HAND-01

STEP 4 — Post-restart: agent reads snapshot FIRST before any other action (φ1)
  Do NOT rely on in-context recall of pre-condense state (LA-3)
```

**Snapshot exclusions (do NOT include):**
- Raw tool output text (too verbose; include only extracted findings)
- Intermediate reasoning chains (include only conclusions)
- Full file contents (include only paths and change-summary)

<rules>
- MUST write snapshot to `artifacts/temp_work_log.json` BEFORE clearing context.
- MUST include all `artifacts_produced` paths — these survive the restart.
- MUST NOT condense STOP conditions, immutable axiom references, or HAND-03 check results (always re-read from source).
- MUST notify Coordinator via inline note before L3 session restart (not after).
- SHOULD include `pending_decisions[]` to avoid re-deriving already-blocked decisions.
</rules>
<stop_conditions>STOP-03 (writing snapshot outside write_territory)</stop_conditions>
<see_also>§LA-3, §LA-5, meta-antipatterns.md §AP-09, meta-core.md §φ4</see_also>
</meta_section>
```

### Patch: `meta-antipatterns.md` — AP-09 mitigation update

```xml
<meta_section id="AP-09-MITIGATION" version="6.0.0" axiom_refs="phi4,LA-3">
## AP-09: Context Collapse — v6.0.0 Active Mitigation

<purpose>Update AP-09 mitigation from passive (5-turn reload recommendation) to active
(OP-CONDENSE protocol). Adds AP-12 (Debate Loop Inflation) as new anti-pattern.</purpose>

**Updated mitigation for AP-09 (v6.0.0):**

| Mitigation | Trigger | Action |
|-----------|---------|--------|
| Passive | Every 5 agent turns | Re-read STOP_CONDITIONS + DOMAIN_RULES (existing) |
| Active (v6.0.0) | Context window approaching 60% OR 30 turns | Execute OP-CONDENSE (meta-ops.md §OP-CONDENSE) |
| Restart (v6.0.0) | Post-condense if active context still > 60% | L1 or L3 isolation restart with snapshot as input |

**Detection signal for Active mitigation:** Agent self-estimate OR Coordinator inserts `CONDENSE_REQUEST` in HAND-01 `constraints[]`.
</meta_section>
```

---

## Mechanism 4: EVALUATOR-OPTIMIZER LOOP

**Target files:** `meta-roles.md`, `meta-workflow.md`
**New elements:** RUBRIC scoring schema, score-based loop continuation, `rubric_scores` in HAND-02 `detail`
**Immutable Zone delta:** None — augments HAND-02 optional `detail` field; AU2 binary gate is PRESERVED as a minimum bar

### Design

Binary PASS/FAIL gates are replaced with rubric-based scoring for iterative quality improvement.
The AU2 10-item checklist is PRESERVED as the minimum bar (all 10 must still pass);
the rubric adds gradient scoring on top. Score < threshold → improvement loop; score ≥ threshold → PASS.

### RUBRIC Schema

```yaml
RUBRIC:
  version: "6.0.0"
  total: 100
  pass_threshold: 80
  loop_max: 3          # max improvement iterations before escalating
  dimensions:
    - id: R1
      name: logical_correctness
      weight: 40
      criteria: "derivation/argument is logically valid from stated premises"
    - id: R2
      name: traceability
      weight: 25
      criteria: "A3 chain preserved: equation → discretization → code (or paper → code → experiment)"
    - id: R3
      name: scope_compliance
      weight: 20
      criteria: "output matches IF-AGREEMENT deliverable contract exactly"
    - id: R4
      name: format_compliance
      weight: 15
      criteria: "output format matches template requirements (AU2 items 2, 6, 9)"
```

**Scoring rules:**
- Each dimension scored 0–(weight) by the Auditor/Reviewer
- `total_score = sum(dimension_scores)`
- `total_score >= 80` → PASS (also requires all 10 AU2 items PASS — binary gate preserved)
- `40 <= total_score < 80` → CONDITIONAL_PASS with mandatory `improvement_targets[]`
- `total_score < 40` → REJECT (equivalent to current binary FAIL)

### Patch: `meta-workflow.md` — Evaluator-Optimizer loop

```xml
<meta_section id="EVALUATOR-OPTIMIZER" version="6.0.0" axiom_refs="phi1,phi5,phi7,A3,A6">
## § EVALUATOR-OPTIMIZER LOOP (v6.0.0)

<purpose>Replace binary Yes/No gates with gradient rubric scoring for iterative improvement.
AU2 binary gate (10 items) is PRESERVED as minimum bar — rubric scores only above this threshold.
Maintains φ5 Bounded Autonomy: loop_max = 3 prevents infinite improvement cycles.</purpose>

### Integration with P-E-V-A

In VERIFY and AUDIT phases, Reviewer/Auditor output now includes:

```
RUBRIC_RESULT:
  total_score:         {0-100}
  pass_threshold:      80
  dimensions:
    R1_logical_correctness: {0-40}  # with one-line rationale
    R2_traceability:        {0-25}
    R3_scope_compliance:    {0-20}
    R4_format_compliance:   {0-15}
  au2_items_passed:    {0-10}       # binary gate still required
  verdict:             PASS | CONDITIONAL_PASS | REJECT
  improvement_targets:             # populated when score < 80
    - "{specific dimension}: {what to improve}"
  loop_round:          {1 | 2 | 3}
```

### Rubric-P-E-V-A flow

```
VERIFY phase:
  Reviewer scores artifact with RUBRIC_RESULT
  → score ≥ 80 AND au2_items_passed = 10 → HAND-02 SUCCESS (REVIEWED commit)
  → 40 ≤ score < 80 → HAND-02 CONDITIONAL_PASS → EXECUTE (loop round N+1)
  → score < 40 → HAND-02 REJECT (standard flow)

LOOP counter:
  loop_round: 1 → improvement attempt 1 → re-VERIFY
  loop_round: 2 → improvement attempt 2 → re-VERIFY
  loop_round: 3 → improvement attempt 3 → re-VERIFY
  loop_round: 4 → escalate (STOP-07 equivalent; loop_max exceeded)
```

### Anti-grade-inflation rule

Reviewer MUST NOT increase any dimension score without citing the specific change that improved it.
Generic score inflation without rationale = AP-03 (Verification Theater) applied to rubric scoring.

### CONDITIONAL_PASS format in HAND-02

```
RETURN → {coordinator}
  status:   CONDITIONAL_PASS
  produced: [{artifact_paths}]
  rubric:
    total_score:        {N}
    improvement_targets: [{specific delta required}]
    loop_round:         {1|2|3}
  issues:   none
```

On CONDITIONAL_PASS: Coordinator issues HAND-01 back to Specialist with `constraints: ["improve: {improvement_targets}"]`. Specialist makes targeted edits and resubmits.
</meta_section>
```

### Patch: `meta-roles.md` — ConsistencyAuditor + PaperReviewer rubric authority

```xml
<meta_section id="RUBRIC-AUTHORITY" version="6.0.0" axiom_refs="phi7,A3,A6">
## Rubric Scoring Authority (v6.0.0 extension)

ConsistencyAuditor and PaperReviewer receive additional authority to:
- Score artifacts on R1–R4 dimensions (0–100 total)
- Issue CONDITIONAL_PASS (new verdict) when 40 ≤ score < 80 AND all AU2 items PASS
- Include `improvement_targets[]` with specific, actionable delta for the Specialist

**Hard constraints (unchanged):**
- AU2 10-item binary gate STILL REQUIRED — rubric scoring is ON TOP OF binary gate, not replacing it
- REJECT still valid when score < 40 (no rebuttals needed for < 40)
- PROTO-DEBATE (HAND-04) MAY be used by Specialist for a REJECT with score 35–39 (near threshold)
- CONDITIONAL_PASS with loop_round = 3 → next cycle is final: PASS or REJECT only (no 4th CONDITIONAL_PASS)
</meta_section>
```

---

## New Anti-Pattern: AP-12 Debate Loop Inflation

**Target file:** `meta-antipatterns.md`

```xml
<meta_section id="AP-12" version="6.0.0" axiom_refs="phi5,phi7,A4">
## AP-12: Debate Loop Inflation

**Severity:** HIGH
**Introduced:** v6.0.0 (companion to PROTO-DEBATE)
**Applicable roles:** Specialist (sender), Gatekeeper (receiver/detector)

**Pattern:**
Specialist uses HAND-04 DEBATE tokens as delay tactics — submitting near-identical rebuttals
with trivially modified or recycled evidence paths to defer a legitimate REJECT verdict.

**Detection signals:**
- HAND-04 round 2 `evidence[]` contains no new paths (all paths already in round 1)
- Rebuttal text is a minor rephrasing of round 1 with no new logical argument
- DEBATE chain has been used > 2 times in a single session on the same artifact

**Mitigation:**
- DB-2 (hard rule): round 2 MUST contain ≥1 new evidence path not in round 1
- Auto-SUSTAIN if DB-2 violated: Gatekeeper issues immediate DEBATE-RESULT SUSTAIN without reading rebuttal
- Pattern logged in `ACTIVE_LEDGER §DEBATE_LOG` for session audit
- Repeated AP-12 behavior (> 1 per session) → Coordinator flags to ConsistencyAuditor; agent profile reviewed

**Injection tier:** TIER-2 and TIER-3 for all Specialist roles
</meta_section>
```

---

## Implementation Roadmap (Suggested Sequence)

**Prerequisites:** CHK-tracked MetaEvolutionArchitect session; Stage 1b will trigger on SCHEMA-IN-CODE changes.

| Step | Action | Files Modified | Gate |
|------|--------|---------------|------|
| 1 | Add AP-12 anti-pattern | `meta-antipatterns.md` | No immutable zone change — low risk |
| 2 | Add OP-CONDENSE operation | `meta-ops.md` | No immutable zone change — low risk |
| 3 | Update AP-09 mitigation notes | `meta-antipatterns.md` | No immutable zone change |
| 4 | Add PROTO-DEBATE rules to workflow | `meta-workflow.md` | No immutable zone change |
| 5 | Add DYNAMIC-REPLANNING rules to workflow | `meta-workflow.md` | No immutable zone change |
| 6 | Add EVALUATOR-OPTIMIZER LOOP to workflow | `meta-workflow.md` | No immutable zone change |
| 7 | Add TaskPlanner REPLAN authority | `meta-roles.md` | No immutable zone change |
| 8 | Add Rubric authority to ConsistencyAuditor / PaperReviewer | `meta-roles.md` | No immutable zone change |
| 9 | **Extend SCHEMA-IN-CODE** (HAND-04, BLOCKED_REPLAN_REQUIRED) | `meta-roles.md` | **IMMUTABLE ZONE** — Stage 1b fires; constitutional PR required |
| 10 | Add HAND-04 DEBATE token operation | `meta-ops.md` | depends on Step 9 |
| 11 | Full EnvMetaBootstrapper regeneration (`meta_version: "6.0.0"`) | all `prompts/agents-{env}/*.md` | Stage 5 Q3 all 50 files |

**Steps 1–8** can be applied without touching the Immutable Zone.
**Step 9** requires a dedicated constitutional commit with explicit MetaEvolutionArchitect authorization and a CHK entry.
**Steps 10–11** follow atomically after Step 9 passes Stage 1b.

---

## v5.1.0 → v6.0.0 Feature Flag Summary

```yaml
# Additions to _base.yaml for v6.0.0:
meta_version: "6.0.0"

# New feature flags:
proto_debate:           "enabled"    # PROTO-DEBATE max 2 rounds
dynamic_replanning:     "enabled"    # BLOCKED_REPLAN_REQUIRED + REPLAN-TASK flow
context_condensation:   "enabled"    # OP-CONDENSE auto at 60% context
evaluator_optimizer:    "enabled"    # Rubric scoring in VERIFY + AUDIT

# Threshold configuration:
debate_max_rounds:      2
replan_max_cycles:      2
condense_threshold_pct: 60
condense_turn_threshold: 30
rubric_pass_threshold:  80
rubric_loop_max:        3
```

---

## Cross-References

- `→ WIKI-M-016`: Design philosophy synthesis (3 pillars that v6.0.0 extends, not replaces)
- `→ WIKI-M-017`: Constitutional layer (Immutable Zone boundaries this spec must respect)
- `→ WIKI-M-020`: Canonical operations (context for HAND-01/02/03 that HAND-04 extends)
- `→ WIKI-M-019`: Workflow protocols (P-E-V-A loop that EVALUATOR-OPTIMIZER and REPLANNING integrate into)
- `→ WIKI-M-011`: AP-01..AP-11 catalogue (AP-12 added by this spec)
- `→ WIKI-M-014`: EnvMetaBootstrapper (Stage 1b immutable gate that will fire on Step 9)
