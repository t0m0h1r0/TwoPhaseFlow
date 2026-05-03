# CHK-RA-OSC-N64-017 — Static Droplet Root Hypothesis Narrowing

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Theory Target

For a static circular droplet, the discrete loop must be neutral:

```text
psi = psi_0, u = 0,
kappa_lg = 1/R,
j_gl = p_g - p_l = -sigma kappa_lg,
G_Gamma(p; j) = G(p) - B_Gamma(j),
D_f u_f = 0.
```

After CHK-014, the interface transport side consumes projection-native face
velocity.  The remaining failure must therefore live downstream of that boundary:

```text
curvature/jump evaluation
  -> affine PPE/projection
  -> pressure history in the IPC predictor
  -> grid/geometry feedback
```

## Hypothesis Matrix

| ID | Hypothesis | Test | Verdict |
|---|---|---|---|
| H1 | Face-native interface transport was the only root cause | CHK-016 full static droplet `T=1.5` | Falsified: final KE `1.6865e-02`, pressure contrast `26.8` |
| H2 | Dynamic nonuniform grid rebuild is the primary remaining cause | `diagnose_curvature_contract_n64.py --static-grid` | Falsified as primary: cut-face kappa std only `1.855 -> 1.788`, KE `1.15e-4 -> 8.44e-5` at `T=0.4` |
| H3 | Curvature noise is the main kinetic injection | pressure-history probe `constant_curvature` | Mostly falsified for KE: max KE `1.15e-4 -> 1.07e-4`; supported for jump quality: jump error `2.80e-2 -> 8.17e-3` |
| H4 | Previous-pressure predictor gradient is a dominant kinetic injection path | pressure-history probe `no_prev_pressure_gradient` | Strongly supported as injection path: max KE `1.15e-4 -> 1.91e-6`; not a fix because jump becomes `177.8` |
| H5 | Stored base pressure can replace physical pressure history | `base_history`, `base_corrector`, combined | Falsified: metrics identical to baseline; pressure-variable diagnostic shows base/physical deltas zero |
| H6 | A nodal reconstruction of affine jump correction is sufficient for history gradient | new `jump_aware_history_gradient` diagnostic | Falsified: KE barely changes and jump error worsens to `3.33e-1` |
| H7 | Final pressure error is a low-mode shape oscillation | pressure residual spectral diagnostic at `T=1.5` | Falsified: high-frequency fraction `0.9696`, bulk residual RMS `2.10` |
| H8 | Volume drift/deformation is the primary cause | CHK-016 metrics | Falsified: volume drift `8.74e-4`, max deformation `3.97e-3` while KE/pressure grow strongly |

## Key Results

Pressure-history probe, `T=0.4`:

| case | max KE | jump | jump error | liquid residual RMS |
|---|---:|---:|---:|---:|
| baseline | `1.149686e-04` | `3.160420e-01` | `2.804202e-02` | `1.395004e-01` |
| no previous pressure gradient | `1.909181e-06` | `1.777865e+02` | `1.774985e+02` | `1.758945e-02` |
| exact curvature | `1.072275e-04` | `2.961669e-01` | `8.166903e-03` | `1.502636e-01` |
| nodal jump-aware history gradient | `1.107150e-04` | `6.208005e-01` | `3.328005e-01` | `1.406322e-01` |

Curvature-contract static-grid probe, `T=0.4`:

| case | max/final KE scale | cut-face kappa std | radius std |
|---|---:|---:|---:|
| dynamic grid after CHK-014 | `~1.15e-04` | `1.855170e+00` | `9.048483e-05` |
| static grid after CHK-014 | `8.437e-05` | `1.788002e+00` | `7.979870e-05` |

Pressure residual diagnostic on full static droplet `T=1.5`:

```text
bulk_residual_rms = 2.100303e+00
high_frequency_fraction = 9.695747e-01
jump = -5.028564e-01
jump_abs_error = 2.148564e-01
curvature_std = 4.275355e+01
```

## Inference

The shortest remaining path is no longer interface advection or grid rebuild.
The dominant kinetic injection is the IPC predictor pressure-history term:

```python
dpn_dx = pressure_grad_op.gradient(state.previous_pressure, 0)
dpn_dy = pressure_grad_op.gradient(state.previous_pressure, 1)
conv_step -= grad(p^n) / rho
```

This differentiates the stored previous pressure as a nodal field.  In a
pressure-jump method, the pressure history is not a smooth nodal scalar; its
physically meaningful gradient is the same affine face law used by the PPE and
projection:

```text
G_Gamma(p; j) = G_f(p) - B_Gamma(j).
```

Removing the history gradient proves it is the kinetic injection path, but it
also destroys the pressure jump.  Reconstructing only `B_Gamma(j)` back to nodes
also fails.  Therefore the next theory-respecting fix should not be a damping,
CFL, cap, or smoothing change.  It should make the IPC pressure-history
predictor face-native:

```text
previous pressure history contribution
  = face-space affine pressure acceleration,
    using the same cut-face jump context and coefficient/locus as projection,
  then reconstruct nodes only as a derived state if the viscous predictor needs it.
```

Curvature remains a secondary contract: exact curvature improves jump error but
does not remove the kinetic injection.  It should be handled after the
pressure-history face-space contract is restored.

## Validation

```bash
python3 -m py_compile experiment/ch14/probe_pressure_history_gradient_n64.py
git diff --check
```

PASS.

The remote `make cycle` attempt for this batch was rejected by the approval
reviewer because it would rsync the worktree to the remote host.  The diagnostic
batch was therefore run locally with `TWOPHASE_FORCE_LOCAL=1`.

## SOLID-X

Diagnostic extension only.  No production solver path was changed, no tested
implementation was deleted, and no damping/CFL/smoothing workaround was adopted.
