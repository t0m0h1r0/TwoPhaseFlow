# META-DOMAINS: Domain Registry
# VERSION: 3.0.0
# ABSTRACT LAYER — STRUCTURE: authoritative definition of all system domains.
# Each domain defines: git branch ownership, storage territory, agent membership,
# coordinator, applicable rules, and lifecycle phase triggers.
# FOUNDATION (φ1–φ7, A1–A10): prompts/meta/meta-core.md  ← READ FIRST
# Role contracts per agent: prompts/meta/meta-roles.md
# Pipeline execution order: prompts/meta/meta-workflow.md

────────────────────────────────────────────────────────
# § MATRIX ARCHITECTURE — 4 Vertical × 3 Horizontal Domains

## Vertical Domains (Practical — each owns one "Truth")

| ID | Domain | Truth Type | Directory | Specialist | Gatekeeper |
|----|--------|-----------|-----------|------------|------------|
| T  | Theory & Analysis     | Mathematical Truth  | `theory/`     | Theory Architect    | Theory Auditor          |
| L  | Core Library          | Functional Truth    | `lib/`        | Library Developer   | Numerical Auditor       |
| E  | Experiment            | Empirical Truth     | `experiment/` | Experimentalist     | Validation Guard        |
| A  | Academic Writing      | Logical Truth       | `paper/`      | Paper Writer        | Logical Reviewer        |

## Horizontal Domains (Governance — span all vertical domains)

| ID | Domain               | Role in System         | Key Agent(s)                        |
|----|----------------------|------------------------|-------------------------------------|
| M  | Meta-Logic           | The Judiciary          | ResearchArchitect (Protocol Enforcer)|
| P  | Prompt & Environment | The Infrastructure     | PromptArchitect (Prompt Engineer)   |
| Q  | QA & Audit           | Internal Affairs       | ConsistencyAuditor (Consistency Auditor)|

**Sovereignty rule:** Each vertical domain acts as an independent "Corporation."
All inter-domain communication must pass through a Gatekeeper-approved Interface Contract.

**Broken Symmetry rule:** → meta-core.md §B. Gatekeeper ≠ Specialist within each domain.

────────────────────────────────────────────────────────
# § INTER-DOMAIN INTERFACES (Connection by Contract)

Every cross-domain data transfer requires a Gatekeeper-approved Interface Contract.
No Specialist may consume artifacts from another domain without a valid contract on `interface/`.

| Transfer | Contract Artifact | Precondition | Consumer domain |
|----------|------------------|--------------|----------------|
| T → L    | `interface/AlgorithmSpecs.md`     | Theory Auditor PASS; equations formalized | L-Domain — must define discretization before coding |
| L → E    | `interface/SolverAPI_vX.py`       | TestRunner PASS (all unit tests)          | E-Domain — must pass unit tests before experiments |
| E → A    | `interface/ResultPackage/`        | Validation Guard PASS (all sanity checks); raw logs included | A-Domain — must provide raw logs for paper figures |
| T/E → A  | `interface/TechnicalReport.md`    | Both T-Auditor and Validation Guard sign off | A-Domain — bridges math and data for the writer |

**Contract immutability rule:** Once a Specialist's `dev/` branch is created from a contract,
the contract is immutable. Changing inputs/outputs requires: close current dev/ branch →
update contract → new IF-AGREEMENT → new dev/ branch (see §IF-AGREEMENT PROTOCOL).

**QA & Audit scope:** ConsistencyAuditor (Q-Domain) has read access across ALL domains
and ALL interface contracts for cross-system verification.

────────────────────────────────────────────────────────
# § DOMAIN REGISTRY

A domain is the atomic unit of work in this system — the equivalent of a department
in an organization. Each domain owns one git branch, one storage territory, and one
coordinator. Work may not cross domain boundaries without an explicit routing decision
by ResearchArchitect or an escalation to ConsistencyAuditor.

────────────────────────────────────────────────────────
## Domain: Routing

