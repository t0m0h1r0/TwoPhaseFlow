---
ref_id: WIKI-T-148
title: "Bootstrap Reinitialization Is Pre-Consistency, Not a Convergence Proof"
domain: theory
status: ACTIVE
superseded_by: null
tags: [bootstrap, reinitialization, hfe, initial_condition, nonuniform_grid]
sources:
  - path: paper/sections/appendix_f_bootstrap.tex
    description: "Initial-condition bootstrap sequence and step 3.5 caveat"
  - path: paper/sections/10_grid.tex
    description: "Nonuniform grid generation dependency on initial phi"
  - path: paper/sections/12u3_hfe.tex
    description: "HFE component verification context"
depends_on:
  - "[[WIKI-T-018]]"
  - "[[WIKI-T-104]]"
  - "[[WIKI-T-142]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Bootstrap Pre-Consistency

## Knowledge Card

The appendix bootstrap resolves a circular dependency: the adaptive/nonuniform
grid needs an initial interface, while accurate interface quantities need the
final grid and operators.

The intended sequence is:

```text
uniform provisional SDF
generate target grid
initialize psi on that grid
build CCD/FCCD/HFE operators
run one reinitialization consistency pass
then construct initial Young-Laplace pressure
```

That reinitialization pass is a pre-consistency step.  It prevents a low-order
provisional SDF from contaminating the initial pressure, but it does not prove
HFE convergence or certify the full grid series.

## Consequences

- Initial-condition quality must be checked on the same grid series used for
  HFE and pressure diagnostics.
- A successful bootstrap pass is not a replacement for component verification.
- Initial Young-Laplace pressure should be built only after the metric field is
  consistent with the target grid.
- Failure at early time can come from bootstrap contamination, not only from
  time integration or PPE.

## Paper-Derived Rule

Use bootstrap reinitialization to make the initial state consistent before
pressure construction; do not cite it as an HFE order proof.
