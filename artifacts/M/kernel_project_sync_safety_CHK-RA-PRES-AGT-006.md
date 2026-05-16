# Kernel Project Sync Safety Audit - CHK-RA-PRES-AGT-006

## Questions
1. Could syncing the `prompts/meta` submodule accidentally overwrite the user-authored `kernel-project.md`?
2. Is it documented that `kernel-project.md` is user-created/project-specific?
3. Is there guidance for what to write in `kernel-project.md`?

## Finding Before Fix
- Documentation did say `kernel-project.md` is project-specific, but it was not explicit enough about the submodule risk.
- Some docs could be read as ordinary `git submodule update --remote prompts/meta` being safe.
- `scripts/sync_research_agent.py` did not preserve `prompts/meta/kernel-project.md` explicitly.
- `scripts/deploy_codex_agents.py` consumed `prompts/meta/kernel-project.md`, but reports did not clearly state its user-owned overlay status.

## User Decision
The project profile remains at `prompts/meta/kernel-project.md`. It is not moved outside the submodule, because keeping it beside the kernel files is simpler to manage.

## Fix
- `scripts/sync_research_agent.py` now treats `prompts/meta/kernel-project.md` as the only allowed local submodule overlay:
  - aborts if other submodule files are dirty,
  - snapshots `kernel-project.md`,
  - restores the submodule file before update if needed,
  - updates the submodule,
  - restores the snapshot afterward.
- `prompts/meta/kernel-deploy.md` now states:
  - `prompts/meta/kernel-project.md` is the receiving project's user-owned project profile overlay,
  - sync helpers must preserve it,
  - deployment must never overwrite an existing file,
  - users edit it to retarget the project.
- `prompts/meta/README.md` now documents:
  - use the sync helper instead of bare submodule update,
  - `kernel-project.md` is user-authored,
  - required contents: project identity, PR-1..PR-6, path conventions, validation, remote/local policy, forbidden shortcuts, and portability notes.
- Root `README.md` now contains a visible Research-Agent Prompt System section with the same high-level contract.
- `scripts/deploy_codex_agents.py` now reports:
  - `project_kernel_source: prompts/meta/kernel-project.md`
  - `project_kernel_ownership: user-owned project overlay inside prompts/meta; sync helper preserves this file`

## Evidence
- `python3 scripts/sync_research_agent.py --dry-run` prints:
  - `Project-specific profile prompts/meta/kernel-project.md would be preserved across sync.`
- `python3 scripts/deploy_codex_agents.py` writes CHK-006 deploy reports.
- `artifacts/P/codex_overwrite_deploy_CHK-RA-PRES-AGT-006/schema_resolution_report.json` records:
  - `project_kernel_source`: `prompts/meta/kernel-project.md`
  - `project_kernel_ownership`: `user-owned project overlay inside prompts/meta; sync helper preserves this file`

## Answers
1. Bare submodule commands can still replace submodule worktree files, so the safe operation is the helper, not raw `git submodule update --remote`. With `scripts/sync_research_agent.py`, the project file is snapshotted and restored.
2. Yes, now root `README.md`, `prompts/meta/README.md`, and `kernel-deploy.md` explicitly say the file is user-authored/project-specific.
3. Yes, `prompts/meta/README.md` now lists the minimum contents and common fields.

## Validation
- `python3 -m py_compile scripts/deploy_codex_agents.py scripts/sync_research_agent.py`: PASS
- `python3 scripts/sync_research_agent.py --dry-run`: PASS
- `python3 scripts/deploy_codex_agents.py`: PASS
- `git diff --check`: PASS before commit

## Residual Risk
Users can still bypass the helper and run raw Git submodule commands manually. The docs now warn against this, and the helper is the intended path.

## Verdict
PASS. The project keeps `kernel-project.md` inside `prompts/meta/`, while the sync/deploy tooling and docs now treat it as a user-owned overlay that must be preserved.
