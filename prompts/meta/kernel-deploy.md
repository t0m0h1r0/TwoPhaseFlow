# kernel-deploy.md — EnvMetaBootstrapper v7.0.0 Spec
# Replaces: meta-deploy.md (46KB → ~20KB, -57%).
# Bootstrapper role: generate and validate full agent system + docs/ from kernel-*.md files.
# FOUNDATION: kernel-constitution.md §AXIOMS ← READ FIRST

<meta_section id="META-DEPLOY" version="7.0.0" axiom_refs="phi6,A7,A10">
<purpose>EnvMetaBootstrapper specification. Deterministic generation from kernel-*.md → agent prompts + docs/.</purpose>
<authority>ResearchArchitect invokes full bootstrap. PromptArchitect invokes WARM_BOOT for non-axiom meta edits.</authority>
<rules>
- MUST execute stages sequentially. Do not skip stages.
- MUST NOT improvise beyond defined workflow.
- MUST abort on any STOP-02; emit schema_resolution_report.json before abort.
- MUST NOT modify φ1–φ7 or A1–A11 text (grep gates: count==7 for ## φ, count==11 for ## A).
- MUST use `git rev-parse --git-common-dir` for path resolution (works in primary checkout and worktrees).
</rules>
</meta_section>

────────────────────────────────────────────────────────
# § INPUTS (v7.0.0 — 8 kernel files)

| File | Purpose |
|------|---------|
| kernel-constitution.md | φ1–φ7, A1–A11, isolation levels, LA-1..LA-5 |
| kernel-roles.md | SCHEMA-IN-CODE, Agent Profile Table, CoVe mandate |
| kernel-ops.md | All operations: HAND-01..04, GIT, LOCK, BUILD, TEST, EXP, AUDIT, K ops |
| kernel-domains.md | 4×4 domain matrix, branch ownership, micro-agent taxonomy |
| kernel-workflow.md | P-E-V-A loop, T-L-E-A pipeline, STOP-RECOVER MATRIX, DYNAMIC-REPLANNING |
| kernel-antipatterns.md | AP-01..AP-12 + injection rules |
| kernel-project.md | PR-1..PR-6 project-specific rules |
| kernel-deploy.md | THIS FILE — bootstrapper spec (excluded from Stage 1b checks) |

Also reads: `prompts/agents-claude/_base.yaml` and `prompts/agents-codex/_base.yaml`.

────────────────────────────────────────────────────────
# § ENVIRONMENT PROFILES (Q2)

| Env | Style |
|-----|-------|
| Claude | Explicit constraints; structure and traceability; stop conditions emphasized |
| Codex | Executable clarity; patch-oriented, diff-first; minimal line changes; invariants |

────────────────────────────────────────────────────────
# § DEPLOYMENT WORKFLOW

## Stage 1: Parse

Read all 8 kernel files. Extract:
- φ1–φ7, A1–A11, LA-1..LA-5, isolation levels L0-L3 (kernel-constitution.md)
- SCHEMA-IN-CODE (HandoffEnvelope, Hand01..04Payload, DebateResult), Agent Profile Table, CoVe spec (kernel-roles.md)
- All operations: HAND-01..04, GIT, LOCK, BUILD, TEST, EXP, AUDIT, K, shorthand syntax (kernel-ops.md)
- 4×4 domain registry, branch rules, micro-agent taxonomy, DDA rules (kernel-domains.md)
- P-E-V-A loop, T-L-E-A pipeline, pipeline modes, STOP-RECOVER MATRIX, DYNAMIC-REPLANNING, PROTO-DEBATE (kernel-workflow.md)
- AP-01..AP-12, injection rules (kernel-antipatterns.md)
- PR-1..PR-6 project rules (kernel-project.md)
- Environment profiles Q2, _base.yaml feature flags (this file + _base.yaml)

### Stage 1b: XML-Aware Parse

**Scope:** All kernel-*.md EXCEPT kernel-deploy.md (this file is spec text, not schema-wrapped content).

1. **Closed-vocabulary allow-list check.** Inside each `<meta_section>` block, child tags MUST be subset of:
   `purpose, authority, rules, tool_use, tool_declaration, parameters, procedure, thought_process, stop_conditions, see_also`
   Unknown tag inside meta_section → STOP-02.

2. **Tag balance check.** Count meta_section opens/closes per file; must match. Mismatch → STOP-02.

3. **`<meta_section id="…">` discovery.** Required attributes: `id` (unique across all files), `version` (matches meta_version in _base.yaml), `axiom_refs` (comma-separated). Optional: `immutable="true"`.

4. **`immutable="true"` body-diff gate.** For sections with `immutable="true"` (φ1–φ7, A1–A11, HAND-03 7-checks, SCHEMA-IN-CODE): diff body against `git show HEAD:prompts/meta/{file}`. Non-empty diff → STOP-02 SYSTEM_PANIC (axiom drift).

5. **Eager `$ref` resolution.** For every `<parameters format="json">` block with `"$ref": "kernel-*.md#…"`: verify file exists + anchor resolves. Dangling ref → abort; do NOT write any agent prompt. Emit `schema_resolution_report.json`.

6. **RFC-2119 rules check.** Every `<rules>` bullet MUST begin with `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, or `MAY`. Non-conformant → STOP-SOFT with warning in report.

7. **Legacy anchor preservation.** Every wrapped section must have its markdown heading (e.g., `## HAND-01:`) inside the meta_section block. Missing → STOP-02.

8. **Backward compatibility.** Files without meta_section wrappers pass through to legacy text-pattern parser unchanged.

**Report artifact:** emit `schema_resolution_report.json` after every run:
```json
{
  "vocab_check": "PASS|FAIL",
  "balance_check": "PASS|FAIL",
  "id_registry": [...],
  "immutable_diff_results": [...],
  "ref_resolution_results": [...],
  "rfc2119_violations": [...],
  "timestamp": "ISO 8601 UTC"
}
```
Absence of this file after a run → STOP-SOFT.

────────────────────────────────────────────────────────
## Stage 2: Initialize Directory Structure + docs/

### 2a: Create Matrix Directories

```sh
mkdir -p docs/memo/                         # T-Domain — theory derivations
mkdir -p src/twophase/                      # L-Domain — solver library
mkdir -p experiment/                        # E-Domain — experiment scripts + results
mkdir -p paper/                             # A-Domain — LaTeX sources
mkdir -p prompts/meta/                      # M-Domain — kernel files (SSoT)
mkdir -p prompts/agents-claude/ prompts/agents-codex/  # P-Domain — agent prompts
mkdir -p docs/interface/                    # Cross-domain contracts
mkdir -p artifacts/{T,L,E,Q,M}/            # Micro-agent staging areas
mkdir -p docs/locks/                        # Branch lock files
mkdir -p docs/wiki/{theory,experiment,cross-domain,paper,code}/  # K-Domain wiki
```

FORBIDDEN: `prompts/meta/schemas/` — HandoffEnvelope definitions are inline in kernel-roles.md §SCHEMA-IN-CODE.
FORBIDDEN: Directories with leading numbers (`01_foo/`) or dot-prefix files beyond legacy exceptions.

**Exception (backward compat):** `docs/00_GLOBAL_RULES.md`, `docs/01_PROJECT_MAP.md`, `docs/02_ACTIVE_LEDGER.md` retain legacy names. New files must use clean names.

### 2b: Generate docs/ Files

Three files to generate (if missing) or update header (if stale):

**docs/00_GLOBAL_RULES.md** (project-independent):
Required sections: `§A` Core Axioms A1–A11 | `§C` Code Rules C1–C6 | `§P` Paper Rules P1–P4,KL-12 | `§Q` Prompt Rules Q1–Q4 | `§AU` Audit Rules AU1–AU3 | `§GIT` 3-Phase Lifecycle | `§P-E-V-A` Execution Loop

**docs/01_PROJECT_MAP.md** (project-specific technical structure):
Required sections: `§1` Module Map | `§2` Interface Contracts | `§3` Config Hierarchy | `§4` Construction + SOLID | `§5` Implementation Constraints | `§6` Numerical Algorithm Reference | `§7` Active Assumption Register (ASM-ID) | `§8` C2 Legacy Register | `§9` Paper Structure | `§10` P3-D Register | `§11` Matrix Domain Map

**docs/02_ACTIVE_LEDGER.md** (live state, append-only for CHK/ASM/KL):
Required sections: `§ACTIVE_STATE` phase/branch/next_action | `§CHECKLIST` CHK-IDs | `§ASSUMPTIONS` ASM-IDs | `§LESSONS` LES-IDs | `§REPLAN_LOG` (v7.0.0 addition)

Also required: `§4 BRANCH_LOCK_REGISTRY` (under concurrency_profile == "worktree"):
```
[BRANCH_LOCK_REGISTRY]
  branch: dev/L/CodeArchitect/task-42
  session_id: {UUID v4}
  acquired_at: {ISO 8601 UTC}
  lock_path: docs/locks/dev-L-CodeArchitect-task-42.lock.json
```

**docs/03_PROJECT_RULES.md** (generated from kernel-project.md):
Required: all PR-1..PR-6 sections. Verification: `grep -c "^## PR-" docs/03_PROJECT_RULES.md` must equal 6.

Also generate: `docs/wiki/INDEX.md` if absent.

### 2c: Generate prompts/README.md

Generate (or overwrite) `prompts/README.md` on every bootstrap run.
Header line: `# GENERATED — do NOT edit directly. Edit prompts/meta/kernel-*.md and regenerate.`

Required sections in order:

| Section | Source |
|---------|--------|
| §1 Architecture Principle | kernel-deploy.md §INPUTS (3-layer stack) |
| §2 Directory Map | kernel-deploy.md §2a + Stage 3 output paths |
| §3 Rule Ownership Map | kernel-constitution.md + kernel-roles.md |
| §4 A1–A11 Quick Reference | kernel-constitution.md §AXIOMS |
| §4b φ-Principles TL;DR | kernel-constitution.md §DESIGN PHILOSOPHY |
| §5 Execution Loop | kernel-workflow.md §P-E-V-A |
| §5b Agent Interaction Map | kernel-domains.md §AGENT INTERACTION MAP (verbatim) |
| §6 Agent Roster | kernel-roles.md §Agent Profile Table (all 23 agents) |
| §7 Regeneration Instructions | kernel-deploy.md §PORTABILITY |

§5b MUST be copied verbatim from `kernel-domains.md §AGENT INTERACTION MAP` — do NOT regenerate independently.

────────────────────────────────────────────────────────
## Stage 3: Generate Agent Prompts

Output: `prompts/agents-{env}/{AgentName}.md`
Header on each file: `# GENERATED — do NOT edit directly. Edit prompts/meta/kernel-*.md and regenerate.`

### 3a: Agent Composition Formula

```
Agent Prompt = Base[archetype] + Domain[domain] + TaskOverlay[agent] + RULE_MANIFEST + AP_INJECTION
```

**Base archetypes (from kernel-roles.md §Agent Profile Table):**
- Root: ResearchArchitect patterns (routing, condensation, replan, all protocols)
- Gate: Gatekeeper patterns (G-01..G-08, AU2 gate, CONDITIONAL PASS)
- Spec: Specialist patterns (S-01..S-07, CoVe, primitive-diff only)

**Domain modules:**
- L: C1-SOLID + C2-PRESERVE + CCD primacy (PR-1) + PPE policy (PR-2) + MMS (PR-3) + toolkit (PR-4)
- T: A3 chain + algorithm fidelity (PR-5) + no PPE LGMRES (PR-6)
- E: EXP-01/02 + SC-1..SC-4 + twophase.experiment toolkit
- A: P1-P4 + KL-12 + BUILD-01/02
- P: Q1-Q4 + WARM_BOOT rules
- K: K-COMPILE + K-LINT + K-DEPRECATE + K-IMPACT-ANALYSIS

**TaskOverlay:** derived from kernel-roles.md §Agent Role Contracts (DELIVERABLES / AUTHORITY / CONSTRAINTS / STOP per agent).

**AP injection:** per tier and agent's inject list from kernel-antipatterns.md. ≤ 200 tokens.

### 3b: Tiered Prompt Generation

| Tier | Target tokens | Pipeline mode | Contents |
|------|--------------|---------------|---------|
| TIER-1 (MINIMAL) | ~500 | TRIVIAL | PURPOSE + 3 critical constraints + STOP codes + RULE_MANIFEST.always |
| TIER-2 (STANDARD) | ~1500 | FAST-TRACK | Full Q1 template + domain rules + task overlay (no Behavioral Action Table) |
| TIER-3 (FULL) | ~3000 | FULL-PIPELINE | Full Q1 template + Behavioral Action Table + domain rules + task overlay + recovery guidance |

**Tier assignment** (from kernel-roles.md §Agent Profile Table `tier` column):
- TIER-1: Librarian, TraceabilityManager (simple KV lookup roles)
- TIER-2: all Specialists not in TIER-1 or TIER-3
- TIER-3: all Gatekeepers + Root Admin (ResearchArchitect)

**THOUGHT_PROTOCOL injection rules (v7.0.0 — tier-conditional):**
- TIER-1: NO THOUGHT_PROTOCOL (removed entirely)
- TIER-2: 1-line shorthand: `Before HAND-02: Q1 (logical), Q2 (axiom A1-A11), Q3 (scope/IF-AGREEMENT).`
- TIER-3: Full CoVe spec from kernel-roles.md §COVE MANDATE

**Primitive-diff inheritance rule (v7.0.0):**
Agent files declare ONLY fields that differ from _base.yaml defaults. Do NOT re-declare:
- Default STOP codes (STOP-01, STOP-02, STOP-03 apply to all)
- Default isolation level L1 (only declare if different)
- Default CoVe mandate (only declare exception if TIER-1)

### 3c: RULE_MANIFEST Generation

Generate per-agent RULE_MANIFEST YAML:
```yaml
RULE_MANIFEST:
  always:
    - STOP                 # kernel-ops.md §STOP CONDITIONS
    - DOM-02               # kernel-domains.md §DOM-02
    - SCOPE                # DISPATCH scope_out
  domain:                  # domain-specific rules (LA-4: include only agent's domain)
    - C1-SOLID             # kernel-constitution.md §C-rules
    - PR-1                 # kernel-project.md §PR-1 (L-domain only)
  on_demand:               # loaded JIT when operation needed (LA-5)
    - kernel-ops.md §GIT-SP
    - kernel-ops.md §HAND-01
    - kernel-ops.md §AUDIT-01
  task_specific:           # loaded only for current task class
    - kernel-ops.md §TEST-02  # (for CCD operator changes)
```

### 3d: AP Injection Table (per agent)

```markdown
### Anti-Patterns (check before output)
| AP | Pattern | Self-check |
|----|---------|-----------|
| AP-03 | Verification Theater | Independent evidence (tool output)? |
| AP-09 | Context Collapse | STOP conditions re-read in last 5 turns? |
```

TIER-1: AP-03, AP-05 only. TIER-2: add AP-04, AP-06, AP-09. TIER-3: all applicable per inject list.

────────────────────────────────────────────────────────
## Stage 4: Validate Generated Output

Run after all agent files written. Abort on STOP-02.

### Q3 Validation Checklist (10 items, v7.0.0)

| # | Check | Method | STOP on fail |
|---|-------|--------|-------------|
| 1 | φ1–φ7 count = 7 in kernel-constitution.md | `grep -c '^## φ' kernel-constitution.md` | STOP-02 |
| 2 | A1–A11 count = 11 in kernel-constitution.md | `grep -c '^## A[0-9]' kernel-constitution.md` | STOP-02 |
| 3 | AP-01..AP-12 count = 12 in kernel-antipatterns.md | `grep -c '^## AP-' kernel-antipatterns.md` | STOP-02 |
| 4 | Agent file count = 23 per environment | `ls prompts/agents-claude/*.md \| grep -v _base \| wc -l` = 23 | STOP-02 |
| 5 | PR-ID count = 6 in docs/03_PROJECT_RULES.md | `grep -c '^## PR-' docs/03_PROJECT_RULES.md` | STOP-SOFT |
| 6 | No duplicate meta_section IDs | `grep -o 'id="[^"]*"' kernel-*.md \| sort \| uniq -d` = empty | STOP-02 |
| 7 | v6.0.0 features present in required agents | grep checks below | STOP-SOFT |
| 8 | schema_resolution_report.json exists | file exists + dangling_refs == [] | STOP-SOFT |
| 9 | immutable zone sha256 unchanged | body-diff gate (Stage 1b step 4) | STOP-02 |
| 10 | Token budget: TIER-1 < 700, TIER-2 < 2000, TIER-3 < 3500 | tiktoken count per agent | STOP-SOFT |

**Check 7 grep gates:**
```bash
grep -c 'HAND-04\|PROTO-DEBATE' prompts/agents-claude/ConsistencyAuditor.md   # > 0
grep -c 'BLOCKED_REPLAN\|REPLAN(' prompts/agents-claude/CodeWorkflowCoordinator.md  # > 0
grep -c 'OP-CONDENSE\|CONDENSE()' prompts/agents-claude/ResearchArchitect.md   # > 0
grep -c 'R1\|R2\|R3\|R4\|rubric\|≥80' prompts/agents-claude/ConsistencyAuditor.md  # > 0
```

### Load-Bearing Generation Invariant (φ6)

Full-regen diff across all 23 agents MUST show mechanical (same N lines per file) additive changes.
Any non-mechanical drift → bootstrapper bug → abort and investigate.

────────────────────────────────────────────────────────
## Stage 5: Register + Notify

1. Create CHK entry in `docs/02_ACTIVE_LEDGER.md §CHECKLIST`:
   ```
   CHK-{NNN} | IN_PROGRESS | prompt | prompts/agents-{env}/ | regen v7.0.0 | {date}
   ```
2. Update `§ACTIVE_STATE` with current phase + branch.
3. Emit HAND-02 to ResearchArchitect: `status: SUCCESS; produced: [schema_resolution_report.json, prompts/agents-claude/, prompts/agents-codex/, prompts/README.md]`.

────────────────────────────────────────────────────────
# § PORTABILITY: Retargeting to a New Project

1. Replace `kernel-project.md` with new PR-rules.
2. Regenerate `docs/03_PROJECT_RULES.md` from the new kernel-project.md.
3. Update `_base.yaml :: project_rules` if PR-IDs change.
4. Universal files (kernel-constitution.md, kernel-domains.md, kernel-ops.md, kernel-workflow.md, kernel-antipatterns.md) require NO changes.
5. Verification: `grep -c "^## PR-" docs/03_PROJECT_RULES.md` must equal the count in the new kernel-project.md.

────────────────────────────────────────────────────────
# § WARM_BOOT Fast-Path

Triggered when meta-file edit does NOT affect A1–A11 or φ1–φ7 text.

```
1. Bootstrapper: Structural Generate (Fast) — IDs + file paths + tag closure only.
2. ConsistencyAuditor: Audit Meta-Consistency (Heavy) — Axiom alignment + cross-ref integrity.
3. Gatekeeper: Sign & Hot-Reload generated agents (overwrite affected agents only).
```

WARM_BOOT is NOT permitted if φ1–φ7 / A1–A11 text diff is non-empty → full COLD_START required.
