# CHK-RA-CH14-AO-FASTVOL-045

## Question

After fixing the non-uniform CCD computational-coordinate scaling bug, can the Chapter 14 capillary AO-Fast active projection safely use DC?

## Theoretical Gate

The DC path is acceptable only if it satisfies the same SP-AO contract as the PCG/Newton path:

- the active Schur normal equation residual must converge to the requested tolerance;
- the projected `q = Q_h(phi)` state must match the dense SP-AO oracle;
- the capillary Riesz representative must reproduce the dense raw face covector, because `T_q^T lambda` depends on the representative and not only on a small scalar residual;
- the GPU path must satisfy the same normal-equation gate before the stage advances.

This check intentionally does not accept "the time step did not explode" as proof.

## Hypotheses And Results

| Hypothesis | Test | Result | Verdict |
|---|---|---|---|
| H1: The non-uniform-grid fix also makes DC-only exact. | Component exactness, `--scheme dc --dc-max-iterations 8 --dc-tolerance 1e-11`. | `schur_dc active_residual_linf = 9.207e-04 > 1e-11`; raw capillary covector diff `4.354e+00`; GPU projection residual slightly above tolerance. | Refuted. |
| H2: DC-only only needs more iterations after the grid fix. | Component exactness, `--scheme dc --dc-max-iterations 256 --dc-tolerance 1e-11`. | Same Schur residual scale, `9.207e-04`, and same raw capillary covector failure. | Refuted; not an iteration-count issue. |
| H3: DC-only can pass the integrated fail-close if made expensive. | Stage chain, DC-only, 256 DC iterations, 3 steps. | It advanced 3 steps, but component exactness still failed. | Not certified. |
| H4: DC followed by PCG can be a preconditioned chain. | Component exactness, `--scheme dc_then_pcg --dc-max-iterations 8`. | Projection and Schur residual pass, but raw capillary covector still differs by `2.532e-07 > 1e-11`. | Partially supported; not a full capillary Riesz replacement. |
| H5: PCG-only remains the certified reference path. | Component exactness, `--scheme pcg`. | Projection, Schur, raw capillary Riesz, and GPU residual all pass. | Supported. |

## Integrated Runs

- DC-only, 32 DC iterations, 10 requested steps: fail-closed at step 1 with `AO capillary source solve violates Young-Laplace normal equations (1.602379e-08 > 1e-11)`.
- DC-only, 256 DC iterations, 3 steps: advanced, but exactness diagnostics prove it is not mathematically certified.
- DC-then-PCG, 10 steps: advanced without fail-close; step 10 reached `ppe_rhs = 2.222586968010e+02`, `div_u = 3.743229679709e-04`, comparable to the post-fix PCG-only short run, but not exact in the raw capillary covector oracle.

## Conclusion

DC-only is still not acceptable for Chapter 14 AO-Fast capillary production use after the non-uniform-grid fix.

The non-uniform fix removed the catastrophic coordinate-scaling error, but it did not change the mathematical defect of DC-only: the fixed-point representative does not solve the active Schur/Riesz problem to the AO tolerance, and increasing DC iterations does not reduce the oracle residual. Therefore the checked-in capillary YAML should remain PCG-only for certified runs.

DC-then-PCG may be useful as an experimental preconditioned chain only if final PCG acceptance remains mandatory. It should not be described as "DC is OK" until the raw capillary Riesz covector equality is also certified.

## Validation Commands

- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme dc --dc-max-iterations 8 --dc-tolerance 1e-11'`
- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme dc --dc-max-iterations 256 --dc-tolerance 1e-11'`
- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme dc_then_pcg --dc-max-iterations 8 --dc-tolerance 1e-11'`
- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme pcg'`
- `make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 10 --active-projection-scheme dc --active-projection-max-iterations 32 --active-projection-dc-max-iterations 32 --active-projection-dc-tolerance 1e-11'`
- `make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 3 --active-projection-scheme dc --active-projection-max-iterations 32 --active-projection-dc-max-iterations 256 --active-projection-dc-tolerance 1e-11'`
- `make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 10 --active-projection-scheme dc_then_pcg --active-projection-max-iterations 32 --active-projection-dc-max-iterations 32 --active-projection-dc-tolerance 1e-11 --active-projection-pcg-tolerance 1e-12 --active-projection-pcg-max-iterations 256'`
- `.venv/bin/python3 -m py_compile experiment/ch14/diagnose_ao_stage_chain.py`
- `git diff --check`
