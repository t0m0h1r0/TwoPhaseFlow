# CHK-RA-IFACE-REGRID-003 — Main-Text Interface-Regrid Theory Placement

Date: 2026-05-03
Branch: `ra-interface-reconstruction-theory-20260503`
Verdict: PASS

## Correction

- The every-step interface-following fitted-grid theory is not appendix-only material.
- Chapter 10 now states the standard path up front: every physical step rebuilds the fitted non-uniform grid from the current interface.
- The appendix now only supplements the ALE omission scale estimate.

## Changes

- Renamed the Chapter 10 framing from fixed-grid geometry to interface-following grid geometry.
- Replaced the old scope box so the standard route is every-step interface-following rebuild plus conservative remap, velocity reprojection, history reset, and face-geometry reconstruction.
- Moved the Mode 1/Mode 2 decision, ALE omission estimate, and closure table into the main body.
- Demoted Appendix D.1 to a supplemental ALE-effect estimate that points back to the Chapter 10 definition.
- No additional code change was required in this checkpoint; the default every-step rebuild and config/runtime policy were already restored in CHK-RA-IFACE-REGRID-002.

## A3 Traceability

- Equation: `eq:ale_omission_error` now lives in the Chapter 10 main-body decision block.
- Discretization: fixed-grid Mode 1 is comparison-only; every-step Mode 2 is the standard path with conservative remap/reprojection/reset/current-face-geometry reconstruction.
- Code: every-step default remains `grid_rebuild_freq=1` / omitted fitted-grid `schedule -> 1`, as recorded in CHK-RA-IFACE-REGRID-002.

## Validation

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS, producing `paper/main.pdf` with 242 pages.
- `paper/main.log` undefined/citation/multiply-defined grep clean.
- `git diff --check` PASS.
- Touched-section KL-12 literal-dollar scan PASS.
- Old fail-closed/static-standard wording scan over touched paper sections PASS.

## SOLID-X

- [SOLID-X] No implementation responsibility changed in this checkpoint.
- [SOLID-X] No tested code was deleted. The paper placement correction only makes the already-restored every-step default visible in the main text.
