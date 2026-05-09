# CHK-RA-CH14-BHODGE-KKT-RANK-001: Boundary Hodge Coupled-KKT Rank RCA

## Question

The remaining wall-localized velocity ring in wall-bounded rising-bubble runs is
not a damping/CFL/visualization issue.  It is a compatibility question between
the face state used by conservative common-flux transport and the nodal no-slip
state published after pressure projection.

The physically correct target space is

\[
  K_h=\{ f : D_h f=0,\ C_w f=0\},\qquad C_w=B_hR_h.
\]

The question is whether the current production operators can be completed into
a coupled pressure+wall Hodge projection without violating the existing
pressure complex, GPU-first design, and fail-close contracts.

## Hypotheses And Broken Contracts

| ID | Hypothesis | It would have to preserve / break | Verdict |
|---|---|---|---|
| H01 | The velocity ring is only a plotting artifact. | Numeric `C_w f` and `u-R_hf` would be near roundoff. | Rejected. Previous one-step RCA measured a wall-localized mismatch. |
| H02 | Boundary-face zeroing is enough for no-slip. | Would imply boundary faces determine all wall nodal components. | Rejected. Tangential components on a wall are reconstructed from interior-normal faces, so `C_w f` remains nonzero. |
| H03 | Nodal post-clamping is harmless. | Must preserve the single-state contract `u=R_h f`, `m=rho u`, and next-step flux `f`. | Rejected. It publishes a nodal state different from the preserved transport face state. |
| H04 | Wall-trace-only Hodge projection is a production fix. | Must preserve `D_h f=0` while imposing `C_w f=0`. | Rejected by short run: wall trace to `O(1e-11)` but `div_u=O(1e-2)`. |
| H05 | Pressure-only projection is sufficient. | Must make `C_w f=0` without a wall multiplier. | Rejected. Pressure projection enforces `D_h f=0`, not no-slip trace. |
| H06 | The intersection `ker D_h ∩ ker C_w` is empty. | Would make exact no-slip incompressible face states impossible. | Rejected on small full-wall grids: null dimension was positive. |
| H07 | Current production basis `[G_A,\ M_f^{-1}C_w^T]` spans all constraint corrections. | `rank([D_h;C_w][G_A,C_w^T])` must equal `rank([D_h;C_w])`. | True for the tested full-wall grid; false for mixed periodic-wall. |
| H08 | Coupled KKT is numerically easy once the rank is right. | Condition number should not blow up with the physical `dt`. | Rejected. The block becomes poorly scaled as the pressure block is multiplied by `dt`. |
| H09 | A dense CPU KKT solve is an acceptable production route. | Must satisfy GPU-first, backend-native, and large-grid contracts. | Rejected as production; useful only as a manufactured diagnostic. |
| H10 | Replacing `G_A` by a generic assembled `D_h^T` is harmless. | Must preserve the pressure Green identity and active affine/variational pressure contract. | Rejected as a shortcut. If `G_A` is wrong, fix the pressure complex rather than bypass it. |
| H11 | Mixed periodic-wall can reuse full-wall rows unchanged. | Periodic image nodes must be quotient variables, not extra independent constraints. | Rejected by rank deficiency with current production pressure basis. |
| H12 | The affine-jump pressure block can be used as-is inside the homogeneous KKT block. | Must avoid double-counting capillary/affine source terms in the projection basis. | Risk remains. Homogeneous pressure reaction and source cochains must be separated. |
| H13 | Pressure-coordinate history automatically covers wall reaction history. | BDF2/history must describe every reaction cochain used in publication. | Risk remains. First-order wall reaction history is acceptable only if stated and gated. |
| H14 | DCCD/FCCD/UCCD damping/suppression should remove the ring. | Would modify the physical equations rather than the constraint complex. | Rejected. Negative knowledge: not a production fix. |
| H15 | A penalty/slip wall term is acceptable. | Would replace exact no-slip with an approximate wall law. | Rejected for this problem. The required boundary law is an equality constraint. |

## Efficient Verification Order

Long rising-bubble runs are too expensive and too indirect for this issue.  The
fast discriminating order is:

1. Unit adjointness: verify `C_w^T` against `C_w`.
2. Manufactured wall-only projection: prove `ker C_w` projection works and
   then check whether it preserves `D_h`.
3. Small-grid operator rank probe: assemble `D_h` and `C_w` by basis vectors and
   measure `rank([D_h;C_w])`.
4. Production correction-basis rank probe: measure the rank of
   `[D_h;C_w][G_A,\ M_f^{-1}C_w^T]`.
5. Time-step scaling probe: repeat the rank/condition estimate for realistic
   `dt` scaling before attempting Krylov.
