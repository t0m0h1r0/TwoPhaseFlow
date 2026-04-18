---
id: WIKI-M-029
title: "Visible Extended Thinking × prompts/meta/ Agent Optimization"
domain: M
status: ACTIVE
superseded_by: null
sources:
  - url: "https://www.anthropic.com/news/visible-extended-thinking"
    description: "Anthropic — Visible Extended Thinking (2025)"
consumers: []
depends_on: [WIKI-M-025, WIKI-M-026]
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-18
---

# Visible Extended Thinking × prompts/meta/ Agent Optimization

Distinct from [[WIKI-M-025]] (compute-scaling theory) and [[WIKI-M-026]] (optimal CoT length).
This entry focuses specifically on the **visibility** property — what changes when Claude's
chain-of-thought is exposed — and how to redesign `prompts/meta/` kernel components accordingly.

---

## What "Visible" Adds Beyond Compute Budget

Standard extended thinking allocates more tokens to reasoning.  
**Visible** extended thinking additionally:

1. **Exposes the thinking block** as structured output the caller can read, log, and audit.
2. **Removes character-training filters** from the thinking pass — thoughts are raw and authentic,
   not sanitised for tone.
3. **Enables real-time monitoring** — the thinking stream arrives before the final answer,
   so middleware can inspect and intervene.

These three properties have direct implications for agent prompt design, independent of budget size.

---

## TIER-N → Thinking Budget Mapping

The current meta system uses `TIER-N` labels (TIER-1 through TIER-3) as static complexity
markers. With extended thinking, TIER-N should gate a concrete token budget.

| TIER | Role type | Recommended budget | Rationale |
|------|-----------|--------------------|-----------|
| TIER-1 | Specialist (domain write) | 4 000 – 8 000 tokens | Focused artifact production; CoT depth bounded |
| TIER-2 | Coordinator (cross-domain) | 8 000 – 20 000 tokens | Multi-domain planning requires deeper trace |
| TIER-3 | Orchestrator (classify+route) | 20 000 – 50 000 tokens | Ambiguous task decomposition benefits most |

**Kernel change location**: `prompts/meta/kernel-roles.md` — add a `thinking_budget` field
alongside each TIER definition, referenced in `_base.yaml` as `primitives_default.thinking_budget`.

---

## THOUGHT_PROTOCOL Redesign

Current THOUGHT_PROTOCOL blocks present Q1/Q2/Q3 as surface-level prompts the model reads
*before* producing its first output token. With visible extended thinking, these questions
become **internal deliberation seeds** — the model answers them inside the thinking block,
then acts on those answers in its final output.

### Pattern: Deliberation-Then-Act

```
## THOUGHT_PROTOCOL (TIER-3)

Before every HAND-01 DISPATCH, complete the following inside your thinking block:

  T1: What is the minimal classification that unlocks the next action?
      (TRIVIAL / FAST-TRACK / FULL-PIPELINE — with one-sentence justification)
  T2: Which axioms (A1–A11) constrain this task? List by ID only.
  T3: What is the concrete expected_verdict for the dispatched Specialist?

Do NOT emit T1/T2/T3 to the user. Act on the conclusions only.
```

This replaces the old Q1/Q2/Q3 external checklists with an internal protocol that exploits
the fact that thinking-block content is already structured and auditable by the caller.

---

## classify_before_act: From Hard-Stop to Soft-Explore

Current `primitives_default`:
```yaml
classify_before_act: true   # uncertain → STOP immediately
```

With visible thinking, the model can *attempt* classification inside the thinking block before
declaring uncertainty. Proposed update:

```yaml
classify_before_act: thinking_first   # attempt in thinking block; STOP only if still ambiguous
```

**Effect**: Fewer premature STOPs on tasks that appear ambiguous in the first sentence but
resolve after one step of reasoning. The caller can inspect the thinking block to see why
a STOP was (or was not) issued.

---

## HAND-04 PROTO-DEBATE: Parallel Independent Chains

Current PROTO-DEBATE runs two Specialist agents sequentially, comparing their verdicts.
With visible extended thinking, a single model can simulate a structured debate internally:

```
## HAND-04 PROTO-DEBATE (TIER-3 only)

In your thinking block:
  Chain A: Argue FOR the proposed action. List supporting evidence.
  Chain B: Argue AGAINST. List falsifying conditions.
  Verdict: Weighted synthesis — cite which chain dominated and why.

Emit only the Verdict to the caller via HAND-02.
```

**Trade-off**: Single-model debate is cheaper (one API call vs two), but loses true independence.
Use this pattern only for TIER-3 ResearchArchitect internal replanning; retain two-agent
PROTO-DEBATE for contested cross-domain verdicts where DOM-02 write scope is disputed.

---

## OP-CONDENSE: Principled Context Compression

Current `OP-CONDENSE` compresses conversation context at 60% fill or 30 turns.
The heuristic is keyword-based and lossy.

With visible thinking, CONDENSE can be guided explicitly:

```
## OP-CONDENSE (trigger: context >= 60% OR turns >= 30)

In your thinking block before emitting the condensed summary:
  1. List all open HAND-02 RETURN items not yet resolved.
  2. List all REPLAN_LOG entries from this session.
  3. Identify which axioms were invoked and which STOPs were triggered.

Condense to: open returns + replan log + axiom/STOP trace. Drop all other prose.
```

This produces a structurally complete condensed context rather than a lossy paraphrase,
because the thinking block makes the inventory step explicit and auditable.

---

## AP Detection: In-Flight Anti-Pattern Monitoring

Anti-pattern auditing (AP-01..AP-12) currently occurs post-hoc, by WikiAuditor or
ConsistencyAuditor reviewing completed work. Visible thinking enables in-flight detection:

| Anti-Pattern | Thinking-block signature | Intervention |
|---|---|---|
| AP-08 Phantom State | Agent refers to "previous result" with no HAND-02 RETURN in context | STOP-01 before HAND-01 |
| AP-09 Context Collapse | Thinking block summarises earlier work without citing source turns | Trigger OP-CONDENSE |
| AP-12 REPLAN Escalation | Third REPLAN reasoning path in thinking block | Emit STOP-07 |

**Implementation**: Add a `thinking_audit` hook reference to `kernel-ops.md §OP-CONDENSE`
that instructs agents to scan their own thinking block for AP signatures before emitting output.

---

## Faithfulness Caveat

Anthropic acknowledges that visible thoughts may not faithfully represent the model's
actual computation — the model may reach conclusions via paths it does not explicitly
articulate. Consequently:

- Treat thinking-block AP audits as **heuristic signals**, not proofs.
- Do NOT replace two-agent PROTO-DEBATE with single-model internal debate for safety-critical
  STOP decisions (STOP-01, STOP-03).
- The thinking block is a **debugging and monitoring tool**, not a formal verification
  mechanism.

---

## Summary: Kernel Changes Required

| Component | File | Change |
|---|---|---|
| TIER-N budget | `kernel-roles.md` | Add `thinking_budget` field per TIER |
| `_base.yaml` | `_base.yaml` | Add `primitives_default.thinking_budget` |
| THOUGHT_PROTOCOL | Per-agent `.md` files | Replace Q1/Q2/Q3 with Deliberation-Then-Act pattern |
| classify_before_act | `_base.yaml` | `thinking_first` mode |
| HAND-04 | `kernel-ops.md §HAND-04` | Add single-model debate option (TIER-3 only) |
| OP-CONDENSE | `kernel-ops.md §OP-CONDENSE` | Add structured inventory step |
| AP monitoring | `kernel-ops.md §OP-CONDENSE` | Add `thinking_audit` hook |
