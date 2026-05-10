# CHK-RA-CH14-BUBBLE-PPE-DC-001 — rising-bubble blow-up RCA and PPE defect-correction fix

## Request

Investigate the Chapter 14 rising-bubble blow-up from first principles:

- generate many hypotheses from physics, mathematics, computation, and software design;
- state the constraint, invariant, consistency condition, or implementation contract each hypothesis would break;
- order verification efficiently with unit tests, manufactured/one-step probes, and short comparison experiments;
- reject shortcuts, parameter tuning, fallback branches, and case-specific fixes;
- implement only theoretically admissible fixes;
- record theory, validation, implementation, and negative knowledge.

Canonical experiment SSoT remained
`experiment/ch14/config/ch14_rising_bubble.yaml`.  The YAML grid is `[32,64]`.

## Observed Failure

The prior remote GPU run with

```sh
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make cycle EXP=experiment/run.py \
  ARGS="--config ch14_rising_bubble --final-time 0.03 --checkpoint-interval 0.01"
```

did not reach `T=0.03`.

Key observed values:

| Quantity | Value |
|---|---:|
| final time | `2.367834126506e-02` |
| samples | `3372` |
| final kinetic energy | `2.974161792852e+06` |
| final volume conservation | `7.381674992093e-06` |
| pre-blowup checkpoint | `checkpoint_pre_blowup_input.npz`, `t=2.367827075068e-02` |
| final checkpoint | `checkpoint_final.npz`, `t=2.367834126506e-02` |

The blow-up was not a slow phase-volume drift: volume error stayed near
`1e-5`, while pressure, divergence, and PPE residual exploded.

## Hypothesis Inventory

| ID | Hypothesis | Broken contract if true | Verdict |
|---|---|---|---|
| H1 | Physical water-air acceleration at 10 mm scale | Dimensional rise speed and pressure scale should remain physical, about cm/s to dm/s, not `1e3 m/s` | Rejected |
| H2 | Phase volume loss drives the failure | Conserved liquid/gas volume should drift before velocity energy | Rejected: volume error stayed `7.4e-06` at final |
| H3 | Capillary CFL violation | Explicit capillary stability bound should be exceeded before growth | Rejected: the original capillary-limited step was small; instability appeared after pressure/PPE residual growth |
| H4 | Interface cut-edge stratum singularity | Cut geometry transversality, no near-zero `dpsi` on crossings | Rejected: checkpoint probes showed no singular cut-edge denominator |
| H5 | Wall or periodic boundary topology error | Boundary trace or periodic quotient should localize the defect | Not primary: largest growth localized near gas-side interface, not a wall-only mode |
| H6 | Component Hodge saddle uses the wrong metric under inexact projection | Positive Hodge Gram matrix, saddle constraint measured in the projected Hodge space | Confirmed contract bug; fixed, but not sufficient alone |
| H7 | PPE defect correction with fixed relaxation overshoots in high-density affine-jump state | PPE residual monotonicity, incompressibility projection, and pressure-adjoint Hodge consistency | Confirmed root blow-up trigger |
| H8 | More defect-correction iterations with the old relaxation will cure it | Defect correction should reduce residual as iterations increase | Rejected: residual and kinetic energy grew catastrophically |
| H9 | Smaller fixed relaxation is an acceptable production fix | Algorithmic residual minimization should not depend on case-tuned damping | Rejected as negative knowledge |
| H10 | Brute-force full rerun is the fastest diagnostic | Efficient RCA should isolate the failing step before spending GPU time | Rejected: checkpoint one-step and short continuation probes isolate the defect faster |

## Efficient Verification Order

1. Inspect existing `data.npz` time history.
2. Use checkpoint probes around `t=0.02` and the pre-blowup state.
3. Measure volume, pressure, velocity, divergence, PPE residual, and component-Hodge denominator.
4. Run manufactured unit probes for the algebraic contracts.
5. Run one-step probes from `checkpoint_pre_blowup_input.npz`.
6. Run short continuation from `checkpoint_t0p02.npz` across the old blow-up time.

This ordering avoids spending a full GPU run to rediscover the same late-step
failure.

## Diagnostic Results

Time-history RCA:

| Indicator | First decisive signal |
|---|---|
| `KE >= 1e-3` | step `3323`, `t=2.349722646815e-02` |
| `KE >= 0.01` | step `3348`, `t≈2.366405393326e-02` |
| `KE >= 0.1` | step `3371`, `t=2.367827075068e-02` |
| final `KE` | `2.974161792852e+06` |
| final `ppe_dc_final_relative_l2` | `5.45089e+02` |
| final `div_u_max` | `2.691e+09` |
| final `bf_residual_max` | `4.044e+14` |
| final `ppe_rhs_max` | `1.142e+14` |

The old component-Hodge denominator became non-positive before catastrophic
growth:

```text
t=2.346187102658e-02, denominator=-5.577468193604e-04,
ppe_dc_final_relative_l2=1.237828306745e-02,
KE=6.409512863361e-04
```

This proved an inexact-projection metric bug in the diagnostic/correction
split.  However, after fixing the Hodge metric alone, the one-step pre-blowup
probe still reproduced the kinetic-energy explosion.  Therefore H6 was a real
contract bug but not the root trigger.

Defect-correction negative probes from the same pre-blowup checkpoint:

