# SP-AJ: Conservative Common-Flux Energy Ledger for Water-Air Rising Bubbles

**Status**: ACTIVE / implementation target after ch14 rising-bubble blow-up RCA
**Date**: 2026-05-09
**Scope**: ch14 SI water-air rising bubble, conservative momentum form, common-flux transport, pressure metric, reinitialization/remap, energy certificates
**Companion papers**: SP-AF, SP-AI, SP-Z, SP-X

## Abstract

The 10 mm x 20 mm water-air rising-bubble run on a 32 x 64 grid fails near
`t = 0.018033 s` through a near-Nyquist horizontal velocity mode localized in
the interface band.  The physical scales rule out a real bubble transient:
the pre-blowup speed is `O(10^4) m/s`, while the capillary and buoyancy speeds
are `O(10^-1) m/s`.  Therefore the remedy cannot be a smaller CFL, damping,
curvature capping, pressure smoothing, or another filter.  It must be a
discrete mechanics statement that prevents unaccounted energy transfer into
grid-scale interface modes.

This short paper formulates the required remedy as a conservative common-flux
Navier--Stokes route.  The primary state is not primitive velocity but

```text
q_i       liquid fraction,
m_i(q)   = V_i (rho_g + (rho_l-rho_g) q_i),
p_i      = m_i u_i.
```

The admissible step transports `q`, `m`, and `p` by one flux ledger, applies
only conservative reinitialization/remap or fails closed, derives capillary and
gravity impulses from energy variations, applies viscosity through a certified
dissipative stress, and projects velocity by a transported-mass metric.  The
scheme is accepted only when a per-step energy ledger can name the work or
defect of every operator.

## 1. Failure Signature

For a bubble diameter `D = 5 mm` and radius `R = 2.5 mm`,

```text
Eo        = (rho_l-rho_g) g D^2 / sigma = 3.402
t_sigma   = sqrt(rho_l R^3 / sigma)     = 1.473e-02 s
U_sigma   = R / t_sigma                 = 1.697e-01 m/s
sqrt(gD)  = 2.215e-01 m/s
Delta p_h = (rho_l-rho_g) g 20 mm       = 1.960e+02 Pa
Delta p_L = sigma / R                   = 2.880e+01 Pa
```

The saved pre-blowup input has instead

```text
max speed        = 1.559372e+04 m/s
max |pressure|   = 1.946613e+11 Pa
Nyquist fraction = 9.991236e-01
```

The unstable mode is not a smooth rise velocity.  It is an interface-band,
grid-scale horizontal mode with opposite signs on the two lateral flanks of the
bubble.  The root question is therefore:

```text
Which discrete operator injected kinetic energy into a near-Nyquist mode?
```

Any remedy that cannot answer this question is not a physical remedy.

## 2. Conservative State and Energy

Let `q_i` be the liquid fraction in a cell of volume `V_i`.  Define

```text
rho_i(q) = rho_g + (rho_l-rho_g) q_i,
m_i      = V_i rho_i(q),
p_i      = m_i u_i.
```

The discrete energy is

```text
E_h(q,m,p) = K_h(m,p) + sigma S_h(q) + Phi_h(m),
K_h(m,p)   = sum_i |p_i|^2 / (2 m_i),
Phi_h(m)   = sum_i m_i g y_i.
```

On the staggered grid the implementation may store face velocities and face
mass, but the same principle remains: the metric used by transport, forces,
viscosity, and pressure projection must be the metric of the transported mass.

Primitive velocity is insufficient because a level-set or fraction update can
change the mass while leaving `u` apparently unchanged.  At water-air density
ratio this is a large impulse in disguise.

## 3. Admissible One-Step Factorization

An admissible production step has the factorization

```text
(q^n,m^n,p^n)
  -- C_h --> (q^T,m^T,p^T)
  -- R_h --> (q^R,m^R,p^R)
  -- F_h --> (q^R,m^R,p^*)
  -- P_h --> (q^{n+1},m^{n+1},p^{n+1}),
```

