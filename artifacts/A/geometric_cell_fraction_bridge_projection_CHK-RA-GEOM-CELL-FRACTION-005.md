# CHK-RA-GEOM-CELL-FRACTION-005

## Purpose

User request:

> Push further toward solving the remaining issues.

This artifact advances the previous residual-task analysis by proposing a
concrete 2D bridge theory for the main blocker:

```text
How can theta_C be locally volume-exact while Gamma_h remains a continuous,
capillary-ready interface?
```

Adoption remains undecided.  This is a mathematical candidate and its proof
obligations.

## 1. Refined Diagnosis

The prior half-cell probe showed:

```text
theta_C alone fixes material volume, not surface energy.
```

Independent cellwise PLIC adds a normal and intercept per cell, so it can match
`theta_C`, but it does not automatically make a continuous `Gamma_h`.

The next candidate must therefore satisfy three conditions at once:

```text
local volume exactness:        A_h(Gamma_h)_C = theta_C,
global interface continuity:   Gamma_h is one trace, not unrelated cuts,
capillary variational closure: S_h(Gamma_h), dS_h, and T_h share one geometry.
```

## 2. Proposed Bridge: Theta-Constrained P1 Trace Bundle

Represent the geometric state as a compatible pair:

```text
B_h = { (theta, phi) :
        theta_C = A_h(Gamma(phi))_C for all active mixed cells C,
        sign/topology inequalities hold in full/empty cells }.
```

Here:

```text
theta_C              hard material volume coordinate,
phi                  continuous P1/Q1 level-set gauge,
Gamma(phi)           marching-squares trace of phi=0,
A_h(Gamma(phi))_C    cellwise liquid area fraction of that trace.
```

This is not F-only geometry.  The physical state is a bundle:

```text
material coordinate: theta,
geometry gauge:      phi,
compatibility:       theta = A_h(Gamma(phi)).
```

The reconstructed interface is simply:

```text
Gamma_h = Gamma(phi).
```

Because `phi` is continuous over nodes, `Gamma_h` is a continuous P1 trace on a
fixed regular stratum.  Because `theta=A_h(Gamma(phi))`, the material volume
and the sharp trace volume are identical:

```text
sum_C |C| theta_C = |Omega_l(Gamma_h)|.
```

## 3. Retraction / Compatibility Projection

After conservative phase transport, the solver may have:

```text
theta^-  conservative transported cell fractions,
phi^-    transported or predicted gauge.
```

Project back to the compatibility bundle by solving:

```text
minimize_phi
    1/2 ||phi - phi^-||_W^2 + eta/2 ||L phi - L phi^-||^2
subject to
    A_h(Gamma(phi))_C = theta^-_C        for mixed cells,
    full/empty sign inequalities,
    periodic/wall topology constraints.
```

Then:

```text
theta^+ = theta^-,
phi^+   = projected gauge,
Gamma^+ = Gamma(phi^+).
```

This makes reinitialization a gauge projection only.  It does not alter the
material volume coordinate.

### Why this is different from independent PLIC

PLIC with per-cell normals:

```text
cell C owns its own line segment.
```

Theta-constrained P1 trace:

```text
all cells share one nodal phi field, hence one continuous trace.
```

The price is that exact local constraints may become infeasible near topology
events or incompatible transported `theta`.  In those cases the method should
fail close or enter an explicit topology/remeshing route.

## 4. Local Solvability Probe

Let

```text
J_A(phi) = d A_h(Gamma(phi)) / d phi_nodes
```

restricted to mixed cells.  If `J_A` has full row rank on a fixed stratum, the
implicit function theorem gives local solvability of the compatibility
constraints for nearby `theta`.

A manufactured ellipse probe computed finite-difference rows of `J_A` for
mixed cells on uniform grids:

```text
N  mixed_constraints  nodal_unknowns  rank
8         16                81          16
12        24               169          24
16        32               289          32
24        48               625          48
32        64              1089          64
```

The row rank was full in all tested cases.  This supports the bridge theorem:

```text
For regular nondegenerate traces, a nearby theta field can be represented by a
continuous P1 gauge phi while preserving local cell fractions.
```

However, the smallest singular values were small in these finite-difference
probes.  This is a warning, not a contradiction:

- near vertex crossings,
- near topology changes,
- with very thin slivers,
- or with incompatible transported fractions,

the projection can become ill-conditioned.  Those cases require stratum gates,
preconditioning, and fail-close semantics.

## 5. Capillary Virtual Work on the Bundle

Surface energy is defined from the trace:

```text
E_sigma(theta,phi) = sigma S_h(Gamma(phi)),
```

with compatibility `theta=A_h(Gamma(phi))`.

A virtual face velocity `w_f` changes material volume by geometric transport:

```text
delta theta = T_theta(Gamma_h) w_f.
```

It also has a natural level-set predictor variation:

