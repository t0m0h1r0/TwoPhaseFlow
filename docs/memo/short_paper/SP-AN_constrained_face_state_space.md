# SP-AN: Constrained Face-State Space Reformulation

**Status**: ACTIVE theory candidate  
**Date**: 2026-05-09  
**Scope**: wall-bounded conservative common-flux two-phase flow after the
boundary-Hodge KKT rank probe  
**Companion papers**: SP-AJ, SP-AK, SP-AL, SP-AM, SP-W, SP-X

## 1. Executive Claim

The previous boundary-Hodge route correctly identified the target constraint

```text
D_h f = 0,
C_w f = B_h R_h f = 0,
u = R_h f,
m = rho u.
```

But it tried to repair an unconstrained face space by adding a wall multiplier
after the pressure complex had already been designed for that unconstrained
space.  The rank probe showed that this is not a clean production foundation:

```text
full wall:      algebraically feasible, but dt-scaled KKT is poorly conditioned
periodic_wall:  production [G_A, C_w^T] correction basis is rank deficient
```

The stronger formulation is to make the admissible velocity space itself a
wall-constrained face space:

```text
F_w(q) = { f in F_h : C_w f = 0 }.
```

The incompressible projection is then a pressure Hodge projection inside
`F_w`, not a full-space pressure projection plus a separate wall repair.

## 2. What Was Wrong With The Additive KKT View

The additive KKT view was not physically wrong at the continuous level.  Its
problem was representational: it kept the wrong ambient space as the main
state space.

The old implementation path effectively maintained two states:

```text
transport state: f in F_h
published state: u = wall_clamp(R_h f)
```

This breaks the common-flux ledger because the state used to transport
`q`, `rho`, and momentum is not the state used to publish `m=rho u`.

SP-AL fixed the target by requiring:

```text
f in K_h = ker D_h cap ker C_w.
```

SP-AM then proposed a full-space coupled KKT:

```text
f = f_dag - dt G_A p - dt M_f^{-1} C_w^T lambda.
```

The KKT is a valid diagnostic equation, but three facts make it a weak
production foundation:

1. `G_A` is the pressure reaction for the unconstrained face space.  The
   pressure reaction for the wall-constrained space is the adjoint of
   `D_h` restricted to `F_w`.
2. The wall multiplier cancels components that would not exist if the velocity
   space had been constrained from the start.
3. The periodic-wall rank defect shows that pressure variables, periodic image
   nodes, and wall trace rows are not being represented in one quotient space.

Therefore the correct next step is not to tune or precondition the old KKT
alone.  It is to rebuild the discrete phase space and derive the pressure
operator from that space.

## 3. State Space Before Reactions

Let

```text
F_h  = production face-normal velocity array space
N_h  = nodal vector velocity publication space
Q_h  = pressure scalar space modulo gauge and topology quotients
W_h  = no-slip wall trace space
R_h  : F_h -> N_h
B_h  : N_h -> W_h
C_w  = B_h R_h
M_f(q) = Q_f rho_f, the transported face-mass metric
```

Define the wall-constrained face state space:

```text
F_w(q) = ker C_w.
```

The physical one-step velocity state must live in

```text
K_w(q) = { f in F_w(q) : D_h f = 0 }.
```

The published nodal and momentum variables are dependent variables:

```text
u = R_h f,
m = rho(q) u.
```

There is no independent nodal wall clamp after publication.  If `f` is not in
`F_w`, the step has not produced a valid velocity state.

## 4. Metric Retraction To F_w

The wall trace is a holonomic equality constraint on velocity.  Its metric
orthogonal retraction is

```text
P_w(q) = I - M_f^{-1} C_w^T (C_w M_f^{-1} C_w^T)^+ C_w.
```

It satisfies

```text
C_w P_w f = 0,
P_w^2 = P_w,
P_w is M_f-self-adjoint.
```

The previously implemented wall-trace projection is this `P_w`.  Its failure
as a post-pressure correction does not invalidate it.  It means `P_w` must be
part of the velocity-space chart, not an afterthought applied to a pressure
projected field.

The rule is:

```text
only P_w f is a velocity state;
components (I-P_w)f are wall reaction work and are not transported.
```

The metric is the full transported face mass, not face density alone:

```text
M_f = Q_f rho_f.
```

Here `Q_f` is the diagonal face control measure induced by the same primal
nonuniform grid on which `D_h` and `G_A` are built.  A density-only metric
breaks the restricted Green identity because pressure work is paired against
cell/control-volume measures.  In validation, the density-only implementation
gave an order-one restricted Green residual, while the `Q_f rho_f` metric
reduced the full-wall residual to roundoff.

## 5. Restricted Pressure Hodge Projection

Given a predictor face quantity `f_dag`, only its admissible wall-constrained
part participates in the pressure projection:

```text
f_dag^w = P_w f_dag.
```

The incompressible update is

