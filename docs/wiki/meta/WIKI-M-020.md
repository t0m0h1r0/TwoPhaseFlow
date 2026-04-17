# WIKI-M-020: Canonical Operations Reference
**Category:** Meta | **Created:** 2026-04-18
**Sources:** `prompts/meta/meta-ops.md` (full — all GIT/DOM/LOCK/HAND/AUDIT/K ops)

**JIT Rule:** Agent prompts include only operation ID + trigger condition + AUTH_LEVEL tag.
Full syntax lives here. Agents MUST read this file when the operation is needed — never improvise from memory.

---

## § Authority Tiers Quick Reference

| Tier | Roles | Key Operations Authorized |
|------|-------|--------------------------|
| Root Admin | ResearchArchitect (system-level) | GIT-04 Phase B (merge to main), PATCH-IF, system config |
| Gatekeeper | Domain coordinators, reviewers, auditors | GIT-02/03/04-A, DOM-01 lock, HAND-01 dispatch, AUDIT-01/02/03 |
| Specialist | Domain workers | File writes within write_territory, HAND-02 return, CoVe, LOCK-ACQUIRE/RELEASE |

---

## § Git Operations

### GIT-SP — Specialist Branch Creation

**Authorized:** All agents | **[AUTH_LEVEL: Specialist]**

```sh
scripts/git-sp.sh {domain} {agent_id} {task_id}
```

Creates branch `dev/{domain}/{agent_id}/{task_id}`. If already on a non-domain branch → switch.
`main` branch → wrapper returns SYSTEM_PANIC.

**Commit format:** `{branch}: {summary} [CHK-{N}]`

---

### GIT-WORKTREE-ADD — Create Isolated Worktree (v5.1)

**Authorized:** Coordinators under `concurrency_profile == "worktree"` | **[AUTH_LEVEL: Gatekeeper]**

```sh
git worktree add ../wt/"${SESSION_ID}"/"${BRANCH_SLUG}" -b "${BRANCH}"
```

**Critical:** path MUST be `../wt/{SESSION_ID}/{BRANCH_SLUG}` (sibling directory, not inside `$REPO_ROOT`).
Any path inside `$REPO_ROOT` or non-sibling → STOP-09 (SYSTEM_PANIC). Worktree removal requires human review.

---

### GIT-00 — Interface Agreement Pre-flight

**Authorized:** Gatekeepers | **[AUTH_LEVEL: Gatekeeper]** | **Phase:** Before any dev/ branch creation

```sh
# Step 1: read existing IF-AGREEMENT (if any)
cat docs/interface/{domain}_{feature}.md 2>/dev/null || echo "No existing agreement"
# Step 2: write/update IF-AGREEMENT
# (Gatekeeper authors the contract — see IF-AGREEMENT format in WIKI-M-018)
# Step 3: commit signed contract
git add docs/interface/{domain}_{feature}.md
git commit -m "{branch}: if-agreement — {feature} (signed by {gatekeeper})"
```

**IF-COMMIT token required** for writes to `docs/interface/`. Gatekeepers only.

---

### GIT-01 — Branch Preflight

**Authorized:** Gatekeepers | **[AUTH_LEVEL: Gatekeeper]** | **Phase:** Start of P-E-V-A

```sh
# Step 1: verify current branch
git branch --show-current | grep -E "^(code|paper|prompt|theory|wiki|experiment|dev/)" \
  || echo "STOP: not on a domain branch"
# Step 2: fetch and sync interface files
git fetch origin main
git diff --name-only HEAD origin/main | grep "^docs/interface/" && git merge origin/main --no-ff
# Step 3: conflict check
git status | grep -c "conflict" && echo "STOP: merge conflict — report to user"
```

**STOP conditions:** non-domain branch → switch or report; merge conflict → STOP; auto-switch fails → STOP.

---

### GIT-02 — DRAFT Commit

**Authorized:** Gatekeepers | **[AUTH_LEVEL: Gatekeeper]** | **Phase:** End of EXECUTE

```sh
git add {files}    # explicit paths — never -A
git commit -m "{branch}: draft — {summary}"
```

---

### GIT-03 — REVIEWED Commit

**Authorized:** Gatekeepers | **[AUTH_LEVEL: Gatekeeper]** | **Phase:** End of VERIFY

**Trigger:** TestRunner PASS / PaperReviewer 0 FATAL+0 MAJOR / PromptAuditor Q3 PASS

```sh
git add {files}
git commit -m "{branch}: reviewed — {summary}"
```

---

