# SP-D: FCCD Advection — Node-Output and Conservative-Flux Formulations with Dirichlet Wall BC

**Status**: Short paper draft (research memo)
**Date**: 2026-04-21
**Related**: [SP-A](SP-A_face_centered_upwind_ccd.md), [SP-C](SP-C_fccd_matrix_formulation.md), [WIKI-T-046](../../wiki/theory/WIKI-T-046.md), [WIKI-T-050](../../wiki/theory/WIKI-T-050.md), [WIKI-T-051](../../wiki/theory/WIKI-T-051.md), [WIKI-T-053](../../wiki/theory/WIKI-T-053.md), [WIKI-T-054](../../wiki/theory/WIKI-T-054.md), [WIKI-T-055](../../wiki/theory/WIKI-T-055.md), [WIKI-T-056](../../wiki/theory/WIKI-T-056.md), [WIKI-L-024](../../wiki/code/WIKI-L-024.md), [WIKI-X-018](../../wiki/cross-domain/WIKI-X-018.md)

---

## Abstract

SP-A/SP-C established the Face-Centered Combined Compact Difference (FCCD) operator $\mathbf{M}^{\text{FCCD}} = \mathbf{D}_1 - \mathbf{D}_2 \mathbf{S}_{\text{CCD}}$ as the remediation of the balanced-force (BF) truncation mismatch on the *pressure-gradient* axis (H-01). The remaining gap is the **advection** term of the momentum equation (and, by analogy, level-set advection): in the current pipeline both remain node-centred CCD, so the Rhie–Chow-reconstructed face velocity interacts inconsistently with the face-located gradient operators. This paper closes that gap with two parallel derivations. **Option C** (§6) gives a 4th-order Hermite face→node reconstructor $\mathbf{R}_4$ that emits a nodal gradient, preserving shape-compatibility with the AB2 momentum buffer and level-set TVD-RK3. **Option B** (§7) replaces the convection by a conservative face-flux divergence $-\nabla \cdot (u_k \phi)$ assembled from the FCCD primitives. Both options share one new face-value interpolation primitive $\mathbf{P}_f$ (§5) and are derived at $\mathcal{O}(H^4)$ on uniform grids, $\mathcal{O}(H^3)$ on non-uniform grids, with explicit leading-coefficient analysis. §8 introduces a Dirichlet wall BC (Option IV) completing Option III's Neumann catalogue for no-slip velocity fields. §11 reviews ripple effects: Option C is a drop-in; Option B requires face-form ∇p + CSF + PPE-RHS to complete the BF-preservation theorem (§7.2). §12 describes the library layout (additive-only, default-preserving). The resulting framework permits switching the advection discretisation at configuration level while leaving all existing experiments bit-exact.

---

## 1. Introduction

