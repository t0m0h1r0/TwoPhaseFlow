# META-OPS: Operational Command Specifications & Handoff Protocols
# VERSION: 3.0.0
# ABSTRACT LAYER — canonical commands, parameters, success criteria, and handoff structures.
# FOUNDATION (φ1–φ7, A1–A11): prompts/meta/meta-core.md  ← READ FIRST
# Role bindings (who may invoke): prompts/meta/meta-roles.md §AUTHORITY
# Execution timing (when to invoke): prompts/meta/meta-workflow.md §DOMAIN PIPELINES

────────────────────────────────────────────────────────
# § PHILOSOPHY

Operations (GIT-xx, BUILD-xx, TEST-xx, EXP-xx): canonical commands. meta-roles.md = WHO; meta-workflow.md = WHEN; this file = exact command. Improvised variants are violations.

Handoff protocols (HAND-xx): informal handoffs bypass the verification layer and break traceability (φ4). Canonical tokens make every transfer auditable.

**Parameter notation:** `{param}` required; `[param]` optional; `{branch}` = `code` | `paper` | `prompt`; `{summary}` = specific one-line description.

────────────────────────────────────────────────────────
# § AUTHORITY TIERS

| Tier | Agents | Obligations |
|------|--------|-------------|
| **Root Admin** | ResearchArchitect | Final merge + syntax/format check of PRs to `main` |
| **Gatekeeper** | CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptArchitect, PromptAuditor, WikiAuditor | Domain branch management; PR review + merge from dev/; PR issuance to main |
| **Specialist** | CodeArchitect, CodeCorrector, CodeReviewer, TestRunner, ExperimentRunner, SimulationAnalyst, PaperWriter, PaperReviewer, PaperCompiler, TheoryArchitect, ConsistencyAuditor, DevOpsArchitect, KnowledgeArchitect, Librarian, TraceabilityManager | Absolute sovereignty over own `dev/{agent_role}` branch; must attach Evidence of Verification to every PR |

- **TheoryAuditor:** git tier = Specialist (`dev/T/TheoryAuditor/`); T-Domain verdict authority = Gatekeeper. Signs `docs/interface/AlgorithmSpecs.md`. No other agent may sign T-Domain Interface Contracts.
- **ConsistencyAuditor:** git tier = Specialist (`dev/Q/ConsistencyAuditor/`); AU2 verdict authority = Gatekeeper. Never commits to domain branches (Broken Symmetry).
- **WikiAuditor:** git tier = Gatekeeper. Manages `wiki` branch; issues K-LINT verdicts. No other agent may approve wiki entries.

────────────────────────────────────────────────────────
# § ROLE → OPERATION INDEX

| Tier | Role | Operations | Handoff Role |
|------|------|------------|-------------|
| Root Admin | ResearchArchitect | GIT-01 (auto-switch only), GIT-04 (final merge to main) | DISPATCHER |
| Gatekeeper | CodeWorkflowCoordinator | GIT-00, GIT-01, DOM-01, GIT-02, GIT-03, GIT-04, GIT-05 | DISPATCHER + ACCEPTOR |
| Gatekeeper | PaperWorkflowCoordinator | GIT-00, GIT-01, DOM-01, GIT-02, GIT-03, GIT-04, GIT-05 | DISPATCHER + ACCEPTOR |
| Gatekeeper | PromptArchitect | GIT-00, GIT-01, DOM-01, GIT-02 | DISPATCHER + RETURNER |
| Gatekeeper | PromptAuditor | GIT-03, GIT-04 | RETURNER |
| Specialist | PaperCompiler | GIT-SP, BUILD-01, BUILD-02 | RETURNER |
| Specialist | TestRunner | GIT-SP, TEST-01, TEST-02 | RETURNER |
| Specialist | ExperimentRunner | GIT-SP, EXP-01, EXP-02 | RETURNER |
| Specialist | CodeArchitect, CodeCorrector, CodeReviewer, PaperWriter, PaperReviewer, TheoryArchitect, SimulationAnalyst, DevOpsArchitect | GIT-SP | RETURNER |
| Specialist | TheoryAuditor | GIT-SP, AUDIT-01, AUDIT-02 | RETURNER |
| Specialist | ConsistencyAuditor | GIT-SP, AUDIT-01, AUDIT-02, AUDIT-03 | RETURNER |
| Gatekeeper | WikiAuditor | GIT-00, GIT-01, DOM-01, GIT-03, GIT-04, K-LINT, K-DEPRECATE | DISPATCHER + ACCEPTOR |
| Specialist | KnowledgeArchitect | GIT-SP, K-COMPILE | RETURNER |
| Specialist | Librarian | GIT-SP, K-IMPACT-ANALYSIS | RETURNER |
| Specialist | TraceabilityManager | GIT-SP, K-REFACTOR | RETURNER |
| Specialist | DiagnosticArchitect | GIT-SP | RETURNER + DISPATCHER |
| Micro-Agent (T) | EquationDeriver, SpecWriter | GIT-SP | RETURNER |
| Micro-Agent (L) | CodeArchitectAtomic, LogicImplementer, ErrorAnalyzer, RefactorExpert | GIT-SP | RETURNER |
| Micro-Agent (E) | TestDesigner | GIT-SP | RETURNER |
| Micro-Agent (E) | VerificationRunner | GIT-SP, TEST-01, EXP-01, EXP-02 | RETURNER |
| Micro-Agent (Q) | ResultAuditor | GIT-SP, AUDIT-01, AUDIT-02 | RETURNER |

