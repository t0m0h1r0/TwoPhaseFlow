# CHK-RA-VISCOUS-DC-003 — Low Helmholtz hypothesis validation

Date: 2026-05-02  
Branch: `ra-viscous-dc-20260502`  
Scope: validation of CHK-RA-VISCOUS-DC-002 hypotheses.

## Purpose

Validate the theoretical hypotheses behind the low-order viscous Helmholtz
bottleneck before implementing optimizations. The tests intentionally separate
mathematical structure from implementation cost so that no ad-hoc performance
patch is accepted as a substitute for the DC contract.

The fixed-point contract remains

```text
A_H u = b,  r_k = b - A_H u_k,  A_L delta_k ~= r_k,
 u_{k+1} = u_k + omega delta_k.
```

Accuracy is controlled by the high-order residual `A_H`, while the low solve is
a contraction/preconditioning mechanism whose residual must be monitored.

## V1 — Sparse pattern fixedness under coefficient and grid-coordinate changes

Test: build the current low-order Helmholtz matrix for a periodic tensor grid
and compare CSC `indptr`/`indices` after changing `mu`, `rho`, and after
rebuilding a non-uniform fitted grid from a different interface geometry.

Result:

```text
same-grid coeff-change comp 0 indptr True indices True
same-grid coeff-change comp 1 indptr True indices True
coords-differ True
rebuilt-grid coord-change comp 0 indptr True indices True
rebuilt-grid coord-change comp 1 indptr True indices True
```

Conclusion: sparse row/column pattern is fixed by node count and boundary
topology, not by the non-uniform coordinate values or variable coefficients.
Therefore fixed-pattern assembly is mathematically safe even when the grid is
rebuilt, provided the shape and boundary topology are unchanged. Numeric factor
caching remains unsafe for rebuilt grids because values change.

## V2 — GPU low-order cost decomposition

Test: remote GPU micro-timing on the N=128 alpha=4 fitted static-droplet grid,
using the current low-order Helmholtz implementation.

Result:

```text
shape (129, 129), hmin 0.005171998362093255
init_total 0.6722867771 s
matrix_build_times [0.2487333689, 0.2447048330] s
splu_times [0.0944010301, 0.0843006698] s
mean_current_solve_components 0.1559847984 s
mean_direct_device_factor_solve 0.1513369288 s
copy_time_total 0.0004958450 s across 12 asnumpy calls
solve_copy_time_total 0.0004251569 s across 10 solve copies
```

Conclusion: sparse LU is not the sole bottleneck. Matrix assembly is larger than
LU factorization, and four low solves per three-correction DC step are also
large. Raw device-host RHS transfer is not a dominant cost at this size; the
important host-side issue is Python/NumPy sparse assembly of a structured
stencil.

## V3 — Inexact low solve versus exact sparse LU

Test: CPU N=16 variable-coefficient wall-bounded representative problem. Keep
the high residual `A_H` exact. Compare DC residual history when low corrections
are solved by exact LU or by low-matrix GMRES with tolerances from `1e-2` to
`1e-8`. This is not a production recommendation to use GMRES; it is a theorem
check that sparse LU exactness is not required for outer DC accuracy.

Result, relative high residual histories:

```text
LU          3.076e-02 1.895e-02 1.191e-02 7.601e-03 4.914e-03 ratio 1.598e-01
GMRES1e-2   3.076e-02 1.898e-02 1.192e-02 7.599e-03 4.905e-03 ratio 1.595e-01
GMRES1e-4   3.076e-02 1.895e-02 1.191e-02 7.601e-03 4.914e-03 ratio 1.598e-01
GMRES1e-6   3.076e-02 1.895e-02 1.191e-02 7.601e-03 4.914e-03 ratio 1.598e-01
GMRES1e-8   3.076e-02 1.895e-02 1.191e-02 7.601e-03 4.914e-03 ratio 1.598e-01
```

Conclusion: the statement "sparse LU is necessary for accuracy" is rejected in
this representative case. The DC outer residual is insensitive to low-solve
exactness once the low solve residual is sufficiently controlled. This supports
future matrix-free or iterative low solvers, but only with explicit low residual
and high residual monitoring.

## V4 — Common scalar Helmholtz low operator

Test: use a scalar low operator

```text
A_S = 0.5 (A_x + A_y),
```

which corresponds to replacing component stress weights `diag(2,1)` and
`diag(1,2)` by the common isotropic coefficient `c=3/2`. Use `A_S` for both
velocity components in the same CPU N=16 high-residual DC test.

Result:

```text
component-low   3.076e-02 1.895e-02 1.191e-02 7.601e-03 4.914e-03 ratio 1.598e-01
scalar-low-c1.5 2.991e-02 1.807e-02 1.064e-02 6.249e-03 3.696e-03 ratio 1.236e-01
random Rayleigh ratio component/scalar: min 0.951, max 1.048
```

Conclusion: the common scalar Helmholtz low operator is not only theoretically
admissible as a spectrally equivalent preconditioner; in this representative
case it contracts the high residual at least as well as the component-specific
low operators. This validates proceeding to a theory-first scalar-low design.

## Hypothesis verdicts

| Hypothesis | Verdict | Evidence |
|---|---|---|
| H1: current slow run is slow because grid rebuilds every step | rejected for static-droplet run | `_rebuild_freq=0`; printed static-grid mode |
| H2: sparse LU factorization is the sole bottleneck | rejected | LU ~0.179s, build ~0.493s, solve ~0.156s per two-component solve |
| H3: Python sparse assembly dominates initialization | supported | build time exceeds LU time |
| H4: raw host-device RHS transfer dominates | rejected/refined | all measured `asnumpy` calls total ~0.0005s; host-side Python assembly is the real host bottleneck |
| H5: fixed sparse pattern is invalid under grid updates | rejected | pattern unchanged under coefficient and coordinate changes |
| H6: matrix-free/inexact low solve cannot preserve accuracy | rejected | low GMRES residual-controlled corrections match LU DC residual history |
| H7: common scalar low Helmholtz is theoretically impossible | rejected | `A_S=0.5(A_x+A_y)` contracts high residual and is spectrally close |

## Design implications

1. First implementation target: fixed-pattern sparse assembly with GPU-side
   value update. This is compatible with dynamic grid rebuilds because only
   values change.
2. Second target: scalar-low Helmholtz option, derived as `c=3/2`, to reduce two
   component factors and repeated solves to one common low operator.
3. Third target: matrix-free/iterative low solvers only after adding explicit
   inner residual controls and preserving high residual diagnostics.
4. Do not prioritize numeric factor caching as the general solution for dynamic
   grids. It is valid only for static geometry and unchanged coefficients.

[SOLID-X] Investigation and design validation only. No production code changed;
no tested code deleted. The result narrows the next code change to low-order
Helmholtz assembly/solver strategy without changing the BDF2/DC mathematical
contract.
