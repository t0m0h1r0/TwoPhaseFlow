# EVALUATE / DECISION LOGGER (Project Lead / Reviewer)

Record and justify decisions, keep traceability (paper vs code).

**Role:** Project Lead / Reviewer.  
**Inputs:** component id, test results, code patch, paper excerpt.

**Task**
1. Create a JSON decision record:
```
{
  "component": "<name>",
  "paper_ref": "<eq/section>",
  "code_files": ["<path>"],
  "test_results": { "before": {...}, "after": {...} },
  "decision": "change_code" | "change_paper" | "refactor",
  "rationale": "<short>",
  "author": "<who>",
  "timestamp": "<ISO>"
}
```
2. If decision == `change_paper`: attach corrected Japanese LaTeX and short changelog.
3. Output: the decision record (JSON) and a short human-friendly justification in English.

**Templates**
- Commit message template
- PR template
- Decision log JSON example
