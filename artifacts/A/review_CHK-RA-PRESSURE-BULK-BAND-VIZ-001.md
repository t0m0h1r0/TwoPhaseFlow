# CHK-RA-PRESSURE-BULK-BAND-VIZ-001

## Scope

User observation: the constant-pressure-looking region near the interface appears too wide.

This check targets visualization semantics only.  It does not change the pressure solve, capillary range projection, curvature, CFL, smoothing, or any momentum/PPE calculation scheme.

## Finding

The observed width is caused by the `pressure_bulk` visualization contract, not by a broadened pressure solve.  `pressure_bulk` intentionally masks the single-valued nodal pressure representative in the diffuse interface layer:

```text
bulk = (psi <= gas_max_psi) or (psi >= liquid_min_psi)
defaults: gas_max_psi = 0.05, liquid_min_psi = 0.95
```

For the pulled `N=64,T=1` static-droplet result, the centerline physical width of one masked interface side is:

- `0.05 < psi < 0.95`: `0.12089230169662823`
- `0.10 < psi < 0.90`: `0.07821963684054248`
- `0.20 < psi < 0.80`: `0.05078469185646589`
- `0.30 < psi < 0.70`: `0.024998250433138886`

With droplet radius `0.25`, the default `0.05..0.95` visualization band is visibly wide.  That is a plotting interpretation issue: sharp-interface pressure is phase-wise one-sided and discontinuous at `Gamma`; the nodal representative inside the diffuse band is not a physical single-valued observable.

## Change

`pressure_bulk_snapshot` now draws the two mask thresholds, `psi=gas_max_psi` and `psi=liquid_min_psi`, as thin dashed gray contours in addition to the existing black `psi=0.5` interface contour.

This makes the hidden undefined band visible without filling, smoothing, capping, narrowing, or otherwise altering pressure data.

Config control:

- `bulk_band_contours: true` by default
- set `bulk_band_contours: false` in a figure spec to restore the previous visual style
- `gas_max_psi` and `liquid_min_psi` remain configurable per figure

## Regeneration

Existing cached `N=64,T=1` plots were regenerated from `data.npz` using `make plot` and the temporary config was removed afterward:

```bash
PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH make plot EXP=experiment/run.py ARGS="--config _tmp_ch14_static_droplet_n64_t1_viz0p2"
```

Regenerated files:

- `experiment/ch14/results/_tmp_ch14_static_droplet_n64_t1_viz0p2/pressure_bulk_t0.003.pdf`
- `experiment/ch14/results/_tmp_ch14_static_droplet_n64_t1_viz0p2/pressure_bulk_t0.201.pdf`
- `experiment/ch14/results/_tmp_ch14_static_droplet_n64_t1_viz0p2/pressure_bulk_t0.401.pdf`
- `experiment/ch14/results/_tmp_ch14_static_droplet_n64_t1_viz0p2/pressure_bulk_t0.602.pdf`
- `experiment/ch14/results/_tmp_ch14_static_droplet_n64_t1_viz0p2/pressure_bulk_t0.803.pdf`
- `experiment/ch14/results/_tmp_ch14_static_droplet_n64_t1_viz0p2/pressure_bulk_t1.000.pdf`

## Validation

- `pytest src/twophase/tests/test_plot_snapshot_figures.py -q`: `6 passed`

## Verdict

The broad near-interface region is a visualization-mask artifact.  The fix is to expose the mask boundaries in the plot, not to alter pressure, capillary, or projection numerics.

[SOLID-X] Visualization-only change with targeted test coverage.  No production calculation scheme, damping/CFL workaround, curvature cap, smoothing, FD/WENO/PPE fallback, or alternate pressure scheme was introduced.
