# SP-AM: Discrete Boundary-Constrained Face Hodge Operator

**Status**: ACTIVE discretization specification  
**Date**: 2026-05-09  
**Scope**: implementation-ready discretization of SP-AL for wall-bounded
conservative common-flux two-phase flow  
**Companion papers**: SP-AL, SP-AJ, SP-AK, SP-AI, SP-W, SP-X

## 1. Goal

SP-AL defines the correct target space:

```text
K_h = { f : D_h f = 0 and B_h R_h f = 0 }.
```

This note fixes the concrete discretization of each symbol using the current
FCCD face-state pipeline.  The rule is: reuse the production pressure and
transport operators, add only the missing wall-trace operator and its adjoint,
and solve a single constrained projection.

The accepted step must publish one state:

```text
f^{n+1} in K_h,
u^{n+1} = R_h f^{n+1},
m^{n+1} = rho^{n+1} u^{n+1}.
```

No post-projection nodal overwrite may change `u` after publication.

## 2. Existing Operators To Reuse

The current code already provides the following operators.

```text
D_h(f)      = FCCDDivergenceOperator.divergence_from_faces(f)
F_h(u)      = FCCDDivergenceOperator.face_fluxes(u)
R_h(f)      = FCCDDivergenceOperator.reconstruct_nodes(f)
G_A(p)      = FCCDDivergenceOperator.pressure_fluxes(
                  p, rho, pressure_force_contract=variational_adjoint, ...)
```

The pressure complex documentation states the signed Green identity:

```text
<G_A p, w>_{M_f} + <p, D_h w>_W = 0.
```

SP-AM does not change this identity.  It appends wall trace rows to the same
metric projection.

## 3. Array Shapes In 2D

Let `Nx, Ny` be cell counts.  Nodal arrays use shape

```text
N_h component: (Nx+1, Ny+1).
```

Face-normal arrays use:

```text
f_x: (Nx,   Ny+1)    x-normal faces between x nodes
f_y: (Nx+1, Ny  )    y-normal faces between y nodes
```

The flattened face vector is

```text
f = concat(vec(f_x), vec(f_y)).
```

The scalar pressure/RHS vector uses nodal/cell-compatible pressure shape already
accepted by the active PPE operator.  SP-AM treats that pressure vector as the
same one used by `pressure_fluxes`; it does not introduce a second pressure
space.

## 4. Discrete Reconstruction Operator R_h

The current reconstruction is axis-wise averaging:

For nonperiodic axis `a`,

```text
(R_h f_a)_{i_a=0}     = f_a at first face,
(R_h f_a)_{1..N_a-1} = 1/2 (f_a,left + f_a,right),
(R_h f_a)_{i_a=N_a}  = f_a at last face.
```

For periodic axis `a`,

```text
(R_h f_a)_i = 1/2 (f_a_i + f_a_{i-1}),
periodic image nodes are synchronized.
```

This defines a linear map

```text
R_h : F_h -> N_h.
```

The important point is that `R_h` is not a no-slip operator.  Therefore the wall
constraint must be built as a separate map `B_h R_h`, not as boundary-face
zeroing.

## 5. Wall Trace Operator C_w = B_h R_h

Define

```text
C_w = B_h R_h : F_h -> W_h.
```

`W_h` is the list of no-slip wall nodal velocity components.  For `bc_type=wall`
in 2D:

```text
left wall:   u_x[0, j], u_y[0, j]      for j=0..Ny
right wall:  u_x[Nx,j], u_y[Nx,j]      for j=0..Ny
bottom wall: u_x[i, 0], u_y[i, 0]      for i=0..Nx
top wall:    u_x[i,Ny], u_y[i,Ny]      for i=0..Nx
```

Duplicate corner entries must not be counted twice in the same component.  A
canonical implementation should emit unique `(component, i, j)` trace rows:

```text
wall_nodes = unique boundary nodal indices for every constrained component.
```

For mixed boundary types such as `periodic_wall`, wall rows are emitted only on
wall axes.  Periodic image nodes are not independent wall constraints.

The discrete trace norm may be unweighted for the equality constraint, but
diagnostics should report a weighted wall trace:

```text
||C_w f||_{W_h}^2 = sum_{wall node k} omega_k |(R_h f)_k|^2,
```

where `omega_k` is a boundary quadrature length/area.  Equality solving itself
uses rows; metric scaling can be absorbed into `lambda` or used as row
preconditioning.

## 6. Wall Trace Adjoint

The wall trace adjoint must satisfy

```text
<lambda, C_w f>_{W_h} = <C_w^T lambda, f>_F.
```

A direct matrix-free implementation is:

