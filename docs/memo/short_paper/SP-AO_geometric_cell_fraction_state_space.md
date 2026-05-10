# SP-AO: Geometric Cell-Fraction State Space

**Status**: ACTIVE theory and implementation specification
**Date**: 2026-05-11
**Scope**: volume-first two-phase interface state space, geometric
cell-fraction discretization, compatibility projection, bundle capillarity,
common-flux integration, GPU-first fast implementation, and YAML contract
**Companion papers**: SP-AF, SP-AI, SP-AJ, SP-AK, SP-AN

## Abstract

The recent reinitialization and capillary investigations exposed a structural
problem: the numerical method had multiple discrete notions of phase volume.
Diffuse `psi` mass, sharp interface volume, reinitialization volume brackets,
and capillary geometry could each be locally sensible, yet mutually
incompatible.  That is why a method could preserve one volume measure while
failing a sharp-volume bracket, or balance a static droplet while deleting the
physical drive of a non-equilibrium interface.

This short paper records the replacement state space.  The physical material
carrier is the geometric liquid cell volume

```text
q_C = |C| theta_C,
```

where `theta_C` is only the normalized fraction view.  The sharp capillary
geometry is the interface complex `Gamma_h = Gamma(phi)` induced by a
continuous gauge `phi`.  The two are tied by a hard local compatibility
constraint:

```text
Q_h(phi)_C = |C cap Omega_l(Gamma(phi))| = q_C.
```

Transport advances `q` by a bounded geometric swept-volume flux.  Capillary
force is not a curvature patch; it is the virtual-work derivative of the same
geometry, lifted through the compatibility bundle and represented in the same
face Hodge metric as the pressure projection.  Compatibility projection is not
Ridge-Eikonal reinitialization: it changes only the gauge needed to represent
the already-conserved material volume, and any surface-energy change it causes
is recorded separately as projection work.

The document is written so that implementation can start later without
reopening the theory: it specifies the discrete objects, module boundaries,
YAML contract, fail-close rules, GPU path, validation ladder, and negative
knowledge.

## 1. Why A New State Space Is Needed

The continuous material law is not preservation of a smoothed profile.  It is
transport of the sharp material region:

```text
partial_t chi_l + div(chi_l u) = 0.
```

The continuous surface tension law is the variation of one sharp surface:

```text
E_sigma(Gamma) = sigma |Gamma|.
```

The same interface determines both volume and surface energy:

```text
delta V       = integral_Gamma w_n dS,
delta E_sigma = - integral_Gamma sigma kappa w_n dS.
```

A discrete scheme that preserves one volume measure while differentiating
another surface measure is not a discretization of this continuous structure.
It is a two-measure model.

The observed failure modes follow from this:

```text
sharp-volume reinit bracket failure:
  diffuse/gauge correction cannot satisfy the requested sharp-volume state.

range-projected capillary zero-drive:
  pressure-range removal deletes the divergence-free capillary drive of
  non-equilibrium geometry.

static droplet velocity ring:
  the capillary covector is not exactly pressure-exact in the selected
  discrete Hodge metric.

nonuniform-volume confusion:
  normalized fractions are treated as physical volume without |C| weighting.
```

These are not independent bugs.  They are symptoms of missing state ownership.

## 2. Single-Owner Rule

The new state space uses a strict ownership split:

```text
q_C        owns material volume and density.
Gamma_h    owns sharp surface geometry.
phi        owns the continuous gauge representation of Gamma_h.
psi        is optional visualization or legacy bridge state.
```

The normalized fraction is:

```text
theta_C = q_C / |C|.
```

Density is the affine image of the same material owner:

```text
rho_C(q) = rho_g + (rho_l - rho_g) q_C / |C|.
```

Rejected immediately:

```text
density from q but capillarity from incompatible psi,
capillarity from phi but phase transport from an unrelated fraction,
global mass correction after non-geometric transport,
clipping q after transport and calling the result conservative.
```

## 3. Discrete Cell Complex

Let the computational mesh be an oriented metric cell complex:

