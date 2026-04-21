---
ref_id: WIKI-X-028
title: "Conservative Momentum Form for Two-Phase UCCD6 (∂ₜ(ρu) + ∇·(ρu⊗u) Under Density Jumps)"
domain: cross-domain
status: PROPOSED  # Design refinement; conservative-form UCCD6 PoC pending
superseded_by: null
sources:
  - description: Internal research memo on conservative momentum form under density jumps (2026-04-22)
depends_on:
  - "[[WIKI-X-023]]: UCCD6 Integration Design for Incompressible NS"
  - "[[WIKI-X-024]]: Balanced-Force Design for Two-Phase UCCD6-NS"
  - "[[WIKI-T-062]]: UCCD6 Sixth-Order Upwind CCD"
  - "[[WIKI-T-006]]: One-Fluid Formulation"
consumers:
  - domain: future-impl
    description: "TwoPhaseNSSolver refactor: replace ρ(u·∇)u with ∂ₜ(ρu) + ∇·(ρu⊗u)"
  - domain: experiment
    description: "Re-measure KE blow-up on ch13 with conservative-form momentum"
  - domain: theory
    description: "Proof that conservative form + UCCD6 preserves the skew-adjoint dissipation budget across ρ jumps"
tags: [conservative_form, skew_symmetric, uccd6, density_jump, two_phase, momentum, design_refinement]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Conservative Momentum Form for Two-Phase UCCD6

## Thesis

