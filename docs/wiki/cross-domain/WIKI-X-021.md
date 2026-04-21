# WIKI-X-021: N-Robust BF-Consistent Full-Stack Architecture — Unified Role Map for the 10-Method Toolkit

## Statement of the principle

The 128² parasitic blow-up documented in [WIKI-X-020](WIKI-X-020.md) proves that the $J^3$-scaling of the CSF-PPE pipeline (κ × ∇H × div, each carrying a CCD metric factor $J = 1/h_\text{phys}$) cannot be tamed by a single operator change. A simulation that passes at $N=64$ and blows up at $N=128$ is not "marginally wrong" — it is *not converging* and therefore not a simulation.

$N$-independence requires that **all five pipeline stages cooperate on a single discretisation philosophy** — namely, every operator that participates in the balanced-force cancellation at the corrector step must live on the same face locus, and every auxiliary field (SDF, curvature, extension) must be consistent with that locus at $\mathcal{O}(h^k)$ with $k$ matching the target accuracy.

The 10-method toolkit developed across the wiki — **BF, CCD, FCCD, CN, AB2, GFM, HFE, IIM, Ridge-Eikonal, FMM** — is sufficient to construct this unified stack. This cross-domain entry is the *role map*: one row per pipeline stage, one column per method responsibility, one link per governing wiki entry.

## Pipeline × Method role map

The NS / two-phase predictor-corrector loop executed in [`ns_pipeline.py`](../../../src/twophase/simulation/ns_pipeline.py) runs five stages per step. The table below assigns each method from the toolkit to the stage where it is the *governing* operator, and names the wiki entries that prove correctness of that assignment.

| Stage | Governing operators | BF-consistency requirement | Relevant wiki |
|---|---|---|---|
| **1. Interface reinitialisation** (ψ, φ → SDF) | **Ridge-Eikonal + FMM** with **σ\_eff / ε\_local** | topological freedom (ridge) + metric rigidity (FMM Eikonal), decoupled per [WIKI-X-019](WIKI-X-019.md) | [WIKI-T-047](../theory/WIKI-T-047.md), [WIKI-T-048](../theory/WIKI-T-048.md), [WIKI-T-057](../theory/WIKI-T-057.md), [WIKI-T-059](../theory/WIKI-T-059.md), [WIKI-L-025](../code/WIKI-L-025.md) |
| **2. Curvature + CSF force** (κ, f = σκ∇ψ) | **CCD** (node) for κ; **HFE** for Young-Laplace jump when split-PPE is active | κ-invariance via ψ-based formula; HFE extends source-side fields before CCD samples them across Γ | [WIKI-T-001](../theory/WIKI-T-001.md), [WIKI-T-008](../theory/WIKI-T-008.md), [WIKI-T-018](../theory/WIKI-T-018.md), [WIKI-T-020](../theory/WIKI-T-020.md) |
| **3. NS predictor** (u* = u + Δt(-AB2 · conv + CN · visc + buoy)) | **AB2** (explicit convection, $\mathcal{O}(\Delta t^2)$) + **CN** (implicit viscous, $\mathcal{O}(\Delta t^2)$) | time-splitting at the IPC $\mathcal{O}(\Delta t^2)$ floor; independent of the spatial operator | [WIKI-T-003](../theory/WIKI-T-003.md) |
| **4. PPE** (∇·(1/ρ)∇p = rhs) | **FVM + DC+LU** (R-1.5 today) → **FCCD face operator** (R-1 target) + **IIM** (sharp-jump corrector) | single-locus Laplacian consistent with the corrector gradient; IIM restores high-order accuracy at interface-crossing stencils | [WIKI-T-017](../theory/WIKI-T-017.md), [WIKI-T-021](../theory/WIKI-T-021.md), [WIKI-T-024](../theory/WIKI-T-024.md), [WIKI-T-034](../theory/WIKI-T-034.md), [WIKI-T-046](../theory/WIKI-T-046.md), [WIKI-L-023](../code/WIKI-L-023.md) |
| **5. Corrector + reprojection** (u = u\* − Δt/ρ · ∇p; post-rebuild projection) | **FCCD gradient** (same face locus as PPE) + **GFM / IIM** reprojection after rebuild | BF identity: $\nabla p = f/\rho$ at rest → *must* share the operator with stage 2's $\nabla_h$; GFM absorbs high-ρ ratio at interface | [WIKI-T-044](../theory/WIKI-T-044.md), [WIKI-T-046](../theory/WIKI-T-046.md), [WIKI-L-024](../code/WIKI-L-024.md), [WIKI-E-029](../experiment/WIKI-E-029.md) |

