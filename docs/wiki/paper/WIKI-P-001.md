---
ref_id: WIKI-P-001
title: "Paper Narrative Structure: Sections 4-10 Flow Analysis"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/04_ccd.tex
    git_hash: 7328bf1
    description: "Section 4 opening, roadmap, CCD motivation"
  - path: paper/sections/05_grid.tex
    git_hash: 7328bf1
    description: "Section 5 opening, grid design"
  - path: paper/sections/06_time_integration.tex
    git_hash: 7328bf1
    description: "Section 6 time integration framework"
  - path: paper/sections/07_advection.tex
    git_hash: 7328bf1
    description: "Section 7 CLS advection, scheme roles table"
  - path: paper/sections/08_collocate.tex
    git_hash: 7328bf1
    description: "Section 8 P-V coupling, Balanced-Force"
  - path: paper/sections/09_ccd_poisson.tex
    git_hash: 7328bf1
    description: "Section 9 PPE solver"
  - path: paper/sections/10_full_algorithm.tex
    git_hash: 7328bf1
    description: "Section 10 full algorithm assembly"
consumers:
  - domain: A
    usage: "PaperWriter uses this for structural revision guidance"
depends_on: []
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Overall Arc: Tool -> Application -> Assembly

The paper follows a clear three-phase progression:

1. **Tool Design** (S4-S5): CCD engine + operating environment (grid)
2. **Integration Framework** (S6-S7): Time advancement + first CCD deployment (CLS)
3. **Pressure System + Assembly** (S8-S10): P-V coupling theory, PPE solver, full algorithm

## Chapter-to-Chapter Bridge Quality

| Transition | Quality | Issue |
|-----------|---------|-------|
| S4 internal (CCD->BC->DCCD) | Good | Roadmap compensates for missing inter-subsection bridges |
| S4 -> S5 | Good | Forward reference in S4 opening explicitly defers grid to S5 |
| S5 internal (grid->transform) | Good | One redundancy: duplicate opening paragraphs (lines 6-13) |
| S5 -> S6 | **WEAK** | No transition paragraph; ends on ALE modes, jumps to time integration |
| S6 internal | Good | TVD-RK3 -> AB2+IPC -> accuracy table -> CN; logical flow |
| S6 -> S7 | **MISSING** | Ends on CN Thomas detail; no forward pointer to spatial discretization |
| S7 internal (advection->reinit) | Good | Intro lists 3 sub-topics; DCCD reuse from advection to compression |
| S7 -> S8 | **MISSING** | Ends on capillary CFL; no bridge to P-V coupling theory |
| S8 internal | Good | Problem -> Helmholtz -> Projection -> BF -> DCCD; strong logic |
| S8 -> S9 | **STRONG** | Explicit closing paragraph connects four elements to PPE |
| S9 internal | Good | CCD-PPE -> DC solver -> BC -> accuracy summary; well-structured |
| S9 -> S10 | Implicit | Summary box ends with future outlook, not explicit bridge |
| S10 internal | Good | Operator map -> 7-step flow -> bootstrap -> DCCD params |

## Identified Issues (6 items)

### ISSUE-1: S5->S6 Bridge (Medium)
S5 ends on grid modes (Mode 1/Mode 2 ALE). S6 opens with "spatial O(h^6) needs matching temporal accuracy." Missing: a bridge connecting grid-dependent CFL constraints to time integration design choices.

**Recommendation**: Add 2-3 sentence bridge at end of S5 or opening of S6 connecting grid Jacobian / non-uniform spacing to CFL and time-step constraints.

### ISSUE-2: S6->S7 Bridge (Medium)
S6 closes on CN tridiagonal Thomas algorithm. S7 opens with "apply CCD to physical terms." Missing: "having established the time framework, we detail the spatial operators that plug into it."

**Recommendation**: Add closing paragraph to S6: "With the temporal skeleton established (TVD-RK3 for CLS, AB2+IPC+CN for NS), the next three sections detail the spatial discretization of each physical term."

### ISSUE-3: S7->S8 Bridge (Medium)
S7b ends on capillary CFL mitigation. S8 opens with collocated grid theory. Missing motivation: "Now that we can track the interface, we need pressure to advance velocity."

**Recommendation**: Add closing paragraph to S7b: "Sections 4-7 established CCD, grid, time integration, and CLS advection. The remaining bottleneck is pressure-velocity coupling."

### ISSUE-4: S6 Forward References to S7 (Low)
S6 references eq:dccd_adv_filter and alg:dccd_adv (defined in S7). Reader encounters time integrator before learning what spatial operator L(psi) is. Consider adding a brief note: "the spatial operator L is detailed in S7."

### ISSUE-5: Pressure Filter Prohibition Placement (Low)
`08c_pressure_filter.tex` sits between S8 and S9. Content logically belongs after S9 (PPE solver) where the reader understands what "solving PPE" means. Currently feels orphaned.

**Recommendation**: Move to end of S9, or add a one-line bridge: "Before proceeding to the PPE solver, we establish a critical constraint on filter application."

### ISSUE-6: DCCD Cross-Reference Scatter (Medium)
DCCD appears in S4 (definition), S7 (CLS advection), S8 (checkerboard), S10 (parameter design) with three distinct parameter regimes. The scheme_roles table in S7 partially addresses this but precedes S8-S9 content.

**Recommendation**: Add a consolidated DCCD usage map table in S10 (near sec:dccd_params), cross-referencing all three modes. See [[WIKI-X-001]].

## Structural Anomalies

- **File 05b header says "04c"**: Naming inconsistency; CCD extensions placed in S5 but conceptually S4 material
- **Duplicate opening in 05_grid.tex**: Lines 6-8 and 10-13 are near-identical; delete one
- **DC k=1 stated 6 times**: Redundant across S9 intro, S9.3, S9.5, S9 summary, S10 Step 6, S10 Step 6 detail; 3 mentions suffice
- **Accuracy table in S9d omits density-ratio limitation**: kappa(L_h) = O(rho_l/rho_g / h^2) divergence at rho_l/rho_g >= 10 not noted in tab:accuracy_summary
- **C/RC-DCCD (eq:crc_dccd)**: Defined in S8 but not referenced in S10 algorithm flow; clarify if active or theoretical only
