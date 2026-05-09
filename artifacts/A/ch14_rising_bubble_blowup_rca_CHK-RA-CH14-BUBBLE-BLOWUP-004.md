# CHK-RA-CH14-BUBBLE-BLOWUP-004

## Question

Identify the shortest theoretical path to the rising-bubble blow-up root cause,
without treating damping, CFL reduction, caps, fallback operators, or benchmark
branches as physics.

Case inspected:

- `experiment/ch14/results/_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p02`
- water/air, `sigma=0.072`, `g=9.81`, `Lx x Ly = 10 mm x 20 mm`
- `Nx x Ny = 32 x 64`, wall boundaries, `closed_interface_riesz`
- continuation from `t ~= 0.01 s`, blow-up guard at `t=0.01803300047319706 s`

## Physical Scale Check

For a radius `R=2.5 mm` bubble in water/air,

```text
Bo = (rho_l-rho_g) g R^2 / sigma ~= 0.85
tau_sigma = sqrt(rho_l R^3 / sigma) ~= 1.47e-2 s
U_buoyancy ~= sqrt(g R) ~= 1.6e-1 m/s
U_capillary_liquid ~= sqrt(sigma/(rho_l R)) ~= 1.7e-1 m/s
```

Thus `t=0.018 s` is a meaningful capillary-inertial time, but velocities of
`1e4 m/s` are not a physical bubble response. The blow-up is numerical.

## Evidence Summary

Timeline from `data.npz`:

```text
t=0.010002616  KE=5.939e-05  max stable speed ~= 3.0e-01 m/s
t=0.017901485  KE=1.756e-04  ppe_rhs_max=1.238e+07
t=0.018002600  KE=1.764e-03  ppe_rhs_max=3.750e+08
t=0.018030835  KE=3.062e+00  ppe_rhs_max=3.857e+10
t=0.018033000  KE=1.745e+06  ppe_rhs_max=4.830e+16
```

The final high-speed mode is symmetric on the bubble sides, localized in the
gas-side interface shell, not at a wall.

## Hypothesis Inventory

### H1: Physical Rayleigh-Taylor/capillary acceleration

Prediction: velocities should remain on the order of buoyancy or capillary
speed scales, unless the physical parameters imply an extreme Weber/Froude
response.

Test: dimensional estimates above.

Result: expected `O(1e-1 m/s)`, observed `O(1e4 m/s)`.

Verdict: rejected as root cause.

### H2: capillary CFL violation

Prediction: the capillary timestep bound should become the failing scale before
the runaway.

Observed: the capillary limiter is active until `step=2454`; the explosive
stage is then advective-limited because velocity is already large. The capillary
jump remains `O(1e3 Pa)`.

Verdict: not the primary cause. Reducing timestep may delay the instability but
does not explain the energy source.

### H3: marching-squares stratum near singularity

Prediction: cut edges should have `|psi_hi-psi_lo| << 1`, causing
`dx_Gamma/dpsi ~ h/|dpsi|` to blow up.

Test on initial, `t~=0.01`, and pre-blow-up fields:

```text
pre-blow-up x-cut min |dpsi| = 4.079e-02
pre-blow-up y-cut min |dpsi| = 5.227e-02
max h/|dpsi| <= 6.76e-03
zero-crossing change count = 0
```

Verdict: rejected for this case. The closed interface stratum is not near a
threshold-touch singularity.

### H4: raw closed-interface Riesz capillary cochain blow-up

Prediction: `M_A^{-1} T^* dS_h` should itself have `O(1e12)` face acceleration.

Direct recomputation from checkpoints with the saved grid:

```text
t~=0.01 raw surface acceleration linf: [6.26e+02, 7.63e+02]
pre-blow-up raw surface acceleration linf: [8.19e+02, 1.76e+03]
final raw surface acceleration linf: [1.16e+03, 2.00e+03]
```

Verdict: rejected. The Riesz cochain is large but bounded at the expected
low-inertia interface scale. It is not the `O(1e12)` object.

### H5: component-volume saddle singularity

Prediction: the component saddle denominator should collapse or coefficients
should diverge before blow-up.

Observed diagnostics:

```text
capillary_component_hodge_denominator ~= O(1e-3)
capillary_component_hodge_coefficient_linf ~= O(10-40)
capillary_corrected_jump_linf ~= O(1e3)
```

Verdict: rejected as root cause.

### H6: PPE solve failure

Prediction: pressure defect correction should fail to reduce the residual and
leave a large divergence.

Observed near runaway:

```text
ppe_dc_final_relative_l2 ~= O(1e-9)
div_u_max remains O(1e-5) to O(1e-3) until the very end
```

Verdict: rejected as initial cause. The huge pressure is a reaction to a huge
predictor/nonlinear mode, not a failed elliptic solve.

### H7: restart/checkpoint bug

