# CHK-RA-CODE-GPU-002 — current-code verification of Ch14 capillary-wave paper claims

Date: 2026-05-16
Branch: `codex/ra-code-paper-gpu-review-20260516`
Mode: verification only. No production source code edits.

## Verdict

The current code supports the paper's core capillary-wave claim: the checked-in `ch14_capillary` route completes one continuum capillary-wave period, keeps the wave bounded, reverses phase with the correct restoring sign, preserves q-volume at machine-roundoff scale, and uses the active-geometry graph-HFE / pressure-component Hodge route described in the manuscript.

However, the paper is not literally correct at publication-table precision. The exact numerical values printed in `paper/sections/14_benchmarks.tex` and repeated in `paper/sections/13e2_ao_capillary_split_gate.tex` are slightly stale relative to a fresh current-code run. The mismatch is small for amplitude and energy, but the volume-drift values differ by about a factor of two while still remaining around `1e-13`. This is not a physics failure, but the paper should be updated or rounded less aggressively before claiming exact reproduced values.

## Fresh Current-Code Run

Command:

```text
make cycle EXP=experiment/run.py ARGS="--config ch14_capillary --no-checkpoint-final"
```

Result:

- Remote run completed successfully in `11m44.201s`.
- Output pulled to `experiment/ch14/results/ch14_capillary/`.
- `data.npz` reports `pre_blowup_checkpoint_written=False`.
- No source, YAML, or paper file was edited for the run.

## Theory And YAML Consistency

The paper's finite-depth capillary-wave reference is internally correct for the YAML parameters:

| Quantity | Current recomputation |
|---|---:|
| `k = 2*pi*m/Lx`, `m=2`, `Lx=0.02` | `628.318530717959` |
| `omega` from `sigma k^3 / (rho_l coth(kh_l) + rho_g coth(kh_g))` | `134.419859150827` |
| `T = 2*pi/omega` | `0.046742983863` |

The Ch14 capillary YAML matches the active-geometry capillary section:

- `interface.state_space: active_geometry_capillary`
- q transport: `spatial: geometric_swept_volume`, `time_integrator: tvd_rk3`
- tracking: `gauge_reconstruction: column_height_graph`
- surface tension: `formulation: pressure_jump`, `source: bundle_virtual_work`, `endpoint: column_height_graph`
- projection/PPE: `face_hodge`, FCCD, `phase_separated`, `affine_jump`, `capillary_reaction_projection: pressure_component_hodge`
- capillary reference boundary: no no-slip tangential wall trace; normal wall constraint/free-slip finite-depth interpretation.

This supports the paper's route-level claim, not the older "FCCD interface transport" wording in the common Ch14 stack paragraph.

## Paper Values Versus Fresh Run

Source paper values are in `paper/sections/14_benchmarks.tex:156-195` and `paper/sections/13e2_ao_capillary_split_gate.tex:75`.

| Metric | Paper | Fresh run | Assessment |
|---|---:|---:|---|
| Samples | `2585` | `2585` | exact |
| Final time | `0.046742983863` | `0.046742983863` | exact |
| Initial signed amplitude | `2.002821e-4` | `2.002821033747926e-4` | exact within printed precision |
| Final signed amplitude | `1.589641e-4` | `1.587037990392341e-4` | stale by `0.16%` |
| Final amplitude ratio | `0.794` | `0.792401299791864` | stale by `0.20%` |
| Max kinetic energy | `8.3171e-6` | `8.338458554712006e-6` | stale by `0.26%` |
| Final kinetic energy | `1.1466e-6` | `1.148291590868705e-6` | stale by `0.15%` |
| Final volume drift | `4.0251e-14` | `9.622294280808861e-14` | stale, but still roundoff scale |
| Max volume drift | `4.6621e-14` | `9.961107459710581e-14` | stale, but still roundoff scale |

Phase samples from the fresh run:

| Phase | `t` | `a_2(t)` | `a_2(t)/a_2(0)` | `E_k` |
|---|---:|---:|---:|---:|
| `0` | `1.843598857897e-05` | `2.002821033748e-04` | `1.000000` | `4.698388716604e-11` |
| `1/4 T` | `1.169255835672e-02` | `1.563467269197e-05` | `0.078063` | `8.171200916667e-06` |
| `1/2 T` | `2.336969514009e-02` | `-1.833893356473e-04` | `-0.915655` | `8.191465654441e-07` |
| `3/4 T` | `3.505661460520e-02` | `-4.050561627255e-05` | `-0.202243` | `6.934475810388e-06` |
| `T` | `4.674298386300e-02` | `1.587037990392e-04` | `0.792401` | `1.148291590869e-06` |

## Correctness Assessment

What is supported:

- The wave is restoring, not anti-restoring.
- The run reaches the continuum reference time exactly under the current YAML.
- The signed mode crosses through flat and negative phases and returns positive.
- Kinetic energy remains bounded over the one-cycle window.
- Volume conservation is at machine-roundoff scale.
- The active-geometry graph-HFE / pressure-component Hodge route is the route being exercised.

What should be corrected in the paper:

1. Update the exact numerical table/text values in the Ch14 capillary section from the fresh run, or round them to a precision that does not imply exact reproducibility across reruns.
2. Update the V11 table row that repeats the old `4.66e-14`, `8.32e-6`, and `0.794` values.
3. Keep the qualitative claim: bounded restoring capillary-wave motion, roundoff-level q-volume preservation, and correct pressure-jump sign are supported.
4. Fix or qualify the Ch14 common-stack phrase `FCCD 保存形界面輸送 + TVD--RK3`, because the active-geometry capillary route uses q-owned `geometric_swept_volume` transport; FCCD is the pressure/PPE route here.

## SOLID / Scope

[SOLID-X] Verification run and review artifact only. No `src/twophase/`, experiment YAML, paper text, physical parameter, CFL, damping, smoothing, tolerance, production algorithm, hidden fallback, main merge, branch deletion, or worktree removal was changed.
