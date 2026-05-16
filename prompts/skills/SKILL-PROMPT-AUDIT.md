# SKILL-PROMPT-AUDIT

id: SKILL-PROMPT-AUDIT
purpose: Audit generated prompts/skills for source fidelity, role scope, token ROI, wiki injection, and convergence propagation.
trigger:
- generated agent prompt changed
- Skill Capsule manifest changed
- EnvMetaBootstrapper Stage 4 validation
- prompt bloat, stale wiki policy, copied upstream artifact concern, or ARTIFACT-CONVERGENCE adapter change
minimal_instruction: Run Stage 4 plus Q3-AUDIT Q3-01..Q3-16. Reject copied generated artifacts, duplicated operation bodies, broad preloading, stale/wiki prose injection, role-scope leakage, and token-target overruns.
full_ref: prompts/meta/kernel-deploy.md §Stage 4
input_contract:
- generated agent/skill paths
- token_telemetry_report.json and token_roi_report.json
- wiki_knowledge_injection_report.json or waiver
forbidden_context:
- copied upstream generated artifacts
- full operation bodies where JIT refs exist
- broad skill/wiki preloading
- role-specific artifacts required outside their role/domain
- token-target overrun without recorded ROI justification
success_metric:
- Q3-AUDIT and AP-13/AP-17 PASS
- token telemetry and token ROI PASS
- no stale generated artifacts or role leakage
token_target: 180
