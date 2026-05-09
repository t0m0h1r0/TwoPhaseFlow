---
ref_id: WIKI-T-168
title: "Constrained Face-State Space Reformulation"
domain: theory
status: ACTIVE
tags: [state_space, common_flux, no_slip, hodge_projection, boundary, gpu]
sources:
  - path: docs/memo/short_paper/SP-AN_constrained_face_state_space.md
    description: "State-space reformulation after boundary-Hodge KKT rank probe"
  - path: artifacts/A/boundary_hodge_coupled_kkt_rank_rca_CHK-RA-CH14-BHODGE-KKT-RANK-001.md
    description: "Rank/conditioning evidence motivating the reformulation"
depends_on:
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-164]]"
  - "[[WIKI-T-165]]"
  - "[[WIKI-T-166]]"
  - "[[WIKI-T-167]]"
consumers:
  - domain: code
    usage: "Use before implementing boundary-constrained production velocity space"
  - domain: experiment
    usage: "Use S1--S8 gates before long wall-bounded rising-bubble reruns"
  - domain: theory
    usage: "Use as the active production direction beyond the additive KKT reference"
compiled_by: ResearchArchitect
compiled_at: "2026-05-09"
---

# Constrained Face-State Space Reformulation

## Claim

The production velocity state for wall-bounded common-flux flow should live in:

```text
F_w = { f in F_h : C_w f = B_h R_h f = 0 }.
```

Pressure projection is then performed inside this space:

```text
f_new = P_w f_dag - P_w G_A p,
D_h f_new = 0,
```

where

```text
P_w = I - M_f^{-1} C_w^T (C_w M_f^{-1} C_w^T)^+ C_w.
M_f = Q_f rho_f.
```

## Why This Replaces The Additive Production KKT

The old route added a wall multiplier to the full face space:

```text
f = f_dag - G_A p - M_f^{-1} C_w^T lambda.
```

It remains a useful diagnostic reference, but the rank probe showed:

```text
full wall:      feasible but dt-scaled conditioning is poor
periodic_wall:  production [G_A, C_w^T] basis is rank deficient
```

The new route treats `P_w` as the state-space chart, not as a post-correction.
The pressure operator becomes:

```text
D_h P_w G_A.
```

## Gates

```text
P_w^2 = P_w
P_w is M_f-self-adjoint
C_w P_w = 0
restricted Green identity holds for G_w=P_wG_A
rank(D_h P_w G_A) = rank(D_h | F_w)
||D_h f||, ||C_w f||, ||u-R_hf||, ||m-rho u|| all pass together
```

## Implemented Slice

Current code implements the GPU-first building block:

```text
restricted_pressure_fluxes(p) = P_w G_A(p)
```

in `src/twophase/simulation/boundary_hodge.py`.  It is a matrix-free helper and
diagnostic operator, not yet a production PPE replacement.  The canonical
`ch14_rising_bubble.yaml` records `state_space: constrained_face` and
`pressure_pairing: restricted_variational_adjoint` with `mode: off`.

## Validation Status

Efficient operator probes showed that the metric must be the geometric
transported face mass `Q_f rho_f`, not face density alone.  The density-only
version broke the restricted Green identity at order one.  After the metric
correction, full-wall probes pass:

```text
restricted Green relative residual = 8.826843e-17
rank(D_h P_w G_A) = rank(D_h | F_w) = 19
manufactured K_w recovery relative error = 1.537101e-14
manufactured divergence L2 = 4.713074e-13
manufactured wall-trace Linf = 5.532534e-31
```

Mixed `periodic_wall` remains fail-closed until topology quotients are rebuilt:

```text
rank(D_h P_w G_A) = 27,
rank(D_h | F_w)   = 30,
restricted Green relative residual = 1.037769e-01.
```

## Negative Knowledge

Do not use as production fixes:

```text
wall-only projection after pressure,
generic D_h^T pressure substitute,
dense CPU KKT,
nodal post-clamp,
boundary-face zeroing,
penalty slip,
damping/CFL/smoothing/DCCD/UCCD suppression.
```

Read SP-AN for the full derivation and implementation ladder.
