---
ref_id: WIKI-X-041
title: "Curated Wiki Retrieval Map: Active Contracts and Retired Knowledge"
domain: cross-domain
status: ACTIVE
superseded_by: null
tags: [wiki_curation, retrieval_map, active_contracts, retired_knowledge]
sources:
  - path: docs/wiki/INDEX.md
    description: "Wiki inventory before CHK-RA-WIKI-CURATION-001 curation"
  - path: docs/02_ACTIVE_LEDGER.md
    description: "Current ResearchArchitect ledger through 2026-05-06"
  - path: paper/sections/06b_advection.tex
    description: "Current CLS advection contract: FCCD face-flux transport"
  - path: paper/sections/11_full_algorithm.tex
    description: "Current one-step algorithm and projection-native face closure"
  - path: paper/sections/13f_error_budget.tex
    description: "Current verification reading for V1/V6/V7/V9/V10"
  - path: docs/wiki/cross-domain/WIKI-X-040.md
    description: "Recent research insight digest and stale-contract list"
  - path: docs/wiki/theory/WIKI-T-160.md
    description: "Fully discrete reinit-aware capillary Hodge reference and defect-ledger lesson"
  - path: docs/wiki/theory/WIKI-T-161.md
    description: "Retired fixed-stratum variational reinit candidate; negative knowledge only"
  - path: docs/wiki/theory/WIKI-T-162.md
    description: "Closed-interface capillary discretization policy after variational/Riesz rigor pass"
depends_on:
  - "[[WIKI-X-037]]"
  - "[[WIKI-X-040]]"
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-088]]"
  - "[[WIKI-T-101]]"
  - "[[WIKI-T-129]]"
  - "[[WIKI-T-152]]"
  - "[[WIKI-T-153]]"
  - "[[WIKI-T-154]]"
  - "[[WIKI-T-158]]"
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-160]]"
  - "[[WIKI-T-161]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-157]]"
  - "[[WIKI-E-062]]"
  - "[[WIKI-X-045]]"
  - "[[WIKI-X-046]]"
consumers:
  - domain: theory
    usage: "Start here before using older theory cards for derivations"
  - domain: experiment
    usage: "Separate preserved negative evidence from obsolete acceptance bounds"
  - domain: code
    usage: "Route implementation work to live interface, projection, and GPU contracts"
  - domain: paper
    usage: "Keep wiki retrieval synchronized with current paper terminology"
compiled_by: ResearchArchitect
compiled_at: 2026-05-06
---

# Curated Wiki Retrieval Map

## Purpose

This card is the active retrieval gate for `docs/wiki`.  It does not delete
historical evidence; it prevents old design memos from being read as current
algorithm policy.

## Active Contract Stack

