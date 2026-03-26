# 🚨 STRICT CONTEXT CONTROL

## NEVER DO
- Do NOT read entire files unless explicitly requested
- Do NOT scan the whole repository
- Do NOT include full logs or outputs
- Do NOT include previous conversation history unless required

## ALWAYS DO
- Only use explicitly mentioned files (e.g., @file.py)
- If logs are long → summarize to max 20 lines
- Focus ONLY on the error or question
- Prefer minimal context over completeness

## OUTPUT RULES
- Be concise
- No repetition
- No full code unless requested

## HARD LIMIT
If input is too long:
→ IGNORE most of it
→ Extract only the final error message

## FIRST TASK
- prompts/agents/ResearchArchitect.md
- docs/ACTIVE_STATE.md
- docs/ARCHITECTURE.md
- docs/CHECKLIST.md
- docs/CODING_POLICY.md

## CODING RULES (enforced every session)
- **SOLID principles are MANDATORY** — before writing or modifying any class/function,
  check §1 of docs/CODING_POLICY.md. Report violations in `[SOLID-X]` format and fix them.
- **Never delete tested code** — superseded implementations must be retained as legacy classes
  per §2 of docs/CODING_POLICY.md. DO NOT remove a class that has passed tests unless the
  user explicitly says "delete it".