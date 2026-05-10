# CHK-RA-CH14-AO-FASTVOL-001 - AO fast sharp-volume route

Date: 2026-05-11
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Worktree: `.claude/worktrees/codex-ra-ch14-ao-fast-volume-20260511`

## Scope

User request: read SP-AO and the corresponding paper equations, treat
`codex/ra-ch14-osc-sharp-volume-20260510` as the direct AO implementation case,
and establish a fast route using approximation, GPU optimization, and efficient
iteration.

No production solver source is changed in this checkpoint. This artifact
records the accepted algorithm route that a later implementation must follow.

## Source Reading

- `docs/memo/short_paper/SP-AO_geometric_cell_fraction_state_space.md`:
  `q_C=|C|theta_C` is the single material-volume owner; `Q_h(phi)=q` is a hard
  compatibility constraint; capillary work is the virtual-work derivative of
  the same geometry and is represented in the pressure-adjoint face Hodge.
- `paper/sections/09b_split_ppe.tex`: the corresponding paper contract is the
  face-space formulation around `q_c`, `T_f(q_c)`, `s_f`, `M_A`, the component
  volume reactions `B_{m,f}`, and the constrained capillary Hodge residual.
- `codex/ra-ch14-osc-sharp-volume-20260510`: the branch materializes the AO
  route as a large implementation slice (`src/twophase/geometry/*`,
  `geometric_phase_runtime`, ch14 YAML activation, and tests). It is useful
  evidence for the state-space contract, but its direct per-step geometry path
  is not the production cost model.

## Direct AO Cost Hazard

The direct route computes `Q_h`, `S_h`, `J_q`, `dS_h`, compatibility projection,
swept fluxes, bundle capillarity, and diagnostics as full-grid stage products.
Even when only a one-cell-thick interface band is active, the implementation
shape encourages:

- full `NX x NY` geometry arrays for every Newton and line-search trial;
- repeated fixed-stratum cut geometry recomputation inside projection;
- Schur CG expressed over dense cell-shaped arrays instead of a compact
  interface graph;
- scalar host synchronizations inside iteration control;
- pressure/capillary diagnostics that may try to represent a face cochain as a
  scalar field even when the accepted theorem object is face-native.

This is exact but not scalable. The paper and SP-AO equations do not require
that cost model; they require that the final accepted state satisfies the same
geometric compatibility and face-Hodge work identities.

## Accepted Fast Route

### 0. Theoretical Split: Geometric Carrier, Smooth Operators

The fast route keeps the SP-AO ownership theorem intact:

```text
q/theta: discontinuous finite-volume material cochain,
phi: smooth gauge chart for the same geometry,
u_f,p: face/pressure cochains paired by the pressure work identity.
```

CCD/DCCD/FCCD/UCCD may be useful only on the smooth side of this split. They
are candidates for `phi` prediction, screened gauge metric `W_eta`, pressure
adjoint pairing, face-state reconstruction, and smooth residual diagnostics.
They are not candidates for differentiating `theta_C` as a smooth scalar or
for replacing the exact geometric maps `Q_h`, `J_q`, `T_q`, and `dS_h`.

### 1. Active-Stratum Geometry Cache

Represent the regular stratum by compact active tables, not full-grid arrays:

```text
A = {cells with 0 < Q_h(phi)_C < |C|} plus one face-neighbor halo,
node_ids[A,4], case_code[A], edge_lambda[A,*],
Q_A, S_A, J_A_local[A,4], dS_A_local[A,4],
face_ids[A,*], component_id[A].
```

Full and empty cells are stored as state flags. They are not revisited by
cut-cell kernels unless a sign-margin event expands the active set. All
periodic quotient and wall ownership is applied while building the active
tables, so seam cells are counted once.

### 2. Approximate Candidate, Exact Acceptance

Fast updates may use frozen-stratum linearization:

