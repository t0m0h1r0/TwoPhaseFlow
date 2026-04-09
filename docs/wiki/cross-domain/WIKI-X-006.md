---
ref_id: WIKI-X-006
title: "Zalesak Disk Role in Balanced-Force CLS: Stress Test, Not Performance Benchmark"
domain: X
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/zalesak_role_in_balanced_force.md
    description: "Full analysis: BF relevance, CLS ε-limit, reinit method unification"
consumers:
  - domain: A
    description: "Paper §11 framing: Zalesak as robustness check, single vortex as primary benchmark"
  - domain: E
    description: "Experiment interpretation: hybrid is default, no method switching"
depends_on:
  - "[[WIKI-T-004]]: Balanced-Force condition (σκδ balancing premise)"
  - "[[WIKI-T-007]]: CLS transport and H_ε(φ) resolution limit"
  - "[[WIKI-T-030]]: Hybrid reinitialization (Comp-Diff + DGR)"
  - "[[WIKI-E-009]]: Shape preservation parameter study (single vortex)"
  - "[[WIKI-E-010]]: Zalesak DCCD study"
  - "[[WIKI-E-011]]: Hybrid reinit discovery (split vs hybrid comparison)"
tags: [Zalesak, balanced-force, CLS, surface-tension, benchmark-role, methodology]
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-09
---

## Key Decision

**Zalesak slotted disk is a stress test, not a performance benchmark, in this research.**

Rationale: The Balanced-Force framework assumes σ≠0. Surface tension smooths
sharp corners on the capillary time scale — the slotted-disk geometry is
physically unrealizable when σ>0. Therefore, shape preservation of sharp
corners is not a relevant performance metric.

## Three Findings

1. **BF precondition test**: Zalesak verifies the advection/reinit subsystem
   does not catastrophically degrade φ. If φ degrades, κ = κ(φ) degrades,
   and BF fails. This is a necessary condition check, not a performance
   evaluation.

2. **CLS ε-limit is geometry-independent**: Both sharp corners (Zalesak)
   and thin filaments (single vortex) hit the same fundamental resolution
   limit: features < ε are unresolvable in H_ε(φ). The geometric
   manifestation differs; the cause (smoothed Heaviside width) is identical.

3. **Single method for generality**: Split reinit favors Zalesak, hybrid
   favors single vortex. Rather than switching by geometry, hybrid is chosen
   as the sole method because it is optimized for the physically relevant
   case (smooth interfaces, σ≠0). Zalesak degradation under hybrid is an
   acknowledged CLS limitation, not a method deficiency.

## Paper Positioning (§11)

| Test | Role | Metric | Method |
|------|------|--------|--------|
| Single vortex | **Primary benchmark** | L₂(φ), area error | hybrid |
| Zalesak | Stress test / robustness | area error, visual | hybrid |

Zalesak results should state: "the method does not break on sharp features"
rather than "the method preserves sharp features."
