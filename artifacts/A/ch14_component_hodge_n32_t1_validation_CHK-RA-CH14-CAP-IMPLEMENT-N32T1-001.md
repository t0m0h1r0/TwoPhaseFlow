# CHK-RA-CH14-CAP-IMPLEMENT-N32T1-001

## Scope

User request: summarize the capillary Hodge theory in wiki/short paper, implement the selected route, and validate static/oscillating droplets at `N=32,T=1` with visualization.

## Implemented Route

Added runtime mode:

```text
capillary_range_projection: component_hodge_augmented
```

For the capillary jump cochain `c` and the unit constant component pressure-jump cochain `b`, the solver computes:

```text
h_c   = c - Pi_R c
h_b   = b - Pi_R b
beta  = <h_c,h_b>_M / <h_b,h_b>_M
c_aug = c - beta h_b
```

The corrector receives `c_aug`.  This is the one-component `range(A_fG_f)+range(B)` Hodge projection slice, not a shape classifier and not blanket `c -> Pi_R c`.

## Validation

Commands:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test PYTEST_ARGS="twophase/tests/test_interface_projection_diagnostics.py twophase/tests/test_config_io_fccd.py twophase/tests/test_ns_pipeline_fccd.py -k capillary"
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test PYTEST_ARGS="twophase/tests/test_interface_projection_diagnostics.py::test_component_hodge_augmented_projection_removes_unit_reaction_component twophase/tests/test_config_io_fccd.py::test_ch14_static_droplet_yaml_uses_base_dynamic_route twophase/tests/test_config_io_fccd.py::test_ch14_canonical_yamls_share_base_numerical_stack twophase/tests/test_config_io_fccd.py::test_ch14_rising_bubble_yaml_loads_execution_stack"
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS="--config _tmp_ch14_static_droplet_n32_t1_component_hodge --no-checkpoint-final"
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS="--config _tmp_ch14_oscillating_droplet_n32_t1_component_hodge --no-checkpoint-final"
```

The second test command expanded to the full remote CPU suite and passed `590 passed, 32 skipped`.

## Metrics

| Quantity | Static N32/T1 | Oscillating N32/T1 |
|---|---:|---:|
| final time | `1.0` | `1.0` |
| steps | `102` | `100` |
| final KE | `5.284015e-09` | `3.643971e-04` |
| max `|Delta V|/V0` | `1.903440e-15` | `2.428289e-15` |
| deformation / signed deformation | `0 -> 0` | `7.617534e-02 -> 4.334637e-02` |
| max snapshot velocity Linf | `1.833331e-05` | `9.417805e-03` |
| max capillary face Linf | `9.525267e-05` | `1.417884e-02` |
| max corrected Hodge weighted L2 | `2.814614e-04` | `4.477470e-02` |
| max Hodge divergence Linf | `3.324017e-11` | `3.285230e-09` |
| PPE DC final relative L2 max | `2.278601e-09` | `2.360888e-09` |
| reinit triggered | `0` | every step after first |

## Visualization

Generated PDFs:

- `experiment/ch14/results/ch14_component_hodge_n32_t1_summary.pdf`
- `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t1_component_hodge/{deformation,volume_drift,kinetic_energy}.pdf`
- `experiment/ch14/results/_tmp_ch14_static_droplet_n32_t1_component_hodge/{psi,velocity,pressure}_t*.pdf`
- `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t1_component_hodge/{signed_deformation,volume_drift,kinetic_energy}.pdf`
- `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t1_component_hodge/{psi,velocity,pressure}_t*.pdf`

## Verdict

The zero-drive bug is fixed in the targeted sense: the oscillating droplet receives nonzero corrected Hodge drive and develops velocity/kinetic energy, instead of the previous `~1e-37` KE freeze under `range_projected`.

The static droplet is stable in volume and deformation but not an exact roundoff equilibrium under the current scalar face-implicit curvature cochain.  The residual is much smaller than the oscillating drive, but it is real.  Therefore the next theorem-grade step remains the full fixed-stratum transport-adjoint Riesz cochain `s=-M_f^{-1}T^Td(sigma S_h)^T`; the residual must not be hidden with damping, smoothing, curvature caps, CFL reduction, benchmark-name branching, or blanket projection.

[SOLID-X] `component_hodge_augmented` is isolated in the pressure-stage face-cochain responsibility; no tested implementation deleted; no FD/WENO/PPE fallback, damping/CFL workaround, curvature cap, smoothing, benchmark branch, blanket `c -> Pi_R c`, or QP-as-physics path introduced.
