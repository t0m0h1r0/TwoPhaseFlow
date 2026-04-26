# SP-AA — Capillary Energy Stability and Variational Geometry Design

- **Status**: ACTIVE
- **Compiled by**: Codex
- **Compiled at**: 2026-04-26
- **Scope**: ch13 capillary-wave / rising-bubble surface-tension failure
- **Primary consumers**: paper §2, §3, §5, §8, §9, §10, §13
- **Depends on**: SP-J, SP-Y, SP-Z, WIKI-T-008, WIKI-T-020, WIKI-T-023, WIKI-T-076
- **Public-citation policy**: this SP is an internal research memo and must
  not be cited in the paper. The paper should cite the external references in
  §11.

## 1. Abstract

The current ch13 failure should not be interpreted as "Ridge--Eikonal does not
minimise surface area." Reinitialisation is not the physical surface-tension
operator. Its admissible role is to restore a signed-distance/profile
representation while preserving the interface and mass. Surface-area reduction
must instead enter through the capillary force/pressure-jump discretisation,
because in the continuum two-phase Navier--Stokes system the capillary term is
the variational derivative of interfacial area.

The literature survey gives a sharp design criterion:

```text
Discrete capillarity must be the negative gradient of a discrete surface energy,
or at least be exactly balanced by the same pressure/projection operator.
```

The current implementation computes curvature by a pointwise
`psi_direct_hfe` path and injects it into a pressure-jump decomposition. The
continuous monotone-invariance theorem for curvature is correct, but it is not
a discrete energy-stability theorem. On non-uniform grids, compact finite
differences do not satisfy the nonlinear chain rule exactly. Therefore
direct-`psi` curvature can produce a curvature field that is high-order
accurate on smooth manufactured fields yet not a variational derivative of the
discrete area functional. That mismatch is a plausible root cause of the
observed late-time blow-up.

This memo establishes a theory-first redesign: keep Ridge--Eikonal as a
geometry reparametrisation step, introduce a capillary geometry operator whose
surface tension is projection-native and energy-auditable, and test hypotheses
by falsifiable energy and operator identities before changing production YAML.

## 2. Empirical trigger

The failing reference run was the 64x128 rising-bubble T=8 experiment copied
from the previous remote run:

```text
experiment/ch13/results/_rising_bubble_water_air_alpha2_n64x128_T8/data.npz
```

It reaches `t = 3.788289` and then blows up. The last five kinetic-energy
values are:

```text
5.83e-01, 1.61e+01, 8.01e+02, 4.25e+04, 2.25e+06.
```

The same interval shows:

| Diagnostic | Late-time behaviour | Interpretation |
|---|---:|---|
| volume conservation | stays near `5.04e-04` | mass collapse is not the primary trigger |
| `kappa_max` | oscillates around `O(10^3)` before blow-up | curvature spikes are present before projection failure |
| `ppe_rhs_max` | `6.23e3 -> 1.82e5 -> 8.97e6 -> 4.56e8` | pressure equation receives an explosive source |
| `bf_residual_max` | `1.96e5 -> 5.79e6 -> 2.91e8 -> 1.47e10` | balanced-force residual becomes the dominant defect |
| `div_u_max` | `4.78e-2 -> 2.77e-1 -> 2.01 -> 13.9` | projection no longer controls incompressibility |
| phase mean compatibility | remains tiny until the end | global phase gauge is not the first-order cause |

Snapshot-level interface-length proxies decrease early and then grow only
slightly, so the failure is not a global surface-area explosion. The more
precise hypothesis is a high-frequency, interface-local curvature/pressure
defect: the global area remains plausible while the discrete capillary force
ceases to be a stable surface-energy gradient.

## 3. Literature survey result

### 3.1 CSF and balanced-force methods

Brackbill--Kothe--Zemach introduced the continuum-surface-force (CSF) model,
where surface tension is represented as a volumetric force concentrated near
the interface. The decisive numerical lesson is not merely the formula
`sigma*kappa*n*delta`, but the need to discretise the pressure gradient and the
surface-tension force on compatible locations.

Francois et al. and Popinet made this point operational: parasitic currents are
controlled when the capillary force and pressure gradient are balanced by the
same discrete operator. Height-function curvature is successful in VOF not
because it is "more smoothed," but because it gives a geometrically coherent
curvature to a face/volume force balance.

**Implication for this codebase**: A high-order nodal curvature is not
sufficient. The capillary field must be routed through the same face/projection
contract as the PPE and corrector.

### 3.2 Sharp-interface pressure jumps

Fedkiw--Aslam--Merriman--Osher and Kang--Fedkiw--Liu established ghost-fluid
and boundary-condition-capturing strategies for imposing discontinuous pressure
conditions at material interfaces. These methods support the current
pressure-jump direction, but they also imply a strict contract: the jump,
normal, curvature, coefficient, and pressure operator must refer to the same
interface geometry and the same discrete normal location.

**Implication**: The pressure-jump formulation is not wrong; an inconsistent
geometry-to-PPE handoff is the likely weak point.

### 3.3 Variational mean-curvature flow

Almgren--Taylor--Wang, Luckhaus--Sturzenhecker, and
Merriman--Bence--Osher treat mean-curvature motion as a gradient flow of
surface area. Esedoglu--Otto and related threshold-dynamics work show that
stable interface motion can be obtained from minimising-movement or
thresholding formulations.

**Implication**: If we deliberately add a geometry relaxation, it must be
identified as a variational capillary substep, not hidden inside
reinitialisation. Its volume constraint and energy dissipation must be stated.

### 3.4 Energy-stable two-phase flow

Abels--Garcke--Grün and Barrett--Garcke--Nürnberg provide the cleanest
thermodynamic target. The physically correct system satisfies an energy law:

```text
d/dt [ ∫ 1/2 rho |u|^2 dx + sigma |Gamma| + ∫ rho Phi_g dx ]
  = - ∫ 2 mu |D(u)|^2 dx
```

up to boundary work and model-specific assumptions. With no gravity, the sum of
kinetic and surface energy must not increase except by numerical error. With
gravity, kinetic, surface, and potential energies exchange, while viscosity
dissipates.

**Implication**: The next design must include an energy diagnostic. "No NaN" or
"bounded volume error" is insufficient.

### 3.5 Capillary stiffness and semi-implicit surface tension

Hou--Lowengrub--Shelley, Baensch, Hysing, Sussman--Ohta, and capillary-CFL
studies by Galusinski--Vigneaux and Denner--van Wachem motivate
semi-implicit or geometry-implicit capillary treatments. Explicit capillarity
has a severe `dt ~ h^(3/2)` wave restriction, and curvature errors can be
stiff even when the interface position changes slowly.

**Implication**: Reducing `dt` may delay the failure, but it will not prove the
scheme correct. The deeper requirement is an energy-stable capillary operator.

## 4. Theoretical reconstruction

### 4.1 Reinitialisation is not surface minimisation

Ridge--Eikonal reinitialisation should solve the representation problem:

```text
Given psi^n, construct phi_geo such that |grad phi_geo| = 1
near Gamma and H_eps(phi_geo) preserves the intended mass/interface.
```

It should not solve:

```text
minimise |Gamma| subject to fixed volume.
```

The latter is volume-preserving mean-curvature flow, a physical capillary
relaxation model. Mixing it into reinitialisation would introduce an
unaccounted artificial surface-tension time scale and would make mass/profile
repair indistinguishable from physical dynamics.

### 4.2 Continuous curvature invariance is not discrete energy stability

The continuous theorem is:

```text
psi = g(phi), g' > 0
=> grad psi / |grad psi| = grad phi / |grad phi|
=> kappa(psi) = kappa(phi).
```

This theorem remains mathematically correct. The failing step is the inference:

```text
continuous invariance
=> any high-order discrete derivative of psi gives an energy-stable curvature.
```

That implication is false. A compact finite-difference operator `D_h` generally
does not satisfy:

```text
D_h(g(phi)) = g'(phi) D_h(phi)
D_h(a b)    = a D_h b + b D_h a
```

exactly, especially on non-uniform grids and near clipped/saturated CLS tails.
The algebraic cancellation of `g''` terms in the analytic curvature formula is
therefore not exact in the discrete formula. The result can be a curvature
field that is locally accurate but not the derivative of a discrete area.

### 4.3 Discrete capillary energy criterion

Let `A_h(Gamma_h)` be the discrete surface measure and let `u_f` be the
face-normal velocity used by the projection. A capillary discretisation is
admissible only if its power satisfies:

```text
<u_f, f_sigma,h>_f = -sigma dA_h/dt + O(consistency error)
```

or, in a pressure-jump formulation, if the jump pressure is inserted through
the same `D_f A_f G_f` contract as the projection:

```text
L_h = D_f A_f G_f.
```

This is the surface-tension analogue of the projection-closure theorem in
WIKI-T-076.

## 5. Hypotheses and falsification plan

The purpose of generating many hypotheses is not to keep all of them alive. It
is to reject the easy ones and identify the operator identity that fails.

| ID | Hypothesis | Current evidence | Next falsification test |
|---|---|---|---|
| H-01 | Mass/reinitialisation collapse causes blow-up | unlikely: volume error stays near `5e-4` | run with mass diagnostics and compare `psi` histogram |
| H-02 | Phase mean compatibility/pinning causes blow-up | unlikely: phase mean after gauge remains tiny until final steps | log pin location and per-phase nullspace residual |
| H-03 | Direct-`psi` curvature violates discrete chain-rule cancellation | plausible: current curvature path differentiates `psi` directly | compare `kappa(psi)`, `kappa(phi_geo)`, and weak curvature on saved snapshots |
| H-04 | HFE extends curvature into an energetically wrong support | plausible: HFE lowers some spikes but may move force support | compare raw/HFE/face-local force power |
| H-05 | Pressure-jump capillary field is not projection-native | very plausible: `bf_residual` explodes before divergence | compute `G_f p_sigma + f_sigma` residual on static bubble |
| H-06 | Curvature is located at nodes but capillary work is at faces | plausible by BF theory | add face-work audit `<u_f,f_sigma,f>` |
| H-07 | Non-uniform grid metrics break curvature/area adjointness | plausible: chain/product rules are weakest on stretched grids | uniform vs alpha=2 static droplet operator residual |
| H-08 | Explicit capillary time step is too large | possible but insufficient: instability is late and residual-driven | halve `dt`; if growth rate scales but identity fails, root cause remains operator |
| H-09 | Ridge extraction introduces topology/pinning asymmetry | possible but not primary from volume data | log ridge seeds and left/right symmetry on capillary wave |
| H-10 | Buoyancy residual couples to capillary defect | plausible in rising bubble, not in capillary wave | run gravity-off bubble/perturbed circle capillary-only |
| H-11 | Viscous damping is under-resolved | possible at high curvature modes | compare viscous dissipation to capillary work in energy budget |
| H-12 | Density face coefficient mismatch amplifies pressure jump | plausible at water-air ratio | verify same `A_f` in PPE, corrector, and capillary jump |
| H-13 | Missing energy monitor hides anti-dissipative modes | confirmed: existing gates do not check energy law | add `E_k`, `sigma A_h`, `rho Phi_g`, viscous dissipation |
| H-14 | Curvature clipping masks, then releases, a stiff mode | possible if `kappa_max` active | repeat with clipping diagnostics and no production acceptance |
| H-15 | The geometry variable used for curvature differs from the transported interface | possible in any split geometry path | enforce one `CapillaryGeometryState` per step |
| H-16 | Surface-tension force is not a discrete gradient of a scalar capillary pressure | very plausible | construct `p_sigma` and compare force from `G_f p_sigma` |
| H-17 | Reinitialisation frequency aliases with capillary waves | possible | vary reinit period while holding energy operator fixed |
| H-18 | `psi_min` support truncation creates discontinuous capillary forcing | plausible near tails | replace hard support by variational interface quadrature in test branch |

