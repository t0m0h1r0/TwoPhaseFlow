---
ref_id: WIKI-X-040
title: "Recent Research Insight Digest: 2026-04-24 to 2026-05-03"
domain: cross-domain
status: ACTIVE
superseded_by: null
tags: [research_digest, projection_closure, affine_jump, capillary, cls, verification, meta_prompt]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
    description: "Recent ResearchArchitect CHK register for 2026-04-24--2026-05-03"
  - path: docs/wiki/cross-domain/WIKI-X-037.md
    description: "Prior wiki retrieval atlas"
  - path: docs/wiki/theory/WIKI-T-076.md
    description: "Projection-closure theorem for phase-separated FCCD"
  - path: docs/wiki/experiment/WIKI-E-032.md
    description: "ch13 projection-closure trial synthesis"
  - path: docs/wiki/theory/WIKI-T-077.md
    description: "Capillary energy stability and projection-native surface tension"
  - path: docs/wiki/cross-domain/WIKI-X-039.md
    description: "Affine jump and oriented Young--Laplace contract"
  - path: artifacts/A/review_CHK-RA-CH13-V7-IMEX-001.md
    description: "V7 IMEX-BDF2 coupled-stack root-cause analysis"
  - path: artifacts/A/review_CHK-RA-CH13-V10-SHAPE-001.md
    description: "V10 shape-error root-cause analysis"
  - path: artifacts/A/review_CHK-RA-CH12-001.md
    description: "Chapter 12 component verification refresh"
  - path: artifacts/A/ch14_affine_pressure_history_faces_CHK-RA-OSC-N64-018.md
    description: "Projection-native pressure-history face contract"
  - path: artifacts/A/review_CHK-RA-SRC-TEST-001.md
    description: "Source-test retention audit after recent stack changes"
  - path: artifacts/M/review_CHK-RA-META-V8-001.md
    description: "Meta-prompt v8 candidate research incorporation"
  - path: artifacts/M/review_CHK-RA-META-V8-002.md
    description: "Codex target bootstrap from v8 candidate"
depends_on:
  - "[[WIKI-X-037]]"
  - "[[WIKI-T-076]]"
  - "[[WIKI-E-032]]"
  - "[[WIKI-T-077]]"
  - "[[WIKI-X-039]]"
consumers:
  - domain: theory
    usage: "Quick selection of governing invariants before new capillary/projection derivations"
  - domain: experiment
    usage: "Checklist for interpreting V7/V10/ch14 negative results without retuning them away"
  - domain: code
    usage: "Guardrail for pressure-jump, projection, test-contract, and GPU/backend edits"
  - domain: paper
    usage: "Recent evidence map for keeping Chapter 12--14 narrative current"
  - domain: meta
    usage: "Prompt-system lessons from v8 candidate and Codex bootstrap"
compiled_by: ResearchArchitect
compiled_at: 2026-05-03
---

# Recent Research Insight Digest

## Scope

This page distills reusable findings from the ten-day research window
2026-04-24 through 2026-05-03.  It is a retrieval map, not a replacement for
the detailed source wiki pages and CHK artifacts.

## Executive Findings

1. Projection closure is the dominant invariant for high-density two-phase
   flow: PPE and velocity correction must share the same face-space
   `D_f A_f G_f` operator, wall rows, and phase labels.
2. Capillary coupling must be an oriented affine interface-stress contract,
   not a regular pressure field or a case-specific body force.
3. Recent negative results are mostly structural limits or contract mismatches,
   not knobs to retune: V7, V10-a, V10-b, and N64 static droplets each reject
   local CFL/reinit/mass-correction fixes.
4. Component verification must track the current production contract.  Retired
   CCD-LU/CN interpretations are useful history but must not drive current U2
   or U8 claims.
5. Documentation and prompt infrastructure became part of the research system:
   wiki, paper, tests, and generated agent prompts now need explicit
   traceability to the same governing contracts.

## Projection Closure

The most reusable mathematical lesson is:

```text
L_h = D_f A_f G_f
```

is not merely the PPE matrix.  It is the projection identity.  The corrector,
wall rows, face coefficients, pressure-jump fluxes, and diagnostic residuals
must use the same face-space objects.  The ch13 rising-bubble trial ladder
showed that changing source terms, carrying face state, or moving buoyancy
cannot repair a mismatch between `A_f^PPE` and `A_f^corr`.

Research consequence: before proposing a new force, predictor, or pressure
repair, first ask whether it preserves the face operator identity.

## Capillary Interface Stress

The ch14 capillary work refined projection closure into a sharper capillary
contract.  The physically stored jump is:

```text
psi = 1 liquid, psi = 0 gas
n_lg = liquid-to-gas normal
kappa_lg = div_Gamma n_lg
j_gl = p_gas - p_liquid = -sigma kappa_lg
G_Gamma(p; j_gl)_f = G(p)_f - B_f(j_gl)
```