DISPATCHER = sends HAND-01; RETURNER = sends HAND-02; ACCEPTOR = receives HAND-02 + runs HAND-03.
DOM-02 is universal (no AUTHORITY grant needed — all agents, all writes).
Atomic micro-agent DDA enforcement → meta-experimental.md.

────────────────────────────────────────────────────────
# § MERGE CRITERIA

**Three mandatory conditions for any merge to `main`:**

| Criterion | Definition | Enforcement |
|-----------|-----------|-------------|
| TEST-PASS | All applicable pytest tests pass (exit code 0) | TestRunner must attach `tests/last_run.log` to PR |
| BUILD-SUCCESS | LaTeX compiles cleanly (exit code 0, no `Undefined reference`) | PaperCompiler must attach `paper/build.log` to PR |
| LOG-ATTACHED | Full execution log attached (test/build/experiment); partial logs are not acceptable | Gatekeeper must verify before merging |

Gatekeeper may IMMEDIATELY REJECT a PR that is missing any of these three artifacts.

────────────────────────────────────────────────────────
# § GIT OPERATIONS

────────────────────────────────────────────────────────
## GIT-SP: Specialist Branch + Commit

**Authorized:** All Specialists (see ROLE→OPERATION INDEX)
**[AUTH_LEVEL: Specialist]**
**Trigger:** MANDATORY — first action before any file change
**Phase:** Start of EXECUTE

```sh
scripts/git-sp.sh {domain} {agent_id} {task_id}
```

The wrapper enforces: creates `dev/{domain}/{agent_id}/{task_id}`, updates `docs/01_PROJECT_MAP.md` active task, SYSTEM_PANIC on `main` branch.

**Commit format:** `{domain}/{agent_id}: {summary}`

────────────────────────────────────────────────────────
## GIT-00: Interface Agreement Pre-flight

**Authorized:** Gatekeepers (CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptArchitect, WikiAuditor)
**[AUTH_LEVEL: Gatekeeper]**
**Trigger:** MANDATORY before dispatching any Specialist (FULL-PIPELINE only)
**Phase:** Session start, before first DISPATCH

```sh
# Step 1: Read existing IF-AGREEMENT (or draft new one)
cat docs/interface/{id}.md  # confirm outputs still match current spec

# Step 2: Write/update IF-AGREEMENT
docs/interface/{id}.md:
  inputs:       [{what the Specialist receives}]
  outputs:      [{what the Specialist must deliver — exact file paths}]
  constraints:  [{out-of-scope items}]
  signed_by:    {self — Gatekeeper name}
  status:       SIGNED

# Step 3: Commit signed IF-AGREEMENT on domain branch
git add docs/interface/{id}.md
git commit -m "{branch}: if-agree — {summary}"
```

