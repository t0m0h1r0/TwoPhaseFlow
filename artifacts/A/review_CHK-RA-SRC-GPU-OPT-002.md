# CHK-RA-SRC-GPU-OPT-002 — src GPU Optimization Re-Audit

## Scope

Strict ResearchArchitect re-audit of `src/twophase/` computational schemes for
GPU residency, avoidable CuPy scalar synchronization, hidden device-to-host
full-field transfers, and CPU/GPU semantic parity.

Stop condition: no MAJOR+ findings, or review round > 10.

## Round 1 — MAJOR Fixed

Finding A: `DGRReinitializer.reinitialize()` still converted backend scalar
reductions to Python floats for interface-band existence, median width, and
scale gating.

Impact: on CuPy this forced device synchronization inside the reinitialization
scheme. The old comment treated the sync as acceptable because DGR is not run
every step, but it is still a numerical scheme hot path when selected.

Fix: replace the Python branch with `_band_median_or_default()`, which computes
the exact interface-band median by sorting backend arrays and selecting the
lower/upper median entries with device-side masks. The no-band fallback and the
scale gate now use `xp.where`, so GPU execution remains device-resident.

Finding B: host-only schemes accepted a GPU backend and then transferred full
fields to CPU:

- `PPESolverIIM`
- `PPESolverIterative`
- `FDPPEMatrix`
- `ConsistentIIMReprojector`

Impact: these paths looked GPU-configurable but were actually host workflows.
That is a hidden CPU fallback, not a GPU-optimized scheme.

Fix: fail closed on GPU before any host transfer. Users must select an existing
GPU-native PPE/reproject path or run these legacy/reference workflows
explicitly on CPU.

Finding C: `PPESolverFCCDMatrixFree` recorded linear-solve diagnostics by
extracting several scalar norms separately.

Impact: the solve itself stayed on device, but diagnostics forced multiple
serial scalar transfers after each solve.

Fix: compute the relative residual with device-side `xp.where` and transfer the
diagnostic vector once.

## Round 2 — No MAJOR+

Re-ran targeted host-boundary scans over:

- `src/twophase/ppe`
- `src/twophase/levelset`
- `src/twophase/ns_terms`
- `src/twophase/simulation`
- `src/twophase/ccd`

Remaining hits are classified as:

- explicit diagnostics or convergence-control scalar boundaries;
- checkpoint/output/runtime setup host materialization;
- legacy reference implementations retained under C2;
- host-only IIM/iterative/legacy-FD paths now rejected on GPU;
- `eikonal_fmm`, already rejected on GPU in favor of the GPU-resident
  `ridge_eikonal` path.

Stop: no MAJOR+ findings before round 10.

## Validation

- Targeted tests PASS:
  - `test_dgr_default_is_paper_exact_no_smoothing`
  - `test_dgr_band_median_default_matches_interface_band_median`
  - `test_gpu_fail_closed.py`
  - `test_iim.py`
  - IIM reprojector fail-closed tests
  - `test_fccd_matrixfree_records_true_linear_residual`
- `git diff --check` PASS.
- `make test` attempted remote first; remote unavailable, local CPU fallback
  PASS: `563 passed, 31 skipped in 73.59s`.

## SOLID-X

No C1 violation introduced. No tested implementation deleted. Unsupported
GPU paths now fail closed instead of silently transferring to host. Production
GPU-native paths preserve their algorithms while avoidable synchronization was
removed.
