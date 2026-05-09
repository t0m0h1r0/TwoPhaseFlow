# SP-AL: Boundary-Constrained Face Hodge Projection

**Status**: ACTIVE theory candidate
**Date**: 2026-05-09
**Scope**: SI water-air rising bubble, wall-bounded conservative common-flux
two-phase flow, face-native pressure projection, no-slip walls
**Companion papers**: SP-AJ, SP-AK, SP-AI, SP-W, SP-X

## 1. Executive Claim

The rising-bubble route must not be formulated as a divergence-only Hodge
projection followed by a separate nodal wall overwrite.  In a wall-bounded
no-slip tank the admissible velocity space is

```text
V_0 = { u : div u = 0 and u|Gamma_w = 0 }.
```

The discrete face state used by common-flux transport and the nodal velocity
used by conservative momentum must therefore be one constrained state.  The
correct projection is the `M_f(q)`-orthogonal projection onto the face subspace

```text
K_h(q) = { f in F_h : D_h f = 0 and B_h R_h f = 0 }.
```

Here `D_h` is the production FCCD face divergence, `R_h` reconstructs nodal
velocity from face velocity, and `B_h` selects no-slip wall nodal degrees of
freedom.  The missing wall equation is not damping.  It is the Lagrange
constraint for the physical no-slip boundary.

## 2. Why The Previous Formulation Was Incomplete

The conservative common-flux state after SP-AJ and SP-AK is

```text
q^n        phase/CLS field
rho^n      rho_g + (rho_l-rho_g) q^n
m^n        rho^n u^n
f^n        face velocity used by common-flux transport
```

The intended invariant is

```text
u^n = R_h f^n,
B_h u^n = 0,
m^n = rho^n u^n,
transport uses f^n.
```

The diagnosed code path instead represents a post-step state as

```text
f^{n+1}       divergence-free projected face velocity
u_raw         R_h f^{n+1}
u^{n+1}       B_h u_raw   (nodal wall overwrite)
m^{n+1}       rho^{n+1} u^{n+1}
next transport uses f^{n+1}
```

Therefore one time level contains two velocities:

```text
transport velocity  = f^{n+1},
momentum velocity   = B_h R_h f^{n+1}.
```

If `R_h f^{n+1}` is not already no-slip at the wall, the common-flux theorem no
longer applies to the stored momentum state.  The measured defect is exactly
wall-localized: the interior mismatch is zero while wall mismatch is finite.

## 3. Continuous Variational Principle

Let the kinetic metric be

```text
(u,v)_rho = integral_Omega rho u dot v dx.
```

Given a predictor velocity `u_dag`, the continuous projection for an
incompressible no-slip velocity is

```text
u^{n+1} = argmin_{u in V_0}
          1/2 ||u-u_dag||_rho^2.
```

Introduce pressure `p` for incompressibility and wall multiplier `lambda` for
no-slip.  The stationary equations are

```text
rho (u-u_dag) + grad p + E_w^* lambda = 0,
div u = 0,
E_w u = 0.
```

`E_w` is the wall trace operator.  The wall multiplier is the constraint
reaction.  It does no work on admissible velocities because every admissible
test velocity has zero wall trace.

This is the governing principle to preserve.  A pressure-only projection
followed by post-hoc nodal clamping is a splitting approximation to this
constrained minimization, not the exact discrete principle.

## 4. Discrete Spaces And Operators

Use the production nonuniform grid and backend-specific arrays.

```text
C_h    cell or nodal scalar space for density/phase/PPE RHS
F_h    face-normal velocity cochain space used by FCCD common flux
N_h    nodal vector velocity space used for momentum publication
Q_h    pressure scalar space modulo constants
W_h    wall nodal vector trace space
```

Operators:

```text
D_h : F_h -> C_h          production face divergence
G_h : Q_h -> F_h          pressure reaction in face space
R_h : F_h -> N_h          face-to-node reconstruction
B_h : N_h -> W_h          no-slip wall trace selector
C_h^w = B_h R_h : F_h -> W_h
M_f(q)                   transported face-mass metric
```

The symbol `C_h^w` is used for the wall constraint operator, not for the scalar
cell space.  In implementation this operator should have a less ambiguous
name, for example `wall_trace_from_faces`.

The admissible face subspace is

```text
K_h(q) = ker D_h cap ker C_h^w.
```

Periodic axes simply do not contribute wall rows to `C_h^w`.  Wall axes
contribute all velocity components on the wall nodal trace, matching no-slip.
For a free-slip wall one would constrain only the normal trace, but the rising
bubble YAML is no-slip wall.

