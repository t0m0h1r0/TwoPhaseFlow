paper/CHANGELOG.md
# Changelog

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
