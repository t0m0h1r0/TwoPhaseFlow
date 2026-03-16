# Changelog

## Paper Revision — Pedagogical Expansion (2026-03-16)

### Files Modified

| File | Change |
|------|--------|
| `sections/00_abstract.tex` | Fixed pressure solver description: BiCGSTAB → 仮想時間 CCD 陰解法 |
| `sections/01_introduction.tex` | Swapped table rows 4–5 (Grid/CCD order) + corrected roadmap paragraph order to Grid→CCD |
| `sections/08_time_integration.tex` | Added step-by-step capillary wave time constraint derivation (defbox) |
| `sections/09_full_algorithm.tex` | Corrected C_WENO operator label from 保存形 → 非保存形 with pedagogical note |
| `sections/11_conclusion.tex` | Complete rewrite: 31 lines → ~280 lines with §11.1 design table, accuracy summary, precision mismatch discussion, §11.2 future work, §11.3 learner message |

### Verification

```
xelatex -interaction=nonstopmode main.tex
→ Output written on main.pdf (102 pages, no undefined references)
```

---

## Merged Version (Combined A & B)

### Structural Changes
- **Document Class:** Switched from `article` to `bxjsarticle` (XeLaTeX compliant) as defined in Paper B.
- **Project Structure:** Refactored monads into `paper/sections/` modules.
- **Preamble:** Unified package imports. Preserved `tcolorbox` styles from Paper A (mybox, derivbox, etc.) for detailed equations.
- **Fonts:** Adopted `Times New Roman` and `Hiragino Mincho ProN` (via `xeCJK`) from Paper B.

### Content & Methodology Updates
- **Interface Tracking:** Replaced Standard Level Set (Paper A) with **Conservative Level Set (CLS)** (Paper B). Equations updated to use $\psi$ instead of $\phi$ for advection.
- **Advection Scheme:** Introduced **WENO5** (Paper B) for advection terms, replacing generic references.
- **Rhie-Chow Correction:** Updated the coefficient definition to the harmonically averaged density form found in Paper B.
- **Surface Tension:** Clarified the Balanced-force formulation using CLS variables.

### Content Preservation
- Retained detailed derivations of CCD coefficients (Paper A).
- Retained detailed grid metric transformation rules (Paper A).
- Retained the detailed algorithm flowchart logic (Paper A).