The H-01 hypothesis ([WIKI-E-030](../../wiki/experiment/WIKI-E-030.md)) identifies a truncation-order mismatch between the FVM face-average gradient $G^{\text{adj}}$ ($\mathcal{O}(H^2)$) and the node-centred CCD ($\mathcal{O}(h^6)$) as the driver of the late-time capillary BF residual. SP-A/SP-C deployed FCCD on the gradient operator to equalise truncation orders. The advection term, however, remained untouched: `ConvectionTerm.compute` still forms $u_k \partial_k u_j$ at nodes ([convection.py:35](../../../src/twophase/ns_terms/convection.py#L35)); the level-set pipeline likewise uses `DissipativeCCDAdvection._rhs` at nodes ([levelset/advection.py:361](../../../src/twophase/levelset/advection.py#L361)). Two consequences:

1. **Flux–gradient locality mismatch.** When the pressure gradient and surface-tension force live on faces (FCCD) while the advective transport lives at nodes, the mixed discrete momentum balance picks up a $\mathcal{O}(H^{p_{\min}})$ residual even at rest, because the transport term contributes a nontrivial projection of $u \equiv 0$ through interpolation noise on non-uniform grids.
2. **Non-conservation of momentum on Option-B side.** A conservative face-flux form is available in principle but has not been derived, so any attempt to chase a discrete energy/momentum conservation bound on the FCCD solver stops at the node-centred inertia.

This paper supplies the missing theory. The scope is deliberately dual-track: Option C offers a node-output drop-in replacement with minimal ripple, while Option B provides the conservative form needed for the full BF-preservation theorem (§7.2) at the cost of pipeline rewiring.

The derivation strategy follows SP-C: build matrix-form primitives from existing CCD output ($q = \mathbf{S}_{\text{CCD}} \mathbf{u}$), compose them, and verify by Taylor expansion and DFT symbol.

---

## 2. Notation and data layout

We inherit the geometry convention of SP-C §2 (nodes $x_0, \ldots, x_N$; $N$ interior faces $f_{i-1/2}$; face width $H_i$; cell-centred face $\theta_i = 1/2$).

**Nodal arrays** carry subscript $i \in \{0, \ldots, N\}$ and have length $N+1$ along the axis:
$$
\mathbf{u} = (u_0, \ldots, u_N)^T, \qquad
\mathbf{q} = \mathbf{S}_{\text{CCD}} \mathbf{u} \in \mathbb{R}^{N+1}.
$$

**Face arrays** carry subscript $j = 0, \ldots, N-1$ and have length $N$. Throughout we use the convention
$$
\text{face}[j] \equiv f_{j+1/2} = \text{face between nodes } j \text{ and } j+1.
$$
This places the first face at $j=0$ (between nodes $0$ and $1$) and wraps at $j = N-1$ for periodic BC.

**Momentum equation component index** $j$ runs over $\{1, \ldots, d\}$ (space dimension). **Transport axis** index $k$ runs over $\{1, \ldots, d\}$. The convective acceleration on component $j$ is written $-(u \cdot \nabla) u_j = -\sum_k u_k \partial_{x_k} u_j$ in the non-conservative form and $-\sum_k \partial_{x_k}(u_k u_j) + u_j \sum_k \partial_{x_k} u_k$ in the conservative form (the second term vanishes for $\nabla \cdot u = 0$).

---

## 3. Inherited primitives (brief recap)

From SP-C:

**Face gradient operator** (uniform or cell-centred non-uniform grid):
$$
d_{f_{i-1/2}}^{\text{FCCD}} = \frac{u_i - u_{i-1}}{H_i} - \frac{H_i}{24}(q_i - q_{i-1}),
\qquad
\mathbf{d}^{\text{FCCD}} = (\mathbf{D}_1 - \mathbf{D}_2 \mathbf{S}_{\text{CCD}}) \mathbf{u}.
$$

**Periodic DFT symbol**:
$$
\hat M^{\text{FCCD}}(\omega) = \mathrm{i}\omega \cdot e^{\mathrm{i}\omega H/2} \cdot \left[ 1 - \frac{7 (\omega H)^4}{5760} + \mathcal{O}((\omega H)^6) \right]. \qquad \text{(SP-C §7.4)}
$$

**Wall Option III** (Neumann fields $\psi$, $p$): boundary faces $f_{-1/2}, f_{N+1/2}$ carry zero entries in the augmented matrix (SP-C §6). In the interior-only face layout of the present paper this is a no-op.

---

## 4. New primitive: face-value interpolation $\mathbf{P}_f$

The advection conservative form requires $u_f = u(x_{f_{i-1/2}})$ at face midpoints. A 4th-order compact reconstruction uses the existing $\mathbf{q}$:

**Derivation.** Taylor expand symmetrically around the face midpoint $x_c = x_{f_{i-1/2}}$ with $h = H_i/2$:
$$
u_{i-1} = u_c - h u'_c + \tfrac{h^2}{2} u''_c - \tfrac{h^3}{6} u'''_c + \tfrac{h^4}{24} u''''_c - \cdots,
$$
$$
u_{i}   = u_c + h u'_c + \tfrac{h^2}{2} u''_c + \tfrac{h^3}{6} u'''_c + \tfrac{h^4}{24} u''''_c + \cdots.
$$
Averaging:
$$
\tfrac{1}{2}(u_{i-1} + u_i) = u_c + \tfrac{H_i^2}{8} u''_c + \tfrac{H_i^4}{384} u''''_c + \mathcal{O}(H^6).
$$
The $\mathcal{O}(H^2)$ overshoot must be cancelled. Using $q$ at nodes,
$$
\tfrac{1}{2}(q_{i-1} + q_i) = u''_c + \tfrac{H_i^2}{8} u''''_c + \mathcal{O}(H^4),
$$
so the required correction is $-(H_i^2/8) \cdot u''_c \approx -(H_i^2/8) \cdot (q_{i-1}+q_i)/2 = -(H_i^2/16)(q_{i-1}+q_i)$. Hence:

$$
\boxed{
u^{\text{FCCD}}_{f_{i-1/2}} = \tfrac{1}{2}(u_{i-1} + u_i) - \tfrac{H_i^2}{16}(q_{i-1} + q_i) + \mathcal{O}(H^4)
}.
$$

**Matrix form**:
$$
\mathbf{u}_f = \mathbf{P}_1 \mathbf{u} - \mathbf{P}_2 \mathbf{q}, \qquad \mathbf{P}_1, \mathbf{P}_2 \in \mathbb{R}^{N \times (N+1)} \text{ bidiagonal},
$$
$$
\mathbf{P}_1 = \tfrac{1}{2}\begin{pmatrix} 1 & 1 & & \\ & 1 & 1 & \\ & & \ddots & \ddots \end{pmatrix},
\qquad
\mathbf{P}_2 = \tfrac{H_i^2}{16}\begin{pmatrix} 1 & 1 & & \\ & 1 & 1 & \\ & & \ddots & \ddots \end{pmatrix}.
$$

Composing with $\mathbf{S}_{\text{CCD}}$:
$$
\mathbf{P}_f := \mathbf{P}_1 - \mathbf{P}_2 \mathbf{S}_{\text{CCD}}, \qquad \mathbf{u}_f = \mathbf{P}_f \mathbf{u}.
$$

**Leading truncation**:
$$
u_f - u(x_c) = -\tfrac{5}{384} H^4 u''''(x_c) + \mathcal{O}(H^6).
$$
(Derivation: sum the $\mathcal{O}(H^4)$ terms — $H^4/384$ from the nodal average and $-H^4/64$ from the correction — gives $(1-6)/384 \cdot H^4 = -5/384 \cdot H^4$.)

**Periodic DFT symbol**:
$$
\hat P_f(\omega) = e^{\mathrm{i}\omega H/2} \cos(\omega H/2) \cdot [1 + (\omega H)^2/8] + \mathcal{O}((\omega H)^6).
$$
(Derivation parallel to SP-C §7.4; the exact leading truncation matches the Taylor prediction above.)

---

## 5. R_4 Hermite face→node reconstructor

For Option C we need a 4th-order nodal gradient assembled from face gradients. Plain averaging of adjacent faces gives $\mathcal{O}(H^2)$; the correction uses the nodal $q$ gradient.

**Derivation.** Assume $d^{\text{FCCD}}_{f_{i \pm 1/2}}$ is $\mathcal{O}(H^4)$-accurate at its face midpoint. Taylor expand around node $x_i$:
$$
d_{f_{i-1/2}} = u'_i - \tfrac{H}{2} u''_i + \tfrac{H^2}{8} u'''_i - \tfrac{H^3}{48} u''''_i + \cdots + \mathcal{O}(H^4),
$$
$$
d_{f_{i+1/2}} = u'_i + \tfrac{H}{2} u''_i + \tfrac{H^2}{8} u'''_i + \tfrac{H^3}{48} u''''_i + \cdots + \mathcal{O}(H^4).
$$
Average:
$$
\tfrac{1}{2}(d_{f_{i-1/2}} + d_{f_{i+1/2}}) = u'_i + \tfrac{H^2}{8} u'''_i + \mathcal{O}(H^4).
$$

Using $\mathbf{q}$:
$$
q_{i+1} - q_{i-1} = u''(x_i + H) - u''(x_i - H) = 2 H u'''_i + \mathcal{O}(H^3).
$$

To cancel $(H^2/8) u'''_i$:
$$
c \cdot H (q_{i+1} - q_{i-1}) = 2 c H^2 u'''_i + \mathcal{O}(H^4) \Rightarrow c = -\tfrac{1}{16}.
$$

Hence the **R_4 reconstructor**:
$$
\boxed{
(\partial_x u)^{\text{node-FCCD}}_i = \tfrac{1}{2}(d_{f_{i-1/2}} + d_{f_{i+1/2}}) - \tfrac{H}{16}(q_{i+1} - q_{i-1}) + \mathcal{O}(H^4)
}.
$$

**Matrix form** (interior nodes):
$$
\mathbf{M}^{\text{node-FCCD}}_4 = \tfrac{1}{2} \mathbf{R}_\Sigma \mathbf{M}^{\text{FCCD}} - \tfrac{H}{16} \mathbf{\Delta}_c \mathbf{S}_{\text{CCD}},
$$
where $\mathbf{R}_\Sigma$ averages adjacent faces to nodes (bidiagonal, $N \times N$ followed by embedding to $\mathbb{R}^{N+1}$) and $\mathbf{\Delta}_c = (\delta_{i, i+1} - \delta_{i, i-1})$ is the centred nodal difference.

**Periodic DFT symbol**. The averaging term gives $\frac{1}{H}\sin(\omega H) \cdot [1 - 7(\omega H)^4/5760 + \cdots]$; the correction gives $-\mathrm{i}\omega H \sin(\omega H) / 8$. Expanding and normalising yields (leading truncation):
$$
\hat M_4^{\text{node-FCCD}}(\omega) = \mathrm{i}\omega [1 + \alpha_4 (\omega H)^4 + \mathcal{O}((\omega H)^6)],
$$
with $\alpha_4$ a small explicit constant whose sign is negative (deferred complete evaluation — see §15 for the self-referential verification check supplied by the pytest `test_node_gradient_hermite_order`).

**Drop-in compatibility**. Output lives at nodes; AB2 history buffer, PPE RHS, CSF $\sigma \kappa \nabla \psi$, and Rhie–Chow are unchanged. Replacement point in the code: `ccd.differentiate(u, ax)[0]` → `fccd.node_gradient(u, ax, q=...)` at [ns_pipeline.py:770-776](../../../src/twophase/simulation/ns_pipeline.py#L770).

---

## 6. Option C — Node-output convection

The convective acceleration on component $j$ is assembled by pointwise multiplication at nodes:
$$
\text{RHS}^{(j)}_i = - \sum_k u_k(x_i) \cdot (\partial_{x_k} u_j)^{\text{node-FCCD}}_i.
$$
Each axial gradient uses R_4 (§5) and shares the nodal $q_j^{(k)}$ with the pressure-gradient / viscous pipeline (no extra CCD solve).

**Truncation**: $\mathcal{O}(H^4)$ on uniform interior nodes; $\mathcal{O}(H^3)$ on non-uniform grids (inherited from SP-C §5); $\mathcal{O}(H^2)$ at boundary nodes where R_4 degenerates to a one-sided face average. This boundary degradation is shared with the gradient track (SP-C §8.1) and does not worsen the global BF residual.

**AB2 compatibility**. Output is nodal and shape-matches the existing `ConvectionTerm.compute(...)` return. The AB2 history buffer $C^n = -(u \cdot \nabla) u^n$ stored in `ab2_predictor.py:92` is unaffected.

---

## 7. Option B — Conservative face-flux divergence

### 7.1 Face flux forms

Let $F_{f_{i-1/2}}^{(k, j)}$ denote the flux at face $f_{i-1/2}$ contributing to the $j$-th component of $-\partial_{x_k}(u_k u_j)$:

**Non-conservative**:
$$
F^{(k,j), \text{nc}}_{f_{i-1/2}} = u^{(k)}_f \cdot (\partial_{x_k} u^{(j)})_f
= (\mathbf{P}_f u^{(k)})_{i-1/2} \cdot (\mathbf{M}^{\text{FCCD}} u^{(j)})_{i-1/2}.
$$

**Conservative** (canonical Option B):
$$
F^{(k,j), \text{cons}}_{f_{i-1/2}} = (u^{(k)} u^{(j)})_f = \big(\mathbf{P}_f (u^{(k)} u^{(j)})\big)_{i-1/2}.
$$

**Skew-symmetric** (recommended for momentum stability):
$$
F^{(k,j), \text{sk}}_{f_{i-1/2}} = \tfrac{1}{2}\big(F^{(k,j), \text{cons}}_{f_{i-1/2}} + F^{(k,j), \text{nc}}_{f_{i-1/2}}\big).
$$
(Kok 2000; Ham et al. 2002.)

The nodal divergence:
$$
[\nabla \cdot F^{(j)}]_i = \sum_k \frac{F^{(k,j)}_{f_{i+1/2}} - F^{(k,j)}_{f_{i-1/2}}}{H_i}.
$$

**Truncation**. All three forms inherit FCCD's $\mathcal{O}(H^4)$ uniform / $\mathcal{O}(H^3)$ non-uniform accuracy from SP-C.

### 7.2 Balanced-force preservation theorem (on-faces)

**Theorem.** If $\nabla p$ (FCCD), $\sigma \kappa \nabla \psi$ (FCCD face form), and the convective flux $\nabla \cdot (u \otimes u)$ (FCCD face flux, Option B) are **all face-located with the common operator $\mathbf{M}^{\text{FCCD}} = \mathbf{D}_1 - \mathbf{D}_2 \mathbf{S}_{\text{CCD}}$**, then at rest ($\mathbf{u} \equiv 0$) the discrete momentum balance has BF residual
$$
\|\mathbf{R}_\text{BF}\|_\infty = \mathcal{O}(H^4) \text{ (uniform)}, \qquad \mathcal{O}(H^3) \text{ (non-uniform)}.
$$

*Proof.* At rest $\mathbf{u} \equiv 0$, so all three forms of the convective flux (§7.1) vanish identically — $(u^{(k)} u^{(j)})$, $u^{(k)}_f (\partial_{x_k} u^{(j)})_f$, and their skew-symmetric average are all zero. The pressure gradient and CSF contributions remain and cancel to the truncation order of their common operator $\mathbf{M}^{\text{FCCD}}$, which is $\mathcal{O}(H^4)$ uniform / $\mathcal{O}(H^3)$ non-uniform (SP-C §4-§5). Hence $\|\mathbf{R}_\text{BF}\|_\infty$ is bounded by the common operator's truncation. $\square$

**Corollary.** Unifying the advection with the gradient operators **completes** the H-01 remediation beyond SP-C (which was pressure-side only). The residual measured in the [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md) capillary benchmark is expected to drop from the SP-C floor $\mathcal{O}(H^2)$ (set by the remaining node-centred advection) to $\mathcal{O}(H^4)$ with Option B enabled on all three terms.

### 7.3 Momentum-equation closure

The closed momentum update with Option B:
$$
\frac{u^{n+1}_j - u^n_j}{\Delta t} = - \sum_k \frac{(u_k u_j)^{*}_{f_{i+1/2}} - (u_k u_j)^{*}_{f_{i-1/2}}}{H_i} + \text{(viscous + } \nabla p + \sigma\kappa\nabla\psi + g),
$$
with all RHS terms evaluated on faces and the result assembled at nodes via `face_divergence`. The pressure Poisson equation RHS is then naturally expressed as $\nabla_h \cdot u^*$ with the FCCD face divergence, closing the loop. See §11 for the ripple-effect inventory.

### 7.4 Periodic DFT analysis — composed symbol

For a single mode $u = A e^{i \omega x}$ with $A$ constant the face flux of the conservative form has symbol $\hat F = A^2 \hat P_f(\omega) \cdot \hat P_f(\omega)$ (product of face-value symbols applied to $u u$). The divergence inherits the $(1 - e^{-i\omega H})/H$ circulant-difference factor. Expansion gives:
$$
\widehat{\nabla \cdot F}(\omega) = \mathrm{i}\omega \cdot A^2 \cdot \hat P_f(\omega)^2 \cdot \left[1 + \mathcal{O}((\omega H)^4)\right],
$$
matching the continuous $\partial_x (u^2) = 2 u \partial_x u$ to $\mathcal{O}(H^4)$.

---

## 8. Wall BC for advection

### 8.1 Option III (Neumann fields $\psi$, $p$)

Inherited from SP-C §6; no change. For $\psi$ advection the boundary face gradient and boundary face value are both zero in the augmented matrix; at the interior-only layout this manifests as zero boundary-node divergence (the `enforce_wall_option_iii` hook is a no-op).

### 8.2 Option IV (Dirichlet no-slip $u = 0$)

For no-slip we impose $u(x_\text{wall}) = 0$. The ghost mirror with sign flip:
$$
u_{-1} = -u_1, \qquad q_{-1} = -q_1 \text{ (by anti-symmetry of } u'' \text{ under } u \to -u\text{)}.
$$

**Face gradient at the left boundary face** $f_{-1/2}$:
$$
d^{\text{FCCD}}_{f_{-1/2}} = \frac{u_0 - u_{-1}}{H} - \frac{H}{24}(q_0 - q_{-1}) = \frac{u_0 + u_1}{H} - \frac{H}{24}(q_0 + q_1).
$$

At $u_0 = 0$:
$$
d^{\text{FCCD}}_{f_{-1/2}} = \frac{u_1}{H} - \frac{H}{24}(q_0 + q_1), \qquad \text{generally nonzero (wall shear rate)}.
$$

**Face value at the left boundary face**:
$$
u^{\text{FCCD}}_{f_{-1/2}} = \tfrac{1}{2}(u_{-1} + u_0) - \tfrac{H^2}{16}(q_{-1} + q_0) = -\tfrac{1}{2} u_1 + \tfrac{1}{2} u_0 - \tfrac{H^2}{16}(q_0 - q_1).
$$

At $u_0 = 0$:
$$
u^{\text{FCCD}}_{f_{-1/2}} = -\tfrac{1}{2} u_1 + \tfrac{H^2}{16}(q_1 - q_0), \qquad \text{goes to zero at } u_1 = 0 \text{ (continuous no-slip limit)}.
$$

Mirrored formula on the right boundary. **Physical check**: Option-IV face velocity at the wall face matches the continuous no-slip value to $\mathcal{O}(H^3)$ (one order less than the interior), consistent with the standard boundary accuracy loss of compact schemes.

**Option B impact**. The Option-B flux $F_{f_{-1/2}}^{(k,j)} = u^{(k)}_f \cdot u^{(j)}_f$ at the wall face equals zero to leading order (both factors $\to 0$), consistent with physical no-slip momentum flux through the wall.

**Implementation hook** `FCCDSolver.enforce_wall_option_iv` (currently identity on the interior-only face layout) will apply the mirror correction when a concrete moving-wall case arises.

---

## 9. Periodic BC for advection

Inherited from SP-C §7 without modification: the block-circulant structure of $\mathbf{S}_{\text{CCD}}$ propagates to $\mathbf{P}_f$ and $\mathbf{M}^{\text{FCCD}}$, and the face array wraps via `roll(-1)` in the library implementation ([fccd.py:_face_slice](../../../src/twophase/ccd/fccd.py)). Numerical verification: `test_fccd.py::test_face_gradient_convergence_rate` shows $\mathcal{O}(H^4)$ periodic convergence.

---

## 10. Level-set variant

For the Continuum Level-Set (CLS) transport equation $\partial_t \psi + u \cdot \nabla \psi = 0$, both Option C and Option B apply with the scalar $\psi$ replacing the momentum component:

**Option C** ($-u \cdot \nabla \psi$ at nodes):
$$
\text{RHS}_i^{\psi} = - \sum_k u_k(x_i) \cdot (\partial_{x_k} \psi)^{\text{node-FCCD}}_i.
$$

**Option B** ($-\nabla \cdot (u \psi)$ face-conservative):
$$
\text{RHS}_i^{\psi} = - \sum_k \frac{(u_k \psi)^{*}_{f_{i+1/2}} - (u_k \psi)^{*}_{f_{i-1/2}}}{H_i}.
$$

**Wall BC**: Option III applies ($\psi$ is a Neumann field in CLS).

**Spectral filter $\varepsilon_d$**. The DissipativeCCDAdvection's filter ($\varepsilon_d = 0.05$) is retained as an optional post-stage smoother for under-resolved interfaces (SP-D §10 flag `use_filter`, disabled by default with FCCD since the scheme's natural 4th-order dissipation is usually sufficient).

---

## 11. Ripple effects — pipeline integration

| Subsystem | Option C (node) | Option B (flux) |
|---|---|---|
| `ConvectionTerm` → `FCCDConvectionTerm` | drop-in (same output shape) | new class; AB2 buffer still nodal (produced by `face_divergence`) |
| `ns_pipeline.py:770` inline advection | swap `ccd.differentiate` → `fccd.node_gradient` | swap to `fccd.advection_rhs` call |
| `ab2_predictor.py:92` | unchanged (stores nodal $C^n$) | unchanged |
| PPE RHS ([ns_pipeline.py:802](../../../src/twophase/simulation/ns_pipeline.py#L802)) | unchanged | face-based $\nabla \cdot u^*$ preferred for consistency; provided by `FCCDSolver.face_divergence` |
| DCCD PPE filter ([dccd_ppe_filter.py](../../../src/twophase/spatial/dccd_ppe_filter.py)) | unchanged | Rhie–Chow's primary stabilisation is redundant when Option B supplies face velocity; disable under `fccd_flux` |
| CSF ([ns_pipeline.py:762](../../../src/twophase/simulation/ns_pipeline.py#L762)) | unchanged | face form $\sigma \kappa \nabla \psi$ required for BF theorem; calls `fccd.face_gradient(psi, ax)` |
| Rhie–Chow ([rhie_chow.py:159](../../../src/twophase/spatial/rhie_chow.py#L159)) | unchanged | redundant once FCCD flux supplies face velocity; disable under `fccd_flux` |
| No-slip wall $u$ | Option III via Neumann fields | Option IV (T4 above) + face flux → 0 at wall |
| CFL ([cfl.py:106](../../../src/twophase/time_integration/cfl.py#L106)) | existing bound safe (FCCD spectral radius ≤ CCD) | document spectral radius for composed flux-div in WIKI-T-055 §CFL |
| $\|\nabla \cdot u\|_\infty$ diagnostic ([diagnostics.py:44](../../../src/twophase/simulation/diagnostics.py#L44)) | unchanged | offer parallel FCCD divergence diagnostic (CCD baseline retained) |

**Minimal-edit path (default-preserving)**. The library ships Option C and Option B as opt-in. Existing experiments continue through the CCD path by default. A single config flag `numerics.convection_scheme` (and companion `numerics.advection_scheme`) selects `fccd_nodal` or `fccd_flux`; the `SimulationBuilder.build` factory branches accordingly. See §12.

---

## 12. Implementation notes

### 12.1 Library layout

Additive only; no edits to existing `CCDSolver`. Three new modules:

- [`src/twophase/ccd/fccd.py`](../../../src/twophase/ccd/fccd.py) — `FCCDSolver` class
- [`src/twophase/ns_terms/fccd_convection.py`](../../../src/twophase/ns_terms/fccd_convection.py) — `FCCDConvectionTerm(mode='node'|'flux')`
- [`src/twophase/levelset/fccd_advection.py`](../../../src/twophase/levelset/fccd_advection.py) — `FCCDLevelSetAdvection(mode='node'|'flux')`

### 12.2 GPU / CPU unification

All array operations go through `backend.xp` (NumPy or CuPy). Fused kernels use the `@fuse` decorator from `backend.py` (CuPy `fuse` on GPU, identity on CPU):

```python
@_fuse
def _face_gradient_kernel(u_lo, u_hi, q_lo, q_hi, inv_H, H_over_24):
    return (u_hi - u_lo) * inv_H - H_over_24 * (q_hi - q_lo)
```

Three kernels (`_face_gradient_kernel`, `_face_value_kernel`, `_hermite_kernel`) cover all scalar primitives. Pre-computed constants (`H`, `H/24`, `H²/16`, `H/16`, per-axis) are uploaded once at `__init__` so the hot path does no host-device transfer.

### 12.3 q-sharing optimisation

`CCDSolver.differentiate` returns both $\mathbf{d}^{(1)}$ and $\mathbf{q}$ in one call. `FCCDSolver` accepts a pre-computed `q` argument:

```python
fccd.face_gradient(u, axis, q=q_u)  # re-uses CCD output
```

This reduces the CCD block-solve count from $2\,\text{ndim}^2$ to $\text{ndim}^2$ when both pressure-gradient and convection want $\mathbf{q}$ for the same component.

### 12.4 Shared LU with `CCDSolver`

`FCCDSolver.__init__` accepts `ccd_solver` (existing instance) to avoid a duplicate block factorisation. `SimulationBuilder.build` constructs a single `CCDSolver`, then a single `FCCDSolver(ccd_solver=ccd)` if any `fccd_*` scheme is active.

### 12.5 Config dispatch

```python
numerics.advection_scheme: str = "dissipative_ccd"  # + 'weno5' | 'fccd_nodal' | 'fccd_flux'
numerics.convection_scheme: str = "ccd"             # + 'fccd_nodal' | 'fccd_flux'
```

Defaults unchanged; existing experiments bit-exact.

---

## 13. Verification programme

Implemented in pytest:

| # | Property | Test |
|---|---|---|
| V1 | Face gradient $\mathcal{O}(H^4)$ periodic | `test_fccd.py::test_face_gradient_convergence_rate` |
| V2 | Periodic DFT symbol leading coef $-7/5760$ | `test_fccd.py::test_periodic_symbol_leading_coefficient` |
| V3 | Face value $\mathcal{O}(H^4)$ convergence | `test_fccd.py::test_face_value_convergence_rate` |
| V4 | R_4 node gradient $\mathcal{O}(H^4)$ interior | `test_fccd.py::test_node_gradient_hermite_order` |
| V5 | Wall Option III boundary zero | `test_fccd.py::test_wall_option_iii_boundary_zero` |
| V6 | Wall Option IV Dirichlet $u$ | `test_fccd.py::test_wall_option_iv_face_value_consistency` |
| V7 | CPU/GPU parity (rtol 1e-12) | `test_fccd_gpu_smoke.py` |
| V8 | Convection vs CCD baseline on TGV | `test_fccd_convection.py::test_tgv_agreement_vs_baseline` |
| V9 | AB2 buffer compatibility | `test_fccd_convection.py::test_ab2_buffer_shape` |
| V10 | $\psi$ advection mass drift (flux form) | `test_fccd_advection_levelset.py::test_flux_mode_mass_conservation_uniform_divfree` |

All V1–V6, V8–V10 pass on CPU; V7 passes when `--gpu` is available. V11 (BF residual on WIKI-E-030) is deferred to the Route-R-1 PoC CHK.

---

## 14. Scope limits

- $\mathcal{O}(H^4)$ global convergence of the full NS solver is limited by AB2 time integration ($\mathcal{O}(\Delta t^2)$). An RK3/RK4 integrator is required to demonstrate full 4th-order spatial convergence in practice (deferred).
- Route-2 native face-CCD (block system with face unknowns) remains deferred — SP-C §10 / WIKI-T-054 §10.
- Option B full pipeline integration (face-form PPE RHS + CSF + Rhie–Chow disabling) is **specified** in this paper but **not yet wired end-to-end**; the current library provides `FCCDSolver.face_divergence` and `advection_rhs` primitives. A follow-up "FCCD Route R-1 PoC" CHK completes the wiring.
- 3-D: the implementation is dimension-agnostic (axis loop); tests cover 1-D and 2-D. A 3-D smoke test is deferred.
- Non-uniform grid + periodic: an uncommon combination; tests cover uniform+periodic and non-uniform+wall separately.
- GFM coupling for FCCDLevelSetAdvection is deferred — tests run the non-GFM pipeline first.

---

## 15. Relation to SP-A/B/C and WIKI-X-018

- **SP-A** (FCCD derivation): provides $\mathbf{M}^{\text{FCCD}}$ as face operator.
- **SP-C** (matrix formulation): establishes composite matrix form + wall Option III + periodic DFT; this paper extends to $\mathbf{P}_f$ + $\mathbf{M}_4^{\text{node-FCCD}}$ + Option IV.
- **WIKI-X-018** (H-01 remediation atlas): SP-C closed the gradient-axis row; this paper closes the advection-axis row. Full BF theorem (§7.2) requires both.
- **SP-B** (Ridge–Eikonal hybrid): parallel track for $\psi$-reinitialisation; orthogonal to advection but consumes the same `FCCDSolver` face primitives.

---

## 16. References

1. SP-A: FCCD derivation — [`SP-A_face_centered_upwind_ccd.md`](SP-A_face_centered_upwind_ccd.md)
2. SP-C: FCCD matrix formulation — [`SP-C_fccd_matrix_formulation.md`](SP-C_fccd_matrix_formulation.md)
3. WIKI-T-053: FCCD executable equations — [`WIKI-T-053`](../../wiki/theory/WIKI-T-053.md)
4. WIKI-T-054: FCCD matrix + wall/periodic BC — [`WIKI-T-054`](../../wiki/theory/WIKI-T-054.md)
5. WIKI-T-055: FCCD advection operator — [`WIKI-T-055`](../../wiki/theory/WIKI-T-055.md)
6. WIKI-T-056: Wall Option IV Dirichlet — [`WIKI-T-056`](../../wiki/theory/WIKI-T-056.md)
7. WIKI-L-024: FCCD library module — [`WIKI-L-024`](../../wiki/code/WIKI-L-024.md)
8. WIKI-X-018: H-01 remediation atlas — [`WIKI-X-018`](../../wiki/cross-domain/WIKI-X-018.md)
9. WIKI-E-030: Capillary benchmark — [`WIKI-E-030`](../../wiki/experiment/WIKI-E-030.md)
10. Chu, P. C. & Fan, C. (1998). *A three-point combined compact difference scheme*. J. Comp. Phys. 140(2), 370–399.
11. Kok, J. C. (2000). *A high-order low-dispersion symmetry-preserving finite-volume method for compressible flow*. NLR-TP-2009-775.
12. Ham, F. E., Lien, F. S., & Strong, A. B. (2002). *A fully conservative second-order finite difference scheme for incompressible flow on non-uniform grids*. J. Comp. Phys. 177(1), 117–133.
