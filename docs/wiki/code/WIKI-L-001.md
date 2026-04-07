---
ref_id: WIKI-L-001
title: "Algorithm Flow: 7-Step Time Integration Loop"
domain: L
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/10_full_algorithm.tex
    git_hash: 7328bf1
    description: "7-step algorithm flow, operator mapping, timestep control"
  - path: paper/sections/10b_implementation_details.tex
    git_hash: 7328bf1
    description: "Bootstrap initialization, DCCD parameter design"
consumers:
  - domain: L
    usage: "simulation/_core.py implements this loop; builder.py handles bootstrap"
  - domain: E
    usage: "Experiment scripts follow this algorithm structure"
  - domain: A
    usage: "fig:ns_solvers maps NS terms to discrete solvers"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-002]]"
  - "[[WIKI-T-003]]"
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-005]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## 7-Step Time Integration Loop

Each time step n -> n+1:

| Step | Operation | Method | DCCD Mode |
|------|-----------|--------|-----------|
| 1 | CLS advection | DCCD + TVD-RK3 | Uniform eps_d=0.05 |
| 2 | CLS reinitialization | DCCD + TVD-RK3 (virtual time, n_reinit=4) | Uniform eps_d=0.05 |
| 3 | Property update | rho(psi), mu(psi) from smoothed Heaviside | None |
| 4 | Curvature | CCD kappa from psi', psi'' | Uniform eps_d=0.05 |
| 5 | Predictor | AB2(convection) + CN(viscosity) + sigma*kappa*grad_CCD(psi) + g - (1/rho)*grad_CCD(p^n) | Adaptive eps_d=0.05*S(psi) |
| 6 | PPE | DC (k=1): L_FD(delta_p) = div_DCCD(u*)/dt | Checkerboard eps_d=1/4 |
| 7 | Corrector | u^{n+1} = u* - (dt/rho)*grad_CCD(delta_p) | Checkerboard eps_d=1/4 (divergence check) |

## Bootstrap Initialization (5 Steps)

Before the first time step, resolve circular dependencies:

1. **Uniform grid evaluation**: Compute phi on temporary uniform grid
2. **Non-uniform grid generation**: Generate interface-conforming grid from phi via grid density function
3. **CLS variable initialization**: Re-evaluate psi on non-uniform grid; apply reinitialization
4. **CCD operator construction**: Build block tridiagonal matrices for new grid spacing
5. **Initial pressure**: Solve PPE with p^0 = sigma/R (Laplace pressure) as initial guess

## Timestep Control

dt = min(dt_adv, dt_sigma) * safety_factor

- **Advective CFL**: dt_adv = CFL_max * min(dx_i) / max(|u_i|), CFL_max <= 0.5 (operational)
- **Capillary wave**: dt_sigma = sqrt(rho_avg * min(dx)^3 / (pi * sigma))
- Safety factor: typically 0.8

## AB2 Startup

At n=0, AB2 requires u^{n-1} which does not exist. Use Forward Euler for the first step:
- n=0: u* = u^0 + dt * [FE(convection) + ...]  (O(dt))
- n>=1: u* = u^n + dt * [AB2(convection) + ...]  (O(dt^2))

## Key Design Notes

- **ADI splitting** in Step 5 (viscous CN): x-sweep and y-sweep use 2nd-order FD for Thomas compatibility (CCD not compatible with scalar Thomas). ADI splitting error is O(dt^2), same order as IPC.
- **Balanced-Force**: Steps 5 and 7 both use grad_CCD — same operator for surface tension and pressure gradient (see [[WIKI-T-004]])
- **PPE RHS filter**: Step 6 applies DCCD (eps_d=1/4) to predicted velocity divergence before forming PPE RHS — this is the checkerboard suppression mechanism (see [[WIKI-X-001]])