## 6. Design proposal

### 6.1 New abstraction: CapillaryGeometryState

Each time step should construct one geometry object:

```text
CapillaryGeometryState:
  psi                  transported CLS field
  phi_geo              Ridge--Eikonal signed-distance field
  delta_gamma          interface quadrature / regularised delta
  n_face               face-normal geometry
  kappa_interface      curvature on the same geometry support
  p_sigma              capillary pressure/jump potential
  area_h               discrete interface measure
```

No surface-tension path may recompute an independent geometry from raw `psi`
without declaring which identity it preserves.

### 6.2 Minimum viable repair: projection-native capillary pressure

The least invasive design is:

1. Build `phi_geo` by Ridge--Eikonal.
2. Compute curvature from `phi_geo` or a weak/face geometry operator, not from
   raw saturated `psi`.
3. Construct a capillary pressure potential `p_sigma`.
4. Inject `p_sigma` through the same `G_f`, `A_f`, and `D_f` used by the PPE.
5. Audit the static balance:

```text
R_BF = || -G_f p_sigma + f_sigma,f || / ||f_sigma,f||.
```

This directly tests the theory of Brackbill/Francois/Popinet in the current
FCCD projection language.

### 6.3 Stronger repair: variational capillary substep

If projection-native capillary pressure is insufficient, add a separate
volume-preserving mean-curvature substep:

```text
V_n = -M (kappa - kappa_bar)
```

where `kappa_bar` enforces volume conservation. This is not reinitialisation.
It is a physical/variational geometry relaxation step with its own time scale
and energy law:

```text
A_h^{n+1} <= A_h^n.
```

For production, this substep must be optional and documented as semi-implicit
or variational capillary treatment, not as a hidden stabiliser.

### 6.4 Long-term repair: semi-implicit capillary coupling

The most rigorous but most invasive path is a semi-implicit surface-tension
operator based on the Laplace--Beltrami linearisation:

```text
(I - dt^2 sigma/rho L_sigma) u^{n+1}
  = u^* + dt/rho f_sigma^n.
```

This can relax capillary CFL, but it must preserve balanced-force and
projection closure. A semi-implicit operator that breaks `D_f A_f G_f`
consistency is not acceptable.

## 7. GPU and implementation constraints

The design is GPU-compatible only if the dominant operations are array-level
and reuse existing step data:

- construct `phi_geo`, `n_face`, `delta_gamma`, `p_sigma`, and `area_h` once per
  step and pass them through the pipeline;
- use `backend.xp` for all field operations;
- avoid CPU synchronisation in diagnostics except at configured output points;
- prefer CuPy vector operations for geometry products and reductions;
- use custom kernels only if profiling shows CuPy expression overhead dominates;
- do not use a cache as a substitute for the mathematical state object;
- store reusable physical data explicitly in `CapillaryGeometryState`.

The important distinction is conceptual: reusable geometry is part of the
numerical method, not an implementation cache.

## 8. Proposed YAML vocabulary

The YAML should name theory, not implementation trivia:

```yaml
interface:
  geometry:
    source: ridge_eikonal_sdf
    curvature: face_variational
    capillary_state: shared

numerics:
  momentum:
    terms:
      surface_tension:
        formulation: projection_native_jump
        energy_audit: true
        geometry_relaxation: off
```

Possible values:

| Key | Values | Meaning |
|---|---|---|
| `geometry.source` | `psi`, `ridge_eikonal_sdf` | field used to define interface geometry |
| `geometry.curvature` | `psi_direct_hfe`, `sdf_direct`, `face_variational`, `weak_variational` | curvature operator family |
| `surface_tension.formulation` | `pressure_jump`, `projection_native_jump`, `semi_implicit` | capillary coupling |
| `surface_tension.energy_audit` | `true`, `false` | output discrete energy budget |
| `surface_tension.geometry_relaxation` | `off`, `volume_preserving_mcf` | explicit variational geometry substep |

Backward-compatible aliases can map existing `psi_direct_hfe` and
`pressure_jump` to current behaviour.

## 9. Experiment ladder

The design should be accepted only if it passes this ladder in order:

1. **Static droplet, zero gravity**: `u` remains near zero; pressure jump is
   constant; `R_BF` is small.
2. **Perturbed circle, capillary-only**: `sigma A_h + E_k` is non-increasing
   up to time-discretisation error.
3. **Capillary wave**: amplitude decays at the theoretical viscous rate and no
   asymmetric pin force appears at one intersection.
4. **Rising bubble, short time**: previous `t=0.5` gate remains stable.
5. **Rising bubble, T=8**: energy budget remains bounded; no late
   `bf_residual -> ppe_rhs -> div_u -> KE` cascade.

No production claim should be made from the T=8 run alone.

## 10. A3 traceability chain

| Theory claim | Discretisation obligation | Code target | Verification gate |
|---|---|---|---|
| capillarity is `-delta(sigma A)` | compute force from discrete area/jump potential | new capillary geometry service | capillary-only energy audit |
| BF requires operator consistency | use same face `G_f`, `A_f`, `D_f` contract | PPE/corrector/surface-tension handoff | static droplet `R_BF` |
| reinit is representation repair | keep Ridge--Eikonal free of area minimisation | `ridge_eikonal_reinitializer.py` remains geometric | mass/profile/idempotence tests |
| direct-`psi` invariance is continuous | do not treat it as discrete energy proof | curvature method selection | `kappa(psi)` vs `kappa(phi_geo)` snapshot audit |
| capillary CFL is stiffness, not root-cause proof | use dt studies only as falsification | YAML experiment ladder | growth-rate vs operator-residual comparison |

