---
ref_id: WIKI-T-123
title: "Term-Specific Discretization Is a Regularity Contract"
domain: theory
status: ACTIVE
superseded_by: null
tags: [scheme_selection, regularity, discretization, ccd, interface_band]
sources:
  - path: paper/sections/06_scheme_per_variable.tex
    description: "Field-characteristic based scheme assignment and prohibitions"
depends_on:
  - "[[WIKI-T-079]]"
  - "[[WIKI-T-093]]"
  - "[[WIKI-T-120]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Regularity-Based Scheme Selection

## Knowledge Card

The paper's scheme table is a regularity contract.  It does not say "use the
highest-order method everywhere."  It says:

```text
smooth bulk velocity       -> CCD/UCCD6/FCCD admissible
tanh-like psi profile      -> FCCD conservative face flux
pressure with jump         -> face flux + GFM/IIM/HFE
rho, mu step-like fields   -> algebraic/low-order property rules
interface-band velocity    -> lower-order one-sided/central closure
```

Formal order is conditional on the field being smooth enough over the stencil.

## Consequences

- Applying nodal CCD to raw `psi`, `p` jumps, or step-like material fields is a
  premise violation.
- Lower-order treatment in the interface band is sometimes the high-fidelity
  choice.
- Scheme assignment belongs to the variable/term, not to the codebase globally.
- Verification should include prohibition tests, not only convergence tests.

## Paper-Derived Rule

Choose the spatial operator by the regularity of the quantity being acted on;
formal order is void when the stencil crosses a discontinuity or kink.
