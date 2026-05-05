# kernel-deploy.md - Generic Research Agent Deployment v1.0.0
# Bootstrapper spec: generate and validate the research-agent system from kernel-*.md.

<meta_section id="META-DEPLOY" version="1.0.0" axiom_refs="phi6,A7,A10">
<purpose>Deterministic deployment workflow for generic research agents: kernel files -> docs -> agent prompts -> validation reports.</purpose>
<authority>ResearchArchitect invokes full bootstrap. PromptArchitect may perform WARM_BOOT for non-axiom prompt edits.</authority>
<rules>
- MUST execute deployment stages sequentially.
- MUST preserve source artifacts under `paper/source/`.
- MUST abort on schema or source-integrity failure.
- MUST keep full operation syntax in kernel files or skill capsules, not repeated inside generated agent prompts.
</rules>
</meta_section>

--------------------------------------------------------
# § INPUTS

| File | Purpose |
|------|---------|
| kernel-constitution.md | universal axioms and authority rules |
| kernel-roles.md | role contracts and handoff schemas |
| kernel-ops.md | operations and STOP conditions |
| kernel-domains.md | generic research domain registry |
| kernel-workflow.md | P-E-V-A and research pipeline |
| kernel-antipatterns.md | anti-pattern catalogue |
| kernel-project.md | current project profile |
| kernel-deploy.md | this deployment spec |

Also reads `prompts/agents-claude/_base.yaml` and `prompts/agents-codex/_base.yaml`.

--------------------------------------------------------
# § ENVIRONMENT PROFILES

| Env | Style |
|-----|-------|
| Claude | explicit constraints, role narrative, traceability emphasis |
| Codex | executable clarity, patch-oriented work, compact invariants, worktree-first commits, user-approved no-ff main merges |

--------------------------------------------------------
# § DEPLOYMENT WORKFLOW

## Stage 1 - Parse

Full bootstrap reads all kernel files and extracts the table below. WARM_BOOT
reads only changed kernel files plus direct dependencies named by their
`on_demand` references.

| Source | Extract |
|--------|---------|
| constitution | axioms, authority, isolation levels |
| roles | agent roster, schema, role contracts |
| ops | handoff, git, lock, audit, metric, tool-trust operations |
| domains | domain registry, write territories, interface contracts |
| workflow | task classification, P-E-V-A, replan, debate |
| antipatterns | AP checks and injections |
| project | PR-1..PR-6 |

Emit `schema_resolution_report.json` with tag balance, duplicate IDs, dangling refs,
and source-integrity status.

## Stage 2 - Initialize Directories

```sh
mkdir -p paper/source paper/sections paper/figures paper/presentations
mkdir -p docs/memo docs/evidence docs/interface docs/locks docs/wiki/{theory,analysis,evidence,paper,cross-domain,changelog}
mkdir -p src analysis notebooks tests data
mkdir -p artifacts/{M,T,R,E,A,Q,K,P}
mkdir -p prompts/meta prompts/agents-claude prompts/agents-codex prompts/skills
```

Generated docs:

| File | Purpose |
|------|---------|
| docs/00_GLOBAL_RULES.md | compact universal rules and workflow pointers |
| docs/01_PROJECT_MAP.md | source artifact map and active research structure |
| docs/02_ACTIVE_LEDGER.md | live state, checklist, assumptions, lessons, replans |
| docs/03_PROJECT_RULES.md | generated PR-1..PR-6 from kernel-project.md |
| prompts/README.md | generated prompt-system guide |
| AGENTS.md | lightweight external-agent instructions |

`AGENTS.md` content profile:

- first-read operational contract for external agents;
- read order for active brief, ledger, project rules, project map, base prompt,
  and role prompt;
- source-integrity and output-location map;
- Codex worktree, coherent-commit, user-change, and user-approved no-ff
  `main` merge guardrails;
- anomaly-detection research claim gates and Python experiment standard;
- prompt-maintenance path back to `prompts/meta/` and `prompts/skills/`.

## Stage 3 - Generate Agent Prompts

Primary output: `prompts/agents-{env}/{AgentName}.md`.

Composition:

```
Agent Prompt = Base[env] + Domain[domain] + RoleContract[agent] + RULE_MANIFEST + AP checks
```

Prompt compression rule: each generated agent prompt contains only role, STOP
conditions, output contract, and JIT references. Full operation bodies stay in
`kernel-ops.md` or `prompts/skills/`.

Codex generation invariants:

- Preserve `prompts/agents-codex/_base.yaml :: codex_runtime`.
- Generated Codex prompts must not imply unilateral `main` merge authority.
- Any Codex prompt that mentions a `main` merge must also require explicit user
  instruction and no-ff merge semantics.
- Coordinator prompts should say "prepare PR" or "merge eligible" unless the
  step is explicitly user-approved `main` integration.

## Stage 4 - Validate

Required checks:

| # | Check | Method |
|---|-------|--------|
| 1 | project rules count | `grep -c '^## PR-' docs/03_PROJECT_RULES.md` equals 6 |
| 2 | agent count | 24 agent files per environment, excluding `_base.yaml` |
| 3 | source preserved | source PDF and extracted text exist and are unmodified by deployment |
| 4 | domain leakage | no project-specific legacy terms outside `kernel-project.md` unless intentional |
| 5 | handoff schema present | `kernel-roles.md` contains HandoffEnvelope |
| 6 | prompt skills present | 6 skill capsules exist |
| 7 | token report present | `token_telemetry_report.json` exists |

## Stage 5 - Register

Update `docs/02_ACTIVE_LEDGER.md` with:

| Field | Value |
|-------|-------|
| phase | DEPLOYED |
| branch | current git branch |
| next_action | first paper-improvement critique task |
| produced | docs, prompts, source text, validation reports |

Emit HAND-02 to ResearchArchitect with `status: SUCCESS` and produced artifact paths.

--------------------------------------------------------
# § WARM_BOOT

Allowed when meta edits do not modify universal axioms or handoff schema:

1. PromptArchitect regenerates affected docs/prompts.
2. PromptAuditor runs leakage and token checks.
3. ConsistencyAuditor signs if cross-domain behavior is unchanged.

If a workflow limitation is discovered during paper work, record it in
`artifacts/M/` before changing kernel files.
