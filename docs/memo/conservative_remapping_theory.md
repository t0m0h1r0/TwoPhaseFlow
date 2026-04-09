# Conservative Remapping Theory for CLS on Non-Uniform Grids

Date: 2026-04-09  
Status: Investigation memo (theory-first)

---

## 1. Problem definition

CLS field ψ ∈ [0,1] on node-centered tensor-product grid.  
Grid rebuilt periodically to track moving interface.  
**Requirement**: preserve discrete mass exactly during grid transfer:

    M = Σ_{i,j} ψ_{ij} · h_x[i] · h_y[j] = const

Current approach: ψ → φ → cubic interpolate → heaviside → ψ → mass correction.  
Result: mass_err = 3–11%.

---

## 2. Why does the current approach fail?

Three operations destroy conservation:

### 2a. Nonlinear transform: ψ → φ → ψ round-trip

    φ = ε · logit(ψ) = ε · ln(ψ/(1−ψ))

This is unbounded near ψ=0 and ψ=1. Cubic interpolation of φ produces
overshoots/undershoots in the logit-space. Then heaviside(φ) = 1/(1+exp(−φ/ε))
clips these extremes, destroying mass. **The nonlinear round-trip is the
primary mass loss mechanism.**

Even if ∫φ dV were conserved, ∫H(φ) dV ≠ ∫H(φ_old) dV because H is
nonlinear. Conservation of the integrand does not imply conservation of
the transformed quantity.

### 2b. Point-value interpolation ignores cell volumes

Interpolation estimates ψ(x_new) from ψ(x_old). This is correct for
approximating the **field** at new points but says nothing about the
**integral** Σ ψ h. When h changes (non-uniform grid), the weighted sum
changes even if the field values are exact.

### 2c. Post-hoc correction is too large

With 11% mass error, the correction λ·w (w = 4ψ(1−ψ)) must redistribute
a large mass deficit at the interface, effectively thickening or thinning it.
The correction is a shape distortion proportional to the mass error magnitude.

---

## 3. What should be conserved?

ψ is an **intensive** quantity (like density). The conserved **extensive**
quantity is:

    m_i = ψ_i · dV_i     (mass at node i)

The total mass M = Σ m_i is a discrete quadrature. The remapping must preserve
this specific discrete sum, not some continuous integral.

**Key point**: both old and new grids use the same quadrature rule
(Grid.cell_volumes()), so we need:

    Σ_j ψ_j^(new) · dV_j^(new) = Σ_i ψ_i^(old) · dV_i^(old)

---

## 4. What should we remap: ψ or φ?

| Quantity | Bounded? | Smooth? | Conservation meaning |
|----------|----------|---------|---------------------|
| ψ | [0,1] | Yes (sigmoid, ~6ε width) | ∫ψ dV = mass (direct) |
| φ | unbounded | No (logit singularity at ψ→0,1) | ∫H(φ) dV = mass (indirect) |

**Conclusion: remap ψ directly.** Use φ only for grid generation (update_from_levelset).

Rationale:
- ψ is bounded → no interpolation overshoot beyond physical range
- ψ is the quantity whose integral defines mass → conservation is direct
- No nonlinear φ→ψ transform needed after remap → eliminates §2a entirely
- ψ has a smooth sigmoid profile over ~6 cells → cubic interpolation accurate

The current code remaps φ because "φ is smoother". But this is wrong:
φ = ε·logit(ψ) diverges at ψ=0 and ψ=1. The clipped logit is numerically
bounded but still has steep gradients where ψ is near saturation. ψ itself
is the smoother, better-conditioned quantity.

---

## 5. Can the remap be split axis-by-axis?

**Yes.** For tensor-product grids, dV_{ij} = h_x[i] · h_y[j].

Mass:  M = Σ_i Σ_j ψ_{ij} · h_x[i] · h_y[j]
         = Σ_j h_y[j] · ( Σ_i ψ_{ij} · h_x[i] )

If we remap axis 0 first (x-direction), preserving the 1D mass for each j:

    Σ_k ψ̃_{kj} · h_x^(new)[k] = Σ_i ψ_{ij} · h_x^(old)[i]   ∀j

Then: M_new = Σ_j h_y^(old)[j] · Σ_k ψ̃_{kj} · h_x^(new)[k]
            = Σ_j h_y^(old)[j] · Σ_i ψ_{ij} · h_x^(old)[i]
            = M_old  ✓

After remapping axis 1 (y-direction) with the same logic, total mass is
preserved. **Dimension splitting is exactly conservative on tensor-product grids.**