```text
f^{n+1} = argmin_{f in F_w}
          1/2 ||f - f_dag^w||_{M_f}^2
          subject to D_h f = 0.
```

Equivalently, for every test velocity `eta in F_w`,

```text
<M_f(f - f_dag^w), eta> + <p, D_h eta> = 0,
D_h f = 0.
```

This is the Hodge projection for the restricted divergence

```text
D_w = D_h |_{F_w}.
```

The pressure reaction is not the unconstrained `M_f^{-1}D_h^T` but the
restricted adjoint:

```text
G_w = M_f^{-1} D_w^*.
```

Using the existing production pressure map, the compatible candidate is:

```text
G_w p = P_w G_A p
```

provided the restricted Green identity passes:

```text
<G_w p, eta>_{M_f} + <p, D_h eta> = 0
for all eta in F_w.
```

The pressure equation becomes:

```text
D_h P_w G_A p = D_h P_w f_dag.
```

and the final state is:

```text
f^{n+1} = P_w f_dag - P_w G_A p.
```

This differs from the rejected wall-only post projection:

```text
rejected: f = P_w(f_dag - G_A p_old)
accepted: p solves D_h(P_w f_dag - P_w G_A p)=0
```

The pressure operator itself includes the wall-state chart.

## 6. Force Covectors On The Constrained Space

Gravity, capillarity, viscosity, and pressure history should be read as
covectors on admissible virtual velocities:

```text
eta in F_w.
```

Given a full-space force covector `r`, the constrained acceleration is:

```text
a_w = P_w M_f^{-1} r.
```

The eliminated component

```text
(I-P_w) M_f^{-1} r
```

is a wall reaction.  It should be diagnosable, but it is not a transported
velocity component.  This is why DCCD/UCCD damping, wall clipping, and
post-hoc nodal clamping are not physical fixes: they change the force or state
instead of restricting the variational space.

## 7. Topology And Quotient Spaces

Periodic axes are quotient identifications, not extra boundary constraints.
The state space must be built from topology first:

```text
1. identify periodic image nodes and pressure gauge variables;
2. construct C_w on unique wall trace DOFs;
3. define P_w on that quotient;
4. restrict pressure through D_h P_w G_A.
```

The previous periodic-wall rank defect is explained by constructing an
additive KKT in the wrong quotient order.  The new acceptance gate is not

```text
rank([D_h; C_w][G_A, C_w^T]) = rank([D_h; C_w])
```

as the primary production test.  Instead it is:

```text
rank(D_h P_w G_A) = rank(D_h |_{F_w})
```

with pressure gauge and periodic quotient removed before the rank is measured.

## 8. Relation To Nodal-Primary Alternatives

A different clean route is possible:

```text
U_0 = { u in N_h : B_h u = 0 },
f = F_h u,
D_h F_h u = 0.
```

This nodal-primary formulation makes no-slip natural and derives face fluxes
from nodal velocity.  It may be more familiar, but it risks weakening the
common-flux transport contract because `f` becomes a derived object rather than
the preserved transport state.

For the current codebase, the constrained face-state space is the smaller
theoretical rotation:

```text
keep f primary,
make f admissible before projection,
publish u and m as dependent variables.
```

A full mixed/FEEC or MAC-like redesign remains a long-range clean-room option,
but it is more invasive than needed for the next proof.

## 9. Implementation Consequences

The production implementation should introduce a state-space layer, not another
post-corrector:

```text
velocity_space:
  kind: constrained_face
  wall_trace: reconstruct_nodes
  wall_retraction: metric_projection
  pressure_pairing: restricted_variational_adjoint
```

Core operators:

```text
P_w.apply(faces)
P_w.apply_acceleration(face_covectors_or_accel)
restricted_pressure_fluxes(p) = P_w G_A(p)
restricted_pressure_operator(p) = D_h restricted_pressure_fluxes(p)
```

Publication gates:

```text
||C_w f||                <= tolerance
||D_h f||                <= tolerance
||u - R_h f||            <= tolerance
||m - rho u||            <= tolerance
restricted Green residual <= tolerance
rank(D_h P_w G_A) gate passes on small probes
```

The old `boundary_hodge.wall_trace_projection` remains useful as the
implementation of `P_w`, but not as a final-state repair.

### Implemented First Slice

The first code slice implements the state-space building blocks, not the final
restricted PPE solve:

```text
P_w.apply(faces)                 = project_wall_trace(...)
restricted_pressure_fluxes(p)    = P_w G_A(p)
diagnostic restricted operator   = D_h P_w G_A
```

The canonical rising-bubble YAML records:

```yaml
boundary_hodge:
  mode: off
  state_space: constrained_face
  wall_retraction: metric_projection
  pressure_pairing: restricted_variational_adjoint
  gate: diagnostic
```

`mode: off` is intentional.  It prevents the old post-pressure wall repair from
being mistaken for the new state-space projection.  Production enablement
requires the remaining solve and publication gates.