```text
C_h      cells C
F_h      oriented faces f
N_h      gauge nodes v
B        cell-face incidence matrix
|C|      physical cell area/volume
|f|      physical face length/area
H_C      diag(|C|)
M_f      face kinetic/mass Hodge
W_v      nodal gauge Hodge
```

The finite-volume divergence is:

```text
D_h U = H_C^{-1} B U.
```

The conservative phase update is written in integrated volume units:

```text
q^{n+1} = q^n - Delta t B Phi_l.
```

For periodic and wall-closed phase transport:

```text
1^T B Phi_l = 0,
```

so global liquid volume conservation is topological.  Metrics and grid
stretching do not appear in this identity until the normalized view
`theta=H_C^{-1}q` is requested.

### Periodic and wall domains

Periodic boundaries are quotient complexes:

```text
periodic nodes are identified in phi,
periodic faces are one oriented flux degree of freedom,
surface and volume are counted once at the seam.
```

Impermeable walls enforce:

```text
Phi_l = 0 on wall phase faces.
```

If a contact-angle law is introduced later, it must enter as a boundary term
in `dS_h`, not as a curvature post-processing correction.

### Nonuniform grids

All geometry is physical geometry:

```text
q_C, |C|, |f|, cut areas, swept volumes, and surface lengths
```

are computed after the mesh mapping.  A sum over `theta_C` is never a physical
volume unless multiplied by `|C|`.

## 4. Fixed-Stratum Geometry Map

Use a continuous P1/Q1 gauge `phi` on mesh nodes:

```text
Omega_l(phi) = { x : phi_h(x) < 0 },
Gamma(phi)   = { x : phi_h(x) = 0 }.
```

On a regular fixed stratum `S`, the sign pattern and crossing pattern are
fixed.  The geometry maps are:

```text
Q_h^S(phi)_C = |C cap Omega_l(Gamma(phi))|,
A_h^S(phi)_C = Q_h^S(phi)_C / |C|,
S_h^S(phi)   = |Gamma(phi)|.
```

The compatibility Jacobian is:

```text
J_q(phi) = d Q_h^S(phi) / d phi.
```

For `Omega_l={phi<0}`, the shape derivative is:

```text
delta q_C
  = - integral_{Gamma(phi) cap C} delta phi / |grad phi| dS.
```

For a P1 trace this is exact on each segment because `delta phi` is linear and
`grad phi` is constant per subcell.  Therefore each row of `J_q` touches only
the local trace nodes.

The normalized derivative

```text
J_A = H_C^{-1} J_q
```

is useful for reports and plots.  It is not the hard physical constraint
operator on nonuniform grids.

## 5. Compatibility Bundle

The geometric cell-fraction state is the bundle:

```text
B_h = { (q, phi) :
        Q_h^S(phi)_C = q_C on active cells,
        sign/topology inequalities hold,
        wall/periodic quotient constraints hold }.
```

After transport:

```text
q^-    conservative transported material volume,
phi^-  transported or predicted gauge.
```

The projection is:

```text
min_phi  1/2 ||phi - phi^-||_{W_eta}^2
subject to Q_h^S(phi)_C = q^-_C.
```

with

```text
W_eta = W_v + eta L^T H_L L.
```

The linearized step is:

```text
r_q = q^- - Q_h^S(phi_k),

[ W_eta   J_q^T ][ delta ] = [ W_eta delta_pred ]
[ J_q       0   ][ lambda]   [ r_q              ].
```

Schur form:

```text
S_q lambda = J_q delta_pred - r_q,
S_q = J_q W_eta^{-1} J_q^T,
delta = delta_pred - W_eta^{-1} J_q^T lambda.
```

Projection gates:

```text
rank and conditioning of J_q/S_q,
maximum line-search step before sign or case change,
hard residual ||Q_h(phi^+) - q^-||,
boundedness 0 <= q_C <= |C|,
projection surface work Delta S_Pi.
```

If a gate fails, the solver must fail close or enter a declared topology
route.  It must not silently relax the hard volume constraint.

## 6. Projection Work Is Not Capillary Work

The projection can change surface length while holding `q` fixed:

```text
Delta S_Pi = S_h(Gamma(phi^+)) - S_h(Gamma(phi^-)).
```

