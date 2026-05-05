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
    description: "Current ResearchArchitect ledger through 2026-05-05"
  - path: paper/sections/06b_advection.tex
    description: "Current CLS advection contract: FCCD face-flux transport"
  - path: paper/sections/11_full_algorithm.tex
    description: "Current one-step algorithm and projection-native face closure"
  - path: paper/sections/13f_error_budget.tex
    description: "Current verification reading for V1/V6/V7/V9/V10"
  - path: docs/wiki/cross-domain/WIKI-X-040.md
    description: "Recent research insight digest and stale-contract list"
depends_on:
  - "[[WIKI-X-037]]"
  - "[[WIKI-X-040]]"
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-088]]"
  - "[[WIKI-T-101]]"
  - "[[WIKI-T-129]]"
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
compiled_at: 2026-05-05
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
| CLS transport | [[WIKI-T-088]], [[WIKI-T-101]], paper §6/§11 | Current paper contract is FCCD face-flux CLS transport with projected face velocity. |
| Capillary jump | [[WIKI-X-039]], [[WIKI-X-040]] | Use oriented affine interface stress and face acceleration, not a regular pressure field. |
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

## Retained Negative Knowledge

Negative results are not removed when they isolate a real failure mechanism.
They are retained with a bounded reading:

- old FFT proxy claims do not transfer to V1;
- old CCD-LU/CN component interpretations do not transfer to U2/U8;
- V7, V10-a, V10-b, and N64 static droplet failures are structural-contract
  evidence, not tuning targets;
- pre-projection-native nonuniform density-ratio limits remain experiment
  history, not the current solver envelope.

## Index Rule

`docs/wiki/INDEX.md` lists all retained cards, including retired ones.  For
new research or implementation work, start from this card or [[WIKI-X-040]]
before following older wiki links.
