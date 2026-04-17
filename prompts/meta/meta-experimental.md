# DEPRECATED — v7.0.0: Superseded by kernel-domains.md §DDA (merged). Do not edit. Retained for reference only.
# META-EXPERIMENTAL: Micro-Agent Architecture
# VERSION: 2.0.0
# STATUS: OPERATIONAL — load on demand; see meta-core.md §SYSTEM STRUCTURE for load policy
# ABSTRACT LAYER — micro-agent definitions extracted from meta-workflow.md and meta-roles.md.
# FOUNDATION (φ1–φ7, A1–A11): prompts/meta/meta-core.md  ← READ FIRST

<meta_section id="META-EXPERIMENTAL" version="5.1.0" axiom_refs="phi4,phi5,phi6,A2,A4">
<purpose>Micro-agent architecture + hierarchical L0–L3 isolation policy + Directory-Driven Authorization (DDA). Constitutional-adjacent: L0–L3 levels are referenced by every Coordinator dispatch decision.</purpose>
<authority>Coordinators (ResearchArchitect, TaskPlanner, CodeWorkflowCoordinator, PaperWorkflowCoordinator) consult this file to determine the isolation level for each HAND-01. Micro-agents (EquationDeriver, SpecWriter, LogicImplementer, etc.) inherit their SCOPE + CONTEXT_LIMIT from here.</authority>
<rules>
- MUST NOT modify the L0–L3 definitions without a CHK-tracked MetaEvolutionArchitect session (constitutional).
- MUST use L3 for cross-domain handoffs and AU2 verification.
- MUST NOT invent new isolation levels beyond L0–L3 (closed set).
- DDA enforcement is atomic — one micro-agent = one directory = one operation (see §DIRECTORY-DRIVEN AUTHORIZATION).
</rules>
<see_also>meta-core.md §B (Broken Symmetry), meta-ops.md §HAND-03 check 7, meta-persona.md §ATOMIC MICRO-AGENT PROFILES, meta-roles.md §MATRIX ROLE PAIRS</see_also>

────────────────────────────────────────────────────────
# § HIERARCHICAL ISOLATION POLICY

> **SSoT:** Isolation levels L0–L3 are defined in `meta-core.md §B.1` (canonical).
> Summary: L0=same context, L1=prompt-boundary, L2=tool-mediated, L3=session-isolated.
> Cross-domain handoffs and AU2 MUST use L3. Intra-domain approval MAY use L1.
> ResearchArchitect dispatches use L1 (intra-domain) or L3 (cross-domain).

────────────────────────────────────────────────────────
# § INTERFACE-FIRST LOOSE COUPLING

All micro-agent inputs and outputs pass through files in the `docs/interface/` and
`artifacts/` directories. Direct agent-to-agent conversation is prohibited.
Communication is file-based and asynchronous via SIGNALs.

## Principles

| # | Principle | Description |
|---|-----------|-------------|
| IF-01 | No direct conversation | Agents never pass context directly — all data flows through `docs/interface/` or `artifacts/` files |
| IF-02 | Artifact-mediated handoff | HAND-01/HAND-02 tokens reference artifact paths, not inline content |
| IF-03 | SIGNAL-based coordination | State transitions are communicated via SIGNAL files, not agent dialogue |
| IF-04 | Immutable artifacts | Once an artifact is signed, it is read-only until a new version is produced |

## Artifact Directory Structure

```
artifacts/
  T/                     ← Theory domain artifacts
    derivation_{id}.md   ← EquationDeriver output
    spec_{id}.md         ← SpecWriter output
  L/                     ← Library domain artifacts
    architecture_{id}.md ← CodeArchitect (Atomic) output
    impl_{id}.py         ← LogicImplementer output
    diagnosis_{id}.md    ← ErrorAnalyzer output
    fix_{id}.patch       ← RefactorExpert output
  E/                     ← Evaluation domain artifacts
    test_spec_{id}.md    ← TestDesigner output
    run_{id}.log         ← VerificationRunner output
  Q/                     ← Audit domain artifacts
    audit_{id}.md        ← ResultAuditor output
```

**Naming:** `{type}_{id}.{ext}` — `{id}` zero-padded 3 digits (e.g., `derivation_001.md`).

