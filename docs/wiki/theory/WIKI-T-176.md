---
ref_id: WIKI-T-176
title: "PhaseRegion-Primary InterfaceAtlas for Multi-Component Ch14 Capillarity"
domain: theory
status: ACTIVE
tags: [ch14, phase_region, interface_atlas, multi_component, rising_bubble, capillary]
sources:
  - path: artifacts/A/ch14_phase_region_atlas_theory_CHK-RA-CH14-VAR-015.md
    description: "PhaseRegion/InterfaceAtlas ownership lift and force-gate implications"
depends_on:
  - "[[WIKI-T-174]]"
  - "[[WIKI-T-175]]"
  - "[[WIKI-E-068]]"
consumers:
  - domain: theory
    usage: "Use before force-coupling theory or multi-component interface design"
  - domain: code
    usage: "Use before adding InterfaceAtlas or PhaseRegion abstractions"
  - domain: experiment
    usage: "Use before rising-bubble/top-layer probes or T/8 admission"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# PhaseRegion-Primary InterfaceAtlas for Multi-Component Ch14 Capillarity

## Knowledge Card

Lift ownership from a single interface chart to the phase region:

```text
Omega_h owner -> InterfaceAtlas(boundary Omega_h)
              -> q_phys = Q_h(Omega_h)
              -> r = q_T - q_phys
```

Graph and closed-curve charts remain valid, but only as one-component atlas
charts.  The final abstraction must also support multi-component regions such
as a rising bubble plus a top gas layer:

```text
Omega_g = Omega_bubble ∪ Omega_layer
Gamma   = boundary Omega_g
```

Surface energy is still one principle:

```text
E[Omega_g] = sigma Perimeter(Omega_g)
```

## Usage

Use this card before any force-coupling probe.  If topology, boundary
attachment, orientation, and volume-constraint policy are not represented,
force admission must remain closed.

The existing graph/closed q-manifold helpers are not invalidated.  They are
restricted chart gates inside the broader `PhaseRegion/InterfaceAtlas` theory.

## Next Gate

Add an atlas design or smoke oracle for:

```text
Omega_g = Omega_closed_bubble ∪ Omega_top_layer
```

The oracle should report component topology, boundary attachment, orientation,
total phase volume, optional component volumes, perimeter sum, and residual
split.  It must not run T/8 or connect production force.
