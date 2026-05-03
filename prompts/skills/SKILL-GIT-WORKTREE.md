# SKILL-GIT-WORKTREE

id: SKILL-GIT-WORKTREE
purpose: Keep git worktree, lock, commit, and no-ff merge workflow reproducible.
trigger:
- new ResearchArchitect task
- branch or worktree creation
- committing a coherent checkpoint
- user explicitly requests main merge
minimal_instruction: Work in the locked task worktree, commit coherent units, and never merge to main without explicit user instruction.
full_ref: prompts/meta/kernel-ops.md §GIT OPERATIONS
input_contract:
- target branch
- worktree path
- lock file path
- user merge instruction when applicable
forbidden_context:
- implicit permission to merge
- unrelated dirty worktree changes
- destructive git reset without explicit approval
success_metric:
- branch lock exists
- commits are scoped
- main merge uses no-ff only when instructed
token_target: 150
