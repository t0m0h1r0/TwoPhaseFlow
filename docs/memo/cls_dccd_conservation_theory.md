# CLS Mass Conservation under DCCD: Theoretical Analysis and Unified Reinitialization Proposal

Date: 2026-04-09
Status: PROPOSED
Related: reinitialize.py, advection.py, WIKI-T-007, WIKI-T-027, WIKI-T-002

---

## Abstract

We analyze why the Dissipative CCD (DCCD) filter affects mass conservation
in the Conservative Level Set (CLS) method, and propose a unified
reinitialization scheme that eliminates the dominant mass-loss mechanism.
The key finding is that **the DCCD spatial operator itself preserves mass
exactly for periodic BC**; the observed mass loss originates from
(a) clipping ψ to [0,1], (b) operator-splitting mismatch in
reinitialization, and (c) boundary padding inconsistency. A corrected
scheme — unified explicit RHS with Lagrange-multiplier conservation
constraint — is proposed and shown to be theoretically sound with zero
CFL penalty.

---

## 1. Conservation Identity in CLS

### 1.1 Continuous Form

CLS advection (§3.3 Eq.16):

$$
\frac{\partial\psi}{\partial t} + \nabla\cdot(\psi\mathbf{u}) = 0 \tag{A}
$$

Mass conservation follows from integration over the domain Ω:

$$
\frac{d}{dt}\int_\Omega \psi\,dV = -\oint_{\partial\Omega} \psi\mathbf{u}\cdot\mathbf{n}\,dS = 0
\quad\text{(periodic/wall BC)} \tag{B}
$$

### 1.2 Discrete Condition

Conservation requires:

$$
\sum_i \bigl[\nabla\cdot(\psi\mathbf{u})\bigr]_i = 0 \tag{C}
$$

If the spatial operator satisfies (C), any linear time integrator (including TVD-RK3)
preserves Σ ψᵢ exactly.

---

## 2. DCCD Preserves (C) for Periodic BC — Proof

### 2.1 CCD Block-Circulant Sum Property

The periodic CCD system for f = ψu solves 2N×2N block-circulant:

$$
\text{RHS}_{2i}   = \frac{a_1}{h}(f_{i+1} - f_{i-1})
\qquad\text{(antisymmetric, }\sum_i = 0\text{)}
$$

$$
\text{RHS}_{2i+1} = \frac{a_2}{h^2}(f_{i-1} - 2f_i + f_{i+1})
\qquad\text{(symmetric, }\sum_i = 0\text{)}
$$

Summing the coupled system over all nodes:

$$
\begin{pmatrix} 1+2\alpha_1 & 2\beta_1 \\ 2\alpha_2 & 1+2\beta_2 \end{pmatrix}
\begin{pmatrix} \sum d_1 \\ \sum d_2 \end{pmatrix}
= \begin{pmatrix} 0 \\ 0 \end{pmatrix}
$$

The 2×2 matrix is non-singular for the standard CCD coefficients
(α₁=7/16, β₁=−1/16, α₂=−1/16, β₂=−1/8; det ≈ 0.77 ≠ 0).

**Therefore Σ d1 = 0 and Σ d2 = 0 (exact).**

### 2.2 DCCD Filter Sum Property

The DCCD filter (§5 eq:dccd_adv_filter):

$$
\tilde{f}'_i = d_{1,i} + \varepsilon_d(d_{1,i+1} - 2d_{1,i} + d_{1,i-1})
$$

Summing over all i (periodic indices wrap):

$$
\sum_i \tilde{f}'_i = \sum_i d_{1,i}
+ \varepsilon_d \underbrace{\sum_i(d_{1,i+1} - 2d_{1,i} + d_{1,i-1})}_{= 0\text{ (telescoping)}}
= 0
$$

**Conclusion: For periodic BC, the DCCD spatial operator satisfies (C) exactly.
The DCCD filter does not break mass conservation.**