where:

```text
C_h common-flux conservative transport,
R_h conservative reinitialization/remap, or fail-close,
F_h variational/dissipative force impulse,
P_h transported-mass pressure projection.
```

The scheme is theorem-grade only if each arrow has a work identity or an
explicitly bounded defect.  A run that merely survives does not certify the
mechanics.

## 3.1 Algebraic Formulation

Let `C` be the set of cells and `F` the set of oriented faces.  Use

```text
V_c       diagonal cell-volume matrix,
D        finite-volume face-to-cell divergence, D : R^F -> R^C,
P_f      cell-to-face interpolation/restriction used by the transport flux,
M_f(q)   diagonal transported face-mass metric,
```

where `D` already includes the oriented face areas and cell volumes used by the
production finite-volume update.  The cell inner product is

```text
<a,b>_C = a^T V_c b,
```

and the face velocity inner product is

```text
<u,w>_{M_f} = u^T M_f(q) w.
```

The conservative state space is

```text
Q_h = { q in R^C : 0 <= q_i <= 1 },
M_h(q)_i = V_i (rho_g + Delta rho q_i),
P_h(q) = { p : p_i = M_h(q)_i u_i }.
```

For staggered storage, `p` may be represented on faces as `p_f=M_f(q)u_f`.
The formulation only requires that the same positive metric `M_f(q)` be used
by momentum forces and pressure projection.

### 3.1.1 Flux Ledger

A common-flux ledger for one physical step is

```text
L_h = { alpha_rs, beta_r, F_q^r, F_V^r, U_up^r }_{r=0}^{s-1}.
```

Here `F_q^r` is the liquid-fraction flux, `F_V^r` is the geometric volume flux,
and `U_up^r` maps the conservative state at stage `r` to the upwind velocity
used by momentum transport.  The mass and momentum fluxes are not independent
fields:

```text
F_m^r = rho_g F_V^r + Delta rho F_q^r,
F_p^r = F_m^r U_up^r.
```

The stage update is admissible only if

```text
q^{r+1} = sum_s alpha_rs q^s - dt beta_r D F_q^r,
m^{r+1} = sum_s alpha_rs m^s - dt beta_r D F_m^r,
p^{r+1} = sum_s alpha_rs p^s - dt beta_r D F_p^r,
m^{r+1} = M_h(q^{r+1}).
```

The last equality is the consistency gate.  If the transported mass and the
mass induced by the transported phase disagree beyond tolerance, the stage is
not a conservative common-flux stage.

### 3.1.2 Transport Energy Defect

Define

```text
K_c(m,p) = sum_i |p_i|^2 / (2 m_i).
```

For each accepted transport stage the ledger reports

```text
eps_T^r = K_c(m^{r+1},p^{r+1})
        - sum_s alpha_rs K_c(m^s,p^s).
```

The pure-transport gate is

```text
eps_T^r <= tau_T^r.
```

For exact conservative upwind transport `tau_T^r` is the declared numerical
diffusion/roundoff allowance.  A positive unbounded `eps_T^r` means the flux
transport itself has injected kinetic energy.

### 3.1.3 Reinitialization/Remap Operator

The representation map is

```text
R_h(q^T,m^T,p^T) = (q^R,m^R,p^R).
```

It is admissible only when

```text
m^R = M_h(q^R),
1^T V_c q^R = 1^T V_c q^T + eps_V,
1^T p^R     = 1^T p^T     + eps_P,
K_c(m^R,p^R) - K_c(m^T,p^T) = eps_R,
```

with named tolerances and with `eps_R` included in the step energy ledger.
When these identities cannot be certified, `R_h` must fail closed.

### 3.1.4 Variational Force Operators

Let `T_q(q) : R^F -> R^C` be the differential of the production phase
transport with respect to face velocity:

```text
delta q = T_q(q) w.
```

