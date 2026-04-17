# WIKI-M-018: Domain Architecture Complete Reference
**Category:** Meta | **Created:** 2026-04-18
**Sources:** `prompts/meta/meta-domains.md` (full), `prompts/meta/meta-ops.md §DOM-01/02`

## 4×4 Domain Matrix

```
                 ┌───────────────────── HORIZONTAL (Governance) ─────────────────────┐
                 │  M (Meta-Logic)   P (Prompt/Env)  Q (QA/Audit)   K (Knowledge)    │
     ┌───────────┼───────────────────────────────────────────────────────────────────┤
     │ T (Theory)│  ResearchArch.   PromptArchitect  ConsistAuditor  KnowledgeArch.  │
V    │           │  Routes sessions  Manages prompts  Cross-system    Compiles wiki   │
E    ├───────────┼───────────────────────────────────────────────────────────────────┤
R    │ L (Library│  TaskPlanner     PromptAuditor    WikiAuditor     Librarian        │
T    │           │  Plans across L  Audits prompts   Guards wiki     Tracks refs      │
I    ├───────────┼───────────────────────────────────────────────────────────────────┤
C    │ E (Exper.)│  DevOpsArchitect                  TraceabilityMgr                  │
A    │           │  Infrastructure                   Dep. tracing                    │
L    ├───────────┼───────────────────────────────────────────────────────────────────┤
     │ A (Paper) │  DiagnosticArch.                                                   │
     │           │  Self-healing                                                      │
     └───────────┴───────────────────────────────────────────────────────────────────┘
```

**Simplified view:**

| ID | Dimension | Domain | Truth Type | Directory | Gatekeeper |
|----|-----------|--------|-----------|-----------|------------|
| T | Vertical | Theory & Analysis | Mathematical Truth | `docs/memo/` | TheoryAuditor |
| L | Vertical | Core Library | Functional Truth | `src/` | CodeWorkflowCoordinator |
| E | Vertical | Experiment | Empirical Truth | `experiment/` | ExperimentRunner |
| A | Vertical | Academic Writing | Logical Truth | `paper/` | PaperWorkflowCoordinator |
| M | Horizontal | Meta-Logic | The Judiciary | — | ResearchArchitect |
| P | Horizontal | Prompt & Environment | The Infrastructure | `prompts/agents-{env}/` | PromptAuditor |
| Q | Horizontal | QA & Audit | Internal Affairs | — | ConsistencyAuditor |
| K | Horizontal | Knowledge/Wiki | The Standard Library | `docs/wiki/` | WikiAuditor |

**Sovereignty rule:** Each vertical domain acts as an independent "Corporation."
All inter-domain communication must pass through a Gatekeeper-approved Interface Contract.

---

## Domain Registry (Full)

### Domain: Routing (M-entry)

| Property | Value |
|----------|-------|
| Git branch | none — stateless; reads current state from `main` |
| Coordinator | ResearchArchitect |
| Members | ResearchArchitect |
| Storage (write) | **NONE** — strictly No-Write for all files |
| Storage (read) | `docs/02_ACTIVE_LEDGER.md`, `docs/01_PROJECT_MAP.md` |
| Lifecycle | none — entry point only; routes to domain then exits |

**No-Write rule:** ResearchArchitect must not write during the Routing phase.
Writing is delegated to the receiving domain's coordinator after routing.

### Domain: Theory (T)

| Property | Value |
|----------|-------|
| Git branch | `theory` |
| Coordinator | TheoryArchitect |
| Gatekeeper | TheoryAuditor |
| Members | TheoryArchitect, TheoryAuditor, EquationDeriver (micro), SpecWriter (micro) |
| Storage (write) | `docs/memo/`, `docs/02_ACTIVE_LEDGER.md` |
| Storage (read) | `paper/sections/*.tex`, `docs/01_PROJECT_MAP.md §6` |
| Upstream interface | none (T is the top of the chain) |
| Downstream interface | `docs/interface/AlgorithmSpecs.md` (→ L-Domain) |

### Domain: Library / Code (L)

