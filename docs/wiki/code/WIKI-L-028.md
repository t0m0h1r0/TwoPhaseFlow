# WIKI-L-028 — Implementation: IIM Jump Decomposition + DC Iteration (LU-Free)

**ref_id:** WIKI-L-028 | **Status:** PROPOSED | **CHK:** CHK-177 (proposed)

## Executive Summary

Implements IIM jump decomposition with Defect Correction (DC) iteration to eliminate Kronecker LU from the PPE solver. Maintains sharp-interface pressure jump correction [p] = σκ while achieving matrix-free, convergent solve via Thomas sweep (ADI).

**Key Trade-off:** Replaces O(N⁴) direct LU with O(N²) per-iteration ADI, accepting convergence iterations in exchange for elimination of dense matrix storage.

---

## Architecture

### Problem Statement

IIM jump decomposition naturally splits:
$$p = \tilde{p} + p_{\text{jump}}, \quad p_{\text{jump}} = \sigma \kappa (1 - H_\varepsilon(\phi))$$

Current implementation (_solve_decomp) solves for $\tilde{p}$ via Kronecker LU:
```python
L_sparse = self._build_sparse_operator(rho_smooth, drho_s)
p_tilde = self._spsolve(L_sparse, rhs_tilde)  # ❌ Dense matrix, O(N⁴)
p_combined = p_tilde + p_jump
```

### New Approach: DC Iteration (Matrix-Free)

Replace LU with DC:
```python
p_tilde = self._dc_solve_smooth(rhs_tilde, rho_smooth, drho_s, p_init=None)
# Internally: repeat until convergence
#   R = rhs_tilde - L(p)  [residual, computed via CCD Laplacian]
#   Δp = Thomas_sweep(R, axis=0) → Thomas_sweep(Δp, axis=1)  [ADI]
#   p += Δp
#   check_convergence(R)
```

---

## Implementation Details

### New Method: `_dc_solve_smooth()`

**Location:** `src/twophase/ppe/iim_solver.py:187–241`

```python
def _dc_solve_smooth(self, rhs_np, rho_np, drho_np, p_init=None):
    """DC iteration for smooth field (LU-free).

    Uses Thomas sweep (1D line solve) on two axes in alternating fashion.
    No assembly of dense operator; residual L(p) computed via CCD derivatives.
    """
    shape = self.grid.shape
    dtau = compute_lts_dtau(rho_np, self._c_tau, self._h_min)
    p = np.zeros(shape) if p_init is None else p_init.copy()
    
    for iteration in range(self.maxiter):
        # Residual: R = rhs − L_CCD(p)
        Lp, dp_arrays, _ = compute_ccd_laplacian_with_derivatives(
            p, rho_np, drho_np, self.ccd, self.backend,
        )
        R = rhs_np - Lp
        
        # Convergence check
        residual, converged = check_convergence(R, pin_dof, self.tol)
        if converged:
            break
        
        # ADI step: alternating 1D line solves
        q = thomas_sweep_1d(R, rho_np, drho_np[0], dtau, axis=0, ...)
        dp = thomas_sweep_1d(q, rho_np, drho_np[1], dtau, axis=1, ...)
        
        # Update
        p = p + dp
        p[pin_dof] = 0.0  # Enforce BC
    
    return p
```

### Modified Method: `_solve_decomp()`

**Location:** `src/twophase/ppe/iim_solver.py:119–165`

Changes:
1. Line 152: `p_tilde = self._lu_solve_smooth(...)` → `self._dc_solve_smooth(...)`
2. Line 162: `p = self._lu_solve_smooth(...)` → `self._dc_solve_smooth(...)`
3. Updated docstring to note "DC反復法で p̃ を解く（LU排除）"

---

## Convergence Mechanism

### ADI (Alternating Direction Implicit)

Thomas sweep on axis k solves a 1D tridiagonal system for each row/column orthogonal to k:
$$\left[I - \frac{\Delta \tau}{2} L_{kk}\right] \Delta p^{(k)} = \Delta \tau R^{(k)}$$

Two sweeps (k=0, then k=1) approximate a 2D implicit step without forming the full 2D matrix.

