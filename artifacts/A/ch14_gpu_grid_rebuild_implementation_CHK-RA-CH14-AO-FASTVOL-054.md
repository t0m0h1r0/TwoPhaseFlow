# CHK-RA-CH14-AO-FASTVOL-054 - GPU Grid Rebuild Implementation

## Trigger

User request: implement the GPU grid-update design established in
`WIKI-T-171`, without weakening the nonuniform/interface-tracking grid
contract.

## Implemented Contract

`Grid.update_from_levelset` now keeps the existing CPU path, but uses a
GPU-resident path when the backend is CUDA:

- `psi -> phi` inversion remains on the active backend;
- interface and closure-seed monitors are built with fixed-shape backend arrays;
- wall monitors are built on backend coordinate vectors;
- monitor equidistribution is computed by device prefix sums and a vectorized
  monotone inverse-CDF, avoiding host `np.interp`;
- cell-width floors are applied by the lower-bound simplex projection
  `d_i^*=f+beta max(d_i-f,0)`;
- the regular P1 stratum guard uses fixed device sweeps with vectorized
  coordinate-line shifts, avoiding host `argwhere` over the full field;
- only final one-dimensional coordinate metadata is transferred to host because
  `Grid.coords` remains the metric-builder source of truth.

The implementation deliberately does not disable nonuniform grids, does not
reduce rebuild cadence, and does not remove interface-tracking grid rebuilds.

## Files

- `src/twophase/core/grid.py`
- `src/twophase/tests/test_grid.py`
- `docs/wiki/theory/WIKI-T-171.md`
- `docs/02_ACTIVE_LEDGER.md`

## Validation

- Local `python3 -m py_compile src/twophase/core/grid.py src/twophase/tests/test_grid.py` PASS.
- Local `pytest src/twophase/tests/test_grid.py -q` PASS: `16 passed, 1 skipped`.
- `git diff --check` PASS.
- Remote `make test PYTEST_ARGS='twophase/tests/test_grid.py -q'` ran the remote suite and PASSed:
  `743 passed, 33 skipped`.
- Remote GPU capillary stage-chain with runner initial grid rebuild PASS:
  `make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 3 --runner-initial-grid-rebuild --backend gpu'`.
  It completed in `real 0m35.711s`; regular-stratum margin stayed
  `2.531835986218e-05`, and no fail-close occurred.

## SOLID / Fidelity Audit

- [SOLID-S] GPU coordinate rebuild helpers are separated from CPU legacy
  helpers and metric construction.
- [SOLID-D] The update path depends on backend array semantics and the existing
  grid metric builder contract, not on a concrete CuPy type.
- [SOLID-X] No physical parameter, CFL, damping, smoothing, tolerance
  weakening, fallback solver, uniform-grid replacement, rebuild-cadence
  reduction, interface-tracking removal, main merge, or branch deletion was
  introduced.
