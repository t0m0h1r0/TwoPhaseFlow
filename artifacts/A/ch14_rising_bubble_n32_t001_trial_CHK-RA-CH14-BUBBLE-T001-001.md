# CHK-RA-CH14-BUBBLE-T001-001: rising bubble N=32x64, T=0.01 trial

## Configuration

Temporary reproducibility YAML:

```text
experiment/ch14/config/_tmp_ch14_rising_bubble_n32_t001.yaml
```

The probe uses the current Chapter 14 rising-bubble stack:

```text
domain = 10 mm x 20 mm
grid   = 32 x 64
rho_l/rho_g = 1000.0 / 1.2
mu_l/mu_g   = 1.0e-3 / 1.8e-5
sigma       = 0.072
gravity     = 9.81
T           = 0.01 s
momentum_form = primitive_velocity
```

The production YAML also now states `run.momentum_form: primitive_velocity`
explicitly.  This documents that the new conservative-common-flux route is
not yet wired into the full NS predictor/projection path.

## Run Outcome

The simulation reached `t=0.01` and saved:

```text
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/data.npz
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/checkpoint_final.npz
```

The first full `make cycle` failed only during pressure visualization:

```text
pressure_hodge cannot represent the saved affine face cochain as a scalar
pressure field: relative same-phase gradient residual 5.422822e-02 exceeds
1.000000e-02
```

This is a correct fail-close.  The affine jump face cochain is not sufficiently
integrable as a scalar Hodge pressure representative for this case.  The YAML
was therefore updated to plot the stored scalar `pressure` field as a gauge
field, rather than relabeling a nonintegrable face cochain as physical
pressure.  Plot-only regeneration then succeeded.

## Key Metrics

```text
steps                         1359
t_final                       1.000000e-02
volume_conservation_final     7.655634e-05
volume_conservation_max       7.805083e-05
yc_initial                    5.000540e-03
yc_final                      5.180365e-03
mean_rise_velocity_final      4.971627e-02
deformation_initial           3.091378e-01
deformation_final             3.119929e-01
kinetic_energy_final          5.936032e-05
div_u_max_final               6.160780e-06
div_u_max_over_run            1.613393e-05
kappa_max_over_run            2.586420e+03
dt_capillary_range            7.071088e-06 .. 7.369288e-06
capillary_contract_gate_code  0
```

The defect-correction PPE used all 12 corrections and did not mark
`ppe_dc_converged`, but its final relative L2 residual stayed below
`8.13e-08`.  This should be tracked separately from blow-up.

## Generated Figures

```text
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/bubble_centroid_y.pdf
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/mean_rise_velocity.pdf
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/volume_drift.pdf
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/deformation.pdf
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/psi_t*.pdf
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/velocity_t*.pdf
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t001/pressure_t*.pdf
```

## Interpretation

For this short trial, the run is numerically finite and physically plausible
at the coarse-grid taste-test level: the bubble rises by about `0.18 mm` in
`0.01 s`, velocity grows from rest, and volume drift remains below `8e-5`.

The important remaining warning is not immediate blow-up; it is consistency of
the momentum transport route.  This run still uses `primitive_velocity`.
The conservative common-flux route has been implemented and unit-verified, but
the full NS integration is intentionally fail-closed until the predictor,
projection, restart, and visualization paths all consume the conservative
state.
