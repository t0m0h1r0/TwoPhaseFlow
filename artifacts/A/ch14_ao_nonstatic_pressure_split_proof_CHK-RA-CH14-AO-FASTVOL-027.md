# CHK-RA-CH14-AO-FASTVOL-027 - Proof of certified non-static AO capillary split

## Purpose

User request:

> 未証明なら証明して

This note proves the missing mathematical contract needed to replace the
fail-closed diagonal GPU AO capillary packet by a certified non-static route.
The proof is finite-dimensional and applies to a fixed regular P1 cut-geometry
stratum.  It does not certify the current diagonal approximation; instead it
states exactly which active Schur solve and scalar pressure coordinate must be
certified before the solver may advance.

## 1. Discrete Objects

Let:

```text
q_C          liquid volume cell cochain
phi_v        continuous P1 gauge
Q_h(phi)_C   sharp liquid volume map on the fixed stratum
J            dQ_h/dphi restricted to active mixed cells
E(phi)       sigma S_h(phi)
g            dE/dphi as a nodal covector
W            SPD gauge metric on the active node support
T            face-to-volume tangent map, delta q = T w
L(w)         compatible lift satisfying J L(w) = T w
M_f          SPD face Hodge
```

Assumptions:

1. The sign/case stratum is fixed and regular.
2. `J` has full row rank on the active cell constraints.
3. `W` and `M_f` are symmetric positive definite on their quotient spaces.
4. The lift `L` is linear on the fixed stratum and satisfies `J L = T`.
5. Boundary and periodic quotients have already been applied, so constants and
   wall-null modes are handled by an explicit gauge condition.

These are exactly the gates already required by SP-AO: stratum margin,
rank/conditioning, q/phi compatibility, and pressure-adjoint face space.

## 2. Active Schur Projection Theorem

Define the active Schur operator

```text
S = J W^{-1} J^T.
```

Because `J` has full row rank and `W` is SPD,

```text
lambda^T S lambda
  = (J^T lambda)^T W^{-1} (J^T lambda) > 0
```

for all nonzero active cell cochains `lambda`.  Hence `S` is SPD and the
system

```text
S pi = - J W^{-1} g
```

has a unique solution `pi` on the chosen pressure gauge.

This `pi` is the unique minimizer of

```text
min_mu 1/2 || g + J^T mu ||_{W^{-1}}^2.
```

Proof: differentiating the objective gives

```text
J W^{-1} (g + J^T mu) = 0,
```

which is exactly the Schur equation.  SPD gives uniqueness.  Therefore the
residual

```text
e = g + J^T pi
```

is the `W^{-1}`-orthogonal component of the surface covector that cannot be
represented as a pressure multiplier of the hard volume constraints.

## 3. Young-Laplace Static Criterion

The discrete Young-Laplace static condition is:

```text
exists pi such that g + J^T pi = 0.
```

If this holds, then for any compatible face motion `w`,

```text
-g[L(w)] = pi^T J L(w) = pi^T T w.
```

Thus the capillary covector equals a pressure-reaction covector and the
pressure-balanced drive is zero.  This proves the pressure-exact static route.

If `e != 0`, the non-pressure component is

```text
b_sigma(w) = -e[L(w)].
```

Therefore the correct non-static split is:

```text
capillary(w)        = -g[L(w)]
pressure_reaction(w)=  pi^T T w
balanced_drive(w)   = -e[L(w)].
```

The current diagonal GPU packet violated this theorem because it set
`capillary_face = pressure_reaction_face` even when `e` was nonzero.

Strictly, `b_sigma` can vanish for a nonzero `e` only if `e` lies in the
annihilator of the implemented lift range `L(F_h)`.  That case is not a
valid static certificate; it is a lift/face-space insufficiency and must fail
closed or enrich the lift.  For a capillary wave displacement mode, the lift
range contains the normal interface motion, so a nonzero Young-Laplace
residual gives a nonzero physical capillary drive.

## 4. Scalar AO Pressure Coordinate

The Schur multiplier `pi` is a scalar cell cochain.  Extend it to the full cell
space by the declared gauge, for example zero on inactive cells plus
`H_C`-weighted zero mean on each quotient component.  Define:

```text
p_sigma = pi.
```

Then the pressure-reaction face covector is

```text
r_pi(w) = p_sigma^T T w = (T^T p_sigma)^T w.
```

If `T` is the oriented finite-volume incidence map on the liquid-volume
complex, this is exactly the variational pressure adjoint used by the PPE
face state.  Thus a scalar AO pressure coordinate exists and is unique modulo
the usual pressure gauge.

This proves the missing `pressure_coordinate` contract: the history variable
must be `p_sigma`, not the face reaction itself.  Extrapolating
`p_sigma^{n-1}, p_sigma^{n-2}` and regenerating `T^T p_sigma` preserves the
pressure-adjoint algebra.  Extrapolating a face cochain through a scalar
pressure history without this coordinate is undefined and must remain
fail-closed.

