---
ref_id: WIKI-T-055
title: "FCCD Advection Operator: Option B Flux-Divergence and Option C Node-Output (Hermite Reconstructor)"
domain: theory
status: PROPOSED  # Theory derived + library implemented (CHK-158); end-to-end NS verification deferred (V11)
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-D_fccd_advection.md
    description: Full derivation (this entry is the wiki distillation)
  - path: docs/wiki/theory/WIKI-T-054.md
    description: Gradient matrix formulation that T-055 extends
depends_on:
  - "[[WIKI-T-046]]: FCCD core operator"
  - "[[WIKI-T-053]]: FCCD calculation via CCD d2 closure"
  - "[[WIKI-T-054]]: FCCD matrix formulation + wall/periodic BC"
  - "[[WIKI-T-056]]: FCCD wall Option IV for Dirichlet fields (companion)"
consumers:
  - domain: code
    description: FCCDSolver.advection_rhs, FCCDConvectionTerm, FCCDLevelSetAdvection (WIKI-L-024)
  - domain: cross-domain
    description: WIKI-X-018 advection-axis row (A-01 analogue of H-01)
  - domain: paper
    description: SP-D (short paper for this entry)
tags: [fccd, advection, convection, level_set, flux_divergence, hermite_reconstructor, balanced_force, h01_remediation, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-21"
---

# FCCD Advection Operator: Option B Flux-Divergence and Option C Node-Output

## 1. Why this entry exists

[WIKI-T-054](WIKI-T-054.md) established the FCCD **gradient** operator $\mathbf{M}^{\text{FCCD}} = \mathbf{D}_1 - \mathbf{D}_2\,\mathbf{S}_{\mathrm{CCD}}$ as $\mathcal{O}(H^4)$ uniform with periodic DFT leading coefficient $-7/5760$. Its use has so far been limited to **gradient sites** — $\nabla p$, $\sigma\kappa\nabla\psi$ (SP-C, CHK-156). The advection term $(\mathbf{u}\cdot\nabla)\mathbf{u}$ and the scalar transport $\mathbf{u}\cdot\nabla\psi$ in the current pipeline still use node-centred CCD ([convection.py:35](../../../src/twophase/ns_terms/convection.py#L35), [levelset/advection.py](../../../src/twophase/levelset/advection.py)), defeating the face-locus BF cancellation that SP-C produced for the pressure/capillary balance.

This entry derives two FCCD advection closures — both $\mathcal{O}(H^4)$ uniform, both reusing $\mathbf{M}^{\text{FCCD}}$ and $\mathbf{S}_{\mathrm{CCD}}$ — and specifies the BF-preservation theorem (Option B) that completes the H-01 remediation begun in [WIKI-T-052](WIKI-T-052.md) / [WIKI-T-054](WIKI-T-054.md).

## 2. Notation additions to WIKI-T-054

- Face convention fixed as $f_{j+1/2}$: `face[j]` stores the value at the face between nodes $j$ and $j{+}1$.
- $\mathbf{P}_f \in \mathbb{R}^{N \times (N+1)}$ denotes the new 4th-order **face-value** operator (below §3).
- $\mathbf{R}_4 \in \mathbb{R}^{(N+1) \times N}$ denotes the 4th-order Hermite **face→node reconstructor** (§5).
- $\nabla\!\cdot_f \equiv \mathbf{D}^{\text{node}}_1\mathbf{P}_f^{-1}$ notation is avoided; we work with the concrete sparse operator $(\,\cdot\,)_{i+1/2} - (\,\cdot\,)_{i-1/2}$ over $H$.

## 3. New primitive — face-value interpolation $\mathbf{P}_f$

**Claim.** For a sufficiently smooth nodal field $u$, the 4th-order compact face reconstruction at $f_{j+1/2}$ is
$$
u_{f_{j+1/2}} \;=\; \tfrac{1}{2}(u_j + u_{j+1}) \;-\; \tfrac{H^2}{16}(q_j + q_{j+1}) \;+\; \mathcal{O}(H^4),
\qquad
q := \mathbf{S}_{\mathrm{CCD}} u.
$$

**Derivation** (uniform case, Taylor around $x_{f_{j+1/2}}$). With $x_{j+1/2} := (x_j + x_{j+1})/2$ and $h := H/2$,
$$
u_j = u_f - h u'_f + \tfrac{h^2}{2}u''_f - \tfrac{h^3}{6}u'''_f + \tfrac{h^4}{24}u''''_f + \cdots,
$$
$$
u_{j+1} = u_f + h u'_f + \tfrac{h^2}{2}u''_f + \tfrac{h^3}{6}u'''_f + \tfrac{h^4}{24}u''''_f + \cdots.
$$
Averaging:
$$
\tfrac{1}{2}(u_j + u_{j+1}) \;=\; u_f + \tfrac{h^2}{2}u''_f + \tfrac{h^4}{24}u''''_f + \mathcal{O}(H^6)
\;=\; u_f + \tfrac{H^2}{8}u''_f + \mathcal{O}(H^4).
$$
Using $q_j = u''_j + \mathcal{O}(H^6)$ from the CCD closure,
$$
\tfrac{1}{2}(q_j + q_{j+1}) \;=\; u''_f + \tfrac{H^2}{8}u''''_f + \mathcal{O}(H^4),
$$
so
$$
u_{f_{j+1/2}} - \tfrac{1}{2}(u_j + u_{j+1})
\;=\;
-\tfrac{H^2}{8}\,u''_f + \mathcal{O}(H^4)
\;=\;
-\tfrac{H^2}{16}(q_j + q_{j+1}) + \mathcal{O}(H^4).
$$

**Matrix form.**
$$
\boxed{\;\mathbf{P}_f \;=\; \mathbf{P}_1 \;-\; \mathbf{P}_2\,\mathbf{S}_{\mathrm{CCD}}\;}
$$
with $(\mathbf{P}_1)_{j,\,j} = (\mathbf{P}_1)_{j,\,j+1} = 1/2$, $(\mathbf{P}_2)_{j,\,j} = (\mathbf{P}_2)_{j,\,j+1} = H^2/16$. Both $\mathbf{P}_1, \mathbf{P}_2$ are bidiagonal with structurally identical sparsity to $\mathbf{D}_1, \mathbf{D}_2$.

**Leading truncation** (uniform periodic; symbol derivation as in [WIKI-T-054](WIKI-T-054.md) §7.4). Expanding
$\cos(\omega H/2) = 1 - (\omega H)^2/8 + (\omega H)^4/384 - \mathcal{O}(H^6)$ and combining with $\hat q = -\omega^2(1 + \mathcal{O}((\omega H)^6))$:
$$
\hat P_f(\omega) \;=\; 1 \;+\; \frac{(\omega H)^4}{384}\cdot(1 - \tfrac{1}{2}) \;+\; \mathcal{O}((\omega H)^6)
\;=\;
1 + \tfrac{(\omega H)^4}{768} + \mathcal{O}((\omega H)^6).
$$
Leading relative coefficient $+1/768$ — small and **positive**, so $\mathbf{P}_f$ mildly amplifies at high $\omega$; no dissipative bias added.

## 4. Option B — conservative face-flux divergence

**Flux form.** Define the nodal product $g^{(k,j)}_i := u^{(k)}_i u^{(j)}_i$, reconstruct to the face via $\mathbf{P}_f$, and take the face-to-node central divergence:
$$
F^{(k,j)}_{f_{i+1/2}} \;:=\; \mathbf{P}_f[\,u^{(k)} u^{(j)}\,]_{f_{i+1/2}},
\qquad
\boxed{\;
C^{(j)}_i \;:=\; \sum_k \frac{F^{(k,j)}_{f_{i+1/2}} - F^{(k,j)}_{f_{i-1/2}}}{H}.
\;}
$$
For scalar transport the $j$ index collapses to the transported scalar $\psi$: $F^{(k)}_f = \mathbf{P}_f[u^{(k)}\psi]$.

**Order.** $\mathcal{O}(H^4)$ uniform / $\mathcal{O}(H^3)$ non-uniform (inherits from $\mathbf{P}_f$ and the face-to-node central difference).

**No skew-symmetrisation here.** A split "$\tfrac{1}{2}$cons $+ \tfrac{1}{2}$non-cons" variant is conceivable but is not canonical Option B and is deferred; the present closure is the pure conservative form (analogous to finite-volume flux-divergence with 4th-order face reconstruction).

### 4.1 BF-preservation theorem (Option B on-faces)

**Statement.** If the momentum equation is discretised on the face-locus with the same $\mathbf{M}^{\text{FCCD}}$ for $\nabla p$ and $\sigma\kappa\nabla\psi$ and with Option B for the advection flux divergence, then at mechanical equilibrium $\mathbf{u} \equiv \mathbf{0}$ the discrete residual of
$$
\rho\,\partial_t\mathbf{u} + \rho(\mathbf{u}\cdot\nabla)\mathbf{u} + \nabla p - \sigma\kappa\nabla\psi - \rho\mathbf{g} \;=\; 0
$$
is $\mathcal{O}(H^4)$ uniform and $\mathcal{O}(H^3)$ non-uniform — the same order as the pressure/capillary balance alone.

**Proof.** At $\mathbf{u} \equiv \mathbf{0}$ every face flux $F^{(k,j)}_f = \mathbf{P}_f[u^{(k)}u^{(j)}]_f$ vanishes identically, so $C^{(j)}_i \equiv 0$ exactly (not up to truncation — **identically zero**). The remaining residual is the pre-existing $\nabla p - \sigma\kappa\nabla\psi$ discretisation, whose order is given by [WIKI-T-054](WIKI-T-054.md) §7.4. ∎

**Consequence.** Option B advection is **compatible with BF** at rest even on non-uniform grids, which the current node-centred CCD advection does not guarantee under non-zero curvature gradients (the nodal convective term leaves an $\mathcal{O}(H^2)$ residual at $\mathbf{u}=0$ when interface curvature varies within a cell because the product $u^{(k)}u^{(j)}$ is evaluated at a different locus than the other terms). Option B completes the H-01 remediation begun in [WIKI-T-054](WIKI-T-054.md).

## 5. Option C — Node-output via Hermite reconstructor $\mathbf{R}_4$

**Goal.** Preserve the existing nodal AB2 buffer and ConvectionTerm API — output of the advection operator is nodal, identical shape to [convection.py:35](../../../src/twophase/ns_terms/convection.py#L35) `ConvectionTerm.compute`.

**Claim.** At node $i$, using the face gradients $d_{f_{i\pm 1/2}}$ from $\mathbf{M}^{\text{FCCD}}$ and the nodal $q$ values,
$$
(\partial_x u)_i \;=\; \tfrac{1}{2}\bigl(d_{f_{i-1/2}} + d_{f_{i+1/2}}\bigr) \;-\; \tfrac{H}{16}\bigl(q_{i+1} - q_{i-1}\bigr) \;+\; \mathcal{O}(H^4).
$$

**Coefficient derivation.** Averaging two face-gradient symbols gives
$$
\tfrac{1}{2}(\hat d_{f_{i-1/2}} + \hat d_{f_{i+1/2}})(\omega)
\;=\;
i\omega\cos(\omega H/2)\bigl[1 - \tfrac{7(\omega H)^4}{5760} + \cdots\bigr]
\;=\;
i\omega\bigl[1 - \tfrac{(\omega H)^2}{8} + \mathcal{O}(H^4)\bigr].
$$
The leading $-(\omega H)^2/8$ error must be cancelled. A centred-difference correction of $\mathbf{q}$ has symbol
$$
c H\cdot \hat\Delta_c(\omega) \,\hat S_{\mathrm{CCD}}(\omega)
\;=\;
c H \cdot 2i\sin(\omega H)\cdot(-\omega^2)
\;=\;
c\cdot(-2i\omega^3 H^2) + \mathcal{O}(H^4).
$$
Matching $+i\omega\cdot(\omega H)^2/8 = +i\omega^3 H^2/8$: $-2c = +1/8 \Rightarrow c = -1/16$. Hence

$$
\boxed{\;
\mathbf{M}^{\text{node-FCCD}}_4
\;=\;
\tfrac{1}{2}\mathbf{R}_\Sigma\,\mathbf{M}^{\text{FCCD}}
\;-\;
\tfrac{H}{16}\,\boldsymbol\Delta_c\,\mathbf{S}_{\mathrm{CCD}}.
\;}
$$

where $\mathbf{R}_\Sigma$ is the face-pair-to-node averaging matrix ($(N+1) \times N$ with $\tfrac{1}{2},\tfrac{1}{2}$ per row) and $\boldsymbol\Delta_c$ is the centred nodal difference operator ($(N+1)\times(N+1)$ with $-1, 0, +1$ stencil).

> **Plan-file corrigendum.** The [WIKI-T-054](WIKI-T-054.md)-successor plan draft stated $c = -1/24$ by analogy to $\mathbf{D}_2$. The correct matching coefficient is $-1/16$; the $-1/24$ guess doubles the $q$-correction because $\boldsymbol\Delta_c$ already spans $2H$ whereas $\mathbf{D}_2$ spans $H$. The implementation uses $-1/16$.

**Symbol.**
$$
\hat M^{\text{node-FCCD}}_4(\omega)
\;=\;
i\omega\bigl[1 + \alpha_4 (\omega H)^4 + \mathcal{O}((\omega H)^6)\bigr],
\qquad
\alpha_4 = \tfrac{1}{384} - \tfrac{7}{2\cdot 5760}
\;=\; -\tfrac{11}{11520}.
$$

**Backwards compatibility.** Output shape is $(N+1)$ nodal, identical to `ccd.differentiate(u, ax)[0]`. The `FCCDConvectionTerm.compute` signature therefore matches `ConvectionTerm.compute` exactly; the AB2 history buffer at [ab2_predictor.py:92](../../../src/twophase/time_integration/ab2_predictor.py#L92) sees no shape change.

**Use case.** Drop-in upgrade of the node-centred advection without touching AB2, PPE RHS, CSF, or Rhie-Chow — the minimum-invasion path.

## 6. Level-set variant

Both options apply verbatim to the level-set transport $\partial_t\psi + \mathbf{u}\cdot\nabla\psi = 0$:
- **Option B (flux).** $\partial_t\psi_i = -\sum_k(F^{(k)}_{f_{i+1/2}} - F^{(k)}_{f_{i-1/2}})/H$ with $F^{(k)}_f = \mathbf{P}_f[u^{(k)}\psi]$. Conservative form preserves $\sum_i\psi_i\,\mathrm{d}V$ to boundary-flux accuracy; on periodic domains this is machine precision for zero net boundary flux.
- **Option C (node).** $\partial_t\psi_i = -\sum_k u^{(k)}_i\,(\partial_{x_k}\psi)_i$ with $(\partial_{x_k}\psi)_i$ from the Hermite reconstructor. Nodal form, no explicit conservation guarantee (consistency only).

Wall BC for $\psi$ uses [WIKI-T-054](WIKI-T-054.md) §6 Option III (Neumann). Corresponding spectral filter ($\varepsilon_d$-weighted) is documented in [WIKI-T-002](WIKI-T-002.md); the FCCD variant preserves the filter unchanged.

## 7. Uniform-limit check

Set $\theta_i \equiv 1/2$ in the non-uniform companion $\mathbf{M}^{\text{FCCD,nu}}$ of [WIKI-T-054](WIKI-T-054.md) §5 and $\mathbf{P}_f$ of §3 above. Then $\mu_i \equiv 0$, $\lambda_i \equiv 1/24$, face-value coefficients collapse to $1/2$ and $H^2/16$, and both Options B/C recover the uniform formulas of §4/§5.

## 8. CFL considerations

- **Option C.** Node gradient radius bounded above by CCD radius ([WIKI-T-054](WIKI-T-054.md) Nyquist ≤ 12% relative error); the existing CFL bound in [cfl.py:106](../../../src/twophase/time_integration/cfl.py#L106) applies without modification.
- **Option B.** Composed symbol $-(F_{f_{i+1/2}} - F_{f_{i-1/2}})/H$ has spectral radius bounded by $2\|u\|_\infty/H$ (same as centred 2nd-order upwind); CFL unchanged.

## 9. A3 traceability

| Layer | Decision |
|---|---|
| Equation (Option B) | $C^{(j)}_i = \sum_k \Delta_f[F^{(k,j)}]_i / H$, $F = \mathbf{P}_f[u^{(k)}u^{(j)}]$ |
| Equation (Option C) | $(\partial_x u)_i = \tfrac{1}{2}(d_{f_-}+d_{f_+}) - \tfrac{H}{16}(q_{i+1}-q_{i-1})$ |
| Discretisation | (a) $\mathbf{q} \leftarrow \mathbf{S}_{\mathrm{CCD}}\mathbf{u}$ (pre-factored), (b) $\mathbf{P}_f \mathbf{u}$ or $\mathbf{M}^{\text{FCCD}}\mathbf{u}$, (c) face-to-node divergence or averaging — all $\mathcal{O}(N)$ per axis |
| Code | New `FCCDSolver.advection_rhs(velocity, mode='node'|'flux')`; `FCCDConvectionTerm`/`FCCDLevelSetAdvection` call through; AB2 buffer unchanged; see [WIKI-L-024](../code/WIKI-L-024.md) |
| BF property | Option B: exact zero-residual at $\mathbf{u}=0$ ⇒ BF preserved to $\mathcal{O}(H^4)$ with [WIKI-T-054](WIKI-T-054.md) pressure/capillary gradient |

## 10. Verification programme

| # | Claim | Test file |
|---|---|---|
| V1 | Face gradient $\mathcal{O}(H^4)$ uniform periodic | `test_fccd.py::test_face_gradient_order` |
| V2 | Periodic DFT leading coef $-7/5760$ (±1%) | `test_fccd.py::test_periodic_symbol` |
| V3 | Face value $\mathbf{P}_f$ $\mathcal{O}(H^4)$ | `test_fccd.py::test_face_value_order` |
| V4 | Node gradient $\mathbf{M}^{\text{node-FCCD}}_4$ $\mathcal{O}(H^4)$ | `test_fccd.py::test_node_gradient_hermite_order` |
| V5 | Wall Option III zero face (Neumann $\psi$) | `test_fccd.py::test_wall_option_iii` |
| V6 | Wall Option IV mirror closure (Dirichlet $u$) | `test_fccd.py::test_wall_option_iv` |
| V7 | CPU/GPU parity rtol 1e-12 | `test_fccd_gpu_smoke.py` |
| V8 | TGV agreement vs `ConvectionTerm` | `test_fccd_convection.py::test_tgv_agreement` |
| V9 | AB2 buffer shape compat | `test_fccd_convection.py::test_ab2_compat` |
| V10 | Rotation volume conservation (flux mode) | `test_fccd_advection_levelset.py::test_flux_mode_mass_conservation_uniform_divfree` |

V1–V10 all pass at CHK-158 completion. V11 (BF residual on WIKI-E-030 benchmark) deferred to a future R-1 PoC CHK.

## 11. Scope and limits

- 3D: operator is dimension-agnostic (axis-by-axis loop); tests currently cover 1D + 2D.
- Full H-01 pipeline swap (PPE RHS / CSF face form / Rhie-Chow disable under flux mode): implemented at the primitive level (`face_divergence`, `face_value`) but wire-up deferred; tracked as R-1 PoC successor.
- GFM coupling: FCCD advection tested outside GFM path; combined stability deferred.
- Non-uniform + periodic: uncommon combination; coverage is uniform+periodic and non-uniform+wall.

## 12. References

- [WIKI-T-046](WIKI-T-046.md) — FCCD core operator.
- [WIKI-T-050](WIKI-T-050.md) — Non-uniform cancellation coefficients $\mu, \lambda$.
- [WIKI-T-051](WIKI-T-051.md) — Wall BC Options I/II/III catalogue.
- [WIKI-T-053](WIKI-T-053.md) — FCCD scalar form via CCD closure.
- [WIKI-T-054](WIKI-T-054.md) — Gradient matrix formulation; periodic DFT.
- [WIKI-T-056](WIKI-T-056.md) — Wall Option IV for Dirichlet $u$ (companion).
- [WIKI-L-024](../code/WIKI-L-024.md) — Library module (FCCDSolver + consumers).
- [WIKI-X-018](../cross-domain/WIKI-X-018.md) — H-01 remediation map (advection row).
- SP-D — Short paper backing this entry.