For the current conservative face transport,

```text
T_q(q) w = -D( (P_f q) w )
```

up to the same limiter/upwind linearization selected by the ledger.  Let
`g_S(q)` be the cell covector satisfying

```text
dS_h(q)[delta q] = <g_S(q), delta q>_C.
```

The capillary acceleration cochain is the mass-Riesz representative

```text
a_sigma(q) = -sigma M_f(q)^{-1} T_q(q)^T V_c g_S(q).
```

Equivalently,

```text
<a_sigma,w>_{M_f} + sigma dS_h(q)[T_q(q)w] = 0
```

for all admissible face velocities `w`.  This is the force definition; sampled
curvature is only a possible diagnostic representative of this covector.

Gravity is the variation of

```text
Phi_h(m) = 1^T (m * g y),
```

so the face acceleration `a_g` is obtained by the same mass projection from the
cell potential gradient.  Viscosity is a linear or nonlinear operator `A_mu(q)`
that must satisfy

```text
<u, A_mu(q)u>_{M_f} <= 0.
```

The force predictor in velocity form is

```text
u^* = u^R + dt (a_sigma + a_g + a_mu),
p^* = M_f(q^R) u^*.
```

In cell-momentum form the same equation is read after the face/cell transfer
operators have been fixed; the metric and transfer must be recorded in the
ledger.

### 3.1.5 Reaction-Space Decomposition

Let `G = M_f^{-1} D^T W_c` be the pressure-gradient acceleration operator, with
`W_c` the cell pressure weight used by the PPE.  Let `B` collect component
volume-reaction accelerations, for example

```text
B_l = M_f^{-1} T_q(q)^T V_c g_{V_l}(q),
dV_l(q)[delta q] = <g_{V_l}(q), delta q>_C.
```

Define

```text
X = range([G B]).
```

The admissible capillary drive is decomposed by the `M_f`-orthogonal projection

```text
a_sigma = Pi_X^{M_f} a_sigma + H_X^{M_f} a_sigma.
```

`Pi_X^{M_f} a_sigma` is pressure/component reaction.  `H_X^{M_f} a_sigma` is
the non-reaction drive.  This decomposition is diagnostic/constraint
bookkeeping; it is not permission to replace the production force by a
pre-projected cochain before the variational force has been constructed.

### 3.1.6 Pressure Projection KKT System

Given `u^*`, the pressure projection is

```text
min_u  1/2 (u-u^*)^T M_f (u-u^*)
such that D u = 0 and C_b u = b_b.
```

With boundary constraint matrix `C_b`, the KKT system is

```text
M_f(u^{n+1}-u^*) + D^T pi + C_b^T lambda = 0,
D u^{n+1} = 0,
C_b u^{n+1} = b_b.
```

For homogeneous boundary notation this reduces to

```text
D M_f^{-1} D^T pi = D u^*.
```

The new conservative momentum is

```text
p^{n+1} = M_f(q^R) u^{n+1},
q^{n+1} = q^R,
m^{n+1} = M_h(q^{n+1}).
```

The pressure step reports

```text
eps_Pi = K_f(M_f,u^{n+1}) - K_f(M_f,u^*) <= 0 + tau_Pi.
```

### 3.1.7 Whole-Step Acceptance Inequality

The accepted step satisfies

```text
E_h^{n+1} - E_h^n
  <= sum_r eps_T^r
   + eps_R
   + eps_sigma
   + eps_g
   + eps_mu
   + eps_Pi
   + tau_round,
```

where the ideal signs are

```text
eps_sigma = 0      for reversible capillary work,
eps_g     = 0      for conservative gravitational work,
eps_mu    <= 0     for viscosity,
eps_Pi    <= 0     for projection.
```

The high-frequency interface-band monitor is a certificate field:

```text
H_k = ||Pi_high Chi_Gamma u||_{M_f}^2 / ||Chi_Gamma u||_{M_f}^2.
```