---

## 6. Three candidate approaches

### Approach A: Direct ψ interpolation + small mass correction

    1. φ = invert_heaviside(ψ)        — for grid generation only
    2. grid.update_from_levelset(φ)    — rebuild grid
    3. ψ_new = interpolate(ψ, old→new) — cubic, on ψ directly
    4. apply_mass_correction(ψ_new)    — expect small correction

**Hypothesis**: By skipping the φ round-trip, mass error should be much
smaller (maybe < 1% instead of 11%). If the correction λ·w is small,
shape distortion is negligible.

**Pro**: Simplest to implement (one-line change in experiment).
**Con**: Not formally conservative. Mass error depends on interpolation quality.

### Approach B: Flux-form 1D conservative remap

Treat ψ_i as piecewise constant over control volume CV_i, then redistribute
mass based on old/new cell overlaps.

For each new node j with control volume [l_j^new, r_j^new]:

    m_j^(new) = Σ_i ψ_i^(old) · overlap(CV_i^old, CV_j^new)

    ψ_j^(new) = m_j^(new) / h_j^(new)

**Pro**: Exactly conservative by construction. No post-hoc correction needed.
**Con**: 1st-order accurate (piecewise constant). Control volume definition
at boundaries needs care.

### Approach C: Higher-order flux-form (piecewise linear)

Same as B but reconstruct ψ as piecewise linear with limited slopes:

    ψ(x) = ψ_i + s_i · (x − x_i)   in CV_i

    s_i = minmod(Δψ_{i-1}/Δx_{i-1}, Δψ_i/Δx_i)   (slope limiter)

Overlap integral becomes analytic (linear × indicator):

    ∫_{a}^{b} [ψ_i + s_i(x − x_i)] dx = ψ_i(b−a) + s_i[(b²−a²)/2 − x_i(b−a)]

**Pro**: 2nd-order accurate + conservative. Limiter preserves ψ ∈ [0,1].
**Con**: More complex. Slope limiter may over-damp at interface.

---

## 7. Control volume definition: a subtlety

Grid.h[i] is defined as:
- Boundary: h[0] = dx[0], h[N] = dx[N-1] (full cell width)
- Interior: h[i] = 0.5 · (dx[i-1] + dx[i])

The natural dual-mesh control volume has width:
- Boundary: dx[0]/2, dx[N-1]/2 (half cell)
- Interior: 0.5 · (dx[i-1] + dx[i]) (same as h[i])

So **boundary nodes have h = 2 × natural CV width**. This means the Grid's
quadrature rule gives double weight to boundary nodes compared to the
standard midpoint rule.

For conservative remapping, we must use the SAME weight definition (h from Grid)
in both old and new grids. The overlap computation must respect this:

    CV_i = [x_i − h_i/2, x_i + h_i/2]   (NOT the dual-mesh definition)

Wait — this doesn't work either, because adjacent CVs would overlap.

**Better interpretation**: h_i is not a geometric width but a quadrature weight.
The "mass" M = Σ ψ_i h_i is a specific quadrature formula. Conservative remap
must preserve THIS sum, regardless of geometric interpretation.

**Resolution for flux-form**: Define CV_i using the standard dual mesh
(half-cells at boundaries), then scale the final ψ_j^(new) so that:

    ψ_j^(new) · h_j^(new) = m_j^(new,geometric)

where m_j^(new,geometric) is the overlap integral using geometric CVs. This
automatically satisfies conservation because:

    Σ m_j^(new,geometric) = Σ m_i^(old,geometric) = ∫ψ dx ≈ M

Hmm, but ≈ is not exact. The quadrature sum M = Σ ψ_i h_i may differ from
∫ψ dx by O(h²). So geometric overlap doesn't guarantee exact discrete conservation.

**True resolution**: For exact discrete conservation, define the remap
algebraically as a matrix R satisfying R^T h_new = h_old (see §8).

---

## 8. Algebraic formulation: the remapping matrix

Define the remapping as ψ_new = R · ψ_old where R is (N+1)×(N+1).

Conservation requires: h_new^T · R · ψ_old = h_old^T · ψ_old  ∀ ψ_old

    ⟹ R^T · h_new = h_old                     ...(★)

This is N+1 linear constraints on (N+1)² unknowns. Under-determined.
Additional desiderata:

1. **Locality**: R_{ji} ≠ 0 only if CV_i^old and CV_j^new overlap.
   For smooth grid changes, R is nearly diagonal (banded).

