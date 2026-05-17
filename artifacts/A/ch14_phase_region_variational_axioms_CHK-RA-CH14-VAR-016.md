# CHK-RA-CH14-VAR-016 — PhaseRegion variational axioms after theory reset

## Purpose

Re-check the `PhaseRegion` direction from first principles before any
multi-component atlas or force-coupling implementation.

The important correction is:

```text
"Omega_h owner" is not permission to own an arbitrary cell array q.
```

The discrete owner must be a finite-dimensional phase-region state whose
boundary atlas, volume measure, topology, and transport endpoint are declared
together.

## Continuum Starting Point

The physical state is a gas phase region:

```text
Omega_g(t) subset D
Gamma(t) = partial Omega_g(t)
E[Omega_g] = sigma Perimeter(Omega_g; D)
q_C = |Omega_g ∩ C| / |C|
```

For smooth motion with normal velocity `u · n`,

```text
d/dt |Omega_g| = integral_Gamma u · n dS
d/dt E[Omega_g] = sigma integral_Gamma kappa u · n dS
```

Pressure is the reaction enforcing incompressibility and admitted volume
constraints.  Surface tension is the first variation of perimeter.  This
statement is independent of whether `Gamma` is one graph, one closed curve, or
multiple components.

## Discrete Axioms

### Axiom 1: Region ownership

The owned object is:

```text
R_h = (components, charts, orientation, phase labels, constraints, metric epoch)
```

not `phi` and not a bare `q`.

`Omega_h` is represented by this finite object.  Each component supplies a
boundary chart, but no single chart is the global owner.

### Axiom 2: Measurement is derived

The physical cell measure is:

```text
q_phys = Q_h(R_h)
```

`q_phys` is derived from the region state.  If a transport step produces a
tentative cell field `q_T`, it is evidence to be admitted:

```text
q_T -> R_h* -> q_phys -> r = q_T - q_phys
```

`r` is a diagnostic residual.  It is not curvature, pressure jump, damping, or
hidden force.

### Axiom 3: Energy is perimeter of the same region

The discrete surface energy must be:

```text
E_h(R_h) = sigma sum_{component a} Perimeter_h(component a)
```

Every chart contribution must carry orientation and endpoint/boundary
attachment so that perimeter and volume variations refer to the same region.

### Axiom 4: Constraints are declared, not inferred

The minimal exact constraint is total phase volume:

```text
C_total(R_h) = sum_C Q_h(R_h)_C |C|
```

Component volume constraints are exact only for persistent material
components.  They are not automatically exact for a boundary-attached layer,
a periodic reservoir connection, or a component that undergoes a topology
event.  Component labels therefore require a topology ledger.

### Axiom 5: Force is the adjoint of the production endpoint

Force admission requires a declared tangent map:

```text
T_h(R_h): U_f -> T_{R_h} Region
```

and the work identities:

```text
<s, u>_M    = -dE_h(R_h)[T_h(R_h) u]
<B_i, u>_M =  dC_i,h(R_h)[T_h(R_h) u]
```

No chart is force-admissible until `T_h`, `M`, pressure action, boundary
conditions, and constraint rows are all in the same face-cochain complex.

### Axiom 6: Topology changes are theorem changes

Within one VJP/JVP or force probe, component topology and chart strata are
fixed.  A merge, split, wall contact, periodic reconnection, or layer/bubble
identity swap is a discrete event:

```text
R_h^- -> event ledger -> R_h^+
```

The ledger must report changes in `Q_h`, `E_h`, constraints, and component
labels.  It must not be hidden inside smoothing, reinitialization, or q/phi
rebuild.

## Consequences

### Graph and closed curves remain valid

The earlier graph and closed radial work is not wrong.  It is the
single-component smooth-chart case:

```text
GraphChart        = one atlas component of Omega_h
ClosedCurveChart  = one atlas component of Omega_h
```

Their oracles validated `Q_h`, `E_h`, `dE_h`, residual split, and vectorized
chart parity for restricted states.

### Bare q-primary is still incomplete

A cell field `q` can represent many topologies, but it does not by itself
define a smooth perimeter variation.  If `q` is selected as the numerical
owner, the scheme must define:

```text
E_h[q], dE_h[q], T_h(q), M(q), C_h(q)
```

in q-space.  Reconstructing a pretty `phi` or local PLIC fragments and
borrowing curvature is not a q-primary theory.

### Phi is an atlas gauge

An implicit level-set chart may be useful for topology and local geometry, but
it is still a gauge unless the scheme defines `R_h` as a finite-dimensional
region state with its own perimeter variation and endpoint map.  Smoothness of
`phi` is not the acceptance condition; the acceptance condition is variational
closure of `R_h`.

## Multi-Component Example

For rising bubble plus top gas layer:

```text
Omega_g = Omega_bubble union Omega_layer
Gamma   = Gamma_bubble union Gamma_layer
```

An admissible atlas state must say:

| Component | Topology | Attachment | Orientation | Constraint |
|---|---|---|---|---|
| bubble | closed | none | gas inside | component volume may be exact |
| top layer | open/graph-like | top wall or periodic boundary | gas above | only total gas volume exact unless model declares layer material volume |

Perimeter is the sum of both component perimeters.  Pressure reaction and
surface force are built from the same `T_h(R_h)` and face metric, not from
separate component-specific hacks.

## Required Smoke Oracle Before Force Coupling

Before any production force path, implement a small atlas oracle with no time
advance:

```text
R_h = closed bubble + top layer
```

It must report:

- component topology and attachment;
- orientation and phase ownership;
- total gas volume and optional component volumes;
- perimeter per component and total perimeter;
- `q_phys=Q_h(R_h)`;
- projection/admission residual `r` for synthetic `q_T`;
- finite-difference checks of `dE_h` and `dC_h` per component;
- failure if component labels or topology are ambiguous.

This oracle is a theory gate, not a visual demo.

## Force Gate After Atlas Oracle

Only after the atlas oracle passes may a force-coupling probe attempt:

```text
dE_h[T_h u_f] + <s,u_f>_M = 0
dC_h[T_h u_f] - <B,u_f>_M = 0
```

The probe must include graph-like, closed, and mixed-component structured
velocities.  It must fail closed if:

- `r` is used as force;
- `q_T` and `q_phys` are silently swapped;
- pressure action and force metric are not adjoint;
- topology changes during derivative probes;
- CPU diagnostic geometry is used as hidden GPU runtime geometry.

## Decision

The next implementation should not be force coupling.  It should be an
`InterfaceAtlas` smoke oracle for `closed bubble + top layer`, still with no
T/8 and no production runtime force.  This is the smallest test that can
distinguish true `PhaseRegion` ownership from merely renaming the old
single-chart route.
