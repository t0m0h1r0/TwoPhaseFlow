# kernel-ops.md — Operations Reference v7.0.0
# Replaces: meta-ops.md (63KB → ~30KB, -52%).
# ALL operations, HAND protocols, STOP codes, shorthand syntax.
# Agent prompts reference operation IDs only (JIT rule: "consult kernel-ops.md §<ID>").
#
# Derived output: none (agents load this JIT via RULE_MANIFEST).
# FOUNDATION: kernel-constitution.md §AXIOMS ← READ FIRST

<meta_section id="META-OPS" version="7.0.0" axiom_refs="A1,A6,A8,phi4">
<purpose>Canonical reference for all operations. Agents embed operation IDs only; full syntax loaded JIT.</purpose>
<authority>PromptArchitect edits; no agent may improvise syntax — cite this file and ID instead.</authority>
<rules>
- MUST NOT embed full operation syntax in agent prompts (JIT rule).
- Agent prompt may include: operation ID, trigger condition, AUTH_LEVEL.
- Agent prompt MUST NOT include: full parameter blocks, success criteria tables, failure handling.
</rules>
</meta_section>

────────────────────────────────────────────────────────
# § SHORTHAND SYNTAX (v7.0.0)

These shorthands appear in agent prompts and HAND payloads. Full spec at indicated §ID.

| Shorthand | Expands to | §Ref |
|-----------|-----------|------|
| `LOCK(branch)` | LOCK-ACQUIRE on branch | §LOCK-ACQUIRE |
| `UNLOCK(branch)` | LOCK-RELEASE on branch | §LOCK-RELEASE |
| `HAND-01(agent,task)` | Emit DISPATCH token to agent | §HAND-01 |
| `HAND-02(status,paths)` | Emit RETURN token | §HAND-02 |
| `HAND-03()` | Run 7-check Acceptance | §HAND-03 |
| `HAND-04(topic,A,B)` | Request PROTO-DEBATE between A and B on topic | §HAND-04 |
| `GIT-SP(msg)` | git add -A && git commit -m msg && git push | §GIT-SP |
| `GIT-01(base)` | Create feature branch from base | §GIT-01 |
| `GIT-04()` | Create PR for current branch | §GIT-04 |
| `AUDIT-01(artifact)` | Run AU2 gate (10 items) on artifact | §AUDIT-01 |
| `AUDIT-02(diff)` | Run algorithm fidelity audit on diff | §AUDIT-02 |
| `AUDIT-03(spec)` | Run adversarial edge-case gate | §AUDIT-03 |
| `K-COMPILE()` | Compile wiki entry for current work | §K-COMPILE |
| `CONDENSE()` | Trigger OP-CONDENSE (context compression) | §OP-CONDENSE |
| `REPLAN(reason)` | Trigger DYNAMIC-REPLANNING | §DYNAMIC-REPLANNING |

────────────────────────────────────────────────────────
# § ROLE → OPERATION INDEX

AUTH levels: ROOT > GATE > SPEC > any.

