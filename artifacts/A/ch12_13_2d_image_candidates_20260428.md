# CHK-RA-CH12-13-001 — CH12/CH13 2D Image Candidate Memo

## ResearchArchitect Dispatch

- Classification: FAST-TRACK research/design task.
- Session: `CHK-RA-CH12-13-001`.
- Worktree: `worktree-ra-ch12-13-2d-candidates-20260428`.
- `id_prefix`: `RA-CH12-13` (`RA-CH12` collided with the active review lock, so the prefix was extended by rule).
- Expected verdict: ranked candidate experiment(s) that can add a paper-facing 2D PDF image to chapters 12/13 without violating PR-4/PR-5.

## Verdict

Yes.  The best next 2D image is a chapter 12 figure, not a new chapter 13 simulation:

1. **Primary recommendation: U6-c HFE 2D circular-band field map.**
   This has the best mix of visual impact, scientific relevance, and low implementation risk.
2. **Secondary recommendation: U4 reinitialization/DGR before-after field panel.**
   This is easier, but slightly less central than HFE for the chapter 12 -> 13 bridge.
3. **Chapter 13 optional: V9 local-epsilon failure field.**
   Use only if a negative-result 2D diagnostic is desired.  V3, V4, and V10 already provide strong 2D snapshots in chapter 13.

## Current Visual Inventory

| Scope | Current state | Gap |
| --- | --- | --- |
| Chapter 12 U1--U9 | Every U experiment has a figure, but most are convergence curves, bar charts, or summaries. | Almost no visually immediate 2D field image. |
| Chapter 13 V3 | Static droplet pressure/speed snapshot exists. | Already covered. |
| Chapter 13 V4 | Rayleigh--Taylor 2D snapshot exists. | Already covered; still linear-window, but suitable. |
| Chapter 13 V10 | Zalesak and single-vortex snapshots exist. | Already covered and visually strong. |
| Chapter 13 V9 | Local epsilon instability is only a history/bar figure. | A field image could make the failure mechanism obvious. |

## Candidate Ranking

| Rank | Candidate | Visual | Paper value | Implementation risk | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1 | U6-c HFE circular-band field | 1x3 or 2x2 panel: exact interface extension, HFE extension, log error band, interface contour. | Strong A3 chain: `sec:hfe` -> `sec:U6_split_ppe_dc_hfe` -> `HermiteFieldExtension.extend` -> U6-c 2D band. | Low/medium: U6 already computes the exact projection, HFE extension, band mask, and errors; keep arrays for one representative N. | Implement first. |
| 2 | U4 Eikonal reinit + DGR field | Before/after `|grad phi|-1` heatmaps plus `psi=0.5` contours and thickness band. | Clear interface-primitive story; makes reinit/DGR tangible. | Low: U4 already has `phi0`, `phi_iter`, `psi0`, `psi_dgr` internally, but currently returns only scalars. | Good follow-up. |
| 3 | V9 local-epsilon field | Fixed vs local epsilon panels showing `psi` contour over speed or pressure; local case visually "fails". | Good negative diagnostic explaining why local epsilon is rejected. | Medium: V9 currently stores only histories/final scalars; must retain final fields for representative N/configs. | Optional for chapter 13. |
| 4 | V6/V8 extra static-droplet pressure fields | Pressure contours across density/nonuniform settings. | Mostly repeats V3; less narrative payoff. | Low/medium. | Deprioritize. |
| 5 | New nonlinear RT/KH roll-up for chapter 13 | Very showy. | Better suited to chapter 14 benchmarks than chapter 13 validation; risks changing V4's linear-growth role. | High. | Do not start under this CHK. |

## Primary Implementation Sketch: U6-c HFE Field Figure

Target script: `experiment/ch12/exp_U6_split_ppe_dc_hfe.py`.

Minimal design:

- In `_u6c_hfe_2d_one`, for `N=128` retain `X`, `Y`, `phi`, `field_truth_extension`, `extended`, `band_mask`, and `abs_error`.
- Add `make_hfe_field_figure(results)` with three panels:
  - analytic closest-point extension `f(x_Gamma)`;
  - HFE output `q_ext`;
  - `log10(|q_ext - f(x_Gamma)|)` masked to `|phi| <= 6h`.
- Draw the `phi=0` interface contour in every panel.
- Save to `OUT / "U6_hfe_2d_field"` and `paper/figures/ch12_u6_hfe_2d_field`.
- Insert the paper figure after `fig:ch12_u6` with label `fig:ch12_u6_hfe_field`.

Validation:

- Run `make cycle EXP=experiment/ch12/exp_U6_split_ppe_dc_hfe.py`.
- Rebuild the paper with `cd paper && latexmk -xelatex -interaction=nonstopmode main.tex`.
- Check that `fig:ch12_u6_hfe_field` resolves and no undefined reference/citation is introduced.

Why this is the best fit:

- It is not just decorative; it visualizes the exact object U6-c already measures.
- It strengthens the chapter 12 -> 13 bridge because HFE is the pressure-interface technology later needed by high-density-ratio validation.
- It avoids adding a new physical benchmark into chapter 13, where V3/V4/V10 already carry the 2D visual burden.

## Secondary Implementation Sketch: V9 Local-Epsilon Failure Field

Target script: `experiment/ch13/exp_V9_local_eps_nonuniform.py`.

Minimal design:

- Retain final `psi`, `pressure`, `speed`, and grid coordinates for `N=64` configs A/B/C.
- Add a 1x3 panel comparing A fixed, B fixed, and C local epsilon.
- Use a common speed color scale and overlay `psi=0.5`.
- Save to `paper/figures/ch13_v9_local_eps_field`.

Use this only if chapter 13 needs another 2D image after the current V3/V4/V10 set.  It is visually strong because the local-epsilon case is a failure, but it should be captioned as a negative diagnostic, not as an attractive benchmark.

## SOLID / PR Assessment

- `[SOLID-X]` No production class/module change is required for the recommended first step; the change can remain experiment-script + paper-figure only.
- PR-4 applies: use `twophase.experiment.save_figure`; do not hand-roll output paths beyond the existing script pattern.
- PR-5 applies: the U6 figure must show the same HFE extension already used for U6-c, not a separate visualization-only surrogate.
