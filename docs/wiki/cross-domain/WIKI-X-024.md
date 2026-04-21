---
ref_id: WIKI-X-024
title: "Balanced-Force Design for Two-Phase UCCD6-NS (Surface Tension ↔ Pressure Gradient Consistency is the Primary Driver)"
domain: cross-domain
status: PROPOSED  # Research memo; BF-residual measurement under UCCD6 pending
superseded_by: null
sources:
  - description: Internal research memo on BF-pair design vs UCCD6 priority (2026-04-22)
  - description: "Francois, M. M. et al. (2006). A balanced-force algorithm for continuous and sharp interfacial surface tension models within a volume tracking framework. JCP 213(1), 141–173."
  - description: "Brackbill, J. U., Kothe, D. B., & Zemach, C. (1992). A continuum method for modeling surface tension. JCP 100(2), 335–354."
depends_on:
  - "[[WIKI-X-023]]: UCCD6 Integration Design for Incompressible NS"
  - "[[WIKI-T-004]]: Balanced-Force Condition: Operator Consistency Principle"
  - "[[WIKI-T-044]]: Balanced-Force Residual Diagnostic"
  - "[[WIKI-T-038]]: HFE Curvature Smoothing"
  - "[[WIKI-X-004]]: Pressure Instability in High-Order Two-Phase Flow"
  - "[[WIKI-X-022]]: N-Robust BF-Consistent Full-Stack Architecture"
consumers:
  - domain: experiment
    description: "CHK-176 / ch13_06 BF-residual measurement under UCCD6 momentum convection (H-01 late blow-up; WIKI-E-030)"
  - domain: future-impl
    description: "GFM pressure-jump path in TwoPhaseNSSolver (currently CSF only)"
  - domain: theory
    description: "Discrete force-balance proof (variable-ρ), spurious-current bound for balanced UCCD6-NS"
tags: [balanced_force, parasitic_currents, csf, gfm, uccd6, two_phase, curvature, design_guide]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Balanced-Force Design for Two-Phase UCCD6-NS

## Thesis

> **In two-phase flow with surface tension, the dominant error source is *not*
> the advection operator's order — it is the discrete mismatch between
> $\sigma\kappa\nabla\psi$ and $\nabla p$. UCCD6 stabilises momentum advection;
> balanced-force (BF) pairing of the pressure-gradient and surface-tension
> operators determines whether static drops stay static.**

If UCCD6 is added without repairing the BF pair, the static-droplet test
still exhibits parasitic currents; if BF is satisfied discretely, parasitic
currents collapse to the curvature-evaluation error floor. This entry
positions BF at the centre of the two-phase UCCD6-NS design, with UCCD6
as a secondary (but still necessary) advection-stabilisation layer.

## 1. The BF principle in one line

For a static drop under $\mathbf{u} \equiv 0$, the momentum equation
reduces to

$$
\nabla p \;=\; \sigma\kappa\nabla\psi \quad \text{(exactly, continuous)}.
$$

At the discrete level this becomes a statement about the operators:

$$
\boxed{\; \nabla^{\text{disc}}_p \;\equiv\; (\sigma\kappa)\,\nabla^{\text{disc}}_\psi \quad\Leftrightarrow\quad \text{BF pair.} \;}
$$

**If the two sides use different discretisations, different stencils, or
different grid locations, the residual drives a parasitic flow** whose
magnitude is independent of advection order (Francois et al. 2006,
[WIKI-T-044](../theory/WIKI-T-044.md)).

**UCCD6 applied to the advection operator has zero leverage on this residual**
— it is an NS-level velocity stabiliser, orthogonal to the BF pair.

## 2. Complete discretisation of two-phase UCCD6-NS

The recommended stack — corrections to [WIKI-X-023](WIKI-X-023.md) §3 with
surface tension made explicit:

### 2.1 Predictor (velocity)

$$
\rho \,\frac{\mathbf{u}^{\star} - \mathbf{u}^{n}}{\Delta t}
= \mathcal{A}_{\text{skew+UCCD6}}(\mathbf{u}^{n})
\;+\; \mathcal{V}_{\text{flux}}(\mu, \mathbf{u})
\;+\; \mathbf{f}_\sigma
\;+\; \rho \mathbf{g}.
$$