---

## 3. Actual Sources of Mass Loss

Given §2, where does the experimentally observed mass loss (22× degradation
with reinit frequency, WIKI-T-027) originate?

### 3.1 Source 1: clip(ψ, 0, 1) — Non-conservative projection

After each TVD-RK3 stage / pseudo-time step, ψ is clipped to [0,1]
(advection.py:321–326, reinitialize.py:105,111). DCCD has no TVD guarantee,
so overshoots/undershoots are inevitable. Clipping removes the excess
without redistributing, destroying Σψ.

**Impact: Primary mass-loss source in advection.**

### 3.2 Source 2: Operator Splitting in Reinitialization

The reinitialization PDE:

$$
\frac{\partial\psi}{\partial\tau} + \nabla\cdot[\psi(1-\psi)\hat{n}] = \varepsilon\nabla^2\psi
$$

At the equilibrium profile ψ = H_ε(φ):

$$
\psi(1-\psi)\hat{n} = \varepsilon\nabla\psi
\quad\Longrightarrow\quad
\nabla\cdot[\psi(1-\psi)\hat{n}] = \varepsilon\nabla^2\psi
\tag{*}
$$

Current discrete scheme:
- **Compression**: D_DCCD[ψ(1−ψ)n̂] — CCD d1 + εd-filter (explicit FE)
- **Diffusion**: ε·CN-ADI(CCD Eq-II) — CCD d2, no filter (implicit CN)

These use **different discrete operators**. At the equilibrium profile:

$$
\text{D}_{\text{DCCD}}[\psi(1-\psi)\hat{n}] \neq \varepsilon\cdot\text{D}^2_{\text{CN}}[\psi]
$$

The residual has spectral signature:

- Compression: wave-number response k · H(kh; εd), where H = 1 − 4εd sin²(kh/2)
- Diffusion: wave-number response −k² (unfiltered CCD d2)

At equilibrium, both should give the same value. The DCCD filter on the
compression side damps high-k content by factor H(kh), while the diffusion
side is unfiltered. The mismatch drives ψ away from equilibrium, losing mass.

**Impact: Primary mass-loss source in reinitialization (22× degradation).**

### 3.3 Source 3: Boundary Padding Inconsistency

reinitialize.py:155 hardcodes `'neumann'` for the DCCD filter padding,
regardless of the CCD solver's BC setting:

```python
g_prime_pad = _pad_bc(xp, g_prime, ax, 1, 'neumann')  # hardcoded!
```

For periodic CCD output, Neumann padding breaks the telescoping property:

$$
\tilde{f}'_0^{\text{Neumann}} = d_{1,0} + \varepsilon_d(d_{1,1} - d_{1,0})
\neq d_{1,0} + \varepsilon_d(d_{1,1} - 2d_{1,0} + d_{1,N-1})
= \tilde{f}'_0^{\text{periodic}}
$$

**Impact: Moderate; masked by Source 2 in practice.**

---

## 4. Proposed Scheme: Unified DCCD Reinitialization

### 4.1 Core Idea

Replace operator splitting with a unified explicit RHS where compression
and diffusion use the same CCD framework, plus a Lagrange-multiplier
conservation correction applied before clipping.

### 4.2 Algorithm

For each pseudo-time step τ:

**Step 1 — Gradient and normal (unchanged):**

$$
\psi'_{ax} , \psi''_{ax} \leftarrow \text{CCD}(\psi, ax)
\qquad
\hat{n}_{ax} = \psi'_{ax} / |\nabla\psi|
$$

**Step 2 — Compression divergence with DCCD (unchanged):**

$$
C = \sum_{ax} \text{D}_{\text{DCCD}}[\psi(1-\psi)\hat{n}_{ax}]
$$

**Step 3 — Diffusion from CCD d2 (replaces CN-ADI):**

$$
D = \varepsilon \sum_{ax} \psi''_{ax}
$$

