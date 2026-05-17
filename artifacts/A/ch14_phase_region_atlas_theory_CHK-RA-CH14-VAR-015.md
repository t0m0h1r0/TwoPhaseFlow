# CHK-RA-CH14-VAR-015 — PhaseRegion and multi-component InterfaceAtlas theory

## Claim

The graph and closed-radial modules are valid single-component chart gates, but
they are not the final owner abstraction.  To include capillary waves, closed
droplets, rising bubbles, and a top gas layer in one theory, the owned physical
state should be the phase region:

```text
Omega_g(t) = gas-occupied region
Gamma(t)  = boundary Omega_g(t)
q_C       = |Omega_g ∩ C| / |C|
```

Thus the current origin-reset route should be lifted from:

```text
Gamma_h owner -> q_phys = Q_h(Gamma_h) -> r
```

to:

```text
Omega_h owner -> InterfaceAtlas(boundary Omega_h)
              -> q_phys = Q_h(Omega_h)
              -> r = q_T - q_phys
```

`phi` remains a chart/gauge.  `q` remains a finite-volume measure.  The charts
are local boundary representations of one `Omega_h`, not independent theories.

## Why This Is Needed

A rising bubble with a top gas layer is not representable by a single graph or
a single closed radial chart:

```text
Omega_g = Omega_bubble ∪ Omega_layer
Gamma   = Gamma_bubble ∪ Gamma_layer
```

The bubble boundary is closed.  The top layer boundary is open or boundary
attached.  Forcing both into one graph or one radial parameterization would
make the chart carry topology it does not own.

## Revised Continuous Principle

Use the finite-perimeter/BV viewpoint at the discrete-design level:

```text
E[Omega_g] = sigma Perimeter(Omega_g)
Gamma      = reduced boundary of Omega_g
q          = cell measure of Omega_g
```

For smooth charts this reduces to the earlier graph and closed-curve
formulas:

```text
capillary wave: Omega_g = { y > eta(x) }
closed droplet: Omega_g = inside X(theta)
multi-component: Omega_g = union_i Omega_i
```

The dynamics still use the same volume constraints, incompressibility, and
pressure reaction.  Only the boundary chart changes.

## Discrete Objects

The future abstraction should be:

```text
PhaseRegion
  owns:
    Omega_h identity and phase ownership
  provides:
    q_phys = cell_volume(Omega_h)
    atlas  = boundary_charts(Omega_h)
    E_h    = sigma * sum_component perimeter(component)
    dE_h   = first variation through atlas charts
    C_h    = total/component volume constraints
```

and:

```text
InterfaceAtlas
  components:
    chart_type
    topology
    boundary_attachment
    orientation
    phase_inside/phase_above
    q_component policy
```

Example for rising bubble plus top gas layer:

```text
component 1:
  chart_type: ClosedCurveChart
  topology: closed
  role: rising bubble
  phase_inside: gas

component 2:
  chart_type: OpenCurveChart or GraphChart
  topology: boundary_attached
  role: top gas layer
  phase_above: gas
  boundary_attachment: top/side/wall/periodic
```

## Equation -> Discretization -> Code Contract

| Theory object | Discrete object | Current/Future code boundary |
|---|---|---|
| `Omega_h` | phase-region owner | future `PhaseRegion` object |
| `Gamma_h=∂Omega_h` | atlas of boundary charts | future `InterfaceAtlas`; current graph/closed helpers are one-component charts |
| `q_phys=Q_h(Omega_h)` | cell volume of phase region | current `graph_q_from_eta`, `closed_radial_q_from_chart`; future atlas `Q_h` |
| `E_h=sigma Perimeter(Omega_h)` | sum of component lengths | current graph/closed energy helpers; future atlas sum |
| `dE_h` | chart first variations | current `graph_segment_energy_gradient`, `closed_polygon_geometry.surface_gradient` |
| constraints `C_h` | total gas volume first, component volumes only when physically justified | future phase-region constraint policy |
| residual `r` | non-atlas / non-physical q component | current `ProjectionResult.residual`; remains diagnostic |
| force map | `-T_h^* dE_h` in face cochain space | future force-coupling gate only after atlas contract |

## Constraint Policy

The first exact constraint should be total phase volume:

```text
sum_C q_phys[C] |C| = sum_C q_T[C] |C|
```

Component volumes are exact only when the physical model and transport step
identify persistent material components.  If the top gas layer connects through
a periodic boundary or touches a wall, it is not the same constraint as a
closed bubble volume.  The atlas must therefore store component topology and
attachment before deciding constraints.

All-cell `q_T` exactness remains a falsification test, not the default
geometric constraint.

## Projection Generalization

Previous projection:

```text
q_T -> Gamma* -> q_phys -> r
```

becomes:

```text
q_T -> Omega* with InterfaceAtlas -> q_phys -> r
```

For the existing graph and closed radial oracles, `Omega*` has one component
and one chart, so the old implementation is still a valid restricted case.

For multi-component cases, F0 should be component-local and vectorized:

```text
graph/open component: column or boundary-attached moments
closed component: radial/angular moments
atlas: concatenate component reports and enforce shared total phase volume
```

F1 may solve a small coupled KKT system over low chart modes and exact volume
constraints.  Full nonlinear optimization remains oracle/fail-close only.

## Force-Coupling Consequence

The next force-coupling probe must not use a chart component directly as the
physical state.  It must consume:

```text
PhaseRegion/Omega_h
InterfaceAtlas(boundary Omega_h)
q_phys
r
```

and only then test whether:

```text
dE_h[T_h u_f] + <surface_force, u_f>_M = 0
dC_h[T_h u_f] - <volume_reaction, u_f>_M = 0
```

hold in the same face-cochain metric.  Residual `r` is not a surface-force
source.  If the atlas cannot define topology, orientation, boundary
attachment, and volume constraints, force admission must remain closed.

## Relationship To Existing Work

- `WIKI-T-174` chose between interface-configuration and cell-volume
  ownership.  This checkpoint lifts interface ownership one level higher to
  phase-region ownership.
- `WIKI-T-175`, `WIKI-L-048`, `WIKI-E-067`, and `WIKI-L-049` remain valid as
  single-component atlas chart gates.
- `WIKI-E-068` remains valid as a runtime-facing snapshot probe, but its
  `force_admissible=0` should now be read as: no force until a
  `PhaseRegion/InterfaceAtlas` contract exists.

## Forbidden Shortcuts

- Do not make graph, closed curve, open layer, or implicit level set the global
  owner by itself.
- Do not treat topological branching as a special closed-droplet condition.
- Do not force all components through one radial or graph chart.
- Do not convert residual `r` into curvature, pressure jump, or damping.
- Do not use smoothing, curvature caps, CFL retuning, rebuild skipping,
  FD/WENO/PPE fallback, or hidden CPU fallback.

## Next Gate

Before force-coupling implementation, add an atlas design or smoke oracle that
can represent:

```text
Omega_g = Omega_closed_bubble ∪ Omega_top_layer
```

and report component topology, boundary attachment, orientation, total phase
volume, optional component volume, perimeter sum, and residual split.  T/8 and
production force coupling remain inadmissible until that gate exists.
