---
ref_id: WIKI-T-051
title: "Face-Centered Wall BC for FCCD: Ghost-Cell, One-Sided, and ψ-Only Variants"
domain: theory
status: PROPOSED  # Theory derived; PoC pending (paired with WIKI-T-046, T-050)
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-A_face_centered_upwind_ccd.md
    description: SP-A §6.3(2) caveat — face-centred wall stencil undocumented
depends_on:
  - "[[WIKI-T-012]]: CCD Boundary Treatment, Periodic BC, Elliptic Solver — node-centred wall closure (baseline)"
  - "[[WIKI-T-046]]: FCCD operator definition"
  - "[[WIKI-T-050]]: FCCD non-uniform cancellation coefficients"
  - "[[WIKI-T-044]]: G^adj wall handling reference (boundary 0 initialisation)"
consumers:
  - domain: cross-domain
    description: WIKI-X-018 (R-1 FCCD candidate must satisfy wall-bounded benchmarks)
  - domain: future-impl
    description: FCCD PoC §2 wall-driven benchmarks (ch13_02 capillary wave, lid-driven cavity)
tags: [ccd, fccd, wall_bc, ghost_cell, neumann, one_sided, h01_remediation, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-20"
---

# Face-Centered Wall BC for FCCD: Ghost-Cell, One-Sided, and ψ-Only Variants

## Why this entry exists

The node-centred CCD solver ([WIKI-T-012](WIKI-T-012.md)) handles walls via boundary-closure stencils on the unknown nodes $u_0$, $u'_0$, $u''_0$, $u_N$, $u'_N$, $u''_N$. SP-A §6.3(2) noted that the face-centred FCCD operator ([WIKI-T-046](WIKI-T-046.md), [WIKI-T-050](WIKI-T-050.md)) has no analogous closure: when the FCCD stencil $\{u_{i-1}, u_i\}$ for face $f = i-1/2$ reaches the boundary, the natural face $f = -1/2$ lies outside the physical domain and the cancellation-correction terms $\mu(\theta) H \tilde u''_f + \lambda(\theta) H^2 \tilde u'''_f$ require boundary information.

This entry catalogues three viable wall-BC strategies and recommends a default for the H-01 remediation use case.

## Geometry near the wall

Convention (matches existing codebase, see [WIKI-T-012](WIKI-T-012.md) and [`_fvm_pressure_grad`](../../../src/twophase/simulation/ns_pipeline.py#L381)):

- Nodes $x_0, x_1, \ldots, x_N$ with $x_0 = 0$ (left wall) and $x_N = L$ (right wall).
- Faces between nodes: $f_{1/2}, f_{3/2}, \ldots, f_{N-1/2}$ — $N$ interior faces.
- Wall faces $f_{-1/2}$ (left) and $f_{N+1/2}$ (right) lie outside the domain.

For the FCCD evaluation at the **first interior face** $f_{1/2}$ (between wall node $x_0$ and first interior node $x_1$):

- The 2-point stencil $\{u_0, u_1\}$ is well-defined; the face value $D^{\mathrm{FCCD}} u_{1/2}$ can be computed directly.
- The cancellation terms $\mu H \tilde u''_{1/2}$ and $\lambda H^2 \tilde u'''_{1/2}$ require face-side derivative estimates that, via the Chu–Fan combined relations, couple to neighbouring faces — including the **wall face $f_{-1/2}$** in some closures.

The wall-BC question is therefore **how to define $\tilde u''_{-1/2}$ and $\tilde u'''_{-1/2}$** (or, equivalently, ghost values $u_{-1}$, $u''_0$ at the wall).

## Boundary conditions of physical interest

The H-01 remediation context ([WIKI-E-030](../experiment/WIKI-E-030.md), [WIKI-T-045](WIKI-T-045.md)) is the wall-bounded capillary-wave benchmark. The relevant fields and BCs are:

| Field | Wall BC | Physical justification |
|---|---|---|
| $u, v$ (velocity) | no-slip: $u = v = 0$ at wall | viscous wall |
| $p$ (pressure) | Neumann: $\partial p/\partial n = 0$ | mass-conservation projection |
| $\psi$ (CLS) | Neumann: $\partial \psi/\partial n = 0$ | interface meets wall orthogonally |
| $\phi$ (SDF) | Neumann: $\partial \phi/\partial n = 0$ | same reasoning as $\psi$ |

For the H-01 remediation — unifying the operators applied to $\nabla p$ and $\nabla \psi$ — both fields require Neumann wall conditions. This significantly simplifies the FCCD wall design.

## Three wall-BC variants

### Option I: Ghost-cell with Neumann mirror

Define an outside ghost node $x_{-1}$ at distance $h_L^{(-1)}$ to the left of $x_0$ (typically $h_L^{(-1)} = h_R^{(0)}$ to mirror the first interior interval) and assign

$$
u_{-1} \;:=\; u_0 \quad \text{(Neumann mirror)}.
$$

Apply FCCD ([WIKI-T-046](WIKI-T-046.md), [WIKI-T-050](WIKI-T-050.md)) at the wall face $f_{-1/2}$ using the stencil $\{u_{-1}, u_0\}$:

$$
D^{\mathrm{FCCD}} u_{-1/2} \;=\; \frac{u_0 - u_{-1}}{H_{-1/2}} \;-\; \mu\, H \tilde u''_{-1/2} \;-\; \lambda\, H^2 \tilde u'''_{-1/2}.
$$

The leading term vanishes by mirror symmetry: $u_0 - u_{-1} \equiv 0$. The cancellation terms also vanish to leading order because the mirror symmetry forces $\tilde u''_{-1/2}$ even and $\tilde u'''_{-1/2}$ odd about $x_0$, making the latter zero from the symmetric stencil. The result is

$$
D^{\mathrm{FCCD}} u_{-1/2} \;=\; 0 \;+\; \mathcal{O}(H^3),
$$

which is **exactly the Neumann condition with FCCD truncation order**.

**Pros.** Minimal modification — the FCCD operator is reused unchanged; only the ghost extension is added.
**Cons.** Adds one ghost row to every wall-bounded array; requires careful indexing in 2-D corner cells where two walls meet.

### Option II: One-sided face FCCD

Skip the wall face $f_{-1/2}$ entirely; evaluate FCCD only at interior faces $f_{1/2}, \ldots, f_{N-1/2}$. For the cancellation closure of the first interior face $f_{1/2}$, use a one-sided forward approximation for $\tilde u''_{1/2}$ and $\tilde u'''_{1/2}$ derived from $\{u_0, u_1, u_2, u_3\}$:

$$
\tilde u''_{1/2} \;\approx\; \tfrac{2 u_2 - u_1 - u_3}{(\Delta x_1)^2} + \mathcal{O}(H), \qquad
\tilde u'''_{1/2} \;\approx\; \tfrac{u_3 - 3 u_2 + 3 u_1 - u_0}{(\Delta x_1)^3} + \mathcal{O}(1).
$$

(Exact coefficients depend on local non-uniform spacing; the symbolic form is illustrative.)

**Pros.** No ghost cell; works for any wall BC.
**Cons.** Loses one order of accuracy at the boundary face (matches existing CCD boundary closure of WIKI-T-012); extra stencil width may exceed two cells in extreme stretching.

### Option III: ψ-only ghost mirror (recommended for H-01)

Specialise Option I to fields with **Neumann wall BC** ($\psi$, $\phi$, $p$). Because the mirror $u_{-1} = u_0$ exactly enforces $\partial u/\partial n = 0$ at the wall, **no FCCD evaluation is needed at the wall face** — the gradient is *known* to be zero by physical condition.

Implementation reduces to:

```
G^FCCD u_face[f]  for f = 1/2, 3/2, ..., N-1/2  (interior faces, FCCD as in WIKI-T-050)
G^FCCD u_face[f]  = 0                             for f = -1/2, N+1/2 (wall faces, Neumann)
```

The wall faces are explicitly zeroed; the FCCD interior faces use the symmetric two-point stencil and require no extension beyond the existing node array.

**Pros.** Matches the existing G^adj wall treatment exactly (`_fvm_pressure_grad` returns 0 at walls — see [`ns_pipeline.py:393`](../../../src/twophase/simulation/ns_pipeline.py#L393)); no new code path; backward-compatible.
**Cons.** Limited to fields with Neumann BC. Does not extend to no-slip velocity (use Option I or II for $u, v$).

## Equivalence with current G^adj wall handling

The existing `_fvm_pressure_grad` ([ns_pipeline.py L381–395](../../../src/twophase/simulation/ns_pipeline.py#L381)) implements:

```python
(G^adj u)_i = 0.5 * ( (u_{i+1} - u_i) / d_f^{(i)} + (u_i - u_{i-1}) / d_f^{(i-1)} )   for 1 ≤ i ≤ N-1
(G^adj u)_0 = (G^adj u)_N = 0                                                          (wall Neumann)
```

Option III above prescribes the same boundary value (zero) at wall faces, while replacing the **interior** node-centred average with the face-centred FCCD evaluation. The wall handling is therefore **identical**: both schemes assign zero to the wall face, and both use the symmetric extension for the first interior cell.

This equivalence is what permits the immediate-deployment R-1.5 proposal in [WIKI-T-052](WIKI-T-052.md): the wall layer is unchanged, and the interior is the only place the operator differs.

## Recommended deployment

| Use case | Wall BC | Recommended option |
|---|---|---|
| $\psi$ in $\sigma\kappa\nabla\psi$ (H-01 remediation) | Neumann | **Option III** (ψ-only ghost mirror) |
| $\phi$ in SDF post-processing | Neumann | **Option III** |
| $p$ in projection | Neumann | **Option III** |
| $u, v$ no-slip in viscous step | Dirichlet (zero) | **Option I or II** (future work) |

For the immediate H-01 remediation, **Option III alone is sufficient**: all fields entering the BF residual are Neumann, and Option III preserves the wall behaviour of the existing G^adj while upgrading the interior from $\mathcal{O}(H^2)$ to FCCD's $\mathcal{O}(H^3)$ (non-uniform, [WIKI-T-050](WIKI-T-050.md)) or $\mathcal{O}(H^4)$ (uniform, [WIKI-T-046](WIKI-T-046.md)).

## Verification programme (pure-theory)

1. **Mirror exactness.** Verify that for any smooth $u$ with $u'(0) = 0$, the symbolic substitution $u_{-1} = u_0$ yields $D^{\mathrm{FCCD}} u_{-1/2} = 0$ to all orders in the FCCD truncation.
2. **Reduction check.** Set $\mu \equiv \lambda \equiv 0$ in Option III and verify the result equals the existing G^adj wall handling exactly (already proved by the explicit reduction in §"Equivalence" above).
3. **Order at the boundary.** For Option II with the one-sided closure, confirm convergence rate degrades by one order at $f_{1/2}$ but not at $f_{3/2}$ and beyond — matches the WIKI-T-012 baseline behaviour.

## Open issues

- **Velocity wall (no-slip).** Option I (ghost-cell with $u_{-1} = -u_0$ for Dirichlet zero) is straightforward in 1-D but the 2-D corner closure (where two walls meet) requires careful coupling. Deferred to a future entry tied to FCCD-velocity PoC.
- **Periodic BC.** No special treatment needed: the Chu–Fan combined relations close periodically, and FCCD inherits this directly. Documented in [WIKI-T-012](WIKI-T-012.md) §periodic.
- **Inflow / outflow BC.** Not relevant to the H-01 wall-bounded benchmark; deferred.

## References

- [SP-A full draft](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md) §6.3(2)
- [WIKI-T-012](WIKI-T-012.md), [WIKI-T-046](WIKI-T-046.md), [WIKI-T-050](WIKI-T-050.md), [WIKI-T-044](WIKI-T-044.md)
- [`ns_pipeline.py:_fvm_pressure_grad`](../../../src/twophase/simulation/ns_pipeline.py#L381) — current G^adj wall reference
- [WIKI-X-018](../cross-domain/WIKI-X-018.md) (H-01 remediation map)
