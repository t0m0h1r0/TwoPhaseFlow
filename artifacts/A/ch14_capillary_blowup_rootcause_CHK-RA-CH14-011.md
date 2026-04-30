# CHK-RA-CH14-011 — N32/T10 capillary-wave blowup root-cause analysis

- Worktree: `ra-ch14-capillary-rootcause-20260430`
- Branch: `ra-ch14-capillary-rootcause-20260430`
- Latest main intake: `f25fb5d1` merged into this branch as `42f6b6fd`
- Result analyzed: `experiment/ch14/results/ch14_capillary_n32_t10_affine/data.npz`
- Request: ブローアップ原因を物理学・数学理論に基づき，多数仮説を検証して特定する。小手先修正は禁止。

## Physical Reference

For a small-amplitude capillary wave

```text
η(x,t) = A(t) cos(kx),       k = 4π
```

with liquid below and gas above, the gasward normal curvature is

```text
κ_n = -η_xx = k² A cos(kx).
```

The inviscid Young--Laplace jump is

```text
p_liquid - p_gas = σ κ_n,
```

therefore the jump written as `j = p_gas - p_liquid` must be

```text
j = -σ κ_n.
```

The linearized capillary-wave equation is

```text
A'' + ω² A = 0,       ω² = σ k³ / (ρ_l + ρ_g).
```

For the current water-air setup:

- `ω = 3.777640482252e-01`
- `T_ω = 16.63256558346`
- quarter period `T_ω/4 = 4.158141395866`
- expected initial acceleration for `A0 = 0.01`: `A'' = -1.427056761315e-03`

## Run Facts

- Requested final time: `T = 10`
- Actual stop: `step = 884`, `t = 4.882542161581`
- Stop mechanism: runner BLOWUP guard, `kinetic_energy > 1e6`
- `kinetic_energy`: `1.3826117332e-09 -> 4.6036847916e+06`
- `interface_amplitude`: `1.1969774732e-02 -> 7.4962298424e-02`
- `volume_conservation`: max `5.1135973387e-05`
- `div_u_max`: final/max `4.0251579070e+02`
- `ppe_rhs_max`: max `2.4386901085e+07`
- `bf_residual_max`: max `3.3685626110e+07`
- `kappa_max`: curvature cap first hit at `step=101`, `t=0.5637844285`
- Advective limiter first active at `step=869`, `t=4.8489940568`
- Affine path: `ppe_interface_coupling_affine_jump=1` for all steps; legacy `jump_decomposition=0`

## Decisive Sign Test

The signed `m=2` interface coefficient should initially curve downward:

```text
A''_theory = -1.427056761315e-03.
```

A quadratic fit to the first six saved snapshots gives

```text
A''_observed = +1.502517625523e-03.
```

The magnitude is close to theory (`|observed/theory| = 1.052879`), but the sign is reversed.
This is the decisive evidence: the capillary term is acting as anti-surface-tension, not merely too weak/too strong.

## Curvature/Jump Convention Test

From the first snapshot:

- signed interface coefficient: `η_2 = 1.001905477554e-02`
- reconstructed `ψ`-curvature cosine coefficient: `+1.507222011176`
- expected gasward curvature coefficient: `k² η_2 ≈ +1.582`

So the curvature provided by the `ψ`-direct path is gasward curvature to leading sign and magnitude.

But the affine interface-stress contract states:

```text
j = p_gas - p_liquid = σ κ
```

and the face jump code applies that `j` as a signed liquid-to-gas pressure jump. If `κ` is gasward curvature, physics requires

```text
p_gas - p_liquid = -σ κ.
```

Therefore the current affine route uses the opposite Young--Laplace sign for this capillary-wave geometry.

## Hypothesis Matrix

