---
ref_id: WIKI-T-108
title: "Logit Inversion Is a Diagnostic Bridge, Not a Curvature Prerequisite"
domain: theory
status: ACTIVE
superseded_by: null
tags: [cls, logit, psi_phi_mapping, curvature, diagnostics, hfe]
sources:
  - path: paper/sections/03c_levelset_mapping.tex
    description: "Analytic psi-to-phi logit inverse and direct psi-curvature path"
depends_on:
  - "[[WIKI-T-020]]"
  - "[[WIKI-T-078]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Logit Inversion Scope

## Knowledge Card

The logit inverse

```text
phi = epsilon * log((1 - psi) / psi)
```

is an analytic `O(1)` pointwise bridge from CLS `psi` back to signed distance
`phi`.  The paper makes it the main route when a `phi` field is required, for
example by HFE or distance reconstruction diagnostics.  It is not, however, a
mandatory precursor to curvature: the curvature theorem allows the paper to
compute curvature directly from `psi` derivatives in the interface band.

This split prevents saturation artifacts from being imported into curvature
when `psi` is near 0 or 1.

## Consequences

- Newton inversion is auxiliary; it is not the production path for `psi -> phi`.
- Curvature code should not depend on a globally reconstructed `phi` when the
  direct-`psi` inputs are available.
- Saturation clamps protect logit inversion but do not certify curvature.
- HFE/PPE paths may need `phi`; CSF curvature may not.

## Paper-Derived Rule

Use logit inversion only for consumers that genuinely need `phi`; do not make
it a hidden prerequisite for every interface-geometry calculation.