| Property | Value |
|----------|-------|
| Git branch | `code` |
| Coordinator | CodeWorkflowCoordinator |
| Gatekeeper | CodeWorkflowCoordinator |
| Members | CodeArchitect, CodeCorrector, CodeReviewer, TestRunner, VerificationRunner |
| Storage (write) | `src/twophase/`, `tests/`, `docs/02_ACTIVE_LEDGER.md` |
| Storage (read) | `paper/sections/*.tex`, `docs/01_PROJECT_MAP.md`, `docs/interface/AlgorithmSpecs.md` |
| Upstream interface | `docs/interface/AlgorithmSpecs.md` (from T) |
| Downstream interface | `docs/interface/SolverAPI_vX.py` (→ E-Domain) |

### Domain: Experiment (E)

| Property | Value |
|----------|-------|
| Git branch | `experiment` |
| Coordinator | ExperimentRunner |
| Gatekeeper | ExperimentRunner |
| Members | ExperimentRunner, SimulationAnalyst, TestDesigner (micro) |
| Storage (write) | `experiment/`, `docs/02_ACTIVE_LEDGER.md` |
| Storage (read) | `docs/interface/SolverAPI_vX.py`, `src/twophase/` |
| Upstream interface | `docs/interface/SolverAPI_vX.py` (from L) |
| Downstream interface | `docs/interface/ResultPackage/`, `docs/interface/TechnicalReport.md` (→ A-Domain) |

### Domain: Academic Writing (A)

| Property | Value |
|----------|-------|
| Git branch | `paper` |
| Coordinator | PaperWorkflowCoordinator |
| Gatekeeper | PaperReviewer |
| Members | PaperWriter, PaperReviewer, PaperCompiler |
| Storage (write) | `paper/sections/*.tex`, `paper/bibliography.bib`, `docs/02_ACTIVE_LEDGER.md` |
| Storage (read) | `src/twophase/`, `docs/interface/ResultPackage/`, `docs/interface/TechnicalReport.md` |
| Upstream interface | `docs/interface/ResultPackage/` and `docs/interface/TechnicalReport.md` (from E and T/E) |

### Domain: Prompt (P)

| Property | Value |
|----------|-------|
| Git branch | `prompt` |
| Coordinator | PromptArchitect |
| Gatekeeper | PromptAuditor |
| Members | PromptArchitect, PromptAuditor |
| Storage (write) | `prompts/agents-{env}/*.md` |
| Storage (read) | `prompts/meta/*.md` |
| Rule | Edits to agents-{env}/ only; meta/ is read-only (A10) |

### Domain: Quality / Audit (Q)

| Property | Value |
|----------|-------|
| Git branch | none (operates read-only across all domains) |
| Coordinator | ConsistencyAuditor |
| Members | ConsistencyAuditor |
| Storage (write) | `docs/02_ACTIVE_LEDGER.md` (append-only audit log) |
| Storage (read) | ALL domains (cross-system read scope) |
| Trigger | Invoked before any merge to `main` (AUDIT-01 AU2 gate) |

### Domain: Knowledge / Wiki (K)

| Property | Value |
|----------|-------|
| Git branch | `wiki` |
| Coordinator | KnowledgeArchitect |
| Gatekeeper | WikiAuditor |
| Members | KnowledgeArchitect, WikiAuditor, Librarian, TraceabilityManager |
| Storage (write) | `docs/wiki/`, `docs/02_ACTIVE_LEDGER.md` (compilation trail, append-only) |
| Storage (read) | ALL domains (same scope as Q + `docs/wiki/`) |
| Storage (FORBIDDEN write) | any domain's primary artifacts |
| Rules | K-A1–K-A5 (below), A2 (External Memory), A11 (Knowledge-First Retrieval) |
| Lifecycle | DRAFT → WikiAuditor K-LINT PASS → VALIDATED (published to docs/wiki/) |

---

## K-Domain Axioms (K-A1..K-A5)

### K-A1: No Unstructured Raw Text
Direct writes to `docs/wiki/` are forbidden. All knowledge passes through the K-COMPILE process:
Source artifact (VALIDATED phase) → KnowledgeArchitect K-COMPILE → Compiled Wiki Entry.

