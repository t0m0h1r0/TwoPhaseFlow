---
id: WIKI-M-006
title: "Agent Meta System: Micro-Agent Architecture + Directory-Driven Authorization (DDA) + SIGNAL Protocol"
status: ACTIVE
created: 2026-04-12
updated: 2026-04-12
depends_on: [WIKI-M-004]
---

# Agent Meta System: Micro-Agent Architecture + DDA

## Motivation

Composite agents like `CodeArchitect` tried to do too much in one context window:
design the module interface, implement the code, run tests, analyze failures, refactor.
Each sub-task needed different rules and different anti-pattern inject lists, but
a composite agent loaded all of them, diluting attention across the full task space.

The micro-agent architecture (`f25a9a0`, 2026-03-31 → `1326fa5`, 2026-04-04) decomposes
composite specialists into **9 atomic roles**, each with a narrow SCOPE, tight
CONTEXT_LIMIT, and file-based coordination via the SIGNAL protocol. Authorization is
enforced at the directory level (DDA), not the agent's self-check.

---

## The 9 Atomic Micro-Agents

| Micro-Agent | Domain | Context Limit | Purpose |
|------------|--------|---------------|---------|
| EquationDeriver | T | 4k | Derive governing equations / stencils from first principles |
| SpecWriter | T | 3k | Produce `AlgorithmSpecs.md` from derivation artifacts |
| CodeArchitectAtomic | L | 5k | Module-level architecture decisions (interface + dependency map) |
| LogicImplementer | L | 5k | Implement one module from a signed architecture spec |
| ErrorAnalyzer | L | 4k | Diagnose a failed test → classify THEORY_ERR / IMPL_ERR |
| RefactorExpert | L | 5k | Surgical refactoring patches from an error diagnosis |
| TestDesigner | E | 3k | Author test specifications (not runs) |
| VerificationRunner | E | 4k | Execute tests; produce run logs with hash-pinned results |
| ResultAuditor | Q | 4k | Audit result packages against expected behaviors |

**Key property:** each micro-agent has a SCOPE (READ / WRITE / FORBIDDEN paths) so
narrow that its full rule set + context budget fits in 3–5k tokens. Composite
specialists routinely exceeded 15k.

---

## Directory-Driven Authorization (DDA)

**Problem solved:** in the composite-agent world, a `CodeArchitect` could write to
`src/twophase/ccd/laplacian.py` and `src/twophase/infra/backend.py` and `tests/`
during a single session. A7 (Core/System Sovereignty) forbade Infrastructure→Core
imports but did not forbid cross-territory writes in one session. The audit trail
showed "CodeArchitect wrote both"; forensic analysis could not determine which
write was legitimate scope and which was scope creep.

**Solution:** Directory-Driven Authorization (DDA) — authorization is enforced per
**directory**, not per agent role. The tool wrapper intercepts writes and checks:

```
DDA-01: Agent may write to a path P only if P ∈ agent.SCOPE.WRITE
DDA-02: Agent may read a path P only if P ∈ agent.SCOPE.READ
DDA-03: Agent may NEVER touch a path P if P ∈ agent.SCOPE.FORBIDDEN
DDA-04: One micro-agent = one directory = one operation (atomic)
DDA-05: SCOPE is part of the agent prompt, not runtime-mutable
```

**Enforcement:** at the tool-wrapper level, not the agent self-check level. A
micro-agent that tries to write outside its SCOPE hits a `CONTAMINATION_GUARD`
error before the write executes. No "oops, I'll remember next time" — the write
simply cannot happen.

**Why tool-level, not self-check:** self-checks rely on the agent honestly reporting
whether the write is in scope. AP-03 (Verification Theater) and AP-08 (Phantom
State Tracking) both show agents will not reliably self-report. Moving enforcement
to the tool wrapper is the structural version of the self-check — it cannot be
faked and does not depend on attention mechanics.

---

## SIGNAL Protocol (Async Coordination)

**Problem:** micro-agents operate in separate context windows. A LogicImplementer
needs to wait for CodeArchitectAtomic to finish a spec; an ErrorAnalyzer needs to
know when a test run completed. Direct agent-to-agent conversation is forbidden
(Phantom Reasoning Guard — [[WIKI-M-005]]). So how do they synchronize?

**Solution:** file-based SIGNAL protocol. Each micro-agent emits exactly one of four
state tokens to `docs/interface/signals/{task_id}.signal.json`:

| SIGNAL | Meaning | Next action |
|--------|---------|-------------|
| READY | Artifact produced + CoVe PASS | Downstream micro-agent may begin |
| BLOCKED | Precondition not met (e.g., missing upstream artifact) | Wait; retry after upstream READY |
| INVALIDATED | Upstream artifact changed; my output is stale | Re-run from DRAFT |
| COMPLETE | Full task chain finished; coordinator may merge | Coordinator runs HAND-03 |

