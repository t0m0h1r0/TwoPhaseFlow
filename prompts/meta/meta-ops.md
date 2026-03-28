# META-OPS: Operational Command Specifications & Handoff Protocols
# ABSTRACT LAYER — canonical commands, parameters, success criteria, and handoff structures.
# FOUNDATION (φ1–φ7, A1–A10): prompts/meta/meta-core.md  ← READ FIRST
# Role bindings (who may invoke): prompts/meta/meta-roles.md §AUTHORITY
# Execution timing (when to invoke): prompts/meta/meta-workflow.md §DOMAIN PIPELINES

────────────────────────────────────────────────────────
# § PHILOSOPHY

This file answers: **HOW does each agent execute its operations and communicate with others?**

This file defines two categories:

1. **Operations** (GIT-xx, BUILD-xx, TEST-xx, EXP-xx): canonical commands with parameters,
   success criteria, and failure handling. Invoked by agents with the corresponding AUTHORITY.

2. **Handoff Protocols** (HAND-xx): structured communication tokens for agent-to-agent
   delegation and handback. Used every time control passes between agents.

Operations are canonical: meta-roles.md defines AUTHORITY (permission), meta-workflow.md defines
WHEN; this file defines the exact command. Improvised variants are violations.

Handoff protocols are canonical: informal handoffs bypass the verification layer and break
traceability (φ1, φ4). Canonical tokens make every transfer auditable.

**Relationship: AUTHORITY → OPERATION**
AUTHORITY = permission to act; OPERATION = the canonical form that must be used.
No AUTHORITY → must not invoke. Has AUTHORITY → must use canonical form.

**Parameter notation**

`{param}` — required substitution; agent derives value from context
`[param]` — optional; include only when condition is met
`{branch}` — always one of: `code` | `paper` | `prompt` per domain
`{summary}` — required one-line description; must be specific (not "update" or "fix")

────────────────────────────────────────────────────────
# § AUTHORITY TIERS

Three tiers determine which git operations each agent may invoke:

| Tier | Role | Agents |
|------|------|--------|
| **Root Admin** (Overseer) | Final merge + syntax/format check of PRs to `main` | ResearchArchitect |
| **Gatekeeper** (Integrator) | Domain branch management; PR review + merge from dev/; PR issuance to main | CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptArchitect, PromptAuditor |
| **Specialist** (Developer) | Absolute sovereignty over own `dev/{agent_role}` branch; right to refuse pulls | CodeArchitect, CodeCorrector, CodeReviewer, TestRunner, ExperimentRunner, PaperWriter, PaperReviewer, PaperCompiler, PaperCorrector, ConsistencyAuditor, PromptCompressor |

**Specialist obligations:** Must attach Evidence of Verification (logs/test results) to every PR.
**Gatekeeper rights:** May immediately reject PRs with insufficient or missing evidence.
**Root Admin obligations:** Final syntax/format check of PRs to `main`; executes final merge.

────────────────────────────────────────────────────────
# § ROLE → OPERATION INDEX

Quick reference: which operations and handoff roles each agent has.

| Tier | Role | Operations | Handoff Role |
|------|------|------------|-------------|
| Root Admin | ResearchArchitect | GIT-01 (auto-switch only), GIT-04 (final merge to main) | DISPATCHER |
| Gatekeeper | CodeWorkflowCoordinator | GIT-00 (IF-Agreement), GIT-01, DOM-01, GIT-02, GIT-03, GIT-04 (domain PR review+merge), GIT-05 | DISPATCHER + ACCEPTOR |
| Gatekeeper | PaperWorkflowCoordinator | GIT-00 (IF-Agreement), GIT-01, DOM-01, GIT-02, GIT-03, GIT-04 (domain PR review+merge), GIT-05 | DISPATCHER + ACCEPTOR |
| Gatekeeper | PromptArchitect | GIT-00 (IF-Agreement), GIT-01, DOM-01, GIT-02 | DISPATCHER + RETURNER |
| Gatekeeper | PromptAuditor | GIT-03, GIT-04 (domain PR review+merge) | RETURNER |
| Specialist | PaperCompiler | GIT-SP, BUILD-01, BUILD-02 | RETURNER |
| Specialist | TestRunner | GIT-SP, TEST-01, TEST-02 | RETURNER |
| Specialist | ExperimentRunner | GIT-SP, EXP-01, EXP-02 | RETURNER |
| Specialist | CodeArchitect | GIT-SP | RETURNER |
| Specialist | CodeCorrector | GIT-SP | RETURNER |
| Specialist | CodeReviewer | GIT-SP | RETURNER |
| Specialist | PaperWriter | GIT-SP | RETURNER |
| Specialist | PaperReviewer | GIT-SP | RETURNER |
| Specialist | PaperCorrector | GIT-SP | RETURNER |
| Specialist | ConsistencyAuditor | GIT-SP, AUDIT-01, AUDIT-02 | RETURNER |
| Specialist | PromptCompressor | GIT-SP | RETURNER |

