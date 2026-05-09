# CHK-RA-CH14-BUBBLE-DIAG-RCA-001

Date: 2026-05-09

Scope: ch14 rising bubble after the SP-AN constrained face-state work.  The
observed symptom was that the `T=0.02`, `N=32x64`, 10 mm x 20 mm water-air
run finished, but debug diagnostics still looked alarming:

```text
kappa_max       max 3.213650e+05
ppe_rhs_max     max 5.691935e+07
bf_residual     max 4.089974e+05
div_u_max       max 2.459386e-06
```

The purpose of this check was not to tune parameters.  It was to ask which
physics, algebraic, computational, or software contract the numbers would have
to break if they represented a real production defect.

## Hypothesis Inventory

| ID | Hypothesis | Constraint or contract it would break | Probe |
|---|---|---|---|
| H01 | Young-Laplace face curvature truly reached `O(1e5)` | pressure-jump force magnitude and capillary CFL consistency | Recompute active `face_implicit` cut-face curvature from checkpoints |
| H02 | Legacy nodal `psi_direct` curvature is being reported as production curvature | diagnostic naming contract | Compare reported `kappa_max` with active pressure-jump curvature |
| H03 | PPE RHS diagnostic is recorded before capillary/history source assembly | software diagnostic contract: stored RHS must equal solved RHS | Inspect `solve_ns_pressure_stage` and compare with DC solver RHS diagnostics |
| H04 | Closed-interface Riesz source is added with the wrong sign | pressure work and capillary virtual-work adjoint | One-step/short-run RHS comparison; no production sign change unless work identity fails |
| H05 | Previous pressure-history acceleration is not included in the diagnostic RHS | IPC face-history contract | Inspect RHS assembly order |
| H06 | `bf_residual_max` is a true balanced-force residual in pressure-jump mode | pressure-gradient minus active capillary reaction should be measured in the same cochain | Inspect residual definition against `state.f_x/state.f_y` in pressure-jump mode |
| H07 | Capillary Hodge residual uses an admissible wall face space | restricted Green identity in `F_w=ker C_w` | Compare full-face diagnostic to SP-AN constrained face space |
| H08 | Wall projection metric must be active pressure metric, not always transported velocity mass | pressure Green identity in affine/phase-separated coefficient path | Add explicit face metric API and idempotence/self-adjoint tests |
| H09 | Custom metric API can silently broadcast a wrong face shape | fail-close software contract | Add shape validation and negative unit test |
| H10 | Reinitialization caused the spike | reinit work separation | Run has `reinit_triggered_sum=0`, reject |
| H11 | Dynamic grid remap caused visualization-only shape jump | per-snapshot grid-coordinate contract | Previous CHK fixed; current short prefix physics matches old run |
| H12 | Restart should be forced across code-fingerprint mismatch | checkpoint reproducibility contract | Attempted restart fails closed; accept as correct |
| H13 | DCCD/FCCD/UCCD suppression would hide the issue | PR-5 algorithm fidelity | Reject as non-physical production fix |
| H14 | Damping/CFL/smoothing/curvature caps would reduce numbers | conservation and model fidelity | Reject as negative knowledge |

## Efficient Verification Order

1. Inspect active source path and debug diagnostic wiring before changing any
   numerical model.
2. Recompute active cut-face curvature from saved states.
3. Add unit-level algebraic tests for the constrained face-space metric API.
4. Run a short `T=0.005` experiment from zero start to verify the diagnostic
   change without redoing the long run.
5. Compare prefix physical fields with the previous `T=0.02` run.

## Findings

### Active curvature is not the reported late `O(1e5)` spike

The pressure-jump route uses `face_implicit` curvature through
`evaluate_interface_face_curvature_lg` and `div_op.pressure_fluxes`.  Recomputing
that active face curvature from the saved `T=0.02` state gives:

```text
axis 0 max |kappa_f| = 1.135732e+03
axis 1 max |kappa_f| = 1.167086e+03
```

The old `debug_diagnostics/kappa_max=3.213650e+05` was therefore not the active
pressure-jump Young-Laplace curvature.  It came from the legacy nodal/direct-psi
diagnostic path.  This is a diagnostic interpretation problem, not a license to
cap or smooth curvature.

### PPE RHS was recorded before the final RHS existed

`solve_ns_pressure_stage` previously appended `ppe_rhs_max` immediately after

```text
predictor_rhs + div(f/rho)
```

