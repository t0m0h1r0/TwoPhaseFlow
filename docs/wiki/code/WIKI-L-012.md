---
id: WIKI-L-012
title: "Reinitialization Strategy Pattern: Facade, 4 Strategies, and Shared Operations"
status: ACTIVE
created: 2026-04-10
depends_on: [WIKI-T-007, WIKI-T-028, WIKI-T-030, WIKI-L-009]
---

# Reinitialization Strategy Pattern

## Architecture

```
reinitialize.py          # Reinitializer (facade) + ReinitializerWENO5 (legacy)
reinit_ops.py            # Shared pure functions
reinit_split.py          # SplitReinitializer
reinit_unified.py        # UnifiedDCCDReinitializer
reinit_dgr.py            # DGRReinitializer + HybridReinitializer
```

## Facade: Reinitializer

```python
class Reinitializer(IReinitializer):
    def __init__(self, ..., method='split'):
        # Creates appropriate strategy based on method parameter
        if method == 'split':    self._strategy = SplitReinitializer(...)
        elif method == 'unified': self._strategy = UnifiedDCCDReinitializer(...)
        elif method == 'dgr':    self._strategy = DGRReinitializer(...)
        elif method == 'hybrid': self._strategy = HybridReinitializer(split, dgr)
    
    def reinitialize(self, psi):
        return self._strategy.reinitialize(psi)
```

Backward-compatible: callers (SimulationBuilder) still create `Reinitializer(method='split')` as before.

## Strategy Classes

### SplitReinitializer (default, paper section 5c)

**Algorithm** per pseudo-time step:
1. **Compression** (explicit FE): psi** = psi - dtau * div[psi(1-psi) n_hat]
   - Divergence via Dissipative CCD (eps_d = 0.05)
2. **Diffusion** (CN-ADI): (M2 - mu*B2) psi^{tau+1} = (M2 + mu*B2) psi**
   - Pre-factored Thomas solve per axis
3. Clip to [0, 1]

Post: interface-weighted mass correction (WIKI-T-027).

### UnifiedDCCDReinitializer (WIKI-T-028)

Combined RHS eliminates operator-splitting mismatch:
- R = -C + D with Lagrange conservation correction
- Two-stage clip repair preserves mass to machine precision
- No CN-ADI needed (diffusion from CCD d2 directly)

### DGRReinitializer (WIKI-T-030)

Direct one-step thickness restoration:
1. Estimate eps_eff from median of psi(1-psi)/|grad(psi)| in interface band
2. phi_raw = eps * logit(psi), rescale by eps_eff/eps
3. Reconstruct psi_new = H_eps(phi_sdf)

### HybridReinitializer

Composition: SplitReinitializer (shape) then DGRReinitializer (thickness).
Avoids both failure modes: split alone broadens eps_eff, DGR alone loses position accuracy.

## Shared Operations (`reinit_ops.py`)

| Function | Used by | Description |
|----------|---------|-------------|
| `compute_dtau(grid, eps)` | Split, Unified | Pseudo-time step (parabolic + hyperbolic CFL) |
| `compute_gradient_normal(xp, psi, ccd)` | Unified | Gradient + unit normal computation |
| `filtered_divergence(xp, flux, ax, eps_d, ccd, grid, bc)` | Split, Unified | DCCD filter + divergence |
| `dccd_compression_div(xp, psi, ccd, grid, bc, eps_d)` | Split | Full compression divergence |
| `build_cn_factors(grid, eps, dtau, axis)` | Split | Thomas pre-factorization |
| `cn_diffusion_axis(xp, psi, axis, eps, dtau, h, cn_factors)` | Split | CN half-step (ADI) |
| `volume_monitor(xp, psi, grid)` | Facade | M(tau) = integral psi(1-psi) dV |

## Legacy: ReinitializerWENO5

DO NOT DELETE (C2). Uses WENO5 flux splitting + TVD-RK3 for both compression and diffusion. Superseded by SplitReinitializer (Dissipative CCD + CN). Kept for cross-validation.
