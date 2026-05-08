# CHK-RA-CH14-CLOSED-PERWALL-ADJOINT-001

## Question

Can the closed-interface capillary-wave route be used with horizontal
periodicity and vertical walls, without treating the case as a special
static-droplet or benchmark-name branch?

## Theoretical classification

For a closed interface contained away from the top and bottom walls, the
surface-energy variation remains

```text
dE_sigma(q)[delta q] = <s_h(q), u_f>_{M_f},
```

with the admissible velocity space constrained by the domain boundary:
periodic traces on the horizontal axis and zero wall-normal flux on the
vertical axis.  Therefore the physical question is not whether the initial
shape is a circle or ellipse, but whether the production cochain is the
discrete transport adjoint of the same FCCD divergence/projection operator.

The decisive wall-axis identity is obtained directly from
`FCCDSolver.face_divergence`.  On a wall axis,

```text
(D_f F)_0 = 0,
(D_f F)_i = (F_i - F_{i-1}) / H_i,  i = 1,...,N-1,
(D_f F)_N = 0.
```

Thus the exact negative adjoint must satisfy

```text
<eta, -D_f F> = <(-D_f)^T eta, F>,
((-D_f)^T eta)_j = w_{j+1} eta_{j+1} - w_j eta_j,
w_0 eta_0 = w_N eta_N = 0.
```

Boundary nodal covectors do not enter because the wall divergence has zero
boundary rows.  This is the same variational principle as the all-periodic
case; only the topology of the divergence matrix changes.

## Hypotheses tested

| Hypothesis | Verdict | Evidence |
|---|---:|---|
| H1: closed-interface Riesz is mathematically incompatible with `x` periodic / `y` wall | Refuted | The weak virtual-work form is valid on the constrained velocity space; the wall only removes normal boundary rows. |
| H2: the existing open `capillary_wave` object can be reused as a closed-interface benchmark | Refuted | It is an open graph interface; the closed-interface contract requires a closed stratum such as `perturbed_circle`. |
| H3: existing YAML/config contracts already allow the mixed boundary | Supported | Parser tests cover `{x: periodic, y: wall}` and `bc_type == periodic_wall`; `wall` monitor is the accepted key. |
| H4: production closed-interface Riesz already satisfies the mixed-boundary transport adjoint | Refuted | The first N32/T1 run failed in `_negative_face_divergence_adjoint` with nonuniform wall-axis broadcasting. |
| H5: the wall-axis implementation used the wrong adjoint | Confirmed | The previous implementation multiplied all `N+1` nodal covectors by `inv_H_node` of length `N-1`, included boundary covectors, and had the opposite sign. |
| H6: after the adjoint fix, the mixed-boundary run violates the imposed boundary conditions | Refuted | Final snapshot: `v(y=0)` and `v(y=1)` Linf are `0`; `x=0/1` velocity mismatch is `0`. |

## Code change

- `src/twophase/coupling/transport_variational_capillary.py`
  - Wall-axis branch of `_negative_face_divergence_adjoint` now zeroes boundary
    weights and returns `weighted[1:] - weighted[:-1]`.
- `src/twophase/tests/test_closed_interface_riesz.py`
  - Added a nonuniform `periodic_wall` adjoint-identity test:
    `<eta, -D_f F> = <(-D_f)^T eta, F>` for both the periodic and wall axes.

## Validation

Remote CPU validation:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_closed_interface_riesz.py::test_negative_face_divergence_adjoint_matches_periodic_wall_fccd_divergence -q'

633 passed, 33 skipped in 44.12s
```

Temporary N32/T1 closed-interface capillary wave configuration:

```text
grid.cells = [32, 32]
boundary = {x: periodic, y: {lower: wall, upper: wall}}
initial object = perturbed_circle(center=[0.5,0.5], radius=0.25, epsilon=0.05, mode=2)
surface_tension.source = closed_interface_riesz
closed_interface.residual_contract.metric = pressure_adjoint
capillary_reaction_projection = pressure_component_hodge
```

Result directory:

```text
experiment/ch14/results/_tmp_ch14_closed_capillary_wave_n32_t1
```

Quantitative result:

```text
steps                         99
t_final                       1.0
KE first -> last              7.309138e-10 -> 8.909943e-06
KE max                        8.909943e-06
volume drift max              1.114287e-06
signed deformation first/last 3.830504e-02 -> 4.133053e-02
pressure contrast first/last  1.993975e-02 -> 6.829046e-02
final speed Linf              1.300684e-03
final v(y=0) Linf             0.0
final v(y=1) Linf             0.0
final x-periodic u mismatch   0.0
final x-periodic v mismatch   0.0
```

Generated PDFs:

```text
experiment/ch14/results/_tmp_ch14_closed_capillary_wave_n32_t1/psi_t1.000.pdf
experiment/ch14/results/_tmp_ch14_closed_capillary_wave_n32_t1/velocity_t1.000.pdf
experiment/ch14/results/_tmp_ch14_closed_capillary_wave_n32_t1/pressure_t1.000.pdf
experiment/ch14/results/_tmp_ch14_closed_capillary_wave_n32_t1/kinetic_energy.pdf
```

## Verdict

The useful existing pieces are the `closed_interface_riesz` contract, the
component-volume reaction projection, the mixed-boundary parser, and the FCCD
periodic-wall divergence/projection stack.  The unusable piece was the
production wall-axis transport adjoint.  The fix is not a case-specific
fallback: it restores the exact discrete variational adjoint of the existing
operator on the constrained velocity space.

[SOLID-X] Focused numerical-operator fix plus regression test only.  No tested
implementation was deleted.  No FD/WENO/PPE fallback, damping, CFL workaround,
curvature cap, smoothing, benchmark-name branch, blanket projection, or
QP-as-physics route was introduced.