| Role | Tier | Domain | Key operations |
|------|------|--------|---------------|
| ResearchArchitect | Root | all | HAND-01,02,03,04; AUDIT-01,02,03; K-COMPILE; CONDENSE; REPLAN |
| CodeWorkflowCoordinator | Gate | L | HAND-01,02,03; GIT-00,01,04,SP; LOCK; DOM-01,02 |
| PaperWorkflowCoordinator | Gate | A | HAND-01,02,03; GIT-00,01,04,SP; LOCK; BUILD-01,02 |
| TheoryAuditor | Gate | T | HAND-02,03; AUDIT-01,02,03 |
| ConsistencyAuditor | Gate | cross | HAND-02,03; AUDIT-01,02,03 |
| WikiAuditor | Gate | K | HAND-02,03; K-LINT,DEPRECATE,IMPACT-ANALYSIS |
| PromptArchitect | Gate | M | HAND-01,02,03; K-REFACTOR |
| PromptAuditor | Gate | M | HAND-02,03; AUDIT-01 |
| TaskPlanner | Spec | any | HAND-01,02,03; GIT-01 |
| TheoryArchitect | Spec | T | HAND-02,03; GIT-SP; K-COMPILE |
| CodeArchitect | Spec | L | HAND-02,03; GIT-01,SP; LOCK |
| CodeCorrector | Spec | L | HAND-02,03; GIT-SP; AUDIT-02 |
| TestRunner | Spec | L | HAND-02,03; TEST-01,02; GIT-SP |
| ExperimentRunner | Spec | E | HAND-02,03; EXP-01,02; GIT-SP |
| SimulationAnalyst | Spec | E | HAND-02,03; GIT-SP; K-COMPILE |
| PaperWriter | Spec | A | HAND-02,03; GIT-SP |
| PaperReviewer | Spec | A | HAND-02,03; AUDIT-01,02 |
| PaperCompiler | Spec | A | HAND-02,03; BUILD-01,02; GIT-SP |
| KnowledgeArchitect | Spec | K | HAND-02,03; K-COMPILE,REFACTOR; GIT-SP |
| Librarian | Spec | K | HAND-02,03; K-LINT,DEPRECATE |
| TraceabilityManager | Spec | K | HAND-02,03; K-IMPACT-ANALYSIS |
| DevOpsArchitect | Spec | L | HAND-02,03; GIT-WORKTREE-ADD; LOCK |
| DiagnosticArchitect | Spec | any | HAND-02,03; AUDIT-03 |

────────────────────────────────────────────────────────
# § HANDOFF PROTOCOL

Three tokens: HAND-01 (DISPATCH), HAND-02 (RETURN), HAND-03 (Acceptance Check).
v7.0.0 adds HAND-04 (PROTO-DEBATE). Schema SSoT: kernel-roles.md §SCHEMA-IN-CODE.

────────────────────────────────────────────────────────
<meta_section id="HAND-01" version="7.0.0" axiom_refs="A8,A6,phi4,phi4.1">
## HAND-01: DISPATCH Token

<purpose>Coordinator → Specialist delegation with binding task contract.</purpose>
<authority>Sent by: Coordinators, ResearchArchitect. Received by: any Specialist being delegated to.</authority>

```
DISPATCH → {specialist}
  task:                 {one-sentence objective}
  target:               {deliverable — matches IF-AGREEMENT outputs}
  inputs:               [{artifact_paths}]
  constraints:          [{scope_out}, expected_verdict: {measurable}]
  branch:               {dev/{domain}/{agent_id}/{task_id}}
  session_id:           {UUID v4}
  branch_lock_acquired: {true|false — MUST be true when target writes}
  verification_hash:    {sha256 hex of canonicalized payload}
  timestamp:            {ISO 8601 UTC}
  # Optional:
  worktree_path:        {../wt/{session_id}/{branch_slug}}
  parent_envelope_hash: {sha256 of triggering HAND}
```

<rules>
- task MUST be achievable in a single agent session.
- constraints.expected_verdict MUST be a measurable predicate.
- inputs MUST list ONLY final artifact paths + signed Interface Contract paths (not reasoning/chain-of-thought).
- branch_lock_acquired MUST be true when target will produce writes under worktree concurrency.
</rules>
<stop_conditions>STOP-02, STOP-03, STOP-06, STOP-10</stop_conditions>
</meta_section>

────────────────────────────────────────────────────────
<meta_section id="HAND-02" version="7.0.0" axiom_refs="A8,A6,phi4,phi4.1">
## HAND-02: RETURN Token

<purpose>Specialist → Coordinator handback after EXECUTE + CoVe.</purpose>
<authority>Sent by: any Specialist. Received by: the Coordinator that issued the matching HAND-01.</authority>

```
RETURN → {requester}
  status:               SUCCESS | FAIL | REJECT | BLOCKED_REPLAN_REQUIRED
  produced:             [{file_paths}] | none
  issues:               [{blocker}] | none
  session_id:           {UUID v4 — matches DISPATCH}
  branch_lock_acquired: {true while writes in progress; false after LOCK-RELEASE}
  verification_hash:    {sha256 hex of canonicalized payload}
  timestamp:            {ISO 8601 UTC}
  # Optional:
  lock_released:        {true|false}
  stop_code:            {STOP-xx — REQUIRED when status != SUCCESS}
  replan_context:       {brief reason — REQUIRED when status == BLOCKED_REPLAN_REQUIRED}
```

