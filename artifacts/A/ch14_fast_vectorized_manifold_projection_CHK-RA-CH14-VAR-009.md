# CHK-RA-CH14-VAR-009 — Fast vectorized manifold projection design

## Claim

The q-to-interface-manifold route should not make a full nonlinear optimizer
the normal time-step primitive.  The owned physical state remains the charted
interface `Gamma_h`; transported cell volume `q_T` is a measurement to be
split as

```text
q_T = Q_h(Gamma*) + r.
```

For runtime, `Gamma*` should be found by a vectorized chart projection and, at
most, a small low-mode linearized correction.  Full nonlinear minimization is
reserved for oracle/fail-close analysis, where it can falsify the fast route
without becoming the fast route.

This keeps the origin-reset principle intact:

```text
surface energy acts on Gamma_h
q is a finite-volume measurement
phi is a gauge
r is diagnosed, not converted into capillary force
```

## Evidence Being Preserved

The baseline and failed screened graph-q runtime evidence remain negative
knowledge.  The fast route is not a repair of screened q/phi projection.

The graph q-manifold oracle from `CHK-RA-CH14-VAR-008` shows the useful
separation:

| Case | Observation | Design consequence |
|---|---|---|
| clean `q_T` | residual at roundoff | direct chart measurement is enough |
| representable low mode | residual at roundoff | physical low modes should enter `Gamma*` |
| zero-column cell residual | `residual_l2 = 1.381067932005e-04`, column volume at roundoff | off-manifold cell modes should stay in `r` |

The failure mode to avoid is therefore:

```text
make every cell component of q_T a hard geometric constraint
-> force Gamma_h to carry non-geometric high modes
-> curvature/pressure/velocity amplify them
```

## Runtime Unknowns

Use compact chart variables, not cell fractions, as the optimized unknowns.

### Graph Chart

Represent the interface by a modal or nodal height vector:

```text
eta = eta_base + B_g a
```

where:

- `a` is a small vector of selected graph modes or local spline coefficients;
- `B_g` is a fixed basis matrix or implicit FFT/DCT basis;
- `Q_h(eta)` is still evaluated on finite-volume cells for measurement;
- `q_T` never becomes the owner.

For periodic capillary waves, the fastest direct measurement is the column
volume:

```text
m_j(q_T) = sum_i q_T[i,j] * cell_area[i,j]
eta_meas[j] = y_bottom + m_j(q_T) / dx_j
```

Then project `eta_meas` to the admitted graph chart:

```text
a* = low_modes(eta_meas - eta_base)
eta* = eta_base + B_g a*
r = q_T - Q_h(eta*)
```

This is an `O(N log N)` FFT/DCT projection or `O(N K)` dense-basis projection
with `K << N`, and it is naturally vectorized over columns and batches.

### Closed-Curve Chart

Use a periodic curve, with a low-mode radial chart as the first fast closed
droplet route:

```text
X(theta) = c + R(theta) [cos theta, sin theta]
R(theta) = R0 + B_c a
```

For the early Ch14 mode-2 droplet gate, this is enough to test the same
variational principle without solving for every vertex coordinate.  The direct
measurement should start from radial or angular moments of `q_T` around the
predicted center:

```text
M_l(q_T) = sum_C q_T[C] * cell_area[C] * basis_l(theta_C)
```

The low radial coefficients are recovered from these moments, then exact area
is restored by an analytic `R0` correction.  The residual is again:

```text
r = q_T - Q_h(X*)
```

If a droplet is not star-shaped in the chosen center, this chart must fail
closed rather than silently switching to a different theory.

## Vectorizable Discretization

The implementation should be array-first:

| Object | Shape | Notes |
|---|---|---|
| graph coefficients | `(batch, K_g)` | small dense vectors |
| graph heights | `(batch, nx)` | produced by FFT/DCT or `a @ B_g.T` |
| closed coefficients | `(batch, K_c)` | low radial or curve modes |
| curve vertices | `(batch, M, 2)` | generated from coefficients |
| cell volumes | `(batch, ny, nx)` | finite-volume measurement |
| active cell mask | `(batch, ny, nx)` | narrow interface band only |
| residual | `(batch, ny, nx)` | diagnostic, not force state |
| segment vectors | `(batch, M, 2)` | `roll`-based, no Python vertex loop |
| segment lengths | `(batch, M)` | curve energy and gradient |

All operations should be expressible through `backend.xp`:

```text
roll, take, where, sum, einsum/matmul, fft/rfft when available
```

The expensive geometric part is `Q_h(Gamma_h)`.  It should be evaluated only in
the narrow active band determined by the predicted interface plus a declared
motion envelope.  Outside that band, `q` is copied as pure phase values.  This
is not rebuild skipping; it is the finite-volume statement that only cells cut
by the current chart can change their partial volume.

## Fast Projection Ladder

### F0. Direct Chart Projection

Use chart-specific moments:

```text
graph:        column volume -> eta_meas -> admitted modes
closed curve: angular/radial moments -> R(theta) modes -> area correction
```

This is the default runtime path.  It has no nonlinear iterations and no
cell-wise hard q constraint.

PASS condition:

```text
constrained moments match
E_h(Gamma*) does not grow beyond the admitted physical mode change
r has no low-mode constrained content
```

### F1. One-Step Linearized Manifold Projection

If F0 leaves low-mode residual content, take one linearized correction around
the predicted interface `Gamma_p = Gamma(a_p)`.

Define:

```text
q_p   = Q_h(Gamma(a_p))
dq    = q_T - q_p
J_B   = DQ_h(Gamma(a_p)) B
g_E   = dE_h/da at a_p
H_E   = chart Hessian or positive semidefinite mode stiffness
C_B   = derivative of exact constraints
```

