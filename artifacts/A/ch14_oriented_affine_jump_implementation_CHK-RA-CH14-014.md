# CHK-RA-CH14-014 — oriented affine-jump implementation and verification

- Worktree: `ra-ch14-capillary-rootcause-20260430`
- Branch: `ra-ch14-capillary-rootcause-20260430`
- Date: 2026-04-30
- Request: 理論と実装設計に基づいてコーディングし，正しく動作するか検証する。

## 1. Implemented contract

The affine interface-stress context now stores the physical pressure jump:

```text
j_gl = p_gas - p_liquid.
```

For Young--Laplace capillarity with:

```text
psi = 1 liquid, psi = 0 gas
n_lg = liquid -> gas
kappa_lg = div_Gamma n_lg
```

the builder computes:

```text
j_gl = -sigma * kappa_lg.
```

The face operator remains:

```text
G_Gamma(p; j_gl) = G(p) - B_Gamma(j_gl).
```

Therefore the numerical orientation is unchanged, while the physical sign is
fixed at the data-contract boundary.

## 2. Code changes

- `src/twophase/simulation/interface_stress_closure.py`
  - `InterfaceStressContext` now exposes
    `pressure_jump_gas_minus_liquid`.
  - `signed_pressure_jump_gradient()` consumes the explicit jump field rather
    than recomputing `sigma * kappa`.
  - `build_young_laplace_interface_stress_context()` centralises
    `j_gl=-sigma*kappa_lg`.
  - The older `kappa` alias is kept for diagnostics/backward compatibility.

- `src/twophase/ppe/fccd_matrixfree.py`
  - affine PPE context now uses the Young--Laplace builder.
  - legacy `jump_decomposition` context is preserved as tested legacy code.

- `src/twophase/simulation/ns_step_services.py`
  - face-corrector affine projection now receives the same oriented
    `InterfaceStressContext` as PPE assembly.

## 3. Verification tests

Added/updated tests in `src/twophase/tests/test_interface_stress_closure.py`:

| Test | Contract checked |
|---|---|
| `test_signed_pressure_jump_gradient_orientation` | face orientation still flips `B_Gamma` sign |
| `test_young_laplace_builder_stores_gas_minus_liquid_jump` | `kappa_lg>0` gives `j_gl<0` |
| `test_explicit_pressure_jump_context_is_not_recomputed_from_curvature` | explicit jump is consumed as data |
| `test_affine_jump_flux_vanishes_when_pressure_satisfies_jump` | static liquid droplet has higher liquid pressure |
| `test_affine_jump_flux_vanishes_for_static_gas_bubble_sign` | static gas bubble has higher gas pressure |

Updated `src/twophase/tests/test_ns_pipeline_fccd.py` to verify that the
corrector receives `pressure_jump_gas_minus_liquid=-6` for `sigma=2`,
`kappa_lg=3`.

## 4. Commands run

```text
make test PYTEST_ARGS="-k affine_jump -q"
```

Result:

```text
8 passed, 430 deselected
```

```text
make test PYTEST_ARGS="-k pressure_jump -q"
```

Result:

```text
12 passed, 426 deselected
```

Individual new sign-contract checks:

```text
make test PYTEST_ARGS="-k test_young_laplace_builder_stores_gas_minus_liquid_jump -q"
make test PYTEST_ARGS="-k test_explicit_pressure_jump_context_is_not_recomputed_from_curvature -q"
make test PYTEST_ARGS="-k test_signed_pressure_jump_gradient_orientation -q"
```

Result:

```text
1 passed each
```

`git diff --check` passed.

## 5. Known unrelated test issue

An attempted file-targeted `make test PYTEST_ARGS="twophase/tests/test_interface_stress_closure.py -q"`
falls through the remote wrapper as a full test-suite collection and fails on
pre-existing missing ch13 production config files:

```text
experiment/ch13/config/ch13_capillary_water_air_alpha2_n128.yaml
experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml
```

The new interface-stress tests themselves passed during that run, and the
failure set is unrelated to affine-jump sign logic.

## 6. SOLID audit

[SOLID-X] no violation. The change narrows the interface-stress boundary:
physics-specific Young--Laplace sign construction lives in a builder, while
the face-gradient operator consumes a generic pressure-jump field. No tested
legacy implementation was deleted.

