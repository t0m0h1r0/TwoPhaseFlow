---
ref_id: WIKI-X-052
title: "Ch14 AO-Fast Capillary RCA Trial Ledger"
domain: cross-domain
status: ACTIVE
tags: [ch14, ao_fast, capillary_wave, rca, falsification, grid_rebuild, face_cochain, pressure_history]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
    description: "CHK-RA-CH14-AO-FASTVOL-035--062 capillary AO-Fast RCA, fixes, runs, and GPU probes"
  - commit: 9ddafa77
    description: "Stabilize AO capillary grid rebuild by transporting projected face cochains"
  - path: experiment/ch14/config/ch14_capillary.yaml
    description: "Current quarter-period capillary production configuration"
  - path: src/twophase/ns/ns_grid_rebuild.py
    description: "Grid rebuild path that now carries projection-native face components"
  - path: src/twophase/projection/velocity_reprojector_basic.py
    description: "FaceHodgeReprojector implementation"
depends_on:
  - "[[WIKI-X-050]]"
  - "[[WIKI-X-051]]"
  - "[[WIKI-T-171]]"
consumers:
  - domain: code
    usage: "Regression checklist before changing capillary AO-Fast, grid rebuild, pressure history, or GPU routes"
  - domain: experiment
    usage: "Short-path diagnostic ledger for future ch14 capillary failures"
compiled_by: ResearchArchitect
compiled_at: 2026-05-14
---

# Ch14 AO-Fast Capillary RCA Trial Ledger

## Knowledge Card

The 2026-05-14 Chapter 14 capillary AO-Fast debugging sequence established
that the decisive failure was not a physical timestep, tolerance, tiny-cell, or
pressure-history symptom.  The root contract violation was a moving-grid
projection error: after an interface-following grid rebuild, the code remapped
nodal velocities and then reconstructed face fluxes.  Interpolation, Hodge
projection, and divergence do not commute on the nonuniform face complex, so
the rebuilt state no longer represented the previously projected face cochain.

The valid repair is to transport the projection-native face cochain across the
grid epoch and reproject it with the new face Hodge metric.

The later 2026-05-14 zero-base review found a second, distinct contract
violation.  For `tracking.primary: q` with `gauge_reconstruction:
column_height_graph`, the capillary endpoint is not the generic P1 cut-cell
surface functional.  The owned coordinate is the column height
`H_i(q)=y_min+sum_j q_ij/dx_i`; therefore the discrete surface energy must be
the graph length
`sigma sum_i sqrt(ds_i^2+(H_{i+1}-H_i)^2)`, and its variation must be pulled
back to the single cut cell in each column before applying the finite-volume
incidence adjoint.  Using the generic P1 cut-cell surface derivative on a
moving graph endpoint is finite-dimensional endpoint mixing: it can keep
`q-Q_h(phi)` small while producing `O(10^4)` local capillary cochains when the
graph crosses cell strata.

## Falsification Ledger

| Hypothesis | Probe / Evidence | Result |
|---|---|---|
| A tiny coordinate offset such as `y += 1e-10` resolves the issue. | Compared against regular-stratum and grid-rebuild theory. | Rejected. It hides a node-crossing symptom and violates the no-micro-offset policy in [[WIKI-T-171]]. |
| Defect correction only needed more fixed iterations. | Raising DC cap allowed external split convergence in some probes, but did not stabilize the integrated moving-grid capillary run. | Rejected as root cause. DC must be convergence-gated and fail-close, not iteration-count tuned. |
| Pressure-history extrapolation caused the blowup. | Replacing BDF2 pressure extrapolation by constant history left the 60-step blowup essentially unchanged. | Falsified as immediate root cause. HFE-style smooth pressure coordinates remain required for jump consistency. |
| Nonuniform tiny cells caused the blowup. | `min_dx` and `min_dy` stayed finite, about `5.2e-4` and `3.8e-4`, while diagnostics exploded. | Falsified as immediate root cause. Nonuniform support remains mandatory. |
| Interface-following rebuild is the trigger. | Static/no-rebuild control with `--grid-rebuild-frequency 0` stayed stable through 40 steps: `v_abs~1.07e-3`, `face_hodge_pre=0`, and `ppe_rhs=O(50)`. | Supported. The failure appears at metric-epoch transition. |
| Rebuild loses the projected face state. | Before the fix, step 60 reached `v_abs_max=5.8e3`, `face_hodge_pre=4.6e7`, and `ppe_rhs=2.66e17`. After projected-face transport, step 60 stayed finite: `v_abs_max=2.39e-3`, `projected_face_linf=2.96e-3`, `face_hodge_pre=1.17e-3`, `ppe_rhs=88.7`, `compat=4.78e-13`. | Identified root cause. |
| P1 cut-cell surface work is valid for q-owned graph tracking. | With projected-face transport fixed, both rebuild and no-rebuild 260-step probes still developed huge P1-source spikes (`raw_accel_cos` up to `O(10^4)`) from small interface motion. Replacing the source by the column-height graph Riesz kept `raw_accel_cos` near `14`, `v_abs_max` near `4.3e-3`, and `compat=O(1e-14)` through 260 steps. | Falsified. For graph gauges, capillary work must be graph-endpoint work. |

## Canonical Diagnosis

The capillary AO-Fast moving-grid state contains at least three different
cochain types:

- cell/active-volume cochains such as `q`;
- nodal or diagnostic fields such as `u`, `v`, and `psi`;
- projection-native face cochains used by the divergence/Hodge/PPE complex.

Only the face cochain is the immediate carrier of the projected incompressible
state.  Remapping nodal velocities and rebuilding face fluxes is not a valid
transport of that cochain on a nonuniform rebuilt grid.  The divergence-free
property is therefore destroyed before the next capillary pressure solve, and
the Hodge defect feeds back into the pressure RHS.

## Reusable Probe Set

For future capillary AO-Fast failures, collect these before editing:

- static/no-rebuild control and first-rebuild-only control;
- `min_dx`, `min_dy`, regular-stratum certificate, and grid epoch id;
- `face_hodge_pre`, `face_hodge_post`, `projected_face_linf`, `ppe_rhs`, and
  `compat`;
- pressure-history coordinate mode and whether physical jump pressure is
  decoded only at the face law;
- capillary source discretization (`column_height_graph` versus generic
  `p1_cut_bundle`) and whether it matches the YAML-selected gauge owner;
- DC convergence status, not only DC iteration count;
- GPU route evidence proving that nonuniform metrics and rebuilds were not
  silently disabled.

## Negative Knowledge

Do not use these as fixes:

- micro-offsets to avoid zero-level/node coincidence;
- CFL, damping, smoothing, curvature caps, or tolerance changes without a
  named theorem violation;
- disabling nonuniform grids or interface-following rebuilds;
- replacing convergence gates with fixed iteration counts;
- hidden PCG/DC/GPU fallback that would make a wrong route look successful;
- remapping projected flow by nodal interpolation after a grid rebuild.
- evaluating q-owned graph capillarity with the generic P1 cut-cell surface
  derivative; this mixes endpoints and creates stratum-crossing source spikes.
