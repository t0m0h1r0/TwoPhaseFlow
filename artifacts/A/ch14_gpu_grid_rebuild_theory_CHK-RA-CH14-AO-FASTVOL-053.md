# CHK-RA-CH14-AO-FASTVOL-053 - GPU-Resident Grid Rebuild Theory

## Trigger

During the repeated Chapter 14 capillary-wave quarter run, the remote process
showed low GPU utilization and full CPU saturation:

```text
nvidia-smi: 22-23% GPU, 288 MiB
ps: python3 experiment/run.py --config ch14_capillary --no-checkpoint-final
    CPU 100%, elapsed 26m+
```

The run was stopped at `27m34.845s` after the user redirected the work to
theory construction.  No numerical parameter was changed.

## Root Contract

The capillary-wave YAML intentionally uses:

- nonuniform interface-fitted tensor-product grids on both axes;
- wall refinement on the `y` axis;
- rebuild schedule `1`, so coordinates track the interface every step;
- active-geometry capillary state space.

These are not optional performance decorations.  They define the discrete
measure, Hodge weights, compact derivative metrics, remap problem, and P1
active-geometry stratum.  Therefore the GPU plan must port the rebuild
contract; it must not replace it with a static/uniform grid.

## Mathematical Design

Represent the grid by a tensor-product physical coordinate map

```text
x_a = chi_a(xi_a),      xi_i = i / N_a,      a in {x,y}.
```

For each axis, define a positive monitor

```text
omega_a = 1
        + (alpha_I - 1) I_a(phi)
        + (alpha_W - 1) W_a,
```

where `I_a` is the interface monitor and `W_a` is the wall monitor.  The new
coordinates solve the equidistribution equation

```text
int_0^{x'_i} omega_a(s) ds = (i / N_a) int_0^{L_a} omega_a(s) ds.
```

The discrete GPU form is:

```text
m_{i+1/2} = 0.5 (omega_i + omega_{i+1}) (x_{i+1} - x_i)
C_0 = 0,  C_{i+1} = C_i + m_{i+1/2}
tau_i = (i / N) C_N
x'_i = C^{-1}(tau_i)
```

implemented with device arrays, prefix scans, and monotone inverse lookup.

### Interface Monitor

Compute `phi = H^{-1}(psi)` on device.  For axis `a`,

```text
bar_phi_i^a = min_{j != a} |phi|
I_base = exp(-(bar_phi_i^a)^2 / eps_g^2).
```

Closed-interface seed contributions should be computed with fixed-shape masks
over all x/y edges:

```text
s_e = x_left + |phi_left| / (|phi_left| + |phi_right|)
              * (x_right - x_left)
I_seed_i = max_e mask_e exp(-(x_i - s_e)^2 / eps_g^2).
```

This is mathematically the same projection monitor as the host code, but avoids
dynamic `argwhere`/`where` compaction.

### Width Floor Projection

After inverse-CDF coordinates produce provisional cell widths `d_i`, enforce
the minimum width `f` by projection:

```text
d_i^* = f + beta max(d_i - f, 0),
beta = (L - N f) / sum_i max(d_i - f, 0),
```

or use uniform `L/N` when `N f >= L`.  This preserves total length,
monotonicity, and lower-width admissibility using only device reductions.

### Regular-Stratum Guard

P1 active geometry is valid only on an open sign stratum:

```text
min_node |phi'(x')| >= eta.
```

The GPU guard should avoid sequential host `np.argwhere` and line edits.
Use fixed bounded sweeps:

1. remap/evaluate `phi'` on the candidate grid on device;
2. form violation mask `V = |phi'| < eta`;
3. compute nonuniform nodal gradients `g_a = d phi' / d x_a`;
4. for each coordinate line, reduce violating nodes to a clipped line shift
   that increases `|phi'|` while preserving neighbor spacing floors;
5. update all lines simultaneously;
6. after a fixed number of sweeps, transfer one status packet:
   `min_dx`, `min_stratum_margin`, conservation residuals, and failure bits.

An equivalent exact line formulation is a one-dimensional constrained problem:
choose the smallest line shift `delta` within monotonicity bounds such that
`|phi_r + g_r delta| >= eta` for all violating nodes on that line.  Candidate
solutions are interval endpoints of the forbidden set
`|phi_r + g_r delta| < eta`; this can also be implemented with segmented
device reductions.

### Conservative Remap

Grid update is a map between discrete complexes, not just nodal coordinates.
Conserved cochains must use overlap weights:

```text
q'_{ij} = sum_{kl} O^x_{ik} O^y_{jl} q_{kl},
```

where each 1-D overlap matrix integrates old cell intervals over new cell
intervals.  This preserves physical volume exactly up to floating-point
roundoff.  The same rule applies to density and conservative momentum.

Gauge fields such as diagnostic `phi` may use interpolation; primary conserved
variables must not.

### Metric Epoch

After coordinates are accepted, create one metric epoch:

- device coordinates and widths;
- node widths;
- `J=d xi/dx` and `dJ/dxi`;
- cell volumes and face measures;
- CCD/FCCD/PPE caches;
- active supports and Schur buffers;
- pressure and face history validity.

Any stale object from the previous epoch is invalid.  This is the GPU version
of the nonuniform/rebuild source-of-truth rule.

## What Must Stay CPU

Only outer orchestration has a strong reason to remain on CPU:

- YAML/config parsing;
- Python loop termination and exception/reporting policy;
- one batched timestep/status scalar packet;
- checkpoint/result serialization and Matplotlib PDF generation.

The fitted-grid monitor, inverse CDF, regular-stratum guard, remap weights,
metric rebuild, and cache invalidation do not have a theoretical reason to
remain CPU-bound.

## Implementation Order

1. Introduce a `GridMetricEpoch` object with host metadata plus device-primary
   coordinates/metrics.
2. Port monitor construction and wall/interface indicators to fixed-shape GPU
   arrays.
3. Port equidistribution inverse-CDF and width-floor projection.
4. Port regular-stratum guard as fixed-sweep device line shifts.
5. Add conservative overlap remap for `q`, density, and conservative momentum.
6. Rebuild CCD/FCCD/PPE/active-geometry caches from the new epoch.
7. Add no-inner-D2H tests and a capillary-wave utilization probe.

## Rejected Routes

- Disable fitted grids.
- Reduce rebuild schedule as a performance fix.
- Force a uniform grid.
- Skip regular-stratum certification.
- Use arbitrary coordinate nudges.
- Use host dynamic compaction for active support in the hot path.
- Remap conserved quantities by nodal interpolation.

## SOLID / Fidelity Audit

- [SOLID-S] Coordinate update, remap, metric epoch, and solver-cache refresh
  should be separable services.
- [SOLID-D] Solvers should depend on a metric-epoch interface, not concrete
  host coordinate arrays.
- [SOLID-X] This artifact changes theory/design only: no physical parameter,
  CFL, damping, smoothing, tolerance, fallback, nonuniform-grid removal,
  interface-tracking rebuild removal, main merge, or branch deletion.