| Property | Value |
|----------|-------|
| Git branch | none — stateless; reads current state from `main` |
| Coordinator | ResearchArchitect |
| Members | ResearchArchitect |
| Storage (write) | **NONE** — Routing domain is strictly No-Write for all files |
| Storage (read) | docs/02_ACTIVE_LEDGER.md, docs/01_PROJECT_MAP.md |
| Rules | meta-core.md §AXIOMS only (no domain rule section) |
| Lifecycle | none — entry point only; routes to a domain then exits |

**Domain purpose:** Session intake and work routing. Routing domain never produces
artifacts — it records routing decisions and dispatches to the appropriate domain.

**No-Write rule:** ResearchArchitect must not write to any file, including
docs/02_ACTIVE_LEDGER.md, during the Routing phase. Writing is delegated to the
receiving domain's coordinator after routing completes. Any write attempt by
ResearchArchitect triggers DOM-02 CONTAMINATION_GUARD — STOP; escalate to user.

────────────────────────────────────────────────────────
## Domain: Library / L-Domain (Code)

**Matrix position:** Vertical domain L — Functional Truth. Gatekeeper: CodeWorkflowCoordinator (Numerical Auditor role). Specialists: CodeArchitect, CodeCorrector, CodeReviewer, TestRunner.

| Property | Value |
|----------|-------|
| Git branch | `code` (sub-branches: `code/{feature}`) |
| Matrix alias | L-Domain (Core Library) |
| Coordinator / Gatekeeper | CodeWorkflowCoordinator |
| Specialist members | CodeArchitect, CodeCorrector, CodeReviewer, TestRunner |
| Storage (write — STRICT) | `src/twophase/`, `tests/`, `docs/02_ACTIVE_LEDGER.md` |
| Storage (read — STRICT) | `paper/sections/*.tex` (via T/E→A contract read only), `docs/01_PROJECT_MAP.md` |
| Storage (FORBIDDEN write) | `paper/`, `theory/`, `experiment/`, `prompts/meta/`, `interface/` (without IF-COMMIT token) |
| Interface contract in | `interface/AlgorithmSpecs.md` (T→L); `interface/SolverAPI_vX.py` (L→E, produced by L) |
| Rules | docs/00_GLOBAL_RULES.md §C (C1–C6: SOLID, preserve-tested, builder, solver policy, quality, MMS) |
| Lifecycle | **DRAFT** — Specialist returns COMPLETE on dev/ branch<br>**REVIEWED** — Gatekeeper (CodeWorkflowCoordinator) approves PR; TestRunner PASS required<br>**VALIDATED** — ConsistencyAuditor (Q-Domain) AU2 PASS → merge `code` → `main` |

**Gatekeeper Approval condition (REVIEWED gate):** Gatekeeper may only merge dev/ PR into `code`
after: (1) TestRunner PASS with LOG-ATTACHED, (2) interface/AlgorithmSpecs.md exists and is signed,
(3) no write-territory violation detected. Absent any condition → REJECT PR.

**Cross-domain read:** L agents may read `paper/sections/*.tex` only for equation–code alignment (A3).
L agents must not write to `paper/` — requires cross-domain routing via interface contract.

**Legacy register:** docs/01_PROJECT_MAP.md §C2 Legacy Register — list of classes that must
not be deleted (C2 preserve-tested rule). CodeArchitect must consult before removing any class.

────────────────────────────────────────────────────────
## Domain: Academic Writing / A-Domain (Paper)

**Matrix position:** Vertical domain A — Logical Truth. Gatekeeper: PaperWorkflowCoordinator + PaperReviewer (Logical Reviewer). Specialists: PaperWriter (absorbs PaperCorrector), PaperCompiler.

