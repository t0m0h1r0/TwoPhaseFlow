---
id: WIKI-M-008
title: "Agent Meta System: SLP/RAP/SDP Protocols + Per-Environment Prompt Generation"
status: ACTIVE
created: 2026-04-15
depends_on: [WIKI-M-003, WIKI-M-006, WIKI-M-007]
---

# Agent Meta System: SLP/RAP/SDP Protocols + Per-Environment Prompts

## Motivation

Two additions deployed 2026-04-14 address **operational efficiency** (not
correctness, which was the focus of v5.2 hardening [[WIKI-M-003]]):

1. **Three new protocols** — SLP-01, RAP-01, SDP-01 — reduce token cost,
   prevent unbounded retry, and streamline deployment.
2. **Per-environment agent prompts** — generate Claude-optimized and
   Codex-optimized variants from the same meta source.

---

## Addition 1 — Three New Protocols (commit 72e1cb8)

### SLP-01: Structured Logging Protocol

Token-efficient thought format. Replaces verbose natural-language reasoning
with key-value shorthand in `THOUGHT:` blocks:

```
THOUGHT:
  @GOAL: "CHK-130"
  @RESOURCES: "Attempt 1/3 | Budget: 2h"
  @REF: "[PR-5, §8c]"
  @LOGIC: "condition => inference"
  @ACT: "EDIT viscous.py"
```

**Why:** Free-form reasoning consumed 30–40% of output tokens without
structured traceability. SLP-01 forces telegraphic style while preserving
the reasoning chain for audit.

### RAP-01: Retry Attenuation Protocol

Bounded retry with exponential backoff:
- MAX_ATTEMPTS = 3 per operation
- On failure: diagnose → adjust → retry (not blind retry)
- After 3rd failure: STOP + escalate to user

**Why:** Without RAP-01, agents could loop indefinitely on transient failures
(e.g., compile errors, test flakes), burning the entire context window on
retries of the same operation.

### SDP-01: State Deployment Protocol

Warm-state initialization for session continuation:
1. Read `docs/02_ACTIVE_LEDGER.md` § ACTIVE STATE (last_decision row)
2. Identify open CHK and current phase/branch
3. Skip already-closed CHKs without re-reading their full history
4. Resume from the last `next_action` pointer

**Why:** Cold-start sessions re-read the full ledger (~30k tokens) to orient.
SDP-01 provides a fast path that loads only the tail state, reducing session
init from ~30k to ~3k tokens.

---

## Addition 2 — Per-Environment Agent Prompts (commit c1fdbe3)

### Problem

A single agent prompt must work across Claude (1M context, strong reasoning)
and Codex (128k context, code-first output). The same prompt was suboptimal
for both: too verbose for Codex, insufficiently structured for Claude.

### Solution: EnvMetaBootstrapper dual generation

```
prompts/
├── agents-claude/     # 25 agents, full Q1 YAML + THOUGHT_PROTOCOL (~2500 tok each)
│   ├── _base.yaml     # Shared axioms (A1–A11), primitives, rules
│   ├── ResearchArchitect.md
│   ├── CodeArchitect.md
│   └── ...
├── agents-codex/      # 25 agents, compressed diff-first variant (~1500 tok each)
│   ├── _base.yaml
│   └── ...
└── meta/              # Source meta files (10 files, universal)
```

### Key differences

| Aspect | Claude variant | Codex variant |
|--------|---------------|---------------|
| Token budget | ~2500/agent | ~1500/agent |
| Thought format | SLP-01 full THOUGHT block | Inline `// THOUGHT:` comments |
| Output style | Structured YAML + prose | Diff-first, minimal prose |
| Self-check | AP-01..AP-10 table | AP-01..AP-05 subset (high-severity only) |
| Procedure | Step-by-step with stop conditions | Compressed checklist |

### Generation flow

```
meta/*.md  →  EnvMetaBootstrapper  →  agents-claude/*.md
                                   →  agents-codex/*.md
```

The old `prompts/agents/` directory (33 unified files) was removed. All path
references across `meta-*.md`, `CLAUDE.md`, `README.md`, and `docs/` updated.

### Invariants (both environments)

- Inherit `_base.yaml` (axioms A1–A11, primitives, anti-patterns)
- Same scope boundaries (reads/writes/forbidden territories)
- Same STOP conditions
- Same HAND-01/HAND-02 dispatch protocol

---

## Source

- `72e1cb8` (2026-04-14): SLP-01, RAP-01, SDP-01 across 6 meta files
- `c1fdbe3` (2026-04-14): 25×2 per-environment agent prompt generation
- `prompts/meta/meta-core.md` (SLP-01 reference)
- `prompts/meta/meta-antipatterns.md` (RAP-01 retry attenuation)
- `prompts/meta/meta-deploy.md` (SDP-01 warm-state init)

## Related entries

- [[WIKI-M-003]] v5.2 LLM-Specific Hardening — AP-09/10 that SLP-01 helps mitigate
- [[WIKI-M-006]] Micro-Agent Architecture — SIGNAL/DDA protocols that coexist with SLP/RAP/SDP
- [[WIKI-M-007]] K-Domain — meta-project profile swap that per-env generation extends