The **BF-consistency chain** — the one thing that breaks under $J^3$ scaling — is the link between stages 2 and 5: the force $\sigma \kappa \nabla \psi$ constructed from CCD derivatives in stage 2 must be cancelled exactly by $\nabla_h p$ in stage 5 at rest. [WIKI-T-004](../theory/WIKI-T-004.md) is the principle; [WIKI-X-018](WIKI-X-018.md) is the remediation map; [WIKI-X-020](WIKI-X-020.md) is the $N$-scaling evidence that makes the remediation non-optional.

## Why all ten methods are needed (and none can be removed)

The toolkit is not over-complete. Each method addresses a distinct failure mode that the others do not cover.

| Method | What fails without it | Why another method cannot substitute |
|---|---|---|
| **BF** (principle) | parasitic currents at rest | this is the governing invariant; other methods are instances of its enforcement |
| **CCD** | $\mathcal{O}(h^2)$ κ → BF residual floor above CSF floor | FCCD face-operator is $\mathcal{O}(h^4)$ but lives at a different locus and cannot replace κ-on-node; HFE/IIM are interface-crossing tools, not bulk derivatives |
| **FCCD** | mixed-metric BF residual $\mathcal{O}(h^2)$ — the CHK-173 trigger | CCD node-gradient breaks BF with the FVM Laplacian; plain FVM gradient caps accuracy at $\mathcal{O}(h^2)$ and undoes CCD's purpose |
| **CN** | viscous CFL $\Delta t \leq h^2 / (2\nu)$ — prohibitive at high μ or fine grids | explicit would demand $\Delta t \sim 10^{-7}$ on 128²; Euler implicit is only $\mathcal{O}(\Delta t)$ and loses the IPC splitting-order match |
| **AB2** | $\mathcal{O}(\Delta t)$ convection truncation dominates the temporal error | RK3 for convection exists but doubles the force-evaluation count; AB2 is the cheapest scheme that matches CN's temporal order |
| **GFM** | velocity reprojection after grid rebuild leaks $\mathcal{O}(h)$ divergence at the interface for ρ\_l/ρ\_g = 833 | legacy (uniform ρ) reprojector is unsound at ρ_l/ρ_g ≫ 1; IIM is more costly and targets a stricter invariant |
| **HFE** | CCD stencils sampling across [p] = σκ produce Gibbs oscillations | Aslam iterative extension costs O(1000×) more sweeps; truncation-based stencils lose accuracy where it matters |
| **IIM** | jump-aware PPE corrections vanish when ρ-jump is sharp — residual floor at high ratio | HFE is a *field-extension* tool (interface hygiene for CCD inputs); IIM is a *solver correction* (inside the Laplacian) — different axis, complementary |
| **Ridge-Eikonal** | φ cannot simultaneously carry topology and metric (WIKI-X-019) | DGR/split-reinit cannot handle coalescence/pinch-off; plain Eikonal freezes topology |
| **FMM** | seed-front propagation for the Eikonal step after ridge extraction | iterative Godunov-upwind diverges on non-uniform grids (CHK-138); FSM is only marginally faster and does not gain accuracy |

