---
ref_id: WIKI-T-077
title: "Capillary Energy Stability: Variational Geometry and Projection-Native Surface Tension"
domain: theory
status: ACTIVE
superseded_by: null
tags: [surface_tension, curvature, energy_stability, balanced_force, variational_geometry, ridge_eikonal]
compiled_by: Codex
compiled_at: "2026-04-26"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-008]]"
  - "[[WIKI-T-020]]"
  - "[[WIKI-T-023]]"
  - "[[WIKI-T-076]]"
source_memo: "docs/memo/short_paper/SP-AA_capillary_energy_variational_geometry.md"
---

# Capillary Energy Stability

## Core conclusion

Surface-area minimisation must not be hidden inside Ridge--Eikonal
reinitialisation. Reinitialisation repairs the representation:

```text
psi -> phi_geo, |grad phi_geo| = 1, mass/interface preserved.
```

Surface-area reduction is the physical role of surface tension. It must enter
through a capillary force or pressure-jump operator that is either:

1. projection-native balanced-force, or
2. explicitly variational and energy dissipative.

## Energy law target

For the continuum two-phase system, the target budget is:

```text
d/dt [ E_k + sigma A + E_g ] = -D_mu
```

where:

- `E_k = ∫ 1/2 rho |u|^2 dx`,
- `A = |Gamma|`,
- `E_g = ∫ rho Phi_g dx`,
- `D_mu = ∫ 2 mu |D(u)|^2 dx`.

Therefore a production capillary scheme must monitor more than volume and
NaN/Inf status. It must expose the discrete exchange among kinetic, surface,
and gravitational potential energy.

## Discrete caveat for psi-direct curvature

The monotone-transformation theorem remains true in the continuum:

```text
psi = g(phi), g' > 0
=> kappa(psi) = kappa(phi).
```

However, this is not a discrete energy-stability theorem. A compact difference
operator on non-uniform grids does not satisfy the exact nonlinear chain rule:

```text
D_h(g(phi)) != g'(phi) D_h(phi)
```

in general. Thus direct differentiation of saturated `psi` may be accurate in a
pointwise manufactured-curvature test while still failing to be the negative
gradient of a discrete area functional.

## Current failure hypothesis

The ch13 T=8 rising-bubble blow-up is most consistent with this cascade:

```text
curvature/geometry defect
  -> capillary pressure-jump imbalance
  -> balanced-force residual growth
  -> PPE RHS explosion
  -> divergence growth
  -> kinetic-energy blow-up.
```

The existing failed run supports this ordering:

- volume error remains near `5e-4`;
- phase mean compatibility remains small until the last steps;
- `bf_residual_max`, `ppe_rhs_max`, and `div_u_max` explode together near the
  end;
- global interface-length proxy does not explode, so the issue is likely
  high-frequency/interface-local rather than global area growth.

## Design rule

Introduce a single per-step geometry state:

```text
CapillaryGeometryState:
  psi
  phi_geo
  delta_gamma
  n_face
  kappa_interface
  p_sigma
  area_h
```

All surface-tension paths must consume this object. Recomputing an independent
curvature from raw `psi` inside the capillary stage is not admissible unless the
preserved identity is documented and tested.

## Minimal acceptable implementation

1. Build `phi_geo` from Ridge--Eikonal.
2. Compute curvature on `phi_geo` or by a weak/face variational geometry
   operator.
3. Construct a capillary pressure potential `p_sigma`.
4. Inject it through the same face operators used by the PPE:

```text
L_h = D_f A_f G_f.
```

5. Audit the static balance:

```text
R_BF = || -G_f p_sigma + f_sigma,f || / ||f_sigma,f||.
```

## Hypothesis ledger

| ID | Hypothesis | Status |
|---|---|---|
| H-01 | mass collapse from reinitialisation | rejected for current T=8 failure |
| H-02 | phase mean/gauge incompatibility | rejected as primary |
| H-03 | discrete chain-rule failure in `psi` curvature | supported |
| H-04 | HFE support moves curvature to wrong force support | open |
| H-05 | pressure jump is not projection-native | strongly supported |
| H-06 | nodal curvature / face force mismatch | supported |
| H-07 | non-uniform metrics amplify non-variational curvature | supported |
| H-08 | capillary CFL too large | open; not sufficient alone |
| H-09 | ridge extraction/pinning asymmetry | open; low current evidence |
| H-10 | buoyancy residual couples to capillary defect | open |
| H-11 | viscosity under-resolves high-frequency capillary modes | open |
| H-12 | density face coefficient mismatch | open |
| H-13 | missing energy monitor hides anti-dissipation | confirmed instrumentation gap |
| H-14 | curvature clipping masks stiff modes | rejected for current YAML |
| H-15 | multiple geometry variables in one step | reformulated as missing shared geometry state |
| H-16 | capillary force is not discrete gradient of scalar jump | strongly supported |
| H-17 | reinitialisation period aliases with capillary waves | open |
| H-18 | hard `psi_min` support truncation creates force discontinuity | supported |

## Verification Round 1

The existing failed T=8 rising-bubble run was audited without changing
production code. The run reaches `t = 3.788289083` and fails with:

