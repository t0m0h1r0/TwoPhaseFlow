# META-DOMAINS: Domain Registry
# ABSTRACT LAYER — STRUCTURE: authoritative definition of all system domains.
# Each domain defines: git branch ownership, storage territory, agent membership,
# coordinator, applicable rules, and lifecycle phase triggers.
# FOUNDATION (φ1–φ7, A1–A10): prompts/meta/meta-core.md  ← READ FIRST
# Role contracts per agent: prompts/meta/meta-roles.md
# Pipeline execution order: prompts/meta/meta-workflow.md

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
## Domain: Code

| Property | Value |
|----------|-------|
| Git branch | `code` (sub-branches: `code/{feature}`) |
| Coordinator | CodeWorkflowCoordinator |
| Members | CodeWorkflowCoordinator, CodeArchitect, CodeCorrector, CodeReviewer, TestRunner, ExperimentRunner |
| Storage (write) | `src/twophase/`, `tests/`, `docs/02_ACTIVE_LEDGER.md` |
| Storage (read) | `paper/sections/*.tex`, `docs/01_PROJECT_MAP.md` |
| Rules | docs/00_GLOBAL_RULES.md §C (C1–C6: SOLID, preserve-tested, builder, solver policy, quality, MMS) |
| Lifecycle | **DRAFT** — CodeArchitect or CodeCorrector returns COMPLETE<br>**REVIEWED** — TestRunner PASS (all convergence tests pass)<br>**VALIDATED** — ConsistencyAuditor AU2 PASS → merge `code` → `main` |

**Cross-domain read:** Code agents read `paper/sections/*.tex` to verify equation–code alignment (A3).
Code agents must not write to `paper/` — route to Paper domain instead.

**Legacy register:** docs/01_PROJECT_MAP.md §C2 Legacy Register — list of classes that must
not be deleted (C2 preserve-tested rule). CodeArchitect must consult before removing any class.

────────────────────────────────────────────────────────
## Domain: Paper

| Property | Value |
|----------|-------|
| Git branch | `paper` (sub-branches: `paper/{section}`) |
| Coordinator | PaperWorkflowCoordinator |
| Members | PaperWorkflowCoordinator, PaperWriter, PaperCompiler, PaperReviewer, PaperCorrector |
| Storage (write) | `paper/sections/*.tex`, `paper/bibliography.bib`, `docs/02_ACTIVE_LEDGER.md` |
| Storage (read) | `src/twophase/` (for consistency checks only) |
| Rules | docs/00_GLOBAL_RULES.md §P (P1–P4, KL-12: LaTeX authoring, cross-refs, consistency, skepticism) |
| Lifecycle | **DRAFT** — PaperWriter diff-patch returned COMPLETE<br>**REVIEWED** — PaperReviewer: 0 FATAL + 0 MAJOR findings (loop ≤ MAX_REVIEW_ROUNDS)<br>**VALIDATED** — ConsistencyAuditor AU2 PASS → merge `paper` → `main` |

**Cross-domain read:** Paper agents read `src/twophase/` for equation–implementation consistency checks.
Paper agents must not write to `src/` — route to Code domain instead.

**P3-D register:** docs/01_PROJECT_MAP.md §P3-D Register — multi-site parameter definitions.
PaperWriter must consult when changing a symbol that appears in multiple sections.

────────────────────────────────────────────────────────
## Domain: Prompt

| Property | Value |
|----------|-------|
| Git branch | `prompt` |
| Coordinator | PromptArchitect (acts as both coordinator and primary executor) |
| Members | PromptArchitect, PromptCompressor, PromptAuditor |
| Storage (write) | `prompts/agents/*.md` |
| Storage (read) | `prompts/meta/*.md` (source only; never edit agents/ via meta/) |
| Rules | docs/00_GLOBAL_RULES.md §Q (Q1–Q4: standard template, env profiles, audit checklist, compression) |
| Lifecycle | **DRAFT** — PromptArchitect generates agent prompt (GIT-02)<br>**REVIEWED** — PromptAuditor Q3 checklist PASS (GIT-03)<br>**VALIDATED** — PromptAuditor gate PASS → merge `prompt` → `main` (GIT-04) |

**Note:** Prompt domain has no separate coordinator above PromptArchitect.
PromptArchitect dispatches to PromptCompressor (compress path) or PromptAuditor (review path).

────────────────────────────────────────────────────────
## Domain: Audit

| Property | Value |
|----------|-------|
| Git branch | none — operates on the calling domain's branch |
| Coordinator | ConsistencyAuditor (direct gate; no orchestrator above it) |
| Members | ConsistencyAuditor |
| Storage (write) | none — read-only cross-domain gate |
| Storage (read) | all domains: `paper/sections/*.tex`, `src/twophase/`, `docs/01_PROJECT_MAP.md` |
| Rules | docs/00_GLOBAL_RULES.md §AU (AU1–AU3: authority chain, AU2 gate 10 items, verification A–E) |
| Lifecycle | triggers VALIDATED phase for Code and Paper domains upon AU2 PASS verdict |

**Domain purpose:** Cross-system consistency gate. ConsistencyAuditor is the only agent with
read access across all storage territories. It does not produce artifacts — it issues PASS/FAIL
verdicts that either unlock merge-to-main or route errors back to the appropriate domain.

**Error routing:**
- PAPER_ERROR → PaperWriter (Paper domain)
- CODE_ERROR → CodeArchitect → TestRunner (Code domain)
- Authority conflict → escalate to domain coordinator → user

────────────────────────────────────────────────────────
# § BRANCH RULES

| Branch | Tier | Owned by | May commit | Merge target | Created by |
|--------|------|----------|------------|--------------|------------|
| `main` | — | system | never directly | — | Root Admin |
| `code` | Domain Integration | Code Gatekeeper | CodeWorkflowCoordinator | `main` via PR (Root Admin executes) | CodeWorkflowCoordinator |
| `paper` | Domain Integration | Paper Gatekeeper | PaperWorkflowCoordinator | `main` via PR (Root Admin executes) | PaperWorkflowCoordinator |
| `prompt` | Domain Integration | Prompt Gatekeeper | PromptArchitect, PromptAuditor | `main` via PR (Root Admin executes) | PromptArchitect |
| `dev/{agent_role}` | Individual Workspace | named agent only | named agent only | `{domain}` via PR | Specialist at task start |
| `interface/` | Shared Agreements | Gatekeepers | Gatekeepers only | — (referenced, not merged) | Gatekeeper before task |

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

| Directory / File | Owner domain | Other domains |
|-----------------|-------------|---------------|
| `src/twophase/` | Code | Paper: read-only (consistency check) |
| `tests/` | Code | — |
| `paper/sections/*.tex` | Paper | Code: read-only (equation check) |
| `paper/bibliography.bib` | Paper | — |
| `prompts/agents/*.md` | Prompt | — |
| `prompts/meta/*.md` | Governance (human operators + meta-deploy) | all: read-only |
| `docs/00_GLOBAL_RULES.md` | Governance | all: read-only (authoritative rule source) |
| `docs/01_PROJECT_MAP.md` | Governance | all: read-only; append entries via coordinator |
| `docs/02_ACTIVE_LEDGER.md` | all (append-only) | each domain appends its own phase entries |
| `results/` | Code (ExperimentRunner writes) | Paper: read-only (PaperWriter consumes) |

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
