# CHK-RA-CH14-AO-FASTVOL-048

## Request

Set the Chapter 14 capillary-wave YAML to PCG-only and run the capillary wave for one quarter period.

## YAML Change

`experiment/ch14/config/ch14_capillary.yaml` now runs the first quarter of the configured observed cycle:

- `run.time.final = 0.008899695230`
- `output.snapshots.times = [0.0, 0.002224923808, 0.004449847615, 0.006674771423, 0.008899695230]`
- active projection remains strict PCG-only:
  - `scheme: pcg`
  - `absolute_tolerance: 1.0e-11`
  - `pcg.tolerance: 1.0e-12`
  - no DC fallback

The config parser expectation was updated accordingly.

## Experiment Result

The remote experiment did not complete the requested quarter period.

Command:

```text
make cycle EXP=experiment/run.py ARGS='--config ch14_capillary'
```

Fail-close:

```text
ValueError: GPU AO capillary fail-close: q/phi compatibility residual 2.313133e-11 exceeds tolerance 1.000000e-11; restore q=Q_h(phi) before capillarity
```

The run stopped after the second printed step, at about `t=1.855029080542e-05`, versus the requested target `8.899695230e-03`.

The printed runner diagnostics already showed an unphysical launch:

| step | dt | KE | limiter |
|---|---:|---:|---|
| 1 | `1.844e-05` | `4.502e+01` | capillary |
| 2 | `1.063e-07` | `7.214e+01` | advective |

## RCA Split

The PCG-only policy is not the immediate cause. A stage-chain probe without the runner's initial fitted-grid rebuild still advances small:

```text
make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 3 --active-projection-scheme pcg --active-projection-pcg-tolerance 1e-12 --active-projection-pcg-max-iterations 64'
```

Key values:

- step 1: `ppe_rhs=1.520790e+01`, `div_u=5.145875e-05`
- step 2: `ppe_rhs=6.290552e+02`, `div_u=4.695286e-04`
- step 3: `ppe_rhs=7.746945e+02`, `div_u=7.889478e-04`

Adding a diagnostic flag to reproduce the runner's initial non-uniform fitted-grid rebuild changes the launch scale immediately:

```text
make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 3 --runner-initial-grid-rebuild --active-projection-scheme pcg --active-projection-pcg-tolerance 1e-12 --active-projection-pcg-max-iterations 64'
```

Key values:

- step 1: `u_star=1.044340e+03`, `ppe_rhs=3.732009e+07`, `div_u=6.388738e-02`
- step 2: `ppe_rhs=1.300717e+12`, `div_u=4.817717e+02`
- step 3: `ppe_rhs=2.083042e+12`, `div_u=3.878407e+02`

This identifies the current blocker as the initial non-uniform interface-tracking grid rebuild path, not DC and not the PCG-only active projection policy itself.

## Validation

- `git diff --check` PASS
- local `py_compile experiment/ch14/diagnose_ao_stage_chain.py` PASS
- remote test suite after YAML/test update PASS: `737 passed, 33 skipped`
- remote quarter-period production run FAIL-CLOSE as above
- remote stage-chain without initial rebuild PASS 3 steps
- remote stage-chain with runner initial rebuild reproduces the large launch scale

## Conclusion

The YAML is now PCG-only and configured for the first quarter period, but the capillary-wave experiment cannot yet be certified because production execution fails before reaching the target time. The next root-cause target should be the initial fitted-grid rebuild handoff for active-geometry capillary state: grid metric epoch, q/phi rebuild, active support, pressure-history/prepared-face state, and capillary/PPE Hodge pairing must be checked on the rebuilt non-uniform grid before advancing.