**Handoff roles:**
- DISPATCHER: sends HAND-01 (DISPATCH token) when delegating to a specialist
- RETURNER: sends HAND-02 (RETURN token) when completing work and handing back
- ACCEPTOR: receives HAND-02 and performs HAND-03 (Acceptance Check) before continuing

Any agent attempting to invoke an operation it is not listed for is exceeding its
authority (φ2: Minimal Footprint).

**DOM-02 exception:** DOM-02 (Pre-Write Storage Check) is a universal obligation —
every agent runs it before every write, regardless of the table above. It requires
no AUTHORITY grant because it is a constraint on all writes, not an operation.

────────────────────────────────────────────────────────
# § MERGE CRITERIA

Every PR (dev/{agent_role} → {domain} OR {domain} → main) must satisfy all three criteria
before a Gatekeeper or Root Admin may merge it:

| ID | Criterion | Verified by | Failure action |
|----|-----------|------------|----------------|
| TEST-PASS | 100% success rate of defined unit/validation tests | TestRunner (TEST-01/02) or equivalent | REJECT PR; re-dispatch Specialist |
| BUILD-SUCCESS | Successful static analysis, compilation, or linting | PaperCompiler (BUILD-01/02) or pytest | REJECT PR; re-dispatch Specialist |
| LOG-ATTACHED | Execution logs attached as a comment in the PR | Specialist includes `tests/last_run.log` or equivalent | REJECT PR; Specialist must re-submit with logs |

**Gatekeeper obligation:** Reject immediately if any criterion is unmet — do not merge and expect fixes post-merge.

────────────────────────────────────────────────────────
# § GIT OPERATIONS

────────────────────────────────────────────────────────
## GIT-00: IF-Agreement + Specialist Branch Setup

**Authorized:** Gatekeepers (CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptArchitect)
**Trigger:** MANDATORY — before dispatching any Specialist; precondition for GIT-01
**Phase:** Before PLAN

```sh
# Step 1 — Write interface contract (Gatekeeper only)
# Create/update interface/{domain}_{feature}.md with IF-AGREEMENT block
# (see meta-domains.md §IF-AGREEMENT PROTOCOL for required fields)

# Step 2 — Commit interface contract on interface/ branch
git checkout interface/ 2>/dev/null || git checkout -b interface/
git add interface/{domain}_{feature}.md
git commit -m "interface/{domain}: define {feature} contract"
git checkout {domain}   # return to domain branch

# Step 3 — Specialist reads the contract and creates dev/ branch
# (run by Specialist after receiving DISPATCH with IF-AGREEMENT path)
git checkout {domain}
git checkout -b dev/{agent_role}
```

**Success:** `interface/{domain}_{feature}.md` committed; Specialist confirms `git branch --show-current` = `dev/{agent_role}`

**On failure:**
- interface/ write fails → STOP; escalate to user
- Specialist cannot checkout {domain} → run GIT-01 first

────────────────────────────────────────────────────────
## GIT-SP: Specialist Branch Operations

**Authorized:** All Specialist-tier agents (sovereign over their own dev/ branch)
**Trigger:** Whenever a Specialist commits work or opens a PR
**Phase:** During EXECUTE or VERIFY

```sh
# Commit work (Specialist's own dev/ branch only)
git add {files}
git commit -m "dev/{agent_role}: {summary} [LOG-ATTACHED]"

# Open PR from dev/ → {domain} (after work is complete with evidence)
# Attach tests/last_run.log or BUILD-01 scan output as PR comment
gh pr create \
  --base {domain} \
  --head dev/{agent_role} \
  --title "{agent_role}: {summary}" \
  --body "Evidence: [LOG-ATTACHED — see tests/last_run.log or build log attached below]"
```

**Specialist rights:**
- Absolute sovereignty over `dev/{agent_role}` — may commit, amend, rebase freely BEFORE PR submission
- May refuse a Gatekeeper's request to pull from main if neither Selective Sync condition is met
  (→ meta-domains.md §SELECTIVE SYNC PROTOCOL)

