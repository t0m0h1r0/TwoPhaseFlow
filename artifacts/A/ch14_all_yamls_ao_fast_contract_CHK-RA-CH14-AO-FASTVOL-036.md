# CHK-RA-CH14-AO-FASTVOL-036 — All Chapter 14 YAMLs Use AO-Fast

## Trigger

User requested the same AO-Fast YAML correction for all Chapter 14 YAMLs, not
only the capillary-wave benchmark.

## Correction

Updated the remaining Chapter 14 YAMLs:

- `experiment/ch14/config/ch14_static_droplet.yaml`
- `experiment/ch14/config/ch14_oscillating_droplet.yaml`
- `experiment/ch14/config/ch14_rising_bubble.yaml`
- `experiment/ch14/config/ch14_rayleigh_taylor.yaml`

Each now matches the capillary-wave AO-Fast front door:

- `interface.state_space.kind: geometric_cell_fraction`
- transported `q`, normalized `theta`, and P1 gauge `phi`
- active-cached hard-cell-volume compatibility
- GPU-required struct-of-arrays storage
- inner host transfers forbidden
- dense runtime fallback forbidden
- `fallback.policy: none`
- `numerics.interface.transport.variable: q`
- `numerics.interface.transport.spatial: geometric_swept_volume`
- `numerics.interface.tracking.primary: q`
- `interface.reinitialization.algorithm: none`
- `interface.reinitialization.schedule.every_steps: 0`
- `momentum.terms.surface_tension.source: bundle_virtual_work`
- `closed_interface.endpoint: geometric_cell_fraction`
- `residual_contract.constraints: [cell_volume]`
- `poisson.operator.capillary_reaction_projection: pressure_component_hodge`

Documentation and tests were updated so the canonical Chapter 14 contract is
now uniform AO-Fast rather than capillary-only AO-Fast plus diffuse-CLS
remaining routes.

## Validation

- `PYTHONPATH=src /Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3`
  parser/solver probe confirmed all five Chapter 14 YAMLs build with
  `geometric_swept_volume`, `q_cell_fraction`, `bundle_virtual_work`,
  `reinit_method=None`, and `reinit_every=0`.
- Remote-first `make test PYTEST_ARGS='-k ch14 -q'` passed:
  `15 passed, 728 deselected`.
- Remote-first `make test PYTEST_ARGS='-q'` passed:
  `710 passed, 33 skipped`.
- `git diff --check` passed.

## Non-Changes

No production solver source, physical constants, CFL reduction, damping,
smoothing, curvature cap, clipping repair, hidden PCG/DC fallback, dense-AO
runtime fallback, main merge, branch deletion, or worktree removal was
introduced.
