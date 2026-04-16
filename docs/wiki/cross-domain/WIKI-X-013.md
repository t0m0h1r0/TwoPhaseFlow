---
ref_id: WIKI-X-013
title: "Couette + Explicit CSF: Fundamental Instability in Predictor-Corrector NS"
domain: X
status: ACTIVE
superseded_by: null
sources:
  - commit: "a38af67"
    description: "docs(memo): finalize ch13 readiness report — 2/3 benchmarks PASS"
  - commit: "69bdc66"
    description: "config(ch13): switch all benchmarks to uniform grid (α=1.0)"
depends_on:
  - "[[WIKI-E-022]]"
  - "[[WIKI-X-012]]"
compiled_by: ResearchArchitect
compiled_at: 2026-04-16
---

# Couette + Explicit CSF: Fundamental Instability

The Taylor droplet deformation benchmark (§13.3) applies Couette shear flow
simultaneously with CSF surface tension. This configuration exposes a
**fundamental instability** in the explicit predictor-corrector NS scheme
that cannot be resolved by CFL control, grid refinement, or uniform-grid
choices.

---

## Observed Behavior

All 12 tested configurations (8 at N=128, 4 at N=64) blew up:

| Config | Steps to blowup | Physical time |
|--------|-----------------|---------------|
| N=128, lam1, Ca=0.1 | ~460 | t<0.01 |
| N=128, lam1, Ca=0.2 | ~460 | t<0.01 |
| N=128, lam5, Ca=0.1 | ~460 | t<0.01 |
| N=64,  lam1, Ca=0.2 | ~329 | t<0.03 |
| N=64,  lam5, Ca=0.4 | ~483 | t<0.05 |

Representative trace (N=64, lam1, Ca=0.2):
```
step=    1  t=0.0001  dt=0.00006  KE=1.719e-01   (Couette established)
step=    2  t=0.0001  dt=0.00006  KE=1.773e-01   (CSF onset: +3%)
step=  200  t=0.0092  dt=0.00000  KE=6.641e+03   (exponential growth)
BLOWUP at step=329, t=0.0092
```

---

## Instability Mechanism

1. **Steps 0 to N (Couette establishment):** Shear flow is driven stably.
   KE = γ̇²/12 ≈ 0.177 (for γ̇=2.0, L=1.0). dt remains controlled by
   viscous CFL (with `cn_viscous=true`, 2× relaxation applies).

2. **Step N+1 (CSF activation):** The circular droplet boundary has curvature
   κ = 1/R_ref = 4.0. The CSF force per unit volume at the interface is
   σκ ∇ψ / ρ, where ψ is the Heaviside. This injects a **radial velocity
   perturbation** centered at the interface.

3. **Step N+2 (convective amplification):** The convective term in the
   predictor evaluates `u·∇u_star`. The background Couette shear
   `u_shear = γ̇·y` acts on the perturbation. The radial perturbation has
   components tangent to the shear direction, and the shear amplifies
   them by O(γ̇·dt). For γ̇=2.0 and dt~6e-5, the single-step amplification
   is ~1.2×10⁻⁴ per step — but the perturbation grows exponentially because
   each corrector step feeds the next predictor step with a larger base field.

4. **Steps N+3+:** KE grows exponentially until BLOWUP.

---

## Why Standard Fixes Fail

| Fix | Reason it fails |
|-----|-----------------|
| `cn_viscous=true` | Stabilizes viscous CFL, not convective-surface-tension coupling |
| N=64 (4× larger dt_visc) | Same physical-time instability; more dt headroom in viscous doesn't help |
| α=1.0 uniform grid | Eliminates CCD metric errors but not the coupling instability |
| CFL reduction | Not a CFL problem; dt remains bounded throughout — instability is linear |

The instability is **linear** in the sense that it appears from the first
CSF-active step regardless of amplitude. It is not a nonlinear saturation
or convective CFL problem.

---

## Relationship to Static Droplet (Exp12)

The ch12 static droplet benchmarks (exp12_07, exp12_09) ran up to 200+
steps **without Couette flow** (u=0 background) and were stable. This
confirms that CSF alone (without shear) is stable in the explicit scheme.

The instability is specifically the **combination** of:
- Explicit convective term (u·∇u)
- Couette background shear (provides O(γ̇) amplification factor)
- Explicit CSF force (provides O(σκ/ρ·dt) perturbation each step)

The three together form an unstable feedback loop in the explicit predictor.

---

## Governing Parameter

The relevant dimensionless parameter is the **Capillary number** Ca = μγ̇/σ.
Low Ca (high σ relative to μγ̇) means stronger surface tension forces relative
to viscous damping. The tested cases Ca ∈ {0.1, 0.2, 0.3, 0.4} all fail,
suggesting the instability is not Ca-sensitive within this range — it is
an algorithmic property, not a physics parameter threshold.

---

## Required Fix (Future Work)

The fundamental fix is to treat surface tension **semi-implicitly** or
**implicitly**:

1. **Semi-implicit σκ:** Treat the normal stress jump implicitly in the
   pressure solve. At each step, solve `∇·(∇p/ρ) = ∇·u_star/dt + ∇·(σκδ_s n̂/ρ)`
   where the κ term is updated at the new interface position. This requires
   moving κ from the explicit predictor into the PPE RHS.

2. **Gradual σ ramp-up:** Start with σ=0 (no surface tension), establish
   Couette flow, then increase σ quasi-statically. Avoids the impulsive
   CSF onset. Less rigorous but may be sufficient for steady-state D.

3. **Full implicit coupling:** Monolithic pressure-velocity-interface solve.
   Significant code change; not ch13-scope.

4. **Alternative physics:** Use γ̇=0.5 (lower shear) or μ=0.5 (higher μ)
   to reduce Ca and the convective amplification.

---

## Cross-References

- [[WIKI-E-022]] — Ch13 readiness investigation (discovery context, all 12 cases documented)
- [[WIKI-X-012]] — CCD metric instability (distinct mechanism, same benchmark)
- [[WIKI-E-014]] — Ch12 experiments including static droplet stability (contrast case)
