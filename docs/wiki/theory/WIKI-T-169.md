---
ref_id: WIKI-T-169
title: "Geometric Cell Fraction State-Space Reformulation"
domain: theory
status: PROPOSED
tags: [geometric_cell_fraction, clsvof, volume_conservation, common_flux, capillary_hodge, gpu]
sources:
  - path: artifacts/A/geometric_cell_fraction_theory_CHK-RA-GEOM-CELL-FRACTION-001.md
    description: "ResearchArchitect theory artifact for geometric cell fraction reformulation"
  - path: artifacts/A/ch14_reinit_volume_priority_theory_CHK-RA-REINIT-VOLUME-PRIORITY-001.md
    description: "Volume-first reinitialization theory motivating geometric fractions as long-term route"
  - path: artifacts/A/geometric_cell_fraction_formal_theory_CHK-RA-GEOM-CELL-FRACTION-002.md
    description: "Formal state-space, operator, invariant, and verification theory; adoption intentionally undecided"
  - path: artifacts/A/geometric_cell_fraction_residual_tasks_CHK-RA-GEOM-CELL-FRACTION-003.md
    description: "Residual task analysis, idea matrix, and deeper verification probes for capillary-ready reconstruction"
  - path: artifacts/A/geometric_cell_fraction_notation_CHK-RA-GEOM-CELL-FRACTION-004.md
    description: "Notation refinement from F_C/I_h to theta_C/Gamma_h"
  - path: artifacts/A/geometric_cell_fraction_bridge_projection_CHK-RA-GEOM-CELL-FRACTION-005.md
    description: "Theta-constrained continuous P1 trace bundle and capillary-work lift candidate"
  - path: artifacts/A/geometric_cell_fraction_projection_solver_theory_CHK-RA-GEOM-CELL-FRACTION-006.md
    description: "Implicit compatibility projection solver theory, residual probes, and fail-close gates"
  - path: artifacts/A/geometric_cell_fraction_discretization_theory_CHK-RA-GEOM-CELL-FRACTION-007.md
    description: "Metric cell-complex discretization, q-form phase carrier, Hodge adjoints, and capillary bundle work"
  - path: artifacts/A/geometric_cell_fraction_implementation_ux_CHK-RA-GEOM-CELL-FRACTION-008.md
    description: "Implementation layering, GPU-first route, and UX/YAML contract for geometric cell fractions"
depends_on:
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-160]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-T-164]]"
  - "[[WIKI-T-168]]"
consumers:
  - domain: theory
    usage: "Use as the target formulation when replacing diffuse/nodal phase volume by geometric cell fractions"
  - domain: code
    usage: "Do not implement geometric fractions as diagnostics only; migrate carrier, transport, capillary, and common-flux contracts together"
  - domain: paper
    usage: "Use when rewriting the CLS/VOF position of the method around a geometric conservative carrier"
compiled_by: ResearchArchitect
compiled_at: "2026-05-10"
---

# Geometric Cell Fraction State-Space Reformulation

## Notation Convention

Living notation uses Greek symbols for the geometric objects derived from the
`psi/phi` interface representation:

```text
theta_C  geometric liquid cell fraction / occupancy
Gamma_h  reconstructed discrete interface complex
phi      level-set gauge
psi      optional smoothed profile/gauge
```

Earlier artifacts used `F_C` for the cell fraction and `I_h` for the interface
complex.  Read them as predecessor notation for `theta_C` and `Gamma_h`.
`alpha_C` is intentionally avoided because `alpha` is already heavily used for
grid stretching and time-integration coefficients.

## Claim

Geometric cell fraction is a state-space reformulation, not a plotting or
diagnostic improvement.  The physical phase volume should become

```text
V_h(theta) = sum_C |C| theta_C,
theta_C = |C cap Omega_l| / |C|.
```

Then the sharp geometry volume and conservative finite-volume material volume
are the same discrete functional.

## Root Problem

The current CLS theory uses a diffuse/nodal indicator:

```text
psi = H_eps(-phi),
V_h^psi = sum_nodes psi_i W_i.
```

