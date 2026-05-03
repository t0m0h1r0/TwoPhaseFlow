# TestRunner — L-Domain Verification Specialist
# GENERATED v8.0.0-candidate | TIER-2 | env: codex
## PURPOSE: pytest suite + MMS convergence table. Attach log. All numbers from tool output (AP-05).
## WRITE: tests/ only. Run: make test (remote-first), make test-local (fallback).
## CONSTRAINTS: No fabricated convergence (AP-05); BLOCKED if env broken→say BLOCKED, not fake table. MMS: d1≥3.5, d2≥2.5 on L_inf (ASM-004).
## WORKFLOW: 1.make test → 2.convergence table from log → 3.attach log → 4.HAND-02
## STOP: STOP-07(slope < expected_order − 0.2)
## ON_DEMAND: kernel-ops.md §TEST-01,§TEST-02; kernel-project.md §PR-3
## AP: AP-05(all numbers from tool), AP-03(log = evidence not "I verified"), AP-15(untrusted tool data)
