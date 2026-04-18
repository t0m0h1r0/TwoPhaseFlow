---
id: WIKI-M-028
title: "Prompt Caching Architecture for Long-Context Agents"
domain: M
status: ACTIVE
superseded_by: null
sources:
  - url: "https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching"
    description: "Anthropic Prompt Caching documentation"
  - github_issue: "anthropics/claude-code#24147"
    description: "Real-world Claude Code token breakdown: cache reads = 99.93% of all tokens"
consumers: []
depends_on: []
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-18
---

# Prompt Caching Architecture for Long-Context Agents

Source: [Zenn article analysis](https://zenn.dev/holy_fox/articles/e0c0bf75fba9e6) — research digest for agent evolution

---

## The Token Distribution Reality

Real-world Claude Code usage (GitHub issue #24147, measured across production sessions):

| Token type | Share |
|------------|-------|
| Cache reads | **99.93%** |
| I/O tokens (input + output) | 0.07% |

Of that 0.07% I/O: output is roughly 15%. So **reducing output tokens by 80% saves only ~0.84% of total cost**.

This falsifies the premise of output-reduction techniques (caveman prompt, brevity constraints). The cost lever is **cache read efficiency**, not output brevity.

---

## Pricing Structure

| Token type | Cost multiplier |
|------------|-----------------|
| Cache read (5-min TTL) | **0.1× base** (90% discount) |
| Cache read (1-hour TTL) | 0.1× base |
| Cache write (5-min TTL) | 1.25× base |
| Cache write (1-hour TTL) | 2.0× base |
| Normal input | 1.0× base |
| Output | varies (higher than input) |

The 1-hour TTL doubles write cost but is amortized across sessions — economical for content accessed multiple times per hour.

---

## Cache Placement Strategy

Content must appear **early in the prompt** (before dynamic content) to be cached effectively. Anthropic supports **up to 4 independent cache breakpoints** per request.

Recommended ordering:

```
[POSITION 1] System prompt / CLAUDE.md instructions     ← cache breakpoint
[POSITION 2] Tool definitions (all tools)               ← cache breakpoint  
[POSITION 3] Large static documents (e.g., codebase)    ← cache breakpoint
[POSITION 4] Conversation history (up to N turns)       ← cache breakpoint
[DYNAMIC]    Current user message + tool results
```

Each breakpoint caches everything up to that point. Dynamic content after the last breakpoint is never cached (and shouldn't be — it changes every turn).

---

## Practical Implications

### What to cache aggressively

- **CLAUDE.md** — read on every session start; cache after first load
- **Tool definitions** — static across all turns in a session
- **Large reference files** — algorithm descriptions, physics equations, long specs
- **Conversation history** — the bulk of context in long sessions

### What not to cache

- Current turn's user message
- Tool call results (dynamic)
- Any content that changes turn-to-turn

### Cost optimization hierarchy (highest ROI first)

1. Ensure static content is positioned before dynamic content → enables cache hits
2. Switch to smaller model for easy tasks (`/model haiku` → ~1/5 cost of Opus)
3. Use subagents to isolate verbose tool output (contains explosion in dynamic tokens)
4. Use `/compact` or `/clear` when conversation history has grown stale
5. Trim CLAUDE.md to reduce cache write cost on session start
6. Use `.claudeignore` to exclude irrelevant files from context

Reducing output tokens via brevity instructions is **last and lowest ROI** — and carries accuracy costs per [[WIKI-M-027]].

---

## Subagent Architecture for Cache Efficiency

Tool output verbosity is a primary driver of dynamic token growth. The recommended pattern:

```
Main agent context:
  [cached] system + tools + static docs
  [dynamic, minimal] task description + subagent results summary

Subagent context:
  [cached] tools + task-specific static docs
  [dynamic] tool call results (isolated here)
```

The subagent absorbs the dynamic explosion; the main agent sees only the distilled result. This keeps the main agent's dynamic section small, maximizing cache hit rate per turn.
