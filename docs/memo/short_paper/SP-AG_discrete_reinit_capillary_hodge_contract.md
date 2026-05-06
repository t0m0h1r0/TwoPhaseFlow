# SP-AG: Discrete Reinit-Aware Capillary Hodge Contract

**Status**: REFERENCE / negative research memo
**Date**: 2026-05-06
**Scope**: ch14 capillary validation, discrete pressure-Hodge force, Ridge-Eikonal reinitialization, abandoned implementation route
**Companion papers**: SP-AF, SP-AE, SP-AD, SP-AC, SP-AA

## 2026-05-06 Curation Note

This memo is preserved for the discrete bookkeeping it established, but it is
not an implementation instruction.  The later fixed-stratum retraction
candidate in SP-AH/WIKI-T-161 was tested as a ch14 route and abandoned after
N=32, T=10 validation produced abnormal long-time droplet shape.  The
remaining general lesson is still useful: labelled transport, pressure-Hodge
cochains, and explicit reinit defect ledgers are required before any capillary
diagnosis can be trusted.

## Abstract

SP-AF established the reinit-aware capillary theory as a split-map variational
contract.  This memo pins down the fully discrete version.  The objects are no
longer continuum placeholders: they are finite spaces, mass pairings, transport
maps, pressure ranges, KKT constraints, and diagnostics that a future route
would have to implement without static/oscillating-droplet switches.

The state update is:

```text
q^n -- T_h(u_f) --> q_T
q_T -- Pi_Ridge --> q^{n+1}.
```

Capillary force is the face-space cochain obtained from the adjoint of the
physical transport map:

```text
(c_sigma,w_f)_F = -sigma (g_T,L_T(q^theta)w_f)_Q.
```

Reinitialization is a constrained representation projection.  It may repair
the Ridge-Eikonal/profile field, but it may not silently become a body force,
pressure force, capillary force, damping term, or benchmark-specific correction.

## 1. Discrete State

Use the following finite spaces:

```text
C_h    cell/control-volume space
F_h    oriented face set
Q_h    interface carrier space, such as psi
Phi_h  metric/profile space, such as signed-distance-like phi
U_h    normal face velocity space
P_hs   pressure scalar space
```

The inner products are part of the theorem:

```text
(x,y)_Q = x^T M_Q y
(u,v)_F = u^T M_F v
(p,r)_P = p^T M_P r.
```

`M_Q`, `M_F`, and `M_P` must contain the production grid metrics, face
control volumes, density factors, and phase weights.  A Euclidean substitute is
a different numerical theory.

## 2. Operators and Range

The pressure/corrector complex is:

```text
D_F : U_h -> C_h
G_F : P_hs -> U_h
B_F = A_F G_F
R_h = range(B_F).
```

`A_F` is the same face coefficient used by the production velocity corrector.
The pressure range `R_h` is therefore not an abstract gradient range; it is the
actual acceleration range available to the discrete momentum step.

The interface transport map is:

```text
T_h(q,u_f) = q - dt D_q( diag(P_F q^theta) u_f ),
L_T(q^theta)w_f = -D_q( diag(P_F q^theta) w_f ).
```

`P_F q` and `D_q` must be the projection-native CLS face reconstruction and
carrier-space divergence used by the solver.

## 3. Surface Energy Endpoint

Let `tau_h : Q_h -> A_h` extract the trace/interface degrees of freedom.  The
physical surface energy is:

```text
S_h(q) = S_h(tau_h(q)).
```

Off-interface changes in `q` or `phi` are representation changes unless they
move `tau_h`.  Therefore the capillary discrete gradient is built on the
physical transport endpoint:

```text
(g_T,q_T-q^n)_Q = S_h(q_T) - S_h(q^n).
```

The endpoint is `q^n -> q_T`, not `q^n -> q^{n+1}`, unless the reinitialization
map is proven trace and surface-energy preserving.

## 4. Capillary Cochain

For every admissible face velocity `w_f`, the capillary virtual work is:

```text
(c_sigma,w_f)_F = -sigma (g_T,L_T(q^theta)w_f)_Q.
```

In matrix form:

```text
c_sigma = -sigma M_F^{-1} L_T(q^theta)^T M_Q g_T.
```

This is the discrete definition of the capillary force.  Curvature jumps,
pressure representatives, visual pressure fields, and range projections are
valid only if they reproduce this virtual-work identity in the same weighted
face space.

## 5. Pressure-Hodge Gate

The production pressure step uses the full cochain:

```text
D_F B_F p = r_h + D_F c_sigma
a_f = B_F p - c_sigma
u_f^{n+1} = u_f^* - dt a_f.
```

The pressure representative is diagnostic:

```text
p_sigma = argmin_p ||B_F p - c_sigma||_{M_F}^2
Pi_R c_sigma = B_F p_sigma
h_sigma = c_sigma - Pi_R c_sigma.
```

The static/dynamic decision is:

