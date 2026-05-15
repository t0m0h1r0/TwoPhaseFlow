---
ref_id: WIKI-X-051
title: "Theory-First Problem RCA and Countermeasure Protocol"
domain: cross-domain
status: ACTIVE
tags: [rca, theory_first, root_cause, countermeasure_design, falsification, shortcut_rejection]
sources:
  - description: "User directive, 2026-05-13: problem solving and countermeasures must be based on physics/mathematics, many hypotheses, verification, and no ad hoc fixes"
  - description: "User directive, 2026-05-14: always recall this protocol during troubleshooting; reset to first-principles theory when a path may be a dead end"
  - description: "User directive, 2026-05-15: when a real problem occurs, always zero-base the issue, return to physics/mathematics, generate and verify many hypotheses, then design and test multiple theory-based countermeasures before implementation"
  - path: docs/wiki/cross-domain/WIKI-X-043.md
    description: "RCA artifacts falsify shortcuts before authorizing fixes"
  - path: docs/wiki/cross-domain/WIKI-X-045.md
    description: "Rejected shortcuts preserve the theory boundary"
  - path: docs/wiki/cross-domain/WIKI-X-050.md
    description: "Nonuniform metrics and interface-tracking rebuilds are priority implementation/review gates"
depends_on:
  - "[[WIKI-X-043]]"
  - "[[WIKI-X-045]]"
  - "[[WIKI-X-050]]"
consumers:
  - domain: code
    usage: "Default protocol before changing solver, GPU, YAML, or diagnostics after a failure"
  - domain: experiment
    usage: "Default protocol for classifying failed runs and selecting probes"
  - domain: theory
    usage: "Ensures fixes restore named equations, invariants, or theorem preconditions"
compiled_by: ResearchArchitect
compiled_at: 2026-05-15
---

# Theory-First Problem RCA and Countermeasure Protocol

## Mandatory Incident Recall

When a real problem occurs, recall this card before touching code, YAML,
parameters, tolerances, solver families, GPU routes, diagnostics, or plots.

The mandatory sequence is:

1. Reset to zero base: list the observed facts, unknowns, assumptions, and the
   governing physical/mathematical contracts from first principles.
2. Diagnose from theory: generate as many plausible causes as needed from
   physics and mathematics, then identify the root cause by falsification.
3. Only after the cause is identified, design remedies from the same theory:
   generate multiple countermeasures, compare them by contract restoration, and
   test the selected remedy before implementation is accepted.
4. Treat ad hoc symptom control as forbidden: no tolerance weakening, extra
   iterations without proof, damping, smoothing, micro-offsets, solver-family
   substitutions, hidden fallbacks, plot-only fixes, or physical retuning.

The exact recall prompt is:

> ゼロベースで問題点を整理して、理論の原点に戻って検討して。
> 問題の原因を物理学・数学の理論に基づいて仮説考案し推理してください。
> 仮説をできるだけ多数創出し、それを検証することで問題特定を行なってください。
> 問題特定できたら、その問題への対策をを物理学・数学の理論に基づいて立案し推理してください。
> 対策案をできるだけ多数創出し、それを検証することで実装を行なってください。
> どちらも理論を絶対視し、小手先の技で修正するのは絶対に禁止です。

## Canonical Policy

When a problem occurs, seek the shortest path to the real cause by reasoning
from physics and mathematics first.  Generate as many plausible hypotheses as
needed, test them, and identify the cause by falsification.  Do not treat
symptom relief as a fix.

This protocol is mandatory recall during troubleshooting.  If the investigation
starts to follow implementation details without a named equation, conservation
law, compatibility condition, energy identity, or discrete operator contract,
stop and rebuild the argument from first principles before editing more code.

When designing countermeasures, again start from the governing physical and
mathematical contracts.  Generate multiple theory-consistent remedies, test
their consequences, and select the one that best restores the violated
contract.  Ad hoc technical tricks are forbidden even when they make a run
survive.

## Required RCA Sequence

1. State the governing equation, conservation law, compatibility condition,
   energy identity, or discrete operator contract that should hold.
2. Map that theory to the exact discretization and runtime path being tested:
   variables, grid metric, face/cell/node cochains, solver algebra, GPU/CPU
   backend, YAML policy, and rebuild epoch.
3. Generate a broad hypothesis set before editing:
   physical model, mathematical precondition, discretization, nonuniform metric,
   interface-tracking rebuild, remap/reinitialization, solver algebra, pressure
   history, cache/device residency, YAML wiring, and diagnostics.
4. Design falsification probes that isolate one hypothesis at a time.  Prefer
   manufactured solutions, component exactness checks, uniform/static-grid
   controls, first-rebuild probes, and short fail-close stage-chain diagnostics
   over long brute-force runs.
5. Record negative evidence.  A falsified hypothesis is valuable because it
   blocks repeated detours.
6. Name the root contract violation before implementing a fix.

## Required Countermeasure Sequence

1. List multiple remedies that restore the named contract.
2. Reject any remedy that only changes symptoms: smaller timestep, damping,
   smoothing, curvature cap, tolerance weakening, coordinate micro-offset,
   hidden fallback, plot cleanup, or extra iterations without a spectral or
   algebraic proof.
3. Compare remedies by theorem fidelity, invariant restoration, implementation
   scope, GPU/backend contract, nonuniform/rebuild safety, and YAML clarity.
4. Implement only the selected contract-restoring remedy.
5. Add the smallest regression that would have caught the root defect, not just
   the observed symptom.
6. Re-run the falsification probe and at least one integrated path that crosses
   the original failure boundary.

## Review Gate

Before accepting any post-failure patch, require a written answer to:

- Which physical or mathematical contract was violated?
- Which hypotheses were considered and which were falsified?
- Why does the selected remedy restore the contract?
- Why are rejected shortcuts still invalid?
- Which regression prevents recurrence on nonuniform grids, interface-tracking
  grid rebuilds, and GPU-optimized paths when relevant?

If these answers are missing, the patch is not a root-cause fix.
