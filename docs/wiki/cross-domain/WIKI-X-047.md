---
ref_id: WIKI-X-047
title: "Static-Droplet RCA Consolidates Projection, Geometry, and Output Contracts"
domain: cross-domain
status: ACTIVE
tags: [static_droplet, projection_closure, ridge_eikonal, pressure_hodge, negative_knowledge]
sources:
  - path: docs/memo/short_paper/SP-AE_pressure_hodge_static_droplet_lessons.md
  - path: docs/memo/short_paper/SP-AD_ridge_eikonal_transport_variational_coupling.md
  - path: paper/sections/09b_split_ppe.tex
  - path: paper/sections/13b_twophase_static.tex
  - path: docs/02_ACTIVE_LEDGER.md
depends_on:
  - "[[WIKI-T-158]]"
  - "[[WIKI-E-062]]"
  - "[[WIKI-X-041]]"
---

# Static-Droplet RCA Consolidated Contracts

## Scope

This card summarizes the May 6 static-droplet sequence as reusable
cross-domain knowledge.  It is the bridge between the short paper, theory
cards, experiment cards, and paper edits.

## Accepted Contracts

| Layer | Accepted contract |
|---|---|
| Interface transport | Use projected face velocity for physical interface advection. |
| Reinitialization | Ridge--Eikonal is a geometric/profile projection, not a physical RHS. |
| Capillary pressure jump | Project the known capillary face cochain into `range(A_f G_f)` before correction. |
| Pressure output | Reconstruct a Hodge representative from `pressure_accel_faces`; fail if absent. |
| YAML policy | One production YAML per experiment; pressure output declares `pressure_hodge`. |

## Negative Knowledge

The following routes are retained only as rejected or diagnostic paths:

- coupling Eikonal pseudo-time residuals into physical advection;
- using PPE divergence residual alone as a static-droplet force-balance gate;
- hiding interface pressure with `pressure_bulk`;
- reading raw interface-band nodal pressure as physical pressure;
- damping, blind CFL reduction, curvature caps, and smoothing as pressure fixes;
- extra checked-in diagnostic YAMLs for one-off resolution or plot variants.

## Paper Filter

The paper should keep the mathematical contracts:

- face-space pressure-work cochain;
- range-projected capillary jump;
- Hodge pressure representative;
- static-droplet face-balance diagnostics.

The wiki keeps the trial matrix and failed detours so the research path remains
auditable without promoting every probe to a paper claim.
