# CHK-173: dynamic grid fitting activation for ch13_05 rising bubble

Date: 2026-04-21
Branch: `worktree-rising-bubble`
Execution: remote GPU via `./remote.sh run`

## Change

Added dynamic-grid variants:

- `experiment/ch13/config/ch13_05_rising_bubble_fullstack_alpha2_dynamic.yaml`
- `experiment/ch13/config/ch13_05_rising_bubble_fullstack_alpha2_dynamic_debug.yaml`

At CHK-173 both set:

```yaml
grid:
  grid_rebuild_freq: 10
```

CHK-174 supersedes this cadence for the active dynamic variants: both dynamic
configs now set `grid_rebuild_freq: 1` for per-step interface following. See
`docs/memo/ch13_05_per_step_grid_rebuild.md`.

Updated `run_simulation()` so all `alpha_grid > 1` cases first fit the
non-uniform grid to the initial condition. For dynamic cases, rebuilds then
start at `step_index > 0` every `grid_rebuild_freq` steps. This avoids the
previous dynamic path starting from a uniform-grid first step.

## Remote GPU result

Command:

```bash
./remote.sh run experiment/ch13/run.py ch13_05_rising_bubble_fullstack_alpha2_dynamic_debug
```

Log confirms activation:

```text
[dynamic/10 non-uniform] grid built from IC, h_min=9.1885e-03
```

Result:

| Case | Result | Diagnostics |
|---|---|---|
| static alpha=2 debug | BLOWUP step 27, `t=0.007149` | `KE=1.05e6`, max `bf_residual=3.99e11`, max `div_u=9.73e4` |
| dynamic/10 alpha=2 debug | BLOWUP step 19, `t=0.004829` | `KE=1.22e6`, max `bf_residual=2.24e11`, max `div_u=4.40e4` |

## Interpretation

The dynamic grid-fitting logic is active and reaches the remote GPU run. It is
not stabilizing the current rising-bubble case. The first dynamic rebuild after
startup occurs at step 10; the run crosses the KE threshold at step 19. This is
consistent with CHK-171/172: remap/reprojection on a moving non-uniform grid
adds another projection-closure stress before the face-flux projection issue is
fixed.

## Status

Dynamic grid fitting is now available through dedicated configs and a corrected
initial-fit path. It should remain a diagnostic/experimental mode until the
face/staggered projection state from CHK-172 next-action is implemented.