**Specialist obligations:**
- Must attach Evidence of Verification with every PR (LOG-ATTACHED criterion)
- Must include `tests/last_run.log` or equivalent build output in PR comment

**Isolation rule:** Specialist MUST NOT access any other agent's `dev/` branch.
Violation → CONTAMINATION RETURN + Branch Isolation breach (→ meta-domains.md §BRANCH ISOLATION).

────────────────────────────────────────────────────────
## GIT-01: Branch Preflight

**Authorized:** Gatekeepers (CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptArchitect),
               Root Admin ResearchArchitect (Step 0 auto-switch only — see below)
**Trigger:** MANDATORY — first action of every session, before any GIT-00 dispatch or file edit;
             ALSO triggered automatically when ResearchArchitect detects a branch/domain mismatch
             on a user-issued request (Usability Exception — see below)
**Phase:** Before PLAN

```sh
# Step 1 — Branch Validation (Gatekeeper confirms domain integration branch)
current=$(git branch --show-current)
if [ "$current" != "{branch}" ]; then
  # Auto-Switch (Usability Exception): do not block user with wrong-branch error
  git checkout {branch} 2>/dev/null || git checkout -b {branch}
fi

# Step 2 — Selective Sync: pull latest main into domain branch
# Only if interface/ was updated OR a merge conflict is present (→ meta-domains.md §SELECTIVE SYNC)
git fetch origin main
git merge origin/main --no-edit

# Step 3 — Confirm
git branch --show-current
```

**Parameters**
| Param | CodeWorkflowCoordinator | PaperWorkflowCoordinator | PromptArchitect |
|-------|------------------------|--------------------------|----------------|
| `{branch}` | `code` | `paper` | `prompt` |

**Auto-Switch (Usability Exception):** When the current branch does not match the target
domain, Step 1 executes the checkout automatically — the caller must not block on a
"wrong branch" error at the entry point. The caller derives `{branch}` from the task's
target domain before invoking GIT-01 (see meta-roles.md for per-role branch mapping).

**Unknown branch detection:** If `git branch --show-current` returns a value that does not
appear in the domain branch map (`code` | `paper` | `prompt` | `main`), report
CONTAMINATION immediately:
```
CONTAMINATION ALERT: current branch '{current}' is not in the domain registry.
Do not proceed. Escalate to user for branch cleanup.
```

**Success:** `git branch --show-current` prints `{branch}` — not `main`;
             `git merge origin/main` exits code 0

**On failure**
- Checkout result is `main` → **STOP**; do not proceed under any circumstance
- Merge conflict → **STOP**; report to user; do not resolve unilaterally
- `git fetch` network error → **STOP**; report; do not proceed on stale state

**Post-success:** immediately run DOM-01 to establish the session domain lock.

────────────────────────────────────────────────────────
# § DOMAIN OPERATIONS

────────────────────────────────────────────────────────
## DOM-01: Domain Lock Establishment

**Authorized:** CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptArchitect
**Trigger:** MANDATORY — immediately after GIT-01 confirms branch; before any DISPATCH or file edit
**Phase:** Session start

Establishes the session domain lock. Without it, DOM-02 pre-write checks cannot run
and HAND-03 check 6 will block all specialists.

```
DOMAIN-LOCK:
  domain:          {Code | Paper | Prompt}
  branch:          {git branch --show-current}
  set_by:          {self — coordinator name}
  set_at:          {git log --oneline -1 | cut -c1-7}
  write_territory: {from meta-domains.md §DOMAIN REGISTRY "Storage (write)" for active domain}
  read_territory:  {from meta-domains.md §DOMAIN REGISTRY "Storage (read)" for active domain}
```

**Domain → territory mapping (quick reference):**

| Domain | write_territory | read_territory |
|--------|----------------|----------------|
| Code | `src/twophase/`, `tests/`, `docs/02_ACTIVE_LEDGER.md` | `paper/sections/*.tex`, `docs/01_PROJECT_MAP.md` |
| Paper | `paper/sections/*.tex`, `paper/bibliography.bib`, `docs/02_ACTIVE_LEDGER.md` | `src/twophase/` |
| Prompt | `prompts/agents/*.md` | `prompts/meta/*.md` |

**Output:** DOMAIN-LOCK block recorded in session context; copied verbatim into every
subsequent HAND-01 `context.domain_lock` field.

**On failure:**
- GIT-01 returned `main` → cannot establish lock; STOP (GIT-01 failure path handles this)
- Branch does not match any known domain → STOP; report to user

────────────────────────────────────────────────────────
## DOM-02: Pre-Write Storage Check

