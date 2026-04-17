# WIKI-M-022: System Reconstruction Runbook
**Category:** Meta | **Created:** 2026-04-18
**Sources:** All wiki entries WIKI-M-016 through WIKI-M-021, `prompts/meta/meta-deploy.md`

This runbook is the end-to-end guide to rebuild the meta-prompt system and redeploy all 25 agents
from the wiki + source files alone. If this document and WIKI-M-017 through WIKI-M-021 exist,
reconstruction is possible without the original prompts/ history.

---

## Prerequisites Checklist

Before starting, verify all these are present:

```
prompts/meta/
  ├── meta-core.md        — constitutional layer (φ1–φ7, A1–A11, LA-1..5, MH-1..3)
  ├── meta-persona.md     — 25 agent behavioral profiles + BEHAVIORAL_PRIMITIVES schema
  ├── meta-domains.md     — 4×4 domain registry + K-axioms + storage sovereignty
  ├── meta-roles.md       — per-agent role contracts + SCHEMA-IN-CODE + COVE MANDATE
  ├── meta-ops.md         — all canonical operations (GIT/DOM/LOCK/HAND/AUDIT/K)
  ├── meta-workflow.md    — P-E-V-A loop + pipeline modes + STOP-RECOVER MATRIX
  ├── meta-deploy.md      — EnvMetaBootstrapper 6-stage lifecycle
  ├── meta-antipatterns.md — AP-01..AP-11 anti-pattern catalogue
  ├── meta-experimental.md — L0–L3 isolation + micro-agent DDA
  └── meta-project.md     — project-specific context (swappable)

prompts/agents-claude/_base.yaml   — universal agent foundation

scripts/
  └── git-sp.sh           — branch creation helper (domain + agent_id + task_id)

docs/
  ├── locks/              — directory must exist (empty); LOCK-ACQUIRE creates files here
  ├── 02_ACTIVE_LEDGER.md — must have §4 BRANCH_LOCK_REGISTRY section
  └── interface/          — directory must exist (empty for fresh start)
```

---

## Step 1: Verify Constitutional Layer

Run these checks BEFORE any generation. Failure = STOP-02; do NOT proceed.

```sh
# φ count must be exactly 7
grep -c '^## φ' prompts/meta/meta-core.md
# Expected output: 7

# A count must be exactly 11
grep -c '^## A[0-9]' prompts/meta/meta-core.md
# Expected output: 11

# SCHEMA-IN-CODE section must be present
grep -c 'id="SCHEMA-IN-CODE"' prompts/meta/meta-roles.md
# Expected output: 1

# HAND-03 immutable section must be present
grep -c 'id="HAND-03".*immutable="true"' prompts/meta/meta-ops.md
# Expected output: 1

# _base.yaml version alignment
grep 'meta_version' prompts/agents-claude/_base.yaml
# Expected output: meta_version: "5.1.0"  (or current version)
```

If φ count ≠ 7 or A count ≠ 11: axiom drift detected. Do not proceed. Compare against WIKI-M-017 verbatim text and restore.

---

## Step 2: Verify Agent Foundation

```sh
# Check concurrency profile is set
grep 'concurrency_profile' prompts/agents-claude/_base.yaml
# Expected: concurrency_profile: "worktree"

# Check handoff mode
grep 'handoff_mode' prompts/agents-claude/_base.yaml
# Expected: handoff_mode: "text"

# Verify docs/locks/ directory exists
ls -d docs/locks/
# If missing: mkdir docs/locks/

# Verify BRANCH_LOCK_REGISTRY section in ACTIVE_LEDGER
grep '§4\|BRANCH_LOCK_REGISTRY' docs/02_ACTIVE_LEDGER.md | head -3
# If missing: add empty §4 section to the ledger
```

---

## Step 3: Run EnvMetaBootstrapper (6 Stages)

EnvMetaBootstrapper is the "compiler" — it generates all 50 agent files (25 × 2 environments) from the meta sources.

### Stage 1: Parse
Read all 10 meta files. Extract φ1–φ7, A1–A11, domain registry, per-agent contracts, operations, workflow rules, anti-patterns.

**Critical files parsed in Stage 1:**
- `meta-core.md` — constitutional layer
- `meta-domains.md` — domain registry + K-axioms
- `meta-persona.md` — BEHAVIORAL_PRIMITIVES + agent profiles
- `meta-roles.md` — role contracts + SCHEMA-IN-CODE
- `meta-ops.md` — all operations + STOP conditions
- `meta-workflow.md` — pipeline + STOP-RECOVER
- `meta-antipatterns.md` — AP-01..AP-11 inject lists
- `meta-experimental.md` — L0–L3 isolation model
- `meta-deploy.md` — (self-referential: bootstrapper reads its own spec)
- `meta-project.md` — project-specific context

