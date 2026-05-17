# CHK-RA-CH14-VAR-002 — Ch14 variational state-ownership rebuild and capillary-wave oracle plan

## Claim

The next admissible Ch14 capillary route should own a discrete material
interface configuration `Gamma_h` first, derive `q=Q_h(Gamma_h)` second, and
verify the capillary force through a small graph-chart oracle before any T/8
runtime experiment.

This is not a repair of the screened graph-q projection path.  The preserved
baseline PASS and screened graph-q FAIL are carried forward as evidence in the
hypothesis table below.

## Preserved Evidence

| Evidence | Observation | Consequence for this session |
|---|---|---|
| Baseline GPU capillary-wave probe | `make cycle EXP=experiment/ch14/diagnose_capillary_direction.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 2 --print-every 1 --plot-pdf experiment/ch14/results/capillary_direction_baseline.pdf'` reached step 2 and produced a PDF. Sampled `raw_accel_cos` changed from `2.753533350606e+01` to `-2.808607486070e+01`; `balanced_accel_cos` had opposite sign; `compat_linf=0`. | Keep as short runtime control only.  Do not infer that pre-rebuild transported `q` is generally preserved by a smooth graph/phi chart. |
| Screened graph-q runtime probe | Same diagnostic with `--screened-q-phi-rebuild` failed before step 1 admission: `final residual 1.630e-08 exceeds tolerance 1.000e-11`. | Treat as fail-closed negative knowledge against residual-projection runtime wiring.  Do not weaken tolerance. |
| Exploratory loose-predictor probes | Topology movement, redundant periodic quotient constraints, and line-search failure appeared beyond the strict fail-close. | The root question is state ownership and chart compatibility, not merely a local seam or residual tuning bug. |

## Continuous Problem

The physical unknown is the material interface `Gamma(t)` between liquid and
gas.  Surface tension is the first variation of the surface energy

```text
E[Gamma] = sigma |Gamma|.
```

Admissible motion is constrained by:

- material transport of `Gamma(t)` by the interface-normal fluid velocity;
- phase volume conservation for each connected material component;
- incompressibility, `div u = 0`;
- pressure as a Lagrange multiplier/reaction that enforces the incompressible
  and volume constraints in the velocity/face-cochain space.

`phi` is a gauge or chart for geometry.  `q` is a finite-volume measurement on
cells.  Neither is automatically the physical owner.

## Two Equal Candidate Formulations

| Formulation | Owned state | Surface energy | Conserved object | Main risk | Required first oracle |
|---|---|---|---|---|---|
| Interface-configuration primary | `Gamma_h` in a chart, such as graph `eta(x)` or closed curve `X(theta)` | `E_h[Gamma_h]` is the discrete interface length/surface area | volume is enforced as a constraint on `Gamma_h`; `q=Q_h(Gamma_h)` is diagnostic/derived | transport and projection must move the material interface, not just a gauge rebuild | graph chart: `eta -> Q_h(eta), E[eta], delta E/delta eta`; closed chart: `X(theta) -> Q_h(X), E[X], area` |
| Cell-volume primary | cell volume measure `q` | must define a genuine `E_h[q]` and a q-space variation | `q` is conserved by construction | borrowing curvature from rebuilt `phi` mixes state spaces and can overconstrain smooth charts | q-space perimeter/variation oracle; no phi curvature shortcut |

Both are legitimate research paths.  This session chooses
interface-configuration primary first because it directly makes capillary waves
and closed droplets two charts of one variational principle:

```text
Graph chart:        Gamma_h = {(x, eta(x))}
Closed-curve chart: Gamma_h = {X(theta)}
Same principle:     force = negative variation of sigma |Gamma_h|
Same constraint:    volume/area preservation handled as reaction constraints
Derived measure:    q = Q_h(Gamma_h)
```

This choice rejects theories whose body only works "for closed surfaces" or
"when screened Riesz exists."  Those are implementation states, not the
continuous capillary principle.

## Graph-Chart Oracle

For a periodic capillary wave over `0 <= x < L`, liquid below the graph,

```text
eta(x) = eta0 + A cos(k x),      k = 2 pi m / L.
```

The graph energy is

```text
E[eta] = sigma integral_0^L sqrt(1 + eta_x^2) dx.
```

The first variation in the graph coordinate is

```text
delta E / delta eta = -sigma d/dx(eta_x / sqrt(1 + eta_x^2)).
```

For small amplitude, `delta E/delta eta ~= sigma k^2 A cos(kx)`.  The
restoring capillary acceleration must therefore have the opposite cosine mode
sign to `eta`.  The oracle acceptance is:

| Check | PASS criterion |
|---|---|
| `Q_h(eta)` | P1 cut-cell `q` from `phi(x,y)=y-eta(x)` has the expected total volume and column-volume mode. |
| Energy | analytic graph energy and P1 surface length agree to the expected grid accuracy; energy increases with `A^2`. |
| Variation | finite-difference energy derivative along the cosine mode matches the analytic `delta E/delta eta` projection. |
| Force sign | restoring acceleration mode has sign opposite to the height mode. |
| Symmetry | sine leakage and odd symmetry residuals remain small for cosine input. |
| Phase | `eta > 0` crest gives downward restoring force; trough gives upward restoring force. |
| Visualization | PDF includes interface geometry, `q`, variation/force modes, and energy trend. |

## Closed-Curve Chart Plan

After the graph oracle passes, use the same principle with a closed curve
`X(theta)`:

```text
E[X] = sigma integral |X_theta| dtheta,
Area[X] = 1/2 integral X cross X_theta dtheta.
```

Area conservation is a constraint reaction, not a different theory.  The
closed-droplet chart must reuse the same signs and virtual-work convention
validated by the graph oracle before it is wired into Ch14 T/8 runtime.

## Hypothesis Matrix

| Hypothesis | Preserved observation | Theory prediction | Probe | Current verdict |
|---|---|---|---|---|
| Transported `q` contains degrees of freedom not representable by a smooth phi/graph chart. | Screened graph-q runtime fails hard residual `1.630e-08 > 1.000e-11`; topology movement appears in exploratory probes. | Exact q preservation and smooth graph geometry can conflict. | Compare `Q_h(eta)` from an analytic chart with a transported q field under the same chart projection. | Supported as a live explanation; not fully isolated. |
| `compat_linf=0` after graph rebuild redefines `q` instead of preserving pre-rebuild `q`. | Baseline reports `compat_linf=0` while it is admitted and visually usable. | A chart-owned rebuild can erase incompatible q modes if diagnostics use post-rebuild `Q_h(phi)`. | Store pre-rebuild q, post-rebuild q, and `Q_h(phi)` before any overwrite. | Open; must be checked before runtime connection. |
| Exact q projection makes the interface jagged because q is treated as absolute. | Screened route fails while forming topology carrier; loose probes suggest topology-moving updates. | For q not on the smooth chart manifold, exact q constraints drive jagged or topological chart changes. | Project analytic q versus transported q and compare smoothness/topology at equal residual target. | Supported as negative-knowledge hypothesis. |
| Surface-energy variation and transport do not use the same primary state. | Hybrid path conserves q, rebuilds phi/graph, then computes capillary geometry from the rebuilt chart. | Small residuals can still give wrong force sign, phase, or energy trend. | Graph oracle: compute `E[eta]`, `delta E/delta eta`, force sign, and energy trend without transported q. | This artifact selects a probe; verdict pending. |
| Moving-grid rebuild tracks gauge reconstruction rather than the material interface. | Prior handoff reports moving rebuild/topology carrier sensitivity. | Grid motion can follow a reconstructed phi instead of `Gamma_h`, hiding material-state drift. | Before moving-grid runtime, compare material `Gamma_h`, gauge `phi`, and derived `Q_h(Gamma_h)` across rebuild. | Open; runtime gate only after oracle PASS. |
| Capillary wave and closed droplet are being treated as unrelated theories. | Earlier route accumulated branch-specific graph/closed endpoint conditions. | Chart-specific conditions will fail outside their chart if not derived from one energy. | Derive graph and closed chart from `E=sigma |Gamma_h|`; compare signs and volume reactions. | Partially resolved by this theory choice; closed-chart implementation pending. |
| Pressure, velocity, face cochain, and boundary-condition spaces do not match. | Baseline raw/balanced acceleration signs differ; screened route exposes periodic quotient constraints. | Projection can cancel or flip capillary work if the face-space metric/reaction space is inconsistent. | After graph oracle, connect one short runtime probe and measure face cochain, pressure reaction, boundary trace, and energy sign together. | Open; not tested by the oracle alone. |

## Equation -> Discretization -> Code Plan

| Equation | Discretization | Code target |
|---|---|---|
| `Gamma_h = {(x, eta(x))}` | periodic nodal graph on a uniform 2D `Grid`; gauge only for measurement is `phi(x,y)=y-eta(x)` | `experiment/ch14/diagnose_variational_capillary_oracle.py` |
| `q=Q_h(Gamma_h)` | existing P1 cut-cell geometry on `phi`; `q` remains derived | `twophase.geometry.p1_cut_geometry.cut_geometry_2d` |
| `E[eta]=sigma int sqrt(1+eta_x^2) dx` | periodic trapezoid/segment graph length and amplitude sweep | oracle script |
| `delta E/delta eta=-sigma d/dx(eta_x/sqrt(1+eta_x^2))` | periodic centered segment flux difference and finite-difference mode check | oracle script |
| restoring force | negative graph variation divided by a declared unit mass scale for sign/mode only | oracle script |
| visualization | project-standard PDF output under `experiment/ch14/results/diagnose_variational_capillary_oracle/` | `twophase.tools.experiment.save_figure` |

No runtime Ch14 T/8 experiment is admissible until this oracle passes.

