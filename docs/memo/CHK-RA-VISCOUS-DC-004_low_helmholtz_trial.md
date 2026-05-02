# CHK-RA-VISCOUS-DC-004 — Fixed-pattern and scalar-low Helmholtz trial

Date: 2026-05-02  
Branch: `ra-viscous-dc-20260502`  
Scope: trial implementation of the CHK-RA-VISCOUS-DC-003 design direction.

## Implemented trial

The low-order viscous Helmholtz correction now separates topology from values.
The sparse row/column pattern is built from shape and boundary topology, then
cached. Each implicit-BDF2 DC solve updates only the numeric values from current
`mu`, `rho`, grid coordinates, and `dt_effective`. This keeps the method valid
for dynamically rebuilt grids because the numeric factor is still rebuilt from
current values; only the invariant graph pattern is reused.

A selectable low operator was added under

```yaml
viscosity:
  solver:
    kind: defect_correction
    corrections:
      low_operator: component  # default, old tensor/component low operator
      # or
      low_operator: scalar     # common isotropic low operator, c=(d+1)/d
```

The scalar option uses the common Helmholtz low operator

```text
A_S = I - tau c/(Re rho) div(mu grad),  c=(d+1)/d,
```

which is the component average of the diagonal stress weights. The high-order
residual `A_H` is unchanged, so the DC fixed point remains the high-order BDF2
viscous equation.

## GPU microbenchmark

Remote GPU, N=128 alpha=4 fitted periodic static-droplet grid, same `mu/rho` as
CHK-RA-VISCOUS-DC-003. Tail means exclude the first warm-up construction.

| low operator | init/factor tail mean [s] | two-component low solve tail mean [s] |
|---|---:|---:|
| old reference from CHK-003 component | 0.6723 | 0.1560 |
| fixed-pattern component | 0.1596 | 0.1512 |
| fixed-pattern scalar + batched RHS | 0.0783 | 0.0768 |

Interpretation:

- fixed-pattern value update removes most of the matrix-build bottleneck:
  component init/factor drops by about `4.2x` versus CHK-003.
- scalar-low halves the factor count and, with a batched two-RHS triangular
  solve, halves the low-solve cost as well.
- the remaining component-low solve cost is triangular solve dominated, not
  assembly dominated.

## Short static-droplet run

Remote GPU, fully periodic static droplet, N=128, T=0.1, alpha=4, fixed
`dt=0.001235`, 81 steps.

| low operator | wall time | sec/step | final KE | volume drift | deformation |
|---|---:|---:|---:|---:|---:|
| component | 1m45.735s | 1.305 | 1.7675817105e-07 | 0.0 | 0.0 |
| scalar | 1m18.065s | 0.964 | 1.7675524127e-07 | 0.0 | 0.0 |
| optimized scalar T=1 | 13m11.537s | 0.977 | 3.2078346266e-06 | 0.0 | 0.0 |
| previous CHK-002 T=1 component path | 28m04s | 2.079 | 3.2082084487e-06 | 0.0 | 0.0 |

The scalar and component paths are numerically indistinguishable on this static
balance probe at T=0.1. The full T=1 scalar run preserves the same static
diagnostics as the pre-optimization component run while reducing wall time from
`28m04s` to `13m11.537s`, a `2.13x` end-to-end speedup.

## Verdict

The proposed path is supported:

1. fixed sparse pattern + value update is safe and materially faster;
2. scalar-low Helmholtz is stable on the representative static-droplet probe;
3. scalar-low should remain YAML selectable until broader moving-interface and
   high-density-ratio tests approve making it the default.

Next validation gate: run one dynamic-grid case where pattern caching is used
but numeric factors are rebuilt every step.

[SOLID-X] The topology/value split is isolated inside the low-order viscous
Helmholtz solver. YAML parsing and runtime state only pass an explicit low
operator choice. No tested code was deleted; the high-order residual DC contract
is unchanged.
