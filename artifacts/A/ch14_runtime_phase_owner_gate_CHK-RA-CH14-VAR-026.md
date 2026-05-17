# CHK-RA-CH14-VAR-026 - Runtime phase-owner gate

Date: 2026-05-17

Scope: Step-after-F1 gate before implementing a PhaseRegion runtime dry-run
adapter.  This checkpoint revalidates the existing Ch14 runtime admission
snapshot and fixes the phase-owner mismatch that must be resolved before new
runtime adapter code.  It does not add code, YAML routes, force coupling,
pressure/velocity projection, long stepping, or T/8.

## Trigger

After graph F1 low-mode KKT passed, the next tempting step was to build a
runtime dry-run adapter.  Reading the current owner layers exposed a theory
boundary:

```text
GeometricPhaseState.q = liquid cell volume q_C
PhaseRegionBatch docstring = Omega_g gas phase region owner
```

The existing runtime snapshot probe remains valuable, but it cannot by itself
authorize a PhaseRegion runtime adapter unless this owner conversion is made
explicit.

## Revalidation

Command:

```text
make cycle EXP=experiment/ch14/diagnose_q_manifold_runtime_admission_probe.py
```

Result: PASS.

```text
residual_l2       = 1.022474608009e-07
relative_l2       = 2.244971032800e-02
residual_area_abs = 1.726838710861e-07
mode_cos_2        = 4.977887457363e-04
compat_linf       = 0.000000000000e+00
force_admissible  = 0.0
```

The result confirms that the current closed-radial runtime-facing
`ProjectionResult` diagnostic still works after the graph F1 changes.

## Hypothesis Table

| Hypothesis | Result | Consequence |
|---|---|---|
| H26-1: The existing runtime admission snapshot still passes under the current branch. | Confirmed | It remains a regression control before runtime work. |
| H26-2: `WIKI-E-068` directly authorizes a PhaseRegion runtime adapter. | Falsified as stated | It authorizes only a `ProjectionResult` snapshot with visible residual, not a new atlas adapter. |
| H26-3: Runtime `q_C` and PhaseRegion `Omega_g` currently name different phase owners. | Confirmed | A dry-run adapter must declare a phase-owner map before constructing `PhaseRegionBatch`. |
| H26-4: A liquid-droplet runtime snapshot can be converted to a gas-region atlas by `q_g = cell_area - q_l` plus `GAS_OUTSIDE` orientation. | Open | This is the next design/implementation gate, not an assumption. |
| H26-5: A PASS snapshot permits force coupling or T/8. | Rejected | `force_admissible=0` remains the hard boundary. |

## Required Next Adapter Contract

The next implementation must pick one explicit owner map:

1. keep `PhaseRegionBatch` as gas-region owner and convert runtime liquid
   volume to gas volume with a visible complement residual; or
2. generalize the region schema naming from `Omega_g` to `Omega_phase` and
   carry the owned phase label through the atlas, measurement, and residual
   report.

Either route must preserve the same A3 chain:

```text
Equation: owned phase region Omega_p
Discretization: q_p = Q_h(R_h), residual r_p = q_T,p - q_p
Code: explicit phase-owner field/map before PhaseRegionBatch measurement
```

Fail-closed conditions:

- no implicit liquid-to-gas complement inside plotting or diagnostics;
- no sign-flipped residual without a report field naming the owned phase;
- no force route while the owner map is diagnostic-only;
- no T/8 or micro-step run before the dry-run adapter records pre/post q,
  component volumes, residual, perimeter, attachment, and `force_admissible=0`.

## Step Status

The practical gate order after this checkpoint is:

```text
Step 3 closed-curve chart oracle: inherited PASS from WIKI-E-067
Step 4 multi-component atlas smoke: inherited PASS from WIKI-E-069
Step 6 runtime dry-run: blocked until phase-owner map is explicit
```

This is not a rollback.  It is the theory alignment needed to prevent the next
adapter from silently mixing liquid `q_C` with gas `Omega_g`.

## Docs Validation

```text
git diff --check = PASS
docs/wiki WIKI count = 419
docs/wiki/experiment WIKI-E count = 71
targeted CHK/wiki/owner scan = PASS
```
