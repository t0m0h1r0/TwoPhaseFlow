---
ref_id: WIKI-X-004
title: "Pressure Instability in High-Order Two-Phase Flow: Root Causes and Mitigation Survey"
domain: X
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/survey_pressure_instability_twophase.md
    git_hash: e62cd50
    description: "Survey: rising-bubble divergence diagnosis, capillary CFL violation, force-balance breakdown"
consumers:
  - domain: L
    usage: "Timestep controller, solver selection, stability diagnostics"
  - domain: A
    usage: "§8 stability discussion, §13 future work"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-014]]"
  - "[[WIKI-T-018]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## Diagnosis: Rising Bubble Divergence (t ≈ 0.059)

Two root causes identified:

### 1. Capillary CFL Violation

Timestep was ~4× over capillary CFL limit. Δt_σ ∝ h^{3/2} becomes severe at fine grids. **Fix: enforce capillary CFL (immediate).**

### 2. Force-Balance Breakdown on Moving Interfaces

Static droplet is stable because interface doesn't move → balanced-force condition holds exactly. Moving interfaces accumulate CSF/pressure imbalance each step regardless of spatial order (Popinet 2009).

**Fundamental issue:** CSF body force σκ∇ψ is evaluated at time n, but interface has moved by time n+1. The temporal mismatch creates O(Δt) force error that drives parasitic currents on moving interfaces.

## Literature Mitigation Strategies

| Strategy | Effect | Status |
|----------|--------|--------|
| Capillary CFL enforcement | Prevents explicit instability | **Implemented** |
| GFM with explicit [p]=σκ | Eliminates CSF model error | GFM+CCD fails (operator indefinite) |
| HFE (Hermite Field Extension) | Smooths interface-crossing fields | **Implemented** (see [[WIKI-T-018]]) |
| Semi-implicit surface tension | Relaxes capillary CFL | Not implemented (see [[WIKI-T-023]]) |
| Split-PPE (per-phase) | Avoids variable-density PPE | Future path |

## Key Insight

High spatial order (CCD O(h⁶)) does not solve the fundamental CSF accuracy bottleneck O(ε²) ≈ O(h²). The rate-limiting error is the **model** (regularized delta), not the **discretization**. This is why balanced-force "balances" discretization error to O(h⁶) but cannot eliminate CSF model error.
