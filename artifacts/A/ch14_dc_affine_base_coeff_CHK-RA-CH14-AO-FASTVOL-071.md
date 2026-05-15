# CHK-RA-CH14-AO-FASTVOL-071 — DC Affine Base Coefficient RCA

Date: 2026-05-15

## Scope

Address the ch14 capillary-wave failure where PPE defect correction stalled at
relative residual about `4e-6` even though the high-order route was intended to
be phase-separated PPE + HFE/DC.

## Theory Gate

Defect correction is valid only if the low-order correction operator `L_L` is a
low-order approximation of the same physical operator `L_H`.  For the ch14
capillary route, `L_H` is the phase-separated affine-jump PPE.  On an
interface-cut face it uses the HFE-compatible face resistance

```text
a_f^Gamma = 1 / (theta rho_L + (1 - theta) rho_H).
```

Therefore `L_L` may be lower-order in reconstruction, but it must use the same
phase resistance on the same cut face.  Replacing that coefficient by the
smooth harmonic coefficient is not lower order; it changes the PDE.

## Hypotheses And Falsification

| Hypothesis | Test | Verdict |
|---|---|---|
| DC correction cap is too small | Increase/loosen correction policy would hide failure without changing the operator. | Rejected as non-theoretical. |
| Residual metric is too strict | Old residual was already far above the configured convergence contract and had large `linf`. | Rejected. |
| High-order FCCD/HFE jump is wrong | Inspect high-order operator: it already received the affine interface context. | Not primary. |
| Low-order FDDirect base solves a different density equation | Compare FDDirect/PPEBuilder face coefficient for a cut face. | Supported. |
| Nonuniform/periodic assembly path drops affine context | Audit both normal faces and periodic wrap faces. | Risk closed in implementation. |
| CPU/GPU optimization broke the route | Ensure coefficient assembly uses backend `xp` arrays and does not introduce full-field D2H. | Risk closed. |

## Root Cause

`PPESolverFCCDMatrixFree` received the affine jump/interface-stress context, but
the wrapped `PPESolverFDDirect` used by defect correction rebuilt the low-order
matrix through `PPEBuilder` with smooth harmonic face coefficients.  Thus DC was
iterating between two different elliptic operators:

```text
L_H: phase-separated affine cut-face PPE
L_L: smooth harmonic-density PPE
```

The residual floor near `4e-6` was the algebraic signature of this operator
mismatch.

## Countermeasure

- Thread coefficient policy and interface coupling policy into `PPEBuilder`.
- Bind the same Young--Laplace/interface-stress context into `PPESolverFDDirect`
  through `set_interface_jump_context`.
- Assemble FDDirect matrix faces with affine cut-face resistance when
  `coefficient_scheme: phase_separated` and
  `interface_coupling_scheme: affine_jump`.
- Cover both nonuniform ordinary faces and periodic wrap faces.
- Preserve fail-closed behavior: missing affine context falls back only when the
  configured route is not the affine-jump route.

## Verification

- Targeted coefficient test confirms FDDirect uses the affine cut-face
  resistance instead of the smooth harmonic coefficient.
- YAML/runtime tests confirm ch14 capillary builds the true low-order DC base:
  `coefficient_scheme == phase_separated` and
  `interface_coupling_scheme == affine_jump`.
- Original one-step diagnostic now converges instead of failing:
  old `relative_l2=4.024e-06`, old `linf=2.884e-01`;
  new residual report reaches about `3.790e-07` in 15 DC corrections.
- Ten-step diagnostic keeps the same convergence behavior: each pressure solve
  converges in 15 corrections with residual about `3.793e-07`, and
  `ppe_dc_conv=1`.

## Negative Knowledge

Do not handle this failure by raising `max_corrections`, loosening tolerances,
switching to GMRES, disabling HFE, removing nonuniform grids, bypassing
interface-tracking rebuilds, or adding geometric offsets.  The theoretical
object to fix is the shared operator identity between `L_H` and `L_L`.