### GIT-04 — VALIDATED Commit + PR Merge

**[AUTH_LEVEL: Gatekeeper (Phase A) | Root Admin (Phase B)]**
**Trigger:** Gate auditor issues PASS AND all 3 MERGE CRITERIA satisfied (TEST-PASS, BUILD-SUCCESS, LOG-ATTACHED)

**Phase A — Gatekeeper:**
```sh
git checkout {branch}
git merge dev/{agent_role} --no-ff -m "{branch}: validated — {summary}"
gh pr create --base main --head {branch} \
  --title "merge({branch} → main): {summary}" \
  --body "AU2 PASS. MERGE CRITERIA: TEST-PASS ✓ BUILD-SUCCESS ✓ LOG-ATTACHED ✓"
```

**Phase B — Root Admin:**
```sh
# Check: no direct commits on main (A8), PR title format, AU2 PASS + MERGE CRITERIA in body
git checkout main
git merge {branch} --no-ff -m "merge({branch} → main): {summary}"
git checkout {branch}
```

On merge conflict → STOP; report to user. Post-merge failure → `git revert -m 1 HEAD`; STOP.

---

### GIT-ATOMIC-PUSH — Fetch-Rebase-Push Under Concurrency (v5.1)

**Authorized:** Any agent under `concurrency_profile == "worktree"` | **[AUTH_LEVEL: Specialist]**
**Trigger:** Any `git push` while another Claude Code session may be pushing to same remote.
**Phase:** After HAND-02 `produced:` emission, before `lock_released: true`.

```sh
git fetch origin
git rebase "origin/${BASE_BRANCH}"    # typically origin/main
git push origin "${BRANCH}"
```

- `fetch` + `rebase` are MANDATORY before push — skipping = STOP-05 equivalent (forbidden)
- On rebase conflict → **STOP-11** (STOP-SOFT):
  1. `git rebase --abort` (restore pre-rebase state)
  2. Issue HAND-02 `status: FAIL, stop_code: "STOP-11", lock_released: false` (lock RETAINED)
  3. Report conflicting paths in `issues`; await human intervention
- Force-push (`--force-with-lease`) NOT permitted even on non-linear history — abort and escalate

**Composition:** GIT-ATOMIC-PUSH completes BEFORE LOCK-RELEASE.

---

### GIT-05 — Sub-branch Operations

**Authorized:** CodeWorkflowCoordinator, PaperWorkflowCoordinator | **[AUTH_LEVEL: Gatekeeper]**

```sh
# Create sub-branch
git checkout {parent} && git checkout -b {parent}/{feature}
# Merge back
git checkout {parent} && git merge {parent}/{feature} --no-ff \
  -m "merge({parent}/{feature} → {parent}): {summary}"
```

`{parent}` = `code` or `paper` (never `main`). Sub-branches merge only to parent.

---

## § Domain Operations

### DOM-01 — Domain Lock Establishment

**Authorized:** Gatekeepers | **[AUTH_LEVEL: Gatekeeper]**
**Trigger:** MANDATORY after GIT-01, before any DISPATCH or file edit

```
DOMAIN-LOCK:
  domain:          {Theory | Library | Experiment | AcademicWriting | Prompt | Audit | Routing}
  matrix_id:       {T | L | E | A | P | Q | M}
  branch:          {git branch --show-current}
  set_by:          {coordinator name}
  write_territory: {from meta-domains.md §DOMAIN REGISTRY for active domain}
  forbidden_write: {from meta-domains.md §DOMAIN REGISTRY for active domain}
```

| Matrix ID | write_territory | read_territory |
|-----------|----------------|----------------|
| T | `docs/memo/`, `docs/02_ACTIVE_LEDGER.md` | `paper/sections/*.tex`, `docs/01_PROJECT_MAP.md §6` |
| L | `src/twophase/`, `tests/`, `docs/02_ACTIVE_LEDGER.md` | `paper/sections/*.tex`, `docs/01_PROJECT_MAP.md`, `docs/interface/AlgorithmSpecs.md` |
| E | `experiment/`, `docs/02_ACTIVE_LEDGER.md` | `docs/interface/SolverAPI_vX.py`, `src/twophase/` |
| A | `paper/sections/*.tex`, `paper/bibliography.bib`, `docs/02_ACTIVE_LEDGER.md` | `src/twophase/`, `docs/interface/ResultPackage/`, `docs/interface/TechnicalReport.md` |
| P | `prompts/agents-{env}/*.md` | `prompts/meta/*.md` |
| Q | `docs/02_ACTIVE_LEDGER.md` | all domains (read-only) |

