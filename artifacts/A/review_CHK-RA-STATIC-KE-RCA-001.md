# CHK-RA-STATIC-KE-RCA-001

## Question

Is the kinetic-energy rise in the `N=32` static-droplet run physically
reasonable?  If not, which mathematical contract is failing?

## Theory Baseline

For a zero-gravity, closed or periodic two-phase system, the continuum energy
identity is

```text
d/dt [ integral 1/2 rho |u|^2 dx + sigma |Gamma| ]
  = - integral 2 mu |D(u)|^2 dx <= 0 .
```

A circular 2-D droplet with fixed liquid volume is the constrained minimizer of
surface energy.  Its static solution is

```text
u = 0,
p_liquid - p_gas = sigma / R = 0.072 / 0.25 = 0.288 .
```

Therefore a persistent KE increase is not a physical static-droplet solution.
At most, a short numerical adjustment may appear; the long-time source must
decay if the discrete Young--Laplace / projection / viscosity chain is
well-balanced.

In the affine pressure-jump route, the stronger discrete statement is face
based:

```text
a_f = beta_f (G_f p - B_f(j)) = 0
```

for a static droplet.  The PPE enforces `D_f a_f = rhs`.  That is not enough:
a nonzero divergence-free face cochain can satisfy the projection equation but
still accelerate the velocity and inject kinetic energy.

## Hypotheses

| ID | Hypothesis | Test / evidence | Verdict |
|---|---|---|---|
| H1 | The KE rise is a physical capillary oscillation. | Static run keeps deformation `0`, volume drift is roundoff, and frozen-interface runs still grow KE. | Rejected. |
| H2 | The rise is caused by liquid-volume loss. | `N=32,T=20` final/max volume drift `6.22e-15/7.36e-15`; all T=2 probes remain roundoff-level. | Rejected. |
| H3 | The PPE/DC solver is simply under-converged. | T=2 debug probes: `ppe_dc_final_relative_l2 <= 2.8e-9`, `ppe_dc_converged=1` for all steps, `div_u_max <= 6.5e-9`. | Rejected. |
| H4 | The CFL is too large. | Runs are capillary-limited by the theory CFL. More importantly, the first frozen-interface step has `ppe_rhs=0`, `D_f a_f ~= 1e-8`, but `a_f != 0`; reducing `dt` would scale the symptom, not remove the nonzero cochain. | Rejected as root. |
| H5 | Dynamic grid rebuild / ALE remap is the sole cause. | T=2 static-grid probe has larger KE than base: `5.956e-4` vs `3.474e-4`. | Rejected as sole cause. |
| H6 | Ridge--Eikonal reinitialization amplifies the problem. | Suppressing fixed reinit lowers T=2 KE from `3.474e-4` to `1.695e-4`; `kappa_max` spikes disappear (`4.0e7` -> `2.69e1`). | Supported as amplifier. |
| H7 | Interface transport is the root cause. | Frozen-interface/static-grid probe still reaches T=2 KE `1.466e-4`. | Rejected as root. |
| H8 | Nonuniform grid metrics are the root cause. | Uniform-grid probe still reaches T=2 KE `2.106e-4` with nonzero face acceleration. | Rejected as sole cause. |
| H9 | The pressure scalar diagnostic is misleading. | True, but insufficient: KE and `pressure_accel_faces` are not scalar-pressure visualization artifacts. | Not root. |
| H10 | The KE diagnostic is an endpoint/periodic duplicate artifact. | Snapshot velocity Linf grows consistently with KE; frozen first-step face acceleration is nonzero before any diagnostic accumulation ambiguity can dominate. | Rejected. |
| H11 | `transport_variational_p2_ale_discrete_gradient` produces a static-circle pressure-jump cochain with excess work. | Frozen T=2 with P2 ALE DG: KE `1.466e-4`, first/final `|a_f|_inf=5.945e-3/6.563e-3`. Replacing only the jump curvature route by `face_implicit` lowers KE to `1.095e-5` and `|a_f|_inf` to `1.137e-3/1.177e-3`. | Strongly supported. |
| H12 | The immediate failure is a face-space Hodge/range residual: nonzero solenoidal `a_f`. | Frozen first step: `ppe_rhs=0`, `|a_f|_inf=5.945e-3`, but recomputed `|D_f a_f|_inf=1.25e-8`. This is a divergence-free nonzero capillary cochain. | Supported; primary localization. |
| H13 | Pressure history / remap history is stale. | Frozen first step has no prior pressure history and no remap history, yet `a_f != 0`. | Rejected as root. |
| H14 | Viscosity/density ratio creates KE by itself. | With no nonzero capillary face cochain there is no energy source; viscosity can only dissipate. Density/viscosity set the response amplitude, not the source. | Rejected as source. |

## Probe Matrix

Remote GPU probes were generated as temporary YAMLs derived from
`ch14_static_droplet.yaml`, with `N=32`, `T=2`, debug diagnostics enabled, and
only ablation fields changed.  Temporary YAMLs were removed after analysis.

