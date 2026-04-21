# CHK-174: per-step interface-following grid rebuild for ch13_05 rising bubble

Date: 2026-04-21
Branch: `worktree-rising-bubble`
Execution: remote GPU via `make cycle`

## Change

The dynamic rising-bubble variants now request interface-following every step:

- `experiment/ch13/config/ch13_05_rising_bubble_fullstack_alpha2_dynamic.yaml`
- `experiment/ch13/config/ch13_05_rising_bubble_fullstack_alpha2_dynamic_debug.yaml`

Both set:

```yaml
grid:
  grid_rebuild_freq: 1
```

Removed the previous `TwoPhaseNSSolver` fallback that silently changed
non-uniform `grid_rebuild_freq == 1` to `10`. This makes the YAML value the
single source of truth: `0` means static fitted grid, `1` means per-step
interface following, and `K>1` means every K steps.

## Verification

Local:

```bash
PYTHONPATH=src /Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m pytest \
  src/twophase/tests/test_ns_pipeline_fccd.py \
  src/twophase/tests/test_ns_pipeline.py -q
```

Result: `16 passed`.

Remote GPU:

```bash
make cycle EXP="experiment/ch13/run.py ch13_05_rising_bubble_fullstack_alpha2_dynamic_debug"
```

Log confirms activation:

```text
[dynamic/1 non-uniform] grid built from IC, h_min=9.1885e-03
```

Result:

| Case | Result | Early diagnostics |
|---|---|---|
| dynamic/10 debug | BLOWUP step 19, `t=0.004829` | prior CHK-173 baseline |
| dynamic/1 debug | BLOWUP step 4, `t=0.0013` | step 2 `bf_res=6.391e+05`, `div_u=7.793e+00` |

## Interpretation

Per-step interface following is active. The stronger instability is expected:
moving the non-uniform grid every step repeatedly remaps the velocity/CLS state
and then applies the currently non-closed projection/corrector pair. This
amplifies the CHK-171/172 projection mismatch earlier than the every-10-step
variant.

## Next Action

Keep `dynamic/1` as the requested active behavior, but treat the blowup as a
diagnostic result. The production fix should target the projection state:
carry conservative face/staggered fluxes through the projection, then
reconstruct nodal velocities from those projected fluxes.