Failure: branch doesn't match known domain → STOP; report to user.

---

### DOM-02 — Pre-Write Storage Check (Universal)

**Authorized:** every agent (universal) | **Trigger:** every file write

**Failure modes:**
- DOMAIN-LOCK absent → STOP signal; request domain lock from coordinator
- Target path outside `write_territory` → CONTAMINATION_GUARD error; notify coordinator

---

## § Lock Operations (v5.1)

### LOCK-ACQUIRE — Branch Semaphore Acquisition

**Authorized:** every agent under `concurrency_profile == "worktree"` | **[AUTH_LEVEL: universal]**
**Trigger:** MANDATORY before the first write to any branch owned by the session.
**No-op when `concurrency_profile == "legacy"`.**

```sh
BRANCH_SLUG="$(echo "${BRANCH}" | tr '/' '-')"
LOCK_FILE="docs/locks/${BRANCH_SLUG}.lock.json"

python3 - <<'PY'
import os, json, uuid, datetime, sys
path = os.environ["LOCK_FILE"]
payload = {
  "branch":       os.environ["BRANCH"],
  "branch_slug":  os.environ["BRANCH_SLUG"],
  "session_id":   os.environ["SESSION_ID"],
  "worktree_path": os.environ.get("WORKTREE_PATH", ""),
  "holder_agent": os.environ["HOLDER_AGENT"],
  "acquired_at":  datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
  "expires_at":   (datetime.datetime.utcnow() + datetime.timedelta(hours=24)).isoformat(timespec="seconds") + "Z",
  "meta_version": "5.1.0",
}
# O_EXCL: fails atomically if another session already holds the lock
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
except FileExistsError:
    sys.stderr.write("STOP-10 foreign lock: " + path + "\n"); sys.exit(10)
with os.fdopen(fd, "w") as f:
    json.dump(payload, f, indent=2)
PY
```

**Post-conditions:**
1. `docs/locks/{branch_slug}.lock.json` exists with this session's UUID (O_EXCL = no race window)
2. Matching row appended to `docs/02_ACTIVE_LEDGER.md §4 BRANCH_LOCK_REGISTRY` in first commit
3. Every `HandoffEnvelope` produced while held carries `branch_lock_acquired: true`

**Failure modes:**
- `O_EXCL` refuses (file exists) → **STOP-10** foreign lock: halt; HAND-02 `status: REJECT, stop_code: "STOP-10"`; do NOT delete or overwrite existing lock
- Stale lock (`expires_at` in past) → do NOT auto-reclaim; human-initiated `--force` procedure:
  1. Confirm `expires_at < $(date -u)` AND holder session no longer active
  2. Append FORCED_RECOVERY entry to LEDGER §4 with timestamp, stale `session_id`, reason
  3. `rm docs/locks/{branch_slug}.lock.json`
  4. Run LOCK-ACQUIRE normally
- Lock acquired but registry entry missing (or vice versa) → **STOP-10 CONTAMINATION_GUARD**

---

### LOCK-RELEASE — Branch Semaphore Release

**Authorized:** the session that owns the lock (only) | **[AUTH_LEVEL: universal]**
**Trigger:** MANDATORY at HAND-02 emission when Specialist finished all writes. Runs AFTER GIT-ATOMIC-PUSH.
**MUST NOT release on FAIL** (lock retained for retry, e.g., STOP-11).

```sh
BRANCH_SLUG="$(echo "${BRANCH}" | tr '/' '-')"
LOCK_FILE="docs/locks/${BRANCH_SLUG}.lock.json"

python3 - <<'PY'
import os, json, sys
path = os.environ["LOCK_FILE"]
with open(path) as f:
    data = json.load(f)
if data.get("session_id") != os.environ["SESSION_ID"]:
    sys.stderr.write("STOP-10 foreign lock force: " + path + "\n"); sys.exit(10)
os.remove(path)
PY
```

- Ownership verified by `session_id` equality BEFORE file removal
- Registry row in LEDGER §4 is **NOT deleted** — updated with `released_at` (append-only audit log)
- MUST run at HAND-02 SUCCESS emission; MUST NOT run on FAIL

---

## § Handoff Protocol

### HandoffEnvelope TypeScript Schema (SSoT: `meta-roles.md §SCHEMA-IN-CODE`)

