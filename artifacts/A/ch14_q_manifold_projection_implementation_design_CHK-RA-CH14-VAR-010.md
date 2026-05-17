# CHK-RA-CH14-VAR-010 — q-manifold projection implementation design

## Scope

This is an implementation design only.  No production code should be written
from this checkpoint without first passing the planned oracle gates.

The implementation target is the fast route from `CHK-RA-CH14-VAR-009`:

```text
q_T = Q_h(Gamma*) + r
```

where `Gamma_h` is the owned interface configuration, `q_T` is a transported
finite-volume measurement, and `r` is an exposed off-manifold residual.  The
initial implementation must make it impossible to accidentally return to:

```text
transport q
-> rebuild phi to match all cells
-> compute force from phi
```

## Layer Boundaries

The implementation should be split into three layers.

| Layer | Responsibility | May depend on | Must not do |
|---|---|---|---|
| chart | own `Gamma_h` coordinates and variational energy | `backend.xp`, `Grid` metrics | inspect runtime pressure or velocity |
| measurement | compute `Q_h(Gamma_h)` and constrained moments | chart state, grid, cut geometry | decide capillary force |
| projection | split `q_T = q_phys + r` and report diagnostics | chart + measurement | hide residuals or smooth geometry |

The runtime face-cochain coupling remains a later layer.  It should consume a
validated `ProjectionResult`, not own the q-manifold projection logic.

## Proposed File Map

Do not create all files at once.  Add them only when the corresponding oracle
needs them.

| Future file | Purpose | First allowed stage |
|---|---|---|
| `src/twophase/geometry/interface_charts.py` | chart state dataclasses and vectorized graph/closed energy, area, basis construction | graph helper extraction |
| `src/twophase/geometry/q_manifold_projection.py` | F0/F1 projection orchestration and `ProjectionResult` | after graph helper tests |
| `src/twophase/diagnostics/q_manifold.py` | residual spectra, constrained moments, fail-close reports | graph helper tests |
| `experiment/ch14/diagnose_closed_q_manifold_projection_oracle.py` | closed mode-2 oracle and visualization | after graph helper parity |
| `src/twophase/simulation/...` adapter | runtime admission object plumbing only | after closed oracle PASS |

Avoid placing this logic inside `ns_step_services.py` first.  That file should
only receive a small adapter after the chart/projection contract is proven.

## Public Objects

### Chart States

The chart layer should expose small immutable state objects:

```text
GraphChartState:
    eta:        (batch, nx + 1)
    coeffs:     (batch, K_g)
    basis_meta: periodic graph modes, base height, mode list

ClosedRadialChartState:
    center:     (batch, 2)
    coeffs:     (batch, K_c)
    theta:      (M,)
    vertices:   (batch, M, 2)
    basis_meta: radial modes and area mode policy
```

These are chart states, not level-set fields.  A `phi` array may be generated
inside measurement code as a gauge, but it must not become the stored owner.

### Projection Result

The projection layer should return one object:

```text
ProjectionResult:
    chart_kind
    stage                 # F0, F1, F2, or F3-oracle
    gamma_state           # graph or closed chart state
    q_phys                # Q_h(Gamma*)
    residual              # q_T - q_phys
    constraint_report
    energy_report
    residual_report
    validity_report
```

No caller should receive `q_phys` without the residual and validity reports.
This is the primary guard against silently turning `r` into geometry.

## A3 Contract Table

| Equation object | Discrete object | Producer | Consumer | Fail-close condition |
|---|---|---|---|---|
| `Gamma_h` | graph `eta` or closed vertices | chart builder | energy, measurement, projection | invalid chart, non-periodic graph, non-star closed chart |
| `E[Gamma_h]` | segment/polygon length | chart energy | F1 report, later force map | NaN, negative length, wrong rigid-mode response |
| `Q_h(Gamma_h)` | cell volume `q_phys` | measurement evaluator | residual split | unsupported backend, invalid sign stratum, missed active band |
| exact constraints | total/component volume, selected modes | moment evaluator | F0/F1 KKT | low-mode residual remains after admitted correction |
| `r` | full cell residual | projection result | diagnostics and fail-close only | omitted report, hidden subtraction, force consumer access |
| `dE` | chart covector | chart variation | later face-cochain map | finite-difference mismatch |

## F0 Direct Projection Design

### Graph

Input:

```text
q_T:       (batch, nx, ny)
grid:      node-centered Grid
basis:     admitted periodic modes
```

Operations:

```text
column_volume = sum_y q_T
eta_meas      = column_volume / dx + y_bottom
coeffs        = project eta_meas to admitted modes
eta_star      = base + B_g coeffs
q_phys        = Q_h(eta_star)
residual      = q_T - q_phys
```

