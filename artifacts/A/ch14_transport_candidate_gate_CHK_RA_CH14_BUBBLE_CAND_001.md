# CHK-RA-CH14-BUBBLE-CAND-001

## Purpose

Execute the next efficient verification step after identifying the
`rho dV`-metric/history interaction.  The question is whether simple
mass-compatible transport candidates close the manufactured energy gate, or
whether the issue is fundamentally the time-history discretization in a
time-varying mass metric.

## Strategy

Use the same control design:

```text
1. constant density + history lag
2. variable density + zero history lag
3. variable density + history lag
```

and compare candidate transport histories offline.

Candidates tested:

```text
baseline_velocity_uccd6_imex
  Current production-style velocity acceleration history:
  2 C_uccd6^n - C_uccd6^{n-1}.

current_only_uccd6
  Diagnostic control: no history extrapolation.

conservative_velocity_imex
  Build mass flux m_f=rho_f u_f, momentum flux m_f u_f,
  convert conservative momentum RHS to velocity acceleration, then extrapolate
  the velocity acceleration.

current_only_conservative_velocity
  Same conservative velocity form, no history extrapolation.

consistent_momentum_history
  Extrapolate mass RHS and momentum RHS together:
  2 F_mom^n-F_mom^{n-1}, 2 rho_t^n-rho_t^{n-1}.

current_only_momentum
  Conservative mass/momentum current-only control.
```

Reusable script:

```text
artifacts/A/ch14_transport_candidate_gate.py
```

Output:

```text
artifacts/A/ch14_transport_candidate_gate_CHK_RA_CH14_BUBBLE_CAND_001/
  candidate_gate.csv
  candidate_gate_summary.json
  candidate_history_gate.pdf
```

## Main Result

At `N=32`, one-cell manufactured history lag:

```text
candidate                              ratio=1 delta      ratio=833 delta
baseline_velocity_uccd6_imex           -5.434e-09         +3.052e-02
conservative_velocity_imex             -1.041e-17         +3.048e-02
consistent_momentum_history            -2.209e-18         +2.986e-02
current_only_conservative_velocity      0.000e+00          0.000e+00
current_only_momentum                   0.000e+00          0.000e+00
current_only_uccd6                      0.000e+00          0.000e+00
```

For density ratio `833`, the history defect grows approximately with lag:

```text
candidate                       shift=0      shift=0.25   shift=0.5    shift=1.0
baseline_velocity_uccd6_imex    0.000e+00    +7.589e-03   +1.525e-02   +3.052e-02
conservative_velocity_imex      0.000e+00    +7.579e-03   +1.523e-02   +3.048e-02
consistent_momentum_history     0.000e+00    +7.511e-03   +1.500e-02   +2.986e-02
```

## Interpretation

The good news:

- Constant density remains closed for all candidates.
- Zero-lag variable density remains closed.
- Current-only mass/momentum forms close the gate.

The important negative result:

```text
Naively making the spatial transport mass-compatible is not enough once an
explicit two-time-level history is introduced.  Even a consistent mass and
momentum RHS history still opens the same variable-density energy channel.
```

Therefore the root cause is not merely the spatial form of `C_h`.  It is the
combination of:

```text
time-varying mass matrix M(rho^n)
+ explicit extrapolation of a nonlinear transport operator evaluated at old
  states
+ measuring the result in the current rho^n dV kinetic-energy metric.
```

This means a fix that only swaps UCCD6 for a conservative flux form is unlikely
to solve the blow-up.  A current-only method closes the diagnostic gate but
would sacrifice the intended second-order IMEX history and is not yet a
mathematically complete production answer.

## Refined Theoretical Requirement

A viable production scheme must provide a discrete energy estimate for a
time-dependent mass matrix:

```text
M^n = diag(rho^n V)
```

and a history update.  In other words, it must control a BDF2/G-stability-like
quantity, not only the instantaneous power:

```text
E_G(q^n,q^{n-1}; M^n, M^{n-1})
```

or use a midpoint/variational transport construction where mass and momentum
are advanced by a common map before velocity is recovered.

Candidate families that remain theoretically plausible:

1. Conservative mass/momentum update with velocity recovery, but using an
   energy-stable variable-mass time discretization rather than naive explicit
   extrapolation.
2. Midpoint/variational ALE transport where `rho`, `rho u`, and kinetic energy
   are transported by the same face map.
3. Fail-close mode for high-density-ratio two-phase runs if the selected
   convection time integrator lacks a variable-mass energy certificate.

Candidate families now deprioritized:

1. "Just replace UCCD6 by conservative flux and keep IMEX-BDF2 history."
2. "Use DCCD/FCCD as a post-hoc velocity/pressure suppressor."
3. "Lower CFL until the explicit history defect is small enough."

## Next Efficient Test

Before touching production source, the next offline gate should implement one
true variable-mass time candidate:

```text
mass/momentum midpoint transport:
  rho^{n+1}, (rho u)^{n+1} from one common face map
  velocity recovered as u^{n+1} = m^{n+1}/rho^{n+1}
```

and evaluate the discrete kinetic-energy change directly:

```text
E^{n+1} - E^n
```

on the same manufactured controls.  This tests the full update rather than an
instantaneous RHS power surrogate.