## 5. Boundary-Constrained Hodge Projection

Given a predictor face velocity `f_dag`, define the accepted post-step face
velocity by

```text
f^{n+1} = argmin_f 1/2 (f-f_dag)^T M_f(q) (f-f_dag)
          subject to D_h f = 0,
                     C_h^w f = 0.
```

The KKT system is

```text
M_f (f - f_dag) + D_h^T p + (C_h^w)^T lambda = 0,
D_h f = 0,
C_h^w f = 0.
```

Equivalently,

```text
f = f_dag - M_f^{-1} D_h^T p - M_f^{-1} (C_h^w)^T lambda.
```

The Schur complement is

```text
[ D_h M_f^{-1} D_h^T       D_h M_f^{-1} (C_h^w)^T       ] [p     ]
[ C_h^w M_f^{-1} D_h^T     C_h^w M_f^{-1} (C_h^w)^T     ] [lambda]

=
[ D_h f_dag   ]
[ C_h^w f_dag ].
```

This is the mathematically correct replacement for a pressure-only PPE if
`R_h f` is preserved as the canonical state.  The pressure part removes the
compressible range.  The wall multiplier removes the wall trace component.
Both are metric-orthogonal constraint reactions.

## 6. Relation To Existing Pressure-Adjoint Operators

The production pressure force is not a raw compact gradient.  It is the active
face pressure reaction already used by pressure-adjoint/variational operator
contracts.  Therefore the practical KKT should be written using the active
pressure face map `G_A`:

```text
f = f_dag - G_A p - M_f^{-1} (C_h^w)^T lambda,
D_h f = 0,
C_h^w f = 0.
```

The pressure block is then the same block that current PPE validation already
tests:

```text
D_h G_A p.
```

The new block is the wall-trace coupling:

```text
D_h M_f^{-1} (C_h^w)^T lambda,
C_h^w G_A p,
C_h^w M_f^{-1} (C_h^w)^T lambda.
```

Thus SP-AL does not replace SP-W, SP-X, SP-AI, SP-AJ, or SP-AK.  It completes
their constrained target space.

## 7. Correct State Publication

After solving the constrained face projection, the state must be published as

```text
f^{n+1} in K_h,
u^{n+1} = R_h f^{n+1},
m^{n+1} = rho^{n+1} u^{n+1},
next common-flux transport uses f^{n+1}.
```

No additional nodal wall overwrite should change `u^{n+1}` after publication.
If `B_h R_h f^{n+1}` is not zero to tolerance, the step must fail closed.

This is the single-state principle:

```text
velocity_for_transport == velocity_for_momentum == velocity_for_restart.
```

The restart checkpoint should store the same `f`, `u=R_h f`, `m=rho u`, and
pressure/wall history objects if higher-order extrapolation needs them.

## 8. Energy Theorem

Let `P_K^M` be the `M_f`-orthogonal projection onto `K_h`.  Then

```text
f^{n+1} = P_K^M f_dag.
```

For any admissible `v in K_h`,

```text
(f_dag - f^{n+1}, v)_{M_f} = 0.
```

The projection is non-expansive:

```text
||f^{n+1}||_{M_f} <= ||f_dag||_{M_f}
```

when the origin is admissible, which it is for no-slip walls.  More generally,
it is the nearest admissible state.  The wall multiplier cannot add kinetic
energy through admissible virtual velocities because

```text
<lambda, C_h^w v> = 0 for all v in K_h.
```

Therefore this remedy is not damping.  It is the exact metric projection onto
the physical constraint manifold.

## 9. Force Covectors In The New Space

SP-AI and SP-AK define capillary and gravity forces as face covectors:

```text
r_sigma = -T_q(q)^T dE_sigma/dq,
r_g     = -T_m(q)^T dPhi_g/dm.
```

The predictor face velocity is assembled as

```text
f_dag = f^n + dt M_f^{-1}(r_sigma + r_g + r_mu + r_other)
        + transport/convection/viscous predictor increments.
```

The physical acceleration after constraint enforcement is the `K_h` component
of this predictor.  The pressure and wall reactions remove only inadmissible
range/trace parts.  They must not be pre-subtracted by projecting the force
covector itself before the step, because that would reproduce the earlier
"force disappears under range projection" failure.

Diagnostics should report:

```text
force_l2_M
pressure_removed_l2_M
wall_removed_l2_M
K_h_residual_l2_M
D_h f_linf
C_h^w f_linf
```

