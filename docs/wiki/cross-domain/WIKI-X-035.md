---
ref_id: WIKI-X-035
title: "Buoyancy-Aware Predictor Redesign Theorem: Minimal Admissible Algorithm for ch13"
domain: cross-domain
status: PROPOSED
superseded_by: null
sources:
  - description: "SP-R — Interface-band predictor closure derivation"
  - description: "SP-S — Buoyancy-aware predictor redesign theorem and algorithm spec"
  - description: "WIKI-X-034 — redesign memo"
depends_on:
  - "[[WIKI-T-072]]: Buoyancy-driven predictor assembly"
  - "[[WIKI-T-073]]: Interface-band predictor closure derivation"
  - "[[WIKI-X-034]]: redesign memo"
consumers:
  - "[[WIKI-E-031]]: ch13 rising-bubble hypothesis verdicts"
tags: [predictor, redesign, theorem, algorithm, buoyancy, interface_band, cn]
compiled_by: ResearchArchitect
compiled_at: "2026-04-25"
---

# Buoyancy-Aware Predictor Redesign Theorem

## Core result

The redesign problem can now be stated compactly:

> if the dominant defect is a buoyancy-driven mismatch in the raw intermediate
> state `u_pred`, supported on the full two-axis dilated interface band, then
> the minimal admissible cure is to assemble a buoyancy-carrying substate
> first, repair that substate on the same band, and only then compose the final
> `u_pred` passed to `V(u_pred)`.

## Why this matters

This theorem excludes a large class of tempting but weaker fixes:

- late witness terms,
- strict-interface-only repairs,
- x-only or y-only band repairs,
- reduced-pressure corrector proxies,
- scalar pressure/hydrostatic weights.

They all act too late or on the wrong geometric support.

## Admissible algorithm class

Preferred primary form:

\[
\widetilde{\mathbf{u}}_B
= \mathcal{T}_{I_1}\!\left(\mathbf{u}^n + \Delta t\,B(\psi^n)\right),
\]

\[
\mathbf{u}_{\mathrm{pred}}
= \widetilde{\mathbf{u}}_B
+ \Delta t\left(C(\mathbf{u}^n)+\mathbf{V}(\mathbf{u}^n)+\cdots\right).
\]

Secondary coupled form:

\[
\widetilde{\mathbf{u}}_{BV}
= \mathcal{T}_{I_1}\!\left(\mathbf{u}^n + \Delta t(B(\psi^n)+\mathbf{V}(\mathbf{u}^n))\right).
\]

## Algorithmic rule

The redesign must preserve this order:

1. build buoyancy-carrying predictor substate,
2. repair on the full two-axis interface band,
3. compose final `u_pred`,
4. evaluate `V(u_pred)`,
5. project.

## Code implication

The implementation focus stays local to:

- `src/twophase/time_integration/cn_advance/picard_cn.py`
- `src/twophase/time_integration/cn_advance/richardson_cn.py`
- `src/twophase/simulation/ns_step_services.py`
- `src/twophase/simulation/ns_predictor_assembly.py`

## Acceptance rule

Only promote a redesign that beats `buoyancy_local` or extends the stable
horizon without a harsher failure mode.

## Cross-links

- `docs/memo/short_paper/SP-S_buoyancy_predictor_redesign_theorem.md`
- `docs/memo/short_paper/SP-R_interface_band_predictor_closure_derivation.md`
- `docs/wiki/cross-domain/WIKI-X-034.md`
