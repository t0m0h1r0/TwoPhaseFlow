# Interface Filter Design Using CCD Derivatives
# A3-traced: filter equations → CCD discretization → implementation
# Date: 2026-04-04  (updated with HFE filter + stability analysis)

---

## 0. Motivation

The current pipeline computes κ via CCD 6th-order derivatives of φ.
High-frequency oscillations in **n** (unit normal) propagate into κ, driving
spurious currents via the CSF term.  The existing DCCD 3-point dissipative
filter (`_dccd_filter_1d`) damps these modes only weakly because it acts
linearly on the *derivative field* after computation, not on the *geometric
quantities* κ and n.

This memo details two CCD-native filters ordered by expected impact.

---

## 1. Infrastructure Available in src/

| Symbol | Source | API |
|--------|--------|-----|
| `ccd.differentiate(f, ax)` | `ccd/ccd_solver.py` | Returns `(∂f/∂x_ax, ∂²f/∂x_ax²)` |
| `delta(xp, phi, eps)` | `levelset/heaviside.py` | `δ_ε(φ) = (1/ε)H(1-H)` |
| `invert_heaviside(xp, psi, eps)` | `levelset/heaviside.py` | `ψ → φ` |
| `NormalVectorFilter` | `levelset/normal_filter.py` | **NEW** — normal diffusion filter |
| `InterfaceLimitedFilter` | `levelset/curvature_filter.py` | **NEW** — HFE filter |

---

## 2. Critical: h² Scaling (Mesh-Independent Parameters)

**All filters implemented as explicit diffusion steps:**

    q* = q + C h² w ∇²q     (+ sign = diffusion; − sign = anti-diffusion → BUG)

where **h = min grid spacing**.

### Why h² is mandatory

CCD computes *physical* derivatives: `ccd.differentiate(f, ax)[0]` = `∂f/∂x` (units: 1/L).
The Laplacian `∇²q` has units `q/L²`. For a uniform grid with L=1, N points: `|∇²q_noise| ~ q/h²`.

Without h² scaling: `C · ∇²q_noise ~ C · q/h²`. For C=0.05 and N=64: update = `0.05 · 64² · q ≈ 200q`. Unstable.

With h² scaling: `C · h² · ∇²q_noise ~ C · q`. For C=0.05: update = `0.05 · q`. Correct.

### Stability limit (2D, w ≤ 1)

Fourier attenuation factor at highest mode: `(1 − 8C·w_max)`.
Stable for: `C < 1/8 = 0.125`.

| C     | Damping per step (highest mode) |
|-------|--------------------------------|
| 0.03  | 24% |
| 0.05  | 40% ← default |
| 0.08  | 64% |
| 0.125 | 100% (kills highest mode completely) |

**C > 0.125 = UNSTABLE in 2D.**

### User-facing parameter C

The h² normalization is built into the implementation. `C` is truly
mesh-independent: the same C on N=32, 64, 128 grids gives the same
physical damping ratio.

---

## 3. Filter 1: Normal-Vector Diffusion Filter (Priority 1)

**File:** `src/twophase/levelset/normal_filter.py`

**Equation:**
```
n* = n + C h² ∇·(|∇φ| ∇n)     (componentwise, per n_i)
n* ← n* / |n*|                  re-normalisation
```

**Interface weight:** `w = |∇φ|` (≈ 1 near interface for a good SDF).
Mask: `δ_ε(φ) > threshold_frac · max(δ_ε)`.

**CCD discretization (per component n_i, per axis ax):**
```
Step 1.  dni_ax, _ = ccd.differentiate(n_i, ax)      # ∂n_i/∂x_ax
Step 2.  flux = |∇φ| · dni_ax                        # w · ∂n_i/∂x_ax
Step 3.  dflux, _ = ccd.differentiate(flux, ax)      # ∂(w·∂n_i/∂x_ax)/∂x_ax
Step 4.  div_term += dflux
Step 5.  n_i_new = n_i + C · h² · div_term
```

**CCD cost:** 2·ndim CCD calls per component = 8 calls in 2D.

**Why it works:** κ = -∇·n; noise in κ originates from high-frequency
kinks in n. Smoothing n at the interface reduces κ noise without touching
φ. Volume conservation: perfect (φ unchanged).

---

