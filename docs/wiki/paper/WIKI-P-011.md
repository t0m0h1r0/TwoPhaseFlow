---
ref_id: WIKI-P-011
title: "Optimizing Multi-Agent Kernel Prompts with Visible Extended Thinking"
domain: M
status: ACTIVE
superseded_by: null
sources:
  - url: "https://www.anthropic.com/news/visible-extended-thinking"
    description: "Anthropic — Visible Extended Thinking (2025)"
depends_on:
  - "[[WIKI-M-025]]"
  - "[[WIKI-M-026]]"
  - "[[WIKI-M-029]]"
compiled_by: ResearchArchitect
compiled_at: 2026-04-18
---

# Optimizing Multi-Agent Kernel Prompts with Visible Extended Thinking

## Abstract

We investigate how Anthropic's Visible Extended Thinking feature — which exposes Claude's
chain-of-thought as structured output — can be applied to improve the efficiency of a
kernel-driven multi-agent system. Six concrete optimizations are proposed targeting task
classification, self-verification, debate protocols, context condensation, and anti-pattern
detection. The primary insight is that *visibility* (the exposure of reasoning, not merely
its depth) unlocks prompt patterns that are impossible or unreliable when chain-of-thought
is hidden. All proposed changes are localized to `prompts/meta/kernel-*.md` and `_base.yaml`,
leaving agent `.md` files largely unchanged.

---

## 1. Introduction

The `prompts/meta/` kernel system governs 23 specialized agents through a set of shared
axioms (A1–A11), anti-pattern codes (AP-01..AP-12), handoff operators (HAND-01..HAND-04),
and a behavioral primitive layer. Agents are classified by orchestration tier:
TIER-1 (Specialists), TIER-2 (Coordinators), TIER-3 (Orchestrators).

The current system has three known friction points:

1. **THOUGHT_PROTOCOL rigidity** — Q1/Q2/Q3 self-checks are static surface prompts that the
   model processes linearly without explicit deliberation structure.
2. **Early STOP on ambiguous tasks** — `classify_before_act: true` halts on the first
   uncertainty rather than attempting resolution via reasoning.
3. **Post-hoc anti-pattern detection** — AP-01..AP-12 violations are caught by auditor agents
   after work is complete, not during execution.

Visible Extended Thinking addresses all three by making Claude's reasoning process an
inspectable, auditable intermediate artifact. This paper describes how.

---

## 2. System Overview

The kernel system operates as follows. ResearchArchitect (TIER-3) receives a task, classifies
it (TRIVIAL / FAST-TRACK / FULL-PIPELINE), and dispatches via HAND-01 to the appropriate
Coordinator or Specialist. Specialists perform domain writes and return results via HAND-02.
Context is compressed by OP-CONDENSE at 60% fill or 30 turns. Contested verdicts escalate to
HAND-04 PROTO-DEBATE.

Each agent carries a THOUGHT_PROTOCOL block with tier-specific Q-checks and a RULE_MANIFEST
that references kernel sections as single source of truth. Agents are regenerated from kernel
files via `kernel-deploy.md`; individual `.md` files are generated artifacts.

The relevant kernel files for this study:

| File | Role |
|---|---|
| `kernel-roles.md` | TIER definitions, agent responsibilities |
| `kernel-ops.md` | HAND-01..04, OP-CONDENSE, GIT ops |
| `kernel-workflow.md` | Pipeline modes, STOP-RECOVER MATRIX |
| `_base.yaml` | `primitives_default`, feature flags, budget defaults |

---

## 3. Method: Six Optimizations

### O1 — TIER-N Thinking Budget Mapping

Map TIER labels to concrete `thinking_budget` values in `kernel-roles.md`.
TIER-1: 4k–8k tokens; TIER-2: 8k–20k tokens; TIER-3: 20k–50k tokens.
Add `primitives_default.thinking_budget` to `_base.yaml` with per-TIER defaults.

*Rationale*: The relationship between thinking tokens and accuracy is logarithmic (WIKI-M-025).
Tying budgets to TIER ensures cost-proportionality: Specialists spend less, Orchestrators more.

### O2 — Deliberation-Then-Act THOUGHT_PROTOCOL

Replace Q1/Q2/Q3 checklist items with a `Deliberation-Then-Act` pattern:
the model is instructed to answer the questions *inside the thinking block* and act only on
the conclusions, not emit the deliberation as output.

```
T1: Classify (TRIVIAL / FAST-TRACK / FULL-PIPELINE) with one-sentence justification.
T2: List constraining axioms by ID (A1–A11) only.
T3: State expected_verdict for the dispatched agent.
Do NOT emit T1/T2/T3 to the user.
```