Removing any one row collapses the stack to a lower-order or lower-robustness solver that fails at at least one production benchmark: [WIKI-E-028](../experiment/WIKI-E-028.md) (FMM on Prosperetti), [WIKI-E-029](../experiment/WIKI-E-029.md) (GFM at ρ = 833:1), or [WIKI-E-030](../experiment/WIKI-E-030.md) (H-01 blow-up on α=1.5 grid).

## Remediation ladder — extending WIKI-X-018 with the N-scaling argument

[WIKI-X-018](WIKI-X-018.md) defined the H-01 ladder R-0 → R-1.5 → R-1 → R-2 → R-3. [WIKI-X-020](WIKI-X-020.md) supplied the missing $N$-scaling argument (BF residual $\propto J^3$). Combining the two:

| Tier | Deployment | BF residual at constant κ | BF residual at variable κ | $N$-scaling |
|---|---|---|---|---|
| R-0 (current) | FVM-grad + CCD-RHS mixed | $\mathcal{O}(h^2) \cdot J^3$ | $\mathcal{O}(h^2) \cdot J^3$ | *fails at $N=128$* |
| R-1.5 (immediate) | `_fvm_pressure_grad` on ψ for the corrector | machine precision | $\mathcal{O}(h^2)$ (CSF floor) | $N$-independent at rest |
| R-1 (target) | FCCD unified face operator, SP-A | machine precision | $\mathcal{O}(h^4)$ uniform, $\mathcal{O}(h^3)$ non-uniform | $N$-independent |
| R-1 + A-01-B | FCCD advection (flux-divergence) | machine precision + BF-preservation theorem at motion | $\mathcal{O}(h^4)$ off-rest (theorem) | $N$-independent under transport |
| R-3 (variational) | full IIM reprojection post-corrector | machine precision | $\mathcal{O}(h^4)$ variational | $N$-independent, highest cost |

The recommendation is unchanged from [WIKI-X-018](WIKI-X-018.md): **R-1.5 now, R-1 as the long-term target**. The CHK-173 evidence raises the urgency: without R-1.5, every scaling study beyond $N=64$ is corrupted by an unbounded-in-$N$ BF residual, and every result at $N=64$ is one grid-refinement away from the parasitic blow-up mode.

## What WIKI-X-021 is *not*

This entry does not propose to replace CCD with FVM anywhere. The CCD node operator is retained in:

- stage 1 transport coupling via [WIKI-T-036](../theory/WIKI-T-036.md) phi-primary transport,
- stage 2 curvature κ via [WIKI-T-008](../theory/WIKI-T-008.md) ψ-based formula (invariance theorem, WIKI-T-020),
- stage 2 HFE field extension as the interpolant of record.

What moves to FCCD is *only* the gradient operator on the pressure (stage 5) and — once A-01-B is implemented — the momentum-advection divergence (stage 3 inner loop). Both are face-locus operations that were never CCD-native in the strict sense; they were CCD-*interpolated* onto faces, which is precisely the residual cause of $J^3$.

Conversely, the entry does not propose to abandon BF for a lower-order stable scheme (e.g. upwind pressure). Lower-order schemes mask the symptom without addressing the cause and make every other high-order component of the stack (CCD, FCCD, HFE, IIM) redundant — a net loss.

## Open design questions

1. **FCCD × IIM composition**: when R-1 is deployed, does the IIM jump correction need to be re-derived on the face locus? [WIKI-T-021](../theory/WIKI-T-021.md) is written for node CCD; a face-locus analogue is undocumented.
2. **Ridge-Eikonal × FCCD interaction on non-uniform grids**: σ_eff(x) / ε_local(x) are calibrated against node-CCD κ. Whether the same scaling holds when κ is computed with (hypothetical) face-locus FCCD is open.
3. **GPU-native FCCD corrector**: [WIKI-L-026](../code/WIKI-L-026.md) and [WIKI-T-060](../theory/WIKI-T-060.md) describe the P-01 performance axis for the FVM PPE; the FCCD face-operator equivalent is not yet sketched.

These are tractable follow-ups, not blockers — R-1.5 can be deployed today without resolving them.

