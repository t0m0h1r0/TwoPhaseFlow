# SP-I: Time Integration Design for Two-Phase UCCD6-NS — Capillary Wave Resolution, Semi-Implicit Surface Tension, and Balanced-Force Projection

- **Status**: Research design (theory organised; integrated PoC pending)
- **Compiled by**: ResearchArchitect
- **Compiled at**: 2026-04-22
- **Related**: [SP-N](SP-N_uccd6_hyperviscosity.md) (UCCD6 core; formerly SP-H, renumbered 2026-04-23), [SP-G](SP-G_upwind_ccd_pedagogical.md) (upwind foundation), [SP-A](SP-A_face_centered_upwind_ccd.md) (FCCD remedy), [SP-F](SP-F_gpu_native_fvm_projection.md) (projection path), [SP-H](SP-H_fccd_face_jet_fvm_hfe.md) (face jet primitive)
- **Wiki entries**: [WIKI-X-025](../../wiki/cross-domain/WIKI-X-025.md) (this design), [WIKI-X-023](../../wiki/cross-domain/WIKI-X-023.md) (UCCD6-NS), [WIKI-X-024](../../wiki/cross-domain/WIKI-X-024.md) (balanced-force)

## Abstract

Once UCCD6 ([SP-N](SP-N_uccd6_hyperviscosity.md)) has stabilised the momentum advection operator and the balanced-force (BF) pairing ([WIKI-X-024](../../wiki/cross-domain/WIKI-X-024.md)) has removed the dominant surface-tension-driven residual, the next-order design question is time integration. We argue that

- **the capillary time-step restriction is fundamentally a *wave-resolution* constraint — not a stability constraint** — in the sense of Denner & van Wachem (2015 JCP 285; 2022 JCP 449), so choosing "implicit surface tension" does not automatically let the time step grow;
- **Adams–Bashforth 2 (AB2) advection + Crank–Nicolson (CN) viscous + semi-implicit linearised surface tension + variable-density BF projection** is the sweet spot for Level-2 production workflows;
- **fully-implicit Radau IIA + fully-coupled pressure/velocity/interface** (Denner 2024 JCP) is the Level-3 path reserved for stiff regimes (high density/viscosity ratio, very low We, very low Re).

This short paper organises a three-level design map (L1/L2/L3) and fixes the specific predictor/corrector/PPE equations for the recommended Level-2 scheme.

## 1. Why capillary Δt is a wave-resolution constraint

For surface tension $\sigma$ acting on a sharp interface of smallest resolved wavelength $\lambda = 2h$, the dispersion relation of a capillary wave is $\omega_c^2 = \sigma k^3 / (\rho_1 + \rho_2)$ with $k = 2\pi / \lambda$. The *stability* CFL of Brackbill, Kothe & Zemach (1992)

$$
\Delta t_{\sigma}^{\text{BKZ}} \le \sqrt{\frac{(\rho_1 + \rho_2) h^3}{4\pi \sigma}}
$$

bounds the explicit integration of the surface-tension force. Denner & van Wachem (2015, *JCP* 285) — refined in (2022, *JCP* 449) — showed that this bound is not purely a stability matter: a capillary wave must be *resolved in time* to be transported correctly, and the resolution constraint is

$$
\boxed{\;\Delta t_{\text{cap}} \le C_{\text{wave}} \cdot \sqrt{\frac{(\rho_1 + \rho_2) h^3}{2\pi \sigma}},\qquad C_{\text{wave}} \simeq 0.1\text{–}0.3.\;}
$$

Two consequences follow:

1. **Making surface tension implicit does not lift the capillary time-step.** Semi-implicit surface tension ([Aland & Voigt 2019](#references); [Bänsch 2001](#references)) is *unconditionally stable*, but once the physical wavelength is relevant to the solution, $\Delta t$ must still resolve $\omega_c$. Implicit treatment removes the spurious stiff eigenvalue; it does not change the physics.
2. **UCCD6 and BF design operate at a different layer.** UCCD6 stabilises advection; BF pairing fixes the static-force residual; wave-resolution fixes the capillary time-step. All three constraints compose.

Practical corollary: most ch13 two-phase runs (water–air, $\rho_1/\rho_2 = 10^3$, $N=128$) sit in a regime where $\Delta t_{\text{cap}}$ is tighter than $\Delta t_{\text{CFL,adv}}$ and $\Delta t_{\text{visc}}$. Tight-coupling implicit schemes help only when the physical wavelength can safely be underresolved — i.e. when the capillary mode is not dynamically relevant.

## 2. Semi-discrete operator split

Let $\mathcal{A}(\mathbf{u})$ be the UCCD6 skew-symmetric advection + hyperviscosity operator ([WIKI-X-023](../../wiki/cross-domain/WIKI-X-023.md)), $\mathcal{V}(\mathbf{u}) = \nabla \cdot (\mu (\nabla \mathbf{u} + \nabla \mathbf{u}^\top))$ the flux-form viscous operator, $\mathbf{f}_\sigma = \sigma \kappa \nabla \psi$ the CSF surface-tension force (or equivalent GFM jump), and $\mathbf{g}$ gravity. The incompressible NS system in one-fluid form is

$$
\rho(\psi) \, \partial_t \mathbf{u} = -\rho(\psi) \mathcal{A}(\mathbf{u}) + \mathcal{V}(\mathbf{u}) - \nabla p + \mathbf{f}_\sigma + \rho(\psi) \mathbf{g}, \qquad \nabla \cdot \mathbf{u} = 0.
$$

Each operator has a distinct stiffness profile:

| Operator | Stiffness source | Rational time treatment |
|---|---|---|
| $\mathcal{A}(\mathbf{u})$ | advective CFL ($|\mathbf{u}| \Delta t / h$) | **explicit** (AB2 or SSPRK3) |
| $\mathcal{V}(\mathbf{u})$ | viscous CFL ($\nu \Delta t / h^2$); stiff in high-Re 2-D | **CN (semi-implicit)** |
| $\mathbf{f}_\sigma$ | capillary wave ($\Delta t_{\text{cap}}$); stiff at high $\sigma$/low $\rho$ | **semi-implicit (linearised)** at L2; **fully implicit** at L3 |
| $\nabla p$ / $\nabla \cdot \mathbf{u} = 0$ | incompressibility constraint | **projection** (variable-$\rho$ BF) |

This operator-wise choice is the organising principle for the rest of the paper.

## 3. Three design levels

### 3.1 Level 1 — initial / validation

- **Advection**: UCCD6 + SSPRK3 (or RK4 for smooth tests).
- **Viscous**: explicit (viscous CFL).
- **Surface tension**: explicit CSF.
- **Pressure**: variable-density projection with BF gradient.
- **Use**: initial bring-up, unit tests, grid-convergence studies on smooth problems.
- **Drawback**: $\Delta t \le \min(\Delta t_{\text{adv}}, \Delta t_{\text{visc}}, \Delta t_{\sigma}^{\text{BKZ}})$; prohibitively small for ch13 water–air capillary runs.

### 3.2 Level 2 — production (recommended)

- **Advection**: UCCD6 + **AB2** ($= \tfrac{3}{2} \mathcal{A}^n - \tfrac{1}{2} \mathcal{A}^{n-1}$).
- **Viscous**: **Crank–Nicolson** ($\tfrac{1}{2}(\mathcal{V}(u^*) + \mathcal{V}(u^n))$).
- **Surface tension**: **semi-implicit linearised** (Aland–Voigt-type); evaluated at $t^{n+1/2}$ for BF consistency with the curvature-normal pair.
- **Projection**: **variable-density BF PPE** ([WIKI-X-024](../../wiki/cross-domain/WIKI-X-024.md)).
- **Status**: the recommended default for ch13 production.

### 3.3 Level 3 — stiff-regime / future

- **Advection**: UCCD6 inside **Radau IIA** (5-th order A/L-stable IRK).
- **Viscous**: inside the same IRK stage.
- **Surface tension**: **fully implicit jump conditions** (Li 2022) or **fully-coupled pressure/velocity/interface** (Denner 2024).
- **Use**: extreme density/viscosity ratio, very low We, thin films, stiff-regime campaigns.
- **Cost**: nonlinear JFNK per step; reserve for campaigns that cannot tolerate L2.

## 4. Level-2 recommended time discretisation

For $n \to n+1$ with time step $\Delta t$ and density field evaluated at the half step, $\rho^{n+1/2} = \tfrac{1}{2}(\rho^n + \rho^{n+1})$:

### 4.1 Predictor (AB2 advection + CN viscous + semi-implicit ST + gravity)

$$
\boxed{\;
\rho^n \frac{\mathbf{u}^* - \mathbf{u}^n}{\Delta t}
= -\rho^n \Bigl[\tfrac{3}{2}\mathcal{A}_{\text{UCCD6}}(\mathbf{u}^n) - \tfrac{1}{2}\mathcal{A}_{\text{UCCD6}}(\mathbf{u}^{n-1})\Bigr]
+ \tfrac{1}{2}\bigl[\mathcal{V}(\mathbf{u}^*) + \mathcal{V}(\mathbf{u}^n)\bigr]
+ \mathbf{f}_\sigma^{n+1/2}
+ \rho^n \mathbf{g}.
\;}
$$

Notes:

- $\mathcal{A}_{\text{UCCD6}}(\cdot)$ is the skew-symmetric advection plus $\sigma h^7 (-\Delta_{\text{CCD}})^4$ hyperviscosity from [WIKI-X-023](../../wiki/cross-domain/WIKI-X-023.md).
- $\mathcal{V}(\mathbf{u}) = \nabla \cdot (\mu (\nabla \mathbf{u} + \nabla \mathbf{u}^\top))$ in **flux form** (mandatory across $\mu$-jumps; cf. [SP-K](SP-K_viscous_term_ccd_two_phase.md) §3).
- $\mathbf{f}_\sigma^{n+1/2}$ is the semi-implicit linearised surface-tension force on the predicted mid-step interface; paired with the BF pressure gradient via the CSF ↔ ∇p consistency of [WIKI-X-024](../../wiki/cross-domain/WIKI-X-024.md).

### 4.2 Pressure Poisson equation (BF, variable-density)

$$
\boxed{\;
\nabla \cdot \left( \frac{1}{\rho^{n+1/2}} \nabla p^{n+1} \right) = \frac{1}{\Delta t} \nabla \cdot \mathbf{u}^*.
\;}
$$

Discretely: both sides use the *same* gradient and divergence operators as the momentum step — the BF constraint from [WIKI-X-024](../../wiki/cross-domain/WIKI-X-024.md) §3 and [WIKI-T-004](../../wiki/theory/WIKI-T-004.md).

### 4.3 Corrector

$$
\boxed{\;
\mathbf{u}^{n+1} = \mathbf{u}^* - \Delta t \cdot \frac{1}{\rho^{n+1/2}} \nabla p^{n+1}.
\;}
$$

Interface advection (level-set / CLS) follows on $\mathbf{u}^{n+1}$ by the project's existing FCCD-flux transport ([WIKI-T-046](../../wiki/theory/WIKI-T-046.md)); reinitialisation follows the standing ridge-Eikonal schedule.

## 5. Stability and energy accounting

With the discrete $\ell^2$ inner product used in [SP-N §4](SP-N_uccd6_hyperviscosity.md):

1. **Advection**: UCCD6 skew-sym is discretely anti-Hermitian (conjecture, proof pending; open question Q-1 in [WIKI-X-023](../../wiki/cross-domain/WIKI-X-023.md) §7). AB2 is explicit and classically stable under $\Delta t \le \Delta t_{\text{CFL,adv}}$ (factor $\approx 0.72$ of forward-Euler CFL on the advective spectral radius).
2. **Viscous**: CN on $\mathcal{V}$ is A-stable. Energy inequality: $\tfrac{1}{2}\mathrm{d}\|\mathbf{u}\|^2/\mathrm{d}t \le -\nu \|\nabla_{\text{CCD}}\mathbf{u}\|^2$ holds semi-discretely; CN preserves this non-positivity.
3. **Hyperviscosity** ($\sigma h^7 (-\Delta_{\text{CCD}})^4$): in AB2 mode treated as part of $\mathcal{A}_{\text{UCCD6}}$ and therefore bounded by the advective CFL of [SP-N §5](SP-N_uccd6_hyperviscosity.md). Implicit treatment inside CN (promoting $(-\Delta_{\text{CCD}})^4$ to the LHS) lifts this to unconditional stability at the cost of one extra biharmonic-like solve per step (cf. [SP-N §5](SP-N_uccd6_hyperviscosity.md)); listed as optional.
4. **Surface tension**: semi-implicit linearisation of Aland–Voigt (2019) is unconditionally stable on the Laplace–Beltrami part; the capillary-wave *resolution* bound of §1 is the remaining constraint.
5. **Projection**: variable-density BF PPE preserves the null space of div; the spurious-current bound reduces to the BF operator residual (zero under §4.2's matched-operator formulation).

The composite Level-2 step therefore has effective Δt:

$$
\Delta t_{\text{L2}} \approx \min\bigl(\Delta t_{\text{CFL,adv}},\; \Delta t_{\text{cap}}\bigr) \ll \Delta t_{\text{visc}}
$$

for ch13 regimes (Re $\gg 1$, small $h$): the viscous CFL is removed, the capillary bound and the advective CFL remain.

## 6. Implementation notes

- **AB2 warm-up**: use SSPRK3 for step 0→1, switch to AB2 from step 1 onward. Project's existing `AB2` integrator already implements this pattern.
- **CN viscous solve**: a Helmholtz-type system $(I - \tfrac{\Delta t}{2\rho^n}\mathcal{V})\mathbf{u}^* = \text{RHS}$. Reuse the project's CCD-Helmholtz inverse; matrix-free GMRES at $N=128$ is well-conditioned.
- **Semi-implicit ST**: implement as a Laplace–Beltrami linearisation on the predicted interface (see [WIKI-T-023](../../wiki/theory/WIKI-T-023.md) — the "Future" label can now be upgraded to "Level-2 recommended").
- **BF PPE**: the face-coefficient is $1/\rho^{n+1/2}_f$ with harmonic averaging across interface-crossing faces (Francois et al. 2006). The gradient and divergence must share their stencils with the momentum step.
- **Interface Δt budgeting**: `run.time.dt_cap_safety = 0.2` as default; below $0.1$ is wasteful, above $0.3$ risks capillary wave distortion. Monitor the measured capillary period $T_c = 2\pi/\omega_c$ on-the-fly to auto-adjust.
- **Level 3 hook**: the predictor/PPE/corrector abstraction in `ns_pipeline.py` already factors the three steps; a Radau IIA integrator can replace the predictor without touching the PPE solver.

## 7. Open questions for follow-up research

- **Q-I1** — Empirical calibration of $C_{\text{wave}}$ for ch13 water–air capillary wave (M=2 perturbation). Expect $C_{\text{wave}} \simeq 0.2$ to match Denner & van Wachem (2015) Table 1.
- **Q-I2** — Does Crank–Nicolson on $(-\Delta_{\text{CCD}})^4$ introduce measurable phase error at resolved wavenumbers? If yes, AB2 treatment (§5.3) is preferred.
- **Q-I3** — Semi-implicit ST stability proof *with* BF-matched pressure (composition of Aland–Voigt unconditional stability and the discrete Helmholtz decomposition).
- **Q-I4** — Level-3 Radau IIA cost breakpoint: at what $\rho_1/\rho_2$ does the JFNK cost drop below the L2 time-step penalty? Literature suggests $\rho_1/\rho_2 > 10^4$ or $We \ll 1$.

## References

- **Brackbill, J. U., Kothe, D. B., & Zemach, C.** (1992). A continuum method for modeling surface tension. *Journal of Computational Physics* **100**(2), 335–354.
- **Francois, M. M., Cummins, S. J., Dendy, E. D., Kothe, D. B., Sicilian, J. M., & Williams, M. W.** (2006). A balanced-force algorithm for continuous and sharp interfacial surface tension models within a volume tracking framework. *JCP* **213**(1), 141–173.
- **Denner, F., & van Wachem, B. G. M.** (2015). Numerical time-step restrictions as a result of capillary waves. *JCP* **285**, 24–40.
- **Denner, F., & van Wachem, B. G. M.** (2022). On the capillary time-step restriction. *JCP* **449**, 110788.
- **Denner, F.** (2024). A fully-coupled pressure-based finite-volume method for two-phase flows including surface tension with implicit interfacial coupling. *JCP* (in press / 2024).
- **Li, Z.** (2022). Fully implicit jump-condition enforcement for sharp-interface two-phase flow. *JCP* **458**, 111107.
- **Aland, S., & Voigt, A.** (2019). Benchmark computations of diffuse interface models for two-dimensional bubble dynamics. *Int. J. Numer. Meth. Fluids* **91**(3), 111–137 — semi-implicit surface-tension unconditional stability.
- **Bänsch, E.** (2001). Finite element discretization of the Navier–Stokes equations with a free capillary surface. *Numer. Math.* **88**, 203–235 — historical root of semi-implicit Laplace–Beltrami.
- **Chu, P. C., & Fan, C.** (1998). A three-point combined compact difference scheme. *JCP* **140**, 370–399.
- **SP-N** (this series, [SP-N_uccd6_hyperviscosity.md](SP-N_uccd6_hyperviscosity.md)) — UCCD6 core (formerly SP-H; renumbered 2026-04-23 to resolve collision with [SP-H_fccd_face_jet_fvm_hfe.md](SP-H_fccd_face_jet_fvm_hfe.md)).
- **WIKI-X-023** — UCCD6 integration design for incompressible NS.
- **WIKI-X-024** — Balanced-force design for two-phase UCCD6-NS.
- **WIKI-T-004** — Balanced-force condition: operator consistency principle.
- **WIKI-T-023** — Surface-tension semi-implicit method: Laplace–Beltrami linearisation (Future → Level-2 recommended after this note).