```text
static equilibrium        <=> ||h_sigma||_{M_F} <= tol_static ||c_sigma||_{M_F}
dynamic capillary release <=> ||h_sigma||_{M_F} >= tol_release ||c_sigma||_{M_F}.
```

Replacing the production cochain by `Pi_R c_sigma` deletes `h_sigma`.  That
keeps a static droplet quiet, but it also freezes a deformed droplet released
from rest.  It is a force deletion, not a theory.

## 6. Reinitialization as KKT Projection

Ridge-Eikonal/profile reinitialization is:

```text
(q^{n+1},phi^{n+1}) = Pi_Ridge(q_T,phi_ref).
```

For fixed topology it is a constrained projection:

```text
minimize    1/2 ||q-q_T||_W^2 + 1/2 ||phi-phi_ref||_Z^2
subject to  C_H(q,phi) = q - H_eps(-phi) = 0
            C_E(phi) = 0
            C_V(q) = V_h(q) - V_h(q^n) = 0
            C_tau(q) = tau_h(q) - tau_h(q_T) = 0
            C_S(q) = S_h(q) - S_h(q_T) = 0.
```

The KKT multipliers belong to this representation problem.  They are not
pressure, body force, or hidden surface tension.

An identity-preserving reinit satisfies:

```text
tau_h(q^{n+1}) = tau_h(q_T)
S_h(q^{n+1}) = S_h(q_T)
V_h(q^{n+1}) = V_h(q^n).
```

If these fail, define:

```text
Delta_tau_Pi = tau_h(q^{n+1}) - tau_h(q_T)
Delta_S_Pi   = S_h(q^{n+1}) - S_h(q_T)
Delta_V_Pi   = V_h(q^{n+1}) - V_h(q^n).
```

These are projection defects or declared metric/topology events, not capillary
work.

## 7. Energy Ledger

For fixed topology and no external work:

```text
K^{n+1} - K^n
+ sigma [S_h(q_T) - S_h(q^n)]
+ D_visc
+ D_metric
= R_num.
```

The stored surface change splits as:

```text
S_h(q^{n+1}) - S_h(q^n) = Delta_S_T + Delta_S_Pi.
```

Only `Delta_S_T = S_h(q_T)-S_h(q^n)` is reversible capillary work.
`Delta_S_Pi` is a reinitialization/projection term.

## 8. Discrete Theorems

**Static equilibrium**.  With identity-preserving reinit, transport-adjoint
`c_sigma`, and the production pressure/corrector range, a zero-predictor state
remains at rest if and only if `h_sigma = 0` within tolerance.

**Dynamic release**.  Under the same assumptions, if `h_sigma != 0`, a
zero-predictor release has first-step kinetic response:

```text
K^1 = 1/2 dt^2 ||h_sigma||_{M_F}^2 + O(dt^3) + viscous/splitting terms.
```

**Reinit invariance**.  If `Pi_Ridge` preserves trace and surface energy, then:

```text
d S_h(Pi_Ridge(T_h(u))) / du = d S_h(T_h(u)) / du.
```

**Reinit defect is not force**.  At `u_f=0`, `q_T=q^n`.  Any trace or surface
energy change after reinitialization is a projection defect unless a separate
metric/topology model has been declared.

## 9. Required Gates

The implementation must expose and test:

```text
G0  labelled states:
    q_before_transport, q_after_transport_before_reinit,
    q_after_reinit, phi_after_reinit

G1  discrete-gradient identity:
    (g_T,q_T-q^n)_Q = S_h(q_T)-S_h(q^n)

G2  transport virtual work:
    (c_sigma,w_f)_F + sigma (g_T,L_T w_f)_Q = 0

G3  reinit identity/defect:
    Delta_tau_Pi, Delta_S_Pi, Delta_V_Pi

G4  static Hodge residual:
    ||h_sigma||_{M_F}/max(||c_sigma||_{M_F},eps)

G5  dynamic release:
    nonzero h_sigma and dt^2 kinetic response

G6  energy ledger:
    Delta_K, Delta_S_T, Delta_S_Pi, D_visc, D_metric, R_num
```

## 10. ch14 Consequence

The oscillating-droplet failure is explained by two contract violations:

1. pressure-range replacement deleted the Hodge component required for
   capillary release;
2. every-step reinitialization changed deformation diagnostics even when face
   velocity was machine zero.

The repair is not a benchmark switch.  The repair is:

```text
build c_sigma from labelled transport,
apply full c_sigma in the pressure/corrector path,
use weighted Hodge projection only as a diagnostic/certificate,
make reinit trace/energy preserving or charge its defect explicitly.
```

## Conclusion

The final discrete contract is:

```text
spaces + weighted pairings
+ labelled transport endpoint
+ KKT reinitialization projection
+ transport-adjoint surface-energy cochain
+ production pressure-Hodge corrector
+ explicit reinit defect ledger.
```

This is the generic route.  It lets a true discrete Young-Laplace equilibrium
stay still, while requiring a non-equilibrium deformed droplet to move.
