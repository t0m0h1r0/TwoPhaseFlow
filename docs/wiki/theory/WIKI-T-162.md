---
ref_id: WIKI-T-162
title: "Reinitialization-Free CLS Survey and Candidate Routes"
domain: theory
status: PROPOSED
tags: [cls, level_set, reinitialization_free, anti_diffusion, thinc, phase_field, capillary_hodge]
sources:
  - path: artifacts/A/cls_reinit_free_survey_CHK-RA-CLS-001.md
    description: "ResearchArchitect survey artifact for reinit-free/reinit-minimized LS/CLS routes"
  - description: "Guermond, Quezada de Luna, Thompson (2017), conservative anti-diffusion CLS, DOI 10.1016/j.cam.2017.02.016"
  - description: "Sabelnikov, Ovsyannikov, Gorokhovski (2014), modified level-set equation, DOI 10.1016/j.jcp.2014.08.018"
  - description: "Bothe, Fricke, Soga (2024), mathematical analysis of modified level-set equations, DOI 10.1007/s00208-024-02868-y"
  - description: "Shao, Yuan, Chai, Jin, Luo (2023), generalized variational LS for gas-liquid flows, DOI 10.1016/j.jcp.2023.112558"
  - description: "Sun and Beckermann (2007), sharp interface tracking using phase-field equation, DOI 10.1016/j.jcp.2006.05.025"
  - description: "THINC/CSLS literature, including Xiao et al. (2005), Ii et al. (2012), and Xiong et al. (2023)"
depends_on:
  - "[[WIKI-T-007]]"
  - "[[WIKI-T-036]]"
  - "[[WIKI-T-065]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-160]]"
  - "[[WIKI-X-027]]"
consumers:
  - domain: theory
    usage: "Choose candidate routes when reinitialization defects destabilize capillary CLS"
  - domain: experiment
    usage: "Design PoC gates for profile-control flux, THINC/CSLS, or modified-phi tests"
  - domain: code
    usage: "Guard against treating reinit-free methods as silent capillary-work projections"
compiled_by: ResearchArchitect
compiled_at: "2026-05-07"
---

# Reinitialization-Free CLS Survey

## Claim

Reinitialization-free LS/CLS is not achieved by setting `reinit_every=0`.
Successful research routes move the profile-maintenance duty into either:

1. a monolithic conservative anti-diffusion CLS update;
2. a modified/variational LS equation that preserves the geometry gauge;
3. a conservative phase-field or THINC carrier that replaces SDF transport;
4. a hybrid carrier/geometry split such as THINC + LS.

## Project Verdict

The least disruptive PoC is conservative anti-diffusion CLS:

```text
psi_t + div(psi u) = conservative transport + profile-control face flux
```

where profile control is part of the physical-time update, not a pseudo-time
projection after transport.

The second serious route is THINC/CSLS:

```text
mass carrier: THINC/volume fraction
geometry: reconstructed LS/phi
capillary: T_h^* dS_h in the production face metric
```

Modified/variational LS is useful mainly as a `phi` gauge stabilizer. It is not
a standalone replacement for CLS mass transport unless paired with a conservative
carrier.

## Required Gate

Any candidate must pass the reinit-aware capillary Hodge contract:

```text
profile control may not silently change Gamma or S_h
static equilibrium        <=> P_h c_sigma = 0
dynamic capillary release <=> P_h c_sigma != 0
```

If profile control changes trace surface energy, that change must be reported as
`Delta S_profile_control`, not mixed into physical capillary work.

## Candidate Ranking

| Rank | Candidate | Reading |
|---|---|---|
| 1 | Conservative anti-diffusion CLS | Closest to current CLS, removes pseudo-time reinit event. |
| 2 | THINC/CSLS | Strong mass/shape route; changes carrier/geometry split. |
| 3 | Modified `phi` equation | Good gauge stabilizer, needs `psi` or volume carrier for mass. |
| 4 | Conservative phase-field | Robust but changes model class and energy interpretation. |
| 5 | GALS/jet LS | Reduces reinit pressure; not a full deletion in two-phase flow. |

## Do Not Use As A Fix

- Do not disable reinit without profile-control replacement.
- Do not hide profile-control error behind global mass correction.
- Do not replace production capillary force by blanket range projection.
- Do not treat phase-field mobility or THINC reconstruction as cost-free if it
  changes surface energy.

## References

- [CHK-RA-CLS-001 artifact](../../../artifacts/A/cls_reinit_free_survey_CHK-RA-CLS-001.md)
- [WIKI-X-027](../cross-domain/WIKI-X-027.md)
- [WIKI-T-159](WIKI-T-159.md)
- [WIKI-T-160](WIKI-T-160.md)