This is gauge/projection work.  It is not physical capillary work.  It belongs
in a diagnostic ledger and may be a fail-close gate if large.

Physical capillary work is evaluated before or within the physical transport
variation, not by charging the gauge projection to surface tension.

## 7. Geometric Transport And Common Flux

The transport variable is `q`, and the flux is a swept liquid volume:

```text
q^{n+1} = q^n - Delta t B Phi_l(Gamma_h,u).
```

`Phi_l` is not `psi_face * u_face`.  It is the measure of the swept liquid set
through each face.

The common mass flux is derived from the same phase flux:

```text
Phi_m = rho_g Phi_V + (rho_l - rho_g) Phi_l,
```

where `Phi_V` is the total volume flux.  Momentum remap uses this `Phi_m`.
This keeps phase, density, and momentum in one ledger.

Boundedness is a theorem of the flux construction:

```text
0 <= q_C^{n+1} <= |C|.
```

The accepted implementation must provide a certificate.  Clipping after the
update is not a certificate.

## 8. Pressure Hodge And Capillary Bundle Work

For face variable `u_f` with kinetic inner product

```text
<u,v>_M = u^T M_f v,
```

the pressure gradient is the negative Hodge adjoint of the finite-volume
divergence:

```text
<G_h p, u>_{M_f} = -p^T B u,
G_h p = -M_f^{-1} B^T p.
```

Capillary force must return a face covector in this same metric.  At a
compatible state:

```text
q = Q_h(phi),
E_sigma(phi) = sigma S_h(phi).
```

A virtual face motion `w` changes phase volume through:

```text
delta q = T_q(Gamma_h) w.
```

Lift this variation to the compatible gauge:

```text
L_B(w)
  = argmin_delta_phi ||delta_phi - delta_phi_pred(w)||_{W_eta}^2
    subject to J_q delta_phi = T_q(Gamma_h) w.
```

Then the capillary covector is:

```text
r_sigma(w) = - sigma dS_h(phi)[L_B(w)].
```

The acceleration is the Riesz representative:

```text
a_sigma = M_f^{-1} r_sigma.
```

This route replaces hand-built curvature forcing.  The same `Q_h`, `J_q`,
`T_q`, `dS_h`, and `M_f` define both static balance and dynamic drive.

### Young--Laplace range test

A static equilibrium is discrete Young--Laplace if there exists a pressure
multiplier `pi_C` such that:

```text
sigma dS_h(delta_phi) + pi^T J_q delta_phi = 0
```

for all admissible bundle variations.  This is the shape-independent criterion
for zero projected capillary drive.

If the condition does not hold, the interface has physical nonzero capillary
drive.  No code path may branch on "circle", "ellipse", or benchmark name.

## 9. CCD/FCCD/UCCD Orthogonality

The geometric phase variable is discontinuous by construction:

```text
q_C, theta_C are finite-volume cochains.
```

They must not be differentiated by CCD, FCCD, UCCD, or DCCD as if they were
smooth scalar fields.

The CCD-family role remains primary for smooth fields:

```text
velocity,
pressure,
gauge prediction phi,
smooth diagnostics,
manufactured smooth probes.
```

The geometric finite-volume role is:

```text
phase material transport,
local volume conservation,
boundedness,
common mass flux,
compatibility constraints.
```

The connection is only through declared maps:

```text
Q_h, J_q, T_q, L_B.
```

This is a de Rham-style split, not a fallback from CCD.

## 10. Implementation Architecture

Do not retrofit this by reinterpreting existing `psi` arrays.  Add a new
geometry state layer:

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

Suggested responsibilities:

```text
cell_complex.py
  MetricCellComplex, incidence B, cell/face physical measures,
  periodic quotient, wall closure.

phase_state.py
  GeometricPhaseState(q, phi, stratum, ledger), theta view,
  density view, compatibility status.

p1_cut_geometry.py
  fixed-stratum Q_h, A_h, S_h, case codes, sign margins.

p1_cut_jacobian.py
  J_q and dS_h assembly.

swept_flux.py
  bounded geometric Phi_l and boundedness certificates.

compatibility_projection.py
  KKT/Schur hard projection Q_h(phi)=q, trust-region line search,
  fail-close gates, Delta S_Pi ledger.

bundle_capillary.py
  T_q, L_B, r_sigma, M_f Riesz coupling.

diagnostics.py
  q-volume drift, compatibility residual, stratum margin,
  projection work, Young-Laplace Hodge residual.
```

