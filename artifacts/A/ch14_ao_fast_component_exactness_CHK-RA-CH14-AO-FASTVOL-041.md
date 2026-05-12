# CHK-RA-CH14-AO-FASTVOL-041: AO-Fast Component Exactness Check

## Question

Check each AO-Fast component against the dense SP-AO oracle, without hiding
failures by tolerance relaxation, coordinate offsets, smoothing, or fallback
logic.

## Component Map

| Component | Exact equation checked |
|---|---|
| P1 geometry | `Q_h(phi)`, `theta`, `S_h(phi)`, `J_q`, `dS_h` match dense CPU formulas |
| Swept transport | GPU swept phase flux and transported `q` match CPU common-flux oracle |
| Compatibility projection | transported `q` satisfies full `||q-Q_h(phi)||_inf <= tau` |
| Schur solver | `J_q J_q^T lambda = rhs` residual is below tolerance |
| Face Hodge | density and face mass weights match CPU Hodge weights |
| Capillary Riesz | raw face covector `r_sigma=T_q^T lambda` matches CPU oracle, not just the normal residual |
| Pressure reaction split | algebraic split tests preserve `corrected=r_sigma-Bmu` and `balanced=corrected-L_A(corrected)` identities |

## Commands

```bash
make test PYTEST_ARGS='twophase/tests/test_geometry_dense_reference.py twophase/tests/test_geometry_active_table.py twophase/tests/test_geometric_runtime_gpu_gates.py twophase/tests/test_geometric_capillary_reaction_split.py -q'
make push
make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py
make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme dc --dc-max-iterations 256'
make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme dc_then_pcg --dc-max-iterations 8'
make run EXP=experiment/ch14/diagnose_ao_gpu_theory_probe.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 5'
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py
git diff --check
```

## Results

PCG route on a manufactured regular capillary wave:

| Component | Result |
|---|---|
| geometry | PASS: `q`, `theta`, cell surface, total surface, `J_q`, `dS_h` all match CPU oracle; largest diff `8.88e-16` |
| swept transport | PASS: phase flux, transported `q`, and mass flux match exactly to reported precision |
| compatibility projection | PASS: CPU and GPU full residual both `6.299e-13 <= 1e-11` |
| Schur PCG | PASS: active residual `8.212e-13 <= 1e-11` |
| Schur DC | FAIL: active residual `9.207e-04 > 1e-11` |
| DC then PCG | Schur residual PASS, but see representative issue below |
| face Hodge | PASS: density and weights match CPU oracle exactly to reported precision |
| capillary Riesz via PCG | PASS: raw face covector diff `3.586e-13`, normal residual `5.588e-15` |

DC-only route with 256 DC iterations:

| Component | Result |
|---|---|
| compatibility projection | FAIL: GPU full residual `1.531e-11 > 1e-11` |
| Schur DC | FAIL: active residual `9.207e-04 > 1e-11` |
| capillary Riesz | FAIL: raw face covector diff `4.354e+00`, normal residual `1.007e-06` |

DC-then-PCG route:

| Component | Result |
|---|---|
| compatibility projection | PASS: full residual `6.299e-13` |
| Schur equation | PASS: PCG residual `8.212e-13` |
| capillary Riesz representative | FAIL: raw face covector diff `2.532e-07 > 1e-11` even though the normal residual passes |

Chapter 14 integrated capillary-wave probe:

| Step | Observation |
|---|---|
| 1 | compatibility `0`, capillary source normal residual `7.15e-22`, but balanced increment nonzero |
| 2 | compatibility still small (`2.37e-15`), but `ppe_rhs=1.65e29`, `div_u=3.24e23`, `KE=3.35e42` |
| 3 | fail-close: active `q/phi` compatibility residual `1.411891e-10 > 1.0e-10` |

Existing test command ran the repository suite and showed one unrelated
configuration-test mismatch: `test_ch14_capillary_yaml_builds_solver` still
expects DC tolerance `1e-11`, while the current YAML-derived solver value is
`1e-10`.

## Theory Verdict

The strict low-level P1 geometry and common-flux kernels are not the root
cause.  Their formulas match the dense oracle.

PCG from the zero representative is currently the only observed Schur route
that preserves both the Schur residual and the raw capillary face covector.

DC-only is not an exact solver for the active Schur system under the current
contract.  It behaves as a residual-monotone smoother and cannot be advertised
as a certified exact AO-Fast route unless it either converges to the exact
residual and representative or fails closed.

DC-then-PCG has a subtler mathematical bug.  The final Schur residual can pass,
but the raw face covector `T_q^T lambda` does not match the CPU oracle.  This is
consistent with a singular/near-singular Schur system: compatibility projection
only uses `J_q^T lambda`, so a nullspace-contaminated representative can still
move `phi` correctly, while capillary Riesz depends on the actual `lambda`
representative through `T_q^T lambda`.  Therefore residual convergence alone is
not a sufficient acceptance condition for capillary Riesz.

The integrated capillary-wave failure is not solved by coordinate perturbation
or tolerance relaxation.  After step 2, the pressure/PPE coupling produces a
huge velocity/pressure state and the next compatibility projection fails the
hard `q=Q_h(phi)` gate.  The next repair must preserve the exact PCG
representative contract and then check the production pressure-adjoint split
against the actual PPE operator, not just the toy split algebra.

## SOLID-X

This check added only a diagnostic probe and this artifact.  It did not add a
physical parameter change, CFL relaxation, damping, smoothing, curvature cap,
FD/WENO/PPE fallback, dense runtime fallback, coordinate offset workaround, main
merge, or branch deletion.