| Status | Meaning | Coordinator action |
|--------|---------|-------------------|
| SUCCESS | Deliverables produced; verdict PASS | Continue pipeline |
| FAIL | Work attempted; verdict FAIL | Review issues; decide |
| REJECT | HAND-03 rejected or wrapper refusal | Resolve blocker or escalate |
| BLOCKED_REPLAN_REQUIRED | Fundamental assumption wrong; cannot proceed | Trigger §DYNAMIC-REPLANNING |

<rules>
- produced[] MUST be non-empty on SUCCESS.
- issues[] MUST be empty on SUCCESS; non-empty on FAIL/REJECT.
- stop_code REQUIRED when status != SUCCESS.
- lock_released MUST be true on SUCCESS; false on FAIL (retain for retry).
- CoVe (kernel-roles.md §COVE MANDATE) MUST complete BEFORE emission.
</rules>
<stop_conditions>STOP-02, STOP-07, STOP-10, STOP-11</stop_conditions>
</meta_section>

────────────────────────────────────────────────────────
<meta_section id="HAND-03" version="7.0.0" axiom_refs="A8,A6,phi4,phi7" immutable="true">
## HAND-03: Acceptance Check

<purpose>Mandatory first action of any DISPATCH receiver. STOP-02 Immutable Zone: logic body byte-locked.</purpose>
<authority>Performed by EVERY agent upon receiving DISPATCH, before any work. Non-negotiable.</authority>

```
Acceptance Check:
  □ 1. TASK IN SCOPE: does the task fall within this role's PURPOSE in kernel-roles.md?
         If not → REJECT
  □ 2. INPUTS AVAILABLE: do all listed input files/artifacts exist and are non-empty?
         If not → REJECT
  □ 3. CONTEXT CONSISTENT: does `git log --oneline -1` match the `commit` field (HAND-01-ENV)?
         Mismatch → QUERY sender before proceeding
  □ 4. IF-AGREEMENT PRESENT: does DISPATCH context include an `if_agreement` path pointing
         to a valid signed docs/interface/ contract?
         Absent → REJECT; Gatekeeper must run GIT-00 and re-dispatch
         If PASS → read IF-AGREEMENT outputs as the deliverable contract for this task
  □ 5. UPSTREAM CONTRACTS SIGNED (Interface Contract validation — Falsification gate):
         For each contract in `upstream_contracts`:
           a. File exists at stated path in docs/interface/? Absent → REJECT.
           b. Contains `signed_by: {Gatekeeper}` and `status: SIGNED`? Unsigned → REJECT.
           c. Contract `outputs` matches task `inputs`? Mismatch → REJECT.
         Empty upstream_contracts permitted ONLY for T-Domain tasks.
         [FAST-TRACK exception]: `status: SIGNED` check relaxed; absence of field → STOP-SOFT.
  □ 6. PHANTOM REASONING GUARD (Auditor/Gatekeeper roles only):
         Verify DISPATCH `inputs` lists ONLY: final artifact paths, signed Interface Contract paths, test/build logs.
         If inputs include Specialist session history, intermediate derivation notes, or chain-of-thought → REJECT immediately (STOP-HARD).
         Auditor's FIRST action after PASS: perform independent derivation BEFORE opening artifact.
         "Verified by comparison only" = broken symmetry → STOP-HARD.
  □ 7. STRUCTURED OUTPUT SCHEMA (v7.0.0 — universal):
         Verify the DISPATCH envelope carries non-empty `session_id` (UUID v4), `branch_lock_acquired` (boolean),
         `verification_hash` (sha256 hex, 64 chars), and `timestamp` (ISO 8601 UTC), conformant to
         `HandoffEnvelope` (→ kernel-roles.md §SCHEMA-IN-CODE).
         Under `_base.yaml :: concurrency_profile == "worktree"`, additionally require `branch_lock_acquired: true`
         for any DISPATCH that will produce writes (empty-write tasks like pure routing MAY set false).
         Schema-invalid AND worktree profile → REJECT (STOP-10 equivalent: divergent lock state).
         Auditor evaluates the Artifact only — not Specialist process quality.
```

