# CHK-RA-CH14-VAR-023 - Ch14 experiment readiness gate

Date: 2026-05-17

Scope: Step 0 preparation before starting new Ch14 capillary experiments from
the PhaseRegion/InterfaceAtlas theory.  This checkpoint is a freeze and
acceptance sheet only.  It does not add code, YAML routes, solver coupling,
force coupling, pressure/velocity projection, runtime adapters, long runs, or
T/8 experiments.

## Purpose

The next experiment sequence must start from admitted oracles and negative
knowledge, not from the old screened q/phi repair loop.  The preparation gate
therefore fixes:

1. inherited PASS evidence;
2. inherited FAIL evidence;
3. step-by-step admission criteria;
4. stop conditions that force a return to theory instead of continuing an
   already-failed implementation path.

## Evidence Freeze

| Evidence | Status | Use |
|---|---|---|
| `WIKI-E-064` baseline capillary probe | PASS control | Keep as a short runtime regression control only.  `compat_linf=0` does not prove transported pre-rebuild q preservation. |
| `WIKI-E-064` screened graph-q runtime rebuild | FAIL negative knowledge | Do not continue screened q/phi rebuild by tolerance weakening, rebuild skipping, smoothing, damping, CFL retuning, or hidden fallback. |
| `WIKI-E-065` graph variational capillary oracle | PASS oracle | Use as the graph chart physical sign/mode/energy reference. |
| `WIKI-E-066` graph q-manifold projection oracle | PASS oracle | Use as low-mode vs residual split reference; residual remains diagnostic. |
| `WIKI-E-067` closed radial q-manifold oracle | PASS oracle | Use as the closed-chart counterpart under the same variational principle. |
| `WIKI-E-068` runtime admission snapshot probe | PASS snapshot | Use as runtime-facing admission evidence, but keep `force_admissible=0`. |
| `WIKI-E-069` PhaseRegion atlas smoke oracle | PASS atlas | Use as the multi-component `Omega_g = bubble union layer` representation check. |
| `WIKI-L-054` boundary/nonuniform audit | PASS with blocker | Direct atlas smoke passes at `alpha_grid=2`, but graph F0 remains uniform-only. |

## Preserved Negative Knowledge

The next implementation must explicitly preserve the following failure facts:

| Fact | Consequence |
|---|---|
| Transported `q_T` may contain degrees of freedom not representable by a smooth graph/phi chart. | Do not make all-cell q exactness the default physical acceptance condition. |
| `compat_linf=0` after graph rebuild can mean q was redefined from the graph, not that pre-rebuild `q_T` was preserved. | Runtime acceptance must compare pre/post q and `Q_h(R_h)`, not just post-rebuild compatibility. |
| Exact q projection can make the interface jagged because q is being absolutized. | Smooth geometry and physical low modes must be admitted before force coupling. |
| Surface-energy variation and transport state must share the same owner. | `q`, `phi`, force, and projection cannot be accepted as four disconnected spaces. |
| Moving-grid rebuild can follow gauge reconstruction rather than material interface motion. | Snapshot and runtime probes must record owner state, chart, attachment, and q residual separately. |
| Graph wave and closed droplet were previously treated as separate theories. | They must now be chart choices under `PhaseRegion/Omega_g`. |
| Pressure, velocity, face cochain, and boundary-condition spaces can diverge. | Force-coupling gates must check pairing before any long run. |

## Step Gates

| Step | Goal | Acceptance | Stop condition |
|---|---|---|---|
| 1 | Nonuniform graph F0 admission | Uniform parity and `alpha_grid=2` PASS; volume/mode/phase preserved; boundary attachment explicit. | If the graph path needs all-cell q exactness or hidden smoothing, return to theory. |
| 2 | Graph F1 low-mode KKT connection | Small-system correction reduces admitted residual without making `force_admissible` true. | If KKT becomes singular, indefinite, or cell-count-sized, fail closed. |
| 3 | Closed-curve chart oracle | Circle/ellipse mode signs, volume, perimeter, and symmetry match the same variational principle. | If closed chart needs special physics not shared with graph/open charts, stop. |
| 4 | Multi-component atlas | Closed bubble plus top layer admits component and total-volume accounting on uniform and nonuniform grids. | If component q violates capacity or attachment is ambiguous, fail closed. |
| 5 | Force oracle | Force sign, mode/phase, symmetry, and energy trend match `-delta E`; pressure/velocity pairing is declared. | If the force uses a different owner than transport, stop before runtime. |
| 6 | Runtime dry-run | Snapshot adapter builds `PhaseRegionBatch` without advancing solver; no hidden CPU fallback. | If adapter silently rebuilds phi or drops residual, stop. |
| 7 | Micro stepping | A few steps pass before `T/128`; diagnostics include pre/post q, residual, energy, and visualization. | If energy or symmetry fails, do not lengthen the run. |
| 8 | T/8 | Only after all previous gates pass and `force_admissible` is justified. | Any tolerance weakening, damping, smoothing, rebuild skipping, or CFL-retuning primary fix cancels the gate. |

## Acceptance Metrics

Every new experiment artifact must report at least:

| Metric | Required before |
|---|---|
| total volume and component volumes | Step 1 onward |
| `q_T`, `Q_h(R_h)`, and residual `r` | Step 1 onward |
| residual volume integral and residual norm | Step 1 onward |
| mode amplitude and phase | graph/closed chart oracles |
| perimeter or surface energy | all geometry oracles |
| finite-difference gradient check or equivalent | F0/F1 and force oracles |
| boundary attachment and phase role | atlas and runtime adapters |
| nonuniform grid parameter and cell capacity check | all nonuniform probes |
| visualization path | every oracle and runtime probe |
| `force_admissible` | every gate, default false until force oracle passes |

## First Implementation Target

The next concrete target is not a runtime run.  It is the Step 1 oracle:

```text
nonuniform graph F0 admission
eta(x_edges) -> Q_h(eta)
q_T -> physical low-mode graph proposal + residual r
uniform parity + alpha_grid=2 validation
visualization required
force_admissible = false
```

The known blocker to remove is:

```text
project_column_height_to_graph currently requires uniform x spacing
```

The replacement must be a chart-specific nonuniform admission oracle, not a
runtime-side screened q/phi rebuild.

## Validation

This checkpoint is docs/artifact/wiki/ledger preparation only.  Validation:

```text
git diff --check
```

Result: PASS.

Wiki count audit:

```text
rg --files docs/wiki -g 'WIKI-*.md' | wc -l = 416
rg --files docs/wiki/experiment -g 'WIKI-E-*.md' | wc -l = 70
```

Targeted scan:

```text
WIKI-E-070, 416 entries, Experiment (70), CHK-RA-CH14-VAR-023,
project_column_height_to_graph, force_admissible, screened q/phi,
T/8, nonuniform graph F0
```

Result: PASS.
