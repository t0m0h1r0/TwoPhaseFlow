---
ref_id: WIKI-T-054
title: "FCCD Matrix Formulation: Composite Operator, Wall BC Rows, Periodic Block-Circulant"
domain: theory
status: PROPOSED  # Theory derived; PoC pending (CHK-156)
superseded_by: null
sources:
  - path: docs/wiki/theory/WIKI-T-053.md
    description: Source of the face-local FCCD scalar formulas
  - path: docs/wiki/theory/WIKI-T-050.md
    description: Non-uniform cancellation coefficients μ(θ), λ(θ)
  - path: docs/wiki/theory/WIKI-T-051.md
    description: Wall BC options (Option III recommended)
  - path: docs/wiki/theory/WIKI-T-012.md
    description: CCD boundary / periodic baseline (block-circulant assembly)
  - path: src/twophase/ccd/ccd_solver.py
    description: Existing CCD block-tridiagonal (wall) and block-circulant (periodic) solvers
depends_on:
  - "[[WIKI-T-001]]: CCD baseline O(h^6) theory"
  - "[[WIKI-T-012]]: CCD boundary / periodic / elliptic assembly"
  - "[[WIKI-T-046]]: FCCD core operator"
  - "[[WIKI-T-050]]: Non-uniform cancellation coefficients μ, λ"
  - "[[WIKI-T-051]]: FCCD wall BC Options I/II/III"
  - "[[WIKI-T-053]]: FCCD calculation via CCD d2 closure"
consumers:
  - domain: code
    description: FCCDOperator PoC implementation (matrix assembly and application path)
  - domain: cross-domain
    description: WIKI-X-018 (R-1 PoC equation set — matrix form for H-01 remediation)
  - domain: paper
    description: SP-C short paper (FCCD matrix form and BC integration)
