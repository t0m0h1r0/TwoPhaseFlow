---
ref_id: WIKI-E-005
title: "Time Integration Verification (Exp 11-14, 11-15)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_14_tvd_rk3.py
    description: "TVD-RK3 (SSP 3-stage) temporal accuracy"
  - path: experiment/ch11/exp11_15_ab2_time.py
    description: "AB2 with Euler startup temporal accuracy"
consumers:
  - domain: L
    usage: "Validates time stepping in algorithm loop ([[WIKI-L-001]])"
depends_on:
  - "[[WIKI-L-001]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Exp 11-14: TVD-RK3 (Shu-Osher SSP)

Three sub-tests:

### (a) ODE dq/dt = −q, q(0) = 1

| n_steps | Error | Slope |
|---------|-------|-------|
| 4–512 | decreasing | **O(dt^3)** — PASS |

### (b) Scalar advection, N=256 fixed, temporal refinement

| n_steps | L2 error | Slope |
|---------|----------|-------|
| 10–640 | decreasing | **O(dt^3)** — PASS |

### (c) Space-time coupled convergence at CFL = 0.3

Confirms O(dt^3) temporal order is not polluted by spatial discretization.

**Key finding**: TVD-RK3 achieves its design order O(dt^3) in all tests. Parasitic modes are controlled by the SSP property. This is the time integrator for CLS advection (Steps 1–2 in [[WIKI-L-001]]).

## Exp 11-15: AB2 with Forward Euler Startup

ODE dq/dt = −q, q(0) = 1, T = 1.0:

| n_steps | Error | Slope |
|---------|-------|-------|
| 16–512 | decreasing | **O(dt^2)** — PASS |

**Key finding**: AB2 achieves O(dt^2) despite first-order Euler startup. Parasitic root |ρ_2| = 0.5 decays to negligible levels. Error reaches ~1e-15 at n = 512 steps. This is the time integrator for the predictor step (Step 5 in [[WIKI-L-001]]).

## Cross-cutting Insights

- TVD-RK3 O(dt^3) for advection + reinitialization: temporal error subordinate to spatial
- AB2 O(dt^2) for predictor: matches IPC splitting error O(dt^2)
- Euler startup for AB2 does not degrade global second-order accuracy
