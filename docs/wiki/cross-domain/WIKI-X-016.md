---
ref_id: WIKI-X-016
title: "Reinit ε-Scale Propagation Path and σ>0 vs σ=0 Dispatch Policy (CHK-139)"
domain: X
status: ACTIVE
superseded_by: null
sources:
  - path: src/twophase/levelset/reinit_eikonal.py
    description: "EikonalReinitializer — eps_scale parameter, eps_xi computation"
  - path: src/twophase/levelset/reinitialize.py
    description: "Reinitializer facade — eps_scale dispatch to eikonal variants"
  - path: src/twophase/simulation/ns_pipeline.py
    description: "TwoPhaseNSSolver.from_config — reinit_eps_scale YAML key"
depends_on:
  - "[[WIKI-T-042]]: Eikonal reinit theory — eps_scale motivation (interface width effect)"
  - "[[WIKI-E-028]]: CHK-136..139 experimental verification"
  - "[[WIKI-X-010]]: Reinitializer uniform-grid assumption"
consumers:
  - domain: E
    description: "experiment YAML run section: reinit_eps_scale: 1.4"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-18
---

# Reinit ε-Scale Propagation Path and σ>0 vs σ=0 Dispatch Policy (CHK-139)

---

## 1. The ε-Scale Parameter Propagation Chain

CHK-139 introduced `reinit_eps_scale` (float, default 1.0) to allow
explicit control of the interface width used in Eikonal-family
reinitialization. The parameter flows as follows:

```
YAML run section
  reinit_eps_scale: 1.4
        ↓
ns_pipeline.py TwoPhaseNSSolver.from_config (line ~248)
  reinit_eps_scale = float(getattr(run, "reinit_eps_scale", 1.0))
        ↓
TwoPhaseNSSolver.__init__ (line ~116)
  self._reinit_eps_scale = float(reinit_eps_scale)
        ↓
Reinitializer.__init__ (line ~197)
  eps_scale=self._reinit_eps_scale
        ↓
Reinitializer dispatch (reinitialize.py lines ~84-103)
  EikonalReinitializer(eps_scale=eps_scale)  ← for eikonal/eikonal_xi/eikonal_fmm
        ↓
EikonalReinitializer.__init__ (reinit_eikonal.py line ~80)
  eps_xi = float(eps) * float(eps_scale) / h_min
  self._eps_xi = eps_xi
        ↓
reinitialize() Step 3:
  psi_new = 1/(1 + exp(-phi_xi / eps_xi))   ← wider when eps_scale > 1
```

**Scope**: `eps_scale` affects ONLY the ψ reconstruction step (Step 3) and
the mass correction weight W (Step 4). It does NOT affect:
- The initial logit inversion: `phi = invert_heaviside(xp, psi, self._eps)`
  (uses original `eps`; OK because ξ-SDF rebuilds φ from zero-crossings, not magnitude)
- The curvature calculator's `eps_curv` (uses `self._eps` or `make_eps_field()`)
- Non-eikonal reinit methods (split, dgr, hybrid, unified — unaffected by eps_scale)

### Why κ Does Not Need eps_curv to Change

The curvature κ = −∇·(∇φ/|∇φ|) is scale-invariant:
- Curvature uses `phi_curv = eps * logit(psi)` where ψ was built with `f·eps`
- → `phi_curv = eps * phi_xi / (f·eps) = phi_xi / f`
- → `|∇phi_curv| = 1/f`
- → unit normal `∇phi_curv/|∇phi_curv| = ∇phi_xi` (same direction)
- → κ is unchanged

The surface tension force `F = σκ∇ψ` uses `∇ψ` computed by CCD on the
post-reinit ψ field, which automatically has width `f·ε`. So the effective
diffusion of σκ over the interface band is proportional to `f·ε` — exactly
the mechanism that reduces PPE residual.

---

## 2. Dispatch Policy: σ>0 vs σ=0 Reinitialization

Based on CHK-136..139 results, the following dispatch policy is recommended:

| Scenario | Method | eps_scale | Rationale |
|----------|--------|-----------|-----------|
| σ>0, capillary waves (σ=1) | `split` | N/A | Split-only naturally gives ~1.4ε, stable VolCons <1% at T=10 |
| σ>0, capillary waves (σ=1), T≤2 | `eikonal_xi` | 1.4 | Better D(T=2)=0.028 vs split's 0.037, VolCons 1.38% @T=2 |
| σ=0, passive advection (Zalesak) | `eikonal_xi` | 1.0 | Exact zero-set, correct ε, no drift |
| σ=0, single-vortex deformation | `eikonal_xi` | 1.0 | Same as Zalesak |
| Any σ, non-uniform grid α>1 | `split` | N/A | Eikonal xi-SDF: σ>0 long-time not verified |

**Split-only is still the σ>0 reference method** for T>2 until T=10 is verified
for `eikonal_xi + eps_scale=1.4`.

### Method Dispatch Table (reinitialize.py)

| YAML `reinit_method` | Class | zsp | xi_sdf | fmm | eps_scale forwarded |
|---|---|---|---|---|---|
| `split` | SplitReinitializer | — | — | — | No |
| `eikonal` | EikonalReinitializer | True | False | False | Yes |
| `eikonal_xi` | EikonalReinitializer | False | True | False | Yes |
| `eikonal_fmm` | EikonalReinitializer | False | False | True | Yes |
| `dgr` | DGRReinitializer | — | — | — | No |
| `hybrid` | HybridReinitializer | — | — | — | No |

---

## 3. Interface Width Effect on PPE Residual (CHK-138 Root Cause)

This cross-domain connection explains why interface width matters for VolCons:

```
Interface width ε_eff
     ↓
Surface tension force concentration:
  F_σ = σ κ ∇ψ   (width of ∇ψ ≈ ε_eff)
     ↓
PPE source: ∇·u* ∝ σκ / (ρ · ε_eff)
     ↓
Volume conservation drift:
  ΔV/V₀ ≈ (Δt/ρ) ∫ψ ∇·u* dV  ∝  1/ε_eff
```

Split-only gives ε_eff ≈ 1.4ε naturally (PDE diffusion broadening).
ξ-SDF (f=1.0) gives ε_eff = ε → PPE source 1.4× larger → VolCons 3.5×
higher per unit time (empirically confirmed by CHK-138 FMM experiment).

Setting eps_scale=1.4 in ξ-SDF reconstruction restores ε_eff ≈ 1.4ε →
VolCons decreases ~2.5× (from 1.46%@T=2 to ~1.38%@T=2).

---

## 4. Distinction from HeavisideInterfaceReconstructor eps_scale

`ns_pipeline.py` also has `phi_primary_heaviside_eps_scale` (YAML key:
`phi_primary_heaviside_eps_scale`, default 1.0) for the φ-primary
transport feature. This is a DIFFERENT eps_scale from `reinit_eps_scale`:

| Parameter | YAML key | Applies to | Effect |
|-----------|----------|------------|--------|
| `reinit_eps_scale` | `reinit_eps_scale` | EikonalReinitializer only | ψ reconstruction width |
| `phi_primary_heaviside_eps_scale` | `phi_primary_heaviside_eps_scale` | HeavisideInterfaceReconstructor | φ-primary transport |

These are independent; setting one does not affect the other.
