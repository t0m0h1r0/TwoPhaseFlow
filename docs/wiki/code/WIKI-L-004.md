---
ref_id: WIKI-L-004
title: "Level-Set Transport & Remapping Scripts (Exp 11-6, 11-8)"
domain: L
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_6_cls_advection.py
    git_hash: e2a1b1b
    description: "CLS advection: Zalesak disk and single vortex benchmarks"
  - path: experiment/ch11/exp11_8_cls_remapping.py
    git_hash: e2a1b1b
    description: "Conservative remapping on dynamic non-uniform grid"
consumers:
  - domain: E
    usage: "Mirrors [[WIKI-E-003]] — code-level implementation details"
  - domain: T
    usage: "Validates claims in [[WIKI-T-007]]"
depends_on:
  - "[[WIKI-T-007]]"
  - "[[WIKI-T-002]]"
  - "[[WIKI-E-003]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Exp 11-6: CLS Advection (`exp11_6_cls_advection.py`)

**Purpose**: Validate DCCD advection + reinitialization with two standard benchmarks.

**Library classes used**:

| Class | Module | Role |
|-------|--------|------|
| `DissipativeCCDAdvection` | `twophase.levelset.advection` | DCCD advection with eps_d=0.05 |
| `Reinitializer` | `twophase.levelset.reinitialize` | CLS reinitialization (n_steps=4) |
| `RigidRotation` | `twophase.initial_conditions.velocity_fields` | Prescribed velocity for Zalesak |
| `heaviside` | `twophase.levelset.heaviside` | phi → psi conversion |

**Time loop pattern** (shared by both benchmarks):

```python
for step in range(n_steps):
    u, v = velocity_field(X, Y, t)
    psi = adv.advance(psi, [u, v], dt)
    if (step + 1) % reinit_interval == 0:
        psi = reinit.reinitialize(psi)
```

**Two sub-cases**:

| Case | Benchmark | Velocity | Period | Reinit interval | CFL |
|------|-----------|----------|--------|-----------------|-----|
| (a) | Zalesak slotted disk | `RigidRotation(center=(0.5,0.5), period=2pi)` | T=2pi | 20 steps | 0.45/N |
| (b) | Single vortex (LeVeque) | Inline `sin^2(pi x)*sin(pi y)*cos(pi y)*cos(pi t/T)` | T=8 | 10 steps | 0.45/N |

**Zalesak SDF construction**: Composite of circle SDF and slot (max of circle, negated slot):

```python
phi = max(phi_circle, -phi_slot)
```

**Measured quantities**: L2 shape error `sqrt(mean((psi_final - psi_0)^2))` and mass error `|sum(psi_final) - sum(psi_0)| / sum(psi_0)`.

## Exp 11-8: CLS Remapping (`exp11_8_cls_remapping.py`)

**Purpose**: Compare CLS conservative remapping vs LS interpolation on dynamic grid.

**Setup**: N=128, interface-fitted grid (`alpha_grid=2.0`), circular interface R=0.25, uniform velocity (1,0), period T=1.

**Grid refresh pattern**: Every K steps (K=5,10,20,50), regenerate grid from current interface:

```python
if (step + 1) % K == 0:
    phi_cur = eps * log(psi / (1 - psi))   # logit inversion
    mass_before = sum(psi)
    psi = psi * (mass0 / mass_before)       # CLS mass correction
```

**Key detail**: CLS conservative remapping is implemented as global mass scaling (`psi *= mass0/mass_before`). LS path has no correction.

**Measured quantity**: Relative mass error `|sum(psi_final) - sum(psi_0)| / sum(psi_0)` and improvement ratio (LS/CLS).
