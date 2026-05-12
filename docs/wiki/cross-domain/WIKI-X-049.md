---
ref_id: WIKI-X-049
title: "AO-Fast Capillary Admission and Chapter 14 YAML Boundary"
domain: cross-domain
status: ACTIVE
tags: [ao_fast, ch14, yaml, fail_close, capillary, state_space]
sources:
  - path: docs/wiki/theory/WIKI-T-169.md
    description: "Geometric cell-fraction and AO-Fast theory card"
  - path: docs/wiki/experiment/WIKI-E-063.md
    description: "U12/V11 executable AO-Fast capillary split gate"
  - path: artifacts/A/ch14_capillary_mainline_rerun_CHK-RA-CH14-AO-FASTVOL-030.md
    description: "Mainline Chapter 14 capillary rerun on standard production stack"
  - path: artifacts/A/ch14_yaml_state_space_update_CHK-RA-CH14-AO-FASTVOL-032.md
    description: "Historical Chapter 14 diffuse-CLS YAML contract later superseded by AO-Fast YAML corrections"
  - path: artifacts/A/ch14_capillary_ao_fast_yaml_correction_CHK-RA-CH14-AO-FASTVOL-035.md
    description: "Correction restoring the checked-in Chapter 14 capillary-wave YAML to AO-Fast"
  - path: artifacts/A/ch14_all_yamls_ao_fast_contract_CHK-RA-CH14-AO-FASTVOL-036.md
    description: "Correction extending AO-Fast to all checked-in Chapter 14 YAMLs"
depends_on:
  - "[[WIKI-T-169]]"
  - "[[WIKI-E-063]]"
  - "[[WIKI-X-041]]"
consumers:
  - domain: theory
    usage: "Separate AO-Fast pressure-reaction theory from standard capillary benchmark claims"
  - domain: experiment
    usage: "Select the right Ch12/Ch13/Ch14 gate before running or interpreting capillary cases"
  - domain: code
    usage: "Reject implicit state-space/fallback mixing at config boundaries"
  - domain: paper
    usage: "Keep Chapter 14 benchmark claims distinct from AO-Fast diagnostic failures"
compiled_by: ResearchArchitect
compiled_at: 2026-05-12
---

# AO-Fast Capillary Admission and Chapter 14 YAML Boundary

## Retrieval Rule

Before using any AO-Fast capillary result, route through:

```text
WIKI-T-169  theory and YAML contract
WIKI-E-063  U12/V11 executable admission gates
```

Do not start from Chapter 14 production plots when the question is AO-Fast
admission.  All checked-in Chapter 14 YAMLs now explicitly declare AO-Fast
`geometric_cell_fraction`, q transport, and `bundle_virtual_work`.

## Boundary Between Three Capillary Meanings

| Route | YAML signature | Accepted reading |
|---|---|---|
| AO-Fast Chapter 14 | `interface.state_space.kind: geometric_cell_fraction`, q transport, `bundle_virtual_work`, active GPU contract | Capillary wave, Rayleigh--Taylor, static droplet, oscillating droplet, and rising bubble all use the AO-Fast YAML route. |

The boundary is intentionally visible in YAML.  It prevents a stale diffuse-CLS
configuration from being mistaken for the requested AO-Fast run.

## Core Findings To Preserve

- Full pressure-image AO capillary splitting can erase the non-static
  capillary drive exactly; this is a counterexample, not a balanced-force
  success.
- A nonzero nodal Young--Laplace residual is not sufficient.  The admitted
  physical object is the face-work residual after subtracting the correct
  pressure-reaction subspace.
- Component-Hodge readings are probes until the final `R_p(q_T)` theorem is
  proven.
- Non-static zero-drive AO packets fail close.  They do not switch to hidden
  PCG, DC, dense direct AO, or CPU/host fallback.
- Flat/static zero-drive controls must still be accepted; fail-close gates must
  distinguish unresolved non-static packets from exact static cancellation.
- The checked-in Chapter 14 capillary-wave YAML must exercise AO-Fast q
  transport; running the diffuse-CLS curvature-jump route for this case is a
  configuration error.

## Experiment Routing

Use this routing:

```text
U12: algebraic split gate.
V11: integration pre-gate and pressure-history comparison.
Ch14: physical production benchmark only after the route is already admitted.
```

If a long AO-Fast capillary run blows up, treat the long run as a terminal
symptom.  Return to the ladder in `WIKI-T-169`: algebraic certificate,
one-step capillary impulse, two-step pressure-history replay, short horizon,
then fractional-period horizon.

## Rejected Shortcut Interpretations

Do not write or read the result as:

```text
AO-Fast failed because CFL was too large.
AO-Fast can continue by silently falling back to PCG/DC.
component-Hodge probe is the production pressure-reaction split.
Chapter 14 standard capillary success proves AO-Fast success.
V11 old common-flux admissibility proves AO-Fast capillary admissibility.
```

Each of these interpretations was falsified or made stale by the current
theory and gates.
