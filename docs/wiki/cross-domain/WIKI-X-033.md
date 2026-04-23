---
id: WIKI-X-033
title: "Pure High-Order FCCD Two-Phase DNS: FVM-Free Phase-Separated PPE + HFE + GFM + DC"
status: PROPOSED
date: 2026-04-23
links:
  - "[[WIKI-T-046]]: FCCD face-gradient foundation"
  - "[[WIKI-T-069]]: FCCD face jet"
  - "[[WIKI-X-029]]: Balanced-force operator consistency"
  - "[[WIKI-X-030]]: viscous stress-divergence design"
  - "[[SP-M]]: pure FCCD architecture short paper"
compiled_by: ResearchArchitect
---

# Pure High-Order FCCD Two-Phase DNS

## Core position

The updated architecture is deliberately **FVM-free**.  It treats FCCD as a pure
high-order finite-difference language for the full sharp-interface two-phase
solver:

- FCCD/Ridge-Eikonal for interface transport and geometry.
- FCCD + HFE for high-order one-sided interface states.
- CCD/FCCD stress-divergence + defect correction for viscosity.
- Phase-separated FCCD PPE + GFM for pressure and surface-tension jumps.

The design gives up machine-epsilon finite-volume conservation as the primary
invariant.  The replacement invariant is high-order truncation control:
$\mathcal{O}(\Delta x^4)$ face-locus FCCD and $\mathcal{O}(\Delta x^6)$ bulk CCD
where smoothness permits.

## Why this is not general-purpose CFD

This is a DNS-grade research architecture for capillary and sharp-interface
physics, not a robust industrial FVM replacement.  The cost is high and the
implementation is complex because every interface crossing must be handled by
HFE/GFM/jump-aware compact stencils.  Its target problems are microfluidics,
inkjet breakup, bubble inception, capillary waves, and similar regimes where
spurious current and interface smearing dominate the error budget.

## Phase-separated PPE

The pressure equation is split by phase:

$$
\nabla\cdot(\rho_L^{-1}\nabla p_L)=S_L,\qquad
\nabla\cdot(\rho_G^{-1}\nabla p_G)=S_G.
$$

GFM stitches the two systems at the interface:

$$
[p]_\Gamma=\sigma\kappa,\qquad
[\rho^{-1}\partial_n p]_\Gamma=0.
$$

FCCD supplies the high-order face-locus gradient/divergence rows, while GFM
supplies ghost pressure jets so each phase sees a compact single-phase stencil.

## HFE role

HFE is the "sharp one-sided state" mechanism.  It uses the FCCD/CCD jet
$(u,u',u'')$ to reconstruct upwind or source-side values at the face without
sampling through the interface.  In this architecture HFE is not an add-on
filter; it is the state-evaluation contract shared by advection, pressure jumps,
and interface force evaluation.

## Defect correction role

Pure high-order compact rows are expensive and can be poorly conditioned near
jumps.  Defect correction provides the compromise:

1. solve a robust low-order inner problem;
2. evaluate the high-order FCCD/GFM residual;
3. iterate until the high-order residual is small.

This pattern applies to viscous Helmholtz solves and, eventually, to
phase-separated PPE rows.

## Trade-off

| Benefit | Cost |
|---|---|
| Reduced spurious current via common face-locus operators | Hard interface-row assembly |
| Sharp interface and pressure jump fidelity | No machine-epsilon FVM volume identity |
| High-order DNS accuracy in resolved regimes | Expensive elliptic/defect-correction loops |
| Unified FCCD/HFE/GFM language | Limited robustness for under-resolved engineering cases |

## Design rule

Use `fvm` only as a comparison or legacy route.  The pure architecture should
name the mathematical scheme (`fccd`, `ccd`, `uccd6`) and keep locus/form choices
(`face`, `flux`, `bulk`, `normal_fallback`) as term-local options or defaults.


## Code Status: Phase 1 Split PPE

`projection.poisson.operator.coefficient: phase_separated` is the SP-M YAML
entry point.  It is intentionally different from `phase_density`:

- `phase_density` keeps the older mixture-density FCCD operator
  `D_f[(1/rho)_f G_f(p)]`.
- `phase_separated` uses FCCD rows within each density phase and sets
  cross-interface PPE face coupling to zero.
- one pressure gauge is pinned per detected phase block.
- GFM jump ghost pressure jets are still the next stage, not silently faked.

This keeps the implementation honest: the code is already FVM-free and
phase-split, while the missing GFM jump-row closure remains explicit.

## Code Status: Phase 2 Pressure Jump

`momentum.terms.surface_tension.formulation: pressure_jump` is now the SP-M
surface-tension setting.  It differs from `csf`:

- `csf` computes a body force `σκ∇ψ` and adds it to the balanced-force PPE path.
- `pressure_jump` computes no body force and supplies `(ψ,κ,σ)` to the
  phase-separated FCCD PPE.
- the executable pressure is composed as `p = p_tilde + σκ(1-ψ)`, matching the
  existing IIM jump-decomposition sign convention.

This keeps the design philosophy unified: phase physics is declared as a sharp
interface pressure jump, not hidden inside a surface-tension force model.

## Code Status: Phase 3 Per-Phase Compatibility

Because `phase_separated` cuts cross-interface PPE coupling, the gas and liquid
pressure blocks each have a Neumann nullspace.  The solver therefore projects the
PPE RHS to zero mean separately in each detected density phase before GMRES, then
pins one pressure gauge per phase.  This is a solvability requirement for the
split differential operator, not a return to FVM conservation.

## Code Status: Phase 4 Base-Pressure Warm Start

For `pressure_jump`, the PPE unknown is `p_tilde`; the returned pressure is the
assembled physical pressure `p = p_tilde + σκ(1-ψ)`.  The pipeline now warm-starts
GMRES with `p_tilde` only.  This avoids injecting the sharp jump component into
the next smooth phase-block solve.

## Code Status: Phase 5 YAML Semantics

For `surface_tension.formulation: pressure_jump`, `surface_tension.gradient` is
invalid and must be omitted.  The jump path is a PPE pressure condition, not a
body-force gradient.  The loader maps this to `surface_tension_gradient_scheme =
none`, and the direct solver constructor rejects conflicting force-gradient
settings.

## Code Status: Phase 6 Explicit Coupling Key

`phase_separated` now names only the PPE coefficient/block structure.  The
interface closure is explicit as
`projection.poisson.operator.interface_coupling: jump_decomposition`.  This keeps
configuration honest: the current code uses jump decomposition, while a future
GFM ghost-row closure must be introduced as its own coupling mode.

## Code Status: Phase 7 Consistency Guard

`surface_tension.formulation: pressure_jump` now requires
`coefficient: phase_separated` and `interface_coupling: jump_decomposition`.
Both YAML loading and direct solver construction reject inconsistent settings, so
a pressure jump can no longer be requested without the matching SP-M PPE path.

## Code Status: Phase 8 PPE Diagnostics

Debug diagnostics now include SP-M PPE state: phase count, pin count,
pre/post per-phase RHS mean, and whether jump decomposition is active.  These
metrics make the current split-PPE approximation visible in experiment output
instead of hiding it inside the solver.
