# SP-C: FCCD Matrix Formulation — Composite Operator, Wall BC Rows, and Periodic Block-Circulant

**Status**: Short paper draft (research memo)
**Date**: 2026-04-21
**Related**: [SP-A](SP-A_face_centered_upwind_ccd.md), [WIKI-T-046](../../wiki/theory/WIKI-T-046.md), [WIKI-T-050](../../wiki/theory/WIKI-T-050.md), [WIKI-T-051](../../wiki/theory/WIKI-T-051.md), [WIKI-T-053](../../wiki/theory/WIKI-T-053.md), [WIKI-T-054](../../wiki/theory/WIKI-T-054.md), [WIKI-X-018](../../wiki/cross-domain/WIKI-X-018.md)
**Companion papers**: [SP-A (FCCD derivation)](SP-A_face_centered_upwind_ccd.md), [SP-B (Ridge-Eikonal hybrid)](SP-B_ridge_eikonal_hybrid.md)

---

## Abstract

SP-A derived the Face-Centered Combined Compact Difference (FCCD) operator as a face-local scalar stencil whose third-derivative correction term $\tilde u'''_f$ is to be obtained from the Chu–Fan combined relations. WIKI-T-053 subsequently closed that gap by showing $\tilde u'''_f = (q_i - q_{i-1})/H$ with $q_i = (D^{(2)}_{\text{CCD}} u)_i$ supplied by the existing node-centred CCD solve. Three further gaps prevent direct PoC implementation: (i) the face-local scalar formula does not yet describe how the full N-face gradient vector is assembled from the nodal input vector; (ii) WIKI-T-051's Option III wall BC prescribes zero face-gradient values but does not state the augmented matrix rows explicitly; (iii) periodic BC is dismissed in one line without a derivation of the block-circulant structure or a modified-wavenumber analysis. This short paper closes all three gaps by expressing FCCD as a composition $\mathbf{M}^{\text{FCCD}} = \mathbf{D}_1 - \mathbf{D}_2 \mathbf{S}_{\text{CCD}}$ of two sparse bidiagonal matrices and the existing CCD second-derivative operator, stating Option III wall rows explicitly as an augmented zero-row extension, and deriving the periodic case as a circulant-matrix DFT symbol with leading truncation coefficient $-7(\omega H)^4/5760$. No new block system is introduced; the formulation reuses the CCD block-tridiagonal solver for wall BC and the block-circulant solver for periodic BC that are already implemented in `ccd_solver.py`. The resulting matrix form gives the PoC implementer a directly actionable specification: a two-step CCD-then-face-stencil application with explicit wall-face zero prescription.

---

## 1. Introduction

The Face-Centered Combined Compact Difference (FCCD) operator proposed in SP-A is the candidate remediation for hypothesis H-01 in [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md), where a metric inconsistency between the FVM face-average gradient $G^{\text{adj}}$ (currently $\mathcal{O}(H^2)$ [WIKI-T-044](../../wiki/theory/WIKI-T-044.md)) and the node-centred CCD ($\mathcal{O}(h^6)$ [WIKI-T-001](../../wiki/theory/WIKI-T-001.md)) drives a balanced-force residual that destabilises the late-time capillary solution. FCCD places both gradient channels on a common face locus and restores the balanced-force condition to the FCCD truncation order ($\mathcal{O}(H^4)$ uniform, $\mathcal{O}(H^3)$ non-uniform).

Between SP-A (Chu–Fan-faithful derivation) and an executable PoC lie three linked specifications:

