---
ref_id: WIKI-P-018
title: "Chapters 1-13 Recent Paper-Theory Contract Digest"
domain: paper
status: ACTIVE
superseded_by: null
tags: [paper, chapters_1_13, theory_digest, pressure_jump, capillary, verification]
sources:
  - path: paper/sections/01_introduction.tex
    description: "Failure-mode framing and chapter-level traceability through the current stack"
  - path: paper/sections/05_reinitialization.tex
    description: "Physical transport endpoint versus Ridge-Eikonal profile projection split"
  - path: paper/sections/06_scheme_per_variable.tex
    description: "Per-variable operator routing for CLS, momentum, pressure, and capillary closure"
  - path: paper/sections/08b_pressure.tex
    description: "Variational pressure-reaction representative and Green identity"
  - path: paper/sections/09b_split_ppe.tex
    description: "Pressure-jump PPE, capillary face cochain, component saddle system, and Hodge gate"
  - path: paper/sections/11_full_algorithm.tex
    description: "One-step algorithm contract and standard-route boundary"
  - path: paper/sections/13_verification.tex
    description: "Integrated V-series grammar for pressure-jump/capillary projection evidence"
  - path: paper/sections/13d_density_ratio.tex
    description: "V6/V7 reading for density-ratio robustness and capillary-coupled effective order"
  - path: paper/sections/13e_nonuniform_ns.tex
    description: "V9 operator-group diagnostic for nominal/local epsilon switch"
  - path: paper/sections/13f_error_budget.tex
    description: "Error-budget interpretation after pressure-jump and capillary-projection updates"
  - path: docs/wiki/theory/WIKI-T-162.md
    description: "Active closed-interface capillary discretization policy"
  - path: docs/wiki/cross-domain/WIKI-X-048.md
    description: "Trial ledger that keeps falsified capillary/Hodge routes out of paper success claims"
depends_on:
  - "[[WIKI-X-041]]"
  - "[[WIKI-P-015]]"
  - "[[WIKI-P-014]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-X-048]]"
consumers:
  - domain: paper
    usage: "Use before editing Chapters 1-13 after the 2026-05-05..08 theory/paper update window"
  - domain: theory
    usage: "Recover the paper-facing contract summary without rereading every changed section"
  - domain: experiment
    usage: "Interpret V6/V7/V9 as current integrated-stack diagnostics"
compiled_by: ResearchArchitect
compiled_at: 2026-05-08
---

# Chapters 1-13 Recent Paper-Theory Contract Digest

## Scope

This card compiles the reusable paper-design and theory knowledge added or
reshaped in the 2026-05-05 through 2026-05-08 window for Chapters 1-13.  It is
not a changelog of every wording pass.  It records the current contract reading
that should survive future edits.

## Memory Items

1. Chapters 1-13 now read as a contract trace, not as method chronology:

```text
failure mode -> numerical contract -> discretization route
             -> one-step algorithm position -> V-series evidence
```

Avoid describing old "versions" or review history as if they were active
algorithm policy.  The paper-facing object is the verified stack.

2. The standard route is per-variable, not one universal discretization.  CLS
`psi` uses FCCD conservative face flux with the projected face velocity.
Interior momentum convection uses UCCD6.  CCD/FCCD/HFE build interface and
pressure-jump data.  Pressure and capillary terms are face-space correction
objects.  DCCD is not a chapter-wide stabilizing knob and is not applied as a
post-filter to the pressure field or pressure gradient.

3. Surface tension in the two-phase standard route is no longer papered as a
CSF body force in the predictor.  The accepted reading is pressure-jump PPE
plus a capillary face cochain derived from surface-energy virtual work.  The
capillary cochain is pulled back through the same transport endpoint used by
the solver, then decomposed with pressure and component-volume reactions.

4. A pressure gradient that gives the same scalar PPE divergence is not
automatically the correct pressure-work representative.  The pressure reaction
must satisfy the face Green identity used by the correction step.  A
divergence-equivalent representative can still be wrong for kinetic work and
for the capillary Hodge split.

5. The pressure-range projection/Hodge machinery is a diagnostic and static
equilibrium gate unless the standard route explicitly uses the resulting
cochain.  Do not replace the non-equilibrium capillary drive by "the part that
pressure can express" merely because it is algebraically quiet.  The trial
ledger in [[WIKI-X-048]] preserves the negative result: blanket range
projection can produce algebraic rest rather than physical capillary motion.

6. Reinitialization is now split from physical transport in the paper logic.
The capillary endpoint is the transported `psi` before Ridge-Eikonal profile
projection.  Ridge-Eikonal restores the profile/geometry representation; its
geometric work is a separate ledger item, not the surface-energy work of fluid
transport.

7. Chapter 12 is component verification; Chapter 13 is integrated
verification.  The V-series labels encode what is certified by the current
operator group, not generic evidence for a looser method family.

8. V6/V7/V9 must be read as pressure-jump/capillary-projection stack evidence:
V6 supports density-ratio robustness through `rho_l/rho_g = 833` with
roundoff-level CLS volume drift and small terminal speed after capillary
projection.  V7 is Type-D: the observed effective slope `1.59` is attributed
to the capillary pressure-jump / affine FCCD projection interface-band limit,
not to a failed BDF2 coefficient.  V9 is an operator-group diagnostic for
nominal/local epsilon switching; it does not claim local epsilon is an
independent improvement mechanism.

9. Pressure outputs in the pressure-jump route are correction or Hodge
representatives.  They are not raw Laplace absolute pressure diagnostics in the
diffuse interface band.  Read pressure through the stored face cochain or the
phase-wise Hodge representative.

## Retrieval Rule

When updating Chapters 1-13, start from [[WIKI-X-041]], then this card, then
the detailed theory cards such as [[WIKI-T-162]] only if the edit changes a
capillary, pressure, transport, or verification contract.  Keep falsified
trial routes in [[WIKI-X-048]] and keep the paper narrative focused on adopted
contracts and their verification boundary.
