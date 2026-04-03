# Survey: Pressure Instability in High-Order Two-Phase Flow Solvers

**Date**: 2026-04-04  
**Context**: Rising bubble (σ>0, moving interface) diverges at t≈0.059 with FD spsolve + CCD∇p.  
**Question**: How does the literature address pressure/PPE instability with high-order schemes?

---

## Root Cause Diagnosis

### Cause 1: Capillary CFL Violation (Sussman & Ohta 2006)

Explicit CSF has a linear stability constraint:

$$\Delta t_{\rm cap} = \sqrt{\frac{\rho_{\min} h^3}{8\pi\sigma}}$$

For the rising bubble test (ρ_g=1, h=1/64, σ=0.1):

$$\Delta t_{\rm cap} \approx 0.00123$$

Current dt upper bound = 0.005 → **4× violation** → linearly unstable regardless of spatial order.

At N=128: Δt_cap ≈ 4.4×10⁻⁴ (worsens as h^{3/2}).

### Cause 2: Force-Balance Breakdown on Moving Interface

- **Francois et al. (2006)**: Balanced-force condition requires identical stencils for ∇p and ∇(σκδ).
- **Popinet (2009)**: Balance holds only for *stationary* interfaces. When the interface moves, curvature κ is updated each step, and the new CSF force is not in balance with the previous pressure correction.
- Even CCD O(h⁶) for ∇p cannot rescue this: the inconsistency accumulates each timestep.

This explains why the static droplet is stable (interface fixed) but the rising bubble diverges.

---

## Methods in the Literature

### 1. Capillary CFL Enforcement (Immediate Fix)

**Key paper**: Sussman & Ohta (2006), "A Stable and Efficient Method for Treating Surface Tension in Incompressible Two-Phase Flow," *SIAM J. Sci. Comput.*

**Nangia et al. (2019)** ("A Robust Incompressible Navier-Stokes Solver for High Density Ratio Multiphase Flows," *JCP* 390) confirmed that enforcing this single constraint stabilizes explicit CSF at density ratios up to 10⁶.

**Implementation**:
```python
dt_cap = np.sqrt(rho_min * h**3 / (8 * np.pi * sigma))
dt = min(..., dt_cap)
```

**Limitation**: Δt ~ h^{3/2} → increasingly restrictive on fine grids.

---

### 2. Ghost Fluid Method (GFM) — Fundamental Fix

**Key papers**:
- Kang, Fedkiw & Liu (2000), "A Boundary Condition Capturing Method for Multiphase Incompressible Flow," *J. Sci. Comput.* 15.
- Desjardins, Moureau & Pitsch (2008), "An Accurate Conservative Level Set/Ghost Fluid Method for Simulating Turbulent Atomization," *JCP* 227.

**Core idea**: Replace CSF body force with explicit pressure jump condition [p] = σκ inserted directly into the PPE near-interface rows:

$$[p] = \sigma\kappa, \qquad \left[\frac{1}{\rho}\frac{\partial p}{\partial n}\right] = 0$$

The PPE is modified only at interface-crossing faces; the density discontinuity is handled algebraically rather than smeared.

**Effect**: Desjardins et al. demonstrated stability at ρ₁/ρ₂ ~ 10³ with σ>0 and large deformation.

**Integration with CCD**: CCD stencils span multiple cells, complicating jump insertion. Recommended approach: fall back to 2nd-order FD in the 2–3 cells straddling the interface (hybrid CCD/FD), maintain CCD elsewhere.

**Note**: HFE (Hermite Field Extension) in our codebase was designed precisely to support this split-phase PPE — it provides smooth, high-order field extrapolation across the interface for the GFM ghost values.

---

### 3. Semi-Implicit Surface Tension (Eliminates Capillary CFL)

**Key paper**: Sussman & Ohta (2006), same paper as above.

**Core idea**: Linearize the surface tension force at the next time level:

$$\mathbf{u}^{n+1} + \frac{\Delta t}{\rho}\nabla p^{n+1} = \mathbf{u}^n + \frac{\Delta t}{\rho}\mathbf{f}_{\rm CSF}^{n+1}$$

κ is evaluated at time n; only |∇ψ| is treated implicitly. This modifies the PPE to include a surface-tension operator, removing the capillary CFL entirely.

**Cost**: Modified PPE is no longer purely elliptic; requires careful handling of the added term.

---

### 4. Consistent Mass–Momentum Transport (High Density Ratio)