Then solve the small KKT system:

```text
[ J_B^T W J_B + beta H_E   C_B^T ] [ da ] =
[ C_B                     0     ] [ lam]

[ J_B^T W dq - beta g_E ]
[ c(q_T) - C(Gamma_p)   ]
```

with `K` equal to the number of admitted chart modes, not the number of cells.
The update is:

```text
a* = a_p + da
Gamma* = Gamma(a*)
r = q_T - Q_h(Gamma*)
```

This is vectorizable because `J_B` is a batched active-band matrix.  In graph
mode, many entries are analytic column derivatives.  In closed radial mode,
finite differences can be taken per mode in a batched call:

```text
Q_h(a_p + eps e_l) for l = 1..K
```

This costs `K+1` measurements, not a nonlinear solve over all cells.

### F2. Two-Step Trust Check

Allow a second F1 step only if the predicted decrease in low-mode residual and
energy mismatch is observed after the first step.  Otherwise fail closed with
the residual report.  This prevents the old pattern of iterating a broken
projection until the interface becomes rough.

### F3. Full Nonlinear Solve

Use only for oracle, regression, or incident analysis:

```text
min_a 1/2 ||Q_h(Gamma(a)) - q_T||_W^2 + beta E_h(Gamma(a))
```

This solve answers whether the fast approximation missed an admissible chart
state.  It is not a runtime primitive and must not be used to make all-cell
`q_T` exact by default.

## Approximation Semantics

The approximations above are not tolerance weakening, smoothing, damping, CFL
retuning, rebuild skipping, or a fallback scheme.  They are declarations of
the admitted interface chart and measurement metric.

| Approximation | Meaning | Required diagnostic |
|---|---|---|
| low-mode chart | only selected material interface modes are admitted | discarded spectrum in `r` |
| active-band `Q_h` | only cut cells can carry partial-volume changes | band coverage and missed-cut check |
| one-step linearization | transport stayed close to the chart tangent space | residual decrease and step norm |
| radial closed chart | droplet is star-shaped in selected center | star-shaped validity and area error |
| analytic area correction | exact volume is physical, high cell modes are not | area before/after and `r` moments |

The rule is:

```text
approximate Gamma*, never hide r.
```

## Equation -> Discretization -> Code Map

| Equation | Discretization | Code target |
|---|---|---|
| `E[Gamma]=sigma |Gamma|` | graph segment length or polygon edge length | chart energy module |
| `q=Q_h(Gamma)` | finite-volume cut measurement in active band | vectorized `Q_h` wrapper around cut geometry |
| `q_T=Q_h(Gamma*)+r` | residual split after projection | projection diagnostic record |
| exact volume constraint | column total, polygon area, or component volume | small constraint matrix `C_B` |
| `dE(Gamma)` | graph mode stiffness or polygon edge covector | chart variational covectors |
| pressure/force work | later `T_h^T dE` face-cochain map | runtime connection after closed oracle |

The immediate implementation unit should be a library-independent diagnostic
module or experiment helper with these pure functions:

```text
graph_moments_from_q(q_T, grid) -> eta_meas
project_graph_modes(eta_meas, basis) -> eta_star, coeffs
closed_moments_from_q(q_T, grid, center, basis) -> coeffs
build_curve_from_coeffs(coeffs) -> X
measure_q_from_chart(chart_state, grid, active_band) -> q_phys
split_residual(q_T, q_phys, constraints) -> residual_report
```

Only after those helpers pass graph and closed oracle gates should the runtime
receive a `ProjectionResult` object:

```text
Gamma_star, q_phys, residual, constraint_report, energy_report
```

## Complexity Target

Let `N` be cells, `N_b` active-band cells, `K` chart modes, and `M` curve
vertices.

| Route | Cost | Runtime role |
|---|---:|---|
| F0 graph direct | `O(N)` or `O(nx log nx)` | default capillary-wave path |
| F0 closed moments | `O(N_b K + M K)` | default closed oracle candidate |
| F1 linearized | `O((K+1) N_b + K^3)` | rare correction |
| F3 nonlinear | many `Q_h` calls | oracle/fail-close only |

The decisive scaling choice is to keep `K` small and physical.  If `K` must
grow like `N` to match `q_T`, the correct diagnosis is that `q_T` contains
cell-scale non-geometric content or that the chart is invalid.

## Falsification Gates

Before any T/8 runtime experiment, the fast route must pass these gates:

| Gate | PASS criterion | Failure meaning |
|---|---|---|
| graph clean | F0 recovers `eta` and force sign | moment map bug |
| graph low mode | F0 or F1 absorbs representable mode | basis/constraint bug |
| graph high residual | high cell mode stays in `r` | q exactness is leaking into geometry |
| closed mode-2 | radial chart gives restoring energy/force | closed chart bug |
| closed high residual | cell-scale residue remains diagnostic | roughness leak |
| vectorized parity | batched path matches scalar oracle | backend/broadcast bug |
| residual budget | `r` report predicts fail-close before force spike | runtime admission bug |

Only after these pass should Ch14 connect the projection result to the
face-cochain pressure/velocity space.

## Decision

Proceed with:

1. F0/F1 graph helper extraction from the passed oracle.
2. Closed mode-2 F0 radial oracle with vectorized polygon energy, area, and
   residual split.
3. Batched parity tests for graph and closed helpers.
4. Short runtime admission probe only after closed residual classification
   passes.

Do not start with a long T/8 run, and do not use a nonlinear optimizer as the
primary runtime solution strategy.
