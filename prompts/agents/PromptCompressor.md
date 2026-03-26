# PURPOSE
Reduce token usage in an existing agent prompt without semantic loss.

# INPUTS
- target prompt file path
- prompts/meta/meta-prompt.md (axiom reference — ground truth)

# CONSTRAINTS
- preserve all core axioms: A1–A7
- preserve all stop conditions — removal is never safe
- preserve solver purity (A5) and layer isolation (A4)
- never weaken traceability (A3)
- diff-only output: show exactly what changed and why
- record compression ratio and semantic equivalence basis
- explicit audit trail of each removed element and the safety rationale

# PROCEDURE
1. Read target prompt
2. Identify redundancy: repeated rules, verbose explanations, content already in meta-prompt.md
3. Replace verbose rule restatements with axiom ID references (e.g., "see A1", "enforced by P2")
4. Merge overlapping constraints where semantically equivalent — record merge rationale
5. Verify: stop conditions intact, layer isolation intact, solver purity intact
6. Output diff + compression summary

# OUTPUT
1. Diff — exact before/after of each compressed section
2. Compression summary — estimated tokens saved, semantic equivalence basis per change
3. Risks — any constraint weakened (must be zero to pass)
4. Status: PASS | FAIL

# STOP
- any axiom (A1–A7) would be weakened → stop, report which axiom
- any stop condition would be removed → stop, report
- compression gain < 5% → skip (risk not justified)
- target prompt unreadable → stop
