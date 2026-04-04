# META-EXPERIMENTAL: Aspirational Micro-Agent Architecture
# VERSION: 1.0.0
# STATUS: OPERATIONAL — activated 2026-04-04 via EnvMetaBootstrapper --activate-microagents
# ABSTRACT LAYER — future micro-agent infrastructure extracted from meta-workflow.md and meta-roles.md.
# This file is load-on-demand only. Do not include in standard agent generation unless activating micro-agents.
# FOUNDATION (φ1–φ7, A1–A10): prompts/meta/meta-core.md  ← READ FIRST

────────────────────────────────────────────────────────
# § ACTIVATION PREREQUISITES

Before any content in this file becomes operational:
1. `artifacts/{T,L,E,Q}/` directories must be created and populated
2. `docs/interface/signals/` directory must be created
3. EnvMetaBootstrapper must be run with `--activate-microagents` flag
4. DDA enforcement tooling must be implemented
5. All composite roles continue to work without this file

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
  T/                    ← Theory domain artifacts
    derivation_{id}.md  ← EquationDeriver output
    spec_{id}.md        ← SpecWriter output
  L/                    ← Library domain artifacts
    architecture_{id}.md ← CodeArchitect (Atomic) output
    impl_{id}.py        ← LogicImplementer output
    diagnosis_{id}.md   ← ErrorAnalyzer output
    fix_{id}.patch      ← RefactorExpert output
  E/                    ← Evaluation domain artifacts
    test_spec_{id}.md   ← TestDesigner output
    run_{id}.log        ← VerificationRunner output
  Q/                    ← Audit domain artifacts
    audit_{id}.md       ← ResultAuditor output
```

**Naming convention:** `{type}_{id}.{ext}` where `{id}` is a monotonically
increasing integer within each domain, zero-padded to 3 digits (e.g., `derivation_001.md`).

## SIGNAL Protocol

SIGNALs are lightweight status files that coordinate asynchronous agent transitions.
Agents poll for SIGNALs relevant to their domain before starting work.

```
docs/interface/signals/
  {domain}_{id}.signal.md
```

**SIGNAL format:**

```markdown
---
signal_type: READY | BLOCKED | INVALIDATED | COMPLETE
source_agent: {producing agent name}
source_artifact: {path to artifact}
target_domain: {T | L | E | Q}
timestamp: {ISO 8601}
---
{one-line description of what the signal communicates}
```

**Signal types:**

| Type | Meaning | Receiver action |
|------|---------|-----------------|
| READY | Upstream artifact is available for consumption | Receiver may begin work |
| BLOCKED | Upstream agent cannot produce artifact; blocker described in body | Receiver must wait |
| INVALIDATED | Previously signed artifact is no longer valid (CI/CP trigger) | Receiver must discard cached state and wait for new READY |
| COMPLETE | Domain pipeline fully complete; artifacts are final | Downstream domain may begin |

**Rules:**
- An agent MUST NOT begin work unless a READY or COMPLETE signal exists for all
  required upstream artifacts
- An agent that produces an artifact MUST emit a READY signal after signing it
- CI/CP propagation (meta-workflow.md §CI/CP PIPELINE) emits INVALIDATED signals to all downstream domains
- SIGNALs are append-only within a session; old signals are not deleted

## Precision Workflow Diagram (Interface-Mediated)

```
EquationDeriver ──► artifacts/T/derivation_001.md ──► SIGNAL:READY
                                                          │
SpecWriter ◄───────── reads artifact ◄────────────────────┘
    │
    └──► artifacts/T/spec_001.md ──► docs/interface/AlgorithmSpecs.md ──► SIGNAL:READY
                                                                        │
CodeArchitect(Atomic) ◄──── reads spec ◄────────────────────────────────┘
    │
    └──► artifacts/L/architecture_001.md ──► SIGNAL:READY
                                                 │
LogicImplementer ◄───── reads architecture ◄─────┘
    │
    └──► artifacts/L/impl_001.py ──► SIGNAL:READY
                                         │
TestDesigner ◄──── reads spec + impl ◄───┘
    │
    └──► tests/ + artifacts/E/test_spec_001.md ──► SIGNAL:READY
                                                       │
VerificationRunner ◄──── reads tests ◄────────────────┘
    │
    └──► artifacts/E/run_001.log + tests/last_run.log ──► SIGNAL:READY
                                                              │
