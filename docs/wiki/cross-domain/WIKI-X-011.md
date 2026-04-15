---
ref_id: WIKI-X-011
title: "Divergence Criterion Gap: Single-Phase FFT-PPE (1e-10) vs Two-Phase CSF (1e-2)"
domain: B
status: ACTIVE
superseded_by: null
sources:
  - path: "paper/sections/12_verification.tex"
  - path: "paper/sections/12e_coupling.tex"
  - path: "paper/sections/12c_time_accuracy.tex"
depends_on:
  - "[[WIKI-T-006]]"
  - "[[WIKI-X-005]]"
compiled_by: ResearchArchitect
compiled_at: 2026-04-16
---

# Divergence Criterion Gap: Single-Phase (1e-10) vs Two-Phase (1e-2)

## Observation

The chapter 12 verification table sets `||∇·u||_∞ < 1e-10` as the
incompressibility criterion, verified by single-phase Taylor-Green vortex
with FFT direct-solve PPE (periodic, constant-density).

In the two-phase static droplet test (§12e), `||∇·u||_∞` reaches
7.9e-3 to 3.3e-2 (increasing with N), yet the test is judged "stable".

This 8-order-of-magnitude gap arises from fundamentally different
solver configurations.

## Root Causes of Two-Phase Divergence

| Factor | Mechanism | Typical magnitude |
|--------|-----------|-------------------|
| CSF source term | δ-function regularization introduces non-solenoidal body force | O(σ κ δ_ε) |
| Variable-density PPE | ∇·(ρ⁻¹ ∇p) solved iteratively, not exactly | Truncation O(h²) |
| Non-incremental projection | Omitted ∇p^n term removes interface pressure-jump history | O(Δt) |
| Interface-crossing density | Sharp ρ-ratio across interface degrades PPE condition number | Amplifies residual |

## Resolution in Paper

The verification table now:
1. Labels the criterion as "非圧縮条件（単相）"
2. Adds footnote: FFT-PPE single-phase basis; two-phase CSF+variable-ρ PPE
   produces O(1e-2) divergence
3. §12e's stability judgment is based on bounded parasitic currents and
   accurate Laplace pressure, not on the single-phase divergence criterion

## Implications

- Two-phase ∇·u is not a direct measure of solver quality; it reflects
  CSF model fidelity and projection splitting error.
- A separate two-phase divergence criterion (e.g., weighted divergence
  normalized by interface source magnitude) would be more informative
  but is not standard practice in the literature.
- The current approach (parasitic current + Laplace pressure accuracy)
  is the accepted proxy for two-phase incompressibility assessment.

## Cross-References

- [[WIKI-T-006]]: One-fluid formulation and CSF model
- [[WIKI-X-005]]: Verification hierarchy architecture
