# CHK-RA-CAPWAVE-N32T8-RCA-001 — capillary-wave N=32, T=8 root-cause analysis

Date: 2026-04-30  
Scope: N=32 water--air capillary wave, affine pressure-jump route, fixed non-uniform grid.

## 1. Theoretical invariants used as judges

For a gravity-free capillary wave, the continuum energy law is

```text
E(t) = 1/2 ∫ ρ |u|^2 dV + σ |Γ(t)|,
dE/dt = - viscous dissipation ≤ 0.
```

For the small-amplitude mode `η(x,0)=A0 cos(kx)`, with `mode=2`, `L=1`,
`k=4π`, `σ=0.072`, `ρ_l+ρ_g=1001.2`, the deep-water inviscid reference is

```text
ω = sqrt(σ k^3 / (ρ_l + ρ_g)) = 0.377764,
T_period = 16.633,
T_quarter = 4.158.
```

Thus a correct inviscid-or-weakly-viscous computation should show a restoring
oscillation. Viscosity may reduce energy, but it must not create interface
length or total capillary-plus-kinetic energy.

## 2. Primary observation

The stored diagnostic `interface_amplitude` is a maximum vertical deviation,
not the signed Fourier amplitude of the prescribed `mode=2` wave.

Re-analysis of the saved `ψ=0.5` interface gives:

| metric | first | final / event |
|---|---:|---:|
| diagnostic max deviation | `1.197e-2` | `6.839e-2` at `t=8` |
| signed `mode=2` amplitude | `1.002e-2` | `3.327e-4` at `t=8` |
| `mode=2` zero crossing | — | near `t=4.5`, close to theory quarter-period `4.158` |
| max high-mode amplitude | `~1.7e-5` | `2.277e-2` at `t=8` |
| interface length | `1.003902` | `1.454146` at `t=8` |
| estimated `σ(|Γ|-1)+KE` | `2.809e-4` | `3.493e-2` at `t=8` |

So the fundamental capillary mode is not simply anti-restoring. The failure is
more specific: energy is transferred into high-wavenumber interface wrinkles,
and the discrete surface energy grows by about two orders of magnitude.

## 3. Hypotheses and checks

| ID | hypothesis | check | judgement |
|---|---|---|---|
| H0 | The reported failure is only a diagnostic artifact. | Recomputed signed Fourier mode from saved `ψ`. | Partly true: `interface_amplitude` hides that `A_2` decays/crosses. Not sufficient, because high modes and length truly grow. |
| H1 | Young--Laplace sign is reversed. | `A_2` initially decreases and crosses near the theoretical quarter period. | Rejected as primary. A pure sign error would amplify the fundamental immediately. |
| H2 | This is physical viscous damping. | Water--air viscosity is too small to erase the fundamental by `T=8`; total energy should be non-increasing. | Rejected. Measured surface energy grows strongly. |
| H3 | The density/surface-tension time scale is wrong. | Theory quarter period `4.158`; signed `A_2` crosses near `4.5`. | Mostly rejected. Time scale is close enough to indicate the main restoring sign and scale exist. |
| H4 | Capillary CFL alone is too loose. | `dt` is capillary-limited, but energy grows through operator high modes; no smaller-`dt` sweep yet. | Open contributor, not proven primary. A CFL reduction can mask but not repair a missing energy identity. |
| H5 | Curvature cap causes non-physical dynamics. | `kappa_max` reaches cap at `t=1.423`; geometric zero-contour curvature later exceeds `O(10)`. | Confirmed contributor. The cap breaks Young--Laplace proportionality exactly when high modes appear, but it is likely a symptom/amplifier after curvature noise begins. |
| H6 | Jump curvature is sampled from the wrong object. | `B_f` uses adjacent nodal jump averages; the physical `J_f` should be interface/cut-face curvature. Cut-face count grows `37→81`; cut-face `κ` reaches cap while the fundamental is small. | Strongly supported. The jump source is a band/nodal field, not a variational interface quadrature. |
| H7 | Non-uniform wall/FCCD metric mismatch amplifies high modes. | Uniform-grid T=3.5 control is much better than non-uniform T=3.5 controls. | Strongly supported. Non-uniform mode worsens high-mode length growth and max deviation. |
| H8 | Reinitialization itself is the primary seed. | Non-uniform no-reinit T=3.5 reduces length growth but makes `div_u` and PPE RHS much worse. Reinit46 does not cure high modes. | Rejected as sole cause. Reinit is necessary to maintain projection health, but it interacts with curvature/jump consistency. |
| H9 | `psi_direct_filtered` vs logit curvature is the primary issue. | Runtime path appears to instantiate legacy `CurvatureCalculator`; recomputing legacy and ψ-direct curvature on saved fields gives similar late maxima. | Not primary for this run, but a configuration/implementation mismatch remains. |
| H10 | Volume drift drives the result. | T=8 volume drift is `5.87e-4` while interface length/energy grows far larger. | Rejected as primary. |
| H11 | Surface tension is double-counted as CSF plus affine jump. | `pressure_jump` force path is a null force; PPE/corrector use affine context. | Rejected for this route. |
| H12 | Phase gauge or affine activation is wrong. | Diagnostics: affine flag `1`, legacy jump `0`, phase count/pin count `1`. Static affine tests exist. | Rejected as primary for dynamic wrinkling. |
| H13 | The affine operator is algebraically balanced but not energy-compatible. | Static jump invariants pass, but dynamic `σ|Γ|+KE` grows. | Best top-level explanation. The current operator has no discrete capillary-energy identity. |

