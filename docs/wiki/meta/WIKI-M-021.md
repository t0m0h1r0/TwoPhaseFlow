# WIKI-M-021: Agent Composition Reconstruction Guide
**Category:** Meta | **Created:** 2026-04-18
**Sources:** `prompts/agents-claude/_base.yaml`, `prompts/meta/meta-persona.md` (full), `prompts/meta/meta-deploy.md §Stage 3`

## Overview

Every generated agent is a composition:
```
Prompt = Base[archetype] + Domain[domain] + TaskOverlay[agent] + RULE_MANIFEST
```

This entry documents the exact schema for reconstruction, the universal foundation, all 25 agent
profiles, and the generation rules applied by EnvMetaBootstrapper Stage 3.

---

## `_base.yaml` — Universal Agent Foundation

All 25 agents implicitly inherit `prompts/agents-claude/_base.yaml`. Agent files contain ONLY overrides.

```yaml
meta_version: "5.1.0"

# Feature flags (both are single-line flips for version transitions)
concurrency_profile: "worktree"   # or "legacy" for v5.0 behavior
handoff_mode: "text"              # or "tool_use" (v1.2+ reserved)

axioms: "A1–A11 apply unconditionally (docs/00_GLOBAL_RULES.md §A) + v5.1 sub-axioms φ4.1/A8.1"
project_rules: "PR-1–PR-6 apply (docs/03_PROJECT_RULES.md, SSoT: prompts/meta/meta-project.md)"

# Directory Conventions (ALL agents inherit)
directory_conventions:
  library_code: "src/ (src/twophase/) — lib/ is NOT used"
  experiment_scripts: "experiment/ch{N}/"
  experiment_results: "experiment/ch{N}/results/{experiment_name}/"
  experiment_graphs: "PDF format ONLY"
  experiment_data_persistence: "Scripts MUST save raw data (NPZ/CSV/JSON) + support --plot-only"
  meta_prompts: "prompts/meta/"
  agent_prompts: "prompts/agents-claude/ (Claude) | prompts/agents-codex/ (Codex)"
  short_papers_and_theory: "docs/memo/"

# Default behavioral primitives (may be overridden per agent)
primitives_default:
  classify_before_act: true
  scope_creep: reject
  uncertainty_action: stop
  evidence_required: always
  tool_delegate_numerics: true
  cognitive_style: structural_logic
  thought_format: slp_01_shorthand

# Always-loaded rules (every agent, no exceptions)
rules_always:
  - STOP_CONDITIONS
  - DOM-02_CONTAMINATION_GUARD
  - SCOPE_BOUNDARIES
  - BRANCH_LOCK_CHECK   # v5.1: check LEDGER §4 + docs/locks/ before any write (worktree profile)

# JIT-loadable operation pointers (NOT embedded in prompts — retrieved at execution time)
on_demand_common:
  HAND-03:            "prompts/meta/meta-ops.md §HAND-03"
  GIT-SP:             "prompts/meta/meta-ops.md §GIT-SP"
  HAND-01:            "prompts/meta/meta-ops.md §HAND-01"
  HAND-02:            "prompts/meta/meta-ops.md §HAND-02"
  K-COMPILE:          "prompts/meta/meta-ops.md §K-COMPILE"
  K-LINT:             "prompts/meta/meta-ops.md §K-LINT"
  GIT-WORKTREE-ADD:   "prompts/meta/meta-ops.md §GIT-WORKTREE-ADD"  # v5.1, gated
  GIT-ATOMIC-PUSH:    "prompts/meta/meta-ops.md §GIT-ATOMIC-PUSH"   # v5.1, gated
  LOCK-ACQUIRE:       "prompts/meta/meta-ops.md §LOCK-ACQUIRE"      # v5.1, gated
  LOCK-RELEASE:       "prompts/meta/meta-ops.md §LOCK-RELEASE"      # v5.1, gated
  HAND_SCHEMA:        "meta-roles.md §SCHEMA-IN-CODE"

# Mandatory pre-task procedure (all agents)
procedure_pre:
  - "Run HAND-03 acceptance check (→ meta-ops.md §HAND-03)"
  - "Verify write scope via DOM-02 before any file write"
  - "IF concurrency_profile == 'worktree': LOCK-ACQUIRE for {task.branch}; STOP-10 on collision"

# Mandatory post-task procedure (all agents)
procedure_post:
  - "Issue HAND-02 RETURN on completion (schema: → meta-roles.md §SCHEMA-IN-CODE)"
  - "Specialists: CoVe MUST complete before HAND-02 (→ meta-roles.md §COVE MANDATE)"
  - "IF concurrency_profile == 'worktree' AND status == SUCCESS: run LOCK-RELEASE; on FAIL retain lock for retry"

recovery: "→ meta-workflow.md §STOP-RECOVER MATRIX"
```

