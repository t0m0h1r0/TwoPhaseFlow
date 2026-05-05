---
ref_id: WIKI-M-030
title: "Meta-Prompt Evolution Needs Telemetry, Skills, and Tool-Trust Gates"
domain: meta
status: ACTIVE
superseded_by: null
tags: [meta_prompt, telemetry, skill_capsule, tool_trust, generated_prompts]
sources:
  - path: artifacts/M/review_CHK-RA-META-V8-001.md
    description: "ResearchArchitect meta-prompt evolution review"
  - path: artifacts/M/review_CHK-RA-META-V8-002.md
    description: "EnvMetaBootstrapper Codex target review"
depends_on:
  - "[[WIKI-M-023]]"
  - "[[WIKI-M-028]]"
  - "[[WIKI-M-029]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Meta-Prompt Evolution Gates

## Knowledge Card

Prompt evolution is validated by explicit generation and telemetry gates, not
by hand-editing derived prompts.  The v8 artifact set introduced three reusable
guardrails:

- token telemetry and duplicate-rule detection;
- Skill Capsules as a JIT procedural layer between operation IDs and full
  kernel specs;
- tool/web/MCP outputs marked as untrusted data unless promoted by local SSoT.

## Consequences

- Regenerated role prompts must preserve primitive-diff inheritance from the
  base prompt source.
- Validation should count required primitives, antipatterns, schemas, skills,
  and stale-version residues.
- `AGENTS.md` is a lightweight repo-facing derived surface, not the prompt SSoT.
- Multi-agent use should be restricted to independent breadth by effort policy.

## Paper-Derived Rule

For meta-prompt changes, validate the source-to-derived generation path and
tool-trust gates before trusting generated role files.
