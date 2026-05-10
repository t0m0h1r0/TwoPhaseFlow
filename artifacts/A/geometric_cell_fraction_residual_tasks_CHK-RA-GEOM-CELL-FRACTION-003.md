# CHK-RA-GEOM-CELL-FRACTION-003

## Purpose

User request:

> Deepen the investigation.  Clarify remaining issues from physics and
> mathematics, generate as many solution ideas as possible, and verify them to
> clarify the direction.  Theory first; no tactical patching.

This artifact continues the non-adoption theory track.  It asks what remains
unresolved after defining geometric cell fractions and the single-owner rule.

## Executive Thesis

The remaining hard problem is not material volume conservation.  Geometric
cell fractions can own volume cleanly:

```text
V_h(F) = sum_C |C| F_C.
```

The hard problem is making **capillary-ready geometry** from that volume
state.  The physical surface tension law depends on surface energy and its
variation:

```text
E_sigma = sigma |Gamma|,
delta E_sigma = - integral_Gamma sigma kappa w_n dS.
```

Therefore a production-quality geometric cell-fraction theory must determine
not only cell volumes but also an interface complex `I_h` whose surface,
normal displacement, pressure-volume constraint, transport map, and Hodge
metric are mutually compatible.

In short:

```text
F_C determines mass.
F_C alone does not determine capillary physics.
```

## Probe 1: Same Fraction, Different Surface Energy

Consider a unit square cell centered at the origin.  Let a straight interface
cut pass through the center:

```text
n(theta) dot x = 0.
```

For every angle `theta`, the liquid area fraction is exactly:

```text
F_C = 1/2.
```

But the interface segment length is:

```text
L(theta) = 1 / max(|sin theta|, |cos theta|).
```

Numerical values:

```text
angle_deg  interface_length
0.0        1.000000000000
22.5       1.082392200292
30.0       1.154700538379
40.0       1.305407289332
45.0       1.414213562373
60.0       1.154700538379
90.0       1.000000000000
```

Thus all cuts have the same `F_C=0.5`, but their surface energies differ by up
to `sqrt(2)`.  This verifies:

```text
F_C alone is not a sufficient state for capillary surface energy.
```

Any theory that defines `E_sigma` as a function of `F_C` alone must either:

1. add an implicit reconstruction rule;
2. add additional moments/gauge information;
3. accept a nonphysical/nonunique capillary force.

The third option is not admissible.

## Probe 2: Local Volume Exactness Does Not Imply Global Interface Continuity

Take two adjacent unit cells with the same fraction:

```text
F_left = F_right = 1/2.
```

Both cells can be locally reconstructed by a PLIC cut that matches volume:

```text
left cell:  vertical half cut,
right cell: horizontal half cut.
```

Each cell is locally valid and volume exact.  But the two interface segments
need not connect across the common face.  Therefore:

```text
cellwise volume-exact PLIC is not automatically an interface complex.
```

The reconstruction map must include a continuity/topology rule, a gauge
normal field with compatibility, or a fail-close criterion.

## Residual Tasks

### RT1. Under-determined surface geometry

`F_C` gives one scalar per cell.  A capillary-ready interface needs at least:

```text
normal orientation,
intercept,
connectivity/topology,
surface measure,
variation under transport.
```

In 2D, a straight cut has two local degrees of freedom: orientation and
intercept.  `F_C` fixes only the intercept once the orientation is known.

### RT2. Reconstruction integrability

A cellwise normal field is not automatically the normal of a continuous
interface.  It may have nonzero discrete curl, jumps, or incompatible
edge-intersections.  Capillary energy needs an interface, not isolated cuts.

### RT3. Variational capillary closure

Even if `I_h` is constructed, the capillary force must be:

```text
a_sigma = - M_f(F)^{-1} T_h(I_h)^* dS_h(I_h).
```

This requires an explicit transport linearization `T_h` that tells how face
velocity changes the interface geometry and cell fractions.

### RT4. Gauge compatibility

If `phi` is transported as a smooth predictor, it can disagree with `F_C` after
transport or retraction.  If `phi` is reconstructed only from `F_C`, curvature
may be noisy or under-resolved.  The theory must say which object wins and how
the loser is projected.

### RT5. High-order smooth operators vs discontinuous fractions

CCD/FCCD cannot be asked to differentiate discontinuous `F_C` as though it
were pressure or velocity.  Smooth derivatives belong to `phi`, pressure,
velocity, or field extensions.  Conservation belongs to finite-volume
geometry.

### RT6. Bounded conservative flux at useful order

Geometric swept-volume flux gives a clean conservation theorem, but high-order
accuracy and boundedness are often in tension.  The method must not repair
overshoots by clipping without a conservative ledger.

### RT7. Nonuniform and moving/fitted grids

`F_C` is tied to physical cell volumes.  Grid rebuild/remap must transfer
geometric volume exactly enough that the common-flux state does not receive a
hidden mass/momentum impulse.

### RT8. Periodic and wall topology