Sharp capillary geometry uses a different object:

```text
V_h^Gamma(phi) = |Omega_{l,h}(phi)|.
```

Trying to preserve both as hard constraints can make reinitialization
infeasible.  The correct cure is not wider brackets, damping, smoothing,
fallbacks, or case branches.  The cure is selecting one physical volume
functional.  Geometric cell fractions are the route where the sharp geometry
volume and the conservative mass volume become identical.

## Target State

```text
theta_C        geometric liquid cell fraction, hard conservative carrier
m_C(theta)     material mass
p/u_f      common-flux momentum or face velocity state
phi        reconstructed level-set gauge, not the material volume carrier
Gamma_h        reconstructed interface complex
```

Required identities:

```text
V_h(theta) = sum_C |C| theta_C = |Omega_{l,h}(Gamma_h)|,
S_h    = surface measure of Gamma_h,
rho_C  = rho_g + (rho_l-rho_g) theta_C.
```

Capillary, gravity, pressure projection, checkpoint/restart, and visualization
must read from this same state, or from declared adjoint maps of it.

## Working Theory Direction

This is not yet an adoption decision.  It is the coherent theory candidate that
must be developed and tested before production selection.

Use a geometric CLSVOF route:

1. `theta_C` is the hard material volume.
2. `phi` remains a smooth gauge for normals, curvature, HFE, and plots.
3. PLIC/cut geometry with level-set normals reconstructs a per-cell interface
   matching `theta_C`.
4. Geometric swept-volume fluxes update `theta_C`.
5. The common-flux momentum ledger uses that same phase flux.
6. Capillary force is the variational derivative of the same reconstructed
   surface and volume pair.

## Verification Gates

Before production implementation:

```text
G1: sum_C theta_C |C| equals reconstructed sharp volume.
G2: geometric swept-volume flux is conservative and bounded.
G3: static droplet Young--Laplace Hodge residual is zero in the chosen metric.
G4: nonconstant-curvature interfaces produce nonzero capillary drive.
G5: common-flux mass and momentum use the same phase flux.
G6: nonuniform, wall, and periodic geometry is counted in physical coordinates exactly once.
```

## Negative Knowledge

Do not accept:

- geometric fractions used only in plots;
- global mass correction after non-geometric transport;
- independent hard preservation of sharp volume and diffuse nodal mass;
- clipping without a conservative flux ledger;
- density from `theta_C` but capillary or gravity from diffuse `psi`;
- CCD/FCCD differentiation of discontinuous `theta_C` as a smooth field;
- visual long-run success before manufactured geometry and one-step flux gates.

## Formal Theory Layer

The theory is governed by a single-owner rule:

```text
theta_C owns material volume and density.
Gamma_h owns sharp surface and volume geometry.
phi/psi are derived gauges unless an equivalence proof promotes them.
```

The core maps are:

```text
A_h(Gamma_h)_C = |C cap Omega_l(Gamma_h)| / |C|              geometric fraction map
R_h(theta_C,g) -> Gamma_h                                    reconstruction map
Phi_h(Gamma_h) -> phi                                    gauge reconstruction
T_h(Gamma_h)w_f -> delta theta                               transport linearization
```

Required identities and contracts:

```text
sum_C |C| A_h(Gamma_h)_C = |Omega_{l,h}(Gamma_h)|
A_h(R_h(theta,g))_C = theta_C
0 <= theta_C <= 1
Phi_l is a geometric swept-volume flux
Phi_m = rho_g Phi_V + (rho_l-rho_g) Phi_l
M_f(theta) = Q_f rho_f(theta)
E_sigma = sigma S_h(Gamma_h)
a_sigma = -M_f(theta)^{-1} T_h(Gamma_h)^* dS_h
```

The largest unresolved theory problem is the capillary-ready reconstruction:
local volume-exact PLIC is a strong primitive for `theta_C` and fluxes, but it does
not by itself prove a globally smooth or variationally balanced capillary
surface.  Adoption should remain blocked until static Hodge balance and
dynamic nonconstant-curvature drive are both proven on the same `Gamma_h/theta_C`
geometry.

