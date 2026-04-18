---
ref_id: WIKI-P-012
title: "07b_reinitialization: ξ-SDF, FMM, and ε-Widening Sections (CHK-137..139)"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/07b_reinitialization.tex
    description: "Subsubsections added: ξ-SDF (CHK-137), FMM root-cause revision (CHK-138), ε-widening (CHK-139)"
  - path: paper/bibliography.bib
    description: "Sethian1996 FMM reference added"
depends_on:
  - "[[WIKI-P-010]]: CHK-136 Eikonal section (predecessor in same subsection)"
  - "[[WIKI-T-042]]: Theory basis for all three additions"
  - "[[WIKI-E-028]]: Experimental results cited in the sections"
compiled_by: ResearchArchitect
compiled_at: 2026-04-18
---

# 07b_reinitialization: ξ-SDF, FMM, and ε-Widening Sections (CHK-137..139)

Three additions to `paper/sections/07b_reinitialization.tex` arising from
CHK-137 (ξ-SDF strategy), CHK-138 (FMM investigation + root cause revision),
and CHK-139 (ε-widening fix).

---

## CHK-137: New \subsubsection{ξ空間符号距離関数法（CHK-137）}

Added after the Eikonal/ZSP paragraph (CHK-137A mentioned as "実装・検証済み").

### Algorithm Box (algbox)

5-step algorithm with 4 numbered equations:

1. ψ → φ (logit inversion)
2. Zero-crossings:
   ```
   eq:xi_crossing_x: ξ*_x(i,j) = i + φ(i,j)/(φ(i,j) − φ(i+1,j))   [x-dir]
   eq:xi_crossing_y: ξ*_y(i,j) = j + φ(i,j)/(φ(i,j) − φ(i,j+1))   [y-dir]
   ```
3. ξ-SDF:
   ```
   eq:xi_sdf: φ_ξ(i,j) = sgn(φ) × min_k √((i−ξ*_k)² + (j−η*_k)²)
   ```
4. Reconstruction:
   ```
   eq:xi_sdf_psi: ψ(i,j) = H_{ε_ξ}(φ_ξ(i,j)), ε_ξ = ε/h_min
   ```
5. φ-space mass correction (same as DGR, Eikonal Step 4)

### Three Propositions (with proofs)

1. **零点集合保存**: φ_ξ(i,j) = 0 iff the exact zero-crossing passes through
   cell (i,j) — by construction of the minimum-distance field.

2. **ξ空間単位勾配**: |∇_ξ φ_ξ| = 1 almost everywhere; the Voronoi distance
   function satisfies the Eikonal equation in ξ-space.

3. **累積ドリフトなし**: No pseudo-time iteration → no per-call perturbation
   → systematic mode-2 drift mechanism (CHK-136) is eliminated by construction.

### CHK-137 Results Paragraph

- ZSP (Strategy A): D(T=2) = 0.129 (better than Eikonal's 0.245, target 0.05 not met)
- ξ-SDF (Strategy B): D(T=2) = 0.050 (borderline), VolCons 1.46%@T=2, 3.5%@T=10

---

## CHK-138: Revision to the Existing Comparison Table + Root-Cause Paragraph

### FMM Paragraph

Added `\noindent\textbf{CHK-138（Fast Marching Method による検証）：}` paragraph explaining:
- Motivation: C⁰ Voronoi kink hypothesis (test with FMM → C¹ SDF)
- FMM quadratic update: `d = ½(ax+ay+√(2−(ax−ay)²))` if |ax−ay|<1; else d=min+1
- Result: lower φ_xx std (2.83 vs 3.93) but VolCons 5× worse (8.2% vs 1.46%)
- **Conclusion**: Voronoi kink hypothesis refuted

### Interface-Width Hypothesis Paragraph

Added `\noindent\textbf{修正仮説（CHK-138）—界面幅効果：}` with equation:
```
eq:volconsrate (informally):
  ΔV/V₀ ≈ (Δt/ρ) ∫ψ ∇·u* dV  ∝  σκ / (ρ · ε_eff)
```

Split-only gives ε_eff ≈ 1.4ε (diffusion broadening) → reduced PPE residual →
split-only's "defect" is actually its stability mechanism.

### Comparison Table Update (tab:reinit_comparison_chk138)

Row added before \hline:
```
FMM（CHK-138）& ✓ & ✓ & ✗ & — & 8.2%@T=1 & なし
```

---

## CHK-139: New Paragraph + Inline Table After Comparison Table

Added `\noindent\textbf{CHK-139（ε幅拡大による修正）：}` after the comparison table.

### Equation \eqref{eq:xi_sdf_wide}

```latex
\psi_{\text{new}}(i,j) = H_{f\varepsilon_\xi}(\phi_\xi(i,j)), \quad f = 1.4
```

Explains that widening ε_eff = f·ε to match split-only's natural ~1.4ε
broadening explicitly provides the same PPE residual reduction.

### CHK-139 Inline Comparison Table

| Method | D(T=1) | D(T=2) | VolCons max |
|---|---|---|---|
| ξ-SDF (f=1.0, CHK-137) | — | 0.050 | 3.5%@T=10 |
| **ξ-SDF (f=1.4, CHK-139)** | **0.018** ✓ | **0.028** ✓ | **1.38%@T=2** |
| split-only (ref) | — | 0.037 | <1%@T=10 ✓ |

### Residual Analysis Sentence

Notes that VolCons non-monotonically oscillates with capillary wave phase
(t=0.5→1.5: decreasing; t=2.0: rising), indicating PPE residual is phase-coupled
to wave dynamics rather than monotonically accumulating.

### Row Added to Comparison Table (tab:reinit_comparison_chk138)

```
\textbf{ξ-SDF（$f{=}1.4$，CHK-139）}& ✓ & ✓ & ✓ & \textbf{0.028} & 1.38%@T=2 & なし
```

Table caption updated: "CHK-139 更新" replacing "CHK-138 更新".

---

## Bibliography Addition: Sethian (1996)

Added to `paper/bibliography.bib`:

```bibtex
@article{Sethian1996,
  author  = {J.A. Sethian},
  title   = {A Fast Marching Level Set Method for Monotonically Advancing Fronts},
  journal = {Proceedings of the National Academy of Sciences},
  volume  = {93},
  number  = {4},
  pages   = {1591--1595},
  year    = {1996},
  doi     = {10.1073/pnas.93.4.1591},
}
```

Referenced in prose (CHK-138 FMM paragraph) as `\citep{Sethian1996}`.
Note: `OsherSethian1988` was already in bib (level-set method original paper);
Sethian1996 is the FMM-specific reference.
