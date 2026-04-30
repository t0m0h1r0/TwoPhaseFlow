---
ref_id: WIKI-X-039
title: "Affine Jump Interface Stress: Oriented Young--Laplace Contract and ch14 Root Cause"
domain: cross-domain
status: ACTIVE
superseded_by: null
tags: [affine_jump, pressure_jump, young_laplace, balanced_force, capillary_wave, rising_bubble, ch14]
sources:
  - path: artifacts/A/ch14_capillary_rootcause_hypotheses_CHK-RA-CH14-005.md
    description: "Original cancellation diagnosis for legacy jump_decomposition"
  - path: artifacts/A/ch14_affine_interface_stress_implementation_CHK-RA-CH14-008.md
    description: "affine_jump implementation contract and tests"
  - path: artifacts/A/ch14_capillary_n32_short_affine_CHK-RA-CH14-009.md
    description: "N=32 short smoke result showing nonzero capillary response"
  - path: artifacts/A/ch14_capillary_blowup_rootcause_CHK-RA-CH14-011.md
    description: "N=32, T=10 blow-up root-cause analysis"
  - path: artifacts/A/ch14_oriented_interface_stress_design_CHK-RA-CH14-012.md
    description: "Generic oriented interface-stress redesign"
  - path: docs/memo/short_paper/SP-AB_affine_jump_oriented_interface_stress.md
    description: "Short-paper version of the same result"
depends_on:
  - "[[WIKI-X-003]]"
  - "[[WIKI-X-024]]"
  - "[[WIKI-X-029]]"
  - "[[WIKI-T-076]]"
  - "[[WIKI-T-077]]"
consumers:
  - domain: code
    usage: "InterfaceStressContext contract and affine_jump validation gates"
  - domain: experiment
    usage: "ch14 capillary-wave and ch13 rising-bubble acceptance checklist"
  - domain: paper
    usage: "Source memo for replacing provisional §14 capillarity prose"
compiled_by: ResearchArchitect
compiled_at: 2026-04-30
---

# Affine Jump Interface Stress

## Thesis

`affine_jump` is the correct structural direction for sharp capillary coupling,
but it only becomes physical after the pressure jump is given an oriented
Young--Laplace meaning.

The current research result is therefore twofold:

1. the legacy `jump_decomposition` failed because it represented a sharp
   pressure jump as a regular pressure field that the elliptic solve could
   absorb and cancel; and
2. the first `affine_jump` route fixed that algebraic cancellation but exposed
   a deeper sign-contract error: the code supplied `j = +σ κ` as
   `p_gas - p_liquid`, while the oriented Young--Laplace law requires
   `j_gl = -σ κ_lg`.

This is not a CFL issue, not a curvature-cap issue, and not a capillary-wave
special case. It is a mathematical contract issue at the interface-stress
operator boundary.

## 1. What `affine_jump` is

For an interface-crossing face `f`, define:

```text
j_gl = p_gas - p_liquid
s_f  = I_gas(high cell) - I_gas(low cell)
B_f(j_gl) = s_f j_gl / d_f
G_Gamma(p; j_gl)_f = G(p)_f - B_f(j_gl)
```

Here `d_f` is the center-to-center face distance. If the stored pressure already
satisfies the supplied jump, then `G_Gamma` vanishes across a static
interface:

```text
liquid-low / gas-high: p_high - p_low =  j_gl, s_f =  1
gas-low / liquid-high: p_high - p_low = -j_gl, s_f = -1
```

The associated projection operator is affine:

```text
D_f alpha_f G_Gamma(p; j_gl)
  = D_f alpha_f G(p) - D_f alpha_f B(j_gl).
```

Thus the known jump appears as an operator-consistent right-hand-side
contribution, not as an independently discretised body force and not as a
post-solve pressure add-on.

## 2. Why legacy `jump_decomposition` failed

The older decomposition built a regular capillary pressure field `J`, solved

```text
L(p_base) = rhs - L(J),
```

and returned

```text
p_total = p_base + J.
```

For the initially stationary capillary wave, `rhs` is approximately zero, so
the elliptic solve naturally finds `p_base ≈ -J`. The returned pressure is then
nearly zero, and the capillary wave receives almost no restoring impulse.

The decisive one-step diagnostic in CHK-RA-CH14-005 measured:

```text
ptp(p_total) / ptp(J) = 9.022527e-04.
```

That failure is algebraic. It cannot be repaired by tuning time step, output
interval, curvature filters, or visualization scripts.

## 3. What `affine_jump` fixed first

CHK-RA-CH14-008 introduced the `affine_jump` route while preserving legacy
`jump_decomposition` as a comparison path. The important implementation
properties were:

- no post-solve construction of `p_total = p_base + J`;
- no zero mask that removes cut-face jump flux on the affine route;
- global gauge for the cut-face-connected affine solve;
- velocity correction through the same `G_Gamma` face law;
- tests for zero flux when the supplied pressure satisfies the manufactured
  jump and for nonzero cut-face drive in the PPE RHS.

