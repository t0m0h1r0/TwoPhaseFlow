# CHK-RA-CH12-U6C-001 — U6-c HFE 2D root-cause memo

Date: 2026-04-29
Branch: `worktree-ra-ch12-u6c-hfe2d-20260429`
id_prefix: `RA-CH12-U6C`

## Verdict

Root cause is not the HFE theory. It is an implementation/theory mismatch in
the 2D tensor-product Hermite data.

For the row-wise x interpolation used before the final y Hermite interpolation,
the theory requires

- `q`: `(q, q_x, q_xx)`
- `q_y`: `(q_y, q_xy, q_xxy)`
- `q_yy`: `(q_yy, q_xyy, q_xxyy)`

The previous code used `(q_y, q_xy, q_xyy)` for the `q_y` row derivative and
used a linear fallback for `q_yy`. That is the simplified tensor variant which
§9c explicitly says has no O(h^6) guarantee.

## Hypotheses Checked

| ID | Hypothesis | Evidence | Result |
|---|---|---|---|
| H1 | Missing full tensor mixed derivatives lower the 2D order | Replacing the simplified row data with `(q_xxy, q_xxyy)` restores U6-c 2D med from 3.21 effective slope to 8.72 effective diagnostic slope; analytic-CP variant gives pairwise O(h^6) rates. | Adopted |
| H2 | Closest-point normal error is the main cause | CCD closest-point coordinate error is large only at N=32 max, then drops at rates 12.04, 14.94, 7.71. It explains the coarse max outlier, not the persistent median O(h^3) trend. | Secondary |
| H3 | 6-cell band is too wide | Varying band_cells = 1,2,3,4,6 keeps median pairwise rates around 2.5-3.7 in the simplified implementation. | Rejected |
| H4 | Source/target sign convention is flipped | U6 uses `phi=R-r`, so HFE's `source_sign=-1` correctly extends outside source (`phi<0`) into inside target (`phi>=0`). | Rejected |
| H5 | Wall boundary CCD pollution dominates | Circle band is away from the wall; full tensor with the same CCD/wall setup removes the low-order behavior. | Rejected |
| H6 | Test field lacks mixed structure | The field is separable but genuinely 2D, so mixed derivatives are nonzero and exercise the tensor product. | Rejected |
| H7 | Plot/table postprocessing causes a false slope | Direct function-level U6-c recomputation reproduces the old 5.10/3.21 and the fixed 11.35/8.72 before plotting. | Rejected |
| H8 | CPU/GPU backend discrepancy | U6-c uses CPU. The fix uses `backend.xp` only and vectorised parity tests pass against a scalar full-tensor reference. | Rejected |
| H9 | Hermite-5 1D primitive is wrong | U6-c 1D remains 5.91 and unit tests already cover 1D high-order behavior. | Rejected |

## Diagnostic Runs

Local function-level diagnostic, same U6-c error definition:

| Variant | max errors N=32,64,128,256 | max rates | med rates |
|---|---|---|---|
| previous simplified tensor | 1.025e-03, 1.514e-06, 1.994e-07, 2.538e-08 | 9.40, 2.92, 2.97 | 3.67, 3.25, 2.72 |
| full tensor + CCD closest point | 1.025e-03, 4.012e-07, 1.222e-11, 5.795e-14 | 11.32, 15.00, 7.72 | 10.70, 8.08, 7.41 |
| full tensor + analytic closest point | 3.425e-10, 5.710e-12, 9.992e-14, 1.998e-15 | 5.91, 5.84, 5.64 | 6.57, 6.34, 5.70 |
| closest-point coordinate error | 3.777e-04, 8.983e-08, 2.862e-12, 1.368e-14 | 12.04, 14.94, 7.71 | 10.49, 8.42, 7.53 |

Interpretation: analytic closest-point isolates the Hermite interpolation and
shows the expected O(h^6). The CCD closest-point path adds a coarse-grid max
outlier at N=32, but does not explain the old median low order. Therefore the
short path is to restore the full tensor data in `HermiteFieldExtension`, not
to tune the band, the figure, or the slope calculation.

## Validation

- `run_U6c()` after fix: 1D slope 5.91, 2D max effective slope 11.35, 2D median effective slope 8.72.
- `pytest src/twophase/tests/test_hfe.py src/twophase/tests/test_hfe_vectorised.py`: 12 passed.
- [SOLID-X] No new class responsibility split needed. The fix stays inside the existing HFE numerical kernel and its tests.
