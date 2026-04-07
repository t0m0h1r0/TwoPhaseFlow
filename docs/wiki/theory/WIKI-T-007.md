---
ref_id: WIKI-T-007
title: "Conservative Level Set (CLS): Transport, Reinitialization, and Mass Conservation"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/03_levelset.tex
    git_hash: 7328bf1
    description: "CLS theory: conservative transport, reinitialization PDE, mass conservation proof"
  - path: paper/sections/03b_levelset_mapping.tex
    git_hash: 7328bf1
    description: "psi-phi logit inversion, direct psi-curvature, implementation"
consumers:
  - domain: L
    usage: "levelset/ module implements CLS advection + reinitialization"
  - domain: T
    usage: "CLS provides the interface variable for all physical terms"
  - domain: E
    usage: "Mass conservation is a primary benchmark metric"
depends_on:
  - "[[WIKI-T-006]]"
  - "[[WIKI-T-010]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Why CLS Over Standard LS

Standard LS advection (du/dt + u . grad(phi) = 0) has two independent problems:
1. **Eikonal violation** (|grad(phi)| != 1) → curvature error (fixed by reinitialization)
2. **Non-conservative form** → volume drift O(dt*h^2) (persists despite reinitialization)

CLS solves problem 2 fundamentally by using conservative transport.

## CLS Transport Equation

d(psi)/dt + div(psi * u) = 0

Volume conservation proof via divergence theorem:
- d/dt integral(psi dV) = -integral(psi * u . n dS) = 0 for wall/periodic BC
- This holds regardless of discrete div(u) errors
- Mass error per step: O(h^5 * dt) with DCCD (vs O(dt*h^2) for standard LS)

## Variable Definitions

| Variable | Domain | Interface | Meaning |
|----------|--------|-----------|---------|
| phi | R | phi = 0 | Signed distance function (phi < 0 = liquid) |
| psi | [0, 1] | psi = 0.5 | Conservative LS: psi = H_eps(phi) (smoothed Heaviside) |

**Bidirectional transformation:**
- Forward: psi = H_eps(phi) (smoothed Heaviside)
- Inverse (logit): phi = eps * ln(psi / (1-psi))  — analytic, O(1) per point, no Newton iteration

## Reinitialization PDE

d(psi)/d(tau) + div(psi*(1-psi)*n_hat) = div(eps * grad(psi))

- **Compression term**: psi*(1-psi)*n_hat sharpens interface (zero at psi=0 and psi=1)
- **Diffusion term**: eps*Laplacian(psi) prevents over-steepening
- **Fixed point**: equilibrium profile is exactly psi = H_eps(phi)
- **Interface preservation**: at psi=0.5, compression cancels → interface moves O(h^3*dt) only

### Parameters
- Interface thickness: eps = C_eps * dx_min, C_eps ≈ 1.0–2.0
- Pseudotime step: dtau = min(0.5*h^2/(2*N_dim*eps), 0.5*h)
- Typical iterations: 3–5 normal, 10–20 after topology change
- Convergence monitor: M(tau) = integral(psi*(1-psi) dV), trigger when M/M_ref > 1.05

## Logit Inversion Details

phi = eps * ln(psi / (1-psi))

- Saturation handling: psi < 1e-6 or psi > 1-1e-6 → phi = ±phi_max ≈ ±13.8*eps
- Only needed when Split-PPE / HFE requires phi for normal computation
- Not needed for curvature (see [[WIKI-T-008]])

## Comparison: CLS vs Standard LS vs VOF

| Feature | Standard LS | CLS | VOF |
|---------|------------|-----|-----|
| Mass conservation | Poor (O(dt*h^2)) | **Excellent** (O(h^5*dt)) | Excellent |
| Geometric accuracy (kappa) | Good (from phi) | **Good** (from psi, invariance theorem) | Poor (reconstruction) |
| Reinitialization | Sussman (moves interface O(dt*h^2)) | Compression-diffusion (O(h^3*dt)) | N/A |
| Variable | phi (unbounded) | psi in [0,1] (bounded) | alpha in [0,1] |