## 11. Verification round 1 — existing T=8 audit

### 11.1 Data source and audit method

This round used the existing failed run:

```text
experiment/ch13/results/_rising_bubble_water_air_alpha2_n64x128_T8/data.npz
```

No production code was changed. The audit used only stored diagnostics and
saved snapshots. For the discrete chain-rule check, each saved `psi` snapshot
was compared with `phi_logit = log(psi/(1-psi))` using the same second-order
non-uniform finite-difference curvature formula. This is not the production
CCD operator; it is a neutral falsification probe for whether discrete
`kappa(psi)` and `kappa(phi)` remain practically identical.

### 11.2 Observed cascade

The run stops at:

```text
t_last = 3.788289083, steps = 917, snapshots = 76.
```

Late-time diagnostics:

| Quantity | Last five values |
|---|---:|
| volume error | `5.043e-4, 5.043e-4, 5.041e-4, 5.043e-4, 5.041e-4` |
| kinetic energy | `5.833e-1, 1.609e1, 8.011e2, 4.253e4, 2.251e6` |
| `kappa_max` | `2.851e2, 1.076e3, 4.426e2, 1.066e3, 4.386e2` |
| `ppe_rhs_max` | `1.283e3, 6.235e3, 1.821e5, 8.970e6, 4.560e8` |
| `bf_residual_max` | `3.913e4, 1.955e5, 5.789e6, 2.906e8, 1.466e10` |
| `div_u_max` | `1.372e-3, 4.784e-2, 2.766e-1, 2.010e0, 1.387e1` |
| phase mean after gauge | `5.219e-15, 3.316e-14, 2.358e-13, 3.521e-11, 1.127e-9` |

First large ratio events:

| Event | First trigger |
|---|---|
| `bf_residual_max` ratio > 5 | `t = 3.633862` |
| `kappa_max` ratio > 2 | `t = 3.770598` |
| kinetic-energy ratio > 10 | `t = 3.787172` |
| `div_u_max` ratio > 5 | `t = 3.787172` |
| `ppe_rhs_max` ratio > 5 | `t = 3.788135` |

Therefore the empirical ordering is:

```text
balanced-force residual growth
  -> curvature spikes
  -> divergence / kinetic-energy explosion
  -> PPE RHS explosion at terminal step.
```

This does not prove a unique cause, but it rules out a simple "volume collapse
first" story.

### 11.3 Discrete curvature reparametrisation audit

Saved grid spacing is non-uniform:

```text
x: h_min = 0.0111523, h_mean = 0.015625, h_max = 0.0223040, ratio = 2.0
y: h_min = 0.00918847, h_mean = 0.015625, h_max = 0.0183764, ratio = 2.0
```

The `psi`-curvature and logit-`phi` curvature are not numerically identical on
the interface band:

| Snapshot | area proxy | band nodes | median rel. diff | p95 rel. diff | max rel. diff |
|---:|---:|---:|---:|---:|---:|
| `t=0.004` | `2.37436` | `1307` | `2.41e-2` | `9.87e-2` | `2.07e-1` |
| `t=0.953` | `2.31578` | `2595` | `2.06e-2` | `1.65e-1` | `2.04e0` |
| `t=1.902` | `2.31740` | `2602` | `2.42e-2` | `2.53e-1` | `2.27e0` |
| `t=2.851` | `2.32060` | `2614` | `2.85e-2` | `2.49e-1` | `2.42e0` |
| `t=3.754` | `2.32322` | `2622` | `3.08e-2` | `2.65e-1` | `2.39e0` |

This supports the discrete caveat: continuous monotone invariance is not a
practical guarantee that `psi`-direct curvature is the correct capillary energy
gradient on stretched grids.

### 11.4 Code-path audit

The current path is not a single projection-native capillary potential:

```text
src/twophase/simulation/ns_step_services.py
  kappa_raw = curv.compute(state.psi)
  state.kappa = hfe.apply(kappa_raw, state.psi)
  state.f_x, state.f_y = st_force.compute(state.kappa, state.psi, ...)
  rhs = predictor_rhs + div(f_sigma/rho)
  set_interface_jump_context(psi=state.psi, kappa=state.kappa, sigma=state.sigma)

src/twophase/ns_terms/surface_tension.py
  f_sigma = kappa * grad(psi) / We

src/twophase/ppe/fccd_matrixfree_helpers.py
  pressure_eff = pressure + sigma * kappa * (1 - psi)
```

Thus the capillary information enters through both an explicit CSF-like RHS
and a pressure-jump decomposition. The method may still be defensible after a
formal derivation, but it is not yet expressed as:

```text
one geometry -> one p_sigma -> same D_f A_f G_f projection contract.
```

This strongly supports H-05/H-06/H-16.

### 11.5 Hypothesis status after round 1