*Rationale*: Hidden Q-checks are processed linearly as text. Thinking-block Q-checks
are processed as deliberative reasoning, improving classification accuracy on edge cases.

### O3 — `thinking_first` Classification Mode

Change `classify_before_act` from `true` (hard stop on ambiguity) to `thinking_first`
(attempt classification in thinking block; STOP only if still ambiguous after deliberation).

*Effect*: Reduces premature STOPs on tasks that appear ambiguous in the first sentence but
resolve after one reasoning step. Caller can inspect the thinking block to audit the
classification attempt.

### O4 — Single-Model PROTO-DEBATE for TIER-3

Add a single-model internal debate option to `kernel-ops.md §HAND-04`, restricted to TIER-3
ResearchArchitect replanning decisions:

```
Chain A: Argue FOR the proposed action.
Chain B: Argue AGAINST.
Verdict: Weighted synthesis — cite which chain dominated.
Emit Verdict only.
```

Two-agent PROTO-DEBATE is retained for cross-domain write disputes (DOM-02 scope conflicts)
where true independence is required.

*Trade-off*: Single-model debate is cheaper (one call vs two) but sacrifices independence.
Use only for internal replanning, not for safety-critical STOP decisions.

### O5 — Structured OP-CONDENSE Inventory

Prepend a structured inventory step to OP-CONDENSE:

```
In thinking block before condensing:
1. List all open HAND-02 RETURN items.
2. List all REPLAN_LOG entries from this session.
3. List axioms invoked and STOPs triggered.
Condense to: open returns + replan log + axiom/STOP trace only.
```

*Effect*: Context compression becomes principled rather than keyword-lossy. The inventory
is auditable because it appears in the thinking block before the condensed output.

### O6 — In-Flight AP Detection via Thinking Audit

Add a `thinking_audit` hook to `kernel-ops.md §OP-CONDENSE` instructing agents to scan
their own thinking block for AP signatures before emitting any output:

| AP Code | Thinking-block signature |
|---|---|
| AP-08 Phantom State | Reference to "previous result" with no HAND-02 in context |
| AP-09 Context Collapse | Summary of earlier work without source-turn citation |
| AP-12 REPLAN Escalation | Third REPLAN reasoning path present |

Detected APs trigger the corresponding STOP code before the output reaches the caller.

---

## 4. Discussion

### Faithfulness Limitation

Anthropic acknowledges that visible thinking may not faithfully represent the model's
actual computation. The thinking block should be treated as a heuristic debugging signal,
not a formal proof of correct reasoning. Consequently:

- AP detection via thinking audit is probabilistic, not guaranteed.
- Safety-critical STOP decisions (STOP-01, STOP-03) must not be delegated to single-model
  debate alone.
- The `thinking_first` classification mode should retain a hard STOP for cases where
  deliberation genuinely fails to resolve ambiguity (not merely simplifies it).

### Cost-Latency Trade-Off

Visible extended thinking increases per-call latency proportionally to budget size.
The logarithmic accuracy curve (WIKI-M-025) and the inverted-U CoT degradation
(WIKI-M-026) together define the operating envelope:

- TIER-1 Specialists: cap at 8k tokens (accuracy gain plateaus; task is concrete)
- TIER-3 Orchestrators: up to 50k tokens for classification on novel task types

### Future Work

1. **Parallel thought research** (Anthropic, not yet deployed): when available, use
   N independent thinking chains for HAND-04 PROTO-DEBATE to restore true independence
   while avoiding a second API call.
2. **Adaptive budget**: estimate task difficulty from prompt features and dynamically
   allocate within TIER budget bands (per WIKI-M-025 compute-optimal scaling).
3. **Thinking-block logging**: persist thinking blocks alongside HAND-02 RETURN payloads
   as an audit trail for post-hoc AP analysis.

---

## 5. References

1. Anthropic. *Visible Extended Thinking* (2025).  
   https://www.anthropic.com/news/visible-extended-thinking

2. Snell, Lee, Xu, Kumar (DeepMind, 2024). *Scaling LLM Test-Time Compute Optimally
   can be More Effective than Scaling Model Parameters*. arXiv:2408.03314.
   → Discussed in [[WIKI-M-025]].

3. Project internal: [[WIKI-M-026]] — Optimal CoT Length (Inverted U-Curve and Short-m@k).

4. Project internal: [[WIKI-M-029]] — Detailed kernel change specifications for O1–O6.
