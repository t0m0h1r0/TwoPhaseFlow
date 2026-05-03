# SKILL-PROMPT-AUDIT

id: SKILL-PROMPT-AUDIT
purpose: Audit generated prompts for Q3 compliance, rule bloat, and JIT discipline.
trigger:
- PromptAuditor receives generated prompt artifacts
- EnvMetaBootstrapper Stage 4
- AP-13 suspicion
minimal_instruction: Verify Q3 items, reject duplicated operation bodies, and require SkillID or RULE_MANIFEST references where full text is unnecessary.
full_ref: prompts/meta/kernel-deploy.md §Stage 4
input_contract:
- generated agent prompt paths
- prompts/skills paths
- token_telemetry_report.json
forbidden_context:
- PromptArchitect reasoning
- previous generated prompt transcripts
- unlisted draft prompts
success_metric:
- Q3 13-item verdict
- duplicate-rule scan recorded
- token telemetry gate result recorded
token_target: 160