| ID | Status | Round-1 judgement |
|---|---|---|
| H-01 | rejected for this failure | volume and `psi` extrema do not collapse before blow-up |
| H-02 | rejected as primary | phase mean compatibility remains tiny; PPE pin count is zero |
| H-03 | supported | `psi` vs logit-`phi` curvature differs by p95 up to `2.65e-1` and max > `2x` |
| H-04 | open | raw/HFE force-power split is not logged yet |
| H-05 | strongly supported | `bf_residual` grows before terminal PPE/divergence failure |
| H-06 | supported | curvature/force are nodal `kappa*grad(psi)` while projection is face-native |
| H-07 | supported | saved grid has 2:1 spacing ratio and chain-rule discrepancy grows over time |
| H-08 | open, not sufficient | time step shrinks only after velocity explosion; half-dt falsification still needed |
| H-09 | open, low current evidence | PPE pin count is zero; ridge/pin symmetry was not logged |
| H-10 | open | rising bubble mixes buoyancy and capillarity; gravity-off separation is required |
| H-11 | open | viscous dissipation is not recorded |
| H-12 | open | face coefficient consistency must be audited together with capillary pressure |
| H-13 | confirmed instrumentation gap | stored energies contain only kinetic energy |
| H-14 | rejected for this YAML | no curvature cap is configured in the production YAML |
| H-15 | reformulated | current code uses raw `state.psi`, but lacks a shared `CapillaryGeometryState` |
| H-16 | strongly supported | no single scalar `p_sigma` is constructed and projected through one operator |
| H-17 | open | reinitialisation-period sweep not performed |
| H-18 | supported | hard `psi_min` band truncation is present in the capillary path |

### 11.6 Narrowed root-cause cluster

Round 1 narrows the problem to:

```text
capillary operator inconsistency
  = non-variational curvature
  + nodal/face support mismatch
  + dual CSF/jump insertion
  + missing energy audit.
```

The most important negative result is equally useful: the data do not support
"Ridge--Eikonal should minimise area" as the first fix. The next tests should
therefore target capillary operator identities, not reinitialisation smoothing.

### 11.7 Next falsification experiments

Run these before implementing a production replacement:

1. Static droplet with `surface_tension.formulation: pressure_jump` and with
   explicit CSF disabled: measure `R_BF`.
2. Static droplet with explicit CSF only and pressure jump disabled: measure
   parasitic velocity and pressure-jump error.
3. Same geometry, compare `psi_direct_hfe`, `sdf_direct`, and
   `face_variational` curvature candidates.
4. Perturbed circle, gravity off: measure `E_k + sigma A_h`.
5. Rising bubble, gravity on: repeat only after the capillary-only energy gate
   passes.

## 12. Response policy — theory to implementation

### 12.1 Decision

The implementation response should not be "smooth curvature harder" or
"minimise area during reinitialisation." The theoretically admissible response
is:

```text
Represent capillarity exactly once, using one geometry state and one projection
contract.
```

The current hybrid path:

```text
div(f_sigma/rho) in PPE RHS
+ f_sigma/rho in the velocity corrector
+ pressure-jump decomposition
```

is not the right production abstraction. It represents capillarity through two
different algebraic routes. Even if each route is locally plausible, their sum
is not guaranteed to be the negative gradient of a single discrete surface
energy.

### 12.2 Phase-separated PPE compatibility theorem

The phase-separated FCCD PPE does not live on the mixture graph. It lives on
the phase graph:

```text
L_sep = D_f A_f^sep G_f,

A_f^sep(i,j) =
  2/(rho_i + rho_j), if i and j are in the same phase,
  0,                 if i and j are in different phases.
```

Therefore a capillary jump compatible with `L_sep` must also be a
phase-graph object. The sharp-interface datum is not a volumetric force
proportional to `grad(psi)`. It is a pair of phase pressure traces:

```text
[p]_Gamma = p_g|_Gamma - p_l|_Gamma = sigma kappa_Gamma.
```

Discrete theorem:

```text
If the PPE/corrector use L_sep = D_f A_f^sep G_f, then a capillary jump datum
is projection-consistent only if it is represented as a phase-labelled pressure
extension J_sep whose trace jump satisfies

  J_g|_Gamma - J_l|_Gamma = sigma kappa_Gamma,

and whose gradients are consumed only through the same L_sep operator.
```

Equivalently, the capillary stage must be written:

```text
F_J = jump_flux_sep(J_sep),
L_sep q = r - D_f F_J,
u_f^{n+1} = u_f^* - dt (A_f^sep G_f q + F_J).
```

No additional explicit capillary force is allowed in this formulation.

### 12.3 Young--Laplace null test

The theorem has a decisive null test. For a static circular bubble with
constant curvature:

```text
kappa_Gamma = const,
J_l = C_l,
J_g = C_l + sigma kappa_Gamma.
```

Because `J_sep` is constant inside each phase:

```text
G_f J_sep = 0 on same-phase faces,
A_f^sep G_f J_sep = 0 on cross-phase faces,
L_sep J_sep = 0.
```

Thus the projection RHS is not polluted, the velocity correction is zero, and
the physical pressure still has the correct Young--Laplace jump. This is the
minimal discrete statement of balanced force for phase-separated PPE.

The current smooth jump

```text
J_smooth = sigma kappa (1 - psi)
```

does not satisfy this null test on a smeared CLS interface. Even if `kappa` is
constant, `grad(1-psi)` is nonzero inside the interface band. Since `A_f^sep`
cuts cross-phase faces, this smooth transition is not a pure cross-interface
jump; it becomes an intra-phase volumetric source near the thresholded phase
boundary. That is a CSF-like object, not a phase-separated pressure trace.

Therefore `J_smooth` is admissible only as part of a mixture/CSF formulation.
It is not the canonical capillary datum for phase-separated PPE.

### 12.4 Capillary pressure theory

Let `J_sep` denote the discrete capillary jump datum derived from a single
geometry state. In a phase-separated projection-native jump method, `J_sep` is
not treated as an additional explicit body force and is not differentiated by
the ordinary FCCD pressure-gradient operator. It is first converted into a
phase-trace face flux:

```text
F_J = jump_flux_sep(J_sep).
```

The discrete projection should be written as:

