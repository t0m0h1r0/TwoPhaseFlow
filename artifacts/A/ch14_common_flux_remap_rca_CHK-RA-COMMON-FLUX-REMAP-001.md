# CHK-RA-COMMON-FLUX-REMAP-001 — Conservative Common-Flux Remap RCA

Date: 2026-05-10
Branch: `codex/ra-common-flux-remap-20260510`

## Problem

`conservative_common_flux` had been promoted to the chapter-14 YAML contract,
but interface-following fitted-grid remap was not executable.  A minimal
two-step probe reproduced the failure:

```text
ch14_static_droplet.yaml       step 1 NotImplementedError grid remap
ch14_oscillating_droplet.yaml  step 1 NotImplementedError grid remap
ch14_capillary.yaml            step 1 NotImplementedError grid remap
ch14_rising_bubble.yaml        PASS because grid_rebuild_freq=0 and reinit=0
```

This is a structural error: a chapter-level production form cannot be
incompatible with the paper-standard interface-following grid.

## Hypotheses

H01 — Dynamic grid remap is explicitly fail-closed.
Constraint broken: executable YAML contract.  Verification: source guard in
`TwoPhaseNSSolver._advance_conservative_common_flux_stage` raised whenever
`will_rebuild=True`; two-step ch14 probes failed exactly there.  Accepted.

H02 — Current remap moves primitive velocity, not conservative momentum.
Constraint broken: common-flux state closure `m=V rho(q)`, `p=m u`.
Verification: `rebuild_ns_grid` remapped `psi,u,v`; it did not accept or return
`rho` or `rho u`.  Accepted.

H03 — Phase remap is only endpoint volume corrected, not coupled to momentum.
Constraint broken: same representation operator must act on `(q,m,p)`.
Verification: `psi` used mass correction, while `u,v` used interpolation and
projection.  No momentum integral was named.  Accepted.

H04 — Reinitialization is a hidden q-only remap under common flux.
Constraint broken: `q` changes mass metric while momentum remains on the old
bundle.  Verification: common-flux transport requested a ledger at the
pre-reinit endpoint, and reinit was either fail-closed when projection fields
were recorded or silently overwritten by `ledger.psi_after_transport` when not
recorded.  Accepted.

H05 — The issue is merely a YAML mistake and should be solved by disabling
grid remap or reverting momentum form.
Constraint broken: paper-standard fitted-grid route and conservative state
theory.  Verification: disabling remap avoids the exception but abandons the
interface-following experiment.  Rejected as production fix.

H06 — A CFL/damping/smoothing change could make the run survive.
Constraint broken: no operator identity is restored.  Verification: the failure
occurs before numerical instability, at a theorem gate.  Rejected.

H07 — The correct remap is conservative in phase and momentum integrals.
Constraint satisfied: metric integral constraints on rebuilt grid:
`1^T V^+q^+=1^T V^-q^-` and `1^T V^+p_a^+=1^T V^-p_a^-`.
Verification: manufactured remap test preserves phase and momentum integrals
to `1e-12`.  Accepted.

H08 — Velocity-preserving lift is the least dishonest fixed-grid reinit
coupling.
Constraint satisfied: reinit is not physical transport; it is a vertical
retraction over the velocity fiber: `m^R=V rho(q^R)`, `p^R=m^R u^T`.
Verification: common-flux reinit two-step test keeps density affine in the
post-reinit `psi` and remains finite.  Accepted.

H09 — Pressure projection/reprojection after grid rebuild must update
momentum.
Constraint broken if ignored: `u` and `p` would disagree after enforcing
divergence/boundary constraints.  Verification: implementation resynchronizes
`p=m u` after the grid-rebuild reprojector.  Accepted.

## Implemented Correction

1. `rebuild_ns_grid` now optionally accepts conservative momentum components.
2. During fitted-grid rebuild it remaps `q` and `p_a`, restores phase and
   momentum metric integrals, rebuilds density from the remapped phase, derives
   velocity as `u=p/m`, then lets the existing divergence reprojector act.
3. After reprojection, momentum is reset to `p=m u` so the conservative state
   and primitive representative agree.
4. `conservative_common_flux` no longer rejects `will_rebuild`; it invokes the
   conservative remap path and remaps labelled `psi_previous` /
   `psi_transport_endpoint` to the rebuilt grid.
5. Reinitialization is handled as a velocity-preserving conservative lift
   rather than discarded or blindly accepted as q-only transport.

## Verification

Focused tests:

```text
test_conservative_grid_rebuild_preserves_phase_and_momentum_integrals PASS
test_conservative_common_flux_dynamic_grid_rebuild_two_steps PASS
test_conservative_common_flux_reinit_retraction_keeps_density_affine PASS
```

Expanded local targeted tests:

```text
test_common_flux_transport.py + test_grid_remap.py + ch14 solver-build/common-flux tests
19 passed
```

Canonical two-step probe after correction:

```text
ch14_static_droplet.yaml       PASS rebuild=1 reinit=0
ch14_oscillating_droplet.yaml  PASS rebuild=1 reinit=1
ch14_capillary.yaml            PASS rebuild=1 reinit=1
ch14_rayleigh_taylor.yaml      PASS rebuild=1 reinit=1
ch14_rising_bubble.yaml        PASS rebuild=0 reinit=0
```

Capillary-wave one-period production run:

```text
command: make cycle EXP=experiment/run.py ARGS="--config ch14_capillary"
T_final: 16.632565583
steps: 2145
status: PASS
KE: 1.743931e-09 -> 1.313187e-03, max 1.409062e-03
volume drift: final 3.680555e-04, max 5.506125e-04
interface amplitude: 1.046912e-02 -> 4.807324e-03,
                     min 1.013410e-03, max 1.179988e-02
pre_blowup_checkpoint_written: false
```

## Negative Knowledge

- Do not fix this by setting `grid.distribution.schedule: 0` everywhere.
  That hides the missing conservative remap.
- Do not revert to primitive momentum merely to pass the run.  That discards
  the common-flux theorem.
- Do not treat reinit as physical capillary work.  Work uses the labelled
  transport endpoint; reinit contributes a named representation defect.
- Do not add damping, CFL relaxation, smoothing, curvature caps, fallback PPE,
  or benchmark-specific branches.