**Hard rule:** IF-AGREEMENT `outputs` field is the binding contract for HAND-03 check 4. Gatekeeper signs; Specialist delivers.

────────────────────────────────────────────────────────
## GIT-01: Branch Preflight (Selective Sync)

**Authorized:** All Gatekeepers + ResearchArchitect (auto-switch only)
**[AUTH_LEVEL: Gatekeeper | Root Admin (Step 0 only)]**
**Trigger:** MANDATORY at session start; before any multi-step pipeline; when `docs/interface/` updated upstream
**Phase:** PRE-CHECK

```sh
# Step 1: verify current branch
git branch --show-current

# Step 2: selective sync (only when docs/interface/ changed or conflict detected)
git fetch origin main
git diff --name-only HEAD origin/main | grep "^docs/interface/" && git merge origin/main --no-ff

# Step 3: conflict check
git status | grep -c "conflict" && echo "STOP: merge conflict — report to user"
```

**GIT-01 STOP conditions:** non-domain branch detected → switch or report; merge conflict → STOP; main branch after auto-switch fails → STOP.

────────────────────────────────────────────────────────
## GIT-02: DRAFT Commit

**Authorized:** Gatekeepers  |  **[AUTH_LEVEL: Gatekeeper]**  |  **Phase:** End of EXECUTE

```sh
git add {files}
git commit -m "{branch}: draft — {summary}"
```

`{files}` must be explicit paths (never `-A`). `{summary}` must be concrete.

────────────────────────────────────────────────────────
## GIT-03: REVIEWED Commit

**Authorized:** Gatekeepers  |  **[AUTH_LEVEL: Gatekeeper]**  |  **Phase:** End of VERIFY

```sh
git add {files}
git commit -m "{branch}: reviewed — {summary}"
```

**Trigger:** TestRunner PASS / PaperReviewer 0 FATAL+0 MAJOR / PromptAuditor Q3 PASS.

────────────────────────────────────────────────────────
## GIT-04: VALIDATED Commit + PR Merge

**[AUTH_LEVEL: Gatekeeper (Phase A) | Root Admin (Phase B)]**
**Trigger:** Gate auditor issues PASS AND all three MERGE CRITERIA satisfied.

**Phase A — Gatekeeper:**
```sh
git checkout {branch}
git merge dev/{agent_role} --no-ff -m "{branch}: validated — {summary}"
gh pr create --base main --head {branch} \
  --title "merge({branch} → main): {summary}" \
  --body "AU2 PASS. MERGE CRITERIA: TEST-PASS ✓ BUILD-SUCCESS ✓ LOG-ATTACHED ✓"
```

**Phase B — Root Admin (check then merge):**
- Check: no direct commits on `main` (A8), PR title format, AU2 PASS + MERGE CRITERIA in body.
```sh
git checkout main
git merge {branch} --no-ff -m "merge({branch} → main): {summary}"
git checkout {branch}
```

On merge conflict → STOP; report to user. Post-merge failure → `git revert -m 1 HEAD`; STOP.

────────────────────────────────────────────────────────
## GIT-05: Sub-branch Operations

**Authorized:** CodeWorkflowCoordinator, PaperWorkflowCoordinator  |  **[AUTH_LEVEL: Gatekeeper]**

```sh
# Create: git checkout {parent} && git checkout -b {parent}/{feature}
# Merge:  git checkout {parent} && git merge {parent}/{feature} --no-ff -m "merge({parent}/{feature} → {parent}): {summary}"
```

`{parent}` = `code` or `paper` (never `main`). Sub-branches merge only to parent; parent reaches `main` via GIT-04.

────────────────────────────────────────────────────────
# § DOMAIN OPERATIONS

────────────────────────────────────────────────────────
## DOM-01: Domain Lock Establishment

**Authorized:** Gatekeepers  |  **[AUTH_LEVEL: Gatekeeper]**
**Trigger:** MANDATORY after GIT-01, before any DISPATCH or file edit.

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
| P | `prompts/agents/*.md` | `prompts/meta/*.md` |
| Q | `docs/02_ACTIVE_LEDGER.md` | all domains (read-only) |