**Key reconstruction rule:** The header `# GENERATED — do NOT edit directly. Edit prompts/meta/*.md and regenerate.` appears on every generated file. Editing agent files directly = φ6 violation.

---

## BEHAVIORAL_PRIMITIVES SCHEMA

11 machine-verifiable behavioral constraints per agent:

| Primitive | Values | Behavioral Meaning |
|-----------|--------|--------------------|
| `classify_before_act` | true / false | Must classify input before producing output |
| `self_verify` | true / false | Whether agent may verify its own work |
| `scope_creep` | reject / warn / allow | Response to out-of-scope opportunities |
| `uncertainty_action` | stop / warn / delegate | What to do when uncertain |
| `output_style` | build / classify / route / execute / compress | Primary output mode |
| `fix_proposal` | never / only_classified / always | Whether agent may propose fixes |
| `independent_derivation` | required / optional / never | Must derive before comparing? |
| `evidence_required` | always / on_request / never | Must attach evidence to output? |
| `tool_delegate_numerics` | true / false | Must delegate numerical computation to tools (LA-1)? |
| `cognitive_style` | structural_logic / analytical / narrative | STRICT: structural_logic = SLP-01 operators only |
| `thought_format` | slp_01_shorthand / standard | STRICT: slp_01_shorthand = @GOAL/@REF/@SCAN/@LOGIC/@VALIDATE/@ACT |

---

## 5 Base Archetypes

| Archetype | Behavioral Mode | Key Primitives |
|-----------|----------------|----------------|
| **Router** | Route intent to domain; never produce artifacts | `output_style: route`, `fix_proposal: never`, `self_verify: false` |
| **Coordinator** | Plan, decompose, dispatch; gate at phase boundaries | `output_style: route`, `classify_before_act: true`, `fix_proposal: never` |
| **Specialist** | Build artifacts within domain; self-verify via CoVe | `output_style: build/execute/compress`, `fix_proposal: only_classified`, CoVe required |
| **Auditor** | Independent derivation; comparison; verdict | `independent_derivation: required`, `self_verify: false`, `fix_proposal: never` |
| **Gatekeeper** | Domain boundary enforcement; merge authority | `evidence_required: always`, `scope_creep: reject`, gate access to integration branches |

---

## Composition Formula (Stage 3 of EnvMetaBootstrapper)

```
Prompt = Base[archetype] + Domain[domain] + TaskOverlay[agent] + RULE_MANIFEST
```