```typescript
interface HandoffEnvelope {
  hand_type:            "HAND-01" | "HAND-02" | "HAND-03";
  session_id:           string;   // UUID v4 of the emitting Claude Code session
  branch_lock_acquired: boolean;  // true if session holds exclusive branch lock
  verification_hash:    string;   // sha256 hex (64 chars) over canonical payload
  timestamp:            string;   // ISO 8601 UTC (e.g. "2026-04-11T12:34:56Z")
  meta_version?:        string;   // semver — expected "5.1.0" or later
  payload:              Hand01Payload | Hand02Payload | Hand03Payload;
}

interface Hand01Payload {
  task:                  string;    // one-sentence objective bound to a CHK-id
  target:                string;    // target agent name
  inputs:                string[];  // artifact paths + signed contracts ONLY
  constraints:           string[];  // scope constraints, stop conditions, axiom refs
  branch:                string;    // target git branch; must be locked before writes
  chk_id?:               string;    // pattern: ^CHK-[0-9]{3,}$
  worktree_path?:        string;    // ../wt/{session_id}/{branch_slug} — worktree profile only
  parent_envelope_hash?: string;    // sha256 of triggering HAND (audit chain)
}

interface Hand02Payload {
  status:          "SUCCESS" | "FAIL" | "REJECT";
  produced:        string[];  // file paths written; each MUST lie within write_territory
  issues:          string[];  // blockers; MUST be empty on SUCCESS
  detail?:         string;    // self-evaluation — only when DISPATCH requested it
  lock_released?:  boolean;   // true on SUCCESS; false on FAIL (retain for retry)
  chk_id?:         string;
  stop_code?:      string;    // pattern: ^STOP-[0-9]{2}$ — REQUIRED when status != SUCCESS
}

interface Hand03Payload {
  checks: Array<{
    id: "C1_scope_within_territory" | "C2_no_forbidden_writes" |
        "C3_independent_derivation_present" | "C4_evidence_attached" |
        "C5_diff_first_output" | "C6_no_scope_creep" |
        "C7_structured_output_schema_valid";
    passed: boolean;
    note?:  string;
  }>;  // exactly 7 items; C7 is v5.1 schema check
  verdict:               "PASS" | "REJECT";
  reviewed_envelope_hash?: string;
}
```

**Enforcement:** Under `concurrency_profile == "worktree"`: schema-invalid → REJECT (STOP-10).
Under `legacy`: schema-invalid → STOP-SOFT during v5.0→v5.1 transition.
No external `schemas/hand_schema.json` file — this section IS the SSoT.

---

### HAND-01: DISPATCH Token

**Sent by:** Coordinators, ResearchArchitect | **Received by:** any Specialist

```
DISPATCH → {specialist}
  task:                   {one-sentence objective}
  target:                 {expected deliverable — matches IF-AGREEMENT outputs}
  inputs:                 [{artifact_paths}]
  constraints:            [{scope_out}, expected_verdict: {measurable}]
  branch:                 {dev/{domain}/{agent_id}/{task_id}}
  session_id:             {UUID v4}
  branch_lock_acquired:   {true|false — MUST be true if target will write}
  verification_hash:      {sha256 hex of canonicalized payload}
  timestamp:              {ISO 8601 UTC}
  # Optional:
  worktree_path:          {../wt/{session_id}/{branch_slug}}
  parent_envelope_hash:   {sha256 of the HAND that caused this dispatch}
```

**§HAND-01-ENV fields (environment-injected; NOT written by coordinators):**
`phase`, `matrix_domain`, `branch`, `commit`, `domain_lock`, `if_agreement`,
`upstream_contracts`, `artifact_hash`, `context_root`, `domain_lock_id`, `gatekeeper_approval_required`

**Rules:** `task` must be single-session achievable; `expected_verdict` must be measurable; `inputs` ONLY final artifact paths + signed contracts (no Specialist CoT); `branch_lock_acquired: true` when target will write.

---

### HAND-02: RETURN Token

**Sent by:** Any Specialist | **Received by:** The Coordinator that issued DISPATCH

```
RETURN → {requester}
  status:                 SUCCESS | FAIL | REJECT
  produced:               [{file_paths}] | none
  issues:                 [{blocker}] | none      # FAIL/REJECT only
  detail:                 {CoVe summary — only when explicitly requested}
  session_id:             {UUID v4 — matches DISPATCH}
  branch_lock_acquired:   {true while writes in progress; false after LOCK-RELEASE}
  verification_hash:      {sha256 hex}
  timestamp:              {ISO 8601 UTC}
  # Optional:
  lock_released:          {true on SUCCESS; false on FAIL — retains lock for retry}
  stop_code:              {STOP-xx — REQUIRED when status != SUCCESS}
```