**On REJECT:** Issue RETURN immediately: `status: REJECT; produced: none; issues: ["Acceptance Check failed: check {N} — {reason}"]`

<rules>
- MUST run all 7 checks before any other action.
- MUST emit HAND-02 status: REJECT immediately if any check fails — no partial execution.
- MUST NOT paraphrase or simplify the 7 check definitions above; their text is part of the STOP-02 Immutable Zone.
- Auditor/Gatekeeper MUST perform independent derivation BEFORE opening the artifact under review.
</rules>
<stop_conditions>STOP-02, STOP-03, STOP-06, STOP-10</stop_conditions>
</meta_section>

────────────────────────────────────────────────────────
<meta_section id="HAND-04" version="7.0.0" axiom_refs="A6,A8,phi4">
## HAND-04: PROTO-DEBATE Token (v7.0.0)

<purpose>Coordinator-initiated adversarial debate between two Specialist instances on a contested hypothesis.</purpose>
<authority>Sent by: Coordinators or ResearchArchitect. Received by: two Specialist instances (A, B).</authority>

```
DEBATE → {instance_A} ↔ {instance_B}
  topic:           {contested hypothesis — one sentence, falsifiable}
  round_limit:     {integer, default 3}
  arbiter:         {Coordinator role}
  session_id:      {UUID v4}
  verification_hash: {sha256}
  timestamp:       {ISO 8601 UTC}
```

**DebateResult (returned by arbiter):**
```
  verdict:         CONSENSUS | SPLIT | ESCALATE
  winner:          {A | B | none}
  synthesis:       {1-3 sentence summary of resolution}
  dissent_note:    {optional — surviving objection when SPLIT}
  recommended_action: {proceed | replan | escalate}
```

<rules>
- topic MUST be falsifiable (not preference-based).
- round_limit MUST be ≤ 5; arbiter terminates debate and issues DebateResult when reached.
- SPLIT verdict → arbiter escalates to ResearchArchitect via HAND-02 with stop_code: STOP-SOFT.
- ESCALATE verdict → pauses pipeline; ResearchArchitect decides.
- Instances A and B MUST NOT share session context (isolation L2 minimum).
</rules>
<stop_conditions>STOP-04, STOP-08</stop_conditions>
<see_also>kernel-roles.md §SCHEMA-IN-CODE Hand04Payload, kernel-workflow.md §PROTO-DEBATE</see_also>
</meta_section>

────────────────────────────────────────────────────────
<meta_section id="OP-CONDENSE" version="7.0.0" axiom_refs="A1,phi1">
## OP-CONDENSE: Context Condensation (v7.0.0)

<purpose>Compress conversation context to reclaim token budget when threshold is breached.</purpose>
<authority>Any agent may trigger; ResearchArchitect may mandate.</authority>

**Trigger conditions (either):**
- Context utilization ≥ 60% of session token limit
- Turn count ≥ 30

**Procedure:**
1. Emit summary block:
   ```
   CONDENSE-CHECKPOINT:
     completed:   [{task_id}: {one-line outcome}]
     open:        [{task_id}: {status}]
     artifacts:   [{path}: {sha256_prefix}]
     next_action: {single sentence}
   ```
2. Request session restart with checkpoint as sole context.
3. Resume from `next_action`.

<rules>
- Condensed summary MUST include all produced artifact paths with sha256 prefix (first 8 chars).
- MUST NOT discard open issues or unresolved STOP codes.
- After restart: run HAND-03() on any pending DISPATCH before proceeding.
</rules>
<see_also>kernel-workflow.md §CONTEXT-MANAGEMENT</see_also>
</meta_section>

────────────────────────────────────────────────────────
# § GIT OPERATIONS

## GIT-WORKTREE-ADD
```bash
git worktree add .claude/worktrees/{slug} -b {branch}
```
Branch naming: `{domain}/{agent_id}/{task_id}`. DevOpsArchitect creates; all roles use.
Lock worktree immediately after creation: `LOCK(branch)`.

## GIT-SP (Standard Push)
```bash
git add -p           # stage only intended changes
git commit -m "{type}({scope}): {message}"
git push origin HEAD
```
Commit types: `feat | fix | test | exp | paper | wiki | refactor | chore`.

