# CHK-RA-CH14-012 — oriented generic interface-stress design

- Worktree: `ra-ch14-capillary-rootcause-20260430`
- Branch: `ra-ch14-capillary-rootcause-20260430`
- Trigger: 毛管波ブローアップ根因（CHK-RA-CH14-011）を受け，物理法則を守る汎用対応方法を数学的・原理的に設計する。
- Constraint: 毛管波専用ロジックは禁止。上昇気泡・静止液滴・RT でも同じ interface-stress closure を使う。

## 1. Non-Negotiable Mathematical Convention

Use exactly one orientation convention everywhere:

```text
ψ = 1 in liquid, ψ = 0 in gas
n_lg = unit normal from liquid to gas
κ_lg = ∇_Γ · n_lg
j_gl = p_gas - p_liquid
```

Near a smooth interface represented by the liquid indicator `ψ`,

```text
n_lg = -∇ψ / |∇ψ|.
```

For a graph capillary wave with liquid below and gas above,

```text
η(x,t) = A(t) cos(kx),
n_lg ≈ (-η_x, 1),
κ_lg = -η_xx = k² A cos(kx).
```

For a liquid droplet in gas, `n_lg` is outward and `κ_lg > 0`.
For a gas bubble in liquid, `n_lg` points inward into the bubble and `κ_lg < 0`.

## 2. Physical Law

The traction jump with normal `n_lg` is

```text
(T_g - T_l) n_lg = σ κ_lg n_lg + ∇_s σ.
```

For the current constant-σ, pressure-jump-only path (`τ` terms not yet encoded in the jump),

```text
p_liquid - p_gas = σ κ_lg
j_gl = p_gas - p_liquid = -σ κ_lg.
```

This one formula covers all required cases:

| Case | `κ_lg` | `j_gl = p_g - p_l` | Physical meaning |
|---|---:|---:|---|
| Liquid droplet in gas | `+1/R` | `-σ/R` | liquid pressure higher |
| Gas bubble in liquid | `-1/R` | `+σ/R` | gas pressure higher |
| Capillary wave crest | `+k²A` | `-σk²A` | restoring acceleration |
| Flat RT interface | `0` | `0` | no capillary pressure jump |

So the correction is not “flip for capillary waves”; it is “store and apply the physically oriented pressure jump”.

## 3. Discrete Face Law

For a cut face from low index cell/node to high index cell/node, define

```text
orientation_f = I_gas(high) - I_gas(low)
B_f(j_gl) = orientation_f j_gl / d_f.
```

Then the existing ghost/affine gradient form remains

```text
G_Γ(p; j_gl)_f = G(p)_f - B_f(j_gl).
```

This sign belongs to the ghost-fluid face derivative, not to capillary physics.
It should remain covered by manufactured two-cell tests:

- liquid-low / gas-high with `p_high - p_low = j_gl` gives `G_Γ = 0`;
- gas-low / liquid-high with `p_high - p_low = -j_gl` gives `G_Γ = 0`.

The physics sign belongs upstream in how `j_gl` is computed:

```text
j_gl = -σ κ_lg
```

for the current inviscid pressure-jump closure.

## 4. Required Data Contract

Replace the ambiguous current contract

```text
InterfaceStressContext(kappa, sigma)  ->  internally assumes j = +σ kappa
```

with an oriented contract:

```text
InterfaceGeometry:
    psi
    normal_orientation = "liquid_to_gas"
    curvature_orientation = "liquid_to_gas"
    kappa_lg

InterfaceStressJump:
    pressure_jump_gas_minus_liquid = j_gl
    source = "young_laplace"

InterfaceStressContext:
    psi
    pressure_jump_gas_minus_liquid
    phase_threshold
```

The face-gradient function should consume `pressure_jump_gas_minus_liquid`, not raw `sigma*kappa`.

Recommended API shape:

```text
build_interface_geometry(psi, kappa, orientation="liquid_to_gas")
build_young_laplace_jump(geometry, sigma)
signed_pressure_jump_gradient(context_with_j_gl)
```