**Authorized:** every agent (universal obligation — no AUTHORITY restriction)
**Trigger:** MANDATORY — before every file write, edit, or delete
**Phase:** Any

```
□ 1. Retrieve DOMAIN-LOCK from the DISPATCH token received at session start.
     Absent → STOP; request domain lock from coordinator; do not write.
□ 2. Resolve target_path against write_territory (prefix match).
     Match found   → proceed with write.
     Read-only hit → STOP; do not write; return read data only; notify coordinator.
     No match      → STOP; issue CONTAMINATION_GUARD RETURN (see meta-domains.md §CONTAMINATION GUARD).
```

**Exemptions:** none. `docs/02_ACTIVE_LEDGER.md` is writable by all domains but still
requires DOM-02 — the check passes because all domains include it in write_territory.

────────────────────────────────────────────────────────
## GIT-02: DRAFT Commit

**Authorized:** CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptArchitect
**Trigger:** Primary creation agent completes and returns to coordinator
**Phase:** End of EXECUTE

```sh
git add {files}
git commit -m "{branch}: draft — {summary}"
```

**Parameters**
- `{files}` — explicit file paths (never `-A`; prevents accidental staging of secrets or binaries)
- `{branch}` — active domain branch
- `{summary}` — concrete description, e.g. "implement pressure Poisson solver", "expand §3 derivation"

**Success:** exit code 0; commit hash appears in output

────────────────────────────────────────────────────────
## GIT-03: REVIEWED Commit

**Authorized:** CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptAuditor
**Trigger:** Review phase exits with no blocking findings
**Phase:** End of VERIFY (TestRunner PASS / PaperReviewer 0 FATAL+0 MAJOR / PromptAuditor Q3 PASS)

```sh
git add {files}
git commit -m "{branch}: reviewed — {summary}"
```

**Parameters:** same as GIT-02

**Success:** exit code 0

────────────────────────────────────────────────────────
## GIT-04: VALIDATED Commit + PR Merge

**Phase A — Gatekeeper (merges dev/ PR into domain branch):**
**Authorized:** Gatekeepers (CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptAuditor)
**Trigger:** Gate auditor (ConsistencyAuditor or PromptAuditor) issues PASS verdict AND
             all three MERGE CRITERIA (TEST-PASS, BUILD-SUCCESS, LOG-ATTACHED) are satisfied
**Phase:** End of AUDIT

```sh
# Gatekeeper: merge dev/ PR into domain branch (after evidence verification)
git checkout {branch}
git merge dev/{agent_role} --no-ff -m "{branch}: validated — {summary}"

# Gatekeeper: immediately open PR from domain → main
gh pr create \
  --base main \
  --head {branch} \
  --title "merge({branch} → main): {summary}" \
  --body "AU2 PASS. MERGE CRITERIA: TEST-PASS ✓ BUILD-SUCCESS ✓ LOG-ATTACHED ✓"
```

**Phase B — Root Admin (final check + merge to main):**
**Authorized:** Root Admin (ResearchArchitect)
**Trigger:** Gatekeeper opens PR to main; Root Admin performs final syntax/format check
**Phase:** Final gate before main

```sh
# Root Admin: verify PR contents (syntax, format, no direct-main commits)
# If check passes:
git checkout main
git merge {branch} --no-ff -m "merge({branch} → main): {summary}"
git checkout {branch}
```

**Parameters:** same as GIT-02; `--no-ff` preserves branch topology in history

**Root Admin check items before final merge:**
1. No direct commits on `main` (A8 compliance)
2. PR title follows `merge({branch} → main): {summary}` format
3. AU2 PASS verdict present in PR body
4. All three MERGE CRITERIA confirmed in PR body

**Success:** merge completes; `git log --oneline -3` on `main` shows the merge commit

**On failure**
- Root Admin check fails → REJECT PR; return to Gatekeeper with reason
- Merge conflict → **STOP**; report to user; do not resolve unilaterally
- Post-merge failure detected → revert: `git revert -m 1 HEAD` on `main`; **STOP**; report

────────────────────────────────────────────────────────
## GIT-05: Sub-branch Operations

**Authorized:** CodeWorkflowCoordinator, PaperWorkflowCoordinator
**Trigger:** Task requires isolation within a domain (e.g., experimental refactor, parallel sections)

**Create sub-branch from parent:**
```sh
git checkout {parent}
git checkout -b {parent}/{feature}
```

**Merge sub-branch back to parent (never to `main`):**
```sh
git checkout {parent}
git merge {parent}/{feature} --no-ff -m "merge({parent}/{feature} → {parent}): {summary}"
```