## GIT-00: Interface Drafting Gate
Before any cross-domain dispatch, Gatekeeper MUST create `docs/interface/{id}.md`:
```yaml
id: {domain}-{YYYYMMDD}-{seq}
title: {one-line description}
status: DRAFT | SIGNED
signed_by: {Gatekeeper role}
outputs: [{path}: {description}]
```

## GIT-01: Feature Branch
```bash
git checkout {base_branch}
git pull
git checkout -b dev/{domain}/{agent}/{task_id}
```

## GIT-02: Merge Criteria Gate
Before merge PR, ALL must pass:
- [ ] All tests green (TEST-01)
- [ ] Convergence table present if CCD operator changed (PR-3)
- [ ] Interface contract SIGNED
- [ ] No STOP codes open

## GIT-03: Conflict Resolution
```bash
git merge --no-ff {feature_branch}
# On conflict: resolve manually; never `git checkout --theirs` without domain expert review
```

## GIT-04: Pull Request
```bash
gh pr create --base {base} --head {branch} \
  --title "{type}({scope}): {description}" \
  --body "$(cat docs/interface/{id}.md)"
```

## GIT-05: Tag Release
```bash
git tag -a v{major}.{minor}.{patch} -m "{release notes}"
git push origin --tags
```

## GIT-ATOMIC-PUSH
For concurrent worktree environments — use `scripts/atomic_push.py`:
```bash
python scripts/atomic_push.py --branch {branch} --session {session_id}
```
Handles lock verification before push; aborts if session_id mismatch.

────────────────────────────────────────────────────────
# § LOCK OPERATIONS

## LOCK-ACQUIRE
Semantic: acquire exclusive branch lock before any write.
Implementation: `python scripts/lock.py acquire --branch {branch} --session {session_id}`

Returns: `{lock_path}` on success; raises `LockConflictError` if held.

Stale lock recovery (lock age > 30 min and session dead):
```bash
python scripts/lock.py force-release --branch {branch} --reason "stale"
```

## LOCK-RELEASE
Semantic: release branch lock after write completes or on FAIL.
Implementation: `python scripts/lock.py release --branch {branch} --session {session_id}`

Verifies `session_id` matches lock file before release; raises `LockOwnershipError` if mismatch.

**Rules:** MUST call after HAND-02 SUCCESS; MUST retain on FAIL to allow retry.

────────────────────────────────────────────────────────
# § ID NAMESPACE OPERATIONS (v7.1.0)

Purpose: Make CHK/ASM/KL ticket IDs collision-free across parallel worktrees by
namespacing them with a deterministic per-worktree prefix derived from the
branch name. Replaces the legacy "read ledger max + 1" convention which
caused documented collisions (CHK-115, CHK-161→167, CHK-225→226, CHK-246
unrenumbered). Pure text rule — no scripts, no shared counter file.

## ID-NAMESPACE-DERIVE
Semantic: derive `id_prefix` deterministically from the active branch name.
MUST run once per session at start, before any HAND-01 dispatch carrying an ID.
The result is bound for the lifetime of the session and recorded in
`docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY`.

Procedure:
1. Take `branch_slug` (the branch name as it appears on disk).
2. Strip a leading `worktree-` or `wt-` segment if present.
3. Tokenize on `-`; take the first 2 tokens.
4. Keep only `[A-Z0-9-]` after uppercasing; drop other characters.
5. If total length > 9, truncate the second token so the joined `TOK1-TOK2`
   is ≤ 9 characters; if the first token alone is ≥ 9, take only the first
   token truncated to 9.
6. Collision check: if the resulting prefix already appears in
   `docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY` under a different
   active `session_id`, extend by appending `-` + the third token (or its
   first 4 chars), re-truncated to ≤ 12 characters total.

Examples:
| branch_slug | id_prefix |
|---|---|
| `worktree-ra-ch9-review` | `RA-CH9` |
| `worktree-ra-ch11-review` | `RA-CH11` |
| `worktree-ch14-benchmark-bootstrap` | `CH14-BEN` |
| `worktree-ra-paper-ch4-rewrite` | `RA-PAPER` |
| `researcharchitect-src-refactor-plan` | `RESEARCH` |
| `worktree-ra-meta-id-namespace` | `RA-META` |

