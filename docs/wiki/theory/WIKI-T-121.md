---
ref_id: WIKI-T-121
title: "Face Jet Is a Public Contract, Not a Current Implementation Detail"
domain: theory
status: ACTIVE
superseded_by: null
tags: [face_jet, api_contract, fccd, hermite, architecture]
sources:
  - path: paper/sections/04f_face_jet.tex
    description: "Face jet design consequences and public API contract"
depends_on:
  - "[[WIKI-T-069]]"
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-120]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# FaceJet API Contract

## Knowledge Card

The paper treats FaceJet as a public interface:

```text
input consumers ask for (u_f, u'_f, u''_f) on the face
implementation may currently reuse CCD node outputs
future implementation may promote face quantities to independent unknowns
```

The key is that downstream pressure, HFE, flux, and BF consumers see the same
face-located tuple.  The current additive construction is replaceable as long
as the face contract remains stable.

## Consequences

- Callers should depend on the face tuple, not on the internal reconstruction
  path.
- Reimplementing the backend must preserve face location and component meaning.
- API stability is what lets pressure/CSF/HFE share a common locus.
- Applying the tuple directly to discontinuous raw fields violates the smooth
  field assumption behind the contract.

## Paper-Derived Rule

Keep FaceJet as the stable shared face API; allow backend changes only if they
preserve the same face-located Hermite contract.
