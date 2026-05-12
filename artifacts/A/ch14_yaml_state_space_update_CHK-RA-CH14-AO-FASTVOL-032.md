# CHK-RA-CH14-AO-FASTVOL-032 - Chapter 14 YAML state-space update

## Purpose

User request:

> 14章の全てのYAMLを更新しておいて

The Chapter 14 production YAMLs must no longer leave the phase state space
implicit after the AO-Fast capillary split review.  The corrected theory says
that the checked-in Chapter 14 benchmarks remain the validated diffuse-CLS
production route, while `geometric_cell_fraction` AO-Fast requires an explicit
contract and must fail-close until its pressure-reaction split gate passes.

## Changes

Updated every checked-in Chapter 14 YAML:

```text
experiment/ch14/config/ch14_capillary.yaml
experiment/ch14/config/ch14_oscillating_droplet.yaml
experiment/ch14/config/ch14_rayleigh_taylor.yaml
experiment/ch14/config/ch14_rising_bubble.yaml
experiment/ch14/config/ch14_static_droplet.yaml
```

Each file now declares:

```yaml
interface:
  state_space:
    kind: diffuse_cls
```

This makes the production state carrier explicit.  It is not a numerical
parameter change and does not alter physical time, CFL, grid, material
constants, reinitialization cadence, or solver tolerances.

For graph/open-interface pressure-jump benchmarks, the surface-tension source
is now explicit:

```yaml
surface_tension:
  formulation: pressure_jump
  source: curvature_jump
```

Closed-interface benchmarks already declare `source: closed_interface_riesz`
with the pressure-component Hodge reaction projection.  The five YAMLs now
separate the three admitted meanings at the front door:

- diffuse CLS production route: checked-in Chapter 14 benchmarks;
- graph/open-interface capillarity: validated `curvature_jump`;
- closed-interface capillarity: validated `closed_interface_riesz`;
- AO-Fast `geometric_cell_fraction`: not implicit, requires a separate YAML
  contract and remains fail-closed before production admission.

## Supporting Updates

Updated `experiment/ch14/config/README.md` so the YAML design document states
the same state-space contract, and extended
`src/twophase/tests/test_config_io_fccd.py` to assert that all canonical
Chapter 14 YAMLs parse as `diffuse_cls`.

## Validation

Remote-first targeted test:

```text
make test PYTEST_ARGS='-k ch14_canonical_yamls -q'
```

Result:

```text
3 passed, 740 deselected
```

[SOLID-X] YAML configuration, config README, config-parser test, artifact, and
ledger only; no production solver source, physical parameter, CFL reduction,
damping, smoothing, curvature cap, FD/WENO/PPE fallback, hidden PCG/DC
fallback, AO-Fast production admission, or main merge was introduced.