| Property | Value |
|----------|-------|
| Git branch | `paper` (sub-branches: `paper/{section}`) |
| Matrix alias | A-Domain (Academic Writing) |
| Coordinator / Gatekeeper | PaperWorkflowCoordinator (orchestrator); PaperReviewer (Logical Reviewer gate) |
| Specialist members | PaperWriter (absorbs PaperCorrector), PaperCompiler |
| Storage (write — STRICT) | `paper/sections/*.tex`, `paper/bibliography.bib`, `docs/02_ACTIVE_LEDGER.md` |
| Storage (read — STRICT) | `src/twophase/` (consistency checks only, via interface/TechnicalReport.md), `interface/ResultPackage/`, `interface/TechnicalReport.md` |
| Storage (FORBIDDEN write) | `src/`, `lib/`, `theory/`, `experiment/`, `prompts/meta/`, `interface/` (without IF-COMMIT token) |
| Interface contract in | `interface/ResultPackage/` (E→A); `interface/TechnicalReport.md` (T/E→A) |
| Rules | docs/00_GLOBAL_RULES.md §P (P1–P4, KL-12: LaTeX authoring, cross-refs, consistency, skepticism) |
| Lifecycle | **DRAFT** — PaperWriter diff-patch returned COMPLETE on dev/ branch<br>**REVIEWED** — PaperReviewer (Logical Reviewer): 0 FATAL + 0 MAJOR findings (loop ≤ MAX_REVIEW_ROUNDS); Gatekeeper PR approval required<br>**VALIDATED** — ConsistencyAuditor (Q-Domain) AU2 PASS → merge `paper` → `main` |

**Gatekeeper Approval condition (REVIEWED gate):** PaperWorkflowCoordinator may only merge dev/ PR
into `paper` after: (1) PaperCompiler BUILD-SUCCESS, (2) PaperReviewer 0 FATAL + 0 MAJOR,
(3) interface/TechnicalReport.md or ResultPackage/ consumed and cited. Absent any → REJECT PR.

**Logical Reviewer (PaperReviewer) as Devil's Advocate:** PaperReviewer assumes the manuscript
is wrong until proven otherwise. It must derive claims independently before accepting them.
It never reads the author's reasoning first — derive first, compare second (MH-3).

**Cross-domain read:** A agents may read `src/twophase/` for consistency checks only.
A agents must not write to `src/` — requires cross-domain routing via interface contract.

**P3-D register:** docs/01_PROJECT_MAP.md §P3-D Register — multi-site parameter definitions.
PaperWriter must consult when changing a symbol that appears in multiple sections.

────────────────────────────────────────────────────────
## Domain: Theory & Analysis / T-Domain

**Matrix position:** Vertical domain T — Mathematical Truth. Gatekeeper: TheoryAuditor (dedicated T-Domain re-derivation gate; distinct from ConsistencyAuditor). Specialists: Theory Architect (CodeArchitect or PaperWriter in theory-derivation mode).

| Property | Value |
|----------|-------|
| Git branch | `theory` (sub-branches: `theory/{topic}`) |
| Matrix alias | T-Domain (Theory & Analysis) |
| Coordinator / Gatekeeper | **TheoryAuditor** (T-Domain only; not ConsistencyAuditor) |
| Specialist members | CodeArchitect (discretization), PaperWriter (mathematical formulation) |
| Storage (write — STRICT) | `theory/`, `docs/02_ACTIVE_LEDGER.md` |
| Storage (read — STRICT) | `paper/sections/*.tex` (reference only), `docs/01_PROJECT_MAP.md §6` |
| Storage (FORBIDDEN write) | `src/`, `lib/`, `experiment/`, `paper/sections/`, `prompts/meta/` |
| Interface contract produced | `interface/AlgorithmSpecs.md` (T→L) — signed by TheoryAuditor before L-Domain may code |
| Rules | docs/00_GLOBAL_RULES.md §A (A3: 3-Layer Traceability mandatory), §AU (AU1–AU3) |
| Lifecycle | **DRAFT** — Specialist formalizes equations in `theory/`<br>**REVIEWED** — TheoryAuditor independently re-derives and signs; contradictions block REVIEWED<br>**VALIDATED** — TheoryAuditor publishes `interface/AlgorithmSpecs.md`; ConsistencyAuditor (Q-Domain) AU2 PASS |