- **Computable equations.** [WIKI-T-053](../../wiki/theory/WIKI-T-053.md) closed the "$\tilde u'''_f$ from Chu–Fan relations" gap by identifying $\tilde u'''_f$ as the finite difference of the existing CCD second derivative $q_i$. This resolved the algebraic closure but left the computation in face-local scalar form.
- **Matrix assembly.** The full gradient vector $\mathbf{d}^{\text{FCCD}}$ must be obtained from the nodal input vector $\mathbf{u}$ by explicit assembly. Without a matrix view, questions about sparsity, cost, spectral properties, and BC handling cannot be answered.
- **Boundary condition integration.** Wall and periodic BC must be expressed in the same matrix form so that the PoC implementation handles the full physical domain, not just the interior.

The present paper supplies all three specifications. §2–§3 establish notation and recap the underlying CCD operator. §4 and §5 state the interior matrix form for uniform and non-uniform grids. §6 gives the wall BC augmented matrix rows for Option III (Neumann fields). §7 derives the periodic BC block-circulant composite and its modified-wavenumber symbol. §8 discusses implementation and §9 the verification programme. §10 records scope limits and deferred items.

Throughout the paper, the matrix forms are composed from operators that already exist in the codebase: no new block system is required, consistent with the [WIKI-T-053](../../wiki/theory/WIKI-T-053.md) research finding.

---

## 2. Notation and setup

We follow the geometry convention of [WIKI-T-051](../../wiki/theory/WIKI-T-051.md) §Geometry.

- **Nodes**: $x_0, x_1, \ldots, x_N$, so $|V| = N+1$. Node index $i$ runs $0 \ldots N$.
- **Interior faces**: $f_{i-1/2}$ for $i = 1, \ldots, N$. There are $N$ interior faces.
- **Wall faces**: $f_{-1/2}$ (left) and $f_{N+1/2}$ (right) lie outside the domain.
- **Face width**: $H_i := x_i - x_{i-1}$. On uniform grids, $H_i \equiv H$.
- **Face position**: $\theta_i := (x_i - x_{f_{i-1/2}})/H_i$. Cell-centred faces have $\theta_i \equiv 1/2$.

Nodal vectors:
$$
\mathbf{u} = (u_0, u_1, \ldots, u_N)^T \in \mathbb{R}^{N+1},
\qquad
\mathbf{q} = (q_0, q_1, \ldots, q_N)^T \in \mathbb{R}^{N+1},
$$
where $q_i := (D^{(2)}_{\text{CCD}} u)_i$ is the nodal second derivative produced by the existing CCD solver.

Interior face-gradient vector:
$$
\mathbf{d}^{\text{FCCD}} = (d_{1/2}, d_{3/2}, \ldots, d_{N-1/2})^T \in \mathbb{R}^{N}.
$$

Augmented face vector (including wall faces for Option III bookkeeping):
$$
\mathbf{d}^{\text{FCCD,aug}} = (d_{-1/2}, d_{1/2}, \ldots, d_{N-1/2}, d_{N+1/2})^T \in \mathbb{R}^{N+2}.
$$

---

## 3. The underlying CCD operator $\mathbf{S}_{\text{CCD}}$

From [WIKI-T-053](../../wiki/theory/WIKI-T-053.md) §1, the Chu–Fan combined relations give the block system
$$
\mathbf{A}_{\text{CCD}}
\begin{pmatrix} \mathbf{u}' \\ \mathbf{q} \end{pmatrix}
= \mathbf{B}_{\text{CCD}} \mathbf{u}
$$
with $\mathbf{A}_{\text{CCD}} \in \mathbb{R}^{2(N+1) \times 2(N+1)}$ **block-tridiagonal** for wall BC (see [`ccd_solver.py:95-101`](../../../src/twophase/ccd/ccd_solver.py#L95)) and **block-circulant** for periodic BC (see [`ccd_solver.py:418-448`](../../../src/twophase/ccd/ccd_solver.py#L418)). The off-diagonal blocks encode the $(\alpha_1, a_1, b_1)$ and $(\beta_2, a_2, b_2)$ coefficients in the Chu–Fan Equations-I/II.

Projecting the solution onto its second component defines
$$
\mathbf{q} = \mathbf{S}_{\text{CCD}} \mathbf{u},
\qquad
\mathbf{S}_{\text{CCD}} := \Pi_q \mathbf{A}_{\text{CCD}}^{-1} \mathbf{B}_{\text{CCD}}.
$$

$\mathbf{S}_{\text{CCD}}$ is generically dense (inverse of a banded matrix) but never formed explicitly. It is applied in $\mathcal{O}(N)$ per axis through the pre-factored block Thomas (wall) or block-circulant LU (periodic) routines in the existing code.

---

## 4. Interior matrix form — uniform grid

Define two sparse **face-to-node difference matrices** $\mathbf{D}_1, \mathbf{D}_2 \in \mathbb{R}^{N \times (N+1)}$, row-indexed by interior faces and bidiagonal (2 non-zeros per row):

- $(\mathbf{D}_1)_{f_{i-1/2},\, i-1} = -1/H$, $\;(\mathbf{D}_1)_{f_{i-1/2},\, i} = +1/H$.
- $(\mathbf{D}_2)_{f_{i-1/2},\, i-1} = -H/24$, $\;(\mathbf{D}_2)_{f_{i-1/2},\, i} = +H/24$.

From the [WIKI-T-053](../../wiki/theory/WIKI-T-053.md) uniform boxed equation,
$$
d_{f_{i-1/2}} = \frac{u_i - u_{i-1}}{H} - \frac{H}{24}(q_i - q_{i-1}),
$$
which reads in matrix form
$$
\mathbf{d}^{\text{FCCD}} = \mathbf{D}_1 \mathbf{u} - \mathbf{D}_2 \mathbf{q}
= (\mathbf{D}_1 - \mathbf{D}_2 \mathbf{S}_{\text{CCD}}) \mathbf{u}.
$$

The composite FCCD operator is therefore
$$
\boxed{\;
\mathbf{M}^{\text{FCCD}}
= \mathbf{D}_1 - \mathbf{D}_2 \mathbf{S}_{\text{CCD}}
\in \mathbb{R}^{N \times (N+1)}.
\;}
$$

**Sparsity.** $\mathbf{D}_1, \mathbf{D}_2$ are bidiagonal (2(N+1) non-zeros). $\mathbf{S}_{\text{CCD}}$ is dense but applied without forming.

**Cost per axis.** $\mathcal{O}(N)$ via the two-step procedure: (i) $\mathbf{q} \leftarrow \mathbf{S}_{\text{CCD}} \mathbf{u}$ by pre-factored block Thomas, (ii) $\mathbf{d}^{\text{FCCD}} \leftarrow \mathbf{D}_1 \mathbf{u} - \mathbf{D}_2 \mathbf{q}$ by face-local stencils.

---

## 5. Interior matrix form — non-uniform grid

With [WIKI-T-050](../../wiki/theory/WIKI-T-050.md) cancellation coefficients $\mu_i = \theta_i - 1/2$ and $\lambda_i = (1 - 3\theta_i(1-\theta_i))/6$, define three sparse bidiagonal matrices $\mathbf{D}_1^{(H)}, \mathbf{D}_\mu^{(H\theta)}, \mathbf{D}_\lambda^{(H)} \in \mathbb{R}^{N \times (N+1)}$ (row $f_{i-1/2}$):

- $\mathbf{D}_1^{(H)}$: $-1/H_i$ at column $i-1$, $+1/H_i$ at column $i$.
- $\mathbf{D}_\mu^{(H\theta)}$ (interpolation of $\tilde u''_f$): $\mu_i H_i \theta_i$ at column $i-1$, $\mu_i H_i (1-\theta_i)$ at column $i$. Both positive.
- $\mathbf{D}_\lambda^{(H)}$ (finite difference for $\tilde u'''_f$): $-\lambda_i H_i$ at column $i-1$, $+\lambda_i H_i$ at column $i$.