Output: `id_prefix: string` matching `^[A-Z0-9]+(?:-[A-Z0-9]+)*$`, length ≤ 12.

## ID-RESERVE-LOCAL
Semantic: assign the next CHK/ASM/KL number within the current session's
prefix. Counter is local to the worktree (no cross-worktree coordination).
Each family (CHK / ASM / KL) has its own counter, starting at 001.

Procedure:
1. Read `docs/02_ACTIVE_LEDGER.md` and grep for entries matching
   `^(CHK|ASM|KL)-{id_prefix}-([0-9]{3})` for the family being reserved.
2. Take max(NNN) within this prefix; output `NNN+1` zero-padded to 3 digits.
3. If no match: NNN = 1.
4. Emit full ID: `{family}-{id_prefix}-{NNN}`.

Output: full ID string matching `^(CHK|ASM|KL)-[A-Z0-9-]+-[0-9]{3,}$`.

## ID-COLLISION-CHECK
Semantic: verify the resulting ID does not already exist in the local ledger
copy. Defense in depth — should be a no-op if ID-RESERVE-LOCAL is correct.

Procedure:
1. After ID-RESERVE-LOCAL, grep ledger for the full ID string.
2. Match count > 0 → raise `IdCollisionError` (STOP-10 IDs).
3. Match count = 0 → pass.

## Backward compatibility (legacy CHK-NNN form)

Legacy entries `CHK-NNN`, `ASM-NNN`, `KL-NN` (without prefix) created before
the v7.1.0 cutover remain valid. The schema regex in `kernel-roles.md
§SCHEMA EXTENSIONS v7.1.0` accepts both forms. Cross-document references
to legacy IDs (e.g., `kernel-constitution.md` cites `CHK-114`) are
unchanged. Migration is forward-only: new IDs minted in worktree sessions
after v7.1.0 cutover MUST use the prefixed form.

## Stop conditions

- `id_prefix` recomputed mid-session → STOP-10 (immutable per session)
- ID emitted that does not contain the session's bound `id_prefix` →
  STOP-10 IDs (HAND-03 C7 schema validation rejects)
- Two active worktrees derive the same prefix and step 6 collision check
  is skipped → STOP-10 IDs

────────────────────────────────────────────────────────
# § DOMAIN OPERATIONS

## DOM-01: Domain Gate Check
Before any cross-domain artifact move, Coordinator verifies:
- [ ] IF-AGREEMENT exists and is SIGNED for the target domain
- [ ] Source domain HEAD is on a clean commit (no untracked writes)
- [ ] Receiving domain branch exists

## DOM-02: Domain Merge Sequencing
T-domain changes merge first (interface contracts), then L, then E, then A.
No A-domain PR may merge before its L-domain dependency is merged.

────────────────────────────────────────────────────────
# § BUILD OPERATIONS

## BUILD-01: LaTeX Compile (single pass)
```bash
cd paper && pdflatex -interaction=nonstopmode main.tex
```
Success: exit 0 + `main.pdf` exists. Failure: emit STOP-SOFT with log tail (last 20 lines).

## BUILD-02: LaTeX Full Build (BibTeX + 2-pass)
```bash
cd paper && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```
Required for final submission builds. PaperCompiler role only.

────────────────────────────────────────────────────────
# § TEST OPERATIONS

## TEST-01: Pytest Suite
```bash
make test   # remote-first; falls back to make test-local
```
Required output: pass count, fail count, coverage % (if configured). STOP-HARD on any fail.

## TEST-02: Convergence Analysis
Run MMS verification per PR-3:

| N | L_inf error | slope |
|---|-------------|-------|
| 32 | … | — |
| 64 | … | … |
| 128 | … | … |
| 256 | … | … |

Acceptance: all slopes ≥ expected_order − 0.2. CCD boundary limits: d1 ≥ 3.5, d2 ≥ 2.5 (ASM-004).

────────────────────────────────────────────────────────
# § EXPERIMENT OPERATIONS

## EXP-01: Simulation Execution
```bash
make run EXP=experiment/{ch}/{script}.py
```
Uses `twophase.experiment` toolkit (PR-4). Remote-first (see CLAUDE.md §Execution Workflow).