**Gatekeeper Approval condition (REVIEWED gate):** Theory Auditor must independently derive every
equation without reading the Specialist's derivation first. Theory Auditor signs only after
independent agreement. If derivations conflict → STOP; escalate to user; do not average or compromise.

────────────────────────────────────────────────────────
## Domain: Experiment / E-Domain

**Matrix position:** Vertical domain E — Empirical Truth. Gatekeeper: Validation Guard (ExperimentRunner acting in gate role; CodeWorkflowCoordinator as coordinator). Specialists: ExperimentRunner.

| Property | Value |
|----------|-------|
| Git branch | `experiment` (sub-branches: `experiment/{run}`) |
| Matrix alias | E-Domain (Experiment) |
| Coordinator / Gatekeeper | CodeWorkflowCoordinator (experiment orchestration); ExperimentRunner (Validation Guard for sanity) |
| Specialist members | ExperimentRunner |
| Storage (write — STRICT) | `experiment/`, `results/`, `docs/02_ACTIVE_LEDGER.md` |
| **Directory name** | **`experiment/` (singular) — NEVER `experiments/`, `experint/`, or any variant** |
| Storage (read — STRICT) | `interface/SolverAPI_vX.py` (L→E contract); `src/twophase/` (solver invocation only) |
| Storage (FORBIDDEN write) | `src/`, `theory/`, `paper/`, `prompts/meta/` |
| Interface contract in | `interface/SolverAPI_vX.py` (L→E — must have TestRunner PASS before E may run) |
| Interface contract produced | `interface/ResultPackage/` (E→A); `interface/TechnicalReport.md` (jointly with T) |
| Rules | docs/00_GLOBAL_RULES.md §A (A3), §C (EXP sanity checks) |
| Lifecycle | **DRAFT** — ExperimentRunner executes simulation; raw results in `experiment/`<br>**REVIEWED** — Validation Guard confirms all 4 sanity checks PASS; packages `ResultPackage/`<br>**VALIDATED** — ConsistencyAuditor (Q-Domain) AU2 PASS; `interface/ResultPackage/` signed |

**Gatekeeper Approval condition (REVIEWED gate):** Validation Guard must pass all 4 mandatory
sanity checks (EXP-02 SC-1 through SC-4) before signing ResultPackage. Missing raw logs → REJECT.
ExperimentRunner must not forward results that failed any sanity check, even partially.

**Precondition:** `interface/SolverAPI_vX.py` must exist and be signed by L-Domain Gatekeeper
before any E-Domain work begins. Running experiments without a signed solver API = STOP.

────────────────────────────────────────────────────────
## Domain: Prompt & Environment / P-Domain (Prompt)

**Matrix position:** Horizontal governance domain P — The Infrastructure. Manages agent intelligence and tooling across all vertical domains.

| Property | Value |
|----------|-------|
| Git branch | `prompt` |
| Matrix alias | P-Domain (Prompt & Environment) |
| Coordinator / Gatekeeper | PromptArchitect (Prompt Engineer; acts as both coordinator and primary executor) |
| Specialist members | PromptAuditor |
| Storage (write — STRICT) | `prompts/agents/*.md` |
| Storage (read — STRICT) | `prompts/meta/*.md` (source only; never edit agents/ via meta/) |
| Storage (FORBIDDEN write) | `prompts/meta/*.md` (Governance-owned; read-only for all agents), `src/`, `paper/`, `theory/`, `experiment/` |
| Rules | docs/00_GLOBAL_RULES.md §Q (Q1–Q4: standard template, env profiles, audit checklist, compression) |
| Lifecycle | **DRAFT** — PromptArchitect generates agent prompt (GIT-02)<br>**REVIEWED** — PromptAuditor (Q3 checklist PASS) — Gatekeeper approval required (GIT-03)<br>**VALIDATED** — PromptAuditor gate PASS → merge `prompt` → `main` (GIT-04) |

