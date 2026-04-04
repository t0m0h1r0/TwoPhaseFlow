# TechnicalReport — T/E→A Interface Contract Template
# GENERATED — do NOT edit directly. Edit prompts/meta/*.md and regenerate.
# Status: {pending} — awaiting T-Domain + E-Domain joint signing

IF-AGREEMENT:
  feature:      "Technical report bridging theory and experiment for paper writing"
  domain:       Theory + Experiment → Academic Writing
  gatekeeper:   ConsistencyAuditor (T-Auditor) + CodeWorkflowCoordinator (Validation Guard)
  specialist:   PaperWriter
  inputs:
    - interface/AlgorithmSpecs.md: validated theory specification
    - interface/ResultPackage/: validated experiment results
  outputs:
    - paper/sections/*.tex: manuscript content
  success_criteria: "PaperReviewer 0 FATAL + 0 MAJOR; PaperCompiler BUILD-SUCCESS"
  created_at:   {pending}

## Theory Summary
(to be filled by T-Domain after AlgorithmSpecs.md is signed)

## Experiment Summary
(to be filled by E-Domain after ResultPackage/ is signed)

## Key Results for Paper
(to be filled jointly — bridges math formulation and empirical data)
