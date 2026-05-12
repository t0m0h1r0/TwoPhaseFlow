# CHK-RA-CH14-CAPILLARY-YAML-UX-001 - active-geometry capillary YAML/UX naming

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: AO is a provisional name; merge latest main and follow the naming
there.

`origin/main` is `ad5fa7c2 merge: chapter 11 paper review`.  Merging latest
main into this worktree branch was a no-op because the branch already contained
that commit.  The main-facing paper text names the route
`アクティブ幾何毛管分解`; this change therefore uses
`active_geometry_capillary` as the canonical YAML scheme name.

No merge into `main` was performed.

## Decision

Chapter 14 experiment YAML should expose only the scheme choice:

```yaml
interface:
  state_space:
    scheme: active_geometry_capillary
```

The parser, not experiment authors, owns the fixed contract expansion:

```text
kind = geometric_cell_fraction
conserved_variable = q
normalized_view = theta
gauge = phi / p1_levelset
projection.implementation = active_cached
gpu_contract.required = true
gpu_contract.active_storage = struct_of_arrays
gpu_contract.inner_host_transfers = forbidden
gpu_contract.dense_runtime_fallback = forbidden
solver.primary = active_pcg_newton
solver.accelerators.dc_candidate.role = proposal_only
solver.fallback.policy = none
```

This keeps the YAML UX aligned with the theory: users select the state-space
scheme, while the active-geometry capillary decomposition front door stays
paper-fixed and fail-closed.

## Compatibility

The old `ao_fast` spelling is retained only as a parser alias so existing local
draft configs fail less abruptly.  It is not the canonical name in checked-in
Chapter 14 YAMLs, README text, or the short-paper memo prose.

Internal module and test names that still contain `ao_fast` are compatibility
or historical runtime-contract identifiers.  They were not renamed in this
slice because doing so would be a wider API migration unrelated to the YAML/UX
front door.

## Files Changed

- `src/twophase/simulation/config_models.py`
- `src/twophase/simulation/config_state_space.py`
- `src/twophase/tests/test_config_state_space.py`
- `src/twophase/tests/test_config_io_fccd.py`
- `experiment/ch14/config/ch14_*.yaml`
- `experiment/ch14/config/README.md`
- `docs/memo/short_paper/SP-AO_geometric_cell_fraction_state_space.md`

## Validation

- `git diff --check` PASS
- `make lint-ids` PASS
- `make test PYTEST_ARGS='-k config_state_space -q'` PASS:
  23 passed, 723 deselected
- `make test PYTEST_ARGS='-k config_io_fccd -q'` PASS:
  76 passed, 670 deselected

[SOLID-X] Parser responsibility is narrowed rather than expanded into runtime
solver work: it converts a canonical scheme token into the existing fixed
state-space contract.  No physical parameter, CFL, damping, smoothing,
curvature cap, FD/WENO/PPE fallback, dense runtime fallback, hidden CPU fallback,
experiment result, merge into main, or branch deletion was introduced.
