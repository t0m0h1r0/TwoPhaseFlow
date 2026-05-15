# CHK-RA-CH14-AO-FASTVOL-042: PCG-only YAML and 10-step Capillary Probe

## Change

Chapter 14 active-geometry projection YAMLs now use the strict PCG-only route:

```yaml
numerics:
  projection:
    active_geometry:
      solver:
        scheme: pcg
        convergence:
          norm: linf
          absolute_tolerance: 1.0e-11
          relative_tolerance: 0.0
          max_iterations: 32
        pcg:
          tolerance: 1.0e-12
          max_iterations: 256
          roundoff_floor: 1.0e-14
```

No `dc` or `fallback` block is declared in the checked-in Chapter 14 YAMLs.
The solver construction test now checks the PCG primary/fallback contract
instead of asserting inactive DC defaults.

## 10-step Probe

Command:

```bash
make run EXP=experiment/ch14/diagnose_ao_gpu_theory_probe.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 10'
```

Result: the run did not reach 10 steps.  It fail-closed at step 3 under the
strict PCG-only tolerance.

Key rows:

| step | t | compatibility | ppe_rhs | div_u | KE |
|---|---:|---:|---:|---:|---:|
| 1 | `3.651782879273e-05` | `0.0` | `1.520790169088e+01` | `5.145875223005e-05` | `8.112259879282e-13` |
| 2 | `7.303565758545e-05` | `2.366460976830e-15` | `1.654729741148e+29` | `3.242616365130e+23` | `3.345783023369e+42` |
| 3 | fail-close | `1.411891e-10 > 1e-11` | n/a | n/a | n/a |

Fail-close message:

```text
GPU AO capillary fail-close: q/phi compatibility residual 1.411891e-10 exceeds tolerance 1.000000e-11; restore q=Q_h(phi) before capillarity
```

## Verdict

The PCG-only YAML change is correct, and the result confirms the remaining
blocker is not DC.  The integrated capillary-wave path still creates an
explosive pressure/PPE state by step 2; the compatibility failure at step 3 is
a downstream hard-gate symptom.

The next root-cause target should be the production pressure-adjoint split
against the actual PPE/divergence operator and face-weight contract used by the
time step, not low-level P1 geometry, common-flux transport, or Schur PCG.

## Validation

```bash
git diff --check
make test PYTEST_ARGS='twophase/tests/test_config_io_fccd.py::test_ch14_capillary_yaml_loads_execution_stack twophase/tests/test_ns_pipeline_fccd.py::test_ch14_capillary_yaml_builds_solver -q'
```

Remote pytest result: `735 passed, 33 skipped`.

## SOLID-X

No physical parameter, CFL, damping, smoothing, curvature cap, FD/WENO/PPE
fallback, dense runtime fallback, coordinate offset workaround, main merge, or
branch deletion was introduced.
