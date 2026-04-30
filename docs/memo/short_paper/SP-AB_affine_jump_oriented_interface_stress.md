# SP-AB — Affine Jump and Oriented Interface-Stress Closure

- **Status**: ACTIVE / design correction
- **Compiled by**: ResearchArchitect
- **Compiled at**: 2026-04-30
- **Scope**: ch14 capillary wave, ch13 rising bubble, generic pressure-jump interface stress
- **Primary consumers**: paper §8, §9, §10, §14; `src/twophase/simulation/interface_stress_closure.py`
- **Wiki twin**: [WIKI-X-039](../../wiki/cross-domain/WIKI-X-039.md)
- **Public-citation policy**: this SP is an internal research memo. The paper
  should cite external GFM/IIM, balanced-force, and capillary-wave references
  rather than this memo directly.

---

## 1. Abstract

The ch14 capillary-wave investigation separates two distinct failures that had
previously been conflated. The legacy `jump_decomposition` formulation failed
because it represented a sharp interfacial pressure jump as a regular pressure
field. In an initially stationary capillary wave, the elliptic solve absorbed
that field through `p_base ≈ -J`, leaving `p_total = p_base + J ≈ 0`. The
measured one-step cancellation ratio was `9.022527e-04`, which is an algebraic
operator failure rather than a time-step or visualization issue.

The replacement `affine_jump` formulation fixes that structural problem by
placing the known pressure jump directly in the face-gradient operator:

```text
G_Gamma(p; j)_f = G(p)_f - B_f(j).
```

However, the N=32, T=10 run revealed a second, deeper problem. The early
capillary acceleration had the correct magnitude but the wrong sign:

```text
A''_theory   = -1.427056761315e-03
A''_observed = +1.502517625523e-03
```

Thus the capillary stiffness was present, but it acted anti-restoringly. The
root cause is the jump convention: the current route supplied `+σ κ` as
`p_gas - p_liquid`, whereas oriented Young--Laplace requires

```text
j_gl = p_gas - p_liquid = -σ κ_lg.
```

The solution is not a capillary-wave special branch. It is a generic oriented
interface-stress contract shared by capillary waves, static droplets, gas
bubbles, rising bubbles, and flat Rayleigh--Taylor interfaces.

## 2. Research question

The user constraint is stronger than "make the capillary wave run":

```text
Build logic that also applies to rising bubbles.
Do not create capillary-wave-only code.
Respect physical law.
Do not hide failures with small technical tricks.
```

This makes the research question:

```text
What is the minimal interface-stress contract that preserves Young--Laplace
sign, projection consistency, and benchmark generality?
```

The answer is an oriented pressure jump consumed by an affine face-gradient
operator.

## 3. Continuum law

Fix the phase and orientation convention:

```text
psi = 1 liquid, psi = 0 gas
n_lg = unit normal from liquid to gas
kappa_lg = div_Gamma n_lg
j_gl = p_gas - p_liquid
```

The Young--Laplace law is:

```text
p_liquid - p_gas = sigma kappa_lg.
```

Therefore:

```text
j_gl = -sigma kappa_lg.
```

This sign is not optional. It determines whether surface tension reduces
surface area or amplifies perturbations. For a capillary-wave crest with
positive gasward curvature, the gas-minus-liquid jump is negative and the
initial acceleration is restoring. For a gas bubble in liquid, `kappa_lg < 0`,
so `j_gl > 0` and the gas pressure is higher.

## 4. Discrete affine-jump operator

On an interface-crossing face, define:

```text
s_f = I_gas(high cell) - I_gas(low cell)
B_f(j_gl) = s_f j_gl / d_f
G_Gamma(p; j_gl)_f = G(p)_f - B_f(j_gl).
```

The projection equation can be written in affine form:

```text
D_f alpha_f G_Gamma(p; j_gl)
  = D_f alpha_f G(p) - D_f alpha_f B(j_gl).
```

Equivalently, the known interfacial jump enters the PPE right-hand side through
the same divergence, face coefficient, and gradient locus used by the pressure
correction. This is the balanced-force requirement in operator form: surface
tension and pressure do not live on separate incompatible discretisations.

The manufactured two-cell identity is the local invariant:

```text
if pressure satisfies the jump j_gl, then G_Gamma(p; j_gl) = 0
for both liquid-low/gas-high and gas-low/liquid-high orientations.
```

## 5. Why regular jump decomposition cannot be production

The old method effectively solved:

```text
L(p_base) = rhs - L(J),
p_total = p_base + J.
```

For an initially stationary capillary wave, `rhs ≈ 0`; the elliptic solve then
has the consistent solution `p_base ≈ -J`. The returned pressure is almost zero,
so the capillary impulse disappears before dynamics begin.

The measured one-step ratio:

```text
ptp(p_total) / ptp(J) = 9.022527e-04
```

is decisive because it happens before long-time instability, reinitialisation
history, curvature caps, or high-mode cascades can be primary causes.

## 6. Experimental evidence chain