1. scatter `lambda` into a nodal vector array on constrained wall nodes,
2. apply the adjoint of the reconstruction `R_h^T`,
3. return face covector arrays shaped like `(f_x,f_y)`.

For the nonperiodic reconstruction above, `R_h^T` is local:

```text
interior nodal lambda contributes 1/2 to each adjacent face,
lower boundary nodal lambda contributes 1 to first face,
upper boundary nodal lambda contributes 1 to last face.
```

For periodic axes, each nodal lambda contributes `1/2` to the local face and
`1/2` to the previous periodic face.  Periodic image synchronization must match
the same convention as `R_h`.

The first unit test for the operator is random adjointness:

```text
dot_W(lambda, wall_trace_from_faces(f))
  == dot_F(wall_trace_adjoint(lambda), f)
```

on uniform, nonuniform, wall, and periodic-wall grids, CPU and GPU.

## 7. Face Mass Metric M_f

The face metric must match the velocity kinetic energy used by common-flux
transport and pressure projection.  With inverse-density pressure coefficient

```text
alpha_f = pressure_flux coefficient = 1/rho_f
```

the kinetic face mass is

```text
M_f = Q_f / alpha_f = Q_f rho_f.
```

`Q_f` is the geometric face/control measure used by `D_h` and pressure
Green identity.  For a diagonal implementation, store:

```text
face_mass_components[axis] = face_volume_weight[axis] * face_density[axis].
```

If the current pressure path internally uses `pressure_fluxes` without exposing
`Q_f`, the constrained projection can still be written in terms of the active
`G_A` for pressure and a diagonal `M_f^{-1}` for wall covectors.  But the
acceptance gate must verify the Green identity with the chosen face weights.

## 8. Predictor Face Velocity

The predictor face velocity is the already assembled face-native quantity:

```text
f_dag = f^n
        + Delta f_transport/viscous/convection
        + dt M_f^{-1}(r_sigma + r_g + r_mu + ...)
        - dt pressure_history_faces
```

The important discretization rule is that all force covectors are converted to
face accelerations with the same `M_f` used by the constrained projection.

Do not preproject `r_sigma` or `r_g` into `K_h`.  The projection must see the
full physical force and remove only inadmissible pressure/wall-reaction
components.

## 9. Constrained Projection System

Unknowns:

```text
p        pressure increment/base scalar
lambda   wall no-slip multiplier
```

Primary state:

```text
f = f_dag - dt G_A(p) - dt M_f^{-1} C_w^T lambda.
```

Constraints:

```text
D_h f = 0,
C_w f = 0.
```

Therefore the coupled linear system is:

```text
[ D_h G_A                  D_h M_f^{-1} C_w^T       ] [p     ]
[ C_w G_A                  C_w M_f^{-1} C_w^T       ] [lambda]

= 1/dt * [ D_h f_dag ]
         [ C_w f_dag ].
```

Sign convention must match the existing projection convention

```text
f_new = f_dag - dt pressure_faces + dt force_faces.
```

If `G_A` already includes interface affine-jump/capillary reaction terms, those
terms stay inside the pressure block exactly as they do in the current PPE.
The wall block is added around that active pressure map.

## 10. Matrix-Free Block Application

A GPU-first operator should expose:

```text
apply_Ap(p):
    gp = pressure_fluxes(p, rho, active pressure kwargs)
    return divergence_from_faces(gp), wall_trace_from_faces(gp)

apply_Al(lambda):
    wf = inv_face_mass * wall_trace_adjoint(lambda)
    return divergence_from_faces(wf), wall_trace_from_faces(wf)

apply_block(p, lambda):
    a11, a21 = apply_Ap(p)
    a12, a22 = apply_Al(lambda)
    return a11 + a12, a21 + a22
```

The RHS is:

```text
rhs_p = divergence_from_faces(f_dag) / dt
rhs_l = wall_trace_from_faces(f_dag) / dt.
```

The solve result updates:

```text
pressure_faces = pressure_fluxes(p, rho, ...)
wall_faces     = inv_face_mass * wall_trace_adjoint(lambda)
f_new          = f_dag - dt pressure_faces - dt wall_faces
u_new          = reconstruct_nodes(f_new)
m_new          = rho * u_new
```

Here `wall_faces` is named as an acceleration/reaction with the same sign as
the stationarity equation.  A sign unit test must check that applying the solve
reduces `C_w f` rather than doubles it.

## 11. Schur Options

The full block KKT Schur is the most faithful first target.  Two equivalent
solver organizations are allowed if they pass the same gates.

### Option A: monolithic block Krylov

Solve `(p,lambda)` with a matrix-free Krylov method.  Precondition with the
existing pressure PPE approximation on the pressure block and a diagonal or
small sparse approximation for the wall block.

