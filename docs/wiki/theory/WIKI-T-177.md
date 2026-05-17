---
ref_id: WIKI-T-177
title: "PhaseRegion Variational Axioms Before Ch14 Force Coupling"
domain: theory
status: ACTIVE
tags: [ch14, phase_region, interface_atlas, variational_axioms, force_gate, topology]
sources:
  - path: artifacts/A/ch14_phase_region_variational_axioms_CHK-RA-CH14-VAR-016.md
    description: "First-principles re-check of PhaseRegion ownership and force admission"
depends_on:
  - "[[WIKI-T-176]]"
  - "[[WIKI-E-068]]"
consumers:
  - domain: theory
    usage: "Use before force-coupling theory or atlas smoke-oracle design"
  - domain: code
    usage: "Use before adding PhaseRegion, InterfaceAtlas, or force-admission code"
  - domain: experiment
    usage: "Use before mixed bubble/layer probes, force-coupling probes, or T/8"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# PhaseRegion Variational Axioms Before Ch14 Force Coupling

## Knowledge Card

The theory reset gives six axioms:

1. Own a finite-dimensional `PhaseRegion`, not `phi` and not a bare `q`.
2. Derive `q_phys=Q_h(R_h)` from that region.
3. Compute `E_h` as perimeter of the same region.
4. Declare total/component volume constraints explicitly.
5. Admit force only through the production endpoint adjoint `T_h^*`.
6. Treat topology changes as theorem changes with an event ledger.

In short:

```text
R_h -> Q_h(R_h), E_h(R_h), C_h(R_h), T_h(R_h)
```

must be one object family.  A pretty `phi`, local PLIC fragments, or exact
cell `q` is not enough.

## Decision

Do not implement force coupling next.  First add a no-runtime atlas smoke
oracle for:

```text
R_h = closed bubble + top layer
```

It must report topology, attachment, orientation, phase ownership, volume
constraints, perimeter sum, residual split, and finite-difference `dE/dC`
checks.  Only after that can a force probe test the face-cochain work
identities.
