---
ref_id: WIKI-T-162
title: "Closed-Interface Capillary Discretization Policy"
domain: theory
status: ACTIVE
tags: [capillary, discrete_variational, hodge_projection, pressure_jump, closed_interface, implementation_policy]
sources:
  - path: docs/memo/short_paper/SP-AI_closed_interface_capillary_discretization_policy.md
  - path: artifacts/A/capillary_variational_rigor_CHK-RA-CH14-CAP-VARIATIONAL-RIGOR-001.md
  - path: artifacts/A/capillary_variational_theory_closure_CHK-RA-CH14-CAP-VARIATIONAL-THEORY-001.md
  - path: artifacts/A/capillary_remedy_candidates_CHK-RA-CH14-CAP-REMEDY-001.md
  - path: artifacts/A/capillary_closed_interface_cochain_rca_CHK-RA-CH14-CAP-VOL-001.md
  - path: artifacts/A/capillary_virtual_work_gate_rca_CHK-RA-CH14-CAP-VW-001.md
  - path: docs/02_ACTIVE_LEDGER.md
depends_on:
  - "[[WIKI-T-155]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-157]]"
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-160]]"
  - "[[WIKI-T-161]]"
  - "[[WIKI-X-041]]"
---

# Closed-Interface Capillary Discretization Policy

## Claim

The accepted closed-interface capillary discretization is not a curvature
formula, range-projection option, or benchmark branch.  It is the
finite-dimensional weighted variational construction:

```text
s      = -M_f^{-1} T^T d(sigma S_h)^T
B      =  M_f^{-1} T^T [dV_1 ... dV_M]^T
K      = ker D intersection ker(B^T M_f)
R_aug  = K^{perp_M} = range(A G) + range(B)
Pi_aug = M_f-orthogonal projection onto R_aug
h      = s - Pi_aug s
```

`h` is the physical incompressible capillary drive, up to the code sign
convention.  The pressure reaction is `Pi_aug s`.

## Discretization Policy

Start from a fixed-topology trace stratum:

```text
component labels,
crossing edges,
cut points,
polygon adjacency,
orientation,
stratum id.
```

Define the geometry on that stratum:

```text
S_h(q)    = trace length/area,
V_m,h(q) = component volume/area.
```

Differentiate those exact discrete functionals, then pull them back to faces
through the pre-reinit transport Jacobian:

```text
T w = trace displacement induced by face velocity w.
```

Curvature samples are admissible only if they are proven equal to this Riesz
pullback in the production face metric.

## Projection Rule

Let:

```text
R = A G,
X = [R B].
```

The augmented pressure/component reaction must be the weighted normal
projection:

```text
X^T M_f X z = X^T M_f s.
```

Solving only:

```text
D(Rp + Bmu) = D s
```

is not enough unless the missing component orthogonality is proven redundant.
The required side condition is:

```text
B^T M_f (Rp + Bmu - s) = 0.
```

## Solver-Oriented Schur Form

Using the existing PPE solve:

```text
L = D R,
C = D B,
r = D s.
```

For component coefficient `mu`:

```text
p(mu) = L^+ (r - C mu),
q(mu) = R p(mu) + B mu - s.
```

The small component system is:

```text
S_B mu = y_B,
S_B = B^T M_f [B - R L^+ C],
y_B = B^T M_f [s - R L^+ r].
```

Then:

```text
h = s - R p - B mu.
```

This is the normal equation reduced to the component subspace, not a fallback.

## Reinit Rule

The theorem applies only to the physical transport arrow:

```text
q^n -> q_T.
```

The reinit arrow:

```text
q_T -> q^{n+1}
```

must report trace, surface-energy, volume, and topology-stratum changes
separately.  Reinit changes are not reversible capillary work.

## Required Gates

Before production use:

```text
1. Riesz pullback:
   <s,w>_M + d(sigma S_h)[T w] = 0
   <b_m,w>_M - dV_m[T w] = 0.

2. SBP:
   <A G p,w>_M + <p,Dw>_C = boundary(p,w).

3. Component range:
   ||H_R b_m||_M / ||b_m||_M is measured for every component.

4. Projection equivalence:
   implemented residual equals s - X(X^T M_f X)^+X^T M_f s.

5. Fixed-stratum derivatives:
   dS_h and dV_m pass centered finite-difference sweeps.

6. Noncritical completeness:
   arbitrary resolved admissible modes with nonzero first variation give h != 0.

7. Reinit ledger:
   S_h and V_m are split between q^n->q_T and q_T->q^{n+1}.
```

## Negative Knowledge

Do not use as production fixes:

```text
blanket c -> Pi_R c,
capillary_range_projection:none without Riesz proof,
curvature mean/null-mode calibration without variational equivalence,
component DOF in diagnostics only,
divergence-only augmented solve without B^T M_f orthogonality,
damping/CFL/caps/smoothing,
FD/WENO/PPE fallback,
benchmark-name branching.
```

## Implementation Target

The first implementation should be diagnostic-only and expose:

```text
ClosedInterfaceStratum
CapillaryVariationalCochain
M_f, D, R, T, S_h, V_m, s, B
Riesz residuals
component range residuals
normal-equation projection residuals
reinit stratum ledger
```

Production may use the cochain only after those gates pass.