### Metric Correction From Operator Validation

The first validation ladder found that the metric must include the geometric
face measure.  For full-wall topology on a small nonuniform manufactured probe:

```text
density-only metric:
  restricted Green relative residual = 9.169329e-01

Q_f rho_f metric:
  restricted Green relative residual = 8.826843e-17
  rank(D_h P_w G_A) = rank(D_h | F_w) = 19
  manufactured K_w recovery relative error = 1.537101e-14
  manufactured divergence L2 = 4.713074e-13
  manufactured wall-trace Linf = 5.532534e-31
```

This is a theoretical correction, not a tuning parameter: the same quadrature
that defines pressure work and `D_h` must define the face-state metric.  The
runtime helper remains matrix-free and backend-native; the dense matrices above
exist only in small validation probes.

Mixed `periodic_wall` topology remains fail-closed at this stage:

```text
rank(D_h P_w G_A) = 27,
rank(D_h | F_w)   = 30,
restricted Green relative residual = 1.037769e-01.
```

The failure is consistent with the quotient-order warning in Section 7.  It is
not a reason to add a fallback or a wall damper; it is a gate that says periodic
identifications, pressure gauge variables, and wall trace rows must be rebuilt
in one quotient space before production use.

## 9.5 Diagnostic and Metric Contract

The rising-bubble debug fields must not be treated as theorem statements unless
they are tied to the active operator.  In the pressure-jump configuration, the
production capillary drive is the affine face jump built from cut-face
`face_implicit` curvature.  The legacy nodal/direct-psi `kappa_max` diagnostic
can therefore spike without implying that the active Young-Laplace cochain has
the same magnitude.  CHK-RA-CH14-BUBBLE-DIAG-RCA-001 recomputed the active
`T=0.02` face curvature and found `O(1e3)`, not the reported legacy
`O(1e5)` spike.

The same rule applies to pressure sources.  The reported PPE RHS must be the
RHS sent to the solver after all closed-interface and face-pressure-history
source terms are assembled.  Recording a partial source is a software
diagnostic error, not a fluid-mechanics fact.  The implementation now records
`ppe_rhs_max` immediately before the PPE solve.

Finally, the metric in `P_w` has two valid roles:

```text
velocity publication / no-slip state:
  M_f = Q_f rho_f

pressure adjoint diagnostics in affine coefficient paths:
  M_A = Q_f / alpha_f
```

Both are face-space metrics, but they answer different inner-product questions.
The helper operators therefore accept explicit face metric components and fail
closed on shape mismatch.  This is an API preparation for constrained
pressure-adjoint diagnostics; it is not yet a production `D_h P_w G_A` solve.

## 10. Verification Ladder

The next efficient proof ladder is:

```text
S1  P_w idempotence and M_f self-adjointness
S2  C_w P_w = 0 on wall and periodic_wall topologies
S3  restricted Green identity for G_w = P_w G_A
S4  rank(D_h P_w G_A) = rank(D_h | F_w)
S5  manufactured projection: f_dag = h + P_w G_A p, h in K_w
S6  one-step rising bubble: C_w f, D_h f, u=R_h f together
S7  short N=32x64 run with no wall-localized face/nodal mismatch
S8  static/oscillating droplet and capillary wave regression to ensure
    wall-space retraction does not alter all-periodic or non-wall cases
```

Do not proceed to long rising-bubble runs before S1--S6 pass.

## 11. Negative Knowledge To Retain

The following routes are now explicitly bounded:

```text
wall-only projection after pressure:
  valid diagnostic P_w, invalid production update

full-space coupled KKT:
  valid mathematical reference, weak production chart unless quotient,
  homogeneous pressure, scaling, and preconditioning are solved

generic D_h^T pressure substitute:
  hides pressure-complex mismatch and bypasses G_A

nodal post-clamp:
  creates two velocity states

boundary-face zeroing:
  fails tangential no-slip trace

damping, CFL, smoothing, DCCD/UCCD suppression:
  changes physics or hides the constraint defect
```

The useful lesson is positive: the remaining problem is not that a wall
reaction is missing numerically.  It is that the wall-constrained velocity
space must be the state space before pressure, gravity, capillary, viscosity,
history, and publication are defined.

## 12. Conclusion

The revised theory keeps the best part of SP-AL, the target

```text
K_w = ker C_w cap ker D_h,
```

but changes the route:

```text
old route: full F_h -> pressure projection -> wall repair
new route: F_w=ker C_w -> restricted pressure projection
```

This is a genuine state-space reformulation.  It reduces the wall multiplier
from a primary runtime unknown to an eliminated reaction, aligns the pressure
operator with admissible virtual velocities, and gives a sharper GPU-friendly
implementation target: matrix-free `P_w`, matrix-free `D_h P_w G_A`, and
fail-closed state publication.
