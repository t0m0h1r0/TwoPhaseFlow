# CHK-RA-CH14-VAR-033 - PhaseRegion runtime force dry-run

Date: 2026-05-17

Scope: add and validate a zero-step Ch14 runtime force dry-run for the
PhaseRegion variational route.  This checkpoint does not advance time, connect
the force to pressure/velocity, run nonlinear optimization, micro-step, or run
T/8.

## Motivation

`CHK-RA-CH14-VAR-030` proved that the Ch14 runtime liquid measure can be mapped
to the PhaseRegion gas owner, and `CHK-RA-CH14-VAR-032` proved the fixed-stratum
energy-to-face-cochain work identity in an endpoint oracle.  The next gate is
to place that identity on the actual Ch14 oscillating-droplet runtime snapshot
without changing the state.

The diagnostic keeps the physical ownership split explicit:

```text
runtime owns q_l
PhaseRegion owns q_g = |C| - q_l
phi is only the runtime chart/gauge for the same initial interface
```

It then checks the fixed-stratum face-work identity on the runtime admission
grid:

```text
T_h(u_f) = -D_f(psi_f u_f)
s_f = -M_f^{-1} T_h^T dE_h
dE_h[T_h(u_f)] + <s_f, u_f>_{M_f} = 0
```

## Implementation

Added:

```text
experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

The script:

1. reads `experiment/ch14/config/ch14_oscillating_droplet.yaml`;
2. constructs the runtime initial `GeometricPhaseState` on the admission grid;
3. maps runtime liquid volume to PhaseRegion gas owner via
   `map_cell_measure_to_phase_owner`;
4. constructs runtime `psi = H(-phi)` from the same chart without rebuilding or
   advancing the state;
5. builds CCD/FCCD/FCDDivergence operators on the runtime grid;
6. forms the face mass metric from nodal runtime density
   `rho_g + (rho_l-rho_g) psi`;
7. assembles the closed-interface Riesz face cochain;
8. checks self and mixed-probe fixed-stratum virtual work;
9. reports weighted pressure range/Hodge and component-reaction diagnostics;
10. saves a visualization of runtime `q_l`, owner `q_g`, `psi`, the face
    cochain, Hodge residual magnitude, and metric bars.

## Preserved Failed Attempts

The first runtime metric attempt passed a cell density array into
`face_mass_components`.  It failed because the face metric expects nodal
density with shapes compatible with x/y face arrays.  The accepted version uses
the runtime nodal `psi` chart to build nodal density before face averaging.

The first virtual-work attempt used the full self acceleration as the finite
difference velocity.  It failed because the perturbation crossed the fixed
stratum.  That is a chart-admissibility failure, not a physics failure.

The next attempt scaled only to a larger sign-margin fraction and stayed inside
the stratum, but the finite-difference power residual was
`3.877e-05`.  The final diagnostic scales the virtual displacement to `2%` of
the sign margin, keeping the finite-difference derivative local; with unchanged
work tolerances this gives `2.48e-07`.  This is not tolerance weakening,
damping, smoothing, CFL retuning, or rebuild skipping.

## Equation -> Discretization -> Code

| Equation | Discretization | Code |
|---|---|---|
| `q_g = |C| - q_l` | exact finite-volume phase-owner complement | `map_cell_measure_to_phase_owner` |
| `psi = H(-phi)` | runtime chart/gauge evaluated on admission nodes | `_phase_state_on_admission_grid`, `heaviside` |
| `rho = rho_g + (rho_l-rho_g) psi` | nodal density for runtime face mass metric | `_compute`, `face_mass_components` |
| `T_h(u_f)=-D_f(psi_f u_f)` | FCCD/FVM fixed-stratum transport increment | `transport_increment_from_face_velocity` |
| `s_f=-M_f^{-1}T_h^T dE_h` | closed-interface Riesz face cochain on runtime metric | `closed_interface_riesz_cochain` |
| `dE_h[T_h(u_f)] + <s_f,u_f>_{M_f}=0` | self and mixed-probe virtual-work checks | `fixed_stratum_virtual_work_check` |
| pressure range/Hodge split | weighted diagnostic face decomposition | `weighted_hodge_decomposition` |
| component pressure reaction | component reaction residual gate | `component_reaction_hodge_gate` |

## Validation Result

Final remote command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Result: PASS.

```text
runtime_steps                    = 0.000000000000e+00
complement_used                  = 1.000000000000e+00
liquid_runtime_volume            = 7.757513792175e-05
gas_target_volume                = 3.224248620783e-04
compat_linf                      = 0.000000000000e+00
stratum_sign_margin              = 2.147233752119e-03
self_fd_power_residual           = 2.481405282624e-07
self_riesz_residual              = 0.000000000000e+00
self_velocity_scale              = 4.684248775783e-04
self_finite_difference           = -3.495283061789e-01
self_capillary_power             = 3.495281327147e-01
probe_fd_power_residual          = 2.481363539023e-07
probe_riesz_residual             = 0.000000000000e+00
probe_velocity_scale             = 4.684198678970e-04
probe_finite_difference          = -3.495245680623e-01
probe_capillary_power            = 3.495243946029e-01
component_weighted_l2            = 2.731625086117e+01
range_weighted_l2                = 2.731087326821e+01
hodge_weighted_l2                = 5.419985591685e-01
hodge_divergence_linf            = 1.083435563487e-09
reaction_beta                    = -1.429861912470e+01
reaction_residual_weighted_l2    = 3.847025435106e-01
reaction_residual_ratio          = 7.097851774750e-01
reaction_residual_divergence_linf = 2.313299773959e-09
sigma                            = 7.280000000000e-02
rho_l                            = 9.982000000000e+02
rho_g                            = 1.204000000000e+00
grid_alpha                       = 2.000000000000e+00
min_dx                           = 5.050147560497e-04
force_admissible                 = 0.000000000000e+00
```

Local outputs pulled from remote:

```text
experiment/ch14/results/diagnose_phase_region_runtime_force_dry_run/data.npz
experiment/ch14/results/diagnose_phase_region_runtime_force_dry_run/phase_region_runtime_force_dry_run.pdf
```

The PDF is nonempty (`127K`) and visualizes the runtime snapshot, owner
measure, face cochain, and residual bars.

## Code Review

[SOLID-X] no violation.  The new code is an experiment diagnostic and reuses
existing runtime config, `GeometricPhaseState`, phase-owner mapping,
closed-interface Riesz, FCCD divergence, and Hodge diagnostics.  It does not
add or modify a production force path, pressure/velocity adapter, runtime YAML
route, solver algorithm, nonlinear optimizer, smoothing, damping, CFL
retuning, tolerance weakening, rebuild skipping, FD/WENO/PPE fallback, hidden
CPU fallback, or micro-step.

## Theory Consistency

The dry-run keeps the PhaseRegion principle intact:

```text
Omega_g owns the physical phase region
q_g is its finite-volume measure
Gamma is the boundary represented by the runtime phi chart
surface energy produces a face cochain through the same runtime face metric
```

The result says the runtime initial interface can support a local
fixed-stratum face-work diagnostic with explicit `q_l -> q_g` ownership and
nodal-density face metric.  It does not yet say the Ch14 runtime can advance
with that force, because the Hodge and reaction diagnostics are still only
reported and `force_admissible = false`.

The next gate should design the production-adjacent force adapter boundary:
which object owns the PhaseRegion `Omega_g` state, how the runtime `phi` gauge
is synchronized without redefining `q`, and how pressure/velocity coupling will
consume the face cochain.  It should remain zero-step or adapter-only until
that ownership boundary is explicit.

## Final Validation

```text
git diff --check = PASS
remote make cycle = PASS
docs/wiki WIKI count = 426
docs/wiki/experiment WIKI-E count = 75
targeted CHK/wiki/script scan = PASS
```
