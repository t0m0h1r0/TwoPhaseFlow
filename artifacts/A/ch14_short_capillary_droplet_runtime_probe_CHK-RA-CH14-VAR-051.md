# CHK-RA-CH14-VAR-051 - Short Capillary-Wave and Oscillating-Droplet Runtime Probe

Date: 2026-05-17

Scope: run short-time Chapter 14 capillary-wave and oscillating-droplet probes
without changing tolerances, CFL, rebuild policy, smoothing, damping, or
runtime force routes.

## Commands

Capillary-wave direction baseline:

```text
make cycle EXP=experiment/ch14/diagnose_capillary_direction.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 2 --print-every 1'
```

Capillary-wave YAML runner:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_capillary --final-time 6e-5 --no-checkpoint-final'
```

Oscillating-droplet YAML runner, two-step attempt:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_oscillating_droplet --final-time 1e-4 --no-checkpoint-final'
```

Oscillating-droplet YAML runner, one-step saved probe:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_oscillating_droplet --final-time 2e-5 --no-checkpoint-final'
```

Oscillating-droplet stage-chain grid-rebuild isolation:

```text
make cycle EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_oscillating_droplet.yaml --steps 2 --uniform-grid'
```

## Capillary-Wave Result

The two-step direction baseline reproduced the preserved short-probe behavior:

```text
step 1: t=3.651782879273e-05
        raw_accel_cos= 2.753533350606e+01
        balanced_accel_cos=-2.753533350606e+01
        compat_linf=0

step 2: t=5.575430939397e-05
        raw_accel_cos=-2.808607486053e+01
        balanced_accel_cos= 2.808607486053e+01
        compat_linf=0
        projected_wall_linf=4.676812974746e-10
```

The short YAML runner also completed and saved results:

```text
times = [1.84359886e-05, 3.65462146e-05, 5.46470569e-05, 6.00000000e-05]
kinetic_energy(final) = 4.96689525e-10
max(volume_conservation) = 4.20128342e-15
signed_interface_amplitude(final) = 2.0026e-04
```

Outputs:

```text
experiment/ch14/results/ch14_capillary/data.npz
experiment/ch14/results/ch14_capillary/signed_interface_amplitude.pdf
experiment/ch14/results/ch14_capillary/volume_drift.pdf
experiment/ch14/results/ch14_capillary/kinetic_energy.pdf
experiment/ch14/results/ch14_capillary/psi_t0.000.pdf
experiment/ch14/results/ch14_capillary/velocity_t0.000.pdf
experiment/ch14/results/ch14_capillary/pressure_t0.000.pdf
```

## Oscillating-Droplet Result

The dynamic nonuniform YAML runner completed one step and saved results when
`final-time` was set below the second-step rebuild:

```text
time = [2.00000000e-05]
kinetic_energy = [5.9046858e-08]
volume_conservation = [0]
signed_deformation = [-5.44313e-03]
```

Outputs:

```text
experiment/ch14/results/ch14_oscillating_droplet/data.npz
experiment/ch14/results/ch14_oscillating_droplet/signed_deformation.pdf
experiment/ch14/results/ch14_oscillating_droplet/volume_drift.pdf
experiment/ch14/results/ch14_oscillating_droplet/kinetic_energy.pdf
experiment/ch14/results/ch14_oscillating_droplet/psi_t0.000.pdf
experiment/ch14/results/ch14_oscillating_droplet/velocity_t0.000.pdf
experiment/ch14/results/ch14_oscillating_droplet/pressure_t0.000.pdf
```

The two-step dynamic nonuniform attempt failed closed after completing the
first step:

```text
RuntimeError:
grid rebuild received projection-native face history but the active reprojector
cannot reproject face cochains
```

This is not a capillary CFL or tolerance issue.  It is the same ownership
boundary identified by the G5 review: projected face arrays can be produced,
but a controlled runtime consumer/reprojector for face cochains across grid
rebuild is not yet implemented.

The stage-chain isolation with `--uniform-grid` completed two manual steps:

```text
step 2 t                         = 7.303565758545e-05
ao_compat                        = 6.265855566819e-12
young_laplace_normal_residual    = 3.953852900934e-13
projected_face_div               = 5.720146578625e-13
geometric_div                    = 1.563194018672e-13
div_u                            = 5.720146578625e-13
ppe_dc_converged                 = 1
```

This localizes the immediate two-step failure to the dynamic nonuniform
grid-rebuild face-history boundary, not to the per-step pressure/corrector
algebra on a fixed grid.

## Failed Diagnostic Kept

`diagnose_droplet_volume_rca.py --steps 2` is currently not a valid short
droplet gate for this config.  It starts with a valid dynamic-diffuse direct
reinitialization probe:

```text
DIRECT_REINIT dynamic_diffuse status=OK
mass_rel=+0
sharp_area_rel=+0
```

but then tries `volume_constraint=sharp_phase_volume` with a reinitializer
method for which that constraint is not implemented:

```text
interface.reinitialization.profile.volume_constraint is only implemented for
method='ridge_eikonal'
```

That stale diagnostic branch was not repaired or used as evidence for
oscillating-droplet success.

## Verdict

Short capillary-wave runtime probing is admitted and reproduced.  Oscillating
droplet is admitted only for a one-step saved dynamic nonuniform probe and for
a two-step fixed-grid stage-chain isolation.  Dynamic nonuniform two-step
runtime remains blocked by face-cochain history reprojection across grid
rebuild.  This is exactly the next implementation gate before micro-step or
T/8.

[SOLID-X] Experiment execution and evidence only; no code, YAML, solver
algorithm, physical parameter, CFL, damping, smoothing, tolerance weakening,
rebuild skipping, FD/WENO/PPE fallback, hidden CPU fallback, production
PhaseRegion runtime force route, nodal `force_components` route, T/8 run, main
merge, branch deletion, worktree removal, or origin push changed.