## 4. Control runs

All controls are N=32 and use the same pressure-jump affine stack unless noted.

| case | grid / reinit | `dt` | first cap hit | max `div_u` to `t=3.5` | max PPE RHS to `t=3.5` | `Amax` at `t≈3.5` | `A2` at `t≈3.5` | high mode at `t≈3.5` | length at `t≈3.5` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `NU_r20` | non-uniform, every 20 | `5.582e-3` | `1.423` | `4.829e-2` | `1.307e1` | `3.714e-2` | `1.922e-3` | `6.346e-3` | `1.078871` |
| `NU_noR` | non-uniform, no reinit | `5.582e-3` | `0.435` | `4.083e-1` | `1.122e2` | `2.302e-2` | `7.580e-3` | `3.069e-3` | `1.015172` |
| `NU_r46` | non-uniform, every 46 | `5.582e-3` | `0.262` | `1.171e-1` | `3.156e1` | `3.767e-2` | `3.161e-3` | `6.313e-3` | `1.058742` |
| `U_r20` | uniform, every 20 | `1.299e-2` | `0.273` | `5.448e-3` | `6.388e-1` | `5.425e-3` | `1.185e-4` | `1.822e-3` | `1.005341` |

Interpretation:

1. Removing reinit is not acceptable: incompressibility/PPE health degrades.
2. Matching the physical reinit interval (`every_steps=46`) does not remove the
   non-uniform high-mode growth.
3. Uniform grid is substantially healthier, so the non-uniform face metric /
   wall corrector / affine jump coupling is implicated.

## 5. Most likely cause

The current route is correct enough to produce the large-scale restoring
capillary wave, but it is not a discrete variational capillary operator.

The theoretical object is

```text
J_Γ = -σ κ_Γ,
G_Γ p = G p - B(J_Γ),
```

where `κ_Γ` is an interface quantity and the pressure projection should be the
negative variation of the same discrete surface energy that the advected
interface uses.

The implementation instead builds an affine face source from a nodal/band
curvature field:

```text
J_f ≈ 0.5 (J_node,lo + J_node,hi),
B_f = s_f J_f / H_f.
```

This passes static/manufactured jump checks, but for a moving diffuse CLS
interface it has no guarantee that

```text
work by affine pressure jump = - change of discrete σ|Γ|.
```

On the non-uniform wall grid, this inconsistency is amplified by metric and
face-gradient/corrector details. The curvature cap then clips the generated
high curvature, so the high modes are neither physically restored nor
energetically dissipated. That combination explains the observed pattern:

```text
smooth fundamental capillary response
  -> curvature/jump high-mode contamination
  -> cap hit
  -> high-wavenumber interface length growth
  -> diagnostic max-amplitude growth despite A2 decay.
```

## 6. What should not be done

Do not tune a stabilising smoother, lower the cap, or hide the diagnostic.
Those changes can reduce the plotted symptom while violating the governing
energy law. The repair must be judged by the capillary energy identity.

## 7. Theory-first next gates

1. Add an energy audit for capillary wave: `KE + σ(|Γ_h|-|Γ_0|)` must be
   non-increasing up to viscous/time-discretisation tolerance.
2. Replace nodal-band `J_f` with a cut-face/interface quadrature value:
   locate `ψ=0.5` on each cut face, evaluate/interpolate `κ_Γ`, then build
   one shared `B_f`.
3. Define the non-uniform wall corrector as an adjoint face-gradient route
   `G_Γ^adj = G^adj - B^adj`, not only `G^FCCD - B^FCCD`.
4. Treat the curvature cap as a diagnostic guard only; acceptance must not
   depend on clipping the Young--Laplace law.
5. Keep reinit, but validate it by profile/energy residuals, not by step-count
   tuning.

