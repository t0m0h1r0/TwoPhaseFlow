# CHK-RA-CH14-N32-T10-GPU-001 — N32/T10 GPU Trace-Riesz Experiment

Date: 2026-05-07  
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`  
Scope: user request to run T=10 and visualize.

## Setup

Temporary, uncommitted YAMLs were derived from the canonical ch14 static and
oscillating droplet configs:

- `grid.cells: [32, 32]`
- `run.time.final: 10.0`
- `output.snapshots.interval: 1.0`
- `surface_tension.source: closed_interface_riesz`
- `poisson.operator.capillary_reaction_projection: pressure_component_hodge`

The temporary YAMLs were removed after the runs and pushed away from remote so
canonical YAML exact-set tests remain clean.

## GPU Solve Adjustment

The first oscillating T=10 GPU run exposed a linear-algebra edge in the Hodge
normal equation: CuPy sparse direct solve can report a near-singular matrix for
the periodic duplicated-node pressure gauge, even though the mathematical
problem is still the same singular compatible normal equation

```text
D_f M_f^{-1}D_f^T p = D_f c.
```

The GPU solve path now validates the direct sparse result against the original
normal equation.  If direct sparse solve returns a non-finite or invalid
solution, it computes the Moore-Penrose/least-squares solution of the same
normal equation using CuPy sparse LSMR and again checks the residual.  This is
not a force-model fallback: `D_f`, `M_f`, `c`, the range cochain, and the Hodge
gate are unchanged.

## Results

Static droplet result directory:

`experiment/ch14/results/_tmp_ch14_static_droplet_n32_t10_trace_riesz_gpu`

- Steps: `1012`
- Final time: `10.0`
- KE: `8.8607e-11 -> 3.4165e-05`
- Max KE: `3.4165e-05`
- Volume drift final/max: `3.8069e-16 / 4.0607e-15`
- Deformation: `0 -> 0`
- Final velocity Linf: `1.8070e-03`
- Visuals: `overview_t10.png`, `diagnostics_t10.png`, plus generated PDF
  snapshots for `psi`, `velocity`, and `pressure_hodge`.

Oscillating droplet result directory:

`experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t10_trace_riesz_gpu`

- Steps: `979`
- Final time: `10.0`
- KE: `2.2534e-09 -> 1.0091e-03`
- Max KE: `1.2251e-03`
- Volume drift final/max: `3.0673e-15 / 4.7288e-15`
- Deformation: `8.0347e-02 -> 4.3696e-02`
- Signed deformation: `7.6175e-02 -> -1.6903e-02`
- Rayleigh-Lamb inviscid reference at `t=10`: `-1.0337e-02`
- Final velocity Linf: `6.9573e-03`
- Visuals: `overview_t10.png`, `diagnostics_t10.png`, plus generated PDF
  snapshots for `psi`, `velocity`, and `pressure_hodge`.

## Interpretation

The zero-drive pathology is gone at T=10: the oscillating droplet develops a
nonzero velocity field, sustained KE, and signed deformation crosses through
zero with the same sign as the Rayleigh-Lamb reference by `t=10`.

The static sampled circle is not a clean equilibrium proof yet.  It keeps
deformation and volume essentially fixed, but the KE grows monotonically to
`O(1e-5)` and the velocity field shows structured interface currents.  That is
consistent with the earlier conclusion: the remaining issue is a force-cochain
static-critical problem, not volume conservation, zero-drive, or Hodge
projection algebra failure.

## Validation

- `git diff --check`: PASS.
- Remote targeted GPU projection test:
  `1 passed in 0.45s`.
- Remote wrapper after removing temporary YAMLs:
  `610 passed, 33 skipped in 43.11s`.

## SOLID-X

No SOLID violation found.  The code change is confined to the GPU linear solve
for the existing weighted Hodge normal equation.  No tested implementation was
deleted, and no FD/WENO/PPE fallback, damping/CFL workaround, curvature cap,
smoothing, benchmark branch, blanket `c -> Pi_R c`, or QP-as-physics route was
introduced.
