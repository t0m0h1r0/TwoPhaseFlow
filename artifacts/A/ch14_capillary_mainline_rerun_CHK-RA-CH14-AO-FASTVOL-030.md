# CHK-RA-CH14-AO-FASTVOL-030 - Mainline ch14 capillary rerun

## Purpose

User request:

> じゃあ本筋の実験に戻ってやってみて

After the AO-Fast Rung-0 algebraic RCA, this run returns to the checked-in
Chapter 14 mainline capillary-wave experiment.  This is the production
`ch14_capillary` path: FCCD pressure jump, UCCD6 momentum convection,
component-Hodge augmented capillary range projection, dynamic fitted grid, and
`psi` interface transport.  It is not the experimental AO-Fast
`geometric_cell_fraction` packet.

## Command

```text
make cycle EXP=experiment/run.py ARGS="--config ch14_capillary --no-checkpoint-final"
```

Remote execution completed on `python` and pulled results into:

```text
experiment/ch14/results/ch14_capillary/
```

## Outcome

The mainline production capillary-wave run completed.

```text
steps/samples: 1623
final time:    0.035379718894
all tracked scalar histories finite: yes
```

Runtime progress showed the capillary CFL limiter was active throughout:

```text
step=1     t=0.0000  dt=1.844e-05  KE=3.402e-11
step=400   t=0.0087  dt≈2.16e-05  KE=1.211e-05
step=800   t=0.0174  dt≈2.19e-05  KE=2.461e-06
step=1200  t=0.0262  dt≈2.16e-05  KE=1.658e-05
step=1600  t=0.0349  dt≈2.19e-05  KE=8.682e-06
```

Post-run `data.npz` scalar check:

| diagnostic | first | last | min | max |
|---|---:|---:|---:|---:|
| `times` | `1.844403902823e-05` | `3.537971889400e-02` | `1.844403902823e-05` | `3.537971889400e-02` |
| `kinetic_energy` | `3.402263947013e-11` | `8.964120933092e-06` | `3.402263947013e-11` | `1.659421578746e-05` |
| `volume_conservation` | `0.0` | `1.132211301775e-09` | `0.0` | `1.556005272020e-08` |
| `signed_interface_amplitude` | `2.005765439897e-04` | `1.919863385356e-04` | `-1.972980192993e-04` | `2.007632588952e-04` |
| `interface_amplitude` | `2.094115043803e-04` | `2.176214791073e-04` | `2.289029994912e-05` | `2.356660283305e-04` |

Generated/pulled figures:

```text
signed_interface_amplitude.pdf
volume_drift.pdf
kinetic_energy.pdf
psi_t*.pdf
velocity_t*.pdf
pressure_t*.pdf
```

## Interpretation

This mainline experiment did not reproduce the AO-Fast failure.  That is
expected: it uses the mature production capillary stack, not the current
AO-Fast `geometric_cell_fraction` packet.  Therefore the result verifies that
the checked-in Chapter 14 production capillary benchmark is still executable
after the AO-Fast branch changes, but it does not clear the AO-Fast algebraic
blocker from CHK-029.

Physics/mathematics reading:

- The production pressure-jump/component-Hodge route preserves a nonzero
  capillary-wave response and reaches the full snapshot window.
- The maximum volume drift stays below `1.6e-8`, so no gross material-volume
  failure appears in this run.
- The AO-Fast root cause remains separate: its current packet over-projects
  the capillary face covector into the full cell-pressure reaction image and
  deletes the non-static drive.

[SOLID-X] Experiment execution/artifact only; no production solver source,
YAML parameter, CFL reduction, damping, smoothing, curvature cap, FD/WENO/PPE
fallback, hidden PCG/DC fallback, main merge, or AO-Fast workaround was
introduced.
