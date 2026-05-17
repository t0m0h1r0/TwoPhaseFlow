# CHK-RA-CH14-VAR-057 - Production Capillary Wave T/4 Pressure/Velocity Run

Date: 2026-05-17

Scope: run the production `ch14_capillary` capillary-wave route to one quarter
period and inspect the pressure and velocity field visualizations.

## Command

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_capillary --final-time 0.011685745966 --no-checkpoint-final'
```

The target time is the configured continuum capillary-wave quarter period:

```text
T/4 = 0.011685745966 s
```

## Result

The production run completed and pulled updated result files from the remote
host.

```text
final_time                    = 0.011685745966
samples                       = 646
signed_interface_amplitude(0) = 2.0028210337479256e-04
signed_interface_amplitude(T/4)
                              = 1.5909283700088754e-05
amplitude_ratio               = 7.943437497417001e-02
max_kinetic_energy            = 8.293415463836741e-06
final_kinetic_energy          = 7.996343117473647e-06
max_volume_conservation       = 4.973777466277256e-14
final_volume_conservation     = 4.458781434346641e-14
```

The run log reached step 600 at `t=0.0109`, then saved `data.npz` at the exact
requested final time.

## Pulled Visualizations

The T/4 field outputs were pulled as:

```text
experiment/ch14/results/ch14_capillary/velocity_t0.012.pdf
experiment/ch14/results/ch14_capillary/pressure_t0.012.pdf
```

Rendered local previews:

```text
/private/tmp/ch14_capillary_Tquarter_velocity.png
/private/tmp/ch14_capillary_Tquarter_pressure.png
```

The pressure figure is the configured scalar gauge diagnostic
`p - <p>`.  It is not a replacement for the AO capillary pressure-reaction face
cochain.

## Boundary

This is a production `ch14_capillary` runtime run, not the reduced PhaseRegion
graph oracle from CHK-RA-CH14-VAR-056.  The output directory also contains older
snapshots from previous full-period runs; the T/4 files listed above are the
ones pulled by this run.

[SOLID-X] Experiment execution/artifact/wiki/ledger only; no code, solver
algorithm, YAML physical parameter, CFL, damping, smoothing, tolerance
weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU fallback, main
merge, branch deletion, worktree removal, or origin push changed.
