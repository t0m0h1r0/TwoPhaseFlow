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
  - path: docs/memo/short_paper/SP-AO_geometric_cell_fraction_state_space.md
    description: "Implementation-ready short paper compiling the geometric cell-fraction state-space theory"
  - path: artifacts/A/ch14_ao_fast_volume_route_CHK-RA-CH14-AO-FASTVOL-001.md
    description: "AO-Fast active-stratum, approximate-candidate, GPU-PCG route for making SP-AO computationally viable"
  - path: artifacts/A/ch14_ao_dc_accuracy_theory_CHK-RA-CH14-AO-FASTVOL-002.md
    description: "AO-Fast fixed-stratum approximation-order contract and residual-monotone DC theory"
  - path: artifacts/A/paper_ch9_ao_fast_theory_CHK-RA-CH14-AO-FASTVOL-003.md
    description: "Paper Chapter 9 insertion of active-stratum approximation accuracy and residual-monotone DC conditions"
  - path: artifacts/A/ch14_ao_fast_algorithm_contract_CHK-RA-CH14-AO-FASTVOL-004.md
    description: "Implementation-ready AO-Fast active geometry acceleration contract, GPU kernel plan, ledger counters, and proof obligations"
  - path: artifacts/A/ch14_ao_yaml_fallback_policy_CHK-RA-CH14-AO-FASTVOL-005.md
    description: "AO-Fast explicit fallback YAML/UX policy preserving fail-close semantics"
  - path: artifacts/A/ch14_ao_fast_design_policy_CHK-RA-CH14-AO-FASTVOL-006.md
    description: "AO-Fast implementation design policy and reuse plan for the direct AO branch"
  - path: artifacts/A/ch14_ao_gpu_import_gate_CHK-RA-CH14-AO-FASTVOL-007.md
    description: "GPU admission gate for importing direct-AO components into AO-Fast"
  - path: artifacts/A/ch14_ao_direct_branch_knowledge_salvage_CHK-RA-CH14-AO-FASTVOL-008.md
    description: "Knowledge salvage packet for retiring the direct dense-AO branch"
  - path: artifacts/A/ch14_ao_fast_preimplementation_design_CHK-RA-CH14-AO-FASTVOL-009.md
    description: "AO-Fast preimplementation design gate: module blueprint, active data shapes, GPU contract, fail-close state machine, validation ladder, and first coding ticket"
  - path: artifacts/A/review_ch14_ao_fast_preimplementation_design_CHK-RA-CH14-AO-FASTVOL-010.md
    description: "Contrarian review of AO-Fast preimplementation design; identifies blockers before production implementation"
  - path: artifacts/A/ch14_ao_fast_design_repair_CHK-RA-CH14-AO-FASTVOL-011.md
    description: "Repair of all contrarian-review findings before AO-Fast implementation"
  - path: artifacts/A/ch14_ao_fast_complexity_audit_CHK-RA-CH14-AO-FASTVOL-012.md
    description: "Complexity audit ensuring AO-Fast repairs do not reintroduce full-grid runtime work"
  - path: artifacts/A/ch14_ao_fast_precode_contrarian_loop_CHK-RA-CH14-AO-FASTVOL-013.md
    description: "Pre-code adversarial review loop and repairs until no major findings remain"
  - path: artifacts/A/ch14_ao_fast_c1_implementation_CHK-RA-CH14-AO-FASTVOL-014.md
    description: "AO-Fast C1 dense oracle, manifest, governance, parser skeleton, and remote validation"
  - path: artifacts/A/ch14_ao_fast_active_core_CHK-RA-CH14-AO-FASTVOL-016.md
    description: "AO-Fast C2-C7 active table, active kernels, matrix-free Schur, PCG floor, and exact active projection core"
  - path: artifacts/A/ch14_ao_fast_runtime_ux_gate_CHK-RA-CH14-AO-FASTVOL-017.md
    description: "AO-Fast C8 YAML/UX gate: valid geometric configs build, solver runtime remains fail-closed"
  - path: artifacts/A/ch14_ao_fast_runtime_contract_adapter_CHK-RA-CH14-AO-FASTVOL-018.md
    description: "AO-Fast C9 disabled runtime contract adapter for q/theta/phi handoff, checkpoint arrays, and bundle capillary contract"
  - path: artifacts/A/ch14_ao_fast_review_hardening_CHK-RA-CH14-AO-FASTVOL-019.md
    description: "AO-Fast review hardening: checkpoint cell/node split, mixed-state YAML rejection, support-stream budget enforcement, and empty-support no-op ledger"
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

