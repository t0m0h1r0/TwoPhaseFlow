# SKILL-PROMPT-AUDIT

id: SKILL-PROMPT-AUDIT
purpose: Audit generated prompt-system artifacts for Q3 compliance, local generation boundary, rule bloat, JIT discipline, and token ROI.
trigger:
- PromptAuditor receives generated prompt artifacts
- EnvMetaBootstrapper Stage 4
- AP-13 suspicion
minimal_instruction: Verify Q3 items, reject copied upstream generated artifacts, reject duplicated operation bodies and broad preloading, and require SkillID/RULE_MANIFEST references where full text has weak ROI.
full_ref: prompts/meta/kernel-deploy.md §Stage 4
input_contract:
- generated agent prompt paths
- prompts/skills paths
- git diff proving upstream copied kernel only
- token_telemetry_report.json
forbidden_context:
- PromptArchitect reasoning
- previous generated prompt transcripts
- unlisted draft prompts
success_metric:
- Q3 8-item verdict
- duplicate-rule scan recorded
- upstream-boundary verdict recorded
- prompt-load ROI verdict recorded
- token telemetry gate result recorded
token_target: 150