| Term | Operator | BF-critical? |
|---|---|---|
| advection | skew-sym CCD + UCCD6 hyperviscosity | no |
| viscous | $\nabla^{\text{CCD}}_{\text{face}}\!\cdot(\mu\,\nabla^{\text{CCD}}_{\text{face}}\mathbf{u})$ flux form | no |
| surface tension | $\mathbf{f}_\sigma = \sigma\kappa\,\nabla^{\text{BF}}\psi$ | **yes** |
| gravity | $\rho\mathbf{g}$ | no |

### 2.2 Variable-density PPE

$$
\nabla^{\text{BF}} \!\cdot\! \left(\tfrac{1}{\rho} \nabla^{\text{BF}} p\right)
= \tfrac{1}{\Delta t}\,\nabla^{\text{BF}} \!\cdot\! \mathbf{u}^{\star}
+ \nabla^{\text{BF}} \!\cdot\! \left(\tfrac{1}{\rho}\, \mathbf{f}_\sigma\right).
$$

The **same** $\nabla^{\text{BF}}$ must appear in all three places:
(i) $\mathbf{f}_\sigma$ construction, (ii) PPE divergence of the CSF term,
(iii) corrector step below. Violating this triple equality is the dominant
source of H-01 late blow-up on non-uniform grids
([WIKI-X-021](WIKI-X-021.md), [WIKI-X-022](WIKI-X-022.md)).

### 2.3 Corrector

$$
\mathbf{u}^{n+1} = \mathbf{u}^{\star} - \Delta t \,\tfrac{1}{\rho}\, \nabla^{\text{BF}} p.
$$

### 2.4 Ψ transport (unchanged from [WIKI-X-023](WIKI-X-023.md))

$$
\partial_t \psi + \mathbf{u}\cdot\nabla\psi = 0
\quad \text{discretised by FCCD / ridge-eikonal reinit}.
$$

Note that $\nabla^{\text{BF}}$ for the pressure pair may differ from the
FCCD advection operator used on $\psi$ — they serve different purposes and
need not share stencils.

## 3. CSF vs GFM — two BF-compatible paths

### 3.1 CSF (continuous surface force)

$$
\mathbf{f}_\sigma = \sigma\kappa\,\nabla^{\text{CCD}}\psi
\qquad\text{with}\qquad
\nabla^{\text{BF}} = \nabla^{\text{CCD}}.
$$

- Pair the CCD pressure gradient (`_grad_op` in `ns_pipeline.py`) with the
  CCD ψ-gradient for $\mathbf{f}_\sigma$.
- On non-uniform grids use FVM gradient on both sides (project's R-1.5,
  CHK-176).
- Residual floor is set by **curvature error**, not the operator pair —
  cf. Francois et al. 2006 §5.

### 3.2 GFM (pressure-jump, sharp)

$$
[p]_\Gamma = \sigma\kappa, \quad \mathbf{f}_\sigma \text{ absent from momentum}.
$$

- Surface tension enters as a jump condition in the PPE RHS, not as a body
  force.
- Curvature enters only the jump term; the momentum equation is
  jump-agnostic.
- Sharper near-interface pressure; implementation cost is higher
  (project uses IIM stencil correction, [WIKI-X-020](WIKI-X-020.md)).

**BF is preserved in both paths**, but the residual structure differs:
CSF residual ∝ curvature error; GFM residual ∝ IIM stencil order.

## 4. Why high-order advection alone does not save the static drop

A common misconception: "switch to UCCD6 and the parasitic currents vanish."
In static equilibrium $\mathbf{u} \equiv 0$, the advection RHS is
*identically zero* regardless of order — so its discretisation is
inactive. The parasitic flow is generated purely by the residual

$$
\mathbf{r}_{\text{BF}} = \nabla^{\text{disc}}_p - (\sigma\kappa)\,\nabla^{\text{disc}}_\psi
$$

driving $\rho\,\partial_t\mathbf{u} = -\mathbf{r}_{\text{BF}}$. UCCD6
*reduces* the growth once a spurious $\mathbf{u} \ne 0$ is established,
but it cannot remove $\mathbf{r}_{\text{BF}}$ itself.

## 5. Curvature as the residual error source

After BF is enforced, the remaining spurious-current amplitude is governed
by how accurately $\kappa$ is estimated (Francois et al. 2006):