Pros:

```text
closest to theory,
one residual,
easy fail-close semantics.
```

Risk:

```text
needs careful scaling between pressure RHS and wall trace rows.
```

### Option B: pressure Schur plus wall correction

Eliminate pressure approximately or exactly using the existing PPE solver, then
solve for lambda in the wall Schur complement:

```text
S_w lambda =
  C_w f_dag/dt - C_w G_A A_p^{-1} D_h f_dag/dt.
```

Pros:

```text
reuses existing pressure solver strongly,
wall system is small.
```

Risk:

```text
any inexact pressure solve must be included in final coupled residual gates.
```

### Option C: constrained reconstruction basis

Construct a reconstruction/projection pair whose range already satisfies
`B_h R_h f=0`, then use the existing pressure projection inside that reduced
face space.

Pros:

```text
fast once built,
simple post-step publication.
```

Risk:

```text
harder to prove exact adjointness with current FCCD operators;
more invasive.
```

For first implementation, Option A is the clearest correctness target.  Option
B is a reasonable performance refinement only after the monolithic residual is
available as a reference.

## 12. Boundary Rows In 2D

The wall trace builder should emit rows from face arrays directly, not by
materializing a dense matrix.

For `u_x = R_x f_x`:

```text
left/right x-wall:
  u_x[0, j]  = f_x[0, j]
  u_x[Nx,j]  = f_x[Nx-1,j]

bottom/top y-wall values of u_x:
  u_x[i,0]   = reconstruction in x direction at node (i,0)
  u_x[i,Ny]  = reconstruction in x direction at node (i,Ny)
```

For `u_y = R_y f_y`:

```text
bottom/top y-wall:
  u_y[i,0]   = f_y[i,0]
  u_y[i,Ny]  = f_y[i,Ny-1]

left/right x-wall values of u_y:
  u_y[0,j]   = reconstruction in y direction at node (0,j)
  u_y[Nx,j]  = reconstruction in y direction at node (Nx,j)
```

This is why zeroing only normal boundary faces is insufficient: no-slip also
requires tangential components on the wall trace.

## 13. Nonuniform Grid Weights

The equality constraints are geometric trace constraints and do not depend on
mesh uniformity.  However, residual norms and preconditioner scaling should use
nonuniform boundary quadrature:

```text
left/right wall node weight  ~ local dy_j
bottom/top wall node weight  ~ local dx_i
corner weight                ~ sum or average of adjacent half-edges per component
```

The face mass metric must use the same nonuniform face/control weights as the
pressure Green identity.  Do not use uniform-grid constants in the wall block
when `alpha_grid > 1`.

## 14. Interaction With Pressure History

Pressure history in the current route is a face acceleration cochain.  With
wall constraints, history must be split consistently:

```text
pressure_history_faces = G_A(p_history)
wall_history_faces     = M_f^{-1} C_w^T(lambda_history)  [optional]
```

The first implementation may choose first-order wall reaction history:

```text
lambda_history = none at startup,
projection solves current lambda each step.
```

But then the time integrator contract must state that the BDF2 pressure
coordinate history does not include extrapolated wall reaction until a wall
history mode is implemented.  Fail-close if a second-order pressure-history
contract claims both pressure and wall reactions are extrapolated but only
pressure is stored.

## 15. Diagnostics

Every debug step should record:

```text
boundary_hodge_div_linf          = ||D_h f||_inf
boundary_hodge_wall_linf         = ||C_w f||_inf
boundary_hodge_reconstruct_linf  = ||u - R_h f||_inf
boundary_hodge_momentum_linf     = ||m - rho u||_inf
boundary_hodge_pressure_l2_M     = ||dt G_A p||_{M_f}
boundary_hodge_wall_l2_M         = ||dt M_f^{-1} C_w^T lambda||_{M_f}
boundary_hodge_residual_l2       = coupled KKT residual
```

The wall-localized mismatch from the RCA should become:

```text
wall_linf near solver tolerance,
interior mismatch unchanged near zero,
no nodal post-clamp delta after projection.
```

## 16. Acceptance Tests

### T1: wall trace adjoint identity

Random face fields and random wall multipliers:

```text
<lambda, C_w f>_W == <C_w^T lambda, f>_F.
```

Run on:

```text
uniform wall,
nonuniform wall,
periodic_wall,
CPU,
GPU.
```

### T2: manufactured wall projection

Choose a face field with zero divergence but nonzero wall trace.  Project with
`D_h` disabled or pressure RHS zero.  The wall block must remove `C_w f` without
creating pressure divergence beyond tolerance.

### T3: manufactured pressure projection

