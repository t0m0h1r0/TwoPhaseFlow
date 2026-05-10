# CHK-RA-GEOM-CELL-FRACTION-006

## Purpose

User request:

> Deepen the investigation.  Clarify remaining issues from physics and
> mathematics, generate many solution ideas, and verify them to clarify the
> direction.  Theory first; no tactical patching.

This artifact focuses on the implicit compatibility projection:

```text
theta_C = A_h(Gamma(phi))_C.
```

The previous note proposed the compatibility bundle.  This note asks how the
projection can fail, what mathematical structure is required, and which solver
direction is most defensible.

## 1. Root Cause of the Remaining Problem

The compatibility equation is not a cell-local formula.  It couples cells
through shared nodal values of a continuous `phi` field:

```text
theta = A_h(Gamma(phi)).
```

Therefore three facts must be held simultaneously:

1. `theta_C` is the hard material volume.
2. `phi` must remain continuous enough to define `Gamma_h`, normals, and
   surface energy.
3. Not every bounded `theta` field is guaranteed to be representable by a
   continuous P1 trace on the current topology stratum.

The remaining issue is thus:

```text
Find a compatible continuous gauge phi for a transported theta without turning
the projection into a hidden physical force, hidden mass correction, or
topology guess.
```

## 2. Mathematical Form of the Projection

Given:

```text
theta^-     transported material fraction,
phi^-       predicted gauge,
S           current regular stratum,
```

solve:

```text
min_phi  1/2 ||phi - phi^-||_W^2
       + eta/2 ||L(phi - phi^-)||^2

subject to
  A_h^S(Gamma(phi))_C = theta^-_C       active mixed cells,
  sign inequalities for full/empty cells,
  periodic/wall/topology constraints.
```

The nonlinear equality is only smooth on a fixed stratum.  If the stratum
changes, the solver must either enter a declared topology route or fail close.

Linearization:

```text
r      = theta^- - A_h(Gamma(phi_k)),
J_A    = dA_h(Gamma(phi_k))/dphi,
W_eta  = W + eta L^T L,
```

Newton/SQP correction:

```text
min_delta  1/2 ||delta - delta_pred||_{W_eta}^2
subject to J_A delta = r.
```

In the simplest projection step `delta_pred=0`, giving:

```text
delta = W_eta^{-1} J_A^T
        (J_A W_eta^{-1} J_A^T)^{-1} r.
```

The Schur complement is over mixed cells, not all nodes:

```text
S_A = J_A W_eta^{-1} J_A^T.
```

This is the natural GPU target because `J_A` is sparse: each mixed cell row
touches only its corner nodes on a P1/Q1 trace.

## 3. Manufactured Probe Results

### P1. Smooth target from a perturbed ellipse

Starting from a compatible ellipse `phi0`, define:

```text
phi_target = phi0 + amp * eta_smooth,
theta_target = A_h(Gamma(phi_target)).
```

Then solve one linearized minimum-norm projection from `phi0` toward
`theta_target` on the original mixed-cell stratum.

Representative N=32 results:

```text
amp      init_max    after_max   case_changes  step_linf
1e-05    4.44e-05    1.25e-07       0          6.20e-04
3e-05    1.33e-04    3.47e-06       0          5.52e-03
1e-04    4.44e-04    2.48e-04       0          1.24e-01
3e-04    1.33e-03    8.30e-01      20          1.21e+01
1e-03    4.45e-03    9.95e-01      43          2.26e+02
```

Interpretation:

- small residuals can be reduced on a fixed stratum;
- full rank does not imply a safe large step;
- beyond a trust region, the linearized projection jumps strata and fails;
- conditioning is a first-class theoretical issue, not an implementation
  nuisance.

### P2. Constant shift target

For `theta_target=A_h(Gamma(phi0+shift))`, the residual can be reduced with no
case changes over the tested range, but the unconstrained minimum-norm
correction is not the physical constant shift:

```text
shift    after_max   case_changes  step_linf   const_error_linf
1e-06    1.01e-10       0          3.20e-06    4.20e-06
1e-05    1.08e-08       0          6.27e-05    7.27e-05
1e-04    1.14e-05       0          5.95e-03    6.05e-03
3e-04    1.37e-04       0          2.21e-02    2.24e-02
```

