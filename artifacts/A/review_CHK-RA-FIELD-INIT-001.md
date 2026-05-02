# CHK-RA-FIELD-INIT-001 — Field Initialization Architecture

Date: 2026-05-03
Branch: `ra-field-initialization-20260503`
Verdict: PASS AFTER EXTENSION AND GENERALIZATION

## Scope

- Library: `src/twophase/simulation/initial_conditions/`, `src/twophase/simulation/runtime_setup.py`, and the `TwoPhaseNSSolver.build_ic/build_velocity` entry points.
- Experiment surface: `experiment/ch14/config/README.md`.
- Focus: maintainable initial field composition, multiple object placement, and configurable initial velocity perturbations without introducing a second construction path.

## Design

- Shape composition remains owned by `InitialConditionBuilder`; no new solver-side special cases were added.
- `objects` is accepted as an experiment-facing alias for `shapes`, while `shapes` remains valid for primitive-level tests and existing configs.
- Object entries are generic shape primitives: `circle`, `ellipse`, `layer`, `rectangle`, `half_space`, `capillary_wave`, `perturbed_circle`, and `zalesak_disk` are peer options.
- `bubble` is only a convenience alias for a gas-filled circle, not the core object model.
- Velocity composition reuses the existing `VelocityField` abstraction. `CompositeVelocityField` sums child fields, and `SinusoidalPerturbation` is one child type rather than a separate parser route.
- Config shorthand supports both one primitive (`type: uniform`) and structured composition (`base` plus `perturbations`).

## Changes

- Added `default_shape_phase()` and `bubble` deserialization to `shape_factory.py`.
- Added `objects` support and mixed-key rejection to `InitialConditionBuilder.from_dict()`.
- Updated runtime IC normalization so `type: objects` and bare `objects:` infer the correct liquid background for bubble collections.
- Added `Layer` / `slab` as a finite-thickness axis-aligned layer primitive with `bounds`, `lower/upper`, `min/max`, or `center/thickness` input forms.
- Added `CompositeVelocityField` and `SinusoidalPerturbation`, with YAML factory support for `composite`, `superposition`, `sinusoidal`, and `sinusoidal_perturbation`.
- Documented object collections and velocity perturbation examples in the ch14 config README.

## Validation

- `git diff --check` PASS.
- Remote targeted pytest PASS: `twophase/tests/test_initial_conditions.py -k 'bubble or objects or mixed_shape_keys'` (`5 passed`).
- Remote targeted pytest PASS: `twophase/tests/test_initial_conditions.py -k 'sinusoidal_perturbation or composite_velocity'` (`3 passed`).
- Remote targeted pytest PASS: `twophase/tests/test_initial_conditions.py -k 'layer or generic_objects'` (`3 passed`).
- Remote full initial-condition pytest PASS: `twophase/tests/test_initial_conditions.py` (`44 passed`).
- Note: `make test PYTEST_ARGS="-k bubble"` also selected existing ch13 rising-bubble YAML tests and failed on missing `experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml`; this is unrelated to the new IC/velocity paths. A second `make test` attempt exposed the known quoting limitation for space-containing `-k` expressions, so direct remote pytest was used for the acceptance signal.

## SOLID-X

- [SOLID-X] No new violation found. High-level simulation construction still goes through `SimulationBuilder` / config runtime services; parsing stays in factories, composition stays in `InitialConditionBuilder` and `VelocityField`, and no tested implementation was deleted or hidden behind fallback behavior.
