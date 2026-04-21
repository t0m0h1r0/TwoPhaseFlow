---
ref_id: WIKI-X-025
title: "Time Integration Design for Two-Phase UCCD6-NS (Capillary Wave Resolution, Semi-Implicit ST, BF Projection)"
domain: cross-domain
status: PROPOSED  # Research design; Level-2 integrated PoC pending
superseded_by: null
sources:
  - description: Internal research memo on time-integration design for two-phase UCCD6-NS (2026-04-22)
  - description: "Denner, F. & van Wachem, B. G. M. (2015). Numerical time-step restrictions as a result of capillary waves. JCP 285, 24–40."
  - description: "Denner, F. & van Wachem, B. G. M. (2022). On the capillary time-step restriction. JCP 449, 110788."
  - description: "Francois, M. M. et al. (2006). A balanced-force algorithm for continuous and sharp interfacial surface tension models within a volume tracking framework. JCP 213, 141–173."
  - description: "Aland, S. & Voigt, A. (2019). Benchmark computations of diffuse-interface models for two-dimensional bubble dynamics. IJNMF 91(3), 111–137."
  - description: "Denner, F. (2024). A fully-coupled pressure-based finite-volume method for two-phase flows including surface tension with implicit interfacial coupling. JCP."
  - description: "Li, Z. (2022). Fully implicit jump-condition enforcement for sharp-interface two-phase flow. JCP 458, 111107."
depends_on:
  - "[[WIKI-X-023]]: UCCD6 Integration Design for Incompressible NS"
  - "[[WIKI-X-024]]: Balanced-Force Design for Two-Phase UCCD6-NS"
  - "[[WIKI-T-003]]: Variable-Density Projection Method: IPC + AB2 + CN"
  - "[[WIKI-T-004]]: Balanced-Force Condition"
  - "[[WIKI-T-014]]: Capillary CFL Constraint & ALE Grid Motion Effects"
  - "[[WIKI-T-023]]: Surface Tension Semi-Implicit Method (Laplace–Beltrami Linearisation)"
  - "[[WIKI-T-033]]: Extended Crank–Nicolson × CCD: 4th-Order Viscous Time Integration"
  - "[[WIKI-T-062]]: UCCD6 Sixth-Order Upwind CCD"
consumers:
  - domain: future-impl
    description: "ns_pipeline Level-2 integrator: AB2 advection + CN viscous + semi-implicit ST + BF PPE"
  - domain: experiment
    description: "ch13 capillary wave (water–air) capillary-Δt wave-resolution calibration (C_wave)"
  - domain: theory
    description: "Composite stability proof: UCCD6 skew-Hermiticity ⊗ CN viscous ⊗ semi-implicit ST ⊗ BF projection"
tags: [time_integration, ab2, crank_nicolson, semi_implicit_surface_tension, balanced_force, uccd6, two_phase, capillary_wave, design_guide]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Time Integration Design for Two-Phase UCCD6-NS

## Thesis

> **The capillary time-step restriction is a wave-resolution constraint, not
> just a stability constraint (Denner & van Wachem 2015/2022). Making surface
> tension implicit removes the spurious stiff eigenvalue, but does not release
> the $\Delta t$ cap whenever the capillary wavelength is dynamically
> relevant.**
>
> **Consequently: UCCD6 (advection stabilisation, [WIKI-X-023](WIKI-X-023.md)) +
> BF pairing (static force balance, [WIKI-X-024](WIKI-X-024.md)) + correctly
> chosen time integrator (this note) are three orthogonal layers, and each
> must be addressed at its own level.**

This entry selects the time-integration layer. The recommended Level-2 scheme
is **AB2 advection + Crank–Nicolson viscous + semi-implicit linearised surface
tension + variable-density balanced-force projection**.

## 1. The three stiffness sources and their time treatments

| Source | Scale | Constraint | L2 recommended treatment |
|---|---|---|---|
| advection | $|\mathbf{u}| h^{-1}$ | CFL${}_{\text{adv}}$ | **explicit AB2** |
| viscosity | $\nu h^{-2}$ | CFL${}_{\text{visc}}$ (stiff at high-Re 2D) | **Crank–Nicolson** |
| surface tension — stability | $\sqrt{\sigma / (\bar\rho h^3)}$ | Brackwill BKZ (1992) | **semi-implicit linearised** |
| surface tension — *resolution* | $\omega_c = \sqrt{\sigma k^3 / (\rho_1 + \rho_2)}$ | Denner–van Wachem (2015) | $\Delta t$ cap remains |
| incompressibility | — | constraint | **variable-ρ BF projection** |

The critical distinction is between the **BKZ stability bound** (explicit-ST only) and the **Denner–van Wachem resolution bound** (semi-implicit ST still subject to it when the capillary mode matters). See §1 of [SP-I](../../memo/short_paper/SP-I_time_integration_uccd6_ns.md) for the derivation.