`build_young_laplace_jump` is where the physical law lives:

```text
j_gl = -sigma * geometry.kappa_lg
```

No caller should manually multiply `sigma*kappa` and pass it as if the sign were obvious.

## 5. Generic Extension Path

The same contract can later host the full normal-stress jump:

```text
j_gl = p_g - p_l
     = n_lg · (τ_g - τ_l) n_lg - σ κ_lg
```

and tangential traction:

```text
P_t (τ_g - τ_l) n_lg = ∇_s σ.
```

For the current codebase, viscous/tangential slots should remain explicit but zero unless a verified discretization is implemented.
Do not smuggle viscous jumps into capillary-specific branches.

## 6. Why This Is Generic for Rising Bubbles

A rising gas bubble is not a special case:

- gas interior means `ψ≈0` inside and `ψ≈1` outside;
- `n_lg = -∇ψ/|∇ψ|` points from outside liquid into gas;
- a round bubble has `κ_lg < 0`;
- therefore `j_gl = -σ κ_lg > 0`, i.e. `p_gas > p_liquid`, as Young--Laplace requires.

Gravity/buoyancy remains a body acceleration and uses the existing face-force/projection path.
Capillarity remains the same oriented jump.
The rise velocity then comes from the non-capillary force balance plus the same interface-stress closure, not from any bubble-specific pressure-jump sign.

## 7. Implementation Order

1. Add/rename data fields so the stored jump is explicitly `pressure_jump_gas_minus_liquid`.
2. Compute `pressure_jump_gas_minus_liquid = -sigma * kappa_lg` in one builder.
3. Keep face orientation logic `I_gas(high)-I_gas(low)` and `G_Γ=G-B(j)`.
4. Remove/avoid ambiguous wording `j = σ κ` unless the curvature orientation is also specified and matches that sign.
5. Add tests before rerunning large experiments.

## 8. Mandatory Tests

| Test | Purpose | Expected result |
|---|---|---|
| Two-cell manufactured jump, L→G | verifies `B_f(j)` orientation | `G_Γ = 0` |
| Two-cell manufactured jump, G→L | verifies opposite face orientation | `G_Γ = 0` |
| Static liquid droplet | `κ_lg>0`, `j_gl<0` | near-zero velocity, liquid pressure higher |
| Static gas bubble | `κ_lg<0`, `j_gl>0` | near-zero velocity, gas pressure higher |
| Capillary wave early acceleration | linear restoring sign | `A''/(-ω²A0) ≈ 1` |
| Rising bubble without gravity | no artificial rise | centroid stays fixed |
| Rising bubble with gravity | generic coupling | centroid rises with same closure |
| Flat RT interface | capillary null case | `j_gl=0`; no capillary artifact |
| Energy audit | anti-surface-tension rejection | `d(K+σ|Γ|)/dt` not spuriously positive without work input |

## 9. Explicitly Forbidden Fixes

- Do not lower CFL as the primary “fix”.
- Do not increase smoothing or reduce curvature cap to hide anti-restoring physics.
- Do not add `if initial_condition == capillary_wave` sign changes.
- Do not branch on rising bubble vs capillary wave.
- Do not change phase labels per experiment to force a desired sign.
- Do not mix `p_liquid-p_gas` and `p_gas-p_liquid` names.
- Do not keep a raw `sigma*kappa` API without orientation metadata.

## 10. Acceptance Criteria

The design is accepted only if the same generic closure satisfies:

```text
static droplet     -> no parasitic capillary motion
static gas bubble  -> no parasitic capillary motion
capillary wave     -> restoring acceleration and no anti-surface-tension growth
rising bubble      -> buoyancy-driven rise with Young--Laplace sign intact
RT flat interface  -> zero capillary jump when κ=0
```

Any solution passing only capillary waves is rejected.

[SOLID-X] Design artifact only; no production class/module boundary change.
