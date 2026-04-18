---
id: WIKI-M-026
title: "Optimal CoT Length — Inverted U-Curve and Short-m@k"
domain: M
status: ACTIVE
superseded_by: null
sources:
  - arxiv: "2502.07266"
    authors: "Wu, Wang, Ye, Du, Jegelka, Wang"
    description: "When More is Less: Understanding Chain-of-Thought Length in LLMs"
  - arxiv: "2505.17813"
    authors: "Hassid, Synnaeve, Adi, Schwartz"
    description: "Don't Overthink it. Preferring Shorter Thinking Chains for Improved LLM Reasoning"
  - arxiv: "2402.12875"
    authors: "Li, Liu, Zhou, Ma (ICLR 2024)"
    description: "Chain of Thought Empowers Transformers to Solve Inherently Serial Problems"
consumers: []
depends_on:
  - "[[WIKI-M-025]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-18
---

# Optimal CoT Length — Inverted U-Curve and Short-m@k

Source: [Zenn article analysis](https://zenn.dev/holy_fox/articles/e0c0bf75fba9e6) — research digest for agent evolution

---

## Core Finding: The Inverted U-Curve

Task accuracy **does not monotonically increase** with chain-of-thought length. It follows an inverted U-shape:

```
Accuracy
   ↑
   |        ★ optimal
   |      /   \
   |    /       \
   |  /           \  ← overthinking degrades
   | /               \
   +─────────────────── CoT length
   short            long
```

(arXiv:2502.07266)

Rules:
- Optimal length **increases** with task difficulty
- Optimal length **decreases** with model capability (stronger models need less CoT)
- During RL training, models naturally converge toward shorter CoTs as accuracy improves ("simplicity bias" — correct solutions are discovered and reinforced at shorter lengths)

---

## Why CoT Works at All: Theoretical Basis

arXiv:2402.12875 (ICLR 2024) provides a formal explanation:

- Without CoT: constant-depth transformers can only solve **AC⁰ problems** (highly parallelizable, low-depth circuit complexity)
- With T reasoning steps: the same model can solve problems requiring **boolean circuits of size T**
- CoT enables **serial computation** in an architecture that is inherently parallel

This sets a principled upper bound: CoT steps beyond what the task's serial complexity requires yield no theoretical benefit, and empirically cause the inverted-U degradation.

---

## Short-m@k: Practical Parallel Sampling Strategy

arXiv:2505.17813 proposes **short-m@k**: generate k completions in parallel, stop after m finish, apply majority voting.

Key results:

| Method | Accuracy | Thinking tokens |
|--------|----------|-----------------|
| Majority vote (all k) | Baseline | 100% |
| short-1@k | ≈ Majority vote | **−40%** |
| short-3@k | **> Majority vote** | −33%, **1.3x faster** |

Insight: **shorter chains within the same question are up to 34.5% more accurate** than the longest chain sampled. The longest reasoning chain is often overthinking, not the best answer.

---

## Practical Implications for Agent Design

1. **Cap thinking budgets** — do not set thinking_budget to maximum by default. Match to estimated task difficulty (see [[WIKI-M-025]] for budget guidance).
2. **Parallel subagents + majority vote** is more robust than single long-reasoning chains for ambiguous tasks.
3. **Stopping early** (short-m@k pattern) saves tokens without sacrificing accuracy — implement via checking intermediate outputs when possible.
4. **Training note**: if fine-tuning agents, train on optimally-lengthed demonstrations, not the longest available. Reward shaping that penalizes excessive length improves efficiency.

---

## Anti-Pattern

**Forcing maximum CoT length** (e.g., "think step by step as thoroughly as possible") actively degrades performance on tasks where the model is capable. Match reasoning depth to task, not to anxiety about missing steps.

This is the empirical refutation of "more thinking = always better" — which complements [[WIKI-M-025]]'s finding that test-time compute is valuable up to a task-appropriate ceiling.