| Status | Meaning | Coordinator action |
|--------|---------|-------------------|
| SUCCESS | All deliverables produced; verdict PASS | Continue pipeline |
| FAIL | Work attempted; verdict FAIL | Review issues; decide |
| REJECT | HAND-03 rejected, STOPPED, or wrapper refusal | Resolve blocker or escalate |

**Procedure before emission:**
1. Complete CoVe (Q1 logical, Q2 axiom, Q3 scope) — non-negotiable
2. Canonicalize payload → sha256 → `verification_hash`
3. Emit RETURN envelope
4. IF `status == SUCCESS` AND `concurrency_profile == "worktree"` → invoke LOCK-RELEASE

---

### HAND-03: Acceptance Check (STOP-02 Immutable Zone)

**Performed by:** EVERY agent upon receiving DISPATCH, before any work

7 semantic checks that the wrapper cannot perform:

```
Acceptance Check:
  □ C1. TASK IN SCOPE: does task fall within this role's PURPOSE in meta-roles.md?
         → REJECT if not
  □ C2. INPUTS AVAILABLE: do all listed input files/artifacts exist and are non-empty?
         → REJECT if not
  □ C3. CONTEXT CONSISTENT: does git log --oneline -1 match the commit field (HAND-01-ENV)?
         → QUERY sender before proceeding if mismatch
  □ C4. IF-AGREEMENT PRESENT: does DISPATCH include if_agreement path to valid signed contract?
         → REJECT if absent; Gatekeeper must run GIT-00 and re-dispatch
         → If PASS: read IF-AGREEMENT outputs as the deliverable contract for this task
  □ C5. UPSTREAM CONTRACTS SIGNED:
         For each contract in upstream_contracts:
           a. File exists at stated path in docs/interface/? → REJECT if absent
           b. Contains signed_by: {Gatekeeper} and status: SIGNED? → REJECT if unsigned
           c. Contract outputs match task inputs? → REJECT if mismatch
         Empty upstream_contracts permitted ONLY for T-Domain tasks.
         [FAST-TRACK exception]: status: SIGNED check relaxed; absence → STOP-SOFT
  □ C6. PHANTOM REASONING GUARD (Auditor/Gatekeeper roles only):
         Verify DISPATCH inputs lists ONLY: final artifact paths, signed contracts, test/build logs.
         If inputs include Specialist session history, intermediate derivations, or CoT → REJECT (STOP-HARD)
         Auditor's FIRST action after PASS: independent derivation BEFORE opening artifact.
         "Verified by comparison only" = broken symmetry → STOP-HARD
  □ C7. STRUCTURED OUTPUT SCHEMA (v5.1 — universal):
         Verify DISPATCH envelope carries: non-empty session_id (UUID v4), branch_lock_acquired (bool),
         verification_hash (sha256 hex, 64 chars), timestamp (ISO 8601 UTC)
         Under worktree profile: branch_lock_acquired must be true for write tasks
         Schema-invalid AND worktree profile → REJECT (STOP-10 equivalent)
         Legacy profile: schema-invalid → STOP-SOFT during v5.0→v5.1 transition
```

**On REJECT:** Issue RETURN immediately: `status: REJECT; produced: none; issues: ["Acceptance Check failed: check {N} — {reason}"]`

---

### CoVe MANDATE — Chain-of-Verification (mandatory for ALL Specialists)

Runs INSIDE EXECUTE, AFTER artifact generation, BEFORE HAND-02 emission.

```
CoVe PROCESS (3 steps — non-negotiable):

Step 1 — Generate 3 Critical Questions
  Q1: Logical — "Is there an error in the core logic, derivation, or structure?"
  Q2: Axiom Compliance — "Does this output violate any A1–A11 axiom or φ-principle?"
  Q3: Scope/IF-Agreement — "Does this output satisfy the deliverable contract from IF-AGREEMENT?"

Step 2 — Derive Answers Independently
  Answer each question by reading the artifact with adversarial intent.
  Do NOT use the same reasoning chain used to produce the artifact.
  If ANY answer finds a flaw → correct the artifact.

Step 3 — Finalize
  Place ONLY the corrected artifact in HAND-02 payload.
  Append CoVe summary to HAND-02 detail:
    "CoVe: Q1={pass|corrected}, Q2={pass|corrected}, Q3={pass|corrected}"
```

