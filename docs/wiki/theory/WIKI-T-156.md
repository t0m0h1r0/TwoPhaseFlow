---
ref_id: WIKI-T-156
title: "Projection-Native Transport Is a Face-Space Conservation Contract"
domain: theory
status: ACTIVE
tags: [projection_native, cls_transport, face_flux, conservation]
sources:
  - path: paper/sections/09b_split_ppe.tex
  - path: paper/sections/14_benchmarks.tex
  - path: docs/02_ACTIVE_LEDGER.md
---

# Projection-Native Transport Is a Face-Space Conservation Contract

## Claim

The projected face velocity is the velocity of the CLS conservation law.  It
must not be converted to nodes and then re-interpolated to build a new face
flux.

## Effective Knowledge

- The projection equation certifies `D_f u_f = 0` for the canonical face state.
- Reconstructing node velocities and applying another face interpolation creates
  a different discrete divergence operator.
- Static N64 droplet RCA showed that this mismatch can inject interface
  perturbations that later appear as curvature and pressure artifacts.

## Rejected Reading

Treating nodal velocity reconstruction as an equivalent representation of the
projected face flux is false for the coupled interface transport problem.

## Implication

Any future transport/remap route must state which face velocity it consumes and
which divergence operator owns the conservation law.
