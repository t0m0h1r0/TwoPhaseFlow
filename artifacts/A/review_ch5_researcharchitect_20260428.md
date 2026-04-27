# §5 ResearchArchitect Review — 2026-04-28

Verdict after fixes: PASS (0 FATAL, 0 MAJOR).

## Scope
- Reviewed `paper/sections/05_reinitialization.tex`.
- Reviewed `paper/sections/05b_cls_stages.tex`.
- Checked downstream consistency in `paper/sections/06d_viscous_3layer.tex`.

## Findings
- R5-1 FATAL, fixed: §5 conflated Ridge--Eikonal, Gaussian ridge projection, and the uniform-grid xi-SDF baseline. The text now defines Ridge--Eikonal as the redistancing family, makes xi-SDF the uniform-grid baseline, and points the full Gaussian/non-uniform FMM path to §3.4 and §10.
- R5-2 MAJOR, fixed: Eikonal zero-set preservation was stated as exact while the same section later described Godunov drift. The guarantee is now limited to the continuous PDE and the non-iterative path is motivated explicitly.
- R5-3 FATAL, fixed: The xi-SDF proposition claimed exact grid-node zero preservation with `sgn(0)=0`, but the implementation assigns exact zero to one side. The proposition now covers the linearly interpolated zero-crossing set actually constructed by the algorithm.
- R5-4 FATAL, fixed: §5.2 mandated psi-space mass correction after reinitialization even though §5.1 identifies phi-space correction as the safe post-reinit closure. Stage B and Stage F are now separated: psi-space closure after advection/remap, phi-space closure after reinitialization.
- R5-5 MAJOR, fixed: The implementation guide applied pseudo-time loop controls to the one-shot Ridge--Eikonal/xi-SDF/FMM path. The loop controls are now scoped to iterative Godunov/WENO-HJ fallback only.
- R5-6 MINOR, fixed: An equation label was referenced with `\S\ref`, stale source comments exposed old file names/CHK history, and a §13 verification reference remained in §5. These were cleaned or redirected.

## Residual Risk
- No code was changed; SOLID audit is not applicable.
- Broader paper sections still contain `sec:verification` forward references, but §5 no longer does.