```text
delta phi_pred = T_phi(phi) w_f
               = - w_f · grad_h phi             (schematic)
```

To stay on the compatibility bundle, choose the lifted gauge variation:

```text
L_B(w_f)
= argmin_delta_phi ||delta_phi - delta_phi_pred||_W^2
  subject to J_A(phi) delta_phi = T_theta(Gamma_h) w_f.
```

Then capillary virtual work is:

```text
r_sigma(w_f)
= - sigma dS_h(phi)[ L_B(w_f) ].
```

The face acceleration is the Riesz representative:

```text
a_sigma = M_f(theta)^(-1) r_sigma.
```

This is the core bridge idea.  It avoids both bad extremes:

```text
theta-only capillarity: impossible because surface energy is underdetermined.
phi-only capillarity:   can break material-volume conservation.
```

The bundle lift uses `theta` for material volume and `phi` for surface
geometry, tied by the exact local constraint.

## 6. Discrete Work Accounting

The finite step has two different contributions:

```text
physical capillary work:
  computed from r_sigma(w_f) at a compatible state.

gauge projection work:
  Delta S_Pi = S_h(Gamma(phi^+)) - S_h(Gamma(phi^-_transported)).
```

`Delta S_Pi` is not physical capillary work.  It must be recorded separately,
just as previous reinit-aware Hodge theory demanded.  If projection work is
large, the time step or reconstruction route is not resolving the geometry.

## 7. Transport Operator Candidate

For small bridge development, use the same trace `Gamma(phi)` to define a
geometric swept-volume phase flux:

```text
Phi_l,f = swept liquid volume through face f per unit time.
```

Then:

```text
theta_C^{n+1} =
theta_C^n - (Delta t/|C|) sum_{f in boundary C} s_{C,f} Phi_l,f.
```

Internal faces cancel by construction.  Boundedness requires the swept regions
to be realizable subsets of donor geometry; if this cannot be proven for a
higher-order version, the bridge should start with a first-order geometric
translation gate and then add order only with a boundedness proof.

## 8. Relation to Existing P1 Closed-Interface Theory

This bridge is attractive because the existing theory already has P1
closed-interface ingredients:

```text
V_h^Gamma(phi)        marching-squares/P1 volume,
S_h(Gamma(phi))       P1 surface length,
dV_h/dphi, dS_h/dphi  fixed-stratum derivatives.
```

The new ingredient is not a new surface formula.  It is the local compatibility
constraint:

```text
A_h(Gamma(phi))_C = theta_C
```

and the bundle lift `L_B` that maps face velocities into compatible `phi`
variations.

## 9. Negative Knowledge

Do not treat the following as solutions:

- independent cellwise PLIC without continuity or defect accounting;
- theta-only surface energy;
- global volume correction in place of local compatibility;
- gauge projection that changes `theta_C`;
- capillary force from `phi` while density/momentum use incompatible `theta`;
- smoothing the normal field until static residual improves while dynamic
  capillary release disappears;
- clipping overshoots without a geometric flux proof.

## 10. Verification Gates for This Bridge

### B1. Compatibility rank gate

For regular traces:

```text
rank J_A = number of active mixed-cell constraints.
```

### B2. Projection manufactured gate

Perturb a compatible `theta` by a known small normal displacement and solve the
projection.  Verify:

```text
A_h(Gamma(phi^+)) = theta^-
||phi^+ - phi_exact|| = expected order.
```

### B3. Continuity gate

Verify that adjacent mixed-cell segments share the same edge crossing induced
by the continuous `phi^+`.

### B4. Half-cell nonuniqueness gate

Confirm that the gauge predictor selects the correct angle `beta`; without
`phi_pred`, the problem is underdetermined.

### B5. Geometric flux gate

Exact translation over a fraction of a cell:

```text
theta^{n+1} from swept flux == A_h(Gamma(translated phi)).
```

### B6. Bundle capillary Hodge gates

Using `L_B`:

```text
constant-curvature static trace: Hodge residual approx 0,
nonconstant-curvature trace:    Hodge residual nonzero.
```

### B7. Projection-work gate

Record:

```text
Delta S_Pi,
Delta V_theta,
||A_h(Gamma(phi^+))-theta^-||.
```

Require `Delta V_theta=0` and local compatibility residual near roundoff.
Large `Delta S_Pi` is not hidden as physical work.

## 11. Direction After This Step

The best next theory-development direction is no longer generic
`PLIC + phi`.  It is:

```text
theta-constrained continuous P1 trace projection,
with capillary work defined by a bundle lift.
```

This gives a concrete path to solve the earlier residual:

```text
theta_C supplies local material volume,
phi supplies continuous capillary geometry,
compatibility constraints prevent them from becoming two independent phases.
```

The remaining hard work is to formulate and test:

```text
J_A construction,
weighted compatibility projection,
bundle lift L_B,
geometric swept-volume flux,
static/dynamic Hodge gates.
```