Two failures became clear:

- representing `sigma kappa` as a regular pressure field can be algebraically
  cancelled by the elliptic solve; and
- applying the opposite Young--Laplace sign produces anti-surface-tension
  acceleration with nearly correct magnitude but wrong direction.

The same face-native idea also applies to pressure history.  A discontinuous
stored pressure must not be differentiated by a nodal scalar gradient at cut
faces.  The reusable object is the affine face acceleration:

```text
a^n_{p,f} = A_f (G_f p^n - B_f(j^n)).
```

## Energy Stability

The capillary energy result separates representation repair from physics.
Ridge--Eikonal or other reinitializers may restore a signed-distance or CLS
representation, but surface-area reduction belongs to surface tension.  A
production capillary scheme must therefore expose a discrete budget for kinetic
energy, surface energy, gravitational potential, and viscous dissipation.

Pointwise curvature accuracy is not enough.  The continuum identity
`kappa(psi) = kappa(phi)` under monotone transformation does not imply a
discrete energy law, because generally:

```text
D_h(g(phi)) != g'(phi) D_h(phi).
```

## Limitation Results To Preserve

| Finding | Accepted reading | Rejected reading | Next useful gate |
|---|---|---|---|
| V7 IMEX-BDF2 coupled-stack order | Capillary pressure-jump/projection interface band controls the measured exponent | IMEX-BDF2 coefficient bug, reinit cadence bug, or reference-only artifact | Structural capillary-jump/projection time discretization, or an isolated BDF2 verification problem |
| V10-a Zalesak shape error | Fixed-grid steep-CLS phase/threshold geometry plus slot/corner under-resolution | Mass correction, CFL, or slot-only explanation | Moving/adaptive mesh or an explicitly fixed-grid shape-limit framing |
| V10-b reversible vortex error | Folded filaments reach grid scale on fixed Eulerian grids | Reinitialization absence, mass correction, or timestep-only failure | Refinement/adaptive geometry study while features remain above grid scale |
| N64 static droplet pressure oscillation | IPC pressure history must be affine face-space acceleration | Pressure deletion, damping, smoothing, or curvature clipping workaround | Long-time ch14 benchmark with projection-native pressure history |
| Ch12 U2/U8 stale contracts | Component tests must follow current production/FVM/BDF2 contracts | Retired CCD-LU/CN results as current evidence | Keep U2/U8 refreshed when Chapters 7--11 contracts move |

## Verification Architecture

The ten-day window tightened the role of component and source tests.

- U2 now verifies the current `PPEBuilder` FVM/spsolve Neumann-gauge path,
  while CCD/Kronecker Poisson remains a smooth/reference component.
- U8 now verifies TVD-RK3/EXT2-AB2/implicit-BDF2/full-operator BDF2 behavior,
  rather than stale CN/explicit-cross limitations.
- U6 remains a valid negative lumped-PPE component result; positive
  phase-separated pressure-jump evidence belongs to integrated Chapter 13
  validation, not to a missing U6 primitive.
- Source tests should be kept when they encode a live mathematical contract
  and removed only when they entangle an obsolete or non-isolating failure
  mechanism.

## Paper And Meta Lessons

Narrative work during the same period exposed a documentation invariant:
reader-facing names must track the current mathematical contract.  Examples
include describing V10 as NS-non-coupled fixed-grid CLS advection rather than
"no interface tracking", keeping V7 values separated between historical
controls and current verdicts, and making appendix filenames encode visible
printed hierarchy.

The meta-prompt v8 candidate adds a parallel operating lesson:

- Skill Capsules provide a just-in-time procedural layer between terse operation
  IDs and full kernel references.
- Token telemetry makes rule bloat measurable instead of anecdotal.
- Adaptive condensation needs explicit lost-context tests and compression
  failure logs.
- Tool/web/MCP outputs stay untrusted unless promoted by local SSoT.
- Multi-agent work is valuable only for independent breadth; delegation
  overhead is itself a failure mode.

## Retrieval Checklist

For projection or rising-bubble failures, start with `WIKI-T-076`,
`WIKI-E-032`, and this page.  For capillary wave, static droplet, or pressure
history failures, add `WIKI-X-039` and `WIKI-T-077`.  For V7/V10 interpretation
or paper wording, inspect the two CHK-RA-CH13 artifacts before changing text or
parameters.  For test failures after stack movement, apply the retention audit
rule: preserve live contracts, retire stale non-isolating tests.

## Open Fronts

1. Capillary-jump/projection time discretization that can make V7 a true
   coupled-stack second-order test.
2. Adaptive or moving-grid geometry path for V10 fixed-grid shape limits.
3. Discrete capillary energy instrumentation for ch14 benchmarks.
4. Long-time validation of projection-native affine pressure history on static
   and oscillating droplets.
5. Post-deploy telemetry for the v8 prompt system after real Codex/Claude runs.