### Stage 1b: XML-Aware Validation
7 structural checks on immutable sections:
1. Closed-vocabulary allow-list (only approved child tags inside `<meta_section>`)
2. Tag balance check (every `<meta_section>` has matching close)
3. `id` attribute uniqueness across all files (mismatch → STOP-02)
4. **Immutable body-diff gate**: compare body of every `immutable="true"` section against baseline — non-empty diff → STOP-02 (axiom drift)
5. Eager `$ref` resolution (every `<parameters format="json">` `$ref` resolves to SCHEMA-IN-CODE)
6. RFC-2119 rules check (MUST/SHALL/SHOULD — violations = STOP-SOFT)
7. Legacy anchor preservation (every wrapped section retains markdown heading)

**If Stage 1b fails:** do NOT proceed to Stage 2. Restore from WIKI-M-017 verbatim text.

### Stage 2: Initialize Directory Structure
Create these directories if not present:
```
docs/                           — SSoT docs layer
prompts/agents-claude/          — Claude environment output
prompts/agents-codex/           — Codex environment output
artifacts/{T,L,E,Q,M}/         — domain artifact storage
```

**FORBIDDEN (φ6 Single Source):**
- `prompts/meta/schemas/` — HandoffEnvelope schema is in meta-roles.md §SCHEMA-IN-CODE; NO external JSON files
- Directories with leading-number prefixes (`01_foo/`) or dot-prefixed files

### Stage 3: Generate Agent Prompts

Composition per agent:
```
Prompt = Base[archetype] + Domain[domain] + TaskOverlay[agent] + RULE_MANIFEST
```

**For each of the 25 agents:**
1. Look up archetype in meta-persona.md (Router / Coordinator / Specialist / Auditor / Gatekeeper)
2. Look up domain in meta-domains.md (M/T/L/E/A/P/Q/K)
3. Look up role contract in meta-roles.md (PURPOSE / DELIVERABLES / AUTHORITY / CONSTRAINTS / STOP)
4. Assign tier (TIER-1/2/3) based on agent complexity
5. Inject AP self-check blocks per tier (WIKI-M-014 injection matrix)
6. Add RULE_MANIFEST (always + domain + on_demand blocks)
7. Append file header: `# GENERATED — do NOT edit directly. Edit prompts/meta/*.md and regenerate.`

**AP injection (Stage 3):**
- TIER-1: AP-03 + AP-05 (CRITICAL only)
- TIER-2: CRITICAL + HIGH (AP-01, AP-04, AP-06, AP-09, AP-11 as applicable)
- TIER-3: all applicable APs for the role (max 200 tokens total for AP block)

For E-Domain agents and DiagnosticArchitect: inject `@RESOURCES RAP-01` block verbatim (MAX_EXP_RETRIES=2, STOP_AND_REPORT on zero-convergence).

### Stage 4: Environment Optimization
Adapt each prompt for target environment:
- **Claude**: explicit constraints, full THOUGHT_PROTOCOL (SLP-01 shorthand), AP self-check table, full procedure steps (~2500 tokens)
- **Codex**: terse diff-first instructions, no THOUGHT_PROTOCOL, compressed procedure (~1500 tokens)

**Compression rules:**
- NEVER compress STOP conditions (preserved verbatim)
- NEVER compress A3/A4/A5 axiom references (may be token-compressed but never meaning-compressed)

### Stage 5: Q3 Validation Checklist

All 10 items must PASS. Failure on any item → HALT; do not proceed to Stage 6.

| # | Check | Pass criterion |
|---|-------|---------------|
| 1 | Core axioms A1–A11 present | All 11 referenced; none weakened |
| 2 | Solver / infra separation | No solver logic mixed with I/O, logging, config |
| 3 | Layer isolation | No cross-layer edits without authorization |
| 4 | External memory discipline | All state refs docs/ files by ID; no old filenames |
| 5 | Stop conditions unambiguous | Every STOP has explicit trigger |
| 6 | Standard template format | PURPOSE / INPUTS / RULES / PROCEDURE / OUTPUT / STOP |
| 7 | Environment optimization | Appropriate for target environment |
| 8 | Backward compatibility | No semantic removal without deprecation note |
| 9 | Core/System sovereignty (A9) | CodeArchitect includes import auditing; ConsistencyAuditor includes CRITICAL_VIOLATION + THEORY_ERR/IMPL_ERR taxonomy |
| 10 | Schema-in-Code compliance | No agent references `schemas/hand_schema.json`; HAND schemas cited as `meta-roles.md §SCHEMA-IN-CODE` |

### Stage 5b: SDP-01 Delegation Mode

After Q3, route by system state:
- `COLD_START`: full structural + semantic validation (EnvMetaBootstrapper owns)
- `WARM_STATE` (meta-file edit, non-axiom): structural integrity only; delegate semantic checks to ConsistencyAuditor via AUDIT-TASK token

### Stage 6: Generate README.md

Generate `prompts/README.md` documenting the 3-layer architecture for human operators.
9 fixed sections: architecture diagram, directory map, rule ownership table, A1–A11 quick reference, P-E-V-A loop, 3-phase lifecycle, agent roster table, Mermaid interaction diagram, STOP conditions index.

