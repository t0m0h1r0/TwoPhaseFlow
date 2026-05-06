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

## Component-Augmented Implementation Slice

The first implemented production candidate is the one-component version of the
augmented Hodge theorem.  It does not identify a shape as circular or
elliptical.  It constructs the component reaction directly in the same
face-cochain complex as the pressure jump:

```text
c      = current capillary jump cochain
b      = unit constant component pressure-jump cochain
h_c    = c - Pi_R c
h_b    = b - Pi_R b
beta   = <h_c,h_b>_M / <h_b,h_b>_M
c_aug  = c - beta h_b
```

This is algebraically the projection onto `range(A G)+span(b)` because the
range part of `b` is already in `range(A G)` and only `h_b` expands the
pressure-range complement.  Consequences:

```text
static constant component reaction: h_c parallel h_b, so c_aug has no Hodge drive;
resolved nonconstant mode: only the unit reaction component is removed;
range_projected control: c -> Pi_R c remains a deletion of all Hodge drive.
```

The runtime mode is `capillary_range_projection: component_hodge_augmented`.
It uses the same `D_f,A_f,G_f`, affine-jump coefficient, pressure history, and
corrector face space as the production pressure stage.  It is still a first
slice, not the final trace/Riesz construction, because the raw `c` must still
be replaced by or verified against the full `s=-M_f^{-1}T^Td(sigma S_h)^T`
object on a fixed trace stratum.

## N32 T1 Validation Note

Remote-first checks on the ch14 stack used `N=32,T=1`, debug diagnostics, and
0.2-time snapshot figures.

| Case | Final KE | Max snapshot velocity Linf | Max corrected Hodge weighted L2 | Volume drift max | Reading |
|---|---:|---:|---:|---:|---|
| static droplet | `5.284015e-09` | `1.833331e-05` | `2.814614e-04` | `1.903440e-15` | bounded but not roundoff static |
| oscillating droplet | `3.643971e-04` | `9.417805e-03` | `4.477470e-02` | `2.428289e-15` | capillary drive restored |

The old `range_projected` production path produced essentially zero velocity
on the oscillating droplet because it replaced `c` by `Pi_R c`.  The new
one-component augmented mode restores nonzero Hodge drive while preserving
volume and PPE convergence.  The static residual is a remaining theorem
obligation, not a tuning target: it says the current scalar face-implicit
curvature cochain is still not the full transport-adjoint surface-energy
Riesz representative.

## Long Validation Note

The N32/T10 and N32/T20 validation separates three questions:

```text
1. Does the old zero-drive failure remain?          no
2. Is the static component reaction fully silent?  not yet at theorem level
3. Does the dynamic phase match Rayleigh-Lamb?     not yet
```

For the static droplet, `N=16,32,64` at `T=1` gave:

| N | final KE | max KE | max snapshot speed | max corrected Hodge weighted L2 | max volume drift |
|---:|---:|---:|---:|---:|---:|
| 16 | `1.490637e-07` | `1.490637e-07` | `9.070593e-05` | `8.428385e-04` | `1.223563e-15` |
| 32 | `5.284015e-09` | `5.284015e-09` | `2.492200e-05` | `2.814614e-04` | `1.903440e-15` |
| 64 | `1.138320e-09` | `2.542873e-09` | `1.941430e-05` | `5.893873e-04` | `3.159875e-15` |

The kinetic leakage improves strongly, but the corrected Hodge residual is
not monotone in `N`.  This means the current component-augmented scalar
cochain is a useful first slice, not a proof that the force is exactly
`T_h^* dS_h`.

For the oscillating droplet, reinit changes the physics-level judgement.  With
reinit every step at `N=32,T=10`, the first signed-deformation zero crossing
is `7.578596`, earlier than the Rayleigh-Lamb reference `9.381529`, and the
max corrected Hodge weighted L2 reaches `9.018738e-02`.  With reinit disabled,
there is no zero crossing by `T=10`; by `T=20`, the first zero crossing is
`13.393564`, later than the same reference, and the final signed deformation
is `-2.228711e-02` while the reference is `-7.454746e-02`.

Therefore the visually coherent pressure/velocity snapshots are not enough to
accept the method as final.  The old algebraic freeze is fixed, but the
remaining physical error is phase/amplitude fidelity and reinit work
contamination.  The next accepted route remains the fixed-stratum
transport-adjoint Riesz cochain:

```text
s = -M_f^{-1} T^T d(sigma S_h)^T
B =  M_f^{-1} T^T [dV_m]^T
```

and a stored `q^n -> q_T -> q^{n+1}` ledger that separates capillary transport
from reinitialization.

## Endpoint Ledger Implementation Slice

The first diagnostic implementation of the split ledger stores the endpoint
fields at snapshot steps:

```text
fields/psi_before_transport
fields/psi_after_transport_before_reinit
fields/psi_after_reinit
```

The same fields are preserved in checkpoint snapshots and reconstructed by the
plot-only runner.  This is not a force change.  It simply makes the state split
observable so later checks can measure

```text
q^n -> q_T      physical transport
q_T -> q^{n+1} reinit/profile/mass-closure projection
```

separately.  On a remote `N=16,T=0.04` endpoint smoke with reinit every step,
the exported NPZ contained all three arrays with shape `(3,17,17)`.  The
maximum physical-transport field delta was `6.436583e-07`, while the maximum
reinit-leg delta was `1.778247e-01`.  This confirms that reinit can dominate
the apparent shape change and must not be counted as capillary work.

## Phase-Error RCA

The remaining phase/static error is not caused by the one-component projection
removing the dynamic mode.  A remote `N=32,T=1` no-reinit probe with
`capillary_range_projection:none` gave the same early Rayleigh-Lamb stiffness
as `component_hodge_augmented`: `omega≈0.14017`, or about `70%` of the
reference stiffness.  The projection is still necessary for the static
component reaction: static `none` produced KE `5.026189e-06`, while static
component mode gave `5.284015e-09`.

The slow no-reinit phase is also not an early grid-remap artifact.  A
static-grid no-reinit `N=32,T=4` component probe gave `omega≈0.13976`, matching
the dynamic-grid no-reinit result through `T=4`.

The current cause is therefore force-side: the scalar `face_implicit`
capillary cochain, even after component augmentation, is not yet the
fixed-stratum Riesz representative of `d(sigma S_h)`.  It removes the constant
component reaction but does not provide the correct surface-energy Hessian for
resolved nonconstant modes.  Reinit is a separate measurement/energy
contaminant: it can shift phase and energy strongly, but it does not explain
the no-reinit under-stiffness.

## Full Implementation Target

The full implementation should expose:

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
