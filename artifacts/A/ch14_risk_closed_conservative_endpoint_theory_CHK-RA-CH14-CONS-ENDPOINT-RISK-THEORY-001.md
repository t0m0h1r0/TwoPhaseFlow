# CHK-RA-CH14-CONS-ENDPOINT-RISK-THEORY-001

## Question

Deepen the conservative face-psi endpoint theory by absorbing the risk audit
into the mathematics.  The goal is to remove ambiguous implementation choices
before code is changed.

The key risks are:

```text
endpoint/material time-level mismatch,
pressure range / metric mismatch,
component-reaction projection ambiguity,
corrector sign ambiguity,
GPU hot-path geometry ambiguity,
static-oracle ambiguity.
```

## Main Refinement

The production theorem must not be written as if

```text
range(G_A) = range(M_f^{-1}D_f^T)
```

is automatic.  In the real scheme, the pressure action is the implemented face
operator

```text
G_A p := div_op.pressure_fluxes(p, rho_c, zero_jump_kwargs),
```

where `A` includes phase-separated density coefficients, nonuniform face
geometry, boundary treatment, and affine-jump zeroing.  The mass metric `M_A`
must be the metric for which this pressure action is adjoint to the divergence:

```text
<G_A p, w>_{M_A} = <p, D_f w>_{W_p}
```

for all regular face velocities `w`, up to boundary/gauge conventions.  If this
adjointness does not hold to tolerance, the capillary Hodge theorem is not
available for the active scheme and production must fail closed.

Thus the active theorem object is:

```text
(q_c, D_f, G_A(q_c), M_A(q_c), T_f(q_c), S_h, V_m,h).
```

`M_A` is not an arbitrary diagnostic norm.  It is induced by the pressure
coefficient and face measure, for example `measure / coeff` in the affine
phase-separated face operator.  A separate kinetic diagnostic weight may be
reported, but reaction orthogonality and energy power must use the adjoint
metric `M_A`.

## Endpoint-Closed Time Level

The capillary substep is defined at one labelled interface endpoint:

```text
q_c := q_T,
q_T = interface state after physical transport and before reinit/profile
      projection.
```

All capillary objects are evaluated at `q_c`:

```text
S_h(q_c),
V_m,h(q_c),
T_f(q_c)u_f = -D_f(P_f q_c u_f),
rho_c = rho(q_c),
G_A(q_c),
M_A(q_c).
```

The post-reinit state

```text
q_R := q^{n+1}
```

is not allowed to supply material coefficients for a force derived at `q_c`
unless an endpoint-equivalence gate passes:

```text
||q_R - q_c||,
|S_h(q_R)-S_h(q_c)|,
|V_m,h(q_R)-V_m,h(q_c)|,
||G_A(q_R)-G_A(q_c)|| diagnostic proxy
```

all below declared tolerances.  Otherwise production must either materialize
capillary coefficients from `q_c` or fail closed.  Mixing `q_c` geometry with
`q_R` coefficients is a different discrete system.

## Endpoint Virtual Work

The surface cochain and component-volume reaction cochains are still:

```text
<s,u>_{M_A}   = -d_q(sigma S_h)(q_c)[T_f(q_c)u],
<B_m,u>_{M_A} =  d_qV_m,h(q_c)[T_f(q_c)u].
```

Equivalently:

```text
s   = -M_A^{-1}T_f(q_c)^T d_q(sigma S_h)(q_c)^T,
B_m =  M_A^{-1}T_f(q_c)^T d_qV_m,h(q_c)^T.
```

The signs are fixed by the release identity.  If the admissible capillary
acceleration is `h`, then

```text
d_q(sigma S_h)(q_c)[T_f(q_c)h] = -<s,h>_{M_A}.
```

## Fully Coupled Reaction Projection

The safest theorem is not "subtract the Hodge part of `B`" as a primitive
definition.  The primitive definition is a constrained saddle system:

```text
h = s - G_A p - B mu,
D_f h = 0,
B^T M_A h = 0.
```

In block form:

```text
D_f G_A p + D_f B mu = D_f s,
B^T M_A G_A p + B^T M_A B mu = B^T M_A s.
```

This is the fully discrete pressure/component reaction problem.  It directly
states what pressure and component multipliers are allowed to remove.  It also
solves the metric-risk issue: the component side condition is written with the
full `B^T M_A`, not with an assumed orthogonalized surrogate unless that
surrogate is proven equivalent.

## PPE-Solve Elimination Form

For implementation with the existing PPE solver, define the divergence lift:

```text
L_A(c) = G_A p_c,
D_f G_A p_c = D_f c,
Z_A(c) = c - L_A(c).
```

`Z_A(c)` is divergence-free.  It is an `M_A`-orthogonal Hodge residual only if
the pressure-adjointness gate holds.  The coupled system can be solved by
PPE-solve elimination:

```text
z_s = Z_A(s),
z_m = Z_A(B_m),
C_ij = B_i^T M_A z_j,
r_i  = B_i^T M_A z_s,
C mu = r,
h = z_s - sum_m mu_m z_m,
c_corrected = s - B mu.
```