For static hydrostatic states, `K_h_residual_l2_M` should be near zero.  For
rising bubbles it should be finite.

## 10. Compatibility With Capillary Benchmarks

### Static droplet

For a static circular droplet away from walls, the surface tension force should
lie in the pressure/component reaction range.  The wall block should be zero or
near roundoff because `C_h^w f_dag` is absent.  The constrained projection must
not create a wall-localized ring.

Acceptance:

```text
D_h f_linf      near solve tolerance
C_h^w f_linf    near solve tolerance
KE growth       near static tolerance
```

### Oscillating droplet

For a non-static closed interface, the non-pressure Hodge component must remain
available.  The wall constraint only removes wall trace components.  It must not
project away interior capillary modes.

Acceptance:

```text
K_h_residual_l2_M > 0 for non-static modes,
C_h^w f_linf near solve tolerance,
oscillation amplitude not suppressed by wall projection.
```

### Capillary wave

For periodic-horizontal/wall-vertical capillary waves, wall rows only apply on
the vertical walls present in the boundary contract.  Periodic directions must
not introduce artificial trace constraints.  The FCCD transport adjoint for
periodic-wall axes remains the operator used in SP-AI.

### Rising bubble

Gravity produces sustained buoyant forcing.  The constrained projection should
separate:

```text
hydrostatic pressure reaction,
wall reaction,
finite divergence-free/no-slip buoyant component.
```

The wall-localized `R_h f - B_h R_h f` defect should disappear because `R_h f`
is already no-slip.

## 11. Why Simpler Fixes Are Invalid

### Zeroing boundary faces is not enough

`zero_wall_velocity_face_components` constrains selected face entries.  The
diagnostic shows that `R_h f` can still have nonzero wall nodal values.  The
constraint must be on `B_h R_h f`, not merely on boundary face entries.

### Recomputing faces from clamped nodes is not enough

If one sets `u = B_h R_h f` and then replaces `f` by `face_fluxes(u)`, the new
face field need not be divergence-free in the pressure Hodge metric.  The next
PPE sees a large divergence defect.  This is exactly why disabling canonical
face state failed earlier.

### Penalizing wall mismatch is not enough

A penalty term

```text
alpha ||C_h^w f||^2
```

approximates the constraint but leaves a parameter-dependent slip and adds
nonphysical dissipation.  It is a useful preconditioner idea only if the limit
system remains the exact KKT constraint.

### CFL, smoothing, curvature caps, and DCCD/UCCD damping are not fixes

The defect is an algebraic split of one velocity into two states.  Reducing the
time step can delay accumulation, but it cannot restore

```text
f in K_h, u=R_h f, m=rho u.
```

## 12. Implementation-Oriented Operator Contract

The minimum implementation surface is:

```text
wall_trace_from_faces(faces) -> wall_trace
wall_trace_adjoint(lambda) -> face_covector
constrained_project_faces(f_dag, rho, pressure_context) -> (faces, p, lambda)
```

Adjoint identity required:

```text
<lambda, C_h^w f>_W = <(C_h^w)^T lambda, f>_F.
```

The wall trace rows are small compared with the pressure unknowns.  GPU-first
implementation should avoid dense host KKT assembly.  Viable routes are:

1. matrix-free block Krylov for `(p,lambda)`,
2. Schur-complement elimination of `lambda` if the wall block is cheap,
3. pressure solve preconditioned by the existing PPE operator plus a sparse wall
   correction.

Whichever route is chosen, acceptance is the equations, not iteration count.

## 13. Fail-Close Gates

A production run using preserved face state must fail closed unless:

```text
D_h f^{n+1}              <= tolerance_div
C_h^w f^{n+1}            <= tolerance_wall
||u^{n+1} - R_h f^{n+1}|| <= tolerance_reconstruct
||m^{n+1} - rho u^{n+1}|| <= tolerance_momentum
```

For checkpoint/restart:

```text
checkpoint stores f,u,m,
restart verifies D_h f, C_h^w f, u=R_h f, m=rho u,
same-map fingerprint remains required.
```

If any gate fails, continuing would mean advancing a state outside the discrete
phase space.

## 14. Conclusion

The corrected formulation is:

```text
conservative common-flux transport
+ variational capillary/gravity force covectors
+ transported face-mass metric
+ boundary-constrained face Hodge projection
+ single canonical face/nodal/momentum state
```

The rising-bubble blow-up is therefore not a reason to abandon face-native
projection.  It is evidence that the face-native projection must include the
wall trace constraint in the same variational KKT solve as pressure.