2. **Partition of unity**: Σ_j R_{ji} = 1 (each old node distributes
   all its mass to new nodes). This means: R^T · 1 = 1.

   Combined with (★): R^T [h_new, 1] = [h_old, 1].

3. **Non-negativity**: R_{ji} ≥ 0 (no negative mass transfer).

4. **Accuracy**: R should reproduce polynomials up to degree p.
   For p=0: R · 1 = 1 (constant preservation).
   For p=1: R · x_old = x_new (linear preservation).

The flux-form approach (§6B) naturally produces an R satisfying all of these.

---

## 9. My assessment after deliberation

### The real insight

The biggest win is NOT choosing the right remapping algorithm — it's
**eliminating the φ round-trip**. The current code:

    ψ → φ → interpolate(φ) → H(φ) → ψ → mass_correction

introduces 11% mass error through two nonlinear transforms. Simply doing:

    ψ → interpolate(ψ) → mass_correction

should reduce mass error to < 1% (interpolation of a bounded [0,1] field).

### Recommendation

**Step 1** (immediate, 5 min): Test direct ψ interpolation in exp11_22.
If mass_err < 0.5%, this may be sufficient. Document as Approach A.

**Step 2** (if Step 1 insufficient): Implement 1D piecewise-constant
flux-form conservative remap. Apply axis-by-axis for 2D. This guarantees
M_new = M_old exactly.

**Step 3** (refinement): If Step 2 shows excessive shape degradation
(piecewise constant is only 1st-order), upgrade to piecewise linear
with minmod limiter.

### Open question

Is the Grid's h definition (doubled boundary weights) a deliberate design
choice or a bug? If it's deliberate, the flux-form remap must match it.
If it's a bug, fixing h would simplify everything.

→ Check: is cell_volumes() used consistently across advection, reinit,
  and mass correction? If yes, it's a convention (not a bug), and the
  remap must respect it.

---

## 10. Experimental verification (2026-04-09)

### Setup
N=128, ε/h=0.5, α=2, dynamic rebuild every 20 steps, Zalesak 1 revolution.

### Results

| Remap mode | L2(φ) | area_err | mass_err | per-remap max |
|------------|-------|----------|----------|---------------|
| φ cubic (current) | 3.57e-2 | 7.15e-2 | **2.97e-2** | 5.3e-2 |
| ψ cubic | 4.68e-2 | 1.10e-2 | **4.59e-3** | 3.3e-2 |
| **ψ linear** | 3.74e-2 | 1.46e-2 | **5.12e-5** | 1.8e-2 |

Reference (uniform, no rebuild): L2(φ)=1.05e-2, area=3.2e-4, mass≈0.

### Analysis

1. **φ round-trip is confirmed as the primary mass loss mechanism.**
   Removing it (ψ direct) reduces mass_err from 3% to 0.005%.

2. **Linear > cubic for ψ interpolation.** Cubic overshoots at the steep
   sigmoid transition (width ~6 cells) → clip → mass loss. Linear is monotone
   → no overshoot → near-perfect mass conservation.

3. **Flux-form conservative remap is NOT needed.** ψ linear interpolation
   + existing mass correction achieves mass_err = 5e-5 (effectively zero).
   The post-hoc correction redistributes < 0.005% of total mass,
   causing negligible shape distortion.

4. **Shape accuracy**: L2(φ) ≈ 3.7e-2 for all dynamic rebuild modes,
   vs 1.05e-2 for uniform. The 3.5× gap is from advection on non-uniform
   grid (known limitation: CN diffusion uses uniform h), not from remapping.

### Conclusion

**The simplest approach wins.** Replace the φ round-trip with direct ψ linear
interpolation. No complex conservative remapping algorithm is needed.

The remaining 3.5× L2(φ) gap vs uniform is an advection/reinit issue on
non-uniform grids (CN diffusion coefficients, GCL), not a remapping issue.

### Changes to make

In `exp11_22_zalesak_nonuniform.py` (and future production code):
```python
# Old (φ round-trip):
phi_cur = invert_heaviside(psi, eps)
grid.update_from_levelset(phi_cur, eps, ccd)
interp = RegularGridInterpolator(old_coords, phi_cur, method="cubic", ...)
psi = heaviside(interp(pts), eps)

# New (ψ direct):
phi_cur = invert_heaviside(psi, eps)  # for grid generation only
grid.update_from_levelset(phi_cur, eps, ccd)
interp = RegularGridInterpolator(old_coords, psi, method="linear", ...)
psi = clip(interp(pts), 0, 1)
```