Prediction: restart should avoid the same state evolution or use an inconsistent
previous-step history.

Observed checkpoint contents include previous velocity, pressure acceleration,
convection history, pressure state, and projected face components. The runaway
continues from the restored state, and the high-speed pattern is already present
in the pre-blow-up input.

Verdict: not the physics/numerics root cause of this blow-up.

### H8: wall boundary or nonuniform grid coordinate corruption

Prediction: the largest fields should occur near walls or at collapsed grid
intervals.

Observed: high-speed shell is on left/right bubble flanks; `h_min` remains
finite. The cut-edge geometry is regular.

Verdict: not the immediate root. Nonuniform-grid operator compatibility remains
relevant below.

### H9: reinitialization as the primary source

Prediction: reinit should change the zero level set or trigger the energy
growth before the velocity mode appears.

Observed:

```text
reinit_zero_crossing_change_count = 0
reinit_zero_level_displacement = O(1e-6 to 1e-5 m)
reinit_linf_delta grows during the velocity runaway
```

Verdict: secondary amplifier/diagnostic confounder, not the primary source in
this run. Reinit still breaks exact material density transport and must be
included in the final energy accounting.

### H10: single-phase convective operator used in a variable-density problem

Continuum theorem:

For incompressible immiscible flow,

```text
D_t rho = 0,  div u = 0
d/dt int 1/2 rho |u|^2 dV
  = pressure boundary work + viscous dissipation + body/surface work.
```

Therefore the discrete convection update must be skew/transport-consistent in
the same density-weighted mass metric used by the kinetic energy, or must be
paired exactly with the discrete density transport term.

Current UCCD6 theorem is single-phase:

```text
C(u)_j = -1/2[(u . grad) u_j + div(u_j u)] + hyperviscosity
```

It is designed to be skew in an unweighted velocity metric. It is not a
two-phase conservative momentum transport operator using the same face mass
flux as `psi`/`rho` transport.

Energy probe at the stable `t~=0.01` checkpoint:

```text
operator     unit-volume power        rho-volume power
uccd6        -3.028e-07               +1.508e-04
fccd_flux    -2.154e-08               +1.346e-04
fccd_nodal   -3.508e-08               +1.233e-04
```

The same velocity field is dissipative/nearly skew in the unweighted metric,
but injects kinetic energy in the physical `rho dV` metric.

Verdict: strongly supported. This is the first hypothesis that explains why
the run is initially plausible, then develops a localized gas/interface mode,
then the explicit nonlinear term and pressure projection enter a runaway.

### H11: pressure acceleration is the root

At pre-blow-up checkpoint:

```text
p_prev_accel_face_components linf ~= [2.80e+11, 1.68e+12]
conv_prev linf ~= [1.13e+13, 1.10e+12]
state u_linf ~= 1.56e+04
```

These are already after the high-speed velocity mode has formed. The pressure
acceleration is a constraint reaction to the nonlinear predictor and does not
by itself identify the energy source.

Verdict: symptom, not root.

## Root-Cause Identification

The most likely root cause is:

```text
The momentum convection path is not a density-compatible, phase-transport-
compatible, energy-stable two-phase operator.  UCCD6/FCCD convection is
single-phase skew in an unweighted metric, while the rising-bubble kinetic
energy and PPE/corrector use a strongly variable rho metric.  The mismatch
allows positive rho-weighted convective power at the interface.  Capillarity
and buoyancy seed a localized gas-side velocity mode; the variable-density
convection/PPE feedback then amplifies it into blow-up.
```

This also explains why the oscillating droplet and static droplet cases can
look acceptable while the physical water/air bubble fails: the density ratio,
low gas inertia, reinitialized interface shell, and nonuniform grid make the
metric mismatch dynamically active.

## Theoretical Direction

Do not treat this with damping, caps, lower CFL as the answer, DCCD velocity
suppression, pressure clipping, or fallbacks.

The correct line of attack is to derive a two-phase momentum transport operator
with the following discrete identity:

```text
<u, C_h(rho, u)>_{M}
  + 1/2 <|u|^2, D_h(rho u)>_{M_cell}
  = boundary flux - D_h^{num}(u) <= boundary flux
```

where the mass flux `rho u` is built from the same CCD/FCCD/UCCD-compatible
transport geometry as `psi`, and where `D_h^{num}` is an explicitly designed
nonnegative high-order dissipation, not an accidental stabilizer.

Required compatibility:

- same face flux topology as FCCD/CCD transport and projection;
- same nonuniform-grid control measures in the kinetic-energy pairing;
- works with wall and periodic axes;
- retains GPU-first array operations through `backend.xp`;
- fail-close if the energy identity cannot be assembled for the selected
  boundary/grid/operator combination.

DCCD/FCCD/UCCD should be used as structure-preserving building blocks, not as a
post-hoc projector that hides an energy-inconsistent convective pump.