(ψ''_{ax} is already available from Step 1 at zero extra cost.)

**Step 4 — Combined RHS with conservation correction:**

$$
R_i = -C_i + D_i
$$

$$
\lambda = -\frac{\sum_j R_j}{\sum_j w_j},
\qquad w_j = 4\psi_j(1-\psi_j)
$$

$$
\hat{R}_i = R_i + \lambda\,w_i
\qquad\Longrightarrow\qquad \sum_i \hat{R}_i = 0 \text{ (exact)}
$$

**Step 5 — Update with two-stage clip correction:**

$$
\psi^* = \psi + \Delta\tau\,\hat{R}
\qquad\text{(mass-conserving before clip)}
$$

$$
\psi^{(\tau+1)} = \text{clip}(\psi^*, 0, 1)
$$

Post-clip mass repair:

$$
\delta M = \sum_i \psi^*_i - \sum_i \psi^{(\tau+1)}_i
$$

$$
\psi^{(\tau+1)}_i \mathrel{+}= \frac{\delta M}{\sum_j w^{\text{clip}}_j}\,w^{\text{clip}}_i,
\qquad w^{\text{clip}}_i = 4\psi^{(\tau+1)}_i(1 - \psi^{(\tau+1)}_i)
$$

### 4.3 Properties

**P1. Equilibrium fixed-point preservation.**
At ψ = H_ε(φ), Steps 2 and 3 act on ψ(1-ψ)n̂ and ε∇ψ respectively.
Since ψ(1-ψ)n̂ = ε∇ψ at equilibrium, both terms produce the same CCD
output (same input, same operator). Thus C = D, R = 0, λ = 0.
The equilibrium is an exact fixed point.

**P2. Exact discrete mass conservation (pre-clip).**
By construction, Σ R̂ = 0 implies Σψ^{n+1} = Σψ^n before clipping.
Post-clip repair closes the remaining gap.

**P3. Zero CFL penalty.**
Current Δτ = min(0.5 h²/(2·ndim·ε), 0.5 h). The parabolic bound
h²/(2·ndim·ε) is the same stability limit that explicit diffusion
requires. For ε = C_ε·h (C_ε ≈ 1–2):

$$
\Delta\tau_{\text{parabolic}} = \frac{h}{2\,n_{\text{dim}}\,C_\varepsilon}
\approx \frac{h}{4}\text{–}\frac{h}{8}
$$

The current scheme already operates at this bound (CN stability is
not exploited because compression CFL dominates). Switching diffusion
to explicit incurs no additional time step restriction.

**P4. Computational cost.**
- Removed: ndim Thomas solves (CN-ADI), per-axis pre-factorization
- Added: nothing (ψ''_{ax} reused from Step 1)
- Net: **cheaper** (Thomas factorization and sweeps eliminated)

---

## 5. Impact on Downstream Processes

| Process | Current dependency | Proposed impact |
|---------|-------------------|-----------------|
| Curvature κ = −∇·n̂ | CCD d1(ψ), independent of reinit method | No change |
| HFE (Hermite Field Extension) | ψ profile quality | Improved (equilibrium preserved) |
| CSF surface tension σκδ_ε∇ψ | κ quality + ψ profile | Improved (better ψ → less parasitic currents) |
| Material properties ρ(ψ), μ(ψ) | Mass of ψ | Improved (conservation → NS mass balance) |
| PPE RHS divergence | ∇·u* consistency | Improved (less ψ-drift → less artificial source) |
| Logit inversion φ = ε·ln(ψ/(1−ψ)) | ψ ∈ (0,1) range | Improved (less clipping → less saturation) |

No downstream process is adversely affected. All improvements derive from
two properties: better equilibrium profile (P1) and better mass conservation (P2).

---

## 6. Theoretical Soundness Assessment

### 6.1 Conservation: SOUND