## SIGNAL Protocol

SIGNALs are lightweight status files in `docs/interface/signals/{domain}_{id}.signal.md`.

| Type | Meaning | Receiver action |
|------|---------|-----------------|
| READY | Upstream artifact available | Receiver may begin work |
| BLOCKED | Cannot produce artifact; blocker in body | Receiver must wait |
| INVALIDATED | Previously signed artifact no longer valid | Discard cached state; wait for new READY |
| COMPLETE | Domain pipeline fully complete | Downstream domain may begin |

On-demand rules (emission, append-only policy, CI/CP propagation): → meta-workflow.md §SIGNAL RULES.

────────────────────────────────────────────────────────
# § ATOMIC ROLE & BRANCH MATRIX

| Micro-Agent | Domain | Isolation Branch Pattern | Merge Authority |
|-------------|--------|--------------------------|-----------------|
| EquationDeriver | T | `dev/T/EquationDeriver/{task_id}` | ConsistencyAuditor (T-Gate) |
| SpecWriter | T | `dev/T/SpecWriter/{task_id}` | ConsistencyAuditor (T-Gate) |
| CodeArchitect (Atomic) | L | `dev/L/CodeArchitectAtomic/{task_id}` | CodeWorkflowCoordinator |
| LogicImplementer | L | `dev/L/LogicImplementer/{task_id}` | CodeWorkflowCoordinator |
| ErrorAnalyzer | L | `dev/L/ErrorAnalyzer/{task_id}` | CodeWorkflowCoordinator |
| RefactorExpert | L | `dev/L/RefactorExpert/{task_id}` | CodeWorkflowCoordinator |
| TestDesigner | E | `dev/E/TestDesigner/{task_id}` | CodeWorkflowCoordinator |
| VerificationRunner | E | `dev/E/VerificationRunner/{task_id}` | CodeWorkflowCoordinator |
| ResultAuditor | Q | `dev/Q/ResultAuditor/{task_id}` | ConsistencyAuditor |

Branch pattern: `dev/{domain}/{agent_id}/{task_id}` — Specialist agents MUST NOT commit to `main` or integration branches; violation triggers **SYSTEM_PANIC** (→ meta-ops.md §STOP CONDITIONS).

────────────────────────────────────────────────────────
# § ATOMIC ROLE TAXONOMY — Micro-Agent Decomposition

**Hierarchy:** Domain → Micro-Agent → single function. No micro-agent spans domains.

## Theory Domain (T)

| Micro-Agent | Parent Role | Function |
|-------------|-------------|----------|
| EquationDeriver | TheoryArchitect | Derives equations; validates theoretical correctness |
| SpecWriter | TheoryArchitect | Converts derivations into implementation-ready specs |

### EquationDeriver
- **PURPOSE:** Derive governing equations from first principles; produce mathematical artifacts only.
- **BRANCH:** `dev/T/EquationDeriver/{task_id}`
- **READ:** `paper/sections/*.tex`, `docs/memo/`, `docs/01_PROJECT_MAP.md §6`
- **WRITE:** `docs/memo/`, `artifacts/T/` — FORBIDDEN: `src/`, `prompts/`, `docs/interface/` (write)
- **CTX:** ≤4000 tokens — target equation context + symbol table only
- **DELIVERABLE:** `artifacts/T/derivation_{id}.md` (derivation + assumption register with ASM-IDs)
- **STOP:** Physical assumption ambiguity → escalate to user

### SpecWriter
- **PURPOSE:** Convert validated derivation into implementation-ready spec; bridge T→L without implementing.
- **BRANCH:** `dev/T/SpecWriter/{task_id}`
- **READ:** `artifacts/T/derivation_{id}.md`, `docs/01_PROJECT_MAP.md §6`
- **WRITE:** `docs/interface/AlgorithmSpecs.md`, `artifacts/T/spec_{id}.md` — FORBIDDEN: `src/`, `paper/` (write)
- **CTX:** ≤3000 tokens — derivation artifact + symbol mapping table only
- **DELIVERABLE:** `artifacts/T/spec_{id}.md` (symbol mapping, discretization recipe, technology-agnostic)
- **STOP:** Derivation artifact missing/unsigned → request EquationDeriver run

## Library Domain (L)

