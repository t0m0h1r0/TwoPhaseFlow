# CHK-RA-CH14-VAR-052 - PhaseRegion Capillary Graph Dry-Run Adapter

Date: 2026-05-17

Scope: pass the Ch14 capillary-wave initial graph through the same
PhaseRegion/InterfaceAtlas owner route used by the droplet dry-run adapters,
without changing runtime tolerances, CFL, smoothing, damping, rebuild policy,
or production force coupling.

## Motivation

The old capillary-wave runner already passes through its graph-specific
active-geometry runtime endpoint.  That is not enough evidence for the new
PhaseRegion-primary scheme: the capillary wave must also be admitted as a
PhaseRegion graph component, not treated as a separate theory from the closed
droplet chart.

This check therefore uses the same physical ownership convention as the
PhaseRegion design:

```text
runtime q_l = liquid cell measure below the graph
PhaseRegion owns Omega_g = gas above the graph
q_g = |C| - q_l
Gamma_h = boundary Omega_g represented by a GAS_ABOVE graph chart
E_h = sigma * Perimeter(Gamma_h)
```

## Implementation

Added:

```text
experiment/ch14/diagnose_phase_region_capillary_graph_dry_run_adapter.py
```

The adapter reads `experiment/ch14/config/ch14_capillary.yaml`, builds the
diagnostic fitted grid, reconstructs the YAML graph `eta(x)`, checks the
runtime `phi`-derived liquid measure against `Q_h(eta)`, maps liquid ownership
to gas by exact finite-volume complement, stores a single `GAS_ABOVE`
`ChartType.GRAPH` component in `PhaseRegionBatch`, and assembles the
PhaseRegion measurement/residual.

It also checks the graph energy covector against a finite-difference variation
along the capillary-wave mode and checks that the restoring force opposes the
interface mode.

Added unit coverage in:

```text
src/twophase/tests/test_phase_region_measure.py
```

The new test verifies the same graph-gas complement contract on an explicitly
nonuniform grid and compares `dE` with the finite-difference derivative.

## Remote Dry Run

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_dry_run_adapter.py
```

Result: PASS.

```text
phase_region_graph_admitted = 1
complement_used             = 1
gas_target_volume           = 2.000000000000e-04
gas_physical_volume         = 2.000000000000e-04
residual_l2                 = 0.000000000000e+00
runtime_graph_q_linf        = 0.000000000000e+00
column_height_linf          = 4.510281037540e-17
dE_dmode_abs_error          = 4.758186900045e-12
force_sign_product          = -1.128342698667e-03
perimeter                   = 2.007772098404e-02
force_admissible            = 0
```

Output:

```text
experiment/ch14/results/diagnose_phase_region_capillary_graph_dry_run_adapter/data.npz
experiment/ch14/results/diagnose_phase_region_capillary_graph_dry_run_adapter/phase_region_capillary_graph_dry_run_adapter.pdf
```

## Remote Tests

First attempt used the local path prefix under the remote `src` root and
therefore selected no tests:

```text
make test PYTEST_ARGS='src/twophase/tests/test_phase_region_measure.py src/twophase/tests/test_q_manifold_projection.py -q'
```

Result:

```text
ERROR: file or directory not found: src/twophase/tests/test_phase_region_measure.py
```

Re-run with the correct remote test paths:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_measure.py twophase/tests/test_q_manifold_projection.py -q'
```

Result: PASS.  The remote make target ran the suite under its configured root:

```text
867 passed, 35 skipped
```

## Verdict

The capillary wave now passes the PhaseRegion graph-owner admission route:
liquid `q_l` from the runtime graph is mapped to gas `q_g`, the `GAS_ABOVE`
graph atlas component reconstructs exactly the same gas cell measure, residual
is zero, the graph energy variation matches finite difference, and the
capillary mode has the correct restoring sign.

This does not yet mean the capillary wave has passed the production
PhaseRegion face-cochain runtime force route.  The adapter keeps
`force_admissible=0` because it stops before building or consuming a
pressure/velocity face cochain.  The remaining unification work is to provide
the graph-chart counterpart of the closed-chart G0--G5 force path and then run
one controlled micro-step through that single interface.

[SOLID-X] Experiment adapter/test/artifact/wiki/ledger only; no solver
algorithm, YAML physical parameter, CFL, damping, smoothing, tolerance
weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU fallback,
production PhaseRegion face-force route, nodal `force_components` route, T/8
runtime run, main merge, branch deletion, worktree removal, or origin push
changed.
