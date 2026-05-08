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
