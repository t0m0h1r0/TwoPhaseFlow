---
ref_id: WIKI-X-054
title: "Ch14 Active-Geometry Capillary Session Synthesis"
domain: cross-domain
status: ACTIVE
tags: [ch14, active_geometry_capillary, ao_fast, capillary_wave, rca, graph_hfe, gpu, nonuniform_grid, grid_rebuild, paper_trace]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
    description: "Long-session CHK ledger for CHK-RA-CH14-CAPILLARY-AO-RCA through CHK-RA-CH14-AO-FASTVOL-074 and follow-up U12/V11 paper update"
  - path: docs/wiki/cross-domain/WIKI-X-051.md
    description: "Mandatory zero-base theory-first RCA and countermeasure protocol"
  - path: docs/wiki/cross-domain/WIKI-X-052.md
    description: "Trial ledger for AO-Fast capillary moving-grid failures and falsified shortcuts"
  - path: docs/wiki/cross-domain/WIKI-X-053.md
    description: "Boundary-constrained face-state RCA and phase-separated PPE + HFE/DC preservation rule"
  - path: docs/wiki/theory/WIKI-T-172.md
    description: "Moving-grid face-cochain and pressure-history contract"
  - path: docs/wiki/theory/WIKI-T-173.md
    description: "Literature-survey-backed capillary-wave route"
  - path: docs/wiki/code/WIKI-L-043.md
    description: "GPU transfer-boundary minimization"
  - path: docs/wiki/code/WIKI-L-044.md
    description: "Finite-stratum fusion and explicit reuse flow for post-transfer GPU acceleration"
  - path: docs/wiki/code/WIKI-L-046.md
    description: "Theory-established implementation review gate"
  - path: docs/wiki/experiment/WIKI-E-063.md
    description: "Current U12/V11 active-geometry capillary split gates"
  - path: docs/wiki/paper/WIKI-P-019.md
    description: "Chapter 14 active-geometry capillary benchmark paper contract"
  - path: experiment/ch12/exp_U12_ao_capillary_split_gate.py
    description: "Updated U12 graph-HFE/grid contract gate"
  - path: experiment/ch13/exp_V11_ao_capillary_split_gate.py
    description: "Updated V11 integration gate"
  - path: paper/sections/12u12_ao_capillary_split_gate.tex
    description: "Papered U12 additional/retrial experiment results"
  - path: paper/sections/13e2_ao_capillary_split_gate.tex
    description: "Papered V11 additional/retrial experiment results"
depends_on:
  - "[[WIKI-X-050]]"
  - "[[WIKI-X-051]]"
  - "[[WIKI-X-052]]"
  - "[[WIKI-X-053]]"
  - "[[WIKI-T-171]]"
  - "[[WIKI-T-172]]"
  - "[[WIKI-T-173]]"
  - "[[WIKI-L-043]]"
  - "[[WIKI-L-044]]"
  - "[[WIKI-L-046]]"
  - "[[WIKI-E-063]]"
  - "[[WIKI-P-019]]"
consumers:
  - domain: code
    usage: "Start here before changing active-geometry capillary, graph HFE, PPE/DC, grid rebuild, or GPU paths"
  - domain: experiment
    usage: "Use as the short diagnostic checklist before rerunning ch14 capillary-wave experiments"
  - domain: paper
    usage: "Use to keep Chapters 1--14 theory, component tests, integration gates, and benchmark claims aligned"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Ch14 Active-Geometry Capillary Session Synthesis

## Knowledge Card

This session converted the provisional AO-Fast capillary work into the current
**active-geometry capillary** contract.  The main lesson is that the problem was
not one missing numerical trick.  It was a chain of discrete-object mismatches:
the surface-energy owner, pressure reaction space, HFE affine context, moving
grid face cochain, boundary face space, and GPU execution boundary all had to
refer to the same finite-dimensional object.

When this route fails, do not start by tuning CFL, damping, smoothing,
iteration caps, tolerances, or solver family.  First run the zero-base
theory-first protocol from [[WIKI-X-051]], then check this session contract:

```text
q-owned graph endpoint
  -> graph HFE pressure jump on the current interface
  -> phase-separated PPE + HFE/DC with matching high/low-order coefficients
  -> pressure-reaction / projection face cochain in the same Hodge metric
  -> interface-following grid rebuild that transports the projected face cochain
  -> boundary-constrained face state compatible with the published nodal state
  -> GPU-resident implementation with explicit, batched scalar transfer boundaries.
```

Each arrow is a possible root cause.  A local patch that checks only the
modified file is not a valid review.

## Final Contract

The current capillary-wave route is not the old CLS result and not the old
full-pressure-image AO packet.  The current route is:

- YAML selects the user-facing scheme `active_geometry_capillary`; internal
  names such as `geometric_cell_fraction` are not YAML front doors.
- The phase coordinate is `q`; for `gauge_reconstruction: column_height_graph`
  the capillary endpoint is the column-height graph, not generic P1 cut-cell
  surface work.
- The graph surface energy is differentiated in the column heights and pulled
  back to the single cut cell in each column.  The HFE jump uses the current
  graph cut `psi_G=h_G(q)-y`.
- The graph HFE pressure jump is a current affine PPE boundary condition, not a
  smooth pressure-history coordinate.
- Phase-separated PPE + HFE/DC remains the base route.  HFE is not optional
  when instability appears.
- DC is accepted by convergence, not by a fixed iteration count.  The low-order
  DC base must use the same affine cut-face phase resistance as the high-order
  FCCD operator.