Simulation adapters:

```text
src/twophase/simulation/geometric_phase_runtime.py
src/twophase/simulation/geometric_transport_ledger.py
src/twophase/simulation/visualization/geometric_phase_fields.py
```

These adapt the geometry package to the existing runner, conservative
common-flux transport, checkpoint, and plotting systems.

## 11. GPU-First Design

The public kernels should be backend-native from the beginning:

```text
xp arrays,
struct-of-arrays geometry cache,
integer case tables on device,
vectorized crossing and area formulas,
sparse row tables for J_q and dS_h,
matrix-free Schur operators,
explicit host transfer only at diagnostics.
```

Geometry cache:

```text
mixed_cell_indices
case_code
edge_crossing_lambda
segment_endpoints
Q_h(phi)_C
S_h contributions
J_q row/column/value arrays
dS_h nodal covector contributions
sign_margin
```

Projection operators:

```text
apply_Jq(delta_phi)
apply_JqT(lambda_cells)
apply_Weta_inv(rhs)
apply_Sq(lambda) = J_q W_eta^{-1} J_q^T lambda
```

Initial solve:

```text
matrix-free CG on S_q,
row-norm or Jacobi preconditioner,
line search against sign/case margins.
```

CPU reference routines are allowed for manufactured tests, but they must not
be the only route if the feature is promoted to production.

### AO-Fast production route

The direct reading of the equations is too expensive for production if every
time step rebuilds full-grid cut geometry, full-grid Jacobian tables, and a
full-cell Schur solve.  The accepted production route is therefore a certified
active-stratum method:

```text
A = mixed/cut cells plus a one-face halo,
Q_A, S_A, J_A, dS_A, T_A, M_A on compact active tables,
full/empty cells as state flags,
periodic quotient and wall ownership resolved while building A.
```

The theory split from Section 9 remains binding.  CCD/DCCD/FCCD/UCCD are
valuable on smooth objects such as the gauge predictor `phi^-`, the screened
metric `W_eta`, face-state reconstruction, pressure-adjoint work pairs, and
smooth residual diagnostics.  They must not be used to differentiate the
discontinuous cell fraction `theta_C` or to replace the geometric maps
`Q_h`, `J_q`, `T_q`, and `dS_h`.

Within a fixed regular stratum, fast kernels may use frozen linearized
geometry:

```text
Q_h(phi + delta phi) = Q_h(phi) + J_q delta phi + O(delta phi^2),
dS_h(phi + delta phi) = dS_h(phi) + local secant/Hessian candidate,
T_q(phi + delta phi) = T_q(phi) + higher-order remainder.
```

The accuracy claim is part of the contract.  On a fixed stratum, let

```text
gamma_C = min crossing-edge |phi_b - phi_a|,
m_C     = min node |phi_v|,
beta_C  = ||delta phi||_{infty,C} / min(gamma_C, m_C).
```

For `beta_C <= beta_* < 1`, the P1 cut maps are smooth in the local nodal
values and the first-order frozen candidate satisfies

```text
|Q_h^S(phi+delta phi)_C - Q_h^S(phi)_C - J_q,C delta phi_C|
  <= C_Q |C| beta_C^2,

|S_h^S(phi+delta phi)_C - S_h^S(phi)_C - dS_C delta phi_C|
  <= C_S |Gamma_C| beta_C^2.
```

The constants depend only on the fixed case table, aspect-ratio bounds, and
the lower crossing margin; they must not depend on the global grid size.  If a
second-order local secant/Hessian candidate is implemented, its advertised
accuracy is `O(beta_C^3)` on the same stratum and must be verified against the
exact active-stratum recomputation.  These are proposal accuracies only; the
committed state is judged by exact physical-volume residuals in `q` units.

These approximations are candidate generators, not the contract.  Acceptance
must recompute the exact active-stratum `Q_h` and `S_h` and check the physical
residual, sign/case margins, and projection-work ledger before committing the
state.  A failed exact check refreshes the stratum once; a repeated failure
fails closed or enters an explicit topology route.