**Parameters**
- `{parent}` — `code` or `paper` (never `main`)
- `{feature}` — short snake_case descriptor, e.g. `ccd_refactor`, `section3_rewrite`
- `{summary}` — one-line description

**Rule:** Sub-branches merge only to their parent branch. The parent branch reaches `main`
via GIT-04 after VALIDATED phase.

────────────────────────────────────────────────────────
# § BUILD OPERATIONS

────────────────────────────────────────────────────────
## BUILD-01: Pre-compile Scan

**Authorized:** PaperCompiler
**Trigger:** MANDATORY before any BUILD-02 invocation
**Phase:** Start of VERIFY (paper domain)

Scan for known authoring trap patterns:

```sh
# KL-12: math in section/caption titles not wrapped in \texorpdfstring
grep -n "\\\\section\|\\\\subsection\|\\\\caption" paper/sections/*.tex \
  | grep "\$" | grep -v "texorpdfstring"

# Hard-coded numeric cross-references
grep -n "\\\\ref{[a-z]*:[0-9]" paper/sections/*.tex

# Inconsistent label prefixes (valid: sec: eq: fig: tab: alg:)
grep -n "\\\\label{" paper/sections/*.tex \
  | grep -v "label{sec:\|label{eq:\|label{fig:\|label{tab:\|label{alg:"

# Relative positional language
grep -ni "\bbove\b\|\bbelow\b\|\bfollowing figure\b\|\bpreceding\b" paper/sections/*.tex
```

**Success:** No matches (or all matches reviewed and documented as false positives)

**On finding:** Fix violation before running BUILD-02. KL-12 violations must be fixed — no exceptions.

────────────────────────────────────────────────────────
## BUILD-02: LaTeX Compilation

**Authorized:** PaperCompiler
**Trigger:** After BUILD-01 scan passes
**Phase:** VERIFY (paper domain)

```sh
cd paper/
{engine} -interaction=nonstopmode -halt-on-error {main_file}.tex
bibtex {main_file}
{engine} -interaction=nonstopmode -halt-on-error {main_file}.tex
{engine} -interaction=nonstopmode -halt-on-error {main_file}.tex
```

**Parameters**
- `{engine}` = `pdflatex` (default) | `xelatex` | `lualatex`
- `{main_file}` = root tex filename without extension (e.g., `main`)
- Three compiler passes: first builds, bibtex resolves citations, second+third resolve cross-refs

**Success:** final pass exits code 0; log contains no `Undefined reference` or `multiply-defined` warnings

**Log classification (on non-zero exit or warnings)**

| Log pattern | Class | Action |
|-------------|-------|--------|
| `! Undefined control sequence` for known command | STRUCTURAL_FIX | add `\newcommand` or fix typo → re-run |
| `! Missing $ inserted` | STRUCTURAL_FIX | add math delimiters → re-run |
| `! Undefined control sequence` for new content | ROUTE_TO_WRITER | STOP; route to PaperWriter |
| `undefined reference` after 3 passes | STRUCTURAL_FIX | check label/ref spelling → re-run |
| `multiply-defined` label | STRUCTURAL_FIX | rename one label → re-run |
| Package option conflict | STRUCTURAL_FIX | resolve in preamble → re-run |

STRUCTURAL_FIX: apply fix → re-run BUILD-02.
ROUTE_TO_WRITER: STOP; do not attempt further compilation; route to PaperWriter.

────────────────────────────────────────────────────────
# § TEST OPERATIONS

────────────────────────────────────────────────────────
## TEST-01: pytest Execution

**Authorized:** TestRunner
**Trigger:** After CodeArchitect or CodeCorrector completes implementation
**Phase:** VERIFY (code domain)

```sh
python -m pytest {target} -v --tb=short 2>&1 | tee tests/last_run.log
```

**Parameters**
- `{target}` — test file or directory, e.g. `tests/test_pressure_solver.py` or `tests/`
- `-v` — verbose output (required for convergence table extraction)
- `--tb=short` — short traceback (sufficient for diagnosis)
- Output always tee'd to `tests/last_run.log` (overwrite each run)

**Success:** all tests PASS; exit code 0; run TEST-02 to confirm convergence

**On failure**
1. Parse `tests/last_run.log` → extract error values and convergence slopes
2. Run TEST-02 on failing tests to construct convergence table
3. Formulate hypotheses with confidence scores
4. **STOP** — output Diagnosis Summary; ask user for direction
5. Do not retry; do not generate patches

────────────────────────────────────────────────────────
## TEST-02: Convergence Analysis