Periodic seams are quotient identifications, not extra faces.  Walls impose no
normal flux and, absent contact-line physics, should not gain new wall
contacts through reconstruction or gauge retraction.

### RT9. Static equilibrium and dynamic release must both survive

The same capillary construction must satisfy:

```text
static constant-curvature: Hodge residual approx 0,
nonconstant-curvature:    Hodge residual nonzero.
```

Any projection or smoothing that improves the first while killing the second
is not physical.

## Candidate Idea Set

### I1. F-only minimal-perimeter reconstruction

Define `I_h` as the minimum-perimeter interface among all geometries matching
`F_C`.

Pros:

- makes `E_sigma(F)` single-valued;
- has a variational flavor.

Cons:

- it erases history and velocity-driven shape information;
- it can collapse oscillatory/dynamic modes into artificial relaxation;
- it is a hidden surface-tension minimization step, not pure transport.

Verdict: reject as production dynamics.  Useful as a mathematical lower-bound
diagnostic only.

### I2. Cellwise PLIC with normals from `phi`

Use `phi` or `grad(phi)` for cell normals; choose intercepts so each cell
matches `F_C`.

Pros:

- locally volume exact;
- GPU-friendly;
- natural bridge from CLS.

Cons:

- continuity of adjacent segments is not guaranteed;
- capillary `S_h` may be noisy unless `phi` is compatible with `F_C`;
- normal errors directly affect surface energy.

Verdict: strong first primitive, but not sufficient alone.  Needs continuity,
gauge compatibility, and Hodge gates.

### I3. Coupled PLIC plus global edge-continuity correction

Start from PLIC normals, then adjust intercepts/normals to connect interface
segments across cell faces while preserving cell fractions.

Pros:

- directly attacks the interface-complex problem;
- can preserve local volumes.

Cons:

- constrained nonlinear problem;
- may be overdetermined for arbitrary `F_C`;
- GPU implementation is harder than cell-local PLIC.

Verdict: promising as a capillary-ready reconstruction route, but feasibility
and fail-close conditions must be characterized.

### I4. Moment-of-Fluid enrichment

Store `F_C` plus liquid centroid or first moments.

Pros:

- reduces reconstruction nonuniqueness;
- centroids provide orientation information independent of `phi`;
- better restart/remap invariants.

Cons:

- expands state and flux ledger;
- moments also require bounded conservative transport;
- capillary smoothness still not automatic.

Verdict: theoretically strong if `F_C + moments` is treated as the material
geometry state.  More invasive than a first bridge.

### I5. Explicit interface complex as primary geometry, `F_C` derived

Track vertices/segments/surface mesh `I_h` directly.  Compute `F_C=A_h(I_h)`
for density and conservation checks.

Pros:

- surface energy and topology are explicit;
- capillary variation is geometrically natural.

Cons:

- topology change and GPU data structures are difficult;
- conservative remap onto Eulerian cells becomes the main challenge;
- not a small extension of current CLS/FCCD architecture.

Verdict: mathematically clean reference, but likely too large for near-term
integration.

### I6. Dual state `F_C + phi`, hard-local compatibility projection

Transport `F_C` conservatively and transport `phi` as a smooth predictor.
After each step, reconstruct `I_h=R_h(F_C,phi)` and replace `phi` by a gauge
of that interface.

Pros:

- `F_C` owns mass;
- `phi` provides smooth normals/history;
- compatibility is local, not just global volume.

Cons:

- projection `R_h` is the central algorithm;
- if projection changes surface energy, that change must be accounted for;
- dynamic mode preservation must be tested.

Verdict: best bridge candidate for theory development.

### I7. Dual state with global-only volume correction

Transport `phi`; reconstruct `F_C`; apply one global shift/correction so
`sum |C|F_C` matches target.

Pros:

- easy;
- resembles current volume-first scalar offset.

Cons:

- only global conservation;
- local material volume can drift;
- cannot support common-flux mass/momentum rigorously.

Verdict: reject for geometric cell-fraction production.  It remains a bridge
for current CLS, not this theory.

### I8. Height-function capillary on geometric fractions

Use geometric fractions for volume and height functions for curvature.

Pros:

- established VOF path for curvature in favorable geometries;
- can be accurate for column-resolved interfaces.

Cons:

- orientation/column choice is delicate for closed shapes and topology;
- must still pair with the same pressure Hodge metric;
- not naturally compatible with arbitrary nonuniform/fitted grids.

Verdict: candidate for diagnostics or specialized curvature reconstruction,
not the base theory.

### I9. Variational reconstruction by minimizing gauge mismatch plus surface energy

Define `I_h` as the minimizer:

```text
min_I  alpha ||A_h(I)-F||^2 + beta dist(I,phi_pred)^2 + gamma S_h(I)
subject to A_h(I)=F if hard local volume is required.
```

Pros:

- explicitly balances volume, gauge, and surface regularity;
- gives a variational definition.

Cons:

- if `gamma` acts in physical time, it adds artificial capillary relaxation;
- constrained optimization is expensive;
- local minima and topology changes need fail-close semantics.

Verdict: useful as a projection theory, but only if the energy contribution is
classified as gauge projection work, not physical capillary work.

### I10. Discrete exterior calculus/cut-cell complex

Build a full cut-cell complex with subcell volumes, apertures, interface
facets, and incidence matrices.

Pros:

- unifies volume, surface, flux, and Hodge operators;
- best theoretical match to pressure/capillary compatibility.

Cons:

- large architecture shift;
- complex GPU kernels and memory layout;
- 3D would be significantly harder.

Verdict: strongest long-term mathematical structure.  Could be developed
incrementally by first defining 2D cut-cell complexes.

### I11. Phase-field-like regularized energy on `F_C`

Define a diffuse interfacial energy directly from `F_C`.

Pros:

- makes energy a function of the transported scalar;
- avoids explicit reconstruction.

Cons:

- changes the physical model from sharp-interface capillarity;
- introduces mobility/interface-width energetics;
- not the same Young--Laplace pressure-jump theory.

Verdict: reject for this project unless intentionally changing model class.

### I12. THINC-like algebraic reconstruction

Use a hyperbolic tangent profile per cell to represent fractions and normals.

Pros:

- conservative and GPU-friendly;
- closer to algebraic VOF.

Cons:

- still needs a sharp surface/volume variational interpretation;
- can become another diffuse-measure system if not tied to `I_h`.

Verdict: possible transport primitive, not a complete capillary theory.

## Verification Matrix for Ideas

| Idea | Volume exact | Surface unique | Interface continuous | Capillary variational | Common-flux ready | Verdict |
|---|---:|---:|---:|---:|---:|---|
| I1 F-only minimum perimeter | yes | yes by artificial rule | maybe | dangerous | partial | reject for dynamics |
| I2 PLIC + phi normals | yes | yes with phi | not guaranteed | not yet | yes for flux | bridge primitive |
| I3 PLIC + continuity correction | yes if feasible | yes | intended | possible | possible | promising, hard |
| I4 moments | yes | improved | not automatic | possible | harder | promising later |
| I5 explicit interface primary | yes via rasterization | yes | yes | strong | hard | clean reference |
| I6 dual F+phi local projection | yes | yes through R_h | needs proof | possible | strong | best bridge |
| I7 global correction | global only | no | no | weak | weak | reject |
| I8 height function | yes | orientation-dependent | local | specialized | partial | diagnostic/special |
| I9 variational projection | yes if constrained | yes | possible | projection-work issue | possible | theory tool |
| I10 cut-cell complex | yes | yes | yes | strong | strong | long-term target |
| I11 phase-field energy | yes-ish | diffuse | n/a | model change | possible | reject for sharp model |
| I12 THINC | yes-ish | implicit | not guaranteed | incomplete | possible | transport primitive |

## Direction Clarified

The theory should now split into two nested targets:

### Target A: Near-theory bridge

```text
dual state:       F_C + phi_pred
reconstruction:   PLIC/cut geometry using phi normals
hard constraint:  A_h(I_h)_C = F_C locally
gauge retraction: phi_new = signed_distance(I_h)
flux:             geometric swept-volume flux from I_h
```

This is the most useful route for further theoretical work because it
preserves the current level-set gauge intuition while making material volume
geometric and local.

Required proof obligations:

```text
A_h(R_h(F,phi)) = F,
interface continuity or declared defect measure,
bounded conservative geometric flux,
capillary Hodge gates on the same I_h,
no hidden surface-energy work in gauge retraction.
```

### Target B: Long-term complete theory

```text
cut-cell complex K_h:
  cell subvolumes,
  face apertures,
  interface facets,
  incidence matrices,
  pressure/capillary Hodge metrics.
```

Here `F_C` is just the cell-volume part of a richer geometric complex.  This
is the mathematically clean endpoint because surface energy, volume flux,
pressure projection, wall/periodic quotient, and capillary variation live in
one discrete complex.

## Remaining Adoption Blockers

Before adoption, the following must be resolved:

1. Define `R_h(F,phi)` so local volume exactness and interface continuity are
   both handled.
2. Define `S_h(I_h)` and `dS_h` with a stable Hodge pairing.
3. Define `T_h(I_h)` for geometric swept flux and virtual work.
4. Prove boundedness without clipping as a hidden fix.
5. Prove common-flux mass/momentum consistency with the same geometric flux.
6. Define nonuniform/periodic/wall quotient geometry.
7. Define gauge-retraction work accounting.
8. Define checkpoint state sufficient for restart equivalence.

The next useful theoretical step is therefore not YAML or implementation.  It
is a focused formulation of `R_h(F,phi)` and `T_h(I_h)` in 2D, followed by
manufactured tests for:

```text
half-cell nonuniqueness,
two-cell continuity,
exact translation,
static circle Hodge balance,
nonconstant-curvature release.
```