The [WIKI-T-053](../../wiki/theory/WIKI-T-053.md) non-uniform boxed equation
$$
d_{f_{i-1/2}} = \frac{u_i - u_{i-1}}{H_i} - \mu_i H_i [\theta_i q_{i-1} + (1-\theta_i) q_i] - \lambda_i H_i (q_i - q_{i-1})
$$
reads
$$
\mathbf{d}^{\text{FCCD,nu}} = \mathbf{D}_1^{(H)} \mathbf{u} - (\mathbf{D}_\mu^{(H\theta)} + \mathbf{D}_\lambda^{(H)}) \mathbf{q}
$$
and therefore
$$
\boxed{\;
\mathbf{M}^{\text{FCCD,nu}}
= \mathbf{D}_1^{(H)} - (\mathbf{D}_\mu^{(H\theta)} + \mathbf{D}_\lambda^{(H)}) \mathbf{S}_{\text{CCD}}.
\;}
$$

**Uniform limit.** $\theta_i \equiv 1/2 \Rightarrow \mu_i \equiv 0$, $\lambda_i \equiv 1/24$, $\mathbf{D}_\mu^{(H\theta)} \equiv \mathbf{0}$, $\mathbf{D}_\lambda^{(H)} = \mathbf{D}_2$, recovering §4 exactly.