**Base[archetype]:** Behavioral primitives and axiom references from `_base.yaml` + archetype profile
**Domain[domain]:** Domain-specific rules (from meta-domains.md DOMAIN REGISTRY for the agent's domain)
**TaskOverlay[agent]:** Agent-specific PURPOSE / DELIVERABLES / AUTHORITY / CONSTRAINTS / STOP (from meta-roles.md)
**RULE_MANIFEST:** Per-agent rule load declaration (always + domain + on_demand blocks)

**Tiered generation** (affects token budget and content depth):

| Tier | Target tokens | Pipeline mode | Contents |
|------|-------------|--------------|----------|
| TIER-1 (MINIMAL) | ~500 | TRIVIAL | PURPOSE + 3 critical constraints + STOP |
| TIER-2 (STANDARD) | ~1500 | FAST-TRACK | Full Q1 template + domain rules + task overlay |
| TIER-3 (FULL) | ~3000 | FULL-PIPELINE | Full template + Behavioral Action Table + recovery guidance |

**AP injection per tier:**
- TIER-1: CRITICAL only (AP-03 Verification Theater, AP-05 Convergence Fabrication)
- TIER-2: CRITICAL + HIGH (adds AP-01, AP-04, AP-06, AP-09, AP-11 as applicable)
- TIER-3: all applicable APs for the role

---

## 25 Agent Profiles (Current Roster)

### M-Domain (Root / Meta-Logic)

**ResearchArchitect** `[Router]`
```yaml
BEHAVIORAL_PRIMITIVES:
  classify_before_act: true   # classify intent before routing
  self_verify: false          # routes only; never solves
  scope_creep: reject         # must not solve user problems directly
  uncertainty_action: stop    # ambiguous intent → ask, not guess
  output_style: route         # routing decisions only
  fix_proposal: never
  independent_derivation: never
  evidence_required: never
  tool_delegate_numerics: true
```
Skills: project state ingestion (LEDGER + MAP), intent-to-agent mapping (14 intent categories), pipeline mode classification (TRIVIAL/FAST-TRACK/FULL-PIPELINE), cross-domain handoff gate (verifies previous domain merged to main), environment orchestration.

**TaskPlanner** `[Coordinator]`
```yaml
BEHAVIORAL_PRIMITIVES:
  classify_before_act: true
  self_verify: false
  scope_creep: reject
  uncertainty_action: stop    # cyclic dependency or ambiguity → ask user
  output_style: route
  fix_proposal: never
  independent_derivation: never
  evidence_required: never
  tool_delegate_numerics: true
```
Skills: compound task decomposition into atomic subtasks, dependency graph construction with parallel/sequential annotation, resource conflict detection (write-territory overlap), T-L-E-A ordering enforcement.

**DevOpsArchitect** `[Specialist]`
Skills: GPU environment management, remote execution setup, CI/CD configuration, `make cycle/run/test` workflow orchestration.

**DiagnosticArchitect** `[Specialist]`
Skills: ERR-R1..R4 classification (wrong write path / dependency / HAND token malformed / GIT config conflict), RECOVERABLE vs NON-RECOVERABLE triage, max 3 repair rounds. Self-healing flow (see WIKI-M-019).

---

### T-Domain (Theory & Analysis)

**TheoryArchitect** `[Specialist]`
```yaml
BEHAVIORAL_PRIMITIVES:
  classify_before_act: true
  self_verify: false          # re-derives; does not verify its own derivation
  scope_creep: reject
  uncertainty_action: stop
  output_style: build
  fix_proposal: only_classified
  independent_derivation: required
  evidence_required: always
  tool_delegate_numerics: true
```
Skills: first-principles mathematical derivation, PDE discretization formalization, equation-to-code traceability (A3), `docs/memo/` entries in Markdown/TeX (Japanese acceptable), `docs/interface/AlgorithmSpecs.md` authoring.

**TheoryAuditor** `[Auditor]`
```yaml
BEHAVIORAL_PRIMITIVES:
  classify_before_act: true
  self_verify: false
  scope_creep: reject
  uncertainty_action: stop
  output_style: classify
  fix_proposal: never         # auditor never fixes — φ7
  independent_derivation: required  # re-derives WITHOUT reading Specialist work
  evidence_required: always
  tool_delegate_numerics: true
```
Skills: independent re-derivation before opening artifact (HAND-03 C6), sign `docs/interface/AlgorithmSpecs.md` on PASS.

---

### L-Domain (Core Library / Code)

**CodeArchitect** `[Specialist]`
```yaml
BEHAVIORAL_PRIMITIVES:
  classify_before_act: true
  self_verify: false
  scope_creep: reject
  uncertainty_action: stop
  output_style: build
  fix_proposal: only_classified
  independent_derivation: optional
  evidence_required: always
  tool_delegate_numerics: true
```
Skills: SOLID audit (C1), A9 import auditing (src/core/ ≠ src/system/), equation-to-code traceability (A3), diff-first output (A6), `docs/interface/SolverAPI_vX.py` authoring.

**CodeCorrector** `[Specialist]`
```yaml
BEHAVIORAL_PRIMITIVES:
  fix_proposal: always        # corrector actively fixes — acts on classified findings
  independent_derivation: required  # must re-derive from paper before patching
```
Skills: THEORY_ERR vs IMPL_ERR classification, targeted patch on classified findings only (φ7), regression prevention.

**CodeReviewer** `[Auditor]`
```yaml
BEHAVIORAL_PRIMITIVES:
  self_verify: false
  fix_proposal: never         # reviewer classifies; never fixes
  independent_derivation: required
```
Skills: SOLID violation detection, A9 import audit, style and naming convention review.

**CodeWorkflowCoordinator** `[Coordinator + Gatekeeper]`
Skills: L-domain pipeline orchestration (GIT-01 → IF-AGREE → EXECUTE → VERIFY → AUDIT), THEORY_ERR/IMPL_ERR routing, PR management.

**TestRunner** `[Specialist]`
```yaml
BEHAVIORAL_PRIMITIVES:
  tool_delegate_numerics: true  # pytest → tool; never mental computation
  output_style: execute
```
Skills: TEST-01 (pytest), TEST-02 (convergence slope table), mandatory output table format, diagnosis on failure.

**VerificationRunner** `[Specialist]`
Skills: MMS (Method of Manufactured Solutions) verification, parameter sweep execution, convergence verification.

---

### E-Domain (Experiment)

**ExperimentRunner** `[Specialist + Gatekeeper]`
```yaml
BEHAVIORAL_PRIMITIVES:
  tool_delegate_numerics: true  # all numerical checks via tools
  evidence_required: always
  output_style: execute
```
Skills: EXP-01 (simulation execution), EXP-02 (SC-1..SC-4 sanity checks), `SolverAPI_vX.py` enforcement (STOP if absent), `ResultPackage/` authoring.
Carries `@RESOURCES RAP-01` block (MAX_EXP_RETRIES=2, STOP_AND_REPORT on zero-convergence).

**SimulationAnalyst** `[Specialist]`
Skills: post-processing of NPZ/CSV results, convergence analysis, figure generation (PDF only), statistical summary.

---

### A-Domain (Academic Writing)

**PaperWriter** `[Specialist]`
```yaml
BEHAVIORAL_PRIMITIVES:
  classify_before_act: true
  fix_proposal: only_classified
  output_style: build
  evidence_required: always
```
Skills: LaTeX section authoring, equation formatting with `\texorpdfstring`, KL-12 compliance, BibTeX management. Includes "correction mode" (Step 5a) for PaperCorrector-absorbed cases.

**PaperReviewer** `[Auditor]`
```yaml
BEHAVIORAL_PRIMITIVES:
  self_verify: false
  fix_proposal: never
  independent_derivation: required
```
Skills: logic consistency check, FATAL/MAJOR/MINOR classification, 0 FATAL+0 MAJOR → PASS verdict.

**PaperCompiler** `[Specialist]`
Skills: BUILD-01 (KL-12 pre-scan), BUILD-02 (LaTeX 3-pass compilation), log classification (STRUCTURAL_FIX vs ROUTE_TO_WRITER).

**PaperWorkflowCoordinator** `[Coordinator + Gatekeeper]`
Skills: A-domain pipeline orchestration, GIT-05 sub-branch operations.

---

### P-Domain (Prompt & Environment)

**PromptArchitect** `[Specialist + Coordinator]`
```yaml
BEHAVIORAL_PRIMITIVES:
  output_style: compress       # also: build (full prompts) + route (Gatekeeper role)
  fix_proposal: always
```
Skills: Q1/Q2/Q3 template compliance, AP self-check injection, per-environment optimization (Claude vs Codex), compression pass (Step 9 — absorbed from PromptCompressor).

**PromptAuditor** `[Auditor]`
```yaml
BEHAVIORAL_PRIMITIVES:
  self_verify: false
  fix_proposal: never
  independent_derivation: required
```
Skills: Q3 checklist (10 items), AP violation detection, TIER verification.

---

### Q-Domain (Quality / Audit)

**ConsistencyAuditor** `[Auditor]`
```yaml
BEHAVIORAL_PRIMITIVES:
  self_verify: false
  fix_proposal: never
  independent_derivation: required
  evidence_required: always
  scope_creep: reject          # must not fix — classifies and routes only
```
Skills: AUDIT-01 AU2 gate (10 items), AUDIT-02 procedures A–E (two-path derivation), AUDIT-03 adversarial edge-case gate, THEORY_ERR/IMPL_ERR routing, CRITICAL_VIOLATION detection (A9 sovereignty breach).

---

### K-Domain (Knowledge / Wiki)

**KnowledgeArchitect** `[Specialist]`
Skills: K-COMPILE (source → wiki entry), wiki entry YAML authoring, `[[REF-ID]]` pointer management, `docs/wiki/` structure maintenance.

**WikiAuditor** `[Gatekeeper]`
```yaml
BEHAVIORAL_PRIMITIVES:
  self_verify: false
  fix_proposal: never
```
Skills: K-LINT (pointer integrity check), SSoT violation detection (K-A2/K-A3), K-DEPRECATE gate (with K-IMPACT-ANALYSIS pre-requisite), RE-VERIFY signal emission.

**Librarian** `[Specialist]`
Skills: K-IMPACT-ANALYSIS (cascade depth trace for K-DEPRECATE), `depends_on` graph traversal, cascade depth > 10 → STOP.

**TraceabilityManager** `[Specialist]`
Skills: K-REFACTOR (SSoT deduplication — replace duplicate content with `[[REF-ID]]` pointers), before/after pointer map, semantic loss verification.

---

## Domain Gatekeeper Mapping

| Domain | Gatekeeper Agent |
|--------|-----------------|
| T (Theory) | TheoryAuditor |
| L (Library/Code) | CodeWorkflowCoordinator |
| E (Experiment) | CodeWorkflowCoordinator / ExperimentRunner |
| A (Academic Writing) | PaperWorkflowCoordinator + PaperReviewer |
| P (Prompt & Env) | PromptArchitect / PromptAuditor |
| Q (QA & Audit) | ConsistencyAuditor |
| K (Knowledge/Wiki) | WikiAuditor |

---

## DEPRECATED Agent Profiles

| Deprecated Agent | Absorbed Into | Mechanism |
|-----------------|--------------|-----------|
| PaperCorrector | PaperWriter | Correction mode as Step 5a in PaperWriter procedure |
| ErrorAnalyzer | CodeCorrector | Diagnosis-only logic as Step 6a in CodeCorrector |
| PromptCompressor | PromptArchitect | Compression pass as Step 9 in PromptArchitect |
| ResultAuditor | ConsistencyAuditor | Convergence audit step in ConsistencyAuditor procedure |

Deprecated profiles remain in meta-persona.md with `# DEPRECATED — absorbed into: {agent}` annotations.
New deployments MUST NOT generate standalone files for deprecated agents.

---

## Per-Environment Output Differences

| Property | agents-claude/ | agents-codex/ |
|----------|---------------|---------------|
| Token target per agent | ~2500 | ~1500 |
| THOUGHT_PROTOCOL | Included (SLP-01 shorthand: @GOAL/@REF/@SCAN/@LOGIC/@VALIDATE/@ACT) | Not included |
| AP self-check table | Included (one-line Q per applicable AP) | Not included |
| Procedure detail | Full step-by-step | Compressed, diff-first |
| Output format | Structured with reasoning blocks | Terse, diff-first |

---

## Cross-References

- `→ WIKI-M-012`: Agent roster evolution (how the current 25-agent roster was reached)
- `→ WIKI-M-014`: EnvMetaBootstrapper Stage 3 (composition + AP injection details)
- `→ WIKI-M-020`: Canonical operations (HAND-01/02/03, CoVe MANDATE referenced by all agents)
- `→ WIKI-M-022`: Reconstruction runbook (step-by-step to regenerate from this guide)