| CHK | Finding | Interpretation |
|---|---|---|
| CHK-RA-CH14-005 | `jump_decomposition` produced `p_base≈-J` and `p_total≈0` | regular pressure-field jump is algebraically absorbable |
| CHK-RA-CH14-008 | `affine_jump` route added with `G_Gamma=G-B(j)` and targeted tests | correct structural direction |
| CHK-RA-CH14-009 | N=32 short run active, finite, nonzero capillary response | cancellation removed |
| CHK-RA-CH14-010 | N=32, T=10 stopped at `t=4.882542161581` by KE guard | not yet physically validated |
| CHK-RA-CH14-011 | `A''` magnitude matched theory but sign reversed | pressure-jump sign contract is wrong |
| CHK-RA-CH14-012 | oriented generic contract designed | same law covers capillary waves and bubbles |

The N=32, T=10 blow-up diagnostics were:

```text
kinetic_energy: 1.3826e-09 -> 4.6037e+06
div_u_max final/max: 4.0252e+02
ppe_rhs_max max: 2.4387e+07
bf_residual_max max: 3.3686e+07
```

Those late-time quantities are downstream symptoms. The early-time signed
acceleration is the root-cause diagnostic.

## 7. A3 traceability

| Level | Contract |
|---|---|
| Equation | `p_l - p_g = σ κ_lg`, hence `j_gl = p_g - p_l = -σ κ_lg` |
| Geometry | `ψ=1` liquid, `ψ=0` gas, `n_lg` liquid-to-gas, `κ_lg=∇_Γ·n_lg` |
| Discretisation | `G_Gamma(p;j_gl)=G(p)-B(j_gl)` on interface-crossing faces |
| Data contract | store `pressure_jump_gas_minus_liquid`, not raw `sigma*kappa` |
| Code locus | `InterfaceStressContext` builder computes `j_gl`; PPE/corrector consume it |
| Experiment gate | droplets, bubbles, capillary waves, and RT flat interface all use the same closure |

The traceability rule is important: if a future change cannot state which
physical jump it stores, it should not enter production capillary logic.

## 8. Genericity across benchmark families

| Benchmark | Geometry sign | Required jump | Expected physical response |
|---|---:|---:|---|
| liquid droplet in gas | `κ_lg > 0` | `j_gl < 0` | liquid pressure higher; static balance possible |
| gas bubble in liquid | `κ_lg < 0` | `j_gl > 0` | gas pressure higher; no artificial collapse |
| capillary wave crest | gasward curvature positive | `j_gl < 0` | perturbation accelerates back toward flat |
| flat RT interface | `κ_lg = 0` | `j_gl = 0` | capillarity contributes no spurious pressure |

This is why the implementation must not branch on benchmark names. The
benchmark-specific object is only the geometry that produces `κ_lg`; the
interface-stress closure consumes the same `j_gl` everywhere.

## 9. Balanced-force interpretation

The current finding does not say "balanced force is impossible." It says that
balanced force is conditional on a correct physical jump. A perfectly
compatible operator can still inject an unphysical response if the supplied
traction has the wrong sign.

The decisive evidence is:

```text
observed acceleration magnitude ≈ theoretical capillary magnitude,
observed acceleration sign = opposite of Young--Laplace restoring sign.
```

Therefore the next correction is the oriented pressure-jump contract. Smaller
time steps, stronger smoothing, or curvature caps would merely delay the
anti-restoring instability and would violate the theory-first policy.

## 10. Implementation policy

Required:

1. introduce or rename the public field to `pressure_jump_gas_minus_liquid`;
2. compute `pressure_jump_gas_minus_liquid = -sigma * kappa_lg` in one
   Young--Laplace builder;
3. keep `signed_pressure_jump_gradient` as a consumer of the physical jump;
4. verify both face orientations by manufactured two-cell tests;
5. run the same closure through static droplet, gas bubble, capillary wave,
   rising bubble, and flat RT gates.

Forbidden:

- capillary-wave-only sign fixes;
- rising-bubble-only sign fixes;
- hiding instability with CFL reduction or curvature caps;
- changing phase labels to fit a single result;
- preserving `sigma*kappa` as the public API for the pressure jump.

## 11. Acceptance matrix

| Test | Acceptance criterion |
|---|---|
| two-cell jump L→G/G→L | affine face gradient vanishes for a pressure satisfying `j_gl` |
| static liquid droplet | near-zero velocity and higher liquid pressure |
| static gas bubble | near-zero velocity and higher gas pressure |
| capillary-wave short run | early `A'' / (-ω²A0) ≈ 1` |
| capillary-wave long run | bounded energy, correct oscillatory phase, no anti-restoring growth |
| rising bubble with gravity | buoyant rise while capillary sign remains correct |
| rising bubble without gravity | no capillary-induced bulk translation |
| flat RT | `j_gl=0` and no capillary artifact |
| energy audit | surface-energy decrease transfers to kinetic/viscous channels with correct sign |

Only after this matrix passes should §14 present `affine_jump` as a physical
capillary-wave validation rather than as an implementation milestone.

## 12. Conclusion

The research result is sharper than "affine_jump works" or "affine_jump fails."
The structural idea works: the pressure jump must be part of the projection
operator, not a removable regular pressure field. But the physics contract must
be made explicit: the stored jump is `p_gas - p_liquid`, and Young--Laplace
supplies `-σ κ_lg`.

Once that contract is enforced, the same interface-stress logic can serve the
capillary wave and rising bubble without benchmark-specific logic. That is the
minimum theory-respecting path forward.

