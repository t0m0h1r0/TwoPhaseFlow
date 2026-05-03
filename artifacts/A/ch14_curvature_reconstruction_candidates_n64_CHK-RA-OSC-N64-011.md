# CHK-RA-OSC-N64-011 — Cut-Face Curvature Reconstruction Candidates

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

CHK-RA-OSC-N64-010 showed that the N64 static-droplet pressure oscillation is
not caused by collapse of `|grad psi|` at cut faces.  Test whether replacing the
broad nodal-band `kappa` interpolation by a sharper cut-face reconstruction is
a valid next production direction.

## Diagnostic Extension

Extended `experiment/ch14/diagnose_curvature_contract_n64.py` with:

- direct cut-face `kappa_Gamma` from `psi_x`, `psi_y`, `psi_xx`, `psi_yy`,
  and `psi_xy` interpolated to the same `psi=1/2` cut faces;
- three-point geometric curvature from the ordered cut-point contour;
- diagnostic `--filter-C` override for the documented
  `InterfaceLimitedFilter` coefficient.

## Runs

```bash
make cycle EXP=experiment/ch14/diagnose_curvature_contract_n64.py
make cycle EXP=experiment/ch14/diagnose_curvature_contract_n64.py ARGS="--filter-C 0.10"
```

Both runs completed to `T=0.40` and pulled `data.npz` outputs.

## Results

Final-step metrics:

| case | cut-face `kappa` mean | cut-face `kappa` std | direct-cut std | geometric std | radius std | `m32` radius amp |
|---|---:|---:|---:|---:|---:|---:|
| baseline `C=0.05` | `3.231471e+00` | `1.066869e+01` | `2.324792e+01` | `1.080221e+01` | `5.540336e-04` | `1.075945e-04` |
| filter `C=0.10` | `6.229986e+00` | `7.147180e+00` | `4.223104e+01` | `9.765971e+00` | `1.518525e-03` | `1.386196e-03` |

## Inference

1. Direct derivative reconstruction is worse than the current nodal-band
   cut-face interpolation.  It amplifies the same high-frequency second
   derivative noise rather than removing it.
2. Naive three-point contour curvature is also not a valid production path: it
   produces a large positive bias because alternating horizontal/vertical cut
   points turn subcell contour jitter into local osculating-circle spikes.
3. A stronger documented curvature filter (`C=0.10`) reduces the final
   cut-face `kappa` std from `1.066869e+01` to `7.147180e+00`, but it also
   biases the mean above the exact static value `4.0` and grows radius noise
   (`m32` from `1.075945e-04` to `1.386196e-03`).  This is not yet a root
   production fix.

## Verdict

Do not implement either direct cut-face derivative reconstruction or naive
three-point geometric reconstruction in production.  The next root-cause unit
should move upstream to the interface/profile evolution that creates the
high-mode radius jitter, or establish a rigorously tested curvature-filter
contract before changing defaults.

[SOLID-X] Diagnostic extension only; no production solver/operator boundary
changed, no tested implementation deleted, and no damping/CFL workaround was
adopted as a fix.
