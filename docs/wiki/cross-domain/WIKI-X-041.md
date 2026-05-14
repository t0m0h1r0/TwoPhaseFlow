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
  - path: docs/wiki/theory/WIKI-T-163.md
    description: "Survey of reinitialization-free/reinitialization-minimized LS/CLS candidate routes"
  - path: docs/wiki/theory/WIKI-T-164.md
    description: "Conservative common-flux energy ledger for SI water-air rising-bubble blow-up remedy"
  - path: docs/wiki/theory/WIKI-T-165.md
    description: "Variational gravity Hodge projection for gravity/buoyancy as a transport-adjoint force covector"
  - path: docs/wiki/theory/WIKI-T-166.md
    description: "Boundary-constrained face Hodge projection for no-slip preserved face states"
  - path: docs/wiki/theory/WIKI-T-167.md
    description: "Reference additive KKT contract and rank-probe diagnostics for boundary-constrained face Hodge"
  - path: docs/wiki/theory/WIKI-T-168.md
    description: "Active constrained face-state space reformulation for wall-bounded common-flux flow"
  - path: docs/wiki/cross-domain/WIKI-X-048.md
    description: "Ch14 capillary Hodge trial ledger for knowledge, failures, and falsified routes"
  - path: docs/wiki/paper/WIKI-P-018.md
    description: "Recent Chapters 1-13 paper-theory contract digest"
  - path: docs/wiki/theory/WIKI-T-169.md
    description: "Geometric cell-fraction / AO-Fast theory and YAML state-space contract"
  - path: docs/wiki/experiment/WIKI-E-063.md
    description: "U12/V11 AO-Fast capillary split gate results"
  - path: docs/wiki/cross-domain/WIKI-X-049.md
    description: "AO-Fast capillary admission and Chapter 14 YAML boundary"
  - path: docs/wiki/cross-domain/WIKI-X-050.md
    description: "Theory-first implementation debug priority for nonuniform metrics and grid rebuilds"
  - path: docs/wiki/cross-domain/WIKI-X-051.md
    description: "Theory-first RCA and countermeasure protocol"
  - path: docs/wiki/cross-domain/WIKI-X-052.md
    description: "Ch14 AO-Fast capillary RCA trial ledger"
  - path: docs/wiki/theory/WIKI-T-172.md
    description: "AO-Fast moving-grid face-cochain and pressure-history contract"
  - path: docs/wiki/code/WIKI-L-045.md
    description: "AO-Fast GPU efficiency bottleneck after finite-stratum fusion"
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
  - "[[WIKI-T-163]]"
  - "[[WIKI-T-164]]"
  - "[[WIKI-T-165]]"
  - "[[WIKI-T-166]]"
  - "[[WIKI-T-167]]"
  - "[[WIKI-T-168]]"
  - "[[WIKI-T-169]]"
  - "[[WIKI-X-048]]"
  - "[[WIKI-P-018]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-157]]"
  - "[[WIKI-E-062]]"
  - "[[WIKI-E-063]]"
  - "[[WIKI-X-045]]"
  - "[[WIKI-X-046]]"
  - "[[WIKI-X-049]]"
  - "[[WIKI-X-050]]"
  - "[[WIKI-X-051]]"
  - "[[WIKI-X-052]]"
  - "[[WIKI-T-171]]"
  - "[[WIKI-T-172]]"
  - "[[WIKI-L-045]]"
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
compiled_at: 2026-05-14
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
| Rising-bubble conservative remedy | [[WIKI-T-164]], [[WIKI-T-165]], [[WIKI-T-166]], [[WIKI-T-168]], [[WIKI-T-167]] | Treat SI water-air rising-bubble blow-up as an unaccounted energy injection into an interface-band high-k mode.  The active remedy is conservative common-flux transport of `q,m,p`, conservative reinit/remap or fail-close, transported-mass pressure projection, variational capillary/gravity work, dissipative viscosity, face-cochain pressure history, boundary-constrained face state space, and per-step energy/high-k certificates.  After the pressure-history-only check failed to remove the blow-up, read [[WIKI-T-165]] for gravity as `-T_m^T d Phi_g`; after the wall-localized face/nodal mismatch RCA, read [[WIKI-T-166]] for the target `D_h f=0`, `C_w f=B_h R_h f=0`, then read [[WIKI-T-168]] as the active production direction: build `F_w=ker C_w` first and solve pressure through `D_h P_w G_A`.  Use [[WIKI-T-167]] only as the additive KKT/reference rank-probe contract.  Do not use DCCD/UCCD as a silent velocity damper. |
| Capillary jump | [[WIKI-X-039]], [[WIKI-X-040]] | Use oriented affine interface stress and face acceleration, not a regular pressure field. |
| PPE residual | [[WIKI-T-152]], [[WIKI-E-059]] | Production projection accuracy is the high-order residual contract, not fixed DC iteration count. |
| Pressure representative | [[WIKI-T-154]], [[WIKI-T-158]], [[WIKI-E-060]], [[WIKI-E-062]] | Raw interface-band pressure is diagnostic; read Hodge representatives and face cochains, never masked-band substitutes. |
| Reinit-aware capillary Hodge | [[WIKI-T-162]], [[WIKI-X-048]], [[WIKI-T-159]], [[WIKI-T-160]], [[WIKI-T-155]], [[WIKI-T-157]], [[WIKI-T-161]], [[WIKI-T-163]] | Build capillary work from the labelled physical transport endpoint; for the current solver use [[WIKI-T-162]] first because it fixes the risk-closed conservative theorem: endpoint-closed `q_c=q_T`, pressure-adjoint active `G_A=pressure_fluxes` range, component-constrained saddle projection `h=s-G_Ap-Bmu`, GPU-native P1 geometry, reinit endpoint ledger, CCD/FCCD/UCCD coupling contract, and fail-close gates.  Read [[WIKI-X-048]] before proposing a new fix because it records the zero-drive theorem, `none`/component-Hodge limits, reinit contamination, pressure-representative RCA, trace-Riesz endpoint mismatch, static-critical residual, and falsified shortcut routes.  Treat endpoint/material time-level mismatch, corrector cochain loss, host-loop geometry, and trace aliasing as implementation blockers.  Treat trace-vertex `C_K` as future trace-primary redesign work only; read [[WIKI-T-163]] for reinit-free/profile-control candidate routes and [[WIKI-T-161]] only as the retired fixed-stratum candidate, not as a current route. |
| ALE/remap energy | [[WIKI-T-162]], [[WIKI-T-160]], [[WIKI-T-155]], [[WIKI-T-157]], [[WIKI-T-159]], [[WIKI-T-161]], [[WIKI-T-163]] | Variational curvature work needs shared pressure-work pairing, labelled transport/reinit endpoints, named reinit residuals/defects, and step-local energy accounting; [[WIKI-T-162]] is the current closed-interface discretization policy, [[WIKI-T-163]] is the current reinit-free survey, and [[WIKI-T-161]] is negative knowledge about an abandoned retraction surface. |
| Chapters 1-13 paper contract | [[WIKI-P-018]], [[WIKI-P-015]], [[WIKI-P-014]] | Current paper edits should preserve the failure-mode to contract to discretization to algorithm to V-series trace.  The standard route is per-variable: FCCD face-flux CLS transport, UCCD6 interior momentum, pressure-jump PPE/HFE/DC, capillary virtual-work face cochain, pressure-adjoint representative, and integrated V6/V7/V9 evidence. |
| AO-Fast capillary admission | [[WIKI-X-052]], [[WIKI-T-172]], [[WIKI-X-049]], [[WIKI-T-169]], [[WIKI-E-063]] | Treat AO-Fast `geometric_cell_fraction` as a separate state-space candidate, not as an implicit Chapter 14 fallback.  Full pressure-image splitting can cancel non-static capillary drive exactly; U12/V11 therefore require a pressure-reaction subspace `R_p(q_T)` and residual-certified `r_sigma-Pi^{M_f}_{R_p}r_sigma`.  For moving-grid capillary runs, transport the projected face cochain across rebuild and keep pressure history in the smooth coordinate; do not infer correctness from static/no-rebuild survival. |
| Theory-first implementation debug | [[WIKI-X-051]], [[WIKI-X-052]], [[WIKI-X-050]], [[WIKI-T-094]], [[WIKI-T-096]], [[WIKI-T-135]], [[WIKI-T-171]], [[WIKI-T-172]] | When an implementation test violates a proven theory, first suspect nonuniform metric contracts, interface-tracking grid rebuild contracts, pressure-history coordinates, and face-cochain transport. Use uniform-grid, static-grid/no-rebuild, first-rebuild, `L != 1` metric, pre/post-remap conservation, face-Hodge, and cache-invalidation controls before tuning CFL, damping, tolerances, or solver iterations. |
| GPU optimization | [[WIKI-L-043]], [[WIKI-L-044]], [[WIKI-L-045]], [[WIKI-T-171]] | First eliminate hidden D2H/H2D transfer boundaries; after finite-stratum fusion and explicit sparse solve-plan reuse, remaining low utilization on the AO-Fast capillary route points to fixed-loop geometry compatibility and small-launch orchestration. Optimize by chunked fail-close convergence, exact fused finite-stratum kernels, explicit scratch/prepared flows, and batched scalar packets. Do not disable nonuniform grids, rebuilds, active geometry, or convergence gates to improve utilization. |
| Paper/wiki split | [[WIKI-X-046]], [[WIKI-X-048]], [[WIKI-E-061]] | Put successful contracts in the paper; preserve failed controls, falsified hypotheses, and trial variants in the wiki. |
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
- the ch14 capillary Hodge trial sequence in [[WIKI-X-048]] is the canonical
  place to check already-falsified zero-drive, raw-`none`, component-only,
  pressure-representative, trace-endpoint, and static-critical explanations
  before starting another remedy loop;
- the additive boundary-Hodge KKT in [[WIKI-T-167]] is retained as a diagnostic
  reference after the rank probe, but active production work should start from
  the constrained face-state space in [[WIKI-T-168]]; wall-only post-projection,
  nodal clamping, generic `D_h^T`, dense CPU KKT, and penalty/damping routes
  remain negative knowledge;
- pre-projection-native nonuniform density-ratio limits remain experiment
  history, not the current solver envelope.
- AO-Fast non-static zero-drive packets are retained as fail-close evidence;
  do not reinterpret them as CFL failures or silently repair them by PCG, DC,
  dense direct AO, component-Hodge, or host-controlled GPU fallback.
- the old V11 common-flux admissibility experiment is stale for AO-Fast
  capillary admission; use [[WIKI-E-063]] instead.

## Index Rule

`docs/wiki/INDEX.md` lists all retained cards, including retired ones.  For
new research or implementation work, start from this card or [[WIKI-X-040]]
before following older wiki links.
