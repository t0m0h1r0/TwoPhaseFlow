---
ref_id: WIKI-T-003
title: "Variable-Density Projection Method: IPC + AB2 + CN"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/06_time_integration.tex
    git_hash: 7328bf1
    description: "Time integration taxonomy: TVD-RK3, AB2+IPC, CN, accuracy table"
  - path: paper/sections/08b_pressure.tex
    git_hash: 7328bf1
    description: "Variable-density projection derivation, IPC incremental pressure"
consumers:
  - domain: L
    usage: "time_integration/ and pressure/ modules implement these schemes"
  - domain: A
    usage: "Accuracy table referenced throughout paper"
depends_on:
  - "[[WIKI-T-001]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Time Integration Taxonomy

The monograph uses different time integrators for different equation components:

| Component | Integrator | Order | Rationale |
|-----------|-----------|-------|-----------|
| CLS advection | TVD-RK3 (Shu-Osher) | O(dt^3) | Highest time accuracy for interface; TVD property |
| CLS reinitialization | TVD-RK3 (virtual time) | O(dt^3) | Same as advection for consistency |
| NS convection | AB2 (Adams-Bashforth 2nd) | O(dt^2) | Explicit, no matrix assembly for nonlinear term |
| NS viscosity | CN (Crank-Nicolson) | O(dt^2) | Implicit, unconditionally stable for diagonal terms |
| Pressure splitting | IPC (van Kan 1986) | O(dt^2) | Incremental pressure correction reduces splitting error |

## IPC (Incremental Pressure Correction)

Standard projection (Chorin) has O(dt) splitting error. IPC uses incremental pressure delta_p = p^{n+1} - p^n, reducing splitting error to O(dt^2).

Predictor: u* = u^n + dt * [AB2(convection) + CN(viscosity) + gravity + surface_tension - (1/rho) * grad(p^n)]

PPE: div((1/rho^{n+1}) * grad(delta_p)) = div(u*) / dt

Corrector: u^{n+1} = u* - (dt/rho^{n+1}) * grad(delta_p)

## Variable-Density Extension

The PPE operator becomes: div((1/rho) * grad(p)), which is a variable-coefficient Poisson equation. The product rule expansion gives:

(1/rho) * Laplacian(p) + grad(1/rho) . grad(p)

This produces a non-symmetric operator requiring careful discretization (see [[WIKI-T-005]]).

## Critical Caveats

- **AB2 startup**: n=0 step uses Forward Euler (O(dt)), reducing to O(dt^2) from n=1
- **CN cross-derivative**: mu varies across interface; cross-derivative terms treated explicitly -> O(dt) near interface when mu_l/mu_g >> 1
- **Overall accuracy**: O(dt^2) homogeneous, O(dt) near interface (cross-derivative limited)
- **Spatial rate-limiter**: CSF model error O(h^2) dominates; CCD O(h^6) provides headroom for future GFM upgrade
