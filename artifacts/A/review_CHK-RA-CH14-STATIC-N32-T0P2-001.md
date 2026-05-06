# CHK-RA-CH14-STATIC-N32-T0P2-001

## Scope

Validate the ch14 static droplet production stack at `N=32`, `T=0.2`, using
the canonical `ch14_static_droplet.yaml` numerical scheme with only resolution,
final time, and output directory changed in a temporary YAML.

Temporary config used for the run:
`experiment/ch14/config/_tmp_ch14_static_droplet_base_n32_t0p2.yaml`

The temporary YAML was removed after validation; the checked-in ch14 config
directory is back to the canonical five YAML files.

## Finding And Fix

The first `N=32`, `T=0.2` run completed, but reported a large
`volume_conservation` drift (`final=6.899368485731e-02`,
`max=8.359107723004e-02`). The root cause was not the YAML itself:
`PsiDirectTransport` cached control volumes at construction time. On a dynamic
nonuniform fitted grid, rebuilds update `grid.cell_volumes()`, so using the
initial cached `dV` makes the mass correction target stale after rebuilds.

Fix:

- `src/twophase/levelset/transport_strategy.py` now fetches current grid
  control volumes at each mass-correction and adaptive monitor call.
- `src/twophase/tests/test_fccd_advection_levelset.py` adds a CPU/GPU-covered
  regression test proving `PsiDirectTransport` uses post-rebuild volumes.
- Stale ch14 YAML tests were updated to the current base stack:
  reinitialization every step and both axes interface-fitted for capillary.
- The stale capillary YAML comment that still described a uniform x axis was
  corrected.

## N=32 T=0.2 Result After Fix

Command:

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make cycle EXP=experiment/run.py \
  ARGS="--config _tmp_ch14_static_droplet_base_n32_t0p2 --no-checkpoint-final"
```

Result path:
`experiment/ch14/results/_tmp_ch14_static_droplet_base_n32_t0p2/data.npz`

Key metrics:

| Metric | Value |
|---|---:|
| final time | `2.000000000000e-01` |
| diagnostic samples | `20` |
| final volume drift | `1.268959973271e-15` |
| max volume drift | `1.522751967925e-15` |
| final kinetic energy | `7.561465732234e-06` |
| max kinetic energy | `7.561465732234e-06` |
| final deformation | `0.000000000000e+00` |
| max abs deformation | `0.000000000000e+00` |
| final velocity Linf | `9.398281945014e-04` |
| final velocity L2 | `1.989656799237e-04` |

Young--Laplace pressure-jump check:

- Expected jump: `sigma / R = 0.072 / 0.25 = 2.88e-01`.
- Final phase-mask estimate (`psi<0.10`, `psi>0.90`):
  `3.084125635906e-01`, relative error `7.087695691182e-02`.
- Final geometric bulk estimate (`r<0.20`, `r>0.30`):
  `2.815555169594e-01`, relative error `2.237667722436e-02`.

The pressure jump is qualitatively correct but coarse-grid sensitive at `N=32`;
this is a smoke/short-gate validation, not a strict pressure-accuracy claim.
The corrected mass conservation is the critical pass/fail signal for this
dynamic fitted-grid static-droplet run.

## Validation

Local targeted tests:

```bash
PYTHONPATH=src /Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 \
  -m pytest src/twophase/tests/test_fccd_advection_levelset.py -q
```

Result: `8 passed`.

```bash
PYTHONPATH=src /Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 \
  -m pytest \
  src/twophase/tests/test_ns_pipeline.py::test_rebuild_grid_mass_conservation \
  src/twophase/tests/test_ns_pipeline_fccd.py::test_psi_direct_transport_applies_ch6_mass_correction \
  -q
```

Result: `2 passed`.

```bash
PYTHONPATH=src /Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 \
  -m pytest \
  src/twophase/tests/test_initial_conditions.py::test_ch14_yaml_initial_conditions_use_object_specs \
  src/twophase/tests/test_ns_pipeline_fccd.py::test_ch14_capillary_yaml_builds_solver \
  src/twophase/tests/test_ns_pipeline_fccd.py::test_ch14_rising_bubble_yaml_builds_solver \
  src/twophase/tests/test_ns_pipeline_fccd.py::test_ch14_capillary_yaml_uses_true_low_order_defect_base \
  -q
```

Result: `4 passed`.

Remote full GPU test:

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test
```

Result: `788 passed, 3 skipped`.

## Verdict

PASS for `N=32`, `T=0.2` static-droplet operation after fixing the stale dynamic
grid control-volume bug. No main merge was performed.