```text
r       = D_f u_f^*/dt,
L_sep q = r - D_f F_J,
L_sep   = D_f A_f^sep G_f,
u_f^{n+1} = u_f^* - dt (A_f^sep G_f q + F_J).
```

The important point is not whether the pressure variable is called "physical"
or "corrector" pressure. The important point is that the same `F_J` appears in
both the PPE RHS and the velocity corrector. A separate explicit `f_sigma` may
be kept only in a different formulation, never silently added on top of the
jump formulation.

### 12.5 Admissible capillary formulations

There are three named formulations:

| Formulation | Capillary path | Intended use |
|---|---|---|
| `projection_native_jump` | phase-labelled `J_sep` converted to `jump_flux_sep`; explicit capillary force is zero | production candidate |
| `explicit_balanced_csf` | face force only; jump context disabled | diagnostic / comparison |
| `legacy_csf_jump` | current dual path | regression only, not a theory-backed production scheme |

This naming is important. The current path should not continue to be called
simply `pressure_jump`, because that name hides the simultaneous explicit CSF
insertion.

### 12.6 Geometry state contract

All capillary formulations must consume:

```text
CapillaryGeometryState:
  psi                  transported CLS field
  phi_geo              SDF/reconstructed geometry field
  delta_gamma          interface quadrature support
  n_face               face-located normal geometry
  kappa                curvature from the selected geometry operator
  J_sep                phase-separated capillary jump potential
  area_h               discrete surface measure
```

This is not an implementation cache. It is the mathematical state required to
keep curvature, jump, support, and energy audit mutually consistent.

### 12.7 First implementable design

The first production trial should be deliberately conservative:

1. Build `CapillaryGeometryState` after interface transport/reinitialisation.
2. For the first trial, use existing Ridge--Eikonal/logit reconstruction to
   obtain an SDF-like `phi_geo`; do not add area minimisation.
3. Compute `kappa` by an SDF-direct curvature operator for the jump path.
4. Extend `kappa_Gamma` into each phase along the geometry normals.
5. Construct a phase-labelled jump field:

```text
J_l = 0,
J_g = sigma * kappa_ext,
```

   or an equivalent symmetric gauge:

```text
J_l = -0.5 sigma kappa_ext,
J_g =  0.5 sigma kappa_ext.
```

   The choice differs only by phase constants after gauge projection; the jump
   difference is the invariant.
6. In `projection_native_jump`, set explicit capillary force components to
   zero for both PPE RHS and velocity corrector.
7. Assemble `F_J = jump_flux_sep(J_sep)`.
8. Solve the scalar pressure correction with RHS contribution `-D_f F_J`.
9. Correct face velocity with `-dt F_J` in addition to `-dt A_f^sep G_f q`.
10. Output diagnostic physical capillary pressure `q + J_sep` separately if needed for plots;
   do not use a plotting variable in the velocity correction.

This directly tests the central hypothesis:

```text
If the blow-up is caused by dual inconsistent capillary insertion and
smooth-jump leakage, replacing `sigma*kappa*(1-psi)` with phase-labelled
`J_sep` and removing the explicit CSF path should reduce `bf_residual` and
parasitic velocity in static/capillary-only tests.
```

### 12.8 Required code structure

New or refactored code should use dependency inversion:

```text
src/twophase/capillary/
  state.py              CapillaryGeometryState, CapillaryCoupling
  geometry.py           CapillaryGeometryBuilder
  curvature.py          CapillaryCurvatureOperator interface + implementations
  coupling.py           ProjectionNativeJump, ExplicitBalancedCSF, LegacyCSFJump
  diagnostics.py        energy and balanced-force audits
```

The NS pipeline should depend on these interfaces, not on concrete curvature
classes. Existing tested code such as `CurvatureCalculatorPsi` must be retained
as a legacy implementation and selectable as `legacy_csf_jump`.

The existing helper

```text
apply_fccd_interface_jump(pressure) = pressure + sigma*kappa*(1-psi)
```

must remain available only for `legacy_csf_jump`. The new path should pass an
already-assembled phase-trace flux:

```text
flux_p = A_f^sep G_f q + jump_flux_sep(J_sep).
```

That prevents the PPE layer from silently choosing a mixture-style jump shape or
from differentiating a discontinuous nodal pressure field with a compact
cross-interface stencil.

### 12.9 Pipeline changes

Current stage:

```text
compute curvature -> compute f_sigma -> add div(f_sigma/rho)
-> set jump context -> correct with pressure and f_sigma
```

Target stage:

```text
build CapillaryGeometryState
-> assemble CapillaryCoupling
-> PPE RHS includes non-capillary force divergence
-> PPE RHS adds coupling.rhs_source
-> corrector subtracts coupling.pressure_flux_components
-> corrector adds coupling.corrector_force_components
-> diagnostics use coupling.diagnostic_force_components and energy terms
```

For `projection_native_jump`:

```text
rhs_force_components        = 0
rhs_source                  = -D_f jump_flux_sep(J_sep)
pressure_flux_components    = jump_flux_sep(J_sep)
corrector_force_components  = 0
diagnostic_pressure_jump    = J_sep
diagnostic_force_components = optional reconstructed capillary force
```

For `explicit_balanced_csf`:

```text
rhs_force_components       = face-balanced f_sigma/rho
corrector_force_components = same face-balanced f_sigma/rho
jump_context               = none
```

### 12.10 YAML policy

Use short theory-facing names:

```yaml
numerics:
  momentum:
    terms:
      surface_tension:
        formulation: projection_native_jump
        geometry_source: ridge_eikonal_sdf
        curvature: sdf_direct
        jump_shape: phase_trace
        energy_audit: true
```

Legacy compatibility:

```text
pressure_jump -> legacy_csf_jump
psi_direct_hfe -> legacy psi curvature operator
sigma_kappa_one_minus_psi -> legacy smooth jump shape
```

