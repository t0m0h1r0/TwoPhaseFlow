# WIKI-E-081 - Ch14 Production Capillary T/4 Pressure/Velocity PASS

## Claim

The production `ch14_capillary` route runs to the configured quarter period
`T/4 = 0.011685745966 s` and produces pressure and velocity field PDFs at the
quarter-period snapshot.

## Evidence

Artifact:

```text
artifacts/A/ch14_capillary_production_quarter_pressure_velocity_CHK-RA-CH14-VAR-057.md
```

Command:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_capillary --final-time 0.011685745966 --no-checkpoint-final'
```

Metrics from `experiment/ch14/results/ch14_capillary/data.npz`:

```text
final_time                = 0.011685745966
samples                   = 646
amplitude_ratio           = 7.943437497417001e-02
max_kinetic_energy        = 8.293415463836741e-06
final_kinetic_energy      = 7.996343117473647e-06
max_volume_conservation   = 4.973777466277256e-14
final_volume_conservation = 4.458781434346641e-14
```

Pulled quarter-period field PDFs:

```text
experiment/ch14/results/ch14_capillary/velocity_t0.012.pdf
experiment/ch14/results/ch14_capillary/pressure_t0.012.pdf
```

## Boundary

The pressure plot is the configured scalar gauge diagnostic `p - <p>`.  It must
not be read as the full AO capillary pressure-reaction face cochain.  This card
records the production YAML T/4 run; use WIKI-E-080 for the reduced
PhaseRegion graph T/16 oracle.