It never modifies `u`.  It only identifies a violation when `H_k` grows without
an admissible positive energy entry in the ledger.

## 4. Common-Flux Transport

Let the interface transport produce a stage flux `F_q`.  The mass flux must be
derived from the same ledger:

```text
F_m = rho_g F_V + (rho_l-rho_g) F_q,
```

where `F_V` is the geometric volume flux on the same face, time stage, and
boundary convention.  Momentum is transported by the same mass flux:

```text
F_p = F_m u_up.
```

For a single forward Euler substep this gives

```text
q^T = q^n - dt D F_q,
m^T = m^n - dt D F_m,
p^T = p^n - dt D F_p.
```

For FCCD/UCCD multi-stage updates this identity must hold stage-by-stage.  It
is not enough that endpoint volume appears conserved.  The same stage flux
that moves the interface must move the density and the momentum.

The pure transport certificate is

```text
K_h(m^T,p^T) <= K_h(m^n,p^n) + eps_T.
```

If this inequality fails, the step has created kinetic energy during pure
transport and the responsible face/stage fluxes must be reported.

## 5. Reinitialization Is a Remap, Not a Postprocess

Ridge--Eikonal or any other profile restoration changes the representation of
the interface.  If it changes `q`, it changes `m`.  Therefore the production
operator is not

```text
q -> q',    u unchanged.
```

The admissible operator is a conservative remap

```text
R_h : (q^T,m^T,p^T) -> (q^R,m^R,p^R)
```

with the contract

```text
m_i^R = V_i (rho_g + (rho_l-rho_g) q_i^R),
sum_i V_i q_i^R = sum_i V_i q_i^T       within tolerance,
sum_i p_i^R     = sum_i p_i^T           up to boundary/work terms,
K_h(m^R,p^R) <= K_h(m^T,p^T) + eps_R.
```

If the chosen profile projection cannot provide this remap, the production
route must fail closed.  Continuing with a cleaned interface and a non-remapped
momentum field is not an approximation to the conservative equations; it is an
unmeasured impulse.

## 6. Capillary Impulse

The capillary force is the Riesz representative of surface-energy virtual work.
Let `T_q(q)` map face velocity to the induced phase transport:

```text
delta q = T_q(q) w.
```

Then

```text
f_sigma = - sigma T_q(q)^* d_q S_h,
```

where the adjoint is taken in the same mass/face metric used by the momentum
equation.  This formulation does not ask whether the interface is a circle,
ellipse, capillary wave, or bubble.  It asks whether the current trace is a
constrained critical point of the same discrete surface energy.

Pressure and component reactions may be separated only after constructing the
full variational cochain:

```text
X       = [ range(M_f^{-1}D_f^T), component-volume reaction columns ],
h_sigma = (I - Pi_X^M) f_sigma.
```

This is not the old production replacement `c_sigma -> Pi_R c_sigma`.  The old
replacement can algebraically delete the physical release acceleration.  Here
projection is a reaction-space decomposition in the correct metric.

## 7. Gravity and Buoyancy

Buoyancy must be read from the potential energy

```text
Phi_h(m) = sum_i m_i g y_i.
```

The gravity impulse is the negative variation of this potential with respect to
the transported mass.  The certificate is not simply a rise velocity; it is the
work balance

```text
Delta K_g + Delta Phi_g = eps_g.
```

At density ratio `O(10^3)`, a mismatch between phase transport and mass
transport can appear as a large artificial gravitational work term.  This is
why the gravity operator must consume the conservative state rather than a
separately reconstructed density field.

## 8. Viscosity

The viscous operator is admissible when its discrete stress is dissipative in
the current metric:

```text
<u, L_mu(q) u>_{M_f} <= 0.
```

CCD, FCCD, and UCCD ingredients are allowed, but the name of the stencil is not
the proof.  The proof is the signed viscous work.  Defect correction is allowed
only when the residual defect keeps the certified viscous work non-positive
within tolerance.