Choose `f_dag = G_A p0`.  With no wall trace, the pressure block removes it and
lambda remains zero.

### T4: coupled manufactured projection

Choose

```text
f_dag = G_A p0 + M_f^{-1} C_w^T lambda0 + h,
h in K_h.
```

Projection should recover `h` to tolerance.

### T5: static wall-bounded zero force

`sigma=g=0` remains exactly zero.

### T6: static circular droplet

`sigma>0,g=0` keeps tiny KE and zero wall trace.  No wall ring is introduced.

### T7: rising bubble one-step RCA regression

Normal SI one-step should satisfy:

```text
wall mismatch drops from O(1e-4) to tolerance,
D_h f remains near tolerance,
momentum consistency remains near tolerance.
```

### T8: short N=32x64 run

At `T=0.002`, reproduce previous stable short behavior but with:

```text
face_node_mismatch wall = tolerance,
projected_face_div      = tolerance,
volume drift            small,
no early blow-up.
```

## 17. Fail-Close UX

Suggested YAML:

```yaml
numerics:
  projection:
    face_flux_projection: true
    canonical_face_state: true
    preserve_projected_faces: true
    boundary_hodge:
      mode: constrained_kkt
      wall_trace: reconstruct_nodes
      metric: transported_face_mass
      pressure_block: variational_adjoint
      wall_reaction_history: first_order
      gate: fail_close
```

Invalid combinations:

```text
boundary_hodge.mode=off with preserve_projected_faces=true and wall bc
boundary_hodge.mode=constrained_kkt with raw pressure_force_contract
wall_reaction_history=bdf2 without checkpointed lambda history
metric != transported_face_mass on conservative_common_flux
```

## 18. GPU-First Notes

Do not assemble the full dense KKT matrix.  Implement matrix-free calls over
CuPy arrays:

```text
wall_trace_from_faces
wall_trace_adjoint
inv_face_mass_apply
pressure_fluxes
divergence_from_faces
```

Use existing sparse/Krylov infrastructure only through operator callbacks.
Small wall blocks may be materialized as sparse GPU matrices if that is faster,
but the correctness reference should remain the matrix-free identities.

## 19. Minimal Implementation Order

1. Add `wall_trace_from_faces` and `wall_trace_adjoint` helpers with adjoint
   tests.
2. Add metric helpers for face mass and `M_f^{-1} C_w^T`.
3. Add a standalone constrained projection diagnostic solver for tiny grids.
4. Add matrix-free block application and residual diagnostics.
5. Integrate behind `boundary_hodge.mode=constrained_kkt`.
6. Publish `u=R_h f` only; fail if wall trace is nonzero.
7. Add checkpoint invariants for `D_h f`, `C_w f`, `u=R_h f`, and `m=rho u`.
8. Run T1--T8 before long rising-bubble runs.

## 20. Rank-Probe Refinement

The coupled projection is an operator theorem, not merely a syntactic KKT
block.  Before enabling `boundary_hodge.mode=constrained_kkt`, the
implementation must pass a small-grid rank and conditioning probe using the
same production operators that will be used at runtime.

Let

```text
A = [D_h; C_w],
B = [G_A, M_f^{-1} C_w^T].
```

The required rank gate is

```text
rank(A B) = rank(A).
```

This gate must be evaluated in the pressure quotient space appropriate to the
boundary topology.  A diagnostic dense probe on `Nx=6, Ny=5` found:

```text
wall:          rank(A B)=59/59, feasible but dt-scaled condition number grows
periodic_wall: rank(A B)=49/52, not production-ready
```

The mixed periodic-wall failure is not a reason to replace `G_A` by a generic
assembled `D_h^T`.  Such a replacement would bypass the pressure Green identity
and the affine/variational pressure contract.  The correct remedy is to put the
periodic duplicate rows and pressure variables in the same quotient space used
by the production pressure operator, then rerun the rank gate.

The rank gate is necessary but not sufficient.  The same probe must also report
conditioning after the physical `dt` scaling because

```text
f = f_dag - dt G_A p - dt M_f^{-1} C_w^T lambda
```

can make the pressure/wall blocks badly scaled.  A production solver therefore
requires block row scaling and preconditioning before long runs.

## 21. Conclusion

The discrete fix is not a new force model.  It is a completion of the discrete
constraint complex:

```text
pressure constraint: D_h f = 0
wall constraint:     B_h R_h f = 0
state identity:      u=R_h f, m=rho u
transport identity:  next flux=f
```

The wall operator is the missing row block in the existing face Hodge
projection.  Once it is included, the common-flux ledger, variational gravity,
closed-interface capillary force, and no-slip wall boundary live in one
discrete phase space.
