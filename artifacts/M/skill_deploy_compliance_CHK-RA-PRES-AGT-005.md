# Skill Deploy Compliance Audit - CHK-RA-PRES-AGT-005

## Question
User asked whether skills, JSON, scripts, and related support artifacts are deployed from the metaprompt rather than hand-synchronized.

## Initial Finding
Not fully.

Before this pass, `scripts/deploy_codex_agents.py` generated:
- `prompts/agents-codex/*.md`
- `prompts/agents-codex/_base.yaml`
- `prompts/skills/SKILL-PROMPT-AUDIT.md`
- JSON/Markdown deploy reports under `artifacts/P/`

It did not regenerate all `prompts/skills/*.md`. The presentation deck skill had been manually synchronized with the kernel changes, so strict project-local-generation compliance was incomplete.

## Fix
- Added `<skill_capsule_specs>` to `prompts/meta/kernel-deploy.md`.
- Updated `scripts/deploy_codex_agents.py` to parse that metaprompt block and regenerate all `prompts/skills/*.md`.
- Removed the hardcoded `SKILL-PROMPT-AUDIT` body from the script.
- Added `skill_capsule_generation_report.json`.
- Added `skill_capsule_source` and `skill_capsules_generated` fields to `schema_resolution_report.json`.
- Added a Q3 audit row proving skill regeneration from `kernel-deploy` specs.
- Removed the hardcoded CHK-specific report directory; the script now infers the active report id from `docs/02_ACTIVE_LEDGER.md` or accepts `--report-id`.

## Evidence
- `python3 scripts/deploy_codex_agents.py` prints:
  - `Generated 25 Codex agents into prompts/agents-codex`
  - `Generated 9 skill capsules into prompts/skills`
  - `Reports written to artifacts/P/codex_overwrite_deploy_CHK-RA-PRES-AGT-005`
- `artifacts/P/codex_overwrite_deploy_CHK-RA-PRES-AGT-005/skill_capsule_generation_report.json`:
  - status `PASS`
  - source `prompts/meta/kernel-deploy.md <skill_capsule_specs>`
  - generated_count `9`
  - extra_files `[]`
  - missing_files `[]`
- `artifacts/P/codex_overwrite_deploy_CHK-RA-PRES-AGT-005/q3_audit_report.md` records:
  - `Skill capsules | PASS: 9 prompts/skills/*.md regenerated from kernel-deploy skill_capsule_specs`

## Validation
- `python3 -m py_compile scripts/deploy_codex_agents.py`: PASS
- `python3 scripts/deploy_codex_agents.py`: PASS
- Re-running deploy after commit left the worktree clean: PASS
- `git diff --check`: PASS
- `prompts/skills/*.md`: 9 files
- `prompts/agents-codex/*.md`: 25 files

## Scope Boundary
The deploy helper script itself is the local generator. It is now governed by `kernel-deploy.md`, reads metaprompt sources, regenerates agents/skills/reports, and no longer embeds generated skill bodies or CHK-specific report paths. This pass does not introduce a second-stage bootstrap script that regenerates `scripts/deploy_codex_agents.py` itself from an embedded script template; that would be a separate meta-bootstrap layer if required.

## Verdict
PASS for the practical deployment contract: skills and JSON reports are now reproducibly generated from the metaprompt bundle, and the deploy script no longer requires manual skill-body or report-directory edits.
