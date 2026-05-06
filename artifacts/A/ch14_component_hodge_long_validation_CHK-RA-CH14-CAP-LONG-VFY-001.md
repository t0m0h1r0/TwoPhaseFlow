# CHK-RA-CH14-CAP-LONG-VFY-001: component-hodge long validation

Date: 2026-05-07  
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`  
Scope: decide whether the visually plausible `component_hodge_augmented`
ch14 droplet results are physically credible, using static equilibrium,
Rayleigh-Lamb phase/amplitude, energy, velocity, pressure, and reinit
separation.

## Principle

The judgement must be made in face-cochain space, not by asking whether the
interface is a circle or an ellipse.  For a closed component, a constant
Young-Laplace reaction belongs to the augmented pressure-reaction space, while
arbitrary resolved nonconstant curvature modes must retain a nonzero Hodge
drive.  Therefore the meaningful question is

```text
does the capillary cochain have a nonzero quotient residual after removing
range(A G) and component pressure reactions?
```

The initial ellipse is only a convenient Rayleigh-Lamb probe.  It is not a
classifier and not part of the production theorem.

## Remote-first runs

The sandbox cannot reliably reach the remote without the explicit agent
socket, so all remote experiments used:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS="..."
```

Runs completed:

| Case | Config | Result directory |
|---|---|---|
| static N32/T10, reinit off | `_tmp_ch14_static_droplet_n32_t10_component_hodge` | `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t10_component_hodge` |
| oscillating N32/T10, reinit every step | `_tmp_ch14_oscillating_droplet_n32_t10_component_hodge` | `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t10_component_hodge` |
| oscillating N32/T10, reinit off | `_tmp_ch14_oscillating_droplet_n32_t10_component_hodge_noreinit` | `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t10_component_hodge_noreinit` |
| oscillating N32/T20, reinit off | `_tmp_ch14_oscillating_droplet_n32_t20_component_hodge_noreinit` | `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t20_component_hodge_noreinit` |
| static N16/T1, reinit off | `_tmp_ch14_static_droplet_n16_t1_component_hodge` | `experiment/ch14/results/_tmp_ch14_static_droplet_n16_t1_component_hodge` |
| static N64/T1, reinit off | `_tmp_ch14_static_droplet_n64_t1_component_hodge` | `experiment/ch14/results/_tmp_ch14_static_droplet_n64_t1_component_hodge` |

## Static droplet

| N | final KE | max KE | max snapshot speed | max corrected Hodge weighted L2 | max volume drift |
|---:|---:|---:|---:|---:|---:|
| 16 | `1.490637e-07` | `1.490637e-07` | `9.070593e-05` | `8.428385e-04` | `1.223563e-15` |
| 32 | `5.284015e-09` | `5.284015e-09` | `2.492200e-05` | `2.814614e-04` | `1.903440e-15` |
| 64 | `1.138320e-09` | `2.542873e-09` | `1.941430e-05` | `5.893873e-04` | `3.159875e-15` |

Figure:

```text
experiment/ch14/results/ch14_component_hodge_static_n16_n32_n64_residual_trend.png
experiment/ch14/results/ch14_component_hodge_static_n16_n32_n64_residual_trend.pdf
```

Reading: the static droplet remains shape/volume stable and the kinetic
leakage drops strongly from N16 to N32, then more mildly to N64.  However, the
corrected Hodge residual is not monotone in N and the velocity leakage plateaus
between N32 and N64.  This is acceptable as a diagnostic improvement over the
old zero-drive failure, but it is not a theorem-grade static-equilibrium proof.

## Oscillating droplet and Rayleigh-Lamb phase

For N32/T10 with reinit every step:

```text
signed deformation              7.617534e-02 -> -2.124984e-02
Rayleigh-Lamb reference at t=10 -7.874146e-03
first zero crossing             7.578596
reference first zero crossing   9.381529
final/max KE                    2.174340e-03 / 3.512706e-03
max snapshot speed              1.842288e-02
max corrected Hodge L2          9.018738e-02
max reinit Linf delta           1.803375e-01
```

For N32/T10 with reinit disabled:

```text
signed deformation              7.617534e-02 -> 2.310884e-02
Rayleigh-Lamb reference at t=10 -7.874146e-03
first zero crossing             none by t=10
final/max KE                    5.889060e-04 / 6.247928e-04
max snapshot speed              4.030848e-03
max corrected Hodge L2          7.263806e-03
```

For N32/T20 with reinit disabled:

```text
signed deformation              7.617534e-02 -> -2.228711e-02
Rayleigh-Lamb reference at t=20 -7.454746e-02
first zero crossing             13.393564
reference first zero crossing   9.381529
final/max KE                    4.117141e-05 / 6.247928e-04
max snapshot speed              4.030848e-03
max volume drift                1.456973e-14
```

Figures:

```text
experiment/ch14/results/ch14_component_hodge_n32_t10_2d_snapshots.png
experiment/ch14/results/ch14_component_hodge_n32_t10_velocity_vectors.png
experiment/ch14/results/ch14_component_hodge_n32_t10_pressure_hodge.png
experiment/ch14/results/ch14_component_hodge_n32_t10_reinit_comparison.png
experiment/ch14/results/ch14_component_hodge_n32_rayleigh_reinit_comparison.png
```

Reading: the velocity vectors and pressure field are coherent and nonzero, so
the old `range_projected` algebraic freeze is gone.  But the Rayleigh-Lamb
phase is not yet correct.  Reinit every step drives the first zero too early
and produces much larger kinetic energy and Hodge norm.  With reinit disabled,
the motion is cleaner but too slow and too damped by T20.  Therefore the
visual agreement is not sufficient evidence of physical correctness.

## Verdict

`component_hodge_augmented` is a valid first production slice because it
removes exactly the constant component pressure reaction from the capillary
quotient space instead of deleting all Hodge drive.  It fixes the decisive
zero-drive symptom: the oscillating droplet now moves with nonzero velocity,
pressure, and kinetic energy.

It is not the final capillary force.  Two independent failures remain:

```text
1. Static residual is small but not convergent enough to certify that the
   current scalar face-implicit cochain is T_h^* dS_h.

2. Dynamic phase/amplitude do not match the Rayleigh-Lamb n=2 probe; reinit
   changes the energy/phase strongly, while no-reinit dynamics are too slow
   and damped.
```

The next mathematically honest step is not damping, CFL tuning, smoothing, a
curvature cap, or another range projection.  The next step is to construct or
verify the fixed-stratum transport-adjoint Riesz cochain

```text
s = -M_f^{-1} T^T d(sigma S_h)^T
B =  M_f^{-1} T^T [dV_m]^T
```

and to store the physical transport endpoint separately from the reinit
endpoint so capillary work and reinitialization defects cannot be confused.

## Generated visualization artifacts

```text
experiment/ch14/results/ch14_component_hodge_n32_t10_2d_snapshots.png
experiment/ch14/results/ch14_component_hodge_n32_t10_velocity_vectors.png
experiment/ch14/results/ch14_component_hodge_n32_t10_pressure_hodge.png
experiment/ch14/results/ch14_component_hodge_n32_t10_reinit_comparison.png
experiment/ch14/results/ch14_component_hodge_n32_rayleigh_reinit_comparison.png
experiment/ch14/results/ch14_component_hodge_static_n16_n32_n64_residual_trend.png
```

[SOLID-X] Validation/artifact only; no production solver behavior changed in
this checkpoint; no FD/WENO/PPE fallback, damping/CFL workaround, curvature
cap, smoothing, benchmark-name branch, blanket `c -> Pi_R c`, or QP-as-physics
path introduced.
