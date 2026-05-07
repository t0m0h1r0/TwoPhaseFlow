# CHK-RA-CH14-REMEDY-THEORY-001: capillary remedy theory

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`
Scope: generate and filter remedy ideas for the remaining ch14 capillary
phase/static error after `component_hodge_augmented`.

## Premise

The old `range_projected` production path removed all Hodge drive.  That
algebraic freeze is fixed.  The remaining evidence is different:

```text
no-reinit N32 early stiffness: omega / omega_ref ~= 0.7008
no-reinit N32 first zero:      13.393564 vs 9.381529
reinit-on N32 first zero:       7.578596 vs 9.381529
static N16/32/64 Hodge L2:      nonmonotone residual
```

The force-side problem is not that the interface is or is not an ellipse.  The
interface must be handled as an arbitrary closed trace on a fixed discrete
stratum.  The mathematical object to construct is not a curvature heuristic,
but the face-space Riesz representative of surface-energy virtual work.

## Finite-Dimensional Law

Let `q` be the trace coordinates on one fixed interface stratum.  The stratum
contains the cut graph, component labels, and cell/face incidence pattern.  Let
`w` be a face velocity, and let

```text
T(q): face velocities -> trace-coordinate velocities
```

be the pre-reinit transport differential.  Let the face inner product be

```text
<u,w>_M = u^T M_f w.
```

The discrete surface energy and component volumes are

```text
E_h(q) = sigma S_h(q),
V_h(q) = (V_1,h(q), ..., V_K,h(q)).
```

The capillary covector and component-reaction covectors must be the Riesz
pullbacks

```text
<s,w>_M   = -dE_h(q)[T(q)w],
<b_m,w>_M =  dV_m,h(q)[T(q)w].
```

Equivalently,

```text
s = -M_f^{-1} T(q)^T dE_h(q)^T,
B =  M_f^{-1} T(q)^T [dV_h(q)]^T.
```

Let `R = range(A_f G_f)` denote the pressure-gradient reaction space in the
same face metric.  The physically silent reaction space is

```text
X = [A_f G_f  B].
```

The Hodge drive to be measured is

```text
h = (I - Pi_X) s,
Pi_X s = X (X^T M_f X)^+ X^T M_f s.
```

The production corrector may use the opposite sign depending on the existing
solver convention, namely `a = Pi_X s - s = -h`.  The norm and orthogonality
gate are sign invariant.  What is forbidden is replacing the production force
by `Pi_X s`; that deletes the physical quotient force.

## Theorem Gates

Any remedy must pass these gates before it can be called physical:

| Gate | Required identity |
|---|---|
| Riesz work | `s^T M_f w = -dE_h[T w]` for arbitrary sampled face velocities |
| Volume work | `b_m^T M_f w = dV_m,h[T w]` for each component |
| Projection | `X^T M_f h = 0` and `Pi_X` minimizes `||s-x||_M` over `x in range(X)` |
| Static equilibrium | constrained critical traces satisfy `||h||_M ~= 0` without circle/ellipse classification |
| Noncritical mode | arbitrary nonconstant constrained perturbations satisfy `||h||_M > 0` unless they are true critical modes |
| Rayleigh Hessian | the small-amplitude `n=2` eigenvalue is recovered as a Hessian check, not as a calibration target |
| Reinit split | capillary work is measured only on `q^n -> q_T`; `q_T -> q^{n+1}` is a separate projection ledger |
| Stratum safety | topology/stratum changes make the variational derivative fail closed instead of silently reusing stale derivatives |

## Candidate Space

The classification below avoids near/middle/long time labels.  Each idea is
classified by whether it satisfies the finite-dimensional law.

| ID | Remedy idea | Theory test | Verdict |
|---|---|---|---|
| C01 | Multiply the current capillary cochain by a scalar fitted to Rayleigh-Lamb | fits one Hessian entry but leaves static residual and other modes unproved | reject |
| C02 | Multiply the inertia or density ratio by a scalar | changes all modes and static leakage together; cannot encode `dS_h` | reject |
| C03 | Decrease CFL or time step | early error is O(30%) with `dt*omega_ref ~= 1.6e-3`; not a virtual-work construction | reject |
| C04 | Add damping or viscosity tuning | observed damping is far above physical viscosity; damping hides energy error | reject |
| C05 | Curvature cap | changes the covector without an energy functional | reject |
| C06 | Curvature smoothing | may reduce noise but does not prove `s=-M^{-1}T^TdE` | reject as force law |
| C07 | Use `capillary_range_projection: range_projected` again | theorem gives zero release from rest when `s_prod=Pi_R s` | reject |
| C08 | Use `capillary_range_projection:none` for dynamic cases only | classifier/branch policy; static `none` already leaks component reaction | reject as production |
| C09 | Select policy by circle/ellipse shape diagnostics | violates arbitrary closed-interface requirement | reject |
| C10 | Subtract scalar mean curvature from sampled curvature | continuum-looking, but not tied to discrete `V_m,h` and `M_f` | reject unless derived as `B` reaction |
| C11 | Subtract one constant face component as in current component mode | necessary first reaction slice, but raw `s` remains non-Riesz | partial diagnostic |
| C12 | Tune the component beta | beta is fixed by weighted projection; tuning breaks orthogonality | reject |
| C13 | Add one PPE constraint but ignore `B^TM_f` side conditions | solves divergence but not the metric projection | reject |
| C14 | Weighted normal equations with `X=[A_fG_f B]` | exactly defines `Pi_X` in the solver metric | select for reaction law |
| C15 | Keep scalar `face_implicit` cochain and use the weighted augmented projection | removes constant reaction but does not repair surface Hessian | insufficient |
| C16 | Existing P2/transport variational carrier | variational only in its own carrier; must equal the affine-FCCD face Riesz cochain | diagnostic only |
| C17 | Surface-stress divergence formula | acceptable only if algebraically derived from the same `S_h`, `T`, and `M_f`; otherwise CSF fallback | conditional |
| C18 | Sharp trace polygon length and volume derivatives | directly defines `S_h`, `V_h`, `dS_h`, `dV_h` on a fixed stratum | select |
| C19 | Diffuse Heaviside surface energy derivative | can be variational, but must use the same transport map and match sharp equilibrium/Hessian gates | conditional |
| C20 | Reverse-mode VJP of the actual transport map | gives `T^T dE` without hand-transcribing all local cases | select if backend-safe |
| C21 | Matrix-free finite-difference VJP by face perturbations | tests the identity, but is too expensive/noisy for production | diagnostic |
| C22 | Analytic local VJP from face flux to trace displacement | production-quality version of the selected law | select |
| C23 | Finite-step Gonzalez/AVF discrete gradient for `Delta S_h` | gives nonlinear energy ledger after infinitesimal gates pass | select as extension |
| C24 | Disable reinit in all validation | isolates physical transport but does not fix force law | required diagnostic |
| C25 | Identity-preserving reinit/retraction as capillary force | prior fixed-stratum entropy-dual retraction produced shape anomalies; reinit is not force | reject as force |
| C26 | Store endpoint ledger `q^n -> q_T -> q^{n+1}` | separates physical work from profile projection work | select as measurement law |
| C27 | Improve PPE/DC tolerance | residuals are already small; wrong covector remains wrong after exact projection | reject as primary |
| C28 | Switch deformation diagnostic | useful for reporting, but force law must work before naming modes | diagnostic |
| C29 | Rayleigh-Lamb frequency as calibration input | one benchmark is not the discrete variational law | reject |
| C30 | Rayleigh-Lamb Hessian as acceptance gate | tests the small-amplitude eigenvalue of the selected energy Hessian | select as gate |
| C31 | Multi-component `B` with rank-revealing projection | required for arbitrary closed components and pressure nullspaces | select |
| C32 | Topology hash and fail-closed stratum guards | prevents using derivatives across a changed cut graph | select |
| C33 | QP/minimum-change retraction as physics | optimization constraint is not a capillary virtual-work law | reject |
| C34 | Conservative remap/grid-freezing policy | useful to falsify grid-remap artifacts; not the missing early stiffness cause | diagnostic |
| C35 | Use full `s` in corrector and only project the reaction part | matches quotient force `h`; avoids force deletion | select |
| C36 | Build arbitrary noncritical-mode tests beyond circles/ellipses | proves the method is not a shape classifier | select as gate |

## Survivors

The selected theory is not one trick.  It is a closed diagram:

```text
fixed trace stratum
  -> S_h(q), V_h(q)
  -> dS_h(q), dV_h(q)
  -> T(q)^T pullback to face space
  -> M_f Riesz representatives s, B
  -> weighted projection onto range(A_fG_f) + range(B)
  -> quotient force h, with reinit work excluded