| Case | Final KE | Max KE | Face accel first/final | Speed first/final | PPE DC rel max | Div max | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| base | `3.474e-4` | `3.474e-4` | `1.683e-2/6.159e-3` | `1.412e-4/9.750e-3` | `2.345e-9` | `6.408e-9` | Dynamic grid + fixed reinit. |
| static grid | `5.956e-4` | `5.956e-4` | `1.683e-2/1.437e-2` | `1.412e-4/1.498e-2` | `1.768e-9` | `1.107e-9` | Remap is not the sole source. |
| no fixed reinit | `1.695e-4` | `1.695e-4` | `1.683e-2/6.163e-3` | `1.412e-4/4.511e-3` | `2.798e-9` | `8.642e-10` | Reinit amplifies curvature noise. |
| frozen interface | `1.466e-4` | `1.466e-4` | `5.945e-3/6.563e-3` | `3.709e-5/4.175e-3` | `2.568e-9` | `1.233e-10` | Source remains without interface motion. |
| face-implicit frozen | `1.095e-5` | `1.095e-5` | `1.137e-3/1.177e-3` | `9.029e-6/1.361e-3` | `2.298e-9` | `2.851e-11` | P2 ALE DG route is the major excess-work source. |
| uniform | `2.106e-4` | `2.106e-4` | `4.047e-1/7.375e-3` | `4.757e-3/5.938e-3` | `2.436e-9` | `1.977e-9` | Uniform metrics do not remove the root defect. |

## Diagnosis

The KE rise is not physically acceptable.  It is a numerical energy injection
from the pressure-jump/projection subsystem.

The immediate mathematical failure is:

```text
D_f a_f ~= 0  but  a_f != 0
```

on a static droplet with zero predictor RHS.  The PPE correctly makes the face
pressure cochain divergence-free, but the cochain is not zero.  That residual
is a solenoidal/Hodge component of the capillary pressure-jump work.  It drives
parasitic velocity while preserving volume and keeping `div u` small.

The supported root localization is the
`transport_variational_p2_ale_discrete_gradient` pressure-jump construction.
It is designed to represent finite-step surface-energy work, but in the static
circle gate it does not reduce to the volume-constrained Young--Laplace
equilibrium cochain.  A circular droplet is not an unconstrained surface-area
critical point; it is critical for `sigma S - lambda V`, with
`lambda = sigma / R`.  If the discrete jump route supplies the surface-energy
covector without exactly closing the volume-constraint / scalar-pressure range
part on the same face space, the projection can remove only the divergent part.
The remaining divergence-free part is precisely the observed KE source.

`Ridge--Eikonal` reinitialization and static-grid/nonuniform details change the
amplitude.  They are not the root source.  `face_implicit` is a useful
diagnostic/reference because it reduces the excess face cochain by about a
factor of five and T=2 KE by about a factor of thirteen, but simply switching
production YAMLs to that route would be a scheme substitution unless backed by
a paper-level derivation.

## Prohibited Non-Fixes

Do not fix this by:

- damping velocity;
- lowering CFL as a success criterion;
- clipping curvature;
- smoothing pressure or curvature;
- silently changing to an alternate static-droplet route;
- hiding the pressure scalar in plots.

Those may reduce symptoms but do not enforce `a_f = 0` for the static
Young--Laplace equilibrium.

## Required Root Fix Direction

1. Add an explicit static-droplet face-work gate:
   `|a_f|`, `|D_f a_f|`, and the divergence-free/Hodge residual for zero
   predictor velocity must be reported.
2. Derive the capillary jump cochain from the volume-constrained discrete
   energy variation `delta(sigma S_h - lambda V_h)`, not from unconstrained
   surface energy alone.
3. Make the P2 ALE discrete-gradient route prove and test the finite-step
   identity in the same face space consumed by PPE and corrector:
   static circle must give `a_f ~= 0`, moving interface must satisfy the
   surface-energy work identity.
4. Keep `face_implicit` as a diagnostic/reference gate until the above
   variational route passes.  It should not be used as an unlabelled fallback.

## Validation Commands

Remote-first probes:

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make push
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make run EXP=experiment/run.py ARGS="--config _tmp_ch14_static_ke_base_t2 --no-checkpoint-final"
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make run EXP=experiment/run.py ARGS="--config _tmp_ch14_static_ke_staticgrid_t2 --no-checkpoint-final"
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make run EXP=experiment/run.py ARGS="--config _tmp_ch14_static_ke_no_reinit_t2 --no-checkpoint-final"
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make run EXP=experiment/run.py ARGS="--config _tmp_ch14_static_ke_frozen_t2 --no-checkpoint-final"
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make run EXP=experiment/run.py ARGS="--config _tmp_ch14_static_ke_uniform_t2 --no-checkpoint-final"
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make run EXP=experiment/run.py ARGS="--config _tmp_ch14_static_ke_faceimplicit_frozen_t2 --no-checkpoint-final"
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make pull
```

Local post-processing recomputed the frozen first-step face divergence with
the solver's `divergence_from_faces`:

```text
frozen_t2 first step:
  |a_f|_inf = 5.944729905693952e-03
  |D_f a_f|_inf = 1.2482855805782499e-08
```

[SOLID-X] analysis/artifact only; no production solver code was changed, no
tested implementation was deleted, and no alternate calculation fallback was
introduced.
