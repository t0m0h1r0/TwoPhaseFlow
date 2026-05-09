# CHK-RA-CH14-REALPARAM-001 — ch14 real-parameter audit

## Scope

Target configs:

- `experiment/ch14/config/ch14_capillary.yaml`
- `experiment/ch14/config/ch14_oscillating_droplet.yaml`

The numerical stack is unchanged.  This audit changes only SI physical scale,
material constants, final times, snapshot times, and tests/docs that lock those
values.

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
omega = sqrt(sigma k^3 / (rho_l + rho_g)) = 134.420327920 1/s
T = 2 pi / omega = 0.046742820855 s
```

Snapshot times are `0, T/4, T/2, 3T/4, T`.

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
  `test_ch14_oscillating_droplet_variant_uses_signed_deformation_only`: PASS

## SOLID

[SOLID-X] Parameter/config/docs/test update only.  No solver source, numerical
operator, pressure/PPE route, capillary force implementation, damping/CFL
workaround, smoothing, curvature cap, benchmark branch, blanket projection, or
QP-as-physics path was changed.