The migration should warn in debug mode when a YAML selects the legacy dual
path.

### 12.11 Acceptance gates before rising-bubble T=8

Implementation is not accepted by reaching T=8 alone. It must pass:

1. Static bubble, gravity off: phase-labelled `J_sep` passes the
   Young--Laplace null test `L_sep J_sep = 0` for constant curvature.
2. Static bubble, gravity off: `R_BF` decreases relative to `legacy_csf_jump`.
3. Static bubble, gravity off: maximum parasitic velocity decreases.
4. Perturbed circle, gravity off: `E_k + sigma A_h` does not grow
   systematically.
5. Capillary wave: amplitude decays and intersection pin asymmetry does not
   reappear.
6. Rising bubble T=0.5: existing stable gate remains stable.
7. Rising bubble T=8: no late `bf_residual -> ppe_rhs -> div_u -> KE`
   cascade.

### 12.12 Implementation phases

| Phase | Change | Commit boundary |
|---|---|---|
| P0 | add diagnostics only: `R_BF`, `area_h`, `E_k`, `sigma A_h`, optional `E_g` | safe instrumentation |
| P1 | introduce `CapillaryGeometryState` and `CapillaryCoupling` without changing default behaviour | architecture |
| P2 | move current dual path behind `legacy_csf_jump` | semantic naming |
| P3 | implement `jump_flux_sep(J_sep)` and split RHS/corrector flux | phase-PPE consistency |
| P4 | implement `projection_native_jump` with zero explicit capillary force | first theory-backed trial |
| P5 | add `sdf_direct` curvature source from shared geometry | geometry consistency |
| P6 | run static/perturbed/capillary-wave gates | falsification |
| P7 | only then run rising-bubble T=8 | production candidate |

### 12.13 Verification round 2 — phase-separated null probe

The phase-separated null test was probed with:

```text
experiment/ch13/tools/phase_separated_capillary_jump_probe.py
```

The probe uses a planar static interface with constant curvature surrogate
`kappa_const = 20`, `sigma = 0.072`, and water/air density ratio. It compares:

1. an ideal phase graph operator, where cross-phase faces are cut and
   same-phase gradients are local differences;
2. the current FCCD matrix-free phase-separated PPE core operator.

Results:

| Operator | Density | Jump field | `||LJ||_inf` | `||LJ||_2` | nonzero |
|---|---|---|---:|---:|---:|
| graph | sharp | `J_sep` phase constant | `0.000e0` | `0.000e0` | `0` |
| graph | sharp | `sigma*kappa*(1-psi)` | `6.421e2` | `5.722e3` | `4225` |
| graph | smooth | `J_sep` phase constant | `0.000e0` | `0.000e0` | `0` |
| graph | smooth | `sigma*kappa*(1-psi)` | `2.804e0` | `2.897e1` | `4225` |
| current FCCD | sharp | `J_sep` phase constant | `5.463e2` | `5.798e3` | `4225` |
| current FCCD | sharp | `sigma*kappa*(1-psi)` | `6.443e2` | `5.747e3` | `4225` |
| current FCCD | smooth | `J_sep` phase constant | `2.718e0` | `3.487e1` | `4225` |
| current FCCD | smooth | `sigma*kappa*(1-psi)` | `2.814e0` | `2.901e1` | `4225` |

Interpretation:

```text
The phase-labelled jump theory works on the phase graph.
The current FCCD core operator does not satisfy the same null test when it is
given a discontinuous phase-labelled jump field.
```

The failure is expected: the current FCCD `face_gradient` differentiates the
nodal field with compact stencils that cross the phase jump before the
phase-separated coefficient masks cross-phase faces. Thus `A_f^sep=0` on
cross-phase faces is not enough; the jump-gradient path itself must be
phase-trace aware.

Implementation consequence:

```text
Do not implement projection_native_jump by merely replacing
sigma*kappa*(1-psi) with a nodal J_sep inside the existing FCCD apply().
```

The correct implementation must split the pressure correction:

```text
p_plot = q + J_sep,
flux_p = A_f^sep G_f q + jump_flux_sep(J_sep),
u_f^{n+1} = u_f^* - dt flux_p.
```

For the static constant-curvature null test:

```text
jump_flux_sep(J_sep) = 0.
```

For variable curvature, `jump_flux_sep` must be defined on the phase graph
using phase-trace extensions and the same cut-face policy as `A_f^sep`.

This converts P3 from "pass `J_sep` into the existing FCCD operator" to
"implement a phase-trace jump operator that supplies both `L_sep J_sep` and the
corrector jump flux." Without this change, the theory-backed design will not
work in the current code.

### 12.14 Theory of `jump_flux_sep`

#### 12.14.1 Discrete spaces

Let the nodal phase graph be:

```text
V = V_l ∪ V_g,
E_sep = E_l ∪ E_g,
E_m = { face e=(i,j): i,j ∈ V_m }.
```

The phase-separated PPE operator is:

```text
L_sep q = D_f A_f^sep G_f q,
```

where `A_f^sep=0` outside `E_sep`. The jump datum is not a single smooth nodal
function. It is a pair of phase traces/extensions:

```text
J_sep = (J_l on V_l, J_g on V_g),
J_g|_Gamma - J_l|_Gamma = sigma kappa_Gamma.
```

#### 12.14.2 Definition

`jump_flux_sep` is a map from phase-labelled jump data to face fluxes:

```text
jump_flux_sep : (J_l, J_g) -> F_J on E_sep.
```

It is defined by three axioms:

1. **Cut-face support**

```text
F_J(e) = 0,  e ∉ E_sep.
```

2. **Phase-constant nullity**

```text
J_m = const on V_m  =>  F_J(e)=0 for every e∈E_m.
```