## 5. Certified Approximate Solve Accuracy

Let `pi_k` be an approximate solution and

```text
rho_k = -J W^{-1} g - S pi_k
      = -J W^{-1} (g + J^T pi_k).
```

Then the pressure-coordinate error obeys

```text
||pi - pi_k||_S <= ||rho_k||_{S^{-1}}
                 <= ||rho_k||_2 / sqrt(lambda_min(S)).
```

Also,

```text
||J^T(pi - pi_k)||_{W^{-1}} = ||pi - pi_k||_S.
```

For the balanced face drive,

```text
| (b_k - b)(w) |
  = | (J^T(pi_k - pi))[L(w)] |
  <= ||J^T(pi_k - pi)||_{W^{-1}} ||L(w)||_W.
```

If the lift is bounded by

```text
||L(w)||_W <= C_L ||w||_{M_f},
```

then

```text
||b_k - b||_{M_f^{-1}}
  <= C_L ||rho_k||_{S^{-1}}.
```

This is the precision statement.  A declared tolerance on the Schur residual
directly bounds both scalar pressure-coordinate error and face-drive error.
If `lambda_min(S)` or a Ritz lower bound is unavailable or too small, the
solver cannot certify the error and must fail close.

## 6. PCG, Newton, And DC

Because `S` is SPD, PCG with an SPD preconditioner satisfies the standard
bound

```text
||pi - pi_k||_S
  <= 2 ((sqrt(kappa)-1)/(sqrt(kappa)+1))^k ||pi - pi_0||_S,
```

where `kappa` is the preconditioned condition number.  Warm starts,
component-block Jacobi, and deflation improve `kappa`; they are accelerators,
not correctness assumptions.  Correctness comes from the final residual and
conditioning gates above.

For nonlinear compatibility projection, fixed-stratum `Q_h` is smooth with
Lipschitz Jacobian while the sign/case margins stay positive.  Standard
Newton/Kantorovich theory applies: if the initial residual is small enough and
`J W^{-1} J^T` remains nonsingular, Newton steps with exact residual checks
converge locally.  The commit gate is still exact recomputation of
`Q_h(phi)-q`.

Defect correction is admissible only as a residual-monotone proposal.  Let

```text
R(phi) = Q_h(phi) - q,
delta_phi_DC = -P_0 R(phi).
```

If the frozen preconditioner satisfies the local contraction condition

```text
|| I - J P_0 || < 1
```

in the active residual norm, then the linearized residual decreases.  With the
fixed-stratum Lipschitz remainder, a sufficiently small accepted step also
decreases the exact residual.  Therefore the only valid DC acceptance rule is:

```text
||R(phi + alpha delta_phi_DC)|| < ||R(phi)||,
```

with sign/case and projection-work gates.  If this fails, DC has proved
nothing and is discarded.  A switch to PCG/Newton is valid only as an explicit
declared solver-chain edge; otherwise the step fails close.

## 7. Complexity And GPU Contract

On a fixed active band with `m=|A|` active cells, each `J` row touches at most
the local P1 trace nodes, so

```text
nnz(J) = O(m).
```

A Schur matvec uses:

```text
J^T lambda        O(m) scatter/reduction
W^{-1} z          O(m) for diagonal/block/local compact metric,
                  or O(k_W m) for a certified compact metric solve
J y               O(m) gather/reduction
```

Thus PCG costs

```text
O(k m)
```

for a diagonal/block metric and `O(k k_W m)` for a compact screened metric.
Memory is `O(m)`.  This is the AO-Fast route.  A full-cell Schur construction
or per-iteration full-grid cut-geometry scan is `O(|C_h|)` and is not admitted
as the fast production method.

GPU execution follows from the same sparsity: active rows, nodal support,
Krylov vectors, reductions, and residual gates remain device arrays.  Host
transfer is limited to explicit outer ledger scalars after a candidate solve,
not inside Krylov or line-search control.

## 8. What Is Now Proved

Proved:

1. The active Schur pressure split is well posed under full-row-rank fixed
   stratum assumptions.
2. The Schur multiplier is the scalar AO pressure coordinate required by
   `pressure_coordinate`.
3. The pressure-balanced non-static drive is the lifted residual
   `-e[L(w)]`, not zero by construction.
4. PCG/Newton/DC are admissible only under residual/conditioning gates that
   give explicit accuracy bounds.
5. The certified implementation can be `O(k |A|)` and GPU-resident.

Not proved, and therefore still fail-closed until implemented:

1. The current diagonal Schur approximation satisfies the residual tolerance
   for capillary-wave production.  It does not in CHK-025.
2. The current GPU packet computes `-e[L(w)]`.  It currently cancels it.
3. The production code stores and extrapolates `p_sigma`; it does not yet.

These are implementation obligations, not theory gaps.
