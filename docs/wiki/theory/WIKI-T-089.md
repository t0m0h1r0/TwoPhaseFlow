---
ref_id: WIKI-T-089
title: "Dissipation Channel Taxonomy: None, Post-Filter, Internal, and Face-Locus"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ccd, dccd, uccd6, fccd, dissipation, operator_family]
sources:
  - path: paper/sections/04c_dccd_derivation.tex
    description: "DCCD as nodal post-filter and interface-switched stabilization"
  - path: paper/sections/04d_uccd6.tex
    description: "UCCD6 as internal hyperviscosity and scheme-family comparison"
depends_on:
  - "[[WIKI-T-079]]"
  - "[[WIKI-T-088]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Dissipation Channel Taxonomy

## Knowledge Card

The paper separates CCD-derived schemes by where dissipation lives:

```text
CCD:   nodal, no dissipation
DCCD:  nodal, external post-filter
UCCD6: nodal, internal selective hyperviscosity
FCCD:  face-locus reconstruction, no dissipation channel
```

This taxonomy matters because the schemes are not interchangeable stabilizers.
DCCD can damp nodal oscillations but does not provide face-locus consistency.
UCCD6 preserves bulk high-order momentum transport through internal Nyquist-band
dissipation.  FCCD changes the output locus rather than adding damping.

## Consequences

- DCCD is an outer correction and can need separate conservation repair.
- DCCD is deliberately disabled near the interface by `S(psi)`.
- UCCD6 is suited to smooth/bulk velocity transport, not kinked `psi`.
- FCCD is selected when face-centered flux identity is the contract.
- Scheme choice must specify both smoothness class and output locus.

## Paper-Derived Rule

Do not describe all CCD derivatives as "high-order with some damping"; name the
dissipation channel and the output locus.
