---
ref_id: WIKI-P-003
title: "Problem Statement: Four Failure Modes and Three-Pillar Solution"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/01_introduction.tex
    git_hash: 7328bf1
    description: "§1: four difficulties, four failure modes, method positioning, learning roadmap"
consumers:
  - domain: A
    usage: "Motivates entire paper structure; each failure mode addressed in specific chapters"
  - domain: E
    usage: "Benchmark experiments target each failure mode"
depends_on: []
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Four Fundamental Numerical Difficulties

| # | Difficulty | Root Cause | Solution in This Paper |
|---|-----------|-----------|----------------------|
| 1 | Interface tracking + mass conservation | Non-conservative LS advection → volume drift | CLS conservative transport (§3) |
| 2 | Accurate surface tension evaluation | Curvature needs 2nd derivatives (error amplification) | CCD O(h^6) curvature (§4) + Balanced-Force (§8) |
| 3 | Incompressibility maintenance | Variable-coefficient PPE + checkerboard instability | CCD-PPE + DCCD eps_d=1/4 (§9) |
| 4 | Density stratification + spurious currents | Operator mismatch in grad(p) vs kappa*grad(psi) | Unified CCD operator (§8, Balanced-Force) |

## Four Failure Modes

| Mode | Symptom | Cause | Fix |
|------|---------|-------|-----|
| Spurious currents | Vortex velocity at stationary interface | Curvature error + operator mismatch feedback loop | CCD O(h^6) + Balanced-Force |
| Mass loss | Droplet shrinks/disappears | Non-conservative LS advection O(dt*h^2) | CLS conservative transport |
| Checkerboard instability | Pressure oscillations (2dx pattern) | Central difference on collocated grid — pressure-velocity decoupling | DCCD eps_d=1/4 |
| Interface smearing | Interface widens over time | Numerical diffusion in advection | DCCD + CLS reinitialization |

## Three-Pillar Solution Strategy

1. **CCD O(h^6)**: Compact 3-point stencil achieving 6th-order accuracy — handles locality trap at interfaces
2. **CLS + DCCD**: Conservative interface tracking with controlled numerical dissipation
3. **Balanced-Force**: Same CCD operator for pressure gradient and surface tension → O(h^6) discrete equilibrium

## Method Positioning vs Prior Art

| Approach | Surface tension | Mass conservation | This paper's advantage |
|----------|----------------|-------------------|----------------------|
| François et al. (VOF+BF) | Balanced-Force but O(h^2) FVM | Excellent | CCD O(h^6) vs FVM O(h^2) |
| Desjardins et al. (GFM+LS) | Sharp jump + Extension PDE | Standard LS (poor) | CLS preserves mass; no Extension PDE needed for current formulation |
| This paper (CCD+CLS+BF) | O(h^6) unified operator | CLS O(h^5*dt) | Both advantages combined |

## Paper Structure (7-Step Algorithm)

- **Interface subsystem** (Steps 1–4): CLS advection → Reinitialization → Property update → Curvature
- **Hydrodynamics subsystem** (Steps 5–7): Predictor → PPE → Corrector
- Coupling via rho(psi), mu(psi), kappa between subsystems

See [[WIKI-L-001]] for the complete 7-step algorithm.
