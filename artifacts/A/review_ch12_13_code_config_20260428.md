# §12--§13 Code / Configuration Review — 2026-04-28

## Verdict

PASS after fixes.  Review scope: §13 experiment scripts, §13 paper values/figures,
and §14 production YAML stack used as the reference configuration for §12--§13.

## Findings And Fixes

1. **V10 hidden scheme mismatch — fixed.**
   - Finding: V10 prose described high-order FCCD-style CLS advection, but the
     script used WENO5.
   - Fix: V10 now uses `FCCDLevelSetAdvection` in flux mode with TVD--RK3.

2. **V10 non-uniform FCCD construction order — fixed.**
   - Finding: FCCD was constructed before `grid.update_from_levelset`, leaving
     face weights inconsistent with the updated non-uniform grid.
   - Fix: construct/update grid first, then rebuild CCD/FCCD operators.
   - Effect: stale-path Zalesak `alpha=2, N=128` volume drift no longer appears;
     corrected value is `1.519%`.

3. **Missing 2D visual diagnostics — fixed.**
   - Added V3 static-droplet pressure/speed field snapshot.
   - Added V10 Zalesak initial/final snapshots.
   - Added V10 single-vortex deformation/reversal snapshots.

4. **Single-vortex case missing — fixed.**
   - Added reversible single-vortex CLS transport case to V10.
   - Result: `N=96, alpha=2`, `L1_reverse = 2.424e-3`, volume drift `0.000%`.

5. **V3 setting mismatch — fixed.**
   - Finding: paper text said `rho_l = rho_g = 1`, script used `rho_l=10`,
     `rho_g=1`.
   - Fix: paper setting now matches the script.

6. **V4 setting description mismatch — fixed.**
   - Finding: script docstring described an exact periodic Galilean test, but
     the script is a wall-BC reduced residual-scale check.
   - Fix: script docstring and paper setting now describe the reduced test.

7. **§14 YAML registry stale — fixed.**
   - Finding: paper listed two old YAML filenames; repository contains three
     active config files.
   - Fix: §14 now lists `ch14_capillary.yaml`, `ch14_rising_bubble.yaml`, and
     `ch14_rayleigh_taylor.yaml`.

## Residual Intentional Exceptions

- V5 uses FD only as a labeled comparison baseline.
- V4-b still uses a reduced first-order `phi` update and is explicitly reported
  as a conditional setting check, not as the production interface-transport
  validation.
- V1/V2 use analytic/spectral or MMS-style reduced diagnostics to isolate time
  and spatial orders; this is intentional and not a production-stack benchmark.

## Validation

- `make cycle EXP=experiment/ch13/exp_V3_static_droplet_longterm.py`
- `make cycle EXP=experiment/ch13/exp_V10_cls_advection_nonuniform.py`
- `python3 -m py_compile experiment/ch13/exp_V*.py`
- stale-value scan: no `12.17%`, old WENO import, or stale ch14 YAML filenames
  remain in §13/§14 or ch13 scripts.
- figure-reference check: all §13/§14 `paper/figures/*.pdf` references exist.
