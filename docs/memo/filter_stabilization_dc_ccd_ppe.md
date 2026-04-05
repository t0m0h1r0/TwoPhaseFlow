# Filter Stabilization of DC-CCD PPE Solver: Experimental Study

**Date**: 2026-04-05  
**Experiments**: exp10_16 – exp10_19  
**Status**: Negative result with clear theoretical explanation

---

## 1. Problem

Solve the variable-density PPE with CCD accuracy:

$$\nabla \cdot \!\left(\frac{1}{\rho}\nabla p\right) = q, \quad [0,1]^2, \quad \partial_n p\big|_{\partial\Omega}=0$$

**DC iteration**: use cheap FD as preconditioner, CCD as residual evaluator:

$$R^{(k)} = q - L_H p^{(k)}, \quad L_{FD}\,\delta p = R^{(k)}, \quad p^{(k+1)} = p^{(k)} + \delta p$$

Fixed point is $L_H p^* = q$ (CCD-accurate solution) regardless of $L_{FD}$ accuracy.

---

## 2. Why DC Diverges (exp10_16)

The iteration matrix in Fourier space has eigenvalue:

$$\mu_k = 1 - \frac{\lambda_{H,k}}{\lambda_{FD,k}}$$

CCD better approximates the true Laplacian eigenvalue $-k^2$, while FD underestimates it.  
At Nyquist ($kh = \pi$): $|\lambda_H| / |\lambda_{FD}| \approx \pi^2/4 \approx 2.47 > 2$.

**Condition**: DC converges iff $\max_k \lambda_{H,k}/\lambda_{FD,k} < 2$.  
Violated at high wavenumbers → divergence. Observed even at $\rho=1$ (uniform density).

---

## 3. Strategy B: Insert a Damping Filter

After each DC step, apply filter $F_\alpha^{-1} = (I - \alpha L)^{-1}$:

$$p^{(k+1)} = F_\alpha^{-1}\!\left(p^{(k)} + \delta p\right)$$

Transfer function: $G(k) = 1/(1 - \alpha \lambda_k) \in (0,1]$ — low-pass filter.  
Combined spectral radius:

$$|\mu_{\rm combined}| = \frac{|1 - \lambda_H/\lambda_{FD}|}{|1 - \alpha\lambda_L|}$$

For convergence: $\alpha > (\lambda_H/\lambda_{FD} - 2) / |\lambda_L| \approx 0.12\, h^2$ at Nyquist.

### 3.1 Fixed-point Bias (applies to all filter variants)

With constant $\alpha \neq 0$, the fixed point satisfies a **modified equation**:

$$L_H p^* = q + \alpha\, L_{\rm filter}^2\, p^* \quad \neq \quad L_H p^* = q$$

Bias: $\|p^* - p^{**}\|_\infty \approx \alpha\, |\lambda_{FD,1}|^2 / |\lambda_{H,1}| \cdot \|p^{**}\|_\infty \approx \alpha\cdot 2\pi^2 \|p^{**}\|_\infty$

For $\alpha = c\,h^2$: bias $= O(h^2)$ (second-order). **Destroys CCD's $O(h^6)$ accuracy.**

---

## 4. Experiments and Results

### 4.1 exp10_17 — CCD Filter $(I - \alpha L_H)^{-1}$

**Result**: All cases diverge. Larger $\alpha$ → faster divergence.

**Cause**: CCD uses 4-point one-sided compact BC at walls; FD uses ghost-cell  
reflection $p[-1]=p[1]$. Different BCs → different eigenvectors → filter  
amplifies the diverging modes instead of damping them.

### 4.2 exp10_18 — FD Filter $(I - \alpha L_{FD})^{-1}$

$L_{FD}$ and $(I - \alpha L_{FD})$ share the same eigenvectors (polynomial relation).  
Filter theory is exact in the $L_{FD}$ eigenbasis.

**Result**: Divergence stopped (STALL). Residuals plateau at predictable level.

| $N$ | $\rho_l/\rho_g$ | $\alpha=0.25h^2$, err$_\infty$ |
|-----|----------|-------------------------------|
| 32  | 1        | $4.8 \times 10^{-3}$          |
| 64  | 1        | $1.2 \times 10^{-3}$ (×4 as $h$→0) |
| 32  | 1000     | $3.9 \times 10^{-1}$ (too large) |

Bias scales as $h^2$ for uniform density, but explodes at high density ratio  
because $\|L_{FD}^2\| \propto \rho_l/\rho_g \cdot h^{-4}$.

### 4.3 exp10_19 — Ghost-cell BC Alignment + CCD Filter

**User insight**: align CCD's Neumann BC to FD ghost-cell so they share eigenvectors.

Implementation: after CCD differentiation, override boundary rows:

$$\left.\frac{\partial p}{\partial x}\right|_{\rm wall} = 0, \qquad \left.\frac{\partial^2 p}{\partial x^2}\right|_{\rm wall} = \frac{2(p_1 - p_0)}{h^2}$$

**Result**: Ghost-BC CCD filter STALLs (no divergence). STALL level **identical to FD  
filter** — the ghost-cell override makes $L_H = L_{FD}$ exactly at boundary nodes,  
so both filters produce the same bias.

---

## 5. Summary

| Solver | $\rho=1$ behavior | $\rho=1000$ behavior | Root cause |
|--------|-------------------|----------------------|------------|
| DC + LU (no filter) | DIV | DIV | $\lambda_H/\lambda_{FD} > 2$ at Nyquist |
| CCD filter (CCD BC) | DIV faster | DIV faster | BC mismatch → wrong eigenvectors |
| FD filter (fixed $\alpha$) | STALL $O(h^2)$ err | STALL large err | Fixed-point bias |
| Ghost-BC CCD filter | STALL $O(h^2)$ err | STALL large err | Same bias |
| Any filter, fading $\alpha$ | DIV (after fade) | DIV (after fade) | DC re-diverges |

**Fundamental trade-off**: The filter must satisfy $\alpha \geq O(h^2)$ for stability,  
but this causes $O(1)$ bias unless cancelled by another mechanism.

---

## 6. Viable Paths Forward

| Option | Cost | Accuracy | Status |
|--------|------|----------|--------|
| Direct Kronecker LU on $L_H$ | $O(N^3)$ setup, $O(N^2)$ solve | CCD $O(h^6)$ | ✓ Implemented |
| Krylov (CG/GMRES) + $L_{FD}$ precond | $O(N^2)$ per iter | CCD $O(h^6)$ | Candidate |
| DC as smoother + multigrid coarse correction | $O(N^2)$ | depends | Requires MG |
| Filter-stabilized DC | $O(N^2)$ | $O(h^2)$ only | This work — not viable |

For the current solver (§8c in paper): **Kronecker LU is the recommended path.**  
Filter-stabilized DC is not viable for high density ratios.

---

## References

- exp10_16: `experiment/ch10/exp10_16_dc_sweep_convergence_limit.py`
- exp10_17: `experiment/ch10/exp10_17_ccd_filter_dc.py`  
- exp10_18: `experiment/ch10/exp10_18_fd_filter_dc.py`
- exp10_19: `experiment/ch10/exp10_19_ghost_bc_ccd_filter.py`
- Theory: `docs/memo/理論_CCD-DC反復収束性解析.md`