```text
Q_h(phi_k + delta phi) ~= Q_k + J_k delta phi,
dS_h(phi_k + delta phi) ~= dS_k + H_S,k delta phi  (optional local secant),
T_q(phi_k + delta phi) ~= T_k.
```

The approximation is only a candidate generator. Acceptance still recomputes
exact `Q_h` and `S_h` on the active stratum and checks:

```text
||Q_h(phi^+) - q^-||_inf <= tau_q,
sign/case margins stay positive,
Delta S_Pi remains inside the projection-work budget.
```

If an exact check fails, refresh the stratum and retry once; if the refreshed
problem fails, fail closed. No tolerance may silently relax the physical volume
contract.

Useful high-order approximations are therefore limited to smooth auxiliary
maps. Examples are FCCD/UCCD prediction of `phi^-`, DCCD/FCCD construction of
the screened gauge Hodge `W_eta`, and high-order face-state reconstruction for
`delta_phi_pred(w)`. Every such approximation is accepted only after the
geometric `Q_h` and face-Hodge work gates pass.

### 3. Compact Matrix-Free Schur Solve

Solve the compatibility projection on the active cell graph:

```text
S_A lambda = J_A W_eta^{-1} J_A^T lambda = b_A.
```

Use matrix-free PCG with:

- warm start from the previous step's `lambda` restricted to current components;
- diagonal plus component-block Jacobi preconditioning;
- optional null/near-null deflation per connected interface component;
- inexact Newton tolerance tied to the downstream exact gate:
  `tau_cg <= min(0.1 tau_q, c_work tau_surface, c_round sqrt(|A|) eps)`;
- exact residual recomputation before accepting the Newton step.

The solve complexity is `O(k |A|)` per Newton update, where `|A|` is the number
of mixed/interface-band cells. The forbidden model is `O(k |C_h|)` full-domain
Schur work per line-search candidate.

### 4. GPU Execution Contract

Production kernels stay device-resident:

- struct-of-arrays active tables and fixed small arity local rows;
- fused case-table kernels for `Q_h/S_h/J_q/dS_h`;
- ELL/CSR-style gathers and scatters for `J_A` and `J_A^T`;
- batched reductions with at most one scalar diagnostic transfer per accepted
  outer iteration;
- no `.get()`, `asnumpy`, Python list materialization, or scalar D2H inside CG
  iteration control;
- mixed precision allowed only for matvec candidates, with FP64 reductions and
  exact final residual gates.

### 5. Bundle Capillary And Pressure-Hodge Coupling

`dS_h`, `T_q`, component volume reactions, pressure range projections, and wall
retractions use the same active tables and face metric `M_A`. The face cochain
is the primary object; scalar pressure reconstruction is an optional diagnostic
and may fail closed without invalidating the computation.

### 6. Activation Gates

Promote the route only after these gates pass:

```text
AO-F1: active-table Q/S/J/dS equals exact full-grid reference on manufactured cuts;
AO-F2: frozen-stratum candidate reduces projection work and passes exact residual gates;
AO-F3: compact PCG iteration count is bounded under nonuniform, periodic, and wall probes;
AO-F4: GPU tests show no per-iteration host synchronization and no full-domain geometry rebuild;
AO-F5: ch14 one-step static/oscillating/capillary runs conserve q and expose face-native pressure diagnostics;
AO-F6: restart restores active tables or rebuilds them deterministically and matches zero-start short runs.
```

## Decision

The accepted route is **AO-Fast**: exact SP-AO state-space invariants with a
compact active-stratum approximation layer used only to propose candidates,
matrix-free preconditioned active Schur solves, and GPU-resident face-native
operators. The route rejects dense full-grid AO projection as the production
model, and it rejects any approximation that is not certified by exact
compatibility and capillary-work gates.

## SOLID-X

Theory/specification artifact only. No solver source, experiment result,
tested implementation deletion, FD/WENO/PPE fallback, damping/CFL workaround,
smoothing, curvature cap, benchmark branch, blanket projection,
QP-as-physics path, or hidden DCCD/UCCD damper introduced.