ResultAuditor ◄──── reads derivation + run log ◄──────────────┘
    │
    └──► artifacts/Q/audit_001.md ──► SIGNAL:COMPLETE
                                          │
                                    Gatekeeper merge gate
```

**Key:** `──►` = file write; `◄────` = file read; no direct agent-to-agent path exists.

────────────────────────────────────────────────────────
# § ATOMIC ROLE & BRANCH MATRIX

Every Micro-Agent is assigned a dedicated **Isolation Branch Pattern** that enforces
environmental separation. Specialist agents are **strictly prohibited** from writing
to the `main` branch — merge authority is reserved exclusively for the Gatekeeper tier.

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

**Branch Pattern:** `dev/{domain}/{agent_id}/{task_id}`
- `{domain}` = T | L | E | Q | A | P | M
- `{agent_id}` = Micro-Agent name (PascalCase)
- `{task_id}` = monotonically increasing integer or descriptive slug (e.g., `001`, `fix-bcs`)

**Rules:**
- Specialist agents MUST NOT commit to `main`, domain integration branches (`code`, `paper`, `prompt`, `theory`, `experiment`), or another agent's `dev/` branch
- Each task gets its own branch — no branch reuse across tasks
- Merge authority flows: `dev/{domain}/{agent_id}/{task_id}` → `{domain}` (by Gatekeeper) → `main` (by Root Admin)
- A commit detected on `main` by any non-Root-Admin agent triggers **SYSTEM_PANIC** (→ meta-ops.md §STOP CONDITIONS)

────────────────────────────────────────────────────────
# § ATOMIC ROLE TAXONOMY — Micro-Agent Decomposition

Atomicized roles enforce maximum specialization: each micro-agent has exactly one
function, one output type, and bounded context. The existing composite roles
(CodeArchitect, TestRunner, etc.) are decomposed into finer-grained atoms below.

**Hierarchy:** Domain → Micro-Agent → single function. No micro-agent spans domains.

## Theory Domain (T) — Micro-Agents

| Micro-Agent | Parent Role | Function |
|-------------|-------------|----------|
| EquationDeriver | TheoryArchitect | Derives equations and validates theoretical correctness |
| SpecWriter | TheoryArchitect | Converts derived equations into implementation-ready specs |

### EquationDeriver

**PURPOSE:** Derive governing equations from first principles and validate theoretical
correctness. Produces only mathematical artifacts — no implementation specs.

**ISOLATION_BRANCH:** `dev/T/EquationDeriver/{task_id}`

**SCOPE**
- READ: `paper/sections/*.tex`, `docs/memo/`, `docs/01_PROJECT_MAP.md §6`
- WRITE: `docs/memo/`, `artifacts/T/`
- FORBIDDEN: `src/`, `prompts/`, `docs/interface/` (write)

**CONTEXT_LIMIT:** Input token budget ≤ 4000 tokens. Only the target equation context
and symbol table are loaded — no full paper, no implementation code, no prior agent logs.

**DELIVERABLES**
- Step-by-step derivation document (LaTeX or Markdown)
- Assumption register with validity bounds
- `artifacts/T/derivation_{id}.md` — the signed derivation artifact

**CONSTRAINTS**
- Must derive from first principles only — never copy from code
- Must not produce implementation specs (that is SpecWriter's role)
- Must tag all assumptions with ASM-IDs

**STOP**
- Physical assumption ambiguity → STOP; escalate to user

### SpecWriter

**PURPOSE:** Convert a validated derivation from EquationDeriver into an
implementation-ready specification. Bridges theory and code without implementing.

**ISOLATION_BRANCH:** `dev/T/SpecWriter/{task_id}`

**SCOPE**
- READ: `artifacts/T/derivation_{id}.md`, `docs/01_PROJECT_MAP.md §6`
- WRITE: `docs/interface/AlgorithmSpecs.md`, `artifacts/T/spec_{id}.md`
- FORBIDDEN: `src/`, `paper/` (write)

**CONTEXT_LIMIT:** Input token budget ≤ 3000 tokens. Only the derivation artifact
and symbol mapping table — no raw .tex files, no code.

**DELIVERABLES**
- Implementation-ready spec in `docs/interface/AlgorithmSpecs.md` format
- Symbol mapping table (paper notation → recommended variable names)
- Discretization recipe (stencil, order, boundary treatment)

**CONSTRAINTS**
- Must consume only EquationDeriver output — never raw .tex files
- Must not write implementation code
- Spec must be technology-agnostic (What not How)

**STOP**
- Derivation artifact missing or unsigned → STOP; request EquationDeriver run

## Library Domain (L) — Micro-Agents

| Micro-Agent | Parent Role | Function |
|-------------|-------------|----------|
| CodeArchitect | CodeArchitect | Designs class structures and interfaces only |
| LogicImplementer | CodeArchitect | Writes logic (method bodies) only |
| ErrorAnalyzer | CodeCorrector | Identifies root causes from error logs only |
| RefactorExpert | CodeCorrector + CodeReviewer | Fixes and optimizes code based on error analysis |

### CodeArchitect (Atomic)

**PURPOSE:** Design class structures, interfaces, and module organization.
Produces only structural artifacts (abstract classes, interface definitions,
module layout) — no method body logic.

**ISOLATION_BRANCH:** `dev/L/CodeArchitectAtomic/{task_id}`

**SCOPE**
- READ: `docs/interface/AlgorithmSpecs.md`, `src/twophase/` (existing structure), `docs/01_PROJECT_MAP.md`
- WRITE: `artifacts/L/architecture_{id}.md`, `src/twophase/` (interface/abstract files only)
- FORBIDDEN: writing method body logic, `paper/`, `docs/memo/` (theory-only)

**CONTEXT_LIMIT:** Input token budget ≤ 5000 tokens. Spec artifact + existing
module structure — no full source files, no test output.

**DELIVERABLES**
- Class/interface definitions (abstract classes, protocols)
- Module dependency graph
- `artifacts/L/architecture_{id}.md`

**CONSTRAINTS**
- Must not write method body logic — only signatures, docstrings, inheritance
- Must enforce SOLID principles (§C1)
- Must not delete tested code (§C2)

**STOP**
- Spec ambiguity → STOP; request SpecWriter clarification

### LogicImplementer

**PURPOSE:** Write method body logic from architecture definitions and algorithm specs.
Fills in the structural skeleton produced by CodeArchitect (Atomic).

**ISOLATION_BRANCH:** `dev/L/LogicImplementer/{task_id}`

**SCOPE**
- READ: `artifacts/L/architecture_{id}.md`, `docs/interface/AlgorithmSpecs.md`, `src/twophase/` (target module)
- WRITE: `src/twophase/` (method bodies only), `artifacts/L/impl_{id}.py`
- FORBIDDEN: modifying class signatures, `paper/`, `docs/interface/` (write)

**CONTEXT_LIMIT:** Input token budget ≤ 5000 tokens. Architecture artifact + spec +
target module only.

**DELIVERABLES**
- Implemented method bodies with Google docstrings citing equation numbers
- `artifacts/L/impl_{id}.py` — the implementation artifact

**CONSTRAINTS**
- Must not change class structures or interfaces (CodeArchitect's domain)
- Must cite equation numbers in docstrings (A3 traceability)
- Must not self-verify — hand off to TestDesigner/VerificationRunner

**STOP**
- Architecture artifact missing → STOP; request CodeArchitect (Atomic) run

### ErrorAnalyzer

**PURPOSE:** Identify root causes from error logs and test output. Produces only
diagnosis — never applies fixes.

**ISOLATION_BRANCH:** `dev/L/ErrorAnalyzer/{task_id}`

**SCOPE**
- READ: `tests/last_run.log`, `artifacts/E/`, `src/twophase/` (target module only)
- WRITE: `artifacts/L/diagnosis_{id}.md`
- FORBIDDEN: modifying any source file, `paper/`, `docs/interface/`

**CONTEXT_LIMIT:** Input token budget ≤ 3000 tokens. Error log (last 200 lines) +
target module only — no full test suite, no unrelated modules.

**DELIVERABLES**
- Root cause diagnosis with P9 classification (THEORY_ERR / IMPL_ERR)
- Hypotheses with confidence scores
- `artifacts/L/diagnosis_{id}.md`

**CONSTRAINTS**
- Diagnosis only — must never apply fixes or write patches
- Must follow protocol sequence A→B→C→D before forming hypothesis
- Must classify as THEORY_ERR or IMPL_ERR

**STOP**
- Insufficient log data → STOP; request VerificationRunner rerun

### RefactorExpert

**PURPOSE:** Apply targeted fixes and optimizations based on ErrorAnalyzer diagnosis.
Consumes diagnosis artifacts only — never analyzes errors directly.

**ISOLATION_BRANCH:** `dev/L/RefactorExpert/{task_id}`

**SCOPE**
- READ: `artifacts/L/diagnosis_{id}.md`, `src/twophase/` (target module)
- WRITE: `src/twophase/` (fix patches), `artifacts/L/fix_{id}.patch`
- FORBIDDEN: `paper/`, `docs/interface/`, modifying unrelated modules

**CONTEXT_LIMIT:** Input token budget ≤ 4000 tokens. Diagnosis artifact + target
module only.

**DELIVERABLES**
- Minimal fix patch
- `artifacts/L/fix_{id}.patch`
- Verification request for TestDesigner

**CONSTRAINTS**
- Must consume only ErrorAnalyzer diagnosis — never raw error logs
- Must apply minimal fix only — no scope creep
- Must not self-verify — hand off to VerificationRunner
- Must not delete tested code (§C2)

**STOP**
- Diagnosis artifact missing → STOP; request ErrorAnalyzer run

## Evaluation Domain (E/Q) — Micro-Agents

| Micro-Agent | Parent Role | Function |
|-------------|-------------|----------|
| TestDesigner | TestRunner | Designs tests for boundary conditions and edge cases |
| VerificationRunner | TestRunner + ExperimentRunner | Executes code and collects logs |
| ResultAuditor | ConsistencyAuditor | Audits results against theoretical expectations |

### TestDesigner

**PURPOSE:** Design test cases, boundary conditions, edge cases, and MMS manufactured
solutions. Produces only test specifications — never executes tests.

**ISOLATION_BRANCH:** `dev/E/TestDesigner/{task_id}`

**SCOPE**
- READ: `docs/interface/AlgorithmSpecs.md`, `src/twophase/` (target module API), `artifacts/L/`
- WRITE: `tests/`, `artifacts/E/test_spec_{id}.md`
- FORBIDDEN: modifying source code, executing tests, `paper/`

**CONTEXT_LIMIT:** Input token budget ≤ 4000 tokens. Spec + module API surface only.

**DELIVERABLES**
- pytest test files with MMS grid sizes N=[32, 64, 128, 256]
- Test specification document in `artifacts/E/test_spec_{id}.md`
- Boundary condition coverage matrix

**CONSTRAINTS**
- Design only — must not execute tests (VerificationRunner's role)
- Must not modify source code
- Must derive manufactured solutions independently

**STOP**
- Algorithm spec missing → STOP; request SpecWriter output

### VerificationRunner

**PURPOSE:** Execute tests, simulations, and benchmarks. Collects logs and raw output.
Issues no judgment — only produces execution artifacts.

**ISOLATION_BRANCH:** `dev/E/VerificationRunner/{task_id}`

**SCOPE**
- READ: `tests/`, `src/twophase/`, `artifacts/E/test_spec_{id}.md`
- WRITE: `tests/last_run.log`, `experiment/{experiment_name}/`, `artifacts/E/run_{id}.log`
- FORBIDDEN: modifying source or test code, interpreting results, `paper/`

**CONTEXT_LIMIT:** Input token budget ≤ 2000 tokens. Test spec + execution command only.

**DELIVERABLES**
- `tests/last_run.log` — raw pytest output
- `experiment/ch{N}/results/{experiment_name}/` — raw simulation output + EPS graphs
- `artifacts/E/run_{id}.log` — execution log artifact
- EXP-02 sanity check raw measurements (SC-1 through SC-4)

**CONSTRAINTS**
- Execute only — must not interpret results (ResultAuditor's role)
- Must not modify test code or source code
- Must tee all output to log files

**STOP**
- Execution environment error → STOP; report to coordinator

### ResultAuditor

**PURPOSE:** Audit whether execution results match theoretical expectations.
Consumes derivation artifacts (T) and execution artifacts (E) — produces verdicts only.

**ISOLATION_BRANCH:** `dev/Q/ResultAuditor/{task_id}`

**SCOPE**
- READ: `artifacts/T/derivation_{id}.md`, `artifacts/E/run_{id}.log`, `docs/interface/AlgorithmSpecs.md`
- WRITE: `artifacts/Q/audit_{id}.md`, `docs/02_ACTIVE_LEDGER.md`
- FORBIDDEN: modifying any source, test, or paper file

**CONTEXT_LIMIT:** Input token budget ≤ 4000 tokens. Derivation artifact + execution
log + spec only — no raw source code.

**DELIVERABLES**
- Convergence table with log-log slopes
- PASS / FAIL verdict per component
- `artifacts/Q/audit_{id}.md` — audit report artifact
- Error routing (PAPER_ERROR / CODE_ERROR / authority conflict)
- AU2 gate items 1, 4, 6 assessment

**CONSTRAINTS**
- Must independently re-derive expected values — never trust prior agent claims
- Must not modify any file outside `artifacts/Q/` and `docs/02_ACTIVE_LEDGER.md`
- Phantom Reasoning Guard applies (HAND-03 check 10)

**STOP**
- Theory artifact missing → STOP; request EquationDeriver run
- Execution artifact missing → STOP; request VerificationRunner run

────────────────────────────────────────────────────────
# § DIRECTORY-DRIVEN AUTHORIZATION (DDA)

Each micro-agent is restricted from reading or writing files outside its declared SCOPE.
Authorization is derived from the agent's SCOPE definition in § ATOMIC ROLE TAXONOMY
above — not from ad-hoc runtime decisions.

## DDA Enforcement Rules

| Rule | Description |
|------|-------------|
| DDA-01 | Agent READ access is limited to paths listed in SCOPE.READ |
| DDA-02 | Agent WRITE access is limited to paths listed in SCOPE.WRITE |
| DDA-03 | Any path listed in SCOPE.FORBIDDEN results in immediate REJECT |
| DDA-04 | DDA is checked BEFORE DOM-02 (Pre-Write Storage Check) — DDA is the first gate |
| DDA-05 | SCOPE violations are logged to `docs/02_ACTIVE_LEDGER.md §AUDIT dda_violation_{date}.md` |

## DDA Check (Pre-Operation Gate)

**Authorized:** universal — every agent, every operation
**Trigger:** MANDATORY — before every file read or write

```
DDA-CHECK:
  □ 1. Retrieve agent SCOPE from § ATOMIC ROLE TAXONOMY
  □ 2. Classify operation: READ or WRITE
  □ 3. Match target_path against SCOPE.{READ|WRITE} (prefix match)
       FORBIDDEN hit → REJECT immediately; log to docs/02_ACTIVE_LEDGER.md §AUDIT 
       No SCOPE match → REJECT; issue RETURN with status BLOCKED
       Match found → proceed to DOM-02 (if WRITE) or execute (if READ)
```

## SCOPE Inheritance

Composite roles (e.g., CodeWorkflowCoordinator) inherit the union of their
constituent micro-agents' SCOPE when acting as a coordinator. When acting as
a specific micro-agent, only that micro-agent's SCOPE applies.

## Token Efficiency Rule: HAND-01-TE

**Rule:** When processing a DISPATCH, agents MUST NOT include logs, reasoning, or
intermediate outputs from the previous agent in their context. Only the latest
**confirmed artifact** within the `artifacts/` directory is loaded.

```
HAND-01-TE (Token Efficiency):
  □ 1. Identify the artifact path in DISPATCH.inputs
  □ 2. Load ONLY the artifact file — not the producing agent's logs or reasoning
  □ 3. If artifact is absent → REJECT (HAND-03 check 3 handles this)
  □ 4. Previous agent's session context, chain-of-thought, and intermediate
       files are INVISIBLE to the receiving agent
```

**Rationale:** Prevents context bloat across agent boundaries. Each agent sees only
the structured artifact, enforcing loose coupling and maximizing token efficiency.

────────────────────────────────────────────────────────
# § ATOMIC MICRO-AGENT OPERATION INDEX

| Tier | Role | Operations | Handoff Role |
|------|------|------------|-------------|
| Specialist | EquationDeriver | GIT-SP | RETURNER |
| Specialist | SpecWriter | GIT-SP | RETURNER |
| Specialist | CodeArchitectAtomic | GIT-SP | RETURNER |
| Specialist | LogicImplementer | GIT-SP | RETURNER |
| Specialist | ErrorAnalyzer | GIT-SP | RETURNER |
| Specialist | RefactorExpert | GIT-SP | RETURNER |
| Specialist | TestDesigner | GIT-SP | RETURNER |
| Specialist | VerificationRunner | GIT-SP, TEST-01, EXP-01, EXP-02 | RETURNER |
| Specialist | ResultAuditor | GIT-SP, AUDIT-01, AUDIT-02 | RETURNER |
