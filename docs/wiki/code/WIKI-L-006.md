---
ref_id: WIKI-L-006
title: "Time Integration Verification Scripts (Exp 11-14, 11-15)"
domain: L
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_14_tvd_rk3.py
    git_hash: e2a1b1b
    description: "TVD-RK3 time integration: ODE and advection convergence"
  - path: experiment/ch11/exp11_15_ab2_time.py
    git_hash: e2a1b1b
    description: "AB2 with Euler startup: ODE convergence"
consumers:
  - domain: E
    usage: "Mirrors [[WIKI-E-005]] — code-level implementation details"
  - domain: T
    usage: "Validates time integration claims in [[WIKI-T-003]]"
depends_on:
  - "[[WIKI-T-003]]"
  - "[[WIKI-E-005]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Exp 11-14: TVD-RK3 (`exp11_14_tvd_rk3.py`)

**Purpose**: Verify O(dt^3) accuracy of Shu-Osher SSP 3-stage Runge-Kutta.

**Library function**: `from twophase.time_integration.tvd_rk3 import tvd_rk3` — called as `q = tvd_rk3(xp, q, dt, rhs_fn)`.

**Two sub-cases**:

| Case | Test | Setup | RHS |
|------|------|-------|-----|
| (a) ODE | dq/dt = -q, q(0)=1 | Scalar `q = xp.array([[1.0]])` | `lambda q: -q` |
| (b) Advection | u_t + u_x = 0 on N=256 | CCD periodic grid | `lambda q: -ccd.differentiate(q, 0)[0]` |

**ODE test pattern**: Loop `q = tvd_rk3(xp, q, dt, lambda q: -q)` for n steps, compare `q` vs `exp(-T)`.

**Advection convergence**: Fixed N=256 (spatial error negligible), vary n=[10..640] steps. Measures temporal order in isolation.

**Step counts**: `n_list = [4, 8, 16, ..., 512]` for ODE; `[10, 20, 40, ..., 640]` for advection.

## Exp 11-15: AB2 (`exp11_15_ab2_time.py`)

**Purpose**: Verify O(dt^2) accuracy of Adams-Bashforth 2nd order with Forward Euler startup.

**Implementation** (inline, no library import):

```python
for step in range(n):
    f_n = -q
    if step == 0:
        q = q + dt * f_n                       # Forward Euler startup
    else:
        q = q + dt * (1.5 * f_n - 0.5 * f_prev)  # AB2
    f_prev = f_n
```

**Key detail**: No library class — AB2 is implemented inline as 3-line formula. This is the simplest experiment script (87 lines total, no external dependencies beyond numpy).

**Test**: ODE dq/dt = -q, q(0)=1, n=[16..512] steps, T=1.

**Parasitic root**: |rho_2| = 0.5 (from AB2 characteristic equation) decays negligibly — confirmed by clean O(dt^2) convergence.
