# CHK-RA-OSC-N64-014 — Projection-Native ψ Transport

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Decision

No new production YAML switch was added.  The existing configuration already
states the mathematical contract:

```yaml
numerics:
  interface:
    transport:
      variable: psi
      spatial: fccd
  projection:
    face_flux_projection: true
    canonical_face_state: true
```

For this contract, the interface transport velocity is not an independent
option.  The only projection-consistent update is to consume the retained
projected face-normal velocity directly:

```text
d_t psi = -D_f(P_f psi * u_f^proj).
```

Adding a YAML choice such as `transport.velocity_source: reconstructed_nodes`
would formalize the broken path found in CHK-013, so it is deliberately not
introduced.

## A3 Chain

| Layer | Contract |
|---|---|
| Equation | Static Young--Laplace droplet equilibrium requires `u=0`, `d_t psi=0`, and `p_l-p_g=sigma/R`. |
| Discretisation | The projected incompressible velocity lives on faces; conservative ψ transport must use the same face field in `-D_f(P_f psi * u_f)`. |
| Code | `FCCDLevelSetAdvection.advance_with_face_velocity` computes `P_f psi`, multiplies by retained projected face velocities, and applies FCCD face divergence. |
| Solver path | `TwoPhaseNSSolver._advance_interface_stage` selects the face-native path when `NSStepState.face_velocity_components` are available. |
| Verification | N64 production diagnostic now matches the previous diagnostic-only face-native control. |

## Implementation

- `src/twophase/levelset/fccd_advection.py` adds a projection-native FCCD ψ
  advance using supplied face-normal velocities without nodal reconstruction.
- `src/twophase/levelset/transport_strategy.py` exposes the face-native path for
  `PsiDirectTransport`, preserving adaptive reinitialization and ψ-space mass
  correction semantics.
- `src/twophase/simulation/ns_pipeline.py` consumes retained projected face
  components for interface transport when the transport supports the contract.
- `src/twophase/tests/test_ns_pipeline_fccd.py` adds focused tests proving the
  face-native transport and pipeline path are selected.

## Validation

```bash
git diff --check
```

PASS.

```bash
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m pytest \
  src/twophase/tests/test_ns_pipeline_fccd.py \
  -k "projection_native_face_velocity or projected_face_velocity" -q
```

PASS: `2 passed, 49 deselected`.

```bash
PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH \
  make test PYTEST_ARGS='twophase/tests/test_ns_pipeline_fccd.py \
  -k "projection_native_face_velocity or projected_face_velocity" -q'
```

Remote was unavailable; Make fell back to local CPU.  PASS:
`2 passed, 546 deselected`.

```bash
PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH \
  make cycle EXP=experiment/ch14/diagnose_curvature_contract_n64.py
```

Remote was unavailable; Make fell back to local CPU.  Completed `T=0.40`.

## N64 Result

| case | final cut-face `kappa` std | final cut-face error RMS | radius std | `m16` amp |
|---|---:|---:|---:|---:|
| production after CHK-014 | `1.855170e+00` | `1.864412e+00` | `9.048483e-05` | `2.447877e-05` |
| CHK-013 diagnostic face-native | `1.855280e+00` | `1.864517e+00` | `9.048645e-05` | `2.447892e-05` |
| CHK-012 frozen interface | `1.659596e-02` | `1.677964e-02` | `2.320123e-05` | `6.396132e-06` |

The production path is now numerically identical to the previous face-native
diagnostic control.  The remaining gap to frozen-interface curvature is a
smaller downstream physics/math problem, not the original nodal-reconstruction
transport shortcut.

## SOLID-X

No SOLID violation found.  The change preserves responsibility boundaries:
FCCD advection owns face-flux discretization, ψ transport owns reinit/mass
correction, and the NS pipeline only chooses the available velocity
representation already carried by `NSStepState`.  No tested implementation was
deleted, and no damping/CFL/smoothing workaround was introduced.
