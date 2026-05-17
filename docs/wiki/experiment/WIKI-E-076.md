---
ref_id: WIKI-E-076
title: "Ch14 Short Capillary/Droplet Runtime Probe"
domain: experiment
status: ACTIVE
tags: [ch14, capillary_wave, oscillating_droplet, short_runtime, face_history, grid_rebuild, fail_close]
sources:
  - path: artifacts/A/ch14_short_capillary_droplet_runtime_probe_CHK-RA-CH14-VAR-051.md
    description: "Command log, metrics, and verdict for the short capillary-wave and oscillating-droplet probes"
  - path: experiment/ch14/results/ch14_capillary/data.npz
    description: "Short capillary-wave YAML runner result"
  - path: experiment/ch14/results/ch14_oscillating_droplet/data.npz
    description: "One-step oscillating-droplet YAML runner result"
  - path: docs/wiki/experiment/WIKI-E-075.md
    description: "G0--G5 zero-step face-force dry-run boundary"
depends_on:
  - "[[WIKI-E-064]]"
  - "[[WIKI-E-075]]"
consumers:
  - domain: experiment
    usage: "Use before any dynamic nonuniform oscillating-droplet micro-step or T/8 attempt"
  - domain: code
    usage: "Use before implementing face-cochain history reprojection across grid rebuild"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Short Capillary/Droplet Runtime Probe

## Knowledge Card

The short capillary-wave runtime path remains admitted.  The oscillating
droplet can run and save a one-step dynamic nonuniform result, but a two-step
dynamic nonuniform run fails closed at grid rebuild:

```text
grid rebuild received projection-native face history but the active reprojector
cannot reproject face cochains
```

This is the current runtime experiment boundary.  Do not interpret it as a
CFL, tolerance, or smoothing problem.

## Capillary Wave

Direction baseline:

```text
make cycle EXP=experiment/ch14/diagnose_capillary_direction.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 2 --print-every 1'
```

Result: PASS.

```text
step 1 raw_accel_cos= 2.753533350606e+01 balanced_accel_cos=-2.753533350606e+01 compat_linf=0
step 2 raw_accel_cos=-2.808607486053e+01 balanced_accel_cos= 2.808607486053e+01 compat_linf=0
```

Short YAML runner:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_capillary --final-time 6e-5 --no-checkpoint-final'
```

Result: PASS.  The saved result reaches `t=6e-5`, has final kinetic energy
`4.96689525e-10`, and max volume drift `4.20128342e-15`.

## Oscillating Droplet

One-step dynamic nonuniform YAML runner:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_oscillating_droplet --final-time 2e-5 --no-checkpoint-final'
```

Result: PASS.

```text
time = [2.00000000e-05]
kinetic_energy = [5.9046858e-08]
volume_conservation = [0]
signed_deformation = [-5.44313e-03]
```

Two-step dynamic nonuniform attempt:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_oscillating_droplet --final-time 1e-4 --no-checkpoint-final'
```

Result: FAIL-CLOSE at the second-step grid rebuild after the first step
completed.

Fixed-grid isolation:

```text
make cycle EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_oscillating_droplet.yaml --steps 2 --uniform-grid'
```

Result: PASS for the two-step stage-chain isolation:

```text
ao_compat                     = 6.265855566819e-12
young_laplace_normal_residual = 3.953852900934e-13
projected_face_div            = 5.720146578625e-13
geometric_div                 = 1.563194018672e-13
div_u                         = 5.720146578625e-13
ppe_dc_converged              = 1
```

## Practice

The next implementation gate is not "run T/8 with a smaller CFL" and not
"skip rebuild."  It is a controlled dynamic nonuniform single-step/two-step
consumer for projection-native face history:

```text
projected face cochain at grid epoch n
-> grid rebuild / metric epoch update
-> admissible face cochain at grid epoch n+1
-> pressure/velocity work and divergence checks
```

Until that exists, capillary-wave short probes are regression controls, and
oscillating-droplet dynamic nonuniform runtime is admitted only up to the saved
one-step probe.
