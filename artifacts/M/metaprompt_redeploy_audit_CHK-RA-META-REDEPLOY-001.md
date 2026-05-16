# CHK-RA-META-REDEPLOY-001 — Metaprompt Redeploy Audit

## Scope

User request: redeploy Codex agents and related support artifacts from the
metaprompt source, inspect the deployed outputs, and update the metaprompt if
problems or concerns are found.

Write scope:

- `prompts/meta/kernel-deploy.md`
- `prompts/meta/kernel-roles.md`
- `scripts/deploy_codex_agents.py`
- generated `prompts/agents-codex/*`
- generated `prompts/skills/*`
- deploy reports under `artifacts/P/codex_overwrite_deploy_CHK-RA-META-REDEPLOY-001/`
- ledger entry in `docs/02_ACTIVE_LEDGER.md`

No production solver, experiment, paper, physical parameter, result, or main
merge scope was touched.

## Redeploy Result

Command:

```text
python3 scripts/deploy_codex_agents.py
```

Generated:

- 25 Codex agents in `prompts/agents-codex/`
- 9 Skill Capsules in `prompts/skills/`
- reports in `artifacts/P/codex_overwrite_deploy_CHK-RA-META-REDEPLOY-001/`

Report status:

- `schema_resolution_report.json`: PASS
- `token_telemetry_report.json`: PASS
- `token_roi_report.json`: PASS
- `skill_capsule_generation_report.json`: PASS
- `wiki_knowledge_injection_report.json`: PASS
- `q3_audit_report.md`: Q3-01..Q3-16 PASS, AP-13 PASS, AP-17 PASS

Token ROI:

- max agent static prompt: `ResearchArchitect.md` 301 / 320
- max skill: `SKILL-PRESENTATION-DECK` 377 / 460

## Issues Found and Repaired

### MRD-001 — Stale generated deployment version

Severity: Medium

Problem:

- Generated agent headers, `_base.yaml`, and telemetry used a hard-coded
  `8.2.0-candidate` value even though current metaprompt operation sections
  include `8.7.0-candidate`.

Impact:

- Behavior still deployed, but provenance was stale. Future audit could not
  reliably tell whether a generated prompt came from the current metaprompt
  kernel or an older deployment.

Fix:

- `scripts/deploy_codex_agents.py` now derives deployment `VERSION` from the
  maximum version found in `prompts/meta/kernel-*.md`.
- `token_telemetry_report.json` records `version_source`.
- `schema_resolution_report.json` records `deployment_version` and
  `deployment_version_source`.
- `q3_audit_report.md` records a Version provenance PASS row.
- `prompts/meta/kernel-deploy.md` now requires generated prompts and telemetry
  to record a metaprompt-derived deployment version.

Validation:

- Generated headers now use `8.7.0-candidate`.
- `_base.yaml` uses `meta_version: "8.7.0-candidate"`.
- Reports record `deployment_version: "8.7.0-candidate"`.

Status: Resolved

### MRD-002 — PromptAuditor deliverable referenced old Q3 count/version

Severity: Medium

Problem:

- `PromptAuditor` deliverables still said `15 items v8.2.0-candidate`, while
  the current Q3 audit has 16 items.

Impact:

- A generated auditor prompt could under-audit Q3-16 Token ROI or treat the
  current checklist as an older version.

Fix:

- `prompts/meta/kernel-roles.md` now says PromptAuditor reports PASS/FAIL per
  current `kernel-deploy.md` item, plus Skill Capsule, WikiKnowledgePacket,
  Token Telemetry/ROI, and version-provenance audits.

Validation:

- Regenerated `prompts/agents-codex/PromptAuditor.md` contains the new dynamic
  wording.
- Targeted stale scan for `15 items`, `Q3-AUDIT ... 8.2`, and generated
  `8.2` headers returned no matches.

Status: Resolved

## Generated-Output Audits

Checks run after the repairs and final redeploy:

- JSON status scan for schema, telemetry, ROI, skill generation, and wiki
  injection reports: PASS
- agent count: 25
- skill count: 9
- generated version provenance: PASS (`8.7.0-candidate`)
- stale generated version scan: PASS
- Code/Paper generated-prompt scan for presentation-only artifacts
  (`audience_profile`, `story_map`, `slide_spec`, `slide 2`, `review_plan`,
  `issue_register`, `convergence_dashboard`): PASS
- shared metaprompt project-leakage scan outside `kernel-project.md`
  (`src/twophase`, `experiment/ch*`, `TwoPhaseFlow`, `make cycle`, `ch11`,
  `ch13`, `ch14`): PASS
- role manifest spot-check:
  - `CodeArchitect`: `SCHEME-CODE-01`, no presentation adapter
  - `PaperWriter`: `PAPER-WRITE-01`, no presentation adapter
  - `PresentationWriter`: `PRESENTATION-GEN-01`, `VISUAL-CONCEPT-01`
  - `PaperReviewer`: paper + presentation review adapters by design
  - `PromptAuditor`: Q3/Wiki/token audit prompt rules only
- `python3 -m py_compile scripts/deploy_codex_agents.py`: PASS
- `git -C prompts/meta diff --check`: PASS

Notes:

- Anti-pattern names such as `AP-17 ... (v8.2.0-candidate)` remain as
  historical introduction labels. They are not deployment-version headers and
  are not considered stale generated provenance.

## Verdict

After two repair cycles, no unresolved generated-output issue remains in this
redeploy pass. The deployed artifacts are compact, source-derived, role-scoped,
and report their current metaprompt provenance.
