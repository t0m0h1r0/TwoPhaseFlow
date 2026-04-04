# AlgorithmSpecs — T→L Interface Contract Template
# GENERATED — do NOT edit directly. Edit prompts/meta/*.md and regenerate.
# Status: {pending} — awaiting T-Domain pipeline execution

IF-AGREEMENT:
  feature:      "{algorithm_name} — discretization specification"
  domain:       Theory → Library
  gatekeeper:   ConsistencyAuditor (Theory Auditor)
  specialist:   CodeArchitect
  inputs:
    - theory/derivations/{derivation_id}.md: validated derivation artifact
    - docs/01_PROJECT_MAP.md §6: symbol conventions
  outputs:
    - src/twophase/{module}.py: implementation matching spec
    - tests/test_{module}.py: MMS tests N=[32,64,128,256]
  success_criteria: "TestRunner PASS; convergence order matches theoretical order"
  created_at:   {pending}

## Symbol Mapping Table

| Paper Notation | Variable Name | Type | Description |
|---------------|---------------|------|-------------|
| (to be filled by SpecWriter) | | | |

## Discretization Recipe

| Property | Value |
|----------|-------|
| Method | (to be filled) |
| Order | (to be filled) |
| Stencil | (to be filled) |
| Boundary Treatment | (to be filled) |