**Authorized:** TestRunner
**Trigger:** After TEST-01 (on both PASS and FAIL)
**Phase:** VERIFY (code domain)

**Computation:** for error values `e[N]` at N ∈ {32, 64, 128, 256}:

```
slope(Nᵢ, Nᵢ₊₁) = log(e[Nᵢ] / e[Nᵢ₊₁]) / log(Nᵢ₊₁ / Nᵢ)
```

**Acceptance criterion:** all observed slopes ≥ `expected_order − 0.2`

**Required output table:**

```
| N   | L∞ error   | slope |
|-----|------------|-------|
| 32  | {e_32}     | —     |
| 64  | {e_64}     | {s1}  |
| 128 | {e_128}    | {s2}  |
| 256 | {e_256}    | {s3}  |

Expected order: {expected_order}
Observed range: {min_slope} – {max_slope}
Verdict: PASS | FAIL
```

This table is mandatory in every TestRunner output — PASS or FAIL.

────────────────────────────────────────────────────────
# § EXPERIMENT OPERATIONS

────────────────────────────────────────────────────────
## EXP-01: Simulation Execution

**Authorized:** ExperimentRunner
**Trigger:** After parameter validation against benchmark spec
**Phase:** EXECUTE (experiment step, optional in code pipeline)

```sh
python -m src.twophase.run \
  --config {config_file} \
  --output {output_dir} \
  --seed {seed} \
  2>&1 | tee {output_dir}/run.log
```

**Parameters**
- `{config_file}` — experiment configuration file (JSON or YAML; must be committed before run)
- `{output_dir}` — result directory, e.g. `results/{experiment_id}/`; created if absent
- `{seed}` = 42 (default; override only when explicitly authorized)

**Success:** exit code 0; all expected output files present in `{output_dir}`

**On failure:** STOP; report to user; do not modify parameters and retry silently

────────────────────────────────────────────────────────
## EXP-02: Mandatory Sanity Checks

**Authorized:** ExperimentRunner
**Trigger:** MANDATORY after every EXP-01; results must NOT be forwarded until all four pass
**Phase:** VERIFY (experiment step)

| ID | Check | Criterion | Failure action |
|----|-------|-----------|----------------|
| SC-1 | Static droplet pressure jump | `\|dp_measured − 4σ/d\| / (4σ/d) ≤ 0.27` at ε=1.5h | STOP → report |
| SC-2 | Convergence slope | log-log slope ≥ (expected_order − 0.2) | STOP → report |
| SC-3 | Spatial symmetry | `max\|f − flip(f, axis)\| < 1e-12` | STOP → report |
| SC-4 | Mass conservation | `\|Δmass\| / mass₀ < 1e-4` over full run | STOP → report |

Any single FAIL → STOP; do not forward results to PaperWriter; report which check failed with measured value.

────────────────────────────────────────────────────────
# § AUDIT OPERATIONS

────────────────────────────────────────────────────────
## AUDIT-01: AU2 Release Gate

**Authorized:** ConsistencyAuditor
**Trigger:** MANDATORY before any merge to `main` (Code and Paper domains)
**Phase:** AUDIT

All 10 items must pass. A single FAIL blocks merge. No item may be skipped.

| # | Item | Failure action |
|---|------|---------------|
| 1 | Equation = discretization = solver (3-layer traceability A3) | FAIL → route per error type |
| 2 | LaTeX tag integrity (no raw math in titles/captions — KL-12) | FAIL → PaperWriter |
| 3 | Infrastructure non-interference (A5: infra changes do not alter numerical results) | FAIL → CodeArchitect |
| 4 | Experiment reproducibility (EXP-02 SC-1–4 all passed) | FAIL → ExperimentRunner |
| 5 | Assumption validity (ASM-IDs in ACTIVE state, no silent promotion) | FAIL → coordinator |
| 6 | Traceability from claim to implementation (paper claim → code line) | FAIL → per error type |
| 7 | Backward compatibility of schema changes (A7) | FAIL → CodeArchitect |
| 8 | No redundant memory growth (02_ACTIVE_LEDGER.md §LESSONS not stale) | FAIL → coordinator |
| 9 | Branch policy compliance (A8: no direct commits on main; dev/ → domain via PR; domain → main via Root Admin PR) | FAIL → coordinator |
| 10 | Merge authorization compliance (VALIDATED phase required; all MERGE CRITERIA satisfied — TEST-PASS, BUILD-SUCCESS, LOG-ATTACHED) | FAIL → coordinator |

