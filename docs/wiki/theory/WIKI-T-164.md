---
ref_id: WIKI-T-164
title: "Conservative Common-Flux Energy Ledger for Rising Bubbles"
domain: theory
status: ACTIVE
tags: [rising_bubble, conservative_momentum, common_flux, energy_ledger, pressure_projection, reinitialization, fail_close]
sources:
  - path: docs/memo/short_paper/SP-AJ_conservative_common_flux_energy_ledger.md
    description: "Short-paper derivation of the conservative common-flux remedy"
  - path: artifacts/A/ch14_rising_bubble_blowup_rca_CHK-RA-CH14-BUBBLE-BLOWUP-RCA-002.md
    description: "SI rising-bubble blow-up RCA identifying the interface-band Nyquist velocity mode"
  - path: artifacts/A/ch14_rising_bubble_remedy_theory_CHK-RA-CH14-BUBBLE-REMEDY-THEORY-001.md
    description: "Theory-first remedy matrix and YAML contract"
  - path: artifacts/A/ch14_common_flux_transport_impl_CHK-RA-CH14-COMMON-FLUX-IMPL-001.md
    description: "Existing isolated common-flux transport foundation"
  - path: artifacts/A/ch14_common_flux_implementation_ux_CHK-RA-CH14-COMMON-FLUX-UX-001.md
    description: "Implementation dependency order and YAML UX contract"
  - path: docs/wiki/theory/WIKI-T-165.md
    description: "Refinement of gravity/buoyancy as a variational Hodge force covector"
depends_on:
  - "[[WIKI-T-088]]"
  - "[[WIKI-T-101]]"
  - "[[WIKI-T-153]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-158]]"
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-T-163]]"
  - "[[WIKI-T-165]]"
  - "[[WIKI-X-041]]"
  - "[[WIKI-X-048]]"
consumers:
  - domain: theory
    usage: "Use as the active remedy contract for SI water-air rising-bubble blow-up"
  - domain: code
    usage: "Route implementation toward q,m,p common-flux state, conservative remap, pressure metric, and energy certificates"
  - domain: experiment
    usage: "Interpret future rising-bubble long runs only after certificate gates pass"
  - domain: paper
    usage: "Convert successful portions into Chapter 14 only after implementation and validation"
compiled_by: ResearchArchitect
compiled_at: "2026-05-09"
---

# Conservative Common-Flux Energy Ledger for Rising Bubbles

## Claim

The SI 10 mm x 20 mm water-air rising-bubble blow-up is not a physical bubble
motion.  It is an interface-band near-Nyquist velocity mode.  The accepted
remedy class is therefore not damping, smoothing, CFL reduction, curvature
capping, pressure filtering, or a benchmark-specific branch.  The accepted
remedy is a conservative common-flux Navier--Stokes route with a per-step
energy ledger.

## Minimal State

The production state must be conservative:

```text
q_i       liquid fraction,
m_i(q)   = V_i (rho_g + (rho_l-rho_g) q_i),
p_i      = m_i u_i,
E_h      = sum_i |p_i|^2/(2m_i) + sigma S_h(q) + sum_i m_i g y_i.
```

Primitive velocity is not a sufficient primary state for water-air rising
bubbles because reinitialization or phase transport can change mass without a
matching momentum remap.

## Algebraic Contract

Use cells `C`, oriented faces `F`, cell-volume matrix `V_c`, finite-volume
divergence `D : R^F -> R^C`, and transported face-mass metric `M_f(q)`.  The
inner products are

```text
<a,b>_C = a^T V_c b,
<u,w>_M = u^T M_f(q) w.
```

A step ledger contains stage fluxes

```text
L_h = {F_q^r, F_V^r, U_up^r, alpha_rs, beta_r}.
```

The only admissible mass and momentum fluxes are

```text
F_m^r = rho_g F_V^r + (rho_l-rho_g) F_q^r,
F_p^r = F_m^r U_up^r.
```

Thus each stage must satisfy

```text
q^{r+1} = sum_s alpha_rs q^s - dt beta_r D F_q^r,
m^{r+1} = sum_s alpha_rs m^s - dt beta_r D F_m^r,
p^{r+1} = sum_s alpha_rs p^s - dt beta_r D F_p^r,
m^{r+1} = V_c (rho_g + (rho_l-rho_g) q^{r+1}).
```

The capillary acceleration is not a curvature sample.  It is the Riesz
representative

