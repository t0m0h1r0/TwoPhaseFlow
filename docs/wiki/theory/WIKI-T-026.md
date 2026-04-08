---
ref_id: WIKI-T-026
title: "HFE Applicability Scope: Harm Mechanism on Smooth Fields and Valid Use Cases"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appendix_verification_details.tex
    git_hash: 93a1b79
    description: "HFE ON/OFF comparison on smoothed Heaviside pressure — 4-digit parasitic current increase"
  - path: paper/sections/08c_pressure_filter.tex
    git_hash: 93a1b79
    description: "Prohibition of direct pressure field filtering; divergence-free constraint"
  - path: paper/sections/09b2_split_ppe.tex
    git_hash: 93a1b79
    description: "Split-phase PPE formulation where HFE is essential"
  - path: paper/sections/12d_coupling.tex
    git_hash: 93a1b79
    description: "HFE scope statement with experimental evidence"
consumers:
  - domain: L
    usage: "HFE module guard logic — when to enable/disable HFE in pipeline"
  - domain: A
    usage: "§8c (pressure filter prohibition), §9.3 (split-PPE), §12d (coupling), App E.2 (scope)"
  - domain: E
    usage: "Static droplet HFE ON/OFF ablation (appendix_verification_details.tex)"
depends_on:
  - "[[WIKI-T-018]]"
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-005]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-09
---

## Core Principle

HFE (Hermite Field Extension) overwrites target-phase grid values with source-phase values via closest-point Hermite interpolation. This is beneficial **only when the field has a genuine interface discontinuity**. Applying HFE to an already-smooth field **creates** an artificial discontinuity that did not exist.

## Harm Mechanism (3 Steps)

### Step 1: Smoothed Heaviside produces a smooth pressure field

In the monolithic (smoothed Heaviside) solver, density is regularized:

    ρ(x) = ρ_g + (ρ_l − ρ_g) H_ε(φ(x)),   ε = 1.5h

The PPE ∇·(1/ρ ∇p) = q yields a pressure field p that transitions smoothly across the interface. CCD can evaluate ∇p at O(h⁶) without any special treatment.

### Step 2: HFE overwrites target-phase values, creating artificial kink

HFE replaces gas-phase pressure values near the interface with extrapolated liquid-phase values. Since the monolithic p was solved with variable 1/ρ(x), liquid-side and gas-side pressure profiles have different curvatures (governed by different local 1/ρ). Copying liquid-side values into gas-side locations creates a **gradient discontinuity** at the overwrite boundary:

    p_original:  smooth C^∞ transition through interface zone
    p_after_HFE: liquid-side extrapolation | abrupt join | unmodified gas-side
                                           ↑ artificial kink

### Step 3: Velocity correction amplifies the kink into parasitic currents

The velocity correction u^{n+1} = u* − (Δt/ρ)∇p requires smooth ∇p. The artificial kink produces O(1) gradient errors localized at the interface, which:

1. Violate the divergence-free condition ∇·u^{n+1} = 0 (the PPE solution was for the original smooth p, not the HFE-modified p)
2. Generate parasitic velocity that feeds back into the next time step
3. Break Balanced-Force consistency ([[WIKI-T-004]]) because ∇p no longer matches the CSF force discretization

## Experimental Evidence

Static droplet test (R=0.25, We=10, non-incremental projection, 200 steps):

| Metric | HFE OFF | HFE ON |
|--------|---------|--------|
| Parasitic current | O(10⁻⁴) | O(1) — **4-digit increase** |
| Laplace pressure | 1.2% error | **collapsed** |

Source: appendix_verification_details.tex §E.2

## Applicability Decision Table

| Solver Configuration | Pressure Field Character | HFE Status | Reason |
|----------------------|--------------------------|------------|--------|
| Smoothed Heaviside + non-incremental projection | Smooth (ε-regularized, no jump) | **Harmful** | Creates artificial discontinuity in smooth field |
| IPC (incremental projection) | Discontinuous ([p] = σκ) | **Essential** | ∇p^n in predictor crosses Young-Laplace jump |
| Split-phase PPE | Discontinuous (per-phase independent solve) | **Essential** | Jump condition [p] = σκ must be imposed via HFE |

## Root Cause Summary

The harm arises from a **precondition mismatch**: HFE assumes the input field contains an interface discontinuity that must be smoothed. When the field is already smooth, HFE's overwrite operation violates this precondition and introduces the very discontinuity it was designed to remove.

This is analogous to the direct pressure filter prohibition (§8c, [[warn:pressure_direct_filter]]): any post-hoc modification of the PPE solution p destroys the divergence-free projection guarantee.

## Implementation Guard

HFE should be gated by solver configuration:

    if surface_tension_model == "split_ppe" or projection == "incremental":
        apply HFE to pressure before CCD gradient
    else:
        skip HFE (smoothed Heaviside pressure is already smooth)