The N=32 short run then confirmed that the route was active, the legacy path
was inactive, no NaN/blow-up occurred, and capillary forcing produced nonzero
velocity/kinetic energy instead of the earlier cancellation.

## 4. What the T=10 run revealed

The longer N=32, T=10 capillary-wave run did not validate the physics. It
stopped at:

```text
step = 884
t    = 4.882542161581
guard: kinetic_energy > 1e6
```

Main diagnostics:

```text
kinetic_energy: 1.3826e-09 -> 4.6037e+06
div_u_max final/max: 4.0252e+02
ppe_rhs_max max: 2.4387e+07
bf_residual_max max: 3.3686e+07
```

The decisive early-time signed-mode test was:

```text
A''_theory   = -1.427056761315e-03
A''_observed = +1.502517625523e-03
|observed/theory| = 1.052879
```

The magnitude is correct to within about five percent, but the sign is
reversed. This is the strongest possible diagnostic: the capillary stiffness
scale is present, but it is driving the mode anti-restoringly.

## 5. Oriented Young--Laplace contract

The only admissible convention is:

```text
psi = 1 liquid, psi = 0 gas
n_lg = unit normal from liquid to gas
kappa_lg = div_Gamma n_lg
j_gl = p_gas - p_liquid
```

Young--Laplace then gives:

```text
p_liquid - p_gas = sigma kappa_lg
j_gl = p_gas - p_liquid = -sigma kappa_lg.
```

Therefore the data contract must not expose an ambiguous raw field named
`sigma*kappa`. It must expose the physical jump:

```text
pressure_jump_gas_minus_liquid = j_gl.
```

The builder may compute that field from curvature, Marangoni stress, imposed
membrane stress, or a future constitutive law, but the projection operator must
consume an already oriented `j_gl`.

## 6. Why this is generic

This contract covers the required benchmark families without branching:

| Case | `kappa_lg` | `j_gl = p_g - p_l` | Consequence |
|---|---:|---:|---|
| liquid droplet in gas | positive | negative | liquid pressure is higher |
| gas bubble in liquid | negative | positive | gas pressure is higher |
| capillary-wave crest | positive gasward curvature | negative | crest is restored |
| flat RT interface | zero | zero | no capillary artifact |

The same `G_Gamma(p; j_gl)` law is used for capillary waves and rising bubbles.
Any solution that introduces `if capillary_wave` or `if rising_bubble` into the
interface-stress logic is a design failure.

## 7. Balanced force is not the blocker

Balanced force is a compatibility principle, not a magic sign oracle. It can
only balance the force it is given. If the supplied Young--Laplace jump has the
wrong sign, a balanced operator will faithfully inject the wrong capillary
response.

The CHK-RA-CH14-011 evidence rejects the interpretation that balanced force is
principally impossible here. The observed acceleration has the correct
capillary magnitude and wrong sign, so the next fix must be the oriented
pressure-jump contract, not a weaker force filter or a smaller time step.

## 8. Implementation guardrails

Required implementation direction:

1. rename or replace ambiguous jump fields with
   `pressure_jump_gas_minus_liquid`;
2. compute Young--Laplace jumps once in a builder:
   `j_gl = -sigma * kappa_lg`;
3. keep `G_Gamma = G - B(j_gl)` and verify both face orientations with a
   manufactured two-cell test;
4. pass the same `InterfaceStressContext` to PPE assembly and velocity
   correction;
5. preserve legacy `jump_decomposition` only as tested legacy/comparison code.

Explicitly forbidden fixes:

- capillary-wave-only sign flips;
- rising-bubble-only sign flips;
- curvature caps as the primary remedy;
- reducing `dt` to hide the wrong-sign instability;
- changing phase labels to make one benchmark pass;
- continuing to pass raw `sigma*kappa` through the public interface-stress API.

## 9. Validation gates

The closure is accepted only when all of the following pass with the same
generic interface-stress path:

| Gate | Required result |
|---|---|
| two-cell manufactured jump, L→G and G→L | `G_Gamma = 0` when pressure satisfies `j_gl` |
| static liquid droplet | near-zero velocity; liquid pressure higher |
| static gas bubble | near-zero velocity; gas pressure higher |
| capillary wave early acceleration | `A'' / (-omega^2 A0) ≈ 1` |
| rising bubble with gravity | buoyant rise with Young--Laplace sign intact |
| rising bubble without gravity | no capillary-driven artificial translation |
| flat Rayleigh--Taylor interface | `j_gl = 0`; no capillary artifact |
| energy audit | surface-energy loss and kinetic-energy gain have the correct sign |

Passing only the capillary-wave gate is insufficient. Passing only the
rising-bubble gate is also insufficient. The purpose of the oriented contract
is to make the whole benchmark family share one physical law.

