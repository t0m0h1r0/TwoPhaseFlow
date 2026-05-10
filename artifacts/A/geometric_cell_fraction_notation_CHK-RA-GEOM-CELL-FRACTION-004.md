# CHK-RA-GEOM-CELL-FRACTION-004

## Purpose

User note:

> Not essential, but because the objects are derived from `psi/phi`, I want
> `I` and `F` to be Greek letters.

This note refines notation only.  It does not change the theory or decide
adoption.

## Notation Decision

Use Greek symbols in the living theory notation:

```text
old working notation       living notation
F_C                        theta_C
I_h                        Gamma_h
F or F_h as fraction field theta or theta_h
```

Meaning:

```text
theta_C  geometric liquid occupancy / cell fraction
Gamma_h  reconstructed discrete interface complex
phi      level-set gauge
psi      optional smoothed profile/gauge
```

## Rationale

`Gamma_h` is the natural discrete interface symbol because the continuous
interface is already `Gamma(t)`.

`theta_C` is chosen for the cell fraction because:

- it is Greek, matching `psi` and `phi`;
- it avoids overloading `F` as a generic flux/field/VOF notation;
- it avoids `alpha_C`, which would collide with grid-stretching `alpha` and
  time-integration coefficients;
- it leaves `chi_l` available for the continuous sharp characteristic
  function when needed.

When an angle is needed in manufactured probes, use `beta` rather than
`theta` to avoid local ambiguity.

## Living Single-Owner Rule

```text
theta_C owns material volume and density.
Gamma_h owns sharp surface and volume geometry.
phi/psi are derived gauges unless an equivalence proof promotes them.
```

Historical artifacts may still contain `F_C` and `I_h`; they should be read as
the predecessor notation for `theta_C` and `Gamma_h`.