## Cross-references

### Principle and scaling evidence
- [WIKI-T-004](../theory/WIKI-T-004.md) — Balanced-Force operator consistency (principle)
- [WIKI-X-018](WIKI-X-018.md) — H-01 remediation map (R-1.5 / R-1 / A-01 / P-01)
- [WIKI-X-019](WIKI-X-019.md) — ξ/φ role separation (topology vs metric)
- [WIKI-X-020](WIKI-X-020.md) — $J^3$ $N$-scaling evidence (CHK-173); Options A/C refutation

### Stage-wise method anchors
- Stage 1 reinit: [WIKI-T-042](../theory/WIKI-T-042.md), [WIKI-T-047](../theory/WIKI-T-047.md), [WIKI-T-048](../theory/WIKI-T-048.md), [WIKI-T-057](../theory/WIKI-T-057.md), [WIKI-T-059](../theory/WIKI-T-059.md); code [WIKI-L-025](../code/WIKI-L-025.md); experiments [WIKI-E-028](../experiment/WIKI-E-028.md)
- Stage 2 curvature/CSF: [WIKI-T-001](../theory/WIKI-T-001.md), [WIKI-T-008](../theory/WIKI-T-008.md), [WIKI-T-018](../theory/WIKI-T-018.md), [WIKI-T-020](../theory/WIKI-T-020.md)
- Stage 3 time integration: [WIKI-T-003](../theory/WIKI-T-003.md) (IPC + AB2 + CN)
- Stage 4 PPE: [WIKI-T-017](../theory/WIKI-T-017.md) (FVM), [WIKI-T-021](../theory/WIKI-T-021.md) (IIM-CCD), [WIKI-T-024](../theory/WIKI-T-024.md) (solver convergence + ADI failure), [WIKI-T-034](../theory/WIKI-T-034.md) (IIM reprojection); code [WIKI-L-023](../code/WIKI-L-023.md)
- Stage 5 corrector: [WIKI-T-044](../theory/WIKI-T-044.md) (G^adj), [WIKI-T-046](../theory/WIKI-T-046.md) (FCCD), [WIKI-T-050](../theory/WIKI-T-050.md) (non-uniform), [WIKI-T-051](../theory/WIKI-T-051.md) (wall BC), [WIKI-T-054](../theory/WIKI-T-054.md) (matrix formulation), [WIKI-T-055](../theory/WIKI-T-055.md) (advection variant); code [WIKI-L-024](../code/WIKI-L-024.md); experiments [WIKI-E-029](../experiment/WIKI-E-029.md), [WIKI-E-030](../experiment/WIKI-E-030.md)

### Short-paper anchors (reading order)
- [SP-A (face-centred upwind CCD)](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md) — FCCD theory
- [SP-B (ridge-Eikonal hybrid)](../../memo/short_paper/SP-B_ridge_eikonal_hybrid.md) — stage 1 design
- [SP-D (FCCD advection)](../../memo/short_paper/SP-D_fccd_advection.md) — A-01-B advection closure
- [SP-E (non-uniform ridge-Eikonal)](../../memo/short_paper/SP-E_ridge_eikonal_nonuniform_grid.md) — CHK-159

## CHK rows

| CHK | Delivery | Stage(s) |
|---|---|---|
| CHK-152 | open: unify G^adj with σκ∇ψ (R-1 gate) | 5 |
| CHK-155 | R-1.5 PoC (3-line edit, immediate) | 5 |
| CHK-158 | A-01 advection companion (FCCD flux-divergence) | 3, 5 |
| CHK-159 | Ridge-Eikonal non-uniform with σ_eff/ε_local | 1 |
| CHK-160 | ch13\_04 fullstack $N=64$ $\alpha=2$ PASS T=8 | 1–5 (full stack baseline) |
| **CHK-173** | **$J^3$ evidence, Options A/C refuted — recorded in [WIKI-X-020](WIKI-X-020.md)** | 2, 4, 5 |
