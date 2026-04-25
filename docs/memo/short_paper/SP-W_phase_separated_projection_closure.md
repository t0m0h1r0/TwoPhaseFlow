# SP-W: Phase-Separated Projection Closure for Buoyancy-Driven Two-Phase FCCD

## Abstract

The ch13 static α=2 water-air rising-bubble blowup was traced to a discrete
operator mismatch. The pressure Poisson equation used a phase-separated FCCD
operator that cuts cross-phase faces, while the velocity corrector and the
face-native buoyancy residual used harmonic mixture-density pressure fluxes.
This violates the projection identity and leaves an interface-supported
divergence defect. Enforcing the same phase-separated face coefficient in PPE,
predictor residual, and corrector removes the blowup to `T=0.05`.

## 1. Discrete formulation

Let

`L_h(p) = D_f[A_f G_f(p)]`.

For phase-separated PPE,

`A_f = (1/rho)_f^sep`,

where `A_f=0` on faces connecting different phases. A fractional-step update is
projection-consistent only if the same `A_f` appears in the PPE and in the
corrector:

`u^{n+1}_f = u^*_f - dt A_f G_f(p) + dt f_f/rho_f`.

If the PPE uses `A_f^sep` but the corrector uses `A_f^mix`, then

`D_f u^{n+1}_f = -dt D_f[(A_f^mix - A_f^sep)G_f(p)]`,

even when `L_sep(p)=D_f u^*/dt` is solved accurately.

## 2. Buoyancy residual split

The pressure-robust split is

`rho' g = -grad(rho' Phi_g) + Phi_g grad(rho')`.

The face residual implementation must therefore evaluate the hydrostatic
gradient with the same `A_f` and `G_f` as the PPE/projection pair. Otherwise the
split removes a gradient in one discrete space and projects in another.

## 3. q-jump hypothesis

For `q = p + rho' Phi_g`, the phase jump changes as

`[q]_{G-L} = [p]_{G-L} + (rho_g-rho_l)Phi_g`.

This was implemented as an explicit q-jump PoC and tested with and without the
known-jump RHS correction `L_h(J)`. Before face-space coefficient closure, this
did not cure the blowup. After closure, both q-jump and no-q-jump runs reached
`T=0.05`, with no-q-jump slightly cleaner in `div_u`.

Conclusion: q-jump consistency is theoretically meaningful, but it was not the
dominant defect in the observed ch13 blowup.

## 4. Numerical result

Configuration:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_richardson_buoyancyfaceresidualstagesplit_debug.yaml`

Before closure:

- blowup at `step=4`, `t≈0.0109`
- `ppe_rhs≈5.07e+07`, `bf_res≈4.41e+11`, `div_u≈1.60e+08`

After closure:

- reached `T=0.05`
- final `KE=1.119e-05`
- final `ppe_rhs=1.174e+02`
- final `bf_res=1.777e+02`
- final `div_u=4.353e-01`

Long-time visualization run:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_richardson_buoyancyfaceresidualstagesplit_longviz.yaml`

- reached `T=0.5`
- final `KE=9.491e-04`
- final `ppe_rhs=6.565e+02`
- final `bf_res=1.704e+02`
- final `div_u=1.241e+00`
- generated `psi`, velocity, and pressure PDF snapshots every `0.05`

## 5. Practical rule

For two-phase FCCD projection, "same metric" is insufficient. The PPE, residual
body-force split, and corrector must share:

- the same physical grid metric,
- the same face gradient/divergence pair,
- the same wall control-volume rows,
- the same phase-separated face coefficient policy.
