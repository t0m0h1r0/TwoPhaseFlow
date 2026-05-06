# SP-AH: Fixed-Stratum Variational Reinitialization Retraction

**Date**: 2026-05-06
**Status**: RETIRED / negative research memo
**Scope**: ch14 reinitialization theory, fixed-topology trace strata, conservative variational profile retraction, abandoned implementation route
**Companion papers**: SP-AF, SP-AG, SP-AD, SP-AC, SP-AA
**Branch-only provenance**: theory, discretization, variational-correction,
and implementation co-design artifacts were created on the abandoned ch14 work
branch, but are intentionally not carried into this docs-only main cutout.

## 2026-05-06 Outcome

This memo is retained as theory provenance and negative knowledge, not as a
production route.  The subsequent trace-preserving retraction implementation
was abandoned after ch14 long-time validation: the N=32, T=10 oscillating
droplet run showed abnormal shape evolution rather than a trustworthy
capillary mode.  Therefore the implementation commit and YAML/config surface
for this route are intentionally excluded from the docs-only main cutout.

The valid lesson is theoretical: any reinitialization used in a capillary run
must name its trace, conservation, material, and topology defects instead of
silently moving shape.  The particular fixed-stratum entropy-dual retraction
below is a retired candidate unless a future derivation and validation replace
this negative outcome.

## Abstract

Ridge--Eikonal reinitialization should be a representation retraction, not a
hidden shape evolution.  This memo records a candidate formulation on a fixed
nondegenerate trace/topology stratum.  On that stratum, the candidate
retraction tries to preserve the discrete trace, volume, bounds, and any
declared material-profile invariants through affine trace rows
`A_tau delta q=beta_tau(q_0)`; otherwise it records named defects or fails
closed.  The objective is not an arbitrary QP: the intended formulation is a
constrained variational retraction that minimizes a representation
free-energy defect, such as Bernoulli relative entropy from the canonical
redistanced profile, on the fixed physical/geometric fiber.  A quadratic
program is only the entropy-Hessian tangent approximation, not the physics.
If the fiber is empty or the state leaves the stratum, no valid
trace-preserving conservative reinitialization exists for that step.  The
solver should not replace this outcome by a `phi` shift, clipping, mass-only
repair, or arbitrary SPD-QP.

## 1. Why SP-AG Needed Completion

SP-AG established the fully discrete split:

```text
q^n --T_h(u_f)--> q_T
q_T --Pi_h--> q^{n+1}.
```

It also required `tau_h`, `V_h`, and `S_h` to be part of the reinit ledger.
The remaining gap was the exact mathematical identity of `Pi_h`.  A volume-only
projection can preserve `V_h` while moving the `q=1/2` trace; this is precisely
the nonphysical shape motion found in ch14.  The candidate theory replaced
"mass correction" by a fixed-stratum constrained variational retraction, but
the attempted implementation route did not survive validation.

No benchmark-specific shape, resolution, or arbitrary numerical example is a
valid premise of this theory.  The premises are finite spaces, trace strata,
constraints, and functionals.

## 2. Fixed Trace Stratum

Let `Q_h = R^n` be the discrete carrier space.  The threshold is `q=1/2`.
The trace map is not globally smooth: cut edges can be created, deleted, hit a
vertex, merge, or split.  Therefore the theory is stated on a stratum
`Omega_alpha`.

A stratum `Omega_alpha` fixes:

- the cut edge or trace-element set;
- phase labels on uncut edge endpoints;
- optional connected-component labels;
- wall/contact trace constraints;
- the interpolation model for trace coordinates.

For a linear cut edge `e=(i,j)`, the target trace coordinate is the old
root fraction `r_e`:

```text
(1-r_e) q_i + r_e q_j = 1/2,        0 < r_e < 1.
```

If the reference profile `q_0` already satisfies this discrete trace equation,
a correction `delta q` preserves this trace coordinate iff:

```text
(1-r_e) delta q_i + r_e delta q_j = 0.
```

In the literal finite-dimensional carrier, however, `q_0=H(phi_d/eps_local)`
need not put the linear `q=1/2` edge root at the old `r_e`, even when `phi_d`
has the correct continuum zero set.  The generic discrete row is therefore
affine:

```text
A_tau(alpha,q_T) delta q = beta_tau(q_0),
beta_tau(q_0) = t_alpha - A_tau q_0.
```

The homogeneous form is the exact-trace chart `beta_tau=0`, not the general
discrete statement.