| Topic | Use first | Active reading |
|---|---|---|
| Projection closure | [[WIKI-T-080]], [[WIKI-X-040]] | PPE, corrector, pressure history, and diagnostics share face-space objects. |
| CLS transport | [[WIKI-T-156]], [[WIKI-T-088]], [[WIKI-T-101]] | Current paper contract is FCCD face-flux CLS transport with projected face velocity. |
| Capillary jump | [[WIKI-X-039]], [[WIKI-X-040]] | Use oriented affine interface stress and face acceleration, not a regular pressure field. |
| PPE residual | [[WIKI-T-152]], [[WIKI-E-059]] | Production projection accuracy is the high-order residual contract, not fixed DC iteration count. |
| Pressure representative | [[WIKI-T-154]], [[WIKI-T-158]], [[WIKI-E-060]], [[WIKI-E-062]] | Raw interface-band pressure is diagnostic; read Hodge representatives and face cochains, never masked-band substitutes. |
| Reinit-aware capillary Hodge | [[WIKI-T-162]], [[WIKI-T-159]], [[WIKI-T-160]], [[WIKI-T-155]], [[WIKI-T-157]], [[WIKI-T-161]] | Build capillary work from the labelled physical transport endpoint; for implementation use [[WIKI-T-162]] first because it gives the trace geometry, Riesz pullback, component-reaction matrix, augmented weighted projection, and the current `component_hodge_augmented` one-component implementation slice; read [[WIKI-T-161]] only as the retired fixed-stratum candidate, not as a current route. |
| ALE/remap energy | [[WIKI-T-162]], [[WIKI-T-160]], [[WIKI-T-155]], [[WIKI-T-157]], [[WIKI-T-159]], [[WIKI-T-161]] | Variational curvature work needs shared pressure-work pairing, labelled transport/reinit endpoints, named reinit residuals/defects, and step-local energy accounting; [[WIKI-T-162]] is the current closed-interface discretization policy, while [[WIKI-T-161]] is negative knowledge about an abandoned retraction surface. |
| Paper/wiki split | [[WIKI-X-046]], [[WIKI-E-061]] | Put successful contracts in the paper; preserve failed controls and trial variants in the wiki. |
| Negative shortcuts | [[WIKI-X-045]] | Damping/CFL/smoothing/caps/hyperviscosity are retained as rejected detours, not paper success claims. |
| Verification reading | [[WIKI-E-040]], [[WIKI-X-040]] | V-series labels encode what was certified; stale FFT/CCD-LU/CN readings are historical only. |
| Density-ratio evidence | [[WIKI-E-053]], [[WIKI-X-040]], paper §13 | Current §14 stack evidence reaches density ratio 833 in V6; older nonuniform-grid gates are not global limits. |
| Code interfaces | [[WIKI-L-009]], [[WIKI-L-035]], [[WIKI-L-036]] | Interface paths live in concrete subpackages; capillary coupling is projection-native and GPU-aware. |

## Retired From Active Retrieval

The following cards remain as provenance but must not be used as current
recommendations without the curation note at the top of each page.

| Card | Retired reading | Replacement |
|---|---|---|
| [[WIKI-X-014]] | `rho <= 20` as a global two-phase density-ratio limit; `legacy` reprojection fallback as recommended operation. | Current projection-native / affine-history §14 stack evidence summarized in [[WIKI-X-040]]. |
| [[WIKI-X-020]] | Ridge-Eikonal -> GFM/HFE -> IIM chain with Approach-B FD Hessian and older jump decomposition as active pressure path. | Oriented affine jump and projection-native face-space pressure closure in [[WIKI-X-039]] and [[WIKI-X-040]]. |
| [[WIKI-X-032]] | Eight-phase WENO5/CN algorithm as the current full step. | Paper §11 one-step algorithm and [[WIKI-T-101]]. |
| [[WIKI-T-013]] | DCCD as the current preferred CLS transport. | FCCD face-flux CLS transport in paper §6 and §11; WENO5 remains a reference comparator only. |
| [[WIKI-T-058]] | FD Hessian fallback as an admissible production path. | Direct physical-space nonuniform CCD/FCCD derivative contracts; FD result is a historical CHK-159 probe only. |
| [[WIKI-L-001]] | Seven-step DCCD/Rhie-Chow/DC-ADI loop as implementation contract. | Paper §11 one-step algorithm, [[WIKI-T-101]], and projection-native face-space routing in [[WIKI-X-040]]. |
| [[WIKI-X-001]] | DCCD parameter modes as cross-algorithm policy. | Retain only pressure-filter prohibition and historical filter taxonomy; active transport/PPE routes through [[WIKI-X-041]] and [[WIKI-T-101]]. |
| [[WIKI-X-005]] | DC+LU/DCCD/Rhie-Chow verification architecture and old density-ratio limits. | Current verification reading in [[WIKI-X-040]] and V-series experiment cards. |
| [[WIKI-X-011]] | FFT-PPE single-phase divergence threshold as a transferable two-phase criterion. | V1/current verification reading in [[WIKI-E-050]] and [[WIKI-X-040]]. |
| [[WIKI-X-022]] | Ten-method R-1.5/R-1 role map as current full-stack architecture. | Projection-native affine jump and pressure-history face acceleration in [[WIKI-X-039]] and [[WIKI-X-040]]. |
| [[WIKI-L-028]] | IIM jump decomposition plus ADI defect correction as a selectable PPE fallback. | GPU-resident Krylov/preconditioner roadmap in [[WIKI-L-026]] and algebra-preserving GPU policy in [[WIKI-L-038]]. |
| [[WIKI-P-003]], [[WIKI-P-005]] | Early paper problem/verification maps with DCCD/CN/CSF as the organizing story. | Paper traceability cards [[WIKI-P-015]] and [[WIKI-P-016]]. |
| [[WIKI-X-025]] | AB2/CN/semi-implicit-ST Level-2 design as production default. | Startup/projection consistency in [[WIKI-T-147]] and current digest [[WIKI-X-040]]. |
| [[WIKI-X-007]] | Scheme-specific CFL constants as proof of capillary benchmark validity. | Capillary energy/mode and resolution contracts in [[WIKI-E-055]] and [[WIKI-E-056]]. |
| [[WIKI-P-001]], [[WIKI-P-002]], [[WIKI-P-004]], [[WIKI-P-006]] | Early paper narrative, accuracy, and review snapshots as current status. | Current chapter/appendix traceability in [[WIKI-P-015]] and [[WIKI-P-016]]. |
| [[WIKI-X-037]] | Previous ResearchArchitect wiki atlas as the active retrieval map. | This card, [[WIKI-X-041]], plus recent digest [[WIKI-X-040]]. |
| [[WIKI-L-008]], [[WIKI-L-014]], [[WIKI-L-015]], [[WIKI-L-022]] | Old code/module maps as current file-path or implementation policy. | Current code interface map [[WIKI-L-009]], backend boundary [[WIKI-L-037]], and projection-native code cards [[WIKI-L-035]]/[[WIKI-L-036]]. |
| [[WIKI-L-013]], [[WIKI-L-016]] | April SOLID score and CN strategy snapshot as current code authority. | Current code routing via [[WIKI-L-009]] and timing/projection contracts via [[WIKI-T-147]]/[[WIKI-X-038]]. |