**Anti-pattern (AP-03 Verification Theater):** Pro-forma "no issues found" without genuine adversarial reasoning = CoVe violation. Gatekeeper MUST reject HAND-02 tokens where CoVe summary contains generic language not tied to the specific artifact.

---

## § Build Operations

### BUILD-01: Pre-compile Scan

**Authorized:** PaperCompiler | **Phase:** Start of VERIFY (paper domain)

```sh
# KL-12: math in titles/captions not wrapped in \texorpdfstring
grep -n "\\\\section\|\\\\subsection\|\\\\caption" paper/sections/*.tex | grep "\$" | grep -v "texorpdfstring"
# Hard-coded numeric cross-references
grep -n "\\\\ref{[a-z]*:[0-9]" paper/sections/*.tex
# Inconsistent label prefixes (valid: sec: eq: fig: tab: alg:)
grep -n "\\\\label{" paper/sections/*.tex | grep -v "label{sec:\|label{eq:\|label{fig:\|label{tab:\|label{alg:"
# Relative positional language
grep -ni "\bbove\b\|\bbelow\b\|\bfollowing figure\b\|\bpreceding\b" paper/sections/*.tex
```

Fix KL-12 violations before BUILD-02. No exceptions.

### BUILD-02: LaTeX Compilation

**Authorized:** PaperCompiler | **Phase:** VERIFY (paper domain)

```sh
cd paper/
{engine} -interaction=nonstopmode -halt-on-error {main_file}.tex
bibtex {main_file}
{engine} -interaction=nonstopmode -halt-on-error {main_file}.tex
{engine} -interaction=nonstopmode -halt-on-error {main_file}.tex
```

`{engine}` = `pdflatex` (default) | `xelatex` | `lualatex`

---

## § Test Operations

### TEST-01: pytest Execution

**Authorized:** TestRunner | **Phase:** VERIFY (code domain)

```sh
python -m pytest {target} -v --tb=short 2>&1 | tee tests/last_run.log
```

On failure: parse log, run TEST-02, formulate hypotheses with confidence scores → STOP; output Diagnosis Summary; ask user. Do NOT retry or patch silently.

### TEST-02: Convergence Analysis

**Authorized:** TestRunner | **Phase:** VERIFY

`slope(Nᵢ, Nᵢ₊₁) = log(e[Nᵢ] / e[Nᵢ₊₁]) / log(Nᵢ₊₁ / Nᵢ)`
**Acceptance:** all slopes ≥ `expected_order − 0.2`

**Mandatory output table:**
```
| N   | L∞ error | slope |
|-----|----------|-------|
| 32  | {e_32}   | —     |
| 64  | {e_64}   | {s1}  |
| 128 | {e_128}  | {s2}  |
| 256 | {e_256}  | {s3}  |

Expected order: {expected_order}
Observed range: {min_slope} – {max_slope}
Verdict: PASS | FAIL
```

---

## § Experiment Operations

### EXP-01: Simulation Execution

**Authorized:** ExperimentRunner | **Phase:** EXECUTE

```sh
python -m src.twophase.run --config {config_file} --output {output_dir} --seed {seed} 2>&1 | tee {output_dir}/run.log
```

`{seed}` = 42 (default). `{config_file}` must be committed before run. On failure → STOP; report; do not silently retry.

### EXP-02: Mandatory Sanity Checks

**Trigger:** MANDATORY after every EXP-01. Do not forward results until all 4 pass.

| ID | Check | Criterion | Failure action |
|----|-------|-----------|----------------|
| SC-1 | Static droplet pressure jump | `|dp_measured − 4σ/d| / (4σ/d) ≤ 0.27` at ε=1.5h | STOP → report |
| SC-2 | Convergence slope | log-log slope ≥ (expected_order − 0.2) | STOP → report |
| SC-3 | Spatial symmetry | `max|f − flip(f, axis)| < 1e-12` | STOP → report |
| SC-4 | Mass conservation | `|Δmass| / mass₀ < 1e-4` over full run | STOP → report |

---

## § Audit Operations

### AUDIT-01: AU2 Release Gate

**Authorized:** ConsistencyAuditor | **Trigger:** MANDATORY before any merge to `main`

All 10 items must pass. A single FAIL blocks merge.