The compatibility projection is solved on the active interface graph:

```text
S_A lambda = J_A W_eta^{-1} J_A^T lambda,
```

using matrix-free PCG, previous-step warm starts, diagonal plus component-block
Jacobi preconditioning, and optional connected-component deflation.  The
iteration tolerance is inexact-Newton style and is bounded by the downstream
exact gate, e.g.

```text
tau_cg <= min(0.1 tau_q, c_work tau_surface, c_round sqrt(|A|) eps).
```

Defect correction is admissible when it is a residual-monotone nonlinear
compatibility iteration.  Define the exact active residual

```text
R(phi) = Q_h^S(phi) - q^-.
```

Let `P_0` be a cheap frozen active-Schur inverse or preconditioned approximate
inverse.  A DC candidate is

```text
delta phi_DC = - P_0 R(phi_k),
phi_trial(alpha) = phi_k + alpha delta phi_DC.
```

The accepted `alpha` is chosen by an on-device line search or scalar quadratic
model to decrease the exact residual ledger:

```text
||R(phi_trial(alpha))||_{H_C^{-1}} < ||R(phi_k)||_{H_C^{-1}},
```

while also preserving sign/case margins and projection-work gates.  Fixed-count
DC without residual decrease is not an AO-Fast method.  If DC stagnates, the
solver escalates to the active PCG/Newton solve or fails closed; it must not
repair the state by clipping `q` or relaxing the hard volume constraint.

The target complexity is `O(k |A|)` per Newton update, where `|A|` is the
number of active interface-band cells.  The rejected production complexity is
`O(k |C_h|)` full-domain cut-geometry and Schur work per line-search trial.

GPU execution must keep all active tables and Krylov vectors on device.  Host
transfer is limited to explicit ledger scalars after an accepted outer
iteration.  In particular, no `.get()`, `asnumpy`, Python list materialization,
or scalar D2H synchronization belongs inside CG iteration control.

## 12. YAML Contract

The front door is a state-space declaration:

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
        condition_gate: diagnostic
      ledger:
        record_delta_surface: true
        record_residuals: true
```

The compatible numerical stack:

```yaml
numerics:
  interface:
    transport:
      variable: q
      spatial: geometric_swept_volume
      time_integrator: tvd_rk3
      boundedness: certified
      fail_close: true
  momentum:
    form: conservative_common_flux
    terms:
      surface_tension:
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
        pressure_force_contract: variational_adjoint
        scalar_operator_pairing: variational_operator
        capillary_reaction_projection: pressure_component_hodge
```

Legacy/default state:

```yaml
interface:
  state_space:
    kind: diffuse_cls
```

If the block is absent, parse as `diffuse_cls` for backward compatibility.

### Reinitialization

Compatibility projection is not reinitialization.  For the geometric route:

```yaml
interface:
  reinitialization:
    algorithm: none