```text
a_sigma(q) = -sigma M_f(q)^{-1} T_q(q)^T V_c g_S(q),
dS_h(q)[delta q] = <g_S(q),delta q>_C,
T_q(q)w = -D((P_f q)w)
```

up to the same transport linearization used in the ledger.

Gravity is the analogous mass-transport pullback, refined in [[WIKI-T-165]]:

```text
r_g(q) = -T_m(q)^T d Phi_g/dm,
a_g(q) = M_f(q)^{-1} r_g(q).
```

Thus the legacy nodal body-force form is not a production definition unless it
is proven equal to this covector in the transported face-mass metric.

Pressure projection is the KKT system

```text
M_f(u^{n+1}-u*) + D^T pi + C_b^T lambda = 0,
D u^{n+1} = 0,
C_b u^{n+1} = b_b.
```

The whole step is accepted only if

```text
E_h^{n+1} - E_h^n
  <= sum_r eps_T^r + eps_R + eps_sigma + eps_g
   + eps_mu + eps_Pi + tau_round,
```

with viscosity and projection non-positive up to tolerance.  The high-k monitor

```text
H_k = ||Pi_high Chi_Gamma u||_{M_f}^2 / ||Chi_Gamma u||_{M_f}^2
```

is a witness, not a filter.

## Required Step Contract

An admissible step is:

```text
(q,m,p)^n
  -> common-flux transport of q,m,p
  -> conservative reinitialization/remap, or fail-close
  -> variational capillary and gravity impulse
  -> dissipative viscosity
  -> transported-mass pressure projection
  -> certified state
```

Each arrow must have either an equality or a named defect:

```text
transport:     K(m^T,p^T) <= K(m^n,p^n) + eps_T
reinit/remap:  K(m^R,p^R) <= K(m^T,p^T) + eps_R
capillary:     Delta K + sigma Delta S = eps_sigma
gravity:       Delta K + Delta Phi = eps_g
viscosity:     viscous_work <= eps_mu, with eps_mu small
projection:    K_after <= K_before in transported M_f
```

If the ledger cannot be produced, the correct production behavior is
fail-close.

## Common Flux

If the phase flux is `F_q`, the mass flux must be derived from the same face
and stage:

```text
F_m = rho_g F_V + (rho_l-rho_g) F_q,
F_p = F_m u_up.
```

The same ledger must drive phase, density/mass, and momentum.  Endpoint volume
conservation alone is not enough.

## 2026-05-09 Implementation Audit

The stabilized rising-bubble route is admissible because each code change
restores one algebraic identity of the conservative common-flux system:

- **Same divergence complex.**  The projected face velocity is incompressible
  only in the divergence operator that produced it.  Phase and momentum
  transport must therefore accumulate fluxes with the same `D`; otherwise a
  face field can be divergence-free for pressure but compressive for transport.
- **Affine density closure.**  Density is `rho(q)`, not an independent
  unknown.  The stage ledger must store the phase state so that every RK stage
  uses `rho^r = rho_g + (rho_l-rho_g)q^r` and rejects non-affine restarts or
  clipped/projected ledgers.
- **No duplicate primitive convection.**  Once `p=rho u` has been advanced by
  `div(p tensor u)`, a primitive `u dot grad u` predictor would count the same
  nonlinear transport work again.  The conservative route therefore disables
  primitive convection and its AB/BDF history while retaining velocity history
  for non-advective time integration.
- **Flux limiting, not endpoint clipping.**  Boundedness may be enforced only
  by replacing the recorded phase flux with
  `F_low + alpha(F_high-F_low)`, `0<=alpha<=1`, so mass and momentum see the
  same limited face flux.  This is theorem-grade only when the donor low-order
  update is invariant-domain admissible under the current CFL; otherwise the
  step must be rejected or fail-closed.
- **Wall trace projection.**  A reconstructed node field used by CCD/UCCD or
  viscosity must satisfy `C_b u=0`.  Enforcing this trace after face
  reconstruction is a boundary reaction on the representative; it must not
  replace the canonical projected face cochain.
- **Checkpoint closure.**  Restart equivalence requires pre-step `q,m,p` plus
  projected face state and pressure-history face cochains.  Primitive velocity
  alone is not a conservative restart state.

This audit supports the current static-grid, reinit-free
`conservative_common_flux` route.  It does not yet certify q-only
reinitialization, dynamic interface-fitted remap, curvature near-singular
diagnostics, or long-time high-k growth; those remain fail-close or diagnostic
targets, not solved physics.

