# CHK-RA-CH14-AO-FASTVOL-046

## Question

Which active projection policy is more advantageous for Chapter 14 AO-Fast capillary waves: PCG-only or DC-then-PCG?

## Decision

PCG-only is more advantageous for certified Chapter 14 AO-Fast capillary runs.

DC-then-PCG is not currently advantageous because it adds DC sweeps, does not lower the PCG iteration budget needed by the manufactured Schur probe, and changes the capillary Riesz representative even after the normal residual passes.

## Theory

The active Schur system is semidefinite on the full active cell space. A zero-start PCG selects a stable representative for the Lagrange multiplier. A DC pre-pass can inject a null-space component into the initial guess. PCG then removes range residuals, but it does not necessarily remove the inherited null-space representative. Since the capillary force uses the representative through the raw face covector, not only the scalar normal residual, this difference is physically relevant.

For the current fixed-iteration GPU implementation, PCG does not stop early on the host. It runs the configured loop count and freezes updates after tolerance. Therefore DC-then-PCG can only be faster if the DC initial guess safely permits a smaller `pcg_max_iterations`.

## Evidence

| Policy / setting | Exactness result | Cost result | Verdict |
|---|---|---|---|
| PCG-only, `max_pcg_iterations=32` | Capillary Riesz passes, but manufactured Schur residual fails: `4.130e-06 > 1e-11`. | Too small for the generic Schur contract. | Reject for certified AO-Fast. |
| PCG-only, `max_pcg_iterations=48` | Manufactured Schur, projection, capillary Riesz, and GPU normal residual all pass. Raw face covector diff: `3.586e-13`. | Component probe wall time `9.945s`. | Best certified setting in this sweep. |
| PCG-only, `max_pcg_iterations=64` | Fully passes. | Stage-chain 10-step wall time `1m20.256s`. Step 10: `ppe_rhs=2.278688662973e+02`, `div_u=3.572547373059e-04`. | Certified and stable. |
| DC-then-PCG, `dc=8`, `max_pcg_iterations=32` | Manufactured Schur residual fails at the same scale as PCG-only. | No evidence DC lowers the safe PCG budget. | Reject. |
| DC-then-PCG, `dc=8`, `max_pcg_iterations=48` | Schur residual passes, but capillary raw face covector fails: `2.532e-07 > 1e-11`. | Component probe wall time `9.798s`, within noise, but algebraically not certified. | Reject for certified capillary force. |
| DC-then-PCG, `dc=8`, `max_pcg_iterations=64` | Schur and normal residual pass, but capillary raw face covector still fails: `2.532e-07 > 1e-11`. | Stage-chain 10-step wall time `1m21.642s`. Step 10: `ppe_rhs=2.277888369165e+02`, `div_u=3.582332483382e-04`. | Short-run comparable, but slower and not representative-exact. |

## Conclusion

Use PCG-only for the Chapter 14 AO-Fast capillary YAML.

The best current production policy is:

- `scheme: pcg`
- keep a conservative `pcg.max_iterations` budget; this sweep shows `48` is enough for the manufactured `32x32` probe, while `64` also passes and gives margin;
- do not enable DC-then-PCG unless the capillary Riesz representative is explicitly gauge-fixed or otherwise proven invariant.

DC-then-PCG should remain experimental. It may still be useful as a future preconditioner if the implementation projects out the Schur null-space component or proves that the raw capillary force is invariant under the DC-injected representative. That proof is not true for the current implementation.

## Validation Commands

- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme pcg --max-pcg-iterations 16'`
- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme pcg --max-pcg-iterations 32'`
- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme pcg --max-pcg-iterations 48'`
- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme pcg --max-pcg-iterations 64'`
- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme dc_then_pcg --max-pcg-iterations 48 --dc-max-iterations 8 --dc-tolerance 1e-11'`
- `make run EXP=experiment/ch14/diagnose_ao_fast_component_exactness.py ARGS='--scheme dc_then_pcg --max-pcg-iterations 64 --dc-max-iterations 8 --dc-tolerance 1e-11'`
- `make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 10 --active-projection-scheme pcg --active-projection-max-iterations 32 --active-projection-pcg-tolerance 1e-12 --active-projection-pcg-max-iterations 64'`
- `make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 10 --active-projection-scheme dc_then_pcg --active-projection-max-iterations 32 --active-projection-dc-max-iterations 8 --active-projection-dc-tolerance 1e-11 --active-projection-pcg-tolerance 1e-12 --active-projection-pcg-max-iterations 64'`
