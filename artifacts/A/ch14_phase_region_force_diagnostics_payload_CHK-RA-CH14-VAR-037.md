# CHK-RA-CH14-VAR-037 - PhaseRegion force diagnostics payload

Date: 2026-05-17

Scope: attach optional zero-step work/Hodge/reaction diagnostics to
`PhaseRegionForceAdmission`.  This checkpoint does not connect the candidate to
pressure/velocity projection, nonlinear optimization, micro-step, or T/8.

## Motivation

`CHK-RA-CH14-VAR-036` introduced the explicit force candidate, but the runtime
dry-run still computed virtual-work, Hodge, and component-reaction diagnostics
outside the candidate.  That left one more split:

```text
candidate owns owner-map / face metric / Riesz cochain
experiment owns work/Hodge/reaction admission checks
```

The payload added here keeps those diagnostics attached to the same zero-step
candidate object, while preserving `force_admissible=false`.

## Implementation

Extended:

```text
src/twophase/coupling/phase_region_force_admission.py
src/twophase/tests/test_phase_region_force_admission.py
experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Added:

```text
PhaseRegionForceDiagnostics
attach_phase_region_force_diagnostics
```

The diagnostic attachment:

1. rejects invalid candidates with `diagnostics.valid=false`;
2. scales the self face velocity to the fixed stratum;
3. optionally scales and checks a supplied probe velocity;
4. runs `fixed_stratum_virtual_work_check`;
5. computes weighted Hodge and component-reaction diagnostics;
6. merges scalar diagnostics into `admission.metrics`;
7. keeps `admission.force_admissible=false`.

## Equation -> Discretization -> Code

| Equation | Discretization | Code |
|---|---|---|
| `eps ||T_h(scale u_f)||_inf <= alpha min|psi-0.5|` | local fixed-stratum displacement gate | `scale_face_velocity_to_fixed_stratum` |
| `dE_h[T_h(u_f)] + <s_f,u_f>_{M_f}=0` | self and optional probe virtual-work checks | `attach_phase_region_force_diagnostics` |
| `s_f = range + hodge` | weighted diagnostic Hodge split | `weighted_hodge_decomposition` |
| `hodge(s_f - beta B_f)` | component-reaction residual | `component_reaction_hodge_gate` |
| no force acceptance | explicit status bit | `force_admissible=False` |

## Tests

Added tests for:

```text
valid candidate receives valid diagnostics
self and probe work checks remain valid
Hodge and reaction residual divergences are bounded
invalid candidate receives diagnostics.valid=false
force_admissible remains false
```

## Validation

Remote command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
```

Result: PASS.  The current `make test` target ran the full suite:

```text
839 passed, 35 skipped
```

Runtime dry-run regression:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Result: PASS with unchanged key metrics:

```text
self_fd_power_residual  = 2.481405282624e-07
probe_fd_power_residual = 2.481363539023e-07
hodge_divergence_linf   = 1.083435563487e-09
force_admissible        = 0.0
```

## Code Review

[SOLID-X] no violation.  The helper remains a contract object with no
pressure/velocity consumer and no runtime route selection.  The experiment
keeps plotting and YAML orchestration; the helper only gathers diagnostics for
the already-built candidate.

## Theory Consistency

The same candidate now owns:

```text
q_l -> q_g owner map
runtime psi gauge
nodal-density face metric
Riesz face cochain
fixed-stratum work/Hodge/reaction diagnostics
```

This closes the zero-step diagnostic object without admitting the force to a
time step.  The next safe gate is a candidate-focused zero-step adapter
experiment or a diagnostic report object.  Pressure/velocity coupling,
micro-stepping, and T/8 remain forbidden.

## Final Validation

```text
git diff --check = PASS
remote make test = PASS
remote make cycle = PASS
docs/wiki WIKI count = 430
docs/wiki/code WIKI-L count = 63
targeted CHK/wiki/script scan = PASS
```
