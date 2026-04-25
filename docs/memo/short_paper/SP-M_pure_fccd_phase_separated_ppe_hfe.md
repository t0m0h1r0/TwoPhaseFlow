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

## 10. Implementation Status: Pressure-Jump Surface Tension Phase 2

The executable SP-M stack now separates the two surface-tension roles:

```yaml
momentum:
  terms:
    surface_tension:
      formulation: pressure_jump
```

`pressure_jump` deliberately returns no CSF body force.  Instead, the pipeline
passes `(ψ, κ, σ)` to the phase-separated FCCD PPE and composes the final pressure
as

\[
p = \tilde p + \sigma\kappa(1-\psi).
\]

This matches the existing IIM jump-decomposition convention and prevents the
configuration from pretending that a CSF body force and a sharp pressure jump are
the same numerical object.  Full GFM ghost pressure jets remain the next row-level
closure; Phase 2 provides the correct YAML semantics and executable jump
composition path.

## 11. Implementation Status: Per-Phase PPE Compatibility Phase 3

Once cross-interface PPE coupling is removed, each phase block is a Neumann
elliptic problem with its own nullspace.  Therefore the discrete RHS must satisfy
one compatibility condition per phase:

\[
\sum_{\Omega_q} rhs_q \approx 0,\qquad q\in\{L,G\}.
\]

The FCCD matrix-free phase-separated solver now projects the RHS by subtracting
its mean separately in the gas and liquid masks before GMRES, and it keeps one
pressure gauge pin per detected phase.  This is not a finite-volume conservation
claim; it is the solvability condition for the FVM-free differential PPE blocks.

The gauge pin is a nullspace constraint, not a physical boundary condition.
Therefore it must be placed on a bulk row of each phase block.  Pinning the
first density-threshold crossing is mathematically unsafe: in a diffuse
interface it can select a contact-line/interface row, replacing a pressure-jump
or cut-face row by a Dirichlet gauge row.  In the wall-bounded capillary-wave
case this produced a left-edge force spike and a two-order-of-magnitude kinetic
energy inflation.  The production rule is now:

1. detect the gas and liquid masks from the phase-separated density threshold;
2. prefer cells whose density is within 5% of the phase bulk value;
3. within those bulk candidates, choose the cell farthest from the domain
   boundary in index distance;
4. fall back to the old phase mask only if no bulk candidate exists.

This keeps the gauge operation aligned with the Neumann nullspace theory: the
pin removes only an arbitrary phase constant and does not alter an interface or
wall-contact equation.

## 12. Implementation Status: Base-Pressure Warm Start Phase 4

With pressure-jump decomposition, the elliptic unknown is not the final pressure
`p`; it is the smooth block pressure `p_tilde`.  The physical pressure is
assembled afterward as

\[
p = \tilde p + \sigma\kappa(1-\psi).
\]

Warm-starting GMRES with the assembled pressure would feed the discontinuous jump
component back into the next smooth PPE solve.  The pipeline therefore stores
`last_base_pressure` and uses only `p_tilde` as the next PPE initial guess, while
returning the assembled pressure to the momentum corrector.

## 13. Implementation Status: Pressure-Jump YAML Semantics Phase 5

`pressure_jump` is not a CSF force model.  Therefore it must not carry a
`surface_tension.gradient` setting.  In the YAML contract, force-gradient choices
belong only to `formulation: csf`; the SP-M pressure-jump path applies surface
tension through the PPE context `(ψ,κ,σ)` and sets the surface-tension gradient
scheme to `none`.

This keeps the user-facing configuration scheme-first and term-correct: `fccd`
selects the pressure/interface differential scheme, while `pressure_jump` selects
the sharp-interface surface-tension role.

## 14. Implementation Status: Explicit PPE Interface Coupling Phase 6

The PPE operator configuration now separates two concepts:

```yaml
operator:
  coefficient: phase_separated
  interface_coupling: jump_decomposition
```

`coefficient` defines the phase-block elliptic operator.  `interface_coupling`
defines how the blocks are closed across Γ.  The current executable coupling is
`jump_decomposition`; future GFM ghost pressure jets should appear as a distinct
coupling mode rather than being implied by `phase_separated`.

## 15. Implementation Status: Pressure-Jump Consistency Guard Phase 7

`pressure_jump` is now guarded as a coupled PPE feature.  It is valid only with

```yaml
operator:
  coefficient: phase_separated
  interface_coupling: jump_decomposition
```

This prevents silent fallbacks where the user requests a sharp pressure jump but
the selected PPE operator is still the mixture-density model or has no jump
closure.  The same guard exists in the direct `TwoPhaseNSSolver` constructor.

## 16. Implementation Status: PPE Diagnostics Phase 8

The SP-M PPE path now exposes runtime diagnostics when step diagnostics are
enabled:

- `ppe_phase_count`
- `ppe_pin_count`
- `ppe_rhs_phase_mean_before_max`
- `ppe_rhs_phase_mean_after_max`
- `ppe_interface_coupling_jump`

These values verify that the phase-separated PPE actually sees two phase blocks,
uses one pressure gauge per block, and projects the RHS to the per-phase Neumann
compatibility condition before GMRES.

## 17. Implementation Status: Regrid Reprojection Context Guard Phase 9

Dynamic interface-fitted grid rebuilds invoke a velocity reprojection PPE before
the main timestep PPE.  That auxiliary reprojection must not inherit the previous
step's `pressure_jump` context; otherwise the discontinuous assembled pressure
jump is differentiated during remap cleanup and can create artificial kinetic
energy.  `update_grid()` and `invalidate_cache()` now clear the stored interface
jump context, so only the main SP-M PPE receives `(ψ,κ,σ)` for the current step.