The production route is AO-Fast, not dense direct AO.  It keeps compact
active-stratum tables for mixed/cut cells plus a one-face halo, uses frozen
linearized geometry only as a candidate generator, and accepts a step only
after exact active-stratum `Q_h/S_h` residual, sign-margin, and
projection-work gates pass.  Compatibility projection is solved on the active
interface graph by matrix-free PCG with warm starts, diagonal/component-block
Jacobi preconditioning, and optional connected-component deflation, targeting
`O(k |A|)` work rather than full-domain `O(k |C_h|)` geometry and Schur work.

Approximation accuracy must be declared locally.  With
`beta_C=||delta phi||_{infty,C}/min(gamma_C,m_C)` on a fixed regular stratum,
first-order frozen geometry has `O(beta_C^2)` local `Q_h/S_h` remainders, and
any second-order secant/Hessian candidate must demonstrate `O(beta_C^3)` before
promotion.  Approximation order never replaces exact acceptance in physical
`q` units.

DC is admissible as a geometry compatibility iteration only when it is
residual-monotone for the exact residual `R(phi)=Q_h^S(phi)-q^-`.  The frozen
active Schur inverse may be used as a cheap defect-correction operator, with
the step length chosen by an on-device residual decrease test.  Fixed-count DC,
clipping, or relaxed volume constraints remain forbidden.

The implementation contract is an active-geometry acceleration route: detect
dirty sign/case/crossing/metric/ownership rows, reuse compact active-table rows
outside the dirty halo, recompute exact `Q/S/J/dS` only on the active graph,
and expose `|A|`, `|dirty|`, refreshed-cell count, kernel-launch count, and
host-transfer count in the ledger.  The YAML must name the primary active
solver.  Frozen active linearization or residual-monotone DC may be
proposal-only accelerators, but rejection discards the proposal and does not
change solver family.  PCG/Newton is either the declared primary solver or a
declared `explicit_chain` fallback target.  There is no implicit DC-to-PCG
recovery.  The speedup is credited to active geometry, incremental cache
refresh, and device-resident fused kernels, not to DC itself.

The direct AO branch `codex/ra-ch14-osc-sharp-volume-20260510` should be used
as a dense reference implementation and source of formulas, not as the
production compute loop.  Reusable pieces are the P1 cut geometry algebra,
fixed-stratum derivative formulas, `MetricCellComplex` cache, q/theta/phi phase
state, fail-close parser gates, capillary face-Hodge runtime contracts, and
manufactured tests.  The dense compatibility projection and dense line search
remain oracle/debug code; AO-Fast rewrites them into `ActiveGeometryTable`
rows, dirty plus one-face halo refresh, and device-resident active Schur
operators.  Dense reference mode is an oracle/debug path, not a runtime
fallback; default production stays `active_cached` plus fail-close.

Importing from the direct AO branch is GPU-gated.  Each imported symbol must be
classified as `oracle_only`, `gpu_production`, or `reject`.  Production
admission requires backend-native arrays, struct-of-arrays active storage,
fused active-row kernels, device-side reductions for residuals and acceptance,
metric-cache reuse, preallocated work buffers, and no inner-loop host transfer
inside CG/Newton/DC/line search.  A component that fails this gate remains an
oracle/test helper; it is not a dense runtime fallback.

The direct branch also contributed non-code knowledge that must survive branch
retirement.  Parser gates require explicit `state_space.kind` and reject
diffuse routes carrying `q/theta`.  Geometry gates preserve complement volume,
physical nonuniform-cell measures, periodic quotient semantics, and reject
degenerate nodal sign strata.  Projection gates operate in physical `q` units
with sign-margin line search and fail close on full/empty-cell target changes.
Swept transport gates require bounded q flux, declared wall/periodic closure,
and common mass flux from the same `Phi_l/Phi_V` arrays.  Capillary gates are
face-Hodge/Riesz work identities with periodic seam splitting and component
reaction orthogonality.  Runtime gates prevent legacy `psi` transport after
geometric parser acceptance and validate checkpoint face-history shapes at load
time.  Diagnostic knowledge also matters: `pressure_hodge` is stricter than a
scalar pressure plot and may fail closed; canonical plots should use the scalar
gauge pressure unless the Hodge representation is explicitly under test.
Finally, the sharp-volume Ridge-Eikonal rerun showed a real two-measure
obstruction: P1 sharp area and nodal diffuse mass can have no simultaneous
solution under a fixed interface, so that route is not an AO fallback.