## 2. Three design levels

### 2.1 Level 1 — bring-up / validation

- Integrator: SSPRK3 (or RK4) + explicit viscous + explicit CSF.
- Use: unit tests, grid-convergence studies on smooth problems.
- Drawback: $\Delta t \le \min(\Delta t_{\text{adv}}, \Delta t_{\text{visc}}, \Delta t_{\sigma}^{\text{BKZ}})$ — prohibitively small on ch13 water–air configs.

### 2.2 Level 2 — production (recommended)

- Advection: UCCD6 + **AB2** (SSPRK3 warm-up for step 0→1).
- Viscous: **Crank–Nicolson**, flux form for $\mu$ jumps.
- Surface tension: **semi-implicit linearised** (Aland–Voigt 2019 unconditional stability), evaluated at $t^{n+1/2}$ for BF consistency.
- Projection: **variable-density BF PPE** with harmonic-averaged $1/\rho$ face coefficient.
- Status: recommended default for ch13 production workflows.

### 2.3 Level 3 — stiff regimes (future)

- Integrator: **Radau IIA** (5-th order A/L-stable implicit RK) inside a fully-coupled pressure/velocity/interface solver (Denner 2024) or fully-implicit jump-condition enforcement (Li 2022).
- Use: extreme $\rho_1/\rho_2$ ($\gtrsim 10^4$), very low $We$, thin films, stiff campaigns.
- Cost: nonlinear JFNK per step; reserved for campaigns that cannot tolerate Level-2 wave resolution.

## 3. Level-2 recommended discretisation

Let $\rho^{n+1/2} = \tfrac{1}{2}(\rho^n + \rho^{n+1})$ and let $\mathcal{A}_{\text{UCCD6}}$ be the [WIKI-X-023](WIKI-X-023.md) skew-sym + hyperviscosity operator.

### 3.1 Predictor

$$
\boxed{\;
\rho^n \frac{\mathbf{u}^* - \mathbf{u}^n}{\Delta t}
= -\rho^n \Bigl[\tfrac{3}{2}\mathcal{A}_{\text{UCCD6}}(\mathbf{u}^n) - \tfrac{1}{2}\mathcal{A}_{\text{UCCD6}}(\mathbf{u}^{n-1})\Bigr]
+ \tfrac{1}{2}\bigl[\mathcal{V}(\mathbf{u}^*) + \mathcal{V}(\mathbf{u}^n)\bigr]
+ \mathbf{f}_\sigma^{n+1/2} + \rho^n \mathbf{g}.
\;}
$$