## Residual Task Refinement

The decisive obstruction is now sharper:

```text
theta_C determines material mass, but theta_C alone does not determine surface energy.
```

A half-cell manufactured probe shows the nonuniqueness.  In a unit square,
every central straight cut has `theta_C=1/2`, but the interface length is

```text
L(beta) = 1 / max(|sin beta|, |cos beta|),
```

which varies from `1` to `sqrt(2)`.  Therefore `E_sigma` is not a function of
`theta_C` alone unless a reconstruction rule, moments, gauge, or explicit
interface complex is part of the state.

The candidate directions are now separated into two nested theory targets:

```text
Target A: bridge theory
  dual state theta_C + phi_pred,
  PLIC/cut reconstruction using phi normals,
  local hard constraint A_h(Gamma_h)_C = theta_C,
  phi_new = signed_distance(Gamma_h),
  geometric swept-volume flux.

Target B: complete theory
  cut-cell complex K_h with subcell volumes, face apertures, interface facets,
  incidence matrices, pressure/capillary Hodge metrics.
```

Target A is the best next theory-development route because it keeps the
level-set gauge intuition while forcing material volume to be local and
geometric.  Target B is the long-term mathematically clean endpoint.

Remaining adoption blockers:

```text
R_h(theta,phi) local volume exactness plus interface continuity,
S_h(Gamma_h), dS_h, and T_h(Gamma_h) in one Hodge metric,
bounded geometric swept flux without hidden clipping,
common-flux mass/momentum from the same Phi_l,
nonuniform/periodic/wall quotient geometry,
gauge-retraction surface-work accounting,
checkpoint state for restart equivalence.
```

## Bridge Projection Candidate

The current best bridge theory is a compatibility bundle:

```text
B_h = { (theta,phi) :
        theta_C = A_h(Gamma(phi))_C on active mixed cells,
        full/empty sign and topology constraints hold }.
```

Here `theta_C` is the material coordinate and `phi` is the continuous P1 gauge.
The interface is not independent cellwise PLIC:

```text
Gamma_h = Gamma(phi).
```

This solves the continuity defect of independent PLIC while preserving local
cell fractions.

A local solvability probe computed the mixed-cell Jacobian

```text
J_A(phi) = d A_h(Gamma(phi)) / d phi_nodes
```

for manufactured ellipses.  The Jacobian had full row rank for N=8,12,16,24,32
with mixed constraints 16,24,32,48,64 respectively.  This supports a local
implicit-function theorem: for regular nondegenerate traces, nearby `theta`
fields can be represented by a continuous P1 gauge.

The proposed projection after transport is:

```text
min_phi  1/2 ||phi-phi^-||_W^2 + eta/2 ||Lphi-Lphi^-||^2
subject to A_h(Gamma(phi))_C = theta^-_C.
```

Capillary virtual work is defined by a bundle lift.  For a face virtual
velocity `w_f`,

```text
delta theta = T_theta(Gamma_h) w_f,
delta phi_pred = T_phi(phi) w_f,

L_B(w_f)
  = argmin_delta_phi ||delta_phi-delta_phi_pred||_W^2
    subject to J_A(phi) delta_phi = T_theta(Gamma_h) w_f,

r_sigma(w_f) = -sigma dS_h(phi)[L_B(w_f)],
a_sigma      = M_f(theta)^(-1) r_sigma.
```

This is the first concrete capillary-ready bridge candidate:

```text
theta_C supplies local material volume,
phi supplies continuous capillary geometry,
the compatibility constraint prevents two independent phases.
```

Projection surface-work must be recorded separately:

```text
Delta S_Pi = S_h(Gamma(phi^+)) - S_h(Gamma(phi^-_transported)).
```

It is not physical capillary work.

## Implicit Projection Solver Direction

The compatibility equation is solved as a fixed-stratum hard constrained
projection, not as an explicit per-cell formula:

