# CHK-RA-CH14-REALPARAM-001 — ch14 real-parameter audit

## Scope

Target configs:

- `experiment/ch14/config/ch14_capillary.yaml`
- `experiment/ch14/config/ch14_oscillating_droplet.yaml`

The numerical stack is unchanged.  This audit changes only SI physical scale,
material constants, final times, snapshot times, and tests/docs that lock those
values.

Initial validation exposed the then-existing fail-closed contract that
`conservative_common_flux` could not be combined with dynamic grid rebuilds
until conservative `q,m,p` remap existed.  After merging main
`CHK-RA-COMMON-FLUX-REMAP-001`, that remap/reinit representation is available,
so the targeted capillary and oscillating-droplet YAMLs restore the
interface-following route with `grid.distribution.schedule: 1`.

After the conservative common-flux remap/reinitialization representation landed
on main, both targeted dynamic YAMLs use every-step profile restoration:
`grid.distribution.schedule: 1` and
`interface.reinitialization.schedule.every_steps: 1`.

The same smoke reached `data.npz` and then fail-closed in plotting because the
saved affine pressure face cochain was not same-phase integrable as a scalar
Hodge representative at the smoke time.  The oscillating-droplet pressure
snapshot now plots the stored scalar `pressure` field, matching the README rule
for non-integrable affine cochains.

## Interpretation

The user request "N=10mm程度" is treated as a 10 mm-class physical length:

- Capillary wave: wavelength `lambda = 10 mm`.
- Oscillating droplet: equivalent diameter `2 R_eq = 9.949874 mm`.

Both cases use a 20 mm square tank so the interface stays away from walls while
preserving the existing relative geometry.

## Adopted Material Constants

Approximate water-air values at 20 C:

- `rho_l = 998.2 kg/m^3`
- `mu_l = 1.002e-3 Pa s`
- `rho_g = 1.204 kg/m^3`
- `mu_g = 1.825e-5 Pa s`
- `sigma = 0.0728 N/m`
- `g = 0` for both capillary-only benchmarks

## Capillary Wave

Geometry:

- Domain: `0.02 m x 0.02 m`
- Mode: `m = 2`
- Wavelength: `lambda = L_x / m = 0.01 m`
- Initial interface: `y = 0.01 + 0.0002 cos(2 pi m x / L_x)`

Inviscid small-amplitude reference:

```text
k = 2 pi m / L_x = 628.318530718 1/m
h_l = h_g = 0.01 m
omega = sqrt(sigma k^3 / (rho_l coth(k h_l) + rho_g coth(k h_g)))
      = 134.419859151 1/s
T = 2 pi / omega = 0.046742983863 s
```

The continuum reference period is retained as a theory reference, but the
paper-facing production window uses the signed mode-2 response so that the
2-D snapshots show one actual cycle of the computed benchmark:

```text
t = 0,
    0.008899695230   first signed-amplitude zero crossing,
    0.017677817828   lower signed-amplitude extremum,
    0.026630729902   second signed-amplitude zero crossing,
    0.035379718894   return to the upper signed-amplitude extremum.
```

The paper-facing capillary-wave history uses `signed_interface_amplitude`,
the signed projection of the reconstructed interface onto the configured
cosine mode.  The older `interface_amplitude` is intentionally retained as a
non-negative envelope diagnostic, but it folds the sign and therefore has half
the physical period; it must not be used to count capillary-wave periods.

## Oscillating Droplet

Geometry:

- Domain: `0.02 m x 0.02 m`
- Center: `(0.01 m, 0.01 m)`
- Semi-axes: `a = 0.0055 m`, `b = 0.0045 m`
- Initial signed deformation: `D0 = (a-b)/(a+b) = 0.10`
- Area-equivalent radius: `R_eq = sqrt(ab) = 0.004974937 m`

Rayleigh-Lamb `n=2` reference:

```text
omega0 = sqrt(n(n^2-1)sigma / ((rho_l + rho_g) R_eq^3))
       = 59.578473371 1/s
T = 2 pi / omega0 = 0.105460663082 s
```

Snapshot times are `0, T/4, T/2, 3T/4, T`.

## Validation

- `git diff --check`: PASS
- Targeted config tests:
  `test_ch14_capillary_yaml_loads_execution_stack`,
  `test_ch14_oscillating_droplet_yaml_uses_signed_deformation_only`, and
  `test_ch14_oscillating_droplet_variant_uses_signed_deformation_only`,
  plus `test_ch14_canonical_yamls_share_base_numerical_stack`: PASS
- Remote-first experiment execution: remote unavailable; local fallback is used
  with the project virtualenv on `PATH`.
- Full capillary local fallback was attempted after the remote check failed, but
  CPU execution was stopped after it exceeded the useful interactive budget.
- Local smoke copies in `/private/tmp` PASS:
  - `/private/tmp/ch14_capillary_smoke.yaml`: 3 steps, final `t=5.0e-5`,
    `dt_cap=1.844e-5`, finite KE, wrote
    `/private/tmp/results/ch14_capillary_smoke/data.npz`.
  - `/private/tmp/ch14_oscillating_droplet_smoke.yaml`: 2 steps, final
    `t=5.0e-5`, `dt_cap=2.652e-5`, finite KE, wrote
    `/private/tmp/results/ch14_oscillating_droplet_smoke/data.npz`.

## SOLID

[SOLID-X] Parameter/config/docs/test update only.  No solver source, numerical
operator, pressure/PPE route, capillary force implementation, damping/CFL
workaround, smoothing, curvature cap, benchmark branch, blanket projection, or
QP-as-physics path was changed.