## 4. Filter 2: Interface-Limited HFE Filter (Priority 2)

**File:** `src/twophase/levelset/curvature_filter.py`

**Equation:**
```
q* = q + C h² w(ψ) ∇²q
```

**Interface weight:** `w(ψ) = 4ψ(1−ψ)` — mesh-independent O(1) weight.

### Why 4ψ(1-ψ) instead of δ_ε(φ)?

`δ_ε(φ) ~ 1/h` (since `ε ~ h`).  With h² scaling:
`h² · δ_ε · ∇²q ~ h² · (1/h) · q/h² = q/h` → grows with refinement. NOT mesh-independent.

`4ψ(1-ψ) = 4H(1-H) = 4ε·δ_ε ~ 4h·δ_ε = O(1)`.  With h² scaling:
`h² · 4ψ(1-ψ) · ∇²q ~ h² · O(1) · q/h² = O(q)` → mesh-independent. ✓

**CCD discretization:**
```
Step 1.  w = 4·ψ·(1-ψ)
Step 2.  for ax in range(ndim):
             _, q_xx = ccd.differentiate(q, ax)       # ∂²q/∂x_ax² (free alongside d1)
             lap_q += q_xx
Step 3.  q* = q + C · h² · w · lap_q
```

**Zero-overhead path:** pass `d2_list` (pre-computed d2 from curvature pipeline):
```python
d2_list = [ccd.differentiate(kappa, ax)[1] for ax in range(ndim)]
kappa_filt = hfe.apply(kappa, psi, d2_list=d2_list)  # 0 extra CCD calls
```

**CCD cost:** ndim calls if d2 not pre-computed; else 0.

**Application:** Call after κ computation, before CSF force evaluation.

---

## 5. Integration into CurvatureCalculator

```python
# Constructor injection (SOLID DIP):
nf = NormalVectorFilter(backend, ccd, eps, alpha=0.05)
hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)
curv = CurvatureCalculator(backend, ccd, eps,
                            normal_filter=nf,
                            kappa_filter=hfe)

# compute() pipeline:
# 1. φ = invert_heaviside(ψ)
# 2. d1, d2 = CCD derivatives of φ
# 3. [if normal_filter] n = d1/|d1|; n* = filter(n); κ = -∇·n*
#    [else]             κ from Hessian formula
# 4. [if kappa_filter]  κ* = kappa_filter.apply(κ, ψ)
# 5. return κ*
```

---

## 6. Recommended Pipeline

```
1. φ advection (WENO5 + TVD-RK3)
2. Light reinit: 1–3 steps (Reinitializer)
3. φ → n (CCD)
4. [NormalVectorFilter]     n* = n + C h² ∇·(|∇φ| ∇n)
5. κ = -∇·n* (CCD)
6. [InterfaceLimitedFilter] κ* = κ + C h² 4ψ(1-ψ) ∇²κ
7. CSF surface tension (uses κ*)
8. NS predictor → PPE → corrector
```

---

## 7. Parameter Guideline

| Parameter | Stable range (2D) | Recommended | Notes |
|-----------|-------------------|-------------|-------|
| `NormalVectorFilter.alpha` | C < 0.125 | 0.05 | per-step 40% damping |
| `InterfaceLimitedFilter.C` | C < 0.125 | 0.05 | same stability bound |
| `w_threshold_frac` | — | 0.10 | mask: 10% of δ_ε peak |

Can use both filters simultaneously; they are independent operators.

---

## 8. What NOT to Do

| Action | Reason |
|--------|--------|
| Filter φ directly | Destroys volume conservation |
| Use − sign in `q ± C h² w ∇²q` | Anti-diffusion: amplifies noise |
| Use `δ_ε` as weight for HFE (not h-corrected) | Not mesh-independent |
| C > 0.125 | Unstable in 2D |
| Apply κ filter to PPE | Destroys divergence-free condition (§4d paper) |

---

## 9. Open Questions

1. **Balanced-force consistency:** Filtered n gives κ* that may not balance
   the discrete ∇p exactly. Check `∇p = σκ*∇H` after filtering.
2. **Spectral design:** CCD has known Fourier transfer functions. Could
   design C to null-space the problematic wavenumbers exactly.
3. **3D:** Both filters extend trivially (just loop over 3 components/axes).
