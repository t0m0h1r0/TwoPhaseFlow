# Generated Prompt ROI Audit - CHK-RA-META-AUDIT-002

## Scope
- User request: repeat metaprompt audit for redundancy, contradictions, role scope, project-specific leakage, and explicitly audit deployed agents/skills for token waste and ROI.
- Target sources: `prompts/meta/*.md`, `scripts/deploy_codex_agents.py`.
- Target generated outputs: `prompts/agents-codex/*.md`, `prompts/skills/*.md`, deploy reports under `artifacts/P/codex_overwrite_deploy_CHK-RA-META-AUDIT-002/`.
- Main merge: not performed.

## Issue Register

| ID | Severity | Category | Finding | Risk | Fix |
|---|---|---|---|---|---|
| MP-ROI-001 | High | Token ROI | `SKILL-PRESENTATION-DECK.md` is 816 tokens against `token_target: 460`. | The skill duplicates details already available through `full_ref`, wasting default context and weakening progressive disclosure. | Compress the skill spec in `kernel-deploy.md` to adapter triggers, compact contracts, and JIT pointers while preserving critical behavior. |
| MP-ROI-002 | Medium | Token ROI | `SKILL-PROMPT-AUDIT.md` is 192 tokens against `token_target: 180`. | Small overrun signals that token targets are aspirational rather than checked. | Tighten wording and include skill-target checking in deploy ROI reports. |
| MP-ROI-003 | High | Deployment gate | Deploy reports include token telemetry, but no per-skill token-target enforcement or ROI verdict. | Future generated skills can exceed targets while Q3 still passes. | Add `token_roi_report.json`, Q3 token ROI row, and fail-fast behavior for over-target skills or over-large agent prompts. |

## Repair Plan
1. Update `prompts/meta/kernel-deploy.md` skill specs to reduce generated token load while keeping full behavior behind `full_ref`.
2. Update `scripts/deploy_codex_agents.py` to compute agent and skill ROI metrics, write `token_roi_report.json`, and make Q3 audit report include Token ROI.
3. Redeploy generated agents/skills using report id `CHK-RA-META-AUDIT-002`.
4. Rerun leakage, role-boundary, token-target, and deploy report validation.

## Repairs Applied

- `prompts/meta/kernel-deploy.md`
  - Compressed `SKILL-PRESENTATION-DECK` from a detailed always-loaded rule list to a compact adapter capsule; detailed behavior remains behind `full_ref: prompts/meta/kernel-ops.md §PRESENTATION-GEN-01`.
  - Compressed `SKILL-PROMPT-AUDIT` and updated it from Q3-01..Q3-15 to Q3-01..Q3-16.
  - Added Q3-16: generated agents and Skill Capsules must pass token ROI gates.
  - Required `token_roi_report.json` alongside `token_telemetry_report.json`.
- `scripts/deploy_codex_agents.py`
  - Added `AGENT_STATIC_PROMPT_LIMIT = 320`.
  - Added per-skill token count vs `token_target` and per-agent static prompt limit checks.
  - Emits `token_roi_report.json`.
  - Includes Token ROI in `q3_audit_report.md`.
  - Fails deploy when any generated skill or agent violates the token ROI gate.
- Regenerated 25 Codex agents and 9 Skill Capsules with report id `CHK-RA-META-AUDIT-002`.

## Validation

| Check | Result |
|---|---|
| `python3 scripts/deploy_codex_agents.py --report-id CHK-RA-META-AUDIT-002` | PASS |
| `token_roi_report.json` overall status | PASS |
| Maximum generated agent static prompt tokens | 301 / 320 |
| Maximum generated Skill delta over target | -27 (all under target) |
| `SKILL-PRESENTATION-DECK.md` token count | 377 / 460 |
| `SKILL-PROMPT-AUDIT.md` token count | 146 / 180 |
| Q3 audit | PASS Q3-01..Q3-16, AP-13, AP-17, Token ROI |
| Shared/generated project leakage scan | PASS |
| Code/paper prompt scan for presentation-specific artifact leakage | PASS |
| Paper-role RULE_MANIFEST boundary scan | PASS |
| `git -C prompts/meta diff --check` | PASS |
| `python3 -m py_compile scripts/deploy_codex_agents.py` | PASS |
| `git diff --check` | PASS |

## Final Issue Status

| ID | Status |
|---|---|
| MP-ROI-001 | Resolved |
| MP-ROI-002 | Resolved |
| MP-ROI-003 | Resolved |

## Residual Risk

- The agent static prompt limit is currently a project-local deploy-script constant (`320`). It is intentionally conservative for current generated prompts. If a future runtime has a different context budget, the limit should become an environment setting in the deployment profile rather than a hard-coded constant.

## Status
DONE. No open findings remain after the final targeted scans and ROI gate.