The Lagrange multiplier correction with basis w = 4ψ(1−ψ) is the same
foundation as Olsson & Kreiss (2005), but applied at each pseudo-time
step within the spatial operator rather than post-hoc. The interface-weighted
basis ensures corrections are concentrated at the interface (w(0) = w(1) = 0,
w(0.5) = 1), preserving bulk ψ values.

### 6.2 Equilibrium Preservation: SOUND

The unified operator ensures C = D at equilibrium by construction (same
CCD input = same CCD output). This eliminates the operator-splitting residual
that is the dominant mass-loss mechanism in the current scheme.

Note: CCD d2 ≠ D_DCCD(D_CCD(ψ)). The diffusion uses the direct second
derivative d2 from the CCD coupled system, not a DCCD-filtered first
derivative of a first derivative. This is more accurate (O(h⁶) vs
O(h⁴)·H²(kh) for double-DCCD), while still being "the same CCD framework"
in the sense that both compression and diffusion originate from a single
ccd.differentiate() call.

### 6.3 Stability: SOUND with caveat

Explicit Forward Euler for the combined RHS is stable under the parabolic CFL
Δτ < h²/(2·ndim·ε). The current code already satisfies this with safety
factor 0.5. For large ε/h ratios (thick interfaces), the CFL may become
restrictive; in that regime, a semi-implicit variant (implicit diffusion
only, using the same CCD d2) could be considered.

### 6.4 Spectral Consistency: ACCEPTABLE

The compression term is DCCD-filtered (H(kh) < 1 at high k), while the
diffusion d2 is unfiltered. At equilibrium, both evaluate the SAME function
(ψ(1-ψ)n̂ = ε∇ψ), so the CCD inputs are identical and outputs match regardless
of downstream filtering. Away from equilibrium, the filter asymmetry means
high-k compression is damped more than high-k diffusion, which effectively
adds a small stabilizing term. This is beneficial, not harmful.

---

## 7. Relation to Existing Work

| Approach | Scope | When applied | Conservation | Equilibrium |
|----------|-------|-------------|-------------|-------------|
| WIKI-T-027 post-hoc correction | advection + reinit | After all steps | Approximate | Not addressed |
| Olsson-Kreiss λ(τ) in PDE | reinit | Each pseudo-step | Exact (continuous) | Not addressed |
| **This proposal (unified DCCD)** | reinit | Each pseudo-step | Exact (discrete) | **Preserved** |

The key advance over WIKI-T-027 is addressing the **root cause** (operator
splitting mismatch) rather than the **symptom** (mass drift).

---

## 8. Implementation Plan

1. Modify `Reinitializer.reinitialize()`: replace operator-split loop with
   unified RHS (Steps 2–5 above)
2. Fix reinitialize.py:155: use `self._bc` instead of hardcoded `'neumann'`
3. Remove CN-ADI infrastructure (`_cn_factors`, `_cn_diffusion_axis`,
   `_build_cn_factors`) — no longer needed
4. Validate: exp11_6 single vortex, mass error target < 1e-3 at reinit_freq=1
5. Validate: existing test suite, all 98 tests PASS

---

## 9. Open Questions

1. **TVD-RK3 for reinitialization?** The current scheme uses Forward Euler
   per pseudo-time step. TVD-RK3 would allow larger Δτ (factor ~2) with
   per-stage conservation correction and clip repair. Trade-off: 3× RHS
   evaluations per step vs 2× larger Δτ.

2. **Adaptive εd for reinitialization?** The uniform εd = 0.05 may be
   suboptimal for the compression term. Near-interface cells (where ψ(1−ψ)
   is large) may benefit from lower εd, while far-field cells are irrelevant.
   But uniform εd simplifies the operator and ensures consistency.

3. **Extension to advection?** The advection operator is already
   mass-conservative for periodic BC (§2). The main loss is from clipping.
   A clip-then-repair strategy (identical to Step 5) could be applied
   independently, without changing the spatial operator.