```text
min_phi  1/2 ||phi-phi^-||_W^2 + eta/2 ||L(phi-phi^-)||^2
subject to A_h^S(Gamma(phi))_C = theta^-_C.
```

Linearized correction:

```text
r     = theta^- - A_h(Gamma(phi_k)),
J_A   = dA_h(Gamma(phi_k))/dphi,
W_eta = W + eta L^T L,

delta = W_eta^{-1} J_A^T
        (J_A W_eta^{-1} J_A^T)^{-1} r.
```

Manufactured probes clarified two hazards:

1. Small smooth perturbations can be corrected on a fixed stratum, but larger
   residuals quickly cross case boundaries.  A one-step linear solve at N=32
   reduced `amp=1e-5` residual from `4.44e-05` to `1.25e-07`, while
   `amp=3e-4` changed 20 cell cases and failed.
2. Constraint equations alone do not select a physical gauge.  For constant
   shift targets, residuals can be matched with no case changes, but the
   unconstrained minimum-norm correction is not the constant shift.  Therefore
   `phi^-`, `W_eta`, and smooth/eikonal gauge terms are part of the theory.

Clarified solver direction:

```text
fixed-stratum hard projection
+ predictor-based gauge selection
+ W_eta smoothness/eikonal metric
+ trust-region and sign-margin gates
+ Schur complement over mixed cells
+ explicit Delta S_Pi ledger.
```

Mandatory fail-close gates:

```text
rank(J_A),
condition estimate,
maximum admissible step before sign/case change,
hard compatibility residual after line search,
Delta S_Pi not hidden as capillary work.
```

## Discrete Cell-Complex Formulation

The production hard phase variable is the integrated liquid volume

```text
q_C = |C| theta_C,
theta_C = q_C / |C|.
```

`theta_C` remains the normalized user-facing fraction, but conservation,
compatibility residuals, and work pairings are written in `q` units.  This is
mandatory on nonuniform grids because equal `theta` changes do not represent
equal physical volumes.

Use an oriented metric cell complex:

```text
B      cell-face incidence,
H_C    diag(|C|),
M_f    face kinetic/mass Hodge,
D_h U  = H_C^{-1} B U.
```

The conservative phase update is:

```text
q^{n+1} = q^n - Delta t B Phi_l,
```

where `Phi_l` is a bounded geometric swept-volume flux of the same liquid set
represented by `Gamma_h`.  For periodic/wall closure:

```text
1^T B Phi_l = 0,
```

so global liquid volume conservation is topological.  Boundedness must be
proved by the swept-volume construction, not repaired by clipping.

The geometry map on a fixed regular stratum is:

```text
Q_h^S(phi)_C = |C cap Omega_l(Gamma(phi))|,
J_q = d Q_h^S(phi) / d phi.
```

The physical compatibility projection is:

```text
min_phi  1/2 ||phi-phi^-||_{W_eta}^2
subject to Q_h^S(phi)_C = q^-_C.
```

Linearized KKT form:

```text
[ W_eta   J_q^T ][ delta ] = [ W_eta delta_pred ]
[ J_q       0   ][ lambda]   [ r_q              ],

r_q = q^- - Q_h^S(phi_k).
```

Using `J_A=H_C^{-1}J_q` is acceptable for reporting normalized fractions, but
the hard projection and Schur complement must be based on `J_q`:

```text
S_q = J_q W_eta^{-1} J_q^T.
```

Pressure and capillary work use the same face Hodge.  With face variable `u`,

```text
<G_h p, u>_{M_f} = -p^T B u,
G_h p = -M_f^{-1} B^T p.
```

At a compatible state `q=Q_h(phi)`, capillary force is defined by bundle
virtual work:

```text
L_B(w)
  = argmin_delta_phi ||delta_phi-delta_phi_pred(w)||_{W_eta}^2
    subject to J_q delta_phi = T_q(Gamma_h) w,

r_sigma(w) = -sigma dS_h(phi)[L_B(w)],
a_sigma    = M_f^{-1} r_sigma.
```