| # | Item | Failure routing |
|---|------|----------------|
| 1 | Equation = discretization = solver (3-layer traceability A3) | per error type |
| 2 | LaTeX tag integrity (no raw math in titles/captions — KL-12) | PaperWriter |
| 3 | Infrastructure non-interference (A5: infra changes do not alter numerical results) | CodeArchitect |
| 4 | Experiment reproducibility (EXP-02 SC-1–4 all passed) | ExperimentRunner |
| 5 | Assumption validity (ASM-IDs in ACTIVE state, no silent promotion) | coordinator |
| 6 | Traceability from claim to implementation (paper claim → code line) | per error type |
| 7 | Backward compatibility of schema changes (A7) | CodeArchitect |
| 8 | No redundant memory growth (02_ACTIVE_LEDGER.md §LESSONS not stale) | coordinator |
| 9 | Branch policy compliance (A8: no direct commits on main) | coordinator |
| 10 | Merge authorization compliance (VALIDATED required; TEST-PASS, BUILD-SUCCESS, LOG-ATTACHED) | coordinator |

**Error routing (items 1, 2, 3, 6):** PAPER_ERROR → PaperWriter; CODE_ERROR → CodeArchitect → TestRunner; authority conflict → STOP → user.
**Verdict:** AU2 PASS unlocks GIT-04.

### AUDIT-02: Verification Procedures A–E

**Authorized:** ConsistencyAuditor | **Trigger:** Part of AUDIT-01 items 1, 6

| Procedure | Description | Output |
|-----------|-------------|--------|
| A | Independent derivation from first principles | Re-derived formula or stencil |
| B | Code–paper line-by-line comparison (symbol, index, sign conventions) | Match/mismatch table |
| C | MMS test result interpretation (TEST-02 output) | PASS/FAIL verdict per component |
| D | Boundary scheme derivation (ghost cell treatment at domain walls) | Boundary stencil verification |
| E | Authority chain conflict: MMS-passing code > docs/01_PROJECT_MAP.md §6 > paper | Definitive verdict on wrong artifact |

**Procedure A — Two-Path Requirement:** When ≥2 plausible interpretations exist:
- Path 1: direct Taylor expansion from governing PDE
- Path 2: operator algebra (matrix form or spectral analysis)
- Both agree → PASS. Disagree → STOP-HARD; HAND-02 `status: REJECT`. Do NOT average or pick one.

### AUDIT-03: Adversarial Edge-Case Gate

**Authorized:** ConsistencyAuditor | **Trigger:** MANDATORY for FULL-PIPELINE; OPTIONAL for FAST-TRACK

| Step | Action |
|------|--------|
| 1 | Identify boundary conditions → `artifacts/Q/edge_case_list_{id}.md` |
| 2 | Predict expected behavior from T-Domain for each edge case |
| 3 | Probe artifact (run test, trace code, or derive analytically) |
| 4 | Compare expected vs. actual; classify: THEORY_ERR / IMPL_ERR / SCOPE_LIMIT |

Edge cases (code): ρ→0, μ→0, Δt→0; contrast ratio >1000; interface on grid edge; sphere of radius h.
Edge cases (paper): equations at domain boundaries; limiting cases; sign at negative coordinates.
AUDIT-03 PASS if all = PASS or SCOPE_LIMIT (documented). FAIL → route per error type.

### PATCH-IF: Interface Patch Protocol

**Authorized:** ResearchArchitect (with explicit user confirmation) | **[AUTH_LEVEL: Root Admin]**
**Trigger:** Downstream domain finds minor error in upstream Interface Contract

```
PATCH-IF {target_interface} --scope {minimal_change}
```

| Scope | Definition | Action |
|-------|-----------|--------|
| MINOR | Typo, unit label, clarification note — no API or math change | ResearchArchitect patches + re-signs; downstream resumes |
| FUNCTIONAL | API signature, equation form, operator structure, boundary conditions | PATCH-IF DENIED → run full CI/CP |

**Hard rule:** at most ONE PATCH-IF per Interface Contract version. Two patches = FUNCTIONAL scope → CI/CP.

---

## § Knowledge Operations

