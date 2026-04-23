# SP-M: Pure High-Order FCCD Two-Phase DNS Architecture — Phase-Separated PPE, HFE, GFM, and Defect Correction without FVM

**Status**: PROPOSED research architecture  
**Date**: 2026-04-23  
**Related**: SP-A, SP-C, SP-D, SP-H, SP-J, SP-K, WIKI-X-033, WIKI-T-046, WIKI-T-069

---

## Abstract

This short paper records the updated design target: a fully non-FVM, pure
high-order finite-difference two-phase solver built around FCCD.  The governing
principle is to give up machine-epsilon finite-volume conservation as the
primary invariant and instead drive spatial truncation error to the
$\mathcal{O}(\Delta x^4)$--$\mathcal{O}(\Delta x^6)$ regime using a single
high-order differential language.  The resulting architecture combines
Ridge-Eikonal interface geometry, FCCD/HFE advection, CCD/FCCD viscous
stress-divergence with defect correction, and a phase-separated FCCD PPE stitched
by GFM jump conditions.  Its natural role is not broad engineering throughput
but sharp-interface DNS for capillary-dominated phenomena where spurious current
suppression and interface fidelity dominate cost considerations.

---

## 1. Design Thesis

The architecture is intentionally not a hybrid "FVM for conservation, FD for
accuracy" solver.  It is a pure high-order FD solver:

$$
\text{interface},\ \text{momentum},\ \text{viscosity},\ \text{pressure}
\quad\longrightarrow\quad
\text{CCD/FCCD operators plus jump-aware interface closures}.
$$

The trade is explicit:

| Keep | Give up |
|---|---|
| Common high-order differential operators | Machine-epsilon FVM volume conservation |
| Face-locus pressure/surface-tension consistency | Low-order robust FVM averaging |
| HFE/GFM sharp-interface evaluation | Simple conservative control-volume assembly |
| Defect correction for stiffness | Cheap industrial-scale robustness |

Mass/volume conservation becomes an asymptotic high-order property rather than a
control-volume identity.  This is acceptable only when the target is DNS-grade
resolution and the truncation error is driven below the physical error budget.

---

## 2. Phase 1 — Interface Tracking

The interface is not represented by a VOF volume fraction.  It remains a
high-order transported field:

- **Topology/metric split**: Ridge-Eikonal keeps distance quality and topology
  handling separate.
- **Transport**: FCCD advances the conservative interface field $\psi$ without
  falling back to low-order VOF fluxing.
- **Geometry**: $\phi$, normals, and curvature are geometry assets used by
  surface tension, HFE, and viscous normal/tangent switching.

---

## 3. Phase 2 — Momentum Advection with FCCD + HFE

Momentum advection should be evaluated as a high-order differential operation,
not as a finite-volume cell update.  The face jet