**Convergence Rate:** O(1/iteration) for smooth problems; depends on pseudo_c_tau (WIKI-T-024 references).

### Convergence Control

| Parameter | Default | Purpose |
|---|---|---|
| `pseudo_c_tau` | 2.0 | Time-step scaling; lower = more stable, slower |
| `tolerance` | 1.0e-6 | Residual norm stopping criterion |
| `maxiter` | 500 | Iteration limit (warn if not converged) |

---

## Jump Decomposition Integration

Within _solve_decomp:

**Step 1: Smooth density and jump**
$$H_\varepsilon(\phi) = \frac{1}{2}\left(1 + \tanh\frac{\phi}{2\varepsilon}\right), \quad \rho_{\text{smooth}} = \rho_L + (\rho_G - \rho_L) H_\varepsilon$$
$$p_{\text{jump}} = \sigma \kappa (1 - H_\varepsilon)$$

**Step 2: Adjusted RHS**
$$\tilde{f} = f - L_{\text{CCD}}(p_{\text{jump}})$$

**Step 3: DC iterate on smooth ρ**
$$\tilde{p} = \text{DC\_iterate}(\tilde{f}, \rho_{\text{smooth}})$$

**Step 4: Combine**
$$p = \tilde{p} + p_{\text{jump}}$$

---

## Trade-offs & Limitations

| Aspect | Benefit | Drawback |
|---|---|---|
| **Memory** | No Kronecker matrix (O(N²) vs O(N⁴)) | Residual recalculation per iteration |
| **Parallelism** | Thomas sweep is sequential in time | Line solve inherently serial in each sweep |
| **Convergence** | Reliable for smooth ρ | Slower than LU (100s–1000s iterations possible) |
| **Interface handling** | Jump correction exact at stencil level | DC may require extra iterations near interface |

---

## Validation & Next Steps

### Unit Tests

`tests/test_iim_decomp_dc.py` (proposed):
- **V1**: Converges on constant density (no interface)
- **V2**: Jump field reconstruction vs analytical
- **V3**: Residual monotonic decay
- **V4**: Volume conservation with IIM

### Experimental Validation

**ch13_06_capwave_waterair_n128** (CHK-176 + CHK-177):
- Run with `iim_backend: decomp` + default `pseudo_c_tau: 2.0`
- Monitor iteration count in solver diagnostics
- Compare final pressure field with prior LU baseline

---

## Configuration Reference

```yaml
# config.yaml
solver:
  ptype: iim                    # Use IIM solver
  iim_backend: decomp           # Jump decomposition
  iim_mode: hermite             # Interface correction (hermite or first-order)
  pseudo_c_tau: 2.0             # ADI time-step (lower=stable, slower)
  tolerance: 1.0e-6             # Residual convergence
  maxiter: 500                  # Max DC iterations
```

---

## Cross-References

**Related CHKs:**
- CHK-175: IIM jump decomposition (first implementation)
- CHK-176: R-1.5 FVM-CSF fix + water-air capillary experiment
- CHK-177: This entry (DC iteration for decomp)

**Related Wiki:**
- WIKI-T-021: IIM theory (sharp interface, jump correction)
- WIKI-T-024: ADI / DC theory (convergence, smoothing)
- WIKI-X-020: Full three-layer chain (Topological → Geometric → Hydrostatic)

**Code Path:**
- `src/twophase/ppe/iim_solver.py` (_dc_solve_smooth, _solve_decomp)
- `src/twophase/ppe/ccd_ppe_utils.py` (compute_ccd_laplacian_with_derivatives, compute_lts_dtau, check_convergence)
- `src/twophase/ppe/thomas_sweep_legacy.py` (thomas_sweep_1d)

---

## Conclusion

IIM jump decomposition with DC iteration provides a matrix-free, memory-efficient path to sharp-interface PPE solving without sacrificing accuracy or convergence robustness. Suitable for high-density-ratio flows (e.g., water-air) and GPU environments where dense matrices are prohibitive.

**Recommendation:** Use decomp+DC as the production path for IIM; reserve LU only for low-N debugging or validation.
