# CHK-RA-CH14-STATE-SPACE-001: Constrained Face-State Space Reformulation

## Prompt

Revisit whether the boundary-Hodge route is becoming a cul-de-sac and attempt a
more fundamental reformulation of the discrete state space.  Preserve what was
wrong as reusable knowledge.

## Diagnosis

The previous work correctly found the target condition:

```text
D_h f = 0,
C_w f = B_h R_h f = 0,
u = R_h f,
m = rho u.
```

The weak point was not this target.  The weak point was the route:

```text
unconstrained face space F_h
  -> pressure projection in F_h
  -> wall correction / nodal wall clamp
```

This route leaves the code reasoning about two states: the face state used for
common-flux transport and the nodal no-slip state used for momentum
publication.  The additive KKT version repairs this by adding a wall multiplier,
but it still uses the unconstrained face space as the ambient production chart.

The rank probe made the issue concrete:

```text
full wall:      rank condition can pass, but dt scaling makes the KKT hard
periodic_wall:  current production pressure basis is rank deficient
```

This points to state-space design, not to damping, CFL, or a missing parameter.

## Reformulated State Space

Define the admissible wall-constrained face space first:

```text
F_w = ker C_w,
C_w = B_h R_h.
```

The final incompressible velocity space is:

```text
K_w = F_w cap ker D_h.
```

The nodal state is dependent:

```text
u = R_h f,
m = rho u.
```

The metric wall retraction is:

```text
P_w = I - M_f^{-1} C_w^T (C_w M_f^{-1} C_w^T)^+ C_w.
```

The accepted pressure solve should be posed in `F_w`:

```text
f_new = P_w f_dag - P_w G_A p,
D_h f_new = 0.
```

Therefore the pressure operator is:

```text
D_h P_w G_A.
```

This differs fundamentally from the rejected post-projection:

```text
bad:  f_new = P_w(f_dag - G_A p_old)
good: p solves D_h(P_w f_dag - P_w G_A p)=0
```

## Candidate Foundations

| Route | Summary | Theoretical status | Production suitability |
|---|---|---|---|
| A | Constrained face-state space `F_w=ker C_w` | Best fit to common-flux: keeps `f` primary and makes no-slip a state-space property. | Preferred next route. |
| B | Nodal no-slip primary space `U_0`, with `f=F_hu` | No-slip is natural, but face flux becomes derived. | Possible but more invasive to common-flux transport. |
| C | Full mixed/FEEC or MAC-like redesign | Cleanest mathematical complex. | Too large for the next implementation slice. |
| D | Additive full-space KKT | Valid diagnostic reference. | Not preferred as production chart after rank/conditioning evidence. |

## What To Retain As Negative Knowledge

The following were not wasted work; they now define guardrails:

- `C_w=B_hR_h` is the correct no-slip trace, not boundary-face zeroing.
- `P_w` is valid as a metric wall retraction, but invalid as a final
  post-pressure repair.
- A nodal wall clamp creates two velocities and violates the common-flux
  state ledger.
- Generic `D_h^T` cannot replace `G_A`; the pressure complex must remain
  variational and source-aware.
- Mixed periodic-wall topology must be handled as a quotient before rank gates.
- Damping, CFL reduction, smoothing, DCCD/UCCD suppression, and penalty slip
  are not fixes for an equality-constraint state-space mismatch.

## Next Verification Gates

The next efficient ladder is:

```text
S1  P_w idempotence
S2  P_w M_f-self-adjointness
S3  C_w P_w = 0 for wall and periodic_wall
S4  restricted Green identity for G_w=P_wG_A
S5  rank(D_h P_w G_A) = rank(D_h | F_w)
S6  manufactured projection in K_w
S7  one-step rising-bubble state identity
S8  short N=32x64 rising-bubble run plus droplet/capillary regressions
```

Long experiments should not run before S1--S6 pass.

## Deliverables

- Added `SP-AN_constrained_face_state_space.md`.
- Added `WIKI-T-168`.
- Reclassified SP-AM/WIKI-T-167 as the KKT diagnostic/reference path rather
  than the active production route.
- Updated retrieval routing so future sessions start from the constrained
  face-state formulation before proposing boundary-Hodge implementation work.
