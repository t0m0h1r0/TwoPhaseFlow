---
ref_id: WIKI-E-056
title: "Under-Resolved Capillary Droplets Need Resolution Contracts, Not CFL Patches"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [ch14, oscillating_droplet, capillary_cfl, resolution_contract, rca]
sources:
  - path: artifacts/A/ch14_oscillating_droplet_n64_blowup_rca_CHK-RA-OSC-N64-002.md
    description: "N64 oscillating-droplet blowup RCA"
  - path: artifacts/A/ch14_static_droplet_n64_alpha2_CHK-RA-OSC-N64-005.md
    description: "Alpha-2 static droplet control"
depends_on:
  - "[[WIKI-X-043]]"
  - "[[WIKI-T-103]]"
  - "[[WIKI-E-053]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Capillary Resolution Contract

## Knowledge Card

For high-density-ratio pressure-jump capillary tests, the nominal capillary CFL
is not a proof of stability.  A case can be outside the geometry-resolution
contract even when a smaller time step suppresses immediate blow-up.

The N64 oscillating-droplet RCA identifies the relevant resolution budget as a
combination of:

- minimum curvature radius in local grid intervals;
- surface tension and density-ratio stiffness;
- fitted-grid alpha and minimum spacing;
- perturbation amplitude and droplet size.

## Consequences

- Lowering `dt` is symptom control unless the geometry and pressure-jump
  resolution contract is also satisfied.
- Stable directions such as larger droplet, smaller perturbation, or weaker
  fitting alpha are geometry-resolution fixes; lower sigma or equal density are
  controls, not the same benchmark.
- Volume drift and viscous DC can be falsified as primary causes even when a
  run blows up.
- Acceptance for this benchmark family should state the resolution envelope,
  not only the runtime outcome.

## Paper-Derived Rule

For stiff capillary droplet benchmarks, validate the spatial resolution budget
before treating CFL reduction as a fix.
