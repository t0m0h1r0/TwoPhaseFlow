---
ref_id: WIKI-T-118
title: "CCD Local Truncation and Spectral Error Coefficients Are Different Objects"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ccd, truncation_error, modified_wavenumber, spectral_error, diagnostics]
sources:
  - path: paper/sections/04_ccd.tex
    description: "Distinction between stencil residual coefficients and operator-level modified-wavenumber error"
depends_on:
  - "[[WIKI-T-011]]"
  - "[[WIKI-T-117]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Two CCD Error Coefficients

## Knowledge Card

The paper distinguishes two sixth-order error numbers that are easy to conflate:

```text
local Taylor stencil residual coefficient
operator-level modified-wavenumber dispersion coefficient
```

For CCD Equation-I, the local residual coefficient and the spectral
modified-wavenumber coefficient are not the same object.  One comes from the
Taylor-expanded equation stencil; the other measures the effective Fourier
operator after the compact solve.

## Consequences

- Matching a Taylor residual coefficient does not fully characterize dispersion.
- Spectral comparisons must use the coupled operator symbol, not only local
  stencil algebra.
- Verification can legitimately report both local order and modified-wavenumber
  behavior.
- Apparent coefficient discrepancies may be diagnostic-category mismatches.

## Paper-Derived Rule

Name whether a CCD error coefficient is local-stencil or operator-spectral
before using it to compare schemes.