- A neutral zero-jump affine context is still context: `j=0` removes only the
  RHS contribution, while `psi` is still required for cut-face coefficients.
- Moving-grid updates must transport the projection-native face cochain across
  grid epochs.  Reconstructing projected flow from nodal velocity after rebuild
  is a different mathematical object.
- Boundary-constrained face state must match the published no-slip nodal
  velocity.  Mixing no-slip nodes with no-penetration-only faces is a
  mixed-complex bug.
- GPU optimization must preserve the above contracts.  Low utilization on small
  grids is not proof of CPU fallback; hidden D2H/H2D and fixed-loop geometry
  work must be measured before retuning the algorithm.

## RCA Order

For future capillary failures, collect and falsify hypotheses in this order:

1. **Theory object identity.**  Which object is being compared: nodal field,
   cell pressure, graph height, face cochain, HFE jump, or pressure-history
   coordinate?
2. **Endpoint ownership.**  Does YAML-selected `q`/graph tracking use graph
   surface energy, or did the code accidentally use generic P1 cut geometry?
3. **Nonuniform/rebuild contract.**  Are physical widths, face lengths, Hodge
   weights, and grid epoch invalidations used on every path?
4. **Pressure/HFE operator consistency.**  Do high-order FCCD and low-order DC
   base assemble the same affine cut-face coefficient and RHS context?
5. **Pressure history.**  Is only the smooth pressure coordinate stored, with
   the current HFE jump reintroduced at the face law?
6. **Boundary face state.**  Do nodal publication, stored face state, PPE RHS,
   corrector, and remap all live in the same constrained face space?
7. **GPU residency.**  Are reductions batched, sparse analysis reused
   explicitly, and fail-close checks separated from per-element compute?
8. **Physical benchmark.**  Only after the above pass should long capillary
   runs be interpreted as physics.

This ordering is the session's biggest time saver.  Most false starts came from
checking a late symptom before proving the discrete object identity.

## Additional Experiments That Closed the Gap

The old U12/V11 gates proved that full pressure-image splitting can erase a
non-static capillary drive.  They did not prove the current graph-HFE route.
The session therefore added/retried the following gates:

| Gate | Observation | Meaning |
|---|---|---|
| U12 pressure split | N32/N64 full-pressure exact split gives balanced drive `0`; component-volume Hodge diagnostic gives `2.1176/2.3055`. | Full pressure image is an overprojection counterexample, not a success route. |
| Graph HFE jump | On nonuniform `x`, `||j||_inf=11.5323`, weighted mean `1.30e-16`, crest sign negative. | The graph jump has the right conservation/sign contract. |
| HFE history separation | Graph jump returns no pressure-coordinate history base. | Current discontinuous jump is not transported as smooth history. |
| HFE admission | With `dt=1e-8`, increment norm `1e-14`, spatial drive `1e-6`, non-static HFE is admitted. | Admission is a spatial-drive contract, not a CFL-sized increment test. |
| Regular stratum | Nearly horizontal graph moves `y` by `2.50e-3` and leaves `x` shift exactly `0`. | Grid retreat follows the dominant normal direction and does not squeeze tangential cells. |
| V11 split-pending | GPU packet stops at split-pending while retaining non-static drive (`O(1e-5)`). | The boundary is no longer old fail-close; it is a guarded handoff to the admitted production split. |

These results belong in Chapters 12--13 because they are component/integration
admission gates.  Chapter 14 should cite them as prerequisites, not re-prove
them inside the benchmark narrative.

## GPU Lessons

The successful GPU optimization strategy was:

- eliminate or batch D2H/H2D scalar transfers first;
- keep all active-geometry, graph-HFE, nonuniform metric, and grid-rebuild
  operations backend-native;
- fuse finite-stratum operations only after their discrete object contract is
  fixed;
- manage repeated sparse/factor analysis as an explicit reuse flow, not an
  invisible cache that can survive a wrong grid/density/phase epoch;
- fail closed when required context is missing instead of falling back to CPU,
  dense runtime, smooth coefficients, or old pressure routes;
- verify numerical results before interpreting utilization numbers.

Do not optimize by disabling nonuniform grids, disabling interface-following
rebuilds, weakening convergence gates, or changing physical parameters.

## Paper Trace

The final paper update must maintain this mapping:

```text
Chapters 1--11: theory, equations, and final active-geometry scheme
Chapter 12: component gates, especially U12 graph-HFE and split counterexample
Chapter 13: integration gates, especially V11 split-pending + graph-HFE contracts
Chapter 14: physical benchmark using the already-admitted route
```

If a future edit changes the implementation route, update the earlier chapters
and U12/V11 gates before changing Chapter 14 claims.  A Chapter 14 plot alone is
not enough evidence that the theory contract still holds.

## Negative Knowledge

The session explicitly rejected these shortcuts:

- micro-offsets such as moving the interface by `1e-10`;
- GMRES, monolithic FD, non-HFE pressure handling, or hidden fallback as a
  production fix;
- fixed DC iteration counts in place of convergence gating;
- treating pressure magnitude plots, masked pressure, or raw interface-band
  pressure as the physical pressure representative;
- assuming low GPU utilization means the route is CPU-bound without transfer
  and launch diagnostics;
- assuming a static/no-rebuild run proves the moving-grid route;
- using old CLS or old full-pressure AO results as evidence for the current
  active-geometry capillary result;
- letting YAML expose internal implementation stacks instead of user-owned
  scheme, solver policy, tolerances, and initial/boundary conditions.