On failure: branch doesn't match known domain → STOP; report to user.

────────────────────────────────────────────────────────
## DOM-02: Pre-Write Storage Check

**Authorized:** every agent (universal)  |  **[AUTH_LEVEL: universal]**
**Trigger:** every file write — the tool wrapper intercepts writes outside `domain_lock.write_territory`; agents do not pre-check.

**Failure modes:**
- DOMAIN-LOCK absent → STOP signal; request domain lock from coordinator
- Target path outside write_territory → CONTAMINATION_GUARD error; notify coordinator

────────────────────────────────────────────────────────
# § BUILD OPERATIONS

────────────────────────────────────────────────────────
## BUILD-01: Pre-compile Scan

**Authorized:** PaperCompiler  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** MANDATORY before BUILD-02  |  **Phase:** Start of VERIFY (paper domain)

```sh
# KL-12: math in section/caption titles not wrapped in \texorpdfstring
grep -n "\\\\section\|\\\\subsection\|\\\\caption" paper/sections/*.tex | grep "\$" | grep -v "texorpdfstring"
# Hard-coded numeric cross-references
grep -n "\\\\ref{[a-z]*:[0-9]" paper/sections/*.tex
# Inconsistent label prefixes (valid: sec: eq: fig: tab: alg:)
grep -n "\\\\label{" paper/sections/*.tex | grep -v "label{sec:\|label{eq:\|label{fig:\|label{tab:\|label{alg:"
# Relative positional language
grep -ni "\bbove\b\|\bbelow\b\|\bfollowing figure\b\|\bpreceding\b" paper/sections/*.tex
```

Fix KL-12 violations before BUILD-02. No exceptions.

────────────────────────────────────────────────────────
## BUILD-02: LaTeX Compilation

**Authorized:** PaperCompiler  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** After BUILD-01 passes  |  **Phase:** VERIFY (paper domain)

```sh
cd paper/
{engine} -interaction=nonstopmode -halt-on-error {main_file}.tex
bibtex {main_file}
{engine} -interaction=nonstopmode -halt-on-error {main_file}.tex
{engine} -interaction=nonstopmode -halt-on-error {main_file}.tex
```

`{engine}` = `pdflatex` (default) | `xelatex` | `lualatex`

| Log pattern | Class | Action |
|-------------|-------|--------|
| `! Undefined control sequence` for known command | STRUCTURAL_FIX | add `\newcommand` or fix typo → re-run |
| `! Missing $ inserted` | STRUCTURAL_FIX | add math delimiters → re-run |
| `! Undefined control sequence` for new content | ROUTE_TO_WRITER | STOP; route to PaperWriter |
| `undefined reference` after 3 passes | STRUCTURAL_FIX | check label/ref spelling → re-run |
| `multiply-defined` label | STRUCTURAL_FIX | rename one label → re-run |

────────────────────────────────────────────────────────
# § TEST OPERATIONS

────────────────────────────────────────────────────────
## TEST-01: pytest Execution

**Authorized:** TestRunner  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** After CodeArchitect or CodeCorrector completes  |  **Phase:** VERIFY (code domain)

```sh
python -m pytest {target} -v --tb=short 2>&1 | tee tests/last_run.log
```

On failure: parse `tests/last_run.log`, run TEST-02 on failing tests, formulate hypotheses with confidence scores → **STOP**; output Diagnosis Summary; ask user for direction. Do not retry or patch.

────────────────────────────────────────────────────────
## TEST-02: Convergence Analysis

**Authorized:** TestRunner  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** After TEST-01 (both PASS and FAIL)  |  **Phase:** VERIFY

`slope(Nᵢ, Nᵢ₊₁) = log(e[Nᵢ] / e[Nᵢ₊₁]) / log(Nᵢ₊₁ / Nᵢ)`
**Acceptance:** all slopes ≥ `expected_order − 0.2`

**Mandatory output table (every TestRunner output):**
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

────────────────────────────────────────────────────────
# § EXPERIMENT OPERATIONS

────────────────────────────────────────────────────────
## EXP-01: Simulation Execution

**Authorized:** ExperimentRunner  |  **[AUTH_LEVEL: Specialist]**
**Phase:** EXECUTE (experiment step)

