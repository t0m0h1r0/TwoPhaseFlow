---
ref_id: WIKI-T-167
title: "Discrete Boundary-Constrained Face Hodge Operator"
domain: theory
status: REFERENCE
tags: [discretization, hodge_projection, no_slip, wall_boundary, face_state, gpu, common_flux]
sources:
  - path: docs/memo/short_paper/SP-AM_boundary_hodge_discretization.md
    description: "Implementation-ready discretization of SP-AL"
  - path: docs/memo/short_paper/SP-AL_boundary_constrained_face_hodge.md
    description: "Continuous/KKT formulation of boundary-constrained face Hodge projection"
  - path: docs/wiki/theory/WIKI-T-166.md
    description: "Theory card for boundary-constrained face Hodge projection"
depends_on:
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-164]]"
  - "[[WIKI-T-165]]"
  - "[[WIKI-T-166]]"
consumers:
  - domain: code
    usage: "Use as the operator contract for implementing constrained_kkt boundary_hodge"
  - domain: experiment
    usage: "Use T1--T8 gates before long rising-bubble runs"
  - domain: theory
    usage: "Use for discrete adjoint, KKT, and metric details after SP-AL"
compiled_by: ResearchArchitect
compiled_at: "2026-05-09"
---

# Discrete Boundary-Constrained Face Hodge Operator

## Status Note

This card is now the additive KKT reference and diagnostic contract.  For the
active production direction, read [[WIKI-T-168]] first: define the constrained
face-state space `F_w=ker C_w`, then build the pressure projection through
`D_h P_w G_A`.

## Claim

The implementation target is a matrix-free constrained projection over existing
FCCD face operators plus a new wall trace operator:

```text
D_h   = divergence_from_faces
R_h   = reconstruct_nodes
G_A   = pressure_fluxes(... variational_adjoint ...)
C_w   = B_h R_h
M_f   = transported face-mass metric
```

The solve is:

```text
f = f_dag - dt G_A p - dt M_f^{-1} C_w^T lambda,
D_h f = 0,
C_w f = 0.
```

## Required New Operators

```text
wall_trace_from_faces(faces) -> trace
wall_trace_adjoint(lambda) -> face_covector
inv_face_mass_apply(face_covector, rho) -> face_acceleration
```

The wall trace adjoint must pass:

```text
<lambda, C_w f>_W = <C_w^T lambda, f>_F.
```

## Matrix-Free Block

For unknown `(p, lambda)`:

```text
apply_Ap(p):
  gp = pressure_fluxes(p, rho, active kwargs)
  return D_h gp, C_w gp

apply_Al(lambda):
  wl = M_f^{-1} C_w^T lambda
  return D_h wl, C_w wl
```

RHS:

```text
rhs_p = D_h f_dag / dt
rhs_l = C_w f_dag / dt.
```

The corrected state is:

```text
f_new = f_dag - dt pressure_faces - dt wall_faces
u_new = R_h f_new
m_new = rho u_new.
```

## Gates

```text
||D_h f_new||_inf       <= tolerance
||C_w f_new||_inf       <= tolerance
||u_new - R_h f_new||   <= tolerance
||m_new - rho u_new||   <= tolerance
```

## Rank Gate

Before `constrained_kkt` may be enabled as production, the actual runtime
operators must pass:

```text
A = [D_h; C_w]
B = [G_A, M_f^{-1}C_w^T]
rank(A B) = rank(A)
```

Small-grid diagnostic evidence:

```text
wall:          rank(A B)=59/59; feasible but needs dt scaling/preconditioning
periodic_wall: rank(A B)=49/52; not production-ready with current quotient
```

Do not bypass this by substituting a generic dense `D_h^T` for `G_A`; that would
hide a pressure-complex mismatch instead of preserving the variational pressure
contract.

## Rejected Discretizations

Do not use:

```text
boundary-face zeroing as a substitute for C_w,
nodal post-clamping after publication,
face recomputation from clamped nodes without Hodge projection,
dense CPU KKT as the production route,
penalty slip as the physical scheme.
```

## Test Ladder

Run before long experiments:

```text
T1 wall trace adjoint identity
T2 manufactured wall projection
T3 manufactured pressure projection
T4 coupled pressure+wall projection
T5 sigma=g=0 zero state
T6 static circular droplet
T7 one-step rising-bubble wall-mismatch regression
T8 N=32x64 T=0.002 short run
```

Read SP-AM for the full discretization.