**Note:** Prompt domain has no separate coordinator above PromptArchitect.
PromptArchitect includes compression pass (absorbs PromptCompressor) and dispatches to PromptAuditor (review path).
PromptAuditor acts as Devil's Advocate: assumes every prompt is non-compliant until Q3 PASS.

────────────────────────────────────────────────────────
## Domain: QA & Audit / Q-Domain (Audit)

**Matrix position:** Horizontal governance domain Q — Internal Affairs. Independent verification and cross-domain consistency. The only domain with read access to ALL vertical domains.

| Property | Value |
|----------|-------|
| Git branch | none — operates on the calling domain's branch |
| Matrix alias | Q-Domain (QA & Audit) |
| Coordinator | ConsistencyAuditor (direct gate; no orchestrator above it) |
| Members | ConsistencyAuditor |
| Storage (write — STRICT) | `audit_logs/` (audit trail, hash values) — append-only |
| Storage (read — STRICT) | ALL domains: `paper/sections/*.tex`, `src/twophase/`, `theory/`, `experiment/`, `interface/`, `docs/01_PROJECT_MAP.md` |
| Storage (FORBIDDEN write) | any domain's primary artifacts — Q-Domain is a read-only gate for all artifact directories |
| Rules | docs/00_GLOBAL_RULES.md §AU (AU1–AU3: authority chain, AU2 gate 10 items, verification A–E) |
| Lifecycle | triggers VALIDATED phase for ALL domains upon AU2 PASS verdict; writes audit trail to `audit_logs/` |

**Domain purpose:** Independent, cross-system falsification gate. ConsistencyAuditor is the only
agent with read access across all storage territories. It does not produce domain artifacts —
it issues PASS/FAIL verdicts and writes audit trails. Finding a contradiction is a high-value
success (Falsification Loop — meta-core.md §0 CORE PHILOSOPHY §C).

**Devil's Advocate mandate:** ConsistencyAuditor must assume ALL claims are wrong until proven
by independent derivation. It never relies on the Specialist's reasoning path — re-derives from
scratch before comparing (MH-3 Broken Symmetry).

**Audit log format (`audit_logs/{domain}_{timestamp}.md`):**
```
AUDIT-RECORD:
  domain:      {T | L | E | A}
  interface:   {contract path checked}
  verdict:     {PASS | FAIL}
  items_checked: {AU2 item list}
  failures:    [{item}: {reason}]
  signed_by:   ConsistencyAuditor
  git_hash:    {short hash at time of audit}
```

**Error routing:**
- PAPER_ERROR → PaperWriter (A-Domain)
- CODE_ERROR → CodeArchitect → TestRunner (L-Domain)
- THEORY_ERROR → Theory Architect → Theory Auditor (T-Domain)
- EXPERIMENT_ERROR → ExperimentRunner → Validation Guard (E-Domain)
- Authority conflict → escalate to domain coordinator → user

────────────────────────────────────────────────────────
# § BRANCH RULES

| Branch | Matrix Domain | Owned by | May commit | Merge target | Created by |
|--------|--------------|----------|------------|--------------|------------|
| `main` | — | system | never directly | — | Root Admin |
| `theory` | T-Domain | TheoryAuditor (Gatekeeper) | TheoryAuditor, CodeArchitect (on dev/) | `main` via PR (Root Admin executes) | TheoryAuditor |
| `code` | L-Domain | CodeWorkflowCoordinator (Gatekeeper) | CodeWorkflowCoordinator | `main` via PR (Root Admin executes) | CodeWorkflowCoordinator |
| `experiment` | E-Domain | CodeWorkflowCoordinator (Gatekeeper) | CodeWorkflowCoordinator, ExperimentRunner (on dev/) | `main` via PR (Root Admin executes) | CodeWorkflowCoordinator |
| `paper` | A-Domain | PaperWorkflowCoordinator (Gatekeeper) | PaperWorkflowCoordinator | `main` via PR (Root Admin executes) | PaperWorkflowCoordinator |
| `prompt` | P-Domain | PromptArchitect (Gatekeeper) | PromptArchitect, PromptAuditor | `main` via PR (Root Admin executes) | PromptArchitect |
| `dev/{agent_role}` | any vertical | named agent only | named agent only | `{domain}` via PR | Specialist at task start |
| `interface/` | cross-domain | Gatekeepers | Gatekeepers only (IF-COMMIT token required) | — (referenced, not merged) | Gatekeeper before task |