**Error routing (for items 1, 2, 3, 6):**
- PAPER_ERROR (root cause in paper equation or LaTeX) → PaperWriter
- CODE_ERROR (root cause in src/twophase/) → CodeArchitect → TestRunner
- Authority conflict (sources disagree after derivation) → coordinator → STOP → user

**Verdict:** AU2 PASS unlocks GIT-04 (VALIDATED commit + merge to main).

────────────────────────────────────────────────────────
## AUDIT-02: Verification Procedures A–E

**Authorized:** ConsistencyAuditor
**Trigger:** As part of AUDIT-01 items 1, 6 (equation–code traceability checks)
**Phase:** AUDIT

Five procedures, applied in sequence when verifying mathematical claims:

| Procedure | Description | Output |
|-----------|-------------|--------|
| A | Independent derivation from first principles (Taylor expansion, matrix structure analysis) | Re-derived formula or stencil |
| B | Code–paper line-by-line comparison (symbol mapping, index convention, sign convention) | Match/mismatch table |
| C | MMS test result interpretation (convergence slopes vs. expected order, TEST-02 output) | PASS/FAIL verdict per component |
| D | Boundary scheme derivation (one-sided differences, ghost cell treatment at domain walls) | Boundary stencil verification |
| E | Authority chain conflict resolution: MMS-passing code > docs/01_PROJECT_MAP.md §6 > paper equation | Definitive verdict on which artifact is wrong |

**Rule:** Procedure E is invoked only when A–D produce conflicting evidence.
Do not resolve authority conflicts by preference — derive and escalate (φ3, A9).

────────────────────────────────────────────────────────
# § COMMAND FORMAT

Canonical syntax for invoking the agent system:

```
Initialize
Execute [AgentName]
Execute [filename]
```

Rules:
- one command sequence per step (P5: single-action discipline)
- no hidden branching; no multi-goal execution; no unbounded continuation
- `Initialize` = invoke ResearchArchitect with current docs/02_ACTIVE_LEDGER.md
- `Execute [AgentName]` = invoke agent by role name; coordinator dispatches sub-agents
- `Execute [filename]` = load agent definition from prompts/agents/{filename}.md

────────────────────────────────────────────────────────
# § HANDOFF PROTOCOL