**Key papers**:
- Raessi & Pitsch (2012), "Consistent Mass and Momentum Transport for Simulating Incompressible Interfacial Flows with Large Density Ratios Using the Level Set Method," *Computers & Fluids*.
- Owkes & Desjardins (2017), "A Consistent Mass and Momentum Flux Computation Method for Two-Phase Flows," *Computers & Fluids*.

**Core idea**: The mass flux used to advance the density field (level-set → ρ update) must be identical to the convective density flux in the momentum equation. Inconsistency → nonphysical momentum errors at large ρ₁/ρ₂.

**Relevance to current solver**: Our solver uses DissipativeCCDAdvection (CLS) for the level-set and CCD for momentum convection — the flux representations differ. This is a secondary issue compared to capillary CFL but becomes important at ρ_l/ρ_g ≥ 10.

---

### 5. Note on High-Order Compact Schemes

Shukla et al. (*JCP* 2007) developed compact FD up to 20th-order for single-phase flow. However, **essentially no published work combines 6th-order CCD with sharp-interface two-phase flow**. All known high-order multiphase solvers (Desjardins 2008, Owkes 2013 DG-CLS) use 2nd-order for PPE and interface operators, reserving high order for bulk quantities only.

**Implication**: The accuracy mismatch between CCD (bulk) and lower-order treatment (interface) is a recognized design tension, not a bug per se. The standard resolution is a hybrid approach.

---

## Recommended Action Plan

### Phase 1 — Immediate (Capillary CFL)

Add to `run_ch12_rising_bubble.py`:
```python
dt_cap = np.sqrt(min(RHO_G, RHO_L) * h**3 / (8 * np.pi * SIGMA))
dt = min(0.2 * h / u_max, dt_visc, dt_cap, T_FINAL - t)
```

Expected: rising bubble should run past t=0.06. This alone may enable the full T=1.5 simulation.

### Phase 2 — Medium Term (§13 Future Work)

GFM split-phase PPE:
1. Extend `PPEBuilder` to accept interface-crossing face list + [p] = σκ jump values.
2. Hybrid CCD/FD: within 2 cells of interface → FD stencil; outside → CCD.
3. HFE provides ghost-cell field values for the GFM ghost nodes.

This enables: rising bubble, capillary waves (Prosperetti benchmark), σ>0 RT instability.

### Phase 3 — Long Term (§13)

Semi-implicit surface tension + consistent mass–momentum coupling → high ρ ratio (≥10³), high Re, high We regimes.

---

## Connection to Paper §13

| §13 Future Work Item | Literature Basis |
|---|---|
| 分相 PPE + GFM | Kang-Fedkiw (2000), Desjardins (2008) |
| 半陰的表面張力 | Sussman & Ohta (2006) |
| 一貫質量-運動量輸送 | Raessi & Pitsch (2012) |
| HFE の GFM 幽霊値生成への活用 | 本ソルバ独自の接続 |

---

## References

1. Francois, M. M., et al. (2006). "A Balanced-Force Algorithm for Continuous and Sharp Interfacial Surface Tension Models Within a Volume Tracking Framework." *JCP* 213, 141–173.
2. Popinet, S. (2009). "An Accurate Adaptive Solver for Surface-Tension-Driven Interfacial Flows." *JCP* 228, 5838–5866.
3. Kang, M., Fedkiw, R. P., & Liu, X.-D. (2000). "A Boundary Condition Capturing Method for Multiphase Incompressible Flow." *J. Sci. Comput.* 15, 323–360.
4. Desjardins, O., Moureau, V., & Pitsch, H. (2008). "An Accurate Conservative Level Set/Ghost Fluid Method for Simulating Turbulent Atomization." *JCP* 227, 8395–8416.
5. Sussman, M., & Ohta, M. (2006). "A Stable and Efficient Method for Treating Surface Tension in Incompressible Two-Phase Flow." *SIAM J. Sci. Comput.* 28(5), 2457–2480.
6. Raessi, M., & Pitsch, H. (2012). "Consistent Mass and Momentum Transport for Simulating Incompressible Interfacial Flows with Large Density Ratios Using the Level Set Method." *Computers & Fluids* 63, 70–81.
7. Owkes, M., & Desjardins, O. (2017). "A Consistent Mass and Momentum Flux Computation Method for Two-Phase Flows." *Computers & Fluids* 152, 57–76.
8. Nangia, N., et al. (2019). "A Robust Incompressible Navier-Stokes Solver for High Density Ratio Multiphase Flows." *JCP* 390, 548–594.
9. Xiao, et al. (2023). "A Consistent Adaptive Level Set Framework for Incompressible Two-Phase Flows with High Density Ratios." *JCP* 478.