Mandatory sanity checks before HAND-02:
- SC-1: Final time matches `t_end` parameter
- SC-2: Mass/volume conservation error < 1e-6
- SC-3: Output NPZ exists and is non-empty
- SC-4: No NaN/Inf in final velocity or pressure fields

## EXP-02: Result Analysis + Plot
```bash
make plot EXP=experiment/{ch}/{script}.py   # --plot-only flag
```
All figures saved as PDF (CLAUDE.md §Coding Rules). Results in `experiment/{ch}/results/{name}/`.

────────────────────────────────────────────────────────
# § AUDIT OPERATIONS

## AUDIT-01: AU2 Gate (10 items)
Performed by Auditor/Gatekeeper before HAND-02 SUCCESS on any deliverable.

| # | Check |
|---|-------|
| 1 | Algorithm matches paper equation (PR-5) |
| 2 | CCD primacy maintained (PR-1) |
| 3 | No FD operator in solver core src/twophase/ |
| 4 | MMS convergence table present (if spatial operator changed) |
| 5 | Interface contract SIGNED |
| 6 | No STOP codes open |
| 7 | Experiment toolkit used for all infrastructure (PR-4) |
| 8 | Figures saved as PDF |
| 9 | A3 traceability chain intact (equation → memo → code) |
| 10 | No deprecated path usage (results/ top-level) |

All 10 must PASS; any FAIL → AUDIT-01 FAIL with item number cited.

## AUDIT-02: Algorithm Fidelity Audit
Adversarial check that code matches paper equation exactly (PR-5).

Procedure:
A. Read paper equation from `paper/sections/*.tex`
B. Read discretisation memo from `docs/memo/*.md`
C. Independently derive expected code from A+B
D. Compare derived expectation to actual code diff
E. Any deviation → FAIL with specific line reference

Two-Path Requirement: derivation (step C) MUST precede code inspection (step D).
"Verified by comparison only" = STOP-HARD (phantom reasoning violation).

## AUDIT-03: Adversarial Edge-Case Gate
For any new numerical module, DiagnosticArchitect runs:
1. Identify 3 adversarial inputs (zero field, near-singular matrix, boundary-only forcing)
2. Run module on each input
3. Verify output is finite and physically plausible
4. Document each case in `docs/memo/diag_{module}.md`

────────────────────────────────────────────────────────
# § KNOWLEDGE OPERATIONS

## K-COMPILE
Create or update wiki entry after any significant finding.
Format: canonical YAML header + content per `kernel-domains.md §Wiki Entry Format`.
Target: `docs/wiki/{domain}/{WIKI-X-NNN}.md`; register in `docs/wiki/INDEX.md`.

## K-LINT
Check wiki entries for:
- [ ] Canonical YAML header present (id, title, domain, date, status)
- [ ] No duplicate IDs in INDEX.md
- [ ] All cross-references resolve (linked files exist)

## K-DEPRECATE
Mark entry deprecated: update YAML `status: DEPRECATED`, add `superseded_by: {id}`.
Do NOT delete; Librarian registers in `docs/wiki/INDEX.md §DEPRECATED`.

## K-REFACTOR
Structural reorganization of wiki entries (rename, re-ID, merge).
MUST update INDEX.md and all cross-references atomically. TraceabilityManager audits.

## K-IMPACT-ANALYSIS
Before any interface change: TraceabilityManager enumerates all wiki entries + code modules
that reference the affected interface. Report: `{n} entries affected; {m} require update`.

────────────────────────────────────────────────────────
# § PATCH-IF: Interface Patch Protocol

When an interface contract must change post-SIGNED:
1. TheoryAuditor issues new `docs/interface/{id}-v{n+1}.md` with `status: DRAFT`
2. All downstream agents notified via HAND-01 (task: "review updated IF-AGREEMENT")
3. Each downstream agent issues HAND-02 `status: SUCCESS` (accepting) or `REJECT` (blocking)
4. On all SUCCESS: Gatekeeper signs new contract; old contract archived as `{id}-v{n}.deprecated`
5. Any REJECT: triggers HAND-04 PROTO-DEBATE between rejecting agent and TheoryAuditor