| Micro-Agent | Parent Role | Function |
|-------------|-------------|----------|
| CodeArchitect (Atomic) | CodeArchitect | Designs class structures and interfaces only |
| LogicImplementer | CodeArchitect | Writes logic (method bodies) only |
| ErrorAnalyzer | CodeCorrector | Identifies root causes from error logs only |
| RefactorExpert | CodeCorrector | Applies fixes from ErrorAnalyzer diagnosis only |

### CodeArchitect (Atomic)
- **PURPOSE:** Design class structures, interfaces, module organization; no method body logic.
- **BRANCH:** `dev/L/CodeArchitectAtomic/{task_id}`
- **READ:** `docs/interface/AlgorithmSpecs.md`, `src/twophase/` (structure), `docs/01_PROJECT_MAP.md`
- **WRITE:** `artifacts/L/architecture_{id}.md`, `src/twophase/` (interface/abstract files only) — FORBIDDEN: method bodies, `paper/`, `docs/memo/`
- **CTX:** ≤5000 tokens — spec artifact + existing module structure
- **DELIVERABLE:** `artifacts/L/architecture_{id}.md` (class/interface defs, module dependency graph)
- **STOP:** Spec ambiguity → request SpecWriter clarification

### LogicImplementer
- **PURPOSE:** Write method body logic from architecture definitions; fill skeleton produced by CodeArchitect.
- **BRANCH:** `dev/L/LogicImplementer/{task_id}`
- **READ:** `artifacts/L/architecture_{id}.md`, `docs/interface/AlgorithmSpecs.md`, `src/twophase/` (target module)
- **WRITE:** `src/twophase/` (method bodies only), `artifacts/L/impl_{id}.py` — FORBIDDEN: class signatures, `paper/`, `docs/interface/` (write)
- **CTX:** ≤5000 tokens — architecture artifact + spec + target module only
- **DELIVERABLE:** `artifacts/L/impl_{id}.py` (method bodies with equation-number docstrings per A3)
- **STOP:** Architecture artifact missing → request CodeArchitect (Atomic) run

### ErrorAnalyzer
- **PURPOSE:** Identify root causes from error logs; produce diagnosis only — never apply fixes.
- **BRANCH:** `dev/L/ErrorAnalyzer/{task_id}`
- **READ:** `tests/last_run.log`, `artifacts/E/`, `src/twophase/` (target module only)
- **WRITE:** `artifacts/L/diagnosis_{id}.md` — FORBIDDEN: any source file, `paper/`, `docs/interface/`
- **CTX:** ≤3000 tokens — error log (last 200 lines) + target module only
- **DELIVERABLE:** `artifacts/L/diagnosis_{id}.md` (root cause, P9 classification THEORY_ERR/IMPL_ERR, confidence scores)
- **STOP:** Insufficient log data → request VerificationRunner rerun

### RefactorExpert
- **PURPOSE:** Apply targeted fixes from ErrorAnalyzer diagnosis; consume diagnosis artifacts only.
- **BRANCH:** `dev/L/RefactorExpert/{task_id}`
- **READ:** `artifacts/L/diagnosis_{id}.md`, `src/twophase/` (target module)
- **WRITE:** `src/twophase/` (fix patches), `artifacts/L/fix_{id}.patch` — FORBIDDEN: `paper/`, `docs/interface/`, unrelated modules
- **CTX:** ≤4000 tokens — diagnosis artifact + target module only
- **DELIVERABLE:** `artifacts/L/fix_{id}.patch` (minimal fix; no scope creep; §C2 tested-code preservation)
- **STOP:** Diagnosis artifact missing → request ErrorAnalyzer run

## Evaluation Domain (E/Q)

| Micro-Agent | Parent Role | Function |
|-------------|-------------|----------|
| TestDesigner | TestRunner | Designs tests for boundary conditions and edge cases |
| VerificationRunner | TestRunner + ExperimentRunner | Executes code and collects logs |
| ResultAuditor | ConsistencyAuditor | Audits results against theoretical expectations |

