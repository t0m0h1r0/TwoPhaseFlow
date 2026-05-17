---
ref_id: WIKI-T-178
title: "Ch14 PhaseRegion Route Closure Needs One Owner for State, Measure, Energy, and Work"
domain: theory
status: ACTIVE
tags: [ch14, phase_region, capillary, state_ownership, variational_closure, q_residual, pressure_work]
sources:
  - path: docs/wiki/theory/WIKI-T-174.md
    description: "Original capillary state ownership reset: interface configuration or cell volume"
  - path: docs/wiki/theory/WIKI-T-176.md
    description: "PhaseRegion-primary InterfaceAtlas theory"
  - path: docs/wiki/theory/WIKI-T-177.md
    description: "PhaseRegion variational axioms before force coupling"
  - path: docs/wiki/experiment/WIKI-E-064.md
    description: "Baseline PASS and screened graph-q FAIL evidence"
  - path: artifacts/A/ch14_capillary_yaml_time_owned_outputs_CHK-RA-CH14-VAR-063.md
    description: "Corrected YAML-owned one-period capillary run"
depends_on:
  - "[[WIKI-T-174]]"
  - "[[WIKI-T-176]]"
  - "[[WIKI-T-177]]"
  - "[[WIKI-E-064]]"
consumers:
  - domain: theory
    usage: "Use before changing Ch14 capillary ownership, force admission, or chart scope"
  - domain: experiment
    usage: "Use before interpreting capillary-wave, droplet, or mixed bubble/layer probes"
  - domain: code
    usage: "Use as the equation-to-discretization owner map for PhaseRegion code"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Route Closure Needs One Owner for State, Measure, Energy, and Work

## Knowledge Card

The successful Ch14 route is not `q`-primary and not `phi`-primary.  It is
`PhaseRegion`-primary:

```text
R_h(t) = discrete phase region
Gamma_h(t) = boundary chart atlas of R_h(t)
q_h(t) = Q_h(R_h(t))
phi_h(t) = chart/gauge representation
E_h(R_h) = sigma * Perimeter(R_h)
s_f = -T_h^* dE_h
```

The owned object is `R_h`.  Cell measures `q_h` are derived measures, `phi_h`
is a gauge, and graph/closed/open curves are charts of the same boundary.
Surface tension varies the region boundary, not a display array.

This closes the theoretical split that made the screened graph-q path fragile:

```text
transported q_T
  may contain non-geometric modes
  may not equal Q_h(Gamma_h) for any smooth admissible chart
  must be decomposed into q_phys + residual r before being trusted
```

If all cell fractions are treated as inviolable physics, exact projection can
force the interface to fit non-geometric noise.  Capillary curvature then
amplifies that noise into pressure and velocity, so a small representation
error becomes a dynamics error.

## Preserved Failure Knowledge

The following failures are theory evidence, not implementation debris:

| Observation | Theory interpretation |
|---|---|
| Transported `q` can fail smooth graph/phi reconstruction | `q_T` can leave the image of the admissible interface manifold. |
| `compat_linf=0` after graph rebuild can pass while the pre-rebuild state changed | Rebuild can redefine the measured `q` instead of preserving the old material state. |
| Exact `q` projection can make the interface jagged | All-cell `q` constraints overfit non-geometric residuals. |
| Moving-grid rebuild can chase the gauge | The owner must be the material region, not the reconstructed `phi`. |
| Capillary wave and droplet routes diverged | They were treated as different theories instead of different charts of `R_h`. |
| Pressure, velocity, face cochain, and boundary spaces can disagree | Work closure requires the same endpoint map and face metric. |

## Chart Unification

The chart type is not the theory:

```text
capillary wave:       graph chart
oscillating droplet:  closed-curve chart
rising bubble + top:  multi-component atlas
```

All three use the same region, perimeter, volume-constraint, and work-pairing
principle.  No special condition such as "closed surface only" or "screened
Riesz exists" may become the body of the theory.

## Vectorized Discretization Principle

The implementation route should remain vectorizable by storing charts in
component-major packed arrays:

```text
component_offsets
component_to_batch
chart_type / topology / attachment / orientation / phase labels
dof_offsets
active_cell_offsets
```

Small oracles may use dense arrays.  Runtime-facing paths should use
active-band arrays, segment reductions, and backend-dispatched `xp` kernels.
For the graph chart, the exact P1 column integral is the fast `Q_h` map.

Full nonlinear optimization is not the default runtime route.  The fast
admission ladder is:

```text
F0: direct low-mode moment projection + exact total volume correction
F1: small low-mode KKT
F2: guarded second correction
F3: nonlinear solve only for oracle/fail-closed diagnosis
```

## Boundary

The corrected YAML-owned capillary graph run validates the reduced graph route
against exact amplitude, velocity, energy, residual, and volume references.
It does not admit production force coupling; `force_admissible=0` remains a
theory boundary until the pressure/velocity work gate consumes the same
face-shaped capillary cochain under the same metric.