**Precomputation.** The three weight matrices depend only on grid geometry $(H_i, \theta_i)$ and can be precomputed once per axis at grid-build time.

---

## 6. Wall BC matrix rows — Option III (Neumann fields)

From [WIKI-T-051](../../wiki/theory/WIKI-T-051.md) §Option III, Neumann-BC fields ($\psi, \phi, p$) satisfy
$$
d_{-1/2} = 0, \qquad d_{N+1/2} = 0
$$
by the physical wall condition $\partial_n u = 0$.

Extending the face vector to $\mathbf{d}^{\text{FCCD,aug}} \in \mathbb{R}^{N+2}$, the augmented operator $\mathbf{M}^{\text{FCCD,aug}} \in \mathbb{R}^{(N+2) \times (N+1)}$ has

- **Row 0** (wall face $f_{-1/2}$): all zeros.
- **Rows $1, \ldots, N$** (interior faces): inherited from $\mathbf{M}^{\text{FCCD}}$ (§4) or $\mathbf{M}^{\text{FCCD,nu}}$ (§5).
- **Row $N+1$** (wall face $f_{N+1/2}$): all zeros.

Symbolically:
$$
\boxed{\;
\mathbf{M}^{\text{FCCD,aug}}
= \begin{pmatrix}
\mathbf{0}_{1 \times (N+1)} \\
\mathbf{M}^{\text{FCCD}} \\
\mathbf{0}_{1 \times (N+1)}
\end{pmatrix}
\in \mathbb{R}^{(N+2) \times (N+1)}.
\;}
$$

### 6.1 BF=0 proof

For any smooth $u$ with $u'(0) = 0$, the Neumann mirror extension $u_{-1} := u_0$ gives, by symmetry, $q_{-1} = q_0$. Therefore
$$
(u_0 - u_{-1})/H = 0, \qquad (q_0 - q_{-1})/H = 0,
$$
so $D^{\text{FCCD}} u_{-1/2} = 0$ **exactly**. The Option III prescription therefore matches the physical boundary value to all orders in the FCCD truncation. This repeats the [WIKI-T-051](../../wiki/theory/WIKI-T-051.md) §Option I proof for completeness.

### 6.2 CCD wall-row inheritance

