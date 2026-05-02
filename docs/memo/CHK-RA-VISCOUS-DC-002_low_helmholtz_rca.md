# CHK-RA-VISCOUS-DC-002 — Low-order viscous Helmholtz RCA

Date: 2026-05-02  
Branch: `ra-viscous-dc-20260502`  
Scope: implicit-BDF2 viscous defect-correction low-order Helmholtz cost.

Validation note: CHK-RA-VISCOUS-DC-003 refines the provisional H4 verdict below.
Raw host-device RHS transfer is not dominant at N=128; the confirmed host-side
bottleneck is Python/NumPy sparse assembly of the structured stencil.

## Observation

The N=128, T=1, alpha=4 fully-periodic static-droplet validation completed on
remote GPU with the selectable viscous solver set to `defect_correction`.

Run facts:

- grid: 128x128 cells, periodic-periodic, initially fitted non-uniform grid,
  alpha=4.
- time: fixed dt=0.001235, 810 accepted steps, final time 1.0.
- wall time: 28m04s, about 2.08 s/step.
- grid mode: `static non-uniform`; local config inspection gives
  `solver._rebuild_freq == 0`, so this run does not rebuild the grid every
  step after the initial fit.
- final/max kinetic energy: `3.2082084486958047e-06`.
- final/max volume drift: `0.0`.
- final/max deformation: `0.0`.

A one-step low-order Helmholtz micro-timing on the same remote GPU and same
fitted N=128 grid gave:

| component | time [s] |
|---|---:|
| build sparse matrix for u | 0.253 |
| build sparse matrix for v | 0.247 |
| sparse LU for u | 0.0868 |
| sparse LU for v | 0.0876 |
| one two-component triangular solve | 0.146 |

The current DC path performs one initial low solve plus one low solve per
correction. With three corrections, this is roughly
`0.675 + 4*0.146 = 1.26 s/step` before the high-order residual and PPE stages.
Thus the low-order viscous Helmholtz path is the dominant cost, but its dominant
part is not only LU; Python/host sparse assembly and host-device transfer are
also first-order terms.

## Operator theory

For component `alpha`, the low correction currently approximates

```text
A_L,alpha u = u - tau/(Re rho) * div( mu Q_alpha grad u ),
```

where `Q_alpha` is diagonal. In 2D,

```text
Q_x = diag(2, 1),    Q_y = diag(1, 2).
```

The row-scaled matrix is generally not symmetric in the Euclidean inner
product when `rho` varies. Multiplication by the positive mass/density weight
produces the weighted form

```text
rho A_L,alpha u = rho u - tau/Re * div(mu Q_alpha grad u),
```

whose bilinear form is coercive for positive `rho, mu`:

```text
int rho u^2 dx + tau/Re int mu (grad u)^T Q_alpha grad u dx.
```

Therefore exact sparse LU is sufficient but not mathematically necessary. An
inexact low solve is admissible if its residual is controlled tightly enough
that the outer defect-correction residual still contracts. Accuracy is anchored
by the high-order residual equation, not by exactness of the low solver.

## Hypotheses and tests

### H1 — The run is slow because the fitted grid is rebuilt every step.

Rejected for the N=128 static-droplet validation. The YAML uses
`grid.distribution.schedule: static`, and local config inspection gives
`_rebuild_freq == 0`. The run prints `[static non-uniform] grid built from IC`.
Dynamic-grid cases can still invalidate factor caching, but this is not the
cause of the observed 28-minute run.

### H2 — Sparse LU factorization itself is the sole bottleneck.

Rejected. LU costs about `0.174 s/step` for two components, while sparse matrix
assembly costs about `0.500 s/step` and triangular solves cost about
`0.584 s/step` for four low solves. LU matters, but optimizing only LU cannot
recover most of the lost time.

### H3 — Python-level sparse assembly is a dominant bottleneck.