3. **Projection closure**

If `q` solves

```text
L_sep q = D_f u_f^*/dt - D_f F_J,
```

and the corrector uses

```text
u_f^{n+1} = u_f^* - dt(A_f^sep G_f q + F_J),
```

then

```text
D_f u_f^{n+1} = 0
```

up to the linear-solver tolerance.

The proof is algebraic:

```text
D_f u_f^{n+1}
 = D_f u_f^* - dt D_f A_f^sep G_f q - dt D_f F_J
 = dt r - dt(r - D_f F_J) - dt D_f F_J
 = 0.
```

#### 12.14.3 Minimal operator

The minimal GPU-friendly operator is the phase-restricted graph gradient:

```text
F_J,e = A_f^sep(e) * (J_m(j) - J_m(i)) / d_ij,
        e=(i,j)∈E_m,

F_J,e = 0,
        e∉E_sep.
```

This is only second-order/local, but it is exact for phase constants and
therefore passes the Young--Laplace null test. A lower-order phase-consistent
jump flux is preferable to a high-order compact derivative that crosses the
jump and fails the null test.

#### 12.14.4 High-order extension path

A future high-order version may replace the local graph gradient by a
phase-restricted compact operator, but only if it satisfies the same three
axioms. In particular, compact stencils must be truncated, one-sided, or solved
per connected phase component so that no equation couples `V_l` and `V_g`.

#### 12.14.5 Extension of curvature

For variable curvature, `J_m` must be extended into each phase before applying
the graph gradient. The admissible extension is normal-constant near the
interface:

```text
n · grad J_m = 0,
J_g|_Gamma - J_l|_Gamma = sigma kappa_Gamma.
```

In implementation terms, this is a phase-local extension problem. The first
trial may reuse the existing HFE/Ridge--Eikonal geometry to build `kappa_ext`,
but the extension result must be stored in `CapillaryGeometryState`; it must not
be hidden as a cache.

#### 12.14.6 Required implementation contract

The coupling object must expose:

```text
CapillaryCoupling:
  rhs_source               # node field: -D_f F_J
  pressure_flux_components # face fields: F_J
  corrector_force_components # zero for projection_native_jump
  diagnostic_pressure_jump # q + J_sep for plots only
```

`pressure_flux_components` is pressure-like: the corrector subtracts it. It is
not a body force and must not be added as `+dt f/rho`.

[SOLID-OK] The design separates geometry construction, curvature evaluation,
capillary coupling, diagnostics, and NS orchestration. The pipeline depends on
interfaces and preserves existing tested implementations as legacy modes.

## 13. External references for paper use

- Brackbill, Kothe, Zemach, "A continuum method for modeling surface tension,"
  Journal of Computational Physics, 1992. https://doi.org/10.1016/0021-9991(92)90240-Y
- Francois et al., "A balanced-force algorithm for continuous and sharp
  interfacial surface tension models within a volume tracking framework,"
  Journal of Computational Physics, 2006. https://doi.org/10.1016/j.jcp.2005.08.004
- Popinet, "An accurate adaptive solver for surface-tension-driven interfacial
  flows," Journal of Computational Physics, 2009. https://doi.org/10.1016/j.jcp.2009.04.042
- Fedkiw, Aslam, Merriman, Osher, "A non-oscillatory Eulerian approach to
  interfaces in multimaterial flows," Journal of Computational Physics, 1999.
  https://doi.org/10.1006/jcph.1999.6236
- Kang, Fedkiw, Liu, "A boundary condition capturing method for multiphase
  incompressible flow," Journal of Scientific Computing, 2000.
  https://doi.org/10.1023/A:1011178417620
- Sussman, Smereka, Osher, "A level set approach for computing solutions to
  incompressible two-phase flow," Journal of Computational Physics, 1994.
  https://doi.org/10.1006/jcph.1994.1155
- Olsson, Kreiss, "A conservative level set method for two phase flow,"
  Journal of Computational Physics, 2005. https://doi.org/10.1016/j.jcp.2005.04.007
- Sussman, Ohta, "A stable and efficient method for treating surface tension in
  incompressible two-phase flow," SIAM Journal on Scientific Computing, 2009.
  https://doi.org/10.1137/080732122
- Hou, Lowengrub, Shelley, "Removing the stiffness from interfacial flows with
  surface tension," Journal of Computational Physics, 1994.
  https://doi.org/10.1006/jcph.1994.1170
- Baensch, "Finite element discretization of interfacial flows with surface
  tension," Numerische Mathematik, 2001. https://doi.org/10.1007/PL00005443
- Abels, Garcke, Gruen, "Thermodynamically consistent diffuse interface model
  for incompressible two-phase flows with different densities," Mathematical
  Models and Methods in Applied Sciences, 2012. https://arxiv.org/abs/1104.1336
- Barrett, Garcke, Nuernberg, "Stable parametric finite element approximations
  of two-phase Navier--Stokes flow," 2013. https://arxiv.org/abs/1308.3335
- Almgren, Taylor, Wang, "Curvature-driven flows: a variational approach,"
  SIAM Journal on Control and Optimization, 1993. https://doi.org/10.1137/0331020
- Luckhaus, Sturzenhecker, "Implicit time discretization for the mean curvature
  flow equation," Calculus of Variations and Partial Differential Equations,
  1995. https://doi.org/10.1007/BF01212360
- Merriman, Bence, Osher, "Diffusion generated motion by mean curvature," 1992.
  https://www.math.ucla.edu/~bertozzi/254/mbo.pdf
- Esedoglu, Otto, "Threshold dynamics for networks with arbitrary surface
  tensions," Communications on Pure and Applied Mathematics, 2015.
  https://arxiv.org/abs/1503.07469