```sh
python -m src.twophase.run --config {config_file} --output {output_dir} --seed {seed} 2>&1 | tee {output_dir}/run.log
```

`{seed}` = 42 (default). `{config_file}` must be committed before run. On failure → STOP; report; do not silently retry.

────────────────────────────────────────────────────────
## EXP-02: Mandatory Sanity Checks

**Authorized:** ExperimentRunner  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** MANDATORY after every EXP-01; do not forward results until all four pass.

| ID | Check | Criterion | Failure action |
|----|-------|-----------|----------------|
| SC-1 | Static droplet pressure jump | `\|dp_measured − 4σ/d\| / (4σ/d) ≤ 0.27` at ε=1.5h | STOP → report |
| SC-2 | Convergence slope | log-log slope ≥ (expected_order − 0.2) | STOP → report |
| SC-3 | Spatial symmetry | `max\|f − flip(f, axis)\| < 1e-12` | STOP → report |
| SC-4 | Mass conservation | `\|Δmass\| / mass₀ < 1e-4` over full run | STOP → report |

────────────────────────────────────────────────────────
# § AUDIT OPERATIONS

────────────────────────────────────────────────────────
## AUDIT-01: AU2 Release Gate

**Authorized:** ConsistencyAuditor  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** MANDATORY before any merge to `main`  |  **Phase:** AUDIT

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
| 9 | Branch policy compliance (A8: no direct commits on main; dev/ → domain via PR) | coordinator |
| 10 | Merge authorization compliance (VALIDATED required; TEST-PASS, BUILD-SUCCESS, LOG-ATTACHED) | coordinator |

**Error routing (items 1, 2, 3, 6):** PAPER_ERROR → PaperWriter; CODE_ERROR → CodeArchitect → TestRunner; authority conflict → STOP → user.
**Verdict:** AU2 PASS unlocks GIT-04 (VALIDATED commit + merge to main).

────────────────────────────────────────────────────────
## AUDIT-02: Verification Procedures A–E

**Authorized:** ConsistencyAuditor  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** As part of AUDIT-01 items 1, 6

| Procedure | Description | Output |
|-----------|-------------|--------|
| A | Independent derivation from first principles | Re-derived formula or stencil |
| B | Code–paper line-by-line comparison (symbol, index, sign conventions) | Match/mismatch table |
| C | MMS test result interpretation (TEST-02 output) | PASS/FAIL verdict per component |
| D | Boundary scheme derivation (ghost cell treatment at domain walls) | Boundary stencil verification |
| E | Authority chain conflict: MMS-passing code > docs/01_PROJECT_MAP.md §6 > paper | Definitive verdict on wrong artifact |

Procedure E only when A–D produce conflicting evidence. Resolve by derivation, not preference.

────────────────────────────────────────────────────────
## AUDIT-03: Adversarial Edge-Case Gate

**Authorized:** ConsistencyAuditor  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** MANDATORY for FULL-PIPELINE (AUDIT-01 item 4); OPTIONAL for FAST-TRACK

**Purpose:** Verify the artifact resists boundary conditions and degenerate cases — not just that it works for the happy path.

| Step | Action |
|------|--------|
| 1 | Identify artifact boundary conditions (input extremes, singular cases, interface on grid boundary) → `artifacts/Q/edge_case_list_{id}.md` |
| 2 | Predict expected behavior from T-Domain for each edge case |
| 3 | Probe artifact (run test, trace code, or derive analytically) |
| 4 | Compare expected vs. actual; classify: THEORY_ERR / IMPL_ERR / SCOPE_LIMIT |

Edge cases (code): ρ→0, μ→0, Δt→0; contrast ratio >1000; interface on grid edge; sphere of radius h.
Edge cases (paper): equations at domain boundaries; limiting cases; sign at negative coordinates.

AUDIT-03 PASS if all = PASS or SCOPE_LIMIT (documented). FAIL → route per error type.
SCOPE_LIMIT valid ONLY when limitation is in the interface contract or paper. Results appended to `artifacts/Q/audit_{id}.md`.

