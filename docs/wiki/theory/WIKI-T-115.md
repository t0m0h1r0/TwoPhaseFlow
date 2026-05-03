---
ref_id: WIKI-T-115
title: "M(tau) Is a Reinit Call Gate, Not an Error Norm"
domain: theory
status: ACTIVE
superseded_by: null
tags: [adaptive_reinitialization, cls, interface_width, monitor, profile_quality]
sources:
  - path: paper/sections/05_reinitialization.tex
    description: "Adaptive reinitialization trigger based on M(tau)=int psi(1-psi)dV"
depends_on:
  - "[[WIKI-T-087]]"
  - "[[WIKI-T-110]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Reinit Call Gate

## Knowledge Card

The monitor

```text
M(tau) = integral psi * (1 - psi) dV
```

is used as a gate for whether to call reinitialization.  It measures profile
fatness relative to the post-reinit reference value, so it is sensitive to
interface broadening.  The paper does not use it as a universal geometry-error
norm.

This distinction explains why fixed-frequency reinitialization is rejected:
too many calls can introduce cumulative profile distortion even when high-wave
damping is small.

## Consequences

- Reinitialization should be event/quality driven, not called by habit.
- `M/M_ref` is a profile-width trigger, not a curvature or topology certificate.
- A stable transport step can still defer reinit if the profile monitor stays
  inside tolerance.
- Excess reinitialization is a source of error, not a safety blanket.

## Paper-Derived Rule

Use `M(tau)/M_ref` to decide whether reinitialization is needed; do not
interpret it as a complete interface-geometry error metric.
