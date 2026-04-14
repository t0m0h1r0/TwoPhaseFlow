---
id: WIKI-L-016
title: "CN Advance Strategy Pattern: Viscous Time-Integration Subpackage"
status: ACTIVE
created: 2026-04-15
depends_on: [WIKI-T-033, WIKI-L-008, WIKI-L-001]
---

# CN Advance Strategy Pattern

## Location

`src/twophase/time_integration/cn_advance/`

## Problem

The viscous predictor step (`ViscousTerm.apply_cn_predictor`) was a monolithic
method conflating temporal discretization choice with the viscous operator.
Design memo [[WIKI-T-033]] identified a roadmap from Picard-CN (O(Δt²)) through
Richardson (O(Δt³⁺)) to implicit Padé-(2,2) (O(Δt⁴)), requiring the temporal
scheme to be swappable without modifying the viscous operator.

## Solution: ICNAdvance Protocol + Strategy

```
base.py       →  ICNAdvance (typing.Protocol)
picard_cn.py  →  PicardCNAdvance   (Heun predictor–corrector, O(Δt²))
richardson_cn.py → RichardsonCNAdvance(base: ICNAdvance) (Decorator, O(Δt^{p+1}))
```

### ICNAdvance Contract

```python
def advance(self, u_old, explicit_rhs, mu, rho, viscous_op, ccd, dt) -> List
```

- `u_old`: velocity at time n (list of ndim arrays)
- `explicit_rhs`: frozen RHS from AB2+gravity+surface tension at time n
- `viscous_op`: `ViscousTerm` instance (provides `_evaluate`)
- Returns `u_star`: predicted velocity after viscous step

### RichardsonCNAdvance (Decorator Pattern)

Wraps any `ICNAdvance` base and applies Richardson extrapolation:

    u* = (4·Φ(Δt/2)∘Φ(Δt/2) − Φ(Δt)) / 3

- Base = PicardCNAdvance → O(Δt³) (Picard is non-symmetric, +1 gain)
- Base = ImplicitCNAdvance → O(Δt⁴) (CN is symmetric, +2 gain) [Phase 3]
- Base = Padé-(2,2) → O(Δt⁶) (symmetric rational, +2 gain) [Phase 6]
- Cost: ~3× base per outer call
- Stability: inherited from base

### Config Integration

```yaml
cn_advance_method: "picard"       # default
cn_advance_method: "richardson"   # RichardsonCNAdvance(PicardCNAdvance())
```

Wired in `SimulationBuilder.build()` via `config.cn_advance_method`.

## Verification

`exp11_30_cn_convergence.py`: manufactured-solution temporal convergence study.
- Picard-CN: confirmed O(Δt²) slope
- Richardson(Picard): confirmed O(Δt³) slope

## Roadmap (from WIKI-T-033)

| Phase | Strategy | Order | Status |
|-------|----------|-------|--------|
| 1 | PicardCNAdvance | O(Δt²) | IMPLEMENTED |
| 2 | RichardsonCNAdvance(Picard) | O(Δt³) | IMPLEMENTED |
| 3 | ImplicitCNAdvance (true trapezoidal) | O(Δt²), A-stable | DESIGN |
| 4 | Richardson(Implicit) | O(Δt⁴), A-stable | DESIGN |
| 5 | Padé-(2,2) via CCD inversion | O(Δt⁴), L-stable | DESIGN |
| 6 | Richardson(Padé) | O(Δt⁶), L-stable | DESIGN |