- $\mathcal{V}(\mathbf{u}) = \nabla \cdot (\mu (\nabla \mathbf{u} + \nabla \mathbf{u}^\top))$ in flux form (mandatory across $\mu$ jumps; cf. [WIKI-X-023 §2.3](WIKI-X-023.md#23-viscous-term--flux-form-for-mu-jumps)).
- $\mathbf{f}_\sigma^{n+1/2}$ = semi-implicit linearised Laplace–Beltrami surface tension on the predicted mid-step interface; paired with $\nabla p$ via BF consistency ([WIKI-X-024](WIKI-X-024.md)).

### 3.2 Pressure Poisson equation (BF, variable-ρ)

$$
\boxed{\;
\nabla \cdot \left( \frac{1}{\rho^{n+1/2}} \nabla p^{n+1} \right) = \frac{1}{\Delta t} \nabla \cdot \mathbf{u}^*.
\;}
$$

Both sides share the *same* gradient/divergence stencils as the momentum step — the operator-consistency constraint of [WIKI-T-004](../theory/WIKI-T-004.md) and [WIKI-X-024 §3](WIKI-X-024.md).

### 3.3 Corrector

$$
\boxed{\;
\mathbf{u}^{n+1} = \mathbf{u}^* - \Delta t \cdot \frac{1}{\rho^{n+1/2}} \nabla p^{n+1}.
\;}
$$

Interface advection follows on $\mathbf{u}^{n+1}$ by the project's FCCD-flux transport ([WIKI-T-046](../theory/WIKI-T-046.md)); reinitialisation on the existing ridge-Eikonal schedule.

## 4. Composite stability and effective Δt

With UCCD6 skew-sym anti-Hermiticity (conjecture, [WIKI-X-023 §7](WIKI-X-023.md) Q-1), A-stable CN on $\mathcal{V}$, unconditional Aland–Voigt semi-implicit ST, and BF projection preserving $\mathrm{ker}(\nabla\cdot)$:

$$
\Delta t_{\text{L2}} \approx \min\bigl(\Delta t_{\text{CFL,adv}},\; \Delta t_{\text{cap}}\bigr) \ll \Delta t_{\text{visc}},
$$

i.e. the viscous CFL is removed, advection CFL remains, and the capillary **resolution** bound (Denner–van Wachem) remains. Typical ch13 regime is capillary-dominated, so the practical cap is $\Delta t_{\text{cap}} = C_{\text{wave}} \sqrt{(\rho_1+\rho_2) h^3 / (2\pi \sigma)}$ with $C_{\text{wave}} \simeq 0.2$.

## 5. How this composes with the rest of the stack

- **Advection layer**: UCCD6 ([WIKI-X-023](WIKI-X-023.md)) is unchanged; AB2 wraps it without touching the operator definition.
- **Static force balance**: BF pairing ([WIKI-X-024](WIKI-X-024.md)) is unchanged; §3.2 above *is* the BF PPE applied to a time-discrete RHS.
- **Level-set transport**: FCCD-flux ([WIKI-T-046](../theory/WIKI-T-046.md)) runs on $\mathbf{u}^{n+1}$ after the corrector; no new coupling.
- **Curvature**: HFE smoothing ([WIKI-T-038](../theory/WIKI-T-038.md)) is used for $\kappa$ in $\mathbf{f}_\sigma^{n+1/2}$.
- **Interface stability**: [WIKI-E-030](../experiment/WIKI-E-030.md) H-01 BF residual diagnostic is the primary probe; Level-2 should improve the late-time H-01 behaviour relative to the Level-1 baseline.

## 6. Implementation checklist

1. **AB2 integrator**: reuse existing `AB2` class; confirm SSPRK3 warm-up path at step 0.
2. **CN viscous solve**: Helmholtz-type $(I - \tfrac{\Delta t}{2\rho^n}\mathcal{V})\mathbf{u}^* = \text{RHS}$; CCD-Helmholtz inverse or matrix-free GMRES.
3. **Semi-implicit ST**: upgrade [WIKI-T-023](../theory/WIKI-T-023.md) status from "Future" to "Level-2 recommended"; implement Laplace–Beltrami linearisation against the predicted mid-step interface.
4. **BF PPE**: face coefficient $1/\rho^{n+1/2}_f$ with harmonic averaging across interface faces; gradient/divergence operators tied to the momentum step stencils (Francois 2006).
5. **Δt control**: `run.time.dt_cap_safety = 0.2` as default; add on-the-fly capillary-period $T_c$ monitor.
6. **Level-3 hook**: keep predictor/PPE/corrector abstraction in `ns_pipeline.py` factored so a Radau IIA integrator can swap in without touching the projection path.

## 7. Open questions for follow-up research

- **Q-I1** — Empirical calibration of $C_{\text{wave}}$ for ch13 water–air capillary wave (M=2 perturbation).
- **Q-I2** — Does CN on $(-\Delta_{\text{CCD}})^4$ introduce phase error at resolved wavenumbers? If yes, AB2-treatment of the hyperviscosity stays preferred.
- **Q-I3** — Composite stability proof of semi-implicit ST together with the BF-matched pressure operator (Aland–Voigt × discrete Helmholtz decomposition).
- **Q-I4** — Level-3 Radau IIA cost breakpoint: $\rho_1/\rho_2 \gtrsim 10^4$ or $We \ll 1$? Literature hints these regions; project-specific measurement pending.

## References

- [SP-I](../../memo/short_paper/SP-I_time_integration_uccd6_ns.md) — this design as a short paper.
- [WIKI-X-023](WIKI-X-023.md) — UCCD6 integration design for incompressible NS.
- [WIKI-X-024](WIKI-X-024.md) — Balanced-force design for two-phase UCCD6-NS.
- [WIKI-T-003](../theory/WIKI-T-003.md) — Variable-density IPC + AB2 + CN projection method (historical baseline).
- [WIKI-T-004](../theory/WIKI-T-004.md) — Balanced-force operator consistency.
- [WIKI-T-014](../theory/WIKI-T-014.md) — Capillary CFL constraint.
- [WIKI-T-023](../theory/WIKI-T-023.md) — Semi-implicit surface tension (Laplace–Beltrami linearisation).
- [WIKI-T-033](../theory/WIKI-T-033.md) — Extended CN × CCD 4th-order viscous time integration.
- [WIKI-T-062](../theory/WIKI-T-062.md) — UCCD6 core scheme.
- Denner & van Wachem (2015) *JCP* **285**, (2022) *JCP* **449** — capillary time-step as wave resolution.
- Francois et al. (2006) *JCP* **213** — balanced-force algorithm.
- Brackbill, Kothe, Zemach (1992) *JCP* **100** — CSF + BKZ stability bound.
- Aland & Voigt (2019) *IJNMF* **91** — semi-implicit ST unconditional stability.
- Bänsch (2001) *Numer. Math.* **88** — Laplace–Beltrami semi-implicit root.
- Denner (2024) *JCP* — fully-coupled implicit interfacial coupling (Level-3 path).
- Li (2022) *JCP* **458** — fully-implicit jump-condition enforcement (Level-3 path).
