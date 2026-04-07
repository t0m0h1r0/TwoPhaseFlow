---
ref_id: WIKI-T-009
title: "CSF Model Error: The O(h^2) Accuracy Bottleneck"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/02b_surface_tension.tex
    git_hash: 7328bf1
    description: "CSF model definition, O(eps^2) error, Balanced-Force preview"
  - path: paper/sections/01_introduction.tex
    git_hash: 7328bf1
    description: "Four failure modes, spurious current mechanism"
  - path: paper/sections/09d_pressure_summary.tex
    git_hash: 7328bf1
    description: "CSF as overall spatial rate-limiter"
consumers:
  - domain: L
    usage: "ns_terms/surface_tension.py implements CSF; accuracy bounded by O(h^2)"
  - domain: T
    usage: "CSF error justifies DC k=1 (no benefit from O(h^6) PPE)"
  - domain: E
    usage: "Parasitic current benchmarks measure CSF-limited floor"
  - domain: A
    usage: "Rate-limiting argument is central to paper's accuracy analysis"
depends_on:
  - "[[WIKI-T-006]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## CSF Model (Brackbill et al. 1992)

Replaces singular surface force sigma*kappa*n_hat*delta_s with volume force:

f_sigma = sigma * kappa * grad(psi)

where grad(psi) = delta_eps(phi) * grad(phi) is a smoothed delta function of width ~2*eps.

## Model Error

The CSF approximation introduces O(eps^2) ≈ O(h^2) error because:
- The delta function is spread over width eps ≈ C_eps * h
- Integration of the spread force over the transition layer produces O(eps^2) residual vs the sharp jump

This O(h^2) error is **fundamental to the CSF model**, independent of spatial discretization accuracy. Even with CCD O(h^6) derivatives, the overall spatial accuracy is limited to O(h^2).

## Impact on System Design

The CSF bottleneck has cascading design consequences:

| Component | Achievable accuracy | Actual accuracy (CSF-limited) | Design choice |
|-----------|-------------------|-------------------------------|---------------|
| CCD differentiation | O(h^6) | O(h^6) (no CSF impact) | Full CCD |
| Curvature | O(h^6) | O(h^6) (no CSF impact) | Full CCD |
| PPE (DC solver) | O(h^6) at k>=3 | **O(h^2) sufficient** | DC k=1 (saves iterations) |
| Overall spatial | — | **O(h^2)** (CSF floor) | Accept; plan GFM upgrade |

**Key insight**: DC k=1 (FD-equivalent, O(h^2)) is the rational choice because additional DC iterations to reach O(h^6) provide no observable improvement when CSF limits everything to O(h^2).

## Spurious Current Mechanism

At a stationary interface, equilibrium requires: grad(p) = sigma*kappa*grad(psi).

If discrete operators differ (e.g., FD for grad(p), CCD for kappa*grad(psi)):
- Residual force: O(h^2) from operator mismatch
- This drives non-physical velocity (spurious/parasitic currents)
- Positive feedback: velocity → advection error → interface distortion → more spurious force

**Balanced-Force solution**: Use identical CCD operator for both terms → mismatch reduced to O(h^6), leaving only the CSF model error O(h^2) as the floor. See [[WIKI-T-004]].

## Future: GFM Upgrade Path

Ghost Fluid Method (GFM) replaces CSF by:
- Applying sharp jump conditions directly at interface
- Eliminating the O(eps^2) spreading error
- Reducing surface tension error to O(h^p) where p depends on interface reconstruction order

With GFM, the CCD O(h^6) infrastructure becomes fully exploitable:
- DC k>=3 becomes worthwhile
- Overall spatial accuracy rises to O(h^5) (DCCD filter limit) or O(h^6)
- See [[WIKI-P-002]] for the complete accuracy table