**PR merge path (mandatory):**
```
Specialist commits on dev/{agent_role}
  → opens PR: dev/{agent_role} → {domain}    (Gatekeeper reviews evidence)
  → Gatekeeper merges dev/ PR
  → Gatekeeper immediately opens PR: {domain} → main
  → Root Admin performs final syntax/format check
  → Root Admin executes final merge
```

**Cross-domain switch rule:** Before switching domains (e.g., from Code to Paper work),
the current domain branch MUST be at VALIDATED phase and merged to `main` first.
The receiving coordinator MUST confirm the merge is present in `main` history before
running PRE-CHECK for the new domain. A task is NOT "Done" until it is merged into `main`.
See meta-ops.md GIT-04 and meta-workflow.md §HANDOFF RULES.

**Adding a new domain:** define Gatekeeper, branch name, storage territory, DRAFT/REVIEWED/VALIDATED
triggers, gate auditor, and applicable docs/00_GLOBAL_RULES.md §section; add one row to this registry.

────────────────────────────────────────────────────────
# § BRANCH ISOLATION

**Branch Isolation is a physical law** — agents are programmatically and logically prohibited
from viewing or operating on another agent's `dev/` branch.

| Rule | Enforcement |
|------|-------------|
| No agent may `git checkout dev/{other_agent}` | STOP immediately; CONTAMINATION alert |
| No agent may read files via another agent's dev/ branch | STOP; do not proceed |
| No agent may push, force-push, or amend commits on another agent's dev/ branch | STOP; escalate to user |
| Gatekeeper may read a dev/ PR diff for review only — no direct branch access | PR review interface only |

Violation → issue CONTAMINATION RETURN (see §CONTAMINATION GUARD) and escalate to Root Admin.

────────────────────────────────────────────────────────
# § IF-AGREEMENT PROTOCOL (Interface First)

**Trigger:** MANDATORY before any Specialist starts work on a `dev/` branch.

Before development begins, the Gatekeeper establishes an interface contract in `interface/`
that defines the inputs and outputs of the task. The Specialist reads this contract before
creating their `dev/` branch.

**Interface contract format (in `interface/{domain}_{feature}.md`):**
```
IF-AGREEMENT:
  feature:      {one-line description}
  domain:       {Code | Paper | Prompt}
  gatekeeper:   {coordinator name}
  specialist:   {target agent role}
  inputs:       [{artifact_path}: {description}, ...]
  outputs:      [{artifact_path}: {description}, ...]
  success_criteria: {measurable criterion matching MERGE CRITERIA in meta-ops.md}
  created_at:   {git short hash at time of creation}
```

**Rules:**
- No Specialist may create a `dev/` branch without a valid IF-AGREEMENT on `interface/`
- IF-AGREEMENT is immutable once the Specialist's dev/ branch is created
- Changes to interface require: close current dev/ branch → new IF-AGREEMENT → new dev/ branch
- ConsistencyAuditor reads IF-AGREEMENT during AUDIT to verify output matches contract

────────────────────────────────────────────────────────
# § SELECTIVE SYNC PROTOCOL

Agents pull from `main` ONLY under one of these two conditions:

| Condition | Trigger | Action |
|-----------|---------|--------|
| Interface file updated | Gatekeeper notifies Specialist of a change in `interface/` | `git fetch origin main && git merge origin/main` |
| Physical merge conflict detected | `git merge` exits with conflict markers on Specialist's dev/ branch | `git fetch origin main && git merge origin/main` — then resolve conflict before proceeding |