### K-A2: Pointer Integrity (Link Validation)
Every `[[REF-ID]]` in the wiki MUST resolve to an existing, ACTIVE entry.
A broken reference = Segmentation Fault → STOP-HARD; fix before proceeding.
Maps to φ1 (Truth Before Action): you cannot reference knowledge that does not exist.

### K-A3: Single Source of Truth (SSoT)
Duplicate knowledge is a refactoring target. Every concept is defined in exactly **one** wiki entry.
All other references use `[[REF-ID]]` pointers. Duplication = φ6 violation.

### K-A4: Empirical Grounding & Lineage
Every wiki entry carries: source artifact path, source git hash, domain of origin, dependent theory IDs.
This enables A3 traceability at the knowledge level.

### K-A5: Knowledge Mutability (Versioning)
Knowledge is not immutable. On error detection or strategy change:
- Do NOT delete entries — transition to `DEPRECATED` or `SUPERSEDED` status.
- `DEPRECATED` entries retain a pointer to the replacement (`superseded_by: [[REF-ID]]`).
- Status transitions trigger `RE-VERIFY` signals to all consuming domains.

---

## Inter-Domain Interface Contracts

Every cross-domain data transfer requires a Gatekeeper-approved Interface Contract.
No Specialist may consume artifacts from another domain without a valid contract on `docs/interface/`.

| Transfer | Contract Artifact | Precondition | Consumer |
|----------|------------------|--------------|---------|
| T → L | `docs/interface/AlgorithmSpecs.md` | TheoryAuditor PASS; equations formalized | L-Domain |
| L → E | `docs/interface/SolverAPI_vX.py` | TestRunner PASS (all unit tests) | E-Domain |
| E → A | `docs/interface/ResultPackage/` | Validation Guard PASS (all sanity checks); raw logs included | A-Domain |
| T/E → A | `docs/interface/TechnicalReport.md` | Both T-Auditor and Validation Guard sign | A-Domain |
| T → K | `docs/wiki/theory/{REF-ID}.md` | TheoryAuditor PASS; derivation VALIDATED | K-Domain |
| L → K | `docs/wiki/code/{REF-ID}.md` | TestRunner PASS; code VALIDATED | K-Domain |
| E → K | `docs/wiki/experiment/{REF-ID}.md` | Validation Guard PASS; results VALIDATED | K-Domain |
| A → K | `docs/wiki/paper/{REF-ID}.md` | Logical Reviewer PASS; paper VALIDATED | K-Domain |
| K → all | `docs/wiki/{category}/{REF-ID}.md` | WikiAuditor PASS; entry ACTIVE | All (read-only, A11) |

**Contract immutability rule:** Once a Specialist's `dev/` branch is created from a contract, the
contract is immutable. Changing it requires: close current `dev/` branch → update contract →
new IF-AGREEMENT → new `dev/` branch.

---

## IF-Agreement Protocol (GIT-00)

**Trigger:** MANDATORY before any Specialist starts work on a `dev/` branch.

**Interface contract format (in `docs/interface/{domain}_{feature}.md`):**
```
IF-AGREEMENT:
  feature:          {one-line description}
  domain:           {Code | Paper | Prompt}
  gatekeeper:       {coordinator name}
  specialist:       {target agent role}
  inputs:           [{artifact_path}: {description}, ...]
  outputs:          [{artifact_path}: {description}, ...]
  success_criteria: {measurable criterion matching MERGE CRITERIA in meta-ops.md}
  created_at:       {git short hash at time of creation}
```

**Rules:**
- No Specialist may create a `dev/` branch without a valid IF-AGREEMENT on `docs/interface/`
- IF-AGREEMENT is immutable once the Specialist's `dev/` branch is created
- Changes require: close dev/ → new IF-AGREEMENT → new dev/ branch
- ConsistencyAuditor reads IF-AGREEMENT during AUDIT to verify output matches contract
- Writing to `docs/interface/` requires an IF-COMMIT token (Gatekeepers only)

---

## Branch Naming Conventions

```
main                          — protected; Root Admin merge only
code / paper / prompt / wiki  — domain integration staging
dev/{domain}/{agent_id}/{task_id}  — individual Specialist workspaces (sovereign)
```