```

If a transition alias is needed, `algorithm: compatibility_projection` may be
accepted only as a parser alias for
`interface.state_space.compatibility.projection`.  It must not call the old
Ridge-Eikonal sharp-volume bracket.

### Parser fail-close rules

Reject:

```text
geometric_cell_fraction with transport.variable=psi,
transport.variable=q with momentum.form != conservative_common_flux,
bundle_virtual_work with endpoint != geometric_cell_fraction,
geometric_cell_fraction with ridge_eikonal reinitialization,
fail_close=false,
boundedness repaired by clipping,
capillary from curvature_jump on incompatible psi,
normalized J_A used as the hard physical projection operator.
```

## 13. Output, Diagnostics, And Restart

Required diagnostics:

```text
q_volume_conservation
compatibility_residual_q
stratum_margin
projection_surface_work
young_laplace_hodge_residual
common_flux_phase_momentum_certificate
bounded_swept_flux_certificate
```

Plot fields:

```text
theta
q
phi
Gamma overlay
pressure
velocity
capillary_hodge_residual
```

Snapshot series should share color and vector scales across time slices.

Restartable checkpoint class:

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

Post-step plot checkpoints are analysis artifacts.  They are not sufficient
for mathematical continuation.

## 14. Implementation Ladder

Implementation should proceed in this order.

### Stage 0: schema gate

Add config dataclasses and parser validation, but keep activation
fail-closed.  Negative-control tests must prove mixed-state YAML is rejected.

### Stage 1: fixed-stratum geometry

Implement:

```text
Q_h, A_h, S_h, J_q, dS_h
```

for 2D P1/Q1 traces.

Tests:

```text
uniform cell cut area,
nonuniform physical cut area,
finite-difference J_q,
finite-difference dS_h,
periodic seam counted once,
wall cells counted once.
```

### Stage 2: compatibility projection

Implement hard projection:

```text
Q_h(phi)=q
```

with Schur solve and sign-margin line search.

Tests:

```text
constant-shift manufactured target,
smooth perturbation target,
large stratum-crossing target fail-close,
nonuniform q-weighting target.
```

### Stage 3: swept-volume phase transport

Implement bounded `Phi_l`.

Tests:

```text
closed-domain global q conservation,
local boundedness without clipping,
periodic/wall flux closure,
common mass flux uses same Phi_l.
```

### Stage 4: bundle capillary

Implement:

```text
T_q,
L_B,
r_sigma,
M_f Riesz acceleration.
```

Tests:

```text
static Young-Laplace pressure-exact residual,
nonconstant-curvature nonzero drive,
pressure/capillary Hodge adjoint identity,
component-volume reaction gate.
```

### Stage 5: restart and ch14 activation

Tests:

```text
pre_step_full continuation equals zero-start short run,
static droplet remains static by range condition,
oscillating droplet produces capillary drive,
capillary wave conserves q and evolves without hidden projection work,
rising bubble uses q-derived density and common flux.
```

Only after all stage gates pass should chapter-14 YAMLs activate
`geometric_cell_fraction`.

## 15. Negative Knowledge

Do not implement as production:

```text
geometric fractions used only for plots,
global mass correction after diffuse transport,
clipping q after update,
normalized theta residuals as physical constraints on nonuniform grids,
J_A-only Schur solve for hard volume projection,
capillary dS_h from a surface different from Q_h,
CCD/FCCD/UCCD differentiation of discontinuous theta,
Ridge-Eikonal sharp-volume bracket inside the geometric route,
range projection that removes physical non-pressure capillary drive,
benchmark-name branches,
damping/CFL tuning/curvature caps/smoothing as fixes,
FD/WENO/PPE fallback as a phase-geometry repair,
QP-as-physics without the variational bundle proof.
```

## 16. First Implementation Ticket

The first concrete implementation task should be deliberately small:

```text
Implement src/twophase/geometry/cell_complex.py
and src/twophase/geometry/p1_cut_geometry.py
with CPU/GPU-compatible Q_h and S_h for 2D uniform/nonuniform grids.
```

Acceptance:

```text
1. Q_h returns physical cell volumes q_C, not normalized fractions.
2. theta view equals q_C/|C|.
3. S_h uses physical segment length.
4. periodic-x/wall-y seam counting is correct.
5. implementation uses backend.xp on the production path.
6. tests include at least one nonuniform grid manufactured cut.
```

Do not start with transport or capillary.  The geometry map is the SSoT.  If
`Q_h` and `S_h` are not exact and mutually consistent, every later stage will
inherit the old two-measure problem.

## 17. Minimal Ready-To-Start Checklist

Before coding:

```text
[ ] create geometry package and public module boundaries,
[ ] add InterfaceStateSpaceCfg parse model behind fail-closed gate,
[ ] add tests for Q_h/S_h physical geometry,
[ ] add negative YAML tests,
[ ] add no production activation in ch14 YAML yet.
```

After Stage 1:

```text
[ ] add J_q/dS_h derivative tests,
[ ] add projection manufactured probes,
[ ] record Delta S_Pi ledger schema,
[ ] update WIKI-T-169 and SP-AO with measured gates.
```

The theory is ready for implementation at the geometry/projection layer.  The
remaining risk is not conceptual ambiguity but execution discipline: every
consumer must be typed so that the old diffuse `psi` route and the new
geometric `q` route cannot silently mix.