────────────────────────────────────────────────────────
## PATCH-IF: Interface Patch Protocol (Agile Synchronization)

**Authorized:** ResearchArchitect (with explicit user confirmation)  |  **[AUTH_LEVEL: Root Admin]**
**Trigger:** Downstream domain finds minor error in upstream Interface Contract

```
PATCH-IF {target_interface} --scope {minimal_change}
```

| Scope | Definition | Action |
|-------|-----------|--------|
| MINOR | Typo, unit label, clarification note — no API or math change | ResearchArchitect patches + re-signs; downstream resumes |
| FUNCTIONAL | API signature, equation form, operator structure, boundary conditions | PATCH-IF DENIED → run full CI/CP |

After applying: write `docs/02_ACTIVE_LEDGER.md §AUDIT patch_if_{date}.md` with scope + rationale.
Hard rule: at most ONE PATCH-IF per Interface Contract version. Two patches = FUNCTIONAL scope → CI/CP.

────────────────────────────────────────────────────────
# § KNOWLEDGE OPERATIONS

────────────────────────────────────────────────────────
## K-COMPILE: Wiki Entry Compilation

**Authorized:** KnowledgeArchitect  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** Domain artifact reaches VALIDATED phase  |  **Phase:** Post-AUDIT (parallel)

1. Verify source at VALIDATED (git log + audit trail)
2. Check `docs/wiki/` for duplicate (SSoT K-A3) → if found, K-REFACTOR instead
3. Extract structured knowledge; compose entry in canonical format (meta-domains.md §WIKI ENTRY FORMAT)
4. Link refs using `[[REF-ID]]`; commit to `dev/K/KnowledgeArchitect/{task_id}`; open PR → `wiki` (log attached)

────────────────────────────────────────────────────────
## K-LINT: Pointer Integrity Check

**Authorized:** WikiAuditor  |  **[AUTH_LEVEL: Gatekeeper]**
**Trigger:** MANDATORY before any wiki entry merge; also periodic/on-demand  |  `{scope}` = `entry` | `full`

1. Scan all `[[REF-ID]]` pointers; verify each target exists and has `status: ACTIVE`
2. Check SSoT violations (duplicate knowledge); verify sources still at VALIDATED
3. Zero broken pointers + zero SSoT violations → K-LINT PASS.
   Any broken pointer → STOP-HARD (K-A2). SSoT violation → flag for K-REFACTOR.

────────────────────────────────────────────────────────
## K-DEPRECATE: Wiki Entry Deprecation

**Authorized:** WikiAuditor  |  **[AUTH_LEVEL: Gatekeeper]**
**Trigger:** Source artifact invalidated, superseded, or incorrect  |  **Precondition:** K-IMPACT-ANALYSIS complete

1. Set entry `status: DEPRECATED` (or `SUPERSEDED` with `superseded_by: [[REF-ID]]`)
2. Emit RE-VERIFY signal to all consuming domains
3. Record in `docs/wiki/changelog/`
   Cascade depth > 10 → STOP; escalate to user.

────────────────────────────────────────────────────────
## K-REFACTOR: SSoT Deduplication

**Authorized:** TraceabilityManager  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** K-LINT reports duplicate knowledge

1. Identify canonical entry; replace duplicate content with `[[REF-ID]]` pointers
2. Verify no semantic loss; run K-LINT on affected entries
3. Commit to `dev/K/TraceabilityManager/{task_id}`; open PR with before/after pointer map
   Semantic meaning would change → STOP; escalate to KnowledgeArchitect.

────────────────────────────────────────────────────────
## K-IMPACT-ANALYSIS: Deprecation Cascade Analysis

**Authorized:** Librarian  |  **[AUTH_LEVEL: Specialist]**
**Trigger:** Before K-DEPRECATE

1. Trace direct consumers (entries with `depends_on: [[{ref_id}]]`)
2. Trace transitive consumers (full closure); identify affected domains; estimate cascade depth
   Cascade depth > 10 → STOP; escalate to user.

────────────────────────────────────────────────────────
# § STOP CONDITIONS

