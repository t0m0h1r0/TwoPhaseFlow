# CHK-RA-CH14-CAPILLARY-AO-RCA-003 — shortest theory path for AO capillary

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Purpose

Continue the theory-first RCA and identify the shortest non-hacky route toward a working Chapter 14 AO capillary wave.  No solver fix is applied in this checkpoint.

## Extra Rung-0 Probes

Commands:

```bash
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 32 --ny 32 --mode capillary_wave --amplitude 1.0e-4'
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 32 --ny 32 --mode capillary_wave --amplitude 4.0e-4'
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 64 --ny 64 --mode capillary_wave --amplitude 2.0e-4'
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 32 --ny 32 --mode capillary_wave --wave-number 1'
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 32 --ny 32 --mode capillary_wave --wave-number 3'
make run EXP=experiment/ch14/diagnose_ao_algebraic_split.py ARGS='--nx 32 --ny 32 --mode capillary_wave --boundary-y periodic'
```

Results:

| Probe | CPU exact balanced_l2 | CPU component-Hodge balanced_l2 | GPU balanced_l2 | Verdict |
|---|---:|---:|---:|---|
| A=1e-4, N32, k=2 | 0.0 | 1.2566480188877793 | 0.0 | same failure class |
| A=2e-4, N32, k=2 | 0.0 | 2.117576366046111 | 0.0 | same failure class |
| A=4e-4, N32, k=2 | 0.0 | 3.558211768995462 | 0.0 | same failure class |
| A=2e-4, N64, k=2 | 0.0 | 2.3054842783888376 | 0.0 | same failure class |
| A=2e-4, N32, k=1 | 0.0 | 0.4646413811892921 | 0.0 | same failure class |
| A=2e-4, N32, k=3 | 0.0 | 5.837843211706435 | 0.0 | same failure class |
| y-periodic diagnostic | CPU rejects periodic phi closure | CPU rejects periodic phi closure | 0.0 | invalid complex for this graph |

The component-Hodge residual grows monotonically with amplitude and wave number, and remains nonzero at N64.  This is the expected qualitative physics for capillary curvature release.  The full-pressure split and current GPU packet delete it in every valid non-flat probe.

## Expanded Hypotheses

| ID | Hypothesis | Test | Status |
|---|---|---|---|
| H16 | The failure is a single-amplitude artifact. | A=1e-4,2e-4,4e-4 all fail with full-pressure zero drive; component residual grows. | Rejected |
| H17 | The failure is a single-resolution artifact. | N32 and N64 both show full-pressure zero drive and component residual. | Rejected |
| H18 | The failure is tied only to mode-2 geometry. | k=1,2,3 all show full-pressure zero drive and component residual. | Rejected |
| H19 | The wall boundary is the physical root cause. | Changing y to periodic violates the periodic phi closure for the CPU theorem path; valid wall-complex probes already isolate the algebra. | Rejected as primary |
| H20 | Component-Hodge residual is random numerical leakage. | It scales coherently with amplitude and wave number and is zero for flat controls. | Rejected |
| H21 | `R_p = full cell-pressure Schur image` is admissible. | It removes every non-flat capillary-wave drive. | Rejected |
| H22 | `R_p = 0` is the fastest fix. | It would move the wave but cannot represent static Young-Laplace pressure reaction or pressure history. | Rejected |
| H23 | `R_p = component-volume reactions` is final. | It passes flat/wave qualitative gates but lacks scalar PPE-compatible pressure-coordinate proof. | Candidate diagnostic only |
| H24 | `R_p` should be the pressure-adjoint image admitted by the physical face complex, not the full active Schur image. | This is exactly the gap left by SP-AO/WIKI-T-169: define `R_p(q_T)` in `M_f` and project only there. | Supported |
| H25 | A long capillary-wave run is the next useful test. | Algebraic Rung-0 gates are still failing; long runs would only test an unadmitted packet. | Rejected |

## Candidate Reaction Spaces

| Candidate `R_p` | Flat zero | Wave nonzero | Scalar pressure coordinate | Theorem status |
|---|---|---|---|---|
| Full active cell-pressure image | yes | no | yes | too large; deletes physics |
| Zero reaction | yes | yes | trivial none | too small; cannot carry static pressure reaction |
| Component-volume reactions | yes | yes | not yet | useful lower-dimensional diagnostic, not final |
| Physical pressure-adjoint face complex quotient | expected yes | expected yes | required | shortest real target |

## Root-Cause Sharpening

The problem is not merely "the diagonal Schur solve is inaccurate."  Even the CPU exact full-pressure split deletes the capillary-wave drive.  The diagonal GPU residual is a separate admission failure, but solving the same over-large full-pressure Schur problem more accurately would still preserve the zero-drive pathology.

The shortest theory-respecting path is therefore:

```text
Define R_p(q_T) in the face mass metric M_f.
Build r_sigma from bundle virtual work.
Compute r_bal = r_sigma - Pi_{R_p}^{M_f} r_sigma.
Certify flat zero, wave nonzero, amplitude scaling, wave-number scaling, N32/N64 consistency.
Only then connect a scalar AO pressure coordinate for pressure_history.
```

This avoids the two bad shortcuts:

- tiny geometry offsets, which do not change the algebra and would violate translational invariance;
- hidden component-Hodge fallback, which may be a useful probe but is not yet the final scalar pressure-coordinate theorem.

## Immediate Next Slice

Implement a diagnostic-only `R_p` gate, not a production run:

1. factor the current component-volume reaction probe into a named candidate `R_p_component`;
2. add a second candidate for the physical pressure-adjoint quotient once its basis is derived;
3. make the diagnostic emit pass/fail rows for flat, shifted flat, wave k=1/2/3, amplitude sweep, and N64;
4. require scalar pressure-coordinate reconstruction before any non-static AO production admission.

[SOLID-X] Theory/probe/artifact only; no production solver source, YAML physical parameter, CFL reduction, damping, smoothing, curvature cap, FD/WENO/PPE fallback, hidden dense/CPU fallback, hidden component-Hodge fallback, geometry offset workaround, long unadmitted run, main merge, or branch deletion introduced.
