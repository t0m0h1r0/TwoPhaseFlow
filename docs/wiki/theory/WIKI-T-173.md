---
ref_id: WIKI-T-173
title: "Capillary-Wave Surface-Tension Literature Survey and AO-Fast Route"
domain: theory
status: ACTIVE
tags: [capillary_wave, surface_tension, balanced_force, projection, boundary_hodge, moving_grid, ao_fast]
sources:
  - url: https://doi.org/10.1016/0021-9991(92)90240-Y
    description: "Brackbill, Kothe, and Zemach (1992), continuum surface force"
  - url: https://doi.org/10.1016/j.jcp.2005.08.004
    description: "Francois et al. (2006), balanced-force surface tension"
  - url: https://doi.org/10.1016/j.jcp.2009.04.042
    description: "Popinet (2009), VOF height functions and capillary waves"
  - url: https://doi.org/10.1006/jcph.1999.6236
    description: "Fedkiw et al. (1999), Ghost Fluid Method"
  - url: https://doi.org/10.1006/jcph.2000.6537
    description: "Sussman and Puckett (2000), CLSVOF"
  - url: https://www.ams.org/mcom/1968-22-104/S0025-5718-1968-0242392-2/
    description: "Chorin (1968), projection method"
  - url: https://www.math.utah.edu/~choheneg/brown-cortez-minion-jcp2000.pdf
    description: "Brown, Cortez, and Minion (2001), projection-method boundary accuracy"
  - url: https://doi.org/10.1016/j.cma.2005.10.010
    description: "Guermond, Minev, and Shen (2006), projection-method overview"
  - url: https://doi.org/10.2514/3.61273
    description: "Thomas and Lombard (1979), geometric conservation law"
  - url: https://doi.org/10.1016/0045-7825(96)01028-6
    description: "Lesoinne and Farhat (1996), deforming-mesh GCL"
  - url: https://doi.org/10.1016/S0045-7825(01)00287-X
    description: "Baensch (2001), finite elements for free capillary surfaces"
  - url: https://doi.org/10.1006/jcph.2002.7165
    description: "Jamet, Torres, and Brackbill (2002), energy conservation and parasitic currents"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-077]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-168]]"
  - "[[WIKI-T-172]]"
consumers:
  - domain: code
    usage: "Use before changing active-geometry capillary, pressure projection, boundary face state, or moving-grid remap"
  - domain: experiment
    usage: "Use to design capillary-wave acceptance gates and reject shortcut stabilizations"
  - domain: paper
    usage: "Use for the final AO-Fast capillary-theory narrative"
compiled_by: ResearchArchitect
compiled_at: 2026-05-14
---

# Capillary-Wave Surface-Tension Literature Survey and AO-Fast Route

## Knowledge Card

The capillary-wave lesson from the literature is not "add a sharper curvature
force".  It is operator consistency: surface energy variation, pressure
reaction, divergence, wall boundary conditions, and moving-grid metrics must be
represented in one compatible discrete complex.  A method that survives by
smoothing curvature, adding offsets, changing physical CFLs, disabling
interface-fitted grids, or hiding a fallback violates the survey conclusion.

For the present AO-Fast route, the best-supported approach is:

```text
geometric surface energy S(q)
  -> face virtual-work cochain c_sigma
  -> pressure-reaction split in the active pressure metric
  -> boundary-constrained face state F_w = ker C_w
  -> PPE/corrector using the same D_h, G_A, P_w, and moving-grid metric epoch.
```

## Survey Synthesis

### CSF and Balanced Force

Brackbill--Kothe--Zemach introduced the continuum surface force model: surface
tension is represented as a volumetric force concentrated in an interface band.
This is flexible, but it exposes the central failure mode: if the discrete
surface force and pressure gradient are not colocated and paired, parasitic
currents appear.

Francois et al. and Popinet show the durable cure: use a balanced-force
discretization, accurate geometric curvature, and the same discrete operator
pair for surface tension and pressure.  Popinet's capillary-wave evidence is
especially relevant: the benchmark is sensitive to operator pairing, not only
to curvature magnitude.

### Sharp Interface and Pressure Jump

Ghost Fluid and CLSVOF methods support the sharp-interface direction: pressure
jumps are legitimate physical objects, and volume conservation can be separated
from smooth distance/normal information.  However, the jump must be coupled to
the pressure projection operator itself.  A sharp pressure jump evaluated in a
different face space from the PPE/corrector is only a diagnostic representation,
not a balanced numerical law.

### Projection and Boundary Conditions

Projection-method literature identifies boundary treatment as a first-order
source of splitting error.  Chorin's projection idea becomes accurate only when
the pressure correction, velocity correction, and boundary conditions are
consistent.  Brown--Cortez--Minion and Guermond--Minev--Shen reinforce that
post-hoc boundary clamping is not equivalent to solving in the correct
boundary-constrained velocity space.

For AO-Fast, this means a saved projection-native face cochain and the
published nodal velocity must live in the same wall state.  If nodal velocity
is no-slip but stored faces are only no-penetration, the next step starts from
a mixed boundary space even when `div_u` is small.

### Moving and Nonuniform Grids

The geometric conservation law literature says moving-grid metric epochs are
part of the equation.  Face cochains cannot be rebuilt from nodal interpolation
without changing the discrete Hodge metric.  On interface-following nonuniform
grids, projected face states must be transported as face objects and then
reprojected in the new metric epoch.

### Energy-Stable Variational Methods

Variational capillary-surface methods identify the right acceptance metric:
surface energy, kinetic energy, volume, divergence, and wall trace must close
together.  Reducing one diagnostic while increasing another is not a valid
capillary-wave fix.

## Selected AO-Fast Approach

1. Keep `q` as the owned geometric interface variable.
2. Use the YAML-selected capillary endpoint: graph gauges use graph surface
   energy, not generic P1 cut-cell energy.
3. Convert capillary variation exactly once into projection-face acceleration
   cochains.
4. Store pressure history in a smooth coordinate; decode jumps only at the
   current face law.
5. Transport projected face cochains across grid rebuilds and reproject them
   in the new metric epoch.
6. For wall-bounded runs, require the saved face state to satisfy the same
   no-slip wall state as the nodal velocity.
7. Treat DC/PCG iteration limits as caps; convergence is the acceptance rule.
8. Keep GPU execution matrix-free and backend-native; scalar D2H transfers are
   batched diagnostics or fail-close gates only.

## Rejected Routes

- micro-offsets to avoid interface-grid coincidences;
- curvature smoothing or damping as the primary capillary-wave stabilizer;
- disabling nonuniform grids or interface-following rebuilds;
- discarding projected face cochains after rebuild;
- treating DC iteration count as convergence;
- post-clamping nodal velocity while publishing an unconstrained face state;
- dense CPU KKT as a production substitute for the matrix-free face complex;
- hidden fallback from a failed DC/PCG/GPU route.

## Acceptance Gates

Before claiming a capillary-wave repair, record:

- `compat_linf` and `q-Q_h(phi)`;
- `projected_face_linf`;
- `face_hodge_pre` and `face_hodge_post`;
- wall-trace residual of the stored face state;
- `div_u` from the same face state used for transport;
- kinetic plus surface energy trend;
- phase/mode amplitude against the rigid-wall capillary-wave reference;
- GPU route evidence that nonuniform metrics and rebuilds stayed enabled.