6. One-step rising-bubble comparison: only after the operator tests pass.
7. Short N=32x64 run: only after one-step `D_h f`, `C_w f`, and `u=R_hf` pass.

## Operator Rank Probe

Probe grid: `Nx=6`, `Ny=5`, uniform domain, FCCD face divergence and
production `pressure_fluxes(... variational_adjoint, phase_density)`.

### Full Wall Boundary

```text
faces=71 constraints=86 D_rows=42 C_rows=44
rank([D;C])=59
null_dimension=12
```

The production correction basis spans the constraint corrections:

```text
dt=1:     rankAB=59/59 cond=4.891e+02
dt=1e-2:  rankAB=59/59 cond=3.025e+02
dt=1e-5:  rankAB=59/59 cond=3.002e+05
```

A dense diagnostic least-squares correction removed the constraints to
roundoff:

```text
dense coupled projection residual_l2 = 1.821e-13
rhs_l2                              = 7.318e+01
```

Interpretation: for full-wall topology, the coupled projection is algebraically
possible, but a production implementation needs block scaling and a
preconditioner before physical `dt` runs.

### Periodic-Wall Boundary

```text
faces=71 constraints=66 D_rows=42 C_rows=24
rank([D;C])=52
null_dimension=19
```

The current production correction basis is rank deficient:

```text
dt=1:     rankAB=49/52
dt=1e-2:  rankAB=49/52
dt=1e-5:  rankAB=49/52
```

The residual is not a roundoff effect:

```text
dense coupled projection residual_l2 = 7.930e+00
rhs_l2                              = 7.261e+01
```

A diagnostic comparison showed the exact assembled `[D_h^T,C_w^T]` basis has
full constraint rank in this topology, while the production `[G_A,C_w^T]` basis
does not:

```text
rank A exact_basis = 52/52
rank A prod_basis  = 49/52
rankD=40
rankG=35
```

Interpretation: mixed periodic-wall cannot be promoted to production KKT until
periodic image variables/rows are treated in the correct quotient pressure
space.  Bypassing `G_A` with generic `D_h^T` would hide, not solve, the pressure
complex issue.

## Countermeasures Evaluated

### Candidate A: Coupled constrained KKT in the active pressure complex

Form:

\[
  f=f^\dagger-\Delta t\,G_Ap-\Delta t\,M_f^{-1}C_w^T\lambda,\quad
  D_hf=0,\quad C_wf=0.
\]

This is the correct production direction for full-wall domains, but only after:

- homogeneous pressure reaction is separated from affine/capillary source
  cochains;
- periodic-wall quotient variables are implemented before mixed boundaries are
  enabled;
- block row scaling and preconditioning are added;
- acceptance gates prove `D_h f`, `C_w f`, `u=R_hf`, and `m=rho u` together.

Not implemented as production in this slice because those prerequisites are
part of the mathematical object, not optional engineering polish.

### Candidate B: Wall-trace-only metric projection

Already implemented as a diagnostic:

\[
  \min \frac12\|\hat f-f\|_{M_f}^2\quad\text{s.t.}\quad C_w\hat f=0.
\]

It is valid only as a diagnostic/probe of `C_w` and `C_w^T`.  It is not a
production fix because it breaks `D_h f=0`.

### Candidate C: Dense exact constrained projection

Useful for manufactured probes because it provides a reference on small grids.
Rejected as production because it violates GPU-first design and bypasses the
active pressure complex.

### Candidate D: Reduced face space with built-in wall trace

Potentially attractive after the KKT reference exists.  It must prove that the
reduced basis preserves the pressure Green identity and common-flux transport
adjoint.  Not selected as the first production route.

### Candidate E: Penalties, damping, DCCD/UCCD suppression, CFL tuning

Rejected.  These can reduce a visible ring while violating the exact constraint
complex or changing the physical law.  Record only as negative knowledge.

## Production Decision

No new production solver was enabled by this check.  The valid immediate state
is:

```text
boundary_hodge.mode: off
boundary_hodge.wall_trace_projection: diagnostic only
```

The next production implementation must be a matrix-free coupled projection
with a quotient-compatible pressure space and block preconditioning.  Any
candidate that improves `C_w f` while degrading `D_h f`, pressure Green
identity, common-flux state publication, or GPU/backend-native execution is not
a production fix.

## Validation Commands

Remote operator probes used the same source tree and `.venv`:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock ssh python \
  "cd /root/TwoPhaseFlow && source /root/TwoPhaseFlow/.venv/bin/activate && PYTHONPATH=src python - <<'PY' ..."
```

The probe is intentionally diagnostic and small-grid dense; it is not a runtime
implementation path.
