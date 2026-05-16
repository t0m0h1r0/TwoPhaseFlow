---
ref_id: WIKI-M-033
title: "Meta-Prompt Evolution Uses Wiki Packets and Prompt Audit Gates"
domain: meta
status: ACTIVE
superseded_by: null
tags:
  - metaprompt
  - agent_evolution
  - wiki_packets
  - prompt_audit
  - token_budget
  - deployment
sources:
  - path: artifacts/M/agent_wiki_prompt_enhancement_CHK-RA-AGENT-WIKI-PROMPT-001.md
    description: "Review artifact that extracted wiki-derived agent enhancement lessons and audited the metaprompt update"
  - path: prompts/meta/kernel-deploy.md
    description: "Deployment workflow updated with WikiKnowledgePacket distillation and prompt audit gates"
  - path: prompts/meta/kernel-antipatterns.md
    description: "Anti-pattern library updated with AP-17 Wiki Over-Injection"
  - path: prompts/meta/kernel-roles.md
    description: "PromptArchitect and PromptAuditor role contracts updated for wiki-packet distillation and audit"
  - path: docs/wiki/meta/WIKI-M-011.md
    description: "Anti-pattern catalogue practice for selective detect/mitigate injection"
  - path: docs/wiki/meta/WIKI-M-016.md
    description: "LLM aptitude, token budget, JIT rule loading, and external-memory principles"
  - path: docs/wiki/meta/WIKI-M-032.md
    description: "Layered wiki inventory practice used to avoid broad full-card preloading"
depends_on:
  - "[[WIKI-M-011]]"
  - "[[WIKI-M-013]]"
  - "[[WIKI-M-014]]"
  - "[[WIKI-M-016]]"
  - "[[WIKI-M-018]]"
  - "[[WIKI-M-022]]"
  - "[[WIKI-M-031]]"
  - "[[WIKI-M-032]]"
  - "[[WIKI-X-041]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Meta-Prompt Evolution Uses Wiki Packets and Prompt Audit Gates

## Purpose

Meta-prompt and agent evolution should not copy accumulated wiki knowledge directly into generated prompts. A good evolution pass converts validated wiki knowledge into source-traced, role-relevant behavior deltas, then lets the deployment pipeline decide whether each delta is inline, on-demand, a SkillID trigger, or rejected.

## Core Practice

1. Start from a closed review artifact.
   - Use artifacts that record scope, finding, fix, validation, and residual risk.
   - Do not promote an in-context insight into a kernel rule until it has a source path and an explicit behavior change.

2. Distill wiki knowledge into packets.
   - Each packet needs a `wiki_id`, source refs, target roles, one behavior delta, injection mode, token budget, and conflict check.
   - The behavior delta must say what an agent will do differently, not restate the wiki prose.

3. Choose the insertion layer by behavior.
   - Deployment behavior belongs in `kernel-deploy.md`.
   - Recurrent failure modes belong in `kernel-antipatterns.md`.
   - Role responsibility belongs in `kernel-roles.md`.
   - Long procedures belong in a SkillID or on-demand reference.
   - Project-local constraints belong in `kernel-project.md`, not shared kernel rules.

4. Gate stale knowledge before injection.
   - `ACTIVE` retrieval-front cards can define current behavior.
   - `REFERENCE` cards can contribute provenance or negative knowledge only when curated.
   - `SUPERSEDED` cards must not become static prompt policy unless the successor is named and the packet is marked as negative knowledge.

5. Treat prompt bloat as a correctness risk.
   - Prefer RULE_MANIFEST, SkillID, and wiki on-demand refs over static text.
   - Inline only short behavior that is needed every turn.
   - Record `wiki_static_tokens` with normal token telemetry.

6. Audit the generated prompt, not only the kernel diff.
   - PromptAuditor should check whether wiki-derived rules cite active sources, whether stale cards were promoted, and whether full wiki prose should have been an on-demand pointer.
   - A metaprompt change is incomplete if future deployment cannot produce a `wiki_knowledge_injection_report.json` or an explicit waiver.

7. Keep source and derived artifacts separate.
   - Edit `prompts/meta/` for rules.
   - Regenerate `prompts/agents-*`, skills, docs, and templates only through the deployment workflow.
   - Do not patch generated agents by hand to encode a new rule.

## Packet Template

```yaml
wiki_packet:
  wiki_id: WIKI-...
  status: ACTIVE
  source_refs:
    - docs/wiki/...
  target_roles:
    - PromptArchitect
  behavior_delta: "one enforceable action or STOP trigger"
  injection_mode: inline | rule_manifest | skill_ref | on_demand | reject
  token_budget: 50
  conflict_check: PASS
```

## Review Checklist

- Does the candidate knowledge have an artifact or wiki source, not only session memory?
- Is there exactly one behavior delta per packet?
- Is the target role explicit?
- Is the packet current policy, negative knowledge, or provenance?
- Is the insertion layer the narrowest one that changes behavior?
- Can long text be replaced by a SkillID, RULE_MANIFEST entry, or wiki on-demand pointer?
- Does token telemetry count wiki-derived static text?
- Does PromptAuditor have a concrete Q3 or AP check that would catch misuse?
- Are generated prompts left untouched until the deployment workflow runs?

## Anti-Patterns

- Copying a full wiki section into every agent prompt.
- Treating old `REFERENCE` context as active deployment policy.
- Adding another reminder sentence when a SkillID or on-demand pointer would preserve behavior.
- Encoding project-local constraints in the shared kernel.
- Updating generated agents directly instead of changing the metaprompt source.
- Declaring the metaprompt update complete without a prompt-audit criterion.

## Operational Consequence

Future meta-prompt evolution should preserve the chain:

```text
wiki/artifact evidence -> WikiKnowledgePacket -> kernel insertion layer -> deployment report -> PromptAuditor gate
```

This keeps agent evolution traceable without making prompts heavy enough to reduce compliance.
