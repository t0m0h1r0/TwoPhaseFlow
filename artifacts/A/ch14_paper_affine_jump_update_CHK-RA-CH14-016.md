# CHK-RA-CH14-016 — Paper update for oriented affine jump

## Trigger

User requested that the short paper / Wiki theory and implementation design for `affine_jump` be reflected in the main paper.

## Reflected theory

- Fixed the paper-wide phase contract to `ψ=1` liquid and `ψ=0` gas, with `φ<0` in liquid and `n_lg=∇φ/|∇φ|` pointing liquid to gas.
- Defined curvature as `κ_lg=∇Γ·n_lg`; a circular liquid droplet has `κ_lg>0`.
- Recast Young--Laplace as `p_l-p_g=σκ_lg`, equivalently the gas-minus-liquid pressure jump `j_gl=p_g-p_l=-σκ_lg`.
- Documented the affine jump operator as `G_Γ(p;j_gl)=G(p)-B(j_gl)` with face coefficient `s_f=I_g(high)-I_g(low)` and `B_f=s_f j_gl/d_f`.
- Promoted `InterfaceStressContext.pressure_jump_gas_minus_liquid` as the implementation contract; raw `σκ` is not a portable data contract.

## Paper changes

- Updated the governing-equation, surface-tension, level-set, reinitialization, advection, time-integration, PPE, algorithm, appendix, and conclusion sections to use the oriented pressure-jump convention consistently.
- Reframed legacy `jump_decomposition` as an algebraically absorbable comparison path rather than the production pressure-coupling model.
- Replaced the provisional capillary-wave benchmark text with the root-cause chain and the N=32, T=10 oriented-affine result.
- Preserved the generality requirement: droplet, gas bubble, capillary wave, and Rayleigh--Taylor use the same oriented interface-stress logic; no benchmark-specific branch is introduced.

## Validation

- `cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` passed.
- `git diff --check` passed.
- `[SOLID-X]` No violation: this CHK changes paper/docs only and does not alter production class/module boundaries.