Interpretation:

```text
constraints alone do not choose the correct gauge.
```

The metric `W_eta`, the predictor `phi^-`, and smoothness/eikonal gauge terms
are not optional.  They are part of the mathematical definition of the
projection.

## 4. Residual Tasks

### RT1. Feasibility

Arbitrary `theta^- in [0,1]` may not lie in the image of
`A_h(Gamma(phi))` on the current stratum.

Required response:

```text
compatibility residual gate,
stratum-aware active-set logic,
explicit topology route or fail-close.
```

### RT2. Gauge nonuniqueness

Mixed-cell constraints are fewer than nodal unknowns.  The nullspace contains
many gauge changes that preserve `theta` to first order but alter normals,
curvature, and surface energy.

Required response:

```text
projection metric W_eta must be part of the theory,
not a numerical preference.
```

### RT3. Conditioning

`J_A` can be full row rank but ill-conditioned, especially near sliver cuts,
vertices, and topology changes.

Required response:

```text
trust region,
line search,
row scaling,
Schur preconditioning,
rank/condition fail-close.
```

### RT4. Inequality constraints

Full and empty cells are not equality constraints, but they impose sign
inequalities.  Violating them changes topology or creates spurious droplets.

Required response:

```text
active-set management and sign-margin certificates.
```

### RT5. Projection work

Changing `phi` while holding `theta` fixed can change surface energy.

Required response:

```text
Delta S_Pi is recorded as projection/gauge work,
never mixed into physical capillary work.
```

### RT6. Coupling to capillary virtual work

The same `J_A` used for projection must also define the bundle lift used in
capillary work.  Otherwise projection and force live on different tangent
spaces.

Required response:

```text
one compatibility derivative J_A,
one transport linearization T_theta,
one face metric M_f(theta).
```

### RT7. GPU feasibility

Full nonlinear dense KKT is not acceptable as the production endpoint.

Required response:

```text
sparse mixed-cell rows,
matrix-free W_eta^{-1},
Schur solve over active mixed cells,
fixed small Newton/trust iterations,
device-resident reductions and fail-close scalars.
```

## 5. Candidate Solution Ideas

### I1. Full nonlinear SQP on fixed stratum

Solve the constrained optimization directly until compatibility residual is
small.

Pros:

- most faithful to the theory;
- handles nonlinear area exactly within a stratum.

Cons:

- expensive;
- needs robust globalization;
- fail-close required at stratum changes.

Verdict: best reference algorithm, not necessarily production implementation.

### I2. Sequential linearized projection with trust region

Apply:

```text
J_A delta = r
```

with a trust-region bound on `delta` and line search that preserves case IDs.

Pros:

- directly supported by probes;
- simple to analyze;
- can fail close before topology corruption.

Cons:

- may require several iterations;
- needs condition/rank gates.

Verdict: best near-term theory direction.

### I3. Schur complement over mixed cells

Use:

```text
S_A = J_A W_eta^{-1} J_A^T.
```

Pros:

- problem size is number of mixed cells;
- sparse local `J_A`;
- natural GPU path.

Cons:

- `W_eta^{-1}` may be nonlocal if smoothness/eikonal regularization is used;
- preconditioning is essential.

Verdict: production-relevant linear algebra target.

### I4. Pure local PLIC correction

Adjust each mixed cell independently.

Pros:

- easy and GPU-friendly.

Cons:

- destroys continuous `Gamma_h`;
- not capillary-ready.

Verdict: reject as bridge projection; keep only as diagnostic/local initial
guess.

### I5. Penalty method instead of hard constraint

Minimize:

```text
||phi-phi^-||^2 + mu ||A_h(Gamma(phi))-theta^-||^2.
```

Pros:

- easier numerically.

Cons:

- local volume is no longer exact;
- violates the volume-first premise.

Verdict: reject for production physics.  It may be used only as a continuation
pre-solve if followed by a hard constraint solve.

### I6. Augmented Lagrangian

Use penalty plus multiplier updates.

Pros:

- more robust than pure SQP for nonlinear constraints;
- can reuse matrix-free pieces.