## 9. Pressure Projection and History

Pressure is a Lagrange multiplier for the incompressibility constraint.  The
projection step is the mass-metric minimization

```text
u^{n+1} = argmin_{D u = 0, BC} 1/2 ||u-u^*||^2_{M_f}.
```

Equivalently,

```text
M_f(u^{n+1}-u^*) + G pi = 0,
D u^{n+1} = 0.
```

The projection cannot increase kinetic energy in the projected metric:

```text
K(M_f,u^{n+1}) <= K(M_f,u^*).
```

Affine pressure history must live as the same face impulse/cochain used by this
projection.  A scalar pressure plot is only a representative when the face
cochain is integrable in the active phase graph and metric.

## 10. CCD/FCCD/UCCD Roles

The conservative remedy is compatible with the CCD family if roles are fixed:

```text
FCCD : phase/geometric flux ledger and incidence structure,
UCCD : optional high-order conservative momentum flux evaluator,
CCD  : viscous/stress and elliptic operators with work certificates,
DCCD : diagnostic or certified projection, never an unexplained damper.
```

The orthogonality requirement is between physical contracts:

```text
transport        conservative common flux,
capillarity      surface-energy variation,
gravity          potential-energy variation,
viscosity        dissipative stress,
pressure         mass-metric constraint projection,
reinitialization conservative remap or fail-close.
```

No operator may consume a state produced by an incompatible flux or metric and
still claim the energy theorem.

## 11. Rejected Remedies

The following ideas remain useful as controls or diagnostics, but not as
solutions:

```text
smaller CFL,
velocity damping,
pressure smoothing,
curvature caps,
velocity clipping,
PPE fallback,
FD/WENO fallback,
turning off affine history,
turning off reinitialization,
range-projecting capillarity as the production force,
benchmark-specific branches.
```

They can delay, hide, or localize the failure.  They do not prove why the
interface-band high-frequency mode cannot receive unaccounted energy.

## 12. YAML Contract

The YAML surface should expose the mathematical contract, not a bag of
independent switches.  The intended production shape is:

```yaml
run:
  momentum_form: conservative_common_flux

numerics:
  conservative_transport:
    strict: true
    energy_certificate: strict
    high_k_monitor: fail_close
  pressure:
    projection_metric: transported_face_mass
    history_storage: face_impulse_cochain
  capillary:
    force_form: surface_energy_adjoint
    reaction_projection: diagnostic_or_constraint
  reinitialization:
    remap: conservative_qmp_or_fail
```

Config validation must reject invalid mixtures:

```text
conservative_common_flux requires q,m,p restart state,
conservative_common_flux requires a common flux ledger,
conservative_common_flux requires transported-face-mass projection,
conservative_common_flux forbids q-only production reinit,
conservative_common_flux forbids silent velocity/pressure filtering.
```

## 13. Production Certificate

Each accepted step must emit a ledger such as:

```text
Delta K_transport
Delta K_reinit
Delta K_capillary + sigma Delta S
Delta K_gravity + Delta Phi
viscous_work
Delta K_projection
high_k_energy_fraction
certificate_status
```

The high-k monitor is not a filter.  It is a fail-close witness.  If a
near-Nyquist interface mode grows, the ledger must identify the substep that
fed it or reject the step as non-certified.

## 14. Conclusion

The remedy for the SI rising-bubble blow-up is not to suppress the final
velocity ring.  The remedy is to remove the algebraic freedom that lets the
ring acquire energy without being charged to transport, reinitialization,
capillarity, gravity, viscosity, or projection.

The production target is therefore:

```text
conservative common-flux Navier--Stokes
+ conservative q,m,p remap or fail-close
+ variational surface and gravitational work
+ dissipative viscous stress
+ transported-mass pressure projection
+ face-cochain pressure history
+ per-step energy/high-k certificate.
```

Only after this route is wired should rising-bubble long runs be interpreted as
physical validation rather than as survival tests.