| Variant | One-step kinetic energy | PPE relative residual | Verdict |
|---|---:|---:|---|
| old fixed relaxation, `max_corrections=12` | `2.974e+06` | `5.45e+02` | failure |
| old fixed relaxation, `max_corrections=24` | `2.45e+12` | `4.95e+05` | worse |
| old fixed relaxation, `max_corrections=48` | `1.66e+24` | `4.08e+11` | worse |
| old fixed relaxation, `max_corrections=96` | `7.67e+47` | `2.77e+23` | worse |
| fixed relaxation `0.3` | `3.84e-02` | `2.63e-05` | residual tuning, not production |
| fixed relaxation `0.1` | `4.06e-02` | `6.46e-02` | residual tuning, not production |
| fixed relaxation `0.03` | `3.44e-01` | `5.10e-01` | residual tuning, not production |

Residual-minimizing defect correction from the same pre-blowup checkpoint:

| Variant | One-step kinetic energy | PPE relative residual | Notes |
|---|---:|---:|---|
| monotone DC, `max_corrections=12` | `3.837536077e-02` | `2.456e-06` | no blow-up |
| monotone DC, `max_corrections=20` | same scale | `5.13e-09` | converged |

Short continuation with the implemented monotone DC:

| Probe | Outcome |
|---|---|
| from `checkpoint_t0p02` to `T=0.024` | reached `T=0.024`, crossing the old blow-up time safely; final `KE≈6.59e-04` |
| from `checkpoint_t0p02` to `T=0.03` | reached `T=0.03`; final `KE=8.406284133398e-04`; max `ppe_dc_final_relative_l2≈2.2547e-03`; volume relative drift `≈3.13e-06` |

The continuation probes are targeted RCA probes, not a replacement for a final
remote benchmark rerun.  They are sufficient to identify the late-step
residual-growth trigger and to reject the old fixed-relaxation path.

## Implemented Fixes

### Hodge-Metric Saddle Projection

File:

- `src/twophase/simulation/interface_projection_diagnostics.py`

The component saddle system now builds both matrix and RHS in the projected
Hodge metric:

```text
G_ij = <H c_i, H c_j>_M,
b_i  = <H c_i, H raw>_M.
```

The old algebra used `<c_i, H c_j>_M`, which is equivalent only for an exact
self-adjoint projection.  In an inexact graph/pressure projection, it could
produce a negative one-component denominator and an invalid saddle coefficient.

### Residual-Minimizing Defect Correction

File:

- `src/twophase/ppe/defect_correction.py`

The GPU-only fixed-iteration path was removed.  CPU and GPU now use the same
residual-monotone contract.  At each correction:

```text
r = b - A p,
delta = base_solve(r),
alpha_* = <r, A delta> / <A delta, A delta>,
p_trial = p + alpha delta.
```

The exact residual-minimizing `alpha_*` is tried first if positive.  The
configured relaxation and a short geometric backtracking sequence are retained
only as generic line-search candidates.  A candidate is accepted only if it
strictly reduces the discrete PPE residual.  If no candidate reduces the
residual, the iteration fails closed instead of injecting an amplified pressure
state.

This is not damping, a CFL adjustment, a fallback solver, or a benchmark branch.
It enforces the algebraic contract of defect correction: each accepted
correction must reduce the residual of the operator being corrected.

## Adopted / Rejected Remedies

| Candidate | Theory | Design | GPU/performance | YAML/API impact | Decision |
|---|---|---|---|---|---|
| Residual-minimizing line search in DC | Direct minimizer for `||b-Ap||_2` along the correction direction | Same solver and diagnostics; unified CPU/GPU route | Extra `A delta` and scalar reductions per correction; GPU-suitable with limited sync cost | none | Adopt |
| Projected-Hodge Gram/RHS | Restores positive metric and adjoint meaning under inexact projection | Local to diagnostics/projection contract | Small component system only | none | Adopt |
| Increase `max_corrections` under fixed relaxation | Violates monotone residual requirement | Hides failure behind iteration count | More work and worse residual | YAML tuning temptation | Reject |
| Tune fixed relaxation | Case-dependent damping, not paper-exact | Requires user/API knob to mask instability | Cheap but not robust | YAML/API pressure | Reject |
| Curvature cap/smoothing/CFL shrink | Improves symptoms while leaving PPE residual growth | Breaks algorithm fidelity | May be cheap | Changes physics/numerics | Reject |
| Switch PPE solver fallback | Avoids rather than fixes DC contract | Violates PPE route policy if ad hoc | unpredictable | API/YAML branch | Reject |

## Validation

Targeted tests:

```text
python3 -m pytest \
  src/twophase/tests/test_defect_correction.py \
  src/twophase/tests/test_interface_projection_diagnostics.py -q

16 passed
```

New tests:

- `test_defect_correction_uses_residual_minimising_step_length`
- `test_external_component_saddle_projection_uses_positive_hodge_metric`

The first test manufactures an overscaled base correction.  A fixed unit
relaxation would increase residual, while the residual-minimizing step produces
the pinned-gauge exact solution.

The second test manufactures an oblique pressure range where the old
unprojected component metric would give the wrong denominator sign.  The new
projected-Hodge metric gives a positive denominator and zero corrected residual.

## Remaining Risk

The fix eliminates the identified blow-up mode and prevents residual-amplifying
defect-correction steps.  It does not by itself certify the complete Chapter 14
rising-bubble benchmark as a final paper result.  A fresh remote run should be
performed after this commit to produce the official `T=0.03` result set.

The important production boundary is:

```text
No result may be accepted merely because KE or volume looks better.
The PPE residual, Hodge metric positivity, divergence, volume, and force ledger
must all remain inside their contracts.
```
