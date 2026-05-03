---
ref_id: WIKI-T-087
title: "Reinitialization Trigger and DGR Applicability Are Context-Sensitive"
domain: theory
status: ACTIVE
superseded_by: null
tags: [reinitialization, dgr, adaptive_trigger, interface_thickness, capillary_wave, zalesak]
sources:
  - path: paper/sections/05_reinitialization.tex
    description: "Adaptive reinitialization trigger, DGR thickness correction, and applicability limits"
depends_on:
  - "[[WIKI-T-027]]"
  - "[[WIKI-T-030]]"
  - "[[WIKI-T-085]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Reinitialization Trigger and DGR Applicability

## Knowledge Card

The paper treats reinitialization as a context-sensitive intervention, not a
fixed-frequency ritual.  The trigger is the interface-thickness monitor
`M(tau)=int psi(1-psi)dV`, whose growth indicates deviation from the equilibrium
tanh profile.

DGR is similarly conditional.  It repairs global thickness inflation for suitable
smooth interfaces, but it is forbidden for narrow slot-like geometry and for
surface-tension-driven oscillatory/folded interface bands.

## Consequences

- Fixed-period reinitialization can over-reinitialize and damage shape.
- Too little reinitialization increases profile and curvature error.
- Too much reinitialization moves the interface and accumulates volume error.
- DGR fixes mass/thickness consistency but does not cure all shape metrics.
- DGR must not be added after split reinitialization in capillary oscillation
  cases where folds generate curvature spikes.

## Paper-Derived Rule

Choose reinitialization by monitored interface state and geometry class, not by a
global step counter.
