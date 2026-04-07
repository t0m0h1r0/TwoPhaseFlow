---
ref_id: WIKI-X-005
title: "Architectural Decisions: PPE Strategy, Solver Integration, and Verification Hierarchy"
domain: X
status: ACTIVE
superseded_by: null
sources:
  - path: "docs/memo/改稿_PPE求解の欠陥補正法への転換.md"
    git_hash: e62cd50
    description: "Decision to switch PPE from LGMRES to defect correction; chapter reorganization"
  - path: "docs/memo/改稿_PartIV.md"
    git_hash: e62cd50
    description: "Part IV integration: Ch9 algorithm flow, Ch10 component verification, Ch11 benchmarks"
  - path: "docs/memo/改稿_数値実験計画書：第10-12章の完全検証プラン.md"
    git_hash: e62cd50
    description: "Hierarchical verification: component → NS consistency → two-phase benchmarks"
  - path: "docs/memo/改稿_第11章実験再計画.md"
    git_hash: e62cd50
    description: "Ch11 replanning: gaps identified (no two-phase time integration, no interface-crossing test)"
  - path: "docs/memo/改稿_第12章ゼロベース再設計.md"
    git_hash: e62cd50
    description: "Ch12 redesign: only include experiments that actually run; GFM+NS diverges at ρ≥10"
consumers:
  - domain: L
    usage: "Solver architecture and test infrastructure design"
  - domain: A
    usage: "Paper structure decisions for §9–§12"
depends_on:
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-024]]"
  - "[[WIKI-L-001]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## PPE Solver Strategy Decision

**Decision:** Switch from LGMRES to Defect Correction (DC) + direct LU.

**Rationale:**
- LGMRES requires explicit Kronecker-product matrix assembly → O(N⁴) memory
- DC+LU uses FD tridiagonal preconditioner → O(N²) per iteration, matrix-free CCD evaluation
- k=3 DC iterations achieve O(h⁶) accuracy (see [[WIKI-T-024]])
- ω-relaxation (ω < 0.833) ensures convergence for uniform density

**Limitation:** Stalls at ρ_l/ρ_g ≥ 5. GMRES+FD-preconditioner is the high-density-ratio upgrade path.

## Paper Part IV Structure

### Ch9: Integrated Solver Algorithm

How CCD, DCCD, CLS, RC coordinate in a single timestep on collocated grid. 7-step time loop with operator mapping (see [[WIKI-L-001]]).

### Ch10 (→ became §11): Component-Level Verification

Bottom-up: each component proves design-order accuracy independently before coupling.

### Ch11 (→ became §12): Multi-Phase Benchmarks

System-level validation with realistic physics.

## Verification Hierarchy (3-Tier)

1. **Component math verification:** CCD convergence order, DCCD filter transfer function, CLS mass conservation, PPE with density jump
2. **NS equation physical consistency:** Temporal accuracy (RK3, AB2), spatial operator coupling, pressure-velocity decoupling
3. **Two-phase benchmarks:** Static droplet (parasitic currents), rising bubble (if stable), Rayleigh-Taylor

## Ch11 Replanning: Identified Gaps

- No two-phase time integration test (only single-phase temporal accuracy verified)
- No interface-crossing verification (HFE not tested in coupled context)
- Missing: coupled CLS+PPE convergence test

## Ch12 Zero-Base Redesign

**Principle:** Only include experiments that actually run. No fabricated "predicted results."

**Feasible:** EXP-12A Rayleigh-Taylor (σ=0, already passing), ablation studies for HFE contribution.

**Broken:** Moving interface with σ>0 blows up in 2–3 steps (GFM+NS diverges at ρ≥10). Deferred honestly to Ch13 future work.