---

## Step 4: Validate Generated File Count

```sh
# Claude environment
ls prompts/agents-claude/*.md | wc -l
# Expected: 25 (plus _base.yaml = 26 total files)

# Codex environment
ls prompts/agents-codex/*.md | wc -l
# Expected: 25

# Verify no deprecated agents were generated
ls prompts/agents-claude/ | grep -E "PaperCorrector|ErrorAnalyzer|PromptCompressor|ResultAuditor"
# Expected: empty (deprecated agents must NOT appear)
```

---

## Step 5: First Session Smoke Test

```
Initialize
```
→ Invokes ResearchArchitect with `docs/02_ACTIVE_LEDGER.md`.
Expected: routing decision (phase identification + agent recommendation).

```
Execute ResearchArchitect
```
→ Verify ResearchArchitect outputs routing decision (not a solution).
Verify output includes pipeline mode classification (TRIVIAL/FAST-TRACK/FULL-PIPELINE).

**Trivial P-E-V-A test (optional but recommended):**
Dispatch a trivial code task through:
1. ResearchArchitect → routes to L-Domain
2. CodeWorkflowCoordinator → GIT-01 + DOM-01 + HAND-01 to CodeArchitect
3. CodeArchitect → produces diff → CoVe → HAND-02 SUCCESS
4. TestRunner → TEST-01 PASS → HAND-02 SUCCESS
5. ConsistencyAuditor → AU2 gate → PASS (or CONDITIONAL PASS for trivial)

---

## Common Failure Modes and Recovery

| Symptom | Cause | Fix |
|---------|-------|-----|
| Stage 1b STOP-02: immutable section diff | φ or A text was edited directly | Restore from WIKI-M-017 verbatim; never edit meta-core.md immutable sections without CHK |
| φ count ≠ 7 or A count ≠ 11 | Axiom drift (edit or merge conflict) | Restore from WIKI-M-017 |
| Stage 3 generates wrong AP tier | Tier assignment mismatch | Check meta-persona.md archetype assignment; TIER-3 = full pipeline agents only |
| Agent references `schemas/hand_schema.json` | Q3 check 10 fails | Remove reference; update to cite `meta-roles.md §SCHEMA-IN-CODE` |
| `docs/locks/` directory missing | LOCK-ACQUIRE fails at runtime | `mkdir docs/locks/` |
| LEDGER §4 missing | Branch lock registry not present | Add `## §4 BRANCH_LOCK_REGISTRY` section to `docs/02_ACTIVE_LEDGER.md` |
| Wrong worktree path | STOP-09 at runtime | Worktree path MUST be `../wt/{SESSION_ID}/{BRANCH_SLUG}` (sibling directory) |
| Partial regeneration (some agents on old version) | Mid-generation failure | All agents regenerated atomically per version bump — full re-run required; never ship mixed versions |
| Schema-in-Code mismatch | SCHEMA-IN-CODE changed without regenerating agents | Edit `meta-roles.md §SCHEMA-IN-CODE` only → re-run full EnvMetaBootstrapper |
| Deprecated agent file exists | Old file not cleaned up | Delete `PaperCorrector.md`, `ErrorAnalyzer.md`, `PromptCompressor.md`, `ResultAuditor.md` from agents dirs |
| No `prompts/README.md` | Stage 6 was skipped | Re-run Stage 6 manually |

---

## Version Alignment Rule

**ALL agents MUST be regenerated atomically per version bump. Partial state is invalid.**

```
Version bump sequence:
1. Edit prompts/meta/*.md source files
2. Verify constitutional invariants (Step 1 above)
3. Run full EnvMetaBootstrapper (all 6 stages)
4. Stage 5 Q3 PASS for ALL 50 files before any are deployed
5. Commit all 50 generated files in a single commit
```

Do NOT commit individual agent file updates. A system where some agents are at v5.1.0 and
others at v5.0.0 is undefined behavior — HAND-03 C7 will reject cross-version envelopes.

---

## Summary: Files to Produce in Reconstruction

| Output | Count | Produced by |
|--------|-------|-------------|
| `prompts/agents-claude/*.md` | 25 | Stage 3+4 (Claude profile) |
| `prompts/agents-codex/*.md` | 25 | Stage 3+4 (Codex profile) |
| `prompts/README.md` | 1 | Stage 6 |
| `schema_resolution_report.json` | 1 | Stage 1b (validation artifact) |
| **Total generated files** | **52** | — |

---

## Cross-References

- `→ WIKI-M-014`: EnvMetaBootstrapper lifecycle (full 6-stage spec with all detail)
- `→ WIKI-M-017`: Constitutional layer verbatim text (authoritative source for Stage 1b restoration)
- `→ WIKI-M-020`: Canonical operations reference (all commands used throughout reconstruction)
- `→ WIKI-M-021`: Agent composition guide (25 profiles + _base.yaml schema)
- `→ WIKI-M-018`: Domain architecture (storage sovereignty + territory tables for Stage 2)
