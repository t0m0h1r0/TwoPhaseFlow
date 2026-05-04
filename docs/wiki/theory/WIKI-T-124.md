---
ref_id: WIKI-T-124
title: "TVD-RK3 Label Does Not Guarantee TVD for the FCCD Space Operator"
domain: theory
status: ACTIVE
superseded_by: null
tags: [time_integration, tvd_rk3, fccd, cls, clamp, ssp]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "TVD-RK3 scope and warning that FCCD spatial discretization is not TVD by itself"
depends_on:
  - "[[WIKI-T-088]]"
  - "[[WIKI-T-101]]"
  - "[[WIKI-T-123]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# TVD-RK3 Scope

## Knowledge Card

The paper uses TVD-RK3/SSPRK3 for CLS conservative transport, but it explicitly
does not claim that the full FCCD spatial discretization is TVD.  SSP time
integration inherits TVD behavior only when the forward-Euler spatial step has
the relevant monotonicity property.

Since FCCD is a high-order face-flux construction rather than a TVD limiter,
the paper pairs it with `psi` range clamps and interface-profile monitoring.

## Consequences

- "TVD-RK3" in the time integrator is not a blanket monotonicity certificate.
- Overshoot control still needs clamp/guard logic.
- CLS transport verification should separate temporal SSP order from spatial
  boundedness.
- Reinitialization and profile monitors remain necessary even with SSPRK3.

## Paper-Derived Rule

Use TVD-RK3 as the CLS time integrator, but audit boundedness through the
FCCD+clamp/profile system rather than through the time-integrator name alone.
