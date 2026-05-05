---
ref_id: WIKI-T-144
title: "Eikonal Rigidity Requires a Separate Topology Carrier"
domain: theory
status: ACTIVE
superseded_by: null
tags: [eikonal, signed_distance, topology, ridge_eikonal, fmm]
sources:
  - path: paper/sections/02_governing.tex
    description: "Eikonal topology rigidity box and sign/domain definitions"
  - path: paper/sections/03d_ridge_eikonal.tex
    description: "Gaussian ridge field as topology carrier"
  - path: paper/sections/10d_ridge_eikonal_nonuniform.tex
    description: "Nonuniform ridge-eikonal reconstruction"
depends_on:
  - "[[WIKI-T-111]]"
  - "[[WIKI-T-113]]"
  - "[[WIKI-T-116]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Eikonal Rigidity

## Knowledge Card

A signed-distance field is a metric object, not a topology-free interface
carrier.  Once `phi` is constrained by `|grad phi| = 1` and a fixed zero-level
interface, its nearby level sets are parallel offsets.  That suppresses local
extrema and ridge-like topology changes.

The paper's ridge-eikonal route therefore separates the two jobs:

```text
ridge field / xi_ridge : carry topology changes
phi_sdf                : recover metric distance after topology is chosen
```

FMM or an equivalent Eikonal reconstruction restores distance accuracy after
the topology carrier has done its job.

## Consequences

- A topology-changing algorithm should not demand Eikonal regularity from the
  auxiliary ridge field.
- SDF diagnostics belong to the reconstructed `phi`, not to `xi_ridge`.
- Reinitialization is not a substitute for a topology carrier; it restores the
  metric contract around the chosen interface.
- Nonuniform-grid implementations must keep topology selection and metric
  reconstruction as separate verification targets.

## Paper-Derived Rule

Use Eikonal fields for metric precision and a separate ridge/topology field for
merger/splitting freedom.
