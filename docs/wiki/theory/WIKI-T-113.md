---
ref_id: WIKI-T-113
title: "Ridge-Eikonal Admissibility Is Four Conditions, Not Just FMM"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ridge_eikonal, admissibility, fmm, geometry, projection, normals]
sources:
  - path: paper/sections/03d_ridge_eikonal.tex
    description: "Geometric regularity, projection uniqueness, sign consistency, and normal consistency"
depends_on:
  - "[[WIKI-T-084]]"
  - "[[WIKI-T-111]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Four-Part Ridge-Eikonal Gate

## Knowledge Card

Ridge--Eikonal validity is not guaranteed by running FMM.  The paper requires a
geometric gate before the signed-distance reconstruction is a well-posed
viscosity-solution problem:

```text
1. geometric regularity of Gamma
2. unique closest-point projection near Gamma
3. consistent phase labels/sign across Gamma
4. consistent normal orientation from xi_ridge Hessian data
```

Numerically, these translate into curvature/spacing checks and continuous
eigenvector-branch choices for ridge normals.

## Consequences

- FMM can faithfully reconstruct the wrong problem if the ridge set is
  geometrically inadmissible.
- Close interfaces require spacing checks, not just more iterations.
- Normal sign flips are admissibility failures, not cosmetic orientation noise.
- Topology handling and metric reconstruction should expose separate diagnostics.

## Paper-Derived Rule

Before invoking distance reconstruction, certify the ridge set as a valid
Eikonal boundary with geometry, projection, phase, and normal consistency.