Before code development, AO-Fast has a preimplementation design gate.  The gate
fixes module boundaries (`dense_reference`, `active_table`, `active_kernels`,
`active_projection`, import manifest, parser, runtime adapters), exact active
SoA array shapes, direct-branch symbol classifications, GPU no-inner-D2H
requirements, numerical tolerance ownership, fail-close state transitions, and
the validation ladder from dense oracle import through chapter-14 smoke YAML.
The first coding ticket is therefore dense oracle plus import manifest only;
runtime activation waits until active geometry, GPU, projection, parser, and
adapter gates pass.

A contrarian review of that gate found blockers, now repaired before
production implementation.  AO-Fast uses the constraint support `A_q`, the union
of current mixed cells, previous mixed cells, swept-flux-touched cells,
target-mixed cells with `0<q^-_C<|C|`, and the required halo.  Active rows own
`q_target_A`, `cell_measure_A`, target-state codes, flux-touched masks, and
origin masks.  The import manifest uses only the closed classification enum
`oracle_only/gpu_production/reject` plus a separate migration status.  Physical
q tolerances are unit-invariant, PCG gates record rank/conditioning/stop reason,
topology changes use bounded active-set epochs or fail close, and GPU speed
gates have pass/fail thresholds, not counters alone.

A complexity audit then clarified that the repaired `A_q` design is acceptable
only if target and flux support are compact streams.  Production AO-Fast must
not scan all cells each timestep to discover `target_mixed_cells`, must not
define `flux_touched_cells` from every nonzero velocity face, and must keep
rank/conditioning gates as cheap active-row or Krylov/Ritz estimates.  Dense
oracle comparison, full-grid scans, and dense Schur eigensolves remain
initialization, validation, debug, or declared-degenerate work, not ordinary
runtime.

The final pre-code contrarian pass tightened the remaining hidden-heavy paths:
support compaction is device-side over compact state-changing candidate
streams, not full-grid `where/nonzero`; `flux_touched_cells` excludes irrelevant
bulk full/full phase exchange; active/support buffers require declared capacity
and fail-close on overrun; PCG separates `tau_cg_target` from the attainable
roundoff floor; production conditioning gates are fail-close, not
diagnostic-only.

The C2-C7 implementation now materializes that active core without enabling
chapter-14 runtime YAMLs.  `ActiveGeometryTable` stores compact SoA rows for
`cell_ids_A`, `node_ids_A`, current `Q_h/S_h`, `q_target_A`, `target_theta_A`,
target-state codes, halo/dirty/flux/origin masks, owner epochs, and metric
keys.  `refresh_active_geometry_2d` computes active P1 `Q_h`, `S_h`, `J_q`, and
`dS_h` directly from supplied active cell ids, with dense scans confined to
ledgered debug/oracle builders.  The matrix-free active Schur layer applies
`J`, `J^T`, and `J J^T` without dense Schur assembly, checks adjointness, and
keeps PCG floor semantics fail-closed.  The active projection loop accepts only
exact recomputed active `Q_h` residuals on a fixed sign stratum; active-set
epoch changes remain an outer fail-close/runtime-adapter responsibility.  GPU
tables remain device arrays; the temporary unfused PCG control loop is
intentionally disabled on GPU rather than silently syncing inside the loop.

C8 moves the fail-close boundary from config construction to solver
construction.  A complete `geometric_cell_fraction` YAML may now build an
`ExperimentConfig` if it uses `q_cell_fraction` tracking, `geometric_swept_volume`
transport, `bundle_virtual_work`, `endpoint: geometric_cell_fraction`,
`constraints: [cell_volume]`, `algorithm: none`, and the active-cached GPU
projection contract.  `NSSolverBuilder` still rejects that config before
building runtime options, so the UX can validate the intended AO-Fast YAML while
chapter-14 execution remains blocked until the runtime adapter/checkpoint/smoke
gates pass.

C9 introduces the disabled runtime contract adapter.  Before raising the
fail-close runtime error, `NSSolverBuilder` now validates that the parsed config
still carries the intended q/theta/phi handoff, `q_cell_fraction` tracking,
`geometric_swept_volume` transport, `bundle_virtual_work` with
`endpoint: geometric_cell_fraction`, `constraints: [cell_volume]`, and
`pressure_component_hodge`.  The same module defines the continuation
checkpoint array contract (`state/q`, `state/theta`, `state/phi`,
`state/stratum/case_code`, transport/projection ledger epochs) and validates
pressure/projected face-history component shapes as a test-only gate.  This
found and fixed a C8 parser gap: `bundle_virtual_work` must parse and preserve
the closed-interface contract, not fall back to the legacy `conservative_psi`
default.