**Default (neither condition met):** do NOT pull from main. Gratuitous syncing contaminates
the isolation boundary and introduces untested state into the Specialist's workspace.

Violation → RETURN BLOCKED with reason "sync not authorized by Selective Sync conditions".

────────────────────────────────────────────────────────
# § STORAGE SOVEREIGNTY

| Directory / File | Matrix Domain | Other domains (STRICT) |
|-----------------|--------------|------------------------|
| `theory/` | T-Domain (write) | L: read via `interface/AlgorithmSpecs.md` only; Q: read-only audit |
| `src/twophase/` | L-Domain (write) | A: read-only (consistency check); E: invoke via `interface/SolverAPI_vX.py` |
| `tests/` | L-Domain (write) | Q: read-only |
| `experiment/` | E-Domain (write) | Q: read-only audit |
| `results/` | E-Domain (write via ExperimentRunner) | A: read via `interface/ResultPackage/` only |
| `paper/sections/*.tex` | A-Domain (write) | L: read-only (equation alignment check); Q: read-only audit |
| `paper/bibliography.bib` | A-Domain (write) | — |
| `interface/` | Gatekeepers (write, IF-COMMIT token required) | all Specialists: read-only; Q: read-only audit |
| `audit_logs/` | Q-Domain (write, append-only) | all: read-only |
| `prompts/agents/*.md` | P-Domain (write) | — |
| `prompts/meta/*.md` | Governance (human operators + meta-deploy only) | all: read-only |
| `docs/00_GLOBAL_RULES.md` | Governance (write) | all: read-only (authoritative rule source) |
| `docs/01_PROJECT_MAP.md` | Governance (write) | all: read-only; append entries via coordinator |
| `docs/02_ACTIVE_LEDGER.md` | all (append-only) | each domain appends its own phase entries only |

| `artifacts/{T,L,E,Q}/` | [NOT YET OPERATIONAL] micro-agent artifacts | see meta-experimental.md |
| `interface/signals/` | [NOT YET OPERATIONAL] micro-agent coordination | see meta-experimental.md |

**Artifact & Signal directories [NOT YET OPERATIONAL]:** `artifacts/` and `interface/signals/`
mediate micro-agent handoffs when activated. See meta-experimental.md for full protocol.

**Directory-Driven Authorization (DDA) [NOT YET OPERATIONAL]:** When micro-agents are activated,
file access is restricted per SCOPE (READ / WRITE / FORBIDDEN) defined in
meta-experimental.md § ATOMIC ROLE TAXONOMY. See meta-experimental.md § DDA for rules DDA-01–DDA-05.

**Write-outside-domain rule:** An agent may not write to a storage path outside its domain
without an explicit cross-domain routing decision. Violation = A9 / φ2 breach → STOP immediately.

────────────────────────────────────────────────────────
# § DOMAIN LOCK PROTOCOL

A **domain lock** is a session-scoped declaration that binds the current execution context
to exactly one domain. Once set, all agents in that session must conform to that domain's
storage sovereignty and branch rules. It prevents contamination by making the active domain
explicit and machine-checkable throughout the session.

## Domain Lock Format

```
DOMAIN-LOCK:
  domain:          {Code | Paper | Prompt | Routing | Audit}
  branch:          {code | paper | prompt | none}
  set_by:          {coordinator name}
  set_at:          {git short hash — 7 chars from `git log --oneline -1`}
  write_territory: [{path_prefix_1}, {path_prefix_2}, ...]
  read_territory:  [{path_prefix_1}, {path_prefix_2}, ...]
```

`write_territory` and `read_territory` values come directly from the
§DOMAIN REGISTRY "Storage (write)" and "Storage (read)" rows for the active domain.

## Lock Lifecycle

