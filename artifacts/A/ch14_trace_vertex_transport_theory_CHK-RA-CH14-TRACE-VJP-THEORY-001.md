# CHK-RA-CH14-TRACE-VJP-THEORY-001

## Scope

User request: before implementation, wash the theory thoroughly and do not
patch the symptom.

This checkpoint revisits the previous Riesz diagnostic result and tightens the
theorem contract for the next implementation.  It intentionally makes no
solver or YAML change.

## Correction Of The Previous Reading

`CHK-RA-CH14-RIESZ-VERIFY-001` proved a real identity:

```text
T_c(u) = -D_f(psi_f u_f)
s_c    = -M_f^{-1} T_c^T d(sigma S_h)^T
B_c    =  M_f^{-1} T_c^T dV_h^T
```

For this transport map,

```text
d(sigma S_h)[T_c u] + <s_c,u>_M = 0
```

holds on a fixed stratum.  Therefore the diagnostic was not a numerical
accident.

The overstrong reading is the finite-grid "circle must be roundoff static"
claim.  A continuum circle sampled onto a P1 marching-squares trace is not
automatically an exact discrete constrained critical point of `S_h` under
`V_h`.  At finite `N`, the sampled polygon can retain a discrete residual even
when the continuum curve is perfectly circular.  Thus the sampled-circle test
is a convergence gate, not a roundoff static gate.

The remaining negative result is subtler and more useful:

```text
T_c is Riesz-correct for conservative nodal indicator transport,
but that does not prove it is the physical sharp-trace transport map.
```

The next theorem must identify the actual map from face velocity degrees of
freedom to zero-crossing trace motion.

## Shape-Free Continuum Contract

The law cannot branch on "circle" or "ellipse."  The continuum statement is
component-free and shape-free:

```text
E(Gamma) = sigma |Gamma|
V_m(Gamma) = component volume
delta E[u] = - integral_Gamma sigma kappa (u . n) ds
delta V_m[u] = integral_Gamma (u . n) ds
```

A static component is not "a circle" in the algorithm.  It is a constrained
critical point:

```text
delta E[u] = lambda_m delta V_m[u]   for all admissible u on component m.
```

The discrete algorithm must mirror this finite-dimensionally:

```text
surface covector  = derivative of the chosen discrete surface energy,
reaction covector = derivative of the chosen discrete component volume,
Hodge drive       = component-constrained M_f-orthogonal residual.
```

Curvature may be reconstructed afterward as an interpretation.  It must not be
the primitive force unless it has been shown equal to the discrete virtual-work
derivative.

## Fixed Trace Stratum

Let `q` be the interface carrier and let `K` be a fixed marching-squares trace
stratum: no threshold touch and no change of cell sign case, crossing edge,
or segment connectivity.

For a cut edge `e=(i,j)` with coordinates `x_i,x_j` and threshold `tau`,

```text
alpha_e = (tau - q_i) / (q_j - q_i)
z_e     = x_i + alpha_e (x_j - x_i).
```

The trace geometry is the set of zero-crossing vertices `z_e` connected by the
fixed stratum `K`.  On this stratum the geometric functionals are smooth:

```text
S_h(z) = sum_segments |z_b - z_a|
V_h(z) = shoelace area of each component polygon.
```

For one segment `a -> b`,

```text
ell = |z_b - z_a|,
t   = (z_b - z_a) / ell,
delta S_segment = sigma t . (delta z_b - delta z_a).
```

So the vertex covectors are `-sigma t` at `a` and `+sigma t` at `b`.

For an oriented polygon with vertices `z_k`, the area differential is

```text
delta V = sum_k delta z_k . 0.5 R_-90 (z_{k+1} - z_{k-1}),
```

with the sign matched to the implementation's shoelace convention.

These are exact shape derivatives of the discrete trace.  They do not assume
that the trace is circular, elliptical, convex, single-mode, or smooth beyond
the active stratum.

## Transport Candidates

### Candidate A: Conservative Indicator Transport

```text
T_c(u) = -D_f(psi_f u_f)
```

Status: diagnostic only.

It gives a valid Riesz representative for the nodal scalar transport map it
defines.  Its weakness is that it transports a conservative nodal indicator or
level-set value, then lets the zero trace move indirectly.  It is not the same
object as direct transport of the sharp trace vertices.  Passing virtual work
for `T_c` therefore proves internal algebra, not final physics.

### Candidate B: Advective Level-Set Nodal Transport

```text
T_a(u) = -I_h(u) . grad q
```

Status: rejected as the first production theorem.

This is closer to the level-set PDE, but the result depends on velocity
extension, gradient reconstruction, and tangential gauge.  Two scalar fields
with the same zero set can give different nodal derivatives unless the gauge
is fixed.  That makes it a fragile primitive for a sharp-interface force.

### Candidate C: Curvature Quadrature

```text
s(u) = integral_Gamma sigma kappa n . u ds
```

Status: interpretation only until proven equal to `dS_h`.

