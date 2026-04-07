---
ref_id: WIKI-P-002
title: "Accuracy Summary: Component-Level Precision Map"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/09d_pressure_summary.tex
    git_hash: 7328bf1
    description: "Definitive accuracy summary table (tab:accuracy_summary)"
  - path: paper/sections/06_time_integration.tex
    git_hash: 7328bf1
    description: "Time accuracy table (sec:time_accuracy_table)"
  - path: paper/sections/07_advection.tex
    git_hash: 7328bf1
    description: "Scheme roles table (box:scheme_roles)"
consumers:
  - domain: L
    usage: "Implementation must match stated accuracy orders"
  - domain: E
    usage: "Convergence tests validate against these expected rates"
  - domain: A
    usage: "Authoritative accuracy reference for paper claims"
  - domain: T
    usage: "Theory derivations must be consistent with stated orders"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-003]]"
  - "[[WIKI-T-005]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Authoritative Accuracy Table

Source: tab:accuracy_summary in 09d_pressure_summary.tex (S9 chapter-end). This is the definitive version; earlier partial tables in S6 and S7 are subsets.

| Component | Method | Spatial Order | Temporal Order |
|-----------|--------|:------------:|:--------------:|
| CLS advection | DCCD + TVD-RK3 | O(h^5)* | O(dt^3) |
| Curvature (kappa) | CCD | O(h^6) | — |
| PPE discretization | DC (k=1) | O(h^2)** | — |
| PPE pressure gradient | CCD (BF) | O(h^6) | — |
| NS viscous (diagonal) | CCD + CN | O(h^6)/O(h^2)*** | O(dt^2) |
| NS convection | CCD + AB2 | O(h^6) | O(dt^2) |
| Projection splitting | IPC | — | O(dt^2) |
| HFE (appendix) | Hermite interpolation | O(h^6) | — |
| **Overall spatial** | **(CSF rate-limiter)** | **O(h^2)** | — |
| **Overall temporal** | **(AB2+IPC rate-limiter)** | — | **O(dt^2)** |

### Footnotes

\* CLS advection: local truncation O(h^6) from CCD, but DCCD filter adds O(eps_d h^2) = O(0.05 h^2). Global integral mass error estimate is O(h^5).

\** DC k=1 gives effective O(h^2) (FD-equivalent). k>=3 achieves O(h^6). Current implementation uses k=1 because CSF O(h^2) is the bottleneck.

\*** ADI implicit sweep uses 2nd-order FD O(h^2) for Thomas compatibility; cross-derivative terms use CCD O(h^6). For Re>>1, viscous contribution O(h^2/Re) falls at or below CSF model error O(h^2).

## Accuracy Table Locations (3 instances)

| Location | Section | Content | Scope |
|----------|---------|---------|-------|
| sec:time_accuracy_table | S6 | Time orders per component | Temporal only |
| box:scheme_roles | S7 | Spatial scheme assignments per component | Spatial only |
| **tab:accuracy_summary** | **S9d** | **Full spatial + temporal table** | **Definitive** |

The S6 and S7 tables are partial. Any discrepancy should be resolved in favor of tab:accuracy_summary.

## Known Gap

The accuracy table does NOT note the variable-density PPE condition number limitation: kappa(L_h) = O(rho_l/rho_g / h^2). At rho_l/rho_g >= 10, the PPE solver may diverge. This limitation is documented in sec:ppe_condition_number (09c_ppe_bc.tex) but absent from the summary table.

## Rate-Limiting Analysis

The overall system is O(h^2) spatially due to CSF surface tension model. Upgrading to GFM would:
1. Remove the O(h^2) CSF bottleneck
2. Make DC k>=3 worthwhile (PPE: O(h^2) -> O(h^6))
3. Elevate overall spatial accuracy to O(h^5) (DCCD filter limit) or O(h^6) (without filter)