$$
\mathcal{J}_f(u)=(u_f,u'_f,u''_f)
$$

provides the HFE state at the FCCD face locus.  Upwind or Riemann selection acts
on the directional left/right HFE states, while the final spatial derivative is
returned to the nodal momentum equation through the FCCD operator family.

HFE is therefore a reconstruction layer, not a conservation law by itself.  Its
purpose is to prevent high-order stencils from sampling through discontinuous
phase data without the correct one-sided state.

---

## 4. Phase 3 — Viscosity with Stress-Divergence + DC

The viscous term remains

$$
\nabla\cdot(2\mu D(\mathbf{u})).
$$

The pure-FCCD architecture does not collapse this globally to
$\mu\nabla^2\mathbf{u}$ across a viscosity jump.  Instead:

1. **Bulk**: use high-order CCD/FCCD derivatives where $\nabla\mu=0$.
2. **Interface band**: use stress-divergence with normal-axis fallback and
   tangential CCD retention.
3. **Implicit stiffness**: solve a robust low-order inner problem and compute
   the outer residual with the high-order stress operator:

$$
A_L\delta \mathbf{u}=r_H,\qquad
r_H=\mathrm{RHS}-A_H\mathbf{u}^{(m)}.
$$

This is the viscosity-side analogue of the pressure strategy: stable inner
solve, high-order outer physics.

---

## 5. Phase 4 — Phase-Separated FCCD PPE + GFM

The pressure projection is the architectural centerpiece.  Instead of a
single-fluid smeared PPE or FVM flux balance, solve separate elliptic problems
in each phase:

$$
\nabla\cdot\left(\frac{1}{\rho_L}\nabla p_L\right)=S_L,\qquad
\nabla\cdot\left(\frac{1}{\rho_G}\nabla p_G\right)=S_G.
$$

The phases are stitched at $\Gamma$ by GFM jump conditions:

$$
[p]_\Gamma=\sigma\kappa,\qquad
\left[\frac{1}{\rho}\partial_n p\right]_\Gamma=0
$$

for the no phase-change incompressible case.  FCCD supplies the face-locus
gradient/divergence operators; GFM supplies ghost pressure jets
$(p^*,p'^*,p''^*)$ so compact stencils remain single-phase on each side.

The intended outcome is a pressure operator whose algebraic rows retain the
single-phase high-order structure away from $\Gamma$, while interface
discontinuities enter only through physically derived jump closures.

---

## 6. CFD Positioning

This solver occupies the "research DNS / sharp-interface extreme" corner:

- **Best fit**: microfluidics, inkjet breakup, bubble nucleation, capillary waves,
  coalescence/splitting onset, and other surface-tension-dominated phenomena.
- **Primary win**: reduction of spurious currents by aligning pressure,
  surface-tension, HFE, and interface jump evaluation in a common high-order
  face-locus language.
- **Primary cost**: implementation complexity, difficult interface-row assembly,
  and expensive elliptic solves.
- **Not the target**: broad industrial throughput where FVM robustness and exact
  control-volume conservation dominate.

---

## 7. Compatibility with Existing SP-H

SP-H introduced the FCCD face jet as a bridge between FVM projection and HFE
advection.  SP-M is the FVM-free continuation: the same face jet remains useful,
but conservation is no longer delegated to FVM.  The face jet becomes the common
high-order interface contract for HFE, GFM ghost states, pressure gradients, and
phase-separated PPE rows.

---

## 8. Acceptance Gates

1. Static droplet: spurious current decreases with FCCD/HFE/GFM order and does
   not grow with density ratio.
2. Young-Laplace pressure jump: $[p]=\sigma\kappa$ converges at the designed
   interface order.
3. Projection: post-correction $\nabla_h\cdot\mathbf{u}$ decreases with PPE
   tolerance and grid refinement.
4. Volume drift: no machine-epsilon guarantee is claimed; observed drift must
   scale with the high-order truncation budget.
5. Interface motion: HFE/FCCD advection preserves sharpness without Gibbs-driven
   breakup on resolved test cases.

---

## One-Line Summary

> Pure FCCD two-phase DNS trades finite-volume exact conservation for a single
> high-order, jump-aware differential architecture: phase-separated PPE + GFM for
> pressure, HFE for interface states, and defect correction for stiff viscous and
> elliptic solves.

---

## 9. Implementation Status: Phase-Separated FCCD PPE Phase 1

The executable first stage now distinguishes the SP-M pressure coefficient model
from the older mixture-density model in YAML:

```yaml
projection:
  poisson:
    operator:
      discretization: fccd
      coefficient: phase_separated
```

This selects the FCCD matrix-free PPE with a phase-separated coefficient rule.
Faces whose two endpoint densities belong to different phases are assigned zero
PPE coupling, so the pressure operator is assembled as two FCCD phase blocks
rather than as a smeared mixture-density operator.  Each phase block receives its
own pressure gauge pin.

This is not yet the full GFM jump-row implementation.  The current stage is the
minimal SP-M-consistent executable split:

1. pure FCCD PPE rows inside each phase;
2. no FVM face-volume assembly;
3. no cross-interface density averaging;
4. one pressure nullspace constraint per detected phase;
5. GFM pressure-jump ghost jets retained as the next implementation step.

The corresponding code path is `PPESolverFCCDMatrixFree` with
`ppe_coefficient_scheme="phase_separated"`.
