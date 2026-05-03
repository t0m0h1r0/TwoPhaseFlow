# CHK-RA-OSC-N64-012 — Frozen-Interface Curvature Feedback Check

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

CHK-RA-OSC-N64-011 falsified two cut-face curvature reconstruction shortcuts.
The remaining question is whether the large `kappa_Gamma` growth is produced
inside the curvature evaluator itself, or by the pressure/velocity/interface
transport feedback loop that updates `psi`.

## Diagnostic

Extended `experiment/ch14/diagnose_curvature_contract_n64.py` with
`--freeze-interface`, which sets `numerics.interface.tracking.primary=none` and
`enabled=false` for the diagnostic config.  The NS pressure/projection stack
still runs, but the interface field is not advected.

Run:

```bash
make cycle EXP=experiment/ch14/diagnose_curvature_contract_n64.py ARGS="--freeze-interface"
```

The run completed to `T=0.40`.

## Results

Final-step comparison:

| case | band `kappa` std | cut-face `kappa` mean | cut-face `kappa` std | cut-face error RMS | radius std | `m16` radius amp | `m32` radius amp |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline transport | `2.164945e+01` | `3.231471e+00` | `1.066869e+01` | `1.069634e+01` | `5.540336e-04` | `2.238773e-04` | `1.075945e-04` |
| frozen interface | `1.019542e+00` | `4.002476e+00` | `1.659596e-02` | `1.677964e-02` | `2.320123e-05` | `6.396132e-06` | `5.227498e-06` |

The frozen-interface run also kept the cut-face profile gradient healthy:
`min |grad psi| = 1.048392e+01`.

## Inference

The curvature evaluator is not spontaneously generating the N64
`kappa_Gamma` explosion when `psi` is held fixed.  The failure requires the
closed feedback loop:

1. a small pressure/projection residual creates a nonzero velocity field;
2. interface transport advects `psi` by that velocity;
3. tiny profile/position perturbations are amplified by the curvature operator;
4. the amplified Young--Laplace jump drives a larger affine PPE/projection
   correction on the next step.

This explains why exact `kappa=4` and stronger curvature filtering reduce KE
but do not establish a root fix: they weaken one leg of the loop while leaving
the interface-transport feedback path intact.

## Next Unit

Audit the velocity used by interface transport.  The active config already uses
face-flux projection and canonical face state, but the transport API consumes
reconstructed nodal velocities.  The next theory-respecting check should compare
transport with projection-native face fluxes or otherwise prove that the
advecting velocity is discretely compatible with the phase-separated affine PPE
projection.

[SOLID-X] Diagnostic extension only; no production solver/operator boundary
changed and no tested implementation deleted.
