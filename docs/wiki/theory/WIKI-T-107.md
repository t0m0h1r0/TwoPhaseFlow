---
ref_id: WIKI-T-107
title: "One-Fluid CSF Absorbs the Stress Jump as a Weak-Form Body Force"
domain: theory
status: ACTIVE
superseded_by: null
tags: [one_fluid, two_fluid, csf, stress_jump, weak_form, surface_tension]
sources:
  - path: paper/sections/02_governing.tex
    description: "Two-fluid stress jump and one-fluid CSF weak-form conversion"
depends_on:
  - "[[WIKI-T-006]]"
  - "[[WIKI-T-083]]"
  - "[[WIKI-T-097]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Stress Jump Absorption

## Knowledge Card

The One-Fluid formulation is not merely a convenient interpolation of density
and viscosity.  Its key move is to absorb the two-fluid interface stress jump
into a distributional body force:

```text
two-fluid jump condition on Gamma
  -> surface delta body force in the volume equation
  -> one velocity field over the whole domain
```

The paper justifies this as a weak-form equivalence: testing the volume force
against arbitrary functions reproduces the original interface force integral.
That is why CSF is a single-domain representation of the jump condition, not a
separate ad hoc force added after the fact.

## Consequences

- CSF sign conventions must follow the same oriented jump convention as the
  two-fluid stress condition.
- A one-fluid equation still carries the interface condition; it has not
  discarded it.
- Surface-tension discretization errors are errors in the absorbed jump.
- A sharp pressure-jump PPE and a smooth CSF path are different closures of the
  same interface-stress origin.

## Paper-Derived Rule

When using One-Fluid CSF, audit whether the discrete body force still represents
the original stress jump in the same weak-form sense.