but before `_install_pressure_jump_context(...)` and before previous
face-pressure acceleration was added.  This made the scalar debug field a
partial source, not the RHS sent to `ppe_solver.solve`.

The fix moves the append to immediately before `ppe_solver.solve(rhs, ...)`.
No pressure equation, pressure jump, time integration, or capillary force was
changed.

### `bf_residual_max` is not a balanced-force residual in pressure-jump mode

In the pressure-jump route, `state.f_x/state.f_y` are zero because capillarity is
encoded as an affine pressure-jump/closed-interface source.  The current
`bf_residual_max` therefore measures a pressure-gradient magnitude against a
zero CSF force, not a balanced-force residual in the active capillary cochain.
It should not be used as a production acceptance metric for this route.

### The remaining real algebraic issue is the admissible face-space metric

The persistent

```text
capillary_contract_pressure_adjoint_residual = 3.570416e-01
```

is consistent with a full-face diagnostic being tested outside the constrained
wall state space and without an explicit active pressure metric.  SP-AN requires
the pressure adjoint to be evaluated in the same admissible face space

```text
F_w = ker C_w
```

and in the active pressure metric

```text
M_A = Q_f / alpha_f
```

for affine/phase-separated coefficient paths.  The production restricted PPE
solve is still not enabled, but the building block must be able to accept that
metric.  This check implemented only that API/contract slice.

## Implementation

Changed:

```text
src/twophase/simulation/ns_step_services.py
src/twophase/simulation/boundary_hodge.py
src/twophase/tests/test_boundary_hodge.py
```

Details:

```text
1. ppe_rhs_max is now recorded after closed-interface source and pressure-history
   source assembly, immediately before the PPE solve.
2. boundary_hodge face-mass helpers accept explicit face metric components.
   Default remains Q_f rho_f.
3. Explicit metric components are shape-checked per face axis and fail closed.
4. Unit tests cover explicit active-metric projection, idempotence,
   M-self-adjointness, wall-trace removal, and malformed metric rejection.
```

## Validation

Targeted remote test command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make test PYTEST_ARGS='twophase/tests/test_boundary_hodge.py -q'
```

The wrapper expanded to the full CPU suite:

```text
650 passed, 33 skipped in 43.14s
```

Short experiment:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make cycle EXP=experiment/run.py \
ARGS="--config _tmp_ch14_rising_bubble_n32x64_t0005_diag --checkpoint-interval 0.005"
```

Result:

```text
T_final                 5.000000e-03
kinetic_energy_final    3.727144e-05
volume_drift_final      1.875499e-06
kappa_max_final         1.129876e+03
kappa_max_max           1.141419e+03
ppe_rhs_max_final       1.082777e+05
ppe_rhs_max_max         3.707382e+06
capillary_face_linf     4.639447e+02
capillary_div_linf      3.702047e+06
hodge_residual_final    1.339807e+01
```

Prefix comparison against the old `T=0.02` run through `t=0.005`:

```text
times                   Linf diff 0.000000e+00
kinetic_energy          Linf diff 2.032879e-20
volume_conservation     Linf diff 2.889768e-16
kappa_max               Linf diff 8.481038e-11
capillary_face_linf     Linf diff 1.648459e-12
capillary_hodge_resid   Linf diff 1.204370e-11
ppe_rhs_max             Linf diff 2.696201e+06
```

Only the intended diagnostic `ppe_rhs_max` changed; physical trajectories and
active capillary diagnostics match to roundoff over the shared prefix.

The attempted restart from the old `checkpoint_t0p015.npz` failed with:

```text
CheckpointError: checkpoint code fingerprint differs; refusing restart
```

This is correct fail-close behavior and was not bypassed.

## Production Decision

Accepted production-safe changes:

```text
diagnostic RHS record location,
explicit face metric API for boundary Hodge diagnostics/operators,
fail-closed metric shape validation,
targeted tests.
```

Rejected production fixes:

```text
curvature cap or smoothing,
damping or CFL reduction,
DCCD/FCCD/UCCD suppression,
restart fingerprint bypass,
case-specific rising-bubble branch,
post-pressure wall-only repair,
generic pressure-bypass operator.
```

Remaining work:

```text
1. Rename or split legacy `kappa_max` and `bf_residual_max` so pressure-jump
   route reports active face-curvature and active cochain residuals explicitly.
2. Move capillary contract diagnostics to the constrained face space `F_w` with
   the active pressure metric `M_A=Q_f/alpha_f`.
3. Only after those gates pass, consider production `D_h P_w G_A` PPE assembly.
```
