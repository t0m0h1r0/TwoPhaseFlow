# WIKI-M-014: meta-deploy Protocol + EnvMetaBootstrapper Lifecycle
**Category:** Meta | **Created:** 2026-04-18 | **Source:** `prompts/meta/meta-deploy.md`

## Purpose

EnvMetaBootstrapper (EMB) is the "compiler" of the agent system. It reads the abstract
meta-layer (10 `prompts/meta/*.md` files) and deterministically generates concrete,
environment-specific agent prompt files (`prompts/agents-{env}/`). It also validates
the meta-system itself during generation.

EMB version: 3.2.0 (as of 2026-04-11, companion to meta-system v5.1.0-Concurrency-Aware).

---

## Deployment Stage Sequence

Stages execute sequentially. No skipping.

### Stage 1: Parse

Read all 10 meta files and extract:
- φ1–φ7 core philosophy + A1–A11 axioms + system targets (`meta-core.md`)
- Domain registry: branches, storage territory, agent membership, lifecycle (`meta-domains.md`)
- Per-agent character + skills (`meta-persona.md`)
- Per-agent role definitions: PURPOSE / DELIVERABLES / AUTHORITY / CONSTRAINTS / STOP (`meta-roles.md`)
- P-E-V-A pipeline, domain pipelines, handoff rules, control protocols (`meta-workflow.md`)
- Canonical operation specs: GIT-01..05, DOM-01..02, HAND-01/02/03, AUDIT-01/02 (`meta-ops.md`)
- Known failure patterns + inject lists (`meta-antipatterns.md`)

### Stage 1b: XML-Aware Parse (v1.1 Hybrid)

Seven structural checks on all meta files except `meta-deploy.md` itself:
1. **Closed-vocabulary allow-list**: only approved child tags inside `<meta_section>` blocks
2. **Tag balance check**: every `<meta_section>` open must have a matching close
3. **`id` attribute discovery**: unique across all in-scope files; mismatch → STOP-02
4. **`immutable="true"` body-diff gate**: extract body lines of every immutable section and diff against the last bootstrapper-verified generation — non-empty diff → STOP-02 (axiom drift)
5. **Eager `$ref` resolution**: validate that every `<parameters format="json">` `$ref` resolves to a concrete section in `meta-roles.md §SCHEMA-IN-CODE`
6. **RFC-2119 rules check**: every `<rules>` bullet must begin with MUST/SHALL/SHOULD/etc. — violations are STOP-SOFT (warning only)
7. **Legacy anchor preservation**: every wrapped section must retain its legacy markdown heading inside the block (for grep invariant checks)

Generates `schema_resolution_report.json`. Absence of this file after a run → STOP-SOFT.

### Stage 2: Initialize Directory Structure

Creates the 3-layer directory tree:
- `docs/` (SSoT docs layer)
- `prompts/agents-claude/`, `prompts/agents-codex/` (per-environment output)
- `artifacts/{T,L,E,Q,M}/` (domain artifact storage)

**FORBIDDEN directories (φ6 Single Source):**
- `prompts/meta/schemas/` — HandoffEnvelope schema is in `meta-roles.md §SCHEMA-IN-CODE`; no external JSON schema files
- Directories with leading-number prefixes (`01_foo/`) or dot-prefixed files — CLEAN names only

### Stage 3: Generate Agent Prompts

Composition formula per agent:
```
Prompt = Base[archetype] + Domain[domain] + TaskOverlay[agent] + RULE_MANIFEST
```

Five base archetypes (Specialist, Gatekeeper, Coordinator, Auditor, Router) are composed
with the appropriate domain module and agent-specific task overlay. This eliminates
boilerplate duplication across the ~25-agent roster.

**Tiered generation** — each agent is generated at one of three tiers:

| Tier | Target | Pipeline mode | Contents |
|------|--------|--------------|----------|
| TIER-1 (MINIMAL) | ~500 tokens | TRIVIAL | PURPOSE + 3 critical constraints + STOP |
| TIER-2 (STANDARD) | ~1500 tokens | FAST-TRACK | Full Q1 template + domain rules + task overlay |
| TIER-3 (FULL) | ~3000 tokens | FULL-PIPELINE | Full template + Behavioral Action Table + recovery guidance |

**AP injection (Stage 3)** — anti-patterns from `meta-antipatterns.md` are injected
based on tier and agent role:
- TIER-1: CRITICAL only (AP-03 Verification Theater, AP-05 Convergence Fabrication)
- TIER-2: CRITICAL + HIGH (adds AP-01, AP-04, AP-06, AP-09, AP-11 as applicable)
- TIER-3: all applicable APs for the role