## Retained Negative Knowledge

Negative results are not removed when they isolate a real failure mechanism.
They are retained with a bounded reading:

- old FFT proxy claims do not transfer to V1;
- old CCD-LU/CN component interpretations do not transfer to U2/U8;
- the CCD Kronecker+LU ch11-only restriction in [[WIKI-X-009]] remains valid,
  but its older solver list and dependency on retired verification maps are
  historical;
- V7, V10-a, V10-b, and N64 static droplet failures are structural-contract
  evidence, not tuning targets;
- N64 oscillating droplet pressure artifacts must separate projection
  underconvergence, face cochains, scalar representatives, and curvature theory;
- static-droplet pressure output must be Hodge-reconstructed from saved face
  cochains; masked interface-band plots are retired;
- reinit-induced deformation under zero velocity is projection defect unless
  [[WIKI-T-160]] trace, surface-energy, and volume identity gates pass;
- the fixed-stratum trace-preserving entropy-dual retraction in [[WIKI-T-161]]
  is retained as a failed candidate after ch14 N=32, T=10 abnormal-shape
  validation; do not implement its YAML surface from this card;
- the current implementation route for closed-interface capillarity is
  [[WIKI-T-162]]: first use `component_hodge_augmented`, then finish the
  trace stratum, `s=-M_f^{-1}T^TdS`, component reaction columns
  `B=M_f^{-1}T^TdV`, and weighted projection through `X=[A G B]`;
- N64 static-grid, `fccdface`, `transportvar`, phase/density variants, and
  other non-DC probes remain useful controls only with their acceptance gates;
- rejected shortcuts such as damping, smoothing, curvature caps, hyperviscosity,
  and blind CFL reduction remain negative knowledge, not solver fixes;
- pre-projection-native nonuniform density-ratio limits remain experiment
  history, not the current solver envelope.

## Index Rule

`docs/wiki/INDEX.md` lists all retained cards, including retired ones.  For
new research or implementation work, start from this card or [[WIKI-X-040]]
before following older wiki links.