Supported. `_build_component_matrix` loops over every node and neighbor in
Python, computes row/column/value triplets, transfers them to GPU, and then
forms a CuPy sparse matrix. On N=128, this takes about `0.25 s` per component,
more than the corresponding GPU sparse LU. This is a structural implementation
issue, not a numerical-theory issue.

### H4 — Host/device ping-pong is a dominant bottleneck.

Supported. `_LowOrderViscousHelmholtzSolver` copies `mu`, `rho`, and each RHS to
host with `backend.asnumpy`, then copies vectors back to device for sparse LU
and solves. Because this happens every step and every low solve, the current
implementation is not a GPU-resident algorithm even though the sparse factor is
CuPy-side.

### H5 — Sparse pattern fixedness is invalid when the grid moves.

Rejected in topology, accepted in coefficients. If the number of nodes and
boundary topology are fixed, the nonzero pattern of the second-order Helmholtz
operator is fixed even when non-uniform coordinates, `rho`, and `mu` change.
Only values change. Therefore row/column pattern caching is mathematically safe
for both static and dynamically rebuilt tensor grids, while numeric factor
caching is not safe when geometry or coefficients change.

### H6 — Matrix-free low solves cannot preserve accuracy.

Rejected as a theorem. Direct sparse LU is not part of the defect-correction
accuracy proof. The high-order fixed point is preserved when the outer residual
is evaluated with `A_H`; an inexact low correction only needs residual control.
For variable density, vanilla Euclidean CG is not the correct formulation, but a
weighted SPD matrix-free solve, flexible Krylov, Chebyshev/Jacobi smoothing, or
multigrid can be mathematically admissible if the low residual is measured and
bounded.

### H7 — A shared scalar Helmholtz low operator is theoretically impossible.

Rejected. The component operators differ only by the diagonal stress weights
`Q_x` and `Q_y`. A scalar operator

```text
A_S u = u - tau c/(Re rho) div(mu grad u)
```

is spectrally equivalent to both component operators for any fixed positive
`c`. Choosing `c=3/2` in 2D gives anisotropy ratios between `2/3` and `4/3` at
the bilinear-form level. This is admissible as a DC preconditioner/low operator
because the missing tensor anisotropy is recovered by the high residual. It
requires convergence monitoring; it is not an exact replacement for the high
viscous operator.

### H8 — The slow path is caused by physical instability or loss of static
balance.

Rejected as primary for cost. The validation stayed bounded through T=1 with
zero reported volume drift and deformation. KE grew slowly to `3.2e-6`, so the
static balance is not exact, but the wall-time issue appears in the linear
viscous correction path independently of blow-up or gross physical failure.

## Cause identified

The root cause of the observed low-order Helmholtz cost is that the current DC
low solve is not yet a GPU-native low-order solver. It repeatedly constructs a
small-stencil sparse matrix through Python/NumPy host loops, sends data to the
GPU, performs two component-wise sparse LU factorizations, and repeatedly moves
RHS vectors through host memory before triangular solves.

This is a mathematical-design mismatch: the low problem is a local structured
Helmholtz operator on a tensor grid, but the implementation treats it as a fresh
general sparse matrix problem at every time step.

## Design consequences

1. First optimization target: fixed sparse pattern with GPU-side value update.
   This preserves the current direct-LU low solve and directly attacks the
   confirmed assembly bottleneck.
2. Second target: remove host RHS transfers and keep low correction vectors
   GPU-resident.
3. Third target: optional shared scalar Helmholtz low operator with `c=3/2` and
   high-residual monitoring. This halves factorization and solve count while
   preserving the DC fixed-point contract.
4. Fourth target: matrix-free weighted SPD or flexible Krylov/multigrid low
   solve. This is theoretically admissible only with explicit inner residual
   controls and outer high-residual verification.

[SOLID-X] Investigation only. No production module boundary changed. The
mathematical contract remains `A_H` residual plus controlled `A_L` correction;
no tested code is deleted.
