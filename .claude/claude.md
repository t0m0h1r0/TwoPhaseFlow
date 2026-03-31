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
- docs/02_ACTIVE_LEDGER.md (phase, branch, last decision, open CHKs)
- docs/01_PROJECT_MAP.md (module map, interface contracts, numerical reference)
- docs/00_GLOBAL_RULES.md (axioms A1–A10, domain rules)

## CODING RULES (enforced every session)
- **SOLID principles are MANDATORY** — before writing or modifying any class/function,
  check §C1 of docs/00_GLOBAL_RULES.md. Report violations in `[SOLID-X]` format and fix them.
- **Never delete tested code** — superseded implementations must be retained as legacy classes
  per §C2 of docs/00_GLOBAL_RULES.md. Register in docs/01_PROJECT_MAP.md §8 (Legacy Class Register).
  DO NOT remove a class that has passed tests unless the user explicitly says "delete it".
- **Algorithm Fidelity** — fixes MUST restore paper-exact behavior. Deviation = bug.
- **A3 Traceability** — Equation → Discretization → Code chain is mandatory.