Injection format: a self-check table with a one-line question per AP. Total injection must
not exceed 200 tokens (LA-4 Rule Load Budgeting).

For TIER-2 and TIER-3 E-Domain agents and DiagnosticArchitect: inject the `@RESOURCES` RAP-01
block verbatim (MAX_EXP_RETRIES counter, STOP_AND_REPORT trigger on zero-convergence).

**File header on every generated file:**
```
# GENERATED — do NOT edit directly. Edit prompts/meta/*.md and regenerate.
```

### Stage 4: Optimize

Adapt each generated prompt to the target environment profile:
- **Claude**: explicit constraints, structure, traceability, full THOUGHT_PROTOCOL
- **Codex**: executable clarity, diff-first output, minimal line changes

Compression is permitted under Q4 rules. **Compression-exempt** (never compress):
- STOP conditions (preserved verbatim)
- A3/A4/A5 axiom references (compressed in token count, never in meaning)

### Stage 5: Validate — Q3 Checklist

Run the 10-item Q3 audit checklist against every generated prompt:

| # | Check | Pass criterion |
|---|-------|---------------|
| 1 | Core axioms A1–A11 present | All 11 referenced; none weakened |
| 2 | Solver / infra separation | No solver logic mixed with I/O, logging, config |
| 3 | Layer isolation | No cross-layer edits without authorization |
| 4 | External memory discipline | All state refs docs/ files by ID; no old filenames |
| 5 | Stop conditions unambiguous | Every STOP has an explicit trigger |
| 6 | Standard template format | PURPOSE / INPUTS / RULES / PROCEDURE / OUTPUT / STOP |
| 7 | Environment optimization | Appropriate for target environment |
| 8 | Backward compatibility | No semantic removal without deprecation note |
| 9 | Core/System sovereignty (A9) | CodeArchitect includes import auditing mandate; ConsistencyAuditor includes CRITICAL_VIOLATION + THEORY_ERR/IMPL_ERR taxonomy |
| 10 | Schema-in-Code compliance | No agent references `schemas/hand_schema.json`; HAND schemas cited as `meta-roles.md §SCHEMA-IN-CODE` |

FAIL on any item → halt; do not proceed to Stage 6.

**Stage 5b: SDP-01 Delegation Mode** — after Q3, route by system state:
- `COLD_START`: full structural + semantic validation (EMB owns)
- `WARM_STATE`: structural integrity only; delegate semantic checks to ConsistencyAuditor via AUDIT-TASK token

### Stage 6: Generate README.md

Generate `prompts/README.md` documenting the 3-layer architecture for human operators.
Contains 9 fixed sections: architecture diagram, directory map, rule ownership table,
A1–A11 quick reference, P-E-V-A loop, 3-phase lifecycle, agent roster table, Mermaid
interaction diagram, and STOP conditions index.

---

## Key Generation Invariants

| Invariant | Check | Failure action |
|-----------|-------|----------------|
| φ count | `grep -c '^## φ' meta-core.md == 7` | STOP-02 (axiom drift) |
| A count | `grep -c '^## A[0-9]' meta-core.md == 11` | STOP-02 |
| HAND-01 fields | 4 manual + env-injected | Reject non-conformant token |
| Mechanical diff | Full-regen diff across all agents shows same N lines added/removed per file | Non-mechanical drift = bootstrapper bug → abort |
| No schemas/ dir | `schemas/hand_schema.json` must not exist | Delete + warn if found |

---

## CHK Trace (Major Deployments)

| CHK | Date | Event |
|-----|------|-------|
| CHK-094 | 2026-04-08 | First 33-agent full deployment; Q3 9/9 PASS (commit `efd93dd`) |
| CHK-114 | 2026-04-11 | v5.1 concurrency propagation; 32/32 LOCK-ACQUIRE, 17/17 GIT-ATOMIC-PUSH confirmed; `concurrency_profile` field added to all agents |
| CHK-123 | 2026-04-12 | v5.2 AP-09/10 redeploy; 33 agents aligned; Q3 9/9 PASS |
| 2026-04-14 | — | Dual-env split: 25 × 2 = 50 agent files generated (agents-claude/ + agents-codex/) |

---

## Cross-References

- `→ WIKI-M-011`: AP catalogue — the full inject list referenced at Stage 3
- `→ WIKI-M-012`: Agent roster — the 25-agent roster that Stage 3 iterates over
- `→ WIKI-M-013`: v1.1 XML Hybrid format — Stage 1b parser spec
- `→ WIKI-M-002`: v4.1 Schema-in-Code (the FORBIDDEN schemas/ rationale)
- `→ prompts/meta/meta-antipatterns.md §INJECTION RULES`: bootstrapper-facing AP injection spec
