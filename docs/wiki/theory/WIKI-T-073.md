---
ref_id: WIKI-T-073
title: "Interface-Band Predictor Closure: NS–LS–CFD Derivation for Buoyancy-Driven Assembly"
domain: theory
status: PROPOSED
superseded_by: null
sources:
  - description: "SP-Q — Buoyancy-driven predictor assembly theory"
  - description: "SP-R — Interface-band predictor closure derivation"
  - description: "WIKI-T-006 — One-fluid formulation"
  - description: "WIKI-T-007 — Conservative level set"
  - description: "WIKI-T-066 — Body-force discretization in variable-density NS"
depends_on:
  - "[[WIKI-T-006]]: One-fluid variable-density NS"
  - "[[WIKI-T-007]]: CLS transport and interface variable"
  - "[[WIKI-T-066]]: Body-force discretization"
  - "[[WIKI-T-072]]: Buoyancy-driven predictor assembly"
consumers:
  - "[[WIKI-E-031]]: ch13 rising-bubble hypothesis verdicts"
  - "[[WIKI-X-034]]: buoyancy-aware predictor redesign"
tags: [predictor, interface_band, buoyancy, closure, variable_density, cn, levelset, cfd]
compiled_by: ResearchArchitect
compiled_at: "2026-04-25"
---

# Interface-Band Predictor Closure

## Core statement

The current ch13 rising-bubble instability is best formulated as

> a **buoyancy-driven mismatch in the raw intermediate predictor state**
> `u_pred`, supported on a **two-axis dilated interface band**, and amplified
> when the CN predictor evaluates `V(u_pred)` before projection.

## Continuous model

The starting one-fluid system is

\[
\rho(\psi)(\partial_t \mathbf{u} + \nabla\cdot(\mathbf{u}\otimes\mathbf{u}))
= -\nabla p + \nabla\cdot(2\mu(\psi)\mathbf{D}(\mathbf{u})) + \rho(\psi)\mathbf{g} + \mathbf{f}_\sigma,
\qquad \nabla\cdot\mathbf{u}=0.
\]

The interface variable is the conservative level-set field `psi`, advected by

\[
\partial_t \psi + \nabla\cdot(\psi\mathbf{u}) = 0.
\]

Thus NS and LS are connected through the property maps `rho(psi)` and
`mu(psi)`, and through the interfacial force localisation.

## Discrete CFD statement

The current CN predictor is algebraically

\[
\mathbf{u}_{\mathrm{pred}}^{\mathrm{raw}}
= \mathbf{u}^n + \Delta t\left(\mathbf{E}^n + \mathbf{V}(\mathbf{u}^n)\right),
\]

followed by

\[
\mathbf{u}_\star
= \mathbf{u}^n + \Delta t\left(\mathbf{E}^n + \tfrac12\mathbf{V}(\mathbf{u}^n) + \tfrac12\mathbf{V}(\mathbf{u}_{\mathrm{pred}}^{\mathrm{raw}})\right),
\]

and then variable-density projection.

The key object is therefore not an isolated source term but the **assembled
intermediate state** `u_pred^raw`.

## Interface-band definition

The strict interface set is

\[
I_0 = \{x : 0 < \psi(x) < 1\}.
\]

The effective repair band found by the PoC ladder is the one-cell dilated band

\[
I_1 = I_0 \cup \mathcal{N}_x(I_0) \cup \mathcal{N}_y(I_0).
\]

Recent probes establish:

- strict `I_0` is insufficient,
- x-only dilation is insufficient,
- y-only dilation is insufficient,
- only the **full two-axis band** retains the useful signal.

## Defect model

Write

\[
\mathbf{u}_{\mathrm{pred}}^{\mathrm{raw}} = \mathbf{u}_{\mathrm{pred}}^\star + \delta \mathbf{u}_{I,B},
\qquad \mathrm{supp}(\delta \mathbf{u}_{I,B}) \subset I_1.
\]

Then

\[
\mathbf{V}(\mathbf{u}_{\mathrm{pred}}^{\mathrm{raw}})
= \mathbf{V}(\mathbf{u}_{\mathrm{pred}}^\star) + \mathcal{L}_V[\delta \mathbf{u}_{I,B}] + \mathcal{N}_V(\delta \mathbf{u}_{I,B}).
\]

The dominant failure diagnostics (`ppe_rhs`, `bf_residual`, `div_u`) imply that
`\mathcal{L}_V[\delta u_{I,B}]` couples strongly into the closure-sensitive
subspace seen by projection.

## Engineering implication

The strongest stabilising signal comes from repairing the **buoyancy-carrying
predictor substate** on the full band `I_1` before `V(u_pred)` is evaluated.

This yields the design rule:

> construct buoyancy-aware predictor assembly on the same interface-band family
> expected by the viscous/projection closure.

## What this rejects

This theory explains why the following are weaker than the best branch:

- strict-interface repair,
- x-only or y-only band repair,
- mapped-state-only repair,
- late witness additions,
- reduced-pressure / hydrostatic corrector patches.

## Cross-links

- `docs/memo/short_paper/SP-R_interface_band_predictor_closure_derivation.md`
- `docs/memo/short_paper/SP-Q_buoyancy_driven_predictor_assembly.md`
- `docs/wiki/experiment/WIKI-E-031.md`
