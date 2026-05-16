# CHK-RA-AGENT-WIKI-PROMPT-001: Wiki-Derived Agent Prompt Enhancement

## Scope

User request: extract useful agent-enhancement knowledge from the wiki, decide how to incorporate it into deployed agents, define the metaprompt wording needed for deployment, review prompt bloat/contradiction/efficiency risks, strictly review whether generated prompts would remain efficient, and update the metaprompt.

Classification: PROMPT-EVOLUTION with K-domain retrieval input. Chosen execution mode: direct, because the write territory is `prompts/meta/` plus artifact/ledger bookkeeping and there is no dependency DAG blocking the next step. Verification is recorded as PromptAuditor/ConsistencyAuditor-style checks in this artifact.

## Wiki Evidence Used

| Wiki source | Extracted lesson |
|---|---|
| `docs/wiki/meta/WIKI-M-011.md` | Anti-patterns must be selectively injected by tier; self-visible failure modes need detect/mitigate text. |
| `docs/wiki/meta/WIKI-M-016.md` | Token budget, JIT rule loading, external memory, and tool delegation are architectural constraints, not style preferences. |
| `docs/wiki/meta/WIKI-M-013.md` | Compression succeeds when bookkeeping is environment-injected and duplicated operation bodies are replaced by references. |
| `docs/wiki/meta/WIKI-M-014.md` and `docs/wiki/meta/WIKI-M-022.md` | EnvMetaBootstrapper is the compiler; deployment needs explicit parse, generate, optimize, and audit stages. |
| `docs/wiki/meta/WIKI-M-023.md` | Context collapse requires active condensation/JIT behavior rather than relying on long prompt memory. |
| `docs/wiki/meta/WIKI-M-031.md` | Review artifacts should close finding, fix, validation, and residual risk. |
| `docs/wiki/meta/WIKI-M-032.md` | Wiki inventory should start from active retrieval gates and use layered evidence passes, not full linear reading. |
| `docs/wiki/cross-domain/WIKI-X-041.md` | Active retrieval maps prevent old design memos from being interpreted as current policy. |
| `docs/wiki/meta/WIKI-M-018.md` | Prompt, wiki, audit, and routing domains have distinct authority; prompt deployment must preserve these boundaries. |

## Extracted Agent-Enhancement Knowledge

1. Wiki knowledge should enter generated agents as source-traced behavior deltas, not copied prose.
2. Active retrieval maps are the safest front door; `REFERENCE` and `SUPERSEDED` cards need curation-aware handling.
3. Prompt bloat is not neutral: low-ROI reminders can reduce compliance by consuming reasoning budget.
4. Long procedural knowledge belongs behind RULE_MANIFEST, SkillID, or on-demand wiki pointers.
5. Prompt auditing must check not only generic token cost, but also stale wiki injection and missing source refs.
6. Negative knowledge is useful, but only when explicitly marked as historical or rejected-route context.

## Metaprompt Incorporation Decision

Best insertion point: `kernel-deploy.md`, because EnvMetaBootstrapper is the compiler from metaprompt sources to generated agents. The new Stage 1b distills `docs/wiki/` into `WikiKnowledgePacket` records before Stage 3 prompt generation.

Best failure-mode encoding: `kernel-antipatterns.md`, because stale or verbose wiki injection is a recurring LLM/prompt failure mode. AP-17 makes PromptArchitect and PromptAuditor reject full wiki prose, stale active-policy claims, and wiki-derived rules without source refs.

Best role-contract update: `kernel-roles.md`, because PromptArchitect must run the packet distillation and PromptAuditor must audit Q3-14/Q3-15 plus AP-17.

## Authoring Pattern For Future Metaprompts

Use this shape when adding wiki-derived knowledge:

```yaml
wiki_packet:
  wiki_id: WIKI-...
  status: ACTIVE
  target_roles: [...]
  behavior_delta: "one enforceable behavior"
  injection_mode: on_demand
  source_refs: [...]
  token_budget: 50
```

Avoid this shape:

```text
Paste the whole wiki section into every generated prompt because it might be useful.
```

The packet form preserves traceability while keeping generated prompts compact.

## Strict Prompt Review

Review questions applied to the metaprompt change:

| Check | Verdict |
|---|---|
| Does it duplicate existing operation bodies? | PASS: new text points to Stage 1b, RULE_MANIFEST, SkillID, or on-demand refs. |
| Does it weaken A1-A11, STOP, or domain authority? | PASS: no immutable axiom text changed; packets must fail on conflict. |
| Does it permit stale wiki cards as current policy? | PASS: SUPERSEDED cards are rejected for static prompt text unless marked negative knowledge. |
| Does it make generated prompts larger by default? | PASS with guard: static wiki budget is capped at 150 tokens; long content becomes on-demand. |
| Does it add an auditable deployment artifact? | PASS: `wiki_knowledge_injection_report.json` is required when `docs/wiki/` exists. |
| Does PromptAuditor have explicit checks? | PASS: Q3-14/Q3-15 and AP-17 cover source refs, status, and bloat. |

Residual risk: generated project-local prompts and skill capsules were not regenerated in this task. The source metaprompt now requires that future deployments generate and audit `wiki_knowledge_injection_report.json`.

## Files Changed

- `prompts/meta/kernel-deploy.md`: added Stage 1b `WikiKnowledgePacket` distillation, Stage 3 wiki packet references, Q3-14/Q3-15, `wiki_static_tokens`, and AP-17 failure routing.
- `prompts/meta/kernel-antipatterns.md`: added AP-17 Wiki Over-Injection.
- `prompts/meta/kernel-roles.md`: updated PromptArchitect and PromptAuditor contracts for wiki packet distillation and audit.

## Validation Plan

- `git diff --check` in `prompts/meta/`.
- Targeted scans for Q3 count, AP-17, `wiki_static_tokens`, and `WikiKnowledgePacket`.
- Parent repo `git diff --check`.