$$
\|\mathbf{u}_{\text{spurious}}\|_\infty \;\sim\; \frac{\sigma\,\delta\kappa}{\mu}
\quad \text{(Capillary-scale bound).}
$$

- Raw CCD on $\nabla^2\psi$ is under-resolved near the interface; use the
  project's HFE smoothing ([WIKI-T-038](../theory/WIKI-T-038.md)).
- Curvature evaluated on signed-distance $\phi$ (after reinit) is more
  stable than on the CLS field $\psi$ directly; both options are live in
  `CurvatureCalculator` vs `CurvatureCalculatorPsi`.
- High-order derivatives amplify curvature noise — **do not** attempt to
  rescue curvature quality by bumping $\kappa$ evaluation to O($h^6$);
  prefer smoothing (HFE) + lower-order κ.

## 6. Design map (consolidated)

| Component | Scheme | Rationale |
|---|---|---|
| ψ advection | FCCD flux (SP-D §7) | non-uniform grid, BF-compatible metric |
| u advection | CCD skew-sym + UCCD6 hyperviscosity | energy-cons. + selective damping |
| viscous | flux-form μ-weighted Laplacian | handles μ jump |
| **ST force** | **$\sigma\kappa \nabla^{\text{BF}}\psi$** | **must match pressure op** |
| **∇p** | **matched to ST force (CCD or FVM)** | **BF pair** |
| PPE | FVM sparse / matrix-free | rank-safe, variable ρ |
| curvature | HFE smoothing + CCD | balances noise vs accuracy |

## 7. Implementation checklist (ch13)

1. `_grad_op` and surface-tension `∇ψ` share the same operator instance
   (project already does this via R-1.5, CHK-176).
2. PPE RHS includes the full BF divergence
   $\nabla\cdot(\mathbf{f}_\sigma/\rho)$ — verify in
   `ns_pipeline.py:725`.
3. Corrector uses `_grad_op.gradient(p, ax)` — same instance as (1).
4. Curvature is HFE-filtered before entering $\mathbf{f}_\sigma$.
5. UCCD6 hyperviscosity is applied to **velocity only**, not to $\psi$.
6. Diagnose the BF residual per step:
   `bf_res_max = max(|∇p − f_σ/ρ|)`; log via `debug_diagnostics`.

## 8. Open work

- **Spurious-current bound proof** for the balanced UCCD6-NS (variable-ρ,
  2-D). Expected: $\|\mathbf{u}\|_\infty = O(\delta\kappa) + O(\sigma h^7)$
  where the second term is the UCCD6 subdominant hyperviscosity leak.
- **BF residual measurement under UCCD6** — `ch13_06_capwave_waterair_n128_uccd6.yaml`
  provides the vehicle; expected result neutral vs FCCD convection
  (UCCD6 is orthogonal to the BF residual).
- **GFM path in `TwoPhaseNSSolver`** — currently CSF only; add a strategy
  subclass once the CSF + BF-consistent UCCD6 combination is validated
  at N = 128 water-air.

## References

- Francois, M. M., Cummins, S. J., Dendy, E. D., Kothe, D. B., Sicilian, J. M.,
  Williams, M. W. (2006). *A balanced-force algorithm for continuous and
  sharp interfacial surface tension models within a volume tracking
  framework.* JCP 213(1), 141–173.
- Brackbill, J. U., Kothe, D. B., & Zemach, C. (1992). *A continuum method
  for modeling surface tension.* JCP 100(2), 335–354.
- [WIKI-X-023](WIKI-X-023.md): UCCD6 NS integration (parent design)
- [WIKI-T-004](../theory/WIKI-T-004.md) / [WIKI-T-044](../theory/WIKI-T-044.md): BF principle and residual diagnostic
- [WIKI-T-038](../theory/WIKI-T-038.md): HFE curvature smoothing
- [WIKI-X-004](WIKI-X-004.md): two-phase pressure instability survey
- [WIKI-X-022](WIKI-X-022.md): 10-method role map for N-robust BF stack
- [WIKI-X-025](WIKI-X-025.md): **Time-integration design for two-phase UCCD6-NS** — §3.2 below gives the BF PPE operator used by the Level-2 recommended integrator (AB2 advection + CN viscous + semi-implicit ST + BF projection).