> **In two-phase flow with density jumps, the skew-symmetric advection form
> of [WIKI-X-023 §2.1](WIKI-X-023.md#21-advection--skew-symmetric-ccd-form) is
> no longer discretely energy-conserving. The fix is to advance the
> *conservative momentum* $\partial_t(\rho\mathbf{u}) + \nabla\cdot(\rho\mathbf{u}\otimes\mathbf{u})$,
> not the primitive-velocity form $\rho(\mathbf{u}\cdot\nabla)\mathbf{u}$.
> UCCD6 hyperviscosity attaches to the conservative form unchanged.**

This note refines [WIKI-X-023 §2.1](WIKI-X-023.md#21-advection--skew-symmetric-ccd-form) for the two-phase case. [WIKI-X-023](WIKI-X-023.md) was written primarily for single-phase flow; this entry upgrades it for the project's CLS + ρ-jump setting.

## 1. Why skew-symmetry breaks under ρ jumps

In single-phase flow with constant $\rho$, the skew-symmetric split

$$
(\mathbf{u}\cdot\nabla)\mathbf{u}
 = \tfrac{1}{2}\bigl[(\mathbf{u}\cdot\nabla)\mathbf{u} + \nabla\cdot(\mathbf{u}\otimes\mathbf{u})\bigr]
$$

is discretely anti-Hermitian under the CCD $\ell^2$ inner product, giving energy conservation at the semi-discrete level ([WIKI-X-023 §2.1](WIKI-X-023.md#21-advection--skew-symmetric-ccd-form), [WIKI-T-062](../theory/WIKI-T-062.md)).

In two-phase flow the momentum density $\rho(\psi)\mathbf{u}$ has a jump at the interface. The identity

$$
\rho(\mathbf{u}\cdot\nabla)\mathbf{u} \;\ne\; \tfrac{1}{2}\bigl[\rho(\mathbf{u}\cdot\nabla)\mathbf{u} + \nabla\cdot(\rho\mathbf{u}\otimes\mathbf{u})\bigr]
$$

fails because $\nabla\rho \ne 0$ couples to the skew split. Plain primitive-velocity skew-symmetry therefore does not deliver discrete energy conservation across the interface. The spurious production/dissipation that results is proportional to $\|\nabla\rho\|\cdot\|\mathbf u\|^2$, which in water–air (contrast $10^3$) is catastrophic.

## 2. The conservative form

Rewrite the momentum equation as

$$
\boxed{\;
\partial_t (\rho\mathbf{u}) + \nabla\cdot(\rho\mathbf{u}\otimes\mathbf{u})
\;=\; -\nabla p + \nabla\cdot\bigl[\mu(\nabla\mathbf{u} + \nabla\mathbf{u}^\top)\bigr] + \mathbf{f}_\sigma + \rho\mathbf{g}.
\;}
$$

Discrete form with UCCD6:

$$
\frac{(\rho\mathbf{u})^{n+1} - (\rho\mathbf{u})^n}{\Delta t}
\;=\; -\mathcal{A}^{\text{cons}}_{\text{UCCD6}}(\rho, \mathbf{u}) + \text{(viscous + ST + pressure)}
$$

where

$$
\mathcal{A}^{\text{cons}}_{\text{UCCD6}}(\rho, \mathbf{u})
 \;=\; D_1^{\text{CCD}}\!\cdot(\rho\mathbf{u}\otimes\mathbf{u}) \;+\; \sigma h^7 (-\Delta_{\text{CCD}})^4 \mathbf{u}.
$$

The hyperviscosity is applied to $\mathbf{u}$ (not $\rho\mathbf{u}$) — this keeps it a velocity-space smoothing whose amplitude does not scale with the density contrast.

## 3. Equivalent semi-discrete energy statement

For the conservative form, the discrete momentum flux $D_1^{\text{CCD}}\!\cdot(\rho\mathbf{u}\otimes\mathbf{u})$ is the divergence of a symmetric tensor; its contribution to $\tfrac{1}{2}\mathrm{d}\|\rho^{1/2}\mathbf{u}\|^2/\mathrm{d}t$ is bounded by boundary fluxes only (conjecture, full proof pending — open question Q-M1 below). Semi-discrete energy inequality expected:

$$
\tfrac{1}{2}\mathrm{d}\|\rho^{1/2}\mathbf{u}\|^2/\mathrm{d}t
 \;\le\; -\sigma h^7 \|(-\Delta_{\text{CCD}})^2 \mathbf{u}\|^2
 \;-\; \|\mu^{1/2}\nabla_{\text{CCD}}\mathbf{u}\|^2 + \text{BC terms}.
$$

This is the correct two-phase analog of the single-phase identity in [WIKI-X-023 §7](WIKI-X-023.md#7-open-questions-for-follow-up-research).

## 4. Relation to the "acceleration term" language

The user-facing memo phrases the advection + inertia as an "acceleration term". Formally

$$
\mathbf{a} = \partial_t \mathbf{u} + (\mathbf{u}\cdot\nabla)\mathbf{u} = \frac{D\mathbf{u}}{Dt},
$$

and the verdict is:

| Form | When to use | Energy status |
|---|---|---|
| primitive: $\rho \,D\mathbf{u}/Dt$ | single-phase, $\nabla\rho = 0$ | discretely conservative with skew-sym |
| primitive + density: $\rho(\mathbf{u}\cdot\nabla)\mathbf{u}$ | **never in CLS 2-phase** | breaks discrete energy |
| conservative: $\partial_t(\rho\mathbf{u}) + \nabla\cdot(\rho\mathbf{u}\otimes\mathbf{u})$ | two-phase, $\nabla\rho \ne 0$ | discretely conservative (conjecture; see §3) |

## 5. Time treatment (from [WIKI-X-025](WIKI-X-025.md))

Conservative form is fully compatible with AB2:

$$
\frac{(\rho\mathbf{u})^* - (\rho\mathbf{u})^n}{\Delta t}
 = -\bigl[\tfrac{3}{2}\mathcal{A}^{\text{cons}}_{\text{UCCD6}}(\rho, \mathbf{u})^n - \tfrac{1}{2}\mathcal{A}^{\text{cons}}_{\text{UCCD6}}(\rho, \mathbf{u})^{n-1}\bigr] + \text{(implicit viscous, semi-implicit ST)}.
$$

The corrector step of [WIKI-X-025 §3.3](WIKI-X-025.md#33-corrector) then reads

$$
\mathbf{u}^{n+1} = \frac{(\rho\mathbf{u})^* - \Delta t\,\nabla p^{n+1}}{\rho^{n+1}}.
$$

## 6. Diagnostic — when KE blows up

From the ch13 empirical record, kinetic-energy blow-up at high resolution is compatible with (at least) three causes:

1. **BF pair inconsistency** — primary, per [WIKI-X-024](WIKI-X-024.md).
2. **Primitive-form skew-symmetry breach under ρ jump** — this entry.
3. **UCCD6 hyperviscosity too weak** — raise $\sigma$ (noting [WIKI-X-023 §6](WIKI-X-023.md#6-shortest-implementation-path) CFL constraint for explicit time).

Ordering: fix (1) first, then switch to conservative form (2), then re-tune $\sigma$ (3). The current ch13 pipeline is in stage (1)–(2).

## 7. Implementation checklist

1. **Switch variable**: advance $(\rho\mathbf u)^n$ rather than $\mathbf u^n$ in the momentum predictor. Store $\rho^n$ alongside and recover $\mathbf u^n = (\rho\mathbf u)^n / \rho^n$ for UCCD6 hyperviscosity argument.
2. **Flux operator**: reuse the project's `_fvm_conv_flux` / FCCD-flux machinery to evaluate $D_1^{\text{CCD}}\!\cdot(\rho\mathbf u \otimes \mathbf u)$.
3. **Hyperviscosity target**: apply $\sigma h^7 (-\Delta_{\text{CCD}})^4$ to $\mathbf u$, not to $\rho\mathbf u$ — avoids $\rho$-weighted spectral damping.
4. **ST + BF PPE**: unchanged from [WIKI-X-024](WIKI-X-024.md) / [WIKI-X-025 §3.2](WIKI-X-025.md#32-pressure-poisson-equation-bf-variable-ρ).
5. **Validation**: static drop (`wilke_drop`) and ch13 capillary wave — expect reduction of H-01 late-time BF residual relative to primitive form.

## 8. Open questions

- **Q-M1** — Rigorous discrete energy inequality for the conservative UCCD6 form under ρ jumps (sketch in §3).
- **Q-M2** — Does conservative form *alone* fix H-01 late-time blow-up at $N=128$ water-air, or is BF operator consistency ([WIKI-X-024](WIKI-X-024.md)) still the dominant effect? Expected: BF is primary; conservative form is second-order but still necessary for cleanliness at large $t$.
- **Q-M3** — Interplay with semi-implicit surface tension: does the $(\rho\mathbf u)$ corrector step of §5 change the semi-implicit ST linearisation?

## References

- [WIKI-X-023](WIKI-X-023.md) — UCCD6-NS baseline (single-phase skew form).
- [WIKI-X-024](WIKI-X-024.md) — BF pair (primary two-phase driver).
- [WIKI-X-025](WIKI-X-025.md) — time-integration design (conservative form composes with AB2/CN/semi-implicit ST).
- [WIKI-X-026](WIKI-X-026.md) — stiffness policy (why advection stays explicit).
- [WIKI-T-006](../theory/WIKI-T-006.md) — one-fluid formulation (conservative-form provenance).
- [WIKI-T-062](../theory/WIKI-T-062.md) — UCCD6 core.
- Sussman, Smereka, Osher (1994) *JCP* **114** — two-phase LS baseline.
- Kataoka (1986); Kim & Moin (1985); Morinishi et al. (1998) — conservative-form skew vs primitive for variable-density flow.
- Desjardins, Moureau, Pitsch (2008) *JCP* **227** — accurate conservative LS + conservative momentum for large density ratio.