| ID | Condition | Trigger | Action |
|----|-----------|---------|--------|
| STOP-01 | Main branch contamination | Non-Root-Admin commits to `main` | SYSTEM_PANIC → revert + escalate |
| STOP-02 | Immutable Zone modification | Change to φ-principles, axioms, or HAND-03 logic | SYSTEM_PANIC → escalate |
| STOP-03 | Domain lock violation | Write outside DOMAIN-LOCK territory | CONTAMINATION RETURN → Gatekeeper rejects PR |
| STOP-04 | Branch isolation breach | Access to another agent's `dev/` branch | CONTAMINATION RETURN → Gatekeeper rejects PR |
| STOP-05 | GIT-SP skipped | File changes without invoking `scripts/git-sp.sh` | SYSTEM_PANIC → invoke GIT-SP and restart |
| STOP-06 | Context leakage | Downstream consumes upstream conversation history | Context Leakage Violation → re-dispatch |
| STOP-07 | Loop > MAX_REVIEW_ROUNDS | P-E-V-A loop exceeds 5 iterations | STOPPED → escalate to user |
| STOP-08 | Hash mismatch (INTEGRITY_MANIFEST) | Upstream contract hash ≠ recorded | CONTAMINATION → CI/CP re-propagation |

Branch validation enforced by `scripts/git-sp.sh`; `main` branch → wrapper returns SYSTEM_PANIC.

────────────────────────────────────────────────────────
# § COMMAND FORMAT

```
Initialize
Execute [AgentName]
Execute [filename]
```

- One command per step (P5). `Initialize` = invoke ResearchArchitect with `docs/02_ACTIVE_LEDGER.md`.
- `Execute [AgentName]` = invoke by role name. `Execute [filename]` = load from `prompts/agents/{filename}.md`.

────────────────────────────────────────────────────────
# § HANDOFF PROTOCOL

Every transfer of control between agents must use these canonical tokens. Informal handoffs bypass the verification layer and break audit traceability (φ4).

- HAND-01: DISPATCH — coordinator → specialist (delegation)
- HAND-02: RETURN — specialist → coordinator (handback)
- HAND-03: Acceptance Check — receiver's first action before any work

────────────────────────────────────────────────────────
## HAND-01: DISPATCH Token

**Sent by:** Coordinators, ResearchArchitect (initial routing)
**Received by:** Any specialist being delegated to

```
DISPATCH → {specialist}
  task:         {one-sentence objective}
  inputs:       [{artifact_paths}]
  constraints:  [{scope_out}, expected_verdict: {measurable}]
  target:       {expected deliverable — matches IF-AGREEMENT outputs}
```

**§HAND-01-ENV ENVIRONMENTAL METADATA (injected by wrapper; not LLM payload)**
Fields derivable at tool-call time or enforced by env wrapper:
`phase`, `matrix_domain`, `branch`, `commit`, `domain_lock`, `if_agreement`,
`upstream_contracts`, `artifact_hash`, `context_root`, `domain_lock_id`, `gatekeeper_approval_required`.

**Rules:**
- `task` must be achievable in a single agent session (P5)
- `constraints.expected_verdict` must be measurable (e.g., "AU2 PASS: all 10 items")
- When dispatching to an Auditor/Gatekeeper: `inputs` must list ONLY final artifact paths + Interface Contract paths — never Specialist reasoning or intermediate derivations (→ HAND-03 check 6)
- `target` must match IF-AGREEMENT outputs field

────────────────────────────────────────────────────────
## HAND-02: RETURN Token

**Sent by:** Any specialist  |  **Received by:** The coordinator that issued the DISPATCH

```
RETURN → {requester}
  status:    SUCCESS | FAIL | REJECT
  produced:  [{file_paths}] | none
  issues:    [{blocker}] | none      # FAIL/REJECT only
  detail:    {optional: self-eval — only when explicitly requested in DISPATCH}
```

| Status | Meaning | Coordinator action |
|--------|---------|-----|
| SUCCESS | All deliverables produced; verdict PASS | Continue pipeline |
| FAIL | Work attempted; verdict FAIL | Review issues; decide |
| REJECT | HAND-03 rejected, STOPPED, or wrapper refusal | Resolve blocker or escalate |

