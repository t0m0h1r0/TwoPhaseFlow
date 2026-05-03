---
ref_id: WIKI-T-110
title: "epsilon_eff Is a Profile-Quality Sensor, Not a New Width Parameter"
domain: theory
status: ACTIVE
superseded_by: null
tags: [epsilon_eff, cls, profile_quality, reinitialization, smearing, diagnostics]
sources:
  - path: paper/sections/03c_levelset_mapping.tex
    description: "Effective interface-width diagnostic from psi and grad psi"
depends_on:
  - "[[WIKI-T-106]]"
  - "[[WIKI-T-087]]"
  - "[[WIKI-E-036]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# epsilon_eff Diagnostic

## Knowledge Card

The effective width

```text
epsilon_eff = psi * (1 - psi) / |grad psi|
```

is a diagnostic derived from the sigmoid profile and the Eikonal expectation
`|grad phi| ~= 1`.  It is not an alternate width knob.  Near a healthy
interface, `epsilon_eff` should match the designed `epsilon`; if it grows, the
profile has broadened through numerical diffusion or incomplete
reinitialization.

The paper uses this as a profile-quality sensor for direct-`psi` curvature and
reinitialization policy.

## Consequences

- `epsilon_eff >> epsilon` signals smearing, not a new admissible design width.
- The diagnostic is meaningful only where `psi` is in the interface band.
- Reinitialization triggers can be interpreted as profile-quality gates.
- Verification should separate nominal `epsilon/h` settings from measured
  profile width.

## Paper-Derived Rule

Use `epsilon_eff` to detect loss of the intended CLS profile; do not feed it
back as if it redefines the interface model.