```

The survivors and their roles are:

| Survivor | Role |
|---|---|
| Sharp fixed-stratum `S_h,V_h` | defines the discrete energy being differentiated |
| Transport VJP `T^T` | makes the force adjoint to the actual pre-reinit transport |
| Face metric `M_f` | makes force, pressure range, and component reaction live in one Hilbert space |
| Weighted augmented projection | removes pressure and component reactions without deleting quotient force |
| Finite-step discrete gradient | extends infinitesimal correctness to nonlinear energy ledgers |
| Endpoint reinit ledger | prevents reinitialization work from being counted as capillary work |
| Arbitrary-mode gates | block circle/ellipse or benchmark-specific acceptance |

## Proof Sketches

### Static Equilibrium

If a closed trace is a constrained critical point of `E_h` under component
volumes, then there exist multipliers `lambda_m` such that

```text
dE_h[T w] = sum_m lambda_m dV_m,h[T w]
```

for every admissible transport.  By the Riesz definitions,

```text
s = -B lambda
```

up to the sign convention and pressure-range reaction.  Thus `s in range(X)`,
so `(I-Pi_X)s=0`.  This is independent of whether the shape is represented as
a circle, polygon, distorted trace, or any other fixed-stratum closed curve.

### Noncritical Mode

If `dE_h` is not a linear combination of `dV_h` and pressure reactions, then
`s` has a nonzero component in the quotient of face space by `range(X)`.
Weighted projection cannot remove that quotient component because it is the
orthogonal residual by construction.  Therefore `||h||_M>0`.  This is the
formal reason a nonconstant curvature mode must accelerate from rest.

### Rayleigh-Lamb Check

Rayleigh-Lamb is not an implementation branch.  It checks the Hessian of
`E_h` around the circular constrained critical trace.  For a small resolved
mode amplitude `epsilon`,

```text
E_h(q(epsilon)) = E_h(q0) + 0.5 K_h epsilon^2 + O(epsilon^3),
M_eff,h = ||T^{-1} q'(0)||_M^2,
omega_h^2 = K_h / M_eff,h.
```

The current no-reinit probe gives about `70%` of the reference stiffness, so
the existing scalar cochain is not the correct Hessian.  A selected remedy
must improve this as a consequence of the energy Hessian, not by rescaling.

### Reinit Separation

The physical energy/work law applies to the transport leg

```text
q^n -> q_T.
```

Any profile/reinit/mass-closure leg

```text
q_T -> q^{n+1}
```

is a numerical projection.  It may be necessary for stability, but its change
in `S_h`, deformation, or pressure must be reported separately.  Otherwise a
projection artifact can look like capillary work, which is exactly what the
endpoint smoke demonstrated.

## Implementation Contract

The implementation-facing contract is:

```text
1. Build ClosedInterfaceStratum from psi and grid:
   cut graph, component labels, trace coordinates, topology hash.
