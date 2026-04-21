# CHK-172: face-flux projection PoC for ch13_05 alpha=2 bubble

Date: 2026-04-21
Branch: `worktree-rising-bubble`
Execution: remote GPU via `./remote.sh run`

## Goal

CHK-171 identified a projection closure mismatch on the alpha=2 non-uniform
wall grid:

```text
PPE matrix:   A_FVM(rho_face^-1)
Corrector:    nodal rho_i^-1 G_avg p
```

CHK-172 tested whether a minimal face-flux projection can remove the early
`t≈0.007` blowup in the rising-bubble case.

## Implementation

Added experimental face-projection primitives to
`src/twophase/simulation/gradient_operator.py`:

- `face_fluxes(components)`
- `pressure_fluxes(p, rho)`
- `project(components, p, rho, dt, force_components)`
- `reconstruct_nodes(face_components)`

The opt-in flag is:

```yaml
run:
  face_flux_projection: true
```

The default remains `false`. The probe config is:

`experiment/ch13/config/ch13_05_rising_bubble_fullstack_alpha2_faceproj_debug.yaml`

## Verification

Local targeted check:

- `py_compile` for `config_io.py`, `gradient_operator.py`, `ns_pipeline.py`
- `PYTHONPATH=src ... pytest src/twophase/tests/test_ns_pipeline_fccd.py -q`
- result: `6 passed`

## Remote GPU result

| Case | Result | Diagnostics |
|---|---|---|
| default FVM-divergence path | BLOWUP step 27, `t=0.007149` | `KE=1.05e6`, max `bf_residual=3.99e11`, max `div_u=9.73e4` |
| face projection opt-in | BLOWUP step 29, `t=0.007532` | `KE=3.07e6`, max `bf_residual=5.50e12`, max `div_u=1.49e5` |

## Interpretation

The face projection PoC delays blowup slightly but does not solve the
projection closure. A stricter face-preserving reconstruction was also tested
and made the run worse (BLOWUP step 23), so it was restored to the averaged
nodal reconstruction and gated behind `face_flux_projection`.

The failure point is no longer just the pressure gradient metric. The remaining
problem is that the solver state is nodal, while the stable projection lives on
normal faces. Reconstructing a nodal velocity after the projection loses the
exact face flux that the PPE solved for, and wall no-slip enforcement further
breaks the projected face divergence.

## Next countermeasure

The next viable design is a staggered/face-flux projection state:

1. Carry normal face fluxes as a first-class projection variable.
2. Apply PPE correction directly to those face fluxes using `PPEBuilder`'s
   harmonic face coefficient.
3. Use face divergence as the projection gate.
4. Reconstruct nodal velocity only for advection/convection diagnostics, not
   as the source of truth for incompressibility.

The CHK-172 opt-in PoC is useful as a diagnostic scaffold, but not a production
fix.