The continuum formula is correct, but a discrete curvature quadrature is not
automatically the derivative of the polygonal `S_h`.  If it is not exactly the
same covector, the Hodge residual can be a discretization artifact.

### Candidate D: Static Residual Minimization Or QP

Status: rejected as physics.

Minimizing a residual, clipping a cochain, or solving a QP can hide the drive
without identifying the virtual-work derivative.  It can be a diagnostic or
guard, but not the capillary law.

### Candidate E: Direct Trace-Vertex Transport VJP

Status: selected theorem route.

Define a linear map on the fixed stratum:

```text
C_K : face velocities -> trace vertex velocities,
delta z = C_K u_f.
```

Then define the face cochains by transpose pullback:

```text
s_K = -M_f^{-1} C_K^T d_z(sigma S_h)^T
B_K =  M_f^{-1} C_K^T d_z V_h^T.
```

This is the first candidate whose diagram is exactly the physical diagram:

```text
face velocity -> sharp trace displacement -> surface/volume work -> face force.
```

## Choosing C_K

The theorem does not require recognizing shapes.  It requires the same face
degrees of freedom, same metric, and same trace map in every identity.

Possible concrete `C_K` realizations:

```text
1. reconstructed_nodal_p1:
   reconstruct nodal vector velocity from face DOFs, then P1-interpolate it
   to each crossing vertex.

2. direct_face_p1:
   interpolate the relevant vector components directly from staggered face
   locations to each crossing vertex.

3. mimetic_rt_whitney:
   use a face-space trace interpolation designed for the exact FCCD complex.
```

`reconstructed_nodal_p1` is the smallest proof candidate because it is linear,
shape-free, and can be checked immediately.  It is not accepted by taste.  It
is accepted only if the gates below pass.  If it fails a conservation or gauge
gate, the theory points to `direct_face_p1` or a mimetic trace interpolation,
not to damping, smoothing, or range deletion.

## Projection Contract

Let

```text
R = A_f G_f,
B = [B_1 ... B_M],
X = [R B].
```

The component-constrained pressure reaction is the `M_f`-orthogonal projection:

```text
Pi_X s = X (X^T M_f X)^+ X^T M_f s.
```

The dynamic capillary drive is

```text
h = s - Pi_X s.
```

For a constrained critical discrete trace, `h` must vanish.  For a resolved
noncritical trace perturbation, `h` must be nonzero.  This statement is about
the discrete trace geometry and pressure complex, not about whether a human
would call the shape an ellipse.

## Acceptance Gates

The next implementation is not accepted unless it can report these gates:

```text
1. Fixed-stratum gate:
   plus/minus perturbations keep the same cell cases and trace connectivity.

2. Vertex finite-difference gate:
   d_z S_h[C_K u] and d_z V_h[C_K u] match centered finite differences of
   the polygon geometry.

3. Face Riesz gate:
   d_z(sigma S_h)[C_K u] + <s_K,u>_M = 0.

4. Component Riesz gate:
   d_z V_m[C_K u] - <B_m,u>_M = 0.

5. Weighted Hodge gate:
   the residual equals s - X(X^T M_f X)^+X^T M_f s using the same M_f,D_f,A_f,G_f.

6. Static criticality gate:
   an explicitly constructed discrete constrained critical trace gives h ~= 0
   if such a trace is available.

7. Sampled-circle convergence gate:
   a sampled analytic circle need not be roundoff-static at finite N; its
   component residual must be interpreted as a convergence trend, not as a
   shape-name pass/fail.

8. Nonconstant-mode gate:
   arbitrary resolved nonconstant trace perturbations retain h != 0 beyond
   the static consistency floor.

9. Rigid-motion gate:
   constant translations give delta S_h ~= 0 and delta V_h ~= 0.

10. Tangential/gauge gate:
    trace velocities with zero normal displacement give no first-order
    surface/volume work up to the interpolation accuracy of the chosen C_K.

11. Reinit endpoint ledger:
    all work identities use the pre-reinit transport endpoint; reinit changes
    are recorded separately as retraction error, not capillary work.
```

## Verdict

The implementation target is no longer "make the sampled circle residual
roundoff."  The target is:

```text
construct C_K,
pull back exact trace-vertex derivatives through C_K^T,
project with the same M_f pressure/component complex,
measure static convergence and nonconstant drive without shape names.
```

This preserves the physical principle: capillarity is the virtual-work
derivative of surface energy under the actual admissible velocity map.  It also
prevents the old failure mode: replacing a force by its pressure range part is
not a force law.

## Validation

Docs-only checkpoint.  No solver behavior, YAML contract, production capillary
cochain, pressure corrector, transport step, or reinit behavior was changed.

[SOLID-X] theory/artifact only; no tested implementation deleted; no
FD/WENO/PPE fallback, damping/CFL workaround, curvature cap, smoothing,
benchmark-name branch, blanket `c -> Pi_R c`, or QP-as-physics path introduced.
