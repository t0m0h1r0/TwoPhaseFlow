# CHK-RA-CODE-GPU-004 — Ch14 capillary-wave paper update

Date: 2026-05-16
Branch: `codex/ra-code-paper-gpu-review-20260516`
Mode: paper update only. No production source code or experiment YAML edits.

## Scope

Updated the paper so the Ch14 capillary-wave claims match the current `ch14_capillary` run and the accepted active-geometry capillary theory policy.

Changed files:

- `paper/sections/14_benchmarks.tex`
- `paper/sections/13e2_ao_capillary_split_gate.tex`
- Ch14 capillary paper figure PDFs under `paper/figures/ch14_capillary_*.pdf`

## Text Updates

Chapter 14 common-stack wording now separates the two interface transport routes:

- standard CLS route: FCCD conservative face-flux transport;
- active-geometry capillary route: q-owned geometric swept-volume transport with TVD--RK3.

The capillary-wave subsection now states that the finite-depth dispersion relation is the continuum phase clock, not a claim that the `32^2` viscous/discrete/moving-grid run must exactly return to the analytic amplitude after one period.

The Ch14 capillary numerical values were updated from the fresh current-code run:

| Metric | Updated paper value |
|---|---:|
| final `dy_min` | `3.9197e-4 m` |
| quarter-period signed amplitude | `1.563467e-5 m` |
| final signed amplitude | `1.587038e-4 m` |
| final amplitude ratio | `0.792` |
| max kinetic energy | `8.3385e-6` |
| final kinetic energy | `1.1483e-6` |
| final volume drift | `9.6223e-14` |
| max volume drift | `9.9611e-14` |

The V11 integration-gate table now repeats the rounded current values: max volume drift `9.96e-14`, max KE `8.34e-6`, final amplitude ratio `0.792`.

The Chapter 14 benchmark summary table now uses the actual one-period capillary time `T=T_sigma=0.046742983863 s` rather than the older shorter window.

## Figure Updates

Synced the paper's referenced Ch14 capillary figures from the fresh run output:

- signed amplitude, kinetic energy, volume drift histories;
- five psi snapshots;
- five velocity snapshots;
- five pressure/Hodge-representative snapshots.

Unreferenced older dashboard/interface-amplitude aggregate PDFs were not changed.

## Validation

Checks:

- `git diff --check`: PASS.
- Targeted stale-value scan over `paper/sections` and `paper/main.tex`: PASS; no old exact values or old `FCCD 保存形界面輸送` wording remain.
- `make -C paper`: PASS; generated `paper/main.pdf` with 276 pages.
- Final `paper/main.log` scan for LaTeX/package warnings, overfull/underfull boxes, undefined references/citations, missing glyphs, emergency stops, fatal errors, and undefined control sequences: PASS.

## SOLID / Scope

[SOLID-X] Paper text/figure update only. No `src/twophase/`, experiment YAML, physical parameter, CFL, damping, smoothing, tolerance, production algorithm, hidden fallback, main merge, branch deletion, or worktree removal was changed.