$\mathbf{S}_{\text{CCD}}$ itself uses one-sided boundary stencils at rows 0 and $N$ (see [`_boundary_coeffs_left/right`](../../../src/twophase/ccd/ccd_solver.py#L611)). The resulting $q_0, q_N$ have locally reduced order ($\mathcal{O}(H^4)$–$\mathcal{O}(H^5)$ at boundary vs. interior $\mathcal{O}(H^6)$; [WIKI-T-012](../../wiki/theory/WIKI-T-012.md)). These boundary $q$ values then feed the first and last interior FCCD rows ($i=1$ and $i=N$) via $\mathbf{D}_2 \mathbf{q}$, inheriting the CCD boundary-order loss. **No FCCD-specific boundary closure is added** — the scheme inherits the existing CCD treatment unchanged.

### 6.3 Implementation note

The zero rows of $\mathbf{M}^{\text{FCCD,aug}}$ need not be materialised in storage; callers iterating over face indices handle wall faces separately. This matches the existing $G^{\text{adj}}$ wall handling at [`ns_pipeline.py:393`](../../../src/twophase/simulation/ns_pipeline.py#L393), which returns 0 at wall indices by direct assignment.

### 6.4 Scope

Option III covers Neumann fields only. Dirichlet velocity walls (no-slip $u = 0$) and 2D corner closures require Option I (ghost mirror with sign change $u_{-1} = -u_0$) or Option II (one-sided face stencil); both are deferred to future CHK tied to FCCD-velocity PoC.

---

## 7. Periodic BC — block-circulant composite

### 7.1 Index convention

For periodic BC, collapse $u_N \equiv u_0$ and work with $N$ unique node values $\mathbf{u}^{\text{per}} \in \mathbb{R}^N$. Faces $f_{1/2}, \ldots, f_{N-1/2}$ are $N$ in number with wrap $f_{-1/2} \equiv f_{N-1/2}$.

The existing periodic CCD solver ([`_build_axis_solver_periodic`](../../../src/twophase/ccd/ccd_solver.py#L418)) assembles a $2N \times 2N$ **block-circulant** matrix; extracting the $q$ component defines
$$
\mathbf{q}^{\text{per}} = \mathbf{S}^{\text{per}}_{\text{CCD}} \mathbf{u}^{\text{per}},
\qquad
\mathbf{S}^{\text{per}}_{\text{CCD}} \in \mathbb{R}^{N \times N} \text{ circulant}.
$$

The circulant property follows from: (a) every row of $\mathbf{A}^{\text{per}}_{\text{CCD}}$ is a cyclic shift of the same template; (b) the inverse of a block-circulant matrix is block-circulant; (c) the $q$-projection preserves circulant structure.

### 7.2 Periodic face-difference matrices

Define $\mathbf{D}_1^{\text{per}}, \mathbf{D}_2^{\text{per}} \in \mathbb{R}^{N \times N}$ as **bidiagonal circulant** matrices:
$$
(\mathbf{D}_1^{\text{per}})_{i, (i-1) \bmod N} = -1/H, \qquad (\mathbf{D}_1^{\text{per}})_{i, i} = +1/H,
$$
and analogously $\mathbf{D}_2^{\text{per}}$ with entries $\mp H/24$. The wrap entry $(\mathbf{D}_1^{\text{per}})_{0, N-1} = -1/H$ realises the periodic face $f_{-1/2} \equiv f_{N-1/2}$.

### 7.3 Composite operator is circulant

$$
\boxed{\;
\mathbf{M}^{\text{FCCD,per}}
= \mathbf{D}_1^{\text{per}} - \mathbf{D}_2^{\text{per}} \mathbf{S}^{\text{per}}_{\text{CCD}}
\in \mathbb{R}^{N \times N}.
\;}
$$

Products and differences of circulant matrices are circulant; $\mathbf{M}^{\text{FCCD,per}}$ is therefore circulant and **diagonalised by the DFT**.

### 7.4 Modified-wavenumber derivation

Let $\omega_k = 2\pi k /(NH)$ for $k = 0, 1, \ldots, N-1$ and $v_j = e^{i\omega_k x_j}$. The eigenvalue of a circulant operator on $v_j$ is its Fourier symbol.

**Symbol of $\mathbf{D}_1^{\text{per}}$** at face $x_{j-1/2}$:
$$
\hat D_1(\omega_k) = \frac{e^{i\omega_k H/2} - e^{-i\omega_k H/2}}{H} = \frac{2i\sin(\omega_k H/2)}{H}.
$$

**Symbol of $\mathbf{S}^{\text{per}}_{\text{CCD}}$:** From [WIKI-T-001](../../wiki/theory/WIKI-T-001.md) / [WIKI-T-012](../../wiki/theory/WIKI-T-012.md), periodic CCD is 6th-order accurate:
$$
\hat S_{\text{CCD}}(\omega_k) = -\omega_k^2 [1 + \varepsilon_{\text{CCD}}(\omega_k H)],
\qquad
\varepsilon_{\text{CCD}} = \mathcal{O}((\omega_k H)^6).
$$

**Symbol of $\mathbf{D}_2^{\text{per}} \mathbf{S}^{\text{per}}_{\text{CCD}}$:**
$$
\hat D_2(\omega_k) \hat S_{\text{CCD}}(\omega_k)
= \frac{H}{24} \cdot 2i \sin(\omega_k H/2) \cdot (-\omega_k^2)[1 + \varepsilon_{\text{CCD}}]
= -\frac{iH\omega_k^2}{12}\sin(\omega_k H/2)[1 + \varepsilon_{\text{CCD}}].
$$

**Composite FCCD symbol:**
$$
\hat M^{\text{FCCD}}(\omega_k)
= \hat D_1(\omega_k) - \hat D_2(\omega_k) \hat S_{\text{CCD}}(\omega_k)
= 2i\sin(\omega_k H/2)
\left[\frac{1}{H} + \frac{H\omega_k^2}{24}(1 + \varepsilon_{\text{CCD}})\right].
$$

**Taylor expansion** (using $\sin(\omega H/2) = \omega H/2 - (\omega H)^3/48 + (\omega H)^5/3840 - \mathcal{O}(H^7)$):
$$
(2/H)\sin(\omega H/2) = \omega - \omega^3 H^2/24 + \omega^5 H^4/1920 - \mathcal{O}(H^6),
$$
$$
(H\omega^2/12)\sin(\omega H/2) = \omega^3 H^2/24 - \omega^5 H^4/576 + \mathcal{O}(H^6).
$$

Sum the two contributions. The $\omega^3 H^2$ terms cancel exactly — the defining property of the $\lambda = 1/24$ coefficient. The leading error is therefore at $\omega^5 H^4$:
$$
\hat M^{\text{FCCD}}(\omega_k)
= i\omega_k + i\omega_k^5 H^4 \left(\frac{1}{1920} - \frac{1}{576}\right) + \mathcal{O}(H^6).
$$

Computing $1/1920 - 1/576 = 3/5760 - 10/5760 = -7/5760$:
$$
\boxed{\;
\hat M^{\text{FCCD}}(\omega_k)
= i\omega_k \left[1 - \frac{7(\omega_k H)^4}{5760} + \mathcal{O}((\omega_k H)^6)\right].
\;}
$$

### 7.5 Interpretation

- **Leading order**: $\mathcal{O}(H^4)$ — consistent with the [WIKI-T-046](../../wiki/theory/WIKI-T-046.md) uniform-grid claim and with the $\lambda = 1/24$ cancellation engineered in SP-A §4.
- **Explicit truncation coefficient**: $-7/5760 \approx -1.22 \times 10^{-3}$. This coefficient is directly observable in a convergence study and provides a sharp test of the implementation.
- **Nyquist behaviour**: at $\omega_k H = \pi$, relative error is $7\pi^4/5760 \approx 0.118$ (~12%). FCCD is therefore a well-behaved $\mathcal{O}(H^4)$ operator for well-resolved modes; at-or-near-Nyquist content is not recovered — the same property as any compact 4th-order scheme.
- **Comparison baselines**: $G^{\text{adj}}$ is $\mathcal{O}(H^2)$ [WIKI-T-044](../../wiki/theory/WIKI-T-044.md); R-1.5 (zeroth-order FCCD with $\lambda \equiv 0$) is $\mathcal{O}(H^2)$ [WIKI-T-052](../../wiki/theory/WIKI-T-052.md); interior node-CCD is $\mathcal{O}(H^6)$ [WIKI-T-001](../../wiki/theory/WIKI-T-001.md). FCCD sits between these at $\mathcal{O}(H^4)$, paying two orders for face-locus alignment.

### 7.6 Consistency at the wrap face

Since $\mathbf{q}^{\text{per}} = \mathbf{S}^{\text{per}}_{\text{CCD}} \mathbf{u}^{\text{per}}$ with a circulant matrix applied to a periodic vector, $\mathbf{q}^{\text{per}}$ is itself periodic: $q_N \equiv q_0$. The finite difference $q_0 - q_{N-1}$ at the wrap face is therefore a cyclic-indexed instance of the standard formula — no special treatment. The one-line dismissal of periodic BC in [WIKI-T-051](../../wiki/theory/WIKI-T-051.md) L151 is formally justified.

---

## 8. Implementation notes

For a CHK-157 PoC-1 implementation:

**Uniform interior (Route 1 composite, Option III wall):**
1. Reuse `CCDSolver.differentiate(u, axis)`; retrieve `d2` as $\mathbf{q}$.
2. Apply face-local stencils $\mathbf{D}_1 \mathbf{u} - \mathbf{D}_2 \mathbf{q}$ — a two-line kernel mirroring `_fvm_pressure_grad` shape with the $-H(q_i - q_{i-1})/24$ correction added.
3. Zero wall-face entries explicitly.
4. All array ops via `backend.xp`; constants $1/H$, $H/24$ precomputed.

**Periodic BC:**
5. Set `bc_type="periodic"` on `CCDSolver` (block-circulant LU pre-factored at init).
6. Face stencil uses modular indexing for the wrap face.

**Non-uniform interior:**
7. Precompute $\mu_i H_i \theta_i,\; \mu_i H_i (1-\theta_i),\; \lambda_i H_i$ per axis at grid-build time.
8. Apply $\mathbf{D}_1^{(H)} \mathbf{u} - (\mathbf{D}_\mu^{(H\theta)} + \mathbf{D}_\lambda^{(H)}) \mathbf{q}$ with precomputed weights.

---

## 9. Verification programme

1. **Modified-wavenumber match** (uniform periodic). Apply $\mathbf{M}^{\text{FCCD,per}}$ to $u(x) = \sin(\omega x)$; check output differs from $\omega\cos(\omega x)$ by $-7\omega^5 H^4 /5760 + \mathcal{O}(H^6)$.
2. **Circulant diagonalisation**. For small $N$ (e.g. $N=8$), assemble $\mathbf{M}^{\text{FCCD,per}}$ explicitly and verify DFT diagonalisation with the §7.4 symbol.
3. **Wall Option III zero row**. For $u$ with $u_{-1} = u_0$ (Neumann mirror), verify $d_{-1/2} = 0$ by prescription and $d_{1/2} = (u_1 - u_0)/H - H(q_1 - q_0)/24$.
4. **Uniform limit of non-uniform**. Set $\theta_i \equiv 1/2$ and verify $\mathbf{M}^{\text{FCCD,nu}}$ reduces numerically to $\mathbf{M}^{\text{FCCD}}$.
5. **Truncation coefficient test**. Fit the leading error in a convergence study; the measured prefactor must match $7/5760 \approx 1.22 \times 10^{-3}$ within numerical noise.
6. **BF residual on capillary benchmark**. With FCCD unified for $\nabla p$ and $\sigma \kappa \nabla \psi$, measure BF residual on the WIKI-E-030 benchmark and confirm $\mathcal{O}(H^4)$ decay on uniform grids.

---

## 10. Scope limits and deferred items

- **Route 2 native face-CCD**: a $2M \times 2M$ block system with $u'_f, u''_f$ as face-located unknowns, flagged as "production recommended" in [WIKI-T-050](../../wiki/theory/WIKI-T-050.md). The Route 1 composite (this paper) is sufficient for the H-01 PoC and avoids a new block system per [WIKI-T-053](../../wiki/theory/WIKI-T-053.md). Route 2 derivation is deferred to a future short paper.
- **No-slip velocity walls** (Options I or II of [WIKI-T-051](../../wiki/theory/WIKI-T-051.md)): deferred to future CHK tied to FCCD-velocity PoC. Dirichlet mirror $u_{-1} = -u_0$ differs structurally from Neumann Option III.
- **2D corner closure**: where two walls intersect, the face stencil must couple both axes.
- **Mixed BC** (wall × periodic on different axes): standard tensor-product — §6 on one axis, §7 on another.

---

## 11. Relation to companion work

- **SP-A** derives the FCCD operator from Chu–Fan first principles and establishes its role in H-01 remediation. This paper starts where SP-A ends: from the Chu–Fan-faithful scalar stencil, SP-C builds the matrix form and BC integration.
- **[WIKI-T-053](../../wiki/theory/WIKI-T-053.md)** closed the "$\tilde u'''_f$ from Chu–Fan relations" gap by identifying $\tilde u'''_f = (q_i - q_{i-1})/H$. SP-C takes $q_i$ as given and assembles the full operator matrix.
- **[WIKI-T-051](../../wiki/theory/WIKI-T-051.md)** catalogued three wall BC variants and recommended Option III for Neumann fields. SP-C states the explicit matrix rows for Option III.
- **[WIKI-T-054](../../wiki/theory/WIKI-T-054.md)** is the wiki entry that backs this paper; SP-C is the short-paper presentation of the same material.
- **[WIKI-X-018](../../wiki/cross-domain/WIKI-X-018.md)** tracks the H-01 remediation map; the R-1 PoC row cites SP-C for the matrix-form specification.

---

## 12. References

- Chu, P. C., & Fan, C. (1998). A three-point combined compact difference scheme. *J. Comp. Phys.*, 140(2), 370–399.
- [SP-A](SP-A_face_centered_upwind_ccd.md) — FCCD derivation (Chu–Fan faithful).
- [SP-B](SP-B_ridge_eikonal_hybrid.md) — Ridge–Eikonal hybrid (companion, topology-axis).
- [WIKI-T-001](../../wiki/theory/WIKI-T-001.md) — Baseline CCD $\mathcal{O}(h^6)$.
- [WIKI-T-012](../../wiki/theory/WIKI-T-012.md) — CCD boundary / periodic / elliptic.
- [WIKI-T-044](../../wiki/theory/WIKI-T-044.md) — $G^{\text{adj}}$ face-average gradient.
- [WIKI-T-046](../../wiki/theory/WIKI-T-046.md) — FCCD core operator.
- [WIKI-T-050](../../wiki/theory/WIKI-T-050.md) — FCCD non-uniform coefficients.
- [WIKI-T-051](../../wiki/theory/WIKI-T-051.md) — FCCD wall BC options.
- [WIKI-T-052](../../wiki/theory/WIKI-T-052.md) — R-1.5 zeroth-order baseline.
- [WIKI-T-053](../../wiki/theory/WIKI-T-053.md) — FCCD calculation via CCD d2 closure.
- [WIKI-T-054](../../wiki/theory/WIKI-T-054.md) — Matrix formulation wiki backing (this paper).
- [`src/twophase/ccd/ccd_solver.py`](../../../src/twophase/ccd/ccd_solver.py) — Existing block-tridiagonal and block-circulant CCD solvers.
- [`src/twophase/simulation/ns_pipeline.py:381`](../../../src/twophase/simulation/ns_pipeline.py#L381) — Current $G^{\text{adj}}$ wall reference.
