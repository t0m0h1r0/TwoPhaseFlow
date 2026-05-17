# CHK-RA-CH14-VAR-035 - PhaseRegion force-admission helpers

Date: 2026-05-17

Scope: implement the contract-level helper allowed by
`CHK-RA-CH14-VAR-034`.  This checkpoint does not add a production force route,
pressure/velocity coupling, nonlinear optimization, micro-step, or T/8.

## Motivation

The zero-step runtime dry-run proved the equations, but the experiment still
owned two pieces of reusable contract logic:

```text
rho = rho_g + (rho_l-rho_g) psi
M_f = face_mass_components(grid, rho_node)
u_f -> scaled u_f so psi +/- eps*T_h(u_f) remains in the fixed stratum
```

Keeping those inside an experiment makes it too easy for a future adapter to
repeat the earlier mistakes: passing cell density to a face metric, or using a
finite-difference velocity that leaves the stratum.

## Implementation

Added:

```text
src/twophase/coupling/phase_region_force_admission.py
src/twophase/tests/test_phase_region_force_admission.py
```

Exported from `twophase.coupling`:

```text
PhaseRegionFaceMassMetric
FixedStratumVelocityScale
two_phase_nodal_density
phase_region_face_mass_metric
scale_face_velocity_to_fixed_stratum
```

Refactored:

```text
experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

The experiment now consumes the helper for nodal-density face metrics and
fixed-stratum velocity scaling.  Its runtime metrics are unchanged.

## Equation -> Discretization -> Code

| Equation | Discretization | Code |
|---|---|---|
| `rho = rho_g + (rho_l-rho_g) psi` | nodal runtime phase indicator, finite positive densities | `two_phase_nodal_density` |
| `M_f` | face measure times arithmetic face density | `phase_region_face_mass_metric` |
| reject cell-density metric | require `psi.shape == grid.shape` | `phase_region_face_mass_metric` |
| `T_h(u_f)=-D_f(psi_f u_f)` | FCCD fixed-stratum transport increment | `scale_face_velocity_to_fixed_stratum` |
| `eps ||T_h(scale u_f)||_inf <= alpha min|psi-0.5|` | local finite-difference displacement gate | `FixedStratumVelocityScale` |

## Tests

The new tests check:

```text
two-phase nodal density equals rho_g + (rho_l-rho_g) psi
face weights equal face measure times arithmetic nodal density average
cell-density shaped psi fails closed
scaled virtual velocity stays within the fixed-stratum sign margin
zero sign margin returns valid=false
```

The first remote test attempt failed only because the test compared a float to
`pytest.approx` with `<=`.  The implementation was unchanged; the assertion was
rewritten as an explicit upper-bound check.

## Validation

Remote command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
```

Result: PASS.  The current `make test` target ran the full suite:

```text
834 passed, 35 skipped
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

[SOLID-X] no violation.  The new module is a small contract helper with no
I/O, no runtime route, and no pressure/velocity consumer.  The existing
experiment retains plotting and orchestration.  The helper uses existing
`face_mass_components` and `transport_increment_from_face_velocity` rather
than duplicating the discrete operators.

## Theory Consistency

This implementation preserves the `CHK-RA-CH14-VAR-034` boundary:

```text
runtime psi gauge -> nodal density -> face metric
face velocity -> fixed-stratum transport increment -> local displacement scale
force_admissible remains false
```

It does not reinterpret transported `q`, rebuild `phi`, smooth the interface,
weaken tolerances, or hide the Hodge/reaction residual.  The next gate can now
build a zero-step `PhaseRegionForceAdmission` candidate object from these
helpers, still without pressure/velocity coupling or T/8.

## Final Validation

```text
git diff --check = PASS
remote make test = PASS
remote make cycle = PASS
docs/wiki WIKI count = 428
docs/wiki/code WIKI-L count = 61
targeted CHK/wiki/script scan = PASS
```
