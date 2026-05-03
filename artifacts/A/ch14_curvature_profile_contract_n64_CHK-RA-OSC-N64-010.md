# CHK-RA-OSC-N64-010 — Cut-Face Profile Gradient Check

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

After CHK-RA-OSC-N64-009 localized the pressure oscillation to noisy cut-face
curvature `κ_Γ`, test whether that noise is caused by collapse of the
curvature formula denominator `|∇ψ|`, or by high-frequency second-derivative
geometry/profile noise.

## Diagnostic

Extended `experiment/ch14/diagnose_curvature_contract_n64.py` to record
`|∇ψ|` interpolated at the same cut faces used by
`signed_pressure_jump_gradient()`.

Remote-first baseline run:

```bash
make cycle EXP=experiment/ch14/diagnose_curvature_contract_n64.py
```

## Result

At `T=0.40`:

| metric | value |
|---|---:|
| cut-face `κ` std | `1.066869e+01` |
| cut-face radius std | `5.540336e-04` |
| `m32` radius amplitude | `1.075945e-04` |
| cut-face `|∇ψ|` mean | `1.033420e+01` |
| cut-face `|∇ψ|` std | `8.745563e-01` |
| cut-face `|∇ψ|` min | `8.284201e+00` |
| cut-face `|∇ψ|` max | `1.297095e+01` |

## Inference

The curvature failure is not a near-zero-gradient denominator blow-up at the
interface.  The profile remains steep enough at cut faces.  The more precise
failure mode is high-frequency second-derivative amplification: subcell
interface/profile perturbations that are small in radius still become large in
`κ_Γ`, and therefore become large pressure-jump RHS oscillations.

This strengthens the next implementation direction from CHK-RA-OSC-N64-009:
the affine pressure-jump closure should not depend on broad nodal-band
curvature interpolated to cut faces.  It needs a cut-face/interface curvature
quantity with a tested static-circle Young--Laplace contract.

[SOLID-X] Diagnostic extension only; no production algorithm changed and no
damping/CFL/smoothing workaround introduced.