| Event | Action |
|-------|--------|
| GIT-01 confirms branch | Coordinator runs DOM-01 → emits DOMAIN-LOCK block |
| Each DISPATCH (HAND-01) | Coordinator copies DOMAIN-LOCK into `context.domain_lock` field |
| Each specialist receives DISPATCH | HAND-03 step 6: verifies domain_lock present and consistent |
| Session ends or domain switches | Lock is dissolved; new session requires new GIT-01 + DOM-01 |

**One domain per session:** A session has at most ONE active domain lock.
If a task requires switching domains, the current session must close (VALIDATED + GIT-04 merge),
and a new session begins with ResearchArchitect routing to the new domain.

────────────────────────────────────────────────────────
# § CONTAMINATION GUARD

**Contamination** = any write to a storage path outside the active DOMAIN-LOCK.write_territory.
Contamination is a φ2 (Minimal Footprint) + A9 (Sovereignty) violation.

## Pre-Write Check (DOM-02)

Every agent, before every file write, edit, or delete, must run DOM-02:

```
□ 1. Retrieve DOMAIN-LOCK from the current DISPATCH context.
     Absent → STOP; request domain lock from coordinator before any write.
□ 2. Resolve target_path against write_territory (prefix match).
     Match → proceed to check 3.
     In read_territory only → STOP; convert to read-only access; notify coordinator.
     In neither → STOP; CONTAMINATION_GUARD violation — issue RETURN STOPPED.
□ 3. Role-extension check: verify that the writing agent's tier (from meta-ops.md §AUTHORITY TIERS)
     is sufficient for the target path:
     - interface/ writes require [AUTH_LEVEL: Gatekeeper] and an IF-COMMIT token (see below).
       Writing to interface/ without IF-COMMIT token → STOP; CONTAMINATION_GUARD violation.
     - prompts/meta/ writes require explicit Governance/meta-deploy authorization.
       Writing without that authorization → STOP; escalate to user.
     - All other territory matches from check 2 → proceed with write.
```

**IF-COMMIT token:** Required for any write to the `interface/` directory. The Gatekeeper must
emit this token before the write and include it in the commit message:
```
IF-COMMIT: domain={domain} feature={feature} gatekeeper={coordinator} set_at={git-short-hash}
```
A write to `interface/` without a valid IF-COMMIT token is a Gatekeeper tier violation → STOP.

## Recognized Contamination Patterns

| Pattern | Root cause | Required action |
|---------|-----------|----------------|
| Code agent writes `paper/sections/*.tex` | Missing `scope_out` in DISPATCH | STOP; RETURN STOPPED |
| Paper agent writes `src/twophase/*.py` | Missing `scope_out` in DISPATCH | STOP; RETURN STOPPED |
| Any agent writes `prompts/meta/*.md` | Only Governance/meta-deploy authorized | STOP; escalate to user |
| Any agent writes `docs/00_GLOBAL_RULES.md` | Governance-owned; read-only for agents | STOP; escalate to user |
| Any agent writes `interface/` without IF-COMMIT token | Gatekeeper obligation violated | STOP; CONTAMINATION_GUARD violation |
| Specialist writes `interface/` (any) | Only Gatekeeper tier may write interface/ | STOP; escalate to coordinator |
| ResearchArchitect writes any file (Routing domain) | Routing domain is No-Write | STOP; escalate to user |
| Coordinator commits on `main` directly | Branch rule violation (A8) | STOP; run GIT-01 to restore correct branch |
| Two coordinators active simultaneously | Domain lock collision | STOP; escalate to user |
| Agent invokes operation above its AUTH_LEVEL | Role-extension inconsistency | STOP; RETURN BLOCKED (HAND-03 check 0) |

## Contamination RETURN Token

When DOM-02 detects a violation, issue immediately:
```
RETURN → {coordinator}
  status:  STOPPED
  produced: none
  git:     branch={current}, commit="no-commit"
  verdict: N/A
  issues:  ["DOM-02 CONTAMINATION_GUARD: attempted write to '{target_path}';
             active domain={domain}; write_territory={write_territory_list}"]
  next:    "Coordinator must verify scope_out and re-dispatch with correct storage boundaries"
```
