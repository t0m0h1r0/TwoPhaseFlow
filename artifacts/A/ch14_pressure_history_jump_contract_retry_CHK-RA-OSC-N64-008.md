# CHK-RA-OSC-N64-008 — Pressure-History Jump-Contract Retry

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

Retry the nearest shortcut from CHK-RA-OSC-N64-007: make the IPC
previous-pressure predictor term use the same affine pressure-jump face operator
as the projection path, then test whether the N64 static pressure residual
improves.

## Implementation Attempt

Commit `3fee5474` introduced `_previous_pressure_acceleration_nodes()` and routed
affine-jump previous pressure through `div_op.pressure_fluxes(...,
interface_coupling_scheme="affine_jump")` instead of the plain nodal
`pressure_grad_op.gradient(previous_pressure, axis)` path.

Unit-level contract checks passed locally after intaking latest `main`:

```text
3 passed, 48 deselected
```

The full surrounding `test_ns_pipeline_fccd.py` file still has the same 3
current-main failures in viscous Helmholtz DC setup, outside this pressure
history hypothesis.

## Falsification Probe

Remote-first `make cycle` could not use remote in this sandbox and fell back to
local CPU with the shared virtualenv on `PATH`:

```bash
PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH \
  make cycle EXP=experiment/ch14/probe_pressure_history_gradient_n64.py \
  ARGS="--case baseline"
```

The baseline case completed to `T=0.40`, but diagnostics worsened relative to
the CHK-RA-OSC-N64-007 baseline:

| metric | CHK-RA-OSC-N64-007 baseline | retry baseline |
|---|---:|---:|
| max KE | `4.091e-04` | `1.210697e-03` |
| jump error | `2.445e-02` | `3.258439e-01` |
| liquid residual RMS | `2.224e-01` | `1.343469e+00` |
| gas residual RMS | `1.437e-02` | `1.899257e-02` |

## Verdict

FALSIFIED as an implementation fix.  The pressure-history term is still a
plausible coupling path, but directly replacing it with the affine face
pressure flux is not the correct contract for the stored pressure variable.
The result points to a subtler representation issue: distinguish base pressure,
physical jump-bearing pressure, pressure increment, and the operator expected
by predictor history before changing production code.

The solver/test patch was therefore backed out to the latest `main` state.  No
damping, smoothing, CFL tightening, or hidden fallback was added.

[SOLID-X] Failed implementation not retained; no tested code deleted.  The next
unit should audit base-vs-physical pressure storage and derive a static
Young--Laplace equilibrium test before any new code change.