**Key property:** SIGNALs are files, not messages. They accumulate in `docs/interface/signals/`
as an append-only audit trail. A future session can reconstruct "why did
LogicImplementer start when it did" by reading the signal log.

**Composes with:** HAND-01 dispatch (coordinator issues HAND-01 → micro-agent runs →
micro-agent emits READY signal → coordinator reads signal → coordinator issues next
HAND-01 to downstream micro-agent).

---

## Artifact-Mediated Handoff (IF-01 through IF-04)

The micro-agent architecture enforces Interface-First Loose Coupling via four principles:

| # | Principle | Effect |
|---|-----------|--------|
| IF-01 | No direct conversation | All data flows through files in `docs/interface/` or `artifacts/` |
| IF-02 | Artifact-mediated handoff | HAND-01/HAND-02 tokens reference artifact paths, not inline content |
| IF-03 | SIGNAL-based coordination | State transitions are communicated via SIGNAL files, not dialogue |
| IF-04 | Immutable artifacts | Once signed, an artifact is read-only until a new version is produced |

**Artifact naming convention:** `{type}_{id}.{ext}` with zero-padded 3-digit IDs:
- `artifacts/T/derivation_001.md`
- `artifacts/L/impl_042.py`
- `artifacts/E/run_012.log`
- `artifacts/Q/audit_007.md`

---

## Activation Status

**P3 Activation** (2026-04-04, `1326fa5`) — the 9 micro-agents went operational
after the following prerequisites:

1. `artifacts/{T,L,E,Q}/` directories existed
2. `docs/interface/signals/` directory created
3. DDA enforcement embedded per-agent procedure (DDA-01/02/03)
4. HAND-01-TE stateless handoff via `artifact_hash` + `context_limit`
5. SIGNAL protocol per agent (READY/BLOCKED/INVALIDATED/COMPLETE)

**Current operational status** (v5.2, 2026-04-12): the micro-agent infrastructure
is marked `OPERATIONAL — load on demand` in `meta-experimental.md`. Standard
composite specialists still handle most tasks; micro-agents activate for atomic
decomposition when a coordinator determines the task benefits from it.

**Load-on-demand policy:** agents do NOT preload `meta-experimental.md` at session
start. A coordinator loads it only when dispatching a micro-agent, minimizing the
token cost for composite-only sessions.

---

## When to Use Micro-Agents vs. Composite Agents

| Signal | Prefer micro-agents | Prefer composite agent |
|--------|--------------------|-----------------------|
| Task has ≥3 distinct phases | ✓ | |
| Each phase has different anti-pattern risks | ✓ | |
| Context budget is tight | ✓ | |
| Task is self-contained (one file, one function) | | ✓ |
| Coordination overhead would exceed task complexity | | ✓ |

The micro-agent architecture is **additive**, not replacing composite specialists.
`CodeArchitect` and `CodeArchitectAtomic` coexist — the former for large design
tasks, the latter for atomic decomposition.

---

## Interaction with Other Layers

| Layer | Interaction |
|-------|-------------|
| [[WIKI-M-004]] 3-Layer Architecture | Micro-agents are a Layer 2 (meta-experimental.md) overlay on the composite-agent base |
| [[WIKI-M-004]] A9 Sovereignty | DDA enforces A9 at the tool-wrapper level |
| [[WIKI-M-005]] Phantom Reasoning Guard | SIGNAL protocol makes Phantom Reasoning operationally impossible (no direct dialogue) |
| [[WIKI-M-002]] Schema-in-Code | HAND-01-TE envelope uses the same Schema-in-Code TypeScript interfaces |
| [[WIKI-M-001]] Worktree Concurrency | Each micro-agent may run in its own worktree with its own branch lock |

---

## Source

- `prompts/meta/meta-experimental.md §ATOMIC ROLE TAXONOMY` (9 micro-agent definitions)
- `prompts/meta/meta-experimental.md §INTERFACE-FIRST LOOSE COUPLING` (IF-01..IF-04)
- `prompts/meta/meta-experimental.md §DIRECTORY-DRIVEN AUTHORIZATION` (DDA-01..DDA-05)
- `prompts/meta/meta-experimental.md §SIGNAL PROTOCOL` (READY/BLOCKED/INVALIDATED/COMPLETE)
- `prompts/meta/meta-persona.md §ATOMIC MICRO-AGENT PROFILES`
- Commits:
  - `b447eba` (2026-03-31) DDA + roles + workflow
  - `f25a9a0` (2026-03-31) EnvMetaBootstrapper deploy — 9 atomic micro-agents + DDA scope
  - `1326fa5` (2026-04-04) P3 activation — 9 atomic micro-agents operational

## Related entries

- [[WIKI-M-004]] Constitutional Foundations — A9 Sovereignty is the axiomatic basis for DDA
- [[WIKI-M-005]] Dynamic Governance Patterns — Phantom Reasoning Guard is why SIGNAL exists
- [[WIKI-M-002]] v4.1 3-Pillar Protocol — Schema-in-Code is used by HAND-01-TE
