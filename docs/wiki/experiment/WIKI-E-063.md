---
ref_id: WIKI-E-063
title: "U12/V11 AO-Fast Capillary Split Gates"
domain: experiment
status: ACTIVE
tags: [ao_fast, capillary, fail_close, gpu, ch12, ch13]
sources:
  - path: artifacts/A/paper_ch12_13_ao_gate_experiments_CHK-RA-CH14-AO-FASTVOL-031.md
    description: "Remote GPU U12/V11 AO-Fast gate execution and paper reflection"
  - path: experiment/ch12/exp_U12_ao_capillary_split_gate.py
    description: "Chapter 12 algebraic AO-Fast capillary split gate"
  - path: experiment/ch13/exp_V11_ao_capillary_split_gate.py
    description: "Chapter 13 AO-Fast integration pre-gate"
  - path: artifacts/A/ch14_ao_rung0_algebraic_rca_CHK-RA-CH14-AO-FASTVOL-029.md
    description: "Rung-0 diagnostic source for CPU exact, component-Hodge, and GPU packet comparison"
depends_on:
  - "[[WIKI-T-169]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-X-041]]"
consumers:
  - domain: experiment
    usage: "Use before treating any AO-Fast capillary run as a production benchmark"
  - domain: paper
    usage: "Use for U12/V11 wording and for separating diagnostic gates from Chapter 14 physics claims"
  - domain: code
    usage: "Use as acceptance evidence for fail-close behavior, not as AO-Fast production admission"
compiled_by: ResearchArchitect
compiled_at: 2026-05-12
---

# U12/V11 AO-Fast Capillary Split Gates

## Purpose

U12 and V11 are negative/admission gates for AO-Fast capillarity.  They do not
advance Navier--Stokes and do not certify a production AO-Fast benchmark.  They
ask whether the current AO-Fast pressure-reaction split can be admitted into
the Chapter 14 physical path.

## Executed Commands

```text
make cycle EXP=experiment/ch12/exp_U12_ao_capillary_split_gate.py ARGS='--require-gpu'
make cycle EXP=experiment/ch13/exp_V11_ao_capillary_split_gate.py ARGS='--require-gpu'
```

Both runs executed on the remote GPU host.

## U12 Result

| case | CPU exact balanced drive | component-Hodge probe | GPU packet |
|---|---:|---:|---|
| flat N32 | `0.000000e+00` | `0.000000e+00` | `ok`, no fail-close |
| wave N32 | `0.000000e+00` | `2.117576e+00` | `ok`, fail-close |
| wave N64 | `0.000000e+00` | `2.305484e+00` | `ok`, fail-close |

Reading: full pressure-image cancellation is exact for the wave and is a
counterexample, not a success.  The component-Hodge value is a non-staticity
probe, not the final pressure-reaction subspace.

## V11 Result

| case | component-Hodge probe | GPU packet |
|---|---:|---|
| flat N32 pressure-coordinate | `0.000000e+00` | `ok`, no fail-close |
| wave N32 pressure-coordinate | `2.117576e+00` | `ok`, fail-close |
| wave N32 face-acceleration | `2.117576e+00` | `ok`, fail-close |
| wave N64 pressure-coordinate | `2.305484e+00` | `ok`, fail-close |

Reading: changing the pressure-history representation from
`pressure_coordinate` to `face_acceleration` does not admit the current AO-Fast
packet.  The unresolved problem is the pressure-reaction split, not a local
history-format or CFL patch.

## Admission Rule

AO-Fast capillarity remains closed until it supplies a pressure-reaction
subspace `R_p(q_T)` and evaluates

```text
r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma
```

with a residual-certified accuracy budget.  Hidden fallback to PCG, DC,
component-Hodge, dense CPU direct AO, or a host-controlled GPU path is not an
accepted result.  Fallback is admissible only if the YAML names an explicit
chain and records the transition.

## Stale Experiment Removed

`experiment/ch13/exp_V11_common_flux_admissibility.py` is stale for this
question.  It tested an earlier common-flux transport admissibility route and
does not answer whether AO-Fast capillary pressure reaction is physically
admissible.  It should not be cited as a V11 AO-Fast pass.