| ID | Hypothesis | Test | Verdict |
|---|---|---|---|
| H01 | Latest `main` was not incorporated | `main` `f25fb5d1` merged as `42f6b6fd` | REJECT |
| H02 | The run only failed because of an arbitrary guard | Guard is `KE>1e6`; `div_u_max=4.0e2`, residuals `O(1e7)` | REJECT |
| H03 | Bulk volume loss caused failure | max volume drift `5.1e-05`, far smaller than kinetic/residual blowup | REJECT |
| H04 | Capillary force is still algebraically cancelled | affine flag `1` all steps; KE grows instead of staying near zero | REJECT |
| H05 | Surface-tension jump sign is reversed | early `A''` has theory magnitude but opposite sign | ACCEPT PRIMARY |
| H06 | `ψ`-curvature sign and jump convention disagree | reconstructed `κ_ψ` is gasward; code uses `j=p_g-p_l=+σκ` | ACCEPT MECHANISM |
| H07 | Curvature cap creates the instability | cap first hits at `t=0.564`, after wrong-sign acceleration already present | CONTRIBUTOR |
| H08 | High-mode curvature pollution causes late failure | high-mode/`m=2` ratio `1.76e-03 -> 2.00` | CONTRIBUTOR |
| H09 | Reinitialization cadence is the primary trigger | every-20-step windows show no singular jump; growth exists before/after | REJECT PRIMARY |
| H10 | CFL capillary time step is too large | wrong-sign acceleration occurs at first snapshots under capillary limiter | REJECT PRIMARY |
| H11 | Advective CFL failure causes blowup | advective limiter starts only at `t=4.849`, after KE exceeds `O(1)` | REJECT PRIMARY |
| H12 | PPE tolerance/GMRES failure is the initial cause | early modal acceleration already sign-wrong; residual explosion is late | REJECT PRIMARY |
| H13 | Divergence error is the initial cause | early divergence transients exist, but modal sign test matches anti-restoring force | CONTRIBUTOR |
| H14 | Density ratio/inertia scale is wrong | observed acceleration magnitude is `1.05×` theory, not orders wrong | REJECT |
| H15 | Wall boundary effects drive the sign | sign error appears at `t<0.25`, before wall-reflection timescale relevance | REJECT |
| H16 | Viscosity is missing/too small | viscosity would damp; it cannot explain anti-restoring acceleration | REJECT |
| H17 | Gravity/buoyancy contaminates the case | config has `gravity: 0.0` | REJECT |
| H18 | Initial condition has wrong mode | extracted signed `m=2` starts at `1.0019e-02`, correct | REJECT |
| H19 | Initial amplitude is too nonlinear | `kA≈0.126`; linear acceleration magnitude is accurately reproduced | REJECT PRIMARY |
| H20 | Output/PDF/NPZ artifact | NPZ fields finite and diagnostics coherent; guard triggered from computed KE | REJECT |
| H21 | GPU serialization/performance change altered physics | GPU90 main changes are output/config/perf path; affine flags and sign evidence are physics-path | REJECT PRIMARY |
| H22 | Phase-separated coefficient masking is still disconnecting faces | affine route bypasses cut-face zeroing; flags confirm affine path | REJECT |
| H23 | Pressure mean gauge causes force error | gauge shifts cannot change pressure gradient sign | REJECT |
| H24 | UCCD6 convection creates the instability | velocity starts from rest; anti-restoring acceleration precedes nonlinear advection | REJECT PRIMARY |

## Causal Chain

1. The capillary wave has positive initial `m=2` displacement.
2. The `ψ`-direct curvature path supplies gasward curvature with positive `m=2` coefficient.
3. The affine jump contract interprets the same curvature as `j=p_gas-p_liquid=+σκ`.
4. Young--Laplace for gasward curvature requires `j=p_gas-p_liquid=-σκ`.
5. The projection therefore applies an anti-restoring capillary pressure jump.
6. The interface mode grows instead of oscillating: zero crossings remain `0` even past the expected quarter period `t≈4.16`.
7. Curvature reaches the configured cap, high modes grow, PPE/BF residuals amplify, divergence becomes large.
8. KE crosses the runner blowup threshold at `t=4.8825`.

## Root Cause

The primary root cause is a sign-convention mismatch between gasward curvature and the affine pressure-jump contract:

```text
current:  j = p_gas - p_liquid = +σ κ_gasward
physics:  j = p_gas - p_liquid = -σ κ_gasward
```

This turns surface tension into anti-surface-tension. Curvature cap saturation, high-mode growth, divergence growth, and PPE/BF residual explosion are downstream amplifiers, not the first cause.

## Non-Negotiable Fix Direction

Do not fix this by lowering CFL, smoothing more, reducing `κ` cap, or making capillary-wave-only logic. The generic interface-stress law must own a single phase/orientation contract:

- either store `κ` as gasward curvature and set `j = -σ κ`,
- or store `κ` as liquid-normal curvature and set `j = +σ κ`,
- then enforce that convention in static droplet, manufactured jump, capillary-wave early acceleration, rising-bubble, and RT tests.

[SOLID-X] Analysis artifact only; no production class/module boundary change.