| Operation | Auth Level | Trigger | Steps |
|-----------|-----------|---------|-------|
| **K-COMPILE** | Specialist (KnowledgeArchitect) | Domain artifact at VALIDATED | 1. Verify source VALIDATED. 2. Check docs/wiki/ for duplicate (SSoT K-A3) → K-REFACTOR if found. 3. Extract structured knowledge; compose entry. 4. Link refs using `[[REF-ID]]`; commit to dev/K branch; open PR → wiki |
| **K-LINT** | Gatekeeper (WikiAuditor) | Before wiki merge; periodic | 1. Scan all `[[REF-ID]]` pointers; verify each target exists and ACTIVE. 2. Check SSoT violations; verify sources still VALIDATED. 3. Zero broken pointers + zero SSoT violations → K-LINT PASS. Any broken pointer → STOP-HARD (K-A2) |
| **K-DEPRECATE** | Gatekeeper (WikiAuditor) | Source artifact invalidated | 1. Set entry `status: DEPRECATED` (or SUPERSEDED with `superseded_by`). 2. Emit RE-VERIFY signal to all consuming domains. 3. Record in `docs/wiki/changelog/`. Cascade depth > 10 → STOP; escalate |
| **K-REFACTOR** | Specialist (TraceabilityManager) | K-LINT reports duplicate | 1. Identify canonical entry; replace duplicate content with `[[REF-ID]]` pointers. 2. Verify no semantic loss; run K-LINT. 3. Commit to dev/K; open PR with before/after pointer map. Semantic meaning would change → STOP; escalate |
| **K-IMPACT-ANALYSIS** | Specialist (Librarian) | Before K-DEPRECATE | 1. Trace direct consumers (entries with `depends_on: [[{ref_id}]]`). 2. Trace transitive consumers; estimate cascade depth. Cascade depth > 10 → STOP; escalate |

---

## § STOP Conditions Table (Complete)

| ID | Condition | Trigger | Action | Profile |
|----|-----------|---------|--------|---------|
| STOP-01 | Main branch contamination | Non-Root-Admin commits to `main` | SYSTEM_PANIC → revert + escalate | all |
| STOP-02 | Immutable Zone modification | Change to φ-principles, axioms, or HAND-03 logic | SYSTEM_PANIC → escalate | all |
| STOP-03 | Domain lock violation | Write outside DOMAIN-LOCK territory | CONTAMINATION RETURN → Gatekeeper rejects PR | all |
| STOP-04 | Branch isolation breach | Access to another agent's `dev/` branch | CONTAMINATION RETURN → Gatekeeper rejects PR | all |
| STOP-05 | GIT-SP skipped | File changes without invoking `scripts/git-sp.sh` | SYSTEM_PANIC → invoke GIT-SP and restart | all |
| STOP-06 | Context leakage | Downstream consumes upstream conversation history | Context Leakage Violation → re-dispatch | all |
| STOP-07 | Loop > MAX_REVIEW_ROUNDS | P-E-V-A loop exceeds 5 iterations | STOPPED → escalate to user | all |
| STOP-08 | Hash mismatch (INTEGRITY_MANIFEST) | Upstream contract hash ≠ recorded | CONTAMINATION → CI/CP re-propagation | all |
| STOP-09 | Base-directory destruction (v5.1) | Worktree created inside `$REPO_ROOT` or non-sibling path | SYSTEM_PANIC → escalate; human removes worktree | worktree |
| STOP-10 | Foreign branch-lock force (v5.1) | LOCK-ACQUIRE collides with existing lock, OR LOCK-RELEASE without ownership match, OR lock/LEDGER divergence | CONTAMINATION RETURN → HAND-02 REJECT; no destructive recovery; human adjudicates | worktree |
| STOP-11 | Atomic-push rebase conflict (v5.1) | GIT-ATOMIC-PUSH rebase step reports conflicts | STOP-SOFT — `git rebase --abort`; HAND-02 FAIL, `lock_released: false`; human resolves | worktree |
| STOP-12 | Dual handoff emission (RESERVED) | Same session emits both text-format AND tool-call HAND for same token | RESERVED — not yet active; fires only when `handoff_mode == "tool_use"` (v1.2+) | — |

STOP-09/10/11 only fire when `concurrency_profile == "worktree"`.

---

## § Command Format

```
Initialize
Execute [AgentName]
Execute [filename]
```

- `Initialize` = invoke ResearchArchitect with `docs/02_ACTIVE_LEDGER.md`
- `Execute [AgentName]` = invoke by role name
- `Execute [filename]` = load from `prompts/agents-{env}/{filename}.md`
- One command per step (P5)

---

## Cross-References

- `→ WIKI-M-001`: v5.1 concurrency (LOCK-ACQUIRE/RELEASE, GIT-ATOMIC-PUSH context)
- `→ WIKI-M-002`: v4.1 Schema-in-Code (HandoffEnvelope SSoT rationale)
- `→ WIKI-M-013`: LEAN_METASTACK_2024 (HAND-01 14→4 fields compression)
- `→ WIKI-M-019`: Workflow protocols (how these operations compose in P-E-V-A)
- `→ WIKI-M-022`: Reconstruction runbook (how to use these ops to verify a fresh deployment)
