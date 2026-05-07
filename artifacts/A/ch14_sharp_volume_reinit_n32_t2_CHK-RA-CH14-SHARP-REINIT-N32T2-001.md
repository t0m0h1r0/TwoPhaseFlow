# CHK-RA-CH14-SHARP-REINIT-N32T2-001 — sharp-volume reinit fix and N32/T2 rerun

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Problem

The short-path RCA found that ch14 oscillating droplet visual volume loss was not a nonuniform-coordinate volume bug. The runtime conserved diffuse CLS mass

```text
M_psi = sum_i psi_i dV_i
```

while the physically visible phase volume is the sharp P1 liquid area

```text
V_Gamma = |{x : psi(x) >= 0.5}|.
```

Ridge-Eikonal reinitialization with the old diffuse-mass correction could move the zero level to restore `M_psi`, producing large sharp-area loss. The N32/T1 2x2 probe before this fix showed reinit-on sharp-area drift of `-19%..-24%` while reinit-off drift was `O(1e-5)`.

## Theory

Reinitialization is a representation projection

```text
q^n --T_h(u_f)--> q_T --Pi_h--> q^{n+1}.
```

`Pi_h` is not physical capillary transport, so it must not silently change the physical phase volume. For an incompressible closed phase, the projection should preserve both:

1. sharp phase volume `V_Gamma`, because this is the physical liquid volume;
2. diffuse CLS mass `M_psi`, because this is the material property carrier used by the solver.

The implemented projection uses two scalar constraints:

```text
phi_sdf -> phi_sdf + lambda
```

for the sharp P1 volume. Since `|grad(phi + lambda)| = |grad(phi)|`, this keeps the Eikonal distance property away from explicitly pinned wall-contact bands. Then it changes only the logistic profile-width scalar to restore `M_psi`, without moving the zero level.

This is not damping, CFL tuning, curvature capping, smoothing, PPE fallback, or name-based circle/ellipse logic. The gate is geometric and works for arbitrary fixed-topology nonconstant-curvature shapes.

## Implementation

Changed `RidgeEikonalReinitializer`:

- added `volume_constraint="diffuse_mass" | "sharp_phase_volume"`;
- kept legacy diffuse-mass behavior as the default;
- added `preserves_sharp_volume` contract for transport;
- in `sharp_phase_volume` mode:
  - compute target `V_Gamma` using the same P1 `liquid_area_2d` geometry as the capillary Hodge work;
  - solve scalar `lambda` for `V_h(phi_sdf + lambda)=V_target`;
  - solve scalar profile scale for `sum psi*dV = M_target` without moving the zero level;
  - fail closed when either scalar bracket cannot be found.

Changed `PsiDirectTransport` / `PhiPrimaryTransport`:

- when reinit has already enforced sharp volume, skip the outer diffuse `apply_mass_correction`; otherwise it would undo the sharp-volume projection by shifting `psi` again.

Changed YAML UX:

```yaml
interface:
  reinitialization:
    profile:
      volume_constraint: sharp_phase_volume
```

Applied to:

- `experiment/ch14/config/ch14_static_droplet.yaml`
- `experiment/ch14/config/ch14_oscillating_droplet.yaml`

Added regression:

- `test_sharp_volume_constraint_preserves_p1_phase_area`

It checks that sharp-volume mode preserves the P1 phase area to `5e-5` relative and diffuse mass to `1e-8` relative on a nonuniform grid.

## Validation

Remote validation:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_ridge_eikonal.py::test_sharp_volume_constraint_preserves_p1_phase_area -q'
```

Due Makefile behavior this ran the full remote test suite:

```text
611 passed, 33 skipped in 42.91s
```

Local hygiene:

```text
git diff --check PASS
```

## N32/T2 experiments

Runs were executed on remote GPU with `TWOPHASE_USE_GPU=1`, in-memory overrides:

```text
grid.NX = grid.NY = 32
run.T_final = 2.0
run.snap_interval = 0.5
```

Results pulled to:

- `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t2_two_constraint`
- `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t2_two_constraint`

The standard visualization PDFs were generated for `psi`, velocity, pressure, kinetic energy, and volume/deformation histories.

## Static droplet result

Static droplet keeps diffuse mass and sharp area nearly fixed; residual KE growth remains.

```text
steps: 203
t_final: 2.0
KE: 8.860700532831e-11 -> 2.432972926545e-06
reported volume_conservation final: 7.613759839623e-16
sharp P1 area rel final: -8.721322e-05
surface length rel final: -4.303797e-05
speed Linf final snapshot: 6.472838608155e-04
deformation: 0 -> 0
```

Interpretation: the reinit-volume defect is not active here because static config has `every_steps: 0`. The remaining KE is the separate static-Hodge/capillary-cochain residual identified in the RCA, not a reinit-volume symptom.

## Oscillating droplet result

Final two-constraint result:

```text
steps: 211
t_final: 2.0
KE: 2.253389973168e-09 -> 1.533218539288e-04
reported volume_conservation final: 6.572278892318e-06
sharp P1 area rel final: +2.882297e-03
surface length rel final: +9.186493e-04
speed Linf final snapshot: 6.419199963182e-03
signed deformation: 7.617534118366e-02 -> 6.683509921006e-02
```

Snapshot-stage physical-grid mass recomputation using `Grid.cell_volumes` semantics:

| t | `M_psi` rel | sharp area rel | surface rel |
|---:|---:|---:|---:|
| 0.009438 | `+0.000000e+00` | `+0.000000e+00` | `+0.000000e+00` |
| 0.503993 | `-4.197631e-07` | `+1.135536e-03` | `+7.519314e-04` |
| 1.008251 | `-1.685415e-06` | `+1.853205e-03` | `+9.581584e-04` |
| 1.503245 | `-3.738141e-06` | `+2.441125e-03` | `+1.007351e-03` |
| 2.000000 | `-6.572279e-06` | `+2.882297e-03` | `+9.186493e-04` |

Compared with the pre-fix reinit-on localization (`-19%..-24%` sharp-area loss by T1), the dominant reinit-induced volume collapse is removed. The remaining `+0.29%` sharp-area drift by T2 is small but not zero; it may be transport/discrete projection error and should be tracked as a gate, not hidden behind `volume_conservation`.

## Negative intermediate checks

Two intermediate checks were useful:

- `sharp_phase_volume` with outer diffuse correction skipped but profile-width not constrained preserved sharp area but made diffuse mass drift by `O(15%)` for the oscillating T2 run.
- setting `eps_scale=1.0` reduced diffuse drift to `O(5%)`, but still did not satisfy both constraints.

Therefore the accepted implementation is the two-scalar projection, not an `eps_scale` tweak.

## Remaining issue

This patch fixes the main reinit-volume mismatch. It does not fix the independent capillary-cochain static equilibrium defect:

```text
P_h(c_sigma + lambda c_V) != 0
```

That is still visible as static KE growth at N32/T2 and must be handled by the actual transport-endpoint `T_h^* dS_h`/static-Hodge work, not by reinit, damping, CFL changes, or curvature smoothing.

## SOLID / policy

[SOLID-X] No C1 violation introduced: the new code is pure numerical projection logic in `src/twophase/levelset`, with config plumbing only in simulation config builders. No solver-core I/O, no tested implementation deletion, no FD/WENO/PPE fallback, no damping/CFL workaround, no curvature cap, no smoothing, no benchmark-name branch, no blanket `c -> Pi_R c`, and no QP-as-physics path.