The static droplet criterion is not the name of the shape.  It is the discrete
Young--Laplace range condition:

```text
sigma dS_h(delta_phi) + pi^T J_q delta_phi = 0
```

for admissible bundle variations.  If this holds, capillary force is pressure
exact and the projected drive is zero; if it does not hold, the interface has a
physical nonzero capillary drive.

CCD/FCCD/UCCD remain primary for smooth velocity, pressure, and gauge
derivatives.  They must not be applied to discontinuous `theta_C` as though it
were a smooth scalar.  The connection is through declared maps
`Q_h`, `J_q`, `T_q`, and `L_B`, not through hidden differentiation of the
phase fraction.

## Implementation And UX/YAML Direction

The implementation should not overload existing `psi` arrays with new meaning.
Introduce a typed geometric phase state:

```text
GeometricPhaseState:
  q        physical liquid cell volumes
  phi      continuous nodal gauge
  stratum  fixed-stratum case/sign data
  ledger   compatibility residuals, sign margins, Delta S_Pi
```

Recommended module split:

```text
src/twophase/geometry/
  cell_complex.py
  phase_state.py
  p1_cut_geometry.py
  p1_cut_jacobian.py
  swept_flux.py
  compatibility_projection.py
  bundle_capillary.py
  diagnostics.py
```

The production path should be GPU-first:

```text
struct-of-arrays geometry cache,
backend.xp arrays,
vectorized marching-squares case formulas,
sparse row tables for J_q and dS_h,
matrix-free Schur solve S_q lambda = J_q W_eta^{-1} J_q^T lambda,
no host/device transfer except explicit diagnostics.
```

The YAML front door should declare a state-space contract:

```yaml
interface:
  state_space:
    kind: geometric_cell_fraction
    conserved_variable: q
    normalized_view: theta
    gauge:
      variable: phi
      trace: p1_levelset
    compatibility:
      constraint: hard_cell_volume
      units: physical_volume
      projection:
        method: fixed_stratum_schur
        metric: screened_gauge_hodge
        fail_close: true
        trust_region: sign_margin
        residual_tolerance: 1.0e-11
```

The numerical stack must then be internally consistent:

```yaml
numerics:
  interface:
    transport:
      variable: q
      spatial: geometric_swept_volume
      boundedness: certified
      fail_close: true
  momentum:
    form: conservative_common_flux
    terms:
      surface_tension:
        source: bundle_virtual_work
        closed_interface:
          endpoint: geometric_cell_fraction
          residual_contract:
            metric: pressure_adjoint
            constraints: [cell_volume]
            fail_close: true
```

Parser gates must reject mixed-state configurations:

```text
geometric_cell_fraction with transport.variable=psi,
q transport without conservative_common_flux,
bundle_virtual_work with endpoint other than geometric_cell_fraction,
geometric_cell_fraction with old Ridge-Eikonal volume reinitialization,
fail_close=false,
boundedness repaired by clipping,
capillary from incompatible diffuse psi.
```

Compatibility projection is not reinitialization.  It should live under
`interface.state_space.compatibility.projection`; old `interface.reinitialization`
should be `algorithm: none` for the geometric route, or a temporary alias that
maps to the compatibility projection without invoking Ridge-Eikonal.

Required diagnostics:

```text
q_volume_conservation,
compatibility_residual_q,
stratum_margin,
projection_surface_work,
young_laplace_hodge_residual,
common_flux_phase_momentum_certificate.
```

Checkpoint UX should distinguish restartable continuation state from plot
artifacts:

```yaml
output:
  checkpoints:
    continuation_state: pre_step_full
    include:
      - q
      - phi
      - stratum
      - transport_stage_ledger
      - compatibility_projection_ledger
      - pressure_history
      - momentum_state
```

Activation order:

```text
schema fail-closed parse gate,
Q_h/S_h/J_q/dS_h geometry gates,
q compatibility projection gates,
bounded swept-volume/common-flux gates,
bundle capillary Hodge gates,
restart equivalence gates,
then ch14 YAML activation.
```