The C9 review hardening fixes four contract holes before runtime activation.
Continuation checkpoints distinguish cell cochains from node gauges:
`state/q`, `state/theta`, and `state/stratum/case_code` have cell shape
`(nx, ny)`, `state/phi` has P1 node shape `(nx+1, ny+1)`, and pressure/projected
face histories have staggered shapes `(nx, ny+1)` and `(nx+1, ny)`.  The
legacy/default diffuse front door now rejects geometric capillary declarations
such as `bundle_virtual_work`, `endpoint: geometric_cell_fraction`, or
`constraints: [cell_volume]` unless the geometric state space is explicit.
Compact support construction enforces `max_support_stream_ratio` before halo
expansion, enforces active capacity after halo expansion, and rejects device
streams in the temporary host compactor so there is no hidden D2H path under a
GPU contract.  Empty active support is a valid no-op projection state with an
explicit `empty_active_support` ledger, not an empty reduction crash.

CCD/DCCD/FCCD/UCCD remain useful on the smooth side of the split: gauge
prediction, screened gauge metric `W_eta`, face-state reconstruction,
pressure-adjoint work pairs, and smooth residual diagnostics.  They remain
forbidden as derivatives of the discontinuous `theta_C` carrier or as
substitutes for `Q_h`, `J_q`, `T_q`, and `dS_h`.

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
        implementation: active_cached
        dense_reference: test_only
        gpu_contract:
          required: true
          active_storage: struct_of_arrays
          inner_host_transfers: forbidden
          dense_runtime_fallback: forbidden
          record_kernel_counters: true
        method: fixed_stratum_schur
        metric: screened_gauge_hodge
        fail_close: true
        trust_region: sign_margin
        residual_tolerance: 1.0e-11
        condition_gate: fail_close
        support_budget:
          max_active_ratio: 0.25
          max_support_stream_ratio: 0.25
          max_epoch_growth_ratio: 1.5
          on_overrun: fail_close
        solver:
          primary: active_pcg_newton
          accelerators:
            dc_candidate:
              enabled: true
              role: proposal_only
              on_reject: discard_candidate
          fallback:
            policy: none
```

Fallback may be enabled only as an explicit solver chain:

```yaml
solver:
  primary: residual_monotone_dc
  fallback:
    policy: explicit_chain
    chain:
      - from: residual_monotone_dc
        to: active_pcg_newton
        triggers: [no_exact_residual_decrease, trust_region_exhausted]
        record_as: dc_to_pcg_declared_fallback
```

The numerical stack must then be internally consistent:

```yaml
numerics:
  interface:
    transport:
      variable: q
      spatial: geometric_swept_volume
      time_integrator: tvd_rk3
      boundedness: certified
      fail_close: true
    tracking:
      primary: q
  momentum:
    form: conservative_common_flux
    terms:
      surface_tension:
        gradient: none
        formulation: pressure_jump
        source: bundle_virtual_work
        closed_interface:
          endpoint: geometric_cell_fraction
          residual_contract:
            metric: pressure_adjoint
            constraints: [cell_volume]
            fail_close: true
  projection:
    poisson:
      operator:
        discretization: fccd
        coefficient: phase_separated
        interface_coupling: affine_jump
        pressure_force_contract: variational_adjoint
        scalar_operator_pairing: variational_operator
        capillary_reaction_projection: pressure_component_hodge
```

Parser gates must reject mixed-state configurations:

```text
geometric_cell_fraction with transport.variable=psi,
q transport without conservative_common_flux,
bundle_virtual_work with endpoint other than geometric_cell_fraction,
geometric_cell_fraction with old Ridge-Eikonal volume reinitialization,
fail_close=false,
dense_reference/reference_dense used as an implicit runtime fallback,
gpu_contract.required=false for production geometric_cell_fraction,
active_cached with inner_host_transfers other than forbidden,
condition_gate diagnostic-only in production geometric_cell_fraction,
implicit fallback such as auto, try_next, best_effort, or on_failure,
fallback.policy=explicit_chain without from/to/triggers/record_as,
accelerator rejection that switches primary solver family,
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
