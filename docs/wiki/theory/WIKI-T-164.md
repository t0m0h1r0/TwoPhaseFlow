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
depends_on:
  - "[[WIKI-T-088]]"
  - "[[WIKI-T-101]]"
  - "[[WIKI-T-153]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-158]]"
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-T-163]]"
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

The intended production surface is:

```yaml
run:
  momentum_form: conservative_common_flux

numerics:
  conservative_transport:
    strict: true
    energy_certificate: strict
    high_k_monitor: fail_close
  pressure:
    projection_metric: transported_face_mass
    history_storage: face_impulse_cochain
  capillary:
    force_form: surface_energy_adjoint
    reaction_projection: diagnostic_or_constraint
  reinitialization:
    remap: conservative_qmp_or_fail
```

Invalid mixtures should fail at config validation, especially
`conservative_common_flux` with q-only reinitialization, primitive-velocity
restart state, scalar pressure-history storage, or silent filters.

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