Handoffs are the structural seams of the pipeline. Every transfer of control
between agents must use these canonical tokens. Informal handoffs ("just tell
the next agent what to do") are violations — they bypass the verification layer
and break audit traceability (φ4).

**Three protocol operations:**
- HAND-01: DISPATCH token — coordinator → specialist (delegation)
- HAND-02: RETURN token — specialist → coordinator (handback)
- HAND-03: Acceptance Check — receiver's first action before any work

────────────────────────────────────────────────────────
## HAND-01: DISPATCH Token

**Sent by:** Coordinators (CodeWorkflowCoordinator, PaperWorkflowCoordinator),
             ResearchArchitect (for initial routing)
**Received by:** Any specialist being delegated to
**Trigger:** When delegating a task to a specialist

```
DISPATCH → {specialist_name}
  task:         {one-sentence objective — what must be produced, not how}
  inputs:       [{file_or_artifact_1}, {file_or_artifact_2}, ...]
  scope_out:    [{explicitly excluded — prevents overreach}]
  context:
    phase:        {PLAN | EXECUTE | VERIFY | AUDIT}
    branch:       {active domain git branch — Specialist will create dev/{agent_role} from this}
    commit:       "{last commit message — confirms git state at dispatch}"
    domain_lock:  {verbatim copy of active DOMAIN-LOCK block from DOM-01}
    if_agreement: {path to interface/{domain}_{feature}.md — MANDATORY for Specialist dispatch}
  expects:      {deliverable description — must match IF-AGREEMENT outputs field}
```

**Rules**
- `task` must be achievable in a single agent session (P5: one objective per step)
- `scope_out` must be non-empty when there is a plausible adjacent task to exclude
- `commit` must match `git log --oneline -1` at dispatch time
- `domain_lock` must be present — a DISPATCH without domain_lock is malformed; specialist must REJECT (HAND-03 check 6)
- Coordinator must not dispatch if its own RETURN token (from a previous step) has
  unresolved issues — resolve first, then dispatch

────────────────────────────────────────────────────────
## HAND-02: RETURN Token

**Sent by:** Any specialist completing work
**Received by:** The coordinator or agent that issued the DISPATCH
**Trigger:** When the specialist's task is complete (or BLOCKED/STOPPED)

```
RETURN → {coordinator_or_requester}
  status:      COMPLETE | PARTIAL | BLOCKED | STOPPED
  produced:    [{file_path}: {one-line description}, ...] | none
  git:
    branch:    {branch}
    commit:    "{commit message of last commit}" | "no-commit"
  verdict:     PASS | FAIL | N/A
  issues:      [{issue description requiring coordinator decision}] | none
  next:        {recommended next step — coordinator decides; this is advisory only}
```

**Status meanings**
| Status | Meaning | Coordinator action |
|--------|---------|--------------------|
| COMPLETE | All deliverables produced; no blocking issues | Continue pipeline |
| PARTIAL | Some deliverables produced; issues prevent full completion | Review issues; decide |
| BLOCKED | Cannot proceed — missing input, authorization, or information | Resolve blocker; re-dispatch |
| STOPPED | STOP condition triggered; human judgment required | Report to user |

**Rules**
- `produced` must list concrete file paths, not vague descriptions
- `verdict` = PASS only if the agent's own success criterion is met (e.g., tests pass, audit passes)
- `issues` must be specific enough for the coordinator to make a decision without re-reading everything
- STOPPED status must include the exact STOP condition that was triggered

────────────────────────────────────────────────────────
## HAND-03: Acceptance Check

**Performed by:** Every agent upon receiving a DISPATCH token, before any work begins
**Trigger:** MANDATORY — first action upon receiving DISPATCH

```
Acceptance Check:
  □ 1. SENDER AUTHORIZED: is the sender listed in meta-roles.md AUTHORITY as allowed
         to dispatch this role? If not → REJECT
  □ 2. TASK IN SCOPE: does the task fall within this role's PURPOSE in meta-roles.md?
         If not → REJECT
  □ 3. INPUTS AVAILABLE: do all listed input files/artifacts exist and are non-empty?
         If not → REJECT
  □ 4. GIT STATE VALID:
         - Specialists: `git branch --show-current` = `dev/{agent_role}` (not main, not domain branch directly)
         - Gatekeepers/Root Admin: run GIT-01 (branch preflight) if not already done this session
         If Specialist is on main or on a domain branch directly → REJECT; run GIT-SP to create dev/ branch
  □ 5. CONTEXT CONSISTENT: does `git log --oneline -1` match the `commit` field in
         the DISPATCH token? (confirms no intervening changes)
         If mismatch → QUERY sender before proceeding
  □ 6. DOMAIN LOCK PRESENT: does `context.domain_lock` exist and include `write_territory`?
         Absent or malformed → REJECT (coordinator must run DOM-01 and re-dispatch)
         domain_lock.branch ≠ domain portion of git branch → REJECT (branch/domain mismatch)
         If PASS → store domain_lock for DOM-02 checks throughout this session
  □ 7. IF-AGREEMENT PRESENT: does DISPATCH context include an `if_agreement` path pointing
         to a valid interface/ contract? (→ meta-domains.md §IF-AGREEMENT PROTOCOL)
         Absent → REJECT; Gatekeeper must run GIT-00 and re-dispatch
         If PASS → read IF-AGREEMENT outputs as the deliverable contract for this task
```

**On REJECT or QUERY:**
Issue a RETURN token immediately with:
```
status:   BLOCKED
produced: none
git:      branch={current}, commit="no-commit"
verdict:  N/A
issues:   ["Acceptance Check failed: {check number} — {specific reason}"]
next:     "Coordinator must resolve before re-dispatching"
```

**On all checks PASS:** proceed with assigned task.

────────────────────────────────────────────────────────
## Handoff Sequence Diagram

```
Coordinator                          Specialist
    │                                    │
    │──── HAND-01 (DISPATCH) ──────────► │
    │                                    │ HAND-03: Acceptance Check
    │                                    │   □ sender authorized?
    │                                    │   □ task in scope?
    │                                    │   □ inputs available?
    │                                    │   □ git state valid?
    │                                    │   □ context consistent?
    │                                    │   □ domain lock present?  ← DOM-01 output
    │                                    │
    │         [REJECT if any fails]      │
    │◄─── HAND-02 (status: BLOCKED) ─── │
    │                                    │
    │         [PASS → work begins]       │
    │                                    │  ... execute task ...
    │                                    │
    │◄─── HAND-02 (RETURN) ──────────── │
    │  status / produced / git /         │
    │  verdict / issues / next           │
    │                                    │
    │ Review issues                      │
    │ If COMPLETE + verdict PASS:        │
    │   → continue pipeline              │
    │ If BLOCKED/STOPPED:                │
    │   → resolve or escalate to user    │
```