The projection is vectorized over batch and columns.  It must report both
column residuals and discarded high-mode spectra.

### Closed Radial Chart

Input:

```text
q_T:       (batch, nx, ny)
center:    predicted droplet center
basis:     admitted radial modes
```

Operations:

```text
moments       = sum_C q_T[C] * area[C] * basis(theta_C)
coeffs        = low-mode radial fit
R0            = analytic area correction
vertices      = center + R(theta) * unit(theta)
q_phys        = Q_h(vertices)
residual      = q_T - q_phys
```

The chart must fail closed when the droplet is not star-shaped with respect to
the chosen center, when the area correction makes any radius nonpositive, or
when the selected modes cannot preserve the constrained moments.

## F1 Linearized Correction Design

F1 is an optional correction, not the default.

Use only admitted chart coefficients:

```text
a* = a_p + da
```

Build:

```text
J_B = DQ_h(Gamma(a_p)) B
A   = J_B^T W J_B + beta H_E
b   = J_B^T W (q_T - q_p) - beta g_E
```

Then solve a small KKT system with exact constraints.  `K` is the number of
chart modes, not the number of cells.  For the first implementation:

- graph `J_B` may be analytic from column-volume derivatives;
- closed `J_B` may be batched finite difference over modes in oracle code;
- runtime use is forbidden until vectorized parity and closed oracle pass.

F1 must return predicted and actual residual reduction.  If the actual
reduction does not match the prediction, the projection fails closed.

## Backend and GPU Contract

The array path should be written against `backend.xp`, but current
`cut_geometry_2d` explicitly rejects a GPU namespace.  Therefore:

| Stage | `Q_h` backend policy |
|---|---|
| graph/closed oracle | CPU-labeled measurement is allowed and must be declared |
| library helper tests | CPU parity first; no hidden device-to-host fallback |
| GPU runtime admission | impossible until a GPU-capable or explicitly staged active-band `Q_h` exists |

If `TWOPHASE_USE_GPU=1` reaches a projection evaluator that can only measure on
CPU, it must raise.  It must not copy arrays to host and continue silently.

## Active-Band Measurement Contract

The active-band optimization is a measurement acceleration, not rebuild
skipping.

Required inputs:

```text
predicted chart
maximum admitted displacement
grid metrics
pure-phase value outside band
```

Required report:

```text
band_cell_count
missed_cut_count
sign_margin
pure_phase_copy_count
```

Fail closed when any cut cell lies outside the band or when the band cannot be
proven to contain the moved interface.

## Test and Oracle Plan

### Stage 1: Graph Helper Extraction

Extract the passed graph oracle logic into pure helper functions, then keep the
existing experiment as the executable proof.

Required checks:

- clean graph returns roundoff residual;
- representable low mode enters `Gamma*`;
- zero-column cell residual stays in `r`;
- batched helper matches scalar oracle;
- residual report cannot be omitted.

### Stage 2: Closed Radial Oracle

Implement the closed mode-2 oracle before runtime.

Required checks:

- polygon area and `sum q_phys` agree;
- length energy grows like mode amplitude squared;
- `dE` and `dA` match finite differences;
- mode-2 restoring sign is correct after area reaction removal;
- high cell residual stays in `r`;
- visualization shows curve, q fields, residual, covectors, and spectra.

### Stage 3: Vectorized Parity

Run scalar and batched paths on the same synthetic cases.

Required checks:

- CPU scalar vs batch equality for graph;
- CPU scalar vs batch equality for closed polygon energy/area;
- no accidental host/device conversion in hot paths;
- explicit failure when GPU runtime asks for CPU-only `Q_h`.

### Stage 4: Runtime Admission Probe

Only after Stages 1-3 pass, add a runtime adapter that creates a
`ProjectionResult` and records residual reports.  The first runtime probe must
be short and diagnostic.  T/8 remains inadmissible until the short probe shows
that residual budgets predict fail-close before force spikes.

## Review Checklist Before Coding

Before implementation begins, answer these questions in the patch description:

1. Which exact chart owns `Gamma_h` in this patch?
2. Is `q` produced only by `Q_h(Gamma_h)`?
3. Does every public result expose `r`?
4. Which constraints are exact, and which cell modes are diagnostic only?
5. Is the backend boundary explicit?
6. What is the smallest negative test that proves all-cell `q` exactness did
   not leak back into geometry?
7. Which oracle blocks runtime/T/8 if it fails?

If any answer is missing, do not code yet.

## Current Decision

The next code-bearing checkpoint should implement Stage 1 only:

```text
graph helper extraction + graph oracle parity
```

No closed runtime connection, no Ch14 T/8, no nonlinear optimizer, and no GPU
runtime path should be introduced in that checkpoint.