Cons:

- exactness depends on convergence;
- stopping criteria become physical contracts.

Verdict: possible solver technology, but only if final hard residual is
certified.

### I7. Gauge predictor from transported phi

Treat `phi^-` as the primary nullspace selector.

Pros:

- preserves history and dynamic modes;
- resolves the constant-shift nonuniqueness probe.

Cons:

- if `phi^-` is poor, projection can preserve bad geometry.

Verdict: necessary but insufficient; pair with quality diagnostics.

### I8. Eikonal/smoothness metric `W_eta`

Use a metric that penalizes rough gauge modes:

```text
W_eta = W + eta L^T L.
```

Pros:

- controls nullspace artifacts;
- protects normals/curvature.

Cons:

- changes surface energy through projection;
- can hide smoothing if not accounted.

Verdict: admissible only with `Delta S_Pi` ledger and hard `theta`.

### I9. Rank and sign-margin fail-close

Before and during projection, check:

```text
rank(J_A),
condition estimate,
max admissible step before sign/case change,
residual after line search.
```

Pros:

- prevents false physics.

Cons:

- may stop hard cases that need topology handling.

Verdict: mandatory.

### I10. Explicit topology event route

When the stratum changes, enter a separate reconstruction/topology update
instead of forcing fixed-stratum Newton.

Pros:

- physically honest.

Cons:

- large theory and implementation topic.

Verdict: needed eventually; outside the fixed-stratum bridge.

### I11. Moment-enriched theta state

Add centroids or moments to reduce gauge ambiguity.

Pros:

- improves reconstruction conditioning;
- carries geometry history in material state.

Cons:

- more transported quantities;
- moments need their own bounded conservative flux.

Verdict: promising if `phi` predictor is insufficient.

### I12. Energy-minimizing gauge selector

Use surface energy as part of the projection objective.

Pros:

- may choose smoother interfaces.

Cons:

- can act like artificial surface tension in projection;
- risks damping physical oscillations.

Verdict: not a default.  If used, its work must be explicitly recorded and not
counted as physical capillarity.

## 6. Clarified Direction

The best path is:

```text
fixed-stratum hard constrained projection
  + predictor-based gauge selection
  + W_eta smoothness/eikonal metric
  + trust-region and sign-margin gates
  + Schur complement over mixed cells
  + explicit Delta S_Pi ledger
```

This gives the most defensible split:

```text
theta        exact material volume,
phi          continuous capillary gauge,
projection   compatibility restoration, not physics,
capillarity  virtual work on the compatibility tangent space.
```

## 7. Verification Ladder

### V1. Fixed-stratum rank and conditioning

Manufactured circles/ellipses, translated across cell phases:

```text
rank J_A = # mixed cells,
condition estimate below fail threshold,
sign margin positive.
```

### V2. Small perturbation projection

For `theta_target=A_h(Gamma(phi_exact))`:

```text
||A_h(Gamma(phi_projected))-theta_target|| decreases quadratically under Newton,
case IDs unchanged,
Delta S_Pi recorded.
```

### V3. Nullspace selector

For constant-shift targets:

```text
with phi_pred=phi_exact, projection returns near phi_exact,
without predictor/metric, nonphysical nullspace corrections are detected.
```

### V4. Trust-region fail-close

Large perturbations should fail before case IDs change, not after producing
invalid geometry.

### V5. Capillary tangent consistency

Use the same `J_A` in projection and in `L_B(w_f)`.  Verify static/dynamic
Hodge gates.

### V6. GPU algebra gate

Matrix-free application of:

```text
J_A, J_A^T, W_eta^{-1}, S_A
```

must remain device-resident and scale with active mixed cells, not all cells.

## 8. Current Theory Status

The bridge is plausible but not ready for adoption.  The decisive next proof
is not another global volume test.  It is a fixed-stratum projection theorem:

```text
For regular Gamma(phi) with full-row-rank J_A and positive sign margins,
there exists a local constrained projection from nearby theta to a continuous
phi, and the projection can be made unique by the W_eta gauge metric.
```

The production route must then prove that the physical time step keeps
`theta^-` inside that local neighborhood, or explicitly fail close/topology
route when it does not.
