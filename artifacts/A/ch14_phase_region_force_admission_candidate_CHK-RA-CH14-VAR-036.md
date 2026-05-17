# CHK-RA-CH14-VAR-036 - PhaseRegion force-admission candidate

Date: 2026-05-17

Scope: add a zero-step `PhaseRegionForceAdmission` candidate object on top of
the force-admission helpers.  This checkpoint does not connect the candidate to
pressure/velocity projection, nonlinear optimization, micro-step, or T/8.

## Motivation

`CHK-RA-CH14-VAR-035` factored the nodal-density face metric and fixed-stratum
velocity scaling into tested helpers.  The next design gate required a single
candidate object that gathers the zero-step ingredients while keeping
admission status explicit:

```text
owner map
face metric
Riesz cochain
metrics
valid / reason
force_admissible = false
```

This prevents a later runtime integration from confusing "candidate built" with
"force accepted by the pressure/velocity step".

## Implementation

Extended:

```text
src/twophase/coupling/phase_region_force_admission.py
src/twophase/tests/test_phase_region_force_admission.py
experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Added:

```text
PhaseRegionForceAdmission
build_phase_region_force_admission_candidate
```

The builder:

1. rejects `runtime_steps != 0` with `valid=false`;
2. maps `q_source` to the requested owner phase;
3. builds the nodal-density face metric;
4. assembles the closed-interface Riesz cochain;
5. records scalar metrics;
6. always returns `force_admissible=false`.

The existing runtime force dry-run now obtains `owner_map` and `cochain` from
this candidate, then performs the same work/Hodge/reaction diagnostics as
before.

## Equation -> Discretization -> Code

| Equation | Discretization | Code |
|---|---|---|
| `q_g = |C| - q_l` | explicit owner map | `map_cell_measure_to_phase_owner` inside `build_phase_region_force_admission_candidate` |
| `M_f` | nodal-density face metric | `phase_region_face_mass_metric` |
| `s_f=-M_f^{-1}T_h^T dE_h` | closed-interface Riesz cochain | `closed_interface_riesz_cochain` |
| `runtime_steps = 0` | zero-step admission guard | `PhaseRegionForceAdmission.valid` |
| no force acceptance | explicit status bit | `force_admissible=False` |

## Tests

Added candidate-object tests for:

```text
valid zero-step candidate
force_admissible remains false
owner complement is exact
runtime_steps != 0 fails closed
cell-shaped psi fails closed before force use
```

The first remote attempt failed because the synthetic ellipse `psi` in the
test was not a regular closed-interface stratum.  The builder correctly
returned `valid=false`.  The test fixture was changed to the same regular
smooth ellipse chart used by the existing Riesz tests.

## Validation

Remote command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
```

Result: PASS.  The current `make test` target ran the full suite:

```text
837 passed, 35 skipped
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

[SOLID-X] no violation.  The candidate builder is a small contract object and
does not own plotting, experiment I/O, pressure projection, velocity updates,
or runtime route selection.  It gathers already-defined owner-map, face-metric,
and Riesz pieces, and fails closed before any force can be consumed.

## Theory Consistency

The candidate keeps the PhaseRegion state boundary explicit:

```text
runtime q_l -> owner q_g
runtime phi gauge -> psi chart
psi chart -> nodal density -> M_f
M_f and psi -> Riesz cochain
valid candidate != admitted force
```

The next gate is still not T/8.  The next safe step is to add optional
diagnostic work/Hodge payload fields to the candidate or to build a zero-step
adapter experiment around the candidate, while keeping pressure/velocity
coupling disabled.

## Final Validation

```text
git diff --check = PASS
remote make test = PASS
remote make cycle = PASS
docs/wiki WIKI count = 429
docs/wiki/code WIKI-L count = 62
targeted CHK/wiki/script scan = PASS
```