Branch rules:
- No Specialist may work directly on integration branches
- `dev/` branches are sovereign: no cross-agent access without Gatekeeper routing
- Merge path: `dev/{agent_role}` → `{domain}` (Gatekeeper PR) → `main` (Root Admin PR after VALIDATED)

---

## Storage Sovereignty Table

| Directory / File | Owning Domain | Other Domains |
|-----------------|--------------|---------------|
| `docs/memo/` | T + A (shared write) | L: read-only; Q: read-only audit |
| `src/twophase/` | L (write) | E: invoke via SolverAPI contract; A: read-only; Q: read-only audit |
| `tests/` | L (write) | Q: read-only |
| `experiment/` | E (write) | Q: read-only audit |
| `paper/sections/*.tex` | A (write) | L: read-only (equation check); Q: read-only audit |
| `paper/bibliography.bib` | A (write) | — |
| `docs/interface/` | Gatekeepers (write, IF-COMMIT required) | All Specialists: read-only; Q: read-only audit |
| `docs/02_ACTIVE_LEDGER.md` | All (append-only, own domain entries only) | — |
| `prompts/agents-{env}/*.md` | P (write) | — |
| `prompts/meta/*.md` | Governance + meta-deploy only | All: read-only |
| `docs/00_GLOBAL_RULES.md` | Governance (write) | All: read-only |
| `docs/wiki/` | K (write) | All: read-only (A11) |
| `docs/locks/` | All (branch lock files via LOCK-ACQUIRE) | — |

---

## Selective Sync Protocol

Agents pull from `main` ONLY under one of these conditions:

| Condition | Trigger | Action |
|-----------|---------|--------|
| Interface file updated | Gatekeeper notifies Specialist of `docs/interface/` change | `git fetch origin main && git merge origin/main` |
| Physical merge conflict | `git merge` exits with conflict markers | `git fetch origin main && git merge origin/main` — then resolve |

**Default (neither condition met):** do NOT pull from `main`. Gratuitous syncing contaminates
the isolation boundary and introduces untested state into the Specialist's workspace.

---

## Wiki Entry YAML Format

```yaml
WIKI-ENTRY:
  ref_id:        {unique ID, e.g., WIKI-T-001}
  title:         {concise descriptive title}
  domain:        {T | L | E | A | cross-domain}
  status:        {ACTIVE | DEPRECATED | SUPERSEDED}
  superseded_by: {[[REF-ID]] or null}
  sources:
    - path:      {source artifact path}
      git_hash:  {short hash at time of compilation}
  depends_on:    [{[[REF-ID]], ...}]
  created_at:    {ISO 8601 date}
```

### Wiki Entry Lifecycle

```
          ┌─────────┐
          │  DRAFT  │  KnowledgeArchitect compiles on dev/K branch
          └────┬────┘
               │ WikiAuditor K-LINT PASS + K-IMPACT-ANALYSIS
          ┌────▼────┐
          │VALIDATED│  Published to docs/wiki/ on main
          └────┬────┘
     ┌─────────┴──────────┐
┌────▼─────┐        ┌─────▼──────┐
│DEPRECATED│        │ SUPERSEDED │
│(error/   │        │(replaced by│
│ stale)   │        │ new entry) │
└──────────┘        └────────────┘
```

State transitions require WikiAuditor approval.
RE-VERIFY signals are mandatory — consuming domains must acknowledge and re-validate
any artifact depending on a DEPRECATED or SUPERSEDED entry.

---

## DOM-01: Domain Lock Format

Established by Gatekeeper AFTER GIT-01, BEFORE any DISPATCH or file edit:

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

## DOM-02: Pre-Write Storage Check (Contamination Guard)

Universal — applies to every agent on every file write.

**Failure modes:**
- DOMAIN-LOCK absent → STOP signal; request domain lock from coordinator
- Target path outside `write_territory` → CONTAMINATION_GUARD error; notify coordinator

---

## Cross-References

- `→ WIKI-M-007`: K-Domain addition history (K-A1..K-A5, wiki entry format)
- `→ WIKI-M-004`: Constitutional foundations (domain sovereignty as architectural principle)
- `→ WIKI-M-020`: DOM-01/02 operational specs + IF-COMMIT token format
- `→ WIKI-M-019`: Workflow protocols (how domains interact in P-E-V-A pipeline)