The PPE RHS and corrector then use the same `c_corrected`:

```text
rhs += D_f(c_corrected),
pressure_faces = G_A p - c_corrected,
u^{n+1}_f = u^*_f - dt pressure_faces + ...
          = u^*_f + dt(c_corrected - G_A p) + ...
```

The final capillary acceleration is:

```text
h = c_corrected - G_A p.
```

Important distinction:

```text
Do not generally solve C_ij = z_i^T M_A z_j
```

unless the pressure-adjointness gate proves that `range(G_A)` is
`M_A`-orthogonal to `ker D_f`.  The symmetric `z_i^T M_A z_j` formula is a
special case, not the theorem.

## Energy Power Theorem

Assume:

```text
1. pressure adjointness: <G_Ap,w>_{M_A}=0 for all D_fw=0,
2. component constraint: B^T M_A h=0,
3. h=s-G_Ap-Bmu,
4. D_fh=0.
```

Then:

```text
<s,h>_{M_A}
= <h+G_Ap+Bmu, h>_{M_A}
= ||h||_{M_A}^2.
```

Therefore:

```text
d_q(sigma S_h)(q_c)[T_f(q_c)h] = -||h||_{M_A}^2 <= 0.
```

This is the sign-power theorem.  It is stronger than a sign convention test:
if the pressure-adjointness, component orthogonality, or corrector cochain
identity fails, the energy proof fails.

## Static and Dynamic Criteria

A static discrete equilibrium is:

```text
d_q(sigma S_h)(q_c) = sum_m lambda_m d_qV_m,h(q_c)
```

in the same endpoint-closed object

```text
(q_c, T_f, G_A, M_A, D_f).
```

Equivalently, the constrained acceleration from the saddle system satisfies:

```text
||h||_{M_A} = 0
```

up to the declared consistency floor.  A sampled analytic circle is only a
convergence probe unless it is also a constrained critical point of this
finite-dimensional system.

A dynamic mode is any regular perturbation for which the same saddle system
returns:

```text
||h||_{M_A} > static floor.
```

No shape names appear in the definition.

## GPU-First Geometry As Mathematics

The P1 surface and volume gradients are local cell formulas.  On GPU, the
production operator must be defined by the same local formulas in `xp` arrays:

```text
cell corner fields,
edge crossing masks,
crossing denominator regularity,
local polygon/segment derivatives,
scatter-add to nodal covectors.
```

Host-loop graph traversal is not just an optimization problem.  If CPU graph
logic and GPU vectorized logic differ in ambiguous-cell handling, crossing
ordering, or threshold tolerances, they define different `dS_h`/`dV_h`.  The
production theorem therefore requires a GPU-native geometry kernel or an
explicit diagnostic-only label.

The regularity gate is part of the discrete domain:

```text
min |psi_i-threshold| on active denominators > tau_cross,
crossing count in each active cell is regular or explicitly resolved,
component count supported by the current GPU volume labels.
```

Unsupported multiple components, wall contact, open traces, or topology
changes fail closed.

## Revised Implementation Implication

The previous design that subtracts only

```text
B_m^H = B_m - L_A(B_m)
```

is valid only as a shorthand after the coupled equations are honored.  The
implementation should compute `mu` using full `B_i^T M_A z_j` rows and pass:

```text
c_corrected = s - B mu
```

to both PPE RHS and `pressure_fluxes`.  Passing

```text
s - sum_m mu_m B_m^H
```

preserves `D_fs` by construction, but it is not the primitive constrained
reaction law and may fail `B^T M_A h=0` when `L_A` is not exactly
`M_A`-orthogonal.

## Gates Strengthened By This Theory

1. Pressure adjointness gate:
   `<G_Ap,w>_{M_A}` must vanish for divergence-free test fields.
2. Endpoint-closed material gate:
   `q_c` supplies geometry and capillary projection coefficients, or
   `q_R` is ledger-equivalent.
3. Coupled reaction gate:
   solve `C_ij=B_i^TM_AZ_A(B_j)`, not the symmetric shortcut unless proven.
4. Corrector identity gate:
   `c_corrected` is identical in `D_f(c_corrected)` and
   `pressure_fluxes(..., capillary_jump_components=c_corrected)`.
5. Sign-power gate:
   `<s,h>_{M_A}=||h||_{M_A}^2` and
   `dE[T_fh]=-||h||_{M_A}^2`.
6. GPU geometry gate:
   production `dS_h,dV_h` are `xp` local formulas with the same regularity
   masks as the theorem.

## Verdict

The risks do not invalidate the conservative endpoint direction.  They refine
it.  The correct target is not merely "use the conservative cochain" but:

```text
an endpoint-closed, pressure-adjoint, component-constrained saddle projection
of the conservative surface-energy VJP, implemented in the active FCCD/affine
face complex and with GPU-native geometry.
```

[SOLID-X] Theory artifact only.  No production solver/config/result behavior is
changed, no tested implementation is deleted, and no FD/WENO/PPE fallback,
damping/CFL workaround, curvature cap, smoothing, benchmark branch, blanket
projection, or QP-as-physics route is introduced.