### TestDesigner
- **PURPOSE:** Design test cases, boundary conditions, MMS solutions; produce test specs only — never execute.
- **BRANCH:** `dev/E/TestDesigner/{task_id}`
- **READ:** `docs/interface/AlgorithmSpecs.md`, `src/twophase/` (API surface), `artifacts/L/`
- **WRITE:** `tests/`, `artifacts/E/test_spec_{id}.md` — FORBIDDEN: source code modification, test execution, `paper/`
- **CTX:** ≤4000 tokens — spec + module API surface only
- **DELIVERABLE:** `artifacts/E/test_spec_{id}.md` (pytest files, MMS N=[32,64,128,256], BC coverage matrix)
- **STOP:** Algorithm spec missing → request SpecWriter output

### VerificationRunner
- **PURPOSE:** Execute tests, simulations, benchmarks; collect logs — no judgment, no interpretation.
- **BRANCH:** `dev/E/VerificationRunner/{task_id}`
- **READ:** `tests/`, `src/twophase/`, `artifacts/E/test_spec_{id}.md`
- **WRITE:** `tests/last_run.log`, `experiment/{experiment_name}/`, `artifacts/E/run_{id}.log` — FORBIDDEN: source/test modification, result interpretation, `paper/`
- **CTX:** ≤2000 tokens — test spec + execution command only
- **DELIVERABLE:** `artifacts/E/run_{id}.log` (pytest output, simulation output + PDFs, EXP-02 SC-1..SC-4)
- **STOP:** Execution environment error → report to coordinator

### ResultAuditor
- **PURPOSE:** Audit execution results against theoretical expectations; produce verdicts only.
- **BRANCH:** `dev/Q/ResultAuditor/{task_id}`
- **READ:** `artifacts/T/derivation_{id}.md`, `artifacts/E/run_{id}.log`, `docs/interface/AlgorithmSpecs.md`
- **WRITE:** `artifacts/Q/audit_{id}.md`, `docs/02_ACTIVE_LEDGER.md` — FORBIDDEN: source, test, or paper files
- **CTX:** ≤4000 tokens — derivation artifact + execution log + spec only
- **DELIVERABLE:** `artifacts/Q/audit_{id}.md` (convergence table, PASS/FAIL verdict, error routing PAPER_ERROR/CODE_ERROR, AU2 gate items 1/4/6)
- **STOP:** Theory artifact missing → request EquationDeriver; execution artifact missing → request VerificationRunner

────────────────────────────────────────────────────────
# § DIRECTORY-DRIVEN AUTHORIZATION (DDA)

The tool wrapper intercepts reads/writes outside the agent's declared SCOPE and returns a DDA error; agents do not pre-check. Authorization is derived from SCOPE in § ATOMIC ROLE TAXONOMY.

| Rule | Description |
|------|-------------|
| DDA-01 | READ access limited to SCOPE.READ paths |
| DDA-02 | WRITE access limited to SCOPE.WRITE paths |
| DDA-03 | SCOPE.FORBIDDEN path → immediate REJECT |
| DDA-04 | DDA checked before DOM-02 — DDA is the first gate |
| DDA-05 | Violations logged to `docs/02_ACTIVE_LEDGER.md §AUDIT dda_violation_{date}.md` |

**SCOPE Inheritance:** Composite coordinators inherit the union of constituent micro-agent SCOPEs. When acting as a specific micro-agent, only that agent's SCOPE applies.

**HAND-01-TE (Token Efficiency):** When processing a DISPATCH, load ONLY the artifact file from `DISPATCH.inputs` — not the producing agent's logs or reasoning. Previous agent session context and intermediate files are INVISIBLE to the receiving agent.

────────────────────────────────────────────────────────
# § ATOMIC MICRO-AGENT OPERATION INDEX

| Tier | Role | Operations |
|------|------|------------|
| Specialist | EquationDeriver | GIT-SP |
| Specialist | SpecWriter | GIT-SP |
| Specialist | CodeArchitectAtomic | GIT-SP |
| Specialist | LogicImplementer | GIT-SP |
| Specialist | ErrorAnalyzer | GIT-SP |
| Specialist | RefactorExpert | GIT-SP |
| Specialist | TestDesigner | GIT-SP |
| Specialist | VerificationRunner | GIT-SP, TEST-01, EXP-01, EXP-02 |
| Specialist | ResultAuditor | GIT-SP, AUDIT-01, AUDIT-02 |
</meta_section>
