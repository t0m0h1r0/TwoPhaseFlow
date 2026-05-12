# CHK-RA-CH14-CAPILLARY-YAML-UX-004 - scalar active-geometry YAML selection

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: update the YAML according to the settled design.

## Change

All checked-in Chapter 14 YAMLs now use the shortest scheme-selection form:

```yaml
interface:
  state_space: active_geometry_capillary
```

The previous mapping form

```yaml
interface:
  state_space:
    scheme: active_geometry_capillary
```

was valid but still visually suggested that `state_space` might contain more
knobs.  The scalar form makes the UX match the design: the experiment selects
the scheme, and the parser owns every q/theta/phi, active-cached projection,
GPU-contract, solver-accelerator, and fail-close detail.

Updated YAMLs:

- `experiment/ch14/config/ch14_capillary.yaml`
- `experiment/ch14/config/ch14_static_droplet.yaml`
- `experiment/ch14/config/ch14_oscillating_droplet.yaml`
- `experiment/ch14/config/ch14_rayleigh_taylor.yaml`
- `experiment/ch14/config/ch14_rising_bubble.yaml`

Also updated the Chapter 14 README, WIKI current snippets, the short-paper memo
YAML example, and config tests so canonical YAMLs are checked as scalar scheme
selections.

## Validation

- `git diff --check` PASS
- `make lint-ids` PASS
- `make test PYTEST_ARGS='-k config_state_space -q'` PASS:
  27 passed, 723 deselected
- `make test PYTEST_ARGS='-k config_io_fccd -q'` PASS:
  76 passed, 674 deselected

[SOLID-X] YAML UX/docs/tests plus user-facing parser message cleanup only.  No
runtime physics, solver equation, physical parameter, CFL, damping, smoothing,
curvature cap, FD/WENO/PPE fallback, dense runtime fallback, hidden CPU
fallback, experiment result, merge into main, or branch deletion was introduced.