For higher-order trace spaces, the trace representation must expose linear
trace degrees of freedom, such as fixed trace-node or trace-moment constraints,
if the convex variational retraction theorem is to apply.  A genuinely
nonlinear trace-root update is a different theory.

## 3. Product Representation State

The interface representation separates geometry, metric extension, and
material profile:

```text
state = (gamma_h, phi_d, q_h)
gamma_h = tau_h(q_T)
phi_d   = signed-distance-like extension from gamma_h
q_h     = material/color profile for density and viscosity closures
```

Only `gamma_h` is the surface-energy geometry.  `phi_d` is the metric
extension used for curvature/normal quality.  `q_h` is the diffuse material
profile.  Reinitialization may repair `phi_d` and `q_h` only without moving
`gamma_h`.

## 4. Admissible Set

Let `q_0` be the profile reconstructed from the trace-preserving metric
extension, e.g. `q_0 = H(phi_d/eps_local)`.  Define `delta q = q_R - q_0`.
The admissible set is:

```text
K_alpha =
{ delta q :
  A_tau delta q = beta_tau(q_0),
  B_sigma delta q <= b_sigma,
  C_comp delta q = Delta V_comp,
  C_mat delta q = Delta M_mat  or  Delta_Mat_Pi is recorded,
  -q_0 <= delta q <= 1-q_0 }.
```

The roles are:

- `A_tau` and `beta_tau`: exact target trace-coordinate preservation.
- `B_sigma`: sign, topology, wall/contact admissibility.
- `C_comp`: global or component-wise volume preservation.
- `C_mat`: optional material/profile invariants.
- box bounds: `0 <= q_R <= 1`.

The retraction is:

```text
q_R = argmin_{q_0+delta q in K_alpha} D_h(q_0+delta q || q_0),
```

where `D_h` is a representation free-energy/Bregman defect.  For a bounded
volume-fraction carrier, the default physically meaningful local choice is:

```text
D_h(q || q_0)
= sum_i dV_i [
    q_i log(q_i/q_0,i)
  + (1-q_i) log((1-q_i)/(1-q_0,i))
  ].
```

Its tangent quadratic has metric
`R_entropy,ii=dV_i/[q_0,i(1-q_0,i)]`.  An arbitrary SPD metric has no physical
standing.

## 5. Existence, Uniqueness, And Failure

`K_alpha` is an intersection of affine equalities, linear inequalities, and a
box.  Hence it is closed and convex.  On the open box `0<q<1`, the entropy
defect is strictly convex, so an interior feasible fiber gives a unique
minimizer.  Boundary solutions are active-bound KKT limits of the same
variational problem.

If `K_alpha` is empty, the constraints are mutually incompatible.  The theory
does not permit a trace-moving workaround:

```text
empty K_alpha
=> no valid trace-preserving conservative reinit exists on this stratum
=> fail closed or enter a declared topology/defect route.
```

This fail-closed clause is part of the theorem.  A method that always returns a
field by violating trace, volume, bounds, or material constraints is not this
method.

## 6. Theorems

### T1. Identity

If `delta q=0` is feasible, then it is the unique minimizer because the
representation defect is nonnegative and strictly convex around `q_0`:

```text
Pi_{alpha,tau,V,M}(q_0) = q_0.
```

Thus a no-physics state cannot be moved by reinitialization.  If profile repair
is needed, only representation degrees compatible with the affine trace rows may
change.  In the exact-trace chart `beta_tau=0`, this reduces to the homogeneous
statement used above.

### T2. Trace Preservation

For every cut edge:

```text
(1-r_e)(q_{0,i}+delta q_i) + r_e(q_{0,j}+delta q_j)
= 1/2
```

because `A_tau delta q=beta_tau(q_0)`.  Sign inequalities prevent new uncut-edge
crossings.  Therefore:

```text
tau_h(q_R) = tau_h(q_T)
```

on `Omega_alpha`.

### T3. Volume And Material Accounting

If component-volume constraints are imposed:

```text
V_h(q_R) = V_h(q_T).
```

If material constraints are imposed, their invariants are preserved.  If they
are not imposed, the difference is a named representation defect:

```text
Delta_Mat_Pi = M_h(q_R) - M_h(q_T).
```

This prevents diffuse density-band changes from being hidden behind trace
preservation.

### T4. Surface Energy

The physical capillary energy is a trace functional:

```text
S_h(q) = S_hat_h(tau_h(q)).
```

Therefore:

```text
S_h(q_R) = S_h(q_T),        Delta S_Pi = 0
```

