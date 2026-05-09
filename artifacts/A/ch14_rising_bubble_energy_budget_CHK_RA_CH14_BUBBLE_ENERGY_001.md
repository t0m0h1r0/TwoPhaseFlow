# CHK-RA-CH14-BUBBLE-ENERGY-001

## Purpose

Run the first smart verification pass for the SI rising-bubble blow-up:
evaluate discrete energy identities directly on saved checkpoints, without
advancing the PDE or changing the solver.

The target theorem is not a CFL theorem.  For closed walls, the convective
transport part of a two-phase incompressible scheme must not create physical
kinetic energy in the `rho dV` metric once it is paired with the same density
transport used by the interface:

```text
d/dt sum_i 1/2 rho_i |u_i|^2 V_i
  = sum_i rho_i V_i u_i . C_h
    + 1/2 sum_i |u_i|^2 V_i (rho_t)_i
  <= designed numerical flux/dissipation.
```

The probe therefore measures:

- `unit_volume_power = sum V u.C_h`
- `rho_volume_power = sum rho V u.C_h`
- `density_transport_correction = sum 1/2 |u|^2 V rho_t`
- `paired_transport_power = rho_volume_power + density_transport_correction`
- `imex_bdf2_rho_volume_power = sum rho V u.(2 C_h^n - C_h^{n-1})`

## Artifacts

Directory:

```text
artifacts/A/ch14_rising_bubble_energy_budget_CHK_RA_CH14_BUBBLE_ENERGY_001/
```

Files:

- `energy_budget.csv`
- `energy_budget_summary.json`
- `uccd6_energy_metric_probe.pdf`
- `uccd6_imex_history_power.pdf`
- `uccd6_local_rho_power_series.pdf`
- `uccd6_local_paired_transport_power_series.pdf`

Reusable probe:

```text
artifacts/A/ch14_rising_bubble_energy_budget_probe.py
```

Run command:

```text
env HOME=/private/tmp/twophase_home \
    XDG_CACHE_HOME=/private/tmp/twophase_xdg \
    MPLCONFIGDIR=/private/tmp/twophase_mpl_cache \
    PYTHONPATH=src \
    /Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 \
    artifacts/A/ch14_rising_bubble_energy_budget_probe.py
```

## Checkpoints

```text
stable_t0p01
  experiment/ch14/results/_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p01/checkpoint_final.npz

pre_blowup_t0p018033
  experiment/ch14/results/_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p02/checkpoint_pre_blowup_input.npz

final_guard_t0p018033
  experiment/ch14/results/_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p02/checkpoint_final.npz
```

## Main Numbers

UCCD6 production operator:

```text
case                    KE         unit dV      rho dV       density corr   paired       IMEX-BDF2 rho dV
stable_t0p01            5.936e-05  -3.028e-07  +1.508e-04   -1.336e-04    +1.718e-05  +1.786e-03
pre_blowup_t0p018033    8.839e+05  -3.600e+10  -1.410e+13   -2.893e+10    -1.413e+13  -1.314e+15
final_guard_t0p018033   1.745e+06  -9.847e+10  -3.858e+13   -8.775e+10    -3.866e+13  -3.575e+15
```

At the stable checkpoint, all tested convection operators are nearly
skew/dissipative in the unweighted `dV` metric but not in the physical
`rho dV` metric:

```text
operator     unit dV      rho dV       paired
ccd          -7.554e-09   +2.104e-04   +7.681e-05
uccd6        -3.028e-07   +1.508e-04   +1.718e-05
fccd_flux    -2.154e-08   +1.346e-04   +9.368e-07
fccd_nodal   -3.508e-08   +1.233e-04   -1.029e-05
```

The production IMEX-BDF2 explicit history is more revealing than `C_h^n`
alone:

```text
case                    conv_prev rho dV   conv_n rho dV    2conv_n-conv_prev rho dV
stable_t0p01            -1.484e-03         +1.508e-04       +1.786e-03
pre_blowup_t0p018033    +1.286e+15         -1.410e+13       -1.314e+15
final_guard_t0p018033   +3.498e+15         -3.858e+13       -3.575e+15
```

## Interpretation

The first-pass result supports a more specific version of the previous
convection hypothesis:

```text
The dangerous object is not merely instantaneous UCCD6 C_h^n.  The problem is
the combination of a single-phase/unweighted skew convection operator with
variable-density kinetic energy and explicit IMEX-BDF2 history extrapolation.
At t~=0.01, the production history extrapolate already produces positive
rho-weighted kinetic work.  By pre-blow-up, the nonlinear history mode has grown
to O(1e15) power and alternates sign; the current C_h^n is then damping, but the
runaway state already exists.
```

This rejects a naive conclusion that the final instantaneous convection value
is the sole energy source.  It also argues against pressure clipping or DCCD
post-projection as the primary answer: the scheme needs a two-phase
transport-compatible momentum operator and a time integrator whose explicit
history obeys the same energy metric.

Supplementary offline power check from the same checkpoints:

```text
case        pressure actual-sign power   raw Riesz capillary power   gravity y+ power
stable      +7.934e-04                   +6.237e-04                 -9.946e-03
pre-blow    -6.486e+12                   +2.202e+03                 -5.987e-02
final       -1.766e+13                   +3.253e+03                 -2.424e-01
```

At pre-blow-up the pressure reaction and instantaneous convection are both
large and damping in the tested sign convention; raw capillary and gravity are
far too small to explain the `O(1e6)` kinetic energy.  This further points to
the accumulated explicit-history/non-normal mode rather than raw capillary
force or elliptic solve failure.

## Next Verification

The next targeted test should be a manufactured variable-density,
divergence-free flow with closed walls or periodic boundaries:

```text
Given smooth rho(x,y), div u = 0, and no surface force,
check whether sum rho V u.(2C^n-C^{n-1})
and the paired transport power vanish for exact steady advection.
```

If the manufactured test reproduces positive `rho dV` work while constant rho
passes, the root cause is isolated to the two-phase momentum transport/time
integration metric.  If it passes, return to pressure-history face cochain and
viscous BDF2 history as the next suspects.
