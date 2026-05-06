# Prompt Redeploy Required

Shared research-agent metaprompt assets were synced from upstream.

Generated skills, templates, scripts, and agent prompts were not copied.
Before using the changed prompt system, rerun the project-local deployment process so
`prompts/meta/kernel-project.md` is applied to generated agents and runtime
docs. Then run prompt audit checks and remove this marker in the same
project commit that records the successful redeploy.

Upstream revision: `c985b65`