────────────────────────────────────────────────────────
# § INTERFACE DRAFTING — Speculative Parallel Execution

TheoryArchitect MAY publish `docs/interface/{id}.draft` once core algorithm structure is known.
CodeArchitect MAY read `.draft` files to build scaffolding in `artifacts/L/scaffold_{id}.py.draft` only — never in `src/`.

Rules:
1. No `.draft` artifact may be merged into `src/`, `paper/`, or any domain branch.
2. Every draft-derived function must carry: `# DRAFT — pending TheoryAuditor signature on docs/interface/{id}.draft`
3. Promotion gate: TheoryAuditor HAND-02 `interface_contracts_checked: [{id}.draft → SIGNED]` → Gatekeeper removes `.draft` suffix.
4. TheoryAuditor FAIL → all scaffold files MUST be deleted.

────────────────────────────────────────────────────────
# § AUDIT EXIT CRITERIA — Deadlock Prevention

A Gatekeeper / Auditor may REJECT ONLY when tied to a specific violation of:

| Category | Examples |
|----------|---------|
| 1. Formal Checklist | Q1–Q3 item failed; AUDIT-01 item N failed |
| 2. Interface Contract | Output ≠ docs/interface/{contract}.md outputs; contract unsigned |
| 3. Core Axiom | A1–A11 violated (cite axiom + exact violation) |

"Gut feeling" rejection forbidden. When all formal checks pass, Auditor MUST issue CONDITIONAL PASS.

```
CONDITIONAL PASS:
  verdict:      CONDITIONAL_PASS
  warning_note: {specific concern — must reference a named risk}
  escalate_to:  user
  pipeline:     CONTINUES
```

────────────────────────────────────────────────────────
# § DYNAMIC-REPLANNING

Trigger: agent returns `status: BLOCKED_REPLAN_REQUIRED` in HAND-02.

Procedure (ResearchArchitect or Coordinator):
1. Read `replan_context` from HAND-02 payload.
2. Identify invalidated assumptions (cite plan step or IF-AGREEMENT).
3. Issue revised HAND-01 with updated task/constraints, OR escalate to user if fundamental.
4. Log replan in `docs/02_ACTIVE_LEDGER.md §REPLAN_LOG`.

Limits: max 2 replan cycles per task before mandatory user escalation (kernel-antipatterns.md §AP-12).

────────────────────────────────────────────────────────
# § STOP CONDITIONS

| Code | Severity | Trigger | Action |
|------|----------|---------|--------|
| STOP-01 | HARD | Axiom A1–A11 violated | Halt; cite axiom + violation |
| STOP-02 | HARD | HAND-03 Immutable Zone bypassed | Halt; report to ResearchArchitect |
| STOP-03 | HARD | Branch lock not acquired before write | Halt; acquire lock first |
| STOP-04 | HARD | Cross-domain write without DOM-01 gate | Halt; run DOM-01 |
| STOP-05 | HARD | FD operator in solver core (PR-1) | Halt; replace with CCD |
| STOP-06 | HARD | Task not achievable in single session | Decompose; re-dispatch |
| STOP-07 | SOFT | Convergence check failed (PR-3) | Report; escalate to TheoryAuditor |
| STOP-08 | SOFT | DEBATE SPLIT — no consensus | Escalate to ResearchArchitect |
| STOP-09 | SOFT | BUILD-01/02 compile failure | Fix; retry |
| STOP-10 | HARD | Schema-invalid envelope + worktree profile | REJECT; fix envelope |
| STOP-11 | SOFT | Lock conflict — another session holds branch | Wait; retry after TTL |
| STOP-12 | HARD | Dual-emission: text HAND + tool call in same session | Halt; use one mode only |

HARD → immediate halt + HAND-02 REJECT with stop_code.
SOFT → continue with warning + stop_code in HAND-02 detail.

────────────────────────────────────────────────────────
# § COMMAND FORMAT (Quick Reference)

All operations follow: `{OPERATION-ID}: {params}` in agent prose, or shorthand from §SHORTHAND SYNTAX.
Full syntax for each operation is in the §-section of this file.
Agents MUST NOT improvise operation syntax — cite the ID and load JIT.
