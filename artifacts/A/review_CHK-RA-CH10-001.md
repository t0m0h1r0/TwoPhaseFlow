# CHK-RA-CH10-001 — Chapter 10 Strict Review

Date: 2026-05-06
Scope: `paper/sections/10_grid.tex`, `10b_ccd_extensions.tex`, `10c_fccd_nonuniform.tex`, `10d_ridge_eikonal_nonuniform.tex`; adjacent consistency checked against chapters 5, 11, and 13.

## Round 1 Verdict: FAIL

### MAJOR-1 — Nonuniform-grid narrative overclaimed the verified path

Chapter 10 stated that the paper's standard route is "every-step interface-following nonuniform grid + ALE/remap + reset/reprojection." This conflicted with the latest validation boundary in chapter 13: V8 verifies fixed nonuniform static BF reduction, V9 verifies finite-time nominal/local-epsilon switch in the range-projected pressure-jump/HFE stack, and moving long-time nonuniform interface runs remain outside the verified guarantee. As written, chapter 10 made an unverified closure read like the current paper result.

Root fix: reframe chapter 10 as the discrete contract for nonuniform geometry. The verified current route is now explicitly fixed nonuniform/static or finite-time switch diagnostic; every-step following grids are described only as a standardization condition requiring conservative remap, velocity reprojection, history reset, and face-geometry rebuild.

### MAJOR-2 — Grid-count notation and equidistribution endpoints were inconsistent

The chapter used `N` as both number of grid points and number of intervals. The composite equidistribution formula used `i/N_a` while the actual grid construction used `i/(N-1)`, and the FCCD subsection defined nodes `x_0 ... x_N` with an `N x (N+1)` matrix while surrounding sections use `N` grid points. This is not just typography: it changes endpoint normalization and matrix dimensions.

Root fix: equidistribution now uses `i/(N_a-1)`, `i=0,...,N_a-1`; FCCD nonuniform notation now uses nodes `x_0 ... x_{N-1}`, faces `i=1,...,N-1`, and matrix size `(N-1) x N`. The Ridge--Eikonal reference width now uses the same `N_a-1` interval convention.

### MAJOR-3 — D4 reconstruction width looked like a hidden calibration path

Chapter 10 introduced `\varepsilon_\text{scale}=1.4` as a representative value for nonuniform Ridge--Eikonal D4. Chapter 5 now defines the standard width-preserving route as `f=1`, with `f>1` only as an explicit sensitivity/comparison condition. The 10章 wording therefore reintroduced the very hidden width regularization that chapter 5 had removed.

Root fix: D4 now states that the standard width-preserving path uses `\varepsilon_\text{scale}=1`. Any non-unit scale is a declared sensitivity/comparison condition, not part of the fixed-grid standard closure. Failure to meet volume tolerance is treated as a monitor/seed/Stage-F acceptance failure rather than solved by spatial scale calibration.

### MINOR-1 — Mode naming blurred reduced validation and moving-grid requirements

The fixed-grid mode was called only a comparison route, even though it is the current verified nonuniform reduction route for V8/V9-style checks. The moving-grid mode was called the standard route before the closure requirements were fully qualified.

Root fix: fixed grid is now described as "verified reduced/comparison route"; moving grid is "closure conditions required for standardization."

## Round 2 Verdict: PASS

MAJOR+ findings after remediation: 0.

Targeted scans to run:

- stale standard-path wording for every-step nonuniform grid
- stale `\varepsilon_\text{scale}=1.4`
- endpoint/index inconsistencies (`i/N_a`, `x_0...x_N`, `N x (N+1)`)
- implementation-history wording (`trial`, `fallback`, `old`, version-change language)

Validation:

- Targeted stale wording/index/width scans: PASS. The only remaining "every-step standard" wording is explicitly conditional on adopting the full following-grid closure.
- `git diff --check`: PASS.
- `make -C paper`: PASS (`paper/main.pdf`, 243 pages).
- Build-log fatal/error/undefined-reference/undefined-citation/overfull scans: PASS.
