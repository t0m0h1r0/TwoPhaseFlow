---
ref_id: WIKI-T-072
title: "Buoyancy-Driven Predictor Assembly: Interface-Local Intermediate-State Theory"
domain: theory
status: PROPOSED
superseded_by: null
sources:
  - description: "Almgren, Bell, Szymczak, Howell (1998). A Conservative Adaptive Projection Method for the Variable Density Incompressible Navier–Stokes Equations."
  - description: "Brown, Cortez, Minion (2001). Projection Method III: Spatial Discretization on the Staggered Grid."
  - description: "Guermond, Salgado (2009). A Splitting Method for Incompressible Flows with Variable Density Based on a Pressure Poisson Equation."
  - description: "Rudman (1998). A Volume-Tracking Method for Incompressible Multifluid Flows and Large Density Variations."
  - description: "Raessi, Pitsch (2012). Consistent Mass and Momentum Transport for Simulating Incompressible Interfacial Flows with Large Density Ratios Using the Level Set Method."
  - description: "Dodd, Ferrante (2014). A Fast Pressure-Correction Method for Incompressible Two-Fluid Flows."
  - description: "François et al. (2006). A Balanced-Force Algorithm for Continuous and Sharp Surface Tension Models Within a Volume Tracking Framework."
  - description: "Popinet (2009). An Accurate Adaptive Solver for Surface-Tension-Driven Interfacial Flows."
  - description: "Kumar, Natarajan (2017). A Novel Consistent and Well-Balanced Algorithm for Simulations of Multiphase Flows on Unstructured Grids."
depends_on:
  - "[[WIKI-T-066]]: Body-force discretization in variable-density NS"
  - "[[WIKI-T-070]]: Rising-bubble projection-closure diagnosis"
  - "[[WIKI-T-071]]: Face-canonical variable-density projection survey"
consumers:
  - "[[WIKI-E-031]]: ch13 rising-bubble hypothesis verdicts"
tags: [buoyancy, predictor, cn, variable_density, interface_band, hydrostatic_split, reduced_pressure]
compiled_by: ResearchArchitect
compiled_at: "2026-04-25"
---

# Buoyancy-Driven Predictor Assembly

## Core claim

The strongest current diagnosis is:

> the dominant ch13 instability is a **buoyancy-driven mismatch in the raw CN
> intermediate state** `u_pred`, localised to the interface band, and then
> amplified when the predictor evaluates `V(u_pred)`.

This is stronger and more specific than “projection inconsistency” in general.

## Continuous statement

The one-fluid variable-density model is

\[
\rho(\psi)(\partial_t \mathbf{u} + \nabla\cdot(\mathbf{u}\otimes\mathbf{u}))
= -\nabla p + \nabla\cdot(2\mu(\psi)\mathbf{D}(\mathbf{u}))
+ \rho(\psi)\mathbf{g} + \mathbf{f}_\sigma,
\qquad
\nabla\cdot\mathbf{u}=0.
\]

At this level, reduced-pressure and hydrostatic decompositions are legitimate
rewritings. But they only help discretely when the predictor/corrector closure
remains same-space and interface-consistent.

## Discrete statement for the current stack

The Picard-CN path used here is explicitly:

\[
\mathbf{u}_{\text{pred}}
= \mathbf{u}^n + \Delta t(\mathbf{E}^n + \mathbf{V}(\mathbf{u}^n)),
\]

\[
\mathbf{u}_\star
= \mathbf{u}^n + \Delta t(\mathbf{E}^n + \tfrac12\mathbf{V}(\mathbf{u}^n)
+ \tfrac12\mathbf{V}(\mathbf{u}_{\text{pred}})).
\]

`E^n` contains the explicit branches, including buoyancy. The key insight is
that `u_pred` is a **composed state**, not an atomic one.

## Interface-band theory

Let `I_ε` denote the interface band. The current evidence supports:

1. the dangerous defect is supported mainly in `I_ε`
2. it is carried by the **state/value** of raw `u_pred`
3. it is excited most strongly by the **buoyancy branch**
4. it becomes visible through pressure/divergence-sensitive diagnostics rather
   than through mass loss first

In other words, the unstable object is not “the buoyancy source term” by
itself, but the buoyancy-carrying **assembled intermediate state**.

## Why shallow fixes fail

The current hypothesis campaign rejects the following as primary cures:

- reduced-pressure corrector
- projection-side buoyancy proxy
- structural hydrostatic predictor split
- previous-pressure predictor co-balance
- face-density-only buoyancy assembly

These all modify the problem too late, or too partially, relative to the place
where the defect is created.

## What the positive signal says

The strongest positive signal so far is the interface-local repair of the fully
assembled raw `u_pred`, especially on the buoyancy-driven branch.

That means:

> repairing the **assembled interface-local state** is more effective than
> repairing any upstream sub-branch in isolation.

This is the key structural fact.

## Theoretical interpretation

Write

\[
\mathbf{u}_{\text{pred}}^{\text{raw}}
= \mathbf{u}_{\text{pred}}^\star + \delta \mathbf{u}_B,
\qquad
\mathrm{supp}(\delta \mathbf{u}_B)\subset I_\varepsilon.
\]

Then the predictor sees

\[
\mathbf{V}(\mathbf{u}_{\text{pred}}^{\text{raw}})
= \mathbf{V}(\mathbf{u}_{\text{pred}}^\star)
+ \mathcal{L}[\delta \mathbf{u}_B]
+ \text{higher-order terms}.
\]

The experiments show that the harmful part of `L[δu_B]` is not captured by a
single trace-only, shear-only, axis-only, or scalar-weighted witness. It is a
coupled interface-local state mismatch.

## Current best engineering reading

The next serious redesign target is:

> construct the buoyancy-carrying predictor state itself on an
> interface-local, closure-compatible assembly family **before**
> `V(u_pred)` is evaluated.

This is preferable to adding more late witnesses or further corrector-side
patches.

## Cross-links

- Short paper: `docs/memo/short_paper/SP-Q_buoyancy_driven_predictor_assembly.md`
- Survey background: `docs/memo/short_paper/SP-P_face_canonical_projection_survey.md`
- Experiment log: `docs/wiki/experiment/WIKI-E-031.md`