for fixed-stratum trace-preserving reinitialization.

### T5. Hodge Compatibility

The production capillary cochain is built from physical transport:

```text
q^n --T_h(u_f)--> q_T.
```

Reinitialization is not part of the velocity-generated virtual displacement.
Since `Pi_{alpha,tau,V,M}` preserves `tau_h(q_T)` and does not replace
`c_sigma` by its pressure-range representative, it cannot delete a dynamic
Hodge residual:

```text
h_sigma(q_T) = c_sigma(q_T) - Pi_R c_sigma(q_T).
```

Static traces remain static when `h_sigma=0`; nonstatic traces remain capable
of capillary release when `h_sigma != 0`.  Material/profile coefficient changes
must be handled by `C_mat` or `Delta_Mat_Pi`.

## 7. Why Mass-Only Repair Is Not Generic

A mass-only repair has the form:

```text
delta q = lambda w(q_0).
```

On a cut edge, trace preservation would require:

```text
lambda [(1-r_e)w_i + r_e w_j] = 0.
```

For a nonzero volume repair, `lambda != 0`, so every cut edge would need:

```text
(1-r_e)w_i + r_e w_j = 0.
```

This is an exceptional condition, not an identity of the standard
interface-band weights.  Therefore mass-only repair is not a valid generic
reinitialization retraction.  It can only be accepted if it is re-derived as a
trace-constrained variational retraction or if its trace defect is explicitly
recorded and the route is not used as production trace-preserving reinit.

## 8. Degeneracy And Topology Events

The fixed-stratum theory excludes:

- root at a vertex;
- vanishing edge contrast;
- crossing creation or deletion;
- component merger or breakup;
- wall/contact topology changes;
- empty or ill-conditioned admissible set.

These are exits from `Omega_alpha`.  The solver must choose one of:

1. enter a declared topology-event theory;
2. relax a named constraint and record the corresponding defect;
3. fail closed.

It must not silently shift the trace.

## 9. Retired YAML Candidate

This YAML surface is archival.  It names the mathematical candidate that was
tested and abandoned; it must not be read as an accepted production interface.
Any future route must earn a new theory/validation record before exposing a
similar configuration.

The candidate implementation would expose the same discrete objects as the
theory:

```text
TraceRows        edge masks, root fractions, beta_tau
ConservationRows global/component/material rows
RetractionSolver entropy dual Newton with row operators
Diagnostics      affine trace, volume/material, topology, entropy residuals
```

The hot path would need to be GPU-resident.  It should implement `apply_E`, `apply_ET`,
and entropy-dual `apply_J` as vectorized row operators, not as a dense QP
matrix.  Topology/sign violations are fixed-stratum exits; they are not repaired
by clipping or by active bounds at `q=1/2`.

The retired configuration surface was:

```yaml
interface:
  reinitialization:
    method: ridge_eikonal
    projection:
      method: trace_preserving_conservative
      form: constrained_variational_retraction
      profile_potential: bernoulli_relative_entropy
      trace_space: edge_p1
      trace_rhs: affine_from_reference_profile
      volume: global_or_componentwise
      material: constrained_or_defect_ledger
      solver: entropy_dual_newton
      tangent_qp: entropy_hessian_only
      geometry: ridge_eikonal_fmm_from_trace
      topology: fixed_stratum_fail_closed
      infeasible: fail_closed
```

Acceptance must be by residuals and defects:

```text
||A_tau delta q - beta_tau||        trace residual
||C_comp delta q - Delta V||        volume residual
bounds/sign residual                topology guard
Delta S_Pi                          surface-energy projection defect
Delta_Mat_Pi                        material-profile projection defect
labelled Hodge residuals            static/dynamic consistency
```

No acceptance criterion may rely on a benchmark name, selected shape, or
arbitrary numerical example.

## 10. Conclusion

The abandoned candidate can be summarized as:

```text
Ridge--Eikonal reinit
= fixed-stratum, trace-preserving, conservative, bounded representation
  variational retraction with material/profile defect accounting and
  fail-closed exits.
```

It is generic as a mathematical candidate because it is stated in spaces,
strata, constraints, and functionals.  It is not a production solver route
because the associated implementation/validation path produced abnormal
long-time droplet shape.  The surviving result is a fail-closed diagnostic
principle: reinitialization defects must be named and measured, and
infeasibility is a mathematical outcome, not a reason to apply clipping,
mass-only repair, or arbitrary QP replacement.
