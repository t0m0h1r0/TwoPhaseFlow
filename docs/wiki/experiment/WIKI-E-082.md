# WIKI-E-082 - Ch14 Production Capillary YAML One-Period PASS

## Claim

The legacy production capillary YAML route explicitly documented its one-period
default target and ran for the full configured period without a runner
final-time override before the canonical filename moved to the PhaseRegion
route.

## Evidence

Artifact:

```text
artifacts/A/ch14_capillary_yaml_one_period_run_CHK-RA-CH14-VAR-058.md
```

YAML:

```text
experiment/ch14/config/legacy/ch14_capillary_legacy_runtime.yaml
run.time.final = 0.046742983863
```

Command:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_capillary --no-checkpoint-final'
```

Result:

```text
samples                       = 2585
final_time                    = 4.674298386300000e-02
final_amplitude_ratio         = 7.949490881793696e-01
max_kinetic_energy            = 8.280921875848083e-06
final_kinetic_energy          = 1.149639934451300e-06
max_volume_conservation_abs   = 1.044899843732906e-13
final_volume_conservation     = 9.215718466126797e-14
pre_blowup_checkpoint_written = false
```

Pulled PDFs include amplitude/volume/kinetic histories and
`psi`, `velocity`, and `pressure` snapshots at the configured phase samples.

## Boundary

The YAML change is comment-only: it changes no physics, numerics, CFL,
tolerance, solver route, or output directory.  Pressure snapshots are scalar
gauge diagnostics, not the full AO pressure-reaction face cochain.

This is legacy production-runtime evidence.  It is not the new PhaseRegion
graph route; use WIKI-E-083 for the corrected new-route `ch14_capillary.yaml`
one-period run.