`produced` must list concrete file paths. `issues` required for FAIL/REJECT. `detail` only when DISPATCH requested self-evaluation.

────────────────────────────────────────────────────────
## HAND-03: Acceptance Check

**Performed by:** Every agent upon receiving DISPATCH, before any work  |  **Trigger:** MANDATORY

Env-side preconditions (branch, tier, domain lock, expected_verdict, sender authorization) are enforced by the tool wrapper; agents observe them only as STOP signals. HAND-03 covers the semantic checks the wrapper cannot make.

```
Acceptance Check:
  □ 1. TASK IN SCOPE: does the task fall within this role's PURPOSE in meta-roles.md?
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
         Auditor evaluates the Artifact only — not Specialist process quality.
         Cross-domain dispatch to Auditor/Gatekeeper: coordinator MUST invoke L3 isolation.
         Within-domain verification MAY use L1. (→ meta-experimental.md §HIERARCHICAL ISOLATION POLICY)
         Non-Auditor roles: this check is N/A.
```

**On REJECT:** Issue RETURN immediately: `status: REJECT; produced: none; issues: ["Acceptance Check failed: check {N} — {reason}"]`

────────────────────────────────────────────────────────
## Handoff Sequence Diagram

```
Coordinator                     Specialist
    │──── HAND-01 (DISPATCH) ──────►│
    │                               │ HAND-03: checks 1–6 (semantic)
    │◄─── HAND-02 (status:REJECT) ──│  [REJECT if any fail]
    │                               │  [PASS → work begins]
    │◄─── HAND-02 (RETURN) ─────────│
    │  status / produced / issues   │
    │ SUCCESS → continue pipeline   │
    │ FAIL/REJECT → resolve/escalate│
```

────────────────────────────────────────────────────────
# § INTERFACE DRAFTING — Speculative Parallel Execution

TheoryArchitect MAY publish `docs/interface/{id}.draft` once core algorithm structure is known.
CodeArchitect MAY read `.draft` files to build scaffolding only in `artifacts/L/scaffold_{id}.py.draft` — never in `src/`.

Rules:
1. No `.draft` artifact may be merged into `src/`, `paper/`, or any domain branch.
2. Every draft-derived function must carry: `# DRAFT — pending TheoryAuditor signature on docs/interface/{id}.draft`
3. Promotion gate: TheoryAuditor HAND-02 with `interface_contracts_checked: [{id}.draft → SIGNED]` → Gatekeeper removes `.draft` suffix → standard GIT-SP + PR flow applies.
4. TheoryAuditor FAIL on draft → all scaffold files MUST be deleted (coordinator dispatches cleanup).

T-L-E-A ordering enforced for **merges**. DOM-02 always applies. GA-6 blocks final PR until interface is SIGNED.

────────────────────────────────────────────────────────
# § AUDIT EXIT CRITERIA — Deadlock Prevention

A Gatekeeper / Auditor may REJECT ONLY when tied to a specific violation of:

| Category | Examples |
|----------|---------|
| 1. Formal Checklist | Q1–Q3 item failed; AUDIT-01 item N failed |
| 2. Interface Contract | Output ≠ `docs/interface/{contract}.md` outputs; contract unsigned |
| 3. Core Axiom | A1–A11 violated (cite axiom + exact violation) |

"Gut feeling" rejection is forbidden. When all formal checks pass, Auditor MUST issue CONDITIONAL PASS, not continue deliberating.

```
CONDITIONAL PASS:
  verdict:      CONDITIONAL_PASS
  warning_note: {specific concern — must reference a named risk}
  escalate_to:  user
  pipeline:     CONTINUES
```

Auditor that withholds PASS without citable violation commits a Deadlock Violation.

────────────────────────────────────────────────────────
# § JIT COMMAND REFERENCE

Agent prompts MUST NOT embed full operation syntax from this file.
**JIT rule:** "If a specific operation is required, consult `prompts/meta/meta-ops.md` for canonical syntax. Do NOT improvise."
Agent prompts include: operation ID (e.g., `GIT-01`), trigger condition, AUTH_LEVEL tag.
Agent prompts MUST NOT include: full parameter blocks, success criteria tables, failure handling steps.