tags: [ccd, fccd, matrix_form, composite_operator, wall_bc, periodic_bc, block_circulant, modified_wavenumber, h01_remediation, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-21"
---

# FCCD Matrix Formulation: Composite Operator, Wall BC Rows, Periodic Block-Circulant

## 1. Why this entry exists

[WIKI-T-053](WIKI-T-053.md) establishes the **face-local scalar formulas** for FCCD and notes explicitly that "no new block system is required". A PoC implementer, however, still needs three missing pieces:

1. **Assembly view** — how the full face-gradient vector $\mathbf{d}^{\text{FCCD}}$ is obtained from the nodal vector $\mathbf{u}$ as a composition of sparse + dense operators. [WIKI-T-053](WIKI-T-053.md) stops at the per-face boxed equation and does not assemble the N-face matrix.
2. **Boundary matrix rows** — [WIKI-T-051](WIKI-T-051.md) Option III prescribes zero at wall faces but does not state the augmented matrix rows explicitly. Array-shape consistency in an implementation requires this.
3. **Periodic wrap closure** — [WIKI-T-051](WIKI-T-051.md) Line 151 dismisses periodic BC in one line ("FCCD inherits periodic BC directly"). This entry derives the block-circulant structure and gives the DFT-diagonalised modified-wavenumber symbol with explicit leading truncation coefficient.

All three pieces reuse the existing CCD block-tridiagonal and block-circulant solvers ([ccd_solver.py](../../../src/twophase/ccd/ccd_solver.py)); no new block system is introduced.

## 2. Geometry and notation

Following [WIKI-T-051](WIKI-T-051.md) §Geometry:

- Nodes $x_0, x_1, \ldots, x_N$, so $|V| = N+1$.
- Interior faces $f_{i-1/2}$ for $i = 1, \ldots, N$: $N$ in number.
- Wall faces $f_{-1/2}$ (left) and $f_{N+1/2}$ (right) lie outside the domain.
- Face width $H_i := x_i - x_{i-1}$; uniform case $H_i \equiv H$.
- Face position $\theta_i := h_R^{(i)} / H_i = (x_i - x_{f_{i-1/2}}) / H_i$; cell-centred faces ⇒ $\theta_i \equiv 1/2$.

Nodal vectors:
$$
\mathbf{u} = (u_0, u_1, \ldots, u_N)^T \in \mathbb{R}^{N+1},
\qquad
\mathbf{q} = (q_0, q_1, \ldots, q_N)^T \in \mathbb{R}^{N+1},
\qquad
q_i := (D_{\mathrm{CCD}}^{(2)} u)_i.
$$

Interior face vector:
$$
\mathbf{d}^{\text{FCCD}} = (d_{1/2}, d_{3/2}, \ldots, d_{N-1/2})^T \in \mathbb{R}^{N}.
$$

Augmented face vector (wall faces included):
$$
\mathbf{d}^{\text{FCCD,aug}} = (d_{-1/2}, d_{1/2}, \ldots, d_{N-1/2}, d_{N+1/2})^T \in \mathbb{R}^{N+2}.
$$

## 3. Underlying CCD operator

From [WIKI-T-053](WIKI-T-053.md) §1, the Chu–Fan combined relations give the block system
$$
\mathbf{A}_{\mathrm{CCD}}\,
\begin{pmatrix} \mathbf{u}' \\ \mathbf{q} \end{pmatrix}
\;=\;
\mathbf{B}_{\mathrm{CCD}}\, \mathbf{u},
$$
with $\mathbf{A}_{\mathrm{CCD}} \in \mathbb{R}^{2(N+1) \times 2(N+1)}$ **block-tridiagonal** for wall BC, **block-circulant** for periodic BC (see [ccd_solver.py:95-101](../../../src/twophase/ccd/ccd_solver.py#L95) and [ccd_solver.py:418-448](../../../src/twophase/ccd/ccd_solver.py#L418)). Extracting the $\mathbf{q}$ component defines
$$
\mathbf{q} \;=\; \mathbf{S}_{\mathrm{CCD}}\, \mathbf{u},
\qquad
\mathbf{S}_{\mathrm{CCD}} \;:=\; \Pi_q\, \mathbf{A}_{\mathrm{CCD}}^{-1}\, \mathbf{B}_{\mathrm{CCD}},
$$
where $\Pi_q$ projects $(\mathbf{u}', \mathbf{q})$ onto its second component.

$\mathbf{S}_{\mathrm{CCD}}$ is generically **dense** (inverse of a banded matrix) but never explicitly formed. The existing solver pre-factors $\mathbf{A}_{\mathrm{CCD}}$ and applies $\mathbf{S}_{\mathrm{CCD}}$ in $\mathcal{O}(N)$ per solve via block Thomas.

## 4. Uniform interior matrix form

Define two sparse **face-to-node difference matrices** $\mathbf{D}_1, \mathbf{D}_2 \in \mathbb{R}^{N \times (N+1)}$, row-indexed by interior faces and bidiagonal (2 non-zeros per row):

- $(\mathbf{D}_1)_{f_{i-1/2},\, i-1} = -1/H$, $\;(\mathbf{D}_1)_{f_{i-1/2},\, i} = +1/H$.
- $(\mathbf{D}_2)_{f_{i-1/2},\, i-1} = -H/24$, $\;(\mathbf{D}_2)_{f_{i-1/2},\, i} = +H/24$.

From the [WIKI-T-053](WIKI-T-053.md) uniform boxed equation,
$$
\mathbf{d}^{\text{FCCD}}
\;=\;
\mathbf{D}_1\,\mathbf{u} \;-\; \mathbf{D}_2\,\mathbf{q}
\;=\;
(\mathbf{D}_1 \;-\; \mathbf{D}_2\,\mathbf{S}_{\mathrm{CCD}})\,\mathbf{u}.
$$

Therefore
$$
\boxed{\;
\mathbf{M}^{\text{FCCD}}
\;=\;
\mathbf{D}_1 \;-\; \mathbf{D}_2\, \mathbf{S}_{\mathrm{CCD}}
\;\in\; \mathbb{R}^{N \times (N+1)}.
\;}
$$

**Sparsity.** $\mathbf{D}_1, \mathbf{D}_2$ are bidiagonal ($2(N+1)$ non-zeros). $\mathbf{S}_{\mathrm{CCD}}$ is dense but never assembled.

**Cost per axis per time step.**
- $\mathbf{q} \leftarrow \mathbf{S}_{\mathrm{CCD}} \mathbf{u}$: $\mathcal{O}(N)$ via pre-factored block Thomas.
- $\mathbf{D}_1 \mathbf{u}$, $\mathbf{D}_2 \mathbf{q}$: each $\mathcal{O}(N)$.
- Total: $\mathcal{O}(N)$.

## 5. Non-uniform interior matrix form

With $\mu_i = \theta_i - 1/2$ and $\lambda_i = (1 - 3\theta_i(1-\theta_i))/6$ from [WIKI-T-050](WIKI-T-050.md), define three sparse bidiagonal matrices $\mathbf{D}_1^{(H)}, \mathbf{D}_\mu^{(H\theta)}, \mathbf{D}_\lambda^{(H)} \in \mathbb{R}^{N \times (N+1)}$ (row $f_{i-1/2}$):

- $\mathbf{D}_1^{(H)}$: $\;-1/H_i\;$ at column $i{-}1$, $\;+1/H_i\;$ at column $i$.
- $\mathbf{D}_\mu^{(H\theta)}$ (interpolation of $\tilde u''_f$): $\;\mu_i H_i \theta_i\;$ at column $i{-}1$, $\;\mu_i H_i (1-\theta_i)\;$ at column $i$. Both positive.
- $\mathbf{D}_\lambda^{(H)}$ (finite difference for $\tilde u'''_f$): $\;-\lambda_i H_i\;$ at column $i{-}1$, $\;+\lambda_i H_i\;$ at column $i$.

From the [WIKI-T-053](WIKI-T-053.md) non-uniform boxed equation,
$$
\mathbf{d}^{\text{FCCD,nu}}
\;=\;
\mathbf{D}_1^{(H)}\,\mathbf{u}
\;-\;
(\mathbf{D}_\mu^{(H\theta)} + \mathbf{D}_\lambda^{(H)})\, \mathbf{q}.
$$

Therefore
$$
\boxed{\;
\mathbf{M}^{\text{FCCD,nu}}
\;=\;
\mathbf{D}_1^{(H)}
\;-\;
(\mathbf{D}_\mu^{(H\theta)} + \mathbf{D}_\lambda^{(H)})\, \mathbf{S}_{\mathrm{CCD}}.
\;}
$$

**Uniform limit.** $\theta_i \equiv 1/2 \;\Rightarrow\; \mu_i \equiv 0$, $\lambda_i \equiv 1/24$, $\mathbf{D}_\mu^{(H\theta)} \equiv \mathbf{0}$, $\mathbf{D}_\lambda^{(H)} = \mathbf{D}_2$, recovering §4 exactly.

**Precomputation.** All three matrices depend only on grid geometry ($\theta_i, H_i$) and can be precomputed per axis at mesh-build time.

## 6. Wall BC matrix rows (Option III, Neumann fields)

From [WIKI-T-051](WIKI-T-051.md) §Option III, for Neumann fields ($\psi, \phi, p$) the wall-face gradient is prescribed by physical condition:
$$
d_{-1/2} \;=\; 0, \qquad d_{N+1/2} \;=\; 0.
$$

Extending the face vector to the augmented space $\mathbf{d}^{\text{FCCD,aug}} \in \mathbb{R}^{N+2}$, the augmented operator $\mathbf{M}^{\text{FCCD,aug}} \in \mathbb{R}^{(N+2) \times (N+1)}$ has

- **Row 0** (wall face $f_{-1/2}$): all zeros.
- **Rows $1$ through $N$** (interior faces): inherited from $\mathbf{M}^{\text{FCCD}}$ (§4) or $\mathbf{M}^{\text{FCCD,nu}}$ (§5).
- **Row $N+1$** (wall face $f_{N+1/2}$): all zeros.

Symbolically:
$$
\boxed{\;
\mathbf{M}^{\text{FCCD,aug}}
\;=\;
\begin{pmatrix}
\mathbf{0}_{1 \times (N+1)} \\
\mathbf{M}^{\text{FCCD}} \\
\mathbf{0}_{1 \times (N+1)}
\end{pmatrix}
\;\in\; \mathbb{R}^{(N+2) \times (N+1)}.
\;}
$$

**BF=0 proof (repeated from [WIKI-T-051](WIKI-T-051.md) §Option I).** For any smooth $u$ with $u'(0) = 0$, the Neumann mirror extension $u_{-1} := u_0$ gives $q_{-1} = q_0$ by symmetry. Hence $(u_0 - u_{-1})/H = 0$ and $(q_0 - q_{-1})/H = 0$, so $D^{\text{FCCD}} u_{-1/2} = 0$ exactly — the prescription matches the physical boundary value to all orders in the FCCD truncation.

**CCD wall-row inheritance.** $\mathbf{S}_{\mathrm{CCD}}$ itself uses one-sided boundary stencils at rows 0 and $N$ (see [`_boundary_coeffs_left/right`](../../../src/twophase/ccd/ccd_solver.py#L611)). The boundary values $q_0, q_N$ have locally reduced order ($\mathcal{O}(H^4)$–$\mathcal{O}(H^5)$ vs. interior $\mathcal{O}(H^6)$; [WIKI-T-012](WIKI-T-012.md)). These $q$ values then enter interior FCCD rows $i=1$ and $i=N$ via $\mathbf{D}_2 \mathbf{q}$, inheriting the CCD boundary-order loss. **No FCCD-specific boundary closure is added** — the scheme inherits CCD's boundary treatment unchanged.

**Implementation note.** The zero rows need not be materialised in storage; callers iterating over face indices handle wall faces separately. This matches the existing $G^{\text{adj}}$ wall handling at [`ns_pipeline.py:393`](../../../src/twophase/simulation/ns_pipeline.py#L393), which returns 0 at wall indices directly.

**Scope.** Option III applies to fields with Neumann wall BC ($\psi$, $\phi$, $p$). No-slip velocity walls (Dirichlet $u = 0$) and 2D corner closure are deferred to [WIKI-T-051](WIKI-T-051.md) §Open issues; they will require Option I or II rather than Option III.

## 7. Periodic BC: block-circulant composite

### 7.1 Indexing

Collapse $u_N \equiv u_0$ and work with $N$ unique node values $\mathbf{u}^{\text{per}} = (u_0, u_1, \ldots, u_{N-1})^T \in \mathbb{R}^N$. Faces $f_{1/2}, \ldots, f_{N-1/2}$ are $N$ in number with wrap $f_{-1/2} \equiv f_{N-1/2}$.

The existing periodic CCD solver ([`_build_axis_solver_periodic`](../../../src/twophase/ccd/ccd_solver.py#L418)) assembles a $2N \times 2N$ **block-circulant** matrix; extracting the $q$-component defines
$$
\mathbf{q}^{\text{per}} \;=\; \mathbf{S}^{\text{per}}_{\mathrm{CCD}}\, \mathbf{u}^{\text{per}},
\qquad
\mathbf{S}^{\text{per}}_{\mathrm{CCD}} \in \mathbb{R}^{N \times N} \text{ circulant}.
$$

Circulant because: (a) every row of $\mathbf{A}^{\text{per}}_{\mathrm{CCD}}$ is a cyclic shift of the same template; (b) the inverse of a block-circulant matrix is block-circulant; (c) the $q$-projection preserves circulant structure.

### 7.2 Periodic face-difference matrices

Define $\mathbf{D}_1^{\text{per}}, \mathbf{D}_2^{\text{per}} \in \mathbb{R}^{N \times N}$ as **bidiagonal circulant** matrices:
$$
(\mathbf{D}_1^{\text{per}})_{i,\, (i-1) \bmod N} = -\tfrac{1}{H},
\quad
(\mathbf{D}_1^{\text{per}})_{i,\, i} = +\tfrac{1}{H};
$$
analogously $\mathbf{D}_2^{\text{per}}$ with entries $\mp H/24$. The wrap entry $(\mathbf{D}_1^{\text{per}})_{0, N-1} = -1/H$ realises the periodic face $f_{-1/2} \equiv f_{N-1/2}$. Both matrices are circulant.

### 7.3 Composite operator is circulant

$$
\boxed{\;
\mathbf{M}^{\text{FCCD,per}}
\;=\;
\mathbf{D}_1^{\text{per}}
\;-\;
\mathbf{D}_2^{\text{per}}\, \mathbf{S}^{\text{per}}_{\mathrm{CCD}}
\;\in\; \mathbb{R}^{N \times N}.
\;}
$$

Products and differences of circulant matrices are circulant; $\mathbf{M}^{\text{FCCD,per}}$ is therefore **circulant and diagonalised by the DFT**.

### 7.4 Modified wavenumber and leading truncation

Let $\omega_k = 2\pi k /(NH)$ for $k = 0, 1, \ldots, N-1$ and let $v_j = e^{i \omega_k x_j}$ be the Fourier basis node-value. The eigenvalue of a circulant operator on $v_j$ is its Fourier symbol.

**Symbol of $\mathbf{D}_1^{\text{per}}$ at face $x_{j-1/2}$:**
$$
\hat{D}_1(\omega_k)
\;=\;
\frac{e^{i\omega_k H/2} - e^{-i\omega_k H/2}}{H}
\;=\;
\frac{2i\sin(\omega_k H/2)}{H}.
$$

**Symbol of $\mathbf{S}^{\text{per}}_{\mathrm{CCD}}$:** From [WIKI-T-001](WIKI-T-001.md) / [WIKI-T-012](WIKI-T-012.md), periodic CCD is 6th-order accurate:
$$
\hat{S}_{\mathrm{CCD}}(\omega_k)
\;=\;
-\omega_k^2\,\bigl[1 + \varepsilon_{\mathrm{CCD}}(\omega_k H)\bigr],
\qquad
\varepsilon_{\mathrm{CCD}} = \mathcal{O}\bigl((\omega_k H)^6\bigr).
$$

**Symbol of $\mathbf{D}_2^{\text{per}}$ times $\mathbf{S}^{\text{per}}_{\mathrm{CCD}}$:**
$$
\hat{D}_2(\omega_k)\, \hat{S}_{\mathrm{CCD}}(\omega_k)
\;=\;
\frac{H}{24}\cdot 2i\sin(\omega_k H/2) \cdot (-\omega_k^2)\,[1 + \varepsilon_{\mathrm{CCD}}]
\;=\;
-\frac{iH\omega_k^2}{12}\sin(\omega_k H/2)\,[1 + \varepsilon_{\mathrm{CCD}}].
$$

**Composite FCCD symbol:**
$$
\hat{M}^{\text{FCCD}}(\omega_k)
\;=\;
\hat{D}_1(\omega_k) \;-\; \hat{D}_2(\omega_k)\, \hat{S}_{\mathrm{CCD}}(\omega_k)
\;=\;
2i\sin(\omega_k H/2)\,\Bigl[\tfrac{1}{H} + \tfrac{H\omega_k^2}{24}(1 + \varepsilon_{\mathrm{CCD}})\Bigr].
$$

**Taylor expansion** (using $\sin(\omega H/2) = \omega H/2 - (\omega H)^3/48 + (\omega H)^5/3840 - \mathcal{O}(H^7)$):
$$
\frac{2}{H}\sin(\omega H/2) \;=\; \omega \;-\; \tfrac{\omega^3 H^2}{24} \;+\; \tfrac{\omega^5 H^4}{1920} \;-\; \mathcal{O}(H^6),
$$
$$
\frac{H\omega^2}{12}\cdot 2\sin(\omega H/2) \cdot \tfrac{1}{2}
\;=\;
\tfrac{H\omega^2}{12}\sin(\omega H/2)
\;=\;
\tfrac{\omega^3 H^2}{24} \;-\; \tfrac{\omega^5 H^4}{576} \;+\; \mathcal{O}(H^6).
$$

Summing the two contributions (and noting the $\omega^3 H^2$ terms **cancel exactly** — this is the whole point of the FCCD $\lambda = 1/24$ coefficient choice):
$$
\hat{M}^{\text{FCCD}}(\omega_k)
\;=\;
i\omega_k \;+\; i\omega_k^5 H^4 \left(\frac{1}{1920} - \frac{1}{576}\right) \;+\; \mathcal{O}(H^6).
$$

Compute the bracket: $\;1/1920 - 1/576 = 3/5760 - 10/5760 = -7/5760$. Therefore
$$
\boxed{\;
\hat{M}^{\text{FCCD}}(\omega_k)
\;=\;
i\omega_k \cdot \Bigl[\,1 \;-\; \frac{7\,(\omega_k H)^4}{5760} \;+\; \mathcal{O}\bigl((\omega_k H)^6\bigr)\,\Bigr].
\;}
$$

**Interpretation.**
- Leading truncation: $\mathcal{O}(H^4)$ — consistent with [WIKI-T-046](WIKI-T-046.md) uniform-grid claim.
- Explicit coefficient: $-7/5760 \approx -1.22 \times 10^{-3}$. Compact form: $7/(5760) = 7/(2^7 \cdot 3^2 \cdot 5)$.
- At Nyquist $\omega_k H = \pi$: relative error $\approx 7\pi^4/5760 \approx 0.118$ (12% at the shortest resolvable mode). Usable accuracy therefore demands well-resolved fields, as expected for an $\mathcal{O}(H^4)$ scheme.
- Comparison baselines: $G^{\text{adj}}$ face average is $\mathcal{O}(H^2)$ [WIKI-T-044](WIKI-T-044.md), R-1.5 (zeroth-order FCCD with $\lambda \equiv 0$) is $\mathcal{O}(H^2)$ [WIKI-T-052](WIKI-T-052.md), and interior node-CCD is $\mathcal{O}(H^6)$ [WIKI-T-001](WIKI-T-001.md).

### 7.5 Consistency at the wrap face

Is the FCCD closure $\tilde u'''_f \leftarrow (q_i - q_{i-1})/H$ consistent at the wrap face $f_{-1/2} \equiv f_{N-1/2}$?

Since $\mathbf{q}^{\text{per}} = \mathbf{S}^{\text{per}}_{\mathrm{CCD}}\, \mathbf{u}^{\text{per}}$ with a circulant matrix applied to a periodic vector, $\mathbf{q}^{\text{per}}$ is itself periodic: $q_N \equiv q_0$. The finite difference $q_0 - q_{N-1}$ at the wrap face is therefore just a cyclic-indexed instance of the standard formula — no special treatment is needed. The circulant modular indexing realises $f_{-1/2} \equiv f_{N-1/2}$ automatically.

**Conclusion.** FCCD periodic BC is implemented by feeding $\mathbf{q}^{\text{per}}$ (from the existing periodic CCD solver) into the circulant $\mathbf{D}_1^{\text{per}} - \mathbf{D}_2^{\text{per}}$ stencils with cyclic index wrap. **No new code path is required beyond plumbing.** The one-line dismissal in [WIKI-T-051](WIKI-T-051.md) L151 is formally justified by §7.3–§7.5 of this entry.

## 8. Implementation checklist (for CHK-157 PoC-1)

**Uniform interior (Route 1 composite, Option III wall):**

1. Reuse `CCDSolver.differentiate(u, axis)` and retrieve the returned `d2` as $\mathbf{q}$.
2. Apply face-local stencils $\mathbf{D}_1 \mathbf{u} - \mathbf{D}_2 \mathbf{q}$ (two-line kernel, same shape as `_fvm_pressure_grad` with the $-H(q_i - q_{i-1})/24$ correction added).
3. Zero wall-face entries explicitly (Option III).
4. Use `backend.xp` for all array ops; precompute constant coefficients $1/H, H/24$ per axis.

**Periodic BC:**

5. Set `bc_type="periodic"` on the CCDSolver (block-circulant LU already pre-factored at init).
6. Use modular indexing in the face stencil: $(\mathbf{D}_1 \mathbf{u})_{f_{1/2}} = (u_0 - u_{N-1})/H$ at the wrap.

**Non-uniform interior:**

7. Precompute $\mu_i H_i \theta_i,\; \mu_i H_i (1-\theta_i),\; \lambda_i H_i$ per axis at grid-build time.
8. Apply $\mathbf{D}_1^{(H)} \mathbf{u} - (\mathbf{D}_\mu^{(H\theta)} + \mathbf{D}_\lambda^{(H)}) \mathbf{q}$ with the precomputed weights.

## 9. Verification programme (pure-theory)

1. **Modified-wavenumber match (uniform periodic).** Apply $\mathbf{M}^{\text{FCCD,per}}$ to $u(x) = \sin(\omega x)$ on a uniform periodic grid; check that the output differs from $\omega \cos(\omega x)$ by $-7\omega^5 H^4 /5760 + \mathcal{O}(H^6)$.
2. **Circulant diagonalisation.** For small $N$ (e.g. $N = 8$), assemble $\mathbf{M}^{\text{FCCD,per}}$ explicitly and verify that the DFT diagonalises it with the §7.4 symbol.
3. **Wall Option III zero-row.** For any $\mathbf{u}$ with Neumann mirror $u_{-1} = u_0$, verify $d_{-1/2} = 0$ by prescription and $d_{1/2} = -H(q_1 - q_0)/24 + (u_1 - u_0)/H$ with $q_1 - q_0 = \mathcal{O}(H^2)$ for smooth $u$.
4. **Uniform limit of non-uniform.** Set $\theta_i \equiv 1/2$ everywhere and verify $\mathbf{M}^{\text{FCCD,nu}}$ reduces numerically to $\mathbf{M}^{\text{FCCD}}$.
5. **Truncation coefficient $-7/5760$.** Fit the leading error in a convergence study; the measured prefactor must match $7/5760 \approx 1.22 \times 10^{-3}$ within numerical noise.

## 10. Scope limits and deferred items

- **Route 2 native face-CCD** (2M×2M block system with $u'_f, u''_f$ as face-located unknowns): deferred per [WIKI-T-050](WIKI-T-050.md) §Route 2; Route 1 composite (this entry) is sufficient for the H-01 PoC.
- **No-slip velocity wall BC** (Options I or II of [WIKI-T-051](WIKI-T-051.md)): deferred to future CHK tied to FCCD-velocity PoC. Dirichlet mirror $u_{-1} = -u_0$ differs structurally from Neumann Option III.
- **2D corner closure**: intersection of two walls — face stencil must couple both axes; deferred.
- **Mixed BC (wall × periodic on different axes)**: standard tensor-product — §6 applied to one axis and §7 to the other. Formalisation deferred but mechanically straightforward.

## 11. A3 traceability

| Layer | Decision |
|---|---|
| Equation | $\mathbf{M}^{\text{FCCD}} = \mathbf{D}_1 - \mathbf{D}_2\, \mathbf{S}_{\mathrm{CCD}}$; circulant under periodic BC; zero-row wall extension (Option III). |
| Discretisation | Applied as (1) CCD solve for $\mathbf{q}$ via pre-factored block Thomas or block-circulant LU; (2) face-local sparse stencils $\mathbf{D}_1, \mathbf{D}_2$; (3) explicit wall-face zero. |
| Code | Reuse existing `CCDSolver.differentiate`; new FCCD face-stencil kernel mirrors `_fvm_pressure_grad` shape with $(H/24)\,\Delta q$ correction; wall handling preserved via Option III. |
| BF property | Operator applied identically to $p$ and $\psi$ ⇒ BF residual $\mathcal{O}(H^4)$ uniform / $\mathcal{O}(H^3)$ non-uniform, a strict improvement over the current $G^{\text{adj}}$ $\mathcal{O}(H^2)$. |

## 12. References

- [WIKI-T-001](WIKI-T-001.md) — Baseline CCD $\mathcal{O}(h^6)$ theory.
- [WIKI-T-012](WIKI-T-012.md) — CCD boundary / periodic / elliptic assembly (block-circulant precedent).
- [WIKI-T-044](WIKI-T-044.md) — $G^{\text{adj}}$ FVM face-average gradient ($\mathcal{O}(h^2)$ baseline).
- [WIKI-T-046](WIKI-T-046.md) — FCCD core operator definition.
- [WIKI-T-050](WIKI-T-050.md) — Non-uniform cancellation coefficients $\mu, \lambda$.
- [WIKI-T-051](WIKI-T-051.md) — FCCD wall BC Options I/II/III.
- [WIKI-T-052](WIKI-T-052.md) — R-1.5 zeroth-order FCCD baseline.
- [WIKI-T-053](WIKI-T-053.md) — FCCD calculation equations (face-local scalar form).
- [`src/twophase/ccd/ccd_solver.py`](../../../src/twophase/ccd/ccd_solver.py) — Existing block-tridiagonal (wall) and block-circulant (periodic) solvers.
- [`src/twophase/simulation/ns_pipeline.py:381`](../../../src/twophase/simulation/ns_pipeline.py#L381) — `_fvm_pressure_grad` (current $G^{\text{adj}}$ wall reference).
- SP-C (new) — Short paper consolidating matrix form + BC integration (this entry is the wiki backing for SP-C).
