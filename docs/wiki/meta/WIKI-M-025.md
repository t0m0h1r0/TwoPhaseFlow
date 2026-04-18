---
id: WIKI-M-025
title: "Test-Time Compute Scaling via Extended Thinking"
domain: M
status: ACTIVE
superseded_by: null
sources:
  - arxiv: "2408.03314"
    authors: "Snell, Lee, Xu, Kumar (DeepMind, 2024)"
    description: "Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters"
  - url: "https://www.anthropic.com/research/visible-extended-thinking"
    description: "Anthropic Visible Extended Thinking (2025)"
consumers: []
depends_on: []
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-18
---

# Test-Time Compute Scaling via Extended Thinking

Source: [Zenn article analysis](https://zenn.dev/holy_fox/articles/e0c0bf75fba9e6) — research digest for agent evolution

---

## Core Finding

**Test-time compute scaling is more cost-effective than parameter scaling** for improving agent performance on hard tasks. Instead of using a larger model, allocate more inference compute — via parallel sampling, iterative refinement, or extended thinking — to the same model.

Key metric from arXiv:2408.03314:
- Compute-optimal test-time scaling achieves **4x+ efficiency improvement** over best-of-N baselines
- Smaller models can **outperform models 14x their size** when matched on total compute budget
- Strategy: adaptively allocate more compute to harder prompts, less to easy ones

---

## Extended Thinking (Anthropic Implementation)

Claude's `thinking budget` parameter exposes test-time compute scaling directly:

| Metric | Result |
|--------|--------|
| GPQA accuracy (math/science) | Improves logarithmically with thinking tokens |
| Parallel compute scaling | 84.8% GPQA (physics: 96.5%) |
| OSWorld benchmark | Accelerates over multiple interaction steps |
| Prompt injection defense | 74% → 88% with extended thinking |

### Thinking Budget Guidance

```
Low complexity task  → thinking_budget: 1000–5000 tokens
Medium complexity    → thinking_budget: 10000–20000 tokens
Hard reasoning task  → thinking_budget: 50000+ tokens
```

The relationship is **logarithmic** — doubling the budget yields diminishing but consistent returns. Budget allocation is the primary lever for adaptive agent improvement without model changes.

---

## Compute Scaling Strategies

**Serial scaling** — iterative refinement on a single chain:
- Each step builds on the previous result
- Effective for multi-step reasoning, code debugging, mathematical proof

**Parallel scaling** — best-of-N sampling with verifier:
- Generate N independent completions
- Use a reward model / verifier to select the best
- Effective when ground truth can be checked (unit tests, formal verification)

**Hybrid** — compute-optimal allocation:
- Estimate problem difficulty from prompt features
- Allocate serial vs parallel budget accordingly
- Achieves the 4x efficiency gain cited above

---

## Implications for This Project

1. **Hard subagents** (e.g., algorithm derivation, proof checking) should use higher thinking budget — not larger models
2. **Easy subagents** (e.g., file formatting, index updates) should cap thinking budget to minimize cost
3. Parallel sampling + test suite = built-in verifier → enables parallel scaling for code generation tasks
4. The logarithmic relationship means cost scales sublinearly with accuracy gain on hard tasks

---

## Relation to WIKI-M-026

Optimal CoT length ([[WIKI-M-026]]) provides the complementary constraint: more thinking budget is not always better. The two findings together define the operating envelope: allocate more compute on hard tasks, but stop before the inverted-U degradation region.
