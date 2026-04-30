# CHK-RA-CH14-005 — capillary-wave root-cause probe

## Core Measurements

- Result NPZ: `/Users/tomohiro/Downloads/TwoPhaseFlow/experiment/ch14/results/ch14_capillary/data.npz`
- Steps recorded: `19525`; snapshots: `701`
- `dt = 1.792640597458e-03`, `T = 35`, inviscid period `T_omega = 16.632565583`
- Expected velocity scale `A0 omega = 3.777640e-03`
- Observed max snapshot `||u||_inf = 1.061779e-04` (`2.811%` of scale)
- Expected smooth pressure-jump amplitude `sigma A0 k^2 = 1.136978e-01`
- Initial saved pressure range `ptp(p) = 2.139760e-04` (`0.188%` of expected jump amplitude)
- Signed `m=2` mode: `1.000258e-02 -> 1.046510e-02`; zero crossings `0`
- Unsigned amplitude: initial `1.051025e-02`, final `2.315156e-02`, max `2.350395e-02`
- Volume drift max `1.217103e-05`; kinetic max `8.064809e-09`; div max `1.604518e-05`
- `kappa_max` cap hit count `17575 / 19525`
- Interface high-mode/m=2 spectral ratio: initial `1.492e-03`, final `4.774e-01`, max `4.860e-01`

## One-Step Algebraic Probe

- `max|kappa| = 1.951121e+00` before clipping-driven later-time cap saturation
- Constructed jump proxy `J = sigma kappa (1-psi)`: `ptp(J) = 2.371575e-01`
- Returned total pressure after PPE: `ptp(p_total) = 2.139760e-04`
- Cancellation ratio `ptp(p_total) / ptp(J) = 9.022527e-04`
- One-step `||u||_inf = 3.866137e-09`

## Phase-Separated Face Mask Evidence

- `x` faces: cross-phase `12 / 4160` (`0.288%`)
  - density-gradient flux max `2.020354e-05`; cross-phase density flux max `2.020354e-05`
  - phase-separated cross-phase flux is exactly `0` by construction.
- `y` faces: cross-phase `65 / 4160` (`1.562%`)
  - density-gradient flux max `4.808755e-05`; cross-phase density flux max `4.808755e-05`
  - phase-separated cross-phase flux is exactly `0` by construction.

## Interpretation

The primary failure is not CFL instability, viscous overdamping, or insufficient run time.
The capillary-wave drive is algebraically suppressed before it can create the expected
normal velocity.  In the current pressure-jump decomposition the solver forms
`L(p_base)=rhs-L(J)` and then returns `p_total=p_base+J`.  For the initially
stationary wave, `rhs≈0`, so the elliptic solve finds `p_base≈-J`; the returned
pressure range is only about `1e-3` of the represented jump.  The velocity
correction therefore sees almost no capillary pressure gradient.

[SOLID-X] Diagnostic-only script; no production module boundary change.
