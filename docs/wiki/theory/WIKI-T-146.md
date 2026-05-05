---
ref_id: WIKI-T-146
title: "Balanced-Force Failure Modes Are Five Distinct Discrete Mismatches"
domain: theory
status: ACTIVE
superseded_by: null
tags: [balanced_force, csf, pressure_gradient, ppe, face_locus, jump_correction]
sources:
  - path: paper/sections/02b_surface_tension.tex
    description: "Five CSF/BF failure modes"
  - path: paper/sections/08c_bf_failure.tex
    description: "Failure taxonomy before the seven BF principles"
  - path: paper/sections/08d_bf_seven_principles.tex
    description: "Seven balanced-force principles"
  - path: paper/sections/08e_fccd_bf.tex
    description: "FCCD balanced-force construction"
depends_on:
  - "[[WIKI-X-029]]"
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-132]]"
  - "[[WIKI-T-133]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Five BF Mismatches

## Knowledge Card

Balanced force fails in more than one way.  The paper separates five discrete
mismatches that can all create parasitic currents even when the continuous
formula is correct:

| Mode | Mismatch |
|---|---|
| F-1 | pressure gradient and surface tension are evaluated at different loci |
| F-2 | PPE gradient and velocity-corrector gradient are not the same operator |
| F-3 | divergence and gradient are not a discrete adjoint pair |
| F-4 | face `beta = 1/rho` differs across PPE, corrector, and surface tension |
| F-5 | a CCD stencil crosses an interface discontinuity without jump correction |

The later seven BF principles are repairs of these failure modes, not an
independent checklist.

## Consequences

- Raising formal derivative order does not repair a locus mismatch.
- A pressure solver can be accurate in isolation and still fail BF if the
  corrector uses a different face law.
- Interface-crossing stencils need jump-aware treatment before high-order
  claims are meaningful.
- Debugging spurious currents should classify which mismatch is present before
  tuning filters or time step.

## Paper-Derived Rule

Read balanced-force design as the removal of five concrete discrete
mismatches: locus, operator identity, adjointness, coefficient identity, and
jump support.
