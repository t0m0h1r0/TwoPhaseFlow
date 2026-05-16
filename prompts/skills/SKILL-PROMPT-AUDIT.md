# SKILL-PROMPT-AUDIT

id: SKILL-PROMPT-AUDIT
purpose: Audit generated prompts, skill capsules, wiki-packet injection, token telemetry, project-local generation boundaries, and ARTIFACT-CONVERGENCE propagation.
trigger:
- generated agent prompt changed
- Skill Capsule manifest changed
- EnvMetaBootstrapper Stage 4 validation
- prompt bloat, stale wiki policy, copied upstream artifact concern, or ARTIFACT-CONVERGENCE adapter change
minimal_instruction: Verify Stage 4 deployment checks plus Q3-AUDIT items Q3-01..Q3-15, reject copied upstream generated artifacts, reject duplicated operation bodies and broad preloading, require SkillID/RULE_MANIFEST/wiki-packet references where full text has weak ROI, fail AP-17 for stale or prose-heavy wiki injection, and reject presentation vocabulary leakage into code/paper prompts.
full_ref: prompts/meta/kernel-deploy.md §Stage 4
input_contract:
- generated agent prompt paths
- changed skill capsule paths
- token_telemetry_report.json or waiver
- wiki_knowledge_injection_report.json or waiver when docs/wiki exists
forbidden_context:
- generated prompts copied from upstream
- full operation bodies duplicated in role prompts
- broad skill-body preloading
- wiki prose copied into static prompts without source refs and packet status
- presentation-specific artifacts required in code or paper prompts
success_metric:
- Q3-AUDIT 15-item verdict
- AP-13/AP-17 verdict
- token telemetry PASS/WARN/FAIL
- wiki packet PASS/WARN/FAIL
- ARTIFACT-CONVERGENCE references appear where expected without stale generated artifacts
token_target: 180
