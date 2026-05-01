# CHK-RA-GPU-UTIL-012 — No-slip wall phase invariant implementation

Date: 2026-05-01
Scope: `schedule=1` ch14 capillary wave, wall-attached interface, no-slip
contact topology

## Conclusion

The first implementation in this CHK attempted to freeze the full wall trace
`psi_w(s)`.  That is too strong for the smoothed conservative level-set field:
an interface that does not touch the wall may still approach arbitrarily close
to it, changing the smooth Heaviside tail at wall nodes.  Freezing the full
trace would therefore constrain near-wall approach and is not paper-faithful.

The adopted invariant is weaker and sharper:

```math
C(t)=C(0),\qquad \operatorname{sign}(\psi_w(s,t)-1/2)
  =\operatorname{sign}(\psi_w(s,0)-1/2)
```

on stationary no-slip walls, except at the pinned contact roots.  This fixes
the wall phase intervals and prevents creation of new wall contacts, while
allowing same-phase wall values to vary as an interior interface approaches
the wall.

Periodic boundaries are separate: when `bc_type != "wall"`, no wall phase
constraint is created.

## Theory correction

For pure material advection,

```math
\partial_t \psi + u\cdot\nabla\psi=0,\qquad u|_{\partial\Omega}=0.
```

This implies no wall material point switches phase.  For a sharp interface,
the contact roots and the phase intervals on the wall are invariant unless an
explicit slip/contact-line/contact-angle law is supplied.

However, in the CLS algorithm `psi` is also passed through reinitialization,
dynamic remapping, and mass correction.  These are artificial geometry
operations on a smoothed Heaviside profile.  They should not create or move
wall contacts, but they also should not freeze every smooth wall value.  A
nearby but non-contacting interface is allowed to change `psi_w` continuously
without changing its side relative to `1/2`.

Therefore the correct boundary condition for auxiliary geometry operations is
a topology/phase inequality plus exact pinned contact roots, not a full trace
Dirichlet clamp.

## Implementation

- `src/twophase/levelset/wall_contact.py`
  - `WallTrace` now stores the initial wall phase side
    `sign(psi_w - 1/2)` in physical tangent coordinates.
  - `impose_on_wall_trace(...)` projects only boundary nodes that would switch
    phase side; it uses the nearest representable admissible value around
    `1/2`, not an arbitrary macroscopic clamp.
  - Existing contact roots are still imposed exactly by the local two-node
    half-contour representation.
  - `constraint_mask(...)` excludes only contact-root boundary nodes from mass
    correction, not the whole wall trace and not the near-wall interior.
- `src/twophase/levelset/ridge_eikonal_reinitializer.py`
  - When explicit wall phase constraints are present, reinit mass correction
    uses the boundary-contact constraint only.
  - The legacy two-layer contact band remains for direct reinitializer usage
    without explicit `WallContactSet`, preserving prior tested behavior.
- `src/twophase/simulation/ns_grid_rebuild.py`
  - Dynamic remap applies the same contact-root mass-correction mask and then
    projects wall phase topology.

## Validation

Local unit test:

```text
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m pytest src/twophase/tests/test_ridge_eikonal.py -q
27 passed, 2 skipped
```

Remote targeted tests:

```text
make test PYTEST_ARGS="-k wall_phase -q"      -> 1 passed
make test PYTEST_ARGS="-k wall_trace -q"      -> 4 passed
make test PYTEST_ARGS="-k constraint_mask -q" -> 1 passed
```

Experiment `ch14_capillary_n32_t1`:

```text
completed t=1.0
side-wall crossing count max = 1
pinned branch drift = 0.0
```

Experiment `ch14_capillary_n32_t25`:

```text
BLOWUP at step=3801, t=22.4868
saved snapshots through t=22.00073458316183
side-wall crossing count max = 1
first extra crossing = None
pinned branch drift = 0.0
KE max = 1.4990478672195456e6
div_u_max max = 2.2365176005286003
volume drift max = 0.026057273736953625
kappa_max max = 5.0
```

Interpretation: the wall contact/topology issue is fixed without freezing
near-wall approach, but the long-time capillary-wave run still blows up.  The
remaining failure is therefore not wall-contact drift; it is a separate
capillary geometry / curvature / energy-stability problem, consistent with
`kappa_max` being capped throughout the run and the late advective limiter
collapse.

## A3 traceability

```text
Equation:
  Dpsi/Dt=0, u|wall=0, no explicit contact-line law

Sharp boundary invariant:
  fixed wall phase intervals and C(t)=C(0)

Discretization:
  initial wall phase side stored in physical tangent coordinates;
  exact contact roots represented by local half-contour nodes;
  auxiliary reinit/remap/mass correction projected only onto phase topology

Code:
  WallTrace.phase_side
  WallContactSet.impose_on_wall_trace
  WallContactSet.constraint_mask
  RidgeEikonalReinitializer.reinitialize
  rebuild_ns_grid
```

## SOLID audit

[SOLID-X] No violation.  Wall phase/contact responsibility remains isolated in
`src/twophase/levelset/wall_contact.py`; reinit and remap consume the geometry
constraint through existing injection points.  PPE/DC/capillary force modules
were not given wall-contact responsibilities.
