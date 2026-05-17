# CHK-RA-CH14-VAR-053 - PhaseRegion Capillary Graph Few-Step Experiment

Date: 2026-05-17

Scope: make the new PhaseRegion graph route move for a few Ch14 capillary-wave
steps, while keeping the boundary explicit: this is a reduced graph-chart
experiment, not a production Navier--Stokes face-force runtime connection.

## Motivation

CHK-RA-CH14-VAR-052 passed the Ch14 capillary-wave initial state through the
PhaseRegion owner/admission route:

```text
runtime q_l -> q_g=|C|-q_l -> GAS_ABOVE graph PhaseRegionBatch
```

That was a zero-step admission proof.  The next minimal dynamic gate is a
few-step graph experiment in which the PhaseRegion-owned graph state advances,
then re-derives `q_l`, `q_g`, `E_h`, and residual diagnostics every step.

## Implemented Experiment

Added:

```text
experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
```

The experiment reads `ch14_capillary.yaml`, builds the same diagnostic fitted
grid, and owns the graph state through a volume-free capillary-wave modal
basis.  The stepping equation is the linearized variational oscillator:

```text
E_h[eta] = sigma sum_i sqrt(dx_i^2 + (eta_{i+1}-eta_i)^2)
K_h      = d^2 E_h / dA^2 at the flat graph
omega^2  = sigma k^3 / (rho_l coth(k h_l) + rho_g coth(k h_g))
M_mode   = K_h / omega^2
M_mode A'' + K_h A = 0
```

The amplitude is stepped by velocity-Verlet.  At each time level, the
experiment rebuilds:

```text
eta -> q_l = Q_h(eta)
q_g = |C| - q_l
PhaseRegionBatch(GAS_ABOVE graph)
assemble_phase_region_measurement(...)
```

and checks exact linear reference, energy drift, volume drift, and residuals.

The first attempt used the nonlinear perimeter derivative directly while
checking against the linear capillary-wave exact solution.  That failed the
velocity reference gate, as it should: finite-amplitude nonlinear perimeter
induces a small nonlinear frequency shift.  The accepted gate therefore uses
the second variation of the same `E_h`, matching the linear capillary-wave
reference it is required to verify.

## Remote Experiment

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
```

Result: PASS.

```text
phase_region_graph_steps_admitted = 1
steps                             = 8
dt                                = 2.000000000000e-05
t_final                           = 1.600000000000e-04
t_over_T                          = 3.422973605371e-03
max_amplitude_error               = 2.785727377941e-14
max_velocity_error                = 3.482433087558e-10
max_energy_drift                  = 8.356546623106e-10
max_residual_l2                   = 0.000000000000e+00
max_volume_drift                  = 2.710505431214e-20
final_amplitude                   = 1.999537458869e-04
final_exact_amplitude             = 1.999537459147e-04
force_admissible                  = 0
```

Outputs:

```text
experiment/ch14/results/diagnose_phase_region_capillary_graph_steps/data.npz
experiment/ch14/results/diagnose_phase_region_capillary_graph_steps/phase_region_capillary_graph_steps.pdf
```

## Remote Tests

Command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_measure.py -q'
```

Result: PASS.  The current remote make target ran the suite under its
configured root:

```text
867 passed, 35 skipped
```

## Verdict

The new route now moves for a few capillary-wave steps at the PhaseRegion graph
state level.  The run keeps `q` derived from the graph owner, preserves phase
volume, exposes zero residual, and tracks the exact linear capillary-wave
solution over eight steps.

This does not yet connect the graph route to the production pressure/velocity
face-force consumer.  `force_admissible=0` remains correct.  The next gate is
the graph-chart counterpart of G0--G5:

```text
PhaseRegion graph dE
-> transport adjoint face cochain s_f
-> same M_f pressure/velocity work gates
-> controlled micro-step consumer
```

[SOLID-X] Experiment stepper/artifact/wiki/ledger only; no solver algorithm,
YAML physical parameter, CFL, damping, smoothing, tolerance weakening, rebuild
skipping, FD/WENO/PPE fallback, hidden CPU fallback, production graph
PhaseRegion face-force route, nodal `force_components` route, T/8 runtime run,
main merge, branch deletion, worktree removal, or origin push changed.
