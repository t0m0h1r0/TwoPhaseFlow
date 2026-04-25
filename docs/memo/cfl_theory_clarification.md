# CFL theory clarification for TwoPhaseFlow

Date: 2026-04-25

This note is the reference for CFL bookkeeping while the paper text is under
revision.  Do not infer stability limits from the current `paper/` prose unless
the statement is consistent with the primary theory below.

## Primary stability facts

1. **SSP/TVD-RK3 is conditional.**  Shu--Osher / SSPRK3 preserves a strong
   stability property only under the same forward-Euler contractivity condition,
   up to SSP coefficient 1.  If the spatial operator is not forward-Euler TVD or
   monotone, the name "TVD-RK3" does not prove TVD or nonlinear stability.

2. **RK3 absolute-stability constants.**  For the Shu--Osher third-order scheme,
   the scalar stability polynomial is
   `R(z) = 1 + z + z^2/2 + z^3/6`.  Therefore:
   - purely imaginary eigenvalues require `|Im(z)| <= sqrt(3)`;
   - negative-real eigenvalues require approximately `-2.5127 <= Re(z) <= 0`.

3. **AB2 has no finite imaginary-axis stability interval.**  For
   `y' = lambda y`, AB2 is stable only where both roots of
   `r^2 - (1 + 3z/2)r + z/2 = 0` lie in the unit disk.  The stability region is
   tangent to the imaginary axis at the origin; pure central/skew advection is
   therefore not made stable by any positive Courant number.  AB2 momentum
   convection needs enough viscous/upwind/hyperviscous damping, or a separate
   IMEX/eigenvalue stability proof.

4. **Capillary waves impose their own time scale.**  For the shortest resolved
   capillary wave, use
   `dt_cap = C_wave * sqrt((rho_l + rho_g) h_min^3 / (2 pi sigma))`.
   `C_wave = 0.1--0.3` is the Denner--van Wachem wave-resolution range; this
   restriction remains relevant even if surface tension is treated implicitly
   whenever the capillary mode is physically resolved.

5. **Non-uniform compact grids are not certified by scalar CFL alone.**  On
   stretched or wall-bounded compact-difference grids, `h_min` is necessary but
   not sufficient: metric variation and non-normality can create transient
   growth.  Strict certification requires the actual semi-discrete operator
   spectrum/pseudospectrum, or a discrete energy estimate for that operator.

## Runtime timestep budget

For a 2-D explicit step with velocity components `(u, v)`, the necessary
directional Courant scale is

```text
Lambda_adv = max|u| / h_x,min + max|v| / h_y,min
dt_adv     = C_adv / Lambda_adv
```

Using `max(max|u|, max|v|) / h_min` is not the multidimensional CFL condition;
it is too large by up to a factor of the dimension for diagonal flow.

For explicit diffusion in two dimensions,

```text
dt_nu = 1 / (2 nu_max (h_x,min^-2 + h_y,min^-2))
```

which reduces to `h^2/(4 nu_max)` on an isotropic grid.  A true implicit
Crank--Nicolson diffusion solve removes this stability limit for the linear
negative-definite diffusion operator.  A Picard / explicit-trapezoid
approximation does not constitute that proof.

The timestep used by production two-phase runs should therefore satisfy

```text
dt <= min(dt_adv, dt_nu_if_not_truly_implicit, dt_cap, dt_operator)
```

where `dt_operator` is the additional restriction obtained from the actual
FCCD/UCCD/DCCD compact operator spectrum when using non-uniform grids, wall
closures, AB2 momentum convection, or hyperviscosity.

## Judgement for current ch13-style runs

- TVD-RK3 is acceptable for the scalar CLS/psi transport only as an explicit
  Runge--Kutta method; it is not, by itself, a TVD proof for FCCD/DCCD.
- A Courant value such as `C_adv = 0.10` is a conservative engineering setting,
  not a theorem, unless the spatial operator spectrum is shown to lie inside the
  RK3 stability region after scaling by `dt`.
- AB2 momentum convection must not be justified by the RK3 CFL.  It needs a
  separate AB2/viscous/UCCD6 stability budget.
- Non-uniform `alpha > 1` two-phase runs require operator-level stability
  evidence; scalar `h_min` CFL and capillary limits are necessary but not
  sufficient.

## Primary references

- Shu and Osher (1988), JCP 77, 439--471.
- Gottlieb, Shu and Tadmor (2001), SIAM Review 43, 89--112.
- Brackbill, Kothe and Zemach (1992), JCP 100, 335--354.
- Denner and van Wachem (2015), JCP 285, 24--40.
- Denner and van Wachem (2022), JCP 449, 110788.
- Lele (1992), JCP 103, 16--42.
- Visbal and Gaitonde (2002), JCP 181, 155--185.
