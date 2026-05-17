# CHK-RA-CH14-VAR-058 - Production Capillary YAML One-Period Run

Date: 2026-05-17

Scope: update the then-canonical capillary-wave YAML route note and run the
legacy production `ch14_capillary` route for one full configured
capillary-wave period.

## YAML Update

Updated:

```text
experiment/ch14/config/legacy/ch14_capillary_legacy_runtime.yaml
```

The existing numerical value already targeted one continuum free-slip
capillary-wave period:

```text
run.time.final = 0.046742983863
```

The original update only clarified that this was the default production-route
one-period target, and that shorter quarter/short probes should use runner
`--final-time` overrides rather than changing the YAML.  No physical parameter,
CFL, solver choice, tolerance, or route flag changed.  This production-runtime
YAML has since been retained under `config/legacy/` after the canonical
`ch14_capillary.yaml` filename moved to the PhaseRegion graph route.

## Remote Experiment

Command:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_capillary --no-checkpoint-final'
```

Result: PASS.

```text
wall time                       = 11m42.352s
samples                         = 2585
final_time                      = 4.674298386300000e-02
signed_interface_amplitude(0)   = 2.002821033747926e-04
signed_interface_amplitude(T/4) = 1.569308987651216e-05
signed_interface_amplitude(T/2) = -1.833499394721940e-04
signed_interface_amplitude(3T/4)= -4.062530437999640e-05
signed_interface_amplitude(T)   = 1.592140754564376e-04
final_amplitude_ratio           = 7.949490881793696e-01
max_kinetic_energy              = 8.280921875848083e-06
final_kinetic_energy            = 1.149639934451300e-06
max_volume_conservation_abs     = 1.044899843732906e-13
final_volume_conservation       = 9.215718466126797e-14
pre_blowup_checkpoint_written   = false
```

The run log advanced through the full cycle with the capillary limiter active
and saved `data.npz` at the configured final time.

## Outputs

Pulled outputs:

```text
experiment/ch14/results/ch14_capillary/data.npz
experiment/ch14/results/ch14_capillary/signed_interface_amplitude.pdf
experiment/ch14/results/ch14_capillary/volume_drift.pdf
experiment/ch14/results/ch14_capillary/kinetic_energy.pdf
experiment/ch14/results/ch14_capillary/psi_t0.000.pdf
experiment/ch14/results/ch14_capillary/psi_t0.012.pdf
experiment/ch14/results/ch14_capillary/psi_t0.023.pdf
experiment/ch14/results/ch14_capillary/psi_t0.035.pdf
experiment/ch14/results/ch14_capillary/psi_t0.047.pdf
experiment/ch14/results/ch14_capillary/velocity_t*.pdf
experiment/ch14/results/ch14_capillary/pressure_t*.pdf
```

Rendered local previews:

```text
/private/tmp/ch14_capillary_one_period_signed_amplitude.png
/private/tmp/ch14_capillary_one_period_psi_final.png
```

## Boundary

This is a production `ch14_capillary` YAML run.  It is not the reduced
PhaseRegion graph oracle.  The pressure PDFs remain scalar gauge diagnostics;
they must not be relabeled as the full AO capillary pressure-reaction face
cochain.

[SOLID-X] YAML comment/artifact/wiki/ledger plus experiment execution only; no
solver algorithm, physical parameter, CFL, damping, smoothing, tolerance
weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU fallback, main
merge, branch deletion, worktree removal, or origin push changed.