## Reinitialization Rule

Reinitialization is admissible only as

```text
R_h : (q,m,p) -> (q',m',p')
```

with consistent mass, component volume, momentum, and kinetic-energy defect
accounting.  A q-only production reinit is not theorem-grade at density ratio
833.

## Pressure Rule

Pressure projection must solve

```text
u^{n+1} = argmin_{D u = 0, BC} 1/2 ||u-u*||^2_{M_f}
```

with `M_f` equal to the transported face mass metric.  Affine pressure history
must be stored as the matching face impulse/cochain, not as a scalar pressure
field that later changes metric.

## Capillary Rule

Capillarity must be constructed as

```text
f_sigma = - sigma T_q(q)^* d_q S_h
```

in the same metric.  Pressure/component reaction projection is allowed only as
a decomposition of this variational cochain:

```text
h_sigma = (I - Pi_X^M) f_sigma.
```

It is not the old production replacement `c_sigma -> Pi_R c_sigma`, which can
delete physical release acceleration.

## CCD/FCCD/UCCD Reading

Use the CCD family by physical role:

```text
FCCD : common phase/geometric flux ledger and incidence,
UCCD : optional conservative momentum flux evaluator,
CCD  : viscous/stress and elliptic operators with work signs,
DCCD : diagnostic or certified projection, not a damping patch.
```

The operator name does not certify the step.  The energy ledger certifies it.

## YAML Contract

The intended production surface uses `numerics.momentum.form` as canonical.
`run.momentum_form` may remain a compatibility alias only when it agrees.

```yaml
numerics:
  momentum:
    form: conservative_common_flux
    conservative_common_flux:
      mode: strict
      state: cell_qmp
      transport:
        ledger: required
        phase_stage_projection: forbidden
        energy_gate: fail_close
      remap:
        policy: conservative_qmp_or_fail
        allow_q_only: false
      certificates:
        energy: strict
        high_k_interface: fail_close
  pressure:
    projection_metric: transported_face_mass
    history_storage: face_impulse_cochain
  interface:
    transport:
      ledger: required
      clipping: forbidden
```

Invalid mixtures should fail at config validation, especially
`conservative_common_flux` with q-only reinitialization, primitive-velocity
restart state, scalar pressure-history storage, or silent filters.

## Implementation Reading

Implementation should proceed by dependency gates:

```text
G0 config validation remains fail-closed
G1 ConservativeState(q,m,p,u,M_f)
G2 interface stage requests TransportLedger and transports q,m,p together
G3 ConservativeQMPRemapper for reinit/grid rebuild, or fail-close
G4 force predictor treats u as p/m and writes impulses back to p
G5 pressure projection consumes explicit transported M_f(q)
G6 EnergyLedger plus high-k witness
G7 checkpoint schema stores pre-step q,m,p and face-history cochains
```

The current `psi,u,v` grid rebuild path is not admissible for this route because
it remaps velocity rather than conservative momentum.  Until conservative
remap exists, strict conservative runs with reinit or interface-fitted grid
rebuild must fail closed.

**Passive checkpoint corollary (2026-05-09).**  A checkpoint/snapshot schedule is
not a force, constraint, or time integrator.  It must not change `dt` merely to
hit an output time.  The admissible rollback checkpoint is the actual pre-step
state immediately before crossing the requested checkpoint label; exact-time
rollback requires a variable-step/dense-output theorem and must otherwise
remain fail-closed.  Treat any output path that perturbs the discrete trajectory
as a production bug, not as harmless I/O.

## Negative Knowledge

Do not treat the following as solutions:

- smaller CFL;
- velocity or pressure damping;
- curvature caps or smoothing;
- pressure representative fallback;
- PPE fallback;
- FD/WENO fallback;
- disabling affine history as the cure;
- disabling reinitialization without a conservative replacement;
- range-projecting capillarity as the production force;
- benchmark-name branches.

These are controls or diagnostics.  They do not prove that the high-frequency
interface mode cannot receive unaccounted energy.

## Retrieval Note

Use this card after [[WIKI-X-041]] when the question is specifically
water-air rising-bubble blow-up or conservative common-flux implementation.  Use
[[WIKI-T-162]] for the closed-interface capillary force itself and
[[WIKI-T-163]] for reinit-free/profile-control candidate routes.
