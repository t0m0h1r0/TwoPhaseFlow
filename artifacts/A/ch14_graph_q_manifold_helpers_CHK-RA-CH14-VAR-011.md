# CHK-RA-CH14-VAR-011 — Graph q-manifold helper implementation

## Module

Graph F0 q-manifold helper extraction:

```text
q_T -> Gamma*_graph -> q_phys = Q_h(Gamma*) -> r = q_T - q_phys
```

Implemented files:

```text
src/twophase/geometry/interface_charts.py
src/twophase/geometry/q_manifold_projection.py
src/twophase/tests/test_q_manifold_projection.py
experiment/ch14/diagnose_q_manifold_projection_oracle.py
```

The existing graph oracle now consumes the library helpers instead of carrying
its own projection implementation.

## Equation -> Discretization -> Code

| Equation object | Discretization | Code |
|---|---|---|
| `Gamma_h` | periodic graph state `eta[..., nx+1]` | `GraphChartState` |
| `E[Gamma_h]` | periodic segment length and nodal covector | `graph_segment_energy_gradient` |
| graph F0 projection | column volume -> admitted modes | `project_column_height_to_graph` |
| `Q_h(Gamma*)` | graph gauge `phi=y-eta`, P1 finite-volume cut | `graph_q_from_eta` |
| `q_T=Q_h(Gamma*)+r` | residual split with mandatory report | `project_graph_q_f0`, `ProjectionResult` |
| off-manifold residual | norm, total volume, column residual | `ResidualReport` |

## Code Review

Findings after self-review: no blocking issues remain.

- `src/twophase/geometry/interface_charts.py` owns only chart coordinates,
  low-mode projection, and segment energy.
- `src/twophase/geometry/q_manifold_projection.py` owns only graph F0
  projection, CPU `Q_h` measurement, and residual reporting.
- No runtime adapter, closed-chart route, nonlinear optimizer, T/8 path, YAML
  route, pressure/velocity coupling, smoothing, damping, tolerance weakening,
  CFL retuning, rebuild skipping, FD/WENO/PPE fallback, or hidden CPU fallback
  was added.
- The first parity review found a real batched-broadcast bug in column mode
  projection; it was fixed before acceptance.

## Theory Consistency

The module follows the CHK-RA-CH14-VAR-010 implementation contract:

```text
Gamma_h owner -> q_phys = Q_h(Gamma_h) -> r = q_T - q_phys
```

The high-residual test confirms that a zero-column cell-scale perturbation
does not change `Gamma*`; it remains visible as `r`.

Current limitation is explicit: `cut_geometry_2d` is CPU-only, so GPU runtime
projection remains fail-closed until a GPU-capable `Q_h` evaluator is designed.

## Validation

Local quick checks:

```text
.venv/bin/python3 -m py_compile src/twophase/geometry/interface_charts.py src/twophase/geometry/q_manifold_projection.py src/twophase/tests/test_q_manifold_projection.py experiment/ch14/diagnose_q_manifold_projection_oracle.py
.venv/bin/python3 -m pytest src/twophase/tests/test_q_manifold_projection.py -q
```

Result:

```text
5 passed
```

Remote-first experiment:

```text
make cycle EXP=experiment/ch14/diagnose_q_manifold_projection_oracle.py
```

Result: PASS.  Key metrics:

| Case | `residual_l2` | `residual_column_linf` | `eta_delta_linf` | `force_sign_product` |
|---|---:|---:|---:|---:|
| clean | `1.262190153575e-16` | `3.552713678801e-15` | `7.216449660064e-16` | `-2.312348084758e-01` |
| low_mode | `1.578050209727e-16` | `3.552713678801e-15` | `4.440892098501e-16` | `-2.199623647695e-01` |
| high_residual | `1.381067932005e-04` | `3.553364200104e-15` | `7.216449660064e-16` | `-2.312348084758e-01` |

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py -q'
```

The make target ran the remote suite:

```text
800 passed, 35 skipped
```

`git diff --check`: PASS.

## Next Gate

Proceed to the closed radial chart module only after this commit.  Do not add
runtime admission or T/8 until closed residual classification passes.
