---
ref_id: WIKI-T-161
title: "Retired Fixed-Stratum Variational Reinit Candidate"
domain: theory
status: RETIRED
tags: [reinitialization, ridge_eikonal, trace_preservation, variational_retraction, bregman_entropy, capillary_hodge, fail_closed, negative_knowledge]
sources:
  - path: docs/memo/short_paper/SP-AH_trace_preserving_reinit_projection.md
  - path: docs/wiki/theory/WIKI-T-160.md
  - path: docs/memo/short_paper/SP-AG_discrete_reinit_capillary_hodge_contract.md
  - path: docs/02_ACTIVE_LEDGER.md
depends_on:
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-160]]"
  - "[[WIKI-T-155]]"
  - "[[WIKI-T-157]]"
  - "[[WIKI-T-081]]"
  - "[[WIKI-T-150]]"
  - "[[WIKI-X-041]]"
---

# Retired Fixed-Stratum Variational Reinit Candidate

## Curation Note

This card is retained as negative knowledge.  It records the fixed-stratum
variational retraction candidate that followed [[WIKI-T-160]], but the
implementation route was abandoned after ch14 N=32, T=10 validation showed
abnormal long-time droplet shape.  Do not use this card as a YAML contract,
code route, or production implementation instruction.  Its active value is the
diagnostic principle: reinitialization may not hide trace, volume, material, or
topology defects.

## Claim

The retired candidate reinitialization contract was a fixed-stratum
variational retraction:

```text
q_T -- Pi_{alpha,tau,V,M} --> q_R.
```

`alpha` is the fixed nondegenerate trace/topology stratum.  On that stratum,
`Pi` was intended to preserve trace coordinates through affine rows
`A_tau delta q=beta_tau(q_0)`, phase/topology guards, volume constraints, and
optional material invariants.  If the admissible set is empty or the state
leaves the stratum, a valid future route would have to fail closed or enter a
declared topology/defect route.  It must not apply `phi` shift, clipping, or
mass-only repair as a substitute.  It also must not treat an arbitrary QP objective as
physics; any tangent quadratic must come from the representation
free-energy Hessian.

## Trace Stratum

For a linear cut edge `e=(i,j)` with old root fraction `r_e`:

```text
(1-r_e) q_i + r_e q_j = 1/2.
```

If the reference profile `q_0` already lies on that discrete trace plane,
trace preservation by a correction `delta q` is:

```text
(1-r_e) delta q_i + r_e delta q_j = 0.
```

For the fully discrete carrier, `q_0=H(phi_d/eps_local)` may have the correct
continuum zero set but not the same linearly interpolated `q=1/2` edge root.
The generic row is therefore affine:

```text
A_tau(alpha,q_T) delta q = beta_tau(q_0),
beta_tau(q_0) = t_alpha - A_tau q_0.
```

The homogeneous form is the exact-trace chart `beta_tau=0`.

For higher-order trace spaces, the implementation must expose linear trace
DOFs if it wants the convex variational retraction theorem.  A genuinely
nonlinear root update is a separate theory.

## Admissible Set

Let `q_0` be the profile reconstructed from the trace-preserving
Ridge--Eikonal geometry extension.  The correction is `delta q=q_R-q_0`.

```text
K_alpha =
{ delta q :
  A_tau delta q = beta_tau(q_0),
  B_sigma delta q <= b_sigma,
  C_comp delta q = Delta V_comp,
  C_mat delta q = Delta M_mat  or  Delta_Mat_Pi is recorded,
  -q_0 <= delta q <= 1-q_0 }.
```

The retraction is:

```text
q_R = argmin_{q_0+delta q in K_alpha} D_h(q_0+delta q || q_0)
```

For the bounded CLS carrier, the default local representation defect is
Bernoulli relative entropy:

```text
D_h(q || q_0)
= sum_i dV_i [
    q_i log(q_i/q_0,i)
  + (1-q_i) log((1-q_i)/(1-q_0,i))
  ].
```

The quadratic metric `dV_i/[q_0,i(1-q_0,i)]` is only the entropy-Hessian
tangent approximation.

## Theorems

If `K_alpha` has an interior feasible point, it is convex and the entropy
defect is strictly convex.  Therefore the retraction exists and is unique.
Active-bound solutions are KKT/subgradient limits of the same variational
principle.

If `delta q=0` is feasible, it is the unique minimizer.  This gives identity on
admissible no-physics states.

`A_tau delta q=beta_tau(q_0)` puts `q_R=q_0+delta q` on every target trace
coordinate.  Sign/topology inequalities prevent new crossings.  Therefore:

```text
tau_h(q_R) = tau_h(q_T).
```

Volume constraints give global or component-wise volume preservation.  Material
constraints either preserve material/profile invariants or create a named
defect:

```text
Delta_Mat_Pi = M_h(q_R) - M_h(q_T).
```

Since physical surface energy is a trace functional,

```text
S_h(q) = S_hat_h(tau_h(q)),
```

trace preservation gives:

```text
Delta S_Pi = 0.
```

## Hodge Compatibility

The physical capillary cochain is built from the transport endpoint
`q^n -> q_T`.  Reinitialization is not a velocity-generated virtual
displacement.  Since the projection preserves `tau_h(q_T)` and never replaces
the full cochain by its pressure-range representative, it cannot delete the
dynamic Hodge residual:

```text
h_sigma(q_T) = c_sigma(q_T) - Pi_R c_sigma(q_T).
```

Static traces remain static when `h_sigma=0`; dynamic traces remain capable of
release when `h_sigma != 0`.

## Mass-Only Repair Is Not A Projection

A mass-only update `delta q=lambda w(q_0)` preserves a cut-edge trace only if:

```text
lambda [(1-r_e)w_i + r_e w_j] = 0.
```

For nonzero volume repair, this requires:

```text
(1-r_e)w_i + r_e w_j = 0
```

on every cut edge.  That is an exceptional condition, not a generic identity.
Therefore mass-only repair is not a valid trace-preserving reinitialization
principle.

## Retired Candidate Contract

Use this card after [[WIKI-T-160]] only as a warning record.  The following
configuration surface names the abandoned candidate and must not be exposed as
the current route:

```text
projection.method: trace_preserving_conservative
projection.form: constrained_variational_retraction
projection.profile_potential: bernoulli_relative_entropy
projection.trace_space: edge_p1
projection.trace_rhs: affine_from_reference_profile
projection.volume: global_or_componentwise
projection.material: constrained_or_defect_ledger
projection.solver: entropy_dual_newton
projection.tangent_qp: entropy_hessian_only
projection.geometry: ridge_eikonal_fmm_from_trace
projection.topology: fixed_stratum_fail_closed
projection.infeasible: fail_closed
```

Any future revival would have to use row operators for `A_tau`, conservation
rows, and the entropy dual Newton Jacobian.  Dense QP matrices, post-solve
clipping, mass-only repair, and active bounds that push topology labels to
`q=1/2` are not this method.

Acceptance would have to be by affine constraint residuals such as
`||A_tau delta q-beta_tau||`, conservation residuals, and named defect ledgers,
not benchmark names, selected shapes, or arbitrary numerical examples.  Since
the tested route failed long-time droplet-shape validation, this acceptance
surface is archival rather than active.