2. Compute S_h(q) and V_m,h(q) from that trace, with no circle/ellipse branch.
3. Verify centered finite-difference derivatives dS_h,dV_h inside the stratum.
4. Build or verify T(q)^T for the actual pre-reinit transport endpoint.
5. Form s and B by the M_f Riesz equations.
6. Project with X=[A_fG_f B] using the same M_f.
7. Feed full s to the corrector; use projection only for reaction removal.
8. Store q^n, q_T, q^{n+1} and report transport work separately from reinit work.
9. Fail closed when the trace stratum changes during a derivative probe.
```

The first production-grade path should prefer analytic local VJP for speed and
GPU safety, but a centered fixed-stratum VJP probe is acceptable as a
diagnostic scaffold because it tests the exact identities above.

## Final Selection

The only theorem-grade remedy is:

```text
fixed-stratum surface-energy Riesz cochain
+ same-metric component/pressure reaction projection
+ reinit-separated work ledger.
```

Everything else is either a diagnostic, a validation gate, or a symptom
adjustment.  In particular, the remedy is not damping, CFL retuning, curvature
caps/smoothing, PPE fallback, benchmark-specific branching, raw `none`, blanket
range projection, or QP-as-physics.

[SOLID-X] Theory artifact only; no production source/config/result change, no
tested implementation deleted, no FD/WENO/PPE fallback, damping, CFL
workaround, curvature cap, smoothing, blanket `c -> Pi_R c`, benchmark-name
branch, or QP-as-physics path introduced.