```text
bf_residual_max -> ppe_rhs_max -> div_u_max -> kinetic_energy
```

growth, while volume error remains near `5.04e-4` and phase mean compatibility
remains small until the terminal steps. This rejects mass collapse and phase
mean/gauge failure as primary causes for this run.

The same snapshots show that direct `psi` curvature and logit-`phi` curvature
are not numerically equivalent on the stretched grid. At `t=3.754`, the
interface-band relative difference has median `3.08e-2`, p95 `2.65e-1`, and
maximum `2.39e0`. This supports the discrete chain-rule caveat.

The code path currently inserts capillarity through both:

- explicit `div(f_sigma/rho)` with `f_sigma = kappa grad(psi) / We`;
- pressure-jump decomposition `pressure + sigma kappa (1 - psi)`.

Therefore the present implementation is not yet a single
projection-native scalar capillary pressure passed through the same
`D_f A_f G_f` contract.

## Phase-Separated PPE Consistency

For phase-separated PPE, the projection operator is:

```text
L_sep = D_f A_f^sep G_f,

A_f^sep(i,j) =
  2/(rho_i + rho_j), if i and j are in the same phase,
  0,                 otherwise.
```

Therefore capillary pressure must be a phase-labelled pressure trace, not a
smooth `sigma*kappa*(1-psi)` mixture field. The compatible jump datum is:

```text
J_g|_Gamma - J_l|_Gamma = sigma kappa_Gamma.
```

The projection-native split is:

```text
F_J = jump_flux_sep(J_sep),
L_sep q = r - D_f F_J,
u_f^{n+1} = u_f^* - dt(A_f^sep G_f q + F_J).
```

For a static circular bubble, `kappa` is constant, so `J_l` and `J_g` are
phase constants. Then `jump_flux_sep(J_sep)=0` and the velocity correction is zero
while the physical pressure retains the Young--Laplace jump. This is the
required null test.

The current smooth jump `sigma*kappa*(1-psi)` fails this phase-separated null
test because `grad(psi)` is nonzero inside the smeared interface band and
becomes an intra-phase volumetric source after cross-phase faces are cut.

## Verification Round 2

The null test was probed by
`experiment/ch13/tools/phase_separated_capillary_jump_probe.py`.

Result:

- ideal phase graph: `L_sep J_sep = 0` exactly for phase-constant `J_sep`;
- ideal phase graph: smooth `sigma*kappa*(1-psi)` gives nonzero source;
- current FCCD matrix-free core: phase-constant `J_sep` still gives nonzero
  source.

The last result is critical. Existing FCCD `face_gradient` differentiates a
nodal discontinuous jump field with compact stencils before the phase-separated
coefficient masks cross-phase faces. Therefore cross-face cutting alone does
not make a nodal `J_sep` compatible with phase-separated PPE.

Implementation must add a phase-trace jump operator:

```text
flux_p = A_f^sep G_f q + jump_flux_sep(J_sep),
```

where `jump_flux_sep(J_sep)=0` for constant-curvature static bubbles. Simply
passing nodal `J_sep` through the current FCCD operator is predicted to fail.
The implementation contract is tracked in [[WIKI-L-036]].

The algebraic closure is:

```text
L_sep q = D_f u_f^*/dt - D_f jump_flux_sep(J_sep),
u_f^{n+1} = u_f^* - dt(A_f^sep G_f q + jump_flux_sep(J_sep)).
```

Then `D_f u_f^{n+1}=0` follows directly from the PPE equation.

## Response Policy

The production response is to introduce named capillary coupling strategies:

| Name | Capillary representation | Use |
|---|---|---|
| `projection_native_jump` | phase-labelled `J_sep`; explicit capillary force zero | production candidate |
| `explicit_balanced_csf` | face-balanced force only; jump disabled | diagnostic |
| `legacy_csf_jump` | current dual path | regression baseline |

The first implementation target is `projection_native_jump`, backed by a
shared `CapillaryGeometryState` and phase-labelled `J_sep`. This tests whether
the late T=8 cascade is caused by dual/inconsistent capillary insertion and
smooth-jump leakage. The implementation roadmap is tracked in [[WIKI-L-035]].

## Acceptance ladder

1. Static droplet: zero velocity, constant Laplace jump, small `R_BF`.
2. Perturbed circle: `E_k + sigma A_h` non-increasing.
3. Capillary wave: theoretical viscous decay and no single-side pin force.
4. Rising bubble short run: previous `t=0.5` gate remains stable.
5. Rising bubble T=8: no late `bf_residual -> ppe_rhs -> div_u -> KE`
   cascade.

## Paper placement

- Part 1 / governing equations: continuum energy law and capillary variational
  derivative.
- Part 1 / level-set chapter: reinitialisation is representation repair, not
  area minimisation.
- Part 2 / difference method: discrete chain-rule caveat and face-operator
  capillary contract.
- §5 time integration: capillary stiffness and semi-implicit alternatives.
- §8--§9 pressure/projection: projection-native pressure jump.
- §10 complete algorithm: `CapillaryGeometryState` in the step pipeline.
- §13 verification: static droplet, capillary wave, perturbed circle, rising
  bubble energy-budget gates.